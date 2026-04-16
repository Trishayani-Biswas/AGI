#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply AGI experience gate thresholds to a run summary"
    )
    parser.add_argument(
        "--config",
        default="configs/agi_experience_eval.json",
        help="Evaluation config containing thresholds",
    )
    parser.add_argument(
        "--summary-path",
        default="",
        help="Path to evaluation_summary.json (defaults to latest under outputs/agi_experience_eval)",
    )
    parser.add_argument(
        "--report-path",
        default="outputs/agi_experience_eval_gate.md",
        help="Markdown report output path",
    )
    return parser.parse_args()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def load_json_dict(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON root must be object: {path}")
    return payload


def safe_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def resolve_summary_path(root: Path, raw: str) -> Path:
    if raw.strip():
        path = Path(raw)
        return path if path.is_absolute() else root / path

    runs_root = root / "outputs" / "agi_experience_eval"
    if not runs_root.exists():
        raise RuntimeError(f"No runs directory: {runs_root}")

    candidates = [p for p in runs_root.iterdir() if p.is_dir()]
    if not candidates:
        raise RuntimeError(f"No run directories in {runs_root}")

    latest = sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0]
    summary = latest / "evaluation_summary.json"
    if not summary.exists():
        raise RuntimeError(f"Latest run missing evaluation_summary.json: {summary}")
    return summary


def main() -> None:
    args = parse_args()
    root = repo_root()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = root / config_path
    config = load_json_dict(config_path)

    summary_path = resolve_summary_path(root, args.summary_path)
    summary = load_json_dict(summary_path)

    thresholds = config.get("thresholds")
    if not isinstance(thresholds, dict):
        raise SystemExit(f"Missing thresholds in config: {config_path}")

    metrics_obj = summary.get("metrics")
    if not isinstance(metrics_obj, dict):
        raise SystemExit(f"Missing metrics in summary: {summary_path}")

    baseline_memory = safe_float(metrics_obj.get("baseline_memory_hit_rate"))
    evolved_memory = safe_float(metrics_obj.get("evolved_memory_hit_rate"))
    evolved_structured = safe_float(metrics_obj.get("evolved_structured_rate"))
    evolved_advantage = safe_float(metrics_obj.get("evolved_advantage"))

    min_evolved_memory = safe_float(thresholds.get("min_evolved_memory_hit_rate"), 0.0)
    max_baseline_memory = safe_float(thresholds.get("max_baseline_memory_hit_rate"), 1.0)
    min_evolved_structured = safe_float(thresholds.get("min_evolved_structured_rate"), 0.0)
    min_evolved_advantage = safe_float(thresholds.get("min_evolved_advantage"), 0.0)

    checks: List[Tuple[str, bool, str]] = []

    c1 = evolved_memory >= min_evolved_memory
    checks.append(
        (
            "Evolved memory hit rate meets minimum",
            c1,
            f"value={evolved_memory:.3f}, required>={min_evolved_memory:.3f}",
        )
    )

    c2 = baseline_memory <= max_baseline_memory
    checks.append(
        (
            "Baseline memory hit rate stays below max",
            c2,
            f"value={baseline_memory:.3f}, required<={max_baseline_memory:.3f}",
        )
    )

    c3 = evolved_structured >= min_evolved_structured
    checks.append(
        (
            "Evolved structured output rate meets minimum",
            c3,
            f"value={evolved_structured:.3f}, required>={min_evolved_structured:.3f}",
        )
    )

    c4 = evolved_advantage >= min_evolved_advantage
    checks.append(
        (
            "Evolved memory advantage meets minimum",
            c4,
            f"value={evolved_advantage:+.3f}, required>={min_evolved_advantage:+.3f}",
        )
    )

    tier_thresholds = [
        ("sensory", "min_evolved_sensory_hit_rate"),
        ("working", "min_evolved_working_hit_rate"),
        ("long_term", "min_evolved_long_term_hit_rate"),
        ("symbolic", "min_evolved_symbolic_hit_rate"),
    ]

    for tier_name, threshold_key in tier_thresholds:
        if threshold_key not in thresholds:
            continue

        metric_key = f"evolved_{tier_name}_hit_rate"
        metric_value = safe_float(metrics_obj.get(metric_key), 0.0)
        required = safe_float(thresholds.get(threshold_key), 0.0)
        passed = metric_value >= required

        checks.append(
            (
                f"Evolved {tier_name} memory hit rate meets minimum",
                passed,
                f"value={metric_value:.3f}, required>={required:.3f}",
            )
        )

    overall_pass = all(x[1] for x in checks)

    report_path = Path(args.report_path)
    if not report_path.is_absolute():
        report_path = root / report_path

    lines: List[str] = []
    lines.append("# AGI Experience Gate Report")
    lines.append("")
    lines.append(f"Generated: {utc_now()}")
    lines.append(f"Config: {config_path}")
    lines.append(f"Summary: {summary_path}")
    lines.append("")
    lines.append("## Metrics")
    lines.append("")
    lines.append(f"- baseline_memory_hit_rate: {baseline_memory:.3f}")
    lines.append(f"- evolved_memory_hit_rate: {evolved_memory:.3f}")
    lines.append(f"- evolved_structured_rate: {evolved_structured:.3f}")
    lines.append(f"- evolved_advantage: {evolved_advantage:+.3f}")
    for key in sorted(metrics_obj.keys()):
        if not isinstance(key, str):
            continue
        if key.startswith("evolved_") and key.endswith("_hit_rate") and key != "evolved_memory_hit_rate":
            value = safe_float(metrics_obj.get(key), 0.0)
            lines.append(f"- {key}: {value:.3f}")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for label, passed, detail in checks:
        mark = "PASS" if passed else "FAIL"
        lines.append(f"- [{mark}] {label}")
        lines.append(f"  - {detail}")
    lines.append("")
    lines.append(f"Overall gate: {'PASS' if overall_pass else 'FAIL'}")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote gate report: {report_path}")
    print(f"Gate result: {'PASS' if overall_pass else 'FAIL'}")

    if not overall_pass:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
