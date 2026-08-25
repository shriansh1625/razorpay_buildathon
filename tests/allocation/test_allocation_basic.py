"""Portfolio allocation basics."""

from revive.domain.enums import ActionCode, DecisionOutcome
from revive.allocation import (
    allocate_portfolio,
    default_allocator_config,
    default_resource_state,
    ResourceCapacities,
)
from revive.config.policy_pack import PolicyPack, PolicyPackStatus
from revive.recovery.candidates.models import ResourceRequirement
from tests.allocation.helpers import make_item, priced

NOW = 3_600_000_000


def test_single_opportunity_allocated():
    item = make_item(
        "opp_1",
        "cust_1",
        50_000,
        (
            priced(
                "opp_1",
                ActionCode.A03,
                5000,
                (ResourceRequirement("message_capacity", 1), ResourceRequirement("contact_allowance", 1)),
            ),
            priced("opp_1", ActionCode.A00, 0),
        ),
    )
    state = default_resource_state()
    result = allocate_portfolio((item,), state, NOW, "cyc_1")
    selected = result.selected_assignments()
    assert len(selected) == 1
    assert selected[0].action_code == ActionCode.A03
    assert result.total_allocated_enrv_paise == 5000


def test_no_action_when_below_epsilon():
    item = make_item(
        "opp_1",
        "cust_1",
        10_000,
        (
            priced(
                "opp_1",
                ActionCode.A03,
                100,
                (ResourceRequirement("message_capacity", 1), ResourceRequirement("contact_allowance", 1)),
            ),
            priced("opp_1", ActionCode.A00, 0),
        ),
    )
    policy = PolicyPack(
        version="test",
        status=PolicyPackStatus.DRAFT,
        epsilon_paise=500,
    )
    result = allocate_portfolio((item,), default_resource_state(), NOW, "cyc_1", policy=policy)
    assert result.assignments[0].outcome == DecisionOutcome.NO_ACTION


def test_opportunity_exclusivity():
    item = make_item(
        "opp_1",
        "cust_1",
        50_000,
        (
            priced(
                "opp_1",
                ActionCode.A03,
                8000,
                (ResourceRequirement("message_capacity", 1), ResourceRequirement("contact_allowance", 1)),
            ),
            priced(
                "opp_1",
                ActionCode.A04,
                7000,
                (ResourceRequirement("message_capacity", 1), ResourceRequirement("contact_allowance", 1)),
            ),
            priced("opp_1", ActionCode.A00, 0),
        ),
    )
    result = allocate_portfolio((item,), default_resource_state(), NOW, "cyc_1")
    assert len(result.selected_assignments()) == 1


def test_contact_limit_per_customer():
    item_a = make_item(
        "opp_a",
        "cust_1",
        40_000,
        (
            priced(
                "opp_a",
                ActionCode.A05,
                6000,
                (ResourceRequirement("message_capacity", 1), ResourceRequirement("contact_allowance", 1)),
            ),
            priced("opp_a", ActionCode.A00, 0),
        ),
    )
    item_b = make_item(
        "opp_b",
        "cust_1",
        30_000,
        (
            priced(
                "opp_b",
                ActionCode.A05,
                5000,
                (ResourceRequirement("message_capacity", 1), ResourceRequirement("contact_allowance", 1)),
            ),
            priced("opp_b", ActionCode.A00, 0),
        ),
    )
    caps = ResourceCapacities(message_capacity=2, contact_allowance_per_customer=1)
    result = allocate_portfolio(
        (item_a, item_b),
        default_resource_state(caps),
        NOW,
        "cyc_1",
    )
    selected = result.selected_assignments()
    assert len(selected) == 1
    deferred = result.deferred_assignments()
    assert len(deferred) == 1
