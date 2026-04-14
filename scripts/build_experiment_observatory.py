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


def _build_hypothesis_cards(
    rows: List[Dict[str, object]],
    drift: Dict[str, object] | None,
) -> List[Dict[str, str]]:
    cards: List[Dict[str, str]] = []

    # H1: Curriculum vs non-curriculum under comparable settings.
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

    if best_pair_count == 0 or best_group_key is None:
        cards.append(
            {
                "title": "Curriculum Improves Robustness",
                "status": "INCONCLUSIVE",
                "evidence": "No comparable curriculum/non-curriculum run pair in the same campaign settings.",
                "next_action": "Run one baseline and one curriculum run with identical settings and different seeds.",
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
        cards.append(
            {
                "title": "Curriculum Improves Robustness",
                "status": _status_from_delta(delta, pass_threshold=0.1),
                "evidence": (
                    f"Scope={_group_key_label(best_group_key)}; "
                    f"curriculum_mean={curr_mean:.3f}, baseline_mean={base_mean:.3f}, delta={delta * 100.0:+.1f}%."
                ),
                "next_action": "Increase seed count in both groups to reduce variance before finalizing.",
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
        cards.append(
            {
                "title": "Innovation-Rich Policies Outperform Innovation-Sparse Policies",
                "status": _status_from_delta(delta, pass_threshold=0.1),
                "evidence": (
                    f"innovation_rich_mean={rich_mean:.3f}, innovation_sparse_mean={sparse_mean:.3f}, "
                    f"delta={delta * 100.0:+.1f}%."
                ),
                "next_action": "Check if innovation gains persist when shock probability is increased.",
            }
        )
    else:
        cards.append(
            {
                "title": "Innovation-Rich Policies Outperform Innovation-Sparse Policies",
                "status": "INCONCLUSIVE",
                "evidence": "Not enough runs tagged as both innovation_rich and innovation_sparse.",
                "next_action": "Run more seeds until both families are represented with robustness metrics.",
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
                "title": "Survivorship Correlates With Robustness",
                "status": "INCONCLUSIVE",
                "evidence": "Insufficient non-degenerate data for correlation.",
                "next_action": "Collect more runs with varied mean_alive_end values.",
            }
        )
    else:
        if corr >= 0.35:
            status = "PASS"
        elif corr <= -0.15:
            status = "FAIL"
        else:
            status = "INCONCLUSIVE"
        cards.append(
            {
                "title": "Survivorship Correlates With Robustness",
                "status": status,
                "evidence": f"pearson_corr(mean_alive_end, robustness_mean)={corr:+.3f} across {len(alive_values)} runs.",
                "next_action": "Use this signal to tune fitness weighting for alive_end vs innovation pressure.",
            }
        )

    # H4: Drift and robustness should improve together.
    if drift is None:
        cards.append(
            {
                "title": "Campaign Drift Is Productive",
                "status": "INCONCLUSIVE",
                "evidence": "No drift block available for this campaign.",
                "next_action": "Ensure at least four completed comparable runs for drift analysis.",
            }
        )
    else:
        drift_score = _safe_float(drift.get("drift_score"))
        robust_delta = _safe_float(drift.get("robust_delta"))
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
                "title": "Campaign Drift Is Productive",
                "status": status,
                "evidence": (
                    f"drift_score={_fmt_float(drift_score)} ({drift.get('drift_label', 'n/a')}), "
                    f"robust_delta={_fmt_float(robust_delta)}."
                ),
                "next_action": "If inconclusive, add seeds and compare with a fixed no-curriculum ablation group.",
            }
        )

    return cards


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