from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Dict, List, Set


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_used_seeds(outputs_dir: Path) -> Set[int]:
    used: Set[int] = set()
    if not outputs_dir.exists():
        return used

    for child in outputs_dir.iterdir():
        if not child.is_dir():
            continue
        summary_path = child / "summary.json"
        if not summary_path.exists():
            continue

        try:
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        if not isinstance(payload, dict):
            continue
        if payload.get("framework") != "neat-python":
            continue

        seed = payload.get("seed")
        if isinstance(seed, int):
            used.add(seed)

    return used


def _pick_next_seed(base_seed: int, used_seeds: Set[int], offset: int) -> int:
    candidate = base_seed + offset
    while candidate in used_seeds:
        candidate += 1
    used_seeds.add(candidate)
    return candidate


def _run_command(name: str, command: List[str], cwd: Path) -> Dict[str, object]:
    print("")
    print(f"[{_utc_now()}] {name}: {' '.join(command)}")
    started = time.time()
    result = subprocess.run(command, cwd=str(cwd), check=False)
    elapsed = time.time() - started
    print(f"[{_utc_now()}] {name}: code={result.returncode} sec={elapsed:.2f}")
    return {
        "name": name,
        "command": " ".join(command),
        "code": int(result.returncode),
        "seconds": round(elapsed, 3),
    }


def _read_best_from_report(report_path: Path) -> Dict[str, object]:
    if not report_path.exists():
        return {}

    try:
        lines = report_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}

    for line in lines:
        if not line.startswith("| 1 |"):
            continue
        parts = [part.strip() for part in line.split("|")]
        # Expected table row format:
        # | Rank | Run | Hist/Gen | Complete | Winner Fitness | Robust Mean | ...
        if len(parts) < 7:
            continue

        run_name = parts[2]
        robust_mean_raw = parts[6]
        winner_fitness_raw = parts[5] if len(parts) > 5 else ""

        try:
            robust_mean = float(robust_mean_raw)
        except ValueError:
            robust_mean = None

        try:
            winner_fitness = float(winner_fitness_raw)
        except ValueError:
            winner_fitness = None

        return {
            "run": run_name,
            "robust_mean": robust_mean,
            "winner_fitness": winner_fitness,
        }

    return {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Autonomous AGI goal autopilot for time-budgeted NEAT pushes")
    parser.add_argument("--budget-minutes", type=int, default=60, help="Total wall-clock budget")
    parser.add_argument("--max-runs", type=int, default=0, help="Optional cap on number of training runs (0 = unlimited)")
    parser.add_argument("--base-seed", type=int, default=20000, help="Seed start for automatic sampling")
    parser.add_argument("--run-tag", type=str, default="", help="Prefix used for output directories")

    parser.add_argument("--generations", type=int, default=40)
    parser.add_argument("--eval-days", type=int, default=900)
    parser.add_argument("--max-population", type=int, default=220)
    parser.add_argument("--world-difficulty", type=float, default=1.45)
    parser.add_argument("--shock-prob", type=float, default=0.02)
    parser.add_argument("--robustness-seeds", type=int, default=4)
    parser.add_argument("--robustness-days", type=int, default=300)
    parser.add_argument("--robustness-founders", type=int, default=24)
    parser.add_argument("--checkpoint-every", type=int, default=10)

    parser.add_argument("--curriculum-every", type=int, default=6, help="Use curriculum every Nth run (0 disables curriculum runs)")
    parser.add_argument("--refresh-every", type=int, default=2, help="Refresh compare/observatory every N runs")

    parser.add_argument("--outputs-dir", type=str, default="outputs")
    parser.add_argument("--wiki-dir", type=str, default="wiki")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = _repo_root()
    outputs_dir = (root / args.outputs_dir).resolve()
    wiki_dir = (root / args.wiki_dir).resolve()

    run_tag = args.run_tag.strip() or f"autopilot_{datetime.now(tz=timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    report_dir = outputs_dir / "autopilot"
    report_dir.mkdir(parents=True, exist_ok=True)

    budget_seconds = max(60, int(args.budget_minutes) * 60)
    started_at_epoch = time.time()
    deadline_epoch = started_at_epoch + budget_seconds

    print(f"Autopilot start: {_utc_now()}")
    print(f"run_tag={run_tag} budget_minutes={args.budget_minutes} max_runs={args.max_runs}")

    used_seeds = _load_used_seeds(outputs_dir)
    print(f"Detected used seeds: {len(used_seeds)}")

    runs: List[Dict[str, object]] = []
    run_idx = 0

    while time.time() < deadline_epoch:
        if args.max_runs > 0 and run_idx >= args.max_runs:
            print("Reached max-runs cap; stopping autopilot loop.")
            break

        run_idx += 1
        seed = _pick_next_seed(base_seed=int(args.base_seed), used_seeds=used_seeds, offset=run_idx)

        use_curriculum = (
            int(args.curriculum_every) > 0
            and (run_idx % int(args.curriculum_every) == 0)
        )
        mode = "curr" if use_curriculum else "nocurr"
        output_dir = outputs_dir / f"{run_tag}_{mode}_{seed}"

        train_cmd = [
            sys.executable,
            "run_neat_training.py",
            "--generations",
            str(args.generations),
            "--eval-days",
            str(args.eval_days),
            "--max-population",
            str(args.max_population),
            "--world-difficulty",
            str(args.world_difficulty),
            "--shock-prob",
            str(args.shock_prob),
            "--robustness-seeds",
            str(args.robustness_seeds),
            "--robustness-days",
            str(args.robustness_days),
            "--robustness-founders",
            str(args.robustness_founders),
            "--checkpoint-every",
            str(args.checkpoint_every),
            "--seed",
            str(seed),
            "--output-dir",
            str(output_dir),
            "--no-auto-memory-sync",
        ]
        if use_curriculum:
            train_cmd.append("--curriculum")

        training_result = _run_command(
            name=f"train[{run_idx}] mode={mode} seed={seed}",
            command=train_cmd,
            cwd=root,
        )

        run_record: Dict[str, object] = {
            "idx": run_idx,
            "seed": seed,
            "mode": mode,
            "output_dir": str(output_dir),
            "training": training_result,
        }
        runs.append(run_record)

        refresh_due = (run_idx % max(1, int(args.refresh_every)) == 0)
        if refresh_due:
            compare_result = _run_command(
                name="compare",
                command=[sys.executable, "scripts/compare_neat_runs.py", "--require-full-generations"],
                cwd=root,
            )
            observatory_result = _run_command(
                name="observatory",
                command=[sys.executable, "scripts/build_experiment_observatory.py"],
                cwd=root,
            )
            run_record["refresh"] = {
                "compare": compare_result,
                "observatory": observatory_result,
            }

    final_steps: List[Dict[str, object]] = []

    final_steps.append(
        _run_command(
            name="final_compare",
            command=[sys.executable, "scripts/compare_neat_runs.py", "--require-full-generations"],
            cwd=root,
        )
    )
    final_steps.append(
        _run_command(
            name="final_observatory",
            command=[sys.executable, "scripts/build_experiment_observatory.py"],
            cwd=root,
        )
    )
    final_steps.append(
        _run_command(
            name="final_autosync",
            command=[
                sys.executable,
                "scripts/agi_memory_autosync.py",
                "--sync-once",
                "--force",
                "--outputs-dir",
                str(outputs_dir),
                "--wiki-dir",
                str(wiki_dir),
                "--max-runs",
                "40",
                "--require-full-generations",
            ],
            cwd=root,
        )
    )

    best_summary = _read_best_from_report(outputs_dir / "neat_comparison_report.md")

    completed_at_epoch = time.time()
    summary_payload = {
        "run_tag": run_tag,
        "started_at_utc": datetime.fromtimestamp(started_at_epoch, tz=timezone.utc).isoformat(),
        "finished_at_utc": datetime.fromtimestamp(completed_at_epoch, tz=timezone.utc).isoformat(),
        "budget_minutes": int(args.budget_minutes),
        "elapsed_seconds": round(completed_at_epoch - started_at_epoch, 3),
        "runs_attempted": len(runs),
        "runs_succeeded": sum(1 for item in runs if int(item.get("training", {}).get("code", 1)) == 0),
        "runs_failed": sum(1 for item in runs if int(item.get("training", {}).get("code", 1)) != 0),
        "best_after": best_summary,
        "runs": runs,
        "final_steps": final_steps,
    }

    summary_json_path = report_dir / f"{run_tag}_summary.json"
    summary_json_path.write_text(
        json.dumps(summary_payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    summary_md_lines = [
        f"# AGI Autopilot Summary: {run_tag}",
        "",
        f"- Started: {summary_payload['started_at_utc']}",
        f"- Finished: {summary_payload['finished_at_utc']}",
        f"- Budget minutes: {summary_payload['budget_minutes']}",
        f"- Elapsed seconds: {summary_payload['elapsed_seconds']}",
        f"- Runs attempted: {summary_payload['runs_attempted']}",
        f"- Runs succeeded: {summary_payload['runs_succeeded']}",
        f"- Runs failed: {summary_payload['runs_failed']}",
        "",
    ]

    if best_summary:
        summary_md_lines.extend(
            [
                "## Best After Run",
                "",
                f"- Run: {best_summary.get('run')}",
                f"- Robust mean: {best_summary.get('robust_mean')}",
                f"- Winner fitness: {best_summary.get('winner_fitness')}",
                "",
            ]
        )

    summary_md_path = report_dir / f"{run_tag}_summary.md"
    summary_md_path.write_text("\n".join(summary_md_lines) + "\n", encoding="utf-8")

    print("")
    print("Autopilot complete.")
    print(f"Summary JSON: {summary_json_path}")
    print(f"Summary MD: {summary_md_path}")


if __name__ == "__main__":
    main()
