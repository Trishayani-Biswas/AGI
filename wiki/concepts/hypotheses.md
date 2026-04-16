# Hypothesis Board

Source: [../../outputs/experiment_observatory.md](../../outputs/experiment_observatory.md)

## Hypothesis Cards (Auto-Evaluated)

These are machine-evaluated research hypotheses with explicit status and next action.

### H1: Curriculum Improves Robustness

- Status: INCONCLUSIVE
- Evidence: Scope=difficulty=1.450 shock=0.020 eval_days=900 max_population=220; n_curr=43, n_base=233; curriculum_mean=33137.510, baseline_mean=35743.780, delta=-7.3% (95% CI [-17.9%, +2.5%]); mean_diff_CI=[-6599.320, 693.085]; effect_d=-0.335.
- Next action: Increase seed count in both groups to reduce variance before finalizing.

### H2: Innovation-Rich Policies Outperform Innovation-Sparse Policies

- Status: PASS
- Evidence: n_rich=162, n_sparse=21; innovation_rich_mean=38002.841, innovation_sparse_mean=8332.433, delta=+356.1% (95% CI [+236.7%, +578.6%]); mean_diff_CI=[26704.904, 32329.597]; effect_d=6.485.
- Next action: Check if innovation gains persist when shock probability is increased.

### H3: Survivorship Correlates With Robustness

- Status: PASS
- Evidence: pearson_corr(mean_alive_end, robustness_mean)=+0.916 (95% CI [0.899, 0.930]) across 440 runs; r_squared=0.839.
- Next action: Use this signal to tune fitness weighting for alive_end vs innovation pressure.

### H4: Campaign Drift Is Productive

- Status: PASS
- Evidence: drift_score=0.036 (stable), robust_delta=69.343 (95% CI [-1794.811, 1795.617]), effect_d=0.009.
- Next action: If inconclusive, add seeds and compare with a fixed no-curriculum ablation group.

## Run Evidence

- [autopilot_live_nocurr_27032](../runs/autopilot_live_nocurr_27032.md)
- [h3_reward_highalive_30005](../runs/h3_reward_highalive_30005.md)
- [h2_shock_0.020_29098](../runs/h2_shock_0.020_29098.md)
- [autopilot_live_nocurr_27085](../runs/autopilot_live_nocurr_27085.md)
- [h2_shock_0.020_29110](../runs/h2_shock_0.020_29110.md)

