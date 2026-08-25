# M10 Checkpoint — Authorization + Policy Gates + Stopping Rules

**Milestone:** M10 — Recovery Authorization Gate (AUTHORIZE)  
**Date:** 2026-08-23  
**Status:** COMPLETE

---

## Purpose

Deterministic safety boundary between M9 decision validity and M11 execution. Answers: *“Is this already-selected action authorized to proceed?”* — never re-allocates or substitutes actions.

---

## Authorization states

| State | Meaning |
|-------|---------|
| `AUTHORIZED` | All gates pass; M11 may consume artifact |
| `BLOCKED` | Hard deny — structured reason |
| `REQUIRES_HUMAN_APPROVAL` | G7 triggered; awaits approval |
| `STALE` | M9 reconciliation stale |
| `EXPIRED` | Decision/authorization TTL elapsed |
| `REPLAN_REQUIRED` | DEFER/config mismatch — separate replan cycle |

---

## Gate architecture

Fixed order docs/13 §3 — all gates recorded in trace:

| Gate | ID | Verdicts |
|------|-----|----------|
| G1 Consent | RR-GUARD-001 | DENY |
| G2 Communication window | RR-GUARD-002 | DEFER |
| G3 Contact frequency | RR-GUARD-003 | DENY |
| G4 Retry cap | RR-GUARD-004 | DENY |
| G5 Incentive ceiling | RR-GUARD-005 | DENY (no silent clamp — M10) |
| G6 Budget/capacity | RR-GUARD-006 | DEFER |
| G7 Approval threshold | RR-GUARD-007 | REQUIRE_APPROVAL |
| G8 Risk block | RR-GUARD-008 | DENY |
| G9 Duplicate suppression | RR-GUARD-009 | DENY |
| G10 Stopping rules | RR-GUARD-010 | delegated to SR engine |
| G11 Channel eligibility | RR-GUARD-011 | DENY |
| G12 Amount sanity | RR-GUARD-012 | DENY |

Precedence: `DENY > REQUIRE_APPROVAL > DEFER > ALLOW` (docs/13 §4.1)

---

## Stopping rules (SR-01…SR-11)

Implemented per docs/14 §2 — evaluated pre-execution in `authorize_execution()`.

Blocking stopping overrides positive ENRV (tested).

---

## Execution authorization artifact

`ExecutionAuthorization` — consumed by M11:

- `authorization_id`, `decision_id`, `idempotency_key`
- `authorization_state`, `gate_trace`, `stopping_results`
- `authorized_parameters` (unchanged from allocation — no G5 clamp)
- `policy_pack_version`, `configuration_hash`, versions
- `authorized_at_micros`, `expires_at_micros`
- `blocking_gate_id`, `blocking_reason_code`, `explanation`

---

## Fail-closed

- Missing candidate → BLOCKED
- Stale/expired M9 → STALE/EXPIRED
- Config hash mismatch → REPLAN_REQUIRED
- Stopping rule fired → BLOCKED
- Unknown consent → DENY (G1)
- Risk flags → DENY (G8)
- Duplicate idempotency → BLOCKED

---

## No substitution / no re-allocation

- Blocked action A does **not** authorize feasible B
- G5 does **not** silently clamp incentives — returns `MAX_DISCOUNT_EXCEEDED` BLOCKED
- `authorize_execution` contains no `allocate_portfolio` call

---

## Demo scenarios (tested)

| Scenario | Result |
|----------|--------|
| 10% incentive, 5% max | BLOCKED `MAX_DISCOUNT_EXCEEDED` |
| 2 contacts, max 2 | BLOCKED `MAX_CONTACTS_REACHED` |
| ₹80,000 value | REQUIRES_HUMAN_APPROVAL → AUTHORIZED after approval |
| Payment recovered + retry | BLOCKED SR-02 |

---

## Package layout

```
revive/policy/
├── config.py      # PolicyRules PROVISIONAL defaults
├── models.py      # ExecutionAuthorization, GateResult
├── context.py     # AuthorizeContext (observable only)
├── gates.py       # G1–G12
├── stopping.py    # SR-01–SR-11
├── authorize.py   # authorize_execution()
├── store.py       # AuthorizationStore + idempotency
└── __init__.py
```

**Entry:** `authorize_execution(decision, candidate, valuation, ctx, policy)`

---

## Tests

| File | Coverage |
|------|----------|
| `test_authorization_demo.py` | Demo scenarios |
| `test_authorization_integrity.py` | No substitution, idempotency, stale |
| `test_policy_integrity.py` | Oracle guard, no execution |

**Results:** 170 tests passing (10 new M10 tests).

---

## Provisional parameters

| Parameter | Default | Status |
|-----------|---------|--------|
| `max_incentive_pct` | 5.0 | PROVISIONAL |
| `max_contacts_per_customer` | 2 | PROVISIONAL |
| `approval_value_threshold_paise` | 8_000_000 (₹80k) | PROVISIONAL |
| Communication window | 09:00–19:00 | PROVISIONAL |
| PolicyPack | DRAFT | Not benchmark-frozen |
| ε | Via PolicyPack | ADR-011 DRAFT |

---

## Deferred

- G5 `ALLOW_WITH_MODIFICATION` clamp path (intentionally DENY in M10)
- Simulated approver UI (M16)
- Persistent audit chain write (M11)
- Legal consent values (UNVERIFIED — docs/13 §10)

---

## Next milestone

**M11 — Execute in simulated world** (first point allowed to act)

---

## Acceptance criteria

```
[x] Authorization engine exists
[x] Twelve gates implemented (G1–G12 trace)
[x] Eleven stopping rules enforced
[x] M9 validity checked first
[x] PolicyPack enforced via PolicyRules
[x] Retry/contact/window/consent/budget/capacity checks
[x] Incentive limit without silent modification
[x] Approval requirement represented
[x] Idempotency enforced
[x] Expiry enforced
[x] Configuration consistency enforced
[x] Fail-closed behavior
[x] Structured block reasons
[x] No action substitution
[x] No re-allocation
[x] No execution
[x] No oracle access
[x] Tests pass
[x] M10 checkpoint exists
```
