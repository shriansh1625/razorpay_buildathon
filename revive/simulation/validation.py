"""Dataset invariant validation."""

from __future__ import annotations

from revive.errors.exceptions import InvariantViolationError
from revive.simulation.generator import GeneratedDataset
from revive.simulation.observation import get_observable_state
from revive.simulation.oracle._partition import OraclePartition


def validate_dataset(dataset: GeneratedDataset) -> list[str]:
    """Run invariant checks; return list of violations (empty if valid)."""
    violations: list[str] = []
    world = dataset.world
    partition = dataset.oracle_partition

    seen_ids: set[str] = set()
    for opp in world.opportunities:
        if opp.opportunity_id in seen_ids:
            violations.append(f"duplicate opportunity_id {opp.opportunity_id}")
        seen_ids.add(opp.opportunity_id)
        if opp.value_at_risk_paise <= 0:
            violations.append(f"non-positive value_at_risk {opp.opportunity_id}")
        if opp.first_detected_at_micros > opp.recovery_window_expires_at_micros:
            violations.append(f"temporal inversion {opp.opportunity_id}")

    customer_ids = {c.customer_id for c in world.customers}
    for opp in world.opportunities:
        if opp.customer_id not in customer_ids:
            violations.append(f"orphan opportunity customer {opp.opportunity_id}")
        if partition.get_row(opp.opportunity_id) is None:
            violations.append(f"missing oracle row {opp.opportunity_id}")

    signal_hashes: dict[str, str] = {}
    for sig in world.signals:
        if sig.dedupe_hash in signal_hashes:
            if "duplicate_signal" not in world.adversarial_case_ids:
                violations.append(f"duplicate dedupe_hash {sig.signal_id}")
        signal_hashes[sig.dedupe_hash] = sig.signal_id

    observable = get_observable_state(world)
    hidden = observable.contains_hidden_keys()
    if hidden:
        violations.append(f"hidden keys in observable payload: {hidden}")

    for inv in world.invoices:
        total = (
            inv.paid_amount_paise
            + inv.credited_amount_paise
            + inv.written_off_amount_paise
            + inv.disputed_amount_paise
        )
        if total > inv.issued_amount_paise:
            violations.append(f"invoice invariant DM-1 violated {inv.invoice_id}")

    return violations


def assert_dataset_valid(dataset: GeneratedDataset) -> None:
    violations = validate_dataset(dataset)
    if violations:
        raise InvariantViolationError("; ".join(violations))


def validate_oracle_partition(partition: OraclePartition) -> list[str]:
    violations: list[str] = []
    for row in partition.rows.values():
        contacts = sorted(row.fatigue_curve.keys())
        for i in range(1, len(contacts)):
            prev = row.fatigue_curve[contacts[i - 1]]
            curr = row.fatigue_curve[contacts[i]]
            if curr > prev:
                violations.append(f"fatigue not monotone {row.opportunity_id}")
    return violations
