from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
import subprocess
import sys

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
    parser.add_argument(
        "--no-auto-memory-sync",
        action="store_true",
        help="Disable automatic AGI memory autosync after simulation",
    )
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

    if not args.no_auto_memory_sync:
        _maybe_auto_sync_memory(outputs_dir=config.output_dir)

    print(json.dumps(summary, indent=2, ensure_ascii=True))


def _maybe_auto_sync_memory(outputs_dir: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    sync_script = repo_root / "scripts" / "agi_memory_autosync.py"
    if not sync_script.exists():
        return

    sync_outputs_dir = _resolve_autosync_outputs_dir(outputs_dir=outputs_dir)

    command = [
        sys.executable,
        str(sync_script),
        "--sync-once",
        "--outputs-dir",
        str(sync_outputs_dir),
        "--wiki-dir",
        str(repo_root / "wiki"),
    ]

    try:
        subprocess.run(command, cwd=str(repo_root), check=False)
    except OSError:
        # Simulation summary should still be returned even if memory sync fails.
        return


def _resolve_autosync_outputs_dir(outputs_dir: Path) -> Path:
    resolved = outputs_dir.resolve()

    for candidate in (resolved, *resolved.parents):
        if candidate.name == "outputs":
            return candidate

    return resolved


if __name__ == "__main__":
    main()
