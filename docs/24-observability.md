# 24 · Observability

REVIVE's observability stack serves two distinct audiences with different needs:

| Audience | Needs | Priority |
|---|---|---|
| **Operator** (merchant, reviewer) | Is the system working? Is it safe? What did it do and why? | Real-time dashboards, alerts |
| **Evaluator** (judge, engineer) | Are the numbers right? Is the benchmark reproducible? Where did it fail? | Post-run metrics artefact, traces, audit verification |

> **Metrics are defined in [37-metrics-dictionary.md](37-metrics-dictionary.md).** This document
> specifies how they are collected, transported, and alerted on — not what they mean. Where a
> metric is referenced by ID (`M-nn`), see [37](37-metrics-dictionary.md) for its definition,
> unit, direction, and tier.

---

## 1. Logs — structured decision traces

### 1.1 Log format

All logs are structured JSON lines with a mandatory schema:

```
{
  "timestamp":      ISO-8601 virtual clock,
  "level":          "DEBUG" | "INFO" | "WARN" | "ERROR" | "FATAL",
  "component":      "C-01" … "C-23",
  "phase":          "SEE" | "UNDERSTAND" | "SIMULATE" | "PRIORITIZE" | "GUARD" | "ACT" | "VERIFY" | "LEARN",
  "cycle_id":       "cyc_<ULID>",
  "run_id":         "bench_<ULID>",
  "opportunity_id": "opp_<ULID>" | null,
  "event":          structured event name (closed set per component),
  "detail":         {},
  "correlation_id": links related events across components
}
```

### 1.2 Log categories

| Category | Level | Components | Examples |
|---|---|---|---|
| **Signal processing** | INFO | C-01, C-02, C-03 | `signal_ingested`, `signal_quarantined`, `opportunity_created`, `opportunity_deduplicated`, `degradation_window_opened` |
| **Decision pipeline** | INFO | C-04…C-12 | `context_assembled`, `diagnosis_produced`, `candidates_generated`, `prediction_computed`, `enrv_computed`, `allocation_completed` |
| **Gate evaluation** | INFO | C-11, C-13, C-14 | `gate_evaluated{gate, verdict, reason}`, `prefilter_removed`, `stopping_rule_fired` |
| **Execution** | INFO | C-15…C-18 | `approval_queued`, `reservation_held`, `action_intended`, `adapter_invoked`, `adapter_result`, `reservation_committed` |
| **Outcome and learning** | INFO | C-19…C-21 | `outcome_observed`, `attribution_classified`, `strategy_updated` |
| **Fallback and degradation** | WARN | C-05, C-07, C-10, C-12 | `llm_output_rejected`, `llm_unavailable_fallback`, `predictor_unseen_cell`, `allocator_fallback_greedy`, `context_degraded` |
| **Safety violations** | ERROR | C-13, C-16, C-23 | `invariant_violation`, `illegal_transition`, `policy_pack_integrity_failure`, `audit_store_unavailable` |
| **Cycle lifecycle** | INFO | C-23 | `cycle_opened`, `cycle_deciding`, `cycle_executing`, `cycle_verifying`, `cycle_closed`, `cycle_aborted` |

### 1.3 Log rules

| Rule | Statement |
|---|---|
| No PII in logs | Never-log list enforced ([22 § 1.1](22-security-and-privacy.md)) |
| No secrets in logs | API keys, tokens masked at the serialisation boundary |
| Structured only | No unstructured log messages; every event has a schema |
| Deterministic | At a fixed seed, logs are identical between runs (virtual timestamps, deterministic ULIDs) |
| Correlation | Every log entry within a decision pipeline carries `opportunity_id` and `cycle_id` for tracing |

---

## 2. Metrics — operational and business

Metrics are emitted as `MetricSnapshot` rows per `RR-METRIC-002`. Each snapshot carries a
`derivation_ref` that links it to the computation that produced the value.

### 2.1 Operational metrics (per cycle)

These are computed and emitted at cycle close.

| Metric ID | Name | Source component |
|---|---|---|
| `M-52` | Cycle wall clock (per stage) | C-23 |
| `M-33` | Allocator runtime | C-12 |
| `M-34` | Allocator fallback rate | C-12 |
| `M-29` | Capacity utilisation per resource | C-16 |
| `M-48` | LLM cache hit rate | C-05, C-10 |
| `M-49` | LLM token usage and cost | C-05, C-10 |
| `M-50` | LLM output rejection rate | C-05, C-10 |
| `M-54` | Audit event volume per cycle | C-22 |
| `M-56` | Signal hygiene (duplicates, quarantined, late, out-of-order) | C-01 |

Additionally, per component observability counters as specified in [08](08-agent-architecture.md):

| Component | Counter examples |
|---|---|
| C-01 | `signals_ingested`, `signals_quarantined{reason}` |
| C-02 | `opportunities_detected{class}`, `dedupe_merges`, `value_at_risk_total` |
| C-03 | `degradation_windows_open`, `opportunities_flagged_degraded` |
| C-04 | `context_degraded_rate`, `context_field_null_rate{field}` |
| C-05 | `llm_calls{cached,uncached}`, `llm_output_rejected{reason}`, `diagnosis_unclassified_rate` |
| C-06 | `candidates_per_opportunity` distribution, `candidate_fallback_rate` |
| C-07 | `prediction_calls`, `unseen_cell_rate`, `mean_sigma` |
| C-08 | `cost_estimate_total`, `cost_variance_pct` |
| C-09 | `enrv_distribution`, `negative_uplift_candidate_rate` |
| C-12 | `selected/deferred/rejected/no_action` counts, `binding_constraints`, `allocator_mode` |
| C-13 | `gate_verdicts{gate,verdict}`, `gate_evaluation_ms`, `policy_pack_version` |
| C-14 | `stops{rule}` |
| C-15 | `approval_queue_depth`, `approval_latency`, `approval_outcomes{outcome}` |
| C-16 | `budget_utilisation{resource}`, `reservations_open`, `reservations_leaked` |
| C-17 | `interventions{action,outcome}`, `execution_latency`, `idempotency_hits` |
| C-18 | `adapter_calls{adapter,result}`, `adapter_latency` |
| C-19 | `outcomes{class}`, `partial_recovery_rate`, `unobservable_rate` |
| C-20 | `attribution{class}` |
| C-21 | `strategy_version`, `calibration{brier,ece}`, `cells_updated`, `exploration_spend` |

### 2.2 Business metrics (per run)

Computed at run completion from the full event and decision history.

| Metric ID | Name | Group |
|---|---|---|
| `M-01`…`M-13` | Money and recovery | A |
| `M-14`…`M-18`, `M-22` | Guardrails | B |
| `M-19`…`M-28` | Decision quality | C |
| `M-29`…`M-34` | Allocation | D |
| `M-35`…`M-45` | Operational honesty | E |
| `M-46`…`M-58` | Reproducibility, cost, coverage | F |

All definitions, units, directions, and tiers are in [37-metrics-dictionary.md](37-metrics-dictionary.md). This document does not duplicate them.

### 2.3 Metric emission rules

| Rule | Statement | Requirement |
|---|---|---|
| Every metric has a `derivation_ref` | Links to the computation source | `RR-METRIC-002` |
| Money metrics are integer paise | Conversion to rupees only at presentation | `RR-METRIC-007` |
| Zero-denominator ratios reported as undefined | Never as a large number | `RR-METRIC-008` |
| Tier-0 metrics computed by independent evaluators | Not by the runtime components they audit | `RR-METRIC-005` |
| No metric appears without its unit and direction | | `RR-METRIC-006` |
| Coverage metrics publish gap lists | Named, not just counted | `RR-METRIC-009` |

---

## 3. Traces — end-to-end decision traceability

### 3.1 Trace structure

Every recovery opportunity produces a trace spanning its full lifecycle:

```
Signal
 └─► Opportunity (opp_<ULID>)
      ├─► Context assembly
      ├─► Diagnosis (dg_<ULID>)
      ├─► Candidates (cand_<ULID> × N)
      │    ├─► Prediction (p, sigma)
      │    ├─► Cost (c, d, F)
      │    └─► ENRV
      ├─► Allocation decision (dec_<ULID>)
      │    └─► Selected / Deferred / Rejected / No-action
      ├─► Gate trace (per gate, in order)
      │    └─► G1…G12 verdicts
      ├─► Stopping check (SR-01…SR-11)
      ├─► Execution (iv_<ULID>)
      │    ├─► Reservation (HELD → COMMITTED/RELEASED)
      │    ├─► Audit intent (before effect)
      │    ├─► Adapter call → result
      │    └─► Outcome (out_<ULID>)
      │         ├─► recovered_amount_paise
      │         ├─► attribution_class
      │         └─► cost reconciliation
      └─► Final state (RECOVERED / STOPPED / CLOSED_UNRECOVERED)
```

### 3.2 Trace requirements

| Requirement | Statement |
|---|---|
| `RR-AUDIT-005` | Every executed intervention is reachable to its decision, candidate set, diagnosis, and opportunity |
| `RR-AUDIT-009` | Application tables can be rebuilt from the audit chain alone |
| `SM-9` | An opportunity's state is derivable from the audit chain alone |

### 3.3 Correlation

All trace elements share:
- `run_id` — the benchmark run
- `cycle_id` — the specific cycle
- `opportunity_id` — the opportunity being processed
- `decision_id` — the decision (where applicable)
- `intervention_id` — the intervention (where applicable)

A trace query for any of these IDs returns the complete causal chain.

---

## 4. Alerts

Alerts are conditions that require immediate attention. They are categorised by severity.

### 4.1 Critical alerts (require immediate action)

| Alert | Condition | Detection metric | Action |
|---|---|---|---|
| **Policy violation** | `M-16 > 0` (action executed without `ALLOW`) | `M-16` | Run invalidated; halt execution |
| **Missed stop** | `M-17 > 0` (opportunity should have stopped but had action executed) | `M-17` | Run invalidated; investigate |
| **Unapproved execution** | `M-18 > 0` | `M-18` | Run invalidated; investigate |
| **Invariant violation** | `M-22 > 0` | `M-22` | Cycle aborted; run invalidated |
| **Audit store unavailable** | Write to C-22 fails | Log level FATAL | Halt all execution (`RR-AUDIT-010`) |
| **Privacy canary hit** | `M-57 > 0` | `M-57` | Build failure; investigate data pipeline |

### 4.2 High-severity alerts (require prompt investigation)

| Alert | Condition | Detection metric / source | Action |
|---|---|---|---|
| **Duplicate execution detected** | Idempotency key collision with a different effect | `idempotency_hits` anomaly | Investigate; may indicate adapter bug |
| **Budget exhaustion** | A resource reaches 100% utilisation with deferred actions remaining | `M-29` = 1.0 with `M-32` > 0 | Review budget allocation; inform merchant |
| **Allocator sustained fallback** | `M-34` > configured threshold | `M-34` | Investigate allocator timeout; tune parameters |
| **Reproducibility failure** | `M-46` = FAIL | `M-46` | Investigate nondeterminism source; run invalidated |
| **Uncached LLM in evaluation** | `M-47 > 0` | `M-47` | Evaluation invalidated; cache miss bug |

### 4.3 Medium-severity alerts (require review)

| Alert | Condition | Detection metric / source | Action |
|---|---|---|---|
| **Abnormal action distribution** | Action-code distribution deviates significantly from historical | `M-14` profile change | May indicate predictor drift or data change |
| **Elevated failure rate** | Adapter `FAILED_*` rate above baseline | `M-43` | May indicate degradation; check C-03 flags |
| **Recovery collapse** | `M-10` drops significantly between seed sets or cycles | `M-10` trend | Investigate predictor, allocator, or data |
| **Unexpected no-action rate** | `NO_ACTION` share rises above configured threshold | `M-15` | May indicate parameter misconfiguration or economic exhaustion |
| **Latency spike** | `M-52` cycle wall clock exceeds 2× median | `M-52` | Investigate allocator, predictor, or data volume |
| **High approval expiry rate** | `M-38` exceeds threshold | `M-38` | Approval design or staffing issue |
| **Calibration drift** | `M-24` Brier score or ECE degrades across cycles | `M-24` | Learning Engine may need rollback |
| **High unclassified diagnosis rate** | `M-51` exceeds threshold | `M-51` | May indicate new failure modes or LLM degradation |

### 4.4 Low-severity alerts (informational)

| Alert | Condition | Detection metric / source | Action |
|---|---|---|---|
| **LLM output rejection** | `M-50` > 0 but within tolerance | `M-50` | Monitor; deterministic fallback handling |
| **Context degradation** | `context_degraded_rate` elevated | C-04 counters | Data pipeline may have gaps |
| **High deferral age** | Opportunities deferred for > N consecutive cycles | `M-41` | May become `SR-07` candidates; informational |
| **Signal hygiene anomaly** | Elevated duplicates, late, or out-of-order signals | `M-56` | Data pipeline investigation |

---

## 5. Dashboard integration

Observability data feeds the seven UI screens defined in [25-ui-ux-spec.md](25-ui-ux-spec.md):

| Screen | Key observability feeds |
|---|---|
| Revenue Command Center | `M-01`, `M-02`, `M-05`…`M-10`, active alerts |
| Revenue Leakage Explorer | `M-01` by class and cause, `M-14` gate profile |
| Recovery Opportunities | Decision outcomes, `M-15`, approval queue (`M-37`) |
| Decision Detail | Full trace per opportunity (§ 3.1) |
| Recovery Allocation | `M-29`…`M-34`, shadow prices, binding constraints |
| Audit Trail | Audit event stream, chain verification (`M-58`) |
| Benchmark Lab | All run metrics, seed comparison, `M-46` |

---

## 6. Implementation notes

| Aspect | Statement | Label |
|---|---|---|
| Log storage | Append to structured log files; rotation per run | `PROPOSED` |
| Metric storage | `MetricSnapshot` table per run, alongside the audit store | `PROPOSED` |
| Alert evaluation | Post-cycle check against alert rules; no real-time streaming in hackathon | `HACKATHON-SCOPE` |
| Trace query | In-memory for hackathon; indexed store for production | `HACKATHON-SCOPE` |
| Dashboard refresh | Per-cycle polling; no WebSocket push in hackathon | `HACKATHON-SCOPE` |

---

## 7. Requirement mapping

| Requirement | Where |
|---|---|
| `RR-METRIC-002` derivation reference | § 2.3 |
| `RR-METRIC-005` independent evaluation | § 2.3 |
| `RR-METRIC-006` unit and direction | § 2.3 |
| `RR-AUDIT-005` trace reachability | § 3.2 |
| `RR-AUDIT-009` reconstruction | § 3.2 |
| Component observability (per [08](08-agent-architecture.md)) | § 2.1 |
| `M-16`, `M-17`, `M-18`, `M-22` tier-0 alerts | § 4.1 |
| `M-57`, `M-58` 0-adjacent alerts | § 4.1 |
