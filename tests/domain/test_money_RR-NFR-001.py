"""Tests for integer paise money type (RR-NFR-001)."""

import pytest

from revive.domain.money import Paise, paise_from_rupees, rupees_from_paise


def test_paise_zero():
    assert Paise.zero().amount == 0


def test_paise_rejects_float():
    with pytest.raises(TypeError):
        Paise(10.5)  # type: ignore[arg-type]


def test_paise_rejects_negative():
    with pytest.raises(ValueError):
        Paise(-1)


def test_paise_addition():
    assert (Paise(100) + Paise(50)).amount == 150


def test_paise_subtraction_underflow():
    with pytest.raises(ValueError):
        Paise(10) - Paise(20)


def test_paise_from_rupees():
    assert paise_from_rupees(10, 50).amount == 1050


def test_rupees_from_paise():
    assert rupees_from_paise(Paise(1050)) == (10, 50)
