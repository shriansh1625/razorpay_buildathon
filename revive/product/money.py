"""INR display helpers — integer paise remain the source of truth."""

from __future__ import annotations


def paise_to_inr(paise: int) -> float:
    return paise / 100.0


def group_indian(rupees: int) -> str:
    """2,2,3 grouping. ``1234567`` reads ``12,34,567``, never ``1,234,567``.

    Python's ``:,`` is 3,3,3 — correct in New York, wrong in Mumbai, and the
    product quotes rupees. A lakh figure grouped the Western way is the single
    fastest way to tell an Indian finance operator that nobody who works with
    this money reviewed the interface.
    """
    s = str(abs(int(rupees)))
    if len(s) <= 3:
        return s
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts) + "," + tail


def format_inr(paise: int) -> str:
    """Exact rupees and paise. The evidence form — nothing is rounded away."""
    sign = "-" if paise < 0 else ""
    rupees, remainder = divmod(abs(int(paise)), 100)
    return f"{sign}₹{group_indian(rupees)}.{remainder:02d}"


def format_display_inr(paise: int) -> str:
    """Reading form. Paise are dropped once they cannot change a decision.

    ``₹47,42,932.86`` spends its two most prominent trailing glyphs on 86 paise
    of a ₹47 lakh figure. Below ₹1,000 the paise still carry meaning — a ₹4.50
    messaging cost is 4.50, not 5 — so the cutoff is magnitude, not preference.
    The exact figure never disappears: ``format_inr`` remains the evidence form
    on receipts, in provenance and wherever an auditor reconciles a number.
    """
    rupees, remainder = divmod(abs(int(paise)), 100)
    if rupees < 1_000:
        return format_inr(paise)
    sign = "-" if paise < 0 else ""
    if remainder >= 50:
        rupees += 1
    return f"{sign}₹{group_indian(rupees)}"


def format_compact_inr(paise: int) -> str:
    """Headline scale: lakhs / crores when the amount justifies it."""
    sign = "-" if paise < 0 else ""
    rupees = abs(paise) / 100.0
    if rupees >= 10_000_000:
        return f"{sign}₹{rupees / 10_000_000:.2f}Cr"
    if rupees >= 100_000:
        return f"{sign}₹{rupees / 100_000:.2f}L"
    return format_inr(paise)
