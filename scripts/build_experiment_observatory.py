from __future__ import annotations

import argparse
import csv
from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import random
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


def _safe_int(value) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return None
    return None


def _fmt_float(value, digits: int = 3) -> str:
    cast = _safe_float(value)
    if cast is None:
        return "n/a"
    return f"{cast:.{digits}f}"


def _fmt_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{(value * 100.0):.1f}%"


def _percentile(sorted_values: List[float], q: float) -> float | None:
    if not sorted_values:
        return None
    if q <= 0.0:
        return sorted_values[0]
    if q >= 1.0:
        return sorted_values[-1]

    index = q * (len(sorted_values) - 1)
    lo = int(math.floor(index))
    hi = int(math.ceil(index))
    if lo == hi:
        return sorted_values[lo]

    weight = index - lo
    return sorted_values[lo] * (1.0 - weight) + sorted_values[hi] * weight


def _sample_variance(values: List[float]) -> float | None:
    if len(values) < 2:
        return None
    avg = mean(values)
    return sum((value - avg) ** 2 for value in values) / float(len(values) - 1)


def _cohens_d(group_a: List[float], group_b: List[float]) -> float | None:
    if len(group_a) < 2 or len(group_b) < 2:
        return None

    var_a = _sample_variance(group_a)
    var_b = _sample_variance(group_b)
    if var_a is None or var_b is None:
        return None

    n_a = len(group_a)
    n_b = len(group_b)
    pooled_var = ((n_a - 1) * var_a + (n_b - 1) * var_b) / float(n_a + n_b - 2)
    if pooled_var <= 1e-12:
        return None

    return (mean(group_a) - mean(group_b)) / math.sqrt(pooled_var)


def _bootstrap_mean_diff_ci(
    group_a: List[float],
    group_b: List[float],
    *,
    iterations: int = 1200,
    alpha: float = 0.05,
    seed: int = 1337,
) -> Tuple[float | None, float | None]:
    if not group_a or not group_b:
        return (None, None)

    rng = random.Random(seed)
    n_a = len(group_a)
    n_b = len(group_b)
    diffs: List[float] = []

    for _ in range(max(200, iterations)):
        sample_a = [group_a[rng.randrange(n_a)] for _ in range(n_a)]
        sample_b = [group_b[rng.randrange(n_b)] for _ in range(n_b)]
        diffs.append(mean(sample_a) - mean(sample_b))

    diffs.sort()
    lower = _percentile(diffs, alpha / 2.0)
    upper = _percentile(diffs, 1.0 - (alpha / 2.0))
    return (lower, upper)


def _bootstrap_relative_delta_ci(
    group_a: List[float],
    group_b: List[float],
    *,
    iterations: int = 1200,
    alpha: float = 0.05,
    seed: int = 1441,
) -> Tuple[float | None, float | None]:
    if not group_a or not group_b:
        return (None, None)

    rng = random.Random(seed)
    n_a = len(group_a)
    n_b = len(group_b)
    ratios: List[float] = []

    for _ in range(max(200, iterations)):
        sample_a = [group_a[rng.randrange(n_a)] for _ in range(n_a)]
        sample_b = [group_b[rng.randrange(n_b)] for _ in range(n_b)]
        mean_a = mean(sample_a)
        mean_b = mean(sample_b)
        if abs(mean_b) < 1e-9:
            continue
        ratios.append((mean_a - mean_b) / abs(mean_b))

    if not ratios:
        return (None, None)

    ratios.sort()
    lower = _percentile(ratios, alpha / 2.0)
    upper = _percentile(ratios, 1.0 - (alpha / 2.0))
    return (lower, upper)


def _corr_ci(corr: float, n: int) -> Tuple[float | None, float | None]:
    if n <= 3:
        return (None, None)

    clipped = max(-0.999999, min(0.999999, corr))
    fisher = 0.5 * math.log((1.0 + clipped) / (1.0 - clipped))
    se = 1.0 / math.sqrt(float(n - 3))
    low = fisher - (1.96 * se)
    high = fisher + (1.96 * se)
    return (math.tanh(low), math.tanh(high))


def _fmt_ci(value_low: float | None, value_high: float | None, digits: int = 3) -> str:
    if value_low is None or value_high is None:
        return "n/a"
    return f"[{value_low:.{digits}f}, {value_high:.{digits}f}]"


def _fmt_pct_ci(value_low: float | None, value_high: float | None) -> str:
    if value_low is None or value_high is None:
        return "n/a"
    return f"[{value_low * 100.0:+.1f}%, {value_high * 100.0:+.1f}%]"


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

        try:
            run_mtime_epoch = float(child.stat().st_mtime)
        except OSError:
            run_mtime_epoch = None

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
                "run_mtime_epoch": run_mtime_epoch,
                "summary": summary,
                "history": history_rows,
                "robustness": robustness_obj,
                "curriculum_enabled": summary.get("curriculum_enabled")
                if isinstance(summary.get("curriculum_enabled"), bool)
                else None,
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


def _group_key_label(key: Tuple[object, object, object, object]) -> str:
    difficulty, shock, eval_days, max_population = key
    return (
        f"difficulty={_fmt_float(difficulty)} "
        f"shock={_fmt_float(shock)} "
        f"eval_days={eval_days if eval_days is not None else 'n/a'} "
        f"max_population={max_population if max_population is not None else 'n/a'}"
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


def _select_largest_campaign(rows: List[Dict[str, object]]) -> Tuple[List[Dict[str, object]], str]:
    groups: Dict[Tuple[object, object, object, object], List[Dict[str, object]]] = {}
    for row in rows:
        key = _group_key(row)
        groups.setdefault(key, []).append(row)

    if not groups:
        return rows, "all_runs"

    best_key = max(groups.keys(), key=lambda key: len(groups[key]))
    best_group = groups[best_key]
    return best_group, _group_key_label(best_key)


def _sample_history_rows(
    history_rows: List[Dict[str, object]],
    max_points: int = 8,
) -> List[Dict[str, object]]:
    if len(history_rows) <= max_points:
        return history_rows

    last_index = len(history_rows) - 1
    indices = {
        int(round((idx * last_index) / float(max_points - 1)))
        for idx in range(max_points)
    }
    return [history_rows[idx] for idx in sorted(indices)]


def _robustness_score_spread_ratio(episodes: List[Dict[str, object]]) -> float | None:
    scores = [
        _safe_float(episode.get("score"))
        for episode in episodes
        if isinstance(episode, dict)
    ]
    clean = [score for score in scores if score is not None and score > 0]
    if len(clean) < 2:
        return None
    low = min(clean)
    high = max(clean)
    if low <= 0:
        return None
    return high / low


def _infer_policy_family_tags(row: Dict[str, object]) -> List[str]:
    tags: List[str] = []

    robustness_obj = row.get("robustness") if isinstance(row.get("robustness"), dict) else {}
    episodes_obj = robustness_obj.get("episodes")
    episodes = episodes_obj if isinstance(episodes_obj, list) else []

    if not episodes:
        tags.append("no_robustness_data")
    else:
        extinction_days = [
            _safe_int(ep.get("extinction_day"))
            for ep in episodes
            if isinstance(ep, dict)
        ]
        ext_clean = [day for day in extinction_days if day is not None]
        if ext_clean and len(ext_clean) == len(episodes):
            tags.append("extinction_prone")
        elif ext_clean:
            tags.append("partial_survivor")
        else:
            tags.append("survivor_regime")

        mean_alive = _safe_float(robustness_obj.get("mean_alive_end"))
        if mean_alive is not None and mean_alive >= 4:
            tags.append("high_survivorship")
        elif mean_alive is not None and mean_alive <= 0.5:
            tags.append("terminal_end_state")

        mean_innov = _safe_float(robustness_obj.get("mean_innovations"))
        if mean_innov is not None and mean_innov >= 5:
            tags.append("innovation_rich")
        elif mean_innov is not None and mean_innov <= 1.5:
            tags.append("innovation_sparse")

        spread = _robustness_score_spread_ratio(episodes)
        if spread is not None and spread >= 5.0:
            tags.append("brittle_high_variance")
        elif spread is not None and spread <= 2.0:
            tags.append("stable_variance")

    history_rows = row.get("history") if isinstance(row.get("history"), list) else []
    alive_values = [_safe_int(hist.get("alive_end")) for hist in history_rows if isinstance(hist, dict)]
    alive_clean = [value for value in alive_values if value is not None]

    shock_values = [_safe_float(hist.get("shock_days")) for hist in history_rows if isinstance(hist, dict)]
    shock_clean = [value for value in shock_values if value is not None]
    if alive_clean and shock_clean:
        if max(shock_clean) >= 20 and max(alive_clean) >= 2:
            tags.append("shock_tolerant")

    if row.get("run_completed") is False:
        tags.append("truncated_eval")

    deduped = []
    seen = set()
    for tag in tags:
        if tag in seen:
            continue
        seen.add(tag)
        deduped.append(tag)

    return deduped if deduped else ["unclassified"]


def _compact_lineage_timeline(history_rows: List[Dict[str, object]], max_points: int = 8) -> str:
    sampled = _sample_history_rows(history_rows, max_points=max_points)
    chunks: List[str] = []
    for row in sampled:
        generation = _safe_int(row.get("generation"))
        if generation is None:
            continue

        alive_end = _safe_int(row.get("alive_end"))
        shock_days = _safe_int(row.get("shock_days"))
        culture = _safe_float(row.get("mean_culture_size"))
        best = _safe_float(row.get("best_fitness"))

        alive_text = str(alive_end) if alive_end is not None else "?"
        shock_text = str(shock_days) if shock_days is not None else "?"
        culture_text = f"{culture:.1f}" if culture is not None else "?"
        best_text = f"{best:.0f}" if best is not None else "?"

        chunks.append(
            f"g{generation}[a{alive_text}/s{shock_text}/c{culture_text}/b{best_text}]"
        )

    if not chunks:
        return "n/a"
    return " -> ".join(chunks)


def _primary_family_cluster(tags: List[str]) -> str:
    if "survivor_regime" in tags and "high_survivorship" in tags:
        return "resilient_survivor"
    if "survivor_regime" in tags:
        return "survivor_regime"
    if "partial_survivor" in tags:
        return "partial_survivor"
    if "extinction_prone" in tags and "innovation_rich" in tags:
        return "innovator_fragile"
    if "extinction_prone" in tags:
        return "fragile_extinction"
    if "brittle_high_variance" in tags:
        return "brittle_mixed"
    return "mixed"


def _chronological_runs(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    with_time = [row for row in rows if isinstance(row.get("run_mtime_epoch"), (int, float))]
    if len(with_time) >= 2:
        return sorted(
            rows,
            key=lambda row: row.get("run_mtime_epoch")
            if isinstance(row.get("run_mtime_epoch"), (int, float))
            else float("inf"),
        )
    return sorted(rows, key=lambda row: str(row.get("run", "")))


def _cluster_share_table(rows: List[Dict[str, object]]) -> Dict[str, float]:
    if not rows:
        return {}
    counts: Counter[str] = Counter()
    for row in rows:
        tags = _infer_policy_family_tags(row)
        cluster = _primary_family_cluster(tags)
        counts[cluster] += 1
    total = float(sum(counts.values()))
    if total <= 0:
        return {}
    return {cluster: count / total for cluster, count in counts.items()}


def _compute_lineage_cluster_drift(rows: List[Dict[str, object]]) -> Dict[str, object] | None:
    if len(rows) < 4:
        return None

    ordered = _chronological_runs(rows)
    midpoint = len(ordered) // 2
    early = ordered[:midpoint]
    late = ordered[midpoint:]
    if not early or not late:
        return None

    early_share = _cluster_share_table(early)
    late_share = _cluster_share_table(late)

    clusters = sorted(set(early_share.keys()) | set(late_share.keys()))
    if not clusters:
        return None

    deltas: Dict[str, float] = {}
    for cluster in clusters:
        deltas[cluster] = late_share.get(cluster, 0.0) - early_share.get(cluster, 0.0)

    drift_score = 0.5 * sum(abs(deltas[cluster]) for cluster in clusters)
    if drift_score <= 0.25:
        drift_label = "stable"
    elif drift_score <= 0.5:
        drift_label = "moderate"
    else:
        drift_label = "high"

    increase_cluster = max(clusters, key=lambda cluster: deltas[cluster])
    decrease_cluster = min(clusters, key=lambda cluster: deltas[cluster])

    early_robust = [
        _safe_float(row.get("robustness_mean"))
        for row in early
    ]
    early_robust_clean = [value for value in early_robust if value is not None]
    late_robust = [
        _safe_float(row.get("robustness_mean"))
        for row in late
    ]
    late_robust_clean = [value for value in late_robust if value is not None]

    early_robust_mean = mean(early_robust_clean) if early_robust_clean else None
    late_robust_mean = mean(late_robust_clean) if late_robust_clean else None
    robust_delta = None
    if early_robust_mean is not None and late_robust_mean is not None:
        robust_delta = late_robust_mean - early_robust_mean

    trace_items: List[str] = []
    for row in ordered:
        tags = _infer_policy_family_tags(row)
        cluster = _primary_family_cluster(tags)
        trace_items.append(f"{row['run']}:{cluster}")

    return {
        "run_count": len(ordered),
        "early_count": len(early),
        "late_count": len(late),
        "clusters": clusters,
        "early_share": early_share,
        "late_share": late_share,
        "deltas": deltas,
        "drift_score": drift_score,
        "drift_label": drift_label,
        "increase_cluster": increase_cluster,
        "decrease_cluster": decrease_cluster,
        "early_robust_mean": early_robust_mean,
        "late_robust_mean": late_robust_mean,
        "early_robust_values": early_robust_clean,
        "late_robust_values": late_robust_clean,
        "robust_delta": robust_delta,
        "trace": trace_items,
    }


def _pearson_correlation(x_values: List[float], y_values: List[float]) -> float | None:
    if len(x_values) != len(y_values) or len(x_values) < 2:
        return None

    mean_x = mean(x_values)
    mean_y = mean(y_values)
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_values, y_values))
    var_x = sum((x - mean_x) ** 2 for x in x_values)
    var_y = sum((y - mean_y) ** 2 for y in y_values)
    if var_x <= 1e-12 or var_y <= 1e-12:
        return None
    return cov / ((var_x * var_y) ** 0.5)


def _status_from_delta(delta: float, pass_threshold: float = 0.1) -> str:
    if delta >= pass_threshold:
        return "PASS"
    if delta <= -pass_threshold:
        return "FAIL"
    return "INCONCLUSIVE"


def _select_best_curriculum_group(
    rows: List[Dict[str, object]],
) -> Tuple[Tuple[object, object, object, object] | None, List[Dict[str, object]], int]:
    comparable_groups: Dict[Tuple[object, object, object, object], List[Dict[str, object]]] = {}
    for row in rows:
        if row.get("run_completed"):
            comparable_groups.setdefault(_group_key(row), []).append(row)

    best_group_rows: List[Dict[str, object]] = []
    best_group_key: Tuple[object, object, object, object] | None = None
    best_pair_count = 0
    for key, group_rows in comparable_groups.items():
        curriculum_vals = [
            _safe_float(row.get("robustness_mean"))
            for row in group_rows
            if row.get("curriculum_enabled") is True
        ]
        baseline_vals = [
            _safe_float(row.get("robustness_mean"))
            for row in group_rows
            if row.get("curriculum_enabled") is False
        ]
        curriculum_clean = [value for value in curriculum_vals if value is not None]
        baseline_clean = [value for value in baseline_vals if value is not None]
        pair_count = min(len(curriculum_clean), len(baseline_clean))
        if pair_count > best_pair_count:
            best_pair_count = pair_count
            best_group_rows = group_rows
            best_group_key = key

    return best_group_key, best_group_rows, best_pair_count


def _build_hypothesis_cards(
    rows: List[Dict[str, object]],
    drift: Dict[str, object] | None,
) -> List[Dict[str, object]]:
    cards: List[Dict[str, object]] = []

    # H1: Curriculum vs non-curriculum under comparable settings.
    best_group_key, best_group_rows, best_pair_count = _select_best_curriculum_group(rows)

    if best_pair_count == 0 or best_group_key is None:
        cards.append(
            {
                "id": "h1_curriculum",
                "title": "Curriculum Improves Robustness",
                "status": "INCONCLUSIVE",
                "evidence": "No comparable curriculum/non-curriculum run pair in the same campaign settings.",
                "next_action": "Run one baseline and one curriculum run with identical settings and different seeds.",
                "n_curr": 0,
                "n_base": 0,
            }
        )
    else:
        curriculum_clean = [
            float(row.get("robustness_mean"))
            for row in best_group_rows
            if row.get("curriculum_enabled") is True and isinstance(row.get("robustness_mean"), float)
        ]
        baseline_clean = [
            float(row.get("robustness_mean"))
            for row in best_group_rows
            if row.get("curriculum_enabled") is False and isinstance(row.get("robustness_mean"), float)
        ]
        curr_mean = mean(curriculum_clean)
        base_mean = mean(baseline_clean)
        delta = 0.0 if abs(base_mean) < 1e-9 else (curr_mean - base_mean) / abs(base_mean)
        delta_ci_low, delta_ci_high = _bootstrap_relative_delta_ci(curriculum_clean, baseline_clean)
        diff_ci_low, diff_ci_high = _bootstrap_mean_diff_ci(curriculum_clean, baseline_clean)
        effect_d = _cohens_d(curriculum_clean, baseline_clean)
        cards.append(
            {
                "id": "h1_curriculum",
                "title": "Curriculum Improves Robustness",
                "status": _status_from_delta(delta, pass_threshold=0.1),
                "evidence": (
                    f"Scope={_group_key_label(best_group_key)}; "
                    f"n_curr={len(curriculum_clean)}, n_base={len(baseline_clean)}; "
                    f"curriculum_mean={curr_mean:.3f}, baseline_mean={base_mean:.3f}, "
                    f"delta={delta * 100.0:+.1f}% (95% CI { _fmt_pct_ci(delta_ci_low, delta_ci_high) }); "
                    f"mean_diff_CI={_fmt_ci(diff_ci_low, diff_ci_high)}; effect_d={_fmt_float(effect_d)}."
                ),
                "next_action": "Increase seed count in both groups to reduce variance before finalizing.",
                "n_curr": len(curriculum_clean),
                "n_base": len(baseline_clean),
                "delta": delta,
                "delta_ci_low": delta_ci_low,
                "delta_ci_high": delta_ci_high,
                "effect_d": effect_d,
            }
        )

    # H2: Innovation-rich families outperform innovation-sparse families.
    rich_values: List[float] = []
    sparse_values: List[float] = []
    for row in rows:
        robust = _safe_float(row.get("robustness_mean"))
        if robust is None:
            continue
        tags = _infer_policy_family_tags(row)
        if "innovation_rich" in tags:
            rich_values.append(robust)
        if "innovation_sparse" in tags:
            sparse_values.append(robust)

    if rich_values and sparse_values:
        rich_mean = mean(rich_values)
        sparse_mean = mean(sparse_values)
        delta = 0.0 if abs(sparse_mean) < 1e-9 else (rich_mean - sparse_mean) / abs(sparse_mean)
        delta_ci_low, delta_ci_high = _bootstrap_relative_delta_ci(rich_values, sparse_values)
        diff_ci_low, diff_ci_high = _bootstrap_mean_diff_ci(rich_values, sparse_values)
        effect_d = _cohens_d(rich_values, sparse_values)
        cards.append(
            {
                "id": "h2_innovation",
                "title": "Innovation-Rich Policies Outperform Innovation-Sparse Policies",
                "status": _status_from_delta(delta, pass_threshold=0.1),
                "evidence": (
                    f"n_rich={len(rich_values)}, n_sparse={len(sparse_values)}; "
                    f"innovation_rich_mean={rich_mean:.3f}, innovation_sparse_mean={sparse_mean:.3f}, "
                    f"delta={delta * 100.0:+.1f}% (95% CI { _fmt_pct_ci(delta_ci_low, delta_ci_high) }); "
                    f"mean_diff_CI={_fmt_ci(diff_ci_low, diff_ci_high)}; effect_d={_fmt_float(effect_d)}."
                ),
                "next_action": "Check if innovation gains persist when shock probability is increased.",
                "n_rich": len(rich_values),
                "n_sparse": len(sparse_values),
                "delta": delta,
                "delta_ci_low": delta_ci_low,
                "delta_ci_high": delta_ci_high,
                "effect_d": effect_d,
            }
        )
    else:
        cards.append(
            {
                "id": "h2_innovation",
                "title": "Innovation-Rich Policies Outperform Innovation-Sparse Policies",
                "status": "INCONCLUSIVE",
                "evidence": "Not enough runs tagged as both innovation_rich and innovation_sparse.",
                "next_action": "Run more seeds until both families are represented with robustness metrics.",
                "n_rich": len(rich_values),
                "n_sparse": len(sparse_values),
            }
        )

    # H3: Higher survivorship predicts stronger robustness.
    alive_values: List[float] = []
    robust_values: List[float] = []
    for row in rows:
        robustness_obj = row.get("robustness") if isinstance(row.get("robustness"), dict) else {}
        mean_alive = _safe_float(robustness_obj.get("mean_alive_end"))
        robust = _safe_float(row.get("robustness_mean"))
        if mean_alive is None or robust is None:
            continue
        alive_values.append(mean_alive)
        robust_values.append(robust)

    corr = _pearson_correlation(alive_values, robust_values)
    if corr is None:
        cards.append(
            {
                "id": "h3_survivorship",
                "title": "Survivorship Correlates With Robustness",
                "status": "INCONCLUSIVE",
                "evidence": "Insufficient non-degenerate data for correlation.",
                "next_action": "Collect more runs with varied mean_alive_end values.",
                "n_pairs": len(alive_values),
            }
        )
    else:
        if corr >= 0.35:
            status = "PASS"
        elif corr <= -0.15:
            status = "FAIL"
        else:
            status = "INCONCLUSIVE"
        corr_ci_low, corr_ci_high = _corr_ci(corr, len(alive_values))
        r_squared = corr * corr
        cards.append(
            {
                "id": "h3_survivorship",
                "title": "Survivorship Correlates With Robustness",
                "status": status,
                "evidence": (
                    "pearson_corr(mean_alive_end, robustness_mean)="
                    f"{corr:+.3f} (95% CI {_fmt_ci(corr_ci_low, corr_ci_high)}) "
                    f"across {len(alive_values)} runs; r_squared={r_squared:.3f}."
                ),
                "next_action": "Use this signal to tune fitness weighting for alive_end vs innovation pressure.",
                "n_pairs": len(alive_values),
                "corr": corr,
                "corr_ci_low": corr_ci_low,
                "corr_ci_high": corr_ci_high,
                "r_squared": r_squared,
            }
        )

    # H4: Drift and robustness should improve together.
    if drift is None:
        cards.append(
            {
                "id": "h4_drift",
                "title": "Campaign Drift Is Productive",
                "status": "INCONCLUSIVE",
                "evidence": "No drift block available for this campaign.",
                "next_action": "Ensure at least four completed comparable runs for drift analysis.",
                "run_count": 0,
            }
        )
    else:
        drift_score = _safe_float(drift.get("drift_score"))
        robust_delta = _safe_float(drift.get("robust_delta"))
        early_robust_values = [
            value
            for value in (drift.get("early_robust_values") or [])
            if isinstance(value, (int, float))
        ]
        late_robust_values = [
            value
            for value in (drift.get("late_robust_values") or [])
            if isinstance(value, (int, float))
        ]
        robust_ci_low, robust_ci_high = _bootstrap_mean_diff_ci(late_robust_values, early_robust_values)
        robust_effect_d = _cohens_d(late_robust_values, early_robust_values)
        if drift_score is None or robust_delta is None:
            status = "INCONCLUSIVE"
        elif drift_score <= 0.6 and robust_delta > 0:
            status = "PASS"
        elif drift_score > 0.8 and robust_delta <= 0:
            status = "FAIL"
        else:
            status = "INCONCLUSIVE"
        cards.append(
            {
                "id": "h4_drift",
                "title": "Campaign Drift Is Productive",
                "status": status,
                "evidence": (
                    f"drift_score={_fmt_float(drift_score)} ({drift.get('drift_label', 'n/a')}), "
                    f"robust_delta={_fmt_float(robust_delta)} "
                    f"(95% CI {_fmt_ci(robust_ci_low, robust_ci_high)}), "
                    f"effect_d={_fmt_float(robust_effect_d)}."
                ),
                "next_action": "If inconclusive, add seeds and compare with a fixed no-curriculum ablation group.",
                "run_count": drift.get("run_count"),
                "drift_score": drift_score,
                "robust_delta": robust_delta,
                "robust_ci_low": robust_ci_low,
                "robust_ci_high": robust_ci_high,
                "effect_d": robust_effect_d,
            }
        )

    return cards


def _clip01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _ci_width(ci_low: float | None, ci_high: float | None) -> float | None:
    if ci_low is None or ci_high is None:
        return None
    return max(0.0, ci_high - ci_low)


def _score_intervention(
    expected_upside: float,
    confidence: float,
    downside_risk: float,
) -> float:
    upside_term = expected_upside * (0.6 + (0.4 * confidence))
    risk_term = downside_risk * (0.5 + (0.5 * (1.0 - confidence)))
    return upside_term - risk_term


def _build_ranked_interventions(
    cards: List[Dict[str, object]],
    rows: List[Dict[str, object]],
    outcomes: List[Dict[str, object]] | None = None,
) -> List[Dict[str, object]]:
    del rows

    outcome_by_family: Dict[str, Dict[str, object]] = {}
    if outcomes:
        for outcome in outcomes:
            family = outcome.get("family")
            if isinstance(family, str):
                outcome_by_family[family] = outcome

    card_by_id = {
        str(card.get("id")): card
        for card in cards
        if isinstance(card.get("id"), str)
    }

    candidates: List[Dict[str, object]] = []

    h1 = card_by_id.get("h1_curriculum")
    if h1 is not None:
        status = str(h1.get("status", "INCONCLUSIVE"))
        n_curr = _safe_int(h1.get("n_curr")) or 0
        n_base = _safe_int(h1.get("n_base")) or 0
        n_total = n_curr + n_base
        delta = _safe_float(h1.get("delta"))
        effect_d = abs(_safe_float(h1.get("effect_d")) or 0.0)
        ci_low = _safe_float(h1.get("delta_ci_low"))
        ci_high = _safe_float(h1.get("delta_ci_high"))
        ci_w = _ci_width(ci_low, ci_high)

        sample_factor = _clip01(n_total / 50.0)
        ci_precision = _clip01(1.0 - min(1.0, (ci_w or 1.0) / 0.6))
        confidence = _clip01((0.6 * sample_factor) + (0.4 * ci_precision))

        if status in {"FAIL", "INCONCLUSIVE"}:
            expected_upside = _clip01(0.35 + min(0.45, abs(delta or 0.0) * 2.0) + min(0.2, effect_d / 3.0))
            downside = 0.18 if status == "FAIL" else 0.12
            action = "Run a matched curriculum-vs-baseline ablation extension (+8 seeds) under fixed settings."
            rationale = (
                "Curriculum uncertainty is still decision-critical; narrowing CI is likely to change world-regime policy decisions."
            )
            candidates.append(
                {
                    "action": action,
                    "expected_upside": expected_upside,
                    "confidence": confidence,
                    "downside_risk": downside,
                    "rationale": rationale,
                    "source": "h1_curriculum",
                }
            )

    h2 = card_by_id.get("h2_innovation")
    if h2 is not None:
        status = str(h2.get("status", "INCONCLUSIVE"))
        n_rich = _safe_int(h2.get("n_rich")) or 0
        n_sparse = _safe_int(h2.get("n_sparse")) or 0
        n_total = n_rich + n_sparse
        delta = _safe_float(h2.get("delta"))
        effect_d = abs(_safe_float(h2.get("effect_d")) or 0.0)
        ci_w = _ci_width(_safe_float(h2.get("delta_ci_low")), _safe_float(h2.get("delta_ci_high")))

        sample_factor = _clip01(n_total / 100.0)
        ci_precision = _clip01(1.0 - min(1.0, (ci_w or 1.2) / 1.5))
        confidence = _clip01((0.7 * sample_factor) + (0.3 * ci_precision))

        expected_upside = _clip01(0.2 + min(0.4, abs(delta or 0.0) / 2.0) + min(0.25, effect_d / 10.0))
        downside = 0.22 if status == "PASS" else 0.16
        action = "Execute a shock-probability sweep (0.02/0.03/0.04) to verify innovation advantage stability."
        rationale = "Innovation gains are strong but need stress validation before being trusted as a general mechanism."
        candidates.append(
            {
                "action": action,
                "expected_upside": expected_upside,
                "confidence": confidence,
                "downside_risk": downside,
                "rationale": rationale,
                "source": "h2_innovation",
            }
        )

    h3 = card_by_id.get("h3_survivorship")
    if h3 is not None:
        status = str(h3.get("status", "INCONCLUSIVE"))
        corr = _safe_float(h3.get("corr"))
        n_pairs = _safe_int(h3.get("n_pairs")) or 0
        ci_w = _ci_width(_safe_float(h3.get("corr_ci_low")), _safe_float(h3.get("corr_ci_high")))

        sample_factor = _clip01(n_pairs / 160.0)
        ci_precision = _clip01(1.0 - min(1.0, (ci_w or 0.6) / 0.6))
        confidence = _clip01((0.7 * sample_factor) + (0.3 * ci_precision))

        if status in {"FAIL", "INCONCLUSIVE"}:
            expected_upside = _clip01(0.25 + min(0.45, abs(corr or 0.0)) )
            downside = 0.28
            action = "Run a fitness-weight sweep on alive_end vs innovation terms and re-test robustness correlation."
            rationale = "Reward-shaping leverage is high when survivorship linkage is weak or uncertain."
            candidates.append(
                {
                    "action": action,
                    "expected_upside": expected_upside,
                    "confidence": confidence,
                    "downside_risk": downside,
                    "rationale": rationale,
                    "source": "h3_survivorship",
                }
            )

    h4 = card_by_id.get("h4_drift")
    if h4 is not None:
        status = str(h4.get("status", "INCONCLUSIVE"))
        run_count = _safe_int(h4.get("run_count")) or 0
        robust_delta = _safe_float(h4.get("robust_delta"))
        effect_d = abs(_safe_float(h4.get("effect_d")) or 0.0)
        ci_w = _ci_width(_safe_float(h4.get("robust_ci_low")), _safe_float(h4.get("robust_ci_high")))

        sample_factor = _clip01(run_count / 60.0)
        ci_precision = _clip01(1.0 - min(1.0, (ci_w or 7000.0) / 9000.0))
        confidence = _clip01((0.65 * sample_factor) + (0.35 * ci_precision))

        if status in {"FAIL", "INCONCLUSIVE"}:
            expected_upside = _clip01(0.2 + min(0.35, abs((robust_delta or 0.0)) / 8000.0) + min(0.25, effect_d / 2.5))
            downside = 0.2
            action = "Run one fixed-setting stabilization cohort before introducing further ecology complexity."
            rationale = "Controls drift while preserving the ability to attribute gains to concrete changes."
            candidates.append(
                {
                    "action": action,
                    "expected_upside": expected_upside,
                    "confidence": confidence,
                    "downside_risk": downside,
                    "rationale": rationale,
                    "source": "h4_drift",
                }
            )

    candidates.append(
        {
            "action": "Continue fixed-condition monitoring with periodic hypothesis refresh.",
            "expected_upside": 0.18,
            "confidence": 0.9,
            "downside_risk": 0.06,
            "rationale": "Maintains a stable baseline while higher-impact interventions are tested.",
            "source": "baseline",
        }
    )

    for candidate in candidates:
        upside = _clip01(float(candidate["expected_upside"]))
        confidence = _clip01(float(candidate["confidence"]))
        downside = _clip01(float(candidate["downside_risk"]))

        source = str(candidate.get("source", ""))
        outcome = outcome_by_family.get(source)
        if outcome:
            outcome_status = str(outcome.get("status", "INCONCLUSIVE"))
            outcome_effect = abs(_safe_float(outcome.get("effect_d")) or 0.0)
            if outcome_status == "PASS":
                upside = _clip01(upside + min(0.08, outcome_effect / 20.0))
                downside = _clip01(max(0.0, downside - 0.04))
            elif outcome_status == "FAIL":
                upside = _clip01(max(0.0, upside - min(0.08, outcome_effect / 20.0)))
                downside = _clip01(downside + 0.08)

            outcome_runs = _safe_int(outcome.get("runs")) or 0
            confidence = _clip01((0.85 * confidence) + (0.15 * _clip01(outcome_runs / 12.0)))

            rationale = str(candidate.get("rationale", ""))
            candidate["rationale"] = (
                f"{rationale} Historical outcome status: {outcome_status} "
                f"(delta={_fmt_float(_safe_float(outcome.get('delta')))})."
            ).strip()

        candidate["expected_upside"] = upside
        candidate["confidence"] = confidence
        candidate["downside_risk"] = downside
        candidate["priority"] = _score_intervention(upside, confidence, downside)

    deduped: List[Dict[str, object]] = []
    seen_actions = set()
    for candidate in sorted(candidates, key=lambda item: float(item["priority"]), reverse=True):
        action = str(candidate.get("action", ""))
        if not action or action in seen_actions:
            continue
        seen_actions.add(action)
        deduped.append(candidate)

    return deduped


def _build_intervention_recommendations(
    cards: List[Dict[str, object]],
    rows: List[Dict[str, object]],
) -> List[str]:
    ranked = _build_ranked_interventions(cards=cards, rows=rows)
    recommendations: List[str] = []
    for item in ranked[:8]:
        recommendations.append(
            "[priority="
            f"{float(item.get('priority', 0.0)):+.3f}; "
            f"upside={float(item.get('expected_upside', 0.0)):.2f}; "
            f"confidence={float(item.get('confidence', 0.0)):.2f}; "
            f"risk={float(item.get('downside_risk', 0.0)):.2f}] "
            f"{item.get('action')}"
        )

    if not recommendations:
        recommendations.append(
            "No immediate intervention required; continue fixed-condition monitoring and periodic ablation checks."
        )

    return recommendations


def _base_training_params(rows: List[Dict[str, object]]) -> Dict[str, float | int]:
    base = rows[0] if rows else {}

    generations = _safe_int(base.get("generations")) or 40
    eval_days = _safe_int(base.get("eval_days")) or 900
    max_population = _safe_int(base.get("max_population")) or 220
    world_difficulty = _safe_float(base.get("world_difficulty")) or 1.45
    shock_prob = _safe_float(base.get("shock_probability")) or 0.02

    return {
        "generations": generations,
        "eval_days": eval_days,
        "max_population": max_population,
        "world_difficulty": world_difficulty,
        "shock_prob": shock_prob,
        "robustness_seeds": 4,
        "robustness_days": 300,
        "robustness_founders": 24,
        "checkpoint_every": 10,
    }


def _collect_used_seeds(rows: List[Dict[str, object]]) -> set[int]:
    used: set[int] = set()
    for row in rows:
        summary = row.get("summary") if isinstance(row.get("summary"), dict) else {}
        seed = _safe_int(summary.get("seed"))
        if seed is not None:
            used.add(seed)
    return used


def _reserve_seeds(used: set[int], count: int, start_seed: int = 29000) -> List[int]:
    seeds: List[int] = []
    candidate = start_seed
    while len(seeds) < count:
        if candidate not in used:
            seeds.append(candidate)
            used.add(candidate)
        candidate += 1
    return seeds


def _single_train_command(
    *,
    seed_expr: str,
    output_expr: str,
    params: Dict[str, float | int],
    curriculum: bool,
    world_difficulty: float | None = None,
    shock_prob: float | None = None,
) -> str:
    difficulty = world_difficulty if world_difficulty is not None else float(params["world_difficulty"])
    shock = shock_prob if shock_prob is not None else float(params["shock_prob"])

    cmd = (
        ".venv/bin/python run_neat_training.py "
        f"--generations {int(params['generations'])} "
        f"--eval-days {int(params['eval_days'])} "
        f"--max-population {int(params['max_population'])} "
        f"--world-difficulty {difficulty:.3f} "
        f"--shock-prob {shock:.3f} "
        f"--robustness-seeds {int(params['robustness_seeds'])} "
        f"--robustness-days {int(params['robustness_days'])} "
        f"--robustness-founders {int(params['robustness_founders'])} "
        f"--checkpoint-every {int(params['checkpoint_every'])} "
        f"--seed {seed_expr} "
        f"--output-dir {output_expr} "
        "--no-auto-memory-sync"
    )
    if curriculum:
        cmd += " --curriculum"
    return cmd


def _post_batch_commands() -> List[str]:
    return [
        ".venv/bin/python scripts/compare_neat_runs.py --require-full-generations",
        ".venv/bin/python scripts/build_experiment_observatory.py",
        ".venv/bin/python scripts/agi_memory_autosync.py --sync-once --force --outputs-dir outputs --wiki-dir wiki --max-runs 40 --require-full-generations",
    ]


def _intervention_family_from_run_name(run_name: str) -> str | None:
    if run_name.startswith("h1_") or run_name.startswith("h1_match_"):
        return "h1_curriculum"
    if run_name.startswith("h2_"):
        return "h2_innovation"
    if run_name.startswith("h4_"):
        return "h4_drift"
    if run_name.startswith("monitor_"):
        return "baseline"
    return None


def _compute_intervention_outcomes(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    ordered = _chronological_runs(rows)
    family_events: Dict[str, List[Dict[str, object]]] = {}

    for idx, row in enumerate(ordered):
        run_name = str(row.get("run", ""))
        family = _intervention_family_from_run_name(run_name)
        robust = _safe_float(row.get("robustness_mean"))
        if family is None or robust is None:
            continue
        family_events.setdefault(family, []).append(
            {
                "idx": idx,
                "run": run_name,
                "robustness_mean": robust,
            }
        )

    outcomes: List[Dict[str, object]] = []
    for family, events in family_events.items():
        first_idx = min(int(event["idx"]) for event in events)

        baseline_window = ordered[max(0, first_idx - 20):first_idx]
        baseline_values = [
            _safe_float(row.get("robustness_mean"))
            for row in baseline_window
            if _safe_float(row.get("robustness_mean")) is not None
        ]
        baseline_clean = [value for value in baseline_values if value is not None]

        post_values = [
            _safe_float(event.get("robustness_mean"))
            for event in events
            if _safe_float(event.get("robustness_mean")) is not None
        ]
        post_clean = [value for value in post_values if value is not None]

        baseline_mean = mean(baseline_clean) if baseline_clean else None
        post_mean = mean(post_clean) if post_clean else None

        delta = None
        if baseline_mean is not None and post_mean is not None:
            delta = post_mean - baseline_mean

        ci_low, ci_high = (None, None)
        effect_d = None
        if baseline_clean and post_clean:
            ci_low, ci_high = _bootstrap_mean_diff_ci(post_clean, baseline_clean)
            effect_d = _cohens_d(post_clean, baseline_clean)

        if ci_low is not None and ci_high is not None:
            if ci_low > 0:
                status = "PASS"
            elif ci_high < 0:
                status = "FAIL"
            else:
                status = "INCONCLUSIVE"
        else:
            status = "INCONCLUSIVE"

        outcomes.append(
            {
                "family": family,
                "runs": len(post_clean),
                "first_run": events[0]["run"] if events else None,
                "baseline_mean": baseline_mean,
                "post_mean": post_mean,
                "delta": delta,
                "delta_ci_low": ci_low,
                "delta_ci_high": ci_high,
                "effect_d": effect_d,
                "status": status,
            }
        )

    outcomes.sort(key=lambda item: str(item.get("family", "")))
    return outcomes


def _build_campaign_templates(
    ranked_interventions: List[Dict[str, object]],
    rows: List[Dict[str, object]],
) -> List[Dict[str, object]]:
    params = _base_training_params(rows)
    used_seeds = _collect_used_seeds(rows)
    templates: List[Dict[str, object]] = []

    for item in ranked_interventions:
        source = str(item.get("source", ""))
        if source == "h1_curriculum":
            nocurr_seeds = _reserve_seeds(used_seeds, count=4)
            curr_seeds = _reserve_seeds(used_seeds, count=4)
            commands: List[str] = []
            commands.append(f"for s in {' '.join(str(seed) for seed in nocurr_seeds)}; do")
            commands.append(
                "  "
                + _single_train_command(
                    seed_expr='"$s"',
                    output_expr='"outputs/h1_match_nocurr_${s}"',
                    params=params,
                    curriculum=False,
                )
                + ";"
            )
            commands.append("done")
            commands.append("")
            commands.append(f"for s in {' '.join(str(seed) for seed in curr_seeds)}; do")
            commands.append(
                "  "
                + _single_train_command(
                    seed_expr='"$s"',
                    output_expr='"outputs/h1_match_curr_${s}"',
                    params=params,
                    curriculum=True,
                )
                + ";"
            )
            commands.append("done")
            commands.extend(_post_batch_commands())

            templates.append(
                {
                    "title": "Matched Curriculum Ablation Extension",
                    "trigger": "h1_curriculum",
                    "estimated_runs": 8,
                    "objective": "Narrow uncertainty around curriculum-vs-baseline robustness under fixed settings.",
                    "commands": commands,
                }
            )

        elif source == "h2_innovation":
            seeds = _reserve_seeds(used_seeds, count=6)
            base_shock = float(params["shock_prob"])
            shock_values = [base_shock, base_shock + 0.01, base_shock + 0.02]
            shock_csv = " ".join(f"{value:.3f}" for value in shock_values)
            seed_csv = " ".join(str(seed) for seed in seeds)

            commands = []
            commands.append(f"for shock in {shock_csv}; do")
            commands.append(f"  for s in {seed_csv}; do")
            commands.append(
                "    "
                + _single_train_command(
                    seed_expr='"$s"',
                    output_expr='"outputs/h2_shock_${shock}_${s}"',
                    params=params,
                    curriculum=False,
                    shock_prob=float(params["shock_prob"]),
                ).replace(f"--shock-prob {float(params['shock_prob']):.3f}", "--shock-prob \"$shock\"")
                + ";"
            )
            commands.append("  done")
            commands.append("done")
            commands.extend(_post_batch_commands())

            templates.append(
                {
                    "title": "Innovation Stress Sweep",
                    "trigger": "h2_innovation",
                    "estimated_runs": len(seeds) * len(shock_values),
                    "objective": "Validate innovation-family robustness across increasing shock pressure.",
                    "commands": commands,
                }
            )

        elif source == "h4_drift":
            seeds = _reserve_seeds(used_seeds, count=6)
            commands = []
            commands.append(f"for s in {' '.join(str(seed) for seed in seeds)}; do")
            commands.append(
                "  "
                + _single_train_command(
                    seed_expr='"$s"',
                    output_expr='"outputs/h4_stabilize_nocurr_${s}"',
                    params=params,
                    curriculum=False,
                )
                + ";"
            )
            commands.append("done")
            commands.extend(_post_batch_commands())

            templates.append(
                {
                    "title": "Fixed-Setting Stabilization Cohort",
                    "trigger": "h4_drift",
                    "estimated_runs": 6,
                    "objective": "Stabilize campaign drift attribution before adding new ecology complexity.",
                    "commands": commands,
                }
            )

    if not templates:
        seeds = _reserve_seeds(used_seeds, count=2)
        commands = []
        commands.append(f"for s in {' '.join(str(seed) for seed in seeds)}; do")
        commands.append(
            "  "
            + _single_train_command(
                seed_expr='"$s"',
                output_expr='"outputs/monitor_nocurr_${s}"',
                params=params,
                curriculum=False,
            )
            + ";"
        )
        commands.append("done")
        commands.extend(_post_batch_commands())

        templates.append(
            {
                "title": "Baseline Monitoring Mini-Batch",
                "trigger": "baseline",
                "estimated_runs": 2,
                "objective": "Maintain signal continuity while waiting for stronger intervention triggers.",
                "commands": commands,
            }
        )

    return templates[:3]


def _dedupe_limit(lines: List[str], max_items: int = 8) -> List[str]:
    out: List[str] = []
    seen = set()
    for line in lines:
        if line in seen:
            continue
        seen.add(line)
        out.append(line)
        if len(out) >= max_items:
            break
    return out


def _detect_simulation_anomalies(metrics_rows: List[Dict[str, str]]) -> List[str]:
    anomalies: List[str] = []
    previous_water: float | None = None
    previous_food: float | None = None
    previous_alive: int | None = None

    for row in metrics_rows:
        day = _safe_int(row.get("day"))
        if day is None:
            continue

        water = _safe_float(row.get("water_abundance"))
        food = _safe_float(row.get("food_abundance"))
        alive = _safe_int(row.get("population_alive"))
        deaths = _safe_int(row.get("deaths"))

        if water is not None and water <= 0.2:
            anomalies.append(f"Day {day}: water crash (water_abundance={water:.3f}).")
        if food is not None and food <= 0.2:
            anomalies.append(f"Day {day}: food crash (food_abundance={food:.3f}).")

        if previous_water is not None and water is not None and (previous_water - water) >= 0.2:
            anomalies.append(
                f"Day {day}: abrupt water drop ({previous_water:.3f} -> {water:.3f})."
            )
        if previous_food is not None and food is not None and (previous_food - food) >= 0.2:
            anomalies.append(
                f"Day {day}: abrupt food drop ({previous_food:.3f} -> {food:.3f})."
            )

        if previous_alive is not None and alive is not None and previous_alive >= 6:
            if alive <= int(previous_alive * 0.5):
                anomalies.append(f"Day {day}: population collapse ({previous_alive} -> {alive}).")

        if previous_alive is not None and previous_alive > 0 and deaths is not None:
            if deaths >= max(3, int(previous_alive * 0.35)):
                anomalies.append(
                    f"Day {day}: death spike ({deaths} deaths with prior population {previous_alive})."
                )

        previous_water = water if water is not None else previous_water
        previous_food = food if food is not None else previous_food
        previous_alive = alive if alive is not None else previous_alive

    return _dedupe_limit(anomalies, max_items=10)


def _detect_champion_anomalies(
    history_rows: List[Dict[str, object]],
    episodes: List[Dict[str, object]],
) -> List[str]:
    anomalies: List[str] = []

    extinction_streak = 0
    max_extinction_streak = 0
    for row in history_rows:
        alive_end = _safe_int(row.get("alive_end"))
        if alive_end == 0:
            extinction_streak += 1
            max_extinction_streak = max(max_extinction_streak, extinction_streak)
        else:
            extinction_streak = 0

    if max_extinction_streak >= 3:
        anomalies.append(
            "Generation extinction streak detected "
            f"({max_extinction_streak} consecutive generations with alive_end=0)."
        )

    high_shock_generations: List[int] = []
    for row in history_rows:
        generation = _safe_int(row.get("generation"))
        shock_days = _safe_float(row.get("shock_days"))
        if generation is not None and shock_days is not None and shock_days >= 20:
            high_shock_generations.append(generation)
    if high_shock_generations:
        joined = ", ".join(str(value) for value in high_shock_generations[:6])
        anomalies.append(f"High-shock generations (>=20 shock days): {joined}.")

    culture_values = [
        _safe_float(row.get("mean_culture_size"))
        for row in history_rows
    ]
    culture_clean = [value for value in culture_values if value is not None]
    if len(culture_clean) >= 2:
        peak = max(culture_clean)
        final = culture_clean[-1]
        if peak >= 1.5 and final <= (peak * 0.5):
            anomalies.append(
                f"Culture regression: peak {peak:.2f} fell to {final:.2f} by final generation."
            )

    extinction_days = [
        _safe_int(ep.get("extinction_day"))
        for ep in episodes
        if isinstance(ep, dict)
    ]
    extinction_clean = [value for value in extinction_days if value is not None]
    if episodes and extinction_clean and len(extinction_clean) == len(episodes):
        anomalies.append("All robustness episodes ended in extinction.")

    early_extinctions = [value for value in extinction_clean if value <= 150]
    if early_extinctions:
        anomalies.append(
            f"Early robustness extinctions (<= day 150): {len(early_extinctions)}/{len(extinction_clean)}."
        )

    innovation_counts = [
        _safe_int(ep.get("innovations"))
        for ep in episodes
        if isinstance(ep, dict)
    ]
    innovation_clean = [value for value in innovation_counts if value is not None]
    if innovation_clean and mean(innovation_clean) < 2.0:
        anomalies.append(
            f"Low robustness innovation regime (mean innovations={mean(innovation_clean):.2f})."
        )

    score_values = [
        _safe_float(ep.get("score"))
        for ep in episodes
        if isinstance(ep, dict)
    ]
    score_clean = [value for value in score_values if value is not None]
    if len(score_clean) >= 2:
        positive = [value for value in score_clean if value > 0]
        if len(positive) >= 2:
            spread = max(positive) / min(positive)
            if spread >= 5.0:
                anomalies.append(f"Large robustness score spread detected (max/min={spread:.2f}).")

    return _dedupe_limit(anomalies, max_items=10)


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

    simulation_anomalies = _detect_simulation_anomalies(metrics_rows)

    action_counts: Counter[str] = event_snapshot["action_counts"]
    if action_counts:
        top_actions = action_counts.most_common(5)
        lines.append("- Top actions observed:")
        for action, count in top_actions:
            lines.append(f"  - {action}: {count}")
    lines.append("")

    lines.append("## Simulation Anomaly Markers")
    lines.append("")
    if simulation_anomalies:
        for marker in simulation_anomalies:
            lines.append(f"- {marker}")
    else:
        lines.append("- No critical simulation anomalies detected in available day-level logs.")
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

        lines.append("## Policy Families (Heuristic Tags)")
        lines.append("")
        lines.append("These tags help demos by grouping policy behavior patterns, not claiming strict taxonomy.")
        lines.append("")
        lines.append("| Run | Family Tags |")
        lines.append("| --- | --- |")
        for row in selection_pool[:6]:
            tags = ", ".join(_infer_policy_family_tags(row))
            lines.append(f"| {row['run']} | {tags} |")
        lines.append("")

        lines.append("## Compact Lineage Timelines")
        lines.append("")
        lines.append("Sampled generation snapshots for live walkthroughs:")
        lines.append("")
        for row in selection_pool[:4]:
            history_rows = row.get("history") if isinstance(row.get("history"), list) else []
            timeline = _compact_lineage_timeline(history_rows)
            lines.append(f"- {row['run']}: `{timeline}`")
        lines.append("")

        lines.append("## Lineage-Cluster Drift (Campaign-Level)")
        lines.append("")
        lines.append("Chronological early-vs-late cohort drift across the largest comparable multi-seed campaign.")
        lines.append("")

        drift_rows, drift_scope = _select_largest_campaign(selection_pool)
        lines.append(f"- Drift scope: {drift_scope}")
        drift = _compute_lineage_cluster_drift(drift_rows)
        if drift is None:
            lines.append("- Not enough completed runs to compute cluster drift (need at least 4).")
            lines.append("")
        else:
            lines.append(f"- Runs analyzed: {drift['run_count']} (early={drift['early_count']}, late={drift['late_count']})")
            lines.append(
                "- Drift score (total variation): "
                f"{_fmt_float(drift['drift_score'])} ({drift['drift_label']})"
            )
            lines.append(
                "- Most increased cluster: "
                f"{drift['increase_cluster']} ({_fmt_pct(drift['deltas'].get(drift['increase_cluster']))})"
            )
            lines.append(
                "- Most decreased cluster: "
                f"{drift['decrease_cluster']} ({_fmt_pct(drift['deltas'].get(drift['decrease_cluster']))})"
            )

            robust_delta = drift.get("robust_delta")
            if isinstance(robust_delta, (int, float)):
                lines.append(
                    "- Cohort robustness mean (early -> late): "
                    f"{_fmt_float(drift.get('early_robust_mean'))} -> {_fmt_float(drift.get('late_robust_mean'))} "
                    f"(delta {robust_delta:+.3f})"
                )
            else:
                lines.append("- Cohort robustness mean delta: n/a")

            lines.append("")
            lines.append("| Cluster | Early Share | Late Share | Delta |")
            lines.append("| --- | ---: | ---: | ---: |")
            for cluster in drift["clusters"]:
                early_share = drift["early_share"].get(cluster, 0.0)
                late_share = drift["late_share"].get(cluster, 0.0)
                delta = drift["deltas"].get(cluster, 0.0)
                lines.append(
                    "| "
                    f"{cluster} | "
                    f"{_fmt_pct(early_share)} | "
                    f"{_fmt_pct(late_share)} | "
                    f"{_fmt_pct(delta)} |"
                )

            trace_items = drift.get("trace")
            if isinstance(trace_items, list) and trace_items:
                lines.append("")
                lines.append("Run-order cluster trace:")
                lines.append("")
                lines.append(f"`{' -> '.join(trace_items[:10])}`")
            lines.append("")

        lines.append("## Hypothesis Cards (Auto-Evaluated)")
        lines.append("")
        lines.append("These are machine-evaluated research hypotheses with explicit status and next action.")
        lines.append("")
        cards = _build_hypothesis_cards(selection_pool, drift)
        for idx, card in enumerate(cards, start=1):
            lines.append(f"### H{idx}: {card['title']}")
            lines.append("")
            lines.append(f"- Status: {card['status']}")
            lines.append(f"- Evidence: {card['evidence']}")
            lines.append(f"- Next action: {card['next_action']}")
            lines.append("")

        intervention_outcomes = _compute_intervention_outcomes(selection_pool)
        lines.append("## Intervention Outcome Tracking")
        lines.append("")
        lines.append("Observed post-intervention performance deltas compared to the immediate pre-intervention baseline window.")
        lines.append("")
        lines.append("| Family | Runs | Baseline Mean | Post Mean | Delta | Delta 95% CI | Effect d | Status |")
        lines.append("| --- | ---: | ---: | ---: | ---: | --- | ---: | --- |")
        if intervention_outcomes:
            for outcome in intervention_outcomes:
                lines.append(
                    "| "
                    f"{outcome.get('family')} | "
                    f"{outcome.get('runs')} | "
                    f"{_fmt_float(_safe_float(outcome.get('baseline_mean')))} | "
                    f"{_fmt_float(_safe_float(outcome.get('post_mean')))} | "
                    f"{_fmt_float(_safe_float(outcome.get('delta')))} | "
                    f"{_fmt_ci(_safe_float(outcome.get('delta_ci_low')), _safe_float(outcome.get('delta_ci_high')))} | "
                    f"{_fmt_float(_safe_float(outcome.get('effect_d')))} | "
                    f"{outcome.get('status')} |"
                )
        else:
            lines.append("| n/a | 0 | n/a | n/a | n/a | n/a | n/a | INCONCLUSIVE |")
        lines.append("")

        ranked_interventions = _build_ranked_interventions(
            cards=cards,
            rows=selection_pool,
            outcomes=intervention_outcomes,
        )

        lines.append("## Intervention Ranking (Uncertainty-Aware)")
        lines.append("")
        lines.append("Expected upside, confidence, and downside risk are combined into a priority score.")
        lines.append("")
        lines.append("| Rank | Intervention | Upside | Confidence | Risk | Priority |")
        lines.append("| --- | --- | ---: | ---: | ---: | ---: |")
        if ranked_interventions:
            for idx, item in enumerate(ranked_interventions[:8], start=1):
                lines.append(
                    "| "
                    f"{idx} | "
                    f"{item.get('action')} | "
                    f"{float(item.get('expected_upside', 0.0)):.2f} | "
                    f"{float(item.get('confidence', 0.0)):.2f} | "
                    f"{float(item.get('downside_risk', 0.0)):.2f} | "
                    f"{float(item.get('priority', 0.0)):+.3f} |"
                )
        else:
            lines.append("| n/a | No ranked interventions available | 0.00 | 0.00 | 0.00 | +0.000 |")
        lines.append("")

        lines.append("## Ranked Campaign Templates (Executable)")
        lines.append("")
        lines.append("Top-ranked interventions are translated into command-ready campaign templates.")
        lines.append("")
        templates = _build_campaign_templates(ranked_interventions=ranked_interventions, rows=selection_pool)
        for idx, template in enumerate(templates, start=1):
            lines.append(f"### Template {idx}: {template.get('title')}")
            lines.append("")
            lines.append(f"- Trigger: {template.get('trigger')}")
            lines.append(f"- Objective: {template.get('objective')}")
            lines.append(f"- Estimated runs: {template.get('estimated_runs')}")
            lines.append("")
            lines.append("```bash")
            for command in template.get("commands", []):
                lines.append(str(command))
            lines.append("```")
            lines.append("")

        lines.append("## Automatic Intervention Recommendations")
        lines.append("")
        lines.append("Prioritized actions generated from current hypothesis outcomes.")
        lines.append("")
        interventions = _build_intervention_recommendations(cards, selection_pool)
        for intervention in interventions:
            lines.append(f"- {intervention}")
        lines.append("")

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

        lines.append("### Champion Stress Markers")
        lines.append("")
        champion_anomalies = _detect_champion_anomalies(best_history, episodes)
        if champion_anomalies:
            for marker in champion_anomalies:
                lines.append(f"- {marker}")
        else:
            lines.append("- No critical champion stress markers detected.")
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