# 20 · Benchmark Design

The Track 03 bar asks for **measured money recovered across a batch**. This document specifies the
measurement. It contains no results, and it is written before any run exists (`RR-BENCH-008`).

> **No performance number appears in this document, and none may be added to it later.** Results live
> only in generated artefacts ([21-evaluation.md](21-evaluation.md) § 8). If a figure ever appears in
> this file, the file has been corrupted.

---

## 1. The claim under test

Pre-registered, falsifiable, and narrow:

> **Claim C.** Under a fixed synthetic environment with scarce recovery capacity, allocating recovery
> effort by expected net recovery value (ENRV) produces more incremental net recovered revenue, per
> unit of cost and per customer contact, than each of six reference policies, while satisfying the same
> guardrails and stopping rules.

### 1.1 Scope of the claim

| The claim **is** | The claim **is not** |
|---|---|
| About one synthetic environment | About real payment behaviour |
| A comparison between policies on identical inputs | An absolute recovery-rate claim |
| About allocation under scarcity | A claim that REVIVE wins when capacity is abundant (§ 6.3) |
| Conditional on the generator's fidelity, which is `UNVERIFIED` | Evidence about Razorpay's rails, merchants, or customers |

### 1.2 Pre-registered falsification conditions

Claim C is **refuted** if any of the following holds in the declared seed set:

| # | Condition |
|---|---|
| F-1 | REVIVE's median paired advantage in `M-10` over the best baseline is ≤ 0 in the `BALANCED` profile |
| F-2 | REVIVE's advantage is achieved with more customer contacts per unit recovered than the best baseline (`M-13`) |
| F-3 | REVIVE's net advantage disappears once action costs and incentives are subtracted |
| F-4 | Any guardrail metric fails: `M-16 > 0`, `M-17 > 0`, or any `INVARIANT_VIOLATION` |
| F-5 | REVIVE recovers less than `B0 NO_ACTION` net of cost in any profile |
| F-6 | Results are not reproducible byte-for-byte at a fixed seed (`RR-NFR-020`) |

Writing F-1…F-6 down in advance is what distinguishes a benchmark from a demonstration. Any of them
occurring must be reported in the artefact headline, not resolved by re-tuning (`19 § 8.3`).

---

## 2. Baselines

Seven reference policies, each a policy REVIVE is plausibly compared to in practice, each implemented
against the **same** interfaces and subject to the **same** guardrails.

| ID | Baseline | Behaviour | What it isolates |
|---|---|---|---|
| `B0` | `NO_ACTION` | Never acts | The **natural recovery floor**. Any recovery above this is the only recovery REVIVE can claim credit for |
| `B1` | `FIXED_RETRY` | Fixed retry schedule per class, no targeting | The status quo in many systems (`15 § 7.1`) |
| `B2` | `CONTACT_ALL` | Acts on every eligible opportunity until capacity runs out, arbitrary order | Effort without prioritisation |
| `B3` | `GREEDY_ENRV` | Ranks by raw `ENRV`, ignores resource density | Isolates the **allocation** contribution specifically (`10 § 5`) |
| `B4` | `VALUE_RANK` | Ranks by `value_at_risk_paise` | "Chase the biggest" — the most common human heuristic |
| `B5` | `PROBABILITY_RANK` | Ranks by `p(i, a)`, ignoring the counterfactual | Isolates the **uplift** contribution (`11 § 5.2`) |
| `B6` | `RANDOM_ELIGIBLE` | Uniform random among eligible, seeded | Sanity floor. A policy that cannot beat `B6` is broken |

### 2.1 Why each baseline is necessary

| Question a reviewer will ask | Baseline that answers it |
|---|---|
| "Did anything you did matter at all?" | `B0` |
| "Isn't this just retry logic?" | `B1` |
| "Would contacting everyone do just as well?" | `B2` |
| "Is the allocator doing anything, or is scoring enough?" | `B3` |
| "Isn't chasing the largest amounts fine?" | `B4` |
| "Why do you need a counterfactual — why not just predict success?" | `B5` |
| "Is the whole thing noise?" | `B6` |

`B3` and `B5` are the two that matter most, because they attack the product's two specific claims. If
REVIVE does not beat `B5`, uplift modelling is unjustified. If it does not beat `B3`, the constrained
allocator is unjustified. Either result must be reported.

### 2.2 Baseline fairness rules

Non-negotiable, because the easiest way to fake a win is to handicap the baselines.

| # | Rule |
|---|---|
| BF-1 | **Identical dataset, identical oracle, identical seed.** Baselines are run on the same generated files, not regenerated |
| BF-2 | **Identical guardrails.** All twelve gates apply to every baseline. Baselines are not permitted to violate consent, caps, or windows |
| BF-3 | **Identical stopping rules.** All eleven apply |
| BF-4 | **Identical capacities and budgets** |
| BF-5 | **Identical horizon `H` and attribution logic** — the same code path computes recovery for every policy (`11 § 2`) |
| BF-6 | **Identical cost model.** Costs and incentives are charged by the same pricing code |
| BF-7 | Baselines get the **same predictor** where they need one (`B1`, `B5`), at the same `StrategyVersion` |
| BF-8 | Baselines are run in the **same execution engine**, differing only in the ranking/selection function |
| BF-9 | No baseline is given a deliberately poor parameter. `B1`'s retry schedule is a reasonable schedule, and it is published |
| BF-10 | Every baseline's full artefact set is published, not just its headline number |

BF-2 and BF-3 make the comparison *harder* for REVIVE, not easier: a guardrailed `B2 CONTACT_ALL` is a
much stronger opponent than an unconstrained one, because it stops doing the obviously harmful things
that would otherwise sink it. That is the point. The comparison must be against a competent baseline,
or the win is uninformative.

BF-9's published schedule matters because "we beat a strawman retry policy" is the single most likely
criticism of a result like this, and the only answer is to show the schedule.

---

## 3. Experimental design

### 3.1 Factors

| Factor | Levels |
|---|---|
| Policy | REVIVE, `B0`…`B6` (8 levels) |
| Profile | `BALANCED`, `HIGH_NATURAL`, `SCARCE`, `ABUNDANT`, `HOSTILE`, `DEGRADED` |
| Seed | A declared set, fixed before measurement (`PROPOSED` 20 per `RR-NFR-033`) |
| LLM mode | `LLM_OFF`, `LLM_DIAGNOSIS_ONLY`, `LLM_FULL` (REVIVE only; § 5.1) |
| Allocator mode | `LAGRANGIAN`, `EXACT`, `FALLBACK_GREEDY` (REVIVE only; § 5.2) |

### 3.2 Held fixed within a comparison

Everything else. A comparison is valid only if the two runs differ in **exactly one** factor: the same
seed, dataset hash, oracle, policy pack version, strategy version, capacities, horizons, `ε`, `λ_f`,
code version, and generator version. `config_hash` differing in any other field invalidates the
comparison, and the report tool checks this rather than trusting it.

### 3.3 Pairing

All comparisons are **paired by seed**. The reported quantity is the distribution of per-seed
differences, not the difference of pooled totals.

| Rule | Statement |
|---|---|
| Primary comparison | `M-10(REVIVE, seed) − M-10(baseline, seed)` for every seed |
| Reported | Every per-seed difference, the median, the min and max, and the count of seeds where REVIVE lost |
| **Not** reported as a headline | A single pooled percentage. Pooling hides seed variance and is the standard way a weak result is made to look strong |
| Losses are reported | `seeds_where_revive_lost` is a required field. Zero would itself be a suspicious result at small N |

### 3.4 Statistical honesty

| Rule | Statement |
|---|---|
| No significance test is claimed as authoritative at this seed count | `PROPOSED` report the paired difference distribution directly; if a test is reported, the seed count and its inadequacy are stated alongside |
| No confidence interval is presented as a population interval | The population is one synthetic generator, not a real market |
| Effect direction and dispersion are reported before any summary statistic | `RR-BENCH-003` |
| No p-value appears without the seed count adjacent to it | Anti-theatre |

The honest framing is: *this is a paired comparison on N seeds of one synthetic environment.* Anything
stronger would be a claim about reality that the dataset cannot support (`19 § 10`).

---

## 4. Procedure

```
FREEZE      parameters, policy pack, horizons, ε, λ_f, seed set, profiles   ──► config_hash
              (RR-BENCH-008; after this point, changes require full re-run)

GENERATE    revive generate --seed s --profile p          for every (s, p)
              ──► dataset files + oracle partition + dataset_hash

PREPARE     revive prepare --seed s --mode LLM_FULL       for every s
              ──► LLM cache populated. THE ONLY NETWORK-ENABLED PHASE (09 § 6.2)

EVALUATE    revive run      --seed s --policy REVIVE --mode m
            revive baseline --seed s --name  B0…B6
              ──► offline, deterministic; cache miss = hard error (RR-NFR-035)

VERIFY      revive verify   --run r        V-1…V-12 for every run
            revive replay   --run r        V-12 state reconstruction
              ──► any failure ⇒ run INVALIDATED ⇒ contributes no metrics (34 § 5.2)

REPRODUCE   re-run one seed end to end; revive diff must show byte identity (RR-NFR-020)

REPORT      revive report   ──► artefact set (§ 7), including failures and cost
```

| # | Rule |
|---|---|
| BP-1 | The PREPARE/EVALUATE split is mandatory. No measured run may make a live model call |
| BP-2 | An `INVALIDATED` run is reported as invalidated and **excluded from metrics but not from the run inventory** — the reader sees that it happened |
| BP-3 | Verification is part of the run, not a follow-up step (`16 § 5.3`) |
| BP-4 | The reproduction check runs on every benchmark invocation, not once at the start of the project |
| BP-5 | Partial matrices are declared. If a cell was not run, the report says which and why (`P-15`) |

---

## 5. Ablations

Ablations are how the package avoids claiming credit for components that contribute nothing.

### 5.1 LLM ablation

| Mode | Diagnosis | Copy | Purpose |
|---|---|---|---|
| `LLM_OFF` | Deterministic rules only | Static templates | The **floor**. If this matches `LLM_FULL`, the LLM adds nothing measurable and the package must say so |
| `LLM_DIAGNOSIS_ONLY` | LLM-assisted cause ranking | Static templates | Isolates diagnosis value |
| `LLM_FULL` | LLM-assisted | LLM-composed copy within slots | Full configuration |

`RR-BENCH-011`: the difference between `LLM_OFF` and `LLM_FULL` is a **reported number**, whatever its
sign. A negative or zero difference is published, because the alternative is asserting AI value without
measuring it — which is the specific failure this whole package is structured to avoid.

### 5.2 Allocator ablation

| Mode | Purpose |
|---|---|
| `EXACT` (ILP) | Upper reference. Reports `optimality_gap` for `LAGRANGIAN` where tractable (`10 § 6`) |
| `LAGRANGIAN` | Default |
| `FALLBACK_GREEDY` | Degraded path. Confirms the fallback is safe, not just present |

### 5.3 Component ablations

| Ablation | Removes | Question it answers |
|---|---|---|
| `NO_UPLIFT` | Uses `p(i,a)` instead of `u(i,a)` | Same question as `B5`, but inside REVIVE — isolates the counterfactual cleanly |
| `NO_FATIGUE` | Sets `λ_f = 0` | Does the fatigue term change behaviour or just the arithmetic? |
| `NO_UNCERTAINTY` | Point estimates only, no approval routing on width | Does uncertainty-aware escalation cost or save money? |
| `NO_EXPLORATION` | Pure exploitation | Does exploration pay for itself within the run's horizon? |
| `NO_SHRINKAGE` | Raw per-cell rates | Confirms hierarchical shrinkage is load-bearing at small `n` |
| `EPSILON_SWEEP` | Varies `ε` | Sensitivity, not tuning — reported as a curve |
| `LAMBDA_F_SWEEP` | Varies `λ_f` | Same |

Sweeps are reported as **sensitivity curves**, and the frozen operating point is marked on them. This
distinction matters: a swept parameter shown as a curve is analysis; a swept parameter silently set to
its best value is tuning on the test set (`19 § 8.3`).

---

## 6. What the benchmark must report even when unflattering

### 6.1 Mandatory failure reporting

| Item | Requirement |
|---|---|
| Actions that failed, by result code | `RR-BENCH-012` |
| Actions taken that recovered nothing | Counted, with total cost spent on them |
| **False positives** — actions on opportunities that would have recovered naturally | `M-12`; the metric that punishes over-contacting |
| Missed opportunities — `NO_ACTION`/`DEFERRED` cases the oracle says would have recovered under action | `M-19` |
| Wrong-action cases — a different action would have done better | Reported by oracle comparison |
| `unresolved_reconciliation_count` | Cases where REVIVE does not know what it did (`15 § 6`) |
| Seeds where REVIVE lost | § 3.3 |
| Invalidated runs | BP-2 |
| Unreached states, ungated cases, unfired rules | Coverage gaps, named (`14 § 6`) |

### 6.2 Mandatory cost reporting

| Item | Requirement |
|---|---|
| Total action cost and incentive spend, per policy | `RR-BENCH-013` |
| Cost per unit recovered | The number that makes gross recovery meaningful |
| LLM token counts and monetary cost, per mode | `09 § 6.4` |
| Wall-clock per cycle and per run | `RR-NFR-030`…`033` |
| Audit event volume | `16 § 10` |
| Human review load — approvals requested and approver time consumed | An operational cost that is easy to hide |

Reporting the human review load is included because an autonomous system that quietly routes half its
decisions to a person has not automated anything, and the metric makes that visible.

### 6.3 The unflattering configuration

`RR-BENCH-009` requires at least one reported configuration where REVIVE's advantage is small or
absent, stated in the headline. `ABUNDANT` is the expected candidate (`19 § 8.2`): with no scarcity,
there is little for an allocator to allocate, and `B2 CONTACT_ALL` should approach REVIVE.

If it turns out REVIVE wins even in `ABUNDANT`, that must be **explained**, not celebrated — the most
likely explanations are that the profile is not actually abundant, or that the advantage is coming from
uplift filtering rather than allocation, which is a different claim than Claim C.

---

## 7. Artefacts

Every artefact is content-hashed and lists its inputs' hashes.

| Artefact | Contents |
|---|---|
| `runs/<run_id>/manifest.json` | Seed, profile, policy, mode, all versions, `config_hash`, `dataset_hash`, genesis and final audit hash, event count, run state |
| `runs/<run_id>/audit.ndjson` | Full chain |
| `runs/<run_id>/decisions.ndjson` | Every decision with candidate set and gate trace |
| `runs/<run_id>/metrics.json` | `MetricSnapshot` set with derivation references (`DM-34`) |
| `runs/<run_id>/failures.json` | § 6.1 |
| `runs/<run_id>/cost.json` | § 6.2 |
| `runs/<run_id>/coverage.json` | Gates fired, rules fired, states reached, actions used, with gaps named |
| `bench/<bench_id>/matrix.json` | Every cell run, every cell skipped and why |
| `bench/<bench_id>/paired.json` | Per-seed paired differences |
| `bench/<bench_id>/disclosures.md` | The full limitation set (`21 § 9`), generated, not hand-written |
| `bench/<bench_id>/report.md` | Human-readable summary, **generated from the above only** |

| # | Rule |
|---|---|
| BA-1 | `report.md` is generated. No number in it is typed by a human (`RR-BENCH-007`) |
| BA-2 | Every number traces to a `MetricSnapshot` and thence to audit events or table rows |
| BA-3 | `disclosures.md` is emitted for every run and cannot be suppressed by a flag |
| BA-4 | Artefacts carry `data_source: SYNTHETIC` at the top level (`RR-UI-007`) |

BA-1 is the structural defence against the most common form of hackathon dishonesty, which is not
fabricated data but a hand-written summary that drifts from the data it summarises.

---

## 8. Threats to validity

Stated here rather than discovered by a reviewer.

| # | Threat | Effect on the claim |
|---|---|---|
| TV-1 | The generator is invented and unvalidated | **Largest threat.** Results are conditional on an unverified model of behaviour (`19 § 10`) |
| TV-2 | The oracle defines truth, so REVIVE is graded by the same process that generated the world | Mitigated by adversarial oracle construction (`OR-4`…`OR-6`) and strict isolation, not eliminated |
| TV-3 | Small seed count | Limits any statistical claim; disclosed with the number adjacent |
| TV-4 | Single merchant configuration | No cross-merchant generalisation is claimed |
| TV-5 | Myopic single-period allocation (`ADR-004`) | Multi-period effects unmeasured |
| TV-6 | `continuation_factor = 0` (`ADR-007`) | Subscription value understated; REVIVE's own numbers are conservative here |
| TV-7 | Baselines are our implementations of others' policies | Mitigated by BF-9 and publication; still our choice |
| TV-8 | Attribution within horizon `H` | A recovery at `H + 1 minute` counts for nobody; the horizon choice is a judgement |
| TV-9 | Predictor trained and evaluated in the same run | Learning benefit may be optimistic; `LLM_OFF` and `NO_EXPLORATION` ablations bound it partially |
| TV-10 | The dataset was constructed to make the thesis falsifiable, which also makes it testable in the thesis's favour | Disclosed in `19 § 5.2` and repeated here |

TV-10 is the honest core of it: a dataset built so that value-ranking can be wrong is a dataset in
which value-ranking will sometimes be wrong. The benchmark shows REVIVE handles that structure. It
does not show the structure is real.

---

## 9. Requirement mapping

| Requirement | Where |
|---|---|
| `RR-BENCH-001` batch measurement | § 3, § 4 |
| `RR-BENCH-002` baseline comparison | § 2 |
| `RR-BENCH-003` dispersion before summary | § 3.4 |
| `RR-BENCH-004` all declared seeds reported | § 3.3 |
| `RR-BENCH-005` oracle isolation | TV-2, `19 § 4.2` |
| `RR-BENCH-007` generated numbers only | BA-1, BA-2 |
| `RR-BENCH-008` pre-measurement freeze | § 1.2, § 4 FREEZE |
| `RR-BENCH-009` unflattering configuration | § 6.3 |
| `RR-BENCH-010` synthetic disclosure | BA-3, BA-4 |
| `RR-BENCH-011` LLM ablation reported | § 5.1 |
| `RR-BENCH-012` failure reporting | § 6.1 |
| `RR-BENCH-013` cost reporting | § 6.2 |
| `RR-NFR-020` byte-identical reproduction | § 4 REPRODUCE, BP-4 |
| `RR-NFR-030`…`033` performance | § 6.2 |
| `RR-NFR-035` no uncached LLM call | BP-1 |

---

## 10. Open items

| Item | Label |
|---|---|
| Seed count and the exact declared seed list | `PROPOSED`; must be frozen before measurement |
| Which profiles are in the headline vs the appendix | `PROPOSED` `BALANCED` headline, all profiles reported |
| Whether `EXACT` ILP is tractable at the chosen scale | `UNKNOWN`; `optimality_gap` is reported only where it is |
| `B1`'s retry schedule | `PROPOSED`; must be published (BF-9) |
| Whether any statistical test is worth reporting at this N | `PROPOSED` no; report the paired distribution |
| Tuning-seed / reporting-seed split | `PROPOSED`; declared before measurement (`19 § 8.3`) |
| Whether a second generator (independently parameterised) should be added to weaken TV-1 | `FUTURE / NOT IMPLEMENTED`; would materially strengthen the claim |
