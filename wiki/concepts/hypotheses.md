# Hypothesis Board

Source: [../../outputs/experiment_observatory.md](../../outputs/experiment_observatory.md)

## Hypothesis Cards (Auto-Evaluated)

These are machine-evaluated research hypotheses with explicit status and next action.

### H1: Curriculum Improves Robustness

- Status: INCONCLUSIVE
- Evidence: Scope=difficulty=1.450 shock=0.020 eval_days=900 max_population=220; n_curr=43, n_base=227; curriculum_mean=33137.510, baseline_mean=35758.496, delta=-7.3% (95% CI [-18.0%, +2.4%]); mean_diff_CI=[-6685.505, 668.310]; effect_d=-0.335.
- Next action: Increase seed count in both groups to reduce variance before finalizing.

### H2: Innovation-Rich Policies Outperform Innovation-Sparse Policies

- Status: PASS
- Evidence: n_rich=153, n_sparse=20; innovation_rich_mean=38026.101, innovation_sparse_mean=8173.593, delta=+365.2% (95% CI [+243.1%, +604.8%]); mean_diff_CI=[26896.527, 32633.301]; effect_d=6.402.
- Next action: Check if innovation gains persist when shock probability is increased.

### H3: Survivorship Correlates With Robustness

- Status: PASS
- Evidence: pearson_corr(mean_alive_end, robustness_mean)=+0.920 (95% CI [0.904, 0.933]) across 422 runs; r_squared=0.846.
- Next action: Use this signal to tune fitness weighting for alive_end vs innovation pressure.

### H4: Campaign Drift Is Productive

- Status: PASS
- Evidence: drift_score=0.030 (stable), robust_delta=182.989 (95% CI [-1803.938, 2022.686]), effect_d=0.023.
- Next action: If inconclusive, add seeds and compare with a fixed no-curriculum ablation group.

## Run Evidence

- [autopilot_live_nocurr_27032](../runs/autopilot_live_nocurr_27032.md)
- [h3_reward_highalive_30005](../runs/h3_reward_highalive_30005.md)
- [h2_shock_0.020_29098](../runs/h2_shock_0.020_29098.md)
- [autopilot_live_nocurr_27085](../runs/autopilot_live_nocurr_27085.md)
- [h2_shock_0.020_29110](../runs/h2_shock_0.020_29110.md)

