#!/usr/bin/env python3
from __future__ import annotations

import json
import importlib
import re
from typing import Any, Dict, List

try:
    importlib.import_module("langchain_core.messages")
    importlib.import_module("langchain_ollama")
    importlib.import_module("langgraph.graph")

    FRAMEWORK_AVAILABLE = True
    FRAMEWORK_IMPORT_ERROR = ""
except Exception as exc:  # pragma: no cover - import guard for optional deps
    FRAMEWORK_AVAILABLE = False
    FRAMEWORK_IMPORT_ERROR = str(exc)


def push_with_limit(items: List[Any], value: Any, limit: int) -> List[Any]:
    items.append(value)
    if len(items) > limit:
        return items[-limit:]
    return items


def trim_history(history: List[Dict[str, str]], history_turns: int) -> List[Dict[str, str]]:
    if history_turns <= 0:
        return []
    max_messages = history_turns * 2
    if len(history) <= max_messages:
        return history
    return history[-max_messages:]


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


def contains_uncertainty(text: str) -> bool:
    low = text.lower()
    cues = ["unknown", "uncertain", "not sure", "cannot", "can't", "insufficient"]
    return any(cue in low for cue in cues)


def enforce_evolved_format(raw_answer: str, prior_history: List[Dict[str, str]]) -> str:
    answer = raw_answer.strip() or "[error] evolved returned an empty response"

    low = answer.lower()
    if all(tag in low for tag in ["answer:", "continuity:", "confidence:", "unknowns:"]):
        return answer

    prior_turns = len(prior_history) // 2
    if prior_turns <= 0:
        continuity = "No prior turns were available; this is first-turn reasoning."
    else:
        continuity = f"Used {prior_turns} prior turn(s) from this session for continuity."

    confidence = 0.46 if contains_uncertainty(answer) else 0.74
    unknowns = "Real internal architecture changes are unknown unless explicitly provided in-session."

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
        key = set_match.group(1).lower()
        value = set_match.group(2)
        memory[key] = value

    if len(memory) > 12:
        trimmed: Dict[str, Any] = {}
        for k in list(memory.keys())[-12:]:
            trimmed[k] = memory[k]
        memory = trimmed

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

    update_sensory_memory(state, user_text)
    update_working_memory(state, user_text, evolved_answer)
    update_symbolic_memory(state, user_text)
    update_episodic_memory(state, user_text, evolved_answer)


class TripartiteLangGraphRuntime:
    """Tripartite AGI runtime built on LangGraph.

    Graph nodes map directly to the architecture:
    - CSG: continuous thought generation
    - MMIE: metacognitive memory + insight synthesis
    - ECC: executive formatting/supervision
    """

    def __init__(
        self,
        *,
        model: str,
        ollama_url: str,
        temperature: float,
        top_p: float,
        max_tokens: int,
        history_turns: int,
        evolved_system: str,
    ) -> None:
        if not FRAMEWORK_AVAILABLE:
            raise RuntimeError(
                "LangGraph runtime dependencies missing. "
                "Install with: python -m pip install -r requirements.txt. "
                f"Import error: {FRAMEWORK_IMPORT_ERROR}"
            )

        self.model = model
        self.ollama_url = ollama_url
        self.history_turns = max(0, int(history_turns))
        self.evolved_system = evolved_system

        messages_mod = importlib.import_module("langchain_core.messages")
        ollama_mod = importlib.import_module("langchain_ollama")
        graph_mod = importlib.import_module("langgraph.graph")

        self._AIMessage = getattr(messages_mod, "AIMessage")
        self._HumanMessage = getattr(messages_mod, "HumanMessage")
        self._SystemMessage = getattr(messages_mod, "SystemMessage")
        self._StateGraph = getattr(graph_mod, "StateGraph")
        self._END = getattr(graph_mod, "END")
        self._ChatOllama = getattr(ollama_mod, "ChatOllama")

        self._llm = self._ChatOllama(
            model=model,
            base_url=ollama_url,
            temperature=temperature,
            top_p=top_p,
            num_predict=max_tokens,
        )

        self._state = self._new_state()
        self._history: List[Dict[str, str]] = []
        self._graph = self._build_graph()

    def _new_state(self) -> Dict[str, Any]:
        return {
            "agent_id": "PersistentMind-v1",
            "session_goal": "Differentiate baseline LLM behavior from evolved continuity-aware behavior",
            "turn_index": 0,
            "first_user_message": "",
            "recent_user_inputs": [],
            "last_unknown_signal_count": 0,
            "last_answer_preview": "",
            "latest_insight_summary": "",
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

    def reset(self) -> None:
        self._state = self._new_state()
        self._history = []

    def get_state(self) -> Dict[str, Any]:
        return json.loads(json.dumps(self._state, ensure_ascii=True))

    def get_history(self) -> List[Dict[str, str]]:
        return json.loads(json.dumps(self._history, ensure_ascii=True))

    def _build_graph(self):
        graph = self._StateGraph(dict)
        graph.add_node("csg", self._node_csg)
        graph.add_node("mmie", self._node_mmie)
        graph.add_node("ecc", self._node_ecc)
        graph.set_entry_point("csg")
        graph.add_edge("csg", "mmie")
        graph.add_edge("mmie", "ecc")
        graph.add_edge("ecc", self._END)
        return graph.compile()

    def _invoke_llm(self, messages: List[Any]) -> str:
        response = self._llm.invoke(messages)
        content = response.content
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            prepared: List[str] = []
            for item in content:
                if isinstance(item, str):
                    prepared.append(item)
                elif isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        prepared.append(text)
            joined = "\n".join(x for x in prepared if x.strip()).strip()
            if joined:
                return joined
        return "[error] model returned an empty response"

    def _memory_hierarchy_json(self, state: Dict[str, Any]) -> str:
        return json.dumps(
            {
                "sensory": state.get("sensory_memory", []),
                "working": state.get("working_memory", {}),
                "episodic": state.get("episodic_memory", []),
                "symbolic": state.get("symbolic_memory", {}),
            },
            ensure_ascii=True,
        )

    def _build_insight_summary(self, state: Dict[str, Any]) -> str:
        episodic_obj = state.get("episodic_memory")
        episodic = episodic_obj if isinstance(episodic_obj, list) else []
        if not episodic:
            return "No episodic events yet; keep collecting trajectory before abstraction."

        intent_counts: Dict[str, int] = {}
        for item in episodic[-10:]:
            if not isinstance(item, dict):
                continue
            intent = str(item.get("intent", "generic"))
            intent_counts[intent] = int(intent_counts.get(intent, 0)) + 1

        if not intent_counts:
            dominant = "generic"
        else:
            dominant = sorted(intent_counts.items(), key=lambda kv: kv[1], reverse=True)[0][0]

        working_obj = state.get("working_memory")
        working = working_obj if isinstance(working_obj, dict) else {}
        goal = str(working.get("current_goal", "respond directly and track session context")).strip()

        symbolic_obj = state.get("symbolic_memory")
        symbolic = symbolic_obj if isinstance(symbolic_obj, dict) else {}

        return (
            "Insight summary: dominant_intent="
            f"{dominant}; active_goal={goal}; symbolic_entries={len(symbolic)}; "
            "recommended_control=prioritize continuity-safe recall before creative expansion."
        )

    def _node_csg(self, turn_state: Dict[str, Any]) -> Dict[str, Any]:
        user_text = str(turn_state.get("user_text", "")).strip()
        state = turn_state.get("evolved_state")
        history = turn_state.get("history")

        if not isinstance(state, dict):
            state = self._state
        if not isinstance(history, list):
            history = []

        state_json = json.dumps(state, ensure_ascii=True)
        hierarchy_json = self._memory_hierarchy_json(state)
        symbolic_json = json.dumps(state.get("symbolic_memory", {}), ensure_ascii=True)
        insight = str(turn_state.get("insight_summary", "")).strip()

        messages: List[Any] = [
            self._SystemMessage(content=self.evolved_system),
            self._SystemMessage(
                content=(
                    "Current internal state (JSON):\n"
                    f"{state_json}\n"
                    "Use this state to preserve continuity."
                )
            ),
            self._SystemMessage(
                content=(
                    "Memory hierarchy snapshot (JSON):\n"
                    f"{hierarchy_json}\n"
                    "Use sensory memory for immediate context, working memory for active goals, "
                    "episodic memory for session continuity, and symbolic memory for exact recall."
                )
            ),
            self._SystemMessage(
                content=(
                    "Explicit symbolic memory extracted from prior user turns (JSON):\n"
                    f"{symbolic_json}\n"
                    "When asked recall questions, prefer this memory before guessing."
                )
            ),
        ]

        if insight:
            messages.append(
                self._SystemMessage(
                    content=(
                        "Latest MMIE insight summary:\n"
                        f"{insight}\n"
                        "Use it to reduce redundancy and preserve conceptual coherence."
                    )
                )
            )

        for item in history:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role", "")).strip().lower()
            content = str(item.get("content", "")).strip()
            if not content:
                continue
            if role == "user":
                messages.append(self._HumanMessage(content=content))
            elif role == "assistant":
                messages.append(self._AIMessage(content=content))

        messages.append(self._HumanMessage(content=user_text))
        model_answer = self._invoke_llm(messages)

        return {"model_answer": model_answer}

    def _node_mmie(self, turn_state: Dict[str, Any]) -> Dict[str, Any]:
        state = turn_state.get("evolved_state")
        history = turn_state.get("history")
        user_text = str(turn_state.get("user_text", "")).strip()
        model_answer = str(turn_state.get("model_answer", "")).strip()

        if not isinstance(state, dict):
            state = self._state
        if not isinstance(history, list):
            history = []

        insight_summary = self._build_insight_summary(state)
        prior_turns = len(history) // 2
        override = deterministic_evolved_override(user_text, state, prior_turns)

        candidate_answer = override if override is not None else model_answer

        return {
            "insight_summary": insight_summary,
            "candidate_answer": candidate_answer,
        }

    def _node_ecc(self, turn_state: Dict[str, Any]) -> Dict[str, Any]:
        history = turn_state.get("history")
        if not isinstance(history, list):
            history = []

        candidate = str(turn_state.get("candidate_answer", "")).strip()
        if not candidate:
            candidate = str(turn_state.get("model_answer", "")).strip()

        final_answer = enforce_evolved_format(candidate, history)
        return {"final_answer": final_answer}

    def respond(self, user_text: str) -> str:
        prepared = user_text.strip()
        if not prepared:
            return "[error] empty user input"

        turn_state = {
            "user_text": prepared,
            "evolved_state": self._state,
            "history": self._history,
            "insight_summary": str(self._state.get("latest_insight_summary", "")),
            "model_answer": "",
            "candidate_answer": "",
            "final_answer": "",
        }

        result = self._graph.invoke(turn_state)
        answer = str(result.get("final_answer", "")).strip() or "[error] evolved returned an empty response"

        self._history.append({"role": "user", "content": prepared})
        self._history.append({"role": "assistant", "content": answer})
        self._history = trim_history(self._history, self.history_turns)

        update_evolved_state(self._state, prepared, answer)
        insight = str(result.get("insight_summary", "")).strip()
        if insight:
            self._state["latest_insight_summary"] = insight

        return answer
