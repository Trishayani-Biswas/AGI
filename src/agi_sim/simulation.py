from __future__ import annotations

import csv
import json
import random
from dataclasses import replace
from pathlib import Path
from typing import Dict, Optional

from .config import SimulationConfig
from .entities import ALLOWED_ACTIONS, Agent, Genome, WorldState
from .llm import DualLLMBrain
from .world import advance_world, apply_action, metabolize


class Simulation:
    def __init__(self, config: SimulationConfig) -> None:
        self.config = config
        self.rng = random.Random(config.seed)
        self.world = WorldState()
        self.brain = DualLLMBrain(config)
        self.agents: Dict[int, Agent] = {}
        self.next_agent_id = 1
        self._seed_population()

    @property
    def alive_count(self) -> int:
        return sum(1 for agent in self.agents.values() if agent.alive)

    def _seed_population(self) -> None:
        for _ in range(self.config.initial_population):
            sex = "F" if self.rng.random() < 0.5 else "M"
            age_days = self.rng.randint(18 * 365, 34 * 365)
            agent = Agent(
                id=self.next_agent_id,
                sex=sex,
                age_days=age_days,
                genome=Genome.random(self.rng),
                water_store=self.rng.randint(3, 6),
                food_store=self.rng.randint(3, 6),
            )
            self.agents[agent.id] = agent
            self.next_agent_id += 1

        adult_males = [
            a
            for a in self.agents.values()
            if a.sex == "M" and a.is_adult(self.config.bio.puberty_days)
        ]
        adult_females = [
            a
            for a in self.agents.values()
            if a.sex == "F" and a.is_adult(self.config.bio.puberty_days)
        ]
        for female in adult_females:
            if not adult_males:
                break
            if self.rng.random() < 0.24:
                father = self.rng.choice(adult_males)
                female.pregnant_until = self.rng.randint(35, min(160, self.config.bio.gestation_days))
                female.co_parent_id = father.id

        if adult_females and not any(a.pregnant_until is not None for a in adult_females):
            mother = self.rng.choice(adult_females)
            father = self.rng.choice(adult_males) if adult_males else None
            if father is not None:
                mother.pregnant_until = self.rng.randint(35, min(120, self.config.bio.gestation_days))
                mother.co_parent_id = father.id

    def _write_event(self, fp, payload: Dict[str, object]) -> None:
        fp.write(json.dumps(payload, ensure_ascii=True) + "\n")

    def _learn(self, agent: Agent, action: str, reward: float) -> None:
        old = agent.action_values.get(action, 0.0)
        updated = old + (self.config.alpha_learning * (reward - old))
        agent.action_values[action] = max(-10.0, min(10.0, updated))

    def _death_reason(self, agent: Agent, check_deprivation: bool = True) -> Optional[str]:
        if agent.health <= 0.0:
            return "health_collapse"
        if check_deprivation:
            if agent.days_without_water >= self.config.bio.max_days_without_water:
                return "dehydration"
            if agent.days_without_food >= self.config.bio.max_days_without_food:
                return "starvation"
        if agent.age_days > self.config.bio.life_expectancy_days:
            years_over = (agent.age_days - self.config.bio.life_expectancy_days) / 365.0
            old_age_chance = min(0.7, 0.01 + (years_over * 0.06))
            if self.rng.random() < old_age_chance:
                return "old_age"
        return None

    def _pick_father(self, exclude_id: int) -> Optional[Agent]:
        males = [
            a
            for a in self.agents.values()
            if a.alive and a.sex == "M" and a.id != exclude_id and a.is_adult(self.config.bio.puberty_days)
        ]
        if not males:
            return None
        return self.rng.choice(males)

    def _spawn_child(self, mother: Agent, father: Agent) -> Agent:
        child_genome = Genome.inherit(mother.genome, father.genome, self.rng)
        inherited_action_values = {}
        for action in ALLOWED_ACTIONS:
            parent_avg = (mother.action_values.get(action, 0.0) + father.action_values.get(action, 0.0)) / 2.0
            inherited_action_values[action] = max(-10.0, min(10.0, parent_avg + self.rng.gauss(0.0, 0.1)))

        child = Agent(
            id=self.next_agent_id,
            sex="F" if self.rng.random() < 0.5 else "M",
            age_days=0,
            genome=child_genome,
            water_store=1,
            food_store=1,
            action_values=inherited_action_values,
        )

        parent_ideas = set(mother.known_innovations) | set(father.known_innovations)
        if parent_ideas:
            teach_count = self.rng.randint(0, min(2, len(parent_ideas)))
            if teach_count > 0:
                child.known_innovations = set(self.rng.sample(list(parent_ideas), k=teach_count))

        self.next_agent_id += 1
        return child

    def _handle_births(self, day: int, fp) -> int:
        births = 0
        mothers = [
            a
            for a in self.agents.values()
            if a.alive and a.sex == "F" and a.pregnant_until is not None and a.pregnant_until <= day
        ]

        for mother in mothers:
            if self.alive_count >= self.config.max_population:
                mother.pregnant_until = day + 7
                self._write_event(
                    fp,
                    {
                        "day": day,
                        "type": "birth_deferred_capacity",
                        "mother_id": mother.id,
                        "alive_population": self.alive_count,
                    },
                )
                continue

            father = self.agents.get(mother.co_parent_id) if mother.co_parent_id is not None else None
            if father is None or not father.alive:
                father = self._pick_father(exclude_id=mother.id)

            if father is None:
                mother.pregnant_until = day + 30
                self._write_event(
                    fp,
                    {
                        "day": day,
                        "type": "birth_failed_no_father",
                        "mother_id": mother.id,
                    },
                )
                continue

            child = self._spawn_child(mother, father)
            self.agents[child.id] = child
            births += 1
            mother.children += 1
            father.children += 1
            mother.pregnant_until = None
            mother.co_parent_id = None
            mother.food_store = max(0, mother.food_store - 1)
            mother.water_store = max(0, mother.water_store - 1)

            self._write_event(
                fp,
                {
                    "day": day,
                    "type": "birth",
                    "mother_id": mother.id,
                    "father_id": father.id,
                    "child_id": child.id,
                    "child_sex": child.sex,
                },
            )

        return births

    def run(self) -> Dict[str, object]:
        out_dir = self.config.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        events_path = out_dir / "events.jsonl"
        metrics_path = out_dir / "daily_metrics.csv"

        final_day = 0

        with events_path.open("w", encoding="utf-8") as events_fp, metrics_path.open("w", encoding="utf-8", newline="") as metrics_fp:
            fieldnames = [
                "day",
                "population_alive",
                "births",
                "deaths",
                "avg_health",
                "global_innovations",
                "water_abundance",
                "food_abundance",
            ]
            writer = csv.DictWriter(metrics_fp, fieldnames=fieldnames)
            writer.writeheader()

            for day in range(1, self.config.days + 1):
                final_day = day
                self.world.day = day
                advance_world(self.world, self.rng)
                births = self._handle_births(day, events_fp)
                deaths = 0

                active_ids = [a.id for a in self.agents.values() if a.alive]
                for agent_id in active_ids:
                    agent = self.agents[agent_id]
                    if not agent.alive:
                        continue

                    metabolize(agent, self.world)
                    death_reason = self._death_reason(agent, check_deprivation=False)
                    if death_reason:
                        agent.alive = False
                        deaths += 1
                        self._write_event(
                            events_fp,
                            {
                                "day": day,
                                "type": "death",
                                "agent_id": agent.id,
                                "reason": death_reason,
                                "age_days": agent.age_days,
                            },
                        )
                        continue

                    alive_snapshot = [a for a in self.agents.values() if a.alive]
                    decision = self.brain.decide(agent, self.world, alive_snapshot, self.rng)
                    outcome = apply_action(
                        agent=agent,
                        decision=decision,
                        world=self.world,
                        population=alive_snapshot,
                        rng=self.rng,
                        day=day,
                        bio=self.config.bio,
                    )
                    self._learn(agent, decision.action, outcome.reward)

                    self._write_event(
                        events_fp,
                        {
                            "day": day,
                            "type": "action",
                            "agent_id": agent.id,
                            "action": decision.action,
                            "confidence": round(decision.confidence, 3),
                            "reason": decision.reason,
                            "invention_hypothesis": decision.invention_hypothesis,
                            "outcome": outcome.summary,
                            "event_type": outcome.event_type,
                            "reward": round(outcome.reward, 3),
                            "health": round(agent.health, 2),
                            "water_store": agent.water_store,
                            "food_store": agent.food_store,
                            "days_without_water": agent.days_without_water,
                            "days_without_food": agent.days_without_food,
                        },
                    )

                    death_reason = self._death_reason(agent)
                    if death_reason:
                        agent.alive = False
                        deaths += 1
                        self._write_event(
                            events_fp,
                            {
                                "day": day,
                                "type": "death",
                                "agent_id": agent.id,
                                "reason": death_reason,
                                "age_days": agent.age_days,
                            },
                        )

                alive_agents = [a for a in self.agents.values() if a.alive]
                avg_health = (sum(a.health for a in alive_agents) / len(alive_agents)) if alive_agents else 0.0
                writer.writerow(
                    {
                        "day": day,
                        "population_alive": len(alive_agents),
                        "births": births,
                        "deaths": deaths,
                        "avg_health": round(avg_health, 3),
                        "global_innovations": len(self.world.innovations),
                        "water_abundance": round(self.world.water_abundance, 3),
                        "food_abundance": round(self.world.food_abundance, 3),
                    }
                )

                if day % self.config.verbose_every == 0 or day == 1:
                    print(
                        (
                            f"day={day:5d} "
                            f"alive={len(alive_agents):4d} "
                            f"births={births:3d} "
                            f"deaths={deaths:3d} "
                            f"innov={len(self.world.innovations):2d} "
                            f"weather={self.world.weather:5s}"
                        )
                    )

                if not alive_agents:
                    print(f"Population extinction at day {day}.")
                    break

        total_dead = sum(1 for a in self.agents.values() if not a.alive)
        summary = {
            "configured_days": self.config.days,
            "simulated_days": final_day,
            "alive_population": self.alive_count,
            "total_agents_ever": len(self.agents),
            "total_dead": total_dead,
            "global_innovations": sorted(self.world.innovations),
            "output_dir": str(out_dir),
            "llm_enabled": self.config.llm_enabled,
            "proposer_model": self.config.proposer_model,
            "critic_model": self.config.critic_model,
        }

        summary_path = out_dir / "summary.json"
        summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        return summary
