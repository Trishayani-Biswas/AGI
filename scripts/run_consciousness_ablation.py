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


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _utc_compact() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")


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


def _resolve_seeds(raw: str) -> List[int]:
    tokens = [token.strip() for token in raw.split(",") if token.strip()]
    if not tokens:
        raise ValueError("Seed list cannot be empty")

    seeds: List[int] = []
    for token in tokens:
        try:
            seeds.append(int(token))
        except ValueError as exc:
            raise ValueError(f"Invalid seed value: {token}") from exc
    return seeds


def _mean(values: Iterable[float]) -> float:
    prepared = list(values)
    if not prepared:
        return 0.0
    return float(statistics.mean(prepared))


def _stddev(values: Iterable[float]) -> float:
    prepared = list(values)
    if len(prepared) <= 1:
        return 0.0
    return float(statistics.stdev(prepared))


def _confidence_95(values: Iterable[float]) -> Tuple[float, float]:
    prepared = list(values)
    if not prepared:
        return (0.0, 0.0)
    if len(prepared) == 1:
        only = float(prepared[0])
        return (only, only)

    mu = _mean(prepared)
    sigma = _stddev(prepared)
    half = 1.96 * (sigma / (len(prepared) ** 0.5))
    return (mu - half, mu + half)


def _extract_candidate_metrics(summary: Dict[str, object]) -> Dict[str, float]:
    evaluation = summary.get("evaluation")
    if not isinstance(evaluation, dict):
        return {}

    candidate = evaluation.get("candidate")
    if not isinstance(candidate, dict):
        return {}

    metric_keys = [
        "survival_score",
        "shock_recovery_score",
        "consistency_score",
        "metacognitive_score",
        "temporal_self_continuity_score",
        "introspective_coherence_score",
        "consciousness_proxy_score",
    ]

    result: Dict[str, float] = {}
    for key in metric_keys:
        val = _safe_float(candidate.get(key))
        if val is not None:
            result[key] = val
    return result


def _failed_checks(summary: Dict[str, object]) -> List[str]:
    evaluation = summary.get("evaluation")
    if not isinstance(evaluation, dict):
        return []

    gate = evaluation.get("gate")
    if not isinstance(gate, dict):
        return []

    checks = gate.get("checks")
    if not isinstance(checks, list):
        return []

    failed: List[str] = []
    for row in checks:
        if not isinstance(row, dict):
            continue
        name = str(row.get("name", "")).strip()
        passed = bool(row.get("passed", False))
        if name and not passed:
            failed.append(name)
    return failed


def _promoted(summary: Dict[str, object]) -> bool:
    evaluation = summary.get("evaluation")
    if not isinstance(evaluation, dict):
        return False

    gate = evaluation.get("gate")
    if not isinstance(gate, dict):
        return False

    return bool(gate.get("promoted", False))


def _memory_entries(summary: Dict[str, object]) -> int:
    states = summary.get("consciousness_states")
    if not isinstance(states, dict):
        return 0

    candidate = states.get("candidate")
    if not isinstance(candidate, dict):
        return 0

    memories = candidate.get("autobiographical_memory")
    if not isinstance(memories, list):
        return 0

    return len(memories)


def _run_campaign(
    *,
    python_executable: str,
    root: Path,
    output_dir: Path,
    seed: int,
    train_episodes: int,
    eval_episodes: int,
    days_per_episode: int,
    train_world_difficulty: float,
    train_shock_prob: float,
    eval_world_difficulty: float,
    eval_shock_prob: float,
    survival_margin: float,
    recovery_margin: float,
    consistency_margin: float,
    metacognitive_margin: float,
    temporal_continuity_margin: float,
    consciousness_margin: float,
    strategy_revision_rate: float,
    strategy_delta_clip: float,
    strategy_bias_decay: float,
    exploration_delta_clip: float,
    consciousness_bias_scale: float,
    consciousness_bias_clip: float,
    consciousness_update_rate: float,
    consciousness_contradiction_gain: float,
    disable_consciousness_stack: bool,
    force: bool,
) -> Dict[str, object]:
    summary_path = output_dir / "summary.json"
    command_log_path = output_dir / "command.log"

    if summary_path.exists() and not force:
        summary = _load_json_dict(summary_path)
        if summary is not None:
            return {
                "seed": seed,
                "output_dir": str(output_dir),
                "summary_path": str(summary_path),
                "command": "skipped_existing",
                "exit_code": 0,
                "skipped": True,
                "summary": summary,
            }

    output_dir.mkdir(parents=True, exist_ok=True)

    command: List[str] = [
        python_executable,
        "run_persistent_agi.py",
        "--seed",
        str(seed),
        "--train-episodes",
        str(train_episodes),
        "--eval-episodes",
        str(eval_episodes),
        "--days-per-episode",
        str(days_per_episode),
        "--train-world-difficulty",
        str(train_world_difficulty),
        "--train-shock-prob",
        str(train_shock_prob),
        "--eval-world-difficulty",
        str(eval_world_difficulty),
        "--eval-shock-prob",
        str(eval_shock_prob),
        "--survival-margin",
        str(survival_margin),
        "--recovery-margin",
        str(recovery_margin),
        "--consistency-margin",
        str(consistency_margin),
        "--metacognitive-margin",
        str(metacognitive_margin),
        "--temporal-continuity-margin",
        str(temporal_continuity_margin),
        "--consciousness-margin",
        str(consciousness_margin),
        "--strategy-revision-rate",
        str(strategy_revision_rate),
        "--strategy-delta-clip",
        str(strategy_delta_clip),
        "--strategy-bias-decay",
        str(strategy_bias_decay),
        "--exploration-delta-clip",
        str(exploration_delta_clip),
        "--consciousness-bias-scale",
        str(consciousness_bias_scale),
        "--consciousness-bias-clip",
        str(consciousness_bias_clip),
        "--consciousness-update-rate",
        str(consciousness_update_rate),
        "--consciousness-contradiction-gain",
        str(consciousness_contradiction_gain),
        "--output-dir",
        str(output_dir),
    ]

    if disable_consciousness_stack:
        command.append("--disable-consciousness-stack")

    result = subprocess.run(
        command,
        cwd=str(root),
        capture_output=True,
        text=True,
        check=False,
    )

    command_log_path.write_text(
        "\n".join(
            [
                f"generated_at_utc: {_utc_now()}",
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

    summary = _load_json_dict(summary_path) or {}
    return {
        "seed": seed,
        "output_dir": str(output_dir),
        "summary_path": str(summary_path),
        "command": " ".join(command),
        "exit_code": int(result.returncode),
        "skipped": False,
        "summary": summary,
    }


def _write_per_seed_csv(rows: List[Dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "seed",
        "off_exit_code",
        "on_exit_code",
        "off_promoted",
        "on_promoted",
        "off_failed_checks",
        "on_failed_checks",
        "off_memory_entries",
        "on_memory_entries",
        "survival_score_off",
        "survival_score_on",
        "survival_score_delta",
        "shock_recovery_score_off",
        "shock_recovery_score_on",
        "shock_recovery_score_delta",
        "consistency_score_off",
        "consistency_score_on",
        "consistency_score_delta",
        "metacognitive_score_off",
        "metacognitive_score_on",
        "metacognitive_score_delta",
        "temporal_self_continuity_score_off",
        "temporal_self_continuity_score_on",
        "temporal_self_continuity_score_delta",
        "introspective_coherence_score_off",
        "introspective_coherence_score_on",
        "introspective_coherence_score_delta",
        "consciousness_proxy_score_off",
        "consciousness_proxy_score_on",
        "consciousness_proxy_score_delta",
    ]

    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _build_markdown_report(
    *,
    run_tag: str,
    generated_at_utc: str,
    aggregate: Dict[str, object],
    per_seed_rows: List[Dict[str, object]],
) -> str:
    metric_rows = aggregate.get("metrics")
    if not isinstance(metric_rows, list):
        metric_rows = []

    lines: List[str] = []
    lines.append("# Multi-Seed Consciousness Ablation Report")
    lines.append("")
    lines.append(f"- run_tag: {run_tag}")
    lines.append(f"- generated_at_utc: {generated_at_utc}")
    lines.append(f"- seeds: {aggregate.get('seed_count', 0)}")
    lines.append(f"- successful_pairs: {aggregate.get('successful_pairs', 0)}")
    lines.append("")

    lines.append("## Aggregate Metric Deltas (ON - OFF)")
    lines.append("")
    lines.append("| metric | off_mean | on_mean | delta_mean | delta_95ci_low | delta_95ci_high | on_better_seed_count |")
    lines.append("| --- | ---: | ---: | ---: | ---: | ---: | ---: |")

    for row in metric_rows:
        if not isinstance(row, dict):
            continue
        lines.append(
            "| "
            f"{row.get('metric', '')} | "
            f"{float(row.get('off_mean', 0.0)):.6f} | "
            f"{float(row.get('on_mean', 0.0)):.6f} | "
            f"{float(row.get('delta_mean', 0.0)):+.6f} | "
            f"{float(row.get('delta_ci95_low', 0.0)):+.6f} | "
            f"{float(row.get('delta_ci95_high', 0.0)):+.6f} | "
            f"{int(row.get('on_better_seed_count', 0))} |"
        )

    lines.append("")
    lines.append("## Gate Outcomes")
    lines.append("")
    lines.append(f"- off_promoted_rate: {float(aggregate.get('off_promoted_rate', 0.0)):.3f}")
    lines.append(f"- on_promoted_rate: {float(aggregate.get('on_promoted_rate', 0.0)):.3f}")
    lines.append(f"- off_memory_entries_mean: {float(aggregate.get('off_memory_entries_mean', 0.0)):.3f}")
    lines.append(f"- on_memory_entries_mean: {float(aggregate.get('on_memory_entries_mean', 0.0)):.3f}")

    top_fail_off = aggregate.get("top_failed_checks_off")
    top_fail_on = aggregate.get("top_failed_checks_on")

    if isinstance(top_fail_off, list):
        lines.append(f"- top_failed_checks_off: {', '.join(str(item) for item in top_fail_off) if top_fail_off else 'none'}")
    if isinstance(top_fail_on, list):
        lines.append(f"- top_failed_checks_on: {', '.join(str(item) for item in top_fail_on) if top_fail_on else 'none'}")

    lines.append("")
    lines.append("## Per-Seed Summary")
    lines.append("")
    lines.append("| seed | off_promoted | on_promoted | delta_consciousness_proxy | delta_introspective | delta_temporal |")
    lines.append("| --- | --- | --- | ---: | ---: | ---: |")

    for row in per_seed_rows:
        lines.append(
            "| "
            f"{row.get('seed')} | "
            f"{row.get('off_promoted')} | "
            f"{row.get('on_promoted')} | "
            f"{float(row.get('consciousness_proxy_score_delta', 0.0)):+.6f} | "
            f"{float(row.get('introspective_coherence_score_delta', 0.0)):+.6f} | "
            f"{float(row.get('temporal_self_continuity_score_delta', 0.0)):+.6f} |"
        )

    lines.append("")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run paired OFF-vs-ON multi-seed consciousness ablation for persistent AGI"
    )
    parser.add_argument(
        "--seeds",
        type=str,
        default="4242,4243,4244,4245,4246,4247",
        help="Comma-separated seeds",
    )
    parser.add_argument("--train-episodes", type=int, default=16, help="Training episodes per run")
    parser.add_argument("--eval-episodes", type=int, default=8, help="Held-out eval episodes per run")
    parser.add_argument("--days-per-episode", type=int, default=240, help="Days per episode")

    parser.add_argument("--train-world-difficulty", type=float, default=1.15)
    parser.add_argument("--train-shock-prob", type=float, default=0.012)
    parser.add_argument("--eval-world-difficulty", type=float, default=1.45)
    parser.add_argument("--eval-shock-prob", type=float, default=0.03)

    parser.add_argument("--survival-margin", type=float, default=0.02)
    parser.add_argument("--recovery-margin", type=float, default=0.03)
    parser.add_argument("--consistency-margin", type=float, default=0.02)
    parser.add_argument("--metacognitive-margin", type=float, default=0.01)
    parser.add_argument("--temporal-continuity-margin", type=float, default=0.01)
    parser.add_argument("--consciousness-margin", type=float, default=0.01)
    parser.add_argument("--strategy-revision-rate", type=float, default=0.65)
    parser.add_argument("--strategy-delta-clip", type=float, default=0.12)
    parser.add_argument("--strategy-bias-decay", type=float, default=0.012)
    parser.add_argument("--exploration-delta-clip", type=float, default=0.015)
    parser.add_argument("--consciousness-bias-scale", type=float, default=0.25)
    parser.add_argument("--consciousness-bias-clip", type=float, default=0.08)
    parser.add_argument("--consciousness-update-rate", type=float, default=0.22)
    parser.add_argument("--consciousness-contradiction-gain", type=float, default=0.4)

    parser.add_argument(
        "--output-root",
        type=str,
        default="outputs/consciousness_ablation",
        help="Root directory for ablation runs",
    )
    parser.add_argument(
        "--run-tag",
        type=str,
        default="",
        help="Optional run tag. If omitted, timestamp tag is used",
    )
    parser.add_argument(
        "--python-executable",
        type=str,
        default=sys.executable,
        help="Python executable used to call run_persistent_agi.py",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run even if output summaries already exist",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = _repo_root()
    seeds = _resolve_seeds(args.seeds)

    run_tag = args.run_tag.strip() if args.run_tag else f"ablation_{_utc_compact()}"

    output_root = Path(args.output_root)
    if not output_root.is_absolute():
        output_root = root / output_root

    run_dir = output_root / run_tag
    run_dir.mkdir(parents=True, exist_ok=True)

    pair_records: List[Dict[str, object]] = []

    for seed in seeds:
        seed_dir = run_dir / f"seed_{seed}"
        off_dir = seed_dir / "off"
        on_dir = seed_dir / "on"

        off_result = _run_campaign(
            python_executable=args.python_executable,
            root=root,
            output_dir=off_dir,
            seed=seed,
            train_episodes=args.train_episodes,
            eval_episodes=args.eval_episodes,
            days_per_episode=args.days_per_episode,
            train_world_difficulty=args.train_world_difficulty,
            train_shock_prob=args.train_shock_prob,
            eval_world_difficulty=args.eval_world_difficulty,
            eval_shock_prob=args.eval_shock_prob,
            survival_margin=args.survival_margin,
            recovery_margin=args.recovery_margin,
            consistency_margin=args.consistency_margin,
            metacognitive_margin=args.metacognitive_margin,
            temporal_continuity_margin=args.temporal_continuity_margin,
            consciousness_margin=args.consciousness_margin,
            strategy_revision_rate=args.strategy_revision_rate,
            strategy_delta_clip=args.strategy_delta_clip,
            strategy_bias_decay=args.strategy_bias_decay,
            exploration_delta_clip=args.exploration_delta_clip,
            consciousness_bias_scale=args.consciousness_bias_scale,
            consciousness_bias_clip=args.consciousness_bias_clip,
            consciousness_update_rate=args.consciousness_update_rate,
            consciousness_contradiction_gain=args.consciousness_contradiction_gain,
            disable_consciousness_stack=True,
            force=args.force,
        )

        on_result = _run_campaign(
            python_executable=args.python_executable,
            root=root,
            output_dir=on_dir,
            seed=seed,
            train_episodes=args.train_episodes,
            eval_episodes=args.eval_episodes,
            days_per_episode=args.days_per_episode,
            train_world_difficulty=args.train_world_difficulty,
            train_shock_prob=args.train_shock_prob,
            eval_world_difficulty=args.eval_world_difficulty,
            eval_shock_prob=args.eval_shock_prob,
            survival_margin=args.survival_margin,
            recovery_margin=args.recovery_margin,
            consistency_margin=args.consistency_margin,
            metacognitive_margin=args.metacognitive_margin,
            temporal_continuity_margin=args.temporal_continuity_margin,
            consciousness_margin=args.consciousness_margin,
            strategy_revision_rate=args.strategy_revision_rate,
            strategy_delta_clip=args.strategy_delta_clip,
            strategy_bias_decay=args.strategy_bias_decay,
            exploration_delta_clip=args.exploration_delta_clip,
            consciousness_bias_scale=args.consciousness_bias_scale,
            consciousness_bias_clip=args.consciousness_bias_clip,
            consciousness_update_rate=args.consciousness_update_rate,
            consciousness_contradiction_gain=args.consciousness_contradiction_gain,
            disable_consciousness_stack=False,
            force=args.force,
        )

        pair_records.append(
            {
                "seed": seed,
                "off": off_result,
                "on": on_result,
            }
        )

    metric_keys = [
        "survival_score",
        "shock_recovery_score",
        "consistency_score",
        "metacognitive_score",
        "temporal_self_continuity_score",
        "introspective_coherence_score",
        "consciousness_proxy_score",
    ]

    per_seed_rows: List[Dict[str, object]] = []

    delta_collector: Dict[str, List[float]] = {key: [] for key in metric_keys}
    off_collector: Dict[str, List[float]] = {key: [] for key in metric_keys}
    on_collector: Dict[str, List[float]] = {key: [] for key in metric_keys}

    off_promoted_values: List[float] = []
    on_promoted_values: List[float] = []
    off_memory_values: List[float] = []
    on_memory_values: List[float] = []

    failed_counts_off: Dict[str, int] = {}
    failed_counts_on: Dict[str, int] = {}

    successful_pairs = 0

    for pair in pair_records:
        seed = int(pair["seed"])
        off_result = pair["off"]
        on_result = pair["on"]

        assert isinstance(off_result, dict)
        assert isinstance(on_result, dict)

        off_summary = off_result.get("summary")
        on_summary = on_result.get("summary")
        if not isinstance(off_summary, dict):
            off_summary = {}
        if not isinstance(on_summary, dict):
            on_summary = {}

        off_metrics = _extract_candidate_metrics(off_summary)
        on_metrics = _extract_candidate_metrics(on_summary)

        off_promoted = _promoted(off_summary)
        on_promoted = _promoted(on_summary)
        off_failed = _failed_checks(off_summary)
        on_failed = _failed_checks(on_summary)
        off_mem = _memory_entries(off_summary)
        on_mem = _memory_entries(on_summary)

        off_promoted_values.append(1.0 if off_promoted else 0.0)
        on_promoted_values.append(1.0 if on_promoted else 0.0)
        off_memory_values.append(float(off_mem))
        on_memory_values.append(float(on_mem))

        for name in off_failed:
            failed_counts_off[name] = failed_counts_off.get(name, 0) + 1
        for name in on_failed:
            failed_counts_on[name] = failed_counts_on.get(name, 0) + 1

        row: Dict[str, object] = {
            "seed": seed,
            "off_exit_code": int(off_result.get("exit_code", 1)),
            "on_exit_code": int(on_result.get("exit_code", 1)),
            "off_promoted": off_promoted,
            "on_promoted": on_promoted,
            "off_failed_checks": ",".join(off_failed),
            "on_failed_checks": ",".join(on_failed),
            "off_memory_entries": off_mem,
            "on_memory_entries": on_mem,
        }

        pair_ok = True
        for key in metric_keys:
            off_val = _safe_float(off_metrics.get(key))
            on_val = _safe_float(on_metrics.get(key))
            if off_val is None or on_val is None:
                pair_ok = False
                off_val = 0.0 if off_val is None else off_val
                on_val = 0.0 if on_val is None else on_val

            delta = on_val - off_val
            row[f"{key}_off"] = round(off_val, 6)
            row[f"{key}_on"] = round(on_val, 6)
            row[f"{key}_delta"] = round(delta, 6)

            off_collector[key].append(float(off_val))
            on_collector[key].append(float(on_val))
            delta_collector[key].append(float(delta))

        if pair_ok:
            successful_pairs += 1

        per_seed_rows.append(row)

    metric_summaries: List[Dict[str, object]] = []
    for key in metric_keys:
        off_vals = off_collector[key]
        on_vals = on_collector[key]
        deltas = delta_collector[key]

        ci_low, ci_high = _confidence_95(deltas)
        on_better_count = sum(1 for delta in deltas if delta > 0.0)

        metric_summaries.append(
            {
                "metric": key,
                "off_mean": round(_mean(off_vals), 6),
                "on_mean": round(_mean(on_vals), 6),
                "delta_mean": round(_mean(deltas), 6),
                "delta_std": round(_stddev(deltas), 6),
                "delta_ci95_low": round(ci_low, 6),
                "delta_ci95_high": round(ci_high, 6),
                "on_better_seed_count": int(on_better_count),
                "seed_count": len(deltas),
            }
        )

    top_failed_off = [
        f"{name}:{count}"
        for name, count in sorted(failed_counts_off.items(), key=lambda item: item[1], reverse=True)[:5]
    ]
    top_failed_on = [
        f"{name}:{count}"
        for name, count in sorted(failed_counts_on.items(), key=lambda item: item[1], reverse=True)[:5]
    ]

    generated_at_utc = _utc_now()

    aggregate: Dict[str, object] = {
        "generated_at_utc": generated_at_utc,
        "run_tag": run_tag,
        "seed_count": len(seeds),
        "successful_pairs": successful_pairs,
        "metrics": metric_summaries,
        "off_promoted_rate": round(_mean(off_promoted_values), 6),
        "on_promoted_rate": round(_mean(on_promoted_values), 6),
        "off_memory_entries_mean": round(_mean(off_memory_values), 6),
        "on_memory_entries_mean": round(_mean(on_memory_values), 6),
        "top_failed_checks_off": top_failed_off,
        "top_failed_checks_on": top_failed_on,
        "config": {
            "seeds": seeds,
            "train_episodes": args.train_episodes,
            "eval_episodes": args.eval_episodes,
            "days_per_episode": args.days_per_episode,
            "train_world_difficulty": args.train_world_difficulty,
            "train_shock_prob": args.train_shock_prob,
            "eval_world_difficulty": args.eval_world_difficulty,
            "eval_shock_prob": args.eval_shock_prob,
            "survival_margin": args.survival_margin,
            "recovery_margin": args.recovery_margin,
            "consistency_margin": args.consistency_margin,
            "metacognitive_margin": args.metacognitive_margin,
            "temporal_continuity_margin": args.temporal_continuity_margin,
            "consciousness_margin": args.consciousness_margin,
            "strategy_revision_rate": args.strategy_revision_rate,
            "strategy_delta_clip": args.strategy_delta_clip,
            "strategy_bias_decay": args.strategy_bias_decay,
            "exploration_delta_clip": args.exploration_delta_clip,
            "consciousness_bias_scale": args.consciousness_bias_scale,
            "consciousness_bias_clip": args.consciousness_bias_clip,
            "consciousness_update_rate": args.consciousness_update_rate,
            "consciousness_contradiction_gain": args.consciousness_contradiction_gain,
            "python_executable": args.python_executable,
            "force": bool(args.force),
        },
    }

    per_seed_csv_path = run_dir / "per_seed_metrics.csv"
    _write_per_seed_csv(per_seed_rows, per_seed_csv_path)

    aggregate_json_path = run_dir / "aggregate_summary.json"
    aggregate_json_path.write_text(
        json.dumps(
            {
                "aggregate": aggregate,
                "pairs": pair_records,
                "per_seed_rows": per_seed_rows,
            },
            indent=2,
            ensure_ascii=True,
        )
        + "\n",
        encoding="utf-8",
    )

    report_text = _build_markdown_report(
        run_tag=run_tag,
        generated_at_utc=generated_at_utc,
        aggregate=aggregate,
        per_seed_rows=per_seed_rows,
    )
    report_path = run_dir / "ablation_report.md"
    report_path.write_text(report_text, encoding="utf-8")

    print(f"Ablation run complete: {run_dir}")
    print(f"Per-seed CSV: {per_seed_csv_path}")
    print(f"Aggregate JSON: {aggregate_json_path}")
    print(f"Markdown report: {report_path}")


if __name__ == "__main__":
    main()
