# M13.24 Performance

Development only: `--mode development --stress-cells 10`. **Not official evidence.**

Host: 12 CPUs. Peak estimate uses parent RSS + worker peak × requested workers (existing M13.20 formula). Safe ceiling remains 6 GB.

| workers | wall (s) | peak parent RSS | peak worker RSS | estimated parallel peak | memory_safe | groups |
|---------|----------|-----------------|-----------------|-------------------------|-------------|--------|
| 1 | 72.336 | 48.9 MB (parent after) | n/a (sequential) | n/a | n/a | sequential |
| 2 | 39.788 | 49.0 MB | 98.7 MB | 246.5 MB | true | 2 |
| 8 | 31.689 | 49.4 MB | 98.2 MB | 834.9 MB | true | 2 |

Notes:

- Stress matrix is two seed/profile groups (10 cells = 2 × 5 policies). Extra workers beyond 2 cannot run extra groups on this workload.
- Wall still dropped vs sequential because two groups run concurrently.
- Estimated peak for workers=8 is inflated by `worker_peak × 8` even though only two workers are busy; still well under 6 GB.

Raw: `performance-raw.json`
