from __future__ import annotations

import argparse
import csv
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from statistics import mean, pstdev
from typing import Dict, Iterable, List, Tuple


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _load_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    try:
        with path.open("r", encoding="utf-8", newline="") as fp:
            reader = csv.DictReader(fp)
            return list(reader)
    except OSError:
        return []


def _safe_float(value) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _fmt_float(value, digits: int = 3) -> str:
    cast = _safe_float(value)
    if cast is None:
        return "n/a"
    return f"{cast:.{digits}f}"


def _parse_innovation_name(outcome: str) -> str | None:
    marker = "innovation "
    if marker not in outcome:
        return None
    tail = outcome.split(marker, 1)[1].strip()
    return tail if tail else None


def _scan_events(events_path: Path) -> Dict[str, object]:
    action_counts: Counter[str] = Counter()
    event_counts: Counter[str] = Counter()
    death_reasons: Counter[str] = Counter()
    innovations: Counter[str] = Counter()
    timeline: List[Tuple[int, str]] = []

    if not events_path.exists():
        return {
            "action_counts": action_counts,
            "event_counts": event_counts,
            "death_reasons": death_reasons,
            "innovations": innovations,
            "timeline": timeline,
        }

    try:
        with events_path.open("r", encoding="utf-8") as fp:
            for line in fp:
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue

                action = payload.get("action")
                if isinstance(action, str):
                    action_counts[action] += 1

                event_type = payload.get("event_type")
                if isinstance(event_type, str):
                    event_counts[event_type] += 1

                if payload.get("type") == "death":
                    reason = payload.get("reason")
                    if isinstance(reason, str):
                        death_reasons[reason] += 1

                outcome = payload.get("outcome")
                if isinstance(outcome, str):
                    innovation_name = _parse_innovation_name(outcome)
                    if innovation_name is not None:
                        innovations[innovation_name] += 1

                day = payload.get("day")
                if isinstance(day, int) and len(timeline) < 40:
                    if payload.get("type") == "birth":
                        timeline.append((day, "Birth event"))
                    elif payload.get("type") == "death":
                        reason = str(payload.get("reason", "unknown"))
                        timeline.append((day, f"Death ({reason})"))
                    elif payload.get("event_type") == "experiment_success":
                        timeline.append((day, str(payload.get("outcome", "Innovation discovered"))))
    except OSError:
        pass

    timeline.sort(key=lambda item: item[0])

    return {
        "action_counts": action_counts,
        "event_counts": event_counts,
        "death_reasons": death_reasons,
        "innovations": innovations,
        "timeline": timeline,
    }


def _collect_neat_runs(outputs_dir: Path) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    if not outputs_dir.exists():
        return rows

    for child in sorted(outputs_dir.iterdir()):
        if not child.is_dir():
            continue

        summary_path = child / "summary.json"
        summary = _load_json(summary_path)
        if not isinstance(summary, dict):
            continue
        if summary.get("framework") != "neat-python":
            continue

        history = _load_json(child / "history.json")
        robustness = _load_json(child / "robustness.json")
        history_rows = history if isinstance(history, list) else []
        robustness_obj = robustness if isinstance(robustness, dict) else {}

        rows.append(
            {
                "run": child.name,
                "summary": summary,
                "history": history_rows,
                "robustness": robustness_obj,
                "history_points": summary.get("history_points"),
                "generations": summary.get("generations"),
                "run_completed": (
                    isinstance(summary.get("history_points"), int)
                    and isinstance(summary.get("generations"), int)
                    and int(summary.get("history_points")) >= int(summary.get("generations"))
                ),
                "winner_fitness": _safe_float(summary.get("winner_fitness")),
                "robustness_mean": _safe_float(
                    robustness_obj.get("mean_score", summary.get("robustness_mean_score"))
                ),
                "robustness_min": _safe_float(
                    robustness_obj.get("min_score", summary.get("robustness_min_score"))
                ),
                "robustness_max": _safe_float(
                    robustness_obj.get("max_score", summary.get("robustness_max_score"))
                ),
                "world_difficulty": _safe_float(summary.get("world_difficulty")),
                "shock_probability": _safe_float(summary.get("shock_probability")),
                "eval_days": summary.get("eval_days"),
                "max_population": summary.get("max_population"),
                "summary_path": str(summary_path),
            }
        )

    rows.sort(
        key=lambda row: (
            1 if row.get("run_completed") else 0,
            row["robustness_mean"] if isinstance(row["robustness_mean"], float) else float("-inf"),
            row["winner_fitness"] if isinstance(row["winner_fitness"], float) else float("-inf"),
        ),
        reverse=True,
    )
    return rows


def _history_turning_points(history_rows: List[Dict[str, object]]) -> List[str]:
    if not history_rows:
        return []

    points: List[str] = []
    best_jumps: List[Tuple[float, int]] = []
    previous_best: float | None = None

    for row in history_rows:
        generation = row.get("generation")
        current_best = _safe_float(row.get("best_fitness"))
        if isinstance(generation, int) and current_best is not None and previous_best is not None:
            best_jumps.append((current_best - previous_best, generation))
        if current_best is not None:
            previous_best = current_best

    if best_jumps:
        top_jump = max(best_jumps, key=lambda item: item[0])
        points.append(f"Generation {top_jump[1]} had the largest best-fitness jump ({top_jump[0]:.2f}).")

    resilience = [row for row in history_rows if isinstance(row.get("alive_end"), int) and row.get("alive_end", 0) > 0]
    if resilience:
        first = resilience[0]
        points.append(
            "First non-extinction generation: "
            f"{first.get('generation')} (alive_end={first.get('alive_end')})."
        )

    shock_peak_row = None
    shock_peak = float("-inf")
    for row in history_rows:
        shocks = _safe_float(row.get("shock_days"))
        if shocks is not None and shocks > shock_peak:
            shock_peak = shocks
            shock_peak_row = row
    if shock_peak_row is not None:
        points.append(
            "Shock peak at generation "
            f"{shock_peak_row.get('generation')} ({int(shock_peak)} shock days)."
        )

    culture_peak_row = None
    culture_peak = float("-inf")
    for row in history_rows:
        culture = _safe_float(row.get("mean_culture_size"))
        if culture is not None and culture > culture_peak:
            culture_peak = culture
            culture_peak_row = row
    if culture_peak_row is not None:
        points.append(
            "Culture peak at generation "
            f"{culture_peak_row.get('generation')} (mean_culture_size={culture_peak:.2f})."
        )

    return points


def _fitness_timeline(history_rows: List[Dict[str, object]], max_rows: int = 12) -> List[str]:
    if not history_rows:
        return []
    sampled = history_rows[-max_rows:]
    values = [_safe_float(row.get("best_fitness")) for row in sampled]
    clean_values = [value for value in values if value is not None]
    if not clean_values:
        return []

    min_value = min(clean_values)
    max_value = max(clean_values)
    span = max(1e-9, max_value - min_value)

    lines: List[str] = []
    for row, value in zip(sampled, values):
        generation = row.get("generation")
        if not isinstance(generation, int) or value is None:
            continue
        level = int(((value - min_value) / span) * 20)
        bar = "#" * max(1, level)
        lines.append(f"Gen {generation:>3}: {bar} {value:.2f}")
    return lines


def _group_key(row: Dict[str, object]) -> Tuple[object, object, object, object]:
    return (
        row.get("world_difficulty"),
        row.get("shock_probability"),
        row.get("eval_days"),
        row.get("max_population"),
    )


def _compute_group_variance(rows: Iterable[Dict[str, object]]) -> str:
    robust = [row.get("robustness_mean") for row in rows]
    clean = [value for value in robust if isinstance(value, float)]
    if len(clean) < 2:
        return "Not enough comparable runs for variance estimate."

    avg = mean(clean)
    sigma = pstdev(clean)
    if abs(avg) < 1e-9:
        return "Comparable runs exist but mean robustness is near zero."

    cv = sigma / abs(avg)
    if cv <= 0.25:
        label = "stable"
    elif cv <= 0.5:
        label = "moderate variance"
    else:
        label = "high variance"

    return f"Comparable robustness CV={cv:.3f} ({label})."


def build_report(outputs_dir: Path, report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)

    root_summary = _load_json(outputs_dir / "summary.json")
    metrics_rows = _load_csv_rows(outputs_dir / "daily_metrics.csv")
    event_snapshot = _scan_events(outputs_dir / "events.jsonl")
    neat_rows = _collect_neat_runs(outputs_dir)

    lines: List[str] = []
    lines.append("# Experiment Observatory")
    lines.append("")
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines.append(f"Generated: {generated_at}")
    lines.append("")
    lines.append("This report is designed for watchability: hypotheses, conditions, signals, and turning points.")
    lines.append("")

    lines.append("## What You Are Watching")
    lines.append("")
    lines.append("- Selection pressure: which policies survive and reproduce under scarcity.")
    lines.append("- Adaptation under shocks: whether behavior changes under nonstationary stress.")
    lines.append("- Cultural carryover: whether useful tokens accumulate across lineages.")
    lines.append("- Robustness: whether champions generalize across unseen seeds.")
    lines.append("")

    lines.append("## Simulation Snapshot")
    lines.append("")
    if isinstance(root_summary, dict):
        lines.append(f"- Simulated days: {root_summary.get('simulated_days', 'n/a')}")
        lines.append(f"- Alive population: {root_summary.get('alive_population', 'n/a')}")
        lines.append(f"- Total agents ever: {root_summary.get('total_agents_ever', 'n/a')}")
        lines.append(f"- Global innovations: {len(root_summary.get('global_innovations', []))}")
    else:
        lines.append("- Root simulation summary not found in outputs/summary.json.")

    if metrics_rows:
        alive_values = [_safe_float(row.get("population_alive")) for row in metrics_rows]
        births = [_safe_float(row.get("births")) for row in metrics_rows]
        deaths = [_safe_float(row.get("deaths")) for row in metrics_rows]
        water = [_safe_float(row.get("water_abundance")) for row in metrics_rows]
        food = [_safe_float(row.get("food_abundance")) for row in metrics_rows]

        alive_clean = [value for value in alive_values if value is not None]
        births_clean = [value for value in births if value is not None]
        deaths_clean = [value for value in deaths if value is not None]
        water_clean = [value for value in water if value is not None]
        food_clean = [value for value in food if value is not None]

        lines.append(f"- Peak alive population: {int(max(alive_clean)) if alive_clean else 'n/a'}")
        lines.append(f"- Total births logged: {int(sum(births_clean)) if births_clean else 'n/a'}")
        lines.append(f"- Total deaths logged: {int(sum(deaths_clean)) if deaths_clean else 'n/a'}")
        lines.append(f"- Minimum water abundance: {_fmt_float(min(water_clean) if water_clean else None)}")
        lines.append(f"- Minimum food abundance: {_fmt_float(min(food_clean) if food_clean else None)}")

    action_counts: Counter[str] = event_snapshot["action_counts"]
    if action_counts:
        top_actions = action_counts.most_common(5)
        lines.append("- Top actions observed:")
        for action, count in top_actions:
            lines.append(f"  - {action}: {count}")
    lines.append("")

    lines.append("## NEAT Scoreboard")
    lines.append("")
    if not neat_rows:
        lines.append("No NEAT runs found under outputs/.")
        lines.append("")
    else:
        lines.append("| Rank | Run | Hist/Gen | Complete | Winner Fitness | Robust Mean | Robust Min | Robust Max | Difficulty | Shock Prob |")
        lines.append("| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |")
        for idx, row in enumerate(neat_rows[:8], start=1):
            generations = row.get("generations")
            history_points = row.get("history_points")
            hist_gen = "n/a"
            if isinstance(history_points, int) and isinstance(generations, int):
                hist_gen = f"{history_points}/{generations}"
            complete = "yes" if row.get("run_completed") else "no"

            lines.append(
                "| "
                f"{idx} | "
                f"{row['run']} | "
                f"{hist_gen} | "
                f"{complete} | "
                f"{_fmt_float(row.get('winner_fitness'))} | "
                f"{_fmt_float(row.get('robustness_mean'))} | "
                f"{_fmt_float(row.get('robustness_min'))} | "
                f"{_fmt_float(row.get('robustness_max'))} | "
                f"{_fmt_float(row.get('world_difficulty'))} | "
                f"{_fmt_float(row.get('shock_probability'))} |"
            )
        lines.append("")

        full_rows = [row for row in neat_rows if row.get("run_completed")]
        selection_pool = full_rows if full_rows else neat_rows
        best = selection_pool[0]
        best_history = best.get("history") if isinstance(best.get("history"), list) else []
        best_robust = best.get("robustness") if isinstance(best.get("robustness"), dict) else {}
        robustness_episodes = best_robust.get("episodes")
        episodes = robustness_episodes if isinstance(robustness_episodes, list) else []
        extinctions = [ep for ep in episodes if isinstance(ep, dict) and ep.get("extinction_day") is not None]

        lines.append("## Champion Narrative")
        lines.append("")
        lines.append(f"- Best run: {best['run']}")
        lines.append(
            "- Champion selection pool: "
            f"{'full-generation runs only' if full_rows else 'all runs (no full-generation runs available)'}"
        )
        lines.append(f"- Winner fitness: {_fmt_float(best.get('winner_fitness'))}")
        lines.append(f"- Robustness mean/min/max: {_fmt_float(best.get('robustness_mean'))} / {_fmt_float(best.get('robustness_min'))} / {_fmt_float(best.get('robustness_max'))}")
        lines.append(f"- Comparable summary path: {best.get('summary_path')}")
        if episodes:
            lines.append(f"- Robustness episodes with extinction: {len(extinctions)}/{len(episodes)}")

        lines.append("")
        lines.append("### Fitness Timeline (Best Run)")
        lines.append("")
        timeline_lines = _fitness_timeline(best_history)
        if timeline_lines:
            lines.append("```text")
            lines.extend(timeline_lines)
            lines.append("```")
        else:
            lines.append("No history timeline available.")
        lines.append("")

        lines.append("### Turning Points")
        lines.append("")
        points = _history_turning_points(best_history)
        if points:
            for point in points:
                lines.append(f"- {point}")
        else:
            lines.append("- No turning points available from history data.")
        lines.append("")

        key = _group_key(best)
        comparable = [row for row in selection_pool if _group_key(row) == key]
        lines.append("### Stability Read")
        lines.append("")
        lines.append(f"- Comparable run count (same difficulty/shock/eval/pop): {len(comparable)}")
        lines.append(f"- {_compute_group_variance(comparable)}")
        lines.append("")

    lines.append("## Observer Protocol (Next Session)")
    lines.append("")
    lines.append("1. Run one new seed with fixed hard-mode parameters.")
    lines.append("2. Rebuild NEAT comparison leaderboard.")
    lines.append("3. Rebuild this observatory report and inspect variance + turning points.")
    lines.append("")
    lines.append("Command template:")
    lines.append("")
    lines.append("```bash")
    lines.append(".venv/bin/python run_neat_training.py --generations 8 --eval-days 650 --max-population 220 --world-difficulty 1.45 --shock-prob 0.02 --robustness-seeds 6 --robustness-days 450 --robustness-founders 24 --checkpoint-every 4 --seed <NEW_SEED> --output-dir outputs/neat_stage2_hard_run<NAME>")
    lines.append(".venv/bin/python scripts/compare_neat_runs.py --require-full-generations")
    lines.append(".venv/bin/python scripts/build_experiment_observatory.py")
    lines.append("```")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a watch-oriented experiment report from output artifacts")
    parser.add_argument("--outputs-dir", type=str, default="outputs", help="Directory containing run outputs")
    parser.add_argument(
        "--report-path",
        type=str,
        default="outputs/experiment_observatory.md",
        help="Path to write observatory report",
    )
    args = parser.parse_args()

    outputs_dir = Path(args.outputs_dir)
    report_path = Path(args.report_path)
    build_report(outputs_dir=outputs_dir, report_path=report_path)
    print(f"Wrote observatory report: {report_path}")


if __name__ == "__main__":
    main()