# Evolution Intelligence Roadmap (Mastery-First)

This roadmap is intentionally bold and obvious: each priority has a mastery gate before expansion.

## Priority 1: Observability And Scientific Framing

Why it matters:
- If observers cannot explain what changed and why, the project does not feel scientific.

Mastery gate:
- Every run produces a watch report with hypotheses, conditions, turning points, and variance signals.
- A new observer can understand the run story in under 10 minutes.

Now:
- Implemented observatory report generator with anomaly markers, policy-family tags, compact lineage timelines, campaign drift metrics, auto hypothesis cards, and automatic intervention recommendations: `scripts/build_experiment_observatory.py`.
- Implemented persistent AGI wiki memory layer (raw sources -> wiki -> schema) with automated ingest/index/log maintenance: `scripts/build_agi_wiki.py`, `wiki/`, `AGI_WIKI.md`.
- Implemented automatic memory orchestration pipeline that refreshes compare + observatory + wiki + lint outputs after runs and via hook triggers: `scripts/agi_memory_autosync.py`, `scripts/lint_agi_wiki.py`, `.github/hooks/agi-memory-sync.json`.
- Added confidence intervals and effect-size summaries to hypothesis cards for curriculum ablation, innovation-family gap, survivorship correlation, and campaign drift: `scripts/build_experiment_observatory.py`.
- Added uncertainty-aware intervention ranking that scores actions by expected upside, confidence, and downside risk before recommending next experiments: `scripts/build_experiment_observatory.py`.
- Added ranked executable campaign templates generated from top interventions, including command-ready seed-batch loops and post-batch sync commands: `scripts/build_experiment_observatory.py`.
- Added intervention outcome tracking that compares post-intervention robustness against pre-intervention baselines and feeds historical outcomes back into ranking: `scripts/build_experiment_observatory.py`.

Next checkpoints:
1. Add cross-run causal ablation summaries for major metric jumps.
2. Add auto-execution mode for top-ranked templates with budget caps and post-run scorecards.

## Priority 2: Stability Over Seed Luck

Why it matters:
- A lucky run is not intelligence; repeatable performance is.

Mastery gate:
- Fixed-condition hard-mode campaigns achieve low variance.
- Comparable-run coefficient of variation stays inside target bands.

Now:
- Hard-mode seed campaign is active (A, B, C_fixed, D) with variance tracking.
- Completed ranked intervention template execution for innovation stress sweep (18 runs at shock 0.020/0.030/0.040) with post-batch full sync/lint.
- Completed a second innovation stress sweep (18 more runs at shock 0.020/0.030/0.040) with post-batch full sync/lint.
- Completed a third innovation stress sweep (18 runs at shock 0.020/0.030/0.040 with fresh seeds) with post-batch full sync/lint.
- Completed a fourth innovation stress sweep (18 runs at shock 0.020/0.030/0.040 with a second fresh seed window) with post-batch full sync/lint.
- Completed a fifth innovation stress sweep (18 runs at shock 0.020/0.030/0.040 with a third fresh seed window) with post-batch full sync/lint.
- Completed a higher-pressure H2 sweep (18 runs at shock 0.050/0.060/0.070) with post-batch full sync/lint.
- Completed another matched curriculum ablation extension (+8 seeds) with post-batch full sync/lint.
- Completed a second matched curriculum extension block (+8 seeds) with post-batch full sync/lint.
- Completed a third matched curriculum extension block (+8 seeds; total +24 extension seeds across three blocks) with post-batch full sync/lint.
- Completed a fourth matched curriculum extension block (+8 seeds; total +32 extension seeds across four blocks) with post-batch full sync/lint.
- Completed a fifth matched curriculum extension block (+8 seeds; total +40 extension seeds across five blocks) with post-batch full sync/lint.
- Completed H3 reward-weight sweep (alive_end vs innovation) with post-batch full sync/lint; higher alive_end weighting improved robustness and average survivorship, while innovation-heavy weighting underperformed.
- Latest hypothesis snapshot keeps H1 INCONCLUSIVE and near-neutral (delta -7.3%, 95% CI [-18.0%, +2.4%]), while H2 remains PASS on rich-vs-sparse separation but with a somewhat weaker gap than the previous refresh; H2 intervention-outcome tracking remains inconclusive and ranking still favors another shock-stability sweep.

Next checkpoints:
1. Continue ranked H2 shock-stability sweeps (0.02/0.03/0.04) until intervention-outcome confidence no longer crosses zero.
2. Tune reward pressure and robustness protocol until variance drops.
3. Keep alternating with matched H1 +8 extensions whenever H1 remains the tighter unresolved uncertainty boundary.

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

## Priority 6: Communication Quality

Why it matters:
- Strong technical progress still fails if outcomes are hard to understand and hard to act on.

Mastery gate:
- Every major implementation closes with a clear done checklist and plain-language outcome summary.
- Significant user-visible progress consistently updates README.
- Every major result includes explicit next-stage brainstorming.

Now:
- Collaboration defaults are hard-coded in workspace instructions and README.

Next checkpoints:
1. Add lightweight response-time guardrails so the 3-rule format is reinforced per prompt.
2. Track communication-checklist pass rate at each roadmap milestone.

## Current Implementation Focus

Current active focus is Priority 1 then Priority 2, with Priority 6 enforced continuously.

Execution rhythm:
1. Improve observability tooling.
2. Run fixed-condition seed batches.
3. Compare and tighten robustness variance.
4. Move forward only when mastery signals are met.