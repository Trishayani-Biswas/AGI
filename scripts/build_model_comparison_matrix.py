from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Dict, List


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


def _fmt(value: float | None, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def _fmt_delta(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:+.3f}"


def _load_candidate_payload(path: Path) -> Dict[str, object]:
    payload = _load_json_dict(path)
    if payload is None:
        raise RuntimeError(f"Could not read candidates file: {path}")

    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        raise RuntimeError(f"Candidates file has invalid candidates list: {path}")

    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build markdown model comparison matrix from candidate evaluation summaries"
    )
    parser.add_argument(
        "--candidates-file",
        type=str,
        default="configs/model_candidates.json",
        help="Candidate configuration JSON",
    )
    parser.add_argument(
        "--outputs-root",
        type=str,
        default="",
        help="Override outputs root where evaluation summaries are stored",
    )
    parser.add_argument(
        "--baseline-id",
        type=str,
        default="local_baseline",
        help="Baseline candidate id for delta columns",
    )
    parser.add_argument(
        "--report-path",
        type=str,
        default="outputs/model_comparison_matrix.md",
        help="Markdown output path",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = _repo_root()

    candidates_path = Path(args.candidates_file)
    if not candidates_path.is_absolute():
        candidates_path = root / candidates_path

    payload = _load_candidate_payload(candidates_path)

    configured_outputs_root = ""
    if isinstance(payload.get("default_outputs_root"), str):
        configured_outputs_root = str(payload.get("default_outputs_root"))

    outputs_root_raw = args.outputs_root.strip() if args.outputs_root else configured_outputs_root
    if not outputs_root_raw:
        outputs_root_raw = "outputs/model_evals"

    outputs_root = Path(outputs_root_raw)
    if not outputs_root.is_absolute():
        outputs_root = root / outputs_root

    report_path = Path(args.report_path)
    if not report_path.is_absolute():
        report_path = root / report_path

    candidates = payload.get("candidates")
    assert isinstance(candidates, list)

    rows: List[Dict[str, object]] = []
    baseline_alive_ratio: float | None = None

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue

        candidate_id = str(candidate.get("id", "")).strip()
        if not candidate_id:
            continue

        summary_path = outputs_root / candidate_id / "evaluation_summary.json"
        summary = _load_json_dict(summary_path)

        metrics_obj: Dict[str, object] = {}
        if isinstance(summary, dict):
            payload_metrics = summary.get("metrics")
            if isinstance(payload_metrics, dict):
                metrics_obj = payload_metrics

        alive_ratio = _safe_float(metrics_obj.get("mean_final_alive_ratio_ever"))
        extinction_rate = _safe_float(metrics_obj.get("extinction_rate"))
        days_ratio = _safe_float(metrics_obj.get("mean_days_ratio"))
        innovations = _safe_float(metrics_obj.get("mean_global_innovations"))
        runs_total = metrics_obj.get("runs_total")
        runs_success = metrics_obj.get("runs_successful")

        if candidate_id == args.baseline_id:
            baseline_alive_ratio = alive_ratio

        if summary is None:
            status = "no-data"
        else:
            failed = int(metrics_obj.get("runs_failed", 0)) if isinstance(metrics_obj.get("runs_failed"), (int, float)) else 0
            status = "partial" if failed > 0 else "ready"

        rows.append(
            {
                "candidate_id": candidate_id,
                "host": str(candidate.get("host", "n/a")),
                "mode": str(candidate.get("mode", "n/a")),
                "proposer_model": str(candidate.get("proposer_model", "n/a")),
                "critic_model": str(candidate.get("critic_model", "n/a")),
                "runs_total": runs_total if isinstance(runs_total, (int, float)) else "n/a",
                "runs_success": runs_success if isinstance(runs_success, (int, float)) else "n/a",
                "alive_ratio": alive_ratio,
                "extinction_rate": extinction_rate,
                "days_ratio": days_ratio,
                "innovations": innovations,
                "notes": str(candidate.get("notes", "")),
                "summary_path": summary_path,
                "status": status,
            }
        )

    def _sort_key(row: Dict[str, object]):
        alive_ratio = row.get("alive_ratio")
        if isinstance(alive_ratio, float):
            return (1, alive_ratio)
        return (0, -1.0)

    rows.sort(key=_sort_key, reverse=True)

    lines: List[str] = []
    lines.append("# Model Comparison Matrix")
    lines.append("")
    lines.append(f"Generated: {_utc_now()}")
    lines.append("")
    lines.append("Local-first rule: run local candidates first, use hosted models only as optional baselines.")
    lines.append("")
    lines.append("| Candidate | Host | Mode | Proposer | Critic | Runs (ok/total) | Alive Ratio (ever) | Delta vs Baseline | Extinction Rate | Days Ratio | Mean Innovations | Status |")
    lines.append("| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |")

    for row in rows:
        alive_ratio = row.get("alive_ratio")
        delta = None
        if isinstance(alive_ratio, float) and isinstance(baseline_alive_ratio, float):
            delta = alive_ratio - baseline_alive_ratio

        runs_success = row.get("runs_success")
        runs_total = row.get("runs_total")
        runs_cell = "n/a"
        if isinstance(runs_success, (int, float)) and isinstance(runs_total, (int, float)):
            runs_cell = f"{int(runs_success)}/{int(runs_total)}"

        lines.append(
            "| "
            f"{row['candidate_id']} | "
            f"{row['host']} | "
            f"{row['mode']} | "
            f"{row['proposer_model']} | "
            f"{row['critic_model']} | "
            f"{runs_cell} | "
            f"{_fmt(row.get('alive_ratio'))} | "
            f"{_fmt_delta(delta)} | "
            f"{_fmt(row.get('extinction_rate'))} | "
            f"{_fmt(row.get('days_ratio'))} | "
            f"{_fmt(row.get('innovations'))} | "
            f"{row['status']} |"
        )

    lines.append("")
    lines.append("## AI Toolkit Actions")
    lines.append("")
    lines.append("1. Use Model Catalog to shortlist proposer/critic candidates.")
    lines.append("2. Use Model Playground to sanity-check decision JSON format consistency.")
    lines.append("3. Run seeded evals with `scripts/run_model_eval.py` for shortlisted candidates.")
    lines.append("4. Apply adoption gate with `scripts/evaluate_model_gate.py` before promoting a candidate.")
    lines.append("")
    lines.append("Command IDs you can run from VS Code Command Palette:")
    lines.append("- `ai-mlstudio.models`")
    lines.append("- `ai-mlstudio.modelPlayground`")
    lines.append("- `ai-mlstudio.openTestTool`")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote model comparison matrix: {report_path}")


if __name__ == "__main__":
    main()
