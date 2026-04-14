# Evolution Intelligence Roadmap (Mastery-First)

This roadmap is intentionally bold and obvious: each priority has a mastery gate before expansion.

## Priority 1: Observability And Scientific Framing

Why it matters:
- If observers cannot explain what changed and why, the project does not feel scientific.

Mastery gate:
- Every run produces a watch report with hypotheses, conditions, turning points, and variance signals.
- A new observer can understand the run story in under 10 minutes.

Now:
- Implemented observatory report generator: `scripts/build_experiment_observatory.py`.

Next checkpoints:
1. Add day-level anomaly markers (resource crashes, extinction cascades).
2. Add policy-family tagging to show lineage clusters.

## Priority 2: Stability Over Seed Luck

Why it matters:
- A lucky run is not intelligence; repeatable performance is.

Mastery gate:
- Fixed-condition hard-mode campaigns achieve low variance.
- Comparable-run coefficient of variation stays inside target bands.

Now:
- Hard-mode seed campaign is active (A, B, C_fixed, D) with variance tracking.

Next checkpoints:
1. Run larger fixed-condition campaigns (at least 6 seeds).
2. Tune reward pressure and robustness protocol until variance drops.

## Priority 3: Open-Ended Ecology

Why it matters:
- Static worlds cap intelligence depth.

Mastery gate:
- Policies adapt across multiple habitat regimes, not just one seasonal loop.

Next checkpoints:
1. Procedural geography and migration.
2. Region-specific resources and constraints.

## Priority 4: Competitive Co-Evolution

Why it matters:
- Intelligence sharpens under non-trivial opponents.

Mastery gate:
- Champion league over diverse opponents and worlds with consistent rankings.

Next checkpoints:
1. Policy tournaments.
2. Inter-tribe competition or predator/prey pressure.

## Priority 5: Interpretability And Falsifiability

Why it matters:
- Scientific credibility depends on testable claims.

Mastery gate:
- Each release has explicit hypotheses, predicted outcomes, and pass/fail evidence.

Next checkpoints:
1. Hypothesis template for each run batch.
2. Causal ablation tests on environment and reward terms.

## Current Implementation Focus

Current active focus is Priority 1 then Priority 2.

Execution rhythm:
1. Improve observability tooling.
2. Run fixed-condition seed batches.
3. Compare and tighten robustness variance.
4. Move forward only when mastery signals are met.