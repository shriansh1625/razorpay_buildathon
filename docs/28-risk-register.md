# 28 · Risk Register

Risks that could cause disqualification, an unconvincing demo, or an unsound submission are
prioritised highest. Every risk has a detection signal and a contingency.

---

## 1. Severity scale

| Likelihood | Description |
|---|---|
| HIGH | Expected to occur without mitigation |
| MEDIUM | Plausible; has occurred in similar projects |
| LOW | Unlikely but possible |

| Impact | Description |
|---|---|
| CRITICAL | Disqualification, fundamentally broken submission, safety failure |
| HIGH | Major feature gap, broken demo, untrustworthy results |
| MEDIUM | Reduced quality, incomplete evidence, partial capability |
| LOW | Cosmetic, minor inconvenience |

| Severity | Calculation |
|---|---|
| **S1 — Critical** | Any CRITICAL impact, or HIGH × HIGH |
| **S2 — High** | HIGH × MEDIUM, or MEDIUM × HIGH |
| **S3 — Medium** | MEDIUM × MEDIUM, or HIGH × LOW |
| **S4 — Low** | LOW × LOW, or LOW × MEDIUM |

---

## 2. Risk table

### Product risks

| ID | Risk | Category | Likelihood | Impact | Severity | Mitigation | Detection signal | Contingency | Owner role | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| R-P01 | Product scope drifts beyond Track 03 during implementation | Product | MEDIUM | CRITICAL | S1 | Scope firewall procedure ([03](03-scope-boundaries.md)); implementation contract ([32](32-implementation-contract.md)) | Feature added without scope-firewall pass | Remove feature; record ADR | Product owner | Open |
| R-P02 | Optimisation objective changes silently from ENRV to a simpler metric | Product | MEDIUM | CRITICAL | S1 | Frozen objective in README § C-5; `M-10` as sole primary metric | `M-10` not computed as paired difference; or allocation not constrained | Revert; re-run benchmark | Product owner | Open |
| R-P03 | "Do nothing" is not treated as a valid action | Product | LOW | HIGH | S3 | `NO_ACTION` required in every candidate set (`RR-FUNC-020`); `M-15` reports no-action share | `M-15 = 0` with a non-trivial dataset | Refactor candidate generation | Engineer | Open |

### Engineering risks

| ID | Risk | Category | Likelihood | Impact | Severity | Mitigation | Detection signal | Contingency | Owner role | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| R-E01 | Benchmark is not reproducible (nondeterminism) | Engineering | HIGH | CRITICAL | S1 | Labelled PRNG streams; virtual clock; no wall-clock dependency; `M-46` check | `M-46 = FAIL` | Trace nondeterminism source (unsorted collections, floating-point ordering, unseeded randomness) | Engineer | Open |
| R-E02 | Allocator does not solve under constraints (trivial greedy only) | Engineering | MEDIUM | HIGH | S2 | Greedy fallback is acceptable but must be labelled; primary allocator should handle ≥ 4 constraints | `M-34 = 1.0` (always fallback); no shadow prices | Implement Lagrangian relaxation or constraint-aware greedy | Engineer | Open |
| R-E03 | State machine has illegal transitions in production | Engineering | MEDIUM | HIGH | S2 | Exhaustive illegal-pair sweep test ([34 § 7](34-state-machine.md)); `M-22` check | `M-22 > 0`; crash-resume test failure | Fix transition guard; re-run benchmark | Engineer | Open |
| R-E04 | Audit hash chain breaks during a run | Engineering | LOW | HIGH | S3 | Chain verification at run end (`M-58`); write-before-effect rule | `M-58 = FAIL` | Investigate; run invalidated; fix and re-run | Engineer | Open |
| R-E05 | Cycle takes too long; demo times out | Engineering | MEDIUM | MEDIUM | S3 | Allocator time budget (`RR-FUNC-039`); greedy fallback | `M-52` exceeds target; demo stalls | Reduce batch size for demo; use greedy fallback | Engineer | Open |
| R-E06 | Two-phase reservation leaks capacity | Engineering | LOW | HIGH | S3 | Orphan-reclaim at cycle open; invariant check after every transition | `reservations_leaked > 0`; `M-22 > 0` | Fix leak; add cycle-close sweep assertion | Engineer | Open |

### Data risks

| ID | Risk | Category | Likelihood | Impact | Severity | Mitigation | Detection signal | Contingency | Owner role | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| R-D01 | Synthetic dataset does not create genuine scarcity | Data | MEDIUM | HIGH | S2 | `SCARCE` profile; verify binding constraints exist (`M-29`, `M-32`) | No resource near saturation on the benchmark batch | Adjust generator parameters; add scarcity profile | Engineer | Open |
| R-D02 | Natural recovery rate is zero (trivialises uplift) | Data | MEDIUM | HIGH | S2 | `HIGH_NATURAL` profile; `p(i,∅) > 0` for a meaningful share | `M-07 = 0` on all profiles | Fix generator behavioural model | Engineer | Open |
| R-D03 | Synthetic dataset does not exercise all gates and stopping rules | Data | MEDIUM | MEDIUM | S3 | Generator designed for coverage ([19 § 1](19-synthetic-dataset.md) DS-5) | `M-55` gap list non-empty for a gate or rule | Add adversarial cases to exercise the gap | Engineer | Open |
| R-D04 | Privacy canaries are not planted or not detected | Data | LOW | MEDIUM | S3 | DS-10; `M-57` scan | `M-57` not computed or canaries absent | Add canaries; verify scan pipeline | Engineer | Open |

### AI/ML risks

| ID | Risk | Category | Likelihood | Impact | Severity | Mitigation | Detection signal | Contingency | Owner role | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| R-A01 | Predictor is badly calibrated | AI/ML | MEDIUM | HIGH | S2 | `M-24` calibration reporting; reliability curve; shrinkage to parent cells | High ECE or Brier score; reliability curve off-diagonal | Recalibrate; if time-constrained, use simpler model with wider `sigma` | Engineer | Open |
| R-A02 | LLM diagnosis produces out-of-taxonomy outputs | AI/ML | LOW | MEDIUM | S3 | Schema validation; closed-set constraint; deterministic fallback | `M-50 > 0`; out-of-taxonomy outputs in eval | Tighten schema; rely on deterministic path | Engineer | Open |
| R-A03 | LLM prompt injection succeeds | AI/ML | LOW | HIGH | S3 | Injection test corpus; untrusted-data treatment; closed-set output | Injection corpus test failure | Disable LLM path; use deterministic-only | Engineer | Open |
| R-A04 | Learning engine degrades calibration | AI/ML | LOW | MEDIUM | S3 | Rollback on degradation; ablation comparison | `M-24` worsens post-learning | Disable learning; report learning-off results | Engineer | Open |

### Security risks

| ID | Risk | Category | Likelihood | Impact | Severity | Mitigation | Detection signal | Contingency | Owner role | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| R-S01 | PII leaks into logs, audit events, or LLM prompts | Security | LOW | HIGH | S3 | Never-log list; LLM context stripping; privacy canaries (`M-57`) | `M-57 > 0` | Trace leak; fix pipeline; re-run | Engineer | Open |
| R-S02 | API keys committed to version control | Security | LOW | MEDIUM | S4 | Environment variables; .gitignore; pre-commit hook | Key pattern in repo scan | Rotate key; add to .gitignore | Engineer | Open |

### Financial safety risks

| ID | Risk | Category | Likelihood | Impact | Severity | Mitigation | Detection signal | Contingency | Owner role | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| R-F01 | Action executes without gate approval | Financial | LOW | CRITICAL | S1 | Single execution path (`RR-GUARD-021`); `M-16` independently computed | `M-16 > 0` | Build failure; fix and re-run | Engineer | Open |
| R-F02 | Duplicate financial action | Financial | LOW | HIGH | S3 | Idempotency keys; G9 duplicate suppression; state machine guards | Duplicate intervention in audit chain | Fix idempotency; re-run | Engineer | Open |
| R-F03 | Incentive exceeds merchant ceiling | Financial | LOW | HIGH | S3 | G5 four-ceiling clamp; G12 amount sanity; `RR-GUARD-020` | Executed incentive > ceiling in audit | Fix G5 implementation; re-run | Engineer | Open |

### Evaluation risks

| ID | Risk | Category | Likelihood | Impact | Severity | Mitigation | Detection signal | Contingency | Owner role | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| R-V01 | REVIVE does not beat any baseline | Evaluation | MEDIUM | CRITICAL | S1 | Pre-registered falsification conditions; multiple baselines; dataset designed for allocation advantage | `M-10 ≤ 0` against best baseline (F-1) | Report honestly; investigate; do not fabricate | Product owner | Open |
| R-V02 | Results are cherry-picked across seeds | Evaluation | LOW | HIGH | S3 | Pre-registered seed set; all seeds reported; min/max/loss count | Seed set differs from declared set | Use declared set; report all seeds including bad ones | Product owner | Open |
| R-V03 | Evaluation report omits limitations | Evaluation | MEDIUM | MEDIUM | S3 | Mandatory limitations and adverse-findings sections (`RR-FUNC-091`) | Report generation fails if sections empty | Write honest limitations | Product owner | Open |

### Demo risks

| ID | Risk | Category | Likelihood | Impact | Severity | Mitigation | Detection signal | Contingency | Owner role | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| R-D05 | Demo exceeds 5 minutes | Demo | MEDIUM | MEDIUM | S3 | Scripted beats with timing budget ([26](26-demo-script.md)) | Rehearsal exceeds 5:00 | Cut beat detail; pre-navigate to screens | Product owner | Open |
| R-D06 | Demo screen shows an error or empty state | Demo | MEDIUM | MEDIUM | S3 | Pre-flight check; test all screens before demo | Screen error during rehearsal | Have a recorded backup; fix and retry | Engineer | Open |
| R-D07 | Demo numbers don't match the artefact | Demo | LOW | HIGH | S3 | All numbers from artefact; no hard-coded values | Manual comparison pre-demo | Re-generate artefact; use latest | Engineer | Open |

### Scope risks

| ID | Risk | Category | Likelihood | Impact | Severity | Mitigation | Detection signal | Contingency | Owner role | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| R-SC01 | Implementation adds features outside Track 03 | Scope | MEDIUM | HIGH | S2 | Scope firewall; implementation contract | Feature not in scope boundary doc | Remove before submission | Product owner | Open |
| R-SC02 | Specification is too large to implement in hackathon timebox | Scope | HIGH | HIGH | S1 | Priority tiers (P0/P1/P2); smallest-implementation principle | P0 items incomplete near deadline | Cut P1/P2; deliver P0 only | Product owner | Open |

---

## 3. Top risks by severity

| Rank | Risk ID | Description | Severity |
|---|---|---|---|
| 1 | R-P01 | Scope drift beyond Track 03 | S1 |
| 2 | R-P02 | Objective changes silently | S1 |
| 3 | R-E01 | Benchmark not reproducible | S1 |
| 4 | R-F01 | Action without gate approval | S1 |
| 5 | R-V01 | REVIVE doesn't beat baselines | S1 |
| 6 | R-SC02 | Spec too large for timebox | S1 |
| 7 | R-E02 | Allocator doesn't solve under constraints | S2 |
| 8 | R-D01 | No genuine scarcity in dataset | S2 |
| 9 | R-D02 | Zero natural recovery rate | S2 |
| 10 | R-A01 | Poor calibration | S2 |
| 11 | R-SC01 | Out-of-scope features added | S2 |
