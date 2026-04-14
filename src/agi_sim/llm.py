from __future__ import annotations

import json
import random
import re
from typing import Any, Dict, Iterable, Optional
from urllib import error, request

from .config import SimulationConfig
from .entities import ALLOWED_ACTIONS, Agent, Decision, WorldState


class DualLLMBrain:
    """Two-model decision flow: proposer model suggests, critic model challenges."""

    def __init__(self, config: SimulationConfig) -> None:
        self.config = config
        self._runtime_llm_disabled = False
        self._llm_failures = 0

    def decide(
        self,
        agent: Agent,
        world: WorldState,
        population: Iterable[Agent],
        rng: random.Random,
    ) -> Decision:
        heuristic = self._heuristic(agent, world, population, rng)
        if not self.config.llm_enabled or self._runtime_llm_disabled:
            return heuristic

        state_payload = self._state_payload(agent, world, population)
        proposal = self._ask_model(
            model=self.config.proposer_model,
            system_prompt=(
                "You are a primitive survival planner with no cultural knowledge. "
                "Goal: keep yourself alive and improve long-term lineage survival. "
                "Pick exactly one action from the allowed list. "
                "Return strict JSON only."
            ),
            user_payload={
                "task": "choose_action",
                "allowed_actions": ALLOWED_ACTIONS,
                "state": state_payload,
                "response_schema": {
                    "action": "string",
                    "confidence": "number between 0 and 1",
                    "reason": "short string",
                    "invention_hypothesis": "optional short string"
                },
            },
        )

        if not proposal:
            return heuristic

        proposal_action = proposal.get("action", "")
        if proposal_action not in ALLOWED_ACTIONS:
            return heuristic

        proposal_decision = Decision(
            action=proposal_action,
            confidence=self._safe_confidence(proposal.get("confidence"), fallback=0.55),
            reason=str(proposal.get("reason", "proposal"))[:200],
            invention_hypothesis=self._clean_hypothesis(proposal.get("invention_hypothesis")),
        )

        critique = self._ask_model(
            model=self.config.critic_model,
            system_prompt=(
                "You are a survival critic. Inspect the proposed action and either approve "
                "or replace it with a safer action if needed. Return strict JSON only."
            ),
            user_payload={
                "task": "critic_review",
                "allowed_actions": ALLOWED_ACTIONS,
                "state": state_payload,
                "proposal": {
                    "action": proposal_decision.action,
                    "confidence": proposal_decision.confidence,
                    "reason": proposal_decision.reason,
                    "invention_hypothesis": proposal_decision.invention_hypothesis,
                },
                "response_schema": {
                    "approved": "boolean",
                    "action": "string",
                    "confidence": "number between 0 and 1",
                    "reason": "short string",
                    "invention_hypothesis": "optional short string"
                },
            },
        )

        if not critique:
            return proposal_decision

        critic_action = critique.get("action", proposal_decision.action)
        if critic_action not in ALLOWED_ACTIONS:
            return proposal_decision

        approved = bool(critique.get("approved", False))
        if approved:
            return proposal_decision

        return Decision(
            action=critic_action,
            confidence=self._safe_confidence(critique.get("confidence"), fallback=0.5),
            reason=str(critique.get("reason", "critic override"))[:200],
            invention_hypothesis=self._clean_hypothesis(critique.get("invention_hypothesis")),
        )

    def _heuristic(
        self,
        agent: Agent,
        world: WorldState,
        population: Iterable[Agent],
        rng: random.Random,
    ) -> Decision:
        if agent.days_without_water > 0 and agent.water_store > 0:
            return Decision(action="drink_reserve", confidence=0.94, reason="recover from dehydration", invention_hypothesis=None)

        if agent.days_without_food > 0 and agent.food_store > 0:
            return Decision(action="eat_reserve", confidence=0.9, reason="recover from hunger", invention_hypothesis=None)

        if agent.days_without_water >= 2:
            action = "drink_reserve" if agent.water_store > 0 else "search_water"
            return Decision(action=action, confidence=0.95, reason="urgent hydration", invention_hypothesis=None)

        if agent.days_without_food >= 18:
            action = "eat_reserve" if agent.food_store > 0 else "search_food"
            return Decision(action=action, confidence=0.9, reason="urgent nutrition", invention_hypothesis=None)

        if agent.water_store <= 3 or agent.food_store <= 3:
            water_risk = (agent.days_without_water + 1.0) / 3.0
            food_risk = (agent.days_without_food + 1.0) / 21.0

            if agent.water_store <= 0 and agent.food_store <= 0:
                action = "search_water" if water_risk >= food_risk else "search_food"
                return Decision(action=action, confidence=0.88, reason="dual scarcity triage", invention_hypothesis=None)

            if agent.water_store <= 1:
                return Decision(action="search_water", confidence=0.86, reason="water exhausted", invention_hypothesis=None)

            if agent.food_store <= 1:
                return Decision(action="search_food", confidence=0.86, reason="food exhausted", invention_hypothesis=None)

            action = "search_water" if water_risk >= food_risk else "search_food"
            reason = "low reserves prioritize hydration" if action == "search_water" else "low reserves prioritize nutrition"
            return Decision(action=action, confidence=0.82, reason=reason, invention_hypothesis=None)

        if agent.health < 35.0:
            return Decision(action="rest", confidence=0.8, reason="recover health", invention_hypothesis=None)

        if (
            agent.pregnant_until is None
            and agent.health > 60.0
            and agent.water_store > 2
            and agent.food_store > 2
            and agent.is_adult(16 * 365)
        ):
            if rng.random() < 0.12 * agent.genome.social_drive:
                return Decision(action="mate", confidence=0.58, reason="lineage continuation", invention_hypothesis=None)

        adaptive_scores: Dict[str, float] = {}
        for action in ALLOWED_ACTIONS:
            learned = agent.action_values.get(action, 0.0)
            novelty_push = agent.genome.exploration_drive * (0.3 if action == "experiment" else 0.0)
            survival_push = 0.0
            if action == "search_water":
                survival_push += (1.0 - world.water_abundance) * 0.8
                survival_push += max(0.0, 4.0 - float(agent.water_store)) * 1.6
            if action == "search_food":
                survival_push += (1.0 - world.food_abundance) * 0.8
                survival_push += max(0.0, 4.0 - float(agent.food_store)) * 1.3
            if action in {"mate", "experiment"} and (agent.water_store < 2 or agent.food_store < 2):
                survival_push -= 2.0
            if (
                action == "mate"
                and agent.pregnant_until is None
                and agent.is_adult(16 * 365)
                and agent.health > 62.0
                and agent.water_store >= 5
                and agent.food_store >= 5
            ):
                survival_push += 1.6 + (agent.genome.social_drive * 1.4)
            if action == "experiment" and agent.water_store >= 6 and agent.food_store >= 6:
                survival_push += 0.9 + (agent.genome.exploration_drive * 0.8)
            if action == "rest" and agent.health < 80.0 and agent.water_store >= 3 and agent.food_store >= 3:
                survival_push += 0.6
            adaptive_scores[action] = learned + novelty_push + survival_push

        can_explore = (
            agent.water_store >= 4
            and agent.food_store >= 4
            and agent.days_without_water == 0
            and agent.days_without_food == 0
        )
        explore_probability = max(self.config.exploration_floor, agent.genome.exploration_drive * self.config.exploration_boost)
        if can_explore and rng.random() < explore_probability:
            action = rng.choice(ALLOWED_ACTIONS)
            hypothesis = "new pattern" if action == "experiment" else None
            return Decision(action=action, confidence=0.35, reason="exploration", invention_hypothesis=hypothesis)

        action = max(adaptive_scores, key=adaptive_scores.get)
        hypothesis = "resource preservation" if action == "experiment" else None
        return Decision(action=action, confidence=0.48, reason="heuristic policy", invention_hypothesis=hypothesis)

    def _state_payload(
        self,
        agent: Agent,
        world: WorldState,
        population: Iterable[Agent],
    ) -> Dict[str, Any]:
        alive = [p for p in population if p.alive]
        adults = sum(1 for p in alive if p.is_adult(16 * 365))
        pregnant = sum(1 for p in alive if p.pregnant_until is not None)
        return {
            "self": {
                "age_days": agent.age_days,
                "health": round(agent.health, 2),
                "days_without_water": agent.days_without_water,
                "days_without_food": agent.days_without_food,
                "water_store": agent.water_store,
                "food_store": agent.food_store,
                "shelter_skill": round(agent.shelter_skill, 3),
                "known_innovations": sorted(agent.known_innovations),
                "genome": {
                    "risk_tolerance": round(agent.genome.risk_tolerance, 3),
                    "social_drive": round(agent.genome.social_drive, 3),
                    "exploration_drive": round(agent.genome.exploration_drive, 3),
                    "thriftiness": round(agent.genome.thriftiness, 3),
                },
                "learned_action_values": {k: round(v, 3) for k, v in agent.action_values.items()},
            },
            "world": {
                "day": world.day,
                "weather": world.weather,
                "water_abundance": round(world.water_abundance, 3),
                "food_abundance": round(world.food_abundance, 3),
                "shelter_tech": round(world.shelter_tech, 3),
                "global_innovations": sorted(world.innovations),
            },
            "population": {
                "alive": len(alive),
                "adults": adults,
                "pregnant": pregnant,
            },
        }

    def _ask_model(self, model: str, system_prompt: str, user_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        payload = {
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload, ensure_ascii=True)},
            ],
            "options": {
                "temperature": 0.6,
                "top_p": 0.9,
            },
        }
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        req = request.Request(
            url=f"{self.config.ollama_url.rstrip('/')}/api/chat",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with request.urlopen(req, timeout=self.config.llm_timeout_s) as resp:
                raw = resp.read().decode("utf-8")
                parsed = json.loads(raw)
                text = parsed.get("message", {}).get("content", "")
                extracted = self._extract_json(text)
                if extracted is not None:
                    self._llm_failures = 0
                return extracted
        except (error.URLError, TimeoutError, json.JSONDecodeError, ValueError):
            self._llm_failures += 1
            if self._llm_failures >= 4:
                self._runtime_llm_disabled = True
            return None

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        text = text.strip()
        if not text:
            return None
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass

        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return None

        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    def _safe_confidence(self, value: Any, fallback: float) -> float:
        try:
            as_float = float(value)
        except (TypeError, ValueError):
            return fallback
        return max(0.0, min(1.0, as_float))

    def _clean_hypothesis(self, value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        return text[:120]
