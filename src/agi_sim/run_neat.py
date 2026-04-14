from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path

from .neat_training import NeatSurvivalTrainer, NeatTrainingConfig


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train tabula-rasa NEAT survival policies under biological constraints"
    )
    parser.add_argument("--generations", type=int, default=None, help="Number of NEAT generations")
    parser.add_argument("--eval-days", type=int, default=None, help="Simulation days per generation evaluation")
    parser.add_argument("--seed", type=int, default=None, help="Random seed")
    parser.add_argument("--max-population", type=int, default=None, help="In-evaluation population cap")
    parser.add_argument("--checkpoint-every", type=int, default=None, help="Checkpoint interval in generations")
    parser.add_argument("--output-dir", type=str, default=None, help="Where NEAT artifacts are saved")
    parser.add_argument("--config", type=str, default=None, help="Path to neat_survival.ini")
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> NeatTrainingConfig:
    cfg = NeatTrainingConfig()

    if args.generations is not None:
        cfg = replace(cfg, generations=args.generations)
    if args.eval_days is not None:
        cfg = replace(cfg, eval_days=args.eval_days)
    if args.seed is not None:
        cfg = replace(cfg, seed=args.seed)
    if args.max_population is not None:
        cfg = replace(cfg, max_population=args.max_population)
    if args.checkpoint_every is not None:
        cfg = replace(cfg, checkpoint_every=args.checkpoint_every)
    if args.output_dir is not None:
        cfg = replace(cfg, output_dir=Path(args.output_dir))
    if args.config is not None:
        cfg = replace(cfg, neat_config_path=Path(args.config))

    return cfg


def main() -> None:
    args = parse_args()
    config = build_config(args)
    trainer = NeatSurvivalTrainer(config)
    summary = trainer.train()
    print(json.dumps(summary, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
