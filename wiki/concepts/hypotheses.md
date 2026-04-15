# Hypothesis Board

Source: [../../outputs/experiment_observatory.md](../../outputs/experiment_observatory.md)

## Hypothesis Cards (Auto-Evaluated)

These are machine-evaluated research hypotheses with explicit status and next action.

### H1: Curriculum Improves Robustness

- Status: FAIL
- Evidence: Scope=difficulty=1.450 shock=0.020 eval_days=900 max_population=220; n_curr=23, n_base=183; curriculum_mean=31180.768, baseline_mean=36289.538, delta=-14.1% (95% CI [-30.1%, -0.1%]); mean_diff_CI=[-10705.011, 111.159]; effect_d=-0.693.
- Next action: Increase seed count in both groups to reduce variance before finalizing.

### H2: Innovation-Rich Policies Outperform Innovation-Sparse Policies

- Status: PASS
- Evidence: n_rich=101, n_sparse=12; innovation_rich_mean=38330.531, innovation_sparse_mean=5376.605, delta=+612.9% (95% CI [+367.3%, +1235.7%]); mean_diff_CI=[29946.520, 35518.625]; effect_d=8.492.
- Next action: Check if innovation gains persist when shock probability is increased.

### H3: Survivorship Correlates With Robustness

- Status: PASS
- Evidence: pearson_corr(mean_alive_end, robustness_mean)=+0.929 (95% CI [0.911, 0.944]) across 274 runs; r_squared=0.864.
- Next action: Use this signal to tune fitness weighting for alive_end vs innovation pressure.

### H4: Campaign Drift Is Productive

- Status: PASS
- Evidence: drift_score=0.068 (stable), robust_delta=2272.774 (95% CI [243.700, 4528.952]), effect_d=0.305.
- Next action: If inconclusive, add seeds and compare with a fixed no-curriculum ablation group.

## Run Evidence

- [autopilot_live_nocurr_27032](../runs/autopilot_live_nocurr_27032.md)
- [h3_reward_highalive_30005](../runs/h3_reward_highalive_30005.md)
- [autopilot_live_nocurr_27085](../runs/autopilot_live_nocurr_27085.md)
- [hour_batch_B_nocurr_13131](../runs/hour_batch_B_nocurr_13131.md)
- [autopilot_20m_dev_curr_28005](../runs/autopilot_20m_dev_curr_28005.md)

