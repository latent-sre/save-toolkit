"""Tests for bps."""

import pytest

from bps import clamp_bps


def test_clamp_bps_within_ceiling() -> None:
    assert clamp_bps(0) == 0
    assert clamp_bps(100) == 100
    assert clamp_bps(499) == 499
    assert clamp_bps(500) == 500


def test_clamp_bps_exceeding_ceiling() -> None:
    assert clamp_bps(501) == 500
    assert clamp_bps(1000) == 500


def test_clamp_bps_custom_ceiling() -> None:
    assert clamp_bps(50, ceiling=200) == 50
    assert clamp_bps(250, ceiling=200) == 200


def test_clamp_bps_negative_value_raises() -> None:
    with pytest.raises(ValueError, match="value must be non-negative"):
        clamp_bps(-1)
    with pytest.raises(ValueError, match="value must be non-negative"):
        clamp_bps(-100)


def test_clamp_bps_non_positive_ceiling_raises() -> None:
    with pytest.raises(ValueError, match="ceiling must be positive"):
        clamp_bps(100, ceiling=0)
    with pytest.raises(ValueError, match="ceiling must be positive"):
        clamp_bps(100, ceiling=-50)
