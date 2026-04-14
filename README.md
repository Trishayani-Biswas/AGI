# Local Evolutionary LLM Survival Simulator

This project creates a long-running, local, multi-agent survival simulation where agents:
- make daily decisions using a two-model brain (proposer + critic),
- face hard biological constraints,
- reproduce with 9-month gestation,
- die from dehydration/starvation/old age,
- pass mutated traits and learned action values to offspring,
- discover and socially spread innovations.

It now supports two research modes:
- `LLM mode`: local dual-LLM proposer/critic agents
- `Tabula-rasa mode`: NEAT neuroevolution from random neural policies

## Important Reality Check

No current LLM can be truly knowledge-free because pretraining exists.
This simulator approximates your goal by:
- limiting each agent's explicit prompt to primitive survival context,
- forcing learning through environmental rewards and penalties,
- evolving lineages via mutation + inheritance over many generations.

For closer approximation to zero-prior behavior, use the NEAT mode below.
NEAT starts from random neural networks and learns only from survival outcomes.

## Biological Constraints Implemented

- 3 days without water -> death
- 21 days without food -> death
- life expectancy baseline: 60 years
- gestation: 9 months (273 days)
- puberty threshold for reproduction: 16 years

All values are configurable in environment variables.

## Architecture

- `src/agi_sim/llm.py`: dual-LLM decision engine with fallback heuristic
- `src/agi_sim/neat_training.py`: tabula-rasa NEAT evolutionary trainer
- `src/agi_sim/run_neat.py`: NEAT trainer CLI
- `src/agi_sim/world.py`: world dynamics, action outcomes, innovation effects
- `src/agi_sim/simulation.py`: daily loop, births/deaths, inheritance, logging
- `src/agi_sim/run.py`: CLI parser + config wiring
- `run_simulation.py`: root launcher
- `run_neat_training.py`: root launcher for NEAT mode
- `configs/neat_survival.ini`: tuned NEAT hyperparameters

## Quick Start (Linux)

1. Verify Python:

```bash
python3 --version
```

2. Create virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Install Ollama (if not installed):

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

4. Pull two local models:

```bash
ollama pull llama3.2:3b
ollama pull qwen2.5:3b
```

5. Start Ollama service if needed:

```bash
ollama serve
```

6. Run a quick offline smoke test (no LLM calls):

```bash
python3 run_simulation.py --offline --days 120 --population 10 --verbose-every 10
```

7. Run full dual-LLM evolution:

```bash
python3 run_simulation.py --days 2500 --population 12 --proposer-model llama3.2:3b --critic-model qwen2.5:3b
```

8. Run tabula-rasa NEAT evolution (no LLM priors):

```bash
python3 run_neat_training.py --generations 30 --eval-days 700 --max-population 220
```

9. Quick NEAT smoke test:

```bash
python3 run_neat_training.py --generations 2 --eval-days 90 --max-population 90
```

## Output Files

Generated in `outputs/` by default:
- `events.jsonl`: per-agent per-day actions, rewards, and death events
- `daily_metrics.csv`: population, births, deaths, avg health, innovation count
- `summary.json`: run summary

Generated in `outputs/neat/` for tabula-rasa mode:
- `champion.pkl`: best evolved policy genome
- `history.json`: generation-by-generation fitness records
- `summary.json`: training run summary
- `checkpoint-*`: periodic NEAT checkpoints

## Tuning for More Emergence

- Increase horizon: `--days 10000`
- Increase exploration pressure: set `SIM_EXPLORATION_BOOST` higher
- Switch to stronger local models for deeper strategy
- Run multiple seeds and compare survival lineage patterns

## Environment Configuration

Copy `.env.simulation.example` to `.env.local` (or export variables in shell) and adjust values.

Example:

```bash
export SIM_DAYS=5000
export SIM_INITIAL_POPULATION=18
export SIM_MODEL_PROPOSER=llama3.2:3b
export SIM_MODEL_CRITIC=qwen2.5:7b
python3 run_simulation.py
```
