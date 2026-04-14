from __future__ import annotations

import argparse
from collections import deque
from datetime import datetime
import json
from pathlib import Path
import time
from typing import Deque, Dict


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _bar(value: float | None, width: int = 28) -> str:
    if value is None:
        return "?" * width
    normalized = _clamp(value, 0.0, 1.0)
    filled = int(round(normalized * width))
    return ("#" * filled) + ("-" * (width - filled))


def _trend(values: list[float], width: int = 42) -> str:
    if not values:
        return "n/a"
    sample = values[-width:]
    min_value = min(sample)
    max_value = max(sample)
    if abs(max_value - min_value) < 1e-9:
        return "#" * len(sample)

    chars = " .:-=+*#%@"
    out = []
    for value in sample:
        ratio = (value - min_value) / (max_value - min_value)
        idx = int(ratio * (len(chars) - 1))
        out.append(chars[idx])
    return "".join(out)


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


def _parse_line(line: str) -> Dict[str, object] | None:
    line = line.strip()
    if not line:
        return None
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _read_new_entries(log_path: Path, position: int, entries: Deque[Dict[str, object]]) -> int:
    if not log_path.exists():
        return position

    try:
        size = log_path.stat().st_size
    except OSError:
        return position

    if size < position:
        position = 0

    try:
        with log_path.open("r", encoding="utf-8") as fp:
            fp.seek(position)
            for line in fp:
                payload = _parse_line(line)
                if payload is not None:
                    entries.append(payload)
            return fp.tell()
    except OSError:
        return position


def _render(entries: Deque[Dict[str, object]], log_path: Path) -> None:
    print("\033[2J\033[H", end="")
    print("LIVE WORLD MONITOR")
    print(f"time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"source: {log_path}")
    print("")

    if not entries:
        print("Waiting for world timeline data...")
        print("Tip: start a run with --output-dir and tail this log path.")
        return

    latest = entries[-1]
    generation = _safe_int(latest.get("generation"))
    day = _safe_int(latest.get("day"))
    stage = _safe_int(latest.get("curriculum_stage"))
    alive = _safe_int(latest.get("alive_count"))
    births = _safe_int(latest.get("births"))
    deaths = _safe_int(latest.get("deaths"))
    innovation_events = _safe_int(latest.get("innovation_events"))
    innovations_count = _safe_int(latest.get("innovations_count"))
    weather = str(latest.get("weather", "n/a"))
    shock = latest.get("shock")
    shock_text = str(shock) if shock is not None else "-"
    water = _safe_float(latest.get("water_abundance"))
    food = _safe_float(latest.get("food_abundance"))
    mean_health = _safe_float(latest.get("mean_health"))

    stage_text = str(stage) if stage is not None and stage > 0 else "off"
    health_text = f"{mean_health:.2f}" if mean_health is not None else "?"
    print(
        f"generation={generation if generation is not None else '?'} "
        f"day={day if day is not None else '?'} "
        f"curriculum_stage={stage_text}"
    )
    print(
        f"alive={alive if alive is not None else '?'} "
        f"births={births if births is not None else '?'} "
        f"deaths={deaths if deaths is not None else '?'} "
        f"mean_health={health_text}"
    )
    print(
        f"weather={weather} shock={shock_text} "
        f"innovation_events={innovation_events if innovation_events is not None else '?'} "
        f"innovations_total={innovations_count if innovations_count is not None else '?'}"
    )
    print("")
    print(f"water [{_bar(water)}] {water:.3f}" if water is not None else f"water [{_bar(None)}] n/a")
    print(f"food  [{_bar(food)}] {food:.3f}" if food is not None else f"food  [{_bar(None)}] n/a")
    print("")

    alive_values = [
        float(value)
        for value in (
            _safe_float(entry.get("alive_count"))
            for entry in entries
        )
        if value is not None
    ]
    innovation_values = [
        float(value)
        for value in (
            _safe_float(entry.get("innovations_count"))
            for entry in entries
        )
        if value is not None
    ]
    print(f"alive trend      : {_trend(alive_values)}")
    print(f"innovation trend : {_trend(innovation_values)}")
    print("")

    print("Recent timeline (latest 10 rows):")
    print("gen  day  alive births deaths shock            innov_total")
    for entry in list(entries)[-10:]:
        e_gen = _safe_int(entry.get("generation"))
        e_day = _safe_int(entry.get("day"))
        e_alive = _safe_int(entry.get("alive_count"))
        e_births = _safe_int(entry.get("births"))
        e_deaths = _safe_int(entry.get("deaths"))
        e_shock = entry.get("shock")
        e_innov = _safe_int(entry.get("innovations_count"))
        shock_display = (str(e_shock) if e_shock is not None else "-")[:15]
        print(
            f"{(e_gen if e_gen is not None else 0):>3} "
            f"{(e_day if e_day is not None else 0):>4} "
            f"{(e_alive if e_alive is not None else 0):>5} "
            f"{(e_births if e_births is not None else 0):>6} "
            f"{(e_deaths if e_deaths is not None else 0):>6} "
            f"{shock_display:<15} "
            f"{(e_innov if e_innov is not None else 0):>11}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Watch NEAT world timeline live in the terminal")
    parser.add_argument(
        "--log-path",
        type=str,
        default="outputs/neat_live_watch/world_timeline.jsonl",
        help="Path to world_timeline.jsonl",
    )
    parser.add_argument(
        "--refresh-seconds",
        type=float,
        default=0.8,
        help="Refresh interval while following",
    )
    parser.add_argument(
        "--window",
        type=int,
        default=120,
        help="Number of latest timeline rows to keep in memory for rendering",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Render current snapshot once and exit",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    log_path = Path(args.log_path)
    entries: Deque[Dict[str, object]] = deque(maxlen=max(20, args.window))
    position = 0

    while True:
        position = _read_new_entries(log_path=log_path, position=position, entries=entries)
        _render(entries=entries, log_path=log_path)
        if args.once:
            break
        time.sleep(max(0.1, args.refresh_seconds))


if __name__ == "__main__":
    main()