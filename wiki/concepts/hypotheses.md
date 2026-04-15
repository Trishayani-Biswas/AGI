# Hypothesis Board

Source: [../../outputs/experiment_observatory.md](../../outputs/experiment_observatory.md)

## Hypothesis Cards (Auto-Evaluated)

These are machine-evaluated research hypotheses with explicit status and next action.

### H1: Curriculum Improves Robustness

- Status: INCONCLUSIVE
- Evidence: Scope=difficulty=1.450 shock=0.020 eval_days=900 max_population=220; n_curr=43, n_base=221; curriculum_mean=33137.510, baseline_mean=35894.975, delta=-7.7% (95% CI [-18.6%, +2.2%]); mean_diff_CI=[-6862.594, 635.936]; effect_d=-0.357.
- Next action: Increase seed count in both groups to reduce variance before finalizing.

### H2: Innovation-Rich Policies Outperform Innovation-Sparse Policies

- Status: PASS
- Evidence: n_rich=149, n_sparse=19; innovation_rich_mean=38284.017, innovation_sparse_mean=7366.796, delta=+419.7% (95% CI [+284.2%, +696.7%]); mean_diff_CI=[28164.407, 33557.320]; effect_d=8.022.
- Next action: Check if innovation gains persist when shock probability is increased.

### H3: Survivorship Correlates With Robustness

- Status: PASS
- Evidence: pearson_corr(mean_alive_end, robustness_mean)=+0.926 (95% CI [0.911, 0.939]) across 404 runs; r_squared=0.857.
- Next action: Use this signal to tune fitness weighting for alive_end vs innovation pressure.

### H4: Campaign Drift Is Productive

- Status: PASS
- Evidence: drift_score=0.015 (stable), robust_delta=474.457 (95% CI [-1319.113, 2358.514]), effect_d=0.061.
- Next action: If inconclusive, add seeds and compare with a fixed no-curriculum ablation group.

## Run Evidence

- [autopilot_live_nocurr_27032](../runs/autopilot_live_nocurr_27032.md)
- [h3_reward_highalive_30005](../runs/h3_reward_highalive_30005.md)
- [h2_shock_0.020_29098](../runs/h2_shock_0.020_29098.md)
- [autopilot_live_nocurr_27085](../runs/autopilot_live_nocurr_27085.md)
- [h2_shock_0.020_29110](../runs/h2_shock_0.020_29110.md)

