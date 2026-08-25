# M13.5 Calibration vs Official Frozen Config

Read-only comparison. No reruns.

## Scale and config

| Parameter | M13.5 calibration | Official frozen |
|-----------|-------------------|-----------------|
| Seeds | 1–5 | 1–20 |
| Profiles | 6 | 6 |
| Opportunities | **40** | **500** |
| Customers | **25** | **100** |
| Horizon (days) | 21 | 21 |
| Cycle length (min) | 15 | 15 |
| ε (paise) | **0** (draft pack default) | **100** (sealed pack) |
| PolicyPack | **`pol_m1_draft` DRAFT** | **`pol_m13_official_v1` SEALED** |
| PolicyPack hash | `3618931e…` | `4b31e760…` |
| B1 schedule version | `adr-013_draft_v1` | `adr-013_v1` |
| Predictor | `strat_m7_dev` | `strat_m7_benchmark_v1` |
| Approver | `simulated_v1_provisional` (docs) | `simulated_v1` (frozen) |
| Config hash | (calibration generator) | `62438f185d9ffd95…` |

## Runner path — critical difference

| Aspect | M13.5 calibration | Official benchmark |
|--------|-------------------|-------------------|
| Entry | `run_baseline_separation()` | `run_policy_on_world()` |
| Baseline code | `run_baseline_cycle()` **only** | `run_baseline_cycle_full()` |
| Measures | Mid-cycle snapshot `selected_count` | End-to-end metrics via M10→M11→M12 |
| REVIVE | Not in baseline separation | Full `run_revive_cycle()` M4–M12 |
| Execution | **Never invoked** | Invoked but produces zero |
| Sentinel bridge | **Not tested** | **Tested — fails for baselines** |
| Simulated approver | **Not tested** | **Not wired — fails for REVIVE** |

## B1 selected count — seed=1 BALANCED

| Source | selected_count | Reaches execution? |
|--------|---------------:|--------------------|
| M13.5 calibration snapshot | **16** | Not measured |
| Official mid-cycle decision layer | **134** | **No** (0 sentinel ID overlap) |
| Official cell artifact | **0** `intervention_count` | **No** |

M13.5 and official are **not comparable on outcome metrics** — calibration never ran the official execution glue.

## Opportunity ID namespace

Measured at M13.5 calibration scale (seed=1 BALANCED):

| Set | Count | Example ID |
|-----|------:|------------|
| World observable `opportunity_id` | 40 | `opp_01JFYQCR6T0T5QX116FBFVBM08` |
| Sentinel `detect()` `opportunity_id` | 31 | `opp_0EAW2ZCMAQ2PE1DAQGW0EQ80WK` |
| **ID overlap** | **0** | Different namespaces |

B1 selected 16 decisions — **0** had `opportunity_id` present in sentinel set.

Same property at official scale: 500 world opps, 341 sentinel opps mid-cycle, **0 ID overlap**, 134 B1 selections all unmatched.

## Action mix (M13.5 only)

M13.5 documented B1/B2/B3 mid-cycle mixes (calibration scale, draft pack):

| Policy | selected | action_mix (sample) |
|--------|----------|---------------------|
| B1 | 16 | A01×6, A05×6, A09×3, A08×1 |
| B2 | 37 | A01×17, A05×11, … |
| B3 | 36 | A03×2, A06×22, A02×12 |

Official benchmark never records action mix at execution layer because **zero actions reach M11**.

## Cycle count

| Config | Cycles |
|--------|-------:|
| M13.5 / official horizon 21d, 15min | **2016** |

Same cycle cadence; official runs all 2016 per policy.

## Interpretation

M13.5 **correctly** showed baseline *decision-layer* separation.

Official benchmark **never validated** that decision-layer selections connect to sentinel IDs, authorization, or simulated approval.

The zero-execution official result is consistent with **pipeline integration gaps**, not with M13.5 decision logic being wrong at calibration scale.
