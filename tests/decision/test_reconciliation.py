"""Staleness, expiry, reconciliation tests."""

from revive.config.policy_pack import PolicyPack, PolicyPackStatus
from revive.decision import (
    DecisionStore,
    ObservableReconcileContext,
    reconcile_decision,
    seal_allocation,
)
from revive.decision.config import DecisionLifecycleConfig
from revive.domain.enums import ActionCode, DecisionOutcome
from revive.allocation import allocate_portfolio, default_resource_state, ResourceCapacities
from revive.recovery.candidates.models import ResourceRequirement
from tests.allocation.helpers import make_item, priced

NOW = 3_600_000_000


def _selected_decision(action=ActionCode.A03):
    item = make_item(
        "opp_1",
        "cust_1",
        30_000,
        (
            priced(
                "opp_1",
                action,
                5000,
                (
                    ResourceRequirement("message_capacity", 1),
                    ResourceRequirement("contact_allowance", 1),
                ),
            ),
            priced("opp_1", ActionCode.A00, 0),
        ),
    )
    alloc = allocate_portfolio((item,), default_resource_state(), NOW, "cyc_1")
    bundle = seal_allocation(alloc, (item,), ResourceCapacities(), opportunity_states={"opp_1": "PRICED"})
    return next(d for d in bundle.decisions if d.outcome == DecisionOutcome.SELECTED)


def test_payment_recovered_makes_retry_stale():
    item = make_item(
        "opp_1",
        "cust_1",
        30_000,
        (
            priced(
                "opp_1",
                ActionCode.A01,
                5000,
                (ResourceRequirement("retry_slots", 1),),
            ),
            priced("opp_1", ActionCode.A00, 0),
        ),
    )
    alloc = allocate_portfolio((item,), default_resource_state(), NOW, "cyc_1")
    bundle = seal_allocation(alloc, (item,), ResourceCapacities(), opportunity_states={"opp_1": "PRICED"})
    decision = next(d for d in bundle.decisions if d.outcome == DecisionOutcome.SELECTED)
    result = reconcile_decision(
        decision,
        ObservableReconcileContext(
            now_micros=NOW + 1000,
            opportunity_state="PRICED",
            payment_succeeded=True,
            configuration_hash=decision.configuration_hash,
        ),
    )
    assert result.status.value == "STALE"
    assert "payment_already_recovered" in result.stale_factors
    assert not result.execution_ready


def test_expired_after_ttl():
    decision = _selected_decision()
    result = reconcile_decision(
        decision,
        ObservableReconcileContext(
            now_micros=decision.expires_at_micros + 1,
            opportunity_state="PRICED",
            configuration_hash=decision.configuration_hash,
        ),
    )
    assert result.status.value == "EXPIRED"
    assert not result.execution_ready


def test_config_change_stale():
    decision = _selected_decision()
    result = reconcile_decision(
        decision,
        ObservableReconcileContext(
            now_micros=NOW + 1000,
            opportunity_state="PRICED",
            configuration_hash="different_hash",
        ),
    )
    assert result.status.value == "STALE"
    assert "configuration_changed" in result.stale_factors


def test_contact_consumed_stale():
    item = make_item(
        "opp_1",
        "cust_1",
        30_000,
        (
            priced(
                "opp_1",
                ActionCode.A05,
                5000,
                (
                    ResourceRequirement("message_capacity", 1),
                    ResourceRequirement("contact_allowance", 1),
                ),
            ),
            priced("opp_1", ActionCode.A00, 0),
        ),
    )
    bundle = seal_allocation(
        allocate_portfolio((item,), default_resource_state(), NOW, "cyc_1"),
        (item,),
        ResourceCapacities(contact_allowance_per_customer=1),
    )
    decision = next(d for d in bundle.decisions if d.outcome == DecisionOutcome.SELECTED)
    store = DecisionStore()
    store.record_bundle(bundle)
    result = store.reconcile(
        decision.decision_id,
        ObservableReconcileContext(
            now_micros=NOW + 1000,
            opportunity_state="PRICED",
            contacts_used_for_customer=1,
            contact_allowance_per_customer=1,
            configuration_hash=decision.configuration_hash,
        ),
    )
    assert result.status.value == "STALE"
    assert "contact_capacity_consumed" in result.stale_factors


def test_valid_execution_ready():
    decision = _selected_decision()
    result = reconcile_decision(
        decision,
        ObservableReconcileContext(
            now_micros=NOW + 1000,
            opportunity_state="PRICED",
            configuration_hash=decision.configuration_hash,
        ),
    )
    assert result.execution_ready
    assert result.status.value == "VALID"
