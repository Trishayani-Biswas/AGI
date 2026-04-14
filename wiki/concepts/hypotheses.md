# Hypothesis Board

Source: [../../outputs/experiment_observatory.md](../../outputs/experiment_observatory.md)

## Hypothesis Cards (Auto-Evaluated)

These are machine-evaluated research hypotheses with explicit status and next action.

### H1: Curriculum Improves Robustness

- Status: FAIL
- Evidence: Scope=difficulty=1.450 shock=0.020 eval_days=900 max_population=220; curriculum_mean=27445.762, baseline_mean=36111.226, delta=-24.0%.
- Next action: Increase seed count in both groups to reduce variance before finalizing.

### H2: Innovation-Rich Policies Outperform Innovation-Sparse Policies

- Status: PASS
- Evidence: innovation_rich_mean=38189.965, innovation_sparse_mean=5224.306, delta=+631.0%.
- Next action: Check if innovation gains persist when shock probability is increased.

### H3: Survivorship Correlates With Robustness

- Status: PASS
- Evidence: pearson_corr(mean_alive_end, robustness_mean)=+0.933 across 173 runs.
- Next action: Use this signal to tune fitness weighting for alive_end vs innovation pressure.

### H4: Campaign Drift Is Productive

- Status: PASS
- Evidence: drift_score=0.087 (stable), robust_delta=2364.503.
- Next action: If inconclusive, add seeds and compare with a fixed no-curriculum ablation group.

## Run Evidence

- [autopilot_live_nocurr_27032](../runs/autopilot_live_nocurr_27032.md)
- [autopilot_live_nocurr_27085](../runs/autopilot_live_nocurr_27085.md)
- [hour_batch_B_nocurr_13131](../runs/hour_batch_B_nocurr_13131.md)
- [autopilot_live_nocurr_27068](../runs/autopilot_live_nocurr_27068.md)
- [autopilot_live_nocurr_27029](../runs/autopilot_live_nocurr_27029.md)

