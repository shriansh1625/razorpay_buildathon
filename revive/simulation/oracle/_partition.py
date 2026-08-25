"""
Oracle partition — internal storage. Decision path must not import this module.

See docs/19 §4, docs/17 outcome_oracle_partition.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from revive.domain.enums import ActionCode


@dataclass(frozen=True, slots=True)
class ActionResponse:
    would_recover: bool
    recover_at_micros: int
    amount_paise: int
    adapter_result_override: str | None = None


@dataclass(frozen=True, slots=True)
class OracleRow:
    opportunity_id: str
    customer_id: str
    recovers_naturally: bool
    natural_recovery_at_micros: int | None
    natural_amount_paise: int
    per_action_response: dict[str, ActionResponse]
    fatigue_curve: dict[int, float]
    degradation_cohort_ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "opportunity_id": self.opportunity_id,
            "customer_id": self.customer_id,
            "recovers_naturally": self.recovers_naturally,
            "natural_recovery_at_micros": self.natural_recovery_at_micros,
            "natural_amount_paise": self.natural_amount_paise,
            "per_action_response": {
                code: {
                    "would_recover": r.would_recover,
                    "recover_at_micros": r.recover_at_micros,
                    "amount_paise": r.amount_paise,
                    "adapter_result_override": r.adapter_result_override,
                }
                for code, r in self.per_action_response.items()
            },
            "fatigue_curve": dict(self.fatigue_curve),
            "degradation_cohort_ref": self.degradation_cohort_ref,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OracleRow:
        responses = {
            code: ActionResponse(
                would_recover=entry["would_recover"],
                recover_at_micros=entry["recover_at_micros"],
                amount_paise=entry["amount_paise"],
                adapter_result_override=entry.get("adapter_result_override"),
            )
            for code, entry in data["per_action_response"].items()
        }
        return cls(
            opportunity_id=data["opportunity_id"],
            customer_id=data["customer_id"],
            recovers_naturally=data["recovers_naturally"],
            natural_recovery_at_micros=data.get("natural_recovery_at_micros"),
            natural_amount_paise=data["natural_amount_paise"],
            per_action_response=responses,
            fatigue_curve={int(k): v for k, v in data["fatigue_curve"].items()},
            degradation_cohort_ref=data.get("degradation_cohort_ref"),
        )


@dataclass
class OraclePartition:
    """In-memory oracle store — serialized to dataset/oracle/ only."""

    rows: dict[str, OracleRow] = field(default_factory=dict)
    latent_traits: dict[str, dict] = field(default_factory=dict)

    def add_row(self, row: OracleRow) -> None:
        self.rows[row.opportunity_id] = row

    def get_row(self, opportunity_id: str) -> OracleRow | None:
        return self.rows.get(opportunity_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows": {oid: row.to_dict() for oid, row in self.rows.items()},
            "latent_traits": self.latent_traits,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OraclePartition:
        partition = cls(
            latent_traits=data.get("latent_traits", {}),
        )
        for oid, row_data in data.get("rows", {}).items():
            partition.rows[oid] = OracleRow.from_dict(row_data)
        return partition

    def hidden_field_names(self) -> frozenset[str]:
        return frozenset(
            {
                "intent_to_pay",
                "responsiveness_email",
                "responsiveness_sms",
                "price_sensitivity",
                "annoyance_threshold",
                "instrument_health",
                "attention_delay_minutes",
                "fatigue_sensitivity",
                "per_action_response",
                "recovers_naturally",
                "natural_recovery_at_micros",
                "fatigue_curve",
                "latent_traits",
            }
        )

    def action_codes_in_partition(self) -> frozenset[str]:
        codes: set[str] = set()
        for row in self.rows.values():
            codes.update(row.per_action_response.keys())
        codes.add(ActionCode.A00.value)
        return frozenset(codes)
