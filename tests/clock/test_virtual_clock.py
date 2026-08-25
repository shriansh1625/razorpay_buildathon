"""Virtual clock tests."""

import pytest

from revive.clock import VirtualClock
from revive.domain.timestamps import VirtualTimestamp


def test_clock_advances_monotonically():
    clock = VirtualClock()
    t0 = clock.now
    t1 = clock.advance_minutes(5)
    assert t1 > t0
    assert clock.now == t1


def test_clock_cannot_move_backwards():
    clock = VirtualClock(VirtualTimestamp(1_000_000))
    with pytest.raises(ValueError):
        clock.set(VirtualTimestamp(500_000))


def test_timestamp_add_minutes():
    ts = VirtualTimestamp(0).add_minutes(10)
    assert ts.epoch_micros == 10 * 60 * 1_000_000
