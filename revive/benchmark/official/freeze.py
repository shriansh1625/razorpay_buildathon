"""Freeze prerequisite gate — M13 §5, M13.10 seal."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from revive.benchmark.official.config import (
    OFFICIAL_SEED_COUNT,
    OfficialBenchmarkConfig,
)
from revive.benchmark.official.freeze_constants import (
    ADR_011_ACCEPTED,
    ADR_012_ACCEPTED,
    ADR_013_ACCEPTED,
    OFFICIAL_APPROVER_VERSION,
    OFFICIAL_B1_SCHEDULE_VERSION,
    OFFICIAL_CUSTOMER_COUNT,
    OFFICIAL_CYCLE_LENGTH_MINUTES,
    OFFICIAL_EPSILON_PAISE,
    OFFICIAL_HORIZON_DAYS,
    OFFICIAL_OPPORTUNITY_COUNT,
    OFFICIAL_POLICY_PACK_VERSION,
)
from revive.config.policy_pack import PolicyPackStatus
from revive.recovery.valuation.config import BENCHMARK_STRATEGY_VERSION, VALUATION_VERSION


@dataclass(frozen=True, slots=True)
class FreezeCheckResult:
    complete: bool
    blocked_reasons: tuple[str, ...]
    checklist: dict[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "complete": self.complete,
            "blocked_reasons": list(self.blocked_reasons),
            "checklist": self.checklist,
            "status": "FREEZE_COMPLETE" if self.complete else "FREEZE_INCOMPLETE",
        }


def check_freeze_prerequisites(
    config: OfficialBenchmarkConfig,
    *,
    policy_pack,
    preflight: bool = False,
) -> FreezeCheckResult:
    """Verify freeze items before official or preflight benchmark execution."""
    checklist: dict[str, str] = {}
    blocked: list[str] = []

    checklist["ADR-011"] = "ACCEPTED" if ADR_011_ACCEPTED else "DRAFT"
    if not ADR_011_ACCEPTED:
        blocked.append("ADR-011: epsilon threshold not ACCEPTED")

    checklist["ADR-012"] = "ACCEPTED" if ADR_012_ACCEPTED else "PENDING"
    if not ADR_012_ACCEPTED:
        blocked.append("ADR-012: official benchmark scale/horizon not ACCEPTED")

    checklist["ADR-013_B1_schedule"] = "ACCEPTED" if ADR_013_ACCEPTED else "DRAFT"
    if not ADR_013_ACCEPTED:
        blocked.append("ADR-013: B1 schedule not ACCEPTED")

    pp_status = policy_pack.status.value
    checklist["PolicyPack"] = pp_status
    if policy_pack.status != PolicyPackStatus.SEALED:
        blocked.append(f"PolicyPack status={pp_status}, required SEALED")
    if policy_pack.version != OFFICIAL_POLICY_PACK_VERSION:
        blocked.append(
            f"PolicyPack version={policy_pack.version}, "
            f"required {OFFICIAL_POLICY_PACK_VERSION}"
        )
    if policy_pack.epsilon_paise != OFFICIAL_EPSILON_PAISE:
        blocked.append(
            f"epsilon_paise={policy_pack.epsilon_paise}, "
            f"required {OFFICIAL_EPSILON_PAISE}"
        )

    checklist["ADR-011_epsilon"] = str(policy_pack.epsilon_paise)

    if config.b1_schedule_version != OFFICIAL_B1_SCHEDULE_VERSION:
        blocked.append(
            f"B1 schedule={config.b1_schedule_version}, "
            f"required {OFFICIAL_B1_SCHEDULE_VERSION}"
        )

    checklist["ADR-012_scale"] = (
        "ACCEPTED"
        if config.simulation_horizon_days == OFFICIAL_HORIZON_DAYS
        and config.generator_config.opportunity_count == OFFICIAL_OPPORTUNITY_COUNT
        and config.generator_config.customer_count == OFFICIAL_CUSTOMER_COUNT
        else "MISMATCH"
    )
    if config.simulation_horizon_days != OFFICIAL_HORIZON_DAYS:
        blocked.append(
            f"horizon_days={config.simulation_horizon_days}, "
            f"required {OFFICIAL_HORIZON_DAYS}"
        )
    if config.generator_config.opportunity_count != OFFICIAL_OPPORTUNITY_COUNT:
        blocked.append("opportunity_count mismatch")
    if config.generator_config.customer_count != OFFICIAL_CUSTOMER_COUNT:
        blocked.append("customer_count mismatch")
    if config.cycle_length_minutes != OFFICIAL_CYCLE_LENGTH_MINUTES:
        blocked.append("cycle_length_minutes mismatch")

    checklist["generator_config"] = "FROZEN" if ADR_012_ACCEPTED else "PROVISIONAL"

    checklist["approver_model"] = config.approver_model_version
    if config.approver_model_version != OFFICIAL_APPROVER_VERSION:
        blocked.append(
            f"approver={config.approver_model_version}, "
            f"required {OFFICIAL_APPROVER_VERSION}"
        )

    checklist["generator_version"] = config.generator_version

    official_predictor = f"{VALUATION_VERSION}:{BENCHMARK_STRATEGY_VERSION}"
    checklist["predictor_version"] = config.predictor_version
    if config.predictor_version != official_predictor:
        blocked.append(f"predictor_version={config.predictor_version}, required {official_predictor}")

    checklist["allocator_version"] = config.allocator_version
    checklist["metric_version"] = config.metric_version

    if preflight:
        seed_ok = tuple(config.seed_set) == (1,)
        checklist["seed_set"] = (
            f"{len(config.seed_set)} seeds (preflight requires exactly seed=1)"
        )
        if not seed_ok:
            blocked.append("preflight seed_set must be exactly (1,)")
    else:
        seed_ok = len(config.seed_set) >= OFFICIAL_SEED_COUNT
        checklist["seed_set"] = (
            f"{len(config.seed_set)} seeds (required >={OFFICIAL_SEED_COUNT})"
        )
        if not seed_ok:
            blocked.append(
                f"Seed set has {len(config.seed_set)} seeds; "
                f"official requires >={OFFICIAL_SEED_COUNT}"
            )
        if tuple(config.seed_set) != tuple(range(1, OFFICIAL_SEED_COUNT + 1)):
            blocked.append("seed_set must be exactly 1..20")

    complete = len(blocked) == 0
    return FreezeCheckResult(
        complete=complete,
        blocked_reasons=tuple(blocked),
        checklist=checklist,
    )
