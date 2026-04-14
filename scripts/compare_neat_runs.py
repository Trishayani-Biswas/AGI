from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List


def _load_json(path: Path) -> Dict[str, object] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _fmt_float(value: object) -> str:
    if isinstance(value, (float, int)):
        return f"{float(value):.3f}"
    return "n/a"


def collect_runs(outputs_dir: Path) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    if not outputs_dir.exists():
        return rows

    for child in sorted(outputs_dir.iterdir()):
        if not child.is_dir():
            continue

        summary_path = child / "summary.json"
        if not summary_path.exists():
            continue

        summary = _load_json(summary_path)
        if not summary:
            continue

        if summary.get("framework") != "neat-python":
            continue

        robustness = _load_json(child / "robustness.json") or {}
        rows.append(
            {
                "run": child.name,
                "winner_fitness": summary.get("winner_fitness"),
                "generations": summary.get("generations"),
                "eval_days": summary.get("eval_days"),
                "world_difficulty": summary.get("world_difficulty"),
                "shock_probability": summary.get("shock_probability"),
                "robustness_mean_score": robustness.get("mean_score", summary.get("robustness_mean_score")),
                "robustness_min_score": robustness.get("min_score", summary.get("robustness_min_score")),
                "robustness_max_score": robustness.get("max_score", summary.get("robustness_max_score")),
                "mean_alive_end": robustness.get("mean_alive_end"),
                "mean_innovations": robustness.get("mean_innovations"),
                "summary_path": str(summary_path),
            }
        )

    rows.sort(
        key=lambda row: (
            float(row["robustness_mean_score"]) if isinstance(row["robustness_mean_score"], (int, float)) else float("-inf"),
            float(row["winner_fitness"]) if isinstance(row["winner_fitness"], (int, float)) else float("-inf"),
        ),
        reverse=True,
    )
    return rows


def write_markdown_report(rows: List[Dict[str, object]], report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)

    lines: List[str] = []
    lines.append("# NEAT Run Comparison")
    lines.append("")

    if not rows:
        lines.append("No NEAT runs found.")
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    lines.append("| Rank | Run | Winner Fitness | Robust Mean | Robust Min | Robust Max | Mean Alive End | Mean Innovations | Difficulty | Shock Prob |")
    lines.append("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")

    for idx, row in enumerate(rows, start=1):
        lines.append(
            "| "
            f"{idx} | "
            f"{row['run']} | "
            f"{_fmt_float(row['winner_fitness'])} | "
            f"{_fmt_float(row['robustness_mean_score'])} | "
            f"{_fmt_float(row['robustness_min_score'])} | "
            f"{_fmt_float(row['robustness_max_score'])} | "
            f"{_fmt_float(row['mean_alive_end'])} | "
            f"{_fmt_float(row['mean_innovations'])} | "
            f"{_fmt_float(row['world_difficulty'])} | "
            f"{_fmt_float(row['shock_probability'])} |"
        )

    lines.append("")
    best = rows[0]
    lines.append("## Best Current Run")
    lines.append("")
    lines.append(f"- Run: {best['run']}")
    lines.append(f"- Winner fitness: {_fmt_float(best['winner_fitness'])}")
    lines.append(f"- Robustness mean score: {_fmt_float(best['robustness_mean_score'])}")
    lines.append(f"- Robustness minimum score: {_fmt_float(best['robustness_min_score'])}")
    lines.append(f"- Summary: {best['summary_path']}")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare NEAT training runs and build a leaderboard report")
    parser.add_argument("--outputs-dir", type=str, default="outputs", help="Directory containing run folders")
    parser.add_argument(
        "--report-path",
        type=str,
        default="outputs/neat_comparison_report.md",
        help="Path to write markdown report",
    )
    args = parser.parse_args()

    outputs_dir = Path(args.outputs_dir)
    report_path = Path(args.report_path)

    rows = collect_runs(outputs_dir)
    write_markdown_report(rows, report_path)
    print(f"Compared {len(rows)} run(s). Report: {report_path}")


if __name__ == "__main__":
    main()
