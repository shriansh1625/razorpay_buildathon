# 41 · Future Ideas

Ideas that have value but are **explicitly excluded from this build**. Every item here was
considered and parked because it does not satisfy the scope firewall
([03-scope-boundaries.md](03-scope-boundaries.md)) or exceeds the hackathon timebox.

> **Rule.** Nothing in this document may be built in the current phase unless it passes the
> scope-firewall procedure and is recorded as an ADR in [31](31-decision-records.md). Referencing
> a future idea does not make it in-scope.

---

## 1. Architecture extensions

| ID | Idea | Rationale for deferral | Prerequisite |
|---|---|---|---|
| FI-01 | **Fast-lane cycle for checkout abandonment** | Checkout decay is fast (minutes to hours). A shorter cycle interval for this class would reduce staleness. Deferred because it adds cycle-scheduling complexity | Stable cycle model |
| FI-02 | **Event-driven hybrid** | Continuous signal processing with periodic batch allocation. Would eliminate the worst-case wait of one full cycle | Stable batch model; proven allocation benefit |
| FI-03 | **Multi-tenant architecture** | Serve multiple merchants from one deployment with tenant isolation | Production deployment goal |
| FI-04 | **Distributed allocator** | Partition the allocation problem for larger batches using column generation or branch-and-price | Batch sizes exceeding single-thread Lagrangian performance |
| FI-05 | **Real-time dashboard with WebSocket push** | Replace per-cycle polling with live updates | Stable UI; production deployment |

---

## 2. ML and prediction

| ID | Idea | Rationale for deferral | Prerequisite |
|---|---|---|---|
| FI-06 | **Gradient-boosted tree predictor** | Replace the Bayesian cell model with a more expressive model trained on real historical data | Real training data; sufficient volume per cell |
| FI-07 | **Thompson sampling for exploration** | Replace the fixed exploration fraction with a principled exploration strategy | Stable cell model; calibration validation |
| FI-08 | **Contextual bandit for action selection** | Learn action-context interactions beyond the cell model | Real deployment with feedback loop |
| FI-09 | **Causal inference from observational data** | Estimate uplift from non-experimental data using instrumental variables or doubly-robust estimation | Real data with natural variation in treatment |
| FI-10 | **Dynamic causal graph for leakage model** | Learn cause-effect relationships dynamically rather than using a fixed taxonomy | Larger dataset; causal discovery research |

---

## 3. Communication and channels

| ID | Idea | Rationale for deferral | Prerequisite |
|---|---|---|---|
| FI-11 | **Hinglish voice recovery** | Track 03 example direction. Voice adds telephony complexity, Hinglish speech synthesis, and call orchestration | P0 stable; voice provider selected |
| FI-12 | **Multi-language support** | Templates in regional languages beyond English and Hindi | Translator integration; template QA per language |
| FI-13 | **Rich messaging (WhatsApp interactive)** | Buttons, carousels, quick replies in WhatsApp recovery messages | WhatsApp Business API verified; template approval |
| FI-14 | **Personalised message timing** | Learn per-customer optimal send times from open/click data | Real communication data; privacy review |
| FI-15 | **Promise-to-pay tracking** | Capture and track customer commitments to pay by a specific date | P0 stable; UI for promise capture |

---

## 4. Razorpay integration

| ID | Idea | Rationale for deferral | Prerequisite |
|---|---|---|---|
| FI-16 | **Live Razorpay API integration** | Replace simulated adapters with real API calls | Razorpay API access; verification of all assumptions in [36](36-razorpay-integration-assumptions.md) |
| FI-17 | **Razorpay webhook consumer** | Real-time event ingestion from Razorpay webhooks | API access; webhook secret management |
| FI-18 | **Smart Collect integration** | Use Razorpay Smart Collect for virtual-account-based recovery | Product availability verification |
| FI-19 | **Razorpay dashboard embedding** | Embed REVIVE screens in the Razorpay merchant dashboard | Razorpay partnership or plugin framework |
| FI-20 | **Multi-gateway support** | Support merchants using multiple payment gateways (not just Razorpay) | Gateway-agnostic adapter interface |

---

## 5. Compliance and production readiness

| ID | Idea | Rationale for deferral | Prerequisite |
|---|---|---|---|
| FI-21 | **TRAI DND compliance** | Check the Do Not Disturb registry before sending SMS | TRAI API access; legal review |
| FI-22 | **RBI notification compliance** | Comply with RBI mandate debit notification requirements | RBI guidelines verified; legal review |
| FI-23 | **GDPR/DPDP consent management** | Full consent lifecycle with opt-out, data deletion, and portability | Legal review; production deployment |
| FI-24 | **SOC 2 audit trail** | Harden the audit trail for compliance certification | Production deployment; security audit |
| FI-25 | **Multi-currency support** | Handle merchants with non-INR transactions | Currency conversion model; `C-2` convention change |

---

## 6. Evaluation and measurement

| ID | Idea | Rationale for deferral | Prerequisite |
|---|---|---|---|
| FI-26 | **A/B testing framework** | Run REVIVE vs a baseline on real traffic with statistical significance | Production deployment; real traffic |
| FI-27 | **Continuous calibration monitoring** | Track predictor calibration in production across time | Production deployment; drift detection |
| FI-28 | **Merchant-specific benchmarking** | Generate synthetic data calibrated to a specific merchant's characteristics | Merchant onboarding; data sharing agreement |
| FI-29 | **Counterfactual estimation from production data** | Estimate what would have happened without intervention using propensity scoring | Sufficient production data; causal inference expertise |

---

## 7. Product features

| ID | Idea | Rationale for deferral | Prerequisite |
|---|---|---|---|
| FI-30 | **Merchant self-service policy editor** | UI for merchants to configure policy packs without engineering | Stable policy model; validation layer |
| FI-31 | **Recovery playbooks** | Pre-configured strategy templates for common merchant types | Validated strategies; merchant segmentation |
| FI-32 | **Customer communication preferences** | Per-customer channel and timing preferences learned from interaction data | Real interaction data; privacy model |
| FI-33 | **Revenue forecasting** | Predict future revenue leakage from current trends | Historical data; time-series model |
| FI-34 | **Competitive benchmarking** | Compare REVIVE performance against other recovery products | Market data; standardised evaluation protocol |

---

## 8. Summary

| Category | Count |
|---|---|
| Architecture extensions | 5 |
| ML and prediction | 5 |
| Communication and channels | 5 |
| Razorpay integration | 5 |
| Compliance and production readiness | 5 |
| Evaluation and measurement | 4 |
| Product features | 5 |
| **Total** | **34** |

None of these ideas are in scope for this build. They are listed to demonstrate that the
specification authors considered them and deliberately excluded them, not that they were
overlooked.
