from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Tuple


ALLOWED_ACTIONS = [
    "search_water",
    "search_food",
    "drink_reserve",
    "eat_reserve",
    "build_shelter",
    "rest",
    "cooperate",
    "mate",
    "experiment",
]


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


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


def _iter_simulation_run_dirs(inputs_root: Path) -> List[Path]:
    run_dirs: List[Path] = []
    if not inputs_root.exists():
        return run_dirs

    for summary_path in inputs_root.rglob("summary.json"):
        run_dir = summary_path.parent
        events_path = run_dir / "events.jsonl"
        if not events_path.exists():
            continue
        run_dirs.append(run_dir)

    run_dirs.sort(key=lambda item: item.as_posix())
    return run_dirs


def _classify_run(
    summary: Dict[str, object],
    high_threshold: float,
    failure_alive_threshold: float,
    failure_days_threshold: float,
) -> Tuple[str, float, float]:
    configured_days = _safe_int(summary.get("configured_days")) or 0
    simulated_days = _safe_int(summary.get("simulated_days")) or 0
    final_alive = _safe_int(summary.get("alive_population")) or 0
    total_agents_ever = _safe_int(summary.get("total_agents_ever")) or max(1, final_alive)

    days_ratio = float(simulated_days) / float(configured_days) if configured_days > 0 else 0.0
    alive_ratio_ever = float(final_alive) / float(max(1, total_agents_ever))

    blended_score = (0.7 * alive_ratio_ever) + (0.3 * days_ratio)

    if blended_score >= high_threshold:
        return ("high_survivor", alive_ratio_ever, days_ratio)

    if final_alive == 0 or alive_ratio_ever <= failure_alive_threshold or days_ratio <= failure_days_threshold:
        return ("failure", alive_ratio_ever, days_ratio)

    return ("neutral", alive_ratio_ever, days_ratio)


def _build_split_key(run_name: str, line_number: int, validation_ratio: float) -> str:
    digest = hashlib.sha256(f"{run_name}:{line_number}".encode("utf-8")).hexdigest()
    bucket = int(digest[:8], 16) / float(0xFFFFFFFF)
    return "validation" if bucket < validation_ratio else "train"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Curate fine-tuning examples from simulation traces and emit readiness checklist"
    )
    parser.add_argument(
        "--inputs-root",
        type=str,
        default="outputs/model_evals",
        help="Directory to recursively scan for simulation run traces",
    )
    parser.add_argument(
        "--dataset-path",
        type=str,
        default="outputs/finetune/llm_actions_sft.jsonl",
        help="Output JSONL dataset path",
    )
    parser.add_argument(
        "--schema-path",
        type=str,
        default="outputs/finetune/llm_actions_schema.json",
        help="Output dataset schema path",
    )
    parser.add_argument(
        "--report-path",
        type=str,
        default="outputs/finetune/readiness_report.md",
        help="Output readiness markdown path",
    )
    parser.add_argument(
        "--high-threshold",
        type=float,
        default=0.72,
        help="Blended run score threshold for high-survivor label",
    )
    parser.add_argument(
        "--failure-alive-threshold",
        type=float,
        default=0.35,
        help="Alive-ratio threshold for failure label",
    )
    parser.add_argument(
        "--failure-days-threshold",
        type=float,
        default=0.65,
        help="Days-ratio threshold for failure label",
    )
    parser.add_argument(
        "--high-band-min-reward",
        type=float,
        default=-0.1,
        help="Ignore high-survivor action events below this reward",
    )
    parser.add_argument(
        "--failure-band-max-reward",
        type=float,
        default=0.6,
        help="Ignore failure-band action events above this reward",
    )
    parser.add_argument(
        "--max-examples-per-run",
        type=int,
        default=1000,
        help="Maximum examples emitted per run",
    )
    parser.add_argument(
        "--validation-ratio",
        type=float,
        default=0.1,
        help="Fraction of examples assigned to validation split",
    )
    parser.add_argument(
        "--min-total-examples",
        type=int,
        default=200,
        help="Readiness target for minimum total examples",
    )
    parser.add_argument(
        "--min-band-examples",
        type=int,
        default=50,
        help="Readiness target for high-survivor and failure examples each",
    )
    parser.add_argument(
        "--min-action-variety",
        type=int,
        default=5,
        help="Readiness target for distinct action count",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = _repo_root()

    inputs_root = Path(args.inputs_root)
    if not inputs_root.is_absolute():
        inputs_root = root / inputs_root

    dataset_path = Path(args.dataset_path)
    if not dataset_path.is_absolute():
        dataset_path = root / dataset_path

    schema_path = Path(args.schema_path)
    if not schema_path.is_absolute():
        schema_path = root / schema_path

    report_path = Path(args.report_path)
    if not report_path.is_absolute():
        report_path = root / report_path

    run_dirs = _iter_simulation_run_dirs(inputs_root)
    if not run_dirs:
        raise SystemExit(f"No simulation run traces found under: {inputs_root}")

    examples: List[Dict[str, object]] = []
    runs_by_band: Counter[str] = Counter()
    examples_by_band: Counter[str] = Counter()
    split_counts: Counter[str] = Counter()
    action_counts: Counter[str] = Counter()

    for run_dir in run_dirs:
        run_name = run_dir.name
        summary = _load_json_dict(run_dir / "summary.json") or {}

        band, alive_ratio, days_ratio = _classify_run(
            summary=summary,
            high_threshold=float(args.high_threshold),
            failure_alive_threshold=float(args.failure_alive_threshold),
            failure_days_threshold=float(args.failure_days_threshold),
        )

        if band == "neutral":
            continue

        runs_by_band[band] += 1
        emitted_for_run = 0

        events_path = run_dir / "events.jsonl"
        try:
            with events_path.open("r", encoding="utf-8") as fp:
                for line_no, line in enumerate(fp, start=1):
                    if emitted_for_run >= int(args.max_examples_per_run):
                        break

                    line = line.strip()
                    if not line:
                        continue

                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    if payload.get("type") != "action":
                        continue

                    action = payload.get("action")
                    if not isinstance(action, str) or action not in ALLOWED_ACTIONS:
                        continue

                    reward = _safe_float(payload.get("reward"))
                    if band == "high_survivor" and reward is not None and reward < float(args.high_band_min_reward):
                        continue
                    if band == "failure" and reward is not None and reward > float(args.failure_band_max_reward):
                        continue

                    state_payload = {
                        "day": _safe_int(payload.get("day")),
                        "health": _safe_float(payload.get("health")),
                        "days_without_water": _safe_int(payload.get("days_without_water")),
                        "days_without_food": _safe_int(payload.get("days_without_food")),
                        "water_store": _safe_int(payload.get("water_store")),
                        "food_store": _safe_int(payload.get("food_store")),
                    }

                    user_payload = {
                        "task": "choose_action",
                        "objective": "maximize long-term lineage survival under biological constraints",
                        "allowed_actions": ALLOWED_ACTIONS,
                        "state": state_payload,
                    }

                    assistant_payload = {
                        "action": action,
                        "confidence": _safe_float(payload.get("confidence")),
                        "reason": payload.get("reason"),
                        "invention_hypothesis": payload.get("invention_hypothesis"),
                    }

                    split = _build_split_key(
                        run_name=run_name,
                        line_number=line_no,
                        validation_ratio=float(args.validation_ratio),
                    )

                    example = {
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "You are a primitive survival planner. Return strict JSON with one allowed action."
                                ),
                            },
                            {
                                "role": "user",
                                "content": json.dumps(user_payload, ensure_ascii=True),
                            },
                            {
                                "role": "assistant",
                                "content": json.dumps(assistant_payload, ensure_ascii=True),
                            },
                        ],
                        "metadata": {
                            "run_name": run_name,
                            "quality_band": band,
                            "split": split,
                            "reward": reward,
                            "event_type": payload.get("event_type"),
                            "outcome": payload.get("outcome"),
                            "alive_ratio_ever": round(alive_ratio, 6),
                            "days_ratio": round(days_ratio, 6),
                        },
                    }

                    examples.append(example)
                    emitted_for_run += 1
                    examples_by_band[band] += 1
                    split_counts[split] += 1
                    action_counts[action] += 1
        except OSError:
            continue

    dataset_path.parent.mkdir(parents=True, exist_ok=True)
    with dataset_path.open("w", encoding="utf-8") as fp:
        for example in examples:
            fp.write(json.dumps(example, ensure_ascii=True) + "\n")

    schema_payload = {
        "dataset_name": "llm_actions_sft",
        "format": "jsonl",
        "record": {
            "messages": [
                {"role": "system", "content": "string"},
                {"role": "user", "content": "JSON string payload"},
                {"role": "assistant", "content": "JSON string decision payload"},
            ],
            "metadata": {
                "run_name": "string",
                "quality_band": "high_survivor|failure",
                "split": "train|validation",
                "reward": "number|null",
                "event_type": "string|null",
                "outcome": "string|null",
                "alive_ratio_ever": "number",
                "days_ratio": "number",
            },
        },
        "generated_at_utc": _utc_now(),
    }
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path.write_text(json.dumps(schema_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    total_examples = len(examples)
    high_examples = int(examples_by_band.get("high_survivor", 0))
    failure_examples = int(examples_by_band.get("failure", 0))
    action_variety = len(action_counts)

    checks: List[Tuple[str, bool]] = [
        (
            f"Total examples >= {int(args.min_total_examples)}",
            total_examples >= int(args.min_total_examples),
        ),
        (
            f"High-survivor examples >= {int(args.min_band_examples)}",
            high_examples >= int(args.min_band_examples),
        ),
        (
            f"Failure examples >= {int(args.min_band_examples)}",
            failure_examples >= int(args.min_band_examples),
        ),
        (
            f"Action variety >= {int(args.min_action_variety)}",
            action_variety >= int(args.min_action_variety),
        ),
        ("Validation split has at least one example", int(split_counts.get("validation", 0)) > 0),
    ]
    ready = all(result for _, result in checks)

    lines: List[str] = []
    lines.append("# Fine-Tune Readiness Report")
    lines.append("")
    lines.append(f"Generated: {_utc_now()}")
    lines.append("")
    lines.append(f"Dataset path: {dataset_path}")
    lines.append(f"Schema path: {schema_path}")
    lines.append(f"Inputs scanned: {inputs_root}")
    lines.append("")
    lines.append("## Dataset Totals")
    lines.append("")
    lines.append(f"- Total examples: {total_examples}")
    lines.append(f"- High-survivor examples: {high_examples}")
    lines.append(f"- Failure examples: {failure_examples}")
    lines.append(f"- Train examples: {int(split_counts.get('train', 0))}")
    lines.append(f"- Validation examples: {int(split_counts.get('validation', 0))}")
    lines.append(f"- Action variety: {action_variety}")
    lines.append("")
    lines.append("## Run Coverage")
    lines.append("")
    lines.append(f"- High-survivor runs: {int(runs_by_band.get('high_survivor', 0))}")
    lines.append(f"- Failure runs: {int(runs_by_band.get('failure', 0))}")
    lines.append("")
    lines.append("## Top Actions")
    lines.append("")
    for action, count in action_counts.most_common(8):
        lines.append(f"- {action}: {count}")
    if not action_counts:
        lines.append("- none")

    lines.append("")
    lines.append("## Checklist")
    lines.append("")
    for label, result in checks:
        mark = "PASS" if result else "FAIL"
        lines.append(f"- [{mark}] {label}")

    lines.append("")
    lines.append(f"Overall readiness: {'READY' if ready else 'NOT READY'}")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote dataset: {dataset_path}")
    print(f"Wrote schema: {schema_path}")
    print(f"Wrote readiness report: {report_path}")
    print(f"Readiness: {'READY' if ready else 'NOT READY'}")


if __name__ == "__main__":
    main()
