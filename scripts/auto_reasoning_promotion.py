from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Dict


ROOT = Path(__file__).resolve().parents[1]


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _resolve_path(raw: str) -> Path:
    path = Path(raw)
    if not path.is_absolute():
        return ROOT / path
    return path


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run reasoning benchmark + gate and emit promotion decision"
    )
    parser.add_argument("--model", type=str, required=True, help="Model id served by Ollama")
    parser.add_argument(
        "--baseline-summary",
        type=str,
        required=True,
        help="Baseline benchmark summary JSON path",
    )
    parser.add_argument(
        "--benchmark-file",
        type=str,
        default="configs/random_reasoning_benchmark.json",
        help="Benchmark question config JSON",
    )
    parser.add_argument(
        "--gate-config",
        type=str,
        default="configs/random_reasoning_gate.json",
        help="Reasoning gate config JSON",
    )
    parser.add_argument(
        "--output-root",
        type=str,
        default="outputs/random_reasoning_benchmark",
        help="Benchmark output root",
    )
    parser.add_argument("--run-tag", type=str, required=True, help="Run tag for candidate benchmark")
    parser.add_argument("--max-questions", type=int, default=15, help="Max questions to evaluate")
    parser.add_argument("--timeout-s", type=float, default=90.0, help="Per-request timeout")
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=128,
        help="Maximum tokens to generate per model call",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="Decoding temperature",
    )
    parser.add_argument(
        "--top-p",
        type=float,
        default=0.9,
        help="Nucleus sampling top-p",
    )
    parser.add_argument("--seed", type=int, default=42, help="Question ordering seed")
    parser.add_argument(
        "--decision-path",
        type=str,
        default="",
        help="Optional explicit decision artifact path",
    )
    parser.add_argument(
        "--allow-reject-exit-zero",
        action="store_true",
        help="Return zero exit even when gate rejects promotion",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    output_root = _resolve_path(args.output_root)
    candidate_summary = output_root / args.run_tag / "summary.json"
    gate_report = output_root / args.run_tag / "gate_report.md"
    benchmark_log = output_root / args.run_tag / "benchmark_exec.log"
    gate_log = output_root / args.run_tag / "gate_exec.log"

    if args.decision_path.strip():
        decision_path = _resolve_path(args.decision_path)
    else:
        decision_path = output_root / args.run_tag / "promotion_decision.json"

    benchmark_cmd = [
        sys.executable,
        "scripts/run_random_reasoning_benchmark.py",
        "--benchmark-file",
        args.benchmark_file,
        "--model",
        args.model,
        "--timeout-s",
        str(args.timeout_s),
        "--seed",
        str(args.seed),
        "--max-tokens",
        str(args.max_tokens),
        "--temperature",
        str(args.temperature),
        "--top-p",
        str(args.top_p),
        "--max-questions",
        str(args.max_questions),
        "--output-root",
        args.output_root,
        "--run-tag",
        args.run_tag,
    ]

    bench = _run(benchmark_cmd)
    _write_text(
        benchmark_log,
        "\n".join(
            [
                f"command: {' '.join(benchmark_cmd)}",
                f"exit_code: {bench.returncode}",
                "",
                "--- stdout ---",
                bench.stdout,
                "",
                "--- stderr ---",
                bench.stderr,
                "",
            ]
        ),
    )

    gate_exit = 1
    if bench.returncode == 0 and candidate_summary.exists():
        gate_cmd = [
            sys.executable,
            "scripts/evaluate_random_reasoning_gate.py",
            "--gate-config",
            args.gate_config,
            "--candidate-summary",
            str(candidate_summary),
            "--baseline-summary",
            args.baseline_summary,
            "--report-path",
            str(gate_report),
        ]
        gate = _run(gate_cmd)
        gate_exit = int(gate.returncode)
        _write_text(
            gate_log,
            "\n".join(
                [
                    f"command: {' '.join(gate_cmd)}",
                    f"exit_code: {gate.returncode}",
                    "",
                    "--- stdout ---",
                    gate.stdout,
                    "",
                    "--- stderr ---",
                    gate.stderr,
                    "",
                ]
            ),
        )
    else:
        _write_text(gate_log, "Gate skipped: benchmark failed or candidate summary missing.\n")

    promoted = bench.returncode == 0 and gate_exit == 0

    decision: Dict[str, object] = {
        "generated_at_utc": _utc_now(),
        "model": args.model,
        "run_tag": args.run_tag,
        "benchmark_file": args.benchmark_file,
        "gate_config": args.gate_config,
        "baseline_summary": args.baseline_summary,
        "candidate_summary": str(candidate_summary),
        "gate_report": str(gate_report),
        "benchmark_exec_log": str(benchmark_log),
        "gate_exec_log": str(gate_log),
        "benchmark_exit_code": int(bench.returncode),
        "gate_exit_code": int(gate_exit),
        "promoted": bool(promoted),
    }

    _write_text(decision_path, json.dumps(decision, indent=2, ensure_ascii=True) + "\n")

    print(f"[{_utc_now()}] decision={decision_path}")
    print(f"promoted={promoted} benchmark_exit={bench.returncode} gate_exit={gate_exit}")

    if not promoted and not args.allow_reject_exit_zero:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
