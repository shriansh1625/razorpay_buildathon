"""Idempotency and multi-action attribution tests."""

from revive.measurement import (
    MeasurementStore,
    OpportunityRecoveryLedger,
    aggregate_batch,
    measure_execution,
    measurement_id_for,
)
from revive.measurement.models import AttributionMethod

from tests.measurement.helpers import execute_and_measure, synthetic_execution_result


def test_repeated_measurement_idempotent():
    result, m1, decision, val = execute_and_measure()
    store = MeasurementStore()
    m1 = measure_execution(
        result, val, decision, value_at_risk_paise=5000, store=store,
    )
    m2 = measure_execution(
        result, val, decision, value_at_risk_paise=5000, store=store,
    )
    assert m1.measurement_id == m2.measurement_id
    assert m2.duplicate_measurement is True
    assert len(store.all_measurements()) == 1


def test_measurement_identity_deterministic():
    result, _, decision, val = execute_and_measure()
    mid = measurement_id_for(result.execution_id)
    m = measure_execution(result, val, decision, value_at_risk_paise=5000)
    assert m.measurement_id == mid


def test_multi_action_no_double_count():
    ledger = OpportunityRecoveryLedger()
    store = MeasurementStore()

    exec_a, decision, val = synthetic_execution_result(
        execution_id="exec_a", recovered=5000, attribution="ATTRIBUTED",
    )
    m_a = measure_execution(
        exec_a, val, decision,
        value_at_risk_paise=5000,
        recovery_ledger=ledger,
        store=store,
    )
    assert m_a.gross_recovered_paise == 5000

    exec_b, _, _ = synthetic_execution_result(
        execution_id="exec_b", recovered=5000, attribution="ATTRIBUTED",
    )
    m_b = measure_execution(
        exec_b, val, decision,
        value_at_risk_paise=5000,
        recovery_ledger=ledger,
        store=store,
    )
    assert m_b.gross_recovered_paise == 0
    assert m_b.attribution_method == AttributionMethod.MULTI_ACTION_DEDUP

    batch = aggregate_batch(store.all_measurements())
    assert batch.total_gross_recovered_paise == 5000
    assert batch.execution_count == 2


def test_batch_aggregation_primitives():
    results = []
    store = MeasurementStore()
    for i in range(3):
        exec_r, decision, val = synthetic_execution_result(
            execution_id=f"exec_{i}",
            opportunity_id=f"opp_{i}",
            recovered=1000 * (i + 1),
        )
        results.append(
            measure_execution(
                exec_r, val, decision,
                value_at_risk_paise=5000,
                store=store,
            )
        )
    batch = aggregate_batch(tuple(results), total_at_risk_paise=15_000)
    assert batch.total_gross_recovered_paise == 6000
    assert batch.opportunities_count == 3
    assert batch.execution_count == 3
