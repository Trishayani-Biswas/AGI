from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
import random
import statistics
from typing import Dict, List

from .config import BioConstraints
from .entities import ALLOWED_ACTIONS, Agent, Decision, Genome, WorldState
from .world import advance_world, apply_action, metabolize


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


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


@dataclass(frozen=True)
class EpisodeCondition:
    world_difficulty: float
    shock_probability: float


@dataclass(frozen=True)
class GateThresholds:
    survival_margin: float = 0.02
    recovery_margin: float = 0.03
    consistency_margin: float = 0.02
    metacognitive_margin: float = 0.01
    temporal_continuity_margin: float = 0.01
    consciousness_margin: float = 0.01


@dataclass(frozen=True)
class PersistentAgiConfig:
    seed: int = 42
    days_per_episode: int = 240
    train_episodes: int = 16
    eval_episodes: int = 8
    learning_rate: float = 0.22
    train_condition: EpisodeCondition = field(
        default_factory=lambda: EpisodeCondition(world_difficulty=1.15, shock_probability=0.012)
    )
    eval_condition: EpisodeCondition = field(
        default_factory=lambda: EpisodeCondition(world_difficulty=1.45, shock_probability=0.03)
    )
    gate: GateThresholds = field(default_factory=GateThresholds)
    output_dir: Path = Path("outputs/persistent_agi")
    outer_outputs_dir: Path = Path("outputs")
    recovery_window_days: int = 8
    consciousness_stack_enabled: bool = True
    consciousness_memory_size: int = 64
    strategy_revision_rate: float = 0.65
    strategy_delta_clip: float = 0.12
    strategy_bias_decay: float = 0.012
    exploration_delta_clip: float = 0.015
    consciousness_bias_scale: float = 0.25
    consciousness_bias_clip: float = 0.08
    consciousness_update_rate: float = 0.22
    consciousness_contradiction_gain: float = 0.4


@dataclass
class StrategyState:
    action_bias: Dict[str, float]
    exploration_rate: float

    @staticmethod
    def neutral() -> "StrategyState":
        return StrategyState(
            action_bias={action: 0.0 for action in ALLOWED_ACTIONS},
            exploration_rate=0.12,
        )

    def clone(self) -> "StrategyState":
        return StrategyState(action_bias=dict(self.action_bias), exploration_rate=float(self.exploration_rate))

    def to_dict(self) -> Dict[str, object]:
        return {
            "action_bias": {k: round(v, 6) for k, v in self.action_bias.items()},
            "exploration_rate": round(self.exploration_rate, 6),
        }


@dataclass
class MindState:
    genome: Genome
    action_values: Dict[str, float]
    known_innovations: List[str]

    def clone(self) -> "MindState":
        return MindState(
            genome=Genome(
                risk_tolerance=self.genome.risk_tolerance,
                social_drive=self.genome.social_drive,
                exploration_drive=self.genome.exploration_drive,
                thriftiness=self.genome.thriftiness,
            ),
            action_values=dict(self.action_values),
            known_innovations=list(self.known_innovations),
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "genome": {
                "risk_tolerance": round(self.genome.risk_tolerance, 6),
                "social_drive": round(self.genome.social_drive, 6),
                "exploration_drive": round(self.genome.exploration_drive, 6),
                "thriftiness": round(self.genome.thriftiness, 6),
            },
            "action_values": {k: round(v, 6) for k, v in self.action_values.items()},
            "known_innovations": sorted(set(self.known_innovations)),
        }


@dataclass
class SelfModelState:
    extinction_risk: float
    dehydration_risk: float
    starvation_risk: float
    recovery_confidence: float
    strategy_confidence: float
    episode_count: int = 0
    reflections: List[str] = field(default_factory=list)
    contradiction_safe_but_died: int = 0
    contradiction_risky_but_thrived: int = 0

    @staticmethod
    def neutral() -> "SelfModelState":
        return SelfModelState(
            extinction_risk=0.32,
            dehydration_risk=0.28,
            starvation_risk=0.22,
            recovery_confidence=0.55,
            strategy_confidence=0.5,
        )

    def clone(self) -> "SelfModelState":
        return SelfModelState(
            extinction_risk=self.extinction_risk,
            dehydration_risk=self.dehydration_risk,
            starvation_risk=self.starvation_risk,
            recovery_confidence=self.recovery_confidence,
            strategy_confidence=self.strategy_confidence,
            episode_count=self.episode_count,
            reflections=list(self.reflections),
            contradiction_safe_but_died=self.contradiction_safe_but_died,
            contradiction_risky_but_thrived=self.contradiction_risky_but_thrived,
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "extinction_risk": round(self.extinction_risk, 6),
            "dehydration_risk": round(self.dehydration_risk, 6),
            "starvation_risk": round(self.starvation_risk, 6),
            "recovery_confidence": round(self.recovery_confidence, 6),
            "strategy_confidence": round(self.strategy_confidence, 6),
            "episode_count": int(self.episode_count),
            "reflections": list(self.reflections[-16:]),
            "contradiction_safe_but_died": int(self.contradiction_safe_but_died),
            "contradiction_risky_but_thrived": int(self.contradiction_risky_but_thrived),
            "contradiction_total": int(
                self.contradiction_safe_but_died + self.contradiction_risky_but_thrived
            ),
        }

    def predict(
        self,
        *,
        strategy: StrategyState,
        condition: EpisodeCondition,
    ) -> Dict[str, float]:
        difficulty_pressure = max(0.0, condition.world_difficulty - 1.0)
        shock_pressure = _clamp(condition.shock_probability * max(0.6, condition.world_difficulty), 0.0, 0.5)

        hydration_bias = (
            float(strategy.action_bias.get("search_water", 0.0))
            + (0.7 * float(strategy.action_bias.get("drink_reserve", 0.0)))
        )
        nutrition_bias = (
            float(strategy.action_bias.get("search_food", 0.0))
            + (0.6 * float(strategy.action_bias.get("eat_reserve", 0.0)))
        )
        resilience_bias = (
            float(strategy.action_bias.get("rest", 0.0))
            + float(strategy.action_bias.get("build_shelter", 0.0))
            + (0.6 * float(strategy.action_bias.get("cooperate", 0.0)))
        )

        predicted_extinction = _clamp(
            self.extinction_risk
            + (0.17 * difficulty_pressure)
            + (0.62 * shock_pressure)
            + (0.08 * strategy.exploration_rate)
            - (0.04 * resilience_bias),
            0.01,
            0.99,
        )
        predicted_dehydration = _clamp(
            self.dehydration_risk
            + (0.14 * difficulty_pressure)
            + (0.06 * strategy.exploration_rate)
            - (0.045 * hydration_bias),
            0.01,
            0.99,
        )
        predicted_starvation = _clamp(
            self.starvation_risk
            + (0.12 * difficulty_pressure)
            + (0.05 * strategy.exploration_rate)
            - (0.043 * nutrition_bias),
            0.01,
            0.99,
        )
        predicted_recovery = _clamp(
            self.recovery_confidence
            + (0.05 * resilience_bias)
            - (0.38 * shock_pressure),
            0.01,
            0.99,
        )

        return {
            "extinction_risk": predicted_extinction,
            "dehydration_risk": predicted_dehydration,
            "starvation_risk": predicted_starvation,
            "recovery_confidence": predicted_recovery,
        }

    def update_from_outcome(
        self,
        *,
        episode: Dict[str, object],
        smoothing: float = 0.2,
    ) -> None:
        extinct = 1.0 if bool(episode.get("extinct", False)) else 0.0
        death_reason = str(episode.get("death_reason") or "")
        dehydration = 1.0 if death_reason == "dehydration" else 0.0
        starvation = 1.0 if death_reason == "starvation" else 0.0
        recovery = _safe_float(episode.get("shock_recovery_ratio")) or 0.0
        days_ratio = _safe_float(episode.get("days_ratio")) or 0.0
        predicted_extinction = _safe_float(episode.get("prediction_extinction_risk")) or 0.0

        smooth = _clamp(smoothing, 0.01, 0.9)

        self.extinction_risk = _clamp(((1.0 - smooth) * self.extinction_risk) + (smooth * extinct), 0.01, 0.99)
        self.dehydration_risk = _clamp(((1.0 - smooth) * self.dehydration_risk) + (smooth * dehydration), 0.01, 0.99)
        self.starvation_risk = _clamp(((1.0 - smooth) * self.starvation_risk) + (smooth * starvation), 0.01, 0.99)
        self.recovery_confidence = _clamp(
            ((1.0 - smooth) * self.recovery_confidence) + (smooth * recovery),
            0.01,
            0.99,
        )

        mean_reward = _safe_float(episode.get("mean_reward")) or 0.0
        reward_score = _clamp((mean_reward + 2.0) / 8.0, 0.0, 1.0)
        self.strategy_confidence = _clamp(
            ((1.0 - smooth) * self.strategy_confidence) + (smooth * ((0.7 * days_ratio) + (0.3 * reward_score))),
            0.01,
            0.99,
        )

        contradiction_safe_but_died = extinct >= 0.5 and predicted_extinction <= 0.35
        contradiction_risky_but_thrived = extinct < 0.5 and days_ratio >= 0.98 and predicted_extinction >= 0.65

        if contradiction_safe_but_died:
            self.contradiction_safe_but_died += 1
            self.strategy_confidence = _clamp(self.strategy_confidence - 0.04, 0.01, 0.99)

        if contradiction_risky_but_thrived:
            self.contradiction_risky_but_thrived += 1
            self.strategy_confidence = _clamp(self.strategy_confidence + 0.015, 0.01, 0.99)

        self.episode_count += 1

    def record_reflection(self, reflection: str) -> None:
        cleaned = reflection.strip()
        if not cleaned:
            return
        self.reflections.append(cleaned)
        if len(self.reflections) > 64:
            self.reflections = self.reflections[-64:]


@dataclass
class ConsciousnessMemoryState:
    identity_name: str = "persistent_agi"
    contradiction_salience: float = 0.2
    coherence_drive: float = 0.6
    survival_drive: float = 0.9
    exploration_drive: float = 0.3
    memory_size: int = 64
    autobiographical_memory: List[str] = field(default_factory=list)

    @staticmethod
    def neutral(memory_size: int = 64) -> "ConsciousnessMemoryState":
        return ConsciousnessMemoryState(memory_size=max(8, memory_size))

    def clone(self) -> "ConsciousnessMemoryState":
        return ConsciousnessMemoryState(
            identity_name=self.identity_name,
            contradiction_salience=self.contradiction_salience,
            coherence_drive=self.coherence_drive,
            survival_drive=self.survival_drive,
            exploration_drive=self.exploration_drive,
            memory_size=self.memory_size,
            autobiographical_memory=list(self.autobiographical_memory),
        )

    def to_dict(self) -> Dict[str, object]:
        return {
            "identity_name": self.identity_name,
            "contradiction_salience": round(self.contradiction_salience, 6),
            "coherence_drive": round(self.coherence_drive, 6),
            "survival_drive": round(self.survival_drive, 6),
            "exploration_drive": round(self.exploration_drive, 6),
            "memory_size": int(self.memory_size),
            "autobiographical_memory": list(self.autobiographical_memory[-20:]),
        }

    def remember_episode(
        self,
        episode: Dict[str, object],
        critique: Dict[str, object],
        *,
        update_rate: float = 0.35,
        contradiction_gain: float = 1.0,
    ) -> None:
        issues = critique.get("issues")
        if not isinstance(issues, list):
            issues = []

        rate = _clamp(update_rate, 0.05, 1.0)
        gain = _clamp(contradiction_gain, 0.1, 2.0)

        days_ratio = _safe_float(episode.get("days_ratio")) or 0.0
        reward = _safe_float(episode.get("mean_reward")) or 0.0
        contradiction_safe = bool(episode.get("contradiction_predicted_safe_but_died", False))
        contradiction_risky = bool(episode.get("contradiction_predicted_risky_but_thrived", False))
        contradiction_flag = contradiction_safe or contradiction_risky

        note = (
            f"ep={episode.get('episode_index')}"
            f" days={days_ratio:.3f}"
            f" reward={reward:.3f}"
            f" issues={','.join(str(item) for item in issues) if issues else 'none'}"
            f" contradiction={int(contradiction_flag)}"
        )
        self.autobiographical_memory.append(note)

        if len(self.autobiographical_memory) > self.memory_size:
            self.autobiographical_memory = self.autobiographical_memory[-self.memory_size :]

        contradiction_target = self.contradiction_salience
        coherence_target = self.coherence_drive
        exploration_target = self.exploration_drive

        if contradiction_flag:
            contradiction_target = _clamp(self.contradiction_salience + (0.08 * gain), 0.0, 1.0)
            coherence_target = _clamp(self.coherence_drive + (0.04 * gain), 0.0, 1.0)
            exploration_target = _clamp(self.exploration_drive - (0.03 * gain), 0.0, 1.0)
        else:
            contradiction_target = _clamp(self.contradiction_salience - 0.015, 0.0, 1.0)
            coherence_target = _clamp(self.coherence_drive + 0.005, 0.0, 1.0)
            if days_ratio > 0.98 and reward > 0.2:
                exploration_target = _clamp(self.exploration_drive + 0.01, 0.0, 1.0)

        survival_target = self.survival_drive
        if days_ratio < 0.7:
            survival_target = _clamp(self.survival_drive + (0.03 * gain), 0.0, 1.0)
        elif days_ratio > 0.98:
            survival_target = _clamp(self.survival_drive - 0.005, 0.0, 1.0)

        self.contradiction_salience = _clamp(
            ((1.0 - rate) * self.contradiction_salience) + (rate * contradiction_target),
            0.0,
            1.0,
        )
        self.coherence_drive = _clamp(
            ((1.0 - rate) * self.coherence_drive) + (rate * coherence_target),
            0.0,
            1.0,
        )
        self.exploration_drive = _clamp(
            ((1.0 - rate) * self.exploration_drive) + (rate * exploration_target),
            0.0,
            1.0,
        )
        self.survival_drive = _clamp(
            ((1.0 - rate) * self.survival_drive) + (rate * survival_target),
            0.0,
            1.0,
        )

    def retrieval_bias(self, *, scale: float = 1.0) -> Dict[str, float]:
        factor = _clamp(scale, 0.0, 2.0)
        survival_push = (self.survival_drive * 0.22) + (self.contradiction_salience * 0.16)
        coherence_push = self.coherence_drive * 0.14
        exploration_push = self.exploration_drive * 0.12

        return {
            "search_water": factor * survival_push,
            "search_food": factor * survival_push,
            "drink_reserve": factor * (survival_push * 0.65),
            "eat_reserve": factor * (survival_push * 0.6),
            "rest": factor * coherence_push,
            "build_shelter": factor * coherence_push,
            "cooperate": factor * (coherence_push * 0.5),
            "experiment": factor * (exploration_push - (self.contradiction_salience * 0.07)),
            "mate": factor * (-survival_push * 0.35),
        }


class PersistentAgiLab:
    """Hybrid outer+inner loop lab for persistent single-agent adaptation.

    Outer-loop priors are derived from best NEAT run summaries, then one persistent
    inner-loop mind is trained across episodes with self-critique and strategy revision.
    Promotion is gated on held-out survival, shock recovery, and consistency.
    """

    def __init__(self, config: PersistentAgiConfig) -> None:
        self.config = config
        self.bio = BioConstraints()
        self._base_rng = random.Random(config.seed)
        self._outer_prior = self._derive_outer_prior(config.outer_outputs_dir)

    def run(self) -> Dict[str, object]:
        output_dir = self.config.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        initial_mind = self._build_initial_mind()
        initial_self_model = SelfModelState.neutral()
        initial_consciousness = ConsciousnessMemoryState.neutral(
            memory_size=self.config.consciousness_memory_size,
        )
        baseline_mind = initial_mind.clone()
        candidate_mind = initial_mind.clone()
        baseline_self_model = initial_self_model.clone()
        candidate_self_model = initial_self_model.clone()
        baseline_consciousness = initial_consciousness.clone()
        candidate_consciousness = initial_consciousness.clone()

        baseline_strategy = self._build_strategy_from_outer_prior().clone()
        candidate_strategy = baseline_strategy.clone()

        train_records: List[Dict[str, object]] = []
        critique_records: List[Dict[str, object]] = []

        for episode_index in range(self.config.train_episodes):
            episode_seed = self.config.seed + (episode_index * 101)
            result = self._run_episode(
                episode_index=episode_index,
                split="train",
                seed=episode_seed,
                condition=self.config.train_condition,
                strategy=candidate_strategy,
                mind=candidate_mind,
                self_model=candidate_self_model,
                consciousness_state=candidate_consciousness,
                allow_learning=True,
                update_mind=True,
                update_self_model=True,
                update_consciousness=True,
            )
            train_records.append(result)

            critique = self._self_critique(result)
            self._revise_strategy(candidate_strategy, critique)
            candidate_self_model.record_reflection(str(critique.get("reflection_note", "")))
            if self.config.consciousness_stack_enabled:
                candidate_consciousness.remember_episode(
                    result,
                    critique,
                    update_rate=self.config.consciousness_update_rate,
                    contradiction_gain=self.config.consciousness_contradiction_gain,
                )
            critique_records.append(
                {
                    "episode_index": episode_index,
                    "seed": episode_seed,
                    "critique": critique,
                    "strategy_after": candidate_strategy.to_dict(),
                    "self_model_after": candidate_self_model.to_dict(),
                    "consciousness_after": candidate_consciousness.to_dict(),
                }
            )

        baseline_eval_records: List[Dict[str, object]] = []
        candidate_eval_records: List[Dict[str, object]] = []

        for eval_index in range(self.config.eval_episodes):
            eval_seed = self.config.seed + 100_000 + (eval_index * 137)
            baseline_eval_records.append(
                self._run_episode(
                    episode_index=eval_index,
                    split="heldout_baseline",
                    seed=eval_seed,
                    condition=self.config.eval_condition,
                    strategy=baseline_strategy,
                    mind=baseline_mind,
                    self_model=baseline_self_model,
                    consciousness_state=baseline_consciousness,
                    allow_learning=False,
                    update_mind=False,
                    update_self_model=False,
                    update_consciousness=False,
                )
            )
            candidate_eval_records.append(
                self._run_episode(
                    episode_index=eval_index,
                    split="heldout_candidate",
                    seed=eval_seed,
                    condition=self.config.eval_condition,
                    strategy=candidate_strategy,
                    mind=candidate_mind,
                    self_model=candidate_self_model,
                    consciousness_state=candidate_consciousness,
                    allow_learning=False,
                    update_mind=False,
                    update_self_model=False,
                    update_consciousness=False,
                )
            )

        baseline_eval = self._aggregate_eval_metrics(baseline_eval_records)
        candidate_eval = self._aggregate_eval_metrics(candidate_eval_records)
        gate_report = self._evaluate_gate(baseline_eval, candidate_eval)

        selected_strategy = candidate_strategy if gate_report["promoted"] else baseline_strategy
        selected_mind = candidate_mind if gate_report["promoted"] else baseline_mind
        selected_self_model = candidate_self_model if gate_report["promoted"] else baseline_self_model
        selected_consciousness = (
            candidate_consciousness if gate_report["promoted"] else baseline_consciousness
        )

        selected_strategy_path = output_dir / "selected_strategy.json"
        selected_strategy_path.write_text(
            json.dumps(
                {
                    "generated_at_utc": _utc_now(),
                    "promoted": gate_report["promoted"],
                    "strategy": selected_strategy.to_dict(),
                    "mind": selected_mind.to_dict(),
                    "self_model": selected_self_model.to_dict(),
                    "consciousness": selected_consciousness.to_dict(),
                },
                indent=2,
                ensure_ascii=True,
            )
            + "\n",
            encoding="utf-8",
        )

        train_log_path = output_dir / "train_episode_log.jsonl"
        with train_log_path.open("w", encoding="utf-8") as fp:
            for row in train_records:
                fp.write(json.dumps(row, ensure_ascii=True) + "\n")

        critique_log_path = output_dir / "self_critique_log.jsonl"
        with critique_log_path.open("w", encoding="utf-8") as fp:
            for row in critique_records:
                fp.write(json.dumps(row, ensure_ascii=True) + "\n")

        heldout_log_path = output_dir / "heldout_eval_log.jsonl"
        with heldout_log_path.open("w", encoding="utf-8") as fp:
            for row in baseline_eval_records + candidate_eval_records:
                fp.write(json.dumps(row, ensure_ascii=True) + "\n")

        train_temporal = self._compute_temporal_continuity(train_records)

        summary = {
            "generated_at_utc": _utc_now(),
            "mode": "persistent_inner_loop",
            "outer_loop_prior": self._outer_prior,
            "config": {
                "seed": self.config.seed,
                "days_per_episode": self.config.days_per_episode,
                "train_episodes": self.config.train_episodes,
                "eval_episodes": self.config.eval_episodes,
                "learning_rate": self.config.learning_rate,
                "train_condition": {
                    "world_difficulty": self.config.train_condition.world_difficulty,
                    "shock_probability": self.config.train_condition.shock_probability,
                },
                "eval_condition": {
                    "world_difficulty": self.config.eval_condition.world_difficulty,
                    "shock_probability": self.config.eval_condition.shock_probability,
                },
                "gate": {
                    "survival_margin": self.config.gate.survival_margin,
                    "recovery_margin": self.config.gate.recovery_margin,
                    "consistency_margin": self.config.gate.consistency_margin,
                    "metacognitive_margin": self.config.gate.metacognitive_margin,
                    "temporal_continuity_margin": self.config.gate.temporal_continuity_margin,
                    "consciousness_margin": self.config.gate.consciousness_margin,
                },
                "consciousness_stack_enabled": self.config.consciousness_stack_enabled,
                "consciousness_memory_size": self.config.consciousness_memory_size,
                "strategy_revision_rate": self.config.strategy_revision_rate,
                "strategy_delta_clip": self.config.strategy_delta_clip,
                "strategy_bias_decay": self.config.strategy_bias_decay,
                "exploration_delta_clip": self.config.exploration_delta_clip,
                "consciousness_bias_scale": self.config.consciousness_bias_scale,
                "consciousness_bias_clip": self.config.consciousness_bias_clip,
                "consciousness_update_rate": self.config.consciousness_update_rate,
                "consciousness_contradiction_gain": self.config.consciousness_contradiction_gain,
            },
            "train_summary": {
                "episodes": len(train_records),
                "mean_days_ratio": round(self._mean_from_records(train_records, "days_ratio"), 6),
                "extinction_rate": round(self._mean_from_records(train_records, "extinct", bool_to_float=True), 6),
                "mean_shock_recovery_ratio": round(
                    self._mean_from_records(train_records, "shock_recovery_ratio"),
                    6,
                ),
                "mean_prediction_brier": round(self._mean_from_records(train_records, "prediction_brier"), 6),
                "metacognitive_score": round(
                    _clamp(1.0 - self._mean_from_records(train_records, "prediction_brier"), 0.0, 1.0),
                    6,
                ),
                "mean_introspective_coherence_score": round(
                    self._mean_from_records(train_records, "introspective_coherence_score"),
                    6,
                ),
                "temporal_self_continuity_score": round(train_temporal["temporal_self_continuity_score"], 6),
                "action_policy_continuity_score": round(train_temporal["action_policy_continuity_score"], 6),
                "self_projection_continuity_score": round(train_temporal["self_projection_continuity_score"], 6),
                "mean_consciousness_proxy_score": round(
                    self._mean_from_records(train_records, "consciousness_proxy_score"),
                    6,
                ),
                "contradiction_safe_but_died_count": int(
                    candidate_self_model.contradiction_safe_but_died
                ),
                "contradiction_risky_but_thrived_count": int(
                    candidate_self_model.contradiction_risky_but_thrived
                ),
            },
            "evaluation": {
                "baseline": baseline_eval,
                "candidate": candidate_eval,
                "gate": gate_report,
            },
            "self_models": {
                "baseline": baseline_self_model.to_dict(),
                "candidate": candidate_self_model.to_dict(),
                "selected": selected_self_model.to_dict(),
            },
            "consciousness_states": {
                "baseline": baseline_consciousness.to_dict(),
                "candidate": candidate_consciousness.to_dict(),
                "selected": selected_consciousness.to_dict(),
            },
            "artifacts": {
                "train_log_path": str(train_log_path),
                "critique_log_path": str(critique_log_path),
                "heldout_log_path": str(heldout_log_path),
                "selected_strategy_path": str(selected_strategy_path),
            },
        }

        summary_path = output_dir / "summary.json"
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        return summary

    def _build_initial_mind(self) -> MindState:
        rng = random.Random(self.config.seed + 17)
        genome = Genome.random(rng)
        return MindState(
            genome=genome,
            action_values={action: 0.0 for action in ALLOWED_ACTIONS},
            known_innovations=[],
        )

    def _build_strategy_from_outer_prior(self) -> StrategyState:
        strategy = StrategyState.neutral()

        world_difficulty = _safe_float(self._outer_prior.get("world_difficulty")) or 1.0
        shock_probability = _safe_float(self._outer_prior.get("shock_probability")) or 0.0
        robustness_mean = _safe_float(self._outer_prior.get("robustness_mean_score")) or 0.0

        if world_difficulty >= 1.3:
            strategy.action_bias["search_water"] += 0.22
            strategy.action_bias["search_food"] += 0.22
            strategy.action_bias["experiment"] -= 0.08

        if shock_probability >= 0.015:
            strategy.action_bias["build_shelter"] += 0.24
            strategy.action_bias["rest"] += 0.18

        if robustness_mean >= 30_000.0:
            strategy.action_bias["cooperate"] += 0.05

        strategy.exploration_rate = _clamp(
            0.1 + (self._outer_prior.get("curriculum_enabled") is True) * 0.02,
            0.02,
            0.35,
        )
        return strategy

    def _derive_outer_prior(self, outputs_dir: Path) -> Dict[str, object]:
        if not outputs_dir.exists():
            return {
                "source": "none",
                "reason": "outputs directory missing",
            }

        best: Dict[str, object] | None = None
        for child in outputs_dir.iterdir():
            if not child.is_dir():
                continue
            summary = _load_json_dict(child / "summary.json")
            if not isinstance(summary, dict):
                continue
            if summary.get("framework") != "neat-python":
                continue

            robustness = _load_json_dict(child / "robustness.json") or {}
            mean_score = _safe_float(robustness.get("mean_score", summary.get("robustness_mean_score")))
            if mean_score is None:
                continue

            row = {
                "source": child.name,
                "robustness_mean_score": mean_score,
                "world_difficulty": _safe_float(summary.get("world_difficulty")),
                "shock_probability": _safe_float(summary.get("shock_probability")),
                "curriculum_enabled": bool(summary.get("curriculum_enabled", False)),
            }

            if best is None or float(row["robustness_mean_score"]) > float(best["robustness_mean_score"]):
                best = row

        if best is None:
            return {
                "source": "none",
                "reason": "no neat summaries found",
            }
        return best

    def _spawn_agent(self, mind: MindState) -> Agent:
        return Agent(
            id=1,
            sex="F",
            age_days=22 * 365,
            genome=Genome(
                risk_tolerance=mind.genome.risk_tolerance,
                social_drive=mind.genome.social_drive,
                exploration_drive=mind.genome.exploration_drive,
                thriftiness=mind.genome.thriftiness,
            ),
            water_store=5,
            food_store=5,
            action_values=dict(mind.action_values),
            known_innovations=set(mind.known_innovations),
        )

    def _run_episode(
        self,
        *,
        episode_index: int,
        split: str,
        seed: int,
        condition: EpisodeCondition,
        strategy: StrategyState,
        mind: MindState,
        self_model: SelfModelState,
        consciousness_state: ConsciousnessMemoryState,
        allow_learning: bool,
        update_mind: bool,
        update_self_model: bool,
        update_consciousness: bool,
    ) -> Dict[str, object]:
        rng = random.Random(seed)
        world = WorldState()
        agent = self._spawn_agent(mind)
        prediction = self_model.predict(strategy=strategy, condition=condition)

        shock_records: List[Dict[str, object]] = []
        action_counts: Dict[str, int] = {action: 0 for action in ALLOWED_ACTIONS}
        rewards: List[float] = []
        water_deprivation_trace: List[int] = []
        food_deprivation_trace: List[int] = []

        death_reason: str | None = None
        survived_days = 0

        for day in range(1, self.config.days_per_episode + 1):
            world.day = day
            advance_world(world, rng)
            self._apply_world_difficulty(world, condition.world_difficulty)

            shock = self._maybe_apply_shock(world, rng, condition)
            if shock is not None:
                shock_records.append(
                    {
                        "day": day,
                        "type": shock,
                        "pre_health": round(agent.health, 4),
                        "recovered": False,
                    }
                )

            metabolize(agent, world)
            water_deprivation_trace.append(agent.days_without_water)
            food_deprivation_trace.append(agent.days_without_food)

            death_reason = self._death_reason(agent)
            if death_reason is not None:
                survived_days = day
                break

            action = self._choose_action(
                agent=agent,
                world=world,
                strategy=strategy,
                consciousness_state=consciousness_state,
                rng=rng,
            )
            action_counts[action] += 1

            outcome = apply_action(
                agent=agent,
                decision=Decision(action=action, reason="persistent_policy", confidence=0.5),
                world=world,
                population=[agent],
                rng=rng,
                day=day,
                bio=self.bio,
            )

            reward = float(outcome.reward) + 0.18
            rewards.append(reward)
            if allow_learning:
                self._update_action_value(agent, action, reward)

            death_reason = self._death_reason(agent)
            if death_reason is not None:
                survived_days = day
                break

            self._update_shock_recovery(shock_records, day, agent.health)
            survived_days = day

        if death_reason is None:
            survived_days = self.config.days_per_episode

        if update_mind:
            mind.action_values = dict(agent.action_values)
            mind.known_innovations = sorted(set(agent.known_innovations))[:40]

        days_ratio = float(survived_days) / float(max(1, self.config.days_per_episode))
        shock_total = len(shock_records)
        shock_recovered = sum(1 for row in shock_records if bool(row.get("recovered", False)))
        shock_recovery_ratio = float(shock_recovered) / float(shock_total) if shock_total > 0 else 1.0

        actual_extinction = 1.0 if death_reason is not None else 0.0
        actual_dehydration = 1.0 if death_reason == "dehydration" else 0.0
        actual_starvation = 1.0 if death_reason == "starvation" else 0.0
        actual_recovery = shock_recovery_ratio

        prediction_brier = statistics.mean(
            [
                (prediction["extinction_risk"] - actual_extinction) ** 2,
                (prediction["dehydration_risk"] - actual_dehydration) ** 2,
                (prediction["starvation_risk"] - actual_starvation) ** 2,
                (prediction["recovery_confidence"] - actual_recovery) ** 2,
            ]
        )

        contradiction_safe_but_died = bool(actual_extinction >= 0.5 and prediction["extinction_risk"] <= 0.35)
        contradiction_risky_but_thrived = bool(
            actual_extinction < 0.5 and days_ratio >= 0.98 and prediction["extinction_risk"] >= 0.65
        )
        contradiction_flag = contradiction_safe_but_died or contradiction_risky_but_thrived

        introspective_coherence = _clamp(
            1.0 - ((0.62 * (1.0 if contradiction_flag else 0.0)) + (0.38 * prediction_brier)),
            0.0,
            1.0,
        )

        temporal_proxy = _clamp(
            1.0
            - abs((prediction["extinction_risk"] + prediction["dehydration_risk"]) - (actual_extinction + actual_dehydration)),
            0.0,
            1.0,
        )

        consciousness_proxy_score = _clamp(
            (0.38 * introspective_coherence)
            + (0.32 * _clamp(1.0 - prediction_brier, 0.0, 1.0))
            + (0.30 * temporal_proxy),
            0.0,
            1.0,
        )

        episode_payload = {
            "episode_index": episode_index,
            "split": split,
            "seed": seed,
            "world_difficulty": round(condition.world_difficulty, 6),
            "shock_probability": round(condition.shock_probability, 6),
            "survived_days": survived_days,
            "days_configured": self.config.days_per_episode,
            "days_ratio": round(days_ratio, 6),
            "extinct": bool(death_reason is not None),
            "death_reason": death_reason,
            "final_health": round(agent.health, 6),
            "final_water_store": agent.water_store,
            "final_food_store": agent.food_store,
            "mean_reward": round(statistics.mean(rewards), 6) if rewards else 0.0,
            "shock_count": shock_total,
            "shock_recovered": shock_recovered,
            "shock_recovery_ratio": round(shock_recovery_ratio, 6),
            "avg_days_without_water": round(statistics.mean(water_deprivation_trace), 6) if water_deprivation_trace else 0.0,
            "avg_days_without_food": round(statistics.mean(food_deprivation_trace), 6) if food_deprivation_trace else 0.0,
            "action_counts": action_counts,
            "strategy_snapshot": strategy.to_dict(),
            "prediction_extinction_risk": round(prediction["extinction_risk"], 6),
            "prediction_dehydration_risk": round(prediction["dehydration_risk"], 6),
            "prediction_starvation_risk": round(prediction["starvation_risk"], 6),
            "prediction_recovery_confidence": round(prediction["recovery_confidence"], 6),
            "prediction_brier": round(prediction_brier, 6),
            "contradiction_predicted_safe_but_died": contradiction_safe_but_died,
            "contradiction_predicted_risky_but_thrived": contradiction_risky_but_thrived,
            "introspective_coherence_score": round(introspective_coherence, 6),
            "consciousness_proxy_score": round(consciousness_proxy_score, 6),
        }

        if update_self_model:
            self_model.update_from_outcome(episode=episode_payload)
            episode_payload["self_model_snapshot"] = self_model.to_dict()

        else:
            episode_payload["self_model_snapshot"] = self_model.to_dict()

        if update_consciousness:
            episode_payload["consciousness_state_snapshot"] = consciousness_state.to_dict()
        else:
            episode_payload["consciousness_state_snapshot"] = consciousness_state.to_dict()

        return episode_payload

    def _apply_world_difficulty(self, world: WorldState, world_difficulty: float) -> None:
        pressure = max(0.0, world_difficulty - 1.0)
        world.water_abundance = _clamp(world.water_abundance - (0.006 * pressure), 0.05, 1.0)
        world.food_abundance = _clamp(world.food_abundance - (0.006 * pressure), 0.05, 1.0)

    def _maybe_apply_shock(
        self,
        world: WorldState,
        rng: random.Random,
        condition: EpisodeCondition,
    ) -> str | None:
        shock_prob = _clamp(condition.shock_probability * max(0.6, condition.world_difficulty), 0.0, 0.45)
        if rng.random() >= shock_prob:
            return None

        shock = rng.choice(["drought", "crop_blight", "cold_storm", "disease_wave"])
        if shock == "drought":
            world.weather = "dry"
            world.water_abundance = _clamp(world.water_abundance - 0.3, 0.05, 1.0)
            world.food_abundance = _clamp(world.food_abundance - 0.1, 0.05, 1.0)
        elif shock == "crop_blight":
            world.food_abundance = _clamp(world.food_abundance - 0.35, 0.05, 1.0)
            world.health_regen_bonus = _clamp(world.health_regen_bonus - 0.3, -1.0, 1.5)
        elif shock == "cold_storm":
            world.weather = "rainy"
            world.shelter_tech = _clamp(world.shelter_tech - 0.1, 0.0, 1.2)
            world.health_regen_bonus = _clamp(world.health_regen_bonus - 0.25, -1.0, 1.5)
        else:
            world.health_regen_bonus = _clamp(world.health_regen_bonus - 0.35, -1.0, 1.5)
            world.survival_buffer = _clamp(world.survival_buffer - 0.08, 0.0, 1.2)

        return shock

    def _update_shock_recovery(
        self,
        shock_records: List[Dict[str, object]],
        day: int,
        health: float,
    ) -> None:
        for row in shock_records:
            if bool(row.get("recovered", False)):
                continue
            shock_day = int(row.get("day", 0))
            if day - shock_day > self.config.recovery_window_days:
                continue
            pre_health = _safe_float(row.get("pre_health")) or 0.0
            if health >= max(5.0, pre_health - 1.5):
                row["recovered"] = True

    def _choose_action(
        self,
        *,
        agent: Agent,
        world: WorldState,
        strategy: StrategyState,
        consciousness_state: ConsciousnessMemoryState,
        rng: random.Random,
    ) -> str:
        if agent.days_without_water >= 2:
            return "drink_reserve" if agent.water_store > 0 else "search_water"
        if agent.days_without_food >= 18:
            return "eat_reserve" if agent.food_store > 0 else "search_food"

        if rng.random() < strategy.exploration_rate:
            return rng.choice(ALLOWED_ACTIONS)

        scores: Dict[str, float] = {}
        if self.config.consciousness_stack_enabled:
            raw_bias = consciousness_state.retrieval_bias(scale=self.config.consciousness_bias_scale)
            consciousness_bias = {
                action: _clamp(
                    float(raw_bias.get(action, 0.0)),
                    -self.config.consciousness_bias_clip,
                    self.config.consciousness_bias_clip,
                )
                for action in ALLOWED_ACTIONS
            }
        else:
            consciousness_bias = {action: 0.0 for action in ALLOWED_ACTIONS}
        for action in ALLOWED_ACTIONS:
            base = float(agent.action_values.get(action, 0.0)) + float(strategy.action_bias.get(action, 0.0))
            base += float(consciousness_bias.get(action, 0.0))
            survival_push = 0.0

            if action == "search_water":
                survival_push += max(0.0, 4.0 - float(agent.water_store)) * 1.35
                survival_push += float(agent.days_without_water) * 1.2
                survival_push += (1.0 - world.water_abundance) * 0.8

            if action == "search_food":
                survival_push += max(0.0, 4.0 - float(agent.food_store)) * 1.2
                survival_push += (float(agent.days_without_food) / 3.0) * 1.1
                survival_push += (1.0 - world.food_abundance) * 0.7

            if action == "drink_reserve" and agent.water_store > 0 and agent.days_without_water > 0:
                survival_push += 1.4

            if action == "eat_reserve" and agent.food_store > 0 and agent.days_without_food > 0:
                survival_push += 1.2

            if action == "rest":
                if agent.health < 70.0:
                    survival_push += 0.8
                if world.health_regen_bonus < 0.0:
                    survival_push += 0.5

            if action == "build_shelter":
                if world.weather in {"rainy", "dry"}:
                    survival_push += 0.45
                if world.shelter_tech < 0.3:
                    survival_push += 0.3

            if action == "mate" and (agent.water_store < 4 or agent.food_store < 4):
                survival_push -= 1.8

            if action == "experiment" and (agent.water_store < 5 or agent.food_store < 5):
                survival_push -= 1.2

            scores[action] = base + survival_push + rng.uniform(-0.03, 0.03)

        best_score = max(scores.values())
        best_actions = [action for action, score in scores.items() if abs(score - best_score) < 1e-9]
        return rng.choice(best_actions)

    def _update_action_value(self, agent: Agent, action: str, reward: float) -> None:
        old = float(agent.action_values.get(action, 0.0))
        updated = old + (self.config.learning_rate * (reward - old))
        agent.action_values[action] = _clamp(updated, -12.0, 12.0)

    def _death_reason(self, agent: Agent) -> str | None:
        if agent.health <= 0.0:
            return "health_collapse"
        if agent.days_without_water >= self.bio.max_days_without_water:
            return "dehydration"
        if agent.days_without_food >= self.bio.max_days_without_food:
            return "starvation"
        if agent.age_days > self.bio.life_expectancy_days:
            years_over = (agent.age_days - self.bio.life_expectancy_days) / 365.0
            old_age_chance = min(0.7, 0.01 + (years_over * 0.06))
            if self._base_rng.random() < old_age_chance:
                return "old_age"
        return None

    def _self_critique(self, episode: Dict[str, object]) -> Dict[str, object]:
        adjustments = {action: 0.0 for action in ALLOWED_ACTIONS}
        issues: List[str] = []

        extinct = bool(episode.get("extinct", False))
        death_reason = str(episode.get("death_reason") or "")
        avg_without_water = _safe_float(episode.get("avg_days_without_water")) or 0.0
        avg_without_food = _safe_float(episode.get("avg_days_without_food")) or 0.0
        shock_recovery = _safe_float(episode.get("shock_recovery_ratio")) or 0.0
        mean_reward = _safe_float(episode.get("mean_reward")) or 0.0
        prediction_brier = _safe_float(episode.get("prediction_brier")) or 0.0
        predicted_extinction = _safe_float(episode.get("prediction_extinction_risk")) or 0.0

        if death_reason == "dehydration" or avg_without_water >= 0.9:
            issues.append("hydration_risk")
            adjustments["search_water"] += 0.32
            adjustments["drink_reserve"] += 0.2
            adjustments["experiment"] -= 0.08

        if death_reason == "starvation" or avg_without_food >= 7.0:
            issues.append("nutrition_risk")
            adjustments["search_food"] += 0.3
            adjustments["eat_reserve"] += 0.18
            adjustments["mate"] -= 0.08

        if shock_recovery < 0.55:
            issues.append("shock_recovery_weak")
            adjustments["rest"] += 0.24
            adjustments["build_shelter"] += 0.2

        if mean_reward < -0.25:
            issues.append("low_reward")
            adjustments["cooperate"] += 0.07

        if prediction_brier > 0.18:
            issues.append("metacognitive_mismatch")
            adjustments["rest"] += 0.12
            adjustments["build_shelter"] += 0.08

        if extinct and predicted_extinction < 0.3:
            issues.append("overconfidence")
            issues.append("contradiction_predicted_safe_but_died")
            adjustments["search_water"] += 0.1
            adjustments["search_food"] += 0.1

        if (not extinct) and predicted_extinction > 0.75:
            issues.append("underconfidence")
            issues.append("contradiction_predicted_risky_but_thrived")
            adjustments["experiment"] += 0.05

        if not extinct and shock_recovery >= 0.75 and mean_reward > 0.5:
            issues.append("stable_episode")
            adjustments["experiment"] += 0.05

        exploration_delta = 0.0
        if extinct:
            exploration_delta -= 0.02
        elif shock_recovery < 0.55:
            exploration_delta -= 0.01
        else:
            exploration_delta += 0.005

        if prediction_brier > 0.18:
            exploration_delta -= 0.005
        elif prediction_brier < 0.08 and not extinct:
            exploration_delta += 0.003

        reflection_note = " | ".join(issues) if issues else "stable_no_major_signal"

        return {
            "issues": issues,
            "adjustments": {k: round(v, 6) for k, v in adjustments.items()},
            "exploration_delta": round(exploration_delta, 6),
            "episode_days_ratio": episode.get("days_ratio"),
            "episode_mean_reward": episode.get("mean_reward"),
            "prediction_brier": round(prediction_brier, 6),
            "reflection_note": reflection_note,
        }

    def _revise_strategy(self, strategy: StrategyState, critique: Dict[str, object]) -> None:
        revision_rate = _clamp(self.config.strategy_revision_rate, 0.05, 1.0)
        delta_clip = _clamp(self.config.strategy_delta_clip, 0.01, 1.0)
        bias_decay = _clamp(self.config.strategy_bias_decay, 0.0, 0.2)

        adjustments = critique.get("adjustments")
        if isinstance(adjustments, dict):
            for action in ALLOWED_ACTIONS:
                delta = _safe_float(adjustments.get(action)) or 0.0
                bounded_delta = _clamp(delta, -delta_clip, delta_clip)
                revised = strategy.action_bias[action] + (revision_rate * bounded_delta)
                revised *= (1.0 - bias_decay)
                strategy.action_bias[action] = _clamp(revised, -3.0, 3.0)

        exploration_delta = _safe_float(critique.get("exploration_delta")) or 0.0
        exploration_clip = _clamp(self.config.exploration_delta_clip, 0.001, 0.08)
        bounded_exploration_delta = _clamp(exploration_delta, -exploration_clip, exploration_clip)
        strategy.exploration_rate = _clamp(
            strategy.exploration_rate + (revision_rate * bounded_exploration_delta),
            0.02,
            0.35,
        )

    def _aggregate_eval_metrics(self, records: List[Dict[str, object]]) -> Dict[str, object]:
        survival_values: List[float] = []
        recovery_values: List[float] = []
        prediction_brier_values: List[float] = []
        introspective_values: List[float] = []
        consciousness_proxy_values: List[float] = []
        temporal_continuity = self._compute_temporal_continuity(records)

        for row in records:
            days_ratio = _safe_float(row.get("days_ratio")) or 0.0
            final_health = _safe_float(row.get("final_health")) or 0.0
            health_norm = _clamp(final_health / 100.0, 0.0, 1.0)
            survival_values.append((0.75 * days_ratio) + (0.25 * health_norm))
            recovery_values.append(_safe_float(row.get("shock_recovery_ratio")) or 0.0)
            prediction_brier_values.append(_safe_float(row.get("prediction_brier")) or 0.0)
            introspective_values.append(_safe_float(row.get("introspective_coherence_score")) or 0.0)
            consciousness_proxy_values.append(_safe_float(row.get("consciousness_proxy_score")) or 0.0)

        survival_score = statistics.mean(survival_values) if survival_values else 0.0
        recovery_score = statistics.mean(recovery_values) if recovery_values else 0.0

        if len(survival_values) >= 2 and abs(survival_score) > 1e-9:
            cv = statistics.pstdev(survival_values) / abs(survival_score)
        else:
            cv = 0.0

        consistency = _clamp(1.0 - cv, 0.0, 1.0)
        extinction_rate = self._mean_from_records(records, "extinct", bool_to_float=True)
        mean_prediction_brier = statistics.mean(prediction_brier_values) if prediction_brier_values else 1.0
        metacognitive_score = _clamp(1.0 - mean_prediction_brier, 0.0, 1.0)
        introspective_coherence = statistics.mean(introspective_values) if introspective_values else 0.0
        consciousness_proxy = (
            statistics.mean(consciousness_proxy_values)
            if consciousness_proxy_values
            else _clamp(
                (0.35 * metacognitive_score)
                + (0.35 * temporal_continuity["temporal_self_continuity_score"])
                + (0.30 * introspective_coherence),
                0.0,
                1.0,
            )
        )

        return {
            "episodes": len(records),
            "survival_score": round(survival_score, 6),
            "shock_recovery_score": round(recovery_score, 6),
            "consistency_score": round(consistency, 6),
            "metacognitive_score": round(metacognitive_score, 6),
            "introspective_coherence_score": round(introspective_coherence, 6),
            "consciousness_proxy_score": round(consciousness_proxy, 6),
            "mean_prediction_brier": round(mean_prediction_brier, 6),
            "temporal_self_continuity_score": round(
                temporal_continuity["temporal_self_continuity_score"],
                6,
            ),
            "action_policy_continuity_score": round(
                temporal_continuity["action_policy_continuity_score"],
                6,
            ),
            "self_projection_continuity_score": round(
                temporal_continuity["self_projection_continuity_score"],
                6,
            ),
            "extinction_rate": round(extinction_rate, 6),
            "mean_days_ratio": round(self._mean_from_records(records, "days_ratio"), 6),
            "mean_final_health": round(self._mean_from_records(records, "final_health"), 6),
        }

    def _evaluate_gate(
        self,
        baseline_eval: Dict[str, object],
        candidate_eval: Dict[str, object],
    ) -> Dict[str, object]:
        baseline_survival = _safe_float(baseline_eval.get("survival_score")) or 0.0
        candidate_survival = _safe_float(candidate_eval.get("survival_score")) or 0.0

        baseline_recovery = _safe_float(baseline_eval.get("shock_recovery_score")) or 0.0
        candidate_recovery = _safe_float(candidate_eval.get("shock_recovery_score")) or 0.0

        baseline_consistency = _safe_float(baseline_eval.get("consistency_score")) or 0.0
        candidate_consistency = _safe_float(candidate_eval.get("consistency_score")) or 0.0

        baseline_metacognitive = _safe_float(baseline_eval.get("metacognitive_score")) or 0.0
        candidate_metacognitive = _safe_float(candidate_eval.get("metacognitive_score")) or 0.0

        baseline_temporal = _safe_float(baseline_eval.get("temporal_self_continuity_score")) or 0.0
        candidate_temporal = _safe_float(candidate_eval.get("temporal_self_continuity_score")) or 0.0

        baseline_consciousness = _safe_float(baseline_eval.get("consciousness_proxy_score")) or 0.0
        candidate_consciousness = _safe_float(candidate_eval.get("consciousness_proxy_score")) or 0.0

        survival_required = _clamp(baseline_survival + self.config.gate.survival_margin, 0.0, 1.0)
        recovery_required = _clamp(baseline_recovery + self.config.gate.recovery_margin, 0.0, 1.0)
        consistency_required = _clamp(baseline_consistency + self.config.gate.consistency_margin, 0.0, 1.0)
        metacognitive_required = _clamp(
            baseline_metacognitive + self.config.gate.metacognitive_margin,
            0.0,
            1.0,
        )
        temporal_required = _clamp(
            baseline_temporal + self.config.gate.temporal_continuity_margin,
            0.0,
            1.0,
        )
        consciousness_required = _clamp(
            baseline_consciousness + self.config.gate.consciousness_margin,
            0.0,
            1.0,
        )

        checks = [
            {
                "name": "survival",
                "baseline": round(baseline_survival, 6),
                "candidate": round(candidate_survival, 6),
                "required_min": round(survival_required, 6),
                "passed": candidate_survival >= survival_required,
            },
            {
                "name": "shock_recovery",
                "baseline": round(baseline_recovery, 6),
                "candidate": round(candidate_recovery, 6),
                "required_min": round(recovery_required, 6),
                "passed": candidate_recovery >= recovery_required,
            },
            {
                "name": "consistency",
                "baseline": round(baseline_consistency, 6),
                "candidate": round(candidate_consistency, 6),
                "required_min": round(consistency_required, 6),
                "passed": candidate_consistency >= consistency_required,
            },
            {
                "name": "metacognition",
                "baseline": round(baseline_metacognitive, 6),
                "candidate": round(candidate_metacognitive, 6),
                "required_min": round(metacognitive_required, 6),
                "passed": candidate_metacognitive >= metacognitive_required,
            },
            {
                "name": "temporal_self_continuity",
                "baseline": round(baseline_temporal, 6),
                "candidate": round(candidate_temporal, 6),
                "required_min": round(temporal_required, 6),
                "passed": candidate_temporal >= temporal_required,
            },
            {
                "name": "consciousness_proxy",
                "baseline": round(baseline_consciousness, 6),
                "candidate": round(candidate_consciousness, 6),
                "required_min": round(consciousness_required, 6),
                "passed": candidate_consciousness >= consciousness_required,
            },
        ]

        promoted = all(bool(row.get("passed", False)) for row in checks)
        return {
            "promoted": promoted,
            "checks": checks,
        }

    def _compute_temporal_continuity(self, records: List[Dict[str, object]]) -> Dict[str, float]:
        policy_vectors: List[Dict[str, float]] = []
        projection_vectors: List[Dict[str, float]] = []

        for row in records:
            action_counts = row.get("action_counts")
            if isinstance(action_counts, dict):
                policy_vectors.append(self._action_distribution(action_counts))

            projection_vectors.append(
                {
                    "extinction_risk": _safe_float(row.get("prediction_extinction_risk")) or 0.0,
                    "dehydration_risk": _safe_float(row.get("prediction_dehydration_risk")) or 0.0,
                    "starvation_risk": _safe_float(row.get("prediction_starvation_risk")) or 0.0,
                    "recovery_confidence": _safe_float(row.get("prediction_recovery_confidence")) or 0.0,
                }
            )

        action_policy_continuity = self._continuity_from_vectors(
            vectors=policy_vectors,
            distance_fn=self._distribution_distance,
        )
        self_projection_continuity = self._continuity_from_vectors(
            vectors=projection_vectors,
            distance_fn=self._projection_distance,
        )

        temporal_self_continuity = _clamp(
            (0.55 * action_policy_continuity) + (0.45 * self_projection_continuity),
            0.0,
            1.0,
        )

        return {
            "temporal_self_continuity_score": temporal_self_continuity,
            "action_policy_continuity_score": action_policy_continuity,
            "self_projection_continuity_score": self_projection_continuity,
        }

    def _action_distribution(self, action_counts: Dict[str, object]) -> Dict[str, float]:
        normalized: Dict[str, float] = {action: 0.0 for action in ALLOWED_ACTIONS}
        total = 0.0

        for action in ALLOWED_ACTIONS:
            raw = action_counts.get(action)
            amount = _safe_float(raw) or 0.0
            amount = max(0.0, amount)
            normalized[action] = amount
            total += amount

        if total <= 1e-9:
            return normalized

        for action in ALLOWED_ACTIONS:
            normalized[action] = normalized[action] / total
        return normalized

    def _distribution_distance(self, left: Dict[str, float], right: Dict[str, float]) -> float:
        total = 0.0
        for action in ALLOWED_ACTIONS:
            total += abs(float(left.get(action, 0.0)) - float(right.get(action, 0.0)))
        return _clamp(total / 2.0, 0.0, 1.0)

    def _projection_distance(self, left: Dict[str, float], right: Dict[str, float]) -> float:
        keys = ["extinction_risk", "dehydration_risk", "starvation_risk", "recovery_confidence"]
        distances = [abs(float(left.get(key, 0.0)) - float(right.get(key, 0.0))) for key in keys]
        return _clamp(statistics.mean(distances) if distances else 0.0, 0.0, 1.0)

    def _continuity_from_vectors(self, vectors: List[Dict[str, float]], distance_fn) -> float:
        if len(vectors) < 2:
            return 1.0

        distances: List[float] = []
        previous = vectors[0]
        for current in vectors[1:]:
            distances.append(_clamp(float(distance_fn(previous, current)), 0.0, 1.0))
            previous = current

        if not distances:
            return 1.0

        return _clamp(1.0 - statistics.mean(distances), 0.0, 1.0)

    def _mean_from_records(
        self,
        rows: List[Dict[str, object]],
        key: str,
        bool_to_float: bool = False,
    ) -> float:
        values: List[float] = []
        for row in rows:
            value = row.get(key)
            if bool_to_float and isinstance(value, bool):
                values.append(1.0 if value else 0.0)
                continue
            cast = _safe_float(value)
            if cast is None:
                continue
            values.append(cast)

        if not values:
            return 0.0
        return float(statistics.mean(values))
