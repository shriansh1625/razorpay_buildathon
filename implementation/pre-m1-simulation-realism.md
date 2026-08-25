# Pre-M1 Simulation Realism Audit

**Question:** Is the synthetic environment meaningful enough for the benchmark thesis?

**Verdict classification:** See §4

---

## 1. Required behavioral relationships (spec)

| Relationship | Spec mechanism | Present? |
|--------------|----------------|----------|
| Amount ↔ value at risk | DOMAIN orders/invoices → V(i) | Yes |
| Segment ↔ latent intent | `intent_to_pay` latent; noisy proxies | Yes (`19` §3) |
| Payment method ↔ retry success | `instrument_health_trajectory` | Yes |
| Failure type ↔ candidate actions | Rule table class×cause | Yes |
| Failure timing ↔ horizon/window | Virtual clock, H, SR-01 | Yes |
| Natural recovery ↔ high intent | Shared latent; CF-7 test | Yes (by construction) |
| Retry ↔ rail limits | retry_slots, G4, SR-03 | Yes |
| Communication ↔ responsiveness | `responsiveness{channel}` latent | Yes |
| Fatigue ↔ contact count | `annoyance_threshold`, fatigue_curve | Yes |
| Intervention cost ↔ ENRV | c(a), d, F in formula | Yes (params TBD) |
| Subscription ↔ mandate state | DOMAIN mandate/subscription | Yes |
| Overdue ↔ ageing buckets | Invoice ageing, SR-01 | Yes |
| Scarcity ↔ allocation | DS-4 constructed demand>capacity | Yes |
| Negative uplift possible | OR-4 harmful actions | Yes |
| Value vs recoverability anti-correlation | §5.2 deliberate | Yes (invented) |

---

## 2. Latent vs observable gap

**Strength:** Engine sees proxies only; oracle holds truth (`DS-11`–`13`). Prevents trivial calibration.

**Weakness:** Fidelity to real payments is **UNVERIFIED** — relationships are **designed**, not empirically validated.

---

## 3. Profile design

| Profile | Realism role |
|---------|--------------|
| BALANCED | Primary — mixed regimes |
| HIGH_NATURAL | Tests over-contacting penalty |
| SCARCE | Tests allocation + shadow prices |
| ABUNDANT | **Stress test of thesis** — should shrink allocator advantage |
| HOSTILE | Guardrail realism, not revenue |
| DEGRADED | Provider outage / drift |

Including ABUNDANT is **intellectual honesty**, not realism — it tests whether the benchmark can show null results.

---

## 4. Classification

### **PLAUSIBLE (with explicit synthetic caveat)**

**Not TOO EASY** because:

- DS-3 non-trivial natural recovery required  
- DS-4 scarcity required  
- OR-4 negative uplift required  
- OR-6 post-H recoveries required  
- Value/recoverability negative correlation challenges B4  
- Adversarial injections (`19` §6)  

**Not TOO HARD** because:

- Relationships are cooperative with REVIVE's model family (Beta-Binomial cells match generator structure)  
- Generator priors can align with oracle generative process if engineered carefully — **risk of circularity** if same team tunes both without freeze  

**Not UNDETERMINED** — spec is explicit about constructed correlations and limitations (`19` §5.2, §10).

**Cannot claim real-world realism** — only **internal coherence** for testing allocation-under-scarcity thesis.

---

## 5. Most important generator assumptions

| # | Assumption | If wrong in implementation |
|---|------------|----------------------------|
| G-1 | p(i,∅) has meaningful variance | Uplift thesis collapses (CF-7 fails) |
| G-2 | Demand for ENRV>0 actions exceeds capacity | Allocator untested; B2≈REVIVE |
| G-3 | Some high-V customers have high p∅ | Without this, CONTACT_ALL wins |
| G-4 | Fatigue can reduce recovery below natural | Fatigue term unfalsifiable |
| G-5 | Oracle coherent (no impossible successes) | ENRV unlearnable noise |
| G-6 | Latent traits not leaked to features | Cheating + trivial predictions |
| G-7 | `distributions.json` published | Reviewers cannot judge difficulty |

---

## 6. Circular tuning risk

If generator latent parameters and predictor priors are **co-tuned after seeing M-10**, benchmark becomes self-fulfilling.

**Defence:** `RR-BENCH-008` freeze; separate tune/eval seeds; report `unseen_cell_rate`, calibration M-24 even when weak.

---

## 7. Verdict

| Dimension | Rating |
|-----------|--------|
| Sufficient for hackathon thesis | **Yes** |
| Sufficient for production claims | **No** (explicit) |
| Environment class | **PLAUSIBLE (synthetic, constructed)** |

**M1 can proceed** — realism work peaks at **M2** when generator parameters are chosen and `distributions.json` is published.
