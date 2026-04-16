# Medium Source Review: How to Build an AGI

## Source Metadata

- URL: [bob-k.medium.com/how-to-build-an-agi-26793b9b2a37](https://bob-k.medium.com/how-to-build-an-agi-26793b9b2a37)
- Full text availability: provided in-session by user on 2026-04-16
- Confidence: high for article-derived claims listed below

## High-Value Ideas From The Article

The article contributes three architecture-level ideas that are practical for this repo:

1. Tripartite architecture:

- CSG: Continuous cognitive generation.
- MMIE: Memory consolidation plus metacognitive insight synthesis.
- ECC: Executive controller for regulation, prioritization, and interruption.

1. Emergent metacognition:

- Insight summaries should be generated from prior cognitive traces and fed back into active reasoning.
- Memory should be active and reinterpretive, not passive storage.

1. Materialist constraints and evaluation discipline:

- Focus on functional consciousness properties that are testable.
- Avoid anthropomorphic claims without measurable evidence.
- Use graded capability checks rather than all-or-nothing consciousness claims.

## Translation Into Repo Architecture

This repo now maps the article to concrete components:

1. CSG (generation):

- Implemented as model-driven response drafting in evolved mode.

1. MMIE (memory + insight):

- Sensory memory: short recent user-turn cache.
- Working memory: active goal, intent, entities, and answer preview.
- Episodic memory: compact per-turn event ledger.
- Symbolic memory: exact key/value and token recall path.
- Insight summary: synthesized guidance from recent episodic trajectory.

1. ECC (executive control):

- Enforces response contract (ANSWER / CONTINUITY / CONFIDENCE / UNKNOWNS).
- Routes deterministic recall operations for high-confidence exact-memory tasks.
- Preserves continuity while preventing unconstrained drift.

## What Was Implemented After Full-Text Review

The evolved runtime has been migrated to an open-source framework execution path:

1. Open-source orchestration:

- LangGraph state machine now coordinates CSG -> MMIE -> ECC.

1. Framework-backed live experience:

- Existing side-by-side chat now defaults to the LangGraph runtime.

1. Framework-backed evaluation:

- Benchmark script now defaults to LangGraph runtime while preserving legacy fallback.

1. Existing gate compatibility preserved:

- Output schema and gate checks remain compatible with current pass/fail tooling.

## Remaining Gaps Relative To The Article

1. Contradiction tracking over long horizons is not yet explicit.
2. Confidence calibration is still coarse and mostly format-level.
3. Delayed recall probes need stronger distractor and adversarial patterns.
4. Perception-side qualia-counting experiments (event/spike-like encoding) are not yet integrated.

## Next Stage Plan

1. Add contradiction ledger + auto-repair metrics in eval output.
2. Add confidence-vs-correctness calibration metrics and thresholds.
3. Expand prompt battery with delayed recall, conflict overwrite, and distractor tasks.
4. Add an optional event-based perception toy module for temporal pattern recall experiments.

## Operating Principle

Use this article as architecture guidance.
Use benchmark and gate artifacts in this repo as the acceptance authority for AGI-progress claims.
