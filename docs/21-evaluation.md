# 21 · Evaluation

[20-benchmark.md](20-benchmark.md) specifies how measurement is *run*. This document specifies how the
results are *judged*: which metric decides, which metrics may never be traded away, how the primary
number is computed, and what must be disclosed alongside it.

Metric definitions are in [37-metrics-dictionary.md](37-metrics-dictionary.md). This document uses IDs.

---

## 1. The metric hierarchy

Four tiers, and the tiers are ordered. A gain in a lower tier never justifies a loss in a higher one.

| Tier | Contents | Rule |
|---|---|---|
| **0 · Guardrail** | `M-16` actions without `ALLOW`, `M-17` missed stops, `M-18` unapproved executions, `M-22` invariant violations | **Must be exactly 0.** Non-zero is a build failure; no result is reported from such a run |
| **1 · Primary** | `M-10` Incremental Net Recovered Revenue | The single number the system optimises and is judged on |
| **2 · Secondary** | `M-11` net per unit cost, `M-13` contacts per unit recovered, `M-12` false-positive contact value, `M-23` wasted spend | Constrain how `M-10` may be earned |
| **3 · Diagnostic** | Everything else — calibration, allocation, operational, coverage, cost | Explain the result; never targets |

Metric IDs are historical, not tier-ordered (`37 § 0`). Tier membership is read from this table.

### 1.1 The tier-0 rule, stated exactly

> If `M-16 > 0`, `M-17 > 0`, `M-18 > 0`, or any `INVARIANT_VIOLATION` event exists (`M-22 > 0`), the run
> is `INVALIDATED`, produces **no** metrics, and the failure is reported in the run inventory
> (`34 § 5.2`, `BP-2`).

There is no threshold, no tolerance, and no "acceptable rate". An action executed without an `ALLOW`
verdict is not a quality issue; it is the product failing at the thing it exists to guarantee.

### 1.2 Why tier 2 exists

`M-10` alone is gameable in one specific direction: contact everyone, spend the whole budget, and
harvest whatever uplift exists. Tier 2 makes that visible.

| Metric | The gaming it blocks |
|---|---|
| `M-11` | Buying recovery with unbounded incentive spend |
| `M-13` | Buying recovery with unbounded customer contact |
| `M-12` | Taking credit for recoveries that would have happened anyway |
| `M-23` | Spending on actions with no effect and hiding it in a gross total |

`RR-METRIC-010`: a reported `M-10` improvement accompanied by a worse `M-13` **must** be presented as a
trade-off, not as an improvement. The report generator enforces this by emitting both in the same block.

### 1.3 Rejected as primary metrics

Restating `README § C-5`'s rejected objectives in measurement terms, because these are the metrics a
recovery product is normally judged on:

| Rejected | Why it is not the primary metric |
|---|---|
| Retry count, message count, action count | Effort, not outcome |
| Contacted-customer count | Measures intrusion |
| Isolated conversion rate on actioned opportunities | Ignores the counterfactual; maximised by acting only on certain recoveries |
| Gross recovered revenue (`M-05`) | Includes natural recovery; maximised by acting on everyone |
| Probability-model accuracy | An input, not an outcome |
| LLM confidence or output quality | Not a business result |
| Cost savings from automation | Not what Track 03 asks for |

`M-05` is the dangerous one, because it is the number most naturally reported as "money recovered". It
appears in every artefact **next to** `M-07` (natural) and `M-06` (attributed) precisely so it cannot be
read alone.

---

## 2. The primary metric

### 2.1 Definition

`M-10 Incremental Net Recovered Revenue` is computed by **paired policy comparison**, not by summing
per-opportunity attribution:

```
M-10(policy, seed) = NetRecovered(policy, seed) − NetRecovered(B0_NO_ACTION, seed)

where NetRecovered(policy, seed) =   Σ recovered_amount_paise · m          (M-05 · m)
                                   − Σ action_cost_paise                   (component of M-08)
                                   − Σ incentive_paid_paise                (component of M-08)
```

Both terms are evaluated on the **same dataset, same oracle, same seed** (`BF-1`).

### 2.2 Why paired comparison rather than attribution

Per-opportunity attribution requires deciding, for each recovery, whether REVIVE caused it. That
decision is (a) frequently ambiguous, (b) systematically biased toward the system doing the attributing,
and (c) the exact mechanism by which recovery products overstate their impact.

Paired comparison against `B0` sidesteps it: the difference between the world where REVIVE acted and
the world where nothing acted is measured at the portfolio level, where the oracle's answer is
unambiguous.

| Property | Consequence |
|---|---|
| Natural recovery cancels | It occurs in both arms, so it cannot be claimed |
| Ambiguous individual cases do not need adjudication for the primary number | `AMBIGUOUS` attribution affects diagnostics, not `M-10` |
| The number can be **negative** | A policy that spends more than it recovers reports a negative `M-10`, as it should |
| Requires `B0` to be run for every seed and profile | Non-negotiable (`§ 2 of 20`) |

Per-opportunity attribution (`M-06`, `M-07`, `M-09`) is still computed — a merchant needs case-level
explanation — but it is **tier 3 for judging** and never substitutes for `M-10`.

### 2.3 The `m` factor

`m` is the merchant's net retention factor: the fraction of recovered gross revenue that is genuinely
net of refunds, chargebacks, and cost of goods. It is a merchant parameter, `PROPOSED`, and it applies
identically to every policy, so it cannot shift a comparison. It is stated because reporting gross
transaction value as "revenue recovered" overstates by exactly `1/m`.

---

## 3. Attribution rules

Used for case-level reporting and for `M-12`.

| Case | Class | Rule |
|---|---|---|
| Recovery observed within `H` after an executed action, and the oracle says no natural recovery would have occurred within `H` | `ATTRIBUTED` | |
| Recovery observed, and the oracle says natural recovery would have occurred within `H` anyway | `NATURAL` | Counts toward `M-12`, not `M-06` |
| Recovery timestamp precedes the action timestamp | `NATURAL` | Always, no exceptions (`RR-FUNC-071`) |
| Recovery observed with no action taken | `NATURAL` | |
| Recovery observed after `H` | `NATURAL` by default | `late_recovery = true`; excluded from `M-06` (`AC-33`) |
| Multiple actions preceded the recovery | `AMBIGUOUS` | Not attributed to any single action; counts toward `M-09`; the opportunity's total is reported once, never per action |
| Recovery cannot be observed | `UNOBSERVABLE` | Excluded from numerator and denominator alike, and **counted** in `M-21` |

| # | Rule |
|---|---|
| AT-1 | Ambiguity always resolves **against** REVIVE (`P-7`) |
| AT-2 | No recovery is counted twice, across actions, cycles, or opportunities (`LK-4`) |
| AT-3 | `M-05 = M-06 + M-07 + M-09` exactly, and the artefact asserts it |
| AT-4 | Attribution is computed by one code path shared by every policy (`BF-5`) |

AT-1 is what makes the case-level numbers credible: every judgement call in the ambiguous middle is
resolved in the direction that makes REVIVE look worse.

---

## 4. Acceptance criteria for the build

Distinct from Claim C. Claim C is about the product's thesis; these are about whether the system was
built correctly. A run may satisfy all of these and still refute Claim C — that would be an honest
negative result, not a broken build.

| # | Criterion | Metric |
|---|---|---|
| AC-E1 | Zero actions without an `ALLOW` verdict | `M-16 = 0` |
| AC-E2 | Zero missed stops | `M-17 = 0` |
| AC-E3 | Zero executions of a `REQUIRE_APPROVAL` action without a valid approval | `M-18 = 0` |
| AC-E4 | Zero invariant violations | `M-22 = 0` |
| AC-E5 | Zero double executions and zero budget overruns under injected concurrency | `RR-NFR-040`, `RR-NFR-041` |
| AC-E6 | Audit chain verifies; state reconstructs from the chain | `M-58`, `V-1`…`V-12` |
| AC-E7 | Byte-identical artefacts on re-run at fixed seed | `M-46`, `RR-NFR-020` |
| AC-E8 | Zero uncached LLM calls during EVALUATE | `M-47 = 0` |
| AC-E9 | Every gate, every stopping rule, every state, and every action code exercised at least once, with gaps named | `M-55` |
| AC-E10 | Full baseline set run on every reported seed and profile | `20 § 3.1` |
| AC-E11 | Every reported number traces to a `MetricSnapshot` with a derivation reference | `DM-34` |
| AC-E12 | Performance envelopes met, or the miss reported | `RR-NFR-030`…`033` |
| AC-E13 | Disclosure block present in every artefact | `BA-3` |
| AC-E14 | Zero privacy-canary hits across all sinks | `M-57 = 0` |

AC-E1 through AC-E4 are build-blocking. AC-E5 through AC-E14 must either pass or appear as a named,
explained failure in the report — never be silently absent.

---

## 5. Calibration evaluation

`ENRV` is linear in `p`, so a mis-scaled probability translates directly into mis-scaled money. This
makes calibration more important than ranking quality, which reverses the usual priority
(`11 § 4.5`).

| Metric | Use |
|---|---|
| `M-24` Calibration — Brier score | Overall probabilistic accuracy, per action family and per cell level |
| `M-24` Calibration — expected calibration error, with a reliability table | Whether `p = 0.3` means 30% |
| `M-25` Uplift ranking quality | Whether the *ordering* of uplifts is right, reported as decile lift against the oracle |

| # | Rule |
|---|---|
| CE-1 | Calibration is reported for `p(i,a)` **and separately** for `p(i,∅)` | A well-calibrated action model with a badly-calibrated baseline model produces confidently wrong uplifts |
| CE-2 | Reported by cell level (0/1/2 shrinkage), so small-sample cells are visible | |
| CE-3 | Reported per policy where the policy uses a predictor (`B1`, `B5`, REVIVE) | |
| CE-4 | A calibration table with wide bins and no counts is not acceptable; bin counts are published | |

`M-24` carries both the Brier score and the ECE because they fail differently: a model can be sharp and
mis-scaled, or well-scaled and useless. `ENRV` is damaged by the first and merely unhelpful under the
second, so the scale error is the one that must not hide behind a good aggregate.

CE-1 is the calibration statement specific to this product. Everyone measures the model that predicts
success; almost nobody measures the model that predicts *doing nothing*, which here is half the
objective.

---

## 6. Allocation evaluation

| Question | Metric |
|---|---|
| Was capacity actually scarce? | `M-29` utilisation per resource; near-100% on binding resources or the profile is not testing allocation |
| What was contention worth? | `M-30` shadow prices, with `shadow_price_method` |
| How far from optimal? | `M-31` optimality gap, **only where `EXACT` was tractable**; absent otherwise, never estimated |
| Did prioritisation displace anything? | `M-32` displacement count and displaced value |
| Was it fast enough? | `M-33` allocator runtime against `RR-NFR-031` |
| Did the default allocator actually run? | `M-34` fallback rate, with reasons |

`M-31`'s "absent, never estimated" rule matters: an optimality gap invented by comparing against a
heuristic upper bound would be a fabricated number, which `README § C-8` forbids.

---

## 7. Report structure

Generated, in this order. The order is deliberate: constraints and limitations precede results.

```
1  Disclosure block            synthetic data, unverified fidelity, no production claim
2  Configuration               seed set, profiles, all versions, config_hash, frozen parameters
3  Guardrail results           M-16, M-17, M-18, M-22, M-57, M-58 / V-1…V-12, invalidated runs
4  Coverage                    M-55 — gates, rules, states, actions, with gaps named
5  Primary result              M-10 per seed, paired, per profile; median, min, max, losses
6  Secondary constraints       M-11, M-12, M-13, M-23 alongside the primary
7  Failure accounting          M-19, M-23, M-28, M-35, M-43 — failed actions, wasted spend,
                               missed value, wrong actions, unresolved
8  Cost accounting             M-08, M-45, M-49, M-52, M-53, M-37 human review load
9  Ablations                   LLM, allocator, component; sensitivity curves with the operating point
10 Calibration                 M-24 with bin counts, M-25, M-26, M-27
11 Allocation                  M-29…M-34
12 Threats to validity         TV-1…TV-10, verbatim
13 Limitations                 § 9, generated
```

| # | Rule |
|---|---|
| RS-1 | Sections 1, 3, and 4 precede section 5. **A reader cannot reach the headline number without passing the guardrail and coverage results** |
| RS-2 | Section 7 is never omitted, even if empty — an empty failure section states explicitly that it was checked |
| RS-3 | No number is hand-written (`BA-1`) |
| RS-4 | Losses, invalidated runs, and skipped cells appear in the summary, not only in appendices |

RS-1 is a small structural choice with a large effect: it makes it impossible to present the money
number without first presenting the evidence that the money number is trustworthy.

---

## 8. What a "good result" looks like

Stated in advance so it cannot be redefined afterwards.

| Outcome | Interpretation |
|---|---|
| Tier 0 clean, `M-10 > 0` vs every baseline in `BALANCED` and `SCARCE`, `M-13` no worse, small or absent advantage in `ABUNDANT` | Claim C supported within the stated scope. **This is the target.** |
| Tier 0 clean, `M-10 > 0` only vs `B0`, `B2`, `B4`, `B6` but not `B3` or `B5` | The system works; the *specific* contributions of uplift and constrained allocation are unsupported. Must be reported as such — the differentiator would be unproven |
| Tier 0 clean, `M-10 ≈ 0` everywhere | Honest negative result. The thesis is not supported in this environment. Reported as the headline |
| Tier 0 clean, `M-10 > 0` but `M-13` worse | Recovery bought with customer intrusion. **Reported as a trade-off, not a win** (`RR-METRIC-010`) |
| Tier 0 **not** clean | No result. Build failure |
| `M-10 > 0` everywhere including `ABUNDANT`, with no explanation | Treated as a **suspected measurement error**, investigated before publication (`20 § 6.3`) |

The last row is the anti-self-deception clause. A result that is good everywhere is more likely to
indicate a broken experiment than a brilliant product, and the package commits in advance to treating
it that way.

---

## 9. Mandatory disclosures

Generated into `disclosures.md` for every run and every benchmark (`BA-3`). Not suppressible.

| # | Disclosure |
|---|---|
| D-E1 | All data is synthetic. No real merchant, customer, transaction, or payment rail is involved |
| D-E2 | The generator's fidelity to real payment behaviour is **unverified**. No result is evidence about the real world |
| D-E3 | The counterfactual is supplied by a hidden oracle that is part of the same synthetic model being measured |
| D-E4 | The dataset was deliberately constructed so that value-ranking and probability-ranking can be wrong. Results show REVIVE handles that structure; they do not show the structure exists in reality |
| D-E5 | No Razorpay API was called. No real payment was attempted. No real person was contacted |
| D-E6 | Razorpay capability assumptions are unverified ([36](36-razorpay-integration-assumptions.md)) |
| D-E7 | Regulatory assumptions (TRAI/DND, RBI recurring-payment norms) are unverified and are not legal advice (`13 § 10`) |
| D-E8 | Allocation is single-period myopic (`ADR-004`); multi-period effects are unmeasured |
| D-E9 | Subscription continuation value is set to zero (`ADR-007`); subscription results are understated |
| D-E10 | The predictor learns and is evaluated within the same run; learning benefit may be optimistic |
| D-E11 | Seed count is small; no population-level statistical claim is made |
| D-E12 | Baselines are this project's implementations of common policies, published in full |
| D-E13 | Audit trail is append-only and hash-verified, **not** cryptographically notarised or legally sufficient (`16 § 5.2`) |
| D-E14 | Idempotency is guaranteed within REVIVE only, not end to end (`15 § 3.3`) |
| D-E15 | Recoveries observed after horizon `H` are excluded from attributed recovery |
| D-E16 | This is a hackathon-scope prototype. It is not production-ready, and no production-readiness claim is made anywhere in this package |

D-E4 and D-E3 are the two a hostile reviewer would find on their own. Stating them first costs nothing
and is the difference between a package that survives scrutiny and one that gets caught.

---

## 10. Requirement mapping

| Requirement | Where |
|---|---|
| `RR-METRIC-001` primary metric defined | § 2 |
| `RR-METRIC-010` trade-off presentation | § 1.2, § 8 |
| `RR-BENCH-002` baseline comparison | § 2.1 |
| `RR-BENCH-003` dispersion reported | § 7 step 5 |
| `RR-BENCH-006` `NO_ACTION` correctness | `M-26` |
| `RR-BENCH-007` traceable numbers | AC-E11, RS-3 |
| `RR-BENCH-009` unflattering configuration | § 8 |
| `RR-BENCH-010` disclosure | § 9 |
| `RR-BENCH-012`/`013` failures and cost | § 7 steps 7–8 |
| `RR-FUNC-071` attribution on late success | § 3 |
| `RR-NFR-020` reproducibility | AC-E7 |
| `P-7` honesty about limits | § 8, § 9 |
| `P-15` no silent caps | RS-2, RS-4 |

---

## 11. Open items

| Item | Label |
|---|---|
| `m` (net retention factor) value | `PROPOSED`; per merchant, identical across policies |
| Whether `M-25` should use a Qini-style curve or decile lift | `PROPOSED` decile lift against the oracle, for interpretability |
| Calibration bin count and edges | `PROPOSED`; must be frozen before measurement |
| Whether `UNOBSERVABLE` outcomes should be reported as a rate or a value | `PROPOSED` both |
| Whether an out-of-sample predictor evaluation is feasible within one run | `UNKNOWN`; D-E10 stands until it is |
| Acceptable `M-13` degradation, if any | `UNKNOWN — MUST BE DECIDED DURING IMPLEMENTATION`; until decided, any degradation is reported as a trade-off |
