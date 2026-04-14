from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence, Tuple


@dataclass(frozen=True)
class RunRow:
    run: str
    run_dir: Path
    summary_path: Path
    robustness_path: Path
    history_path: Path
    generations: int | None
    history_points: int | None
    run_completed: bool
    winner_fitness: float | None
    robustness_mean: float | None
    robustness_min: float | None
    robustness_max: float | None
    world_difficulty: float | None
    shock_probability: float | None
    eval_days: int | None
    max_population: int | None
    curriculum_enabled: bool | None
    run_mtime_epoch: float | None


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
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


def _safe_float(value) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _fmt_float(value: float | None, digits: int = 3) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


def _fmt_bool(value: bool | None) -> str:
    if value is None:
        return "n/a"
    return "yes" if value else "no"


def _relative_link(from_file: Path, target_file: Path) -> str:
    return Path(os.path.relpath(target_file, start=from_file.parent)).as_posix()


def collect_neat_runs(outputs_dir: Path, require_full_generations: bool = False) -> List[RunRow]:
    rows: List[RunRow] = []
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

        robustness_path = child / "robustness.json"
        robustness = _load_json(robustness_path)
        robustness_obj = robustness if isinstance(robustness, dict) else {}

        generations = _safe_int(summary.get("generations"))
        history_points = _safe_int(summary.get("history_points"))
        run_completed = (
            isinstance(generations, int)
            and isinstance(history_points, int)
            and history_points >= generations
        )

        if require_full_generations and not run_completed:
            continue

        try:
            run_mtime_epoch = float(child.stat().st_mtime)
        except OSError:
            run_mtime_epoch = None

        rows.append(
            RunRow(
                run=child.name,
                run_dir=child,
                summary_path=summary_path,
                robustness_path=robustness_path,
                history_path=child / "history.json",
                generations=generations,
                history_points=history_points,
                run_completed=run_completed,
                winner_fitness=_safe_float(summary.get("winner_fitness")),
                robustness_mean=_safe_float(
                    robustness_obj.get("mean_score", summary.get("robustness_mean_score"))
                ),
                robustness_min=_safe_float(
                    robustness_obj.get("min_score", summary.get("robustness_min_score"))
                ),
                robustness_max=_safe_float(
                    robustness_obj.get("max_score", summary.get("robustness_max_score"))
                ),
                world_difficulty=_safe_float(summary.get("world_difficulty")),
                shock_probability=_safe_float(summary.get("shock_probability")),
                eval_days=_safe_int(summary.get("eval_days")),
                max_population=_safe_int(summary.get("max_population")),
                curriculum_enabled=(
                    bool(summary.get("curriculum_enabled"))
                    if isinstance(summary.get("curriculum_enabled"), bool)
                    else None
                ),
                run_mtime_epoch=run_mtime_epoch,
            )
        )

    rows.sort(
        key=lambda row: (
            1 if row.run_completed else 0,
            row.robustness_mean if row.robustness_mean is not None else float("-inf"),
            row.winner_fitness if row.winner_fitness is not None else float("-inf"),
        ),
        reverse=True,
    )
    return rows


def _extract_markdown_section(markdown_text: str, heading: str) -> str | None:
    lines = markdown_text.splitlines()
    target = f"## {heading}"

    start_idx = None
    for idx, line in enumerate(lines):
        if line.strip() == target:
            start_idx = idx
            break

    if start_idx is None:
        return None

    end_idx = len(lines)
    for idx in range(start_idx + 1, len(lines)):
        if lines[idx].startswith("## "):
            end_idx = idx
            break

    section = "\n".join(lines[start_idx:end_idx]).strip()
    return section if section else None


def _group_key(row: RunRow) -> Tuple[float | None, float | None, int | None, int | None]:
    return (row.world_difficulty, row.shock_probability, row.eval_days, row.max_population)


def _largest_campaign(rows: Sequence[RunRow]) -> Tuple[Tuple[float | None, float | None, int | None, int | None] | None, List[RunRow]]:
    comparable: Dict[Tuple[float | None, float | None, int | None, int | None], List[RunRow]] = {}
    for row in rows:
        if row.run_completed:
            comparable.setdefault(_group_key(row), []).append(row)

    best_key = None
    best_rows: List[RunRow] = []
    for key, group_rows in comparable.items():
        if len(group_rows) > len(best_rows):
            best_key = key
            best_rows = group_rows
    return best_key, best_rows


def _write_if_changed(path: Path, content: str) -> bool:
    existing = None
    if path.exists():
        try:
            existing = path.read_text(encoding="utf-8")
        except OSError:
            existing = None
    if existing == content:
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _safe_mtime_ns(path: Path) -> int:
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return -1


def _run_page_signature(row: RunRow, rank: int) -> str:
    fields = [
        str(rank),
        row.run,
        str(row.generations),
        str(row.history_points),
        str(row.run_completed),
        _fmt_float(row.winner_fitness, digits=6),
        _fmt_float(row.robustness_mean, digits=6),
        _fmt_float(row.robustness_min, digits=6),
        _fmt_float(row.robustness_max, digits=6),
        _fmt_float(row.world_difficulty, digits=6),
        _fmt_float(row.shock_probability, digits=6),
        str(row.eval_days),
        str(row.max_population),
        str(row.curriculum_enabled),
        str(row.run_mtime_epoch),
        str(_safe_mtime_ns(row.summary_path)),
        str(_safe_mtime_ns(row.robustness_path)),
        str(_safe_mtime_ns(row.history_path)),
    ]
    return "|".join(fields)


def _load_run_cache(cache_path: Path) -> Dict[str, str]:
    if not cache_path.exists():
        return {}

    try:
        raw = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(raw, dict):
        return {}

    parsed: Dict[str, str] = {}
    for key, value in raw.items():
        if isinstance(key, str) and isinstance(value, str):
            parsed[key] = value
    return parsed


def _write_run_cache(cache_path: Path, cache_payload: Dict[str, str]) -> None:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(cache_payload, indent=2, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def _render_run_page(row: RunRow, rank: int, wiki_dir: Path) -> str:
    page_path = wiki_dir / "runs" / f"{row.run}.md"
    summary_rel = _relative_link(page_path, row.summary_path)

    hist_gen = "n/a"
    if isinstance(row.history_points, int) and isinstance(row.generations, int):
        hist_gen = f"{row.history_points}/{row.generations}"

    lines: List[str] = []
    lines.append(f"# Run: {row.run}")
    lines.append("")
    lines.append("## Snapshot")
    lines.append("")
    lines.append(f"- Rank by robustness: {rank}")
    lines.append(f"- Completed full generations: {'yes' if row.run_completed else 'no'} ({hist_gen})")
    lines.append(f"- Winner fitness: {_fmt_float(row.winner_fitness)}")
    lines.append(
        "- Robustness mean/min/max: "
        f"{_fmt_float(row.robustness_mean)} / {_fmt_float(row.robustness_min)} / {_fmt_float(row.robustness_max)}"
    )
    lines.append(f"- World difficulty: {_fmt_float(row.world_difficulty)}")
    lines.append(f"- Shock probability: {_fmt_float(row.shock_probability)}")
    lines.append(f"- Eval days: {row.eval_days if row.eval_days is not None else 'n/a'}")
    lines.append(f"- Max population: {row.max_population if row.max_population is not None else 'n/a'}")
    lines.append(f"- Curriculum enabled: {_fmt_bool(row.curriculum_enabled)}")
    lines.append("")
    lines.append("## Raw Source Artifacts")
    lines.append("")
    lines.append(f"- [summary.json]({summary_rel})")
    if row.robustness_path.exists():
        robustness_rel = _relative_link(page_path, row.robustness_path)
        lines.append(f"- [robustness.json]({robustness_rel})")
    else:
        lines.append("- robustness.json: not available")

    if row.history_path.exists():
        history_rel = _relative_link(page_path, row.history_path)
        lines.append(f"- [history.json]({history_rel})")
    else:
        lines.append("- history.json: not available")

    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    if row.robustness_mean is None:
        lines.append("- Robustness data missing, treat this run as incomplete evidence.")
    else:
        if row.run_completed:
            lines.append("- This run is eligible for apples-to-apples campaign comparisons.")
        else:
            lines.append("- This run is partial and should not drive final decisions.")

        if row.curriculum_enabled is True:
            lines.append("- Curriculum mode was enabled; compare only against matched no-curriculum settings.")
        elif row.curriculum_enabled is False:
            lines.append("- Baseline mode was used; useful as control for curriculum ablations.")

    return "\n".join(lines) + "\n"


def _render_campaign_state(rows: Sequence[RunRow], wiki_dir: Path) -> str:
    full_rows = [row for row in rows if row.run_completed]
    best = full_rows[0] if full_rows else (rows[0] if rows else None)

    lines: List[str] = []
    lines.append("# Campaign State")
    lines.append("")
    lines.append("## Current Snapshot")
    lines.append("")
    lines.append(f"- Total NEAT runs discovered: {len(rows)}")
    lines.append(f"- Full-generation comparable runs: {len(full_rows)}")

    if best is None:
        lines.append("- No runs available yet.")
        return "\n".join(lines) + "\n"

    best_page = _relative_link(wiki_dir / "concepts" / "campaign_state.md", wiki_dir / "runs" / f"{best.run}.md")
    lines.append(f"- Best current run: [{best.run}]({best_page})")
    lines.append(f"- Best robustness mean: {_fmt_float(best.robustness_mean)}")
    lines.append("")

    campaign_key, campaign_rows = _largest_campaign(full_rows)
    lines.append("## Largest Comparable Campaign")
    lines.append("")
    if campaign_key is None:
        lines.append("- Not enough full-generation runs to form a comparable campaign cohort.")
        return "\n".join(lines) + "\n"

    diff, shock, eval_days, max_pop = campaign_key
    lines.append(
        "- Scope: "
        f"difficulty={_fmt_float(diff)} shock={_fmt_float(shock)} eval_days={eval_days if eval_days is not None else 'n/a'} "
        f"max_population={max_pop if max_pop is not None else 'n/a'}"
    )
    lines.append(f"- Runs in scope: {len(campaign_rows)}")

    curriculum_values = [row.robustness_mean for row in campaign_rows if row.curriculum_enabled is True and row.robustness_mean is not None]
    baseline_values = [row.robustness_mean for row in campaign_rows if row.curriculum_enabled is False and row.robustness_mean is not None]

    if curriculum_values and baseline_values:
        curriculum_mean = sum(curriculum_values) / len(curriculum_values)
        baseline_mean = sum(baseline_values) / len(baseline_values)
        delta_pct = 0.0 if abs(baseline_mean) < 1e-9 else ((curriculum_mean / baseline_mean) - 1.0) * 100.0
        lines.append(
            "- Curriculum vs baseline robustness mean: "
            f"{curriculum_mean:.3f} vs {baseline_mean:.3f} ({delta_pct:+.1f}%)"
        )
    else:
        lines.append("- Curriculum/baseline pair coverage is incomplete in this cohort.")

    return "\n".join(lines) + "\n"


def _render_index(rows: Sequence[RunRow], max_runs: int) -> str:
    lines: List[str] = []
    lines.append("# AGI LLM Wiki")
    lines.append("")
    lines.append("This wiki follows the Karpathy LLM Wiki pattern for persistent, compounding experiment memory.")
    lines.append("Raw run outputs remain source-of-truth; this wiki is the maintained synthesis layer.")
    lines.append("")
    lines.append("## Core Pages")
    lines.append("")
    lines.append("- [Schema](../AGI_WIKI.md): wiki operating rules for ingest, query, and lint.")
    lines.append("- [Log](log.md): append-only chronology of wiki ingests and updates.")
    lines.append("- [Campaign State](concepts/campaign_state.md): current campaign-level summary and ablation status.")
    lines.append("- [Hypothesis Board](concepts/hypotheses.md): pass/fail/inconclusive hypothesis outcomes.")
    lines.append("- [Interventions](concepts/interventions.md): prioritized actions from current evidence.")
    lines.append("")

    lines.append(f"## Run Pages (Top {min(max_runs, len(rows))})")
    lines.append("")
    if not rows:
        lines.append("No NEAT runs found yet.")
        return "\n".join(lines) + "\n"

    lines.append("| Rank | Run | Complete | Robust Mean | Curriculum | Page |")
    lines.append("| --- | --- | --- | ---: | --- | --- |")
    for idx, row in enumerate(rows[:max_runs], start=1):
        page = f"runs/{row.run}.md"
        lines.append(
            "| "
            f"{idx} | "
            f"{row.run} | "
            f"{'yes' if row.run_completed else 'no'} | "
            f"{_fmt_float(row.robustness_mean)} | "
            f"{_fmt_bool(row.curriculum_enabled)} | "
            f"[{row.run}]({page}) |"
        )

    return "\n".join(lines) + "\n"


def _render_concept_page(
    title: str,
    source_rel: str,
    section_content: str | None,
    fallback_lines: List[str],
) -> str:
    lines: List[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"Source: [{source_rel}]({source_rel})")
    lines.append("")

    if section_content:
        lines.append(section_content)
    else:
        lines.extend(fallback_lines)
    lines.append("")
    return "\n".join(lines) + "\n"


def _append_run_evidence_section(
    page_markdown: str,
    concept_page_path: Path,
    evidence_rows: Sequence[RunRow],
    max_links: int = 5,
) -> str:
    lines = page_markdown.rstrip().splitlines()
    lines.append("")
    lines.append("## Run Evidence")
    lines.append("")

    if not evidence_rows:
        lines.append("No run pages available yet.")
    else:
        for row in evidence_rows[:max_links]:
            run_page = _relative_link(
                concept_page_path,
                concept_page_path.parent.parent / "runs" / f"{row.run}.md",
            )
            lines.append(f"- [{row.run}]({run_page})")

    lines.append("")
    return "\n".join(lines) + "\n"


def _update_log(wiki_dir: Path, rows: Sequence[RunRow]) -> int:
    log_path = wiki_dir / "log.md"
    if log_path.exists():
        existing_text = log_path.read_text(encoding="utf-8")
    else:
        existing_text = "# Wiki Log\n\nAppend-only timeline of wiki ingests and major updates.\n"

    existing_runs = set(re.findall(r"ingest \| ([^\n]+)", existing_text))

    entries: List[str] = []
    added_runs = 0
    sorted_rows = sorted(rows, key=lambda row: row.run_mtime_epoch or 0.0)
    for row in sorted_rows:
        if row.run in existing_runs:
            continue

        ts = row.run_mtime_epoch if row.run_mtime_epoch is not None else datetime.now(tz=timezone.utc).timestamp()
        day_stamp = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        entries.append(f"## [{day_stamp}] ingest | {row.run}")
        entries.append("")
        entries.append(f"- page: [runs/{row.run}.md](runs/{row.run}.md)")
        entries.append(f"- source: [../outputs/{row.run}/summary.json](../outputs/{row.run}/summary.json)")
        entries.append(f"- full_generation_run: {'yes' if row.run_completed else 'no'}")
        entries.append(f"- robustness_mean: {_fmt_float(row.robustness_mean)}")
        entries.append(f"- winner_fitness: {_fmt_float(row.winner_fitness)}")
        entries.append(f"- curriculum_enabled: {_fmt_bool(row.curriculum_enabled)}")
        entries.append("")
        added_runs += 1

    if not entries:
        return 0

    updated = existing_text.rstrip() + "\n\n" + "\n".join(entries).rstrip() + "\n"
    _write_if_changed(log_path, updated)
    return added_runs


def build_wiki(
    outputs_dir: Path,
    wiki_dir: Path,
    rows: Sequence[RunRow],
    max_runs: int,
    run_cache_path: Path,
) -> Dict[str, int]:
    wiki_dir.mkdir(parents=True, exist_ok=True)
    (wiki_dir / "runs").mkdir(parents=True, exist_ok=True)
    (wiki_dir / "concepts").mkdir(parents=True, exist_ok=True)

    selected_rows = list(rows[:max_runs])
    existing_run_cache = _load_run_cache(run_cache_path)
    next_run_cache: Dict[str, str] = {}
    run_pages_written = 0
    run_pages_skipped = 0
    for idx, row in enumerate(selected_rows, start=1):
        page_path = wiki_dir / "runs" / f"{row.run}.md"
        signature = _run_page_signature(row=row, rank=idx)
        next_run_cache[row.run] = signature
        if existing_run_cache.get(row.run) == signature and page_path.exists():
            run_pages_skipped += 1
            continue

        page = _render_run_page(row, rank=idx, wiki_dir=wiki_dir)
        if _write_if_changed(page_path, page):
            run_pages_written += 1

    _write_run_cache(run_cache_path, next_run_cache)

    observatory_path = outputs_dir / "experiment_observatory.md"
    observatory_text = None
    if observatory_path.exists():
        try:
            observatory_text = observatory_path.read_text(encoding="utf-8")
        except OSError:
            observatory_text = None

    hypotheses_section = (
        _extract_markdown_section(observatory_text, "Hypothesis Cards (Auto-Evaluated)")
        if observatory_text
        else None
    )
    interventions_section = (
        _extract_markdown_section(observatory_text, "Automatic Intervention Recommendations")
        if observatory_text
        else None
    )

    concept_writes = 0
    source_rel = _relative_link(wiki_dir / "concepts" / "hypotheses.md", observatory_path)
    hypotheses_path = wiki_dir / "concepts" / "hypotheses.md"
    hypotheses_md = _render_concept_page(
        title="Hypothesis Board",
        source_rel=source_rel,
        section_content=hypotheses_section,
        fallback_lines=[
            "## Hypothesis Cards (Auto-Evaluated)",
            "",
            "No observatory hypothesis section found yet. Build the observatory report first.",
        ],
    )
    hypotheses_md = _append_run_evidence_section(
        page_markdown=hypotheses_md,
        concept_page_path=hypotheses_path,
        evidence_rows=rows,
        max_links=5,
    )
    if _write_if_changed(hypotheses_path, hypotheses_md):
        concept_writes += 1

    interventions_path = wiki_dir / "concepts" / "interventions.md"
    interventions_md = _render_concept_page(
        title="Interventions",
        source_rel=source_rel,
        section_content=interventions_section,
        fallback_lines=[
            "## Automatic Intervention Recommendations",
            "",
            "No intervention section found yet. Build the observatory report first.",
        ],
    )
    interventions_md = _append_run_evidence_section(
        page_markdown=interventions_md,
        concept_page_path=interventions_path,
        evidence_rows=rows,
        max_links=5,
    )
    if _write_if_changed(interventions_path, interventions_md):
        concept_writes += 1

    campaign_state_md = _render_campaign_state(rows=rows, wiki_dir=wiki_dir)
    if _write_if_changed(wiki_dir / "concepts" / "campaign_state.md", campaign_state_md):
        concept_writes += 1

    index_md = _render_index(rows=rows, max_runs=max_runs)
    index_written = 1 if _write_if_changed(wiki_dir / "index.md", index_md) else 0

    log_entries_added = _update_log(wiki_dir, selected_rows)

    return {
        "run_pages_written": run_pages_written,
        "run_pages_skipped": run_pages_skipped,
        "concept_pages_written": concept_writes,
        "index_written": index_written,
        "log_entries_added": log_entries_added,
        "run_cache_entries": len(next_run_cache),
        "runs_considered": len(selected_rows),
        "runs_total": len(rows),
    }


def _rows_signature(rows: Sequence[RunRow]) -> str:
    parts = [
        f"{row.run}:{row.history_points}:{row.generations}:{row.run_mtime_epoch}"
        for row in rows
    ]
    return "|".join(parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and maintain a local AGI LLM Wiki from NEAT outputs")
    parser.add_argument("--outputs-dir", type=str, default="outputs", help="Directory containing NEAT run folders")
    parser.add_argument("--wiki-dir", type=str, default="wiki", help="Directory where wiki markdown is maintained")
    parser.add_argument("--max-runs", type=int, default=30, help="Maximum number of top runs to materialize into run pages")
    parser.add_argument(
        "--require-full-generations",
        action="store_true",
        help="Only include runs where history_points >= generations",
    )
    parser.add_argument("--watch", action="store_true", help="Continuously rebuild wiki when outputs change")
    parser.add_argument(
        "--run-cache-file",
        type=str,
        default=".agi_wiki_run_cache.json",
        help="Path to incremental run-page cache used to skip unchanged run markdown regeneration",
    )
    parser.add_argument(
        "--watch-interval",
        type=float,
        default=20.0,
        help="Seconds between watch checks",
    )
    return parser.parse_args()


def _run_once(args: argparse.Namespace) -> str:
    outputs_dir = Path(args.outputs_dir)
    wiki_dir = Path(args.wiki_dir)
    run_cache_path = Path(args.run_cache_file)
    rows = collect_neat_runs(outputs_dir, require_full_generations=args.require_full_generations)
    stats = build_wiki(
        outputs_dir=outputs_dir,
        wiki_dir=wiki_dir,
        rows=rows,
        max_runs=args.max_runs,
        run_cache_path=run_cache_path,
    )
    return (
        "Wiki updated: "
        f"runs_written={stats['run_pages_written']} "
        f"runs_skipped={stats['run_pages_skipped']} "
        f"concepts_written={stats['concept_pages_written']} "
        f"index_written={stats['index_written']} "
        f"log_entries_added={stats['log_entries_added']} "
        f"cache_entries={stats['run_cache_entries']} "
        f"runs_considered={stats['runs_considered']} "
        f"runs_total={stats['runs_total']}"
    )


def main() -> None:
    args = parse_args()

    if not args.watch:
        print(_run_once(args))
        return

    last_signature = ""
    print("Watching outputs and maintaining wiki. Press Ctrl+C to stop.")
    try:
        while True:
            rows = collect_neat_runs(Path(args.outputs_dir), require_full_generations=args.require_full_generations)
            signature = _rows_signature(rows)
            if signature != last_signature:
                stats = build_wiki(
                    outputs_dir=Path(args.outputs_dir),
                    wiki_dir=Path(args.wiki_dir),
                    rows=rows,
                    max_runs=args.max_runs,
                    run_cache_path=Path(args.run_cache_file),
                )
                print(
                    "Wiki updated: "
                    f"runs_written={stats['run_pages_written']} "
                    f"runs_skipped={stats['run_pages_skipped']} "
                    f"concepts_written={stats['concept_pages_written']} "
                    f"index_written={stats['index_written']} "
                    f"log_entries_added={stats['log_entries_added']} "
                    f"cache_entries={stats['run_cache_entries']} "
                    f"runs_considered={stats['runs_considered']} "
                    f"runs_total={stats['runs_total']}"
                )
                last_signature = signature
            time.sleep(max(5.0, args.watch_interval))
    except KeyboardInterrupt:
        print("Stopped wiki watch mode.")


if __name__ == "__main__":
    main()
