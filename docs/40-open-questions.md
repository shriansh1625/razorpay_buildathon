# 40 · Open Questions

Items labelled `UNKNOWN — MUST BE DECIDED DURING IMPLEMENTATION` across the documentation
package. These are not gaps in the specification — they are explicit acknowledgements that
the decision requires information or experimentation that was not available during the
specification phase.

> **Rule.** When an implementation decision resolves an open question, record the decision in
> [31-decision-records.md](31-decision-records.md) as an ADR and update this document.

---

## 1. Decision-required items

| # | Question | Source document | Impact area | Constraint | Proposed default | Priority |
|---|---|---|---|---|---|---|
| OQ-01 | What is the ENRV threshold `ε` (minimum justification)? | [09](09-decision-engine.md), [35b § 5.1](35b-additional-decision-specifications.md) | Allocation — how many actions are economically justified | Must be ≥ 0 paise; higher = more conservative | `0` paise (any positive ENRV justifies action) | P0 |
| OQ-02 | What are the G7 approval thresholds (`approval_value_threshold`, `approval_uncertainty_threshold`)? | [13](13-policy-and-guardrails.md) G7, [35b § 5.2](35b-additional-decision-specifications.md) | Autonomy boundary — what requires human approval | Must be finite and positive | `PROPOSED`: value > ₹5000 or interval width / ENRV > 0.5 | P0 |
| OQ-03 | What are the recovery window lengths per risk class? | [35b § 10](35b-additional-decision-specifications.md), [05](05-functional-requirements.md) | Stopping — when opportunities time out | Must be frozen before measurement | `PROPOSED`: checkout 48h, payment 14d, subscription 14d, receivable 90d | P0 |
| OQ-04 | What is the `near-zero denominator` threshold for `RR-METRIC-008`? | [37 § 10](37-metrics-dictionary.md) | Metrics — when a ratio is undefined | Must prevent division artifacts | `PROPOSED`: denominator < 1 paise | P0 |
| OQ-05 | What is the prior weight for the Bayesian cell model? | [35 § 2.2](35-learning-engine.md) | Learning — strength of the prior | Must be > 0; higher = more weight on prior | `PROPOSED`: 10 pseudo-observations | P1 |
| OQ-06 | What is the minimum observation count for shrinkage (`min_obs`)? | [35 § 2.4](35-learning-engine.md) | Learning — when to shrink toward parent cell | Must be > 0 | `PROPOSED`: 20 | P1 |
| OQ-07 | What is the exploration budget fraction? | [35 § 5.2](35-learning-engine.md) | Learning — how much budget is reserved for exploration | Must be in (0, 1); too high wastes budget; too low starves learning | `PROPOSED`: 0.05 (5%) | P1 |
| OQ-08 | What is the calibration regression threshold for rollback? | [35 § 4.3](35-learning-engine.md) | Learning — when to rollback a strategy version | Must be defined in terms of Brier score or ECE delta | No proposed default | P1 |
| OQ-09 | What are the calibration bin edges for `M-24`? | [37 § 10](37-metrics-dictionary.md) | Evaluation — how the reliability curve is binned | Must be frozen before measurement | `PROPOSED`: equal-width deciles | P1 |
| OQ-10 | Should `M-13` count non-contact actions in a separate denominator? | [37 § 10](37-metrics-dictionary.md) | Metrics — what counts as a "contact" | Affects the contact-efficiency metric | `PROPOSED`: yes, reported separately | P1 |
| OQ-11 | Should `M-25` use decile lift or a Qini-style curve? | [37 § 10](37-metrics-dictionary.md) | Evaluation — uplift ranking quality measure | Affects interpretability vs rigour | `PROPOSED`: decile lift, for interpretability | P1 |
| OQ-12 | What is the billing currency for `M-49` (LLM cost)? | [37 § 10](37-metrics-dictionary.md) | Metrics — LLM cost reporting | Must be unambiguous | `PROPOSED`: provider's billing currency, unconverted | P1 |
| OQ-13 | Should `M-21`'s `unobservable_rate` gate reporting of `M-06`? | [37 § 10](37-metrics-dictionary.md) | Metrics — whether attributed recovery is suppressed when observation is poor | Affects report structure | `PROPOSED`: no, but printed adjacently | P1 |
| OQ-14 | What is the pacing factor default? | [35b § 8.2](35b-additional-decision-specifications.md) | Allocation — how budget is distributed across cycles | Must be > 0; 1.0 = even pacing | `PROPOSED`: 1.0 | P1 |
| OQ-15 | What are the cycle interval values for different profiles? | [07 § 1.2](07-system-architecture.md) | Architecture — cycle timing | Must be frozen before measurement | `PROPOSED`: 15 minutes virtual time (all profiles) | P0 |

---

## 2. Resolution process

1. Implementer encounters an open question during development
2. Implementer proposes a value with rationale
3. If the question has a `PROPOSED` default, the default may be used without approval
4. If no default exists, the question is escalated to the product owner
5. The decision is recorded as an ADR in [31](31-decision-records.md) citing this document
6. This document is updated: the `Proposed default` column is replaced with `DECIDED: [value]`
7. Sensitivity analysis is required for all numeric decisions (how much does the result change?)

---

## 3. Sensitivity requirements

For every numeric open question, the implementation must:
- Run the benchmark at the proposed default
- Run at ±50% of the proposed default (where meaningful)
- Report whether `M-10` changes materially
- Record the sensitivity result in the evaluation artefact

This prevents a numeric choice from silently determining the result.

---

## 4. Status summary

| Status | Count |
|---|---|
| Open (no proposed default) | 1 (OQ-08) |
| Open (with proposed default) | 14 |
| Decided | 0 |
| **Total** | **15** |
