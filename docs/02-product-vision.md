# 02 · Product Vision

---

## 1. One line

**REVIVE is a revenue recovery autopilot: it decides where a merchant's next unit of recovery
effort should go, executes it within hard limits, and proves what it earned.**

---

## 2. The insight the product is built on

Most recovery tooling answers a *local* question: given this failed payment, what should we do?

That question has a comfortable answer — retry it, message the customer, maybe offer a discount —
and the answer is almost always "do something". Tools built this way converge on the same
behaviour: act on everything, as often as policy allows, and count gross recoveries as wins.

Two facts make that behaviour economically wrong.

**Fact one: a large share of at-risk revenue recovers by itself.** Customers retry their own
payments. Abandoned carts get completed the next evening. Invoices get paid on the buyer's own
accounts-payable cycle. Acting on those customers produces a recovery you would have got anyway,
at full cost. Gross-recovery metrics are blind to this; they credit the tool for the customer's own
behaviour.

**Fact two: effort is a shared, exhausted resource.** SMS credits, incentive budget, voice minutes,
retry slots on a payment rail, human chase capacity, and the customer's own tolerance for being
contacted — all finite, all consumed by whichever opportunity gets there first. A local decision
engine spends these resources in arrival order. Arrival order has no relationship to value.

Put those together and the real question emerges:

> Given everything currently at risk, and given what I can afford to do, **which opportunities
> deserve which action** — and which deserve nothing at all?

That is a portfolio allocation problem under constraints. REVIVE is built around it.

---

## 3. Product thesis

REVIVE treats revenue recovery as **constrained decision-making over a portfolio**, evaluated on
**incremental** value.

Three commitments follow, and they define the product:

### 3.1 Uplift, not conversion

REVIVE's unit of value is the *difference* between what happens with an action and what would have
happened without it:

```
uplift = P(recover | action) − P(recover | no action)
```

A customer with a 90% chance of self-recovering is a bad target even though acting on them looks
like a 92% success story. A customer with a 20% baseline who jumps to 55% with the right nudge is
where the money is. This single choice is what separates REVIVE from a recovery blaster, and it is
enforced all the way through to the metrics.

### 3.2 Allocation, not workflow

REVIVE does not run one workflow per event. It runs a **recovery cycle**: it looks at everything
currently at risk, prices every feasible action, and solves for the best feasible bundle under all
active constraints simultaneously. Opportunities compete. Losing opportunities are explicitly
deferred with a reason, not silently dropped.

### 3.3 Boundedness as a feature, not a compliance tax

Limits are not obstacles that the intelligence works around; they are the environment the
intelligence reasons inside. A recommendation that violates a limit is not a good recommendation
that got blocked — it is a bad recommendation. The guardrail engine is deterministic and has final
authority precisely so that the reasoning layer can be creative without being dangerous.

---

## 4. The primary differentiator

# Recovery allocation under constraints

REVIVE models the merchant as holding a set of exhaustible recovery resources:

| Resource | Unit | Why it binds |
|---|---|---|
| Incentive / discount budget | paise | Directly reduces margin; capped per cycle and per period |
| Communication capacity | messages per channel | Per-message cost; provider rate limits; consent windows |
| Voice capacity | call-minutes | Expensive; small pool; human-adjacent |
| Retry capacity | attempts per instrument, per cycle | Rails have limits; excessive retries damage authorisation rates |
| Human review capacity | operator slots per cycle | Approval and escalation are the scarcest resource of all |
| Customer contact tolerance | contacts per customer per window | Not a merchant resource but a customer one; exhausting it destroys future value |

And it solves:

> **Maximise expected incremental net recovered revenue, subject to all resource capacities, all
> merchant policy limits, all consent and contact constraints, all stopping rules, and all approval
> thresholds.**

Everything else in the product — detection, diagnosis, counterfactual pricing, execution, audit,
learning — exists to make that one decision well and to prove it was made well.

---

## 5. The loop (frozen)

```
   ┌──────┐   ┌────────────┐   ┌──────────┐   ┌────────────┐
   │ SEE  │──▶│ UNDERSTAND │──▶│ SIMULATE │──▶│ PRIORITIZE │
   └──────┘   └────────────┘   └──────────┘   └─────┬──────┘
                                                    │
   ┌──────┐   ┌────────┐   ┌─────┐   ┌───────┐      │
   │LEARN │◀──│ VERIFY │◀──│ ACT │◀──│ GUARD │◀─────┘
   └──┬───┘   └────────┘   └─────┘   └───────┘
      │                                   ▲
      └───── updates predictors ──────────┘
             (never updates policy limits)
```

| Phase | Question it answers | Owner module | Output |
|---|---|---|---|
| **SEE** | What revenue is at risk right now, and how much of it? | Revenue Sentinel | `RevenueOpportunity` with `value_at_risk_paise` |
| **UNDERSTAND** | Why is it at risk, and what is the customer's state? | Enricher + Root Cause Analyst | `Diagnosis` with ranked candidate causes and evidence refs |
| **SIMULATE** | For each feasible action, what happens — and what happens if we do nothing? | Candidate Generator + Predictor + Counterfactual Evaluator | `ActionCandidate` rows with `p`, `uplift`, `cost`, `ENRV`, `confidence` |
| **PRIORITIZE** | Given everything at risk and everything we can afford, what is the best feasible bundle? | Recovery Allocator | `Decision` set with selected / deferred / rejected + reasons |
| **GUARD** | Is each selected action permitted, affordable, consented, non-duplicate, and within limits? | Policy Engine | `ALLOW` / `ALLOW_WITH_MODIFICATION` / `DEFER` / `DENY` / `REQUIRE_APPROVAL` |
| **ACT** | Execute exactly the approved action, exactly once. | Execution Agent | `Intervention` with idempotency key and adapter result |
| **VERIFY** | Did money actually arrive, and was it attributable? | Outcome Observer | `Outcome` with `recovered_amount_paise` and attribution class |
| **LEARN** | What should we believe differently next cycle? | Learning Engine | Updated `StrategyVersion` predictor parameters |

The loop is frozen. A component that does not belong to exactly one phase does not belong in the
system. See [07-system-architecture.md](07-system-architecture.md).

---

## 6. "Do nothing" is a first-class decision

REVIVE must be able to conclude, for a specific opportunity, with a recorded reason:

> No intervention is economically justified.

This is a product principle, not a fallback. It exists because the objective is value, not
activity. `NO_ACTION` is always in the candidate set, always priced (at `ENRV = 0` by definition),
and it wins whenever no other candidate clears the threshold `ε` under the current constraints.

Circumstances where `NO_ACTION` is the correct answer:

| Situation | Why no action wins |
|---|---|
| Expected uplift × value is smaller than the cheapest action's cost | `ENRV < 0` for every candidate |
| Natural recovery probability is high | Uplift is near zero even if `p(action)` is high |
| Customer has already been contacted twice this window | Fatigue term dominates; also likely gated |
| Failure reason is `RISK_BLOCKED` | Retrying is unsafe and messaging is pointless |
| The recovery window has effectively closed | `p` has decayed below usefulness |
| Budget is exhausted and this opportunity is not competitive | Deferred rather than acted, with a reason |
| Timing is wrong (quiet hours, pre-salary-cycle) | Waiting one cycle strictly dominates acting now |

**The anti-abuse rule.** `NO_ACTION` must never become a way to look safe by doing nothing. It is
measured: the evaluation reports `M-15 No-Action Share` alongside `M-19 Missed Opportunity Value`
— the value REVIVE declined to pursue that the oracle shows was recoverable profitably. A policy
that does nothing scores zero incremental recovery and fails `SC-8`. Inaction is only defensible
when the numbers defend it.

---

## 7. What REVIVE is not

| REVIVE is not | Because |
|---|---|
| A chatbot | Nothing in the product requires conversation with the merchant to work |
| An LLM wrapper | The money-affecting decisions are deterministic; the LLM reasons and explains, it does not price |
| A notification system | Messaging is one of fifteen actions and often the wrong one |
| A retry engine | Retry is one action; choosing *not* to retry is frequently the contribution |
| A fraud detector | Different objective, different data, different track |
| A merchant analytics dashboard | The UI exposes decisions and outcomes, not exploratory charts |
| A CRM | No relationship management, no pipeline, no contact database as the product |
| A generic autonomous-agent demo | Agents exist only where they have measurable output and bounded authority |
| An AI message generator | Copy generation is a leaf capability, not the value |
| A voice bot | Voice is a bounded channel; see [01-track-alignment.md § 4](01-track-alignment.md) |
| A multi-agent architecture in search of a problem | Every module must justify itself against `RR-FUNC-*` |

Detailed architectural differentiation: [33-not-a-clone.md](33-not-a-clone.md).

---

## 8. Users

`ASSUMPTION` — REVIVE is specified for a mid-market Indian merchant with meaningful volume across
one-time payments, subscriptions, and B2B invoices. Personas below are design targets, not
research findings.

| Persona | Needs from REVIVE | Primary screen |
|---|---|---|
| **Revenue / growth owner** | How much is at risk, how much came back, was it worth it | Executive Revenue Command Center |
| **Finance controller** | Budget consumption, incentive spend, ROI, receivables ageing | Recovery Allocation View |
| **Risk / compliance reviewer** | Proof that limits held; every action justified and logged | Audit Trail |
| **Operations agent** | The approval queue; which cases need a human and why | Approval Queue (part of Recovery Opportunities) |
| **Engineer / judge** | Does the decision logic beat a baseline, reproducibly | Benchmark / Evaluation Lab |

The system is designed to be **supervisable**: a human can always see what REVIVE decided, what it
rejected, and why — and can always stop it. See [25-ui-ux-spec.md](25-ui-ux-spec.md).

---

## 9. Value proposition, stated honestly

What REVIVE can credibly claim after this build:

- A specified, implemented decision architecture for constrained revenue recovery.
- A reproducible benchmark showing its allocation policy beats non-trivial baselines **on a
  synthetic environment whose behavioural model is fully documented**.
- Zero policy violations and a verifiable audit chain across that benchmark.
- An explicit accounting of where it wasted effort and where it fell short of the oracle.

What REVIVE **cannot** claim after this build, and must never imply:

- Any real-world recovery rate, or that the synthetic uplift numbers transfer to live traffic.
- Any verified integration with Razorpay or any payment provider.
- Production readiness, regulatory compliance, or safety for real money.
- Causal identification. The system reasons over *candidate* causes and *modelled* uplift; it does
  not run experiments on real customers and does not establish causation.

The gap between those two lists is the honest boundary of the project, and
[21-evaluation.md](21-evaluation.md) § 8 makes stating it a hard requirement of every report.

---

## 10. The sentence the product must survive

If a judge asks one hostile question, it will be some form of:

> "Isn't this just a smarter retry-and-remind loop with a dashboard on top?"

The answer REVIVE must be able to give, with artefacts on screen:

> No. A retry-and-remind loop acts on each event independently and counts gross recoveries. REVIVE
> prices every action by *uplift over doing nothing*, makes opportunities compete for a fixed
> budget under six simultaneous constraints, chooses no-action on a measurable share of cases,
> refuses actions its policy engine forbids rather than routing around them, and reports the
> incremental money it earned over a baseline across twenty seeds with a confidence interval —
> including the cases where it was wrong. Here is the allocation view, here is the shadow price on
> the binding constraint, and here is the audit chain for the action you just watched execute.

Every clause in that answer is a requirement elsewhere in this package. If any clause becomes
unsupportable, the product has lost its differentiator and the build must be corrected, not the
pitch.
