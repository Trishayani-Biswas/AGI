# Local Evolutionary Intelligence Lab

This repository is a local-first research lab for evolving survival intelligence under biological constraints.

It supports two complementary modes:

- `LLM mode`: local dual-model proposer/critic decision loop.
- `Tabula-rasa mode`: NEAT neuroevolution from random neural policies.

The long-term objective is not chatbot imitation. It is emergent adaptive behavior from consequence, selection, and inheritance.

This project is structured as a scientific program, not just a simulator: each run should produce evidence that can be observed, compared, and challenged.

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

- `run_simulation.py`
: root launcher for simulation mode.

- `run_neat_training.py`
: root launcher for NEAT mode.

- `scripts/build_experiment_observatory.py`
: generates a watch-oriented scientific report from output artifacts.

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
: watch-oriented scientific narrative (hypotheses, family tags, lineage timelines, campaign drift metrics, anomaly markers, stability read).

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

