# Hypothesis Board

Source: [../../outputs/experiment_observatory.md](../../outputs/experiment_observatory.md)

## Hypothesis Cards (Auto-Evaluated)

These are machine-evaluated research hypotheses with explicit status and next action.

### H1: Curriculum Improves Robustness

- Status: FAIL
- Evidence: Scope=difficulty=1.450 shock=0.020 eval_days=900 max_population=220; n_curr=27, n_base=187; curriculum_mean=32446.047, baseline_mean=36262.692, delta=-10.5% (95% CI [-24.8%, +1.3%]); mean_diff_CI=[-9092.782, 492.116]; effect_d=-0.520.
- Next action: Increase seed count in both groups to reduce variance before finalizing.

### H2: Innovation-Rich Policies Outperform Innovation-Sparse Policies

- Status: PASS
- Evidence: n_rich=105, n_sparse=12; innovation_rich_mean=38367.335, innovation_sparse_mean=5376.605, delta=+613.6% (95% CI [+354.6%, +1231.1%]); mean_diff_CI=[29545.573, 35771.053]; effect_d=8.607.
- Next action: Check if innovation gains persist when shock probability is increased.

### H3: Survivorship Correlates With Robustness

- Status: PASS
- Evidence: pearson_corr(mean_alive_end, robustness_mean)=+0.930 (95% CI [0.912, 0.944]) across 282 runs; r_squared=0.864.
- Next action: Use this signal to tune fitness weighting for alive_end vs innovation pressure.

### H4: Campaign Drift Is Productive

- Status: PASS
- Evidence: drift_score=0.065 (stable), robust_delta=2614.917 (95% CI [802.951, 4684.213]), effect_d=0.356.
- Next action: If inconclusive, add seeds and compare with a fixed no-curriculum ablation group.

## Run Evidence

- [autopilot_live_nocurr_27032](../runs/autopilot_live_nocurr_27032.md)
- [h3_reward_highalive_30005](../runs/h3_reward_highalive_30005.md)
- [autopilot_live_nocurr_27085](../runs/autopilot_live_nocurr_27085.md)
- [h1_match_curr_29034](../runs/h1_match_curr_29034.md)
- [hour_batch_B_nocurr_13131](../runs/hour_batch_B_nocurr_13131.md)

