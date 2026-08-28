# PAYVANTA — Implementation Plan (M0)

**Status:** Planning artifact — no application code yet  
**Phase:** M0 Specification Audit complete  
**Readiness:** READY WITH MINOR ASSUMPTIONS  
**Date:** 2026-08-21

---

## 1. Architecture summary

REVIVE is a **cycle-based batch decision system** for constrained revenue recovery. Signals are ingested continuously; every virtual-time cycle the full opportunity pool is diagnosed, priced, allocated under shared resource constraints, gated, executed (via simulators), verified, and optionally learned from.

### Frozen loop

```
SEE → UNDERSTAND → SIMULATE → PRIORITIZE → GUARD → ACT → VERIFY → LEARN
```

### Economic core (build this first)

```
Revenue at risk
  → Candidate actions (incl. NO_ACTION)
  → Expected outcomes (p, p∅, uplift, costs)
  → ENRV per candidate
  → Multi-constraint allocation
  → Guardrail validation
  → Simulated execution
  → Measured recovery + attribution
  → Benchmark vs baselines
```

### Authoritative architecture sources

| Concern | Document |
|---------|----------|
| Components & data flow | `docs/07-system-architecture.md` |
| Module roster & permissions | `docs/08-agent-architecture.md` |
| Decision pipeline & ENRV | `docs/09-decision-engine.md`, `docs/11-counterfactual-engine.md` |
| Allocator | `docs/10-recovery-allocation.md` |
| Gates | `docs/13-policy-and-guardrails.md` |
| Stopping rules | `docs/14-stopping-rules.md` |
| State machines | `docs/34-state-machine.md` |
| Data model | `docs/17-data-model.md` |
| Synthetic environment + oracle | `docs/19-synthetic-dataset.md` |
| Benchmark & evaluation | `docs/20-benchmark.md`, `docs/21-evaluation.md` |
| Metrics | `docs/37-metrics-dictionary.md` |
| Binding rules | `docs/32-implementation-contract.md` |

### Technology (PROPOSED — ADR-010 frozen at build start)

| Layer | Choice | Source |
|-------|--------|--------|
| Engine language | Python 3.11+ | `docs/07-system-architecture.md` §5 |
| Storage | SQLite (`revive.db`) | Same |
| Optimisation | Lagrangian relaxation + greedy fallback | `docs/10-recovery-allocation.md`, ADR-007 |
| Prediction | Bayesian cell model (Beta-Binomial) | ADR-006 |
| API | HTTP/JSON | `docs/18-api-contracts.md` |
| UI | SPA reading precomputed artefacts + API | `docs/25-ui-ux-spec.md`, `RR-NFR-034` |
| LLM | Optional; cached & seed-keyed; **never in money path** | `RR-GUARD-020`, `RR-NFR-035` |
| Integrations | **SIMULATED** adapters only | `docs/36-razorpay-integration-assumptions.md` |

---

## 2. Proposed repository structure

```text
razorpay_buildathon/
├── docs/                          # Frozen specification (do not rewrite)
├── implementation/                # Planning artefacts (this folder)
│   ├── implementation-plan.md
│   ├── dependency-map.md
│   ├── open-blockers.md
│   ├── implementation-decisions.md
│   ├── deviations.md              # Created when deviations occur
│   └── checkpoints/               # Per-milestone records (M1+)
├── revive/
│   ├── __init__.py
│   ├── config/                    # Versioned policy packs, merchant config, seeds
│   ├── domain/                    # Typed models (Paise, IDs, enums)
│   ├── db/                        # Schema, migrations, repositories
│   ├── clock/                     # Virtual clock (injected)
│   ├── rng/                       # Labelled PRNG streams
│   ├── generator/                 # C-25 synthetic dataset + hidden oracle partition
│   ├── see/                       # C-01, C-02, C-03
│   ├── understand/                # C-04, C-05 (+ optional LLM cache)
│   ├── simulate/                  # C-06…C-10, C-07 predictor, C-08 cost, C-09 ENRV
│   ├── prioritize/                # C-11 pre-filter, C-12 allocator
│   ├── guard/                     # C-13 gates, C-14 stopping, C-15 approval, C-16 ledger
│   ├── act/                       # C-17 execution, C-18 adapters (simulators)
│   ├── verify/                    # C-19, C-20
│   ├── learn/                     # C-21 (P1)
│   ├── audit/                     # C-22 hash chain
│   ├── orchestrator/              # C-23 cycle runner
│   ├── benchmark/                 # C-24 harness, baselines B0–B6, oracle ceiling
│   ├── metrics/                   # C-26 report + MetricSnapshot
│   ├── api/                       # C-27 HTTP service
│   └── cli/                       # `revive benchmark --seed N`, `revive demo`, etc.
├── tests/
│   ├── unit/                      # Named RR-* / T-* tests
│   ├── integration/
│   ├── safety/
│   └── benchmark/
├── ui/                            # SPA (React or similar — not mandated by spec)
├── artefacts/                     # Generated run outputs (gitignored)
├── pyproject.toml
└── README.md                      # Run instructions only; no fabricated metrics
```

---

## 3. P0 / P1 / P2 classification

Aligned with `docs/32-implementation-contract.md` §2 and user master prompt §11–13.

### P0 — Mandatory (judging story)

| ID | Area | Key requirements |
|----|------|------------------|
| P0.1 | Synthetic environment | `RR-DATA-*`, `docs/19-synthetic-dataset.md`, hidden oracle, labelled PRNG streams |
| P0.2 | Baseline policy | B0–B3 (+ oracle reference); `docs/20-benchmark.md` |
| P0.3 | Revenue-risk detection | `RR-FUNC-001`…`005`, `007` |
| P0.4 | Candidate interventions | `RR-FUNC-020`, `021`, action catalogue from `docs/11-counterfactual-engine.md` |
| P0.5 | Counterfactual / ENRV | `RR-FUNC-023`…`028`, `docs/11-counterfactual-engine.md` |
| P0.6 | Recovery allocation | `RR-FUNC-030`…`034`, `037`, `039`; ≥4 binding constraints |
| P0.7 | Guardrails | `RR-GUARD-001`…`012`, `020`…`026` |
| P0.8 | Stopping rules | `RR-FUNC-050`, `051`; SR-01…SR-11 |
| P0.9 | Execution simulator | `RR-FUNC-060`…`065`, `063`; idempotency, audit-before-effect |
| P0.10 | Outcome measurement | `RR-FUNC-070`…`073`, attribution |
| P0.11 | Batch benchmark | `RR-BENCH-001`…`007`; ≥20 seeds; paired comparison |
| P0.12 | Incremental recovery metric | `M-10`, `docs/37-metrics-dictionary.md` |
| P0.13 | Audit trail | `RR-AUDIT-001`…`010`; hash chain |
| P0.14 | Core command center UI | `RR-UI-001`…`008` (all 7 screens) |

### P1 — After P0 end-to-end works

- Cohort degradation (`RR-FUNC-006`), ageing buckets (`008`)
- LLM-assisted diagnosis/copy (`016`, `024`, `029`, `044`)
- Shadow prices (`035`), exploration budget (`036`), fallback allocator visibility (`038`)
- Learning engine (`080`, `081`), extra actions (WhatsApp, dunning, mandate retry, PTP)
- Baselines B4–B6, full observability (`docs/24-observability.md`)

### P2 — Only if P0 stable

- `VOICE_CALL` / Hinglish (`RR-FUNC-022`)
- Subscription pre-failure (`009`)
- NL policy compilation (`RR-GUARD-027`)
- Real Razorpay sandbox adapter (conditional, `UNVERIFIED`)

---

## 4. Milestone plan (M0–M19)

| Milestone | Deliverable | Primary docs | Exit criteria |
|-----------|-------------|--------------|---------------|
| **M0** | Audit + this plan | All `docs/` | Plan approved (this step) |
| **M1** | Project foundation | `17`, `34`, `32` | Repo layout, pyproject, DB schema skeleton, virtual clock, PRNG, CI test runner |
| **M2** | Synthetic environment | `19`, `17` §4.8 oracle | Generator + oracle partition; `dataset_hash`; AI-6 test (policy cannot read oracle) |
| **M3** | Baseline policies B0–B3 | `20` §2 | Baselines run on same dataset; B0 natural-recovery floor measurable |
| **M4** | Revenue Sentinel | `12`, `05` SEE | `RR-FUNC-001`…`005`, `007` tests pass |
| **M5** | Context + diagnosis | `08` C-04/C-05, `12` §9 | `RR-FUNC-010`…`015`, `011`, `012` |
| **M6** | Action model + catalogue | `11` §3 | `RR-FUNC-020`, `021`; ≥3 candidates incl. NO_ACTION |
| **M7** | Predictor + cost + ENRV | `11`, `09` | `RR-FUNC-023`…`028`; hand-computed ENRV fixtures |
| **M8** | Counterfactual evaluator | `11` | Component-sum reconstruction; negative uplift retained |
| **M9** | Allocator | `10` | `RR-FUNC-030`…`034`, `037`, `039`; ≥4 binding constraints in report |
| **M10** | Guardrails + stopping | `13`, `14` | All gates + SR-01…11; single execution path test |
| **M11** | Execution simulator | `15`, `23` | Adapters + idempotency + two-phase ledger |
| **M12** | Outcome + attribution | `21` §5 | `RR-FUNC-070`…`073` |
| **M13** | Benchmark harness | `20`, `21` | Multi-seed CLI; byte-identical artefacts (`RR-NFR-020`) |
| **M14** | Learning (P1) | `35` | Posterior update; cannot write policy |
| **M15** | API layer | `18` | REST contracts for UI + benchmark artefacts |
| **M16** | UI (7 screens) | `25`, `26` | All screens bind to artefacts; synthetic disclosure |
| **M17** | Audit / observability integration | `16`, `24` | Chain verify on every run; structured logs |
| **M18** | Full E2E integration | `38`, `30` | One complete recovery scenario + benchmark comparison |
| **M19** | Demo readiness | `26`, `27` | 5-min demo script; judging criteria mapping verified |

Each milestone: **implement → test → verify → checkpoint → next**.

---

## 5. Requirement → component → data → test → demo

Sample trace rows (full matrix in `docs/38-traceability-matrix.md`):

| Requirement | Component | Data artefact | Test | Demo |
|-------------|-----------|---------------|------|------|
| `RR-FUNC-001` | C-02 Revenue Sentinel | `RevenueOpportunity` | `T-FUNC-001`, `002` | Beat 2 — leakage view |
| `RR-FUNC-027` | C-09 Counterfactual Evaluator | `ActionCandidate.enrv_paise` | `T-FUNC-027` | Beat 3 — counterfactual table |
| `RR-FUNC-030` | C-12 Allocator | Allocation report, shadow prices | `T-FUNC-030` | Beat 4 — allocation view |
| `RR-GUARD-001`…`012` | C-13 Policy Engine | `GateVerdict` | `T-POL-001`…`018` | Beat 5 — guardrail status |
| `RR-FUNC-060` | C-17 Execution Agent | `Intervention`, idempotency | `T-FUNC-060` | Beat 7 — execute |
| `RR-BENCH-001` | C-24 Benchmark | `artefacts/run_*/metrics.json` | `T-EVAL-*` | Beat 10 — benchmark lab |
| `RR-AUDIT-001` | C-22 Audit Store | `AuditEvent` chain | `T-SAF-008` | Beat 9 — audit trail |
| `M-10` | C-26 Metrics | Paired seed diff | `T-EVAL-003` | Beat 6/10 — incremental ₹ |

---

## 6. Benchmark strategy

1. **Single command:** `revive benchmark --profile BALANCED --seed <n> --policies REVIVE,B0,B1,B2,B3` (extend to B6 in P1).
2. **Held fixed:** dataset hash, oracle, policy pack, strategy version, capacities, horizons, cost model, attribution code (`docs/20-benchmark.md` BF-1…BF-10).
3. **Primary metric:** `M-10` paired difference per seed vs best baseline; report median, min, max, seeds lost.
4. **Integrity:** Policy code never reads oracle partition (`AI-6`); no `if policy == REVIVE: boost recovery` paths.
5. **Honesty:** Report F-1…F-6 falsification conditions, limitations section, adverse findings (`RR-FUNC-091`).
6. **Reproducibility:** Byte-identical metric JSON at same seed (`RR-NFR-020`); LLM cache required for any LLM in benchmark path.

---

## 7. Testing checkpoints

Per `docs/30-test-plan.md`:

| Suite | When | Examples |
|-------|------|----------|
| Unit | Every milestone touching logic | ENRV arithmetic, gate verdicts, state transitions |
| Integration | M10+ | signal → opportunity → decision → gate → execution → outcome |
| Safety | M10+ | policy bypass, duplicate execution, contact cap, invalid discount |
| Benchmark | M13 | baseline fairness, reproducibility, metric formulas |
| E2E | M18 | full recovery scenario per demo script |

Naming: tests include requirement ID in name (`RR-NFR-081`).

---

## 8. Estimated complexity by module

| Module | Complexity | Notes |
|--------|------------|-------|
| Generator + oracle | **High** | Behavioural model, latent traits, adversarial cases |
| Revenue Sentinel | Medium | Dedup + 4 risk classes |
| Predictor (Bayesian cells) | **High** | p(a), p(∅), shrinkage, calibration |
| Allocator (Lagrangian) | **High** | 6 resources, shadow prices, timeout/fallback |
| Policy engine (12 gates) | **High** | Many edge cases; must be exhaustive |
| Execution + ledger | Medium | Two-phase reserve; idempotency |
| Audit hash chain | Medium | Append-only; crash safety |
| Benchmark harness | **High** | 8 policies × profiles × seeds |
| UI (7 screens) | Medium | Mostly read-only artefact binding |
| LLM integration | Low–Medium | Optional P1; cache discipline |

**Critical path:** M2 → M7 → M9 → M11 → M13 → M16.

---

## 9. Risks (summary)

| Risk | Mitigation |
|------|------------|
| Scope explosion (voice, real Razorpay) | Scope firewall; P2 only |
| Benchmark tuning to win | Pre-registered F-1…F-6; ABUNDANT profile; report losses |
| Allocator time budget | Greedy fallback (`RR-FUNC-038` SHOULD); record `allocator_mode` |
| LLM nondeterminism | `LLM_OFF` default for benchmark; cache for any LLM use |
| Hackathon timebox | P0 first; cut P2 then P1, never P0 |
| Oracle leakage | Separate DB partition + static import guard test |

Full register: `docs/28-risk-register.md`.

---

## 10. Implementation readiness verdict

**READY WITH MINOR ASSUMPTIONS**

- Specification is complete for MVP; no code exists yet (expected).
- No CRITICAL doc contradictions (`docs/36b-documentation-consistency-check.md`).
- 15 open numeric decisions have PROPOSED defaults (`docs/40-open-questions.md`); use defaults + ADR + sensitivity runs.
- Razorpay integration explicitly **UNVERIFIED** — simulators only.
- Traceability matrix: no unresolved MUST gaps (`docs/38-traceability-matrix.md` §3).

**Hard stop:** Await plan approval before M1 implementation.
