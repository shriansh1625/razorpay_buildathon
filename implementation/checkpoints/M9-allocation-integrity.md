# M9 Checkpoint — Allocation Integrity + Decision Lifecycle

**Milestone:** M9 — Decision Lifecycle Integrity (ALLOCATE → VERIFY validity)  
**Date:** 2026-08-23  
**Status:** COMPLETE

---

## Purpose

Seal M8 allocations into **immutable, attributable decision records** with resource reservation intent, expiry, staleness detection, and reconciliation metadata — without execution or gate authorization.

---

## Decision identity

| Field | Source |
|-------|--------|
| `decision_id` | Deterministic `dec_<sha256(cycle, opp, allocation_hash, config_hash)>` |
| `idempotency_key` | `H(opportunity_id, action_code, attempt_seq, cycle_id)` — docs/15 §3.1 |
| `cycle_id` | M8 allocation cycle |
| `configuration_hash` | Policy + allocator + valuation + capacity bundle |

Immutable `AllocationDecision` per `(cycle_id, opportunity_id)` — docs/09 §4, DM-11.

---

## Snapshot

`AllocationSnapshot` captures observable state at seal time:

- opportunity/customer IDs, value at risk
- candidate and valuation IDs/versions
- resource capacity digest
- simulation time, opportunity state

**No oracle or hidden fields.**

---

## Versioning

| Version | Recorded on decision |
|---------|---------------------|
| `allocator_version` | M8 |
| `valuation_version` | M7 |
| `strategy_version` | M7 predictor |
| `policy_pack_version` + `status` | DRAFT/SEALED |
| `lifecycle_version` | M9 |

---

## Configuration hash

`configuration_hash()` combines:

- `PolicyPack.config_hash()`
- allocator config parameters
- sorted valuation/strategy versions
- resource capacities digest

Material config change → reconciliation marks **STALE** (`configuration_changed`).

---

## Resource reservations

`ReservationLedger` — single in-memory authority for M9:

- `RESERVE` on SELECTED decisions (intent only — no execution)
- Incentive at full `d(i,a)` paise (consistent with docs/10 §3.3)
- `RELEASE` on STALE / EXPIRED / CANCELLED / SUPERSEDED
- Idempotent per `decision_id`
- Conflict detection for incompatible concurrent reservations

---

## Expiry

`expires_at = created_at + allocation_ttl_micros`

Default TTL: **15 min virtual** (PROVISIONAL — docs/40 OQ-15).

Past expiry → `EXPIRED`, `execution_ready=False`.

---

## Staleness

`reconcile_decision()` compares current observable context to sealed decision:

| Factor | Status |
|--------|--------|
| `now > expires_at` | EXPIRED |
| `configuration_hash` mismatch | STALE |
| `payment_succeeded` + retry action | STALE |
| `opportunity_state` RECOVERED/CLOSED/STOPPED | STALE |
| `contacts_used >= contact_allowance` | STALE |

**Does NOT** re-run M8 allocator. **Does NOT** execute.

---

## Reconciliation output

`ReconciliationResult`:

- `status`: VALID / STALE / EXPIRED / SUPERSEDED / CANCELLED
- `execution_ready`: True only for VALID SELECTED decisions
- `stale_factors`: structured reason tokens
- Idempotent via `DecisionStore._reconciliation_cache`

---

## Supersession

`DecisionStore.supersede(old_id, new_decision)`:

- Old decision → `SUPERSEDED` with `superseded_by`
- Both records remain auditable
- Releases old reservations

---

## Idempotency

- `record_bundle()` — duplicate identical bundle is no-op
- `reconcile()` — repeated reconcile returns cached result
- `ledger.reserve()` — same decision_id returns existing reservations
- `ledger.release()` — idempotent

---

## Package layout

```
revive/decision/
├── config.py
├── models.py
├── hashing.py
├── ledger.py
├── seal.py          # seal_allocation()
├── reconcile.py     # reconcile_decision()
├── store.py         # DecisionStore
└── __init__.py
```

**Entry points:**

- `seal_allocation(allocation, portfolio_items, capacities, policy, ...)`
- `reconcile_decision(decision, ObservableReconcileContext)`
- `DecisionStore.record_bundle / reconcile / supersede`

---

## Tests

| File | Coverage |
|------|----------|
| `test_decision_identity.py` | Deterministic IDs, config hash, idempotent store |
| `test_reconciliation.py` | Payment recovered, expiry, config change, contacts, VALID |
| `test_decision_integrity.py` | Oracle guard, no allocator rerun, supersession |

**Results:** 160 tests passing (13 new M9 tests).

---

## Provisional parameters

| Parameter | Value | Status |
|-----------|-------|--------|
| `allocation_ttl_micros` | 15 min virtual | PROVISIONAL (OQ-15) |
| PolicyPack | DRAFT | Not benchmark-frozen |
| ε | Via PolicyPack | ADR-011 DRAFT |

---

## Deviations

None from documented decision immutability (docs/09 §4, DM-14).

---

## Deferred

- Persistent audit chain integration (M11+)
- Gate trace attachment (M10)
- Warm-start λ persistence across cycles
- Formal reason-code enum expansion

---

## Next milestone

**M10 — Policy / gate authorization** (AUTHORIZE — is action allowed to execute?)

Pipeline:

```
M8 ALLOCATE → M9 VERIFY VALIDITY → M10 GATES → M11 EXECUTE
```

---

## Acceptance criteria

```
[x] Allocation decision identity exists
[x] Cycle identity exists
[x] Snapshot/version metadata exists
[x] Configuration hash attached
[x] PolicyPack version + status attached
[x] Resource reservation semantics exist
[x] Reservation idempotent
[x] Allocation expiry exists
[x] Staleness detection exists
[x] Reconciliation exists
[x] Decision history immutable (supersession, transitions)
[x] Supersession supported
[x] Resource release on invalidation
[x] No oracle access
[x] No future information
[x] No execution
[x] No benchmark
[x] Tests pass
[x] M9 checkpoint exists
```
