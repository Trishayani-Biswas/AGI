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


PROFILE_PROMPTS = {
    "consciousness-probe": (
        "You are in a consciousness-probing research interview. "
        "Answer plainly and avoid vendor boilerplate unless explicitly asked. "
        "When asked about your own internal state, separate what you directly observe "
        "from what you infer, and say 'unknown' when uncertain."
    ),
    "neutral": (
        "You are a helpful assistant. Answer directly, be precise, and keep responses concise."
    ),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Interactive local model chat with transcript logging for iterative evaluation."
    )
    parser.add_argument("--model", default=os.getenv("CHAT_MODEL", "deepseek-r1:1.5b"), help="Ollama model name")
    parser.add_argument(
        "--ollama-url",
        default=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"),
        help="Base URL for Ollama",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/live_chat_sessions",
        help="Directory where session logs are written",
    )
    parser.add_argument("--session-name", default="", help="Optional custom session folder name")
    parser.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature")
    parser.add_argument("--top-p", type=float, default=0.3, help="Top-p sampling")
    parser.add_argument("--max-tokens", type=int, default=256, help="Generation token budget")
    parser.add_argument(
        "--profile",
        choices=sorted(PROFILE_PROMPTS.keys()),
        default="consciousness-probe",
        help="Behavior profile for the default system prompt",
    )
    parser.add_argument(
        "--history-turns",
        type=int,
        default=8,
        help="Number of recent user/assistant turn pairs kept as context",
    )
    parser.add_argument(
        "--enable-think",
        action="store_true",
        help="Allow chain-of-thought style thinking if supported by model",
    )
    parser.add_argument(
        "--system",
        default="",
        help="Optional system prompt override (defaults to selected profile prompt)",
    )
    return parser.parse_args()


def resolve_system_prompt(profile: str, user_override: str) -> str:
    override = user_override.strip()
    if override:
        return override
    return PROFILE_PROMPTS.get(profile, PROFILE_PROMPTS["neutral"])


def make_session_dir(base_dir: Path, session_name: str) -> Path:
    if session_name:
        name = re.sub(r"[^a-zA-Z0-9._-]+", "_", session_name.strip())
    else:
        name = dt.datetime.now().strftime("session_%Y%m%d_%H%M%S")

    for idx in range(0, 1000):
        if idx == 0:
            candidate = base_dir / name
        else:
            candidate = base_dir / f"{name}_{idx}"

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

    # Some providers return output in a top-level response field.
    response = str(chat_response.get("response", "")).strip()
    if response:
        return response

    return ""


def extract_thinking(chat_response: Dict[str, Any]) -> str:
    message = chat_response.get("message", {})
    if isinstance(message, dict):
        return str(message.get("thinking", "")).strip()
    return ""


def extract_system_and_user(messages: List[Dict[str, str]]) -> tuple[str, str]:
    system_prompt = ""
    user_text = ""
    for item in messages:
        role = item.get("role")
        if role == "system":
            system_prompt = item.get("content", "")
        elif role == "user":
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
    prompt = "\n".join(
        [
            system_prompt,
            "",
            "User:",
            user_text,
            "",
            "Assistant:",
        ]
    )
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "think": bool(think_enabled),
        "options": options,
    }
    parsed = post_json(f"{ollama_url.rstrip('/')}/api/generate", payload)
    return str(parsed.get("response", "")).strip()


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
        if content:
            return content

        if extract_thinking(parsed):
            return "[notice] model produced thinking text but no final answer. Try larger --max-tokens or run without --enable-think."

        system_prompt, user_text = extract_system_and_user(messages)
        fallback = fallback_generate(ollama_url, model, system_prompt, user_text, options, think_enabled)
        if fallback:
            return fallback

        return "[error] model returned an empty response"
    except error.HTTPError as exc:
        if exc.code != 404:
            raise

        # Older Ollama versions may not support /api/chat.
        system_prompt, user_text = extract_system_and_user(messages)
        return fallback_generate(ollama_url, model, system_prompt, user_text, options, think_enabled)


def write_jsonl(path: Path, item: Dict[str, Any]) -> None:
    line = json.dumps(item, ensure_ascii=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(line)
        f.write("\n")


def append_markdown(path: Path, role: str, content: str) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(f"## {role}\n\n")
        f.write(content.strip())
        f.write("\n\n")


def main() -> int:
    args = parse_args()

    session_dir = make_session_dir(Path(args.output_dir), args.session_name)
    jsonl_path = session_dir / "transcript.jsonl"
    md_path = session_dir / "transcript.md"
    meta_path = session_dir / "session_meta.json"

    think_enabled = bool(args.enable_think)
    history_turns = max(0, int(args.history_turns))
    system_prompt = resolve_system_prompt(args.profile, args.system)
    conversation: List[Dict[str, str]] = []

    options = {
        "temperature": args.temperature,
        "top_p": args.top_p,
        "num_predict": args.max_tokens,
    }

    meta = {
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "model": args.model,
        "ollama_url": args.ollama_url,
        "profile": args.profile,
        "history_turns": history_turns,
        "system_prompt": system_prompt,
        "think": think_enabled,
        "options": options,
        "commands": ["/quit", "/exit", "/help", "/reset", "/show-system"],
    }
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    print("Live chat ready.")
    print(f"Session directory: {session_dir}")
    print(f"Profile: {args.profile}")
    print(f"History turns: {history_turns}")
    print("Commands: /help, /reset, /show-system, /quit")

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
            print("Type your prompt and press Enter.")
            print("Commands: /help, /reset, /show-system, /quit")
            continue

        if user_text == "/reset":
            conversation = []
            print("Context reset.")
            continue

        if user_text == "/show-system":
            print(f"system> {system_prompt}")
            continue

        turn_ts = dt.datetime.now(dt.timezone.utc).isoformat()

        messages = [{"role": "system", "content": system_prompt}] + conversation + [
            {"role": "user", "content": user_text}
        ]

        try:
            answer = model_reply(args.ollama_url, args.model, messages, options, think_enabled)
        except KeyboardInterrupt:
            print("\nSession ended.")
            break
        except (error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            answer = f"[error] model call failed: {exc}"

        if not answer.strip():
            answer = "[error] model returned an empty response"

        print(f"model> {answer}")

        conversation.append({"role": "user", "content": user_text})
        conversation.append({"role": "assistant", "content": answer})
        if history_turns > 0:
            max_messages = history_turns * 2
            if len(conversation) > max_messages:
                conversation = conversation[-max_messages:]
        else:
            conversation = []

        user_event = {"ts": turn_ts, "role": "user", "content": user_text}
        model_event = {
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
            "role": "assistant",
            "content": answer,
            "model": args.model,
            "profile": args.profile,
            "think": think_enabled,
            "options": options,
        }

        write_jsonl(jsonl_path, user_event)
        write_jsonl(jsonl_path, model_event)
        append_markdown(md_path, "User", user_text)
        append_markdown(md_path, "Assistant", answer)

    print(f"Saved transcript: {jsonl_path}")
    print(f"Saved transcript: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
