# Hypothesis Board

Source: [../../outputs/experiment_observatory.md](../../outputs/experiment_observatory.md)

## Hypothesis Cards (Auto-Evaluated)

These are machine-evaluated research hypotheses with explicit status and next action.

### H1: Curriculum Improves Robustness

- Status: INCONCLUSIVE
- Evidence: Scope=difficulty=1.450 shock=0.020 eval_days=900 max_population=220; n_curr=39, n_base=211; curriculum_mean=32663.424, baseline_mean=35987.137, delta=-9.2% (95% CI [-21.5%, +1.3%]); mean_diff_CI=[-7786.135, 172.941]; effect_d=-0.431.
- Next action: Increase seed count in both groups to reduce variance before finalizing.

### H2: Innovation-Rich Policies Outperform Innovation-Sparse Policies

- Status: PASS
- Evidence: n_rich=139, n_sparse=19; innovation_rich_mean=38308.652, innovation_sparse_mean=7366.796, delta=+420.0% (95% CI [+270.6%, +700.2%]); mean_diff_CI=[28276.493, 33381.899]; effect_d=7.979.
- Next action: Check if innovation gains persist when shock probability is increased.

### H3: Survivorship Correlates With Robustness

- Status: PASS
- Evidence: pearson_corr(mean_alive_end, robustness_mean)=+0.927 (95% CI [0.911, 0.940]) across 378 runs; r_squared=0.859.
- Next action: Use this signal to tune fitness weighting for alive_end vs innovation pressure.

### H4: Campaign Drift Is Productive

- Status: PASS
- Evidence: drift_score=0.016 (stable), robust_delta=830.372 (95% CI [-1027.124, 2929.046]), effect_d=0.106.
- Next action: If inconclusive, add seeds and compare with a fixed no-curriculum ablation group.

## Run Evidence

- [autopilot_live_nocurr_27032](../runs/autopilot_live_nocurr_27032.md)
- [h3_reward_highalive_30005](../runs/h3_reward_highalive_30005.md)
- [h2_shock_0.020_29098](../runs/h2_shock_0.020_29098.md)
- [autopilot_live_nocurr_27085](../runs/autopilot_live_nocurr_27085.md)
- [h1_match_curr_29034](../runs/h1_match_curr_29034.md)

