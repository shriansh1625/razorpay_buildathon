# M13.12 Mathematical Equivalence

## Implemented optimizations

All implemented changes are **implementation-preserving**:

1. **Eligible candidate filter** — identical predicate to inline checks (`A00` skip, `enrv <= epsilon` skip)
2. **Tuple iteration for usage** — same arithmetic as `dict(pc.usage)` iteration
3. **Usage dict cache** — returns identical mapping; cleared each `allocate_portfolio` call
4. **Contact violation / total usage** — same summation semantics; no change to subgradient definition

## Unchanged formulation

```text
rv(i,a) = ENRV(i,a) − Σ_r λ_r · usage_r(i,a)
```

Subgradient, step size, stopping criteria, primal recovery order, tie-breaking keys — unchanged.

## best_rvs semantics preserved

`allocate_portfolio` continues to recompute `best_rvs` from final relaxed picks and returned lambdas (post-iteration lambda state), matching pre-M13.12 behavior.

## Not proven / not implemented

- Independent-opportunity fast path (Option A)
- Uncoupled/coupled decomposition (Option B)
- Cross-cycle lambda warm start (Option C)

## Shadow prices

Allocation assignments, resource usage, and `allocation_hash` are the authoritative regression surface. Shadow prices compared via full `AllocationResult.to_dict()` equivalence.
