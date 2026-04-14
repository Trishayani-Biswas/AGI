from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import random
import subprocess
import sys
import time
from typing import Dict, List, Set


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Dict[str, object] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if isinstance(payload, dict):
        return payload
    return None


def _load_used_seeds(outputs_dir: Path) -> Set[int]:
    used: Set[int] = set()
    if not outputs_dir.exists():
        return used

    for child in outputs_dir.iterdir():
        if not child.is_dir():
            continue
        summary_path = child / "summary.json"
        if not summary_path.exists():
            continue

        try:
            payload = json.loads(summary_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        if not isinstance(payload, dict):
            continue
        if payload.get("framework") != "neat-python":
            continue

        seed = payload.get("seed")
        if isinstance(seed, int):
            used.add(seed)

    return used


def _pick_next_seed(base_seed: int, used_seeds: Set[int], offset: int) -> int:
    candidate = base_seed + offset
    while candidate in used_seeds:
        candidate += 1
    used_seeds.add(candidate)
    return candidate


def _run_command(name: str, command: List[str], cwd: Path) -> Dict[str, object]:
    print("")
    print(f"[{_utc_now()}] {name}: {' '.join(command)}")
    started = time.time()
    result = subprocess.run(command, cwd=str(cwd), check=False)
    elapsed = time.time() - started
    print(f"[{_utc_now()}] {name}: code={result.returncode} sec={elapsed:.2f}")
    return {
        "name": name,
        "command": " ".join(command),
        "code": int(result.returncode),
        "seconds": round(elapsed, 3),
    }


def _read_best_from_report(report_path: Path) -> Dict[str, object]:
    if not report_path.exists():
        return {}

    try:
        lines = report_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}

    for line in lines:
        if not line.startswith("| 1 |"):
            continue
        parts = [part.strip() for part in line.split("|")]
        # Expected table row format:
        # | Rank | Run | Hist/Gen | Complete | Winner Fitness | Robust Mean | ...
        if len(parts) < 7:
            continue

        run_name = parts[2]
        robust_mean_raw = parts[6]
        winner_fitness_raw = parts[5] if len(parts) > 5 else ""

        try:
            robust_mean = float(robust_mean_raw)
        except ValueError:
            robust_mean = None

        try:
            winner_fitness = float(winner_fitness_raw)
        except ValueError:
            winner_fitness = None

        return {
            "run": run_name,
            "robust_mean": robust_mean,
            "winner_fitness": winner_fitness,
        }

    return {}


def _latest_checkpoint(run_dir: Path) -> Path | None:
    checkpoints: List[tuple[int, Path]] = []
    for checkpoint_path in run_dir.glob("checkpoint-*"):
        name = checkpoint_path.name
        if "-" not in name:
            continue
        suffix = name.rsplit("-", 1)[-1]
        try:
            idx = int(suffix)
        except ValueError:
            continue
        checkpoints.append((idx, checkpoint_path))

    if not checkpoints:
        return None
    checkpoints.sort(key=lambda item: item[0])
    return checkpoints[-1][1]


def _read_run_metrics(run_dir: Path) -> Dict[str, object]:
    summary = _load_json(run_dir / "summary.json") or {}
    robustness = _load_json(run_dir / "robustness.json") or {}

    mean_score = robustness.get("mean_score", summary.get("robustness_mean_score"))
    min_score = robustness.get("min_score", summary.get("robustness_min_score"))
    max_score = robustness.get("max_score", summary.get("robustness_max_score"))

    return {
        "mean_score": float(mean_score) if isinstance(mean_score, (int, float)) else None,
        "min_score": float(min_score) if isinstance(min_score, (int, float)) else None,
        "max_score": float(max_score) if isinstance(max_score, (int, float)) else None,
        "world_difficulty": summary.get("world_difficulty"),
        "shock_probability": summary.get("shock_probability"),
        "curriculum_enabled": bool(summary.get("curriculum_enabled", False)),
    }


def _compute_reward(
    metrics: Dict[str, object],
    min_score_floor: float,
    min_weight: float,
) -> float | None:
    mean_score = metrics.get("mean_score")
    min_score = metrics.get("min_score")
    if not isinstance(mean_score, (int, float)) or not isinstance(min_score, (int, float)):
        return None

    mean_value = float(mean_score)
    min_value = float(min_score)
    reward = mean_value + (float(min_weight) * min_value)

    # Penalize fragile policies that spike on mean but collapse on worst-case seeds.
    if min_value < float(min_score_floor):
        reward -= (float(min_score_floor) - min_value) * 0.5

    return reward


def _bootstrap_incumbent(
    outputs_dir: Path,
    min_score_floor: float,
    min_weight: float,
) -> Dict[str, object]:
    best_reward = float("-inf")
    best: Dict[str, object] = {}

    if not outputs_dir.exists():
        return best

    for child in outputs_dir.iterdir():
        if not child.is_dir():
            continue
        summary = _load_json(child / "summary.json")
        if not summary:
            continue
        if summary.get("framework") != "neat-python":
            continue

        checkpoint_path = _latest_checkpoint(child)
        if checkpoint_path is None:
            continue

        metrics = _read_run_metrics(child)
        reward = _compute_reward(
            metrics=metrics,
            min_score_floor=min_score_floor,
            min_weight=min_weight,
        )
        if reward is None or reward <= best_reward:
            continue

        best_reward = reward
        best = {
            "run": child.name,
            "reward": reward,
            "checkpoint": checkpoint_path,
            "metrics": metrics,
        }

    return best


def _build_profiles(args: argparse.Namespace) -> List[Dict[str, object]]:
    base_difficulty = float(args.world_difficulty)
    base_shock = float(args.shock_prob)
    hard_difficulty = max(0.1, base_difficulty + float(args.hard_difficulty_delta))
    hard_shock = max(0.0, base_shock + float(args.hard_shock_delta))

    return [
        {
            "id": "nocurr_base",
            "curriculum": False,
            "world_difficulty": base_difficulty,
            "shock_prob": base_shock,
        },
        {
            "id": "curr_base",
            "curriculum": True,
            "world_difficulty": base_difficulty,
            "shock_prob": base_shock,
        },
        {
            "id": "nocurr_hard",
            "curriculum": False,
            "world_difficulty": hard_difficulty,
            "shock_prob": hard_shock,
        },
        {
            "id": "curr_hard",
            "curriculum": True,
            "world_difficulty": hard_difficulty,
            "shock_prob": hard_shock,
        },
    ]


def _select_profile(
    profiles: List[Dict[str, object]],
    profile_stats: Dict[str, Dict[str, float]],
    completed_reward_count: int,
    explore_c: float,
) -> Dict[str, object]:
    # Warm-up: ensure every profile gets at least one measured attempt.
    for profile in profiles:
        profile_id = str(profile["id"])
        if int(profile_stats[profile_id]["attempts"]) == 0:
            return profile

    total = max(1, int(completed_reward_count))
    best_profile = profiles[0]
    best_ucb = float("-inf")

    for profile in profiles:
        profile_id = str(profile["id"])
        stat = profile_stats[profile_id]
        attempts = max(1.0, float(stat["attempts"]))
        avg_reward = float(stat["avg_reward"])
        explore_bonus = float(explore_c) * math.sqrt(math.log(total + 1.0) / attempts)
        score = avg_reward + explore_bonus

        if score > best_ucb:
            best_ucb = score
            best_profile = profile

    return best_profile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Autonomous AGI goal autopilot for time-budgeted NEAT pushes")
    parser.add_argument("--budget-minutes", type=int, default=60, help="Total wall-clock budget")
    parser.add_argument("--max-runs", type=int, default=0, help="Optional cap on number of training runs (0 = unlimited)")
    parser.add_argument("--base-seed", type=int, default=20000, help="Seed start for automatic sampling")
    parser.add_argument("--run-tag", type=str, default="", help="Prefix used for output directories")

    parser.add_argument("--generations", type=int, default=40)
    parser.add_argument("--eval-days", type=int, default=900)
    parser.add_argument("--max-population", type=int, default=220)
    parser.add_argument("--world-difficulty", type=float, default=1.45)
    parser.add_argument("--shock-prob", type=float, default=0.02)
    parser.add_argument("--robustness-seeds", type=int, default=4)
    parser.add_argument("--robustness-days", type=int, default=300)
    parser.add_argument("--robustness-founders", type=int, default=24)
    parser.add_argument("--checkpoint-every", type=int, default=10)

    parser.add_argument("--curriculum-every", type=int, default=6, help="Use curriculum every Nth run (0 disables curriculum runs)")
    parser.add_argument("--refresh-every", type=int, default=2, help="Refresh compare/observatory every N runs")

    parser.add_argument(
        "--resume-prob",
        type=float,
        default=0.65,
        help="Probability of resuming from current best checkpoint (0.0-1.0)",
    )
    parser.add_argument(
        "--explore-c",
        type=float,
        default=2200.0,
        help="UCB exploration strength for adaptive profile selection",
    )
    parser.add_argument(
        "--min-score-floor",
        type=float,
        default=30000.0,
        help="Reward floor target for robustness minimum score",
    )
    parser.add_argument(
        "--reward-min-weight",
        type=float,
        default=0.35,
        help="Reward weight applied to robustness minimum score",
    )
    parser.add_argument(
        "--hard-difficulty-delta",
        type=float,
        default=0.05,
        help="Added world difficulty for hard profiles",
    )
    parser.add_argument(
        "--hard-shock-delta",
        type=float,
        default=0.002,
        help="Added shock probability for hard profiles",
    )

    parser.add_argument("--outputs-dir", type=str, default="outputs")
    parser.add_argument("--wiki-dir", type=str, default="wiki")

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = _repo_root()
    outputs_dir = (root / args.outputs_dir).resolve()
    wiki_dir = (root / args.wiki_dir).resolve()

    run_tag = args.run_tag.strip() or f"autopilot_{datetime.now(tz=timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    report_dir = outputs_dir / "autopilot"
    report_dir.mkdir(parents=True, exist_ok=True)

    budget_seconds = max(60, int(args.budget_minutes) * 60)
    started_at_epoch = time.time()
    deadline_epoch = started_at_epoch + budget_seconds

    print(f"Autopilot start: {_utc_now()}")
    print(f"run_tag={run_tag} budget_minutes={args.budget_minutes} max_runs={args.max_runs}")

    used_seeds = _load_used_seeds(outputs_dir)
    print(f"Detected used seeds: {len(used_seeds)}")

    profiles = _build_profiles(args)
    print(f"Adaptive profiles: {[profile['id'] for profile in profiles]}")

    profile_stats: Dict[str, Dict[str, float]] = {}
    for profile in profiles:
        profile_id = str(profile["id"])
        profile_stats[profile_id] = {
            "attempts": 0.0,
            "reward_sum": 0.0,
            "avg_reward": 0.0,
            "best_reward": float("-inf"),
        }

    incumbent = _bootstrap_incumbent(
        outputs_dir=outputs_dir,
        min_score_floor=float(args.min_score_floor),
        min_weight=float(args.reward_min_weight),
    )
    incumbent_checkpoint = incumbent.get("checkpoint")
    incumbent_run = incumbent.get("run")
    incumbent_reward = float(incumbent.get("reward", float("-inf")))

    if isinstance(incumbent_checkpoint, Path):
        print(
            "Bootstrap incumbent: "
            f"run={incumbent_run} reward={incumbent_reward:.3f} checkpoint={incumbent_checkpoint}"
        )
    else:
        incumbent_checkpoint = None
        incumbent_run = None
        incumbent_reward = float("-inf")
        print("Bootstrap incumbent: none found, starting from fresh policies.")

    selector_rng = random.Random(int(args.base_seed) + 9137)

    runs: List[Dict[str, object]] = []
    run_idx = 0

    while time.time() < deadline_epoch:
        if args.max_runs > 0 and run_idx >= args.max_runs:
            print("Reached max-runs cap; stopping autopilot loop.")
            break

        run_idx += 1
        seed = _pick_next_seed(base_seed=int(args.base_seed), used_seeds=used_seeds, offset=run_idx)

        completed_reward_count = int(
            sum(profile_stats[profile_id]["attempts"] for profile_id in profile_stats)
        )
        adaptive_profile = _select_profile(
            profiles=profiles,
            profile_stats=profile_stats,
            completed_reward_count=completed_reward_count,
            explore_c=float(args.explore_c),
        )

        use_curriculum = bool(adaptive_profile["curriculum"])
        run_difficulty = float(adaptive_profile["world_difficulty"])
        run_shock = float(adaptive_profile["shock_prob"])
        profile_id = str(adaptive_profile["id"])

        # Keep a periodic curriculum override to prevent mode collapse when requested.
        if int(args.curriculum_every) > 0 and (run_idx % int(args.curriculum_every) == 0):
            use_curriculum = True

        mode = "curr" if use_curriculum else "nocurr"
        output_dir = outputs_dir / f"{run_tag}_{mode}_{seed}"

        resume_from: Path | None = None
        if isinstance(incumbent_checkpoint, Path) and incumbent_checkpoint.exists():
            if selector_rng.random() < max(0.0, min(1.0, float(args.resume_prob))):
                resume_from = incumbent_checkpoint

        train_cmd = [
            sys.executable,
            "run_neat_training.py",
            "--generations",
            str(args.generations),
            "--eval-days",
            str(args.eval_days),
            "--max-population",
            str(args.max_population),
            "--world-difficulty",
            str(run_difficulty),
            "--shock-prob",
            str(run_shock),
            "--robustness-seeds",
            str(args.robustness_seeds),
            "--robustness-days",
            str(args.robustness_days),
            "--robustness-founders",
            str(args.robustness_founders),
            "--checkpoint-every",
            str(args.checkpoint_every),
            "--seed",
            str(seed),
            "--output-dir",
            str(output_dir),
            "--no-auto-memory-sync",
        ]
        if resume_from is not None:
            train_cmd.extend(["--resume", str(resume_from)])
        if use_curriculum:
            train_cmd.append("--curriculum")

        training_result = _run_command(
            name=(
                f"train[{run_idx}] profile={profile_id} mode={mode} seed={seed} "
                f"resume={'yes' if resume_from is not None else 'no'}"
            ),
            command=train_cmd,
            cwd=root,
        )

        run_record: Dict[str, object] = {
            "idx": run_idx,
            "seed": seed,
            "profile_id": profile_id,
            "mode": mode,
            "output_dir": str(output_dir),
            "world_difficulty": run_difficulty,
            "shock_prob": run_shock,
            "resumed_from": str(resume_from) if resume_from is not None else None,
            "training": training_result,
        }

        metrics = _read_run_metrics(output_dir)
        reward = _compute_reward(
            metrics=metrics,
            min_score_floor=float(args.min_score_floor),
            min_weight=float(args.reward_min_weight),
        )
        run_record["metrics"] = metrics
        run_record["reward"] = reward

        if reward is not None:
            stat = profile_stats[profile_id]
            stat["attempts"] += 1.0
            stat["reward_sum"] += float(reward)
            stat["avg_reward"] = stat["reward_sum"] / stat["attempts"]
            stat["best_reward"] = max(float(stat["best_reward"]), float(reward))

        checkpoint_path = _latest_checkpoint(output_dir)
        run_record["latest_checkpoint"] = str(checkpoint_path) if checkpoint_path is not None else None

        if reward is not None and checkpoint_path is not None and float(reward) > incumbent_reward:
            incumbent_reward = float(reward)
            incumbent_checkpoint = checkpoint_path
            incumbent_run = output_dir.name
            run_record["incumbent_update"] = {
                "run": incumbent_run,
                "reward": incumbent_reward,
                "checkpoint": str(incumbent_checkpoint),
            }
            print(
                f"[{_utc_now()}] incumbent updated run={incumbent_run} "
                f"reward={incumbent_reward:.3f} checkpoint={incumbent_checkpoint}"
            )

        runs.append(run_record)

        refresh_due = (run_idx % max(1, int(args.refresh_every)) == 0)
        if refresh_due:
            compare_result = _run_command(
                name="compare",
                command=[sys.executable, "scripts/compare_neat_runs.py", "--require-full-generations"],
                cwd=root,
            )
            observatory_result = _run_command(
                name="observatory",
                command=[sys.executable, "scripts/build_experiment_observatory.py"],
                cwd=root,
            )
            run_record["refresh"] = {
                "compare": compare_result,
                "observatory": observatory_result,
            }

    final_steps: List[Dict[str, object]] = []

    final_steps.append(
        _run_command(
            name="final_compare",
            command=[sys.executable, "scripts/compare_neat_runs.py", "--require-full-generations"],
            cwd=root,
        )
    )
    final_steps.append(
        _run_command(
            name="final_observatory",
            command=[sys.executable, "scripts/build_experiment_observatory.py"],
            cwd=root,
        )
    )
    final_steps.append(
        _run_command(
            name="final_autosync",
            command=[
                sys.executable,
                "scripts/agi_memory_autosync.py",
                "--sync-once",
                "--force",
                "--outputs-dir",
                str(outputs_dir),
                "--wiki-dir",
                str(wiki_dir),
                "--max-runs",
                "40",
                "--require-full-generations",
            ],
            cwd=root,
        )
    )

    best_summary = _read_best_from_report(outputs_dir / "neat_comparison_report.md")

    completed_at_epoch = time.time()
    summary_payload = {
        "run_tag": run_tag,
        "started_at_utc": datetime.fromtimestamp(started_at_epoch, tz=timezone.utc).isoformat(),
        "finished_at_utc": datetime.fromtimestamp(completed_at_epoch, tz=timezone.utc).isoformat(),
        "budget_minutes": int(args.budget_minutes),
        "strategy": {
            "name": "adaptive_ucb_checkpoint_resume",
            "explore_c": float(args.explore_c),
            "resume_prob": float(args.resume_prob),
            "min_score_floor": float(args.min_score_floor),
            "reward_min_weight": float(args.reward_min_weight),
        },
        "elapsed_seconds": round(completed_at_epoch - started_at_epoch, 3),
        "runs_attempted": len(runs),
        "runs_succeeded": sum(1 for item in runs if int(item.get("training", {}).get("code", 1)) == 0),
        "runs_failed": sum(1 for item in runs if int(item.get("training", {}).get("code", 1)) != 0),
        "best_after": best_summary,
        "incumbent": {
            "run": incumbent_run,
            "reward": incumbent_reward if math.isfinite(incumbent_reward) else None,
            "checkpoint": str(incumbent_checkpoint) if isinstance(incumbent_checkpoint, Path) else None,
        },
        "profile_stats": {
            profile_id: {
                "attempts": int(stat["attempts"]),
                "avg_reward": round(float(stat["avg_reward"]), 3) if stat["attempts"] > 0 else None,
                "best_reward": (
                    round(float(stat["best_reward"]), 3)
                    if math.isfinite(float(stat["best_reward"]))
                    else None
                ),
            }
            for profile_id, stat in profile_stats.items()
        },
        "runs": runs,
        "final_steps": final_steps,
    }

    summary_json_path = report_dir / f"{run_tag}_summary.json"
    summary_json_path.write_text(
        json.dumps(summary_payload, indent=2, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )

    summary_md_lines = [
        f"# AGI Autopilot Summary: {run_tag}",
        "",
        f"- Started: {summary_payload['started_at_utc']}",
        f"- Finished: {summary_payload['finished_at_utc']}",
        f"- Budget minutes: {summary_payload['budget_minutes']}",
        f"- Elapsed seconds: {summary_payload['elapsed_seconds']}",
        f"- Runs attempted: {summary_payload['runs_attempted']}",
        f"- Runs succeeded: {summary_payload['runs_succeeded']}",
        f"- Runs failed: {summary_payload['runs_failed']}",
        f"- Strategy: {summary_payload['strategy']['name']}",
        "",
    ]

    incumbent_payload = summary_payload.get("incumbent", {})
    if isinstance(incumbent_payload, dict) and incumbent_payload.get("run"):
        summary_md_lines.extend(
            [
                "## Incumbent Checkpoint",
                "",
                f"- Run: {incumbent_payload.get('run')}",
                f"- Reward: {incumbent_payload.get('reward')}",
                f"- Checkpoint: {incumbent_payload.get('checkpoint')}",
                "",
            ]
        )

    profile_stats_payload = summary_payload.get("profile_stats", {})
    if isinstance(profile_stats_payload, dict):
        summary_md_lines.extend([
            "## Profile Rewards",
            "",
            "| Profile | Attempts | Avg Reward | Best Reward |",
            "| --- | ---: | ---: | ---: |",
        ])
        for profile_id, stat in profile_stats_payload.items():
            if not isinstance(stat, dict):
                continue
            summary_md_lines.append(
                "| "
                f"{profile_id} | "
                f"{stat.get('attempts')} | "
                f"{stat.get('avg_reward')} | "
                f"{stat.get('best_reward')} |"
            )
        summary_md_lines.append("")

    if best_summary:
        summary_md_lines.extend(
            [
                "## Best After Run",
                "",
                f"- Run: {best_summary.get('run')}",
                f"- Robust mean: {best_summary.get('robust_mean')}",
                f"- Winner fitness: {best_summary.get('winner_fitness')}",
                "",
            ]
        )

    summary_md_path = report_dir / f"{run_tag}_summary.md"
    summary_md_path.write_text("\n".join(summary_md_lines) + "\n", encoding="utf-8")

    print("")
    print("Autopilot complete.")
    print(f"Summary JSON: {summary_json_path}")
    print(f"Summary MD: {summary_md_path}")


if __name__ == "__main__":
    main()
