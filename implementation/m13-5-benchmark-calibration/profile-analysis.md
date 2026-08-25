# Profile Analysis

Profiles must differ through documented mechanisms, not row count alone.

## Documented profile parameters

| profile | natural_mult | scarcity_factor | adversarial | degradation |
|---------|----------------|-----------------|-------------|-------------|
| BALANCED | 1.0 | 1.0 | False | 1.0 |
| HIGH_NATURAL | 2.2 | 1.0 | False | 0.8 |
| SCARCE | 0.85 | 2.5 | False | 1.0 |
| ABUNDANT | 1.0 | 0.2 | False | 0.9 |
| HOSTILE | 0.9 | 1.2 | True | 1.1 |
| DEGRADED | 0.95 | 1.0 | False | 2.5 |

## Observed natural recovery by profile

- **ABUNDANT**: avg natural rate=0.58 (n=5 seeds)
- **BALANCED**: avg natural rate=0.58 (n=5 seeds)
- **DEGRADED**: avg natural rate=0.54 (n=5 seeds)
- **HIGH_NATURAL**: avg natural rate=0.91 (n=5 seeds)
- **HOSTILE**: avg natural rate=0.53 (n=5 seeds)
- **SCARCE**: avg natural rate=0.48 (n=5 seeds)

## Profile integrity note

HIGH_NATURAL shows elevated natural rates vs SCARCE/BALANCED when measured — profile overlays affect oracle natural probability via `natural_recovery_multiplier`.
SCARCE `capacity_scarcity_factor=2.5` is documented but **not wired** to benchmark ResourceCapacities in M13 runner (implementation gap).
