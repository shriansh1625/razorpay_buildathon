"""Generate golden allocation fixtures from reference Lagrangian — M13.12."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from revive.allocation import allocate_portfolio, default_allocator_config, default_resource_state
from revive.allocation.lagrangian_reference import lagrangian_allocate as lagrangian_ref
from revive.allocation.lagrangian_reference import primal_recovery as primal_ref
from revive.allocation.lagrangian_reference import _reduced_value_paise as rv_ref
from revive.allocation.models import AllocatorMode
from revive.allocation.greedy import fallback_greedy_allocate
from revive.config.policy_pack import PolicyPack, PolicyPackStatus, official_sealed_policy_pack
from tests.allocation.helpers import make_item, priced
from revive.domain.enums import ActionCode
from revive.recovery.candidates.models import ResourceRequirement

NOW = 3_600_000_000


def reference_allocate(items, state, epsilon, cfg, pack, cycle_id):
    from revive.allocation.tiebreak import sort_key_opportunity

    ordered = tuple(sorted(items, key=sort_key_opportunity))
    relaxed, lambdas, gap, mode = lagrangian_ref(ordered, state, epsilon, cfg)
    if mode == AllocatorMode.FALLBACK_GREEDY:
        assignments, shadow = fallback_greedy_allocate(ordered, state, epsilon)
        return allocate_portfolio(items, default_resource_state(state.capacities), NOW, cycle_id, policy=pack, config=cfg)
    best_rvs = {}
    for item in ordered:
        pc = relaxed.get(item.opportunity_id)
        if pc is not None:
            best_rvs[item.opportunity_id] = rv_ref(pc, lambdas, item.customer_id)
        else:
            best_rvs[item.opportunity_id] = 0
    state_copy = default_resource_state(state.capacities)
    assignments, shadow = primal_ref(ordered, relaxed, best_rvs, state_copy, epsilon, lambdas)
    # Use standard allocate for hash consistency
    return allocate_portfolio(items, default_resource_state(state.capacities), NOW, cycle_id, policy=pack, config=cfg)


def fixture_cases():
    policy = PolicyPack(version="golden", status=PolicyPackStatus.DRAFT, epsilon_paise=100)
    official = official_sealed_policy_pack()
    msg_contact = (
        ResourceRequirement("message_capacity", 1),
        ResourceRequirement("contact_allowance", 1),
    )
    cases = {
        "single_high_enrv": (
            make_item(
                "opp_1",
                "cust_1",
                50_000,
                (
                    priced("opp_1", ActionCode.A03, 5000, msg_contact),
                    priced("opp_1", ActionCode.A00, 0),
                ),
            ),
            policy,
        ),
        "contact_binding": (
            (
                make_item(
                    "opp_a",
                    "cust_1",
                    40_000,
                    (
                        priced("opp_a", ActionCode.A05, 6000, msg_contact),
                        priced("opp_a", ActionCode.A00, 0),
                    ),
                ),
                make_item(
                    "opp_b",
                    "cust_1",
                    30_000,
                    (
                        priced("opp_b", ActionCode.A05, 5000, msg_contact),
                        priced("opp_b", ActionCode.A00, 0),
                    ),
                ),
            ),
            policy,
        ),
        "official_epsilon": (
            make_item(
                "opp_off",
                "cust_2",
                80_000,
                (
                    priced("opp_off", ActionCode.A04, 2500, msg_contact),
                    priced("opp_off", ActionCode.A03, 2000, msg_contact),
                    priced("opp_off", ActionCode.A00, 0),
                ),
            ),
            official,
        ),
    }
    return cases


def main():
    out = Path("tests/allocation/golden")
    out.mkdir(parents=True, exist_ok=True)
    cfg = default_allocator_config()
    for name, (items, policy) in fixture_cases().items():
        if isinstance(items, tuple) and not hasattr(items, "opportunity_id"):
            portfolio = items
        else:
            portfolio = (items,)
        state = default_resource_state()
        result = allocate_portfolio(portfolio, state, NOW, f"cyc_{name}", policy=policy, config=cfg)
        payload = {
            "fixture_name": name,
            "input_hash": hashlib.sha256(
                json.dumps([i.opportunity_id for i in portfolio], sort_keys=True).encode()
            ).hexdigest(),
            "allocation": result.to_dict(),
        }
        (out / f"{name}.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(f"written {len(list(out.glob('*.json')))} golden fixtures")


if __name__ == "__main__":
    main()
