# Source-of-Truth Protocol

## Objective

Keep research decisions grounded in executable code and measured artifacts, not narrative summaries.

## Authority Order

1. Runtime code and configs

Source files under `src/agi_sim/`, evaluation and gate scripts under `scripts/`, and threshold configs under `configs/`.

1. Generated artifacts

Run summaries and reports under `outputs/`, gate reports and promotion decisions under `outputs/random_reasoning_benchmark/`, and observatory outputs under `outputs/experiment_observatory.md`.

1. Documentation

`README.md`, `ROADMAP.md`, and wiki pages are explanatory context.
If docs conflict with code or artifacts, code+artifacts win.

## Direction Anchor

For medium- and long-horizon planning, use `docs/research/openclaw_local_evolution_6m_execution_plan.md` as the strategic reference.
Before starting major implementation, map intended work to the plan's month/week milestones.

## Minimum Evidence For Any Direction Claim

A claim is valid only when all are present:

- Config used for the run
- Raw run summary JSON
- Human-readable report
- Gate report with explicit pass/fail checks
- Decision artifact (promoted/rejected) for promotion claims

## Research Readiness Checklist

Use this checklist before saying a track is "ready to advance":

- Repository state known (`git status --short`)
- Relevant runner script exists and executes
- Candidate run completed with expected question count
- Baseline run completed on same benchmark version
- Baseline-delta gate evaluated
- Failing checks are explicitly identified from gate report

## Standard Validation Commands

```bash
# 1) repo state
if [[ -z "$(git status --short)" ]]; then echo CLEAN; else echo DIRTY; git status --short; fi

# 2) candidate run (example)
.venv/bin/python scripts/run_random_reasoning_benchmark.py \
  --model qwen2.5:7b \
  --max-questions 15 \
  --run-tag qwen7b_candidate

# 3) baseline run (same benchmark version)
.venv/bin/python scripts/run_random_reasoning_benchmark.py \
  --model qwen2.5:0.5b \
  --max-questions 15 \
  --run-tag qwen05b_baseline

# 4) strict baseline-delta gate
.venv/bin/python scripts/evaluate_random_reasoning_gate.py \
  --candidate-summary outputs/random_reasoning_benchmark/qwen7b_candidate/summary.json \
  --baseline-summary outputs/random_reasoning_benchmark/qwen05b_baseline/summary.json \
  --report-path outputs/random_reasoning_benchmark/qwen7b_candidate/gate_vs_baseline.md
```

## Observable Signals During Runs

When a benchmark is running, observers should be able to see:

- Per-question progress (`(i/N) id=<question_id>`)
- Request success rates
- Base/paraphrase/intervention/repair accuracies
- Intervention delta vs base
- Anchor vulnerability metrics
- Consistency and pattern-risk metrics
- Final gate pass/fail checks with reasons

## Drift Guardrail

Before each major decision, regenerate truth from artifacts first, then update docs.

## Capability Expansion Guardrail

When project goals require stronger tooling, better models, or external architectural references, default to capability expansion instead of self-imposed limits. Document what was added, why it was needed, and what measurable gain it is expected to deliver.
