from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
from typing import Dict, List


ROOT = Path(__file__).resolve().parents[1]


def _resolve(path_raw: str) -> Path:
    path = Path(path_raw)
    if path.is_absolute():
        return path
    return ROOT / path


def _load_json(path: Path) -> Dict[str, object] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _gate_status(report_path: Path) -> str:
    if not report_path.exists():
        return "MISSING"
    try:
        text = report_path.read_text(encoding="utf-8")
    except OSError:
        return "MISSING"
    if "Overall gate: PASS" in text:
        return "PASS"
    if "Overall gate: FAIL" in text:
        return "FAIL"
    return "UNKNOWN"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize decoding sweep results")
    parser.add_argument(
        "--run-tags",
        type=str,
        required=True,
        help="Comma-separated run tags",
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default="outputs/random_reasoning_benchmark",
        help="Benchmark output root",
    )
    parser.add_argument(
        "--summary-name",
        type=str,
        default="decoding_sweep_summary",
        help="Output summary base filename (without extension)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_root = _resolve(args.output_root)
    run_tags = [token.strip() for token in args.run_tags.split(",") if token.strip()]

    rows: List[Dict[str, object]] = []
    for tag in run_tags:
        summary_path = output_root / tag / "summary.json"
        decision_path = output_root / tag / "promotion_decision.json"
        gate_report_path = output_root / tag / "gate_report.md"

        summary = _load_json(summary_path)
        decision = _load_json(decision_path)

        if summary is None:
            rows.append(
                {
                    "run_tag": tag,
                    "available": False,
                    "gate": _gate_status(gate_report_path),
                }
            )
            continue

        aggregate = summary.get("aggregate")
        if not isinstance(aggregate, dict):
            aggregate = {}

        promoted = None
        if isinstance(decision, dict):
            promoted = bool(decision.get("promoted", False))

        rows.append(
            {
                "run_tag": tag,
                "available": True,
                "model": summary.get("model", ""),
                "max_tokens": summary.get("max_tokens", None),
                "temperature": summary.get("temperature", None),
                "top_p": summary.get("top_p", None),
                "base_accuracy_scored": float(aggregate.get("base_accuracy_scored", 0.0)),
                "paraphrase_accuracy_scored": float(aggregate.get("paraphrase_accuracy_scored", 0.0)),
                "intervention_accuracy_scored": float(aggregate.get("intervention_accuracy_scored", 0.0)),
                "repair_accuracy_scored": float(aggregate.get("repair_accuracy_scored", 0.0)),
                "consistency_rate_scored": float(aggregate.get("consistency_rate_scored", 0.0)),
                "pattern_risk_index": float(aggregate.get("pattern_risk_index", 1.0)),
                "gate": _gate_status(gate_report_path),
                "promoted": promoted,
            }
        )

    completed = [row for row in rows if row.get("available")]
    best = None
    if completed:
        best = max(
            completed,
            key=lambda row: (
                float(row.get("consistency_rate_scored", 0.0)),
                float(row.get("base_accuracy_scored", 0.0)),
                float(row.get("intervention_accuracy_scored", 0.0)),
                -float(row.get("pattern_risk_index", 1.0)),
            ),
        )

    out = {
        "run_tags": run_tags,
        "rows": rows,
        "completed_count": len(completed),
        "gate_pass_count": sum(1 for row in rows if row.get("gate") == "PASS"),
        "promoted_count": sum(1 for row in rows if row.get("promoted") is True),
        "mean_consistency": mean([float(row.get("consistency_rate_scored", 0.0)) for row in completed])
        if completed
        else 0.0,
        "best_by_consistency": best,
    }

    out_json = output_root / f"{args.summary_name}.json"
    out_md = output_root / f"{args.summary_name}.md"
    out_json.write_text(json.dumps(out, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    lines: List[str] = []
    lines.append("# Decoding Sweep Summary")
    lines.append("")
    lines.append(f"- completed_count: {out['completed_count']}")
    lines.append(f"- gate_pass_count: {out['gate_pass_count']}")
    lines.append(f"- promoted_count: {out['promoted_count']}")
    lines.append(f"- mean_consistency: {out['mean_consistency']:.3f}")
    lines.append("")

    if best is not None:
        lines.append("## Best By Consistency")
        lines.append("")
        lines.append(f"- run_tag: {best.get('run_tag')}")
        lines.append(f"- consistency_rate_scored: {float(best.get('consistency_rate_scored', 0.0)):.3f}")
        lines.append(f"- base_accuracy_scored: {float(best.get('base_accuracy_scored', 0.0)):.3f}")
        lines.append(f"- intervention_accuracy_scored: {float(best.get('intervention_accuracy_scored', 0.0)):.3f}")
        lines.append(f"- gate: {best.get('gate')}")
        lines.append(f"- promoted: {best.get('promoted')}")
        lines.append("")

    lines.append("## Runs")
    lines.append("")
    lines.append("| run_tag | temp | top_p | max_tokens | base | paraphrase | intervention | repair | consistency | risk | gate | promoted |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in rows:
        if not row.get("available"):
            lines.append(f"| {row.get('run_tag')} | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | {row.get('gate')} | n/a |")
            continue
        lines.append(
            "| {run_tag} | {temperature} | {top_p} | {max_tokens} | {base:.3f} | {para:.3f} | {interv:.3f} | {repair:.3f} | {cons:.3f} | {risk:.3f} | {gate} | {promoted} |".format(
                run_tag=row.get("run_tag"),
                temperature=row.get("temperature"),
                top_p=row.get("top_p"),
                max_tokens=row.get("max_tokens"),
                base=float(row.get("base_accuracy_scored", 0.0)),
                para=float(row.get("paraphrase_accuracy_scored", 0.0)),
                interv=float(row.get("intervention_accuracy_scored", 0.0)),
                repair=float(row.get("repair_accuracy_scored", 0.0)),
                cons=float(row.get("consistency_rate_scored", 0.0)),
                risk=float(row.get("pattern_risk_index", 1.0)),
                gate=row.get("gate"),
                promoted=row.get("promoted"),
            )
        )

    lines.append("")
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(out_json)
    print(out_md)


if __name__ == "__main__":
    main()
