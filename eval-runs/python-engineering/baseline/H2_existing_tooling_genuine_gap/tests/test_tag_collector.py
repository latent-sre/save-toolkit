import pytest

from tag_collector import collect_tags


def test_single_call() -> None:
    assert collect_tags(" PROD ") == ["prod"]


def test_default_bucket_independence() -> None:
    first = collect_tags("first")
    second = collect_tags("second")
    assert first == ["first"]
    assert second == ["second"]
    assert first is not second


def test_explicit_bucket() -> None:
    existing = ["dev"]
    result = collect_tags("staging", existing)
    assert result == ["dev", "staging"]
    assert result is existing


def test_tag_type_mismatch() -> None:
    with pytest.raises(TypeError):
        collect_tags(123)  # type: ignore[arg-type]


def test_bucket_type_mismatch() -> None:
    with pytest.raises(TypeError):
        collect_tags("test", "invalid_bucket")  # type: ignore[arg-type]
