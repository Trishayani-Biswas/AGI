from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import os


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    lowered = raw.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return default


@dataclass(frozen=True)
class BioConstraints:
    max_days_without_water: int = 3
    max_days_without_food: int = 21
    life_expectancy_days: int = 60 * 365
    gestation_days: int = int(0.75 * 365)
    puberty_days: int = 16 * 365


@dataclass(frozen=True)
class SimulationConfig:
    days: int = 2500
    initial_population: int = 12
    max_population: int = 450
    seed: int = 42
    output_dir: Path = Path("outputs")
    proposer_model: str = "llama3.2:3b"
    critic_model: str = "qwen2.5:3b"
    ollama_url: str = "http://127.0.0.1:11434"
    llm_timeout_s: float = 25.0
    llm_enabled: bool = True
    verbose_every: int = 30
    alpha_learning: float = 0.22
    exploration_floor: float = 0.04
    exploration_boost: float = 0.24
    bio: BioConstraints = field(default_factory=BioConstraints)

    @staticmethod
    def from_env() -> "SimulationConfig":
        output_dir = Path(os.getenv("SIM_OUTPUT_DIR", "outputs"))
        bio = BioConstraints(
            max_days_without_water=_env_int("SIM_MAX_DAYS_WITHOUT_WATER", 3),
            max_days_without_food=_env_int("SIM_MAX_DAYS_WITHOUT_FOOD", 21),
            life_expectancy_days=_env_int("SIM_LIFE_EXPECTANCY_DAYS", 60 * 365),
            gestation_days=_env_int("SIM_GESTATION_DAYS", int(0.75 * 365)),
            puberty_days=_env_int("SIM_PUBERTY_DAYS", 16 * 365),
        )
        return SimulationConfig(
            days=_env_int("SIM_DAYS", 2500),
            initial_population=_env_int("SIM_INITIAL_POPULATION", 12),
            max_population=_env_int("SIM_MAX_POPULATION", 450),
            seed=_env_int("SIM_SEED", 42),
            output_dir=output_dir,
            proposer_model=os.getenv("SIM_MODEL_PROPOSER", "llama3.2:3b"),
            critic_model=os.getenv("SIM_MODEL_CRITIC", "qwen2.5:3b"),
            ollama_url=os.getenv("SIM_OLLAMA_URL", "http://127.0.0.1:11434"),
            llm_timeout_s=_env_float("SIM_LLM_TIMEOUT_S", 25.0),
            llm_enabled=_env_bool("SIM_LLM_ENABLED", True),
            verbose_every=_env_int("SIM_VERBOSE_EVERY", 30),
            alpha_learning=_env_float("SIM_ALPHA_LEARNING", 0.22),
            exploration_floor=_env_float("SIM_EXPLORATION_FLOOR", 0.04),
            exploration_boost=_env_float("SIM_EXPLORATION_BOOST", 0.24),
            bio=bio,
        )
