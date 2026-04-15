# Hypothesis Board

Source: [../../outputs/experiment_observatory.md](../../outputs/experiment_observatory.md)

## Hypothesis Cards (Auto-Evaluated)

These are machine-evaluated research hypotheses with explicit status and next action.

### H1: Curriculum Improves Robustness

- Status: FAIL
- Evidence: Scope=difficulty=1.450 shock=0.020 eval_days=900 max_population=220; n_curr=27, n_base=193; curriculum_mean=32446.047, baseline_mean=36192.028, delta=-10.4% (95% CI [-23.6%, +2.1%]); mean_diff_CI=[-8762.419, 439.803]; effect_d=-0.511.
- Next action: Increase seed count in both groups to reduce variance before finalizing.

### H2: Innovation-Rich Policies Outperform Innovation-Sparse Policies

- Status: PASS
- Evidence: n_rich=113, n_sparse=14; innovation_rich_mean=38447.836, innovation_sparse_mean=6281.159, delta=+512.1% (95% CI [+323.4%, +956.6%]); mean_diff_CI=[28928.159, 34854.305]; effect_d=8.459.
- Next action: Check if innovation gains persist when shock probability is increased.

### H3: Survivorship Correlates With Robustness

- Status: PASS
- Evidence: pearson_corr(mean_alive_end, robustness_mean)=+0.934 (95% CI [0.918, 0.946]) across 318 runs; r_squared=0.872.
- Next action: Use this signal to tune fitness weighting for alive_end vs innovation pressure.

### H4: Campaign Drift Is Productive

- Status: PASS
- Evidence: drift_score=0.055 (stable), robust_delta=2281.128 (95% CI [314.370, 4146.194]), effect_d=0.311.
- Next action: If inconclusive, add seeds and compare with a fixed no-curriculum ablation group.

## Run Evidence

- [autopilot_live_nocurr_27032](../runs/autopilot_live_nocurr_27032.md)
- [h3_reward_highalive_30005](../runs/h3_reward_highalive_30005.md)
- [autopilot_live_nocurr_27085](../runs/autopilot_live_nocurr_27085.md)
- [h1_match_curr_29034](../runs/h1_match_curr_29034.md)
- [hour_batch_B_nocurr_13131](../runs/hour_batch_B_nocurr_13131.md)

