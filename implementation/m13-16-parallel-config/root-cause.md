# M13.16 Root Cause

**Bug:** Official parallel workers failed with `official_benchmark_config requires a SEALED PolicyPack (got status=DRAFT)`.

## Trace

1. Parent: `execute_benchmark(mode=BenchmarkMode.OFFICIAL)` → `benchmark_mode = mode.value` → **`"OFFICIAL"`** (uppercase)
2. Parent: `run_cell_benchmark_parallel(..., mode="OFFICIAL")` submits worker with sealed config hash in store context
3. Worker: `run_seed_profile_group(..., mode="OFFICIAL")`
4. Worker (old code): `pack = official_sealed_policy_pack() if mode == "official" else default_draft_policy_pack()`
   - `"OFFICIAL" == "official"` → **False**
   - Worker selects **`default_draft_policy_pack()`** (`pol_m1_draft`, DRAFT)
5. Worker (old code): `config_from_worker_payload()` sees `benchmark_id == OFFICIAL_BENCHMARK_ID` → calls `official_benchmark_config(policy_pack=DRAFT)` → **FAIL**

## First divergence point

Step 4 — case-sensitive mode check combined with absent serialized PolicyPack.

Windows spawn did not cause PolicyPack mutation; the worker **reconstructed DRAFT by design** due to the mode string mismatch.

## Fix

- Serialize exact parent `PolicyPack` in worker payload (`policy_pack_to_frozen_payload`)
- Reconstruct with `policy_pack_from_frozen_payload(..., require_sealed=True)` for official runs
- Fail closed on hash/version/status mismatch
- Stop relying on `mode == "official"` lowercase heuristic
