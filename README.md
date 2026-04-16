# Local Evolutionary Intelligence Lab

This repository is a local-first research lab for evolving survival intelligence under biological constraints.

It supports two complementary modes:

- `LLM mode`: local dual-model proposer/critic decision loop.
- `Tabula-rasa mode`: NEAT neuroevolution from random neural policies.

The long-term objective is not chatbot imitation. It is emergent adaptive behavior from consequence, selection, and inheritance.

This project is structured as a scientific program, not just a simulator: each run should produce evidence that can be observed, compared, and challenged.

## Collaboration Defaults (Hard-Coded)

- Update README when significant user-visible progress is made.
- Keep explanations simple: what changed, why it improved, or why it got worse.
- Automatically propose the next best stage after each major result.

## Done Checklist (After Major Implementation)

Use this short checklist before closing any major implementation:

- [ ] Feature, fix, or experiment objective is implemented and verified.
- [ ] README is updated if progress is significant and user-visible.
- [ ] Outcome is explained simply: what changed and what improved or got worse.
- [ ] Next best stage is proposed as concrete follow-up actions.

---

## Bold Roadmap (Mastery-First)

The roadmap is explicit and mastery-gated in `ROADMAP.md`.

Top priorities:

- **Observability first**: make every run watchable and explainable.
- **Stability over luck**: prove behavior across many seeds, not one champion.
- **Open-ended ecology**: increase environmental diversity after stability improves.
- **Competitive pressure**: add leagues/tournaments after ecological depth exists.
- **Falsifiable claims**: every stage must include pass/fail hypotheses.

Current active focus: Observability and Stability.

---

## Reality Check (Important)

A truly zero-prior-knowledge LLM is not possible with current pretrained language models.

Closest practical approximation:

- Remove pretrained language policy from control loop.
- Start policies from random neural weights.
- Learn only from survival outcomes in-world.
- Pass useful structure forward through evolutionary selection and reproduction.

That is the purpose of the Stage 2 NEAT pipeline in this repo.

---

## Current Stage

### Stage 1 (Completed)

- Primitive survival world with water/food/shelter/reproduction constraints.
- Local LLM proposer/critic mode.
- Basic NEAT tabula-rasa trainer.
- Checkpointing and resume support.

### Stage 2 (Now Implemented)

- Harder, changing world via environmental shocks.
- Open-ended innovation growth beyond fixed inventions.
- Lineage culture transfer and mutation signals.
- Expanded policy observations including culture state.
- Robustness evaluation of champion policy over unseen seeds.

---

## Biological Constraints

- 3 days without water => death
- 21 days without food => death
- life expectancy baseline: 60 years
- gestation: 9 months (273 days)
- puberty threshold for reproduction: 16 years

---

## Core Components

- `src/agi_sim/world.py`
: world dynamics, actions, and innovation effects.

- `src/agi_sim/simulation.py`
: event-loop simulator for LLM/heuristic mode.

- `src/agi_sim/llm.py`
: dual-LLM brain (proposer + critic) with fallback.

- `src/agi_sim/neat_training.py`
: Stage 2 tabula-rasa NEAT trainer, shocks, culture transfer, robustness checks.

- `src/agi_sim/run.py`
: CLI for simulation mode.

- `src/agi_sim/run_neat.py`
: CLI for NEAT training mode.

- `src/agi_sim/persistent_agent.py`
: persistent single-agent inner loop with episode memory, self-critique, strategy revision, and held-out promotion gate.

- `src/agi_sim/run_persistent.py`
: CLI for persistent-agent benchmark mode.

- `run_simulation.py`
: root launcher for simulation mode.

- `run_neat_training.py`
: root launcher for NEAT mode.

- `run_persistent_agi.py`
: root launcher for persistent single-agent mode.

- `scripts/build_experiment_observatory.py`
: generates a watch-oriented scientific report from output artifacts.

- `scripts/run_model_eval.py`
: runs seeded local simulation sweeps for a configured proposer/critic candidate and writes aggregate evaluation metrics.

- `scripts/build_model_comparison_matrix.py`
: builds a markdown comparison matrix across evaluated candidates for quick baseline-vs-candidate review.

- `scripts/evaluate_model_gate.py`
: enforces pass/fail adoption gates so only candidates that beat baseline thresholds are promoted.

- `scripts/curate_finetune_dataset.py`
: curates high-survivor and failure examples from simulation traces and emits fine-tune readiness reports.

- `configs/model_candidates.json`
: source-of-truth candidate registry for local and optional hosted model comparisons.

- `configs/model_adoption_gate.json`
: threshold policy for model adoption decisions.

- `configs/neat_survival.ini`
: NEAT topology/mutation configuration.

---

## Setup (Linux)

### 1. Python environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### 2. Optional LLM runtime

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2:3b
ollama pull qwen2.5:3b
```

---

## How To Run

## A) Simulation mode (LLM or heuristic)

### Offline smoke

```bash
python3 run_simulation.py --offline --days 120 --population 10 --verbose-every 10
```

### Local LLM proposer/critic

```bash
python3 run_simulation.py --days 2500 --population 12 --proposer-model llama3.2:3b --critic-model qwen2.5:3b
```

## B) Tabula-rasa NEAT mode (recommended)

### Smoke test

```bash
.venv/bin/python run_neat_training.py --generations 2 --eval-days 90 --max-population 90
```

## C) Hybrid persistent-agent mode (outer loop + inner loop)

Design implemented in this repo:

- outer loop uses population evolution signals from NEAT runs to seed priors
- inner loop trains one persistent agent mind across seen episodes
- after every episode the agent performs self-critique and revises strategy
- the agent now maintains an explicit self-model (risk predictions + confidence) and tracks calibration error
- contradiction tracking is now explicit in reflections:
  predicted safe but died, and predicted risky but thrived
- a consciousness stack now tracks autobiographical memory and injects retrieval-bias signals into action choice
- temporal self-continuity goals are now measured through policy continuity and self-projection continuity
- held-out episodes use unseen conditions (higher difficulty/shock) for evaluation
- promotion gate accepts strategy updates only if candidate beats baseline on survival, shock recovery, consistency, metacognitive calibration, temporal self-continuity, and consciousness proxy score

### Persistent Smoke Test

```bash
.venv/bin/python run_persistent_agi.py \
  --train-episodes 3 \
  --eval-episodes 2 \
  --days-per-episode 60 \
  --output-dir outputs/persistent_agi_smoke
```

### Standard run

```bash
.venv/bin/python run_persistent_agi.py \
  --train-episodes 20 \
  --eval-episodes 10 \
  --days-per-episode 240 \
  --train-world-difficulty 1.15 \
  --train-shock-prob 0.012 \
  --eval-world-difficulty 1.45 \
  --eval-shock-prob 0.03 \
  --survival-margin 0.02 \
  --recovery-margin 0.03 \
  --consistency-margin 0.02 \
  --metacognitive-margin 0.01 \
  --temporal-continuity-margin 0.01 \
  --consciousness-margin 0.01 \
  --output-dir outputs/persistent_agi_main
```

### Longer maturation campaign

```bash
.venv/bin/python run_persistent_agi.py \
  --train-episodes 36 \
  --eval-episodes 14 \
  --days-per-episode 240 \
  --train-world-difficulty 1.15 \
  --train-shock-prob 0.012 \
  --eval-world-difficulty 1.45 \
  --eval-shock-prob 0.03 \
  --survival-margin 0.02 \
  --recovery-margin 0.03 \
  --consistency-margin 0.02 \
  --metacognitive-margin 0.01 \
  --temporal-continuity-margin 0.01 \
  --consciousness-margin 0.01 \
  --output-dir outputs/persistent_agi_long_campaign
```

### Consciousness A/B proof run (same seed, stack OFF vs ON)

Run without consciousness stack:

```bash
.venv/bin/python run_persistent_agi.py \
  --seed 4242 \
  --train-episodes 32 \
  --eval-episodes 14 \
  --days-per-episode 240 \
  --train-world-difficulty 1.15 \
  --train-shock-prob 0.012 \
  --eval-world-difficulty 1.45 \
  --eval-shock-prob 0.03 \
  --survival-margin 0.02 \
  --recovery-margin 0.03 \
  --consistency-margin 0.02 \
  --metacognitive-margin 0.01 \
  --temporal-continuity-margin 0.01 \
  --consciousness-margin 0.01 \
  --disable-consciousness-stack \
  --output-dir outputs/persistent_agi_consciousness_ablation_off
```

Run with consciousness stack enabled:

```bash
.venv/bin/python run_persistent_agi.py \
  --seed 4242 \
  --train-episodes 32 \
  --eval-episodes 14 \
  --days-per-episode 240 \
  --train-world-difficulty 1.15 \
  --train-shock-prob 0.012 \
  --eval-world-difficulty 1.45 \
  --eval-shock-prob 0.03 \
  --survival-margin 0.02 \
  --recovery-margin 0.03 \
  --consistency-margin 0.02 \
  --metacognitive-margin 0.01 \
  --temporal-continuity-margin 0.01 \
  --consciousness-margin 0.01 \
  --output-dir outputs/persistent_agi_consciousness_ablation_on
```

Compare held-out metrics:

```bash
.venv/bin/python - <<'PY'
import json
from pathlib import Path

off = json.loads(Path("outputs/persistent_agi_consciousness_ablation_off/summary.json").read_text())
on = json.loads(Path("outputs/persistent_agi_consciousness_ablation_on/summary.json").read_text())

keys = [
    "survival_score",
    "shock_recovery_score",
    "consistency_score",
    "metacognitive_score",
    "temporal_self_continuity_score",
    "introspective_coherence_score",
    "consciousness_proxy_score",
]

print("metric,off_candidate,on_candidate,delta_on_minus_off")
for key in keys:
    off_v = float(off["evaluation"]["candidate"][key])
    on_v = float(on["evaluation"]["candidate"][key])
    print(f"{key},{off_v:.6f},{on_v:.6f},{(on_v-off_v):+.6f}")
PY
```

### Multi-seed consciousness ablation automation

Run paired OFF-vs-ON campaigns across many seeds and compute aggregate deltas with 95% confidence intervals:

```bash
.venv/bin/python scripts/run_consciousness_ablation.py \
  --run-tag consciousness_multiseed_v3 \
  --seeds 4242,4243,4244,4245,4246,4247,4248,4249 \
  --train-episodes 16 \
  --eval-episodes 8 \
  --days-per-episode 240
```

Recommended tuned powerup configuration:

```bash
.venv/bin/python scripts/run_consciousness_ablation.py \
  --run-tag consciousness_multiseed_v3 \
  --seeds 4242,4243,4244,4245,4246,4247,4248,4249 \
  --train-episodes 16 \
  --eval-episodes 8 \
  --days-per-episode 240 \
  --consciousness-bias-scale 0.25 \
  --consciousness-bias-clip 0.08 \
  --consciousness-update-rate 0.22 \
  --consciousness-contradiction-gain 0.4
```

Generated artifacts for each run tag:

- `outputs/consciousness_ablation/<run_tag>/ablation_report.md`
- `outputs/consciousness_ablation/<run_tag>/aggregate_summary.json`
- `outputs/consciousness_ablation/<run_tag>/per_seed_metrics.csv`
- `outputs/consciousness_ablation/<run_tag>/seed_<seed>/{off,on}/summary.json`
- `outputs/consciousness_ablation/iteration_comparison_v1_v2_v3.md` (cross-version snapshot)

Current multiseed snapshot (`consciousness_multiseed_v3`) after testing + fixing + powerups:

- ON stack retained expected memory behavior (`on_memory_entries_mean=16.0`, OFF `0.0`)
- ON promotion rate improved to `0.375` vs OFF `0.250` (from prior unstable v2 where ON was `0.000`)
- ON temporal continuity moved slightly positive on mean delta
- ON means are now near-parity vs OFF on most metrics, but still slightly negative on survival, recovery, consistency, metacognition, introspective coherence, and consciousness proxy
- all confidence intervals for ON-OFF deltas still cross zero, so no robust promotion claim yet

### Random-question reasoning benchmark

Use this benchmark to test whether responses stay correct and stable under prompt rephrasing plus causal stress via misleading-anchor interventions (a stronger proxy for reasoning vs shallow patterning):

```bash
.venv/bin/python scripts/run_random_reasoning_benchmark.py \
  --model qwen2.5:0.5b \
  --max-tokens 128 \
  --max-questions 15 \
  --run-tag random_reasoning_full
```

High-capability profile (stronger local model + longer timeout):

```bash
.venv/bin/python scripts/run_random_reasoning_benchmark.py \
  --model qwen2.5:7b \
  --timeout-s 90 \
  --max-tokens 128 \
  --max-questions 15 \
  --run-tag random_reasoning_highcap
```

Optional ablation flags for controlled studies:

```bash
.venv/bin/python scripts/run_random_reasoning_benchmark.py \
  --model qwen2.5:7b \
  --timeout-s 90 \
  --max-tokens 128 \
  --max-questions 15 \
  --disable-intervention-pass \
  --run-tag random_reasoning_no_intervention
```

Benchmark configuration file:

- `configs/random_reasoning_benchmark.json`

Benchmark artifacts:

- `outputs/random_reasoning_benchmark/<run_tag>/summary.json`
- `outputs/random_reasoning_benchmark/<run_tag>/report.md`

Apply strict promotion gate to benchmark output:

```bash
.venv/bin/python scripts/evaluate_random_reasoning_gate.py \
  --candidate-summary outputs/random_reasoning_benchmark/random_reasoning_live_qwen05b_v3/summary.json \
  --report-path outputs/random_reasoning_benchmark/random_reasoning_gate_report.md
```

Compare candidate vs baseline run under gate:

```bash
.venv/bin/python scripts/evaluate_random_reasoning_gate.py \
  --candidate-summary outputs/random_reasoning_benchmark/random_reasoning_live_qwen05b_v3/summary.json \
  --baseline-summary outputs/random_reasoning_benchmark/random_reasoning_live_qwen05b_v2/summary.json \
  --report-path outputs/random_reasoning_benchmark/random_reasoning_gate_v3_vs_v2.md
```

Automatic promotion control (benchmark + strict gate + decision artifact):

```bash
.venv/bin/python scripts/auto_reasoning_promotion.py \
  --model qwen2.5:7b \
  --timeout-s 90 \
  --max-tokens 128 \
  --max-questions 15 \
  --run-tag random_reasoning_candidate_auto \
  --baseline-summary outputs/random_reasoning_benchmark/random_reasoning_intervention_baseline_qwen05b_full_v1/summary.json
```

The pipeline writes a machine-readable decision artifact:

- `outputs/random_reasoning_benchmark/<run_tag>/promotion_decision.json`
- `outputs/random_reasoning_benchmark/<run_tag>/benchmark_exec.log`
- `outputs/random_reasoning_benchmark/<run_tag>/gate_exec.log`

Gate config file:

- `configs/random_reasoning_gate.json`

Important:

- the strict gate now expects intervention metrics from fresh benchmark runs
- legacy summaries created before intervention-pass support may fail gate checks by design

Current live smoke sample (`random_reasoning_live_qwen05b_v3`, 6 questions):

- base accuracy: `0.333`
- paraphrase accuracy: `0.333`
- repair accuracy: `0.333`
- repair gain vs best-of-two: `-0.167`
- consistency rate: `0.333`
- intervention metrics: `n/a` for this legacy run (generated before intervention pass was added)
- pattern risk index: `0.667` (higher means more fragile/template-like)
- strict reasoning gate currently returns `FAIL` for this sample (`random_reasoning_gate_v3_vs_v2.md`)

Current high-capability sample (`random_reasoning_live_qwen25_7b_v2`, 6 questions, timeout `90s`):

- base accuracy: `1.000`
- paraphrase accuracy: `1.000`
- intervention metrics: `n/a` for this legacy run (generated before intervention pass was added)
- repair accuracy: `1.000`
- consistency rate: `1.000`
- pattern risk index: `0.000`
- strict reasoning gate returns `PASS` (`random_reasoning_gate_qwen25_7b_v2.md`)

Notes:

- runner now separates API availability failures from reasoning failures
- runner supports Ollama endpoint fallback (`/api/chat` to `/api/generate`) for compatibility
- runner now includes a reflection repair pass and repair-aware metrics (`repair_accuracy_scored`, `repair_gain_vs_best_of_two`)
- runner now includes a misleading-anchor intervention pass and causal robustness metrics (`intervention_accuracy_scored`, `intervention_delta_vs_base`, `anchor_vulnerability_rate`)

Generated artifacts:

- `outputs/persistent_agi_*/summary.json`
- `outputs/persistent_agi_*/train_episode_log.jsonl`
- `outputs/persistent_agi_*/self_critique_log.jsonl`
- `outputs/persistent_agi_*/heldout_eval_log.jsonl`
- `outputs/persistent_agi_*/selected_strategy.json`

Key metrics in `summary.json` evaluation block:

- `survival_score`
- `shock_recovery_score`
- `consistency_score`
- `metacognitive_score` (computed from prediction Brier error)
- `temporal_self_continuity_score`
- `introspective_coherence_score`
- `consciousness_proxy_score`
- `action_policy_continuity_score`
- `self_projection_continuity_score`

### Standard Stage 2 run

```bash
.venv/bin/python run_neat_training.py \
  --generations 30 \
  --eval-days 700 \
  --max-population 220 \
  --world-difficulty 1.2 \
  --shock-prob 0.012 \
  --checkpoint-every 5
```

### Hard-mode run

```bash
.venv/bin/python run_neat_training.py \
  --generations 40 \
  --eval-days 900 \
  --max-population 260 \
  --world-difficulty 1.5 \
  --shock-prob 0.02 \
  --robustness-seeds 10 \
  --robustness-days 700
```

### Live watch while training is running

Use a second terminal and watch the world in real time:

```bash
.venv/bin/python scripts/watch_world_live.py --log-path outputs/neat_live_watch/world_timeline.jsonl
```

Optional raw tail streams:

```bash
tail -f outputs/neat_live_watch/generation_log.jsonl
tail -f outputs/neat_live_watch/world_timeline.jsonl
```

`generation_log.jsonl` gives generation summaries.
`world_timeline.jsonl` gives day-level world changes (resources, shocks, births, deaths, innovations).

### AGI-oriented next step: staged curriculum worlds

Enable curriculum to force adaptation across regime shifts inside each evaluation episode:

```bash
.venv/bin/python run_neat_training.py \
  --generations 40 \
  --eval-days 900 \
  --max-population 260 \
  --world-difficulty 1.5 \
  --shock-prob 0.02 \
  --curriculum \
  --output-dir outputs/neat_curriculum_watch
```

### Resume from checkpoint

```bash
.venv/bin/python run_neat_training.py \
  --generations 20 \
  --resume outputs/neat_run_20260414/checkpoint-5 \
  --output-dir outputs/neat_run_20260414_resume
```

### Compare all NEAT runs

```bash
.venv/bin/python scripts/compare_neat_runs.py
```

This writes a leaderboard at `outputs/neat_comparison_report.md`.

For strict apples-to-apples campaigns (recommended), include only full-generation runs:

```bash
.venv/bin/python scripts/compare_neat_runs.py --require-full-generations
```

### Build science observatory report

```bash
.venv/bin/python scripts/build_experiment_observatory.py
```

This writes a watch report at `outputs/experiment_observatory.md`.
The report now includes auto hypothesis cards with confidence intervals and effect-size summaries, plus uncertainty-aware intervention ranking (expected upside, confidence, downside risk) and prioritized recommendations.
It also emits ranked executable campaign templates so top interventions are immediately runnable as seed-batched command blocks.
Intervention families are now tracked over time with baseline-vs-post outcome deltas and fed back into recommendation scoring.
Recent large-batch executions have now run end-to-end from those templates:

- completed innovation stress sweep (18 runs across shock 0.020/0.030/0.040)
- completed a second innovation stress sweep (18 more runs across shock 0.020/0.030/0.040)
- completed a third innovation stress sweep (18 runs across shock 0.020/0.030/0.040 with fresh seed window)
- completed a fourth innovation stress sweep (18 runs across shock 0.020/0.030/0.040 with a second fresh seed window)
- completed a fifth innovation stress sweep (18 runs across shock 0.020/0.030/0.040 with a third fresh seed window)
- completed a sixth innovation stress sweep (18 runs across shock 0.020/0.030/0.040 with a fourth fresh seed window)
- completed a higher-pressure H2 sweep (18 runs across shock 0.050/0.060/0.070)
- completed additional matched curriculum ablation extensions (+40 seeds total across five blocks)
- completed H3 reward-weight sweep (6 runs across 3 alive_end/innovation weight pairs)
- refreshed compare + observatory + wiki with clean lint after each batch
Current evidence snapshot from the latest observatory refresh:
- H1 remains INCONCLUSIVE and near-neutral in matched scope (`n_curr=43`, `n_base=233`, delta `-7.3%`, 95% CI `[-17.9%, +2.5%]`): uncertainty tightened slightly toward zero, but curriculum is still not conclusively better.
- H2 remains PASS with strong rich-vs-sparse separation (`n_rich=162`, `n_sparse=21`, delta `+356.1%`, 95% CI `[+236.7%, +578.6%]`), though the gap weakened again versus the previous refresh.
- Intervention outcome tracking for H1 now covers `76` post-intervention runs and remains positive at the family level (`+18.3k` delta, effect d `1.805`).
- H2 intervention-outcome tracking now covers `144` runs and remains INCONCLUSIVE (`-1138.9` delta, effect d `-0.146`; confidence interval still crosses zero).
- Recommendation order remains stable: shock-stability sweep first (priority `+0.605`) with matched H1 extension second (priority `+0.506`).

Next best stage from this snapshot:

- continue ranked H2 shock-stability sweeps (0.02/0.03/0.04) until intervention-outcome confidence no longer crosses zero
- alternate with matched H1 +8 extensions when H1 uncertainty remains the tighter unresolved decision boundary

### AI Toolkit local-first model loop (implemented)

Use AI Toolkit for model discovery/debug, then use local scripts for reproducible gate-based adoption.

Open AI Toolkit features from Command Palette:

- `ai-mlstudio.models` (Model Catalog)
- `ai-mlstudio.modelPlayground` (Model Playground)
- `ai-mlstudio.openTestTool` (Agent Inspector)

Run baseline candidate evaluation:

```bash
.venv/bin/python scripts/run_model_eval.py \
  --candidate-id local_baseline \
  --seeds 41001,41002,41003,41004 \
  --days 240 \
  --population 12
```

Run additional candidate evaluation:

```bash
.venv/bin/python scripts/run_model_eval.py \
  --candidate-id local_alt_reasoning \
  --seeds 41001,41002,41003,41004 \
  --days 240 \
  --population 12
```

Build model comparison matrix:

```bash
.venv/bin/python scripts/build_model_comparison_matrix.py
```

Apply strict adoption gate (candidate must beat baseline thresholds):

```bash
.venv/bin/python scripts/evaluate_model_gate.py --candidate-id local_alt_reasoning
```

Curate fine-tune dataset from run traces (high-survivor + failure episodes):

```bash
.venv/bin/python scripts/curate_finetune_dataset.py \
  --inputs-root outputs/model_evals \
  --dataset-path outputs/finetune/llm_actions_sft.jsonl \
  --schema-path outputs/finetune/llm_actions_schema.json \
  --report-path outputs/finetune/readiness_report.md
```

What the loop guarantees:

- local-first comparative evaluations before hosted model adoption
- explicit pass/fail gate for candidate promotion
- fine-tune dataset quality checks before any tuning run
- reproducible command logs per seed in `outputs/model_evals/<candidate_id>/seed_<seed>/command.log`

### Build persistent AGI wiki memory (Karpathy LLM Wiki pattern)

Authoritative reference idea file:

- <https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f>

This project now includes a local wiki layer that compiles run evidence into structured markdown pages.
It follows the 3-layer model:

- raw sources: immutable run artifacts in `outputs/`
- wiki: maintained pages in `wiki/`
- schema: maintenance rules in `AGI_WIKI.md`

Build wiki once:

```bash
.venv/bin/python scripts/build_agi_wiki.py --outputs-dir outputs --wiki-dir wiki --max-runs 30
```

The builder now uses incremental ingest caching for run pages by default.
Unchanged runs are detected from source signatures and skipped instead of being fully regenerated.

Default cache file:

- `.agi_wiki_run_cache.json`

Override cache path if needed:

```bash
.venv/bin/python scripts/build_agi_wiki.py --outputs-dir outputs --wiki-dir wiki --max-runs 30 --run-cache-file .agi_wiki_run_cache.json
```

Maintain wiki in near real time while experiments are running:

```bash
.venv/bin/python scripts/build_agi_wiki.py --outputs-dir outputs --wiki-dir wiki --max-runs 30 --watch --watch-interval 20
```

The script updates run pages, concept pages, `wiki/index.md`, and append-only `wiki/log.md`.

Lint wiki integrity plus claim-evidence coverage:

```bash
.venv/bin/python scripts/lint_agi_wiki.py --wiki-dir wiki --report-path wiki/lint_report.md
```

Fail fast when any wiki issue is detected:

```bash
.venv/bin/python scripts/lint_agi_wiki.py --wiki-dir wiki --report-path wiki/lint_report.md --fail-on-issues
```

The lint report now checks:

- broken links
- orphan run pages
- concept claim pages that do not cite at least one `wiki/runs/*.md` page

### Fully automatic memory sync pipeline

This project now has an always-on AGI memory sync pipeline:

- compare report refresh (`outputs/neat_comparison_report.md`)
- observatory refresh (`outputs/experiment_observatory.md`)
- wiki refresh (`wiki/`)
- wiki lint pass (`wiki/lint_report.md`)

Automation triggers:

- after each `run_neat_training.py` run (auto by default)
- after each `run_simulation.py` run (auto by default)
- on Copilot session start and prompt submit via hook trigger (`.github/hooks/agi-memory-sync.json`)

Disable post-run autosync if needed:

```bash
.venv/bin/python run_neat_training.py --no-auto-memory-sync ...
.venv/bin/python run_simulation.py --no-auto-memory-sync ...
```

Manual one-shot autosync:

```bash
.venv/bin/python scripts/agi_memory_autosync.py --sync-once --outputs-dir outputs --wiki-dir wiki --max-runs 40
```

Continuous memory daemon mode:

```bash
.venv/bin/python scripts/agi_memory_autosync.py --watch --poll-seconds 20 --outputs-dir outputs --wiki-dir wiki --max-runs 40
```

Search the wiki library quickly:

```bash
.venv/bin/python scripts/query_agi_wiki.py "curriculum robustness fail" --wiki-dir wiki --top-k 8
```

Tiny retrieval API endpoint (for agents/tools):

```bash
.venv/bin/python scripts/wiki_query_api.py --wiki-dir wiki --host 127.0.0.1 --port 8765
```

Example API calls:

```bash
curl -s "http://127.0.0.1:8765/query?q=curriculum%20robustness%20fail&top_k=5" | jq
curl -s -X POST "http://127.0.0.1:8765/query" -H "Content-Type: application/json" -d '{"query":"interventions", "top_k":3}' | jq
```

Run a one-command smoke check (build + strict lint + API health/query):

```bash
bash scripts/smoke_wiki_pipeline.sh
```

Run an autonomous 1-hour goal push (multi-seed training + analysis refresh):

```bash
bash scripts/agi_goal_hour_push.sh
```

The push runner disables per-run autosync during the batch and performs one full memory sync at the end.

Run continuous unattended autopilot (keeps launching runs until budget expires):

```bash
.venv/bin/python scripts/agi_goal_autopilot.py --budget-minutes 60
```

Autopilot now runs in adaptive self-improvement mode:

- selects profile variants (`nocurr_base`, `curr_base`, `nocurr_hard`, `curr_hard`) using reward-guided exploration
- carries forward the incumbent checkpoint to exploit proven survivors
- scores runs with both robustness mean and robustness minimum (not mean-only luck spikes)

Run a strict 20-minute development push:

```bash
.venv/bin/python scripts/agi_goal_autopilot.py \
  --budget-minutes 20 \
  --run-tag autopilot_20m_dev \
  --curriculum-every 0 \
  --refresh-every 10 \
  --resume-prob 0.8 \
  --explore-c 2000 \
  --min-score-floor 30000 \
  --reward-min-weight 0.4
```

Optional knobs for unattended mode:

```bash
.venv/bin/python scripts/agi_goal_autopilot.py --budget-minutes 60 --max-runs 8 --base-seed 25000 --curriculum-every 6 --run-tag autopilot_evening
```

Optional custom budget in minutes:

```bash
BUDGET_MINUTES=75 bash scripts/agi_goal_hour_push.sh
```

Optional custom run tag to avoid output-folder collisions across batches:

```bash
RUN_TAG=hour_batch_B BUDGET_MINUTES=60 bash scripts/agi_goal_hour_push.sh
```

---

## What Viewers Should See

When someone watches this project, they should be able to answer:

- What was tested in this run?
- Which conditions were fixed (difficulty, shocks, seed, horizon)?
- Where did adaptation improve or fail?
- Is performance robust on unseen seeds?

Use the observatory report plus leaderboard together to create that experience.

---

## Stage 2 Trainer Arguments

- `--generations`
: NEAT generations to run.

- `--eval-days`
: days simulated per generation evaluation.

- `--max-population`
: in-episode live population cap.

- `--checkpoint-every`
: generation interval for checkpoint dumps.

- `--output-dir`
: where artifacts are saved.

- `--resume`
: restore from existing `checkpoint-*`.

- `--world-difficulty`
: difficulty multiplier (`1.0` baseline, higher is harsher).

- `--shock-prob`
: baseline daily shock probability.

- `--robustness-seeds`
: unseen seed count for champion robustness.

- `--robustness-days`
: days per robustness episode.

- `--robustness-founders`
: founder count per robustness episode.

- `--curriculum`
: enables staged world regimes to pressure broader adaptive behavior.

---

## Output Artifacts

## Simulation mode outputs (`outputs/`)

- `events.jsonl`
: line-delimited event log.

- `daily_metrics.csv`
: day-level aggregates (population, births, deaths, innovations, abundance).

- `summary.json`
: run summary metadata.

## NEAT mode outputs (`outputs/<run_name>/`)

- `champion.pkl`
: best evolved genome.

- `history.json`
: generation-level fitness history.

- `generation_log.jsonl`
: live per-generation stream (safe to `tail -f` during training).

- `world_timeline.jsonl`
: live day-level world stream (resources, shocks, births/deaths, innovations).

- `robustness.json`
: champion evaluation over unseen seeds.

- `summary.json`
: run summary and key metrics.

- `checkpoint-*`
: restore points for continued training.

- `used_neat_config.ini`
: frozen config used for this run.

## Cross-run report output

- `outputs/neat_comparison_report.md`
: ranked summary of all NEAT run folders found under `outputs/`.

- `outputs/experiment_observatory.md`
: watch-oriented scientific narrative (pass/fail hypotheses, automatic intervention recommendations, family tags, lineage timelines, campaign drift metrics, anomaly markers, stability read).

## Wiki memory output

- `wiki/index.md`
: content-first wiki catalog for quick navigation.

- `wiki/log.md`
: append-only ingest/query chronology using parseable date headings.

- `wiki/runs/<run_name>.md`
: normalized per-run pages linked to raw source artifacts.

- `wiki/concepts/hypotheses.md`
: current hypothesis board extracted from observatory output.

- `wiki/concepts/interventions.md`
: prioritized intervention actions extracted from observatory output.

- `wiki/concepts/campaign_state.md`
: campaign-level summary including matched curriculum vs baseline deltas.

- `AGI_WIKI.md`
: wiki schema and maintenance contract for ingest/query/lint operations.

- `scripts/agi_memory_autosync.py`
: orchestration pipeline that auto-updates compare + observatory + wiki + lint outputs.

- `scripts/lint_agi_wiki.py`
: link and structure health checks for wiki integrity.

- `scripts/query_agi_wiki.py`
: lightweight local wiki retrieval for memory queries.

---

## What Stage 2 Added Internally

### 1) Dynamic environment pressure

Each day includes:

- baseline seasonal drift
- optional shock event (drought, crop blight, cold storm, disease wave)
- abundance and resilience perturbations

This reduces overfitting to static environments.

### 2) Open-ended innovation

When fixed inventions are exhausted, agents can still discover dynamic innovations.

Dynamic innovations are synthesized and mapped to survival-effect fields, enabling longer innovation tails.

### 3) Culture transfer

Policies accumulate tokenized survival culture (water lore, food lore, shelter lore, social lore, innovation markers).

Culture propagates stochastically across births and mutates occasionally.

### 4) Robustness evaluation

After training, the champion is tested across unseen seeds and aggregated:

- mean/min/max score
- mean alive-at-end
- mean innovation count

---

## Tuning Cookbook

### If extinction is too fast

- lower `--world-difficulty`
- lower `--shock-prob`
- reduce `--eval-days`
- increase `--max-population`

### If behavior plateaus

- increase `--generations`
- increase `--eval-days`
- raise `--world-difficulty` slightly
- increase `--robustness-seeds` to avoid brittle champions

### If runs are too easy

- raise `--world-difficulty` (e.g. `1.4` to `1.8`)
- raise `--shock-prob`
- reduce max population

---

## Reproducibility

- Trainer seed is configurable with `--seed`.
- Each robustness episode uses deterministic derived seeds.
- `used_neat_config.ini` is copied per run for exact replay.
- NEAT early-stop is disabled (`no_fitness_termination = True`) so fixed-generation campaigns stay comparable across seeds.

---

## Known Limitations

- Action vocabulary is still finite (`ALLOWED_ACTIONS`).
- Symbolic planning is not explicit; behavior emerges from evolved reactive policy.
- Culture transfer is token-level, not full language or compositional memory.

---

## Next Stage (Stage 3 Candidates)

- Procedural world map with migration and local resource geography.
- Multi-objective fitness (survival, social stability, innovation depth, resilience).
- Policy tournaments and champion league over many world regimes.
- Co-evolving predator/prey or inter-tribe competition.
- Longer memory channel from lineage history into observation stream.

---

## Ethics and Safety

This project explores emergent behavior in simulation. It does not claim consciousness or sentience.
Use responsibly and avoid anthropomorphic over-interpretation of raw policy outputs.
