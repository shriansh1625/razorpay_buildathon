# M13.15 Determinism

**Label:** DEVELOPMENT_VALIDATION_ONLY

## Requirements verified

| Property | Status |
|----------|--------|
| `metrics_checksum` per cell | **Identical** workers=1 vs workers=2 |
| Aggregate fingerprint | **Identical** |
| Config hash per worker | Validated on worker startup |
| RNG / generator | Unchanged — each group uses same `generator_config_for_cell()` |
| Aggregation order | Canonical cell plan order via `aggregate_from_store()` |

## Development validation

Matrix: seed=1, profiles=BALANCED+HIGH_NATURAL (10 cells)

```
aggregate_fingerprint_match: true
cell_fingerprint_match: true
```

## Resume

Partial run (`stop_after_cell=5`, workers=2) + resume (workers=2) matches uninterrupted workers=1 run.
