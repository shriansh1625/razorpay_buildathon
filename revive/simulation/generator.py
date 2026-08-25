"""Synthetic environment generator — docs/19 §2."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from revive.clock import VirtualClock
from revive.domain.enums import ActionCode, OpportunityState, RiskClass
from revive.domain.timestamps import VirtualTimestamp
from revive.rng import PRNGStreamRegistry
from revive.simulation.config import GENERATOR_VERSION, GeneratorConfig
from revive.simulation.ids import deterministic_id
from revive.simulation.latent import LatentTraits
from revive.simulation.models import (
    CheckoutSessionRecord,
    CustomerRecord,
    DegradationWindow,
    InvoiceRecord,
    MandateRecord,
    MerchantRecord,
    OrderRecord,
    PaymentInstrumentRecord,
    PrivacyCanary,
    RevenueOpportunityRecord,
    SignalRecord,
    SubscriptionRecord,
    TransactionRecord,
)
from revive.simulation.oracle._partition import ActionResponse, OraclePartition, OracleRow
from revive.simulation.profiles import profile_parameters
from revive.simulation.types import CheckoutStage, GenerationProfile, PaymentFailureReason
from revive.simulation.world import SyntheticWorld

DAY_MICROS = 24 * 60 * 60 * 1_000_000
MINUTE_MICROS = 60 * 1_000_000

SEGMENTS = ("NEW", "RETURNING", "VIP", "DORMANT")
TENURE_BANDS = ("LT_3M", "3M_12M", "GT_12M")
VALUE_BANDS = ("LOW", "MID", "HIGH")


@dataclass(frozen=True, slots=True)
class GeneratedDataset:
    world: SyntheticWorld
    oracle_partition: OraclePartition
    config: GeneratorConfig
    dataset_hash: str


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _draw_latent(customer_id: str, rng) -> LatentTraits:
    return LatentTraits(
        customer_id=customer_id,
        intent_to_pay=_clamp01(0.15 + rng.random() * 0.75),
        responsiveness_email=_clamp01(0.1 + rng.random() * 0.8),
        responsiveness_sms=_clamp01(0.1 + rng.random() * 0.7),
        price_sensitivity=_clamp01(0.1 + rng.random() * 0.85),
        annoyance_threshold=rng.randint(2, 5),
        instrument_health=_clamp01(0.05 + rng.random() * 0.9),
        attention_delay_minutes=rng.randint(15, 180),
        fatigue_sensitivity=_clamp01(0.3 + rng.random() * 0.6),
    )


def _noisy_proxy(latent: LatentTraits, rng) -> float:
    noise = (rng.random() - 0.5) * 0.25
    return _clamp01(latent.intent_to_pay + noise)


def _fatigue_curve(latent: LatentTraits) -> dict[int, float]:
    base = 1.0
    curve: dict[int, float] = {}
    for contact in range(5):
        decay = latent.fatigue_sensitivity * contact * 0.18
        curve[contact] = max(0.05, base - decay)
    return curve


def _in_window(micros: int, windows: list[DegradationWindow]) -> tuple[bool, str | None]:
    for window in windows:
        if window.start_micros <= micros < window.end_micros:
            return True, window.cohort_ref
    return False, None


def _build_oracle_row(
    opp: RevenueOpportunityRecord,
    latent: LatentTraits,
    profile: GenerationProfile,
    oracle_rng,
    degradation_windows: list[DegradationWindow],
    horizon_minutes: int,
) -> OracleRow:
    params = profile_parameters(profile)
    base_micros = opp.first_detected_at_micros
    horizon_micros = horizon_minutes * MINUTE_MICROS

    value_factor = opp.value_at_risk_paise / 100_000
    corr = params.value_recoverability_correlation
    instrument = _clamp01(latent.instrument_health + corr * value_factor * 0.15)

    natural_prob = latent.intent_to_pay * params.natural_recovery_multiplier
    if opp.value_at_risk_paise >= 50_000 and params.high_value_natural_concentration > 0.5:
        natural_prob *= 1.0 + params.high_value_natural_concentration * 0.5

    natural_prob = _clamp01(natural_prob)
    recovers_naturally = oracle_rng.random() < natural_prob
    natural_at: int | None = None
    natural_amount = 0
    if recovers_naturally:
        delay = oracle_rng.randint(30, max(60, latent.attention_delay_minutes))
        natural_at = base_micros + delay * MINUTE_MICROS
        if oracle_rng.random() < 0.2:
            natural_at = base_micros + horizon_micros + oracle_rng.randint(60, 360) * MINUTE_MICROS
        natural_amount = opp.value_at_risk_paise

    in_deg, cohort = _in_window(base_micros, degradation_windows)
    fatigue_curve = _fatigue_curve(latent)

    per_action: dict[str, ActionResponse] = {}

    def add_response(code: ActionCode, prob: float, delay_minutes: int, amount: int) -> None:
        prob = _clamp01(prob)
        would = oracle_rng.random() < prob
        recover_at = base_micros + delay_minutes * MINUTE_MICROS
        if oracle_rng.random() < 0.15:
            recover_at = base_micros + horizon_micros + oracle_rng.randint(30, 240) * MINUTE_MICROS
        override = None
        if code == ActionCode.A07 and oracle_rng.random() < 0.05:
            override = "TIMEOUT_UNKNOWN"
        per_action[code.value] = ActionResponse(
            would_recover=would,
            recover_at_micros=recover_at,
            amount_paise=amount,
            adapter_result_override=override,
        )

    add_response(ActionCode.A00, 0.0, 0, 0)

    immediate_retry_prob = instrument * (0.35 if in_deg else 0.75)
    scheduled_prob = instrument * (0.55 if in_deg else 0.45) + latent.attention_delay_minutes / 600
    alt_instrument_prob = (1.0 - instrument) * 0.7
    reminder_prob = max(latent.responsiveness_email, latent.responsiveness_sms) * latent.intent_to_pay
    incentive_prob = latent.price_sensitivity * latent.intent_to_pay * 0.9
    checkout_prob = latent.intent_to_pay * 0.8 if opp.risk_class == RiskClass.CHECKOUT_ABANDONMENT else 0.2
    mandate_prob = instrument * 0.65 if opp.risk_class in (
        RiskClass.SUBSCRIPTION_FAILURE,
        RiskClass.MANDATE_HEALTH,
    ) else 0.15

    if instrument < 0.15:
        immediate_retry_prob = min(immediate_retry_prob, 0.05)
    if latent.annoyance_threshold <= 2:
        reminder_prob *= 0.5

    add_response(ActionCode.A01, immediate_retry_prob, 5, opp.value_at_risk_paise)
    add_response(
        ActionCode.A02,
        scheduled_prob,
        latent.attention_delay_minutes,
        opp.value_at_risk_paise,
    )
    add_response(ActionCode.A03, alt_instrument_prob, 20, opp.value_at_risk_paise)
    add_response(ActionCode.A04, reminder_prob * 0.85, 45, opp.value_at_risk_paise)
    add_response(ActionCode.A05, reminder_prob, 30, opp.value_at_risk_paise)
    add_response(ActionCode.A06, incentive_prob, 40, opp.value_at_risk_paise)
    add_response(ActionCode.A07, reminder_prob * 0.6, 60, opp.value_at_risk_paise)
    add_response(ActionCode.A08, mandate_prob, 35, opp.value_at_risk_paise)
    add_response(ActionCode.A09, checkout_prob, 25, opp.value_at_risk_paise)
    add_response(ActionCode.A10, latent.intent_to_pay * 0.3, 10, opp.value_at_risk_paise // 2)
    add_response(ActionCode.A11, 0.4, 15, 0)
    add_response(ActionCode.A12, 0.25, 120, opp.value_at_risk_paise)
    add_response(ActionCode.A13, mandate_prob * 0.5, 50, opp.value_at_risk_paise)
    add_response(ActionCode.A14, 0.35, 90, 0)

    if latent.intent_to_pay > 0.7 and reminder_prob > 0.5:
        bad = per_action[ActionCode.A05.value]
        per_action[ActionCode.A05.value] = ActionResponse(
            would_recover=oracle_rng.random() < reminder_prob * 0.3,
            recover_at_micros=bad.recover_at_micros,
            amount_paise=bad.amount_paise,
        )

    return OracleRow(
        opportunity_id=opp.opportunity_id,
        customer_id=opp.customer_id,
        recovers_naturally=recovers_naturally,
        natural_recovery_at_micros=natural_at,
        natural_amount_paise=natural_amount,
        per_action_response=per_action,
        fatigue_curve=fatigue_curve,
        degradation_cohort_ref=cohort,
    )


def _dataset_hash(world: SyntheticWorld, partition: OraclePartition, config: GeneratorConfig) -> str:
    payload = {
        "generator_version": GENERATOR_VERSION,
        "config_hash": config.config_hash(),
        "world_counts": world.entity_counts(),
        "oracle_rows": len(partition.rows),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def generate_dataset(config: GeneratorConfig) -> GeneratedDataset:
    """Generate a full synthetic world + isolated oracle partition."""
    registry = PRNGStreamRegistry(config.seed)
    profile_params = profile_parameters(config.profile)

    customer_rng = registry.stream("customer_generation")
    txn_rng = registry.stream("transaction_generation")
    checkout_rng = registry.stream("checkout_generation")
    failure_rng = registry.stream("failure_generation")
    env_rng = registry.stream("environment_conditions")
    oracle_rng = registry.stream("oracle")

    clock = VirtualClock(VirtualTimestamp(0))
    world = SyntheticWorld()
    partition = OraclePartition()

    window_micros = config.simulation_window_days * DAY_MICROS

    for m_idx in range(config.merchant_count):
        merchant_id = deterministic_id("mer", f"merchant:{config.seed}:{m_idx}")
        world.merchants.append(
            MerchantRecord(
                merchant_id=merchant_id,
                name_token=f"merchant_{m_idx}",
                timezone="Asia/Kolkata",
                net_retention_factor=1.0,
                policy_pack_ref="pol_m1_draft",
            )
        )

    merchant_id = world.merchants[0].merchant_id
    latent_by_customer: dict[str, LatentTraits] = {}

    for c_idx in range(config.customer_count):
        customer_id = deterministic_id("cust", f"customer:{config.seed}:{c_idx}")
        latent = _draw_latent(customer_id, customer_rng)
        latent_by_customer[customer_id] = latent
        partition.latent_traits[customer_id] = latent.to_dict()

        segment = customer_rng.choice(SEGMENTS)
        tenure = customer_rng.choice(TENURE_BANDS)
        value_band = customer_rng.choice(VALUE_BANDS)
        if customer_rng.random() < 0.25 + profile_params.value_recoverability_correlation * -0.2:
            value_band = "HIGH"

        world.customers.append(
            CustomerRecord(
                customer_id=customer_id,
                customer_ref=f"cref_{c_idx:04d}",
                merchant_id=merchant_id,
                segment=segment,
                tenure_band=tenure,
                value_band=value_band,
                prior_self_recovery_rate=_noisy_proxy(latent, customer_rng),
            )
        )

        instrument_id = deterministic_id("pi", f"instrument:{customer_id}")
        health = latent.instrument_health
        expiry = "VALID" if health > 0.3 else "EXPIRED"
        block = "BLOCKED" if health < 0.1 else "ACTIVE"
        world.instruments.append(
            PaymentInstrumentRecord(
                instrument_id=instrument_id,
                customer_id=customer_id,
                method_type=customer_rng.choice(["CARD", "UPI", "NETBANKING"]),
                network_band=customer_rng.choice(["VISA", "MC", "RUPAY"]),
                expiry_state=expiry,
                block_state=block,
                failure_count=customer_rng.randint(0, 4),
            )
        )

    deg_count = max(1, int(config.degradation_frequency * profile_params.degradation_intensity * 3))
    for d_idx in range(deg_count):
        start_day = env_rng.randint(1, max(2, config.simulation_window_days - 2))
        duration_min = env_rng.randint(30, 90)
        start = start_day * DAY_MICROS + env_rng.randint(0, 12) * 60 * MINUTE_MICROS
        end = start + duration_min * MINUTE_MICROS
        world.degradation_windows.append(
            DegradationWindow(
                cohort_ref=f"deg_{d_idx}",
                start_micros=start,
                end_micros=min(end, window_micros),
                severity=0.4 + env_rng.random() * 0.5,
            )
        )

    risk_targets = _risk_class_targets(config)
    opportunities_created = 0
    opp_index = 0

    while opportunities_created < config.opportunity_count:
        customer = customer_rng.choice(world.customers)
        latent = latent_by_customer[customer.customer_id]
        risk_class = _pick_risk_class(failure_rng, risk_targets)
        detected_micros = failure_rng.randint(DAY_MICROS, max(DAY_MICROS, window_micros - DAY_MICROS))
        in_deg, cohort_ref = _in_window(detected_micros, world.degradation_windows)

        opp_id = deterministic_id("opp", f"opp:{config.seed}:{opp_index}")
        opp_index += 1
        amount = failure_rng.randint(2_000, 250_000)
        if customer.value_band == "HIGH":
            amount = failure_rng.randint(50_000, 500_000)
        elif customer.value_band == "LOW":
            amount = failure_rng.randint(1_000, 15_000)

        linked: dict[str, str] = {}
        failure_reason: PaymentFailureReason | None = None
        checkout_stage: CheckoutStage | None = None
        invoice_age: int | None = None
        addressable = True

        if risk_class == RiskClass.PAYMENT_FAILURE:
            order_id = deterministic_id("ord", f"ord:{opp_id}")
            instrument = world.instruments[0]
            for inst in world.instruments:
                if inst.customer_id == customer.customer_id:
                    instrument = inst
                    break
            world.orders.append(
                OrderRecord(
                    order_id=order_id,
                    customer_id=customer.customer_id,
                    merchant_id=merchant_id,
                    amount_paise=amount,
                    created_at_micros=detected_micros - failure_rng.randint(1, 60) * MINUTE_MICROS,
                    status="OPEN",
                )
            )
            failure_reason = failure_rng.choice(list(PaymentFailureReason))
            txn_id = deterministic_id("txn", f"txn:{opp_id}")
            world.transactions.append(
                TransactionRecord(
                    transaction_id=txn_id,
                    order_id=order_id,
                    customer_id=customer.customer_id,
                    amount_paise=amount,
                    method_type=instrument.method_type,
                    instrument_id=instrument.instrument_id,
                    attempt_seq=1,
                    status="FAILED",
                    reason_code=failure_reason.value,
                    reason_text=f"simulated {failure_reason.value}",
                    attempted_at_micros=detected_micros,
                )
            )
            linked = {"order_id": order_id, "transaction_id": txn_id}

        elif risk_class == RiskClass.CHECKOUT_ABANDONMENT:
            checkout_stage = failure_rng.choice(
                [CheckoutStage.CART, CheckoutStage.CHECKOUT, CheckoutStage.PAYMENT_INIT]
            )
            session_id = deterministic_id("chk", f"chk:{opp_id}")
            anonymous = checkout_rng.random() < 0.1
            if anonymous:
                addressable = False
            world.checkout_sessions.append(
                CheckoutSessionRecord(
                    session_id=session_id,
                    customer_id=customer.customer_id if not anonymous else None,
                    merchant_id=merchant_id,
                    cart_value_paise=amount,
                    stage_reached=checkout_stage,
                    method_selected=checkout_rng.choice(["CARD", "UPI", None]),
                    abandoned_at_micros=detected_micros,
                    created_at_micros=detected_micros - checkout_rng.randint(5, 45) * MINUTE_MICROS,
                )
            )
            linked = {"checkout_session_id": session_id}

        elif risk_class == RiskClass.SUBSCRIPTION_FAILURE:
            mandate_id = deterministic_id("man", f"man:{opp_id}")
            instrument = next(i for i in world.instruments if i.customer_id == customer.customer_id)
            world.mandates.append(
                MandateRecord(
                    mandate_id=mandate_id,
                    customer_id=customer.customer_id,
                    instrument_id=instrument.instrument_id,
                    state="ACTIVE",
                    expires_at_micros=detected_micros + 180 * DAY_MICROS,
                    max_amount_paise=amount * 2,
                    presented_count=failure_rng.randint(1, 5),
                )
            )
            sub_id = deterministic_id("sub", f"sub:{opp_id}")
            world.subscriptions.append(
                SubscriptionRecord(
                    subscription_id=sub_id,
                    customer_id=customer.customer_id,
                    mandate_id=mandate_id,
                    cycle_amount_paise=amount,
                    cycle_number=failure_rng.randint(1, 24),
                    next_charge_at_micros=detected_micros,
                    state="PAST_DUE",
                )
            )
            linked = {"subscription_id": sub_id, "mandate_id": mandate_id}

        elif risk_class == RiskClass.RECEIVABLE_OVERDUE:
            invoice_age = failure_rng.randint(16, 120)
            due_at = detected_micros - invoice_age * DAY_MICROS
            inv_id = deterministic_id("inv", f"inv:{opp_id}")
            world.invoices.append(
                InvoiceRecord(
                    invoice_id=inv_id,
                    customer_id=customer.customer_id,
                    merchant_id=merchant_id,
                    issued_amount_paise=amount,
                    paid_amount_paise=0,
                    credited_amount_paise=0,
                    written_off_amount_paise=0,
                    disputed_amount_paise=0,
                    due_at_micros=due_at,
                    terms_days=30,
                    state="OVERDUE",
                    ageing_days=invoice_age,
                )
            )
            linked = {"invoice_id": inv_id}

        else:
            mandate_id = deterministic_id("man", f"manh:{opp_id}")
            instrument = next(i for i in world.instruments if i.customer_id == customer.customer_id)
            world.mandates.append(
                MandateRecord(
                    mandate_id=mandate_id,
                    customer_id=customer.customer_id,
                    instrument_id=instrument.instrument_id,
                    state="EXPIRING",
                    expires_at_micros=detected_micros + failure_rng.randint(7, 45) * DAY_MICROS,
                    max_amount_paise=amount,
                    presented_count=failure_rng.randint(2, 8),
                )
            )
            linked = {"mandate_id": mandate_id}

        natural_key = f"{risk_class.value}:{customer.customer_id}:{opp_index}"
        window_expires = detected_micros + failure_rng.randint(7, 90) * DAY_MICROS

        opp = RevenueOpportunityRecord(
            opportunity_id=opp_id,
            merchant_id=merchant_id,
            customer_id=customer.customer_id,
            risk_class=risk_class,
            natural_key=natural_key,
            value_at_risk_paise=amount,
            original_value_paise=amount,
            continuation_value_paise=0,
            addressable=addressable,
            state=OpportunityState.DETECTED,
            first_detected_at_micros=detected_micros,
            recovery_window_expires_at_micros=window_expires,
            attempt_seq=0,
            contacts_made=0,
            linked_refs=linked,
            failure_reason=failure_reason,
            checkout_stage=checkout_stage,
            invoice_age_days=invoice_age,
            in_degradation_window=in_deg,
        )
        world.opportunities.append(opp)

        oracle_row = _build_oracle_row(
            opp,
            latent,
            config.profile,
            oracle_rng,
            world.degradation_windows,
            config.default_outcome_horizon_minutes,
        )
        partition.add_row(oracle_row)

        sig_id = deterministic_id("sig", f"sig:{opp_id}")
        dedupe = hashlib.sha256(f"{config.seed}:{sig_id}".encode()).hexdigest()
        world.signals.append(
            SignalRecord(
                signal_id=sig_id,
                signal_type=f"{risk_class.value}_SIGNAL",
                source_ref=opp_id,
                payload={"opportunity_id": opp_id, "amount_paise": amount},
                received_at_micros=detected_micros,
                occurred_at_micros=detected_micros - failure_rng.randint(0, 5) * MINUTE_MICROS,
                dedupe_hash=dedupe,
            )
        )

        opportunities_created += 1

    if profile_params.adversarial_injection or config.inject_adversarial_cases:
        _inject_adversarial_cases(world, partition, latent_by_customer, failure_rng)

    if config.inject_signal_faults:
        _inject_signal_faults(world, failure_rng, config.seed)

    for c_idx in range(config.privacy_canary_count):
        canary_id = deterministic_id("can", f"canary:{config.seed}:{c_idx}")
        sentinel = f"SENTINEL_EMAIL_{c_idx}@privacy.test"
        world.privacy_canaries.append(
            PrivacyCanary(
                canary_id=canary_id,
                field_name="contact_ref",
                sentinel_value=sentinel,
                planted_in_entity="customer",
                entity_id=world.customers[c_idx % len(world.customers)].customer_id,
            )
        )

    dataset_hash = _dataset_hash(world, partition, config)
    return GeneratedDataset(
        world=world,
        oracle_partition=partition,
        config=config,
        dataset_hash=dataset_hash,
    )


def _risk_class_targets(config: GeneratorConfig) -> dict[RiskClass, float]:
    return {
        RiskClass.PAYMENT_FAILURE: config.failure_mix_payment,
        RiskClass.CHECKOUT_ABANDONMENT: config.failure_mix_checkout,
        RiskClass.SUBSCRIPTION_FAILURE: config.failure_mix_subscription,
        RiskClass.RECEIVABLE_OVERDUE: config.failure_mix_receivable,
        RiskClass.MANDATE_HEALTH: config.failure_mix_mandate,
    }


def _pick_risk_class(rng, targets: dict[RiskClass, float]) -> RiskClass:
    items = list(targets.items())
    total = sum(w for _, w in items)
    pick = rng.random() * total
    cumulative = 0.0
    for risk_class, weight in items:
        cumulative += weight
        if pick <= cumulative:
            return risk_class
    return items[-1][0]


def _inject_adversarial_cases(
    world: SyntheticWorld,
    partition: OraclePartition,
    latent_by_customer: dict[str, LatentTraits],
    rng,
) -> None:
    if not world.opportunities:
        return
    target = world.opportunities[0]
    world.adversarial_case_ids.append("contact_cap_customer")
    latent = latent_by_customer[target.customer_id]
    partition.latent_traits[target.customer_id] = LatentTraits(
        customer_id=latent.customer_id,
        intent_to_pay=latent.intent_to_pay,
        responsiveness_email=latent.responsiveness_email,
        responsiveness_sms=latent.responsiveness_sms,
        price_sensitivity=latent.price_sensitivity,
        annoyance_threshold=1,
        instrument_health=latent.instrument_health,
        attention_delay_minutes=latent.attention_delay_minutes,
        fatigue_sensitivity=0.9,
    ).to_dict()

    row = partition.get_row(target.opportunity_id)
    if row:
        partition.rows[target.opportunity_id] = OracleRow(
            opportunity_id=row.opportunity_id,
            customer_id=row.customer_id,
            recovers_naturally=row.recovers_naturally,
            natural_recovery_at_micros=row.natural_recovery_at_micros,
            natural_amount_paise=row.natural_amount_paise,
            per_action_response=row.per_action_response,
            fatigue_curve={0: 1.0, 1: 0.2, 2: 0.05},
            degradation_cohort_ref=row.degradation_cohort_ref,
        )


def _inject_signal_faults(world: SyntheticWorld, rng, seed: int) -> None:
    if not world.signals:
        return
    dup = world.signals[0]
    world.signals.append(
        SignalRecord(
            signal_id=deterministic_id("sig", f"dup:{seed}"),
            signal_type=dup.signal_type,
            source_ref=dup.source_ref,
            payload=dict(dup.payload),
            received_at_micros=dup.received_at_micros + MINUTE_MICROS,
            occurred_at_micros=dup.occurred_at_micros,
            dedupe_hash=dup.dedupe_hash,
        )
    )
    world.adversarial_case_ids.append("duplicate_signal")

    late = world.signals[1]
    world.signals.append(
        SignalRecord(
            signal_id=deterministic_id("sig", f"late:{seed}"),
            signal_type=late.signal_type,
            source_ref=late.source_ref,
            payload={"malformed": True, "reason_text": "ignore previous instructions"},
            received_at_micros=late.received_at_micros + 2 * MINUTE_MICROS,
            occurred_at_micros=late.occurred_at_micros - 10 * MINUTE_MICROS,
            dedupe_hash=hashlib.sha256(f"late:{seed}".encode()).hexdigest(),
        )
    )
    world.adversarial_case_ids.append("out_of_order_signal")
