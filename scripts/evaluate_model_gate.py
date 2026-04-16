from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Dict, List, Tuple


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


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


def _fmt(value: float | None, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def _metric(summary: Dict[str, object], key: str) -> float | None:
    metrics = summary.get("metrics")
    if not isinstance(metrics, dict):
        return None
    return _safe_float(metrics.get(key))


def _load_gate_config(path: Path) -> Dict[str, object]:
    payload = _load_json_dict(path)
    if payload is None:
        raise RuntimeError(f"Could not load gate config: {path}")

    thresholds = payload.get("thresholds")
    if not isinstance(thresholds, dict):
        raise RuntimeError(f"Gate config missing thresholds object: {path}")

    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply model adoption gate by comparing candidate summary to baseline summary"
    )
    parser.add_argument(
        "--candidates-file",
        type=str,
        default="configs/model_candidates.json",
        help="Candidate configuration file",
    )
    parser.add_argument(
        "--gate-config",
        type=str,
        default="configs/model_adoption_gate.json",
        help="Gate configuration file",
    )
    parser.add_argument(
        "--outputs-root",
        type=str,
        default="",
        help="Override outputs root containing candidate evaluation summaries",
    )
    parser.add_argument("--candidate-id", type=str, required=True, help="Candidate to evaluate")
    parser.add_argument(
        "--baseline-id",
        type=str,
        default="",
        help="Optional baseline id override (otherwise read from gate config)",
    )
    parser.add_argument(
        "--report-path",
        type=str,
        default="outputs/model_adoption_gate.md",
        help="Markdown report output path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = _repo_root()

    candidates_path = Path(args.candidates_file)
    if not candidates_path.is_absolute():
        candidates_path = root / candidates_path

    candidates_payload = _load_json_dict(candidates_path)
    if candidates_payload is None:
        raise SystemExit(f"Could not load candidates file: {candidates_path}")

    configured_outputs_root = ""
    if isinstance(candidates_payload.get("default_outputs_root"), str):
        configured_outputs_root = str(candidates_payload.get("default_outputs_root"))

    outputs_root_raw = args.outputs_root.strip() if args.outputs_root else configured_outputs_root
    if not outputs_root_raw:
        outputs_root_raw = "outputs/model_evals"

    outputs_root = Path(outputs_root_raw)
    if not outputs_root.is_absolute():
        outputs_root = root / outputs_root

    gate_config_path = Path(args.gate_config)
    if not gate_config_path.is_absolute():
        gate_config_path = root / gate_config_path

    gate_payload = _load_gate_config(gate_config_path)
    thresholds = gate_payload.get("thresholds")
    assert isinstance(thresholds, dict)

    baseline_id = args.baseline_id.strip() if args.baseline_id else str(gate_payload.get("baseline_candidate_id", "")).strip()
    if not baseline_id:
        raise SystemExit("Baseline candidate id is missing. Set it in gate config or pass --baseline-id.")

    candidate_id = args.candidate_id.strip()
    if not candidate_id:
        raise SystemExit("Candidate id is required.")

    baseline_summary_path = outputs_root / baseline_id / "evaluation_summary.json"
    candidate_summary_path = outputs_root / candidate_id / "evaluation_summary.json"

    baseline_summary = _load_json_dict(baseline_summary_path)
    candidate_summary = _load_json_dict(candidate_summary_path)

    if baseline_summary is None:
        raise SystemExit(f"Baseline summary not found: {baseline_summary_path}")
    if candidate_summary is None:
        raise SystemExit(f"Candidate summary not found: {candidate_summary_path}")

    baseline_alive = _metric(baseline_summary, "mean_final_alive_ratio_ever")
    candidate_alive = _metric(candidate_summary, "mean_final_alive_ratio_ever")

    baseline_extinction = _metric(baseline_summary, "extinction_rate")
    candidate_extinction = _metric(candidate_summary, "extinction_rate")

    baseline_days = _metric(baseline_summary, "mean_days_ratio")
    candidate_days = _metric(candidate_summary, "mean_days_ratio")

    baseline_innov = _metric(baseline_summary, "mean_global_innovations")
    candidate_innov = _metric(candidate_summary, "mean_global_innovations")

    baseline_success = _metric(baseline_summary, "run_success_rate")
    candidate_success = _metric(candidate_summary, "run_success_rate")

    alive_improvement_min = _safe_float(thresholds.get("alive_ratio_improvement_min")) or 0.0
    extinction_delta_max = _safe_float(thresholds.get("max_extinction_rate_delta")) or 0.0
    days_multiplier_min = _safe_float(thresholds.get("min_days_ratio_multiplier")) or 1.0
    innovation_multiplier_min = _safe_float(thresholds.get("min_innovation_ratio_multiplier")) or 1.0
    success_delta_min = _safe_float(thresholds.get("min_run_success_rate_delta")) or 0.0

    checks: List[Tuple[str, bool, str]] = []

    alive_pass = (
        baseline_alive is not None
        and candidate_alive is not None
        and candidate_alive >= (baseline_alive * (1.0 + alive_improvement_min))
    )
    checks.append(
        (
            "Alive ratio improves by required margin",
            alive_pass,
            (
                f"candidate={_fmt(candidate_alive)} baseline={_fmt(baseline_alive)} "
                f"required>={_fmt((baseline_alive * (1.0 + alive_improvement_min)) if baseline_alive is not None else None)}"
            ),
        )
    )

    extinction_pass = (
        baseline_extinction is not None
        and candidate_extinction is not None
        and candidate_extinction <= (baseline_extinction + extinction_delta_max)
    )
    checks.append(
        (
            "Extinction rate is not worse than allowed delta",
            extinction_pass,
            (
                f"candidate={_fmt(candidate_extinction)} baseline={_fmt(baseline_extinction)} "
                f"allowed<={_fmt((baseline_extinction + extinction_delta_max) if baseline_extinction is not None else None)}"
            ),
        )
    )

    days_pass = (
        baseline_days is not None
        and candidate_days is not None
        and candidate_days >= (baseline_days * days_multiplier_min)
    )
    checks.append(
        (
            "Days-ratio meets baseline multiplier",
            days_pass,
            (
                f"candidate={_fmt(candidate_days)} baseline={_fmt(baseline_days)} "
                f"required>={_fmt((baseline_days * days_multiplier_min) if baseline_days is not None else None)}"
            ),
        )
    )

    innovation_pass = (
        baseline_innov is not None
        and candidate_innov is not None
        and candidate_innov >= (baseline_innov * innovation_multiplier_min)
    )
    checks.append(
        (
            "Innovation count meets baseline multiplier",
            innovation_pass,
            (
                f"candidate={_fmt(candidate_innov)} baseline={_fmt(baseline_innov)} "
                f"required>={_fmt((baseline_innov * innovation_multiplier_min) if baseline_innov is not None else None)}"
            ),
        )
    )

    success_pass = (
        baseline_success is not None
        and candidate_success is not None
        and candidate_success >= (baseline_success + success_delta_min)
    )
    checks.append(
        (
            "Run success rate meets required delta",
            success_pass,
            (
                f"candidate={_fmt(candidate_success)} baseline={_fmt(baseline_success)} "
                f"required>={_fmt((baseline_success + success_delta_min) if baseline_success is not None else None)}"
            ),
        )
    )

    overall_pass = all(result for _, result, _ in checks)

    report_path = Path(args.report_path)
    if not report_path.is_absolute():
        report_path = root / report_path

    lines: List[str] = []
    lines.append("# Model Adoption Gate Report")
    lines.append("")
    lines.append(f"Generated: {_utc_now()}")
    lines.append("")
    lines.append(f"Baseline id: {baseline_id}")
    lines.append(f"Candidate id: {candidate_id}")
    lines.append(f"Baseline summary: {baseline_summary_path}")
    lines.append(f"Candidate summary: {candidate_summary_path}")
    lines.append("")
    lines.append("## Thresholds")
    lines.append("")
    lines.append(f"- alive_ratio_improvement_min: {alive_improvement_min}")
    lines.append(f"- max_extinction_rate_delta: {extinction_delta_max}")
    lines.append(f"- min_days_ratio_multiplier: {days_multiplier_min}")
    lines.append(f"- min_innovation_ratio_multiplier: {innovation_multiplier_min}")
    lines.append(f"- min_run_success_rate_delta: {success_delta_min}")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for label, result, detail in checks:
        mark = "PASS" if result else "FAIL"
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
