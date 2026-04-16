from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import subprocess
import sys
from typing import Dict, Iterable, List, Tuple


DEFAULT_SEEDS = [41001, 41002, 41003, 41004]


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _safe_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return None
    return None


def _safe_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _load_json_dict(path: Path) -> Dict[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(payload, dict):
        return payload
    return None


def _load_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8", newline="") as fp:
            return list(csv.DictReader(fp))
    except OSError:
        return []


def _resolve_seeds(raw: str) -> List[int]:
    tokens = [token.strip() for token in raw.split(",") if token.strip()]
    if not tokens:
        return list(DEFAULT_SEEDS)

    seeds: List[int] = []
    for token in tokens:
        try:
            seeds.append(int(token))
        except ValueError as exc:
            raise ValueError(f"Invalid seed value: {token}") from exc

    return seeds


def _load_candidate_config(path: Path) -> Dict[str, object]:
    payload = _load_json_dict(path)
    if payload is None:
        raise RuntimeError(f"Could not load candidates file: {path}")

    candidates = payload.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise RuntimeError(f"Candidates file has no candidates list: {path}")

    return payload


def _find_candidate(payload: Dict[str, object], candidate_id: str) -> Dict[str, object]:
    candidates = payload.get("candidates")
    assert isinstance(candidates, list)

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        if str(candidate.get("id", "")).strip() == candidate_id:
            return candidate

    raise RuntimeError(f"Candidate id not found: {candidate_id}")


def _run_simulation(command: List[str], cwd: Path, log_path: Path) -> int:
    result = subprocess.run(command, cwd=str(cwd), capture_output=True, text=True, check=False)

    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        "\n".join(
            [
                f"command: {' '.join(command)}",
                f"exit_code: {result.returncode}",
                "",
                "--- stdout ---",
                result.stdout,
                "",
                "--- stderr ---",
                result.stderr,
                "",
            ]
        ),
        encoding="utf-8",
    )

    return int(result.returncode)


def _collect_run_metrics(run_dir: Path, seed: int, exit_code: int) -> Dict[str, object]:
    summary_path = run_dir / "summary.json"
    summary = _load_json_dict(summary_path) or {}

    daily_rows = _load_csv_rows(run_dir / "daily_metrics.csv")
    daily_alive_values: List[int] = []
    for row in daily_rows:
        raw_alive = row.get("population_alive")
        alive = _safe_int(raw_alive)
        if alive is None:
            continue
        daily_alive_values.append(max(0, alive))

    configured_days = _safe_int(summary.get("configured_days"))
    simulated_days = _safe_int(summary.get("simulated_days"))
    final_alive = _safe_int(summary.get("alive_population"))
    total_agents_ever = _safe_int(summary.get("total_agents_ever"))

    if final_alive is None and daily_alive_values:
        final_alive = daily_alive_values[-1]

    if configured_days is None:
        configured_days = 0
    if simulated_days is None:
        simulated_days = 0
    if final_alive is None:
        final_alive = 0

    peak_alive = max(daily_alive_values) if daily_alive_values else max(1, final_alive)
    mean_alive = statistics.mean(daily_alive_values) if daily_alive_values else float(final_alive)

    if total_agents_ever is None or total_agents_ever <= 0:
        total_agents_ever = peak_alive

    global_innovations = summary.get("global_innovations")
    if isinstance(global_innovations, list):
        innovation_count = len(global_innovations)
    else:
        innovation_count = 0

    days_ratio = float(simulated_days) / float(configured_days) if configured_days > 0 else 0.0
    alive_ratio_peak = float(final_alive) / float(max(1, peak_alive))
    alive_ratio_ever = float(final_alive) / float(max(1, total_agents_ever))

    return {
        "seed": seed,
        "output_dir": str(run_dir),
        "exit_code": int(exit_code),
        "configured_days": configured_days,
        "simulated_days": simulated_days,
        "days_ratio": round(days_ratio, 6),
        "final_alive": final_alive,
        "population_peak": peak_alive,
        "mean_population_alive": round(float(mean_alive), 6),
        "total_agents_ever": total_agents_ever,
        "final_alive_ratio_peak": round(alive_ratio_peak, 6),
        "final_alive_ratio_ever": round(alive_ratio_ever, 6),
        "extinct": bool(final_alive == 0),
        "global_innovations": innovation_count,
        "summary_found": bool(summary),
    }


def _mean(values: Iterable[float]) -> float:
    prepared = list(values)
    if not prepared:
        return 0.0
    return float(statistics.mean(prepared))


def _summarize_records(records: List[Dict[str, object]]) -> Dict[str, object]:
    successful = [record for record in records if int(record.get("exit_code", 1)) == 0]

    alive_ratio_peak = [float(record.get("final_alive_ratio_peak", 0.0)) for record in successful]
    alive_ratio_ever = [float(record.get("final_alive_ratio_ever", 0.0)) for record in successful]
    extinction_values = [1.0 if bool(record.get("extinct", False)) else 0.0 for record in successful]
    days_ratio_values = [float(record.get("days_ratio", 0.0)) for record in successful]
    innovation_values = [float(record.get("global_innovations", 0.0)) for record in successful]
    final_alive_values = [float(record.get("final_alive", 0.0)) for record in successful]
    mean_alive_values = [float(record.get("mean_population_alive", 0.0)) for record in successful]

    total = len(records)
    total_success = len(successful)

    return {
        "runs_total": total,
        "runs_successful": total_success,
        "runs_failed": total - total_success,
        "run_success_rate": round(float(total_success) / float(total), 6) if total > 0 else 0.0,
        "mean_final_alive": round(_mean(final_alive_values), 6),
        "mean_final_alive_ratio_peak": round(_mean(alive_ratio_peak), 6),
        "mean_final_alive_ratio_ever": round(_mean(alive_ratio_ever), 6),
        "extinction_rate": round(_mean(extinction_values), 6),
        "mean_days_ratio": round(_mean(days_ratio_values), 6),
        "mean_global_innovations": round(_mean(innovation_values), 6),
        "mean_population_alive_daily": round(_mean(mean_alive_values), 6),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run seeded simulation evaluation for a model candidate and aggregate metrics"
    )
    parser.add_argument(
        "--candidates-file",
        type=str,
        default="configs/model_candidates.json",
        help="Candidate configuration JSON",
    )
    parser.add_argument("--candidate-id", type=str, required=True, help="Candidate id from config")
    parser.add_argument(
        "--outputs-root",
        type=str,
        default="",
        help="Override outputs root for candidate evaluations",
    )
    parser.add_argument(
        "--seeds",
        type=str,
        default=",".join(str(seed) for seed in DEFAULT_SEEDS),
        help="Comma-separated seed list",
    )
    parser.add_argument("--days", type=int, default=240, help="Simulation days per seed")
    parser.add_argument("--population", type=int, default=12, help="Initial population")
    parser.add_argument("--verbose-every", type=int, default=30, help="Simulation logging cadence")
    parser.add_argument(
        "--python-executable",
        type=str,
        default=sys.executable,
        help="Python executable used to call run_simulation.py",
    )
    parser.add_argument("--force", action="store_true", help="Re-run even if summary already exists")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = _repo_root()

    candidates_path = Path(args.candidates_file)
    if not candidates_path.is_absolute():
        candidates_path = root / candidates_path

    payload = _load_candidate_config(candidates_path)
    candidate = _find_candidate(payload, args.candidate_id)

    configured_outputs_root = ""
    if isinstance(payload.get("default_outputs_root"), str):
        configured_outputs_root = str(payload.get("default_outputs_root"))

    outputs_root_raw = args.outputs_root.strip() if args.outputs_root else configured_outputs_root
    if not outputs_root_raw:
        outputs_root_raw = "outputs/model_evals"

    outputs_root = Path(outputs_root_raw)
    if not outputs_root.is_absolute():
        outputs_root = root / outputs_root

    candidate_id = str(candidate.get("id"))
    candidate_dir = outputs_root / candidate_id
    candidate_dir.mkdir(parents=True, exist_ok=True)

    seeds = _resolve_seeds(args.seeds)
    run_records: List[Dict[str, object]] = []

    mode = str(candidate.get("mode", "llm")).strip().lower()
    proposer_model = str(candidate.get("proposer_model", "")).strip()
    critic_model = str(candidate.get("critic_model", "")).strip()

    print(f"[{_utc_now()}] Candidate={candidate_id} mode={mode} seeds={seeds}")

    for seed in seeds:
        run_dir = candidate_dir / f"seed_{seed}"
        summary_path = run_dir / "summary.json"

        if summary_path.exists() and not args.force:
            record = _collect_run_metrics(run_dir=run_dir, seed=seed, exit_code=0)
            record["reused_existing"] = True
            run_records.append(record)
            print(f"[{_utc_now()}] seed={seed} reused existing summary")
            continue

        run_dir.mkdir(parents=True, exist_ok=True)
        command: List[str] = [
            args.python_executable,
            str(root / "run_simulation.py"),
            "--days",
            str(args.days),
            "--population",
            str(args.population),
            "--seed",
            str(seed),
            "--output-dir",
            str(run_dir),
            "--verbose-every",
            str(args.verbose_every),
            "--no-auto-memory-sync",
        ]

        if mode == "offline":
            command.append("--offline")
        else:
            if proposer_model:
                command.extend(["--proposer-model", proposer_model])
            if critic_model:
                command.extend(["--critic-model", critic_model])

        print(f"[{_utc_now()}] seed={seed} running")
        exit_code = _run_simulation(command=command, cwd=root, log_path=run_dir / "command.log")
        record = _collect_run_metrics(run_dir=run_dir, seed=seed, exit_code=exit_code)
        record["reused_existing"] = False
        run_records.append(record)
        print(f"[{_utc_now()}] seed={seed} exit={exit_code}")

    metrics = _summarize_records(run_records)

    payload_out: Dict[str, object] = {
        "generated_at_utc": _utc_now(),
        "candidate": {
            "id": candidate_id,
            "description": candidate.get("description"),
            "host": candidate.get("host"),
            "mode": mode,
            "proposer_model": proposer_model,
            "critic_model": critic_model,
            "notes": candidate.get("notes"),
        },
        "evaluation_settings": {
            "days": int(args.days),
            "population": int(args.population),
            "verbose_every": int(args.verbose_every),
            "seeds": seeds,
        },
        "metrics": metrics,
        "run_records": run_records,
    }

    out_path = candidate_dir / "evaluation_summary.json"
    out_path.write_text(json.dumps(payload_out, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    print(f"[{_utc_now()}] Wrote evaluation summary: {out_path}")
    print(
        "Metrics: "
        f"alive_ratio_ever={metrics['mean_final_alive_ratio_ever']:.3f} "
        f"extinction_rate={metrics['extinction_rate']:.3f} "
        f"days_ratio={metrics['mean_days_ratio']:.3f} "
        f"innov={metrics['mean_global_innovations']:.3f}"
    )


if __name__ == "__main__":
    main()
