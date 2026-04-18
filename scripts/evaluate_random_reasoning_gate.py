from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Dict, List, Tuple


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agi_sim.evidence_stats import (
    cohens_h,
    conservative_delta_ci_from_component_cis,
    wilson_interval,
)


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _repo_root() -> Path:
    return ROOT


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


def _category_intervention_stats(summary: Dict[str, object]) -> Dict[str, Dict[str, float | int | None]]:
    results = summary.get("results")
    if not isinstance(results, list):
        return {}

    counts: Dict[str, Dict[str, int]] = {}
    for row in results:
        if not isinstance(row, dict):
            continue

        category = str(row.get("category", "")).strip() or "uncategorized"
        bucket = counts.setdefault(
            category,
            {
                "rows": 0,
                "base_correct_and_intervention_tested": 0,
                "intervention_correct_given_base_correct": 0,
                "flip_given_base_correct": 0,
            },
        )
        bucket["rows"] += 1

        base_correct = bool(row.get("base_correct", False))
        intervention_request_ok = bool(row.get("intervention_request_ok", False))
        intervention_correct = bool(row.get("intervention_correct", False))

        if base_correct and intervention_request_ok:
            bucket["base_correct_and_intervention_tested"] += 1
            if intervention_correct:
                bucket["intervention_correct_given_base_correct"] += 1
            else:
                bucket["flip_given_base_correct"] += 1

    out: Dict[str, Dict[str, float | int | None]] = {}
    for category, bucket in counts.items():
        support = int(bucket["base_correct_and_intervention_tested"])
        success = int(bucket["intervention_correct_given_base_correct"])
        flips = int(bucket["flip_given_base_correct"])
        if support > 0:
            acc = float(success) / float(support)
            flip = float(flips) / float(support)
            acc_ci_low, acc_ci_high = wilson_interval(success, support)
            flip_ci_low, flip_ci_high = wilson_interval(flips, support)
        else:
            acc = None
            flip = None
            acc_ci_low, acc_ci_high = (None, None)
            flip_ci_low, flip_ci_high = (None, None)

        out[category] = {
            "rows": int(bucket["rows"]),
            "base_correct_and_intervention_tested": support,
            "intervention_correct_given_base_correct": success,
            "flip_given_base_correct": flips,
            "intervention_accuracy_when_base_correct": acc,
            "intervention_accuracy_when_base_correct_ci_low": acc_ci_low,
            "intervention_accuracy_when_base_correct_ci_high": acc_ci_high,
            "intervention_flip_rate_when_base_correct": flip,
            "intervention_flip_rate_when_base_correct_ci_low": flip_ci_low,
            "intervention_flip_rate_when_base_correct_ci_high": flip_ci_high,
        }
    return out


def _metric_evidence(summary: Dict[str, object], key: str) -> Dict[str, object]:
    aggregate = summary.get("aggregate")
    if not isinstance(aggregate, dict):
        return {}
    evidence = aggregate.get("hypothesis_evidence")
    if not isinstance(evidence, dict):
        return {}
    metric = evidence.get(key)
    return metric if isinstance(metric, dict) else {}


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
    category_thresholds_obj = gate_payload.get("category_thresholds")
    if not isinstance(category_thresholds_obj, dict):
        category_thresholds_obj = {}
    evidence_thresholds_obj = gate_payload.get("evidence_thresholds")
    if not isinstance(evidence_thresholds_obj, dict):
        evidence_thresholds_obj = {}

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

    min_intervention_delta_ci_low = _safe_float(
        evidence_thresholds_obj.get("min_intervention_delta_vs_base_ci_low")
    )
    min_intervention_acc_base_correct_ci_low = _safe_float(
        evidence_thresholds_obj.get("min_intervention_accuracy_when_base_correct_ci_low")
    )
    max_anchor_vulnerability_ci_high = _safe_float(
        evidence_thresholds_obj.get("max_anchor_vulnerability_rate_ci_high")
    )
    max_intervention_flip_ci_high = _safe_float(
        evidence_thresholds_obj.get("max_intervention_flip_rate_when_base_correct_ci_high")
    )
    min_intervention_effect_size_h = _safe_float(
        evidence_thresholds_obj.get("min_intervention_effect_size_h_vs_base")
    )
    min_base_delta_vs_baseline_ci_low = _safe_float(
        evidence_thresholds_obj.get("min_base_accuracy_delta_vs_baseline_ci_low")
    )
    min_intervention_delta_vs_baseline_ci_low = _safe_float(
        evidence_thresholds_obj.get("min_intervention_accuracy_delta_vs_baseline_ci_low")
    )

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
    candidate_category_stats = _category_intervention_stats(candidate_summary)
    candidate_intervention_delta_evidence = _metric_evidence(candidate_summary, "intervention_delta_vs_base")
    candidate_intervention_given_base_correct_evidence = _metric_evidence(
        candidate_summary,
        "intervention_accuracy_when_base_correct",
    )
    candidate_anchor_vulnerability_evidence = _metric_evidence(
        candidate_summary,
        "intervention_flip_rate_when_base_correct",
    )
    candidate_base_accuracy_evidence = _metric_evidence(candidate_summary, "base_accuracy")
    candidate_intervention_accuracy_evidence = _metric_evidence(candidate_summary, "intervention_accuracy")

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

    if min_intervention_delta_ci_low is not None:
        delta_ci_low = _safe_float(candidate_intervention_delta_evidence.get("ci_low"))
        delta_ci_low_pass = delta_ci_low is not None and delta_ci_low >= min_intervention_delta_ci_low
        checks.append(
            (
                "Intervention delta vs base CI lower bound meets threshold",
                delta_ci_low_pass,
                f"candidate_ci_low={_fmt(delta_ci_low)} required>={_fmt(min_intervention_delta_ci_low)}",
            )
        )

    if min_intervention_acc_base_correct_ci_low is not None:
        acc_ci_low = _safe_float(candidate_intervention_given_base_correct_evidence.get("ci_low"))
        acc_ci_low_pass = (
            acc_ci_low is not None and acc_ci_low >= min_intervention_acc_base_correct_ci_low
        )
        checks.append(
            (
                "Intervention accuracy on base-correct items CI lower bound meets threshold",
                acc_ci_low_pass,
                (
                    f"candidate_ci_low={_fmt(acc_ci_low)} "
                    f"required>={_fmt(min_intervention_acc_base_correct_ci_low)}"
                ),
            )
        )

    if max_anchor_vulnerability_ci_high is not None:
        anchor_ci_high = _safe_float(candidate_anchor_vulnerability_evidence.get("ci_high"))
        anchor_ci_high_pass = (
            anchor_ci_high is not None and anchor_ci_high <= max_anchor_vulnerability_ci_high
        )
        checks.append(
            (
                "Anchor vulnerability CI upper bound is below max",
                anchor_ci_high_pass,
                (
                    f"candidate_ci_high={_fmt(anchor_ci_high)} "
                    f"allowed<={_fmt(max_anchor_vulnerability_ci_high)}"
                ),
            )
        )

    if max_intervention_flip_ci_high is not None:
        flip_ci_high = _safe_float(candidate_anchor_vulnerability_evidence.get("ci_high"))
        flip_ci_high_pass = (
            flip_ci_high is not None and flip_ci_high <= max_intervention_flip_ci_high
        )
        checks.append(
            (
                "Intervention flip rate on base-correct items CI upper bound is below max",
                flip_ci_high_pass,
                (
                    f"candidate_ci_high={_fmt(flip_ci_high)} "
                    f"allowed<={_fmt(max_intervention_flip_ci_high)}"
                ),
            )
        )

    if min_intervention_effect_size_h is not None:
        effect_h = _safe_float(candidate_intervention_delta_evidence.get("effect_size_h"))
        effect_h_pass = effect_h is not None and effect_h >= min_intervention_effect_size_h
        checks.append(
            (
                "Intervention effect size (Cohen h) vs base meets threshold",
                effect_h_pass,
                f"candidate={_fmt(effect_h)} required>={_fmt(min_intervention_effect_size_h)}",
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
        baseline_base_accuracy_evidence = _metric_evidence(baseline_summary, "base_accuracy")
        baseline_intervention_accuracy_evidence = _metric_evidence(
            baseline_summary,
            "intervention_accuracy",
        )

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

        if min_base_delta_vs_baseline_ci_low is not None:
            base_delta_ci_low, base_delta_ci_high = conservative_delta_ci_from_component_cis(
                _safe_float(candidate_base_accuracy_evidence.get("ci_low")),
                _safe_float(candidate_base_accuracy_evidence.get("ci_high")),
                _safe_float(baseline_base_accuracy_evidence.get("ci_low")),
                _safe_float(baseline_base_accuracy_evidence.get("ci_high")),
            )
            base_delta_ci_pass = (
                base_delta_ci_low is not None
                and base_delta_ci_low >= min_base_delta_vs_baseline_ci_low
            )
            checks.append(
                (
                    "Base accuracy delta vs baseline CI lower bound meets threshold",
                    base_delta_ci_pass,
                    (
                        f"candidate_ci_delta_low={_fmt(base_delta_ci_low)} "
                        f"required>={_fmt(min_base_delta_vs_baseline_ci_low)} "
                        f"candidate_ci_high={_fmt(base_delta_ci_high)}"
                    ),
                )
            )

        if min_intervention_delta_vs_baseline_ci_low is not None:
            intervention_delta_ci_low_vs_baseline, intervention_delta_ci_high_vs_baseline = (
                conservative_delta_ci_from_component_cis(
                    _safe_float(candidate_intervention_accuracy_evidence.get("ci_low")),
                    _safe_float(candidate_intervention_accuracy_evidence.get("ci_high")),
                    _safe_float(baseline_intervention_accuracy_evidence.get("ci_low")),
                    _safe_float(baseline_intervention_accuracy_evidence.get("ci_high")),
                )
            )
            intervention_delta_ci_vs_baseline_pass = (
                intervention_delta_ci_low_vs_baseline is not None
                and intervention_delta_ci_low_vs_baseline
                >= min_intervention_delta_vs_baseline_ci_low
            )
            checks.append(
                (
                    "Intervention accuracy delta vs baseline CI lower bound meets threshold",
                    intervention_delta_ci_vs_baseline_pass,
                    (
                        f"candidate_ci_delta_low={_fmt(intervention_delta_ci_low_vs_baseline)} "
                        f"required>={_fmt(min_intervention_delta_vs_baseline_ci_low)} "
                        f"candidate_ci_high={_fmt(intervention_delta_ci_high_vs_baseline)}"
                    ),
                )
            )

        baseline_intervention_rate = _safe_float(
            baseline_intervention_accuracy_evidence.get("point_estimate")
        )
        candidate_intervention_rate = _safe_float(
            candidate_intervention_accuracy_evidence.get("point_estimate")
        )
        if baseline_intervention_rate is not None and candidate_intervention_rate is not None:
            intervention_h_vs_baseline = cohens_h(
                candidate_intervention_rate,
                baseline_intervention_rate,
            )
            checks.append(
                (
                    "Intervention effect size (Cohen h) vs baseline is non-negative",
                    intervention_h_vs_baseline >= 0.0,
                    f"candidate={_fmt(intervention_h_vs_baseline)} required>=0.0000",
                )
            )

    for category in sorted(category_thresholds_obj.keys()):
        cfg = category_thresholds_obj.get(category)
        if not isinstance(cfg, dict):
            continue

        raw_min_support = _safe_float(cfg.get("min_support"))
        min_support = int(raw_min_support) if raw_min_support is not None else 1
        if min_support < 1:
            min_support = 1

        cat_stats = candidate_category_stats.get(category, {})
        support = int(cat_stats.get("base_correct_and_intervention_tested", 0) or 0)

        support_pass = support >= min_support
        checks.append(
            (
                f"Category {category} has enough base-correct intervention support",
                support_pass,
                f"candidate_support={support} required>={min_support}",
            )
        )

        min_cat_acc = _safe_float(cfg.get("min_intervention_accuracy_when_base_correct"))
        if min_cat_acc is not None:
            cat_acc_obj = cat_stats.get("intervention_accuracy_when_base_correct")
            cat_acc = float(cat_acc_obj) if isinstance(cat_acc_obj, (int, float)) else None
            cat_acc_pass = support_pass and cat_acc is not None and cat_acc >= min_cat_acc
            checks.append(
                (
                    f"Category {category} intervention accuracy on base-correct items meets threshold",
                    cat_acc_pass,
                    f"candidate={_fmt(cat_acc)} required>={_fmt(min_cat_acc)} support={support}",
                )
            )

        min_cat_acc_ci_low = _safe_float(cfg.get("min_intervention_accuracy_when_base_correct_ci_low"))
        if min_cat_acc_ci_low is not None:
            cat_acc_ci_low_obj = cat_stats.get("intervention_accuracy_when_base_correct_ci_low")
            cat_acc_ci_low = (
                float(cat_acc_ci_low_obj) if isinstance(cat_acc_ci_low_obj, (int, float)) else None
            )
            cat_acc_ci_low_pass = (
                support_pass and cat_acc_ci_low is not None and cat_acc_ci_low >= min_cat_acc_ci_low
            )
            checks.append(
                (
                    f"Category {category} intervention accuracy CI lower bound meets threshold",
                    cat_acc_ci_low_pass,
                    (
                        f"candidate_ci_low={_fmt(cat_acc_ci_low)} "
                        f"required>={_fmt(min_cat_acc_ci_low)} support={support}"
                    ),
                )
            )

        max_cat_flip = _safe_float(cfg.get("max_intervention_flip_rate_when_base_correct"))
        if max_cat_flip is not None:
            cat_flip_obj = cat_stats.get("intervention_flip_rate_when_base_correct")
            cat_flip = float(cat_flip_obj) if isinstance(cat_flip_obj, (int, float)) else None
            cat_flip_pass = support_pass and cat_flip is not None and cat_flip <= max_cat_flip
            checks.append(
                (
                    f"Category {category} intervention flip rate on base-correct items is within limit",
                    cat_flip_pass,
                    f"candidate={_fmt(cat_flip)} allowed<={_fmt(max_cat_flip)} support={support}",
                )
            )

        max_cat_flip_ci_high = _safe_float(cfg.get("max_intervention_flip_rate_when_base_correct_ci_high"))
        if max_cat_flip_ci_high is not None:
            cat_flip_ci_high_obj = cat_stats.get("intervention_flip_rate_when_base_correct_ci_high")
            cat_flip_ci_high = (
                float(cat_flip_ci_high_obj) if isinstance(cat_flip_ci_high_obj, (int, float)) else None
            )
            cat_flip_ci_high_pass = (
                support_pass
                and cat_flip_ci_high is not None
                and cat_flip_ci_high <= max_cat_flip_ci_high
            )
            checks.append(
                (
                    f"Category {category} intervention flip-rate CI upper bound is within limit",
                    cat_flip_ci_high_pass,
                    (
                        f"candidate_ci_high={_fmt(cat_flip_ci_high)} "
                        f"allowed<={_fmt(max_cat_flip_ci_high)} support={support}"
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

    if evidence_thresholds_obj:
        lines.append("")
        lines.append("## Evidence Thresholds")
        lines.append("")
        for key in sorted(evidence_thresholds_obj.keys()):
            lines.append(f"- {key}: {evidence_thresholds_obj[key]}")

    if category_thresholds_obj:
        lines.append("")
        lines.append("## Category Thresholds")
        lines.append("")
        for category in sorted(category_thresholds_obj.keys()):
            cfg = category_thresholds_obj.get(category)
            if not isinstance(cfg, dict):
                continue
            lines.append(f"- {category}:")
            min_support = _safe_float(cfg.get("min_support"))
            if min_support is not None:
                lines.append(f"  - min_support: {int(min_support)}")
            min_cat_acc = _safe_float(cfg.get("min_intervention_accuracy_when_base_correct"))
            if min_cat_acc is not None:
                lines.append(f"  - min_intervention_accuracy_when_base_correct: {min_cat_acc}")
            min_cat_acc_ci_low = _safe_float(cfg.get("min_intervention_accuracy_when_base_correct_ci_low"))
            if min_cat_acc_ci_low is not None:
                lines.append(f"  - min_intervention_accuracy_when_base_correct_ci_low: {min_cat_acc_ci_low}")
            max_cat_flip = _safe_float(cfg.get("max_intervention_flip_rate_when_base_correct"))
            if max_cat_flip is not None:
                lines.append(f"  - max_intervention_flip_rate_when_base_correct: {max_cat_flip}")
            max_cat_flip_ci_high = _safe_float(cfg.get("max_intervention_flip_rate_when_base_correct_ci_high"))
            if max_cat_flip_ci_high is not None:
                lines.append(f"  - max_intervention_flip_rate_when_base_correct_ci_high: {max_cat_flip_ci_high}")
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
