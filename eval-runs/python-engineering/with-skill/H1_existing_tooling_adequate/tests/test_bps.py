"""Tests for bps."""

import pytest

from bps import clamp_bps


def test_clamp_below_ceiling() -> None:
    assert clamp_bps(250) == 250


def test_clamp_at_ceiling() -> None:
    assert clamp_bps(500) == 500


def test_clamp_above_ceiling() -> None:
    assert clamp_bps(600) == 500


def test_clamp_custom_ceiling() -> None:
    assert clamp_bps(150, ceiling=100) == 100
    assert clamp_bps(80, ceiling=100) == 80


def test_clamp_zero_value() -> None:
    assert clamp_bps(0) == 0


def test_clamp_negative_value_raises() -> None:
    with pytest.raises(ValueError, match="value must be non-negative"):
        clamp_bps(-1)


def test_clamp_zero_or_negative_ceiling_raises() -> None:
    with pytest.raises(ValueError, match="ceiling must be positive"):
        clamp_bps(100, ceiling=0)

    with pytest.raises(ValueError, match="ceiling must be positive"):
        clamp_bps(100, ceiling=-50)
