from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import errno
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Dict, Iterable, List, Tuple


SOURCE_FILENAMES = {
    "summary.json",
    "robustness.json",
    "history.json",
    "generation_log.jsonl",
    "world_timeline.jsonl",
    "events.jsonl",
    "daily_metrics.csv",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _resolve_path(root: Path, raw_path: str) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return root / path


def _iter_source_files(outputs_dir: Path) -> List[Path]:
    if not outputs_dir.exists():
        return []

    matched: List[Path] = []
    for path in outputs_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.name not in SOURCE_FILENAMES:
            continue
        matched.append(path)

    matched.sort(key=lambda item: item.as_posix())
    return matched


def _compute_signature(outputs_dir: Path) -> Tuple[str, int]:
    hasher = hashlib.sha256()
    source_files = _iter_source_files(outputs_dir)

    for path in source_files:
        try:
            stat = path.stat()
        except OSError:
            continue

        hasher.update(path.as_posix().encode("utf-8"))
        hasher.update(b"|")
        hasher.update(str(stat.st_mtime_ns).encode("utf-8"))
        hasher.update(b"|")
        hasher.update(str(stat.st_size).encode("utf-8"))
        hasher.update(b"\n")

    return hasher.hexdigest(), len(source_files)


def _load_json(path: Path) -> Dict[str, object]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _run_command(command: Iterable[str], cwd: Path) -> Tuple[int, str, str]:
    result = subprocess.run(
        list(command),
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


@contextmanager
def _acquire_lock(lock_path: Path, timeout_seconds: float):
    lock_file = None
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_file = lock_path.open("w", encoding="utf-8")
    except OSError:
        yield
        return

    try:
        import fcntl  # Linux available in this workspace

        start = time.time()
        while True:
            try:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if exc.errno not in {errno.EACCES, errno.EAGAIN}:
                    raise
                if (time.time() - start) >= timeout_seconds:
                    raise TimeoutError(f"Could not acquire lock {lock_path} within {timeout_seconds}s")
                time.sleep(0.15)

        yield
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    finally:
        try:
            lock_file.close()
        except Exception:
            pass


def _sync_once(
    root: Path,
    outputs_dir: Path,
    wiki_dir: Path,
    max_runs: int,
    require_full_generations: bool,
    state_path: Path,
    force: bool,
) -> Dict[str, object]:
    signature, source_file_count = _compute_signature(outputs_dir)
    state = _load_json(state_path)
    previous_signature = state.get("signature")

    if not force and previous_signature == signature:
        return {
            "status": "no-change",
            "source_file_count": source_file_count,
            "signature": signature,
        }

    compare_cmd = [
        sys.executable,
        str(root / "scripts" / "compare_neat_runs.py"),
        "--outputs-dir",
        str(outputs_dir),
        "--report-path",
        str(outputs_dir / "neat_comparison_report.md"),
    ]
    if require_full_generations:
        compare_cmd.append("--require-full-generations")

    observatory_cmd = [
        sys.executable,
        str(root / "scripts" / "build_experiment_observatory.py"),
        "--outputs-dir",
        str(outputs_dir),
        "--report-path",
        str(outputs_dir / "experiment_observatory.md"),
    ]

    wiki_cmd = [
        sys.executable,
        str(root / "scripts" / "build_agi_wiki.py"),
        "--outputs-dir",
        str(outputs_dir),
        "--wiki-dir",
        str(wiki_dir),
        "--max-runs",
        str(max_runs),
    ]
    if require_full_generations:
        wiki_cmd.append("--require-full-generations")

    lint_cmd = [
        sys.executable,
        str(root / "scripts" / "lint_agi_wiki.py"),
        "--wiki-dir",
        str(wiki_dir),
        "--report-path",
        str(wiki_dir / "lint_report.md"),
        "--fail-on-issues",
    ]

    commands = [
        ("compare", compare_cmd),
        ("observatory", observatory_cmd),
        ("wiki", wiki_cmd),
        ("wiki_lint", lint_cmd),
    ]

    command_results: Dict[str, Dict[str, object]] = {}
    for name, cmd in commands:
        started = time.time()
        code, stdout, stderr = _run_command(cmd, cwd=root)
        elapsed = time.time() - started
        command_results[name] = {
            "code": code,
            "seconds": round(elapsed, 3),
            "stdout": stdout,
            "stderr": stderr,
            "command": " ".join(cmd),
        }

        if code != 0:
            raise RuntimeError(
                f"{name} step failed (code={code})\n"
                f"cmd: {' '.join(cmd)}\n"
                f"stdout: {stdout}\n"
                f"stderr: {stderr}"
            )

    updated_at = datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    new_state = {
        "signature": signature,
        "source_file_count": source_file_count,
        "updated_at": updated_at,
        "outputs_dir": str(outputs_dir),
        "wiki_dir": str(wiki_dir),
        "max_runs": max_runs,
        "require_full_generations": require_full_generations,
        "commands": command_results,
    }
    _write_json(state_path, new_state)

    return {
        "status": "synced",
        "source_file_count": source_file_count,
        "signature": signature,
        "updated_at": updated_at,
        "commands": command_results,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Auto-sync AGI memory artifacts: comparison, observatory, wiki, and wiki lint"
    )
    parser.add_argument("--outputs-dir", type=str, default="outputs", help="Outputs directory to watch")
    parser.add_argument("--wiki-dir", type=str, default="wiki", help="Wiki directory")
    parser.add_argument("--max-runs", type=int, default=40, help="Max runs materialized into wiki run pages")
    parser.add_argument(
        "--require-full-generations",
        action="store_true",
        help="Only include full-generation runs in compare/wiki steps",
    )
    parser.add_argument("--sync-once", action="store_true", help="Run one sync pass and exit")
    parser.add_argument("--watch", action="store_true", help="Watch outputs and sync when sources change")
    parser.add_argument("--poll-seconds", type=float, default=20.0, help="Polling interval in watch mode")
    parser.add_argument("--force", action="store_true", help="Force sync even if source signature did not change")
    parser.add_argument(
        "--state-file",
        type=str,
        default=".agi_memory_state.json",
        help="Path to autosync state file (relative to repo root if not absolute)",
    )
    parser.add_argument(
        "--lock-file",
        type=str,
        default=".agi_memory_sync.lock",
        help="Path to lock file (relative to repo root if not absolute)",
    )
    parser.add_argument(
        "--lock-timeout-seconds",
        type=float,
        default=15.0,
        help="Timeout for acquiring lock",
    )
    return parser.parse_args()


def _print_result(result: Dict[str, object]) -> None:
    status = str(result.get("status", "unknown"))
    source_count = int(result.get("source_file_count", 0))
    signature = str(result.get("signature", ""))[:12]

    if status == "no-change":
        print(
            "AGI memory sync: no-change "
            f"source_files={source_count} signature={signature}"
        )
        return

    updated_at = str(result.get("updated_at", "n/a"))
    print(
        "AGI memory sync: synced "
        f"source_files={source_count} signature={signature} updated_at={updated_at}"
    )

    commands = result.get("commands")
    if isinstance(commands, dict):
        for name, payload in commands.items():
            if not isinstance(payload, dict):
                continue
            print(
                f"- {name}: code={payload.get('code')} sec={payload.get('seconds')} "
                f"stdout={str(payload.get('stdout', ''))[:160]}"
            )


def main() -> None:
    args = parse_args()
    root = _repo_root()

    outputs_dir = _resolve_path(root, args.outputs_dir)
    wiki_dir = _resolve_path(root, args.wiki_dir)
    state_path = _resolve_path(root, args.state_file)
    lock_path = _resolve_path(root, args.lock_file)

    sync_once = args.sync_once or (not args.watch)

    if sync_once and not args.watch:
        with _acquire_lock(lock_path=lock_path, timeout_seconds=max(1.0, args.lock_timeout_seconds)):
            result = _sync_once(
                root=root,
                outputs_dir=outputs_dir,
                wiki_dir=wiki_dir,
                max_runs=max(1, args.max_runs),
                require_full_generations=bool(args.require_full_generations),
                state_path=state_path,
                force=bool(args.force),
            )
        _print_result(result)
        return

    if sync_once and args.watch:
        with _acquire_lock(lock_path=lock_path, timeout_seconds=max(1.0, args.lock_timeout_seconds)):
            result = _sync_once(
                root=root,
                outputs_dir=outputs_dir,
                wiki_dir=wiki_dir,
                max_runs=max(1, args.max_runs),
                require_full_generations=bool(args.require_full_generations),
                state_path=state_path,
                force=bool(args.force),
            )
        _print_result(result)

    print("Watching outputs for AGI memory sync. Press Ctrl+C to stop.")
    last_signature = _load_json(state_path).get("signature")

    try:
        while True:
            signature, _ = _compute_signature(outputs_dir)
            if signature != last_signature:
                with _acquire_lock(lock_path=lock_path, timeout_seconds=max(1.0, args.lock_timeout_seconds)):
                    result = _sync_once(
                        root=root,
                        outputs_dir=outputs_dir,
                        wiki_dir=wiki_dir,
                        max_runs=max(1, args.max_runs),
                        require_full_generations=bool(args.require_full_generations),
                        state_path=state_path,
                        force=False,
                    )
                _print_result(result)
                last_signature = str(result.get("signature", last_signature))
            time.sleep(max(2.0, args.poll_seconds))
    except KeyboardInterrupt:
        print("Stopped AGI memory watch mode.")


if __name__ == "__main__":
    main()
