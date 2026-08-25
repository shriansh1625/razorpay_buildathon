# REVIVE Trace — seed=1 BALANCED (official frozen config)

## Cell evidence

File: `artefacts/benchmark/official/cells/seed-001/BALANCED/REVIVE.json`

| Field | Value |
|-------|-------|
| `intervention_count` | 0 |
| `contact_count` | 0 |
| All recovery paise | 0 |
| `run_valid` | true |
| `elapsed_seconds` | **~570** |

Wall time confirms full M4–M12 cycle traversal; outcome metrics are zero despite compute.

## Stage-by-stage (full 2016-cycle trace)

| Stage | Aggregate count | Notes |
|-------|----------------:|-------|
| M4 `detect()` opportunities | ~11,300/cycle sum | Uses sentinel IDs consistently |
| M5 context assembled | matches M4 | |
| M6 candidates generated | ~812K total | |
| M7 valuations | ~812K total | ~54K ENRV > ε per sample window |
| M8 `allocate_portfolio` SELECTED | **> 0** (~60/auth cycle avg) | **M8 does select actions** |
| M9 `seal_allocation` | 1 decision per M8 selection | |
| M10 `authorize_execution` | **121,107** calls | |
| M10 `AUTHORIZED` | **0** | |
| M10 `REQUIRES_HUMAN_APPROVAL` | **121,107 (100%)** | |
| M11 `execute_authorization` | **0** | Skipped: `auth.authorization_state != AUTHORIZED` (`revive_pipeline.py:203-204`) |
| M12 `measure_execution` | **0** | |

## Critical question: Does M8 select?

**Yes.** M8 produces nonzero selected assignments on official config. The pipeline is not failing at allocation.

## Where selections disappear

```
M8 selected → M9 sealed → M10 authorize_execution
→ G7 verdict REQUIRE_APPROVAL (trigger: UNCERTAINTY, 100% of auths)
→ authorization_state = REQUIRES_HUMAN_APPROVAL
→ execute path skipped
→ intervention_count = len(executions) = 0
```

### G7 evidence

Sample authorization gate trace:

```
G1 ALLOW, G2 ALLOW, G3 ALLOW, G4 ALLOW, G5 ALLOW, ...
G7 REQUIRE_APPROVAL reason=REQUIRES_HUMAN_APPROVAL triggers=['UNCERTAINTY']
```

All 121,107 authorizations: `blocking_gate_id='G7'`, `blocking_reason_code='REQUIRES_HUMAN_APPROVAL'`.

### Missing simulated approver

Official config declares `approver_model_version: simulated_v1` (`artefacts/benchmark/official/config.json`).

`AuthorizeContext` defaults `approval_state=None` (`revive/policy/context.py:31`).

Neither `revive_pipeline.py` nor `baseline_pipeline.py` sets `approval_state=ApprovalRequestState.APPROVED`.

G7 logic (`revive/policy/gates.py:207-240`): when UNCERTAINTY trigger fires and `approval_state` is not `APPROVED`, verdict is `REQUIRE_APPROVAL`.

**Config promises simulated approval; pipeline never supplies it.**

## REVIVE vs baselines

REVIVE uses sentinel IDs end-to-end — no world/sentinel ID mismatch. REVIVE fails one stage later: **M10 G7 human-approval gate with no auto-approver wired**.
