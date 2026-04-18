#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from typing import Any, Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _run(cmd: List[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)


def _repo_clean() -> bool:
    proc = _run(["git", "status", "--short"])
    if proc.returncode != 0:
        return False
    return proc.stdout.strip() == ""


def _load_json_dict(path: Path) -> Optional[Dict[str, Any]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(payload, dict):
        return payload
    return None


def _latest_paths(pattern: str, limit: int = 10) -> List[Path]:
    items = [p for p in ROOT.glob(pattern) if p.is_file()]
    items.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return items[:limit]


def _gate_status_from_report(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    overall = "UNKNOWN"
    for line in text.splitlines():
        if line.startswith("Overall gate:"):
            overall = line.split(":", 1)[1].strip()
            break

    fail_checks: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("- [FAIL]"):
            fail_checks.append(stripped)

    return {
        "path": str(path.relative_to(ROOT)),
        "overall": overall,
        "fail_checks": fail_checks,
    }


def _latest_reasoning_snapshot() -> Dict[str, Any]:
    summaries = _latest_paths("outputs/random_reasoning_benchmark/*/summary.json", limit=20)
    if not summaries:
        return {"available": False}

    def _eligible_payload(path: Path) -> Optional[Dict[str, Any]]:
        payload = _load_json_dict(path)
        if payload is None:
            return None
        aggregate = payload.get("aggregate")
        if not isinstance(aggregate, dict):
            return None
        questions = aggregate.get("questions_evaluated")
        if not isinstance(questions, int) or questions < 10:
            return None
        return payload

    picked_path: Optional[Path] = None
    picked_payload: Optional[Dict[str, Any]] = None

    # Prefer a substantial run that already has a gate report.
    for candidate in summaries:
        payload = _eligible_payload(candidate)
        if payload is None:
            continue
        run_dir = candidate.parent
        gate_reports = sorted(run_dir.glob("gate*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        if gate_reports:
            picked_path = candidate
            picked_payload = payload
            break

    if picked_path is None:
        # Fall back to the latest substantial run even if no gate report exists yet.
        for candidate in summaries:
            payload = _eligible_payload(candidate)
            if payload is None:
                continue
            picked_path = candidate
            picked_payload = payload
            break

    if picked_path is None:
        picked_path = summaries[0]
        picked_payload = _load_json_dict(picked_path)

    if picked_payload is None:
        return {
            "available": False,
            "latest_summary_path": str(picked_path.relative_to(ROOT)),
            "error": "summary_json_unreadable",
        }

    aggregate = picked_payload.get("aggregate")
    if not isinstance(aggregate, dict):
        aggregate = {}

    run_dir = picked_path.parent
    gate_reports = sorted(run_dir.glob("gate*.md"), key=lambda p: p.stat().st_mtime, reverse=True)

    gate_info = None
    if gate_reports:
        gate_info = _gate_status_from_report(gate_reports[0])

    return {
        "available": True,
        "summary_path": str(picked_path.relative_to(ROOT)),
        "run_tag": str(picked_payload.get("run_tag", "")),
        "model": str(picked_payload.get("model", "")),
        "benchmark_version": str(picked_payload.get("benchmark_version", "")),
        "questions_evaluated": aggregate.get("questions_evaluated"),
        "metrics": {
            "base_accuracy_scored": aggregate.get("base_accuracy_scored"),
            "paraphrase_accuracy_scored": aggregate.get("paraphrase_accuracy_scored"),
            "intervention_accuracy_scored": aggregate.get("intervention_accuracy_scored"),
            "intervention_delta_vs_base": aggregate.get("intervention_delta_vs_base"),
            "anchor_vulnerability_rate": aggregate.get("anchor_vulnerability_rate"),
            "intervention_accuracy_when_base_correct": aggregate.get("intervention_accuracy_when_base_correct"),
            "intervention_flip_rate_when_base_correct": aggregate.get("intervention_flip_rate_when_base_correct"),
            "consistency_rate_scored": aggregate.get("consistency_rate_scored"),
            "pattern_risk_index": aggregate.get("pattern_risk_index"),
        },
        "latest_gate_report": gate_info,
    }


def _build_snapshot() -> Dict[str, Any]:
    code_paths = {
        "evolution_track": (ROOT / "src/agi_sim/neat_training.py").exists(),
        "persistent_single_agent_track": (ROOT / "src/agi_sim/persistent_agent.py").exists(),
        "dual_llm_track": (ROOT / "src/agi_sim/llm.py").exists(),
        "reasoning_gate_track": (ROOT / "scripts/evaluate_random_reasoning_gate.py").exists(),
    }

    return {
        "generated_at_utc": _utc_now(),
        "source_of_truth": "code_and_artifacts_first",
        "repo_clean": _repo_clean(),
        "code_tracks_present": code_paths,
        "latest_reasoning_snapshot": _latest_reasoning_snapshot(),
    }


def _to_markdown(snapshot: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# Research Status Snapshot")
    lines.append("")
    lines.append(f"- generated_at_utc: {snapshot.get('generated_at_utc', '')}")
    lines.append(f"- source_of_truth: {snapshot.get('source_of_truth', '')}")
    lines.append(f"- repo_clean: {snapshot.get('repo_clean', False)}")
    lines.append("")

    lines.append("## Code Tracks")
    lines.append("")
    tracks = snapshot.get("code_tracks_present")
    if isinstance(tracks, dict):
        for key, val in tracks.items():
            lines.append(f"- {key}: {bool(val)}")

    lines.append("")
    lines.append("## Latest Reasoning Snapshot")
    lines.append("")
    latest = snapshot.get("latest_reasoning_snapshot")
    if isinstance(latest, dict):
        if not latest.get("available", False):
            lines.append("- available: false")
        else:
            lines.append(f"- summary_path: {latest.get('summary_path', '')}")
            lines.append(f"- run_tag: {latest.get('run_tag', '')}")
            lines.append(f"- model: {latest.get('model', '')}")
            lines.append(f"- benchmark_version: {latest.get('benchmark_version', '')}")
            lines.append(f"- questions_evaluated: {latest.get('questions_evaluated', '')}")
            metrics = latest.get("metrics")
            if isinstance(metrics, dict):
                for key, val in metrics.items():
                    lines.append(f"- {key}: {val}")
            gate = latest.get("latest_gate_report")
            if isinstance(gate, dict):
                lines.append(f"- latest_gate_report: {gate.get('path', '')}")
                lines.append(f"- gate_overall: {gate.get('overall', '')}")
                fails = gate.get("fail_checks")
                if isinstance(fails, list) and fails:
                    lines.append("- gate_fail_checks:")
                    for item in fails:
                        lines.append(f"  - {item}")

    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build ground-truth research status snapshot")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write outputs/research_status/latest_status.json and .md",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs/research_status",
        help="Output directory when --write is enabled",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    snapshot = _build_snapshot()
    print(json.dumps(snapshot, indent=2, ensure_ascii=True))

    if args.write:
        out_dir = Path(args.output_dir)
        if not out_dir.is_absolute():
            out_dir = ROOT / out_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        json_path = out_dir / "latest_status.json"
        md_path = out_dir / "latest_status.md"
        json_path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        md_path.write_text(_to_markdown(snapshot), encoding="utf-8")
        print(f"wrote {json_path}")
        print(f"wrote {md_path}")


if __name__ == "__main__":
    main()
