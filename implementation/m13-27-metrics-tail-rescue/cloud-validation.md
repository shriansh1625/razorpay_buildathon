# M13.27 Cloud Validation

**Status:** PENDING (not run automatically)

## Required cloud repro

After merge, run on cloud VM:

```bash
python scripts/m13_27_metrics_tail.py
```

Or production-equivalent cell runner for **seed=1 ABUNDANT REVIVE** only.

## Success criteria

1. All metric fields and `metrics_checksum` match local equivalence baseline
2. Post-cycle `compute_policy_metrics` wall drops from multi-hour tail to seconds
3. Total cell wall approaches local ~1363 s cycle time (+ I/O), not ~9900 s

## Do not run

- Official 30-cell benchmark
- Full preflight into `artefacts/cloud-preflight-*`

Record measured wall/CPU/RSS in this file when cloud run completes.
