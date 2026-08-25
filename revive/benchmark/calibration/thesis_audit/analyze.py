"""Core thesis-audit analyses — M13.7."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from revive.allocation.lagrangian import _reduced_value_paise
from revive.allocation.resources import can_reserve, normalized_resource_cost, usage_dict
from revive.benchmark.calibration.thesis_audit.actions import action_category
from revive.benchmark.calibration.thesis_audit.cycle import CycleSnapshot
from revive.domain.enums import ActionCode


_RESOURCE_KEYS = (
    "retry_slots",
    "message_capacity",
    "voice_minutes",
    "human_review_slots",
    "incentive_budget",
    "contact_allowance",
)


@dataclass
class BindingResourceRow:
    resource: str
    binding_frequency: float
    average_utilization: float
    peak_utilization: float
    shadow_price_frequency: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource": self.resource,
            "binding_frequency": self.binding_frequency,
            "average_utilization": self.average_utilization,
            "peak_utilization": self.peak_utilization,
            "shadow_price_frequency": self.shadow_price_frequency,
        }


@dataclass
class ShadowPriceStats:
    resource: str
    mean: float
    median: float
    max_value: float
    nonzero_cycle_pct: float
    selection_change_pct: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "resource": self.resource,
            "mean": self.mean,
            "median": self.median,
            "max": self.max_value,
            "nonzero_cycle_pct": self.nonzero_cycle_pct,
            "selection_change_pct": self.selection_change_pct,
        }


@dataclass
class CycleAuditResult:
    seed: int
    profile: str
    opportunity_count: int
    customer_count: int
    simulation_window_days: int
    binding_rows: list[BindingResourceRow]
    shadow_stats: list[ShadowPriceStats]
    portfolio_conflicts: int
    conflict_rate: float
    conflict_by_resource: dict[str, int]
    resource_density_inversions: int
    inversion_by_resource: dict[str, int]
    candidate_action_shares: dict[str, float]
    feasible_action_shares: dict[str, float]
    b3_selected_shares: dict[str, float]
    revive_selected_shares: dict[str, float]
    b3_dominant_action: str | None
    revive_dominant_action: str | None
    differing_allocations: int
    identical_enrv_cause: str
    same_action_reasons: dict[str, int]
    different_action_reasons: dict[str, int]
    allocator_mode: str
    fallback_used: bool
    opportunities_in_cycle: int
    candidates_in_cycle: int
    distinct_actions_in_cycle: int
    shared_resource_pairs: int
    customers_with_multiple_opps: int
    customer_contact_conflicts: int
    competition_ratio_retry: float
    b3_total_enrv: int
    revive_total_enrv: int
    shadow_prices: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "seed": self.seed,
            "profile": self.profile,
            "opportunity_count": self.opportunity_count,
            "customer_count": self.customer_count,
            "simulation_window_days": self.simulation_window_days,
            "binding_rows": [r.to_dict() for r in self.binding_rows],
            "shadow_stats": [s.to_dict() for s in self.shadow_stats],
            "portfolio_conflicts": self.portfolio_conflicts,
            "conflict_rate": self.conflict_rate,
            "conflict_by_resource": self.conflict_by_resource,
            "resource_density_inversions": self.resource_density_inversions,
            "inversion_by_resource": self.inversion_by_resource,
            "candidate_action_shares": self.candidate_action_shares,
            "feasible_action_shares": self.feasible_action_shares,
            "b3_selected_shares": self.b3_selected_shares,
            "revive_selected_shares": self.revive_selected_shares,
            "b3_dominant_action": self.b3_dominant_action,
            "revive_dominant_action": self.revive_dominant_action,
            "differing_allocations": self.differing_allocations,
            "identical_enrv_cause": self.identical_enrv_cause,
            "same_action_reasons": self.same_action_reasons,
            "different_action_reasons": self.different_action_reasons,
            "allocator_mode": self.allocator_mode,
            "fallback_used": self.fallback_used,
            "opportunities_in_cycle": self.opportunities_in_cycle,
            "candidates_in_cycle": self.candidates_in_cycle,
            "distinct_actions_in_cycle": self.distinct_actions_in_cycle,
            "shared_resource_pairs": self.shared_resource_pairs,
            "customers_with_multiple_opps": self.customers_with_multiple_opps,
            "customer_contact_conflicts": self.customer_contact_conflicts,
            "competition_ratio_retry": self.competition_ratio_retry,
            "b3_total_enrv": self.b3_total_enrv,
            "revive_total_enrv": self.revive_total_enrv,
            "shadow_prices": self.shadow_prices,
        }


def _capacity_map(caps) -> dict[str, int]:
    return {
        "retry_slots": caps.retry_slots,
        "message_capacity": caps.message_capacity,
        "voice_minutes": caps.voice_minutes,
        "human_review_slots": caps.human_review_slots,
        "incentive_budget": caps.incentive_budget_paise,
        "contact_allowance": caps.contact_allowance_per_customer,
    }


def _positive_candidates(snapshot: CycleSnapshot) -> list[tuple[Any, Any]]:
    eps = snapshot.policy.epsilon_paise
    out: list[tuple[Any, Any]] = []
    for item in snapshot.items:
        for pc in item.candidates:
            if pc.action_code == ActionCode.A00:
                continue
            if pc.enrv_paise > eps:
                out.append((item, pc))
    return out


def _density(pc) -> float:
    return pc.enrv_paise / normalized_resource_cost(usage_dict(pc))


def _binding_resources(snapshot: CycleSnapshot) -> list[BindingResourceRow]:
    caps = snapshot.capacities
    cap_map = _capacity_map(caps)
    revive = snapshot.revive_state
    b3 = snapshot.b3_state
    shadows = snapshot.revive_result.shadow_prices

    rows: list[BindingResourceRow] = []
    for resource in _RESOURCE_KEYS:
        cap = cap_map.get(resource, 0)
        if cap <= 0:
            continue
        if resource == "retry_slots":
            used_b3 = b3.retry_slots_used
            used_rev = revive.retry_slots_used
        elif resource == "message_capacity":
            used_b3 = b3.message_capacity_used
            used_rev = revive.message_capacity_used
        elif resource == "voice_minutes":
            used_b3 = b3.voice_minutes_used
            used_rev = revive.voice_minutes_used
        elif resource == "human_review_slots":
            used_b3 = b3.human_review_slots_used
            used_rev = revive.human_review_slots_used
        elif resource == "incentive_budget":
            used_b3 = b3.incentive_budget_used_paise
            used_rev = revive.incentive_budget_used_paise
        else:
            used_b3 = 0
            used_rev = 0
            for cust, cnt in revive.customer_contacts.items():
                used_rev = max(used_rev, cnt)
            for cust, cnt in b3.customer_contacts.items():
                used_b3 = max(used_b3, cnt)

        util_b3 = used_b3 / cap
        util_rev = used_rev / cap
        avg_util = (util_b3 + util_rev) / 2.0
        peak_util = max(util_b3, util_rev)
        binding = peak_util >= 0.99
        shadow_freq = 1.0 if shadows.get(resource, 0) > 0 else 0.0
        rows.append(
            BindingResourceRow(
                resource=resource,
                binding_frequency=1.0 if binding else 0.0,
                average_utilization=avg_util,
                peak_utilization=peak_util,
                shadow_price_frequency=shadow_freq,
            )
        )
    return rows


def _count_portfolio_conflicts(snapshot: CycleSnapshot) -> tuple[int, dict[str, int], int]:
    eps = snapshot.policy.epsilon_paise
    lambdas = {k: snapshot.revive_result.shadow_prices.get(k, 0.0) for k in _RESOURCE_KEYS}
    pool = _positive_candidates(snapshot)

    conflict_by_resource: dict[str, int] = defaultdict(int)
    conflicts = 0

    for resource in _RESOURCE_KEYS:
        using: list[tuple[Any, Any, float, float, int]] = []
        for item, pc in pool:
            u = usage_dict(pc)
            qty = u.get(resource, 0)
            if qty <= 0:
                continue
            density = _density(pc)
            rv = _reduced_value_paise(pc, lambdas, item.customer_id)
            using.append((item, pc, density, float(rv), qty))

        for i in range(len(using)):
            for j in range(i + 1, len(using)):
                item_a, pc_a, dens_a, rv_a, _ = using[i]
                item_b, pc_b, dens_b, rv_b, _ = using[j]
                if item_a.opportunity_id == item_b.opportunity_id:
                    continue
                enrv_a, enrv_b = pc_a.enrv_paise, pc_b.enrv_paise
                if enrv_a == enrv_b:
                    continue
                inversion = (enrv_a > enrv_b and dens_a < dens_b) or (
                    enrv_b > enrv_a and dens_b < dens_a
                )
                rv_flip = (enrv_a > enrv_b and rv_a < rv_b) or (
                    enrv_b > enrv_a and rv_b < rv_a
                )
                if inversion or rv_flip:
                    conflicts += 1
                    conflict_by_resource[resource] += 1

    inversion_total = 0
    inversion_by_resource: dict[str, int] = defaultdict(int)
    for item in snapshot.items:
        pcs = [
            pc
            for pc in item.candidates
            if pc.action_code != ActionCode.A00 and pc.enrv_paise > eps
        ]
        for i in range(len(pcs)):
            for j in range(i + 1, len(pcs)):
                a, b = pcs[i], pcs[j]
                if a.enrv_paise == b.enrv_paise:
                    continue
                dens_a, dens_b = _density(a), _density(b)
                if (a.enrv_paise > b.enrv_paise and dens_a < dens_b) or (
                    b.enrv_paise > a.enrv_paise and dens_b < dens_a
                ):
                    inversion_total += 1
                    for resource in _RESOURCE_KEYS:
                        ua, ub = usage_dict(a), usage_dict(b)
                        if ua.get(resource, 0) > 0 and ub.get(resource, 0) > 0:
                            inversion_by_resource[resource] += 1

    return conflicts, dict(conflict_by_resource), inversion_total


def _action_shares(counter: Counter[str], total: int) -> dict[str, float]:
    if total <= 0:
        return {}
    return {k: v / total for k, v in counter.items()}


def _dominant_action(shares: dict[str, float]) -> str | None:
    if not shares:
        return None
    return max(shares.items(), key=lambda x: x[1])[0]


def _decompose_allocations(snapshot: CycleSnapshot) -> tuple[int, str, dict[str, int], dict[str, int]]:
    eps = snapshot.policy.epsilon_paise
    lambdas = {k: snapshot.revive_result.shadow_prices.get(k, 0.0) for k in _RESOURCE_KEYS}
    same_reasons: dict[str, int] = defaultdict(int)
    diff_reasons: dict[str, int] = defaultdict(int)
    differing = 0

    for item in snapshot.items:
        opp_id = item.opportunity_id
        b3_act = snapshot.b3_selections.get(opp_id)
        rev_act = snapshot.revive_selections.get(opp_id)
        if b3_act == rev_act:
            if b3_act is None and rev_act is None:
                same_reasons["both_no_selection"] += 1
            elif b3_act == rev_act:
                pcs = [pc for pc in item.candidates if pc.action_code.value == b3_act]
                if pcs:
                    pc = pcs[0]
                    rv = _reduced_value_paise(pc, lambdas, item.customer_id)
                    if rv == pc.enrv_paise and not lambdas:
                        same_reasons["zero_shadow_price"] += 1
                    else:
                        same_reasons["same_highest_enrv_or_rv"] += 1
                else:
                    same_reasons["same_action_unknown_candidate"] += 1
            continue

        differing += 1
        if b3_act and not rev_act:
            diff_reasons["revive_deferred_b3_selected"] += 1
        elif rev_act and not b3_act:
            diff_reasons["b3_deferred_revive_selected"] += 1
        else:
            diff_reasons["different_action_both_selected"] += 1

    identical_cause = "A_identical_candidates"
    if differing > 0:
        if snapshot.b3_total_enrv == snapshot.revive_total_enrv:
            identical_cause = "B_different_candidates_equal_enrv"
        else:
            identical_cause = "different_allocations"
    elif snapshot.revive_result.shadow_prices and all(
        v == 0 for v in snapshot.revive_result.shadow_prices.values()
    ):
        identical_cause = "D_shadow_prices_zero"
    elif snapshot.revive_result.allocator_mode.value == "FALLBACK_GREEDY":
        identical_cause = "E_fallback_dominating"
    elif snapshot.b3_total_enrv == snapshot.revive_total_enrv:
        identical_cause = "A_identical_candidates"

    return differing, identical_cause, dict(same_reasons), dict(diff_reasons)


def _customer_competition(snapshot: CycleSnapshot) -> tuple[int, int]:
    by_customer: dict[str, list] = defaultdict(list)
    for item in snapshot.items:
        if item.customer_id:
            by_customer[item.customer_id].append(item)

    multi = sum(1 for opps in by_customer.values() if len(opps) > 1)
    contact_conflicts = 0
    eps = snapshot.policy.epsilon_paise
    allowance = snapshot.capacities.contact_allowance_per_customer

    for cust, opps in by_customer.items():
        if len(opps) < 2:
            continue
        contact_candidates = 0
        for item in opps:
            for pc in item.candidates:
                if pc.action_code == ActionCode.A00:
                    continue
                if pc.enrv_paise <= eps:
                    continue
                if usage_dict(pc).get("contact_allowance", 0) > 0:
                    contact_candidates += 1
        if contact_candidates > allowance:
            contact_conflicts += 1

    return multi, contact_conflicts


def _competition_ratio_retry(snapshot: CycleSnapshot) -> float:
    eps = snapshot.policy.epsilon_paise
    demand = 0
    for item in snapshot.items:
        for pc in item.candidates:
            if pc.action_code == ActionCode.A00 or pc.enrv_paise <= eps:
                continue
            demand += usage_dict(pc).get("retry_slots", 0)
    cap = snapshot.capacities.retry_slots or 1
    return demand / cap


def analyze_cycle(snapshot: CycleSnapshot) -> CycleAuditResult:
    eps = snapshot.policy.epsilon_paise
    binding_rows = _binding_resources(snapshot)
    conflicts, conflict_by_res, inversion_total = _count_portfolio_conflicts(snapshot)

    shadows = snapshot.revive_result.shadow_prices
    shadow_stats: list[ShadowPriceStats] = []
    for resource in _RESOURCE_KEYS:
        val = shadows.get(resource, 0.0)
        shadow_stats.append(
            ShadowPriceStats(
                resource=resource,
                mean=val,
                median=val,
                max_value=val,
                nonzero_cycle_pct=100.0 if val > 0 else 0.0,
                selection_change_pct=0.0,
            )
        )

    cand_counter: Counter[str] = Counter()
    feas_counter: Counter[str] = Counter()
    total_cands = 0
    distinct_actions: set[str] = set()

    for item in snapshot.items:
        for pc in item.candidates:
            if pc.action_code == ActionCode.A00:
                continue
            cat = action_category(pc.action_code)
            cand_counter[cat] += 1
            total_cands += 1
            distinct_actions.add(pc.action_code.value)
            if pc.enrv_paise > eps and can_reserve(
                snapshot.revive_state, usage_dict(pc), item.customer_id
            ):
                feas_counter[cat] += 1

    b3_counter: Counter[str] = Counter()
    for act in snapshot.b3_selections.values():
        b3_counter[action_category(ActionCode(act))] += 1

    revive_counter: Counter[str] = Counter()
    for act in snapshot.revive_selections.values():
        revive_counter[action_category(ActionCode(act))] += 1

    differing, identical_cause, same_reasons, diff_reasons = _decompose_allocations(snapshot)
    multi_cust, contact_conflicts = _customer_competition(snapshot)

    shared_pairs = 0
    pool = _positive_candidates(snapshot)
    for i in range(len(pool)):
        for j in range(i + 1, len(pool)):
            ua = usage_dict(pool[i][1])
            ub = usage_dict(pool[j][1])
            if any(
                ua.get(r, 0) > 0 and ub.get(r, 0) > 0 for r in _RESOURCE_KEYS
            ):
                shared_pairs += 1

    opp_count = len(snapshot.items)
    conflict_rate = conflicts / max(1, shared_pairs)

    return CycleAuditResult(
        seed=snapshot.seed,
        profile=snapshot.profile,
        opportunity_count=snapshot.opportunity_count,
        customer_count=snapshot.customer_count,
        simulation_window_days=snapshot.simulation_window_days,
        binding_rows=binding_rows,
        shadow_stats=shadow_stats,
        portfolio_conflicts=conflicts,
        conflict_rate=conflict_rate,
        conflict_by_resource=conflict_by_res,
        resource_density_inversions=inversion_total,
        inversion_by_resource={},
        candidate_action_shares=_action_shares(cand_counter, total_cands),
        feasible_action_shares=_action_shares(feas_counter, sum(feas_counter.values())),
        b3_selected_shares=_action_shares(b3_counter, sum(b3_counter.values())),
        revive_selected_shares=_action_shares(revive_counter, sum(revive_counter.values())),
        b3_dominant_action=_dominant_action(dict(b3_counter)),
        revive_dominant_action=_dominant_action(dict(revive_counter)),
        differing_allocations=differing,
        identical_enrv_cause=identical_cause,
        same_action_reasons=same_reasons,
        different_action_reasons=diff_reasons,
        allocator_mode=snapshot.revive_result.allocator_mode.value,
        fallback_used=snapshot.revive_result.allocator_mode.value == "FALLBACK_GREEDY",
        opportunities_in_cycle=opp_count,
        candidates_in_cycle=total_cands,
        distinct_actions_in_cycle=len(distinct_actions),
        shared_resource_pairs=shared_pairs,
        customers_with_multiple_opps=multi_cust,
        customer_contact_conflicts=contact_conflicts,
        competition_ratio_retry=_competition_ratio_retry(snapshot),
        b3_total_enrv=snapshot.b3_total_enrv,
        revive_total_enrv=snapshot.revive_total_enrv,
        shadow_prices=dict(shadows),
    )
