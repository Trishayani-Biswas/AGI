from __future__ import annotations

import math
import random
from typing import Dict, Iterable, Tuple

from .config import BioConstraints
from .entities import Agent, ActionOutcome, Decision, WorldState


INNOVATION_EFFECTS: Dict[str, Tuple[str, float]] = {
    "water_skin": ("gather_bonus_water", 0.08),
    "fish_trap": ("gather_bonus_food", 0.08),
    "hide_tent": ("shelter_tech", 0.06),
    "embers": ("health_regen_bonus", 0.6),
    "preservation": ("survival_buffer", 0.07),
}


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def advance_world(world: WorldState, rng: random.Random) -> None:
    weather_roll = rng.random()
    if weather_roll < 0.2:
        world.weather = "dry"
    elif weather_roll < 0.78:
        world.weather = "mild"
    else:
        world.weather = "rainy"

    seasonal_wave = 0.08 * math.sin(world.day / 42.0)
    weather_water_delta = {"dry": -0.07, "mild": 0.0, "rainy": 0.1}[world.weather]
    weather_food_delta = {"dry": -0.03, "mild": 0.0, "rainy": 0.03}[world.weather]
    water_recovery = (0.58 - world.water_abundance) * 0.08
    food_recovery = (0.58 - world.food_abundance) * 0.08

    world.water_abundance = _clamp(
        world.water_abundance + seasonal_wave + weather_water_delta + water_recovery + rng.uniform(-0.02, 0.02),
        0.2,
        1.0,
    )
    world.food_abundance = _clamp(
        world.food_abundance + (seasonal_wave * 0.7) + weather_food_delta + food_recovery + rng.uniform(-0.02, 0.02),
        0.2,
        1.0,
    )


def metabolize(agent: Agent, world: WorldState) -> None:
    had_water = agent.water_store > 0
    had_food = agent.food_store > 0

    if agent.water_store > 0:
        agent.water_store -= 1
        agent.days_without_water = max(0, agent.days_without_water - 1)
    else:
        agent.days_without_water += 1
        agent.health -= max(1.0, 2.0 - (world.survival_buffer * 1.2))

    if agent.food_store > 0:
        agent.food_store -= 1
        agent.days_without_food = max(0, agent.days_without_food - 1)
    else:
        agent.days_without_food += 1
        agent.health -= max(0.2, 0.5 - (world.survival_buffer * 0.4))

    if world.weather == "dry":
        agent.health -= 0.2

    if world.weather == "rainy" and agent.shelter_skill < 0.2:
        agent.health -= 0.15

    if had_water and had_food:
        agent.health = min(100.0, agent.health + 0.6 + world.health_regen_bonus * 0.15)

    agent.age_days += 1


def apply_action(
    agent: Agent,
    decision: Decision,
    world: WorldState,
    population: Iterable[Agent],
    rng: random.Random,
    day: int,
    bio: BioConstraints,
) -> ActionOutcome:
    action = decision.action

    if action == "search_water":
        chance = 0.34 + (world.water_abundance * 0.58) + world.gather_bonus_water + (agent.genome.exploration_drive * 0.12)
        if world.weather == "dry":
            chance -= 0.08
        if world.weather == "rainy":
            chance += 0.1
        chance = _clamp(chance, 0.05, 0.95)
        if rng.random() < chance:
            found = rng.randint(2, 5 + int(world.gather_bonus_water * 12))
            agent.water_store += found
            if rng.random() < 0.22:
                agent.food_store += 1
            if agent.days_without_water > 0 and agent.water_store > 0:
                agent.water_store -= 1
                agent.days_without_water = max(0, agent.days_without_water - 1)
                agent.health = min(100.0, agent.health + 0.8)
            return ActionOutcome(reward=3.0 + found, summary=f"found {found} water", event_type="search_water_success")
        agent.health -= 0.25
        return ActionOutcome(reward=-1.2, summary="water search failed", event_type="search_water_fail")

    if action == "search_food":
        chance = 0.3 + (world.food_abundance * 0.56) + world.gather_bonus_food + (agent.genome.exploration_drive * 0.1)
        chance = _clamp(chance, 0.05, 0.95)
        if rng.random() < chance:
            found = rng.randint(2, 5 + int(world.gather_bonus_food * 12))
            agent.food_store += found
            if rng.random() < 0.18:
                agent.water_store += 1
            if agent.days_without_food > 0 and agent.food_store > 0:
                agent.food_store -= 1
                agent.days_without_food = max(0, agent.days_without_food - 2)
                agent.health = min(100.0, agent.health + 0.5)
            return ActionOutcome(reward=2.6 + found, summary=f"found {found} food", event_type="search_food_success")
        agent.health -= 0.25
        return ActionOutcome(reward=-1.2, summary="food search failed", event_type="search_food_fail")

    if action == "drink_reserve":
        if agent.water_store > 0:
            agent.water_store -= 1
            agent.days_without_water = max(0, agent.days_without_water - 2)
            agent.health = min(100.0, agent.health + 2.0)
            return ActionOutcome(reward=2.1, summary="drank water reserve", event_type="drink")
        return ActionOutcome(reward=-1.4, summary="no water reserve", event_type="drink_fail")

    if action == "eat_reserve":
        if agent.food_store > 0:
            agent.food_store -= 1
            agent.days_without_food = max(0, agent.days_without_food - 3)
            agent.health = min(100.0, agent.health + 1.6)
            return ActionOutcome(reward=1.8, summary="ate food reserve", event_type="eat")
        return ActionOutcome(reward=-1.1, summary="no food reserve", event_type="eat_fail")

    if action == "build_shelter":
        chance = 0.1 + (agent.shelter_skill * 0.35) + (agent.genome.risk_tolerance * 0.18) + (world.shelter_tech * 0.25)
        chance = _clamp(chance, 0.05, 0.95)
        if rng.random() < chance:
            agent.shelter_skill = _clamp(agent.shelter_skill + 0.06, 0.0, 1.0)
            world.shelter_tech = _clamp(world.shelter_tech + 0.01, 0.0, 1.0)
            return ActionOutcome(reward=2.4, summary="improved shelter", event_type="shelter_success")
        agent.health -= 0.45
        return ActionOutcome(reward=-1.0, summary="shelter build failed", event_type="shelter_fail")

    if action == "rest":
        recovery = 4.8 + world.health_regen_bonus
        agent.health = min(100.0, agent.health + recovery)
        return ActionOutcome(reward=1.5, summary="rested", event_type="rest")

    if action == "cooperate":
        candidates = [
            peer
            for peer in population
            if peer.alive and peer.id != agent.id and (peer.days_without_water + peer.days_without_food) >= 2
        ]
        if not candidates:
            return ActionOutcome(reward=-0.2, summary="no one needed help", event_type="cooperate_idle")

        target = max(candidates, key=lambda x: x.days_without_water + x.days_without_food)
        transfer_water = 1 if agent.water_store > 1 else 0
        transfer_food = 1 if agent.food_store > 1 else 0
        agent.water_store -= transfer_water
        agent.food_store -= transfer_food
        target.water_store += transfer_water
        target.food_store += transfer_food

        if agent.known_innovations:
            shared = rng.choice(list(agent.known_innovations))
            target.known_innovations.add(shared)

        if transfer_water == 0 and transfer_food == 0:
            return ActionOutcome(reward=0.3, summary="social signal only", event_type="cooperate_signal")

        return ActionOutcome(reward=1.7, summary="shared resources", event_type="cooperate_share")

    if action == "mate":
        partners = [
            peer
            for peer in population
            if peer.alive
            and peer.id != agent.id
            and peer.sex != agent.sex
            and peer.is_adult(bio.puberty_days)
        ]
        if not partners or not agent.is_adult(bio.puberty_days):
            return ActionOutcome(reward=-0.5, summary="no mating partner", event_type="mate_fail")

        partner = max(partners, key=lambda x: (x.genome.social_drive + (x.health / 100.0)))
        mother = agent if agent.sex == "F" else partner
        father = partner if mother is agent else agent

        if mother.pregnant_until is not None:
            return ActionOutcome(reward=-0.4, summary="already pregnant", event_type="mate_fail")

        fertility = (mother.genome.social_drive + father.genome.social_drive) / 2.0
        survival_factor = ((mother.health + father.health) / 200.0)
        chance = _clamp(0.06 + (fertility * 0.28 * survival_factor), 0.02, 0.75)

        if rng.random() < chance:
            mother.pregnant_until = day + bio.gestation_days
            mother.co_parent_id = father.id
            return ActionOutcome(reward=4.3, summary="conception successful", event_type="mate_success")

        return ActionOutcome(reward=0.2, summary="pair bonding, no conception", event_type="mate_no_conception")

    if action == "experiment":
        undiscovered = [name for name in INNOVATION_EFFECTS if name not in world.innovations]
        if not undiscovered:
            return ActionOutcome(reward=0.3, summary="no new innovation left", event_type="experiment_idle")

        chance = _clamp(0.03 + (agent.genome.exploration_drive * 0.2) + (agent.shelter_skill * 0.08), 0.01, 0.8)
        if rng.random() < chance:
            hint = (decision.invention_hypothesis or "").strip().lower()
            if hint:
                pick = sorted(undiscovered)[abs(hash(hint)) % len(undiscovered)]
            else:
                pick = rng.choice(undiscovered)
            world.innovations.add(pick)
            agent.known_innovations.add(pick)
            field_name, delta = INNOVATION_EFFECTS[pick]
            setattr(world, field_name, _clamp(getattr(world, field_name) + delta, 0.0, 1.5))
            return ActionOutcome(reward=8.0, summary=f"discovered innovation {pick}", event_type="experiment_success")

        agent.health -= 0.15
        return ActionOutcome(reward=-0.7, summary="experiment failed", event_type="experiment_fail")

    return ActionOutcome(reward=-0.3, summary="unknown action", event_type="invalid_action")
