# Hypothesis Board

Source: [../../outputs/experiment_observatory.md](../../outputs/experiment_observatory.md)

## Hypothesis Cards (Auto-Evaluated)

These are machine-evaluated research hypotheses with explicit status and next action.

### H1: Curriculum Improves Robustness

- Status: INCONCLUSIVE
- Evidence: Scope=difficulty=1.450 shock=0.020 eval_days=900 max_population=220; n_curr=39, n_base=205; curriculum_mean=32663.424, baseline_mean=36101.130, delta=-9.5% (95% CI [-21.4%, +0.8%]); mean_diff_CI=[-7795.845, 260.355]; effect_d=-0.450.
- Next action: Increase seed count in both groups to reduce variance before finalizing.

### H2: Innovation-Rich Policies Outperform Innovation-Sparse Policies

- Status: PASS
- Evidence: n_rich=133, n_sparse=18; innovation_rich_mean=38277.811, innovation_sparse_mean=7103.826, delta=+438.8% (95% CI [+288.8%, +730.0%]); mean_diff_CI=[28408.489, 33862.314]; effect_d=8.003.
- Next action: Check if innovation gains persist when shock probability is increased.

### H3: Survivorship Correlates With Robustness

- Status: PASS
- Evidence: pearson_corr(mean_alive_end, robustness_mean)=+0.925 (95% CI [0.909, 0.939]) across 360 runs; r_squared=0.856.
- Next action: Use this signal to tune fitness weighting for alive_end vs innovation pressure.

### H4: Campaign Drift Is Productive

- Status: PASS
- Evidence: drift_score=0.016 (stable), robust_delta=1031.912 (95% CI [-780.359, 2996.101]), effect_d=0.134.
- Next action: If inconclusive, add seeds and compare with a fixed no-curriculum ablation group.

## Run Evidence

- [autopilot_live_nocurr_27032](../runs/autopilot_live_nocurr_27032.md)
- [h3_reward_highalive_30005](../runs/h3_reward_highalive_30005.md)
- [autopilot_live_nocurr_27085](../runs/autopilot_live_nocurr_27085.md)
- [h1_match_curr_29034](../runs/h1_match_curr_29034.md)
- [hour_batch_B_nocurr_13131](../runs/hour_batch_B_nocurr_13131.md)

