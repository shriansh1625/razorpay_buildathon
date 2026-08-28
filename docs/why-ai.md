# Why AI is in PAYVANTA — and what actually shipped

Track 03 is **AI Revenue Recovery**. This document states the implemented
architecture without dressing deterministic code as an LLM.

---

## 1. What is actually AI in this submission?

**Not a chat model. Not two LLM agents.**

The shipped intelligence is a **decision system**:

| Stage | Mechanism | LLM? |
|---|---|---|
| Detect revenue at risk | Deterministic Revenue Sentinel | No |
| Diagnose cause | Deterministic taxonomy ranking (`rank_causes`) | No — `llm_used=False`, `allow_llm=False` |
| Generate candidates | Deterministic rule table | No |
| Compare interventions | Deterministic counterfactual ENRV | No |
| Select under scarcity | Deterministic Lagrangian allocator | No |
| Guard / stop / authorize | Deterministic PolicyPack gates | No |
| Execute | Bounded adapters, simulated in sandbox | No |
| Measure / audit | Deterministic attribution + journal | No |
| Official benchmark | `llm_mode=LLM_OFF` | No |

Copy Composer (spec C-10) is **not implemented**. There is no chatbot, no
`llm_used=true`, no external model credentials.

The word **agentic** applies only to **bounded orchestration**: a fixed cycle
that cannot skip GUARD, cannot call adapters without AUTHORIZED, and cannot
retry a financial action without a fresh gate pass.

---

## 2. Why this is still an AI recovery system

“AI” here is **decision intelligence under uncertainty**, not a language model.

Recovery is not a static rule of the form “if failed payment then retry.”

- Natural recovery exists. Contacting someone who would have paid anyway
  destroys value (fatigue, cost). The system scores **uplift**, not conversion.
- Capacity is scarce. The next SMS cannot be assigned without comparing the
  whole batch. That is a portfolio optimisation, not an if-statement.
- Causes are noisy. Observable proxies are not latent `intent_to_pay`. Diagnosis
  ranks a taxonomy; it does not invent a new action class.
- Interventions are counterfactual. ENRV asks what happens **versus doing
  nothing**, then subtracts cost.
- Safety is non-negotiable. No diagnostic label may move money. Gates, stopping
  rules, and authorization sit **after** intelligence and cannot be bypassed.

A static retry schedule is baseline **B1**. Contact-everyone is **B2**. Greedy
scoring without allocation is **B3**. PAYVANTA’s REVIVE policy is the constrained
allocator plus gates. That comparison is the official experiment.

---

## 3. Where context / diagnosis helps

Diagnosis turns a raw failure into a **cause ranking** the candidate generator
can consume. Unmapped reasons fall through to `UNCLASSIFIED` rather than
hallucinating a cause. The spec allowed an optional LLM residual for free-text
reasons. **That residual is not on.** The deterministic map is the production
path of this submission, including the official benchmark.

---

## 4. Where candidate generation helps

Candidates are a **closed action catalogue** (retry, remind, incentive, escalate,
defer, no-action). Feasibility filters by instrument health, channel, policy, and
horizon. This is not open-ended tool use. An LLM that invented a new action
would be a safety defect.

---

## 5. What cannot reasonably be replaced by one static rule

- Batch allocation under shared budgets (Lagrangian / shadow prices)
- Counterfactual ENRV versus natural recovery
- Stopping rules that override a high ENRV
- Idempotent execution after authorization
- Paired M-10 measurement against B0

Those are the product. They are implemented as code, tested, and evaluated
across 600 official cells — not as a prompt.

---

## 6. What remains deterministic for safety

Everything that can move money:

authorization → reservation → adapter → measurement → audit.

Invariant: **no LLM output becomes a number that moves money.** In this
build the invariant holds vacuously: no LLM output exists.

---

## 7. Preferred control flow (implemented)

```
signals
  → detection
  → diagnosis / proposal          (deterministic intelligence)
  → candidate set
  → counterfactual / economics
  → deterministic policy
  → guardrails
  → authorization
  → bounded execution
  → measurement
  → audit
```

Intelligence proposes. Controls decide whether anything executes.

---

## 8. Why we did not bolt on a last-minute LLM

Adding a live model would require credentials, nondeterminism, and a second
diagnosis path that the **frozen official experiment does not use**
(`LLM_OFF`). Faking `llm_used=true` would be a credibility failure.

The honest Track 03 story:

> PAYVANTA is an autonomous recovery **decision system**. It reasons over a
> batch with counterfactuals and constraints. It does not chat. It does not
> call an LLM in this submission. The official evidence was measured with
> LLM mode off.
