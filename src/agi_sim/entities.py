from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Dict, Optional, Set


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


def _clamp_01(value: float) -> float:
    return max(0.0, min(1.0, value))


@dataclass
class Genome:
    risk_tolerance: float
    social_drive: float
    exploration_drive: float
    thriftiness: float

    @staticmethod
    def random(rng: random.Random) -> "Genome":
        return Genome(
            risk_tolerance=rng.uniform(0.2, 0.8),
            social_drive=rng.uniform(0.2, 0.8),
            exploration_drive=rng.uniform(0.2, 0.8),
            thriftiness=rng.uniform(0.2, 0.8),
        )

    @staticmethod
    def inherit(mother: "Genome", father: "Genome", rng: random.Random) -> "Genome":
        def blend(a: float, b: float) -> float:
            return _clamp_01(((a + b) / 2.0) + rng.gauss(0.0, 0.07))

        return Genome(
            risk_tolerance=blend(mother.risk_tolerance, father.risk_tolerance),
            social_drive=blend(mother.social_drive, father.social_drive),
            exploration_drive=blend(mother.exploration_drive, father.exploration_drive),
            thriftiness=blend(mother.thriftiness, father.thriftiness),
        )


@dataclass
class Agent:
    id: int
    sex: str
    age_days: int
    genome: Genome
    health: float = 100.0
    days_without_water: int = 0
    days_without_food: int = 0
    water_store: int = 1
    food_store: int = 1
    shelter_skill: float = 0.0
    alive: bool = True
    pregnant_until: Optional[int] = None
    co_parent_id: Optional[int] = None
    children: int = 0
    action_values: Dict[str, float] = field(default_factory=dict)
    known_innovations: Set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        if not self.action_values:
            self.action_values = {name: 0.0 for name in ALLOWED_ACTIONS}

    def is_adult(self, puberty_days: int) -> bool:
        return self.age_days >= puberty_days


@dataclass
class Decision:
    action: str
    reason: str
    confidence: float
    invention_hypothesis: Optional[str] = None


@dataclass
class ActionOutcome:
    reward: float
    summary: str
    event_type: str


@dataclass
class WorldState:
    day: int = 0
    weather: str = "mild"
    water_abundance: float = 0.55
    food_abundance: float = 0.55
    shelter_tech: float = 0.0
    health_regen_bonus: float = 0.0
    gather_bonus_water: float = 0.0
    gather_bonus_food: float = 0.0
    survival_buffer: float = 0.0
    innovations: Set[str] = field(default_factory=set)
    dynamic_innovation_effects: Dict[str, tuple[str, float]] = field(default_factory=dict)
