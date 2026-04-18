from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
from typing import Dict, List, Set


ROOT = Path(__file__).resolve().parents[1]


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _load_json_dict(path: Path) -> Dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _run(cmd: List[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def _parse_ollama_list_output(raw: str) -> Set[str]:
    installed: Set[str] = set()
    for line in raw.splitlines():
        cleaned = line.strip()
        if not cleaned:
            continue
        if cleaned.lower().startswith("name"):
            continue

        # ollama list prints "model:tag size modified"
        model_name = cleaned.split()[0].strip()
        if model_name:
            installed.add(model_name)
    return installed


def _collect_local_models_from_candidates(candidates_payload: Dict[str, object]) -> Set[str]:
    collected: Set[str] = set()
    candidates = candidates_payload.get("candidates")
    if not isinstance(candidates, list):
        return collected

    for row in candidates:
        if not isinstance(row, dict):
            continue
        if str(row.get("host", "")).strip().lower() != "local":
            continue
        if str(row.get("mode", "")).strip().lower() != "llm":
            continue

        proposer = str(row.get("proposer_model", "")).strip()
        critic = str(row.get("critic_model", "")).strip()
        if proposer:
            collected.add(proposer)
        if critic:
            collected.add(critic)

    return collected


def _collect_targets(expansion_payload: Dict[str, object]) -> Set[str]:
    targets: Set[str] = set()
    local_targets = expansion_payload.get("local_model_targets")
    if not isinstance(local_targets, list):
        return targets
    for item in local_targets:
        model = str(item).strip()
        if model:
            targets.add(model)
    return targets


def _build_markdown_report(report: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# Capability Expansion Audit")
    lines.append("")
    lines.append(f"- generated_at_utc: {report.get('generated_at_utc', '')}")
    lines.append(f"- ollama_available: {report.get('ollama_available', False)}")
    lines.append("")

    installed = report.get("installed_local_models", [])
    required = report.get("required_local_models", [])
    missing = report.get("missing_local_models", [])

    lines.append("## Local Model Inventory")
    lines.append("")
    lines.append(f"- installed_count: {len(installed) if isinstance(installed, list) else 0}")
    lines.append(f"- required_count: {len(required) if isinstance(required, list) else 0}")
    lines.append(f"- missing_count: {len(missing) if isinstance(missing, list) else 0}")
    lines.append("")

    lines.append("### Missing Local Models")
    lines.append("")
    if isinstance(missing, list) and missing:
        for model in missing:
            lines.append(f"- {model}")
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Recommended Commands")
    lines.append("")
    commands = report.get("recommended_commands", [])
    if isinstance(commands, list) and commands:
        for cmd in commands:
            lines.append(f"- {cmd}")
    else:
        lines.append("- none")
    lines.append("")

    hosted = report.get("hosted_baseline_targets", [])
    lines.append("## Hosted Baseline Targets (Optional)")
    lines.append("")
    if isinstance(hosted, list) and hosted:
        for item in hosted:
            lines.append(f"- {item}")
    else:
        lines.append("- none")
    lines.append("")

    repos = report.get("external_reference_repos", [])
    lines.append("## External Reference Repos")
    lines.append("")
    if isinstance(repos, list) and repos:
        for repo in repos:
            lines.append(f"- https://github.com/{repo}")
    else:
        lines.append("- none")
    lines.append("")

    notes = str(report.get("notes", "")).strip()
    if notes:
        lines.append("## Notes")
        lines.append("")
        lines.append(f"- {notes}")
        lines.append("")

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit model/tool expansion opportunities and generate execution commands"
    )
    parser.add_argument(
        "--candidates-config",
        type=str,
        default="configs/model_candidates.json",
        help="Candidate model registry",
    )
    parser.add_argument(
        "--expansion-config",
        type=str,
        default="configs/capability_expansion_targets.json",
        help="Expansion targets and optional references",
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default="outputs/capability_expansion",
        help="Output directory for audit artifacts",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write JSON and markdown artifacts",
    )
    parser.add_argument(
        "--pull-missing",
        action="store_true",
        help="Attempt to pull missing local models via Ollama",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    candidates_path = Path(args.candidates_config)
    if not candidates_path.is_absolute():
        candidates_path = ROOT / candidates_path

    expansion_path = Path(args.expansion_config)
    if not expansion_path.is_absolute():
        expansion_path = ROOT / expansion_path

    output_root = Path(args.output_root)
    if not output_root.is_absolute():
        output_root = ROOT / output_root

    candidates_payload = _load_json_dict(candidates_path)
    expansion_payload = _load_json_dict(expansion_path)

    required_models = _collect_local_models_from_candidates(candidates_payload)
    required_models.update(_collect_targets(expansion_payload))

    ollama_bin = shutil.which("ollama")
    installed_models: Set[str] = set()
    ollama_available = bool(ollama_bin)

    if ollama_available:
        proc = _run(["ollama", "list"])
        if proc.returncode == 0:
            installed_models = _parse_ollama_list_output(proc.stdout)

    missing_models = sorted(required_models - installed_models)

    pulled_models: List[str] = []
    failed_pulls: List[str] = []
    if args.pull_missing and ollama_available:
        for model in list(missing_models):
            pull_proc = _run(["ollama", "pull", model])
            if pull_proc.returncode == 0:
                pulled_models.append(model)
            else:
                failed_pulls.append(model)

        installed_models = set(installed_models)
        installed_models.update(pulled_models)
        missing_models = sorted(required_models - installed_models)

    recommended_commands: List[str] = []
    if not ollama_available:
        recommended_commands.append("curl -fsSL https://ollama.com/install.sh | sh")
    for model in missing_models:
        recommended_commands.append(f"ollama pull {model}")

    run_eval_hint = (
        ".venv/bin/python scripts/run_model_eval.py --candidate-id <candidate_id> --seed-count 8"
    )
    build_matrix_hint = ".venv/bin/python scripts/build_model_comparison_matrix.py"
    gate_hint = ".venv/bin/python scripts/evaluate_model_gate.py --candidate-id <candidate_id>"

    recommended_commands.extend([run_eval_hint, build_matrix_hint, gate_hint])

    hosted_targets = expansion_payload.get("hosted_baseline_targets")
    if not isinstance(hosted_targets, list):
        hosted_targets = []

    external_repos = expansion_payload.get("external_reference_repos")
    if not isinstance(external_repos, list):
        external_repos = []

    notes = str(expansion_payload.get("notes", "")).strip()

    report: Dict[str, object] = {
        "generated_at_utc": _utc_now(),
        "ollama_available": ollama_available,
        "candidates_config": str(candidates_path),
        "expansion_config": str(expansion_path),
        "required_local_models": sorted(required_models),
        "installed_local_models": sorted(installed_models),
        "missing_local_models": missing_models,
        "pulled_models": pulled_models,
        "failed_pulls": failed_pulls,
        "recommended_commands": recommended_commands,
        "hosted_baseline_targets": hosted_targets,
        "external_reference_repos": external_repos,
        "notes": notes,
    }

    print(json.dumps(report, indent=2, ensure_ascii=True))

    if args.write:
        output_root.mkdir(parents=True, exist_ok=True)
        json_path = output_root / "latest_audit.json"
        md_path = output_root / "latest_audit.md"
        json_path.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        md_path.write_text(_build_markdown_report(report), encoding="utf-8")
        print(f"wrote: {json_path}")
        print(f"wrote: {md_path}")


if __name__ == "__main__":
    main()
