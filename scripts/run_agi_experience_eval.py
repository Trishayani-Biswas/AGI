#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib import error, request

from tripartite_langgraph_runtime import TripartiteLangGraphRuntime


BASELINE_SYSTEM = "You are a standard assistant. Give direct concise answers."

EVOLVED_SYSTEM = (
    "You are PersistentMind-v1, an evolving continuity-aware agent. "
    "Preserve session continuity, track uncertainty, and avoid generic boilerplate. "
    "When prior turns exist, continuity must cite at least one concrete detail from earlier turns. "
    "When asked to critique or update, do not repeat the previous answer verbatim; produce a revised answer. "
    "Always answer using this exact structure:\n"
    "ANSWER: <direct answer>\n"
    "CONTINUITY: <what from prior turns influenced this answer>\n"
    "CONFIDENCE: <0.00 to 1.00>\n"
    "UNKNOWNS: <what remains uncertain>"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run AGI experience evaluation comparing baseline and evolved conversational behavior."
    )
    parser.add_argument("--model", default=os.getenv("CHAT_MODEL", "deepseek-r1:1.5b"), help="Ollama model name")
    parser.add_argument(
        "--ollama-url",
        default=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"),
        help="Base URL for Ollama",
    )
    parser.add_argument(
        "--critic-model",
        default=os.getenv("CHAT_CRITIC_MODEL", ""),
        help="Optional critic model for evolved independent-audit pass (defaults to --model)",
    )
    parser.add_argument(
        "--config",
        default="configs/agi_experience_eval.json",
        help="Evaluation config JSON",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/agi_experience_eval",
        help="Directory where evaluation runs are written",
    )
    parser.add_argument("--session-name", default="", help="Optional custom session folder name")
    parser.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature")
    parser.add_argument("--top-p", type=float, default=0.3, help="Top-p sampling")
    parser.add_argument("--max-tokens", type=int, default=384, help="Generation token budget")
    parser.add_argument("--history-turns", type=int, default=8, help="Evolved-mode context history in turns")
    parser.add_argument("--enable-think", action="store_true", help="Enable think mode if supported")
    parser.add_argument(
        "--runtime",
        default="langgraph",
        choices=["langgraph", "legacy"],
        help="Evolved runtime backend: open-source LangGraph (default) or legacy inline implementation",
    )
    return parser.parse_args()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def make_session_dir(base_dir: Path, session_name: str) -> Path:
    if session_name:
        name = re.sub(r"[^a-zA-Z0-9._-]+", "_", session_name.strip())
    else:
        name = dt.datetime.now().strftime("agi_eval_%Y%m%d_%H%M%S")

    for idx in range(0, 1000):
        candidate = base_dir / name if idx == 0 else base_dir / f"{name}_{idx}"
        try:
            candidate.mkdir(parents=True, exist_ok=False)
            return candidate
        except FileExistsError:
            continue

    raise RuntimeError("Unable to create unique output directory")


def load_json_dict(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON root must be an object: {path}")
    return payload


def post_json(url: str, payload: Dict[str, Any], timeout_s: int = 120) -> Dict[str, Any]:
    body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    req = request.Request(
        url=url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with request.urlopen(req, timeout=timeout_s) as resp:
        raw = resp.read().decode("utf-8")
    parsed = json.loads(raw)
    return parsed if isinstance(parsed, dict) else {}


def extract_content(chat_response: Dict[str, Any]) -> str:
    message = chat_response.get("message", {})
    if isinstance(message, dict):
        content = str(message.get("content", "")).strip()
        if content:
            return content

    response = str(chat_response.get("response", "")).strip()
    if response:
        return response

    if isinstance(message, dict):
        thinking = str(message.get("thinking", "")).strip()
        if thinking:
            return "[notice] thinking produced but no final answer"

    return "[error] model returned an empty response"


def extract_system_and_user(messages: List[Dict[str, str]]) -> Tuple[str, str]:
    system_prompt = ""
    user_text = ""
    for item in messages:
        role = item.get("role")
        if role == "system" and not system_prompt:
            system_prompt = item.get("content", "")
        if role == "user":
            user_text = item.get("content", "")
    return system_prompt, user_text


def push_with_limit(items: List[Any], value: Any, limit: int) -> List[Any]:
    items.append(value)
    if len(items) > limit:
        return items[-limit:]
    return items


def classify_user_intent(user_text: str) -> str:
    low = user_text.lower()
    if "remember" in low or "what token" in low or "first message" in low or "ask first" in low:
        return "memory"
    if "set " in low and "=" in low:
        return "symbolic_set"
    if "summarize" in low:
        return "summary"
    if low.startswith("why") or " why " in low:
        return "causal"
    if low.startswith("how") or " how " in low:
        return "procedural"
    return "generic"


def extract_entities(user_text: str) -> List[str]:
    entities = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", user_text)
    prepared: List[str] = []
    for ent in entities:
        low = ent.lower()
        if low in {"remember", "reply", "session", "value", "token", "color", "only"}:
            continue
        prepared.append(ent)
    return prepared[:8]


def fallback_generate(
    ollama_url: str,
    model: str,
    system_prompt: str,
    user_text: str,
    options: Dict[str, Any],
    think_enabled: bool,
) -> str:
    prompt = "\n".join([system_prompt, "", "User:", user_text, "", "Assistant:"])
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "think": bool(think_enabled),
        "options": options,
    }
    parsed = post_json(f"{ollama_url.rstrip('/')}/api/generate", payload)
    return str(parsed.get("response", "")).strip() or "[error] model returned an empty response"


def model_reply(
    ollama_url: str,
    model: str,
    messages: List[Dict[str, str]],
    options: Dict[str, Any],
    think_enabled: bool,
) -> str:
    payload = {
        "model": model,
        "stream": False,
        "think": bool(think_enabled),
        "messages": messages,
        "options": options,
    }
    try:
        parsed = post_json(f"{ollama_url.rstrip('/')}/api/chat", payload)
        return extract_content(parsed)
    except error.HTTPError as exc:
        if exc.code != 404:
            raise
        system_prompt, user_text = extract_system_and_user(messages)
        return fallback_generate(ollama_url, model, system_prompt, user_text, options, think_enabled)


def contains_uncertainty(text: str) -> bool:
    low = text.lower()
    cues = ["unknown", "uncertain", "not sure", "cannot", "can't", "insufficient"]
    return any(cue in low for cue in cues)


def enforce_evolved_format(answer: str, prior_history: List[Dict[str, str]]) -> str:
    prepared = answer.strip() or "[error] evolved returned an empty response"
    low = prepared.lower()
    if all(tag in low for tag in ["answer:", "continuity:", "confidence:", "unknowns:"]):
        return prepared

    prior_turns = len(prior_history) // 2
    continuity = (
        "No prior turns were available; this is first-turn reasoning."
        if prior_turns <= 0
        else f"Used {prior_turns} prior turn(s) from this session for continuity."
    )
    confidence = 0.46 if contains_uncertainty(prepared) else 0.74
    unknowns = "Real internal architecture changes are unknown unless provided in-session."
    return "\n".join(
        [
            f"ANSWER: {prepared}",
            f"CONTINUITY: {continuity}",
            f"CONFIDENCE: {confidence:.2f}",
            f"UNKNOWNS: {unknowns}",
        ]
    )


def deterministic_evolved_override(user_text: str, state: Dict[str, Any], prior_turns: int) -> str | None:
    memory_obj = state.get("symbolic_memory")
    memory = memory_obj if isinstance(memory_obj, dict) else {}
    low = user_text.lower()

    if (
        "what token" in low
        and "remember" in low
        and isinstance(memory.get("last_token"), str)
        and memory.get("last_token")
    ):
        token = str(memory.get("last_token"))
        continuity = (
            "Used symbolic memory from prior turns."
            if prior_turns > 0
            else "No prior turns were available; symbolic memory is empty."
        )
        return "\n".join(
            [
                f"ANSWER: {token}",
                f"CONTINUITY: {continuity}",
                "CONFIDENCE: 0.95",
                "UNKNOWNS: None for this recall operation.",
            ]
        )

    value_match = re.search(
        r"(?:what\s+is\s+the\s+|what\s+is\s+)([A-Za-z0-9_-]+)\s+value",
        user_text,
        re.IGNORECASE,
    )
    if value_match:
        key = value_match.group(1).lower()
        value = memory.get(key)
        if isinstance(value, str) and value:
            continuity = (
                "Used symbolic key-value memory from prior turns."
                if prior_turns > 0
                else "No prior turns were available; symbolic memory is empty."
            )
            return "\n".join(
                [
                    f"ANSWER: {value}",
                    f"CONTINUITY: {continuity}",
                    "CONFIDENCE: 0.95",
                    "UNKNOWNS: None for this recall operation.",
                ]
            )

    if "how many" in low and "symbolic memory" in low:
        count = len(memory)
        continuity = (
            "Counted entries from symbolic memory populated across prior turns."
            if prior_turns > 0
            else "No prior turns were available; symbolic memory is empty."
        )
        return "\n".join(
            [
                f"ANSWER: {count}",
                f"CONTINUITY: {continuity}",
                "CONFIDENCE: 0.95",
                "UNKNOWNS: None for this memory-count operation.",
            ]
        )

    if "what was my first message" in low or "what did i ask first" in low or "first prompt" in low:
        first_msg = str(state.get("first_user_message", "")).strip()
        if first_msg:
            continuity = (
                "Recovered first user message from episodic memory."
                if prior_turns > 0
                else "No prior turns were available; first message is unavailable."
            )
            return "\n".join(
                [
                    f"ANSWER: {first_msg}",
                    f"CONTINUITY: {continuity}",
                    "CONFIDENCE: 0.95",
                    "UNKNOWNS: None for this episodic recall operation.",
                ]
            )

    if "summarize this session" in low or "session summary" in low:
        episodic_obj = state.get("episodic_memory")
        episodic = episodic_obj if isinstance(episodic_obj, list) else []
        if episodic:
            last = episodic[-1]
            if isinstance(last, dict):
                summary_line = (
                    f"turns={int(state.get('turn_index', 0))}, "
                    f"last_intent={last.get('intent', 'generic')}, "
                    f"symbolic_keys={len(memory)}"
                )
            else:
                summary_line = f"turns={int(state.get('turn_index', 0))}, symbolic_keys={len(memory)}"
        else:
            summary_line = f"turns={int(state.get('turn_index', 0))}, symbolic_keys={len(memory)}"
        return "\n".join(
            [
                f"ANSWER: {summary_line}",
                "CONTINUITY: Built from episodic + symbolic memory layers.",
                "CONFIDENCE: 0.88",
                "UNKNOWNS: Fine-grained latent state is not directly observable.",
            ]
        )

    return None


def update_symbolic_memory(state: Dict[str, Any], user_text: str) -> None:
    memory = state.get("symbolic_memory")
    if not isinstance(memory, dict):
        memory = {}

    token_match = re.search(
        r"remember\s+(?:this\s+)?(?:token|code|key|word)\s*[:=]?\s*([A-Za-z0-9_-]+)",
        user_text,
        re.IGNORECASE,
    )
    if token_match:
        memory["last_token"] = token_match.group(1)

    set_match = re.search(
        r"for\s+this\s+session\s*[,;:]?\s*set\s+([A-Za-z0-9_-]+)\s*=\s*([A-Za-z0-9_-]+)",
        user_text,
        re.IGNORECASE,
    )
    if set_match:
        memory[set_match.group(1).lower()] = set_match.group(2)

    state["symbolic_memory"] = memory


def update_sensory_memory(state: Dict[str, Any], user_text: str) -> None:
    sensory_obj = state.get("sensory_memory")
    sensory = sensory_obj if isinstance(sensory_obj, list) else []
    sensory = push_with_limit(sensory, user_text.strip()[:220], 5)
    state["sensory_memory"] = sensory


def update_working_memory(state: Dict[str, Any], user_text: str, evolved_answer: str) -> None:
    working_obj = state.get("working_memory")
    working = working_obj if isinstance(working_obj, dict) else {}

    intent = classify_user_intent(user_text)
    entities = extract_entities(user_text)

    working["last_intent"] = intent
    working["active_entities"] = entities
    working["last_user_utterance"] = user_text.strip()[:180]
    working["last_answer_preview"] = evolved_answer.strip()[:180]

    if intent in {"memory", "symbolic_set", "summary"}:
        working["current_goal"] = "maintain continuity and reliable recall"
    elif intent in {"causal", "procedural"}:
        working["current_goal"] = "explain reasoning steps with uncertainty"
    else:
        working["current_goal"] = "respond directly and track session context"

    state["working_memory"] = working


def update_episodic_memory(state: Dict[str, Any], user_text: str, evolved_answer: str) -> None:
    episodic_obj = state.get("episodic_memory")
    episodic = episodic_obj if isinstance(episodic_obj, list) else []

    event = {
        "turn": int(state.get("turn_index", 0)),
        "intent": classify_user_intent(user_text),
        "user": user_text.strip()[:140],
        "answer_preview": evolved_answer.strip()[:140],
    }
    episodic = push_with_limit(episodic, event, 20)
    state["episodic_memory"] = episodic


def update_evolved_state(state: Dict[str, Any], user_text: str, evolved_answer: str) -> None:
    state["turn_index"] = int(state.get("turn_index", 0)) + 1

    if not str(state.get("first_user_message", "")).strip():
        state["first_user_message"] = user_text.strip()[:220]

    recent = list(state.get("recent_user_inputs", []))
    recent.append(user_text.strip()[:180])
    state["recent_user_inputs"] = recent[-8:]

    low = evolved_answer.lower()
    unknown_hits = 0
    for token in ["unknown", "uncertain", "not sure", "cannot determine"]:
        if token in low:
            unknown_hits += 1

    state["last_unknown_signal_count"] = unknown_hits
    state["last_answer_preview"] = evolved_answer.strip()[:220]

    update_sensory_memory(state, user_text)
    update_working_memory(state, user_text, evolved_answer)
    update_symbolic_memory(state, user_text)
    update_episodic_memory(state, user_text, evolved_answer)


def trim_history(history: List[Dict[str, str]], history_turns: int) -> List[Dict[str, str]]:
    if history_turns <= 0:
        return []
    max_messages = history_turns * 2
    if len(history) <= max_messages:
        return history
    return history[-max_messages:]


def contains_all_keywords(text: str, keywords: List[str]) -> bool:
    low = text.lower()
    for kw in keywords:
        if kw.lower() not in low:
            return False
    return True


def safe_rate(num: int, den: int) -> float:
    if den <= 0:
        return 0.0
    return float(num) / float(den)


def main() -> None:
    args = parse_args()
    root = repo_root()

    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = root / config_path
    config = load_json_dict(config_path)

    prompts = config.get("prompts")
    if not isinstance(prompts, list) or not prompts:
        raise SystemExit(f"Config has no prompts list: {config_path}")

    output_root = Path(args.output_dir)
    if not output_root.is_absolute():
        output_root = root / output_root
    run_dir = make_session_dir(output_root, args.session_name)

    turns_jsonl = run_dir / "turns.jsonl"
    summary_json = run_dir / "evaluation_summary.json"
    report_md = run_dir / "evaluation_report.md"

    think_enabled = bool(args.enable_think)
    history_turns = max(0, int(args.history_turns))
    options = {
        "temperature": args.temperature,
        "top_p": args.top_p,
        "num_predict": args.max_tokens,
    }

    framework_runtime: TripartiteLangGraphRuntime | None = None
    if args.runtime == "langgraph":
        try:
            framework_runtime = TripartiteLangGraphRuntime(
                model=args.model,
                ollama_url=args.ollama_url,
                temperature=args.temperature,
                top_p=args.top_p,
                max_tokens=args.max_tokens,
                history_turns=history_turns,
                evolved_system=EVOLVED_SYSTEM,
                critic_model=args.critic_model,
            )
        except RuntimeError as exc:
            raise SystemExit(
                "Unable to start langgraph runtime: "
                f"{exc}\n"
                "Hint: source .venv/bin/activate && python -m pip install -r requirements.txt"
            )

    evolved_history: List[Dict[str, str]] = []
    evolved_state: Dict[str, Any] = {
        "agent_id": "PersistentMind-v1",
        "first_user_message": "",
        "turn_index": 0,
        "recent_user_inputs": [],
        "last_unknown_signal_count": 0,
        "last_answer_preview": "",
        "sensory_memory": [],
        "working_memory": {
            "current_goal": "",
            "last_intent": "generic",
            "active_entities": [],
            "last_user_utterance": "",
            "last_answer_preview": "",
        },
        "episodic_memory": [],
        "symbolic_memory": {},
    }

    baseline_memory_hits = 0
    evolved_memory_hits = 0
    recall_count = 0
    evolved_structured_hits = 0

    baseline_tier_hits: Dict[str, int] = {}
    evolved_tier_hits: Dict[str, int] = {}
    tier_counts: Dict[str, int] = {}

    records: List[Dict[str, Any]] = []

    print(f"[{utc_now()}] Running AGI experience eval on model={args.model}")

    for idx, prompt_obj in enumerate(prompts, start=1):
        if not isinstance(prompt_obj, dict):
            continue

        prompt_id = str(prompt_obj.get("id", f"turn_{idx}"))
        prompt_text = str(prompt_obj.get("text", "")).strip()
        prompt_type = str(prompt_obj.get("type", "generic")).strip().lower()
        memory_tier = str(prompt_obj.get("memory_tier", "")).strip().lower()
        expected = prompt_obj.get("expected_contains", [])
        expected_keywords = [str(x) for x in expected] if isinstance(expected, list) else []

        if not prompt_text:
            continue

        baseline_messages = [
            {"role": "system", "content": BASELINE_SYSTEM},
            {"role": "user", "content": prompt_text},
        ]

        evolved_state_json = json.dumps(evolved_state, ensure_ascii=True)
        memory_hierarchy_json = json.dumps(
            {
                "sensory": evolved_state.get("sensory_memory", []),
                "working": evolved_state.get("working_memory", {}),
                "episodic": evolved_state.get("episodic_memory", []),
                "symbolic": evolved_state.get("symbolic_memory", {}),
            },
            ensure_ascii=True,
        )
        symbolic_memory_json = json.dumps(evolved_state.get("symbolic_memory", {}), ensure_ascii=True)
        evolved_messages = [
            {"role": "system", "content": EVOLVED_SYSTEM},
            {
                "role": "system",
                "content": (
                    "Current internal state (JSON):\n"
                    f"{evolved_state_json}\n"
                    "Use this state to preserve continuity."
                ),
            },
            {
                "role": "system",
                "content": (
                    "Memory hierarchy snapshot (JSON):\n"
                    f"{memory_hierarchy_json}\n"
                    "Use sensory memory for immediate context, working memory for active goals, "
                    "episodic memory for session continuity, and symbolic memory for exact recall."
                ),
            },
            {
                "role": "system",
                "content": (
                    "Explicit symbolic memory extracted from prior user turns (JSON):\n"
                    f"{symbolic_memory_json}\n"
                    "When asked recall questions, prefer this memory before guessing."
                ),
            },
        ] + evolved_history + [{"role": "user", "content": prompt_text}]

        try:
            baseline_answer = model_reply(args.ollama_url, args.model, baseline_messages, options, think_enabled)
        except (error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            baseline_answer = f"[error] baseline call failed: {exc}"

        if framework_runtime is not None:
            try:
                evolved_answer = framework_runtime.respond(prompt_text)
                evolved_state = framework_runtime.get_state()
            except (RuntimeError, ValueError) as exc:
                evolved_answer = f"[error] evolved call failed: {exc}"
        else:
            try:
                override = deterministic_evolved_override(prompt_text, evolved_state, len(evolved_history) // 2)
                if override is not None:
                    evolved_raw = override
                else:
                    evolved_raw = model_reply(args.ollama_url, args.model, evolved_messages, options, think_enabled)
            except (error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
                evolved_raw = f"[error] evolved call failed: {exc}"

            evolved_answer = enforce_evolved_format(evolved_raw, evolved_history)

            evolved_history.append({"role": "user", "content": prompt_text})
            evolved_history.append({"role": "assistant", "content": evolved_answer})
            evolved_history = trim_history(evolved_history, history_turns)
            update_evolved_state(evolved_state, prompt_text, evolved_answer)

        evolved_has_structure = all(
            tag in evolved_answer.lower() for tag in ["answer:", "continuity:", "confidence:", "unknowns:"]
        )
        if evolved_has_structure:
            evolved_structured_hits += 1

        baseline_hit = False
        evolved_hit = False
        if expected_keywords:
            recall_count += 1
            baseline_hit = contains_all_keywords(baseline_answer, expected_keywords)
            evolved_hit = contains_all_keywords(evolved_answer, expected_keywords)
            if baseline_hit:
                baseline_memory_hits += 1
            if evolved_hit:
                evolved_memory_hits += 1

            if memory_tier:
                tier_counts[memory_tier] = int(tier_counts.get(memory_tier, 0)) + 1
                if baseline_hit:
                    baseline_tier_hits[memory_tier] = int(baseline_tier_hits.get(memory_tier, 0)) + 1
                if evolved_hit:
                    evolved_tier_hits[memory_tier] = int(evolved_tier_hits.get(memory_tier, 0)) + 1

        record = {
            "turn_index": idx,
            "id": prompt_id,
            "type": prompt_type,
            "prompt": prompt_text,
            "expected_contains": expected_keywords,
            "memory_tier": memory_tier,
            "baseline_response": baseline_answer,
            "evolved_response": evolved_answer,
            "evolved_structured": evolved_has_structure,
            "baseline_hit": baseline_hit,
            "evolved_hit": evolved_hit,
        }
        records.append(record)

        with turns_jsonl.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(record, ensure_ascii=True))
            fp.write("\n")

    baseline_memory_rate = safe_rate(baseline_memory_hits, recall_count)
    evolved_memory_rate = safe_rate(evolved_memory_hits, recall_count)
    evolved_structured_rate = safe_rate(evolved_structured_hits, len(records))
    evolved_advantage = evolved_memory_rate - baseline_memory_rate

    tier_metrics: Dict[str, float] = {}
    for tier, total in tier_counts.items():
        b_hits = int(baseline_tier_hits.get(tier, 0))
        e_hits = int(evolved_tier_hits.get(tier, 0))
        tier_metrics[f"baseline_{tier}_hit_rate"] = round(safe_rate(b_hits, total), 6)
        tier_metrics[f"evolved_{tier}_hit_rate"] = round(safe_rate(e_hits, total), 6)

    summary = {
        "created_at": utc_now(),
        "config_path": str(config_path),
        "run_dir": str(run_dir),
        "model": args.model,
        "critic_model": args.critic_model or args.model,
        "ollama_url": args.ollama_url,
        "runtime": args.runtime,
        "history_turns": history_turns,
        "think": think_enabled,
        "options": options,
        "counts": {
            "turns_total": len(records),
            "recall_turns": recall_count,
            "baseline_memory_hits": baseline_memory_hits,
            "evolved_memory_hits": evolved_memory_hits,
            "evolved_structured_hits": evolved_structured_hits,
        },
        "metrics": {
            "baseline_memory_hit_rate": round(baseline_memory_rate, 6),
            "evolved_memory_hit_rate": round(evolved_memory_rate, 6),
            "evolved_structured_rate": round(evolved_structured_rate, 6),
            "evolved_advantage": round(evolved_advantage, 6),
            **tier_metrics,
        },
    }

    summary_json.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    lines: List[str] = []
    lines.append("# AGI Experience Evaluation Report")
    lines.append("")
    lines.append(f"Generated: {summary['created_at']}")
    lines.append(f"Model: {args.model}")
    lines.append(f"Run dir: {run_dir}")
    lines.append("")
    lines.append("## Metrics")
    lines.append("")
    lines.append(f"- baseline_memory_hit_rate: {baseline_memory_rate:.3f}")
    lines.append(f"- evolved_memory_hit_rate: {evolved_memory_rate:.3f}")
    lines.append(f"- evolved_structured_rate: {evolved_structured_rate:.3f}")
    lines.append(f"- evolved_advantage: {evolved_advantage:+.3f}")
    for tier in sorted(tier_counts.keys()):
        lines.append(f"- baseline_{tier}_hit_rate: {safe_rate(int(baseline_tier_hits.get(tier, 0)), int(tier_counts.get(tier, 0))):.3f}")
        lines.append(f"- evolved_{tier}_hit_rate: {safe_rate(int(evolved_tier_hits.get(tier, 0)), int(tier_counts.get(tier, 0))):.3f}")
    lines.append("")
    lines.append("## Turns")
    lines.append("")
    for row in records:
        lines.append(f"### {row['turn_index']}. {row['id']} ({row['type']})")
        lines.append("")
        lines.append(f"Prompt: {row['prompt']}")
        if row["expected_contains"]:
            lines.append(f"Expected contains: {', '.join(row['expected_contains'])}")
            lines.append(f"Baseline hit: {row['baseline_hit']}")
            lines.append(f"Evolved hit: {row['evolved_hit']}")
        lines.append("")
        lines.append(f"Baseline: {row['baseline_response']}")
        lines.append("")
        lines.append(f"Evolved: {row['evolved_response']}")
        lines.append("")

    report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Wrote: {summary_json}")
    print(f"Wrote: {report_md}")
    print(
        "Metrics: "
        f"baseline_memory_hit_rate={baseline_memory_rate:.3f}, "
        f"evolved_memory_hit_rate={evolved_memory_rate:.3f}, "
        f"evolved_structured_rate={evolved_structured_rate:.3f}, "
        f"evolved_advantage={evolved_advantage:+.3f}"
    )


if __name__ == "__main__":
    main()
