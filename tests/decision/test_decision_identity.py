"""Decision identity and configuration hash tests."""

from revive.config.policy_pack import PolicyPack, PolicyPackStatus
from revive.decision import (
    configuration_hash,
    decision_id_for,
    seal_allocation,
    DecisionStore,
)
from revive.allocation import allocate_portfolio, default_resource_state, ResourceCapacities
from revive.allocation.config import default_allocator_config
from revive.domain.enums import ActionCode, DecisionOutcome
from revive.decision.models import DecisionLifecycleStatus, ObservableReconcileContext
from revive.recovery.candidates.models import ResourceRequirement
from tests.allocation.helpers import make_item, priced

NOW = 3_600_000_000


def _bundle():
    item = make_item(
        "opp_1",
        "cust_1",
        20_000,
        (
            priced(
                "opp_1",
                ActionCode.A03,
                4000,
                (
                    ResourceRequirement("message_capacity", 1),
                    ResourceRequirement("contact_allowance", 1),
                ),
            ),
            priced("opp_1", ActionCode.A00, 0),
        ),
    )
    alloc = allocate_portfolio((item,), default_resource_state(), NOW, "cyc_1")
    return seal_allocation(
        alloc,
        (item,),
        ResourceCapacities(),
        opportunity_states={"opp_1": "PRICED"},
    )


def test_deterministic_decision_id():
    b1 = _bundle()
    b2 = _bundle()
    d1 = b1.decisions[0]
    d2 = b2.decisions[0]
    assert d1.decision_id == d2.decision_id
    assert d1.decision_id.startswith("dec_")


def test_different_cycle_different_decision_id():
    item = make_item(
        "opp_1",
        "cust_1",
        20_000,
        (
            priced(
                "opp_1",
                ActionCode.A03,
                4000,
                (
                    ResourceRequirement("message_capacity", 1),
                    ResourceRequirement("contact_allowance", 1),
                ),
            ),
            priced("opp_1", ActionCode.A00, 0),
        ),
    )
    a1 = allocate_portfolio((item,), default_resource_state(), NOW, "cyc_a")
    a2 = allocate_portfolio((item,), default_resource_state(), NOW, "cyc_b")
    b1 = seal_allocation(a1, (item,), ResourceCapacities())
    b2 = seal_allocation(a2, (item,), ResourceCapacities())
    assert b1.decisions[0].decision_id != b2.decisions[0].decision_id


def test_config_hash_stable():
    b = _bundle()
    assert b.configuration_hash
    assert b.decisions[0].configuration_hash == b.configuration_hash


def test_idempotent_store_record():
    bundle = _bundle()
    store = DecisionStore()
    first = store.record_bundle(bundle)
    second = store.record_bundle(bundle)
    assert first.to_dict() == second.to_dict()
    assert len(store._bundles) == 1
