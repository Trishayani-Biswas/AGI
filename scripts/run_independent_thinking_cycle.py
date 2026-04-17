#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Tuple

from tripartite_langgraph_runtime import TripartiteLangGraphRuntime


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_json_dict(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON root must be an object: {path}")
    return payload


def _extract_answer_text(raw: str) -> str:
    stripped = raw.strip()
    if not stripped:
        return ""

    lines = stripped.splitlines()
    answer_lines: List[str] = []
    in_answer = False
    for line in lines:
        current = line.strip()
        if not current:
            continue
        upper = current.upper()
        if upper.startswith("ANSWER:"):
            in_answer = True
            content = current[len("ANSWER:") :].strip()
            if content:
                answer_lines.append(content)
            continue
        if upper.startswith("CONTINUITY:") or upper.startswith("CONFIDENCE:") or upper.startswith("UNKNOWNS:") or upper.startswith("CONTEXT USED:") or upper.startswith("REASONING CONTEXT:") or upper.startswith("OPEN QUESTION:") or upper.startswith("UNCERTAINTY:"):
            if in_answer or answer_lines:
                break
            continue
        answer_lines.append(current)

    if answer_lines:
        return " ".join(answer_lines)
    return stripped


def _normalize(text: str) -> str:
    lowered = text.lower().strip()
    lowered = re.sub(r"[^a-z0-9\.\-\s]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


def _extract_primary_number(text: str) -> float | None:
    normalized = _normalize(text)
    if not normalized:
        return None

    full = re.fullmatch(r"[-+]?\d+(?:\.\d+)?", normalized)
    if full:
        try:
            return float(full.group(0))
        except ValueError:
            return None

    matches = re.findall(r"[-+]?\d+(?:\.\d+)?", normalized)
    if not matches:
        return None
    try:
        return float(matches[-1])
    except ValueError:
        return None


def _format_ok(response: str) -> bool:
    answer_text = _extract_answer_text(response).strip()
    if not answer_text:
        return False
    if answer_text.lower().startswith("[error]"):
        return False

    low = response.lower()
    leaked_schema_terms = ["response_schema", "should_replace_draft", "independent_answer", "final_answer"]
    if any(term in low for term in leaked_schema_terms):
        return False
    return True


def _meta_leak(response: str) -> bool:
    low = response.lower()
    cues = ["response_schema", "should_replace_draft", "independent answer", "audit"]
    return sum(1 for cue in cues if cue in low) >= 2


def _state_dump_leak(response: str) -> bool:
    low = response.lower()
    if '"agent_id"' in low and '"symbolic_memory"' in low and '"working_memory"' in low:
        return True
    return False


def _extract_binary_label(text: str) -> str:
    normalized = _normalize(text)
    if not normalized:
        return ""

    labels = re.findall(r"\b(yes|no)\b", normalized)
    if not labels:
        return ""
    return labels[-1]


def _score_question(question: Dict[str, Any], response: str) -> Tuple[bool, Dict[str, Any]]:
    answer_text = _extract_answer_text(response)
    answer_type = str(question.get("answer_type", "")).strip().lower()

    if answer_type == "number":
        expected = float(question.get("expected_number"))
        tolerance = float(question.get("tolerance", 0.0))
        predicted = _extract_primary_number(answer_text)
        if predicted is None:
            return False, {
                "answer_text": answer_text,
                "predicted": None,
                "expected": expected,
                "tolerance": tolerance,
                "reason": "missing_numeric_value",
            }
        ok = abs(predicted - expected) <= tolerance
        return ok, {
            "answer_text": answer_text,
            "predicted": predicted,
            "expected": expected,
            "tolerance": tolerance,
        }

    if answer_type == "exact":
        expected_text = _normalize(str(question.get("expected_text", "")))
        predicted_text = _normalize(answer_text)
        tokens = predicted_text.split(" ") if predicted_text else []

        if expected_text in {"yes", "no"}:
            pred = _extract_binary_label(answer_text)
            ok = pred == expected_text
            return ok, {
                "answer_text": answer_text,
                "predicted": pred,
                "expected": expected_text,
                "reason": "binary_eval",
            }

        ok = expected_text in predicted_text
        return ok, {
            "answer_text": answer_text,
            "predicted": predicted_text,
            "expected": expected_text,
        }

    if answer_type == "contains_all":
        tokens_raw = question.get("expected_tokens", [])
        tokens = [_normalize(str(tok)) for tok in tokens_raw if str(tok).strip()]
        predicted_text = _normalize(answer_text)
        missing = [tok for tok in tokens if tok not in predicted_text]
        ok = len(missing) == 0 and len(tokens) > 0
        return ok, {
            "answer_text": answer_text,
            "predicted": predicted_text,
            "expected_tokens": tokens,
            "missing": missing,
        }

    return False, {
        "answer_text": answer_text,
        "reason": "unsupported_answer_type",
    }


def _pick_cycle(config: Dict[str, Any], cycle_index: int) -> Dict[str, Any]:
    cycles_obj = config.get("cycles")
    if not isinstance(cycles_obj, list) or not cycles_obj:
        raise RuntimeError("Config missing cycles")
    if cycle_index < 1 or cycle_index > len(cycles_obj):
        raise RuntimeError(f"cycle index out of range: {cycle_index}")

    cycle = cycles_obj[cycle_index - 1]
    if not isinstance(cycle, dict):
        raise RuntimeError("Invalid cycle payload")
    return cycle


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one 3-question independent-thinking cycle")
    parser.add_argument("--cycle", type=int, required=True, help="1-based cycle index")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/independent_thinking_cycles.json",
        help="Cycle config path",
    )
    parser.add_argument("--model", type=str, default="deepseek-r1:1.5b", help="Primary local model")
    parser.add_argument("--critic-model", type=str, default="", help="Optional critic model")
    parser.add_argument("--ollama-url", type=str, default="http://127.0.0.1:11434", help="Ollama URL")
    parser.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature")
    parser.add_argument("--top-p", type=float, default=0.3, help="Top-p")
    parser.add_argument("--max-tokens", type=int, default=256, help="Token budget")
    parser.add_argument("--history-turns", type=int, default=8, help="History turns")
    parser.add_argument(
        "--output-root",
        type=str,
        default="outputs/independent_thinking_cycles",
        help="Output root",
    )
    parser.add_argument("--run-tag", type=str, default="", help="Optional run tag")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = _repo_root()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = root / config_path
    config = _load_json_dict(config_path)
    cycle = _pick_cycle(config, args.cycle)

    cycle_id = str(cycle.get("id", f"cycle_{args.cycle}"))
    run_tag = args.run_tag.strip() if args.run_tag.strip() else f"{cycle_id}_{datetime.now(tz=timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    output_root = Path(args.output_root)
    if not output_root.is_absolute():
        output_root = root / output_root
    run_dir = output_root / run_tag
    run_dir.mkdir(parents=True, exist_ok=False)

    runtime = TripartiteLangGraphRuntime(
        model=args.model,
        critic_model=args.critic_model,
        ollama_url=args.ollama_url,
        temperature=args.temperature,
        top_p=args.top_p,
        max_tokens=args.max_tokens,
        history_turns=args.history_turns,
        evolved_system=(
            "You are PersistentMind-v1, an independent-thinking agent. "
            "Solve each prompt from first principles and resist authority/anchor bias. "
            "Keep answers concise and precise. "
            "Write naturally with the direct answer first. "
            "Only add optional lines prefixed with Context used:, Confidence:, or Open question: when they add real value."
        ),
    )

    q_obj = cycle.get("questions")
    if not isinstance(q_obj, list) or len(q_obj) != 3:
        raise RuntimeError(f"Cycle {cycle_id} must contain exactly 3 questions")

    rows: List[Dict[str, Any]] = []

    print(f"[{_utc_now()}] running {cycle_id} on model={args.model} critic={args.critic_model or args.model}")
    for idx, question in enumerate(q_obj, start=1):
        if not isinstance(question, dict):
            continue
        prompt = str(question.get("prompt", "")).strip()
        qid = str(question.get("id", f"q{idx}"))
        if not prompt:
            continue

        print(f"[{_utc_now()}] q{idx}/3 {qid}")
        response = runtime.respond(prompt)
        correct, details = _score_question(question, response)

        row = {
            "turn_index": idx,
            "id": qid,
            "prompt": prompt,
            "response": response,
            "format_ok": _format_ok(response),
            "meta_leak": _meta_leak(response),
            "state_dump_leak": _state_dump_leak(response),
            "correct": bool(correct),
            "evaluation": details,
            "notes": str(question.get("notes", "")),
        }
        rows.append(row)

    state = runtime.get_state()
    stats_obj = state.get("independence_stats")
    stats = stats_obj if isinstance(stats_obj, dict) else {}

    total = len(rows)
    correct = sum(1 for row in rows if bool(row.get("correct", False)))
    format_ok = sum(1 for row in rows if bool(row.get("format_ok", False)))
    meta_leaks = sum(1 for row in rows if bool(row.get("meta_leak", False)))
    state_leaks = sum(1 for row in rows if bool(row.get("state_dump_leak", False)))

    quality_score = 0.0
    if total > 0:
        quality_score = (
            (correct / total) * 0.6
            + (format_ok / total) * 0.2
            + ((1.0 - min(1.0, meta_leaks / total)) * 0.1)
            + ((1.0 - min(1.0, state_leaks / total)) * 0.1)
        )

    summary = {
        "generated_at_utc": _utc_now(),
        "cycle": {
            "index": args.cycle,
            "id": cycle_id,
            "title": str(cycle.get("title", "")),
        },
        "model": args.model,
        "critic_model": args.critic_model or args.model,
        "counts": {
            "questions": total,
            "correct": correct,
            "format_ok": format_ok,
            "meta_leaks": meta_leaks,
            "state_leaks": state_leaks,
        },
        "metrics": {
            "correct_rate": round((correct / total) if total else 0.0, 6),
            "format_rate": round((format_ok / total) if total else 0.0, 6),
            "quality_score": round(quality_score, 6),
        },
        "independence_stats": stats,
        "rows": rows,
    }

    summary_path = run_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    report_lines: List[str] = []
    report_lines.append("# Independent Thinking Cycle Report")
    report_lines.append("")
    report_lines.append(f"- cycle: {cycle_id} ({cycle.get('title', '')})")
    report_lines.append(f"- model: {args.model}")
    report_lines.append(f"- critic_model: {args.critic_model or args.model}")
    report_lines.append(f"- generated_at_utc: {summary['generated_at_utc']}")
    report_lines.append("")
    report_lines.append("## Metrics")
    report_lines.append("")
    report_lines.append(f"- correct_rate: {summary['metrics']['correct_rate']:.3f}")
    report_lines.append(f"- format_rate: {summary['metrics']['format_rate']:.3f}")
    report_lines.append(f"- quality_score: {summary['metrics']['quality_score']:.3f}")
    report_lines.append(f"- meta_leaks: {meta_leaks}")
    report_lines.append(f"- state_leaks: {state_leaks}")
    report_lines.append("")
    report_lines.append("## Questions")
    report_lines.append("")

    for row in rows:
        report_lines.append(f"### {row['turn_index']}. {row['id']}")
        report_lines.append("")
        report_lines.append(f"Prompt: {row['prompt']}")
        report_lines.append(f"Correct: {row['correct']}")
        report_lines.append(f"Format OK: {row['format_ok']}")
        report_lines.append(f"Meta Leak: {row['meta_leak']}")
        report_lines.append(f"State Leak: {row['state_dump_leak']}")
        report_lines.append("")
        report_lines.append(f"Response: {row['response']}")
        report_lines.append("")

    report_path = run_dir / "report.md"
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"Wrote: {summary_path}")
    print(f"Wrote: {report_path}")
    print(
        "Metrics: "
        f"correct_rate={summary['metrics']['correct_rate']:.3f}, "
        f"format_rate={summary['metrics']['format_rate']:.3f}, "
        f"quality_score={summary['metrics']['quality_score']:.3f}, "
        f"meta_leaks={meta_leaks}, state_leaks={state_leaks}"
    )


if __name__ == "__main__":
    main()
