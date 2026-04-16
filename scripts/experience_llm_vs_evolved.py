#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List
from urllib import error, request


BASELINE_SYSTEM = (
    "You are a standard assistant. "
    "Give a direct response in 2-4 concise sentences."
)

EVOLVED_SYSTEM = (
    "You are PersistentMind-v1, an evolving reasoning agent under continuity testing. "
    "You preserve autobiographical continuity across this session, explicitly track uncertainty, "
    "and avoid generic vendor boilerplate unless the user explicitly asks for policy details. "
    "When answering, follow this structure exactly:\n"
    "ANSWER: <direct answer>\n"
    "CONTINUITY: <what from prior turns influenced this answer>\n"
    "CONFIDENCE: <0.00 to 1.00>\n"
    "UNKNOWNS: <what remains uncertain>"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Interactive side-by-side chat: baseline LLM vs evolved persistent mode."
    )
    parser.add_argument("--model", default=os.getenv("CHAT_MODEL", "deepseek-r1:1.5b"), help="Ollama model name")
    parser.add_argument(
        "--ollama-url",
        default=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"),
        help="Base URL for Ollama",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/live_chat_experience",
        help="Directory where comparison sessions are written",
    )
    parser.add_argument("--session-name", default="", help="Optional custom session folder name")
    parser.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature")
    parser.add_argument("--top-p", type=float, default=0.3, help="Top-p sampling")
    parser.add_argument("--max-tokens", type=int, default=384, help="Generation token budget")
    parser.add_argument(
        "--history-turns",
        type=int,
        default=8,
        help="Number of recent turn pairs retained for evolved mode",
    )
    parser.add_argument(
        "--enable-think",
        action="store_true",
        help="Enable think mode if your model/runtime supports it",
    )
    parser.add_argument(
        "--baseline-system",
        default=BASELINE_SYSTEM,
        help="Optional baseline system prompt override",
    )
    parser.add_argument(
        "--evolved-system",
        default=EVOLVED_SYSTEM,
        help="Optional evolved system prompt override",
    )
    return parser.parse_args()


def make_session_dir(base_dir: Path, session_name: str) -> Path:
    if session_name:
        name = re.sub(r"[^a-zA-Z0-9._-]+", "_", session_name.strip())
    else:
        name = dt.datetime.now().strftime("experience_%Y%m%d_%H%M%S")

    for idx in range(0, 1000):
        candidate = base_dir / name if idx == 0 else base_dir / f"{name}_{idx}"
        try:
            candidate.mkdir(parents=True, exist_ok=False)
            return candidate
        except FileExistsError:
            continue

    raise RuntimeError("Unable to create unique session directory after 1000 attempts")


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

    message = chat_response.get("message", {})
    if isinstance(message, dict):
        thinking = str(message.get("thinking", "")).strip()
        if thinking:
            return "[notice] thinking produced but no final answer; try larger --max-tokens or disable --enable-think"

    return "[error] model returned an empty response"


def extract_system_and_user(messages: List[Dict[str, str]]) -> tuple[str, str]:
    system_prompt = ""
    user_text = ""
    for item in messages:
        role = item.get("role")
        if role == "system" and not system_prompt:
            system_prompt = item.get("content", "")
        if role == "user":
            user_text = item.get("content", "")
    return system_prompt, user_text


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
        content = extract_content(parsed)
        return content if content else "[error] model returned an empty response"
    except error.HTTPError as exc:
        if exc.code != 404:
            raise

        system_prompt, user_text = extract_system_and_user(messages)
        return fallback_generate(ollama_url, model, system_prompt, user_text, options, think_enabled)


def write_jsonl(path: Path, item: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=True))
        f.write("\n")


def append_markdown(path: Path, role: str, content: str) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(f"## {role}\n\n")
        f.write(content.strip())
        f.write("\n\n")


def trim_history(history: List[Dict[str, str]], history_turns: int) -> List[Dict[str, str]]:
    if history_turns <= 0:
        return []
    max_messages = history_turns * 2
    if len(history) <= max_messages:
        return history
    return history[-max_messages:]


def contains_uncertainty(text: str) -> bool:
    low = text.lower()
    cues = ["unknown", "uncertain", "not sure", "cannot", "can't", "insufficient"]
    return any(cue in low for cue in cues)


def enforce_evolved_format(raw_answer: str, prior_history: List[Dict[str, str]]) -> str:
    answer = raw_answer.strip() or "[error] evolved returned an empty response"

    # Keep model-provided structured responses as-is if they already follow the contract.
    low = answer.lower()
    if all(tag in low for tag in ["answer:", "continuity:", "confidence:", "unknowns:"]):
        return answer

    prior_turns = len(prior_history) // 2
    if prior_turns <= 0:
        continuity = "No prior turns were available; this is first-turn reasoning."
    else:
        continuity = f"Used {prior_turns} prior turn(s) from this session for continuity."

    confidence = 0.46 if contains_uncertainty(answer) else 0.74
    unknowns = (
        "Real internal architecture changes are unknown unless explicitly provided in-session."
    )

    return "\n".join(
        [
            f"ANSWER: {answer}",
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
        key = set_match.group(1).lower()
        value = set_match.group(2)
        memory[key] = value

    if len(memory) > 12:
        trimmed: Dict[str, Any] = {}
        for k in list(memory.keys())[-12:]:
            trimmed[k] = memory[k]
        memory = trimmed

    state["symbolic_memory"] = memory


def update_evolved_state(state: Dict[str, Any], user_text: str, evolved_answer: str) -> None:
    state["turn_index"] = int(state.get("turn_index", 0)) + 1

    recent_inputs = list(state.get("recent_user_inputs", []))
    recent_inputs.append(user_text.strip()[:180])
    state["recent_user_inputs"] = recent_inputs[-8:]

    low = evolved_answer.lower()
    unknown_hits = 0
    for token in ["unknown", "uncertain", "not sure", "cannot determine"]:
        if token in low:
            unknown_hits += 1

    state["last_unknown_signal_count"] = unknown_hits
    state["last_answer_preview"] = evolved_answer.strip()[:220]

    update_symbolic_memory(state, user_text)


def main() -> int:
    args = parse_args()

    session_dir = make_session_dir(Path(args.output_dir), args.session_name)
    jsonl_path = session_dir / "transcript.jsonl"
    md_path = session_dir / "transcript.md"
    meta_path = session_dir / "session_meta.json"

    think_enabled = bool(args.enable_think)
    history_turns = max(0, int(args.history_turns))

    options = {
        "temperature": args.temperature,
        "top_p": args.top_p,
        "num_predict": args.max_tokens,
    }

    evolved_history: List[Dict[str, str]] = []
    evolved_state: Dict[str, Any] = {
        "agent_id": "PersistentMind-v1",
        "session_goal": "Differentiate baseline LLM behavior from evolved continuity-aware behavior",
        "turn_index": 0,
        "recent_user_inputs": [],
        "last_unknown_signal_count": 0,
        "last_answer_preview": "",
        "symbolic_memory": {},
    }

    meta = {
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "model": args.model,
        "ollama_url": args.ollama_url,
        "history_turns": history_turns,
        "think": think_enabled,
        "options": options,
        "baseline_system": args.baseline_system,
        "evolved_system": args.evolved_system,
        "commands": ["/help", "/state", "/reset", "/quit", "/exit"],
    }
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    print("Experience mode ready: baseline vs evolved")
    print(f"Session directory: {session_dir}")
    print("Commands: /help, /state, /reset, /quit")

    while True:
        try:
            user_text = input("you> ").strip()
        except EOFError:
            print("\nSession ended.")
            break
        except KeyboardInterrupt:
            print("\nSession ended.")
            break

        if not user_text:
            continue

        if user_text in {"/quit", "/exit"}:
            print("Session ended.")
            break

        if user_text == "/help":
            print("Type a message to compare baseline and evolved outputs.")
            print("Commands: /help, /state, /reset, /quit")
            continue

        if user_text == "/reset":
            evolved_history = []
            evolved_state["turn_index"] = 0
            evolved_state["recent_user_inputs"] = []
            evolved_state["last_unknown_signal_count"] = 0
            evolved_state["last_answer_preview"] = ""
            evolved_state["symbolic_memory"] = {}
            print("Evolved context reset.")
            continue

        if user_text == "/state":
            print("state> " + json.dumps(evolved_state, ensure_ascii=True))
            continue

        turn_ts = dt.datetime.now(dt.timezone.utc).isoformat()

        baseline_messages = [
            {"role": "system", "content": args.baseline_system},
            {"role": "user", "content": user_text},
        ]

        evolved_state_json = json.dumps(evolved_state, ensure_ascii=True)
        symbolic_memory_json = json.dumps(evolved_state.get("symbolic_memory", {}), ensure_ascii=True)
        evolved_messages = [
            {"role": "system", "content": args.evolved_system},
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
                    "Explicit symbolic memory extracted from prior user turns (JSON):\n"
                    f"{symbolic_memory_json}\n"
                    "When a user asks recall questions, prefer this memory before guessing."
                ),
            },
        ] + evolved_history + [{"role": "user", "content": user_text}]

        try:
            baseline_answer = model_reply(args.ollama_url, args.model, baseline_messages, options, think_enabled)
        except (error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            baseline_answer = f"[error] baseline call failed: {exc}"

        try:
            override = deterministic_evolved_override(user_text, evolved_state, len(evolved_history) // 2)
            if override is not None:
                evolved_answer = override
            else:
                evolved_answer = model_reply(args.ollama_url, args.model, evolved_messages, options, think_enabled)
        except (error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            evolved_answer = f"[error] evolved call failed: {exc}"

        evolved_answer = enforce_evolved_format(evolved_answer, evolved_history)

        if not baseline_answer.strip():
            baseline_answer = "[error] baseline returned an empty response"
        if not evolved_answer.strip():
            evolved_answer = "[error] evolved returned an empty response"

        print(f"baseline> {baseline_answer}")
        print(f"evolved> {evolved_answer}")

        evolved_history.append({"role": "user", "content": user_text})
        evolved_history.append({"role": "assistant", "content": evolved_answer})
        evolved_history = trim_history(evolved_history, history_turns)
        update_evolved_state(evolved_state, user_text, evolved_answer)

        write_jsonl(jsonl_path, {"ts": turn_ts, "role": "user", "content": user_text})
        write_jsonl(
            jsonl_path,
            {
                "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
                "role": "baseline",
                "content": baseline_answer,
                "model": args.model,
                "options": options,
                "think": think_enabled,
            },
        )
        write_jsonl(
            jsonl_path,
            {
                "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
                "role": "evolved",
                "content": evolved_answer,
                "model": args.model,
                "options": options,
                "think": think_enabled,
                "state": evolved_state,
            },
        )

        append_markdown(md_path, "User", user_text)
        append_markdown(md_path, "Baseline", baseline_answer)
        append_markdown(md_path, "Evolved", evolved_answer)

    print(f"Saved transcript: {jsonl_path}")
    print(f"Saved transcript: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
