# OpenClaw-Level Local Evolution: 6-Month Execution Plan

## North-Star Outcome

By the end of Month 6, this project should provide a local-first evolutionary environment where:

- each Wild run can produce unique emergent outcomes across devices and sessions
- each Lab run can be replayed deterministically for debugging and scientific comparison
- observability explains what changed, why it changed, and where divergence emerged
- the same codebase runs on commodity local hardware with fidelity tiers

## Program Constraints

- Local-first: no cloud dependency required for core simulation/evaluation.
- Scientific traceability: every claim must map to run artifacts and gate outputs.
- Two operating modes:
  - Wild mode: entropy-rich, uniqueness-forward.
  - Lab mode: deterministic replay from run manifest and RNG streams.
- Device safety/privacy: no raw hardware identifiers in stored artifacts.

## Success Metrics (Program-Level)

Track these monthly and at release-candidate checkpoints:

- diversity retention index over long horizons
- speciation count and persistence
- lineage distance across independent runs
- cross-device divergence score (Wild mode)
- replay fidelity score (Lab mode)
- extinction-recovery frequency
- simulation throughput by fidelity tier (low/medium/high)
- observability completeness score

## Architecture Building Blocks

### 1) Entropy And Replay Subsystem

- Deterministic RNG stream partitioning (world, mutation, interaction, disasters).
- Wild entropy mixer using secure random seed + salted device fingerprint hash + runtime jitter.
- Lab replay token capturing full RNG stream seeds and environmental schedule.

### 2) Ecology And Evolution Subsystem

- Multi-biome world generation with constrained resource gradients.
- Speciation model with genetic distance and reproductive isolation.
- Co-evolution loop with non-trivial ecological pressures.

### 3) Observatory And Evidence Subsystem

- Unified run manifest schema.
- Event lineage graph + mutation maps + adaptation timeline.
- Hypothesis cards with CI/effect-size and pass/fail criteria.

### 4) Local Performance Subsystem

- Fidelity profiles and hardware-aware defaults.
- Hot-loop optimization and batched simulation updates.
- Multi-device campaign orchestration via artifact exchange.

### 5) Model And Tool Expansion Subsystem

- Maintain an evolving local-model portfolio for proposer/critic/evaluator roles.
- Use external model baselines selectively to detect local blind spots.
- Incorporate external open-source modules when they accelerate measurable milestones.

## Month-By-Month Roadmap

## Month 1: Entropy Foundation + Telemetry Contracts

### Month 1 Primary Deliverables

- Implement Run Manifest v1 schema.
- Implement Wild/Lab mode seed plumbing.
- Add RNG stream isolation for major stochastic subsystems.
- Standardize event telemetry schema in simulation outputs.

### Month 1 Acceptance Criteria

- 100 Wild runs show measurable non-trivial divergence in top-level outcomes.
- Same Lab token reproduces key trajectory summaries within tolerance.
- Every run emits manifest + summary + telemetry index.

### Month 1 Week Plan

1. Week 1: Manifest schema, entropy policy, replay contract.
2. Week 2: RNG partition integration and validation tests.
3. Week 3: Wild/Lab mode CLI and output wiring.
4. Week 4: Diversity baseline report + regression guardrails.

## Month 2: Rich Ecology And Adaptive Niches

### Month 2 Primary Deliverables

- Multi-biome terrain/resource generation.
- Seasonal regime and shock scheduler.
- Trait-environment fitness coupling (metabolism, mobility, risk).

### Month 2 Acceptance Criteria

- At least three ecologically distinct survival strategies persist in medium runs.
- Migration and local adaptation patterns appear in observatory output.
- Biome shifts produce measurable trait distribution drift.

### Month 2 Week Plan

1. Week 1: Biome generator + resource gradient tests.
2. Week 2: Seasonal and shock schedule implementation.
3. Week 3: Trait-fitness coupling and pressure calibration.
4. Week 4: Strategy diversity evaluation and observatory upgrade.

## Month 3: Speciation And Open-Ended Evolution Pressure

### Month 3 Primary Deliverables

- Genetic distance/speciation thresholds.
- Reproductive isolation mechanics.
- Diversity-preserving anti-collapse pressure.

### Month 3 Acceptance Criteria

- Observable speciation events in long campaigns.
- No dominant early-collapse mode in majority of test runs.
- Lineage divergence metrics remain above minimum diversity floor.

### Month 3 Week Plan

1. Week 1: Speciation distance metric and lineage tagging.
2. Week 2: Isolation/recombination rule implementation.
3. Week 3: Anti-collapse mechanics and ablation tests.
4. Week 4: Speciation observability views and gate thresholds.

## Month 4: Co-Evolution And Strategic Arms Races

### Month 4 Primary Deliverables

- Predator-prey and competitive interaction layers.
- Cooperation/defection social dynamics.
- Counter-adaptation tracking (arms-race telemetry).

### Month 4 Acceptance Criteria

- Multiple co-evolution cycles observed in long runs.
- Strategy dominance rotates under changing pressures.
- Social traits show context-dependent utility.

### Month 4 Week Plan

1. Week 1: Interaction model extensions.
2. Week 2: Social dynamic payoffs and reproduction effects.
3. Week 3: Arms-race telemetry and cycle detection logic.
4. Week 4: Campaign evaluation and tuning pass.

## Month 5: Local Device Scale And Campaign Federation

### Month 5 Primary Deliverables

- Low/Medium/High fidelity profiles.
- Throughput optimization for commodity CPUs and optional GPU paths.
- Multi-device campaign runner and artifact aggregator.

### Month 5 Acceptance Criteria

- Stable local execution on laptop-class hardware in low/medium profiles.
- Cross-device Wild campaigns produce statistically significant divergence.
- Aggregator renders device-level diversity and convergence snapshots.

### Month 5 Week Plan

1. Week 1: Fidelity profile implementation.
2. Week 2: Performance optimization and benchmark harness.
3. Week 3: Multi-device orchestration + artifact merge.
4. Week 4: Cross-device analysis dashboard and failure hardening.

## Month 6: Validation, Observatory Maturity, Release Candidate

### Month 6 Primary Deliverables

- Full observatory v2 with lineage playback and ecological overlays.
- Validation suite (diversity, speciation, replay, performance, resilience).
- Public benchmark scenarios and release packaging.

### Month 6 Acceptance Criteria

- New contributor can run and observe end-to-end locally with clear outputs.
- Validation suite passes on representative low/medium hardware.
- Wild runs remain distinct while Lab replay stays deterministic.

### Month 6 Week Plan

1. Week 1: Observatory v2 polish and trace completeness.
2. Week 2: Validation suite finalization and CI checks.
3. Week 3: Benchmark packs and release docs.
4. Week 4: RC freeze, burn-in campaign, and launch decision.

## Required Run Modes

## Wild Mode (Uniqueness Priority)

- Entropy sources mixed per run and per device.
- No forced deterministic replay.
- Used for emergent behavior discovery and diversity studies.

## Lab Mode (Reproducibility Priority)

- Full RNG seeds and schedules pinned by manifest token.
- Same initial state and settings produce replayable outcomes.
- Used for debugging, regression analysis, and scientific comparisons.

## Promotion Gate Policy (For Major Stage Advances)

A stage is promoted only if all checks pass:

- diversity floor met over N-run campaign
- speciation persistence above threshold
- replay fidelity in Lab mode within tolerance
- cross-device divergence non-trivial in Wild mode
- observability completeness and artifact integrity pass
- performance targets met for declared fidelity tiers
- capability-expansion decisions are documented with observed benefit or rollback plan

## Artifact Contract

Each campaign must produce:

- run manifest(s)
- summary JSON and markdown report
- gate report with explicit pass/fail checks
- observatory digest with lineage and adaptation interpretation
- comparison artifacts for baseline-vs-candidate stage deltas

## Risks And Mitigations

- Risk: chaos overwhelms signal.
  - Mitigation: isolate RNG streams, add bounded perturbation policies, enforce Lab-mode checks.
- Risk: premature convergence.
  - Mitigation: novelty pressure, dynamic ecology, periodic regime shifts.
- Risk: low-end hardware bottlenecks.
  - Mitigation: fidelity tiers, batched stepping, optional accelerators.
- Risk: unexplainable outcomes.
  - Mitigation: observability-first requirement and manifest completeness gate.

## First 10-Day Sprint (Immediate)

1. Finalize Run Manifest v1 schema and mode flags.
2. Implement Wild/Lab entropy plumbing with RNG stream partitioning.
3. Add diversity baseline metrics and first observatory panel.
4. Execute 50 Wild runs and 10 Lab replay tests.
5. Set Month-1 promotion thresholds from measured baseline.

## Direction-Lock Rule

Before proposing or executing major work, the agent must reconcile planned actions with this file and explicitly state which month/week deliverables the work advances.
