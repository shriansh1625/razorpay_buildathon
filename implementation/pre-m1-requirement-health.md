# Pre-M1 Requirement Health (76 MUST)

**Scope:** The 76 MUST requirements counted in `38-traceability-matrix.md` §2:  
`RR-FUNC-*` (41) + `RR-GUARD-*` (17) + `RR-UI-*` (8) + `RR-AUDIT-*` (10)

**Note:** Additional MUST requirements exist in `RR-NFR-*`, `RR-BENCH-*`, `RR-METRIC-*` (see §5). They are not in the "76" count but are build-blocking.

---

## 1. Summary statistics

| Block | MUST count | Mapped to component | Named test in traceability | Demo beat | Measurable objectively |
|-------|------------|---------------------|----------------------------|-----------|------------------------|
| RR-FUNC | 41 | 41/41 | 41/41 | 28/41 | 41/41 |
| RR-GUARD | 17 | 17/17 | 17/17 | 5/17 | 17/17 |
| RR-UI | 8 | 8/8 | 5/8 (integration) | 7/8 | 6/8 (visual + artefact) |
| RR-AUDIT | 10 | 10/10 | 6/10 | 3/10 | 10/10 |
| **Total** | **76** | **76/76** | **69/76** | **43/76** | **74/76** |

Source: `docs/38-traceability-matrix.md` §2–3 — **no MUST row marked GAP**.

---

## 2. ORPHANS (no implementation mapping)

**None** among the 76 MUST requirements. Every ID maps to component(s) in `38` or `33-requirement-traceability.md`.

**Near-orphan (process, not requirement):** `RR-DATA-001`…`010` referenced in `05` ID blocks but detailed as DS-* in `19` — mapped to generator C-25, not orphaned.

---

## 3. UNTESTABLE or weakly testable MUST requirements

| ID | Issue | Objective validation path | Severity |
|----|-------|---------------------------|----------|
| `RR-FUNC-012` | Vocabulary / no "proven" language | Automated string scan + diagnosis schema | Low — testable with corpus |
| `RR-UI-001`…`007` | No per-screen unit test in traceability | Integration/E2E + manual demo checklist | Low — acceptable per `38` §3 |
| `RR-UI-008` | Synthetic banner on every screen | Visual/regression test | Low |
| `RR-AUDIT-003` | Audit before effect under crash | Crash-injection timing test | Medium — hard but specified in `23` |
| `RR-AUDIT-004` | Completeness catalogue | Event-type coverage audit | Medium |
| `RR-AUDIT-006` | Deterministic audit sequence | Byte hash at seed | Low |
| `RR-AUDIT-009` | Rebuild tables from chain | Replay integration test | Medium — labor but defined |

**Verdict:** No MUST requirement is **fundamentally untestable**. Seven have **higher implementation cost** tests.

---

## 4. REDUNDANT requirements (duplicate obligation)

| IDs | Overlap | Recommendation |
|-----|---------|----------------|
| `RR-GUARD-010` + `RR-FUNC-050` | Both require 11 stopping rules | Keep both — gate integrates SR; dual tests intentional |
| `RR-GUARD-022` + `RR-FUNC-083` | Learning cannot write policy | Keep both — structural + functional |
| `RR-FUNC-061` + `RR-AUDIT-003` | Audit before adapter | Keep both — execution + audit views |
| `RR-NFR-051` + `RR-AUDIT-002` | Chain verification | NFR vs audit block overlap | Accept — same test satisfies both |
| `RR-NFR-052` + `RR-AUDIT-005` | Reachability | Same | Accept |

**No redundant MUST should be dropped** — overlaps are intentional traceability, not spec errors.

---

## 5. OVER-SCOPED requirements (P0 schedule pressure)

| ID | Requirement | Why over-scoped feel | Actual tier | Mitigation |
|----|-------------|----------------------|-------------|------------|
| `RR-UI-002` | Leakage explorer + graph | Rich viz | P0 MUST | Minimal graph; table fallback |
| `RR-FUNC-091` | Mandatory adverse findings section | Report generator work | P0 MUST | Template section; fail if empty |
| `RR-AUDIT-009` | Full chain reconstruction | Heavy | P0 MUST | Incremental replay tests |
| `RR-FUNC-066` | Approval modify + re-gate | Complex | P0 MUST | Single modify path test |
| Seven UI screens | Full surface | Large | P0 MUST | Artefact-driven; shared components |

**None should be removed** — they are Track 03 bar items. Risk is **schedule**, not invalidity.

---

## 6. Full MUST register (abbreviated)

### RR-FUNC (41) — all P0

| ID | Milestone | Benchmark | Demo |
|----|-----------|-----------|------|
| 001–005, 007 | M4 | Y | Beat 2 |
| 010–015 | M5 | Partial | Beat 3 |
| 020–021, 023, 025–028 | M6–M8 | Y | Beat 3 |
| 030–034, 037, 039 | M9 | Y | Beat 4 |
| 040–043 | M9–M10 | Y | Beat 3–4 |
| 050–051 | M10 | Y (M-17) | Beat 5 |
| 060–066 | M11 | Y | Beat 5–7 |
| 070–073 | M12 | Y (M-10) | Beat 3 |
| 082–083 | M1/M14 | N | — |
| 090–091 | M13 | Y | Beat 6–7 |

### RR-GUARD (17) — all P0

| IDs | Milestone | Test prefix |
|-----|-----------|-------------|
| 001–012 | M10 | T-POL-* |
| 020–026 | M1/M10/M14 | T-SAF-* |

### RR-UI (8) — all P0

| IDs | Milestone |
|-----|-----------|
| 001–007 | M16 |
| 008 | M16 (global) |

### RR-AUDIT (10) — all P0

| IDs | Milestone |
|-----|-----------|
| 001–010 | M1 skeleton → M17 hardening |

---

## 7. Related MUST blocks outside the 76

| Block | Count (approx) | P0 relevance |
|-------|----------------|--------------|
| RR-NFR MUST | ~42 | Build-blocking (esp. 020 reproducibility) |
| RR-BENCH | 10+ in `20`/`21` | P0 benchmark |
| RR-METRIC | 16 in `37` | P0 reporting |
| RR-DATA | DS-1–16 in `19` | P0 generator |

---

## 8. Health verdict

| Category | Finding |
|----------|---------|
| ORPHANS | **0** |
| UNTESTABLE | **0 fundamental**; 7 high-effort |
| REDUNDANT | **5 intentional overlaps** — do not merge |
| OVER-SCOPED | **5 schedule-heavy** — mitigate, do not cut |

**Requirement set is internally consistent and implementable** for P0.
