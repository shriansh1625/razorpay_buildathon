# Pre-M1 LLM Boundary Audit

**Frozen rule:** `RR-GUARD-020` / README C-7 — **No LLM output may become a number that moves money.**

---

## 1. Deterministic responsibilities (must stay code)

| Domain | Owner | LLM allowed? |
|--------|-------|--------------|
| Arithmetic (paise) | C-08, C-09 | **Never** |
| ENRV, uplift, costs | C-07, C-08, C-09 | **Never** |
| p(i,a), p(i,∅), σ | C-07 | **Never** |
| Budget / capacity reservation | C-16 | **Never** |
| Gate verdicts ALLOW/DENY/etc. | C-13 | **Never** |
| Stopping rules SR-01–11 | C-14 | **Never** |
| State transitions | State machine layer | **Never** |
| Retry/contact/discount limits | Policy pack + gates | **Never** |
| Allocation selection | C-12 | **Never** |
| Tie-breaking | C-12 | **Never** |
| Benchmark metrics M-* | C-26 evaluators | **Never** |
| Oracle outcome generation | C-25 generator | **Never** |
| Oracle lookup at execution | C-18 adapter | **Never** |
| Idempotency / duplicate suppression | C-13 G9 | **Never** |
| ε threshold enforcement | C-12, policy | **Never** |
| Incentive tier selection | Candidate params enum + G5 | **Never** |
| Strategy/policy version writes | C-21 (predictor only) | **Never for policy** |

---

## 2. LLM responsibilities (optional P1)

| Component | Allowed LLM output | Forbidden |
|-----------|-------------------|-----------|
| **C-05 Root Cause Analyst** | Ranked **closed-set** cause codes; confidence **bands** (not floats); evidence row IDs | Free-form causes; numeric confidence; new reason codes |
| **C-10 Copy Composer** | Text slots in templates | `*_paise`, `*_pct`, amounts, probabilities |
| **RR-GUARD-027** (P2) | NL → compiled rules | Runtime interpretation of free text |

**Band → numeric prior mapping** is a **versioned deterministic table**, not LLM output (`07` §7, `08` C-05).

---

## 3. P0 benchmark path

| Mode | Requirement |
|------|-------------|
| Official benchmark | **`LLM_OFF`** (`implementation-decisions`, `20` §5.1) |
| If LLM enabled elsewhere | Cache keyed `(prompt_version, seed, opp_id)`; zero uncached calls in evaluate (`RR-NFR-035`) |

P0 demo and M-10 **do not require LLM**.

---

## 4. Spec language that could accidentally grant LLM authority

| Location | Text | Risk | Mitigation |
|----------|------|------|------------|
| `08` C-05 | "confidence in [0,1]" in RR-FUNC-010 acceptance | **Medium** — sounds numeric | Diagnosis table has **bands only** (`17` §4.2); map in StrategyVersion |
| `05` RR-FUNC-016 | LLM ranked closed-set causes | Low if schema-enforced | RR-NFR-064 validation |
| `05` RR-FUNC-024 | LLM fills text slots | Low | Template rejects monetary slots |
| `35b` §5.2 | approval_action_families lists A11 as voice | **Low** — mislabel only | Use `11` §3 codes |
| `22` §2 | LLM for "natural-language policy" P2 | Low if compile-only | RR-GUARD-027 compile step |
| `09` §6 | LLM cached for diagnosis in non-benchmark | Low | Not in evaluate path |

**No spec passage authorizes LLM to set ENRV, verdicts, or oracle outcomes.**

---

## 5. Enforcement plan (implementation)

| Control | When |
|---------|------|
| Static grep: LLM call sites → output schema audit | M5+ |
| Schema validation RR-NFR-064 | All LLM calls |
| Prompt serialiser deny-list RR-NFR-062 | Before any LLM call |
| Benchmark CI: `cache_miss_count == 0` | M13 |
| No LLM imports in `pricing/`, `guard/`, `allocator/`, `ledger/` | M1 structure |

---

## 6. Conflicts

**None material.** RR-FUNC-010 acceptance wording vs band-only diagnosis is resolved by **`17-data-model.md` authority** (no numeric confidence on Diagnosis table).

---

## 7. Verdict

LLM boundary is **clear and enforceable**. P0 can be **100% deterministic**. **No blocker for M1.**
