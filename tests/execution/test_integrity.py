"""Execution integrity — adapter isolation and audit ordering."""

import inspect
import pkgutil

from revive.execution.adapters import simulated
from revive.integrity import assert_decision_path_does_not_import_oracle
from revive.audit import AuditEventType, AuditJournal
from revive.decision.ledger import ReservationLedger
from revive.decision.models import ResourceReservation, ReservationStatus
from revive.execution import execute_authorization, ExecutionEnvironment

from tests.execution.helpers import authorize_selected, fixture_partition, NOW


def test_decision_path_still_no_oracle():
    assert_decision_path_does_not_import_oracle()


def test_adapters_not_imported_outside_execution():
    forbidden_imports: list[str] = []
    import revive

    for mod in pkgutil.walk_packages(revive.__path__, prefix="revive."):
        if mod.name.startswith("revive.execution"):
            continue
        try:
            imported = __import__(mod.name, fromlist=["_dummy"])
        except ImportError:
            continue
        source_path = inspect.getfile(imported)
        if not source_path.endswith(".py"):
            continue
        text = open(source_path, encoding="utf-8").read()
        if "revive.execution.adapters" in text:
            forbidden_imports.append(mod.name)
    assert forbidden_imports == []


def test_audit_intent_before_result():
    auth, decision, cand, val = authorize_selected()
    audit = AuditJournal()
    ledger = ReservationLedger()
    ledger.reserve(
        (
            ResourceReservation(
                reservation_id="res_1",
                decision_id=decision.decision_id,
                cycle_id=decision.cycle_id,
                resource_key="retry_slots",
                quantity=1,
                customer_id=None,
                reserved_at_micros=NOW,
                expires_at_micros=decision.expires_at_micros,
                status=ReservationStatus.ACTIVE,
            ),
        )
    )
    execute_authorization(
        auth,
        decision,
        cand,
        val,
        ExecutionEnvironment(
            oracle_partition=fixture_partition(),
            value_at_risk_paise=5000,
            customer_id="cust_var",
        ),
        ledger,
        NOW + 2000,
        audit=audit,
    )
    records = audit.records()
    assert len(records) == 2
    assert records[0].event_type == AuditEventType.ACTION_INTENT
    assert records[1].event_type == AuditEventType.ACTION_RESULT
    assert records[0].sequence_no < records[1].sequence_no


def test_mint_authorised_action_rejects_blocked():
    from revive.execution.authorised import mint_authorised_action
    from revive.policy import authorize_execution
    from revive.policy.models import AuthorizationState

    auth, decision, cand, val = authorize_selected()
    blocked = __import__(
        "revive.policy.models", fromlist=["ExecutionAuthorization"]
    ).ExecutionAuthorization(
        authorization_id=auth.authorization_id,
        decision_id=auth.decision_id,
        opportunity_id=auth.opportunity_id,
        candidate_id=auth.candidate_id,
        action_code=auth.action_code,
        authorized_parameters=dict(auth.authorized_parameters),
        authorization_state=AuthorizationState.BLOCKED,
        gate_trace=auth.gate_trace,
        stopping_results=auth.stopping_results,
        approval_requirement=False,
        approval_state=None,
        policy_pack_version=auth.policy_pack_version,
        configuration_hash=auth.configuration_hash,
        allocator_version=auth.allocator_version,
        valuation_version=auth.valuation_version,
        authorization_version=auth.authorization_version,
        authorized_at_micros=None,
        expires_at_micros=None,
        idempotency_key=auth.idempotency_key,
        enrv_paise=auth.enrv_paise,
        blocking_gate_id="G1",
        blocking_reason_code="BLOCKED",
        audit_reference=auth.audit_reference,
        explanation=(),
    )
    try:
        mint_authorised_action(blocked)
        assert False, "expected ValueError"
    except ValueError:
        pass
