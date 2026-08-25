"""Idempotency, supersession, oracle isolation."""

import inspect

from revive.integrity import assert_decision_path_does_not_import_oracle
from revive.decision import DecisionStore, seal_allocation
from revive.decision.models import AllocationDecision, DecisionLifecycleStatus
from revive.decision.seal import seal_allocation as seal_fn
from revive.domain.enums import ActionCode, DecisionOutcome
from revive.allocation import allocate_portfolio, default_resource_state, ResourceCapacities
from revive.recovery.candidates.models import ResourceRequirement
from tests.allocation.helpers import make_item, priced

NOW = 3_600_000_000


def test_decision_modules_no_oracle():
    assert_decision_path_does_not_import_oracle()


def test_no_allocator_rerun_in_reconcile_module():
    from revive.decision import reconcile as reconcile_mod

    source = inspect.getsource(reconcile_mod.reconcile_decision)
    assert "allocate_portfolio" not in source


def test_reconcile_idempotent():
    item = make_item(
        "opp_1",
        "cust_1",
        25_000,
        (
            priced(
                "opp_1",
                ActionCode.A03,
                4500,
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
        ResourceCapacities(),
    )
    store = DecisionStore()
    store.record_bundle(bundle)
    decision = bundle.decisions[0]
    from revive.decision.models import ObservableReconcileContext

    ctx = ObservableReconcileContext(
        now_micros=NOW + 500,
        opportunity_state="PRICED",
        configuration_hash=decision.configuration_hash,
    )
    r1 = store.reconcile(decision.decision_id, ctx)
    r2 = store.reconcile(decision.decision_id, ctx)
    assert r1.to_dict() == r2.to_dict()
    assert len(store.transitions_for(decision.decision_id)) <= 1


def test_supersession_preserves_history():
    item = make_item(
        "opp_1",
        "cust_1",
        25_000,
        (
            priced(
                "opp_1",
                ActionCode.A03,
                4500,
                (
                    ResourceRequirement("message_capacity", 1),
                    ResourceRequirement("contact_allowance", 1),
                ),
            ),
            priced("opp_1", ActionCode.A00, 0),
        ),
    )
    bundle1 = seal_allocation(
        allocate_portfolio((item,), default_resource_state(), NOW, "cyc_1"),
        (item,),
        ResourceCapacities(),
    )
    store = DecisionStore()
    store.record_bundle(bundle1)
    old = bundle1.decisions[0]

    bundle2 = seal_allocation(
        allocate_portfolio((item,), default_resource_state(), NOW + 1000, "cyc_2"),
        (item,),
        ResourceCapacities(),
    )
    new = bundle2.decisions[0]
    superseded = store.supersede(old.decision_id, new)

    assert superseded.lifecycle_status == DecisionLifecycleStatus.SUPERSEDED
    assert superseded.superseded_by == new.decision_id
    assert store.get(old.decision_id) is not None
    assert store.get(new.decision_id) is not None
