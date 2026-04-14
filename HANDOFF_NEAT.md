# Handoff: Tabula-Rasa AGI Direction (NEAT)

Date: 2026-04-14

## Direction
Move from pretrained-LLM priors toward tabula-rasa learning using NEAT neuroevolution in the same primitive survival world.

## Implemented So Far
- Added NEAT config: `configs/neat_survival.ini`
- Added trainer engine: `src/agi_sim/neat_training.py`
- Added trainer CLI: `src/agi_sim/run_neat.py`
- Added root launcher: `run_neat_training.py`
- Updated package exports: `src/agi_sim/__init__.py`
- Updated dependencies: `requirements.txt` (now includes `neat-python>=0.92`)
- Updated docs with NEAT workflow: `README.md`

## Environment State
- Virtual environment created: `.venv`
- Installed in venv: `neat-python 2.0.0`

## Current Blocker Status
- First NEAT smoke run failed because NEAT 2.0 requires:
  - `no_fitness_termination = False` in `[NEAT]`
- This key has now been added to `configs/neat_survival.ini`.
- Re-run after patch is still pending.

## Resume From Here (exact command)
```bash
cd /home/Jit-Paul-2008/Desktop/AGI
.venv/bin/python run_neat_training.py --generations 1 --eval-days 45 --max-population 80
```

## If It Fails Again
- If NEAT 2.0 reports another missing config item, add it to `configs/neat_survival.ini` exactly as requested.
- Re-run the same smoke command until it passes.

## Once Smoke Test Passes
```bash
cd /home/Jit-Paul-2008/Desktop/AGI
.venv/bin/python run_neat_training.py --generations 25 --eval-days 700 --max-population 220
```

Then check:
- `outputs/neat/summary.json`
- `outputs/neat/history.json`
- `outputs/neat/champion.pkl`
