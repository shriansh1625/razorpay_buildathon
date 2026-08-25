"""Complete synthetic world — observable domain entities."""

from __future__ import annotations

from dataclasses import dataclass, field

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


@dataclass
class SyntheticWorld:
    """Generated DOMAIN + SIGNAL layer — no oracle partition."""

    merchants: list[MerchantRecord] = field(default_factory=list)
    customers: list[CustomerRecord] = field(default_factory=list)
    instruments: list[PaymentInstrumentRecord] = field(default_factory=list)
    orders: list[OrderRecord] = field(default_factory=list)
    transactions: list[TransactionRecord] = field(default_factory=list)
    checkout_sessions: list[CheckoutSessionRecord] = field(default_factory=list)
    subscriptions: list[SubscriptionRecord] = field(default_factory=list)
    mandates: list[MandateRecord] = field(default_factory=list)
    invoices: list[InvoiceRecord] = field(default_factory=list)
    opportunities: list[RevenueOpportunityRecord] = field(default_factory=list)
    signals: list[SignalRecord] = field(default_factory=list)
    degradation_windows: list[DegradationWindow] = field(default_factory=list)
    privacy_canaries: list[PrivacyCanary] = field(default_factory=list)
    adversarial_case_ids: list[str] = field(default_factory=list)

    def entity_counts(self) -> dict[str, int]:
        return {
            "merchants": len(self.merchants),
            "customers": len(self.customers),
            "instruments": len(self.instruments),
            "orders": len(self.orders),
            "transactions": len(self.transactions),
            "checkout_sessions": len(self.checkout_sessions),
            "subscriptions": len(self.subscriptions),
            "mandates": len(self.mandates),
            "invoices": len(self.invoices),
            "opportunities": len(self.opportunities),
            "signals": len(self.signals),
        }
