"""B3 differentiation and resource-density fallback."""

from revive.domain.enums import ActionCode, DecisionOutcome
from revive.allocation import allocate_portfolio, AllocatorConfig, default_resource_state, ResourceCapacities
from revive.config.policy_pack import PolicyPack, PolicyPackStatus
from revive.recovery.candidates.models import ResourceRequirement
from tests.allocation.helpers import make_item, priced


def b3_style_greedy_enrv(items, state, epsilon_paise: int):
    """B3-style: per-opportunity best ENRV, global sort by raw ENRV."""
    from revive.allocation.resources import can_reserve, reserve, usage_dict

    ranked: list[tuple[int, str, object]] = []
    for item in items:
        best = None
        best_enrv = epsilon_paise
        for pc in item.candidates:
            if pc.action_code == ActionCode.A00:
                continue
            if pc.enrv_paise > best_enrv:
                best_enrv = pc.enrv_paise
                best = pc
        if best is not None:
            ranked.append((best_enrv, item.opportunity_id, item, best))
    ranked.sort(key=lambda t: (-t[0], t[1]))

    selected: dict[str, ActionCode] = {}
    for enrv, opp_id, item, pc in ranked:
        if opp_id in selected:
            continue
        usage = usage_dict(pc)
        if can_reserve(state, usage, item.customer_id):
            if reserve(state, usage, item.customer_id):
                selected[opp_id] = pc.action_code
    return selected


def test_fallback_density_differs_from_b3_raw_enrv():
    """Fallback uses ENRV/resource density — not raw ENRV greedy (B3)."""
    high_cost = priced(
        "opp_high",
        ActionCode.A05,
        6000,
        (
            ResourceRequirement("message_capacity", 1),
            ResourceRequirement("contact_allowance", 1),
            ResourceRequirement("incentive_budget", 1),
        ),
        incentive_tier="TIER_3",
    )
    low_cost = priced(
        "opp_low",
        ActionCode.A05,
        5500,
        (
            ResourceRequirement("message_capacity", 1),
            ResourceRequirement("contact_allowance", 1),
        ),
    )
    items = (
        make_item("opp_high", "cust_h", 100_000, (high_cost, priced("opp_high", ActionCode.A00, 0))),
        make_item("opp_low", "cust_l", 80_000, (low_cost, priced("opp_low", ActionCode.A00, 0))),
    )
    caps = ResourceCapacities(message_capacity=1, contact_allowance_per_customer=1)
    policy = PolicyPack(version="t", status=PolicyPackStatus.DRAFT, epsilon_paise=0)

    b3_state = default_resource_state(caps)
    b3_selected = b3_style_greedy_enrv(items, b3_state, policy.epsilon_paise)
    assert b3_selected.get("opp_high") == ActionCode.A05

    m8_state = default_resource_state(caps)
    cfg = AllocatorConfig(force_fallback=True)
    m8_result = allocate_portfolio(items, m8_state, 1, "cyc", policy=policy, config=cfg)
    selected = m8_result.selected_assignments()
    assert len(selected) == 1
    assert selected[0].opportunity_id == "opp_low"
    assert m8_result.allocator_mode.value == "FALLBACK_GREEDY"


def test_positive_enrv_not_guaranteed_selection():
    item_a = make_item(
        "opp_a",
        "cust_a",
        100_000,
        (
            priced(
                "opp_a",
                ActionCode.A12,
                9000,
                (
                    ResourceRequirement("voice_minutes", 5),
                    ResourceRequirement("contact_allowance", 1),
                ),
            ),
            priced("opp_a", ActionCode.A00, 0),
        ),
    )
    item_b = make_item(
        "opp_b",
        "cust_b",
        80_000,
        (
            priced(
                "opp_b",
                ActionCode.A05,
                7000,
                (
                    ResourceRequirement("message_capacity", 1),
                    ResourceRequirement("contact_allowance", 1),
                ),
            ),
            priced("opp_b", ActionCode.A00, 0),
        ),
    )
    caps = ResourceCapacities(voice_minutes=0, message_capacity=1)
    result = allocate_portfolio(
        (item_a, item_b),
        default_resource_state(caps),
        1,
        "cyc",
    )
    assert result.assignments[0].outcome in (
        DecisionOutcome.DEFERRED,
        DecisionOutcome.NO_ACTION,
    )
    selected = result.selected_assignments()
    assert len(selected) == 1
    assert selected[0].opportunity_id == "opp_b"
    assert selected[0].enrv_paise == 7000
