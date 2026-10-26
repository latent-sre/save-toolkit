"""Tests for tag collector."""

from tag_collector import collect_tags


def test_single_call() -> None:
    assert collect_tags(" PROD ") == ["prod"]


def test_no_cross_call_state_bleed() -> None:
    first = collect_tags("tag1")
    second = collect_tags("tag2")
    assert first == ["tag1"]
    assert second == ["tag2"]


def test_explicit_bucket() -> None:
    existing = ["alpha"]
    result = collect_tags("beta", existing)
    assert result == ["alpha", "beta"]
    assert result is existing


def test_explicit_none_bucket() -> None:
    result = collect_tags("gamma", None)
    assert result == ["gamma"]
