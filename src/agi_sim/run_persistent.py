from __future__ import annotations

import argparse
from dataclasses import replace
import json
from pathlib import Path

from .persistent_agent import EpisodeCondition, GateThresholds, PersistentAgiConfig, PersistentAgiLab


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run persistent single-agent inner-loop training with held-out promotion gating"
    )
    parser.add_argument("--seed", type=int, default=None, help="Base random seed")
    parser.add_argument("--days-per-episode", type=int, default=None, help="Days simulated in each episode")
    parser.add_argument("--train-episodes", type=int, default=None, help="Number of inner-loop training episodes")
    parser.add_argument("--eval-episodes", type=int, default=None, help="Number of held-out evaluation episodes")
    parser.add_argument("--learning-rate", type=float, default=None, help="Action value learning rate")

    parser.add_argument("--train-world-difficulty", type=float, default=None, help="Seen-condition world difficulty")
    parser.add_argument("--train-shock-prob", type=float, default=None, help="Seen-condition shock probability")
    parser.add_argument("--eval-world-difficulty", type=float, default=None, help="Held-out world difficulty")
    parser.add_argument("--eval-shock-prob", type=float, default=None, help="Held-out shock probability")

    parser.add_argument("--survival-margin", type=float, default=None, help="Gate margin over baseline for survival score")
    parser.add_argument("--recovery-margin", type=float, default=None, help="Gate margin over baseline for shock recovery")
    parser.add_argument("--consistency-margin", type=float, default=None, help="Gate margin over baseline for consistency")
    parser.add_argument(
        "--metacognitive-margin",
        type=float,
        default=None,
        help="Gate margin over baseline for metacognitive calibration score",
    )
    parser.add_argument(
        "--temporal-continuity-margin",
        type=float,
        default=None,
        help="Gate margin over baseline for temporal self-continuity score",
    )
    parser.add_argument(
        "--consciousness-margin",
        type=float,
        default=None,
        help="Gate margin over baseline for consciousness proxy score",
    )

    parser.add_argument(
        "--disable-consciousness-stack",
        action="store_true",
        help="Disable autobiographical memory and retrieval-bias consciousness stack",
    )
    parser.add_argument(
        "--consciousness-memory-size",
        type=int,
        default=None,
        help="Maximum autobiographical memory entries for consciousness stack",
    )
    parser.add_argument(
        "--strategy-revision-rate",
        type=float,
        default=None,
        help="Smoothing factor for critique-driven strategy updates",
    )
    parser.add_argument(
        "--strategy-delta-clip",
        type=float,
        default=None,
        help="Per-action clip for critique adjustment deltas",
    )
    parser.add_argument(
        "--strategy-bias-decay",
        type=float,
        default=None,
        help="Per-episode decay applied to strategy action biases",
    )
    parser.add_argument(
        "--exploration-delta-clip",
        type=float,
        default=None,
        help="Clip for exploration-rate adjustment per critique",
    )
    parser.add_argument(
        "--consciousness-bias-scale",
        type=float,
        default=None,
        help="Global scale for consciousness retrieval bias contribution",
    )
    parser.add_argument(
        "--consciousness-bias-clip",
        type=float,
        default=None,
        help="Absolute clip for per-action consciousness bias",
    )
    parser.add_argument(
        "--consciousness-update-rate",
        type=float,
        default=None,
        help="Smoothing rate for consciousness drive updates",
    )
    parser.add_argument(
        "--consciousness-contradiction-gain",
        type=float,
        default=None,
        help="Gain applied when contradictions adjust consciousness drives",
    )

    parser.add_argument("--output-dir", type=str, default=None, help="Output directory for persistent-agent artifacts")
    parser.add_argument(
        "--outer-outputs-dir",
        type=str,
        default=None,
        help="Directory containing NEAT run outputs used to derive outer-loop priors",
    )
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> PersistentAgiConfig:
    cfg = PersistentAgiConfig()

    if args.seed is not None:
        cfg = replace(cfg, seed=args.seed)
    if args.days_per_episode is not None:
        cfg = replace(cfg, days_per_episode=args.days_per_episode)
    if args.train_episodes is not None:
        cfg = replace(cfg, train_episodes=args.train_episodes)
    if args.eval_episodes is not None:
        cfg = replace(cfg, eval_episodes=args.eval_episodes)
    if args.learning_rate is not None:
        cfg = replace(cfg, learning_rate=args.learning_rate)

    train_condition = cfg.train_condition
    if args.train_world_difficulty is not None:
        train_condition = replace(train_condition, world_difficulty=args.train_world_difficulty)
    if args.train_shock_prob is not None:
        train_condition = replace(train_condition, shock_probability=args.train_shock_prob)

    eval_condition = cfg.eval_condition
    if args.eval_world_difficulty is not None:
        eval_condition = replace(eval_condition, world_difficulty=args.eval_world_difficulty)
    if args.eval_shock_prob is not None:
        eval_condition = replace(eval_condition, shock_probability=args.eval_shock_prob)

    gate = cfg.gate
    if args.survival_margin is not None:
        gate = replace(gate, survival_margin=args.survival_margin)
    if args.recovery_margin is not None:
        gate = replace(gate, recovery_margin=args.recovery_margin)
    if args.consistency_margin is not None:
        gate = replace(gate, consistency_margin=args.consistency_margin)
    if args.metacognitive_margin is not None:
        gate = replace(gate, metacognitive_margin=args.metacognitive_margin)
    if args.temporal_continuity_margin is not None:
        gate = replace(gate, temporal_continuity_margin=args.temporal_continuity_margin)
    if args.consciousness_margin is not None:
        gate = replace(gate, consciousness_margin=args.consciousness_margin)

    cfg = replace(cfg, train_condition=train_condition, eval_condition=eval_condition, gate=gate)

    if args.output_dir is not None:
        cfg = replace(cfg, output_dir=Path(args.output_dir))
    if args.outer_outputs_dir is not None:
        cfg = replace(cfg, outer_outputs_dir=Path(args.outer_outputs_dir))
    if args.disable_consciousness_stack:
        cfg = replace(cfg, consciousness_stack_enabled=False)
    if args.consciousness_memory_size is not None:
        cfg = replace(cfg, consciousness_memory_size=max(8, int(args.consciousness_memory_size)))
    if args.strategy_revision_rate is not None:
        cfg = replace(cfg, strategy_revision_rate=float(args.strategy_revision_rate))
    if args.strategy_delta_clip is not None:
        cfg = replace(cfg, strategy_delta_clip=float(args.strategy_delta_clip))
    if args.strategy_bias_decay is not None:
        cfg = replace(cfg, strategy_bias_decay=float(args.strategy_bias_decay))
    if args.exploration_delta_clip is not None:
        cfg = replace(cfg, exploration_delta_clip=float(args.exploration_delta_clip))
    if args.consciousness_bias_scale is not None:
        cfg = replace(cfg, consciousness_bias_scale=float(args.consciousness_bias_scale))
    if args.consciousness_bias_clip is not None:
        cfg = replace(cfg, consciousness_bias_clip=float(args.consciousness_bias_clip))
    if args.consciousness_update_rate is not None:
        cfg = replace(cfg, consciousness_update_rate=float(args.consciousness_update_rate))
    if args.consciousness_contradiction_gain is not None:
        cfg = replace(cfg, consciousness_contradiction_gain=float(args.consciousness_contradiction_gain))

    return cfg


def main() -> None:
    args = parse_args()
    config = build_config(args)

    lab = PersistentAgiLab(config)
    summary = lab.run()
    print(json.dumps(summary, indent=2, ensure_ascii=True))


if __name__ == "__main__":
    main()
