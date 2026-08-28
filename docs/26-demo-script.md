# 26 · Demo Script

Five minutes. Ten claims. Every claim has evidence. No fabricated number.

> **Rule.** This script specifies what must be shown and what must not be claimed. Actual
> performance numbers are placeholders marked `[PLACEHOLDER — INSERT FROM BENCHMARK]` and must be
> filled from generated artefacts after the benchmark runs.

---

## 0. Pre-demo setup

| Item | Status |
|---|---|
| Benchmark has been run at the declared seed set | Required |
| Metrics artefact exists and has been verified | Required |
| `M-16 = 0`, `M-17 = 0`, `M-18 = 0`, `M-22 = 0` | Required — if any is non-zero, do not demo |
| `M-46 = PASS` (reproducibility) | Required |
| All seven screens are functional | Required |
| Synthetic-data banners are visible on every screen | Required |

---

## 1. Beat 1 — Problem and stakes (0:00–0:30)

### Screen shown

Revenue Command Center (Screen 1)

### Action taken

Open the dashboard. Point to the value-at-risk figure.

### Exact claim

> "A merchant loses revenue continuously and in small pieces — failed payments, abandoned
> checkouts, subscription failures, overdue invoices. The question is not 'what happened to this
> one payment' — it is 'where should I spend my next unit of recovery effort to get the most
> money back?'"

### Evidence required

- `M-01` value at risk displayed on screen
- Four risk classes visible in the breakdown
- Budget utilisation showing scarcity (capacity < demand)

### What must NOT be claimed

- No claim about real merchant data
- No claim about real revenue amounts
- No claim about Razorpay production volumes
- Must state: "This is synthetic data"

---

## 2. Beat 2 — Revenue leakage (0:30–1:15)

### Screen shown

Revenue Leakage Explorer (Screen 2)

### Action taken

Navigate to the leakage explorer. Show the breakdown by risk class and cause. Click one cause
node in the relationship graph to drill down.

### Exact claim

> "PAYVANTA detects revenue at risk across four categories and diagnoses candidate causes.
> Here's the leakage landscape — [PLACEHOLDER]% of value at risk is from payment failures,
> [PLACEHOLDER]% from overdue receivables. The relationship graph shows how failure reasons
> map to candidate causes and determine which recovery actions are applicable."

### Evidence required

- Leakage by risk class with values
- Leakage by candidate cause
- Relationship graph showing risk class → cause → action mapping
- Drill-down from a cause node to specific opportunities

### What must NOT be claimed

- No claim of "root cause analysis" — these are **candidate causes** with confidence bands
- No claim of causal inference
- No claim these percentages reflect real-world distributions

---

## 3. Beat 3 — One decision deep dive (1:15–2:00)

### Screen shown

Decision Detail (Screen 4)

### Action taken

Select a single opportunity. Walk through the full decision pipeline.

### Exact claim

> "For this [risk class] opportunity worth ₹[PLACEHOLDER], PAYVANTA generated [N] candidate
> actions plus no-action. Here's the counterfactual comparison: each candidate's recovery
> probability, the natural recovery probability, the uplift, the cost, and the expected
> incremental net recovered revenue. PAYVANTA selected [action] because it had the highest ENRV
> of ₹[PLACEHOLDER] paise. The no-action alternative would have cost nothing but recovered
> ₹[PLACEHOLDER] paise less in expectation."

### Evidence required

- Context object visible (customer segment, instrument state, fatigue)
- Candidate causes with confidence bands
- Full candidate set with `p(i,a)`, `p(i,∅)`, uplift, cost components, ENRV
- `NO_ACTION` included as a candidate with `ENRV = 0`
- Visual counterfactual comparison
- Gate trace showing all 12 gates evaluated
- Outcome (if observed): actual recovered amount, attribution class

### What must NOT be claimed

- No claim that the diagnosis is a proven root cause
- No claim that the probability estimates are calibrated against real data
- No claim that the selected action was objectively optimal — only that it had the highest ENRV under the model

---

## 4. Beat 4 — Portfolio-level allocation (2:00–3:00)

### Screen shown

Recovery Allocation (Screen 5)

### Action taken

Show the allocation view. Highlight binding constraints, shadow prices, deferred and rejected
opportunities.

### Exact claim

> "PAYVANTA doesn't decide one opportunity at a time — it solves a portfolio allocation problem.
> This cycle had [N] opportunities competing for [N] resources. The allocator selected [N]
> actions, deferred [N], and chose no-action for [N]. Here are the binding constraints — SMS
> capacity is exhausted, and its shadow price tells us that one more SMS credit would generate
> ₹[PLACEHOLDER] of expected incremental recovery. These [N] opportunities were deferred
> because the budget was insufficient, not because they weren't worth pursuing."

### Evidence required

- Resource utilisation bars showing near-exhaustion for at least one resource
- Shadow prices for binding constraints (with method label)
- Deferred opportunities with their ENRV (money left on the table, honestly shown)
- Rejected opportunities with reasons
- No-action decisions with reason codes and `M-15`
- `allocator_mode` shown (PRIMARY or FALLBACK_GREEDY)

### What must NOT be claimed

- No claim that the allocation is globally optimal (it may be a Lagrangian relaxation or greedy fallback)
- No claim about real resource costs
- Shadow-price method must be labelled — do not present a greedy estimate as a dual optimum

---

## 5. Beat 5 — Guardrails (3:00–3:40)

### Screen shown

Decision Detail (Screen 4) — select an opportunity where a gate denied or modified an action.
Then show the Audit Trail (Screen 6).

### Action taken

Show a gate denial. Show a stopping rule firing. Show the approval queue.

### Exact claim

> "PAYVANTA does not bypass controls. Here's an action that was denied by [gate] because
> [reason]. Here's a stopping rule that fired — this customer was contacted [N] times and
> PAYVANTA stopped, even though the ENRV was positive. Here's the approval queue — this
> high-value action required human approval. And here's the most important number:
> `M-16 = 0` — zero actions executed without a full ALLOW verdict."

### Evidence required

- A gate `DENY` or `ALLOW_WITH_MODIFICATION` visible in a gate trace
- A stopping rule (`SR-*`) that fired, with reason code
- Approval queue with at least one request (approved, rejected, or expired)
- `M-16 = 0` on the dashboard or benchmark screen
- `M-17 = 0` and `M-18 = 0`
- Audit chain verification passing (`M-58`)

### What must NOT be claimed

- No claim that the guardrails are production-ready for real regulatory compliance
- No claim about specific legal requirements (TRAI, RBI) — those are `UNVERIFIED`
- Must state: "Consent semantics and communication rules are synthetic"

---

## 6. Beat 6 — Benchmark (3:40–4:20)

### Screen shown

Benchmark Lab (Screen 7)

### Action taken

Show the baseline comparison table. Show the seed matrix. Show the confidence interval.

### Exact claim

> "PAYVANTA's claim is falsifiable and measured. On a batch of [N] synthetic opportunities
> across [N] seeds, the REVIVE recovery policy recovered ₹[PLACEHOLDER] more than the best non-trivial baseline
> (B[N]: [name]), net of all costs. The median paired advantage is ₹[PLACEHOLDER] with a
> [PLACEHOLDER]% confidence interval of [PLACEHOLDER, PLACEHOLDER]. PAYVANTA also outperforms
> on cost efficiency: ₹[PLACEHOLDER] recovered per rupee spent, versus ₹[PLACEHOLDER] for
> the best baseline. Zero policy violations across all seeds."

### Evidence required

- Comparison table: REVIVE vs B0–B6, with `M-10`, `M-11`, `M-13`, `M-23`
- Multi-seed results with per-seed `M-10`
- Paired confidence interval for the primary comparison
- `M-16 = 0` across all seeds
- Reproducibility: `M-46 = PASS`
- Mandatory: the `ABUNDANT` profile where REVIVE's advantage shrinks (honesty)

### What must NOT be claimed

- No claim about real-world performance
- No claim about production deployment results
- No extrapolation of results to real merchants
- Must show the `ABUNDANT` profile result even if it is unflattering
- Must state: "All results are on synthetic data. Generator fidelity to real payment behaviour is UNVERIFIED"

---

## 7. Beat 7 — Learning and conclusion (4:20–5:00)

### Screen shown

Benchmark Lab (Screen 7) — learning ablation section. Then Revenue Command Center (Screen 1).

### Action taken

Show the learning-on vs learning-off comparison. Return to the command center.

### Exact claim

> "PAYVANTA learns from outcomes. With learning enabled, calibration [improved/was maintained]
> across cycles. The learning-on vs learning-off ablation shows [PLACEHOLDER] — and we report
> both results honestly. The limitations section shows where the REVIVE policy performed worse than a
> baseline or wasted effort. Finally: PAYVANTA doesn't just automate recovery actions. It
> allocates bounded recovery effort toward the opportunities with the highest expected
> incremental net revenue, executes within merchant-defined controls, and proves the result
> through reproducible batch evaluation."

### Evidence required

- Learning-on vs learning-off `M-10` comparison
- `M-24` calibration metrics
- Limitations section visible in the benchmark report (mandatory)
- Adverse findings section visible (mandatory)
- Return to command center showing the system of record

### What must NOT be claimed

- No claim that learning always improves results
- No claim about convergence in production
- Must show limitations and adverse findings — hiding them is a demo failure

---

## 8. Timing budget

| Beat | Start | End | Duration | Screen |
|---|---|---|---|---|
| 1. Problem | 0:00 | 0:30 | 30s | Revenue Command Center |
| 2. Leakage | 0:30 | 1:15 | 45s | Revenue Leakage Explorer |
| 3. Decision | 1:15 | 2:00 | 45s | Decision Detail |
| 4. Allocation | 2:00 | 3:00 | 60s | Recovery Allocation |
| 5. Guardrails | 3:00 | 3:40 | 40s | Decision Detail + Audit Trail |
| 6. Benchmark | 3:40 | 4:20 | 40s | Benchmark Lab |
| 7. Learning | 4:20 | 5:00 | 40s | Benchmark Lab + Command Center |

Total: 5:00

---

## 9. Demo integrity rules

| Rule | Statement |
|---|---|
| No hidden steps | The demo runs end to end without manual intervention behind the scenes |
| No pre-baked results | All numbers come from the benchmark artefact generated by the documented command |
| No cherry-picked seeds | The seed set is declared before the run, not selected for favourable results |
| No suppressed failures | The limitations section is shown, not scrolled past |
| No real-data claims | Every screen shows the synthetic-data banner |
| Reproducible | A judge can re-run the benchmark at the declared seed and see identical results |

---

## 10. Placeholder registry

Every `[PLACEHOLDER]` in this script must be filled from the following metrics after the benchmark
runs. No manual entry.

| Placeholder | Source metric | Filled from |
|---|---|---|
| Value at risk | `M-01` | Artefact |
| Risk-class percentages | `M-01` grouped by class | Artefact |
| Opportunity ENRV | `ENRV` from decision record | Artefact |
| Natural recovery comparison | `p(i,∅)` from candidate | Artefact |
| Batch size | Opportunity count | Artefact |
| Seed count | Run configuration | Config |
| Incremental recovery | `M-10` | Artefact |
| Confidence interval | Paired CI from evaluation | Artefact |
| Cost efficiency | `M-11` | Artefact |
| Learning ablation | `M-10` learning-on vs off | Artefact |

---

## 11. Pitch video — official benchmark segment (04:10–05:00)

Approximately 40–50 seconds of the five-minute pitch. Not the whole video.
Control Room numbers remain **sandbox**. Official cells remain **official**.

| Time | Beat | Surface |
|---|---|---|
| 04:10 | “Now let’s see whether this is just one carefully selected scenario.” | Leave Control Room |
| 04:15 | 20 seeds × 6 profiles × 5 policies | `#/benchmark` |
| 04:20 | 600 official cells | Executive stats |
| 04:25 | 120 groups | Executive stats |
| 04:30 | Profile × policy matrix | `#/benchmark/matrix` |
| 04:35 | ABUNDANT × REVIVE | Matrix cell |
| 04:40 | Seed 14 | Seed drill-down |
| 04:45 | Cell evidence + checksum | Forensic panel |
| 04:50 | “Same engine. Measured across the experiment.” | |
| 05:00 | MEASURED. NOT CLAIMED. | Final seal |

Do not click Run Recovery. Do not present sandbox incremental net as M-10.
Do not claim the 600-cell run proves superiority.

Full evidence map: [42-official-benchmark.md](42-official-benchmark.md).
