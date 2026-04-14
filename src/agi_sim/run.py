from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path

from .config import SimulationConfig
from .simulation import Simulation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Primitive survival evolution simulator")
    parser.add_argument("--days", type=int, default=None, help="Number of simulated days")
    parser.add_argument("--population", type=int, default=None, help="Initial population")
    parser.add_argument("--max-population", type=int, default=None, help="Population hard cap")
    parser.add_argument("--seed", type=int, default=None, help="RNG seed")
    parser.add_argument("--output-dir", type=str, default=None, help="Output directory for logs")
    parser.add_argument("--proposer-model", type=str, default=None, help="Ollama model used for proposing actions")
    parser.add_argument("--critic-model", type=str, default=None, help="Ollama model used for critic review")
    parser.add_argument("--verbose-every", type=int, default=None, help="Print cadence in days")
    parser.add_argument("--offline", action="store_true", help="Disable LLM calls and use heuristic brains")
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> SimulationConfig:
    cfg = SimulationConfig.from_env()

    if args.days is not None:
        cfg = replace(cfg, days=args.days)
    if args.population is not None:
        cfg = replace(cfg, initial_population=args.population)
    if args.max_population is not None:
        cfg = replace(cfg, max_population=args.max_population)
    if args.seed is not None:
        cfg = replace(cfg, seed=args.seed)
    if args.output_dir is not None:
        cfg = replace(cfg, output_dir=Path(args.output_dir))
    if args.proposer_model is not None:
        cfg = replace(cfg, proposer_model=args.proposer_model)
    if args.critic_model is not None:
        cfg = replace(cfg, critic_model=args.critic_model)
    if args.verbose_every is not None:
        cfg = replace(cfg, verbose_every=args.verbose_every)
    if args.offline:
        cfg = replace(cfg, llm_enabled=False)

    return cfg


def main() -> None:
    args = parse_args()
    config = build_config(args)
    sim = Simulation(config)
    summary = sim.run()
    print(json.dumps(summary, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
