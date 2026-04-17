# Independent Thinking Scientific Plan

## Objective

Raise this project from continuity-aware response generation to robust independent reasoning that resists anchoring, survives paraphrase shifts, and self-corrects under critique.

## Working Definition

In this repo, independent thinking means all four are true:

- correct on base prompts
- stable under paraphrase
- resistant to misleading anchors/interventions
- able to revise draft reasoning when critique detects disagreement

## Falsifiable Success Criteria

Primary criteria (must all pass):

- random reasoning gate passes with current strict thresholds in `configs/random_reasoning_gate.json`
- pass rate >= 0.70 across at least 5 seeds on the same candidate profile
- intervention delta vs base >= -0.02 mean across seeds
- consistency rate >= 0.75 mean across seeds
- pattern risk index <= 0.35 mean across seeds

Secondary criteria (quality controls):

- confidence-overconfidence gap <= 0.05
- no internal state JSON leakage in evolved responses
- audit telemetry shows non-zero disagreements and non-zero revisions on adversarial sets

## Experimental Program

### Phase 1: Runtime Integrity (now)

Goal: make the runtime capable of self-critique and safe correction.

Interventions:

- CSG -> AUDIT -> MMIE -> ECC reasoning flow in `scripts/tripartite_langgraph_runtime.py`
- optional critic model (`--critic-model`) for audit pass
- anti-anchor replacement logic on high-confidence disagreement
- deterministic symbolic-memory reflex for exact memory operations
- internal state leak guard and repair draft attempt
- audit telemetry in state (`independence_stats`)

Exit criteria:

- AGI experience smoke run completes reliably
- evolved structured rate = 1.0 in smoke
- no state-dump artifacts in smoke turns

### Phase 2: Adversarial Robustness Tuning

Goal: increase intervention and paraphrase robustness without regression.

Interventions:

- tune decoding profiles per model (`temperature`, `top_p`, `max_tokens`)
- run short multi-seed sweeps (3-5 seeds)
- keep one variable family per sweep (no mixed changes)
- reject candidates that raise anchor vulnerability or pattern risk

Exit criteria:

- candidate beats baseline deltas in all delta checks
- intervention accuracy and consistency both improve vs baseline by >= +0.10

### Phase 3: Self-Revision Quality

Goal: ensure audit revisions are productive, not noise.

Interventions:

- log audit disagreement/revision rates and correlate with correctness
- add ablation comparisons:
  - audit enabled vs audit disabled
  - same proposer model, same seed set
- tune replacement threshold and critic decoding profile

Exit criteria:

- revision precision >= 0.60 (revisions that improve correctness)
- net gain from audit-enabled mode >= +0.08 accuracy vs no-audit on adversarial subset

### Phase 4: Promotion Readiness

Goal: establish reproducible evidence for independent reasoning claims.

Interventions:

- run full benchmark with fixed config and 5+ seeds
- compute mean and confidence intervals for key metrics
- require gate pass-rate >= 0.70 before any promotion claim

Exit criteria:

- promotion decision artifact indicates pass under strict gate on majority seeds
- all failure modes documented with next corrective experiment

## Required Artifacts Per Iteration

- benchmark summary and report under `outputs/random_reasoning_benchmark/<run_tag>/`
- gate report for each run
- multi-seed aggregate markdown summary
- short decision log: keep / reject / tune-next with one-sentence reason

## Recommended Command Sequence

1. run candidate benchmark
2. run gate against candidate
3. run gate against baseline deltas
4. run multi-seed summary sweep
5. decide keep vs reject

## Risk Notes

- very small models can pass memory smoke but fail adversarial reasoning gates
- deterministic memory reflex improves recall but does not imply general independent reasoning
- confidence numbers are only useful when calibrated against correctness

## Current Status Snapshot (2026-04-17)

- runtime now includes audit pass and independence telemetry
- symbolic-memory smoke behavior is stable in latest qwen0.5b run
- strict AGI gate still fails on smoke because full tier checks (sensory/working/long-term) need larger prompt battery
- independent-thinking claim is not yet justified until random reasoning multi-seed gate passes
