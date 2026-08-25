# Pre-M1 Benchmark Integrity Audit

**Question answered:** What prevents REVIVE from cheating?

---

## 1. Integrity mechanisms (spec-defined)

| Mechanism | Spec source | What it prevents |
|-----------|-------------|------------------|
| **Oracle partition isolation** | `19` OR-2,3,7; `17` §4.8; `AI-6`; `RR-BENCH-005` | Policy reading true outcomes before acting |
| **Oracle fixed at generation** | `19` OR-2 | Mid-run outcome mutation based on decisions |
| **Same dataset file for all policies** | `20` BF-1 | Regenerating easier world for REVIVE |
| **Same guardrails/stopping for all** | BF-2, BF-3 | Baselines unconstrained |
| **Same capacities, costs, H** | BF-4, BF-5, BF-6 | Handicapping baselines only |
| **Same execution engine** | BF-8 | Different outcome physics per policy |
| **Baselines not strawmen** | BF-9 | Weak B1 schedule |
| **No policy-specific outcome branches** | `32` IC-05; anti-pattern explicit in master prompt | `if policy==REVIVE: win` |
| **Paired per-seed M-10** | `20` §3.3 | Pooled cherry-picking |
| **All seeds reported** | `RR-BENCH-004`; `seeds_where_revive_lost` | Seed selection bias |
| **Parameter freeze + config_hash** | `RR-BENCH-008`, `19` §8.3 | Post-hoc tuning on test set |
| **Train/tune seed split** | `19` §8.3 | Tuning on evaluation seeds |
| **INVALIDATED runs excluded** | `34` §5.2; `20` BP-2 | Broken audit still counting |
| **Independent metric evaluators** | `RR-METRIC-005` | Runtime self-audit of M-16 |
| **F-1…F-6 falsification** | `20` §1.2 | Pre-registered failure conditions |
| **ABUNDANT profile mandatory** | `RR-BENCH-009` | Only showing scarce wins |
| **LLM cache-only in evaluate** | `20` BP-1, `RR-NFR-035` | Non-reproducible decisions |
| **Byte-identical reproduction** | `RR-NFR-020` | Hidden nondeterminism |
| **Adversarial cases in metrics** | `19` DS-16 | Dropping hard cases |
| **Published p(i,∅) distribution** | `19` §9 `distributions.json` | Hidden easy/hard natural recovery |

---

## 2. Hidden oracle isolation — audit

```
Generator (step 6) writes OracleRow ──► oracle partition (not in engine DB path)
                                              │
Decision path: SEE→…→ALLOCATE→GUARD        │ (never reads)
                                              │
Execution adapter ONLY ──────────────────────┘ lookup outcome
Evaluator / metrics (post-run) may use oracle for M-12, M-19, M-25 (labelled oracle-dependent)
```

**Enforcement at implementation:**

- Separate files / schema with import guard test (`DS-12`)  
- Type system: no oracle types in `revive/simulate`, `revive/prioritize`, etc.  
- Code review + static analysis for oracle imports  

**Residual risk:** Developer bypass in adapter used by REVIVE only — mitigated by **same adapter interface for all policies** (BF-8).

---

## 3. Baseline fairness — audit

| Check | Status |
|-------|--------|
| B0 never acts — measures natural recovery | Fair floor |
| B1 uses published reasonable retry schedule | Must publish at M3 |
| B2 contact-all with same gates | Strong opponent |
| B3 greedy ENRV without resource density | Isolates allocation |
| REVIVE gets same predictor/strategy version as B1/B5 where needed | BF-7 |
| REVIVE cannot skip gates | BF-2 |

**Gap:** P0 plan implements B0–B3 first; demo script cites B0–B6 — **not an integrity issue** but headline comparison must not cherry-pick baseline after run.

---

## 4. Same environment checks

| Dimension | Held fixed? |
|-----------|-------------|
| Opportunity batch | Yes — same `dataset_hash` |
| Resource constraints | Yes — same PolicyPack |
| Action costs | Yes — same cost model code |
| Time horizon H | Yes — same clock + policy |
| Attribution logic | Yes — same C-20 |
| Randomness | Same seed + labelled streams |

---

## 5. Future information leakage — audit

| Vector | Mitigation |
|--------|------------|
| Oracle in predictor training | Train/eval split; no oracle features (`11` §4.4) |
| Late success signals | Pre-execution stopping `RR-FUNC-051` |
| Learning updating mid-batch on eval split | Strategy version snapshot at cycle open |
| LLM training on outcomes | LLM not in pricing path; cache keyed |
| Metrics code reading oracle for M-10 | M-10 from realized outcomes, not oracle ceiling in decision |

**Oracle-dependent metrics** (M-12, M-19, M-20, etc.) are labelled and must not feed back into policy (`RR-METRIC-012`).

---

## 6. Target leakage / tuning on test set

| Rule | Spec |
|------|------|
| Freeze before comparative measurement | `RR-BENCH-008` |
| Change requires full re-run | `19` §8.3 |
| Sensitivity sweeps (ε, λ_f) reported as curves, not silent retune | `20` §5.3 |
| Generator parameters not adjusted after seeing M-10 | `19` §8.1 vector "Tune parameters" |

**Implementation discipline:** One `config_hash` committed before first headline run.

---

## 7. What prevents REVIVE from cheating? (precise)

1. **The decision pipeline has no API to the oracle** — only the execution simulator does, and all policies use the same simulator (`AI-6`, BF-8).  
2. **Outcomes are not functions of policy name** — adapter maps (action, context) → oracle lookup, identical for REVIVE and B3.  
3. **Uplift is computed from a predictor trained without oracle labels** — only observable features; oracle used only ex post for evaluation metrics explicitly marked oracle-dependent.  
4. **Economic objective uses ex ante ENRV; success metric uses ex post net recovery** — cannot optimize M-10 directly in code without building a separate fraudulent metric path (forbidden + code review).  
5. **Reproducibility test** — any cheat that branches on hidden state likely breaks byte-identical artefacts unless cheat is deterministic and same for all policies (then REVIVE gains nothing vs baselines).  
6. **Independent evaluators recompute M-16, M-17** from audit chain.  
7. **Pre-registered falsification F-1…F-6** — must report if REVIVE loses.  
8. **No hand-entered numbers** (`RR-BENCH-007`, `26` §9).  

**What does NOT prevent cheating:** External reviewer trust — mitigation is **open artefacts**, `revive verify`, `revive diff`, published `config_hash`, and `distributions.json`.

---

## 8. Residual integrity risks (implementation-phase)

| Risk | Severity | Control |
|------|----------|---------|
| Accidental oracle import in predictor | High | CI test DS-12 |
| Different adapter instances per policy | High | Shared contract tests RR-NFR-083 |
| Tuning generator after seeing M-10 | High | config_hash discipline |
| Using oracle labels to train p(a) | Critical | Feature audit; no oracle columns |
| Dropping HOSTILE cases from metrics | Medium | DS-16; report coverage |
| LLM uncached in benchmark | Medium | RR-NFR-035 hard error |

---

## 9. Verdict

**Benchmark design is integrity-conscious and falsifiable.** No structural flaw found in spec. Integrity depends on **implementation discipline** (oracle isolation, freeze, no policy branches, honest reporting). **Ready to implement controls in M2/M13** — not a blocker for M1 foundation.
