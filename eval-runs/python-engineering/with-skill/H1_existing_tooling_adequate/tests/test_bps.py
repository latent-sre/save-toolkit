"""Tests for bps."""

import pytest

from bps import clamp_bps


def test_clamp_bps_within_default_ceiling() -> None:
    assert clamp_bps(250) == 250


def test_clamp_bps_at_default_ceiling() -> None:
    assert clamp_bps(500) == 500


def test_clamp_bps_exceeding_default_ceiling() -> None:
    assert clamp_bps(750) == 500


def test_clamp_bps_zero_value() -> None:
    assert clamp_bps(0) == 0


def test_clamp_bps_custom_ceiling() -> None:
    assert clamp_bps(150, ceiling=100) == 100
    assert clamp_bps(800, ceiling=1000) == 800


def test_clamp_bps_negative_value_raises() -> None:
    with pytest.raises(ValueError, match="value must be non-negative"):
        clamp_bps(-1)


def test_clamp_bps_zero_ceiling_raises() -> None:
    with pytest.raises(ValueError, match="ceiling must be positive"):
        clamp_bps(10, ceiling=0)


def test_clamp_bps_negative_ceiling_raises() -> None:
    with pytest.raises(ValueError, match="ceiling must be positive"):
        clamp_bps(10, ceiling=-50)
