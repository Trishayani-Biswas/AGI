from __future__ import annotations

from dataclasses import dataclass
import json
import pickle
from pathlib import Path
import random
import shutil
from statistics import mean
from typing import Dict, List, Tuple

try:
    import neat
except ImportError:
    neat = None

from .config import SimulationConfig
from .entities import ALLOWED_ACTIONS, Agent, Decision, Genome, WorldState
from .world import advance_world, apply_action, metabolize


@dataclass(frozen=True)
class NeatTrainingConfig:
    generations: int = 30
    eval_days: int = 700
    seed: int = 42
    max_population: int = 220
    checkpoint_every: int = 5
    output_dir: Path = Path("outputs/neat")
    neat_config_path: Path = Path("configs/neat_survival.ini")


class NeatSurvivalTrainer:
    """Train tabula-rasa survival policies with NEAT under biological constraints."""

    def __init__(self, training_config: NeatTrainingConfig) -> None:
        self.training_config = training_config
        base_sim = SimulationConfig.from_env()
        self.bio = base_sim.bio
        self._generation_index = 0
        self.history: List[Dict[str, object]] = []

    def train(self) -> Dict[str, object]:
        if neat is None:
            raise RuntimeError(
                "neat-python is not installed. Run: python3 -m pip install neat-python"
            )

        cfg = self.training_config
        if not cfg.neat_config_path.exists():
            raise FileNotFoundError(f"Missing NEAT config: {cfg.neat_config_path}")

        cfg.output_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(cfg.neat_config_path, cfg.output_dir / "used_neat_config.ini")

        neat_config = neat.Config(
            neat.DefaultGenome,
            neat.DefaultReproduction,
            neat.DefaultSpeciesSet,
            neat.DefaultStagnation,
            str(cfg.neat_config_path),
        )

        population = neat.Population(neat_config)
        population.add_reporter(neat.StdOutReporter(True))
        stats = neat.StatisticsReporter()
        population.add_reporter(stats)
        population.add_reporter(
            neat.Checkpointer(
                generation_interval=max(1, cfg.checkpoint_every),
                filename_prefix=str(cfg.output_dir / "checkpoint-"),
            )
        )

        winner = population.run(self._evaluate_generation, cfg.generations)

        champion_path = cfg.output_dir / "champion.pkl"
        with champion_path.open("wb") as fp:
            pickle.dump(winner, fp)

        history_path = cfg.output_dir / "history.json"
        history_path.write_text(json.dumps(self.history, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

        summary = {
            "framework": "neat-python",
            "generations": cfg.generations,
            "eval_days": cfg.eval_days,
            "seed": cfg.seed,
            "max_population": cfg.max_population,
            "winner_fitness": float(winner.fitness if winner.fitness is not None else 0.0),
            "history_points": len(self.history),
            "champion_path": str(champion_path),
            "history_path": str(history_path),
            "config_used_path": str(cfg.output_dir / "used_neat_config.ini"),
        }
        (cfg.output_dir / "summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        return summary

    def _evaluate_generation(self, genomes, neat_config) -> None:
        cfg = self.training_config
        rng = random.Random(cfg.seed + (self._generation_index * 7919))
        self._generation_index += 1

        world = WorldState()
        agents: Dict[int, Agent] = {}
        policy_by_agent: Dict[int, int] = {}
        network_by_policy: Dict[int, object] = {}
        fitness_by_policy: Dict[int, float] = {}
        founder_genomes: Dict[int, object] = {}

        next_agent_id = 1
        founder_policy_ids: List[int] = []

        for policy_id, genome in genomes:
            genome.fitness = 0.0
            founder_genomes[policy_id] = genome
            founder_policy_ids.append(policy_id)
            fitness_by_policy[policy_id] = 0.0
            network_by_policy[policy_id] = neat.nn.FeedForwardNetwork.create(genome, neat_config)

            agent = Agent(
                id=next_agent_id,
                sex="F" if rng.random() < 0.5 else "M",
                age_days=rng.randint(18 * 365, 33 * 365),
                genome=Genome.random(rng),
                water_store=rng.randint(2, 5),
                food_store=rng.randint(2, 5),
            )
            agents[agent.id] = agent
            policy_by_agent[agent.id] = policy_id
            next_agent_id += 1

        self._seed_initial_pregnancies(agents, rng)

        for day in range(1, cfg.eval_days + 1):
            world.day = day
            advance_world(world, rng)

            next_agent_id, _ = self._handle_births(
                agents=agents,
                policy_by_agent=policy_by_agent,
                fitness_by_policy=fitness_by_policy,
                next_agent_id=next_agent_id,
                day=day,
                rng=rng,
                founder_policy_ids=founder_policy_ids,
            )

            active_ids = [agent.id for agent in agents.values() if agent.alive]
            for agent_id in active_ids:
                agent = agents[agent_id]
                if not agent.alive:
                    continue

                metabolize(agent, world)
                policy_id = policy_by_agent[agent_id]

                if self._pre_action_death(agent):
                    agent.alive = False
                    fitness_by_policy[policy_id] -= 14.0
                    continue

                action = self._select_action(
                    network_by_policy=network_by_policy,
                    policy_id=policy_id,
                    agent=agent,
                    world=world,
                    alive_count=len(active_ids),
                    rng=rng,
                )
                decision = Decision(action=action, reason="neat_policy", confidence=0.5)
                alive_snapshot = [a for a in agents.values() if a.alive]
                outcome = apply_action(
                    agent=agent,
                    decision=decision,
                    world=world,
                    population=alive_snapshot,
                    rng=rng,
                    day=day,
                    bio=self.bio,
                )

                fitness_by_policy[policy_id] += self._step_fitness(agent, outcome.reward)
                if outcome.event_type == "mate_success":
                    fitness_by_policy[policy_id] += 8.0
                elif outcome.event_type == "experiment_success":
                    fitness_by_policy[policy_id] += 12.0
                elif outcome.event_type == "cooperate_share":
                    fitness_by_policy[policy_id] += 2.0

                if self._post_action_death(agent, rng):
                    agent.alive = False
                    fitness_by_policy[policy_id] -= 16.0

            if not any(agent.alive for agent in agents.values()):
                break

        for agent_id, agent in agents.items():
            policy_id = policy_by_agent[agent_id]
            if agent.alive:
                fitness_by_policy[policy_id] += 18.0 + (agent.health * 0.1)

        for policy_id in founder_policy_ids:
            alive_lineage = sum(
                1
                for agent_id, agent in agents.items()
                if agent.alive and policy_by_agent[agent_id] == policy_id
            )
            total_lineage = sum(
                1 for mapped_policy in policy_by_agent.values() if mapped_policy == policy_id
            )
            fitness_by_policy[policy_id] += (alive_lineage * 3.0) + (total_lineage * 0.8)

        for policy_id, genome in founder_genomes.items():
            genome.fitness = max(-100.0, fitness_by_policy.get(policy_id, -100.0))

        fitness_values = [genome.fitness for genome in founder_genomes.values()]
        generation_record = {
            "generation": self._generation_index,
            "population": len(founder_genomes),
            "alive_end": sum(1 for agent in agents.values() if agent.alive),
            "best_fitness": max(fitness_values) if fitness_values else 0.0,
            "mean_fitness": mean(fitness_values) if fitness_values else 0.0,
            "world_innovations": sorted(world.innovations),
        }
        self.history.append(generation_record)

        if self._generation_index % 5 == 0:
            print(
                "NEAT generation "
                f"{self._generation_index}: best={generation_record['best_fitness']:.2f} "
                f"mean={generation_record['mean_fitness']:.2f} "
                f"alive_end={generation_record['alive_end']}"
            )

    def _seed_initial_pregnancies(self, agents: Dict[int, Agent], rng: random.Random) -> None:
        adult_males = [
            agent
            for agent in agents.values()
            if agent.sex == "M" and agent.is_adult(self.bio.puberty_days)
        ]
        adult_females = [
            agent
            for agent in agents.values()
            if agent.sex == "F" and agent.is_adult(self.bio.puberty_days)
        ]
        for female in adult_females:
            if not adult_males:
                break
            if rng.random() < 0.15:
                father = rng.choice(adult_males)
                female.pregnant_until = rng.randint(40, min(170, self.bio.gestation_days))
                female.co_parent_id = father.id

        if adult_females and not any(agent.pregnant_until is not None for agent in adult_females):
            mother = rng.choice(adult_females)
            father = rng.choice(adult_males) if adult_males else None
            if father is not None:
                mother.pregnant_until = rng.randint(40, min(140, self.bio.gestation_days))
                mother.co_parent_id = father.id

    def _handle_births(
        self,
        agents: Dict[int, Agent],
        policy_by_agent: Dict[int, int],
        fitness_by_policy: Dict[int, float],
        next_agent_id: int,
        day: int,
        rng: random.Random,
        founder_policy_ids: List[int],
    ) -> Tuple[int, int]:
        births = 0
        mothers = [
            agent
            for agent in agents.values()
            if agent.alive
            and agent.sex == "F"
            and agent.pregnant_until is not None
            and agent.pregnant_until <= day
        ]

        for mother in mothers:
            if sum(1 for agent in agents.values() if agent.alive) >= self.training_config.max_population:
                mother.pregnant_until = day + 7
                continue

            father = agents.get(mother.co_parent_id) if mother.co_parent_id is not None else None
            if father is None or not father.alive:
                father = self._pick_father(agents, exclude_id=mother.id, rng=rng)

            if father is None:
                mother.pregnant_until = day + 21
                continue

            mother_policy = policy_by_agent[mother.id]
            father_policy = policy_by_agent[father.id]
            child_policy = self._inherit_policy(
                mother_policy=mother_policy,
                father_policy=father_policy,
                founder_policy_ids=founder_policy_ids,
                rng=rng,
            )

            child = Agent(
                id=next_agent_id,
                sex="F" if rng.random() < 0.5 else "M",
                age_days=0,
                genome=Genome.inherit(mother.genome, father.genome, rng),
                water_store=1,
                food_store=1,
            )

            agents[child.id] = child
            policy_by_agent[child.id] = child_policy
            next_agent_id += 1
            births += 1

            mother.children += 1
            father.children += 1
            mother.pregnant_until = None
            mother.co_parent_id = None
            mother.water_store = max(0, mother.water_store - 1)
            mother.food_store = max(0, mother.food_store - 1)

            fitness_by_policy[mother_policy] += 9.0
            fitness_by_policy[father_policy] += 9.0

        return next_agent_id, births

    def _pick_father(
        self,
        agents: Dict[int, Agent],
        exclude_id: int,
        rng: random.Random,
    ) -> Agent | None:
        candidates = [
            agent
            for agent in agents.values()
            if agent.alive
            and agent.id != exclude_id
            and agent.sex == "M"
            and agent.is_adult(self.bio.puberty_days)
        ]
        if not candidates:
            return None
        return rng.choice(candidates)

    def _inherit_policy(
        self,
        mother_policy: int,
        father_policy: int,
        founder_policy_ids: List[int],
        rng: random.Random,
    ) -> int:
        roll = rng.random()
        if roll < 0.45:
            return mother_policy
        if roll < 0.9:
            return father_policy
        if roll < 0.97 and founder_policy_ids:
            return rng.choice(founder_policy_ids)
        return mother_policy if rng.random() < 0.5 else father_policy

    def _pre_action_death(self, agent: Agent) -> bool:
        return agent.health <= 0.0

    def _post_action_death(self, agent: Agent, rng: random.Random) -> bool:
        if agent.health <= 0.0:
            return True
        if agent.days_without_water >= self.bio.max_days_without_water:
            return True
        if agent.days_without_food >= self.bio.max_days_without_food:
            return True
        if agent.age_days > self.bio.life_expectancy_days:
            years_over = (agent.age_days - self.bio.life_expectancy_days) / 365.0
            old_age_chance = min(0.7, 0.01 + (years_over * 0.06))
            return rng.random() < old_age_chance
        return False

    def _step_fitness(self, agent: Agent, reward: float) -> float:
        base_survival = 1.2 + (agent.health / 100.0) * 0.35
        reserve_bonus = (min(agent.water_store, 12) * 0.08) + (min(agent.food_store, 12) * 0.06)
        return base_survival + reserve_bonus + (reward * 0.55)

    def _select_action(
        self,
        network_by_policy: Dict[int, object],
        policy_id: int,
        agent: Agent,
        world: WorldState,
        alive_count: int,
        rng: random.Random,
    ) -> str:
        if rng.random() < max(0.02, agent.genome.exploration_drive * 0.08):
            return rng.choice(ALLOWED_ACTIONS)

        network = network_by_policy.get(policy_id)
        if network is None:
            return rng.choice(ALLOWED_ACTIONS)

        observation = self._observation(agent=agent, world=world, alive_count=alive_count)
        outputs = network.activate(observation)
        if len(outputs) < len(ALLOWED_ACTIONS):
            return rng.choice(ALLOWED_ACTIONS)

        best_index = max(range(len(ALLOWED_ACTIONS)), key=lambda idx: outputs[idx])
        return ALLOWED_ACTIONS[best_index]

    def _observation(self, agent: Agent, world: WorldState, alive_count: int) -> Tuple[float, ...]:
        is_dry = 1.0 if world.weather == "dry" else 0.0
        is_mild = 1.0 if world.weather == "mild" else 0.0
        is_rainy = 1.0 if world.weather == "rainy" else 0.0

        return (
            agent.health / 100.0,
            min(1.0, agent.days_without_water / 3.0),
            min(1.0, agent.days_without_food / 21.0),
            min(1.0, agent.water_store / 14.0),
            min(1.0, agent.food_store / 14.0),
            agent.shelter_skill,
            is_dry,
            is_mild,
            is_rainy,
            world.water_abundance,
            world.food_abundance,
            world.shelter_tech,
            min(1.0, world.health_regen_bonus / 2.0),
            min(1.0, world.gather_bonus_water / 2.0),
            min(1.0, world.gather_bonus_food / 2.0),
            min(1.0, world.survival_buffer / 2.0),
            min(1.0, agent.age_days / float(self.bio.life_expectancy_days)),
            1.0 if agent.pregnant_until is not None else 0.0,
            min(1.0, alive_count / float(self.training_config.max_population)),
        )
