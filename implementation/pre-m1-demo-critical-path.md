# Pre-M1 Demo Critical Path

**Source demo spine:** `26-demo-script.md` beats 1–7 + `02` §10 hostile question answer

---

## DEMO CRITICAL PATH

Smallest end-to-end path that proves the full thesis **without optional P1/P2**:

```
M2 Generate (seed S, BALANCED)
  → M4 Detect opportunities (M-01)
  → M5 Diagnose one opportunity (candidate causes)
  → M6–M8 Price candidates incl. NO_ACTION (ENRV table)
  → M9 Allocate under scarce resources (deferrals + binding constraint)
  → M10 Gate trace (≥1 DENY or MODIFY) + SR fire + M-16=0
  → M11 Execute one intervention (sim adapter → oracle)
  → M12 Observe outcome + attribution
  → M13 Benchmark REVIVE vs B0–B3 (≥1 seed; 20 for submission)
  → M17 Audit chain verify (M-58)
  → M16 UI: Command Center + Decision Detail + Allocation + Benchmark + Audit
```

**Single-opportunity narrative path** (demo beats 3–5) runs **inside one cycle** of the above.

---

## Step-by-step dependency map

| Demo step | Implementation | Required data | API/UI | Failure risk |
|-----------|----------------|---------------|--------|--------------|
| **1. Revenue at risk** | C-02, generator signals | `RevenueOpportunity`, M-01 | UI-001 `/metrics/summary` | Empty pool if generator weak |
| **2. Diagnosis / leakage** | C-02, C-05, C-04 | Diagnosis, risk_class breakdown | UI-002 `/leakage` | Graph over-engineered |
| **3. Candidate + counterfactuals** | C-06–C-09 | `ActionCandidate` full set | UI-004 `/opportunities/{id}` | p∅ degenerate |
| **4. Allocation** | C-12, C-16 | Allocation report, shadow prices | UI-005 `/cycles/{id}/allocation` | No binding constraint if not scarce |
| **5. Guardrails** | C-13, C-14, C-15 | GateVerdict[], SR events | UI-004 gate trace, UI-006 audit | Missing injected adversarial case |
| **6. Execution** | C-17, C-18 | `Intervention`, idempotency | UI-004 outcome panel | Oracle leak |
| **7. Recovered money** | C-19, metrics | `Outcome.recovered_amount_paise` | UI-001 M-05/M-09 | Attribution wrong → M-10 skew |
| **8. Baseline comparison** | C-24, C-26 | Per-seed M-10, paired CI | UI-007 `/benchmark/runs` | Runtime > demo slot |
| **9. Audit** | C-22 | Hash chain, M-58 | UI-006 `/audit/verify` | Chain break under crash |

---

## Critical artefacts (must exist before demo)

| Artefact | Producer | Used by |
|----------|----------|---------|
| `dataset/manifest.json` + oracle partition | M2 | All runs |
| `run_{id}/metrics.json` | M13 | UI-001, UI-007 |
| `run_{id}/decisions.jsonl` | Cycle | UI-004 |
| `run_{id}/audit_chain.jsonl` | C-22 | UI-006 |
| `config_hash` + seed list | Freeze | UI-007 integrity |
| `report.md` with limitations + adverse | M13 | Beat 7 |

---

## Minimum viable demo (timeboxed hackathon)

If schedule slips, **still required for Track bar:**

1. One seed, BALANCED, REVIVE vs B0 + B3 (not full B0–B6)  
2. Five screens: Command Center, Decision Detail, Allocation, Benchmark, Audit  
3. Live re-run `revive benchmark --seed S` for M-46  

**Not sufficient for full spec:** 20 seeds, 7 screens, all SR/gate coverage — but critical path above is the **spine**.

---

## Parallel vs serial on critical path

```
M1 ─┬─ M2 ─┬─ M4 ─ M5 ─ M6─M8 ─ M9 ─┬─ M11 ─ M12 ─ M13 ─ M16
    │      │                         │
    │      └─ M10 (gates) ────────────┘
    └─ M17 audit skeleton (parallel from M1)
```

**Longest pole:** M2 generator → M9 allocator → M13 harness → M16 UI binding

---

## Demo failure modes to pre-empt

| Risk | Mitigation |
|------|------------|
| M-16 > 0 | Do not demo; fix gates first (`26` §0) |
| Fabricated placeholders | Fill from artefact only |
| No NO_ACTION cases | Generator OR-5 |
| No binding constraint | SCARCE profile in demo run |
| Reproducibility fail | LLM_OFF; seed in command |
| Skip ABUNDANT in narrative | Show in Benchmark tab appendix (`26` beat 6) |

---

## Verdict

Demo critical path is **achievable** after M13 with **no P1 features**. UI (M16) is on the path but **must not start before M13 artefacts exist**.
