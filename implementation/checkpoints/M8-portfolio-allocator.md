# M8 Checkpoint — Portfolio Recovery Allocator

**Milestone:** M8 — Portfolio Recovery Allocator (PRIORITIZE)  
**Date:** 2026-08-23  
**Status:** COMPLETE

---

## Purpose

Given M7 valuations for multiple opportunities and a shared **resource snapshot**, allocate scarce recovery capacity to maximize portfolio expected net recovery value. M8 does **not** execute actions or run policy gates.

---

## Objective

```
maximize  Σ ENRV(i,a) · x_{i,a}

subject to:
  exactly one action per opportunity
  resource capacities
  ENRV(i,a) > ε  (or NO_ACTION)
```

Lagrangian relaxation with primal recovery (docs/10 §5.1). Greedy **density** fallback on timeout/failure (docs/10 §5.2).

---

## Inputs

| Input | Source |
|-------|--------|
| `PortfolioItem` | M4 opportunity metadata + M6/M7 priced candidates |
| `ResourceState` | Cycle capacity snapshot |
| `PolicyPack` | ε threshold, version hash |
| `AllocatorConfig` | K_max, step rule, iteration budget |
| `now_micros`, `cycle_id` | Virtual clock |

**Forbidden:** oracle, latent traits, future outcomes, realized recovery.

---

## Outputs

`AllocationResult`:

- `assignments` — per-opportunity `SELECTED` / `DEFERRED` / `NO_ACTION`
- `total_allocated_enrv_paise`
- `shadow_prices` + `shadow_price_method` (`LAGRANGIAN_DUAL` or `GREEDY_ESTIMATE`)
- `resource_usage`, `budget_usage_paise`
- `allocator_mode`, `allocation_hash`
- `constraint_summary`

---

## Constraints enforced

| Constraint | Mechanism |
|------------|-----------|
| Opportunity exclusivity | One assignment per opportunity |
| Retry slots | `retry_slots` capacity |
| Message capacity | `message_capacity` |
| Voice minutes | `voice_minutes` |
| Human review | `human_review_slots` |
| Incentive budget | `incentive_budget_paise` (full `d(i,a)` reserve) |
| Contact allowance | Per-customer `contact_allowance` |
| ε threshold | From `PolicyPack.epsilon_paise` |

---

## Optimization formulation

**Lagrangian (default):**

```
rv(i,a) = ENRV(i,a) − Σ_r λ_r · usage_r(i,a)
```

Subgradient ascent on capacity violations; deterministic step `step_scale / sqrt(k)`.

**Primal recovery:** Reserve resources in reduced-value order; defer on binding resource.

**Fallback greedy:** Sort by `ENRV / normalized_resource_cost` (not raw ENRV — B3 differentiation).

---

## Resource model

Six families from docs/10 §3. Usage derived from M6 `resource_requirements`. Incentive reserved at full tier paise (conservative).

---

## Shadow prices

- Lagrangian mode: dual multipliers `λ_r` at convergence
- Fallback: max ENRV of rejected candidate per binding resource (`GREEDY_ESTIMATE`)

---

## Tie-breaking

docs/10 §7: `(-score, -value_at_risk, opportunity_id, action_code)`

---

## Determinism

- Opportunity iteration sorted by `opportunity_id`
- Iteration budget (not wall clock) for benchmark reproducibility
- `allocation_hash` over assignments + policy hash

---

## B3 differentiation

| B3 | M8 |
|----|-----|
| Per-opp best heuristic ENRV | Portfolio Lagrangian + constraints |
| Global sort by raw ENRV | Reduced value / density fallback |
| No shadow prices | `shadow_prices` emitted |

Test: `test_fallback_density_differs_from_b3_raw_enrv` — same ENRV ranking, different winner under 1 message slot.

---

## Package layout

```
revive/allocation/
├── config.py
├── models.py
├── resources.py
├── tiebreak.py
├── lagrangian.py
├── greedy.py
├── allocate.py
└── __init__.py
```

**Entry:** `allocate_portfolio(items, resource_state, now_micros, cycle_id, policy)`

---

## Tests

| File | Coverage |
|------|----------|
| `test_allocation_basic.py` | Single/multi opp, ε, exclusivity, contacts |
| `test_b3_differentiation.py` | Density vs B3, positive ENRV not sufficient |
| `test_allocation_integrity.py` | Oracle guard, determinism, pipeline invariance |

**Results:** 147 tests passing (10 new M8 tests).

---

## Known limitations

- Single-cycle myopic (ADR-004) — no multi-period planner
- `EXACT` ILP mode not implemented (optional per docs/10 §5.3)
- Warm-start λ from prior cycle not wired (interface accepts `lambda_warm_start`)
- Gates (M10) not run — allocation is proposal only

---

## Provisional parameters

| Parameter | Value | Status |
|-----------|-------|--------|
| `K_max` | 40 | PROVISIONAL |
| `step_scale` | 50.0 | PROVISIONAL |
| `ε` | PolicyPack (0 draft) | ADR-011 DRAFT |
| PolicyPack | DRAFT | Not benchmark-frozen |

**No benchmark claims** until ε, PolicyPack, B1 schedule, scale, approver model, and config hash are sealed.

---

## ADR dependencies

| ADR | Impact |
|-----|--------|
| ADR-004 | Single-cycle myopia disclosed |
| ADR-008 | Conservative incentive reservation |
| ADR-011 | ε provisional |

---

## Next milestone

**M10 — Policy / gate validation** (VERIFY POLICY / GATES)  
Then M11 execution, M12 measurement, M13 benchmark.

Pipeline:

```
M8 ALLOCATE → M10 GATES → M11 EXECUTE → M12 MEASURE → M13 BENCHMARK
```

---

## Acceptance criteria

```
[x] Portfolio allocation engine exists
[x] Multiple opportunities allocated simultaneously
[x] Shared resource constraints enforced
[x] Budget, contact, capacity constraints enforced
[x] Opportunity exclusivity enforced
[x] Policy ε respected
[x] NO_ACTION remains possible
[x] Positive ENRV does not guarantee selection
[x] Lagrangian optimizer + greedy fallback
[x] Deterministic tie-breaking and reproducibility
[x] B3 differentiation test
[x] Oracle / future invariance tests
[x] No execution, benchmark, UI, LLM
[x] Tests pass
[x] M8 checkpoint exists
```
