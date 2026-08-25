# 17 · Data Model

Every table in the implementation must appear here (`RR-NFR-080`, `P-9`). Every money field is an
integer in paise with a `_paise` suffix (`README § C-2`). Every id follows `<prefix>_<ULID>`
(`README § C-4`).

Status of this document: **`PROPOSED`**. It is a logical model. Physical types, indexes, and the
storage engine are implementation decisions (§ 12).

---

## 1. Layers

```
┌─ DOMAIN ─────────────── synthetic merchant/customer/payment records (input side)
├─ SIGNAL ──────────────── raw events + quarantine
├─ CORE ─────────────────  opportunities → diagnosis → candidates → decisions → interventions → outcomes
├─ CONTROL ─────────────── policy, action catalogue, resources, ledger, idempotency, halt
├─ LEARNING ────────────── strategy versions, predictor cells, exploration budget
├─ LLM ─────────────────── prompt versions, response cache
└─ RECORD ──────────────── audit chain, cycle/run rows, metric artefacts
```

**Direction of writes.** CORE reads DOMAIN and never writes it. LEARNING writes only its own layer
(`RR-GUARD-022`). RECORD is append-only. No layer writes upward.

---

## 2. DOMAIN layer

Synthetic input records produced by the generator ([19-synthetic-dataset.md](19-synthetic-dataset.md)).
REVIVE reads these; it does not create them.

| Table | Key | Notable fields |
|---|---|---|
| `Merchant` | `mer_` | name token, timezone (`Asia/Kolkata`), `net_retention_factor` (`m`), active policy pack ref |
| `Customer` | `cust_` | pseudonymous `customer_ref`, `segment`, `tenure_band`, `value_band`, `prior_self_recovery_rate`, `language_tag`. **No name, phone, or email** (`§ 6 of 16`) |
| `ContactChannel` | `chn_` | `customer_id`, `channel_type`, `contact_ref` (pseudonymous token), `state` (`USABLE`/`BOUNCED`/`INVALID`), `last_delivery_at` |
| `ConsentRecord` | `con_` | `customer_id`, `channel_type`, `purpose`, `granted`, `granted_at`, `revoked_at` |
| `PaymentInstrument` | `pi_` | `customer_id`, `method_type`, `network_band`, `expiry_state` (enum), `block_state`, `failure_count`. **No PAN, no CVV** |
| `Mandate` | `man_` | `customer_id`, `instrument_id`, `state`, `expires_at`, `max_amount_paise`, `presented_count` |
| `Order` | `ord_` | `customer_id`, `amount_paise`, `created_at`, `status` |
| `CheckoutSession` | `chk_` | `customer_id` or anonymous session token, `cart_value_paise`, `stage_reached`, `method_selected`, `abandoned_at`, `cart_fingerprint` |
| `Transaction` | `txn_` | `order_id`/`invoice_id`/`subscription_id`, `amount_paise`, `method_type`, `instrument_id`, `attempt_seq`, `status`, `reason_code`, `reason_text` (**untrusted**), `attempted_at` |
| `Subscription` | `sub_` | `customer_id`, `mandate_id`, `cycle_amount_paise`, `cycle_number`, `next_charge_at`, `state` |
| `Invoice` | `inv_` | `customer_id`, `issued_amount_paise`, `paid_amount_paise`, `credited_amount_paise`, `written_off_amount_paise`, `disputed_amount_paise`, `due_at`, `terms_days`, `state` |
| `RiskFlag` | `rf_` | `customer_id`, `flag_type` (`FRAUD`/`LEGAL_HOLD`/`INSOLVENCY`/`DECEASED`/`MERCHANT_SUPPRESSION`), `set_at`, `cleared_at`, `source` |

### 2.1 Invariants

| # | Invariant |
|---|---|
| DM-1 | `Invoice.paid + credited + written_off + disputed ≤ issued` |
| DM-2 | `reason_text` is never used in a query, a branch, or a prompt without escaping (`RR-NFR-063`) |
| DM-3 | Absence of a `ConsentRecord` row means **no consent**, never implied consent |
| DM-4 | A `Customer` row contains no field on the never-log list |

---

## 3. SIGNAL layer

| Table | Key | Fields |
|---|---|---|
| `Signal` | `sig_` | `signal_type`, `source_ref`, `payload` (validated), `received_at`, `occurred_at`, `dedupe_hash`, `processed_at`, `opportunity_id` (nullable) |
| `SignalQuarantine` | `sigq_` | `raw_payload`, `rejection_reason`, `received_at`, `schema_version_attempted` |

| # | Invariant |
|---|---|
| DM-5 | `dedupe_hash` is unique; re-delivery of the same signal creates no second row (`RR-FUNC-004`) |
| DM-6 | Every signal is either processed (has `processed_at`) or quarantined. No signal is silently dropped |
| DM-7 | `occurred_at` may precede `received_at` (late arrival) and the model tolerates it (`RR-NFR-045`) |

---

## 4. CORE layer

### 4.1 `RevenueOpportunity` (`opp_`)

The central table.

| Field | Type | Notes |
|---|---|---|
| `opportunity_id` | `opp_<ULID>` | |
| `merchant_id`, `customer_id` | fk | |
| `risk_class` | enum | 5 classes ([12 § 2](12-revenue-leakage-model.md)) |
| `secondary_class` | enum, nullable | Cross-class overlap tag |
| `natural_key` | string | Unique among open opportunities (`LK-2`) |
| `value_at_risk_paise` | integer | Recoverable amount (`RR-FUNC-007`) |
| `original_value_paise` | integer | Before reductions; for reporting only |
| `continuation_value_paise` | integer | Subscription only; `0` by default (`ADR-007`) |
| `addressable` | bool | |
| `non_addressable_reason` | enum, nullable | |
| `state` | enum | 14 states ([34](34-state-machine.md)) |
| `first_detected_at` | timestamp | Virtual clock |
| `recovery_window_expires_at` | timestamp | |
| `ageing_bucket` | enum | |
| `attempt_seq` | integer | Payment attempts made |
| `contacts_made` | integer | Customer touches for this opportunity (`SR-04`) |
| `consecutive_no_action_cycles` | integer | `SR-07` counter |
| `next_eligible_at` | timestamp | Cooldown |
| `degradation_flag` | bool | |
| `degradation_cohort` | string, nullable | |
| `stop_reason` | enum, nullable | |
| `reopen_count` | integer | |
| `linked_refs` | json | `order_id` / `invoice_id` / `subscription_id` / `checkout_session_id` / `mandate_id` |

**Indexes (`PROPOSED`):** `(state, next_eligible_at)` for cycle selection; `(natural_key)` unique
where state is non-terminal; `(customer_id, state)` for per-customer resource checks.

### 4.2 `Diagnosis` (`dg_`)

| Field | Notes |
|---|---|
| `diagnosis_id`, `opportunity_id`, `cycle_id` | |
| `ranked_causes` | ordered list of `{cause_code, confidence_band, evidence_refs[]}` |
| `unclassified` | bool |
| `llm_used`, `llm_cache_hit`, `prompt_version`, `model_id` | nullable when deterministic-only |
| `deterministic_mapping_applied` | bool |
| `produced_at` | |

**No numeric confidence field exists on this table.** Bands only (`RR-GUARD-020`). The band→prior
mapping lives in `StrategyVersion`.

### 4.3 `ActionCandidate` (`cand_`)

| Field | Notes |
|---|---|
| `candidate_id`, `opportunity_id`, `cycle_id` | |
| `action_code` | enum, 15 codes ([11 § 3](11-counterfactual-engine.md)) |
| `params` | `{delay_minutes, channel, incentive_tier, template_id}` |
| `p_action`, `p_natural`, `uplift`, `sigma` | floats |
| `predictor_cell_ref`, `shrinkage_level` | 0/1/2 |
| `gross_paise`, `cost_paise`, `expected_incentive_paise`, `fatigue_cost_paise` | integers |
| `enrv_paise`, `enrv_lo_paise`, `enrv_hi_paise` | integers |
| `resource_usage` | `{resource: quantity}` |
| `prefilter_removed`, `prefilter_reason` | |
| `copy_source` | `STATIC` / `LLM`, nullable |

| # | Invariant |
|---|---|
| DM-8 | `enrv_paise = gross − cost − expected_incentive − fatigue_cost`, exactly (`RR-FUNC-029`) |
| DM-9 | `enrv_lo ≤ enrv_paise ≤ enrv_hi` |
| DM-10 | Every opportunity in `PRICED` has ≥ 3 candidates including `A00`, and `A00` has `enrv_paise = 0` |

### 4.4 `Decision` (`dec_`)

Fields as specified in [09 § 4](09-decision-engine.md). Immutable.

| # | Invariant |
|---|---|
| DM-11 | Unique on `(cycle_id, opportunity_id)` |
| DM-12 | Every opportunity selected into a cycle has exactly one row for it (`AI-8`) |
| DM-13 | `outcome = SELECTED` ⟹ `chosen_action_code` non-null and `enrv_chosen_paise > ε` |
| DM-14 | No row is ever updated. Corrections are new rows in later cycles |

### 4.5 `GateVerdict` (`gv_`)

| Field | Notes |
|---|---|
| `verdict_id`, `decision_id`, `candidate_id`, `cycle_id` | |
| `gate_id` | `G1`…`G12` |
| `sequence` | evaluation order |
| `verdict` | `ALLOW`/`ALLOW_WITH_MODIFICATION`/`DEFER`/`DENY`/`REQUIRE_APPROVAL` |
| `reason_code` | closed set |
| `detail` | json, e.g. requested vs available |
| `inputs_digest` | hash of the state the gate read |
| `original_params`, `modified_params` | G5 only |
| `policy_pack_version` | |

| # | Invariant |
|---|---|
| DM-15 | For every candidate reaching the gates, rows exist for **all** applicable gates, contiguous in `sequence` (`RR-GUARD-027`) |
| DM-16 | An `Intervention` exists only where the final combined verdict was `ALLOW`/`ALLOW_WITH_MODIFICATION` (`M-16 = 0`) |

### 4.6 `ApprovalRequest` (`apr_`)

| Field | Notes |
|---|---|
| `approval_id`, `decision_id`, `opportunity_id` | |
| `trigger_reason` | value band / uncertainty / action family / first-use / cumulative incentive |
| `proposed_action`, `proposed_params` | |
| `value_at_risk_paise`, `enrv_paise`, `enrv_lo_paise`, `enrv_hi_paise` | context for the human |
| `state` | 6 states ([34 § 3](34-state-machine.md)) |
| `queued_at`, `expires_at`, `resolved_at` | |
| `actor_kind` | `HUMAN` / `SIMULATED_APPROVER` — **always recorded, never elided** |
| `actor_role` | role token, never a personal identity |
| `resolution`, `modified_params` | |

`actor_kind` is mandatory because a benchmark run's approvals come from a simulated policy and every
artefact must say so ([20 § 7](20-benchmark.md)).

### 4.7 `Intervention` (`iv_`)

| Field | Notes |
|---|---|
| `intervention_id`, `decision_id`, `opportunity_id`, `cycle_id` | |
| `action_code`, `params` | The **executed** parameters, post-clamp |
| `idempotency_key` | unique |
| `reservation_handle_id` | |
| `adapter_id` | which implementation ran |
| `state` | 7 states ([34 § 2](34-state-machine.md)) |
| `adapter_result` | closed set of 5 |
| `intent_audit_id`, `result_audit_id` | links into the chain |
| `actual_cost_paise`, `actual_incentive_paise` | for cost-variance reporting |
| `invoked_at`, `returned_at`, `latency_ms` | |
| `reconcile_attempts` | |

| # | Invariant |
|---|---|
| DM-17 | `idempotency_key` unique (`RR-NFR-040`) |
| DM-18 | `intent_audit_id.sequence_no < result_audit_id.sequence_no` (`V-6`) |
| DM-19 | Exactly one intervention per `(decision_id)`; a retry is a new decision in a new cycle |

### 4.8 `Outcome` (`out_`)

| Field | Notes |
|---|---|
| `outcome_id`, `opportunity_id`, `intervention_id` (nullable) | Nullable because `NO_ACTION` opportunities also have outcomes |
| `recovered_amount_paise` | 0 if none |
| `partial` | bool |
| `recovered_at` | |
| `horizon_used_minutes` | The `H` applied |
| `observed_within_horizon` | bool |
| `late_recovery` | bool — recovered after `H`; **excluded** from attributed uplift |
| `observability` | `OBSERVED` / `UNOBSERVABLE` |
| `attribution_class` | `ATTRIBUTED` / `NATURAL` / `AMBIGUOUS` |
| `attribution_rationale` | closed set |
| `oracle_counterfactual_paise` | **benchmark only**; written by the evaluator, never readable by the decision path (`AI-6`) |

`oracle_counterfactual_paise` living on this table is a deliberate risk, so it is mitigated
structurally: the column is in a separate physical table in the implementation, the decision path's
data-access layer has no mapping for it, and a test asserts no decision-path module can read it.

### 4.9 Core-layer relationship summary

```
Signal ──► RevenueOpportunity ──► Diagnosis
                    │                 │
                    ├──► ActionCandidate[]  ──► GateVerdict[]
                    │            │
                    │            └──► Decision ──► ApprovalRequest?
                    │                     │
                    │                     └──► Intervention ──► Outcome
                    └──► (state, counters, stop_reason)
```

---

## 5. CONTROL layer

| Table | Key | Notes |
|---|---|---|
| `PolicyPack` | `pol_` | Sealed, hashed, versioned. Full structure in [13 § 2](13-policy-and-guardrails.md). Never updated in place |
| `ActionCatalogueEntry` | `act_` | `action_code`, family, tier, `reversible`, `requires_consent`, resource usage template, cost parameters, `d>0` flag |
| `ResourceDefinition` | `res_` | `resource_key`, scope (`MERCHANT`/`MERCHANT_CHANNEL`/`CUSTOMER`), unit, `period_limit`, `cycle_cap`, `pacing_fraction` |
| `ResourceLedgerEntry` | `led_` | Append-only: `resource_key`, scope key, `delta`, `kind` (`RESERVE`/`COMMIT`/`RELEASE`/`RECLAIM`), `handle_id`, `cycle_id`, `balance_after` |
| `ReservationHandle` | `rsv_` | `handle_id`, `cycle_id`, `decision_id`, `state` (4), `items[{resource_key, quantity}]`, `created_at`, `settled_at` |
| `IdempotencyKey` | — | `key` (PK), `state` (`CLAIMED`/`RESOLVED`), `opportunity_id`, `action_code`, `attempt_seq`, `cycle_id`, `stored_result`, `claimed_at` |
| `HaltState` | `hlt_` | `scope`, `engaged`, `engaged_by_role`, `engaged_at`, `released_at`. Durable across restart (`RR-NFR-046`) |
| `ContactLedger` | `cl_` | Append-only per-customer contact record: `customer_id`, `channel_type`, `opportunity_id`, `occurred_at`. Source of truth for `G3` and `SR-04` |

| # | Invariant |
|---|---|
| DM-20 | `ResourceLedgerEntry` is append-only; balances are derived, never stored as a mutable field of record |
| DM-21 | `committed + reserved ≤ min(period_limit − prior_periods, cycle_cap)` after every entry (`RR-NFR-041`) |
| DM-22 | Zero handles in `HELD` at cycle close (`AL-10`, `SM-7`) |
| DM-23 | `PolicyPack` rows are immutable once `sealed_at` is set |
| DM-24 | `ContactLedger` counts, not `Intervention` counts, drive `G3` — so a contact is counted even if its intervention row is later found inconsistent |

---

## 6. LEARNING layer

| Table | Key | Notes |
|---|---|---|
| `StrategyVersion` | `strat_` | `version`, `parent_version`, `created_at`, `band_to_prior_map`, `shrinkage_constants`, `calibration_summary`, `cells_updated_count` |
| `PredictorCell` | `pc_` | `strategy_version`, `cell_key` (the 6-tuple from [11 § 4.3](11-counterfactual-engine.md)), `alpha`, `beta`, `n_observed`, `level` |
| `NaturalRecoveryCell` | `nrc_` | Same shape, for `p(i,∅)`; separate so a bug in one cannot corrupt the other |
| `ExplorationLedger` | `exp_` | `cycle_id`, `cell_key`, `budget_consumed_paise`, `draw_value`, `stream_position` |

| # | Invariant |
|---|---|
| DM-25 | The LEARNING layer has **no** write path to `PolicyPack`, `ResourceDefinition`, or any threshold (`RR-GUARD-022`). Enforced at the data-access layer and asserted by a test |
| DM-26 | `StrategyVersion` rows are immutable; a new version is a new row |
| DM-27 | A cycle reads one pinned `StrategyVersion`, snapshotted at cycle open |
| DM-28 | Exploration spend never draws on a non-exploration resource |

---

## 7. LLM layer

| Table | Key | Notes |
|---|---|---|
| `PromptVersion` | `pv_` | `prompt_version`, `purpose` (`DIAGNOSIS`/`COPY`), `template_text`, `output_schema`, `model_id`, `decoding_params`, `sealed_at` |
| `LLMCacheEntry` | — | `cache_key` (PK) = `H(prompt_version, model_id, decoding_params, seed, opportunity_id, input_hash)`, `validated_output`, `validation_status`, `fallback_applied`, `created_at` |

| # | Invariant |
|---|---|
| DM-29 | Only schema-validated outputs (or their deterministic fallbacks) are cached ([09 § 6.3](09-decision-engine.md)) |
| DM-30 | No cache entry stores a raw model response that failed validation |
| DM-31 | Cache reads during a benchmark run never miss; a miss is a hard error (`RR-NFR-035`) |
| DM-32 | No never-log field appears in `input_hash`'s source or in any stored output (`RR-NFR-062`) |

---

## 8. RECORD layer

| Table | Key | Notes |
|---|---|---|
| `AuditEvent` | `aud_` | Schema in [16 § 3](16-audit-trail.md). Append-only, hash-chained |
| `CycleRun` | `cyc_` | `cycle_id`, `run_id`, `virtual_time`, `state` (6), counts by decision outcome, `allocator_mode`, `shadow_prices`, `binding_constraints`, `duration_ms`, `abort_reason` |
| `BenchmarkRun` | `bench_` | `run_id`, `seed`, `mode` (`LLM_OFF`/`LLM_DIAGNOSIS_ONLY`/`LLM_FULL`), all versions, `config_hash`, `genesis_hash`, `final_hash`, `event_count`, `state` (5), `artefact_hashes` |
| `MetricSnapshot` | `ms_` | `run_id`, `cycle_id` (nullable for run-level), `metric_id` (`M-*`), `value`, `unit`, `derivation_ref` |

| # | Invariant |
|---|---|
| DM-33 | `AuditEvent` has no update or delete path (`RR-AUDIT-001`) |
| DM-34 | `MetricSnapshot.derivation_ref` points to the audit events or table rows the value was computed from — **no metric exists without a derivation** (`RR-BENCH-007`) |
| DM-35 | A `BenchmarkRun` in `INVALIDATED` has its metric snapshots marked unusable, not deleted |
| DM-36 | Two runs with the same `(seed, mode, all versions, config_hash)` have identical `final_hash` (`RR-NFR-020`) |

---

## 9. Money-field register

Complete list of money columns, so a reviewer can audit unit discipline in one place (`RR-NFR-001`).

| Table | Field |
|---|---|
| `Merchant` | — (`net_retention_factor` is a ratio, not money) |
| `Order` | `amount_paise` |
| `CheckoutSession` | `cart_value_paise` |
| `Transaction` | `amount_paise` |
| `Subscription` | `cycle_amount_paise` |
| `Invoice` | `issued_amount_paise`, `paid_amount_paise`, `credited_amount_paise`, `written_off_amount_paise`, `disputed_amount_paise` |
| `Mandate` | `max_amount_paise` |
| `RevenueOpportunity` | `value_at_risk_paise`, `original_value_paise`, `continuation_value_paise` |
| `ActionCandidate` | `gross_paise`, `cost_paise`, `expected_incentive_paise`, `fatigue_cost_paise`, `enrv_paise`, `enrv_lo_paise`, `enrv_hi_paise` |
| `Decision` | `enrv_chosen_paise`, `enrv_runner_up_paise`, component fields |
| `Intervention` | `actual_cost_paise`, `actual_incentive_paise` |
| `Outcome` | `recovered_amount_paise`, `oracle_counterfactual_paise` |
| `ResourceLedgerEntry` | `delta`, `balance_after` (paise where the resource unit is money) |
| `ExplorationLedger` | `budget_consumed_paise` |
| `PolicyPack` | `epsilon_paise`, incentive caps, budget limits |

A static check asserts: no money column lacks the `_paise` suffix, and no float is assigned to one
(`RR-NFR-001`).

---

## 10. Global invariants

| # | Invariant | Source |
|---|---|---|
| GI-1 | No two open opportunities share a `natural_key` | `LK-2` |
| GI-2 | `Σ value_at_risk_paise` over open opportunities ≤ genuinely outstanding money in the dataset | `LK-1` |
| GI-3 | `Σ recovered_amount_paise` ≤ `Σ value_at_risk_paise` over closed opportunities | `LK-4` |
| GI-4 | Every `Intervention` traces to a `Decision` with an `ALLOW` gate trace | `DM-16` |
| GI-5 | Every state is derivable from `AuditEvent` alone | `SM-9` |
| GI-6 | Learning layer wrote nothing outside its layer | `DM-25` |
| GI-7 | No never-log field exists in any table, log, prompt, or artefact | `RR-NFR-053` |
| GI-8 | Ledger balances derived from entries equal live balances | `DM-20` |
| GI-9 | Detected-opportunity count is independent of action count | `LK-5` |
| GI-10 | Every `MetricSnapshot` has a derivation reference | `DM-34` |

Each is a test named after its ID.

---

## 11. Requirement mapping

| Requirement | Where |
|---|---|
| `RR-NFR-001`/`002` money discipline | § 9 |
| `RR-NFR-080` every table documented | this document |
| `RR-FUNC-004` dedupe | `DM-5`, `GI-1` |
| `RR-FUNC-007` value at risk | § 4.1 |
| `RR-FUNC-029` component reconstruction | `DM-8` |
| `RR-FUNC-044` immutable decisions | `DM-14` |
| `RR-GUARD-022` learner isolation | `DM-25`, `GI-6` |
| `RR-GUARD-027` full gate trace | `DM-15` |
| `RR-NFR-040`/`041` idempotency and ledger | `DM-17`, `DM-21` |
| `RR-NFR-053` never-log list | `GI-7` |
| `RR-BENCH-005` oracle isolation | § 4.8 |
| `RR-BENCH-007` metric derivation | `DM-34` |

---

## 12. Open items

| Item | Label |
|---|---|
| Storage engine | `PROPOSED` SQLite for the prototype; the append-only and unique-constraint requirements are the only hard needs |
| Physical types and index set | `UNKNOWN — MUST BE DECIDED DURING IMPLEMENTATION` |
| Whether `PredictorCell` should be a materialised table or recomputed from outcomes on load | `PROPOSED` materialised, versioned, for determinism |
| Whether `ContactLedger` and `Intervention` should be unified | `PROPOSED` no — `DM-24` depends on their separation |
| Retention and archival | Out of scope (`OS-31`) |
| Real Razorpay entity shapes | `UNVERIFIED`; the DOMAIN layer is REVIVE's own model, mapped by an adapter ([36](36-razorpay-integration-assumptions.md)) |
