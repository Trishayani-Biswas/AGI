# Hypothesis Board

Source: [../../outputs/experiment_observatory.md](../../outputs/experiment_observatory.md)

## Hypothesis Cards (Auto-Evaluated)

These are machine-evaluated research hypotheses with explicit status and next action.

### H1: Curriculum Improves Robustness

- Status: FAIL
- Evidence: Scope=difficulty=1.450 shock=0.020 eval_days=900 max_population=220; n_curr=19, n_base=173; curriculum_mean=29392.147, baseline_mean=36289.774, delta=-19.0% (95% CI [-37.4%, -3.2%]); mean_diff_CI=[-13396.859, -1122.392]; effect_d=-0.930.
- Next action: Increase seed count in both groups to reduce variance before finalizing.

### H2: Innovation-Rich Policies Outperform Innovation-Sparse Policies

- Status: PASS
- Evidence: n_rich=97, n_sparse=12; innovation_rich_mean=38282.596, innovation_sparse_mean=5376.605, delta=+612.0% (95% CI [+359.3%, +1291.4%]); mean_diff_CI=[29979.909, 35614.438]; effect_d=8.342.
- Next action: Check if innovation gains persist when shock probability is increased.

### H3: Survivorship Correlates With Robustness

- Status: PASS
- Evidence: pearson_corr(mean_alive_end, robustness_mean)=+0.932 (95% CI [0.914, 0.946]) across 260 runs; r_squared=0.869.
- Next action: Use this signal to tune fitness weighting for alive_end vs innovation pressure.

### H4: Campaign Drift Is Productive

- Status: PASS
- Evidence: drift_score=0.062 (stable), robust_delta=1906.766 (95% CI [-50.579, 4133.873]), effect_d=0.250.
- Next action: If inconclusive, add seeds and compare with a fixed no-curriculum ablation group.

## Run Evidence

- [autopilot_live_nocurr_27032](../runs/autopilot_live_nocurr_27032.md)
- [autopilot_live_nocurr_27085](../runs/autopilot_live_nocurr_27085.md)
- [hour_batch_B_nocurr_13131](../runs/hour_batch_B_nocurr_13131.md)
- [autopilot_20m_dev_curr_28005](../runs/autopilot_20m_dev_curr_28005.md)
- [h1_match_nocurr_29017](../runs/h1_match_nocurr_29017.md)

