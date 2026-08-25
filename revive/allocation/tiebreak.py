"""Deterministic ordering — docs/10 §7."""

from __future__ import annotations

from revive.domain.enums import ActionCode
from revive.allocation.models import PricedCandidate, PortfolioItem


def sort_key_candidate(
    item: PortfolioItem,
    pc: PricedCandidate,
    score_paise: int,
) -> tuple[int, int, str, str]:
    return (
        -score_paise,
        -item.value_at_risk_paise,
        item.opportunity_id,
        pc.action_code.value,
    )


def sort_key_opportunity(item: PortfolioItem) -> str:
    return item.opportunity_id
