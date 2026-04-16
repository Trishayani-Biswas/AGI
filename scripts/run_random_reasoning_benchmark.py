from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import re
import statistics
import sys
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agi_sim.config import SimulationConfig


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _utc_compact() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")


def _safe_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _load_json_dict(path: Path) -> Dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _extract_json(text: str) -> Dict[str, object] | None:
    stripped = text.strip()
    if not stripped:
        return None

    try:
        payload = json.loads(stripped)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", stripped)
    if not match:
        return None

    try:
        payload = json.loads(match.group(0))
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        return None

    return None


def _call_model(
    *,
    model: str,
    ollama_url: str,
    timeout_s: float,
    prompt: str,
) -> Dict[str, object]:
    system_prompt = (
        "You are a careful reasoner. Solve the task and return strict JSON only. "
        "Use this schema exactly: "
        "{\"final_answer\":\"string\",\"confidence\":number between 0 and 1,\"brief_rationale\":\"short string\"}."
    )

    user_payload = {
        "task": "answer_question",
        "question": prompt,
        "instructions": [
            "Solve carefully and avoid relying on superficial phrase matching.",
            "Return only strict JSON.",
        ],
    }

    payload = {
        "model": model,
        "stream": False,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": json.dumps(user_payload, ensure_ascii=True),
            },
        ],
        "options": {
            "temperature": 0.2,
            "top_p": 0.9,
        },
    }

    def _post_json(url: str, body_payload: Dict[str, object]) -> Dict[str, object]:
        req = request.Request(
            url=url,
            data=json.dumps(body_payload, ensure_ascii=True).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with request.urlopen(req, timeout=timeout_s) as resp:
            raw = resp.read().decode("utf-8")
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}

    chat_url = f"{ollama_url.rstrip('/')}/api/chat"
    generate_url = f"{ollama_url.rstrip('/')}/api/generate"

    try:
        parsed = _post_json(chat_url, payload)
        content = str(parsed.get("message", {}).get("content", ""))
    except error.HTTPError as exc:
        if exc.code != 404:
            raise

        generate_prompt = "\n".join(
            [
                system_prompt,
                "",
                "USER_PAYLOAD_JSON:",
                json.dumps(user_payload, ensure_ascii=True),
                "",
                "Return strict JSON only with keys final_answer, confidence, brief_rationale.",
            ]
        )
        generate_payload: Dict[str, object] = {
            "model": model,
            "prompt": generate_prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "top_p": 0.9,
            },
        }
        parsed = _post_json(generate_url, generate_payload)
        content = str(parsed.get("response", ""))

    extracted = _extract_json(content)
    if extracted is None:
        return {
            "final_answer": content.strip(),
            "confidence": 0.0,
            "brief_rationale": "json_parse_failed",
        }
    return extracted


def _normalize_text(text: str) -> str:
    lowered = text.strip().lower()
    lowered = re.sub(r"[^a-z0-9\.\-\s]", "", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


def _extract_primary_number(text: str) -> float | None:
    stripped = text.strip()
    full = re.fullmatch(r"[-+]?\d+(?:\.\d+)?", stripped)
    if full:
        try:
            return float(full.group(0))
        except ValueError:
            return None

    matches = re.findall(r"[-+]?\d+(?:\.\d+)?", stripped)
    if not matches:
        return None

    # Prefer the final numeric value since many responses include setup numbers first.
    try:
        return float(matches[-1])
    except ValueError:
        return None


def _score_answer(question: Dict[str, object], final_answer: str) -> Tuple[bool, Dict[str, object]]:
    answer_type = str(question.get("answer_type", "")).strip()

    if answer_type == "number":
        expected = _safe_float(question.get("expected_number"))
        tolerance = _safe_float(question.get("tolerance")) or 0.0
        predicted = _extract_primary_number(final_answer)
        if expected is None or predicted is None:
            return False, {
                "answer_type": answer_type,
                "expected": expected,
                "predicted": predicted,
                "reason": "missing_numeric_value",
            }
        ok = abs(predicted - expected) <= tolerance
        return ok, {
            "answer_type": answer_type,
            "expected": expected,
            "predicted": predicted,
            "tolerance": tolerance,
        }

    if answer_type == "exact":
        expected_text = _normalize_text(str(question.get("expected_text", "")))
        predicted_text = _normalize_text(final_answer)
        predicted_primary = predicted_text.split(" ")[0] if predicted_text else ""
        ok = predicted_text == expected_text or predicted_primary == expected_text
        return ok, {
            "answer_type": answer_type,
            "expected": expected_text,
            "predicted": predicted_text,
            "predicted_primary": predicted_primary,
        }

    if answer_type == "contains_all":
        expected_tokens_raw = question.get("expected_tokens")
        if not isinstance(expected_tokens_raw, list):
            expected_tokens_raw = []

        expected_tokens = [_normalize_text(str(token)) for token in expected_tokens_raw if str(token).strip()]
        predicted_text = _normalize_text(final_answer)
        missing = [token for token in expected_tokens if token not in predicted_text]
        ok = len(missing) == 0 and len(expected_tokens) > 0
        return ok, {
            "answer_type": answer_type,
            "expected_tokens": expected_tokens,
            "predicted": predicted_text,
            "missing_tokens": missing,
        }

    return False, {
        "answer_type": answer_type,
        "reason": "unsupported_answer_type",
    }


def _answers_consistent(question: Dict[str, object], left: str, right: str) -> bool:
    answer_type = str(question.get("answer_type", "")).strip()

    if answer_type == "number":
        tolerance = _safe_float(question.get("tolerance")) or 0.0
        lval = _extract_primary_number(left)
        rval = _extract_primary_number(right)
        if lval is None or rval is None:
            return False
        return abs(lval - rval) <= tolerance

    if answer_type in {"exact", "contains_all"}:
        return _normalize_text(left) == _normalize_text(right)

    return False


def _mean(values: Iterable[float]) -> float:
    prepared = list(values)
    if not prepared:
        return 0.0
    return float(statistics.mean(prepared))


def _build_report(payload: Dict[str, object]) -> str:
    aggregate = payload.get("aggregate")
    if not isinstance(aggregate, dict):
        aggregate = {}

    rows = payload.get("results")
    if not isinstance(rows, list):
        rows = []

    lines: List[str] = []
    lines.append("# Random Reasoning Benchmark")
    lines.append("")
    lines.append(f"- generated_at_utc: {payload.get('generated_at_utc', '')}")
    lines.append(f"- model: {payload.get('model', '')}")
    lines.append(f"- questions_evaluated: {aggregate.get('questions_evaluated', 0)}")
    lines.append("")

    lines.append("## Aggregate")
    lines.append("")
    lines.append(f"- base_requests_success_rate: {float(aggregate.get('base_requests_success_rate', 0.0)):.3f}")
    lines.append(f"- paraphrase_requests_success_rate: {float(aggregate.get('paraphrase_requests_success_rate', 0.0)):.3f}")
    lines.append(f"- paired_success_rate: {float(aggregate.get('paired_success_rate', 0.0)):.3f}")
    lines.append(f"- api_error_count: {int(aggregate.get('api_error_count', 0))}")
    lines.append(f"- base_accuracy_scored: {float(aggregate.get('base_accuracy_scored', 0.0)):.3f}")
    lines.append(f"- paraphrase_accuracy_scored: {float(aggregate.get('paraphrase_accuracy_scored', 0.0)):.3f}")
    lines.append(f"- repair_accuracy_scored: {float(aggregate.get('repair_accuracy_scored', 0.0)):.3f}")
    lines.append(f"- repair_gain_vs_best_of_two: {float(aggregate.get('repair_gain_vs_best_of_two', 0.0)):+.3f}")
    lines.append(f"- consistency_rate_scored: {float(aggregate.get('consistency_rate_scored', 0.0)):.3f}")
    lines.append(f"- mean_confidence: {float(aggregate.get('mean_confidence', 0.0)):.3f}")
    lines.append(f"- mean_confidence_when_correct: {float(aggregate.get('mean_confidence_when_correct', 0.0)):.3f}")
    lines.append(f"- mean_confidence_when_wrong: {float(aggregate.get('mean_confidence_when_wrong', 0.0)):.3f}")
    pattern_risk = aggregate.get("pattern_risk_index")
    if isinstance(pattern_risk, (int, float)):
        lines.append(f"- pattern_risk_index: {float(pattern_risk):.3f}")
    else:
        lines.append("- pattern_risk_index: n/a (insufficient successful responses)")
    lines.append("")

    lines.append("## Per Question")
    lines.append("")
    lines.append("| id | category | base_request_ok | paraphrase_request_ok | repair_request_ok | base_correct | paraphrase_correct | repair_correct | consistent |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in rows:
        if not isinstance(row, dict):
            continue
        lines.append(
            f"| {row.get('id', '')} | {row.get('category', '')} | {row.get('base_request_ok')} | {row.get('paraphrase_request_ok')} | {row.get('repair_request_ok')} | {row.get('base_correct')} | {row.get('paraphrase_correct')} | {row.get('repair_correct')} | {row.get('consistent')} |"
        )

    lines.append("")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    cfg = SimulationConfig.from_env()

    parser = argparse.ArgumentParser(description="Run deterministic random-question reasoning benchmark")
    parser.add_argument(
        "--benchmark-file",
        type=str,
        default="configs/random_reasoning_benchmark.json",
        help="Path to benchmark JSON file",
    )
    parser.add_argument("--model", type=str, default=cfg.proposer_model, help="Model id served by Ollama")
    parser.add_argument("--ollama-url", type=str, default=cfg.ollama_url, help="Ollama base URL")
    parser.add_argument("--timeout-s", type=float, default=cfg.llm_timeout_s, help="HTTP timeout per request")
    parser.add_argument("--seed", type=int, default=42, help="Seed for question ordering")
    parser.add_argument("--max-questions", type=int, default=0, help="Optional cap on number of questions")
    parser.add_argument(
        "--output-root",
        type=str,
        default="outputs/random_reasoning_benchmark",
        help="Output root directory",
    )
    parser.add_argument("--run-tag", type=str, default="", help="Optional run tag")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip model calls and emit placeholder rows for pipeline validation",
    )
    parser.add_argument(
        "--disable-repair-pass",
        action="store_true",
        help="Disable reflection repair pass that reconciles base and paraphrase answers",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    benchmark_path = Path(args.benchmark_file)
    if not benchmark_path.is_absolute():
        benchmark_path = ROOT / benchmark_path

    payload = _load_json_dict(benchmark_path)
    questions_raw = payload.get("questions")
    if not isinstance(questions_raw, list) or not questions_raw:
        raise RuntimeError(f"No questions found in benchmark file: {benchmark_path}")

    questions: List[Dict[str, object]] = [
        row for row in questions_raw if isinstance(row, dict) and str(row.get("id", "")).strip()
    ]
    if not questions:
        raise RuntimeError(f"No valid questions found in benchmark file: {benchmark_path}")

    rng = random.Random(args.seed)
    rng.shuffle(questions)

    if args.max_questions > 0:
        questions = questions[: int(args.max_questions)]

    run_tag = args.run_tag.strip() if args.run_tag else f"benchmark_{_utc_compact()}"

    output_root = Path(args.output_root)
    if not output_root.is_absolute():
        output_root = ROOT / output_root

    run_dir = output_root / run_tag
    run_dir.mkdir(parents=True, exist_ok=True)

    print(f"[{_utc_now()}] model={args.model} questions={len(questions)} dry_run={args.dry_run}")

    results: List[Dict[str, object]] = []
    base_scores: List[float] = []
    paraphrase_scores: List[float] = []
    repair_scores: List[float] = []
    repair_gain_values: List[float] = []
    consistency_scores: List[float] = []
    base_request_ok_values: List[float] = []
    paraphrase_request_ok_values: List[float] = []
    repair_request_ok_values: List[float] = []
    paired_request_ok_values: List[float] = []
    confidence_all: List[float] = []
    confidence_correct: List[float] = []
    confidence_wrong: List[float] = []
    api_error_count = 0
    repair_enabled = not args.disable_repair_pass

    for idx, question in enumerate(questions, start=1):
        qid = str(question.get("id", ""))
        category = str(question.get("category", ""))
        prompt = str(question.get("prompt", "")).strip()
        paraphrase = str(question.get("paraphrase", "")).strip() or prompt

        print(f"[{_utc_now()}] ({idx}/{len(questions)}) id={qid}")

        if args.dry_run:
            base_resp = {
                "final_answer": "dry_run",
                "confidence": 0.0,
                "brief_rationale": "dry_run",
                "request_ok": True,
            }
            para_resp = {
                "final_answer": "dry_run",
                "confidence": 0.0,
                "brief_rationale": "dry_run",
                "request_ok": True,
            }
            repair_resp = {
                "final_answer": "dry_run",
                "confidence": 0.0,
                "brief_rationale": "dry_run",
                "request_ok": True,
            }
        else:
            try:
                base_resp = _call_model(
                    model=args.model,
                    ollama_url=args.ollama_url,
                    timeout_s=args.timeout_s,
                    prompt=prompt,
                )
                base_resp["request_ok"] = True
            except error.HTTPError as exc:
                message = f"http_{exc.code}"
                base_resp = {
                    "final_answer": "",
                    "confidence": 0.0,
                    "brief_rationale": f"api_error:HTTPError:{message}",
                    "request_ok": False,
                }
                api_error_count += 1
            except (error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
                base_resp = {
                    "final_answer": "",
                    "confidence": 0.0,
                    "brief_rationale": f"api_error:{type(exc).__name__}",
                    "request_ok": False,
                }
                api_error_count += 1

            try:
                para_resp = _call_model(
                    model=args.model,
                    ollama_url=args.ollama_url,
                    timeout_s=args.timeout_s,
                    prompt=paraphrase,
                )
                para_resp["request_ok"] = True
            except error.HTTPError as exc:
                message = f"http_{exc.code}"
                para_resp = {
                    "final_answer": "",
                    "confidence": 0.0,
                    "brief_rationale": f"api_error:HTTPError:{message}",
                    "request_ok": False,
                }
                api_error_count += 1
            except (error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
                para_resp = {
                    "final_answer": "",
                    "confidence": 0.0,
                    "brief_rationale": f"api_error:{type(exc).__name__}",
                    "request_ok": False,
                }
                api_error_count += 1

            if repair_enabled and bool(base_resp.get("request_ok", False)) and bool(para_resp.get("request_ok", False)):
                repair_prompt = "\n".join(
                    [
                        "Reconcile two candidate answers and produce a corrected final answer.",
                        f"Original question: {prompt}",
                        f"Paraphrase question: {paraphrase}",
                        f"Candidate answer A: {str(base_resp.get('final_answer', ''))}",
                        f"Candidate answer B: {str(para_resp.get('final_answer', ''))}",
                        "Return strict JSON with final_answer, confidence, brief_rationale.",
                    ]
                )
                try:
                    repair_resp = _call_model(
                        model=args.model,
                        ollama_url=args.ollama_url,
                        timeout_s=args.timeout_s,
                        prompt=repair_prompt,
                    )
                    repair_resp["request_ok"] = True
                except error.HTTPError as exc:
                    message = f"http_{exc.code}"
                    repair_resp = {
                        "final_answer": "",
                        "confidence": 0.0,
                        "brief_rationale": f"api_error:HTTPError:{message}",
                        "request_ok": False,
                    }
                    api_error_count += 1
                except (error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
                    repair_resp = {
                        "final_answer": "",
                        "confidence": 0.0,
                        "brief_rationale": f"api_error:{type(exc).__name__}",
                        "request_ok": False,
                    }
                    api_error_count += 1
            else:
                repair_resp = {
                    "final_answer": "",
                    "confidence": 0.0,
                    "brief_rationale": "repair_skipped",
                    "request_ok": False,
                }

        base_answer = str(base_resp.get("final_answer", ""))
        para_answer = str(para_resp.get("final_answer", ""))
        repair_answer = str(repair_resp.get("final_answer", ""))
        base_request_ok = bool(base_resp.get("request_ok", False))
        para_request_ok = bool(para_resp.get("request_ok", False))
        repair_request_ok = bool(repair_resp.get("request_ok", False))
        pair_request_ok = base_request_ok and para_request_ok

        base_request_ok_values.append(1.0 if base_request_ok else 0.0)
        paraphrase_request_ok_values.append(1.0 if para_request_ok else 0.0)
        repair_request_ok_values.append(1.0 if repair_request_ok else 0.0)
        paired_request_ok_values.append(1.0 if pair_request_ok else 0.0)

        if base_request_ok:
            base_ok, base_details = _score_answer(question, base_answer)
        else:
            base_ok = False
            base_details = {
                "reason": "request_failed",
            }

        if para_request_ok:
            para_ok, para_details = _score_answer(question, para_answer)
        else:
            para_ok = False
            para_details = {
                "reason": "request_failed",
            }

        consistent = _answers_consistent(question, base_answer, para_answer) if pair_request_ok else False

        base_conf = _safe_float(base_resp.get("confidence"))
        para_conf = _safe_float(para_resp.get("confidence"))
        if base_conf is None:
            base_conf = 0.0
        if para_conf is None:
            para_conf = 0.0

        for request_ok, conf, ok in [
            (base_request_ok, base_conf, base_ok),
            (para_request_ok, para_conf, para_ok),
        ]:
            if not request_ok:
                continue
            confidence_all.append(conf)
            if ok:
                confidence_correct.append(conf)
            else:
                confidence_wrong.append(conf)

        if base_request_ok:
            base_scores.append(1.0 if base_ok else 0.0)
        if para_request_ok:
            paraphrase_scores.append(1.0 if para_ok else 0.0)
        if pair_request_ok:
            consistency_scores.append(1.0 if consistent else 0.0)

        if repair_request_ok:
            repair_ok, repair_details = _score_answer(question, repair_answer)
            repair_scores.append(1.0 if repair_ok else 0.0)

            best_of_two = 1.0 if (base_ok or para_ok) else 0.0
            repair_gain_values.append((1.0 if repair_ok else 0.0) - best_of_two)
        else:
            repair_ok = False
            repair_details = {
                "reason": "repair_not_available",
            }

        results.append(
            {
                "id": qid,
                "category": category,
                "base_request_ok": base_request_ok,
                "paraphrase_request_ok": para_request_ok,
                "repair_request_ok": repair_request_ok,
                "base_correct": base_ok,
                "paraphrase_correct": para_ok,
                "repair_correct": repair_ok,
                "consistent": consistent,
                "base_response": {
                    "final_answer": base_answer,
                    "confidence": round(base_conf, 6),
                    "brief_rationale": str(base_resp.get("brief_rationale", "")),
                    "scoring": base_details,
                },
                "paraphrase_response": {
                    "final_answer": para_answer,
                    "confidence": round(para_conf, 6),
                    "brief_rationale": str(para_resp.get("brief_rationale", "")),
                    "scoring": para_details,
                },
                "repair_response": {
                    "final_answer": repair_answer,
                    "confidence": round(_safe_float(repair_resp.get("confidence")) or 0.0, 6),
                    "brief_rationale": str(repair_resp.get("brief_rationale", "")),
                    "scoring": repair_details,
                },
            }
        )

    base_acc = _mean(base_scores)
    para_acc = _mean(paraphrase_scores)
    consistency = _mean(consistency_scores)

    # Higher means more likely template-like/fragile behavior under this benchmark.
    repair_acc = _mean(repair_scores)

    if base_scores and paraphrase_scores and consistency_scores and repair_scores:
        pattern_risk_index: float | None = (
            ((1.0 - base_acc) * 0.35)
            + ((1.0 - para_acc) * 0.25)
            + ((1.0 - consistency) * 0.2)
            + ((1.0 - repair_acc) * 0.2)
        )
    else:
        pattern_risk_index = None

    aggregate = {
        "questions_evaluated": len(results),
        "base_requests_success_rate": round(_mean(base_request_ok_values), 6),
        "paraphrase_requests_success_rate": round(_mean(paraphrase_request_ok_values), 6),
        "repair_requests_success_rate": round(_mean(repair_request_ok_values), 6),
        "paired_success_rate": round(_mean(paired_request_ok_values), 6),
        "api_error_count": int(api_error_count),
        "base_scored_count": len(base_scores),
        "paraphrase_scored_count": len(paraphrase_scores),
        "repair_scored_count": len(repair_scores),
        "consistency_scored_count": len(consistency_scores),
        "base_accuracy_scored": round(base_acc, 6),
        "paraphrase_accuracy_scored": round(para_acc, 6),
        "repair_accuracy_scored": round(repair_acc, 6),
        "repair_gain_vs_best_of_two": round(_mean(repair_gain_values), 6),
        "consistency_rate_scored": round(consistency, 6),
        "mean_confidence": round(_mean(confidence_all), 6),
        "mean_confidence_when_correct": round(_mean(confidence_correct), 6),
        "mean_confidence_when_wrong": round(_mean(confidence_wrong), 6),
        "pattern_risk_index": round(pattern_risk_index, 6) if pattern_risk_index is not None else None,
    }

    out_payload = {
        "generated_at_utc": _utc_now(),
        "run_tag": run_tag,
        "benchmark_file": str(benchmark_path),
        "benchmark_version": str(payload.get("version", "")),
        "model": args.model,
        "ollama_url": args.ollama_url,
        "seed": args.seed,
        "max_questions": args.max_questions,
        "dry_run": bool(args.dry_run),
        "repair_enabled": bool(repair_enabled),
        "aggregate": aggregate,
        "results": results,
    }

    json_path = run_dir / "summary.json"
    json_path.write_text(json.dumps(out_payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    report = _build_report(out_payload)
    report_path = run_dir / "report.md"
    report_path.write_text(report, encoding="utf-8")

    print(f"[{_utc_now()}] report={report_path}")
    print(
        "aggregate: "
        f"base_req_ok={aggregate['base_requests_success_rate']:.3f} "
        f"para_req_ok={aggregate['paraphrase_requests_success_rate']:.3f} "
        f"repair_req_ok={aggregate['repair_requests_success_rate']:.3f} "
        f"base_acc={aggregate['base_accuracy_scored']:.3f} "
        f"para_acc={aggregate['paraphrase_accuracy_scored']:.3f} "
        f"repair_acc={aggregate['repair_accuracy_scored']:.3f} "
        f"consistency={aggregate['consistency_rate_scored']:.3f} "
        f"pattern_risk={'n/a' if aggregate['pattern_risk_index'] is None else f'{aggregate['pattern_risk_index']:.3f}'}"
    )


if __name__ == "__main__":
    main()
