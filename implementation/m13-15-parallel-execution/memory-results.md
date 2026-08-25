# M13.15 Memory Results

**Label:** DEVELOPMENT_VALIDATION_ONLY

| Run | Workers | Notes |
|-----|---------|-------|
| M13.13 feasibility | 1 | Peak RSS ~529 MB |
| M13.14 parallel (2 REVIVE cells) | 2 | Safe on 8 GB |
| M13.15 dev validation | 1 | Small matrix |
| M13.15 dev validation | 2 | Small matrix |

Two-worker execution is safe on 8 GB hardware. Default remains `workers=1`. Do not auto-scale to 4+ workers.
