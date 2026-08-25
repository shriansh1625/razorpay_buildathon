# 25 · UI/UX Specification

Seven screens. Each is specified by its purpose, user, data bindings, interactions, and states.
This is not a visual design document — it specifies what the implementation must expose.

> **Convention.** Every metric referenced by `M-nn` is defined in
> [37-metrics-dictionary.md](37-metrics-dictionary.md). Every requirement referenced by `RR-UI-nnn`
> is in [05-functional-requirements.md](05-functional-requirements.md). Every state name is from
> [34-state-machine.md](34-state-machine.md).

---

## 1. Global rules

| Rule | Statement |
|---|---|
| Synthetic-data disclosure | Every screen states when a figure is derived from synthetic data (`RR-UI-008`) |
| No fabricated numbers | No hard-coded metric value. Every number comes from a generated artefact |
| Metric units | Money displayed in ₹ (INR) with paise precision where relevant. Internal storage remains paise |
| Explanation safety | Natural-language explanations (`RR-FUNC-044`) are absent-safe: deleting them breaks no screen (`P-6`) |
| Accessibility | Colour alone never encodes meaning. All interactive elements have labels. Keyboard navigable |
| Responsive | Functional at ≥ 1280px viewport. Degraded but usable at 1024px |

---

## 2. Screen inventory

| # | Screen | Requirement | Primary user |
|---|---|---|---|
| 1 | Revenue Command Center | `RR-UI-001` | Merchant operator, executive |
| 2 | Revenue Leakage Explorer | `RR-UI-002` | Analyst |
| 3 | Recovery Opportunities | `RR-UI-003` | Operator, approver |
| 4 | Decision Detail | `RR-UI-004` | Analyst, reviewer |
| 5 | Recovery Allocation | `RR-UI-005` | Operator, analyst |
| 6 | Audit Trail | `RR-UI-006` | Reviewer, engineer |
| 7 | Benchmark Lab | `RR-UI-007` | Evaluator, judge |

---

## 3. Screen 1 — Revenue Command Center

### Purpose

The executive overview. Answers: "How much money is at risk, how much are we recovering, and is anything wrong?"

### User

Merchant operator, executive reviewer.

### Primary information

| Element | Source | Metric ID |
|---|---|---|
| **Value at risk** | Sum of `value_at_risk_paise` over all open opportunities | `M-01` |
| **Addressable value** | Same, restricted to `addressable = true` | `M-02` |
| **Expected recoverable** | Sum of `ENRV` over selected candidates | Derived from allocation |
| **Recovered revenue (gross)** | `M-05` | `M-05` |
| **Incremental recovery** | `M-10` — REVIVE vs B0, paired | `M-10` |
| **Active interventions** | Count of opportunities in `ACTING` or `AWAITING_OUTCOME` | State query |
| **Budget utilisation** | Per-resource utilisation bar | `M-29` |
| **Important alerts** | Critical and high-severity alerts from [24 § 4](24-observability.md) | Alert engine |
| **Intervention count** | Total interventions this period | `Intervention` count |
| **Policy violations** | `M-16` — must show zero prominently | `M-16` |

### Interactions

| Interaction | Behaviour |
|---|---|
| Click value-at-risk | Navigate to Revenue Leakage Explorer (Screen 2) |
| Click recovered revenue | Navigate to Recovery Opportunities filtered to `RECOVERED` |
| Click an alert | Navigate to the relevant detail screen |
| Click budget bar | Navigate to Recovery Allocation (Screen 5) |
| Time range selector | Filter metrics to selected period |

### States

| State | Display |
|---|---|
| **Empty** | "No opportunities detected yet. Waiting for signals." No fake zeros |
| **Loading** | Skeleton placeholders for each metric card. No spinner blocking the page |
| **Error** | "Unable to load [metric]. Last known value: [value] at [time]." Never hide errors |
| **Success** | All metrics populated with current values. Synthetic-data banner visible |

### Accessibility

- All metric values have `aria-label` with full description and unit
- Colour-coded alert severity supplemented by icon shape (triangle for critical, circle for warning)
- Budget utilisation bars have text percentage labels

---

## 4. Screen 2 — Revenue Leakage Explorer

### Purpose

Understand where revenue leaks and why. Answers: "What categories of loss exist, what causes them, and how do they relate?"

### User

Analyst.

### Primary information

| Element | Source |
|---|---|
| **Leakage by risk class** | `value_at_risk_paise` grouped by `risk_class` (`PAYMENT_FAILURE`, `CHECKOUT_ABANDONMENT`, `SUBSCRIPTION_FAILURE`, `RECEIVABLE_OVERDUE`) |
| **Leakage by cause** | `value_at_risk_paise` grouped by top `candidate_cause` from `Diagnosis` |
| **Contributing factors** | Factor frequency: instrument type, customer segment, payment method, failure reason, ageing bucket |
| **Relationship graph** | Directed graph: risk class → failure reason → candidate cause → action applicability |
| **Drill-down** | Click any node to filter the opportunity list |

### Interactions

| Interaction | Behaviour |
|---|---|
| Click risk-class segment | Filter all views to that class |
| Click cause code | Show opportunities with that diagnosis |
| Click graph node | Highlight connected nodes; filter table |
| Hover graph edge | Show count and value |
| Drill to opportunity | Navigate to Decision Detail (Screen 4) |

### States

| State | Display |
|---|---|
| **Empty** | "No revenue leakage detected. No opportunities exist." |
| **Loading** | Graph skeleton; table skeleton |
| **Error** | "Unable to load leakage data." Partial data shown if available |
| **Success** | Graph and tables populated. Synthetic-data banner |

### Accessibility

- Graph has a tabular alternative view for screen readers
- All segments have text labels, not just colour differentiation

---

## 5. Screen 3 — Recovery Opportunities

### Purpose

The operational worklist. Shows every opportunity with its current state, selected action, and priority. Includes the approval queue.

### User

Operator, approver.

### Primary information

| Column | Source |
|---|---|
| **Opportunity ID** | `opp_<ULID>` |
| **Risk class** | `risk_class` |
| **Amount at risk** | `value_at_risk_paise` (displayed as ₹) |
| **Expected recovery** | `ENRV` of selected candidate (paise → ₹) |
| **Chosen action** | Action code and parameters of the selected candidate |
| **Priority rank** | Allocation rank within the cycle |
| **Policy state** | Combined gate verdict: `ALLOW`, `DEFER`, `DENY`, `REQUIRE_APPROVAL` |
| **Status** | Current opportunity state from [34](34-state-machine.md) |
| **Reason** | For `NO_ACTION`, `DEFERRED`, `REJECTED`, `STOPPED`: the reason code |

### Approval queue integration

The approval queue is a filtered view of this screen where `policy_state = REQUIRE_APPROVAL`.

| Element | Source |
|---|---|
| Pending approvals count | `QUEUED` approval requests |
| Approval action | Approve / Reject / Modify buttons |
| Modification | Modify opens a parameter editor; modified action re-enters all gates (`RR-FUNC-066`) |
| Expiry countdown | Time remaining before `SR-06` voids the request |

### Interactions

| Interaction | Behaviour |
|---|---|
| Click opportunity row | Navigate to Decision Detail (Screen 4) |
| Sort by column | Any column sortable |
| Filter by status | Dropdown: All, Active, Awaiting Approval, Deferred, Stopped, Recovered |
| Filter by risk class | Multi-select |
| Approve action | Submit approval; action re-enters gates next cycle |
| Reject action | Submit rejection; opportunity deferred |
| Modify action | Open parameter editor; submit triggers re-gating |
| Bulk filter by ENRV | Slider for minimum ENRV threshold |

### States

| State | Display |
|---|---|
| **Empty** | "No opportunities in the current view. Adjust filters or wait for the next cycle." |
| **Loading** | Table skeleton rows |
| **Error** | "Unable to load opportunities. Retry." |
| **Success** | Paginated table with sort and filter. Synthetic-data banner |

### Accessibility

- Table rows are keyboard-navigable
- Approval buttons have confirmation dialogs
- Status badges use icons in addition to colour

---

## 6. Screen 4 — Decision Detail

### Purpose

The full decision record for a single opportunity. Everything needed to answer: "Why did REVIVE do this?"

### User

Analyst, reviewer, judge.

### Primary information

| Section | Content |
|---|---|
| **Context** | Customer segment, tenure, spend band, instrument state, contact history, fatigue state, timing context. All from `ContextObject`. Fields marked null have their reason shown |
| **Evidence** | Failure reason, degradation flag, cohort statistics, relevant signals |
| **Candidate causes** | Ranked `Diagnosis` with confidence bands and evidence references |
| **Candidate actions** | Full candidate set including `NO_ACTION`. For each: action code, parameters, `p(i,a)`, `p(i,∅)`, uplift, cost components (`c(a)`, `d(i,a)`, `F(i,a)`), `ENRV`, uncertainty interval |
| **Counterfactual comparison** | Side-by-side: what happens with each action vs no action. Visual bar chart of ENRV by candidate |
| **Expected value** | Selected candidate's ENRV with component breakdown |
| **Selected action** | The chosen action with its rank and reason for selection |
| **Gate verdicts** | Full gate trace (G1…G12), each with verdict and inputs. Includes passes, not just failures |
| **Policy result** | Final combined verdict |
| **Outcome** | If observed: `recovered_amount_paise`, attribution class, actual cost, variance against estimate |
| **Audit history** | Chronological audit events for this opportunity, linked by `opportunity_id` |

### Interactions

| Interaction | Behaviour |
|---|---|
| Expand candidate row | Show full ENRV component breakdown |
| Compare candidates | Toggle comparison view showing all candidates side by side |
| Click gate verdict | Show gate input details and policy pack parameter |
| Click audit event | Expand to show full event payload |
| Navigate to related opportunity | If this opportunity was deduplicated with another |
| Export | Download the full decision record as JSON |

### States

| State | Display |
|---|---|
| **Empty** | "No decision has been made for this opportunity yet." Show context and evidence only |
| **Loading** | Section-by-section loading with skeletons |
| **Error** | "Unable to load [section]." Show available sections |
| **Success** | Full decision record. Synthetic-data banner. Generated explanation clearly marked as generated |

### Accessibility

- ENRV bar chart has a tabular alternative
- All monetary values have `aria-label` with full precision
- Gate verdict icons supplemented by text labels

---

## 7. Screen 5 — Recovery Allocation

### Purpose

Show how limited recovery resources are being allocated. Answers: "Where is the capacity going, and what are we leaving on the table?"

### User

Operator, analyst.

### Primary information

| Section | Content |
|---|---|
| **Available capacity** | Per resource: total, committed, reserved, available. Visual bar |
| **Budget** | Per resource: period limit, consumed, remaining. Pacing indicator |
| **Binding constraints** | Resources at or near capacity with shadow prices (`M-30`) |
| **Allocated actions** | Opportunities with `SELECTED` decisions, grouped by action type |
| **Deferred opportunities** | Opportunities with `DEFERRED` decisions, with deferral reason and ENRV they would have consumed |
| **Rejected opportunities** | Opportunities with `REJECTED` decisions, with rejection reason |
| **No-action decisions** | Opportunities where `NO_ACTION` was chosen, with reason codes and value (`M-15`) |
| **Shadow prices** | Per binding constraint: marginal ENRV per unit of resource, with method label (`M-30`) |
| **Displacement** | Positive-ENRV candidates not selected due to constraints (`M-32`) |
| **Allocator mode** | `PRIMARY` or `FALLBACK_GREEDY`, with reason if fallback |

### Interactions

| Interaction | Behaviour |
|---|---|
| Click resource bar | Drill into consumption by action type |
| Click deferred opportunity | Navigate to Decision Detail (Screen 4) |
| Sort allocated/deferred/rejected | By ENRV, value at risk, or reason |
| Filter by resource | Show only opportunities consuming a specific resource |
| Hover shadow price | Show explanation of what one additional unit would enable |

### States

| State | Display |
|---|---|
| **Empty** | "No allocation has been performed yet. Waiting for the first cycle." |
| **Loading** | Resource bars skeleton; tables skeleton |
| **Error** | "Unable to load allocation data." |
| **Success** | Resource visualisation and tables populated. Shadow-price method labelled. Synthetic-data banner |

### Accessibility

- Resource bars have percentage text labels
- Shadow prices presented in a table as well as visually

---

## 8. Screen 6 — Audit Trail

### Purpose

Complete chronological trace. The system of record made visible.

### User

Reviewer, engineer, judge.

### Primary information

| Element | Content |
|---|---|
| **Event list** | Chronological audit events with `audit_id`, `event_type`, `occurred_at`, actor, correlation IDs |
| **Decision trace** | For a selected opportunity: the full causal chain from signal → diagnosis → candidates → decision → gate → execution → outcome |
| **Execution trace** | For a selected intervention: intent → adapter call → result → outcome → cost reconciliation |
| **Chain verification** | Status of `V-1`…`V-12` verification checks (`M-58`). Green/red per check |
| **Hash chain** | Visual indicator of chain integrity. Current hash, previous hash, any breaks |

### Interactions

| Interaction | Behaviour |
|---|---|
| Filter by event type | Multi-select from closed enum |
| Filter by opportunity | Enter `opp_<ULID>` to show all events for one opportunity |
| Filter by cycle | Select cycle to show its events |
| Search | Free-text search across event payloads (non-PII fields only) |
| Expand event | Show full event payload |
| Verify chain | Run verification checks on demand; display results |
| Export | Download filtered audit events as JSON Lines |

### States

| State | Display |
|---|---|
| **Empty** | "No audit events recorded yet." |
| **Loading** | Event list skeleton |
| **Error** | "Unable to load audit events." |
| **Success** | Paginated, filterable event list. Chain verification status. Synthetic-data banner |

### Accessibility

- Event types have descriptive labels, not just codes
- Chain verification results in text table, not just colour indicators

---

## 9. Screen 7 — Benchmark Lab

### Purpose

The proof screen. Shows that REVIVE beats baselines on measured, reproducible batch evaluation.

### User

Evaluator, judge.

### Primary information

| Section | Content |
|---|---|
| **Baseline comparison** | Table: REVIVE vs each baseline (B0–B6 + Oracle). Per policy: `M-10`, `M-11`, `M-12`, `M-13`, `M-23` |
| **Batch size** | Number of opportunities in the batch |
| **Recovered amount** | Gross (`M-05`) and incremental (`M-10`) per policy |
| **Incremental recovery** | Paired difference with confidence interval, per seed and aggregated |
| **Cost** | `M-08` per policy |
| **Failures** | `M-16`, `M-17`, `M-18`, `M-22` per policy — all must be zero |
| **Reproducibility** | `M-46` status per seed pair. Byte identity confirmation |
| **Seed matrix** | All seeds with per-seed `M-10`, showing variance |
| **Profile comparison** | Results across `BALANCED`, `HIGH_NATURAL`, `SCARCE`, `ABUNDANT` profiles |
| **Single-case replay** | Select one opportunity and see REVIVE vs baseline decision side by side |
| **Coverage** | `M-55` with named gap lists |
| **Limitations** | Mandatory section listing where REVIVE performed worse or wasted effort |

### Interactions

| Interaction | Behaviour |
|---|---|
| Select baseline | Highlight comparison pair |
| Select seed | Show per-seed results |
| Select profile | Filter to profile |
| Click opportunity in comparison | Navigate to Decision Detail (Screen 4) |
| Drill into coverage gaps | Expand named gap lists |
| Export | Download full metrics artefact |
| Toggle confidence intervals | Show/hide CI on charts |

### States

| State | Display |
|---|---|
| **Empty** | "No benchmark runs completed yet. Run the benchmark to see results." |
| **Loading** | Comparison table skeleton; chart skeletons |
| **Error** | "Unable to load benchmark results." |
| **Success** | Full comparison populated. Limitations section visible. Synthetic-data banner. All numbers from generated artefacts, none hard-coded |

### Accessibility

- Comparison table readable by screen reader with row/column headers
- Charts have tabular alternatives
- Confidence intervals shown numerically as well as visually

---

## 10. Design constraints

| Constraint | Rationale |
|---|---|
| No dashboard clutter | Each screen has a single purpose. Unrelated metrics do not share a screen |
| No vanity metrics | Every displayed number is defined in [37](37-metrics-dictionary.md) or derived from a requirement |
| No cosmetic-only animations | Animations serve function (loading, transition) not decoration |
| Data-first, not chart-first | Tables are the primary representation; charts supplement but do not replace |
| Disclosure-first | Synthetic-data banner, limitations section, uncertainty indicators are mandatory, not optional |

---

## 11. Requirement mapping

| Requirement | Screen | Where |
|---|---|---|
| `RR-UI-001` | 1 — Revenue Command Center | § 3 |
| `RR-UI-002` | 2 — Revenue Leakage Explorer | § 4 |
| `RR-UI-003` | 3 — Recovery Opportunities | § 5 |
| `RR-UI-004` | 4 — Decision Detail | § 6 |
| `RR-UI-005` | 5 — Recovery Allocation | § 7 |
| `RR-UI-006` | 6 — Audit Trail | § 8 |
| `RR-UI-007` | 7 — Benchmark Lab | § 9 |
| `RR-UI-008` | All | § 1 |
