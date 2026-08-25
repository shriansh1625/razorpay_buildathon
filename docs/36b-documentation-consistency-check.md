# 36b · Documentation Consistency Check

A formal audit of cross-document consistency across the REVIVE documentation package.
Inconsistencies are exposed, not silently resolved. The implementation phase can resolve them
explicitly via ADRs.

> **Naming.** The number `36` is occupied by
> [36-razorpay-integration-assumptions.md](36-razorpay-integration-assumptions.md). This document
> uses `36b`. Similarly, `35` is occupied by [35-learning-engine.md](35-learning-engine.md), so
> the additional decision specifications use `35b`. The number `33` is occupied by
> [33-not-a-clone.md](33-not-a-clone.md), so requirement traceability was created as
> [33-requirement-traceability.md](33-requirement-traceability.md) (the repository allows both
> to coexist as they serve different purposes). These naming decisions are recorded here.

---

## 1. Product identity

| Check | Result |
|---|---|
| Product name is "REVIVE" everywhere | **CONSISTENT.** All documents use "REVIVE" |
| Subtitle is "Revenue Recovery Autopilot" everywhere | **CONSISTENT** |
| Product definition matches across [00 § 3](00-project-charter.md), [02](02-product-vision.md), [README](README.md) | **CONSISTENT.** The locked definition is reproduced verbatim |

---

## 2. Product definition and objective

| Check | Result |
|---|---|
| Optimisation objective is "maximise expected incremental net recovered revenue (ENRV)" | **CONSISTENT** across [00 § 4](00-project-charter.md), [README § C-5](README.md), [09](09-decision-engine.md), [11](11-counterfactual-engine.md), [37](37-metrics-dictionary.md) `M-10` |
| ENRV formula is identical | **CONSISTENT.** Formula in [README § C-5](README.md) matches [09](09-decision-engine.md) and [11](11-counterfactual-engine.md) |
| Primary metric is `M-10` | **CONSISTENT** across [21 § 1](21-evaluation.md), [37 § 2](37-metrics-dictionary.md), [20](20-benchmark.md), [27](27-judging-criteria-mapping.md) |
| "Do nothing" is a valid action | **CONSISTENT.** `NO_ACTION` documented in [05](05-functional-requirements.md) `RR-FUNC-040`, [09](09-decision-engine.md), [14](14-stopping-rules.md) § 5, [35b](35b-additional-decision-specifications.md) § 6 |

---

## 3. Challenge interpretation and scope

| Check | Result |
|---|---|
| Track 03 brief is reproduced verbatim | **CONSISTENT.** [01 § 1](01-track-alignment.md) contains the verbatim brief |
| Four risk classes named consistently | **CONSISTENT.** `PAYMENT_FAILURE`, `CHECKOUT_ABANDONMENT`, `SUBSCRIPTION_FAILURE`, `RECEIVABLE_OVERDUE` in [05](05-functional-requirements.md), [07](07-system-architecture.md), [08](08-agent-architecture.md), [12](12-revenue-leakage-model.md), [19](19-synthetic-dataset.md) |
| Scope boundaries respected | **CONSISTENT.** [03](03-scope-boundaries.md) defines the firewall; no new document introduces out-of-scope functionality |

---

## 4. Terminology

| Term | Canonical source | Used consistently? |
|---|---|---|
| `RevenueOpportunity` | [17](17-data-model.md) | **YES** |
| `ActionCandidate` | [17](17-data-model.md) | **YES** |
| `Decision` | [17](17-data-model.md) | **YES** |
| `Intervention` | [17](17-data-model.md) | **YES** |
| `Outcome` | [17](17-data-model.md) | **YES** |
| `AuditEvent` | [16](16-audit-trail.md), [17](17-data-model.md) | **YES** |
| `Diagnosis` | [17](17-data-model.md) | **YES** |
| `ContextObject` | [08](08-agent-architecture.md) C-04 | **YES** |
| `PolicyPack` | [13](13-policy-and-guardrails.md) | **YES** |
| `StrategyVersion` | [08](08-agent-architecture.md) C-21 | **YES** |
| `RecoveryCycle` | [07](07-system-architecture.md) | **YES** |
| `GateVerdict` | [13](13-policy-and-guardrails.md) | **YES** |
| `ENRV` | [README § C-5](README.md) | **YES** |
| `uplift` (`u`) | [README § C-5](README.md) | **YES** |

---

## 5. Entity and state names

| Check | Result |
|---|---|
| Opportunity states match [34](34-state-machine.md) | **CONSISTENT.** 14 states used consistently: `DETECTED`, `NOT_ADDRESSABLE`, `DIAGNOSED`, `PRICED`, `AWAITING_APPROVAL`, `AUTHORISED`, `ACTING`, `AWAITING_OUTCOME`, `RECONCILING`, `RECONCILIATION_FAILED`, `DEFERRED`, `NO_ACTION_CYCLE`, `RECOVERED`, `STOPPED`, `CLOSED_UNRECOVERED` |
| Intervention states match [34](34-state-machine.md) | **CONSISTENT** |
| ApprovalRequest states match [34](34-state-machine.md) | **CONSISTENT** |
| ReservationHandle states match [34](34-state-machine.md) | **CONSISTENT** |
| State count | **NOTE:** [34 § 1.1](34-state-machine.md) says "Fourteen states" but lists 15 state names (including `CLOSED_UNRECOVERED`). **Count inconsistency (minor)**. Resolution: count 15 states; text should say "Fifteen states" |

---

## 6. Metrics

| Check | Result |
|---|---|
| Metric names match [37](37-metrics-dictionary.md) | **CONSISTENT** across [21](21-evaluation.md), [24](24-observability.md), [26](26-demo-script.md), [27](27-judging-criteria-mapping.md) |
| Tier membership matches [37 § 0](37-metrics-dictionary.md) | **CONSISTENT** |
| `M-10` definition is paired difference | **CONSISTENT** across [37](37-metrics-dictionary.md), [21](21-evaluation.md), [20](20-benchmark.md) |
| `M-14` description | **NOTE:** [README § C-5](README.md) references `M-14 Wasted Intervention Rate` but [37](37-metrics-dictionary.md) defines `M-14` as "Guardrail-block profile". **INCONSISTENCY FOUND** |

### Inconsistency I-01: M-14 name mismatch

| Source | Name |
|---|---|
| [README § C-5](README.md) | "M-14 Wasted Intervention Rate" |
| [37-metrics-dictionary.md](37-metrics-dictionary.md) | "M-14 Guardrail-block profile" |

**Authority:** [37-metrics-dictionary.md](37-metrics-dictionary.md) is the authoritative source for metric definitions.

**Resolution:** [README § C-5](README.md) contains a stale reference. The correct name is "Guardrail-block profile". The concept of "wasted interventions" is covered by `M-23 Wasted spend`. The README should be corrected during implementation.

---

## 7. Agent responsibilities

| Check | Result |
|---|---|
| Module roster matches [08](08-agent-architecture.md) | **CONSISTENT.** 3 agents + 18 deterministic modules |
| Permission model in [08 § 7](08-agent-architecture.md) is respected in new documents | **CONSISTENT.** [22](22-security-and-privacy.md), [23](23-failure-recovery.md), [24](24-observability.md) reference the same permissions |
| No new document grants a module capability outside [08 § 7](08-agent-architecture.md) | **CONSISTENT** |

---

## 8. Guardrails and stopping rules

| Check | Result |
|---|---|
| 12 gates named consistently | **CONSISTENT** across [05](05-functional-requirements.md), [13](13-policy-and-guardrails.md), [30](30-test-plan.md), [22](22-security-and-privacy.md) |
| Gate evaluation order G1…G12 | **CONSISTENT** |
| 11 stopping rules SR-01…SR-11 | **CONSISTENT** across [14](14-stopping-rules.md), [05](05-functional-requirements.md), [34](34-state-machine.md), [30](30-test-plan.md) |
| Stopping-rule semantics (terminal vs re-openable) | **CONSISTENT** |
| "Silence is never consent" for approvals | **CONSISTENT** across [14](14-stopping-rules.md) SR-06, [13](13-policy-and-guardrails.md) G7, [08](08-agent-architecture.md) C-15 |

---

## 9. Audit fields

| Check | Result |
|---|---|
| Audit event schema matches [16](16-audit-trail.md) | **CONSISTENT** |
| Hash chain algorithm (SHA-256) | **CONSISTENT** across [16](16-audit-trail.md), [22](22-security-and-privacy.md) |
| PII exclusion (never-log list) | **CONSISTENT** across [16](16-audit-trail.md), [22](22-security-and-privacy.md), [19](19-synthetic-dataset.md) |
| `RR-AUDIT-010` blocking rule | **CONSISTENT** across [16](16-audit-trail.md), [13](13-policy-and-guardrails.md), [23](23-failure-recovery.md), [22](22-security-and-privacy.md) |

---

## 10. Benchmark methodology

| Check | Result |
|---|---|
| Baselines B0–B6 described consistently | **CONSISTENT** between [20](20-benchmark.md) and [27](27-judging-criteria-mapping.md) |
| Falsification conditions F-1…F-6 | **CONSISTENT** |
| Multi-seed requirement (≥ 20) | **CONSISTENT** between [00 § 9](00-project-charter.md), [20](20-benchmark.md), [21](21-evaluation.md) |
| Paired comparison with CI | **CONSISTENT** |

---

## 11. UI terminology

| Check | Result |
|---|---|
| Seven screens named consistently | **CONSISTENT** across [05 § 8](05-functional-requirements.md), [25](25-ui-ux-spec.md), [26](26-demo-script.md), [24](24-observability.md) |
| Screen numbering | **CONSISTENT** |

---

## 12. Requirement IDs

| Check | Result |
|---|---|
| ID blocks defined in [05](05-functional-requirements.md) | **CONSISTENT** |
| No ID collisions | **CONSISTENT** — each ID appears in exactly one row |
| IDs used consistently across documents | **CONSISTENT** — spot-checked across [30](30-test-plan.md), [33-requirement-traceability](33-requirement-traceability.md), [27](27-judging-criteria-mapping.md) |

---

## 13. API and data model concepts

| Check | Result |
|---|---|
| Entity names match [17](17-data-model.md) | **CONSISTENT** |
| ID prefixes match [README § C-4](README.md) | **CONSISTENT** |
| API contracts in [18](18-api-contracts.md) consistent with data model | **CONSISTENT** |
| No new document invents an unverified Razorpay API | **CONSISTENT.** All Razorpay API references are marked `UNVERIFIED` and point to [36-razorpay-integration-assumptions.md](36-razorpay-integration-assumptions.md) |

---

## 14. Cross-document references

| Check | Result |
|---|---|
| [README](README.md) references to future documents (22–32) | **NOW CONSISTENT.** All referenced documents exist |
| [00-project-charter.md](00-project-charter.md) references | **NOTE:** References `36-razorpay-integration-assumptions.md`, `29-tradeoffs.md`, `31-decision-records.md`, `38-traceability-matrix.md`, `40-open-questions.md` — all exist |
| [05-functional-requirements.md](05-functional-requirements.md) references | **CONSISTENT** — references to [30](30-test-plan.md), [25](25-ui-ux-spec.md), [24](24-observability.md) now resolve |

---

## 15. Data requirements

| Check | Result |
|---|---|
| No new document requires data absent from [19](19-synthetic-dataset.md) | **CONSISTENT.** New documents ([22](22-security-and-privacy.md)–[36b](36b-documentation-consistency-check.md)) reference the existing data model and synthetic dataset |
| Privacy canaries documented | **CONSISTENT** in [19](19-synthetic-dataset.md) DS-10, [22](22-security-and-privacy.md) § 1.1, [30](30-test-plan.md) T-SAF-009 |

---

## 16. Document numbering conflicts

| Number | Original file | New file | Resolution |
|---|---|---|---|
| 33 | `33-not-a-clone.md` (architectural differentiation) | `33-requirement-traceability.md` (traceability framework) | **Both retained.** They serve different purposes. `33-not-a-clone.md` is a positioning document; `33-requirement-traceability.md` is a traceability framework. No content overlap |
| 35 | `35-learning-engine.md` (learning engine spec) | `35b-additional-decision-specifications.md` (cross-module decision gaps) | **`35b` used.** The learning engine is a module spec; additional decision specifications fill cross-module gaps. No duplication |
| 36 | `36-razorpay-integration-assumptions.md` (Razorpay API assumptions) | `36b-documentation-consistency-check.md` (this document) | **`36b` used.** Completely different purposes |

---

## 17. Inconsistency summary

| ID | Inconsistency | Source A | Source B | Authority | Proposed resolution | Severity |
|---|---|---|---|---|---|---|
| I-01 | `M-14` name mismatch | [README § C-5](README.md): "Wasted Intervention Rate" | [37](37-metrics-dictionary.md): "Guardrail-block profile" | [37](37-metrics-dictionary.md) | Correct README reference during implementation | LOW — cosmetic |
| I-02 | Opportunity state count | [34 § 1.1](34-state-machine.md): "Fourteen states" | [34 § 1.1](34-state-machine.md) table: 15 rows | Table (15 rows is correct) | Update text to "Fifteen states" during implementation | LOW — cosmetic |

No HIGH or CRITICAL inconsistencies were found. The documentation package is internally consistent
on all material points: product identity, objective, scope, architecture, permissions, guardrails,
stopping rules, metrics, state machine semantics, and requirement IDs.

---

## 18. Documents requested but not created

| Requested name | Reason | Resolution |
|---|---|---|
| `35-additional-decision-specifications.md` | Slot occupied by `35-learning-engine.md` | Created as `35b-additional-decision-specifications.md` |
| `36-documentation-consistency-check.md` | Slot occupied by `36-razorpay-integration-assumptions.md` | Created as `36b-documentation-consistency-check.md` (this document) |

These naming decisions do not affect content or traceability. Both documents are referenced
correctly from the README and from other documents that link to them.
