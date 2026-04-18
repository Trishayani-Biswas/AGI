# Hypothesis Board

Source: [../../outputs/experiment_observatory.md](../../outputs/experiment_observatory.md)

## Hypothesis Cards (Auto-Evaluated)

These are machine-evaluated research hypotheses with explicit status and next action.

### H1: Curriculum Improves Robustness

- Status: FAIL
- Evidence: Scope=difficulty=1.450 shock=0.020 eval_days=900 max_population=220; n_curr=23, n_base=93; curriculum_mean=31180.768, baseline_mean=36027.353, delta=-13.5% (95% CI [-29.0%, +0.6%]); mean_diff_CI=[-10672.729, 339.959]; effect_d=-0.563.
- Next action: Increase seed count in both groups to reduce variance before finalizing.

### H2: Innovation-Rich Policies Outperform Innovation-Sparse Policies

- Status: PASS
- Evidence: n_rich=72, n_sparse=10; innovation_rich_mean=38566.368, innovation_sparse_mean=3366.982, delta=+1045.4% (95% CI [+672.6%, +1883.4%]); mean_diff_CI=[33538.269, 36874.289]; effect_d=9.902.
- Next action: Check if innovation gains persist when shock probability is increased.

### H3: Survivorship Correlates With Robustness

- Status: PASS
- Evidence: pearson_corr(mean_alive_end, robustness_mean)=+0.929 (95% CI [0.906, 0.946]) across 185 runs; r_squared=0.863.
- Next action: Use this signal to tune fitness weighting for alive_end vs innovation pressure.

### H4: Campaign Drift Is Productive

- Status: PASS
- Evidence: drift_score=0.052 (stable), robust_delta=948.722 (95% CI [-2372.946, 3978.550]), effect_d=0.108.
- Next action: If inconclusive, add seeds and compare with a fixed no-curriculum ablation group.

## Run Evidence

- [autopilot_live_nocurr_27032](../runs/autopilot_live_nocurr_27032.md)
- [h3_reward_highalive_30005](../runs/h3_reward_highalive_30005.md)
- [hour_batch_B_nocurr_13131](../runs/hour_batch_B_nocurr_13131.md)
- [autopilot_20m_dev_curr_28005](../runs/autopilot_20m_dev_curr_28005.md)
- [h1_match_nocurr_29017](../runs/h1_match_nocurr_29017.md)

