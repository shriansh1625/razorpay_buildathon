# M13.12 Baseline CPU Profile

**Reproduction:** seed=2, profile=BALANCED, official frozen scale, cycle 0 (development script `scripts/m13_12_profile.py`)

## Scale at cycle 0

| Metric | Value |
|--------|-------|
| Opportunities | 251 |
| Candidates | 783 |
| Lagrangian iterations (k_max) | 40 |

## Single-cycle lagrangian_allocate (pre-optimization reference)

| Metric | Value |
|--------|-------|
| lagrangian_allocate | 0.060 s |
| allocate_portfolio | 0.018 s |
| Mode | LAGRANGIAN |

## 50 REVIVE cycles (seed=2, BALANCED) — pre-optimization

| Metric | Value |
|--------|-------|
| Total wall time | 30.17 s |
| Cycles | 50 |
| Per-cycle mean | ~0.60 s |

## cProfile top cumulative (50 cycles, pre-optimization)

Source: `revive-50cycles-profile.txt`

| Function | Cumulative | Calls |
|----------|------------|-------|
| `run_revive_cycle` | 30.07 s | 50 |
| `allocate_portfolio` | 8.59 s | 50 |
| `lagrangian_allocate` | 8.16 s | 50 |
| `_best_action_for_opportunity` | 7.05 s | 502,000 |
| `assemble_context` | 6.10 s | 12,550 |
| `price_candidates` | 5.92 s | 12,550 |
| `generate_candidates` | 5.81 s | 12,550 |
| `_reduced_value_paise` | 3.66 s | 1,755,655 |
| `usage_dict` | 0.83 s | 2,351,441 |
| `sort_key_candidate` | 1.01 s | 1,161,477 |

## Worst single-cycle allocate (all 2016 cycles scanned)

| Cycle | Opps | Candidates | allocate_portfolio |
|-------|------|------------|-------------------|
| 1457 | 427 | 2554 | 0.142 s |

Full-matrix allocate-only total (seed=2, BALANCED, 2016 cycles): **96.11 s**

## Trace finding (user report)

KeyboardInterrupt during `picks` reconstruction inside `lagrangian_allocate()` — consistent with O(iterations × opportunities × candidates) inner-loop cost dominating REVIVE cells at official scale.
