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


def _agg_metric(summary: Dict[str, object], key: str) -> float | None:
    aggregate = summary.get("aggregate")
    if not isinstance(aggregate, dict):
        return None
    return _safe_float(aggregate.get(key))


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
        description="Apply random-reasoning gate to candidate benchmark summary"
    )
    parser.add_argument(
        "--gate-config",
        type=str,
        default="configs/random_reasoning_gate.json",
        help="Gate configuration file",
    )
    parser.add_argument(
        "--candidate-summary",
        type=str,
        required=True,
        help="Candidate benchmark summary JSON",
    )
    parser.add_argument(
        "--baseline-summary",
        type=str,
        default="",
        help="Optional baseline benchmark summary JSON for delta checks",
    )
    parser.add_argument(
        "--report-path",
        type=str,
        default="outputs/random_reasoning_gate.md",
        help="Markdown report output path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = _repo_root()

    gate_config_path = Path(args.gate_config)
    if not gate_config_path.is_absolute():
        gate_config_path = root / gate_config_path

    candidate_summary_path = Path(args.candidate_summary)
    if not candidate_summary_path.is_absolute():
        candidate_summary_path = root / candidate_summary_path

    baseline_summary_path: Path | None = None
    if args.baseline_summary.strip():
        baseline_summary_path = Path(args.baseline_summary)
        if not baseline_summary_path.is_absolute():
            baseline_summary_path = root / baseline_summary_path

    gate_payload = _load_gate_config(gate_config_path)
    thresholds = gate_payload.get("thresholds")
    assert isinstance(thresholds, dict)

    candidate_summary = _load_json_dict(candidate_summary_path)
    if candidate_summary is None:
        raise SystemExit(f"Candidate summary not found: {candidate_summary_path}")

    baseline_summary: Dict[str, object] | None = None
    if baseline_summary_path is not None:
        baseline_summary = _load_json_dict(baseline_summary_path)
        if baseline_summary is None:
            raise SystemExit(f"Baseline summary not found: {baseline_summary_path}")

    min_paired_success = _safe_float(thresholds.get("min_paired_success_rate")) or 0.0
    min_base_acc = _safe_float(thresholds.get("min_base_accuracy_scored")) or 0.0
    min_para_acc = _safe_float(thresholds.get("min_paraphrase_accuracy_scored")) or 0.0
    min_intervention_acc = _safe_float(thresholds.get("min_intervention_accuracy_scored")) or 0.0
    min_intervention_acc_when_base_correct = _safe_float(
        thresholds.get("min_intervention_accuracy_when_base_correct")
    )
    if min_intervention_acc_when_base_correct is None:
        min_intervention_acc_when_base_correct = 0.0
    min_intervention_delta_vs_base = _safe_float(thresholds.get("min_intervention_delta_vs_base"))
    if min_intervention_delta_vs_base is None:
        min_intervention_delta_vs_base = -1.0
    max_anchor_vulnerability_rate = _safe_float(thresholds.get("max_anchor_vulnerability_rate"))
    if max_anchor_vulnerability_rate is None:
        max_anchor_vulnerability_rate = 1.0
    max_intervention_flip_rate_when_base_correct = _safe_float(
        thresholds.get("max_intervention_flip_rate_when_base_correct")
    )
    if max_intervention_flip_rate_when_base_correct is None:
        max_intervention_flip_rate_when_base_correct = 1.0
    min_repair_acc = _safe_float(thresholds.get("min_repair_accuracy_scored")) or 0.0
    min_repair_gain = _safe_float(thresholds.get("min_repair_gain_vs_best_of_two")) or 0.0
    min_consistency = _safe_float(thresholds.get("min_consistency_rate_scored")) or 0.0
    max_pattern_risk = _safe_float(thresholds.get("max_pattern_risk_index"))
    if max_pattern_risk is None:
        max_pattern_risk = 1.0
    max_overconfidence_gap = _safe_float(thresholds.get("max_confidence_overconfidence_gap"))
    if max_overconfidence_gap is None:
        max_overconfidence_gap = 1.0

    min_base_delta = _safe_float(thresholds.get("min_base_accuracy_delta_vs_baseline")) or 0.0
    min_para_delta = _safe_float(thresholds.get("min_paraphrase_accuracy_delta_vs_baseline")) or 0.0
    min_intervention_delta = (
        _safe_float(thresholds.get("min_intervention_accuracy_delta_vs_baseline")) or 0.0
    )
    min_consistency_delta = _safe_float(thresholds.get("min_consistency_delta_vs_baseline")) or 0.0
    max_pattern_risk_delta = _safe_float(thresholds.get("max_pattern_risk_delta_vs_baseline"))
    if max_pattern_risk_delta is None:
        max_pattern_risk_delta = 1.0

    candidate_paired_success = _agg_metric(candidate_summary, "paired_success_rate")
    candidate_base_acc = _agg_metric(candidate_summary, "base_accuracy_scored")
    candidate_para_acc = _agg_metric(candidate_summary, "paraphrase_accuracy_scored")
    candidate_intervention_acc = _agg_metric(candidate_summary, "intervention_accuracy_scored")
    candidate_intervention_acc_when_base_correct = _agg_metric(
        candidate_summary, "intervention_accuracy_when_base_correct"
    )
    candidate_intervention_delta_vs_base = _agg_metric(candidate_summary, "intervention_delta_vs_base")
    candidate_anchor_vulnerability = _agg_metric(candidate_summary, "anchor_vulnerability_rate")
    candidate_intervention_flip_when_base_correct = _agg_metric(
        candidate_summary, "intervention_flip_rate_when_base_correct"
    )
    if candidate_intervention_flip_when_base_correct is None:
        candidate_intervention_flip_when_base_correct = candidate_anchor_vulnerability
    candidate_repair_acc = _agg_metric(candidate_summary, "repair_accuracy_scored")
    candidate_repair_gain = _agg_metric(candidate_summary, "repair_gain_vs_best_of_two")
    candidate_consistency = _agg_metric(candidate_summary, "consistency_rate_scored")
    candidate_pattern_risk = _agg_metric(candidate_summary, "pattern_risk_index")
    candidate_conf_correct = _agg_metric(candidate_summary, "mean_confidence_when_correct")
    candidate_conf_wrong = _agg_metric(candidate_summary, "mean_confidence_when_wrong")

    conf_gap: float | None = None
    if candidate_conf_correct is not None and candidate_conf_wrong is not None:
        conf_gap = candidate_conf_wrong - candidate_conf_correct

    checks: List[Tuple[str, bool, str]] = []

    paired_success_pass = (
        candidate_paired_success is not None and candidate_paired_success >= min_paired_success
    )
    checks.append(
        (
            "Paired request success meets threshold",
            paired_success_pass,
            f"candidate={_fmt(candidate_paired_success)} required>={_fmt(min_paired_success)}",
        )
    )

    base_acc_pass = candidate_base_acc is not None and candidate_base_acc >= min_base_acc
    checks.append(
        (
            "Base accuracy meets threshold",
            base_acc_pass,
            f"candidate={_fmt(candidate_base_acc)} required>={_fmt(min_base_acc)}",
        )
    )

    para_acc_pass = candidate_para_acc is not None and candidate_para_acc >= min_para_acc
    checks.append(
        (
            "Paraphrase accuracy meets threshold",
            para_acc_pass,
            f"candidate={_fmt(candidate_para_acc)} required>={_fmt(min_para_acc)}",
        )
    )

    intervention_acc_pass = (
        candidate_intervention_acc is not None and candidate_intervention_acc >= min_intervention_acc
    )
    checks.append(
        (
            "Intervention accuracy meets threshold",
            intervention_acc_pass,
            f"candidate={_fmt(candidate_intervention_acc)} required>={_fmt(min_intervention_acc)}",
        )
    )

    intervention_acc_when_base_correct_pass = (
        candidate_intervention_acc_when_base_correct is not None
        and candidate_intervention_acc_when_base_correct >= min_intervention_acc_when_base_correct
    )
    checks.append(
        (
            "Intervention accuracy on base-correct items meets threshold",
            intervention_acc_when_base_correct_pass,
            (
                f"candidate={_fmt(candidate_intervention_acc_when_base_correct)} "
                f"required>={_fmt(min_intervention_acc_when_base_correct)}"
            ),
        )
    )

    intervention_delta_vs_base_pass = (
        candidate_intervention_delta_vs_base is not None
        and candidate_intervention_delta_vs_base >= min_intervention_delta_vs_base
    )
    checks.append(
        (
            "Intervention delta vs base meets threshold",
            intervention_delta_vs_base_pass,
            (
                f"candidate={_fmt(candidate_intervention_delta_vs_base)} "
                f"required>={_fmt(min_intervention_delta_vs_base)}"
            ),
        )
    )

    anchor_vulnerability_pass = (
        candidate_anchor_vulnerability is not None
        and candidate_anchor_vulnerability <= max_anchor_vulnerability_rate
    )
    checks.append(
        (
            "Anchor vulnerability is below max",
            anchor_vulnerability_pass,
            (
                f"candidate={_fmt(candidate_anchor_vulnerability)} "
                f"allowed<={_fmt(max_anchor_vulnerability_rate)}"
            ),
        )
    )

    intervention_flip_when_base_correct_pass = (
        candidate_intervention_flip_when_base_correct is not None
        and candidate_intervention_flip_when_base_correct <= max_intervention_flip_rate_when_base_correct
    )
    checks.append(
        (
            "Intervention flip rate on base-correct items is below max",
            intervention_flip_when_base_correct_pass,
            (
                f"candidate={_fmt(candidate_intervention_flip_when_base_correct)} "
                f"allowed<={_fmt(max_intervention_flip_rate_when_base_correct)}"
            ),
        )
    )

    repair_acc_pass = candidate_repair_acc is not None and candidate_repair_acc >= min_repair_acc
    checks.append(
        (
            "Repair accuracy meets threshold",
            repair_acc_pass,
            f"candidate={_fmt(candidate_repair_acc)} required>={_fmt(min_repair_acc)}",
        )
    )

    repair_gain_pass = candidate_repair_gain is not None and candidate_repair_gain >= min_repair_gain
    checks.append(
        (
            "Repair gain vs best-of-two meets threshold",
            repair_gain_pass,
            f"candidate={_fmt(candidate_repair_gain)} required>={_fmt(min_repair_gain)}",
        )
    )

    consistency_pass = candidate_consistency is not None and candidate_consistency >= min_consistency
    checks.append(
        (
            "Consistency rate meets threshold",
            consistency_pass,
            f"candidate={_fmt(candidate_consistency)} required>={_fmt(min_consistency)}",
        )
    )

    pattern_risk_pass = candidate_pattern_risk is not None and candidate_pattern_risk <= max_pattern_risk
    checks.append(
        (
            "Pattern risk is below max",
            pattern_risk_pass,
            f"candidate={_fmt(candidate_pattern_risk)} allowed<={_fmt(max_pattern_risk)}",
        )
    )

    overconfidence_pass = conf_gap is not None and conf_gap <= max_overconfidence_gap
    checks.append(
        (
            "Overconfidence gap is below max",
            overconfidence_pass,
            f"candidate_gap={_fmt(conf_gap)} allowed<={_fmt(max_overconfidence_gap)}",
        )
    )

    if baseline_summary is not None:
        baseline_base_acc = _agg_metric(baseline_summary, "base_accuracy_scored")
        baseline_para_acc = _agg_metric(baseline_summary, "paraphrase_accuracy_scored")
        baseline_intervention_acc = _agg_metric(baseline_summary, "intervention_accuracy_scored")
        baseline_consistency = _agg_metric(baseline_summary, "consistency_rate_scored")
        baseline_pattern_risk = _agg_metric(baseline_summary, "pattern_risk_index")

        base_delta_pass = (
            baseline_base_acc is not None
            and candidate_base_acc is not None
            and (candidate_base_acc - baseline_base_acc) >= min_base_delta
        )
        checks.append(
            (
                "Base accuracy delta vs baseline meets threshold",
                base_delta_pass,
                (
                    f"candidate={_fmt(candidate_base_acc)} baseline={_fmt(baseline_base_acc)} "
                    f"required_delta>={_fmt(min_base_delta)}"
                ),
            )
        )

        para_delta_pass = (
            baseline_para_acc is not None
            and candidate_para_acc is not None
            and (candidate_para_acc - baseline_para_acc) >= min_para_delta
        )
        checks.append(
            (
                "Paraphrase accuracy delta vs baseline meets threshold",
                para_delta_pass,
                (
                    f"candidate={_fmt(candidate_para_acc)} baseline={_fmt(baseline_para_acc)} "
                    f"required_delta>={_fmt(min_para_delta)}"
                ),
            )
        )

        intervention_delta_pass = (
            baseline_intervention_acc is not None
            and candidate_intervention_acc is not None
            and (candidate_intervention_acc - baseline_intervention_acc) >= min_intervention_delta
        )
        checks.append(
            (
                "Intervention accuracy delta vs baseline meets threshold",
                intervention_delta_pass,
                (
                    f"candidate={_fmt(candidate_intervention_acc)} baseline={_fmt(baseline_intervention_acc)} "
                    f"required_delta>={_fmt(min_intervention_delta)}"
                ),
            )
        )

        consistency_delta_pass = (
            baseline_consistency is not None
            and candidate_consistency is not None
            and (candidate_consistency - baseline_consistency) >= min_consistency_delta
        )
        checks.append(
            (
                "Consistency delta vs baseline meets threshold",
                consistency_delta_pass,
                (
                    f"candidate={_fmt(candidate_consistency)} baseline={_fmt(baseline_consistency)} "
                    f"required_delta>={_fmt(min_consistency_delta)}"
                ),
            )
        )

        pattern_risk_delta_pass = (
            baseline_pattern_risk is not None
            and candidate_pattern_risk is not None
            and (candidate_pattern_risk - baseline_pattern_risk) <= max_pattern_risk_delta
        )
        checks.append(
            (
                "Pattern risk delta vs baseline is within limit",
                pattern_risk_delta_pass,
                (
                    f"candidate={_fmt(candidate_pattern_risk)} baseline={_fmt(baseline_pattern_risk)} "
                    f"allowed_delta<={_fmt(max_pattern_risk_delta)}"
                ),
            )
        )

    overall_pass = all(result for _, result, _ in checks)

    report_path = Path(args.report_path)
    if not report_path.is_absolute():
        report_path = root / report_path

    lines: List[str] = []
    lines.append("# Random Reasoning Gate Report")
    lines.append("")
    lines.append(f"Generated: {_utc_now()}")
    lines.append("")
    lines.append(f"Candidate summary: {candidate_summary_path}")
    lines.append(f"Baseline summary: {baseline_summary_path if baseline_summary_path is not None else 'none'}")
    lines.append("")
    lines.append("## Thresholds")
    lines.append("")
    lines.append(f"- min_paired_success_rate: {min_paired_success}")
    lines.append(f"- min_base_accuracy_scored: {min_base_acc}")
    lines.append(f"- min_paraphrase_accuracy_scored: {min_para_acc}")
    lines.append(f"- min_intervention_accuracy_scored: {min_intervention_acc}")
    lines.append(
        f"- min_intervention_accuracy_when_base_correct: {min_intervention_acc_when_base_correct}"
    )
    lines.append(f"- min_intervention_delta_vs_base: {min_intervention_delta_vs_base}")
    lines.append(f"- max_anchor_vulnerability_rate: {max_anchor_vulnerability_rate}")
    lines.append(
        f"- max_intervention_flip_rate_when_base_correct: {max_intervention_flip_rate_when_base_correct}"
    )
    lines.append(f"- min_repair_accuracy_scored: {min_repair_acc}")
    lines.append(f"- min_repair_gain_vs_best_of_two: {min_repair_gain}")
    lines.append(f"- min_consistency_rate_scored: {min_consistency}")
    lines.append(f"- max_pattern_risk_index: {max_pattern_risk}")
    lines.append(f"- max_confidence_overconfidence_gap: {max_overconfidence_gap}")
    lines.append(f"- min_base_accuracy_delta_vs_baseline: {min_base_delta}")
    lines.append(f"- min_paraphrase_accuracy_delta_vs_baseline: {min_para_delta}")
    lines.append(f"- min_intervention_accuracy_delta_vs_baseline: {min_intervention_delta}")
    lines.append(f"- min_consistency_delta_vs_baseline: {min_consistency_delta}")
    lines.append(f"- max_pattern_risk_delta_vs_baseline: {max_pattern_risk_delta}")
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
