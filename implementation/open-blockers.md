# REVIVE — Open Blockers

**Phase:** M0  
**Last updated:** 2026-08-21

---

## 1. Readiness classification

```text
READY WITH MINOR ASSUMPTIONS
```

No **BLOCKED** items prevent starting M1. All material ambiguities have PROPOSED defaults or a documented resolution path.

---

## 2. Genuine blockers

| ID | Blocker | Status | Resolution path |
|----|---------|--------|-----------------|
| — | *None at M0* | — | — |

---

## 3. Open questions requiring decisions (from `docs/40-open-questions.md`)

These are **not blockers** if PROPOSED defaults are adopted and recorded in `implementation-decisions.md` + ADR.

| ID | Question | Priority | Proposed default | Blocks if unset? |
|----|----------|----------|------------------|------------------|
| OQ-01 | ENRV threshold ε | P0 | 0 paise | No — default usable |
| OQ-02 | G7 approval thresholds | P0 | value > ₹5000 or uncertainty/ENRV > 0.5 | No |
| OQ-03 | Recovery window lengths | P0 | checkout 48h, payment 14d, subscription 14d, receivable 90d | No |
| OQ-04 | Near-zero denominator for metrics | P0 | < 1 paise | No |
| OQ-15 | Cycle interval | P0 | 15 min virtual time | No |
| OQ-05…14 | Learning, metrics tuning | P1 | See `40-open-questions.md` | No for P0 |
| OQ-08 | Calibration rollback threshold | P1 | **No default** | No for P0 (learning is P1) |
| — | `max_reconcile_attempts` | P0 exec | `UNKNOWN` in `34-state-machine.md` §9 | Minor — adopt e.g. 3 with ADR |

**Sensitivity requirement:** For each numeric decision, benchmark at default and ±50% where meaningful (`docs/40-open-questions.md` §3).

---

## 4. Documentation inconsistencies (non-blocking)

From `docs/36b-documentation-consistency-check.md`:

| ID | Issue | Authority | Action at implementation |
|----|-------|-----------|---------------------------|
| I-01 | README calls M-14 "Wasted Intervention Rate"; `37` defines "Guardrail-block profile" | `docs/37-metrics-dictionary.md` | Implement M-14 per dictionary; do not edit frozen `docs/` without authorization |
| I-02 | State machine says "Fourteen states" but lists 15 | Table in `34` | Implement 15 states; treat text as typo |

**Severity:** LOW — cosmetic only.

---

## 5. Scope risks (watch list)

| Risk | Why it matters | Mitigation |
|------|----------------|------------|
| Voice-as-hero demo | Exits Track 03 narrative | Voice is P2; demo script order in `docs/26-demo-script.md` |
| UI before engine | Hides weak logic | Milestone order M13 before M16 |
| Cutting benchmark for polish | Fails SC-8 | Tier discipline: never cut P0.11 |
| Real Razorpay integration | UNVERIFIED APIs | Adapter interface + SIMULATED label only |
| LLM in benchmark path | Breaks RR-NFR-020 | Default `LLM_OFF`; cache if enabled |

---

## 6. Missing product decisions (would force invention)

| Topic | Status |
|-------|--------|
| Exact opportunity count / cycle count | `UNKNOWN` in `19` §2.4 — must pick concrete numbers at M2 (proposed: 500–1000 opps, multi-day virtual run) |
| Exact baseline B1 retry schedule | Must publish reasonable schedule at M3 (`BF-9`) |
| Simulated approver model | Documented in `20` §7 — implement at M10/M11 |
| UI framework | Not mandated — choose at M16 (React assumed in plan) |

None of these block M1 foundation work.

---

## 7. Escalation triggers (when to stop and ask)

Per `docs/32-implementation-contract.md` §5:

1. Two authoritative docs conflict on **product semantics** (not cosmetic).
2. A MUST requirement appears impossible within timebox.
3. Implementing a feature requires inventing Razorpay API behaviour.
4. Benchmark shows REVIVE loses — report honestly; do not "fix" by cheating.

---

## 8. Pre-implementation approvals needed

| Item | Needed before |
|------|---------------|
| **This implementation plan** | M1 start |
| Product-owner approval | Any MUST requirement relaxation or scope expansion |
| Documentation edits | Any change to frozen `docs/` intent |

**Current state:** Awaiting plan review. **Do not start M1 until approved.**
