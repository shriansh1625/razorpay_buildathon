# M2 Checkpoint — Synthetic Environment + Hidden Outcome Oracle

**Milestone:** M2 — Synthetic Dataset Generator + Hidden Outcome Oracle  
**Date:** 2026-08-21  
**Status:** COMPLETE  
**Authorization:** M2 MASTER IMPLEMENTATION PROMPT

---

## Implemented

| Component | Location |
|-----------|----------|
| Generator config + profiles | `revive/simulation/config.py`, `profiles.py`, `types.py` |
| Domain entity models | `revive/simulation/models.py`, `world.py` |
| Latent traits (hidden) | `revive/simulation/latent.py` |
| Generator engine | `revive/simulation/generator.py` |
| Oracle partition (isolated) | `revive/simulation/oracle/_partition.py` |
| Oracle resolve API (evaluator boundary) | `revive/simulation/oracle/resolve.py` |
| Observation interface | `revive/simulation/observation.py` |
| Validation + invariants | `revive/simulation/validation.py` |
| Manifest + distributions | `revive/simulation/manifest.py`, `distributions.py` |
| IO + replay | `revive/simulation/io.py`, `replay.py` |
| Dev fixtures | `revive/simulation/fixtures.py` |
| Import-boundary guard (AST) | `revive/integrity/boundaries.py` |
| CLI dev command | `revive generate-dataset` |
| M2 tests | `tests/simulation/` (6 modules) |

---

## Generator architecture

Generation order follows `docs/19 §2.2`:

1. Merchant → customers (with latent traits in oracle partition)
2. Instruments, commercial history per risk class
3. Environmental degradation windows
4. Revenue opportunities + signals
5. Oracle rows fixed at generation (`OR-2`)
6. Adversarial injections (HOSTILE profile / flags)
7. Signal hygiene faults (optional)
8. Privacy canaries

Structured relationships (not independent random outcomes):

- `intent_to_pay` drives natural recovery (shared latent with action outcomes)
- `instrument_health` + degradation windows affect retry timing (A01 vs A02)
- `responsiveness` / `price_sensitivity` affect reminder vs incentive outcomes
- Fatigue curve monotone non-increasing per customer
- Value/recoverability negative correlation (profile parameter)

---

## Observable vs hidden

| Observable | Hidden (oracle partition only) |
|------------|--------------------------------|
| Transaction amount, failure reason, timestamps | `intent_to_pay`, latent traits |
| Customer segment, tenure, value band, prior self-recovery rate (noisy) | True responsiveness, annoyance threshold |
| Checkout stage, invoice ageing | `per_action_response` pre-drawn outcomes |
| Prior contacts, degradation window membership (observable flag) | Fatigue curve internals tied to latent sensitivity |

`get_observable_state()` never returns hidden keys — validated in tests.

---

## Oracle boundary

- Physical separation: `dataset/oracle/partition.json` vs `domain/observable_world.json`
- Module separation: `revive.simulation.oracle._partition` / `latent` forbidden to decision path
- Public oracle API: `resolve_outcome(partition, ...)` only — no truth-leaking getters
- Decision modules (`recovery`, `allocation`, `policy`) cannot import oracle internals (AST-checked)

---

## Profiles supported

All six from `docs/19 §2.3`:

| Profile | Purpose |
|---------|---------|
| `BALANCED` | Primary mixed benchmark profile |
| `HIGH_NATURAL` | Elevated natural recovery — punishes over-contacting |
| `SCARCE` | Capacity scarcity stress |
| `ABUNDANT` | Near-unlimited capacity — expected null advantage |
| `HOSTILE` | Adversarial injection + fatigue stress |
| `DEGRADED` | Elevated payment degradation windows |

---

## Seed / replay behavior

- Master seed + labelled PRNG streams (`generator`, `oracle`, `customer_generation`, etc.)
- `config.config_hash()` stable for identical configuration
- `dataset_hash` includes world counts + config hash
- `replay_dataset(config)` reproduces identical `dataset_hash`
- `revive generate-dataset --seed N` writes artefacts under `artefacts/datasets/`

---

## Validation

- Referential integrity (customer ↔ opportunity ↔ oracle row)
- Temporal ordering (detected < window expiry)
- Invoice DM-1 invariant
- Oracle fatigue monotonicity
- Observable payload hidden-key scan
- Duplicate signal dedupe allowed only when `duplicate_signal` injection flagged

---

## Test results

```text
48 passed in 0.25s
```

Includes: reproducibility, oracle isolation, natural recovery, action variation, profile differences, replay, manifest IO, realism smoke tests.

---

## Development-scale configuration

| Parameter | Dev default |
|-----------|-------------|
| `customer_count` | 40 |
| `opportunity_count` | 80 |
| `simulation_window_days` | 30 |
| Tiny fixture config | 8 customers, 12 opportunities |

**Not** the official benchmark scale. ADR-012 pending for frozen benchmark N.

---

## Known limitations

- Distribution shapes are **invented** (`docs/19 §10`) — `UNVERIFIED` against real payments
- Oracle rows pre-drawn at generation — runtime contact fatigue applied via `fatigue_curve` multiplier
- Adversarial case library is a **subset** of `docs/19 §6` (expandable in later milestones)
- No LLM, UI, allocator, benchmark harness, or baseline policies
- Risk class enum uses M1 names (`SUBSCRIPTION_FAILURE`, `RECEIVABLE_OVERDUE`) — maps to doc 19 substrate semantics

---

## Assumptions

1. ε and action costs remain provisional (PolicyPack DRAFT)
2. Development data — **no benchmark claims**
3. Policy-neutral oracle — no policy identity in `resolve_outcome`
4. Latent traits stored only in oracle partition JSON

---

## Deviations

None recorded. See `implementation/implementation-decisions.md` §12 for M2 notes.

---

## Next milestone

**M3 — Baseline Policies** — **NOT AUTHORIZED**. Explicit approval required.

---

> **No benchmark claims have been made from M2 development data.**
