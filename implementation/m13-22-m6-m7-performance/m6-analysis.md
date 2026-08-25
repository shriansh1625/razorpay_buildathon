# M6 Analysis — Candidate Generation

## Call volume

~753k `generate_candidates` / cell → ~5.55M `evaluate_feasibility` + SHA-256 candidate IDs.

## Repeated work found

| Work | Scope | Verdict |
|------|--------|---------|
| `class_actions` dict rebuilt every feasibility call | immutable | **Hoisted** to module `frozenset` table |
| `config_from_policy_pack` per opportunity | cell (sealed PolicyPack) | **Cached** on `ReviveRunState.candidate_cfg()` |
| SHA-256 via hexdigest + 26 hex-pair parses | per candidate | **Equivalent digest-byte mapping** (`digest[i] & 31`) |
| `json.dumps` of empty params | per A00/A01 | Fast-path `"{}"` |
| Action catalogue `resources_for` | already module-constant | no change |
| Cause/action enumeration | already module tables | no change |

## Cache declarations

| Cache | Scope | Key | Lifetime | Invalidation |
|-------|-------|-----|----------|--------------|
| `CandidateConfig` | cell | PolicyPack metadata | `ReviveRunState` | new cell / new pack |
| `_CLASS_ACTIONS` | immutable world | RiskClass | process | never (code constant) |

No global mutable caches. No reuse after observable state changes.

## Semantic test

Pre-opt vs post-opt 15-cycle seed=2 BALANCED:

- `m6_hash` identical: `b9af5e6f94cf16997a1fa4be600130396041ac6c379aa672dbaeb1b2d070879f`
