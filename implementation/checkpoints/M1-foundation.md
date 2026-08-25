# M1 Checkpoint — Project Foundation

**Milestone:** M1 — Project Foundation  
**Date:** 2026-08-21  
**Status:** COMPLETE  
**Authorization:** M1 APPROVE WITH EXPLICIT ASSUMPTIONS (`implementation/M1-approval-gate.md`)

---

## Delivered

| Item | Location | Notes |
|------|----------|-------|
| Python package | `revive/` | Modular monolith skeleton |
| Domain types | `revive/domain/` | Paise, EntityId, enums (15 opportunity states, 15 action codes) |
| Virtual clock | `revive/clock/` | Monotonic virtual time |
| PRNG streams | `revive/rng/` | Master seed + labelled streams |
| State machines | `revive/state/` | 5 machines; illegal transitions raise (`RR-NFR-043`) |
| Config | `revive/config/` | Settings + PolicyPack **DRAFT** (NOT FROZEN) |
| DB skeleton | `revive/db/` | SQLite DDL for docs/17 layers; oracle partition isolated |
| Errors | `revive/errors/` | Taxonomy incl. `IllegalStateTransitionError` |
| Observability | `revive/observability/` | Logging foundation |
| Integrity | `revive/integrity/` | Decision-path / oracle boundary check |
| Tests | `tests/` | 7 test modules, requirement IDs in names |
| ADR-011 draft | `implementation/adr-011-epsilon-threshold.md` | ε provisional = 0 |
| Tooling | `pyproject.toml` | Python ≥3.11, pytest dev extra |

---

## Explicitly NOT delivered (per M1 scope)

- Synthetic generator / hidden outcome oracle (M2)
- Predictor, allocator, gate execution (M7–M10)
- Benchmark harness and metric claims (M13)
- UI, LLM, Razorpay integrations
- Sealed PolicyPack or benchmark config_hash freeze

---

## Acceptance criteria

| Criterion | Result |
|-----------|--------|
| `pytest` passes | Run locally after `pip install -e ".[dev]"` |
| Money is integer paise only | `Paise` type + tests |
| Illegal state transitions raise | Opportunity + intervention illegal pairs tested |
| PRNG reproducible at same seed | Stream tests |
| Virtual clock deterministic | Clock tests |
| PolicyPack not frozen | Draft status + `is_frozen_for_benchmark == False` |
| Oracle not in decision path | Boundary test (oracle module absent in M1) |
| 15 opportunity states implemented | Enum count test |

---

## Assumptions carried forward

1. **ε = 0 paise** provisional until ADR-011 accepted (see draft).
2. **15 states** implemented despite doc text saying “14” (I-02).
3. **SQLite** single-file DB per ADR-010 proposal.
4. Razorpay integration remains **SIMULATED / UNVERIFIED**.

---

## Next milestone (NOT authorized)

**M2 — Synthetic Dataset Generator + Oracle** — requires explicit user authorization.

---

## Verification command

```bash
python -m pip install -e ".[dev]"
pytest -ra
```
