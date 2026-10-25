import pytest

from tag_collector import collect_tags


def test_single_call() -> None:
    assert collect_tags(" PROD ") == ["prod"]


def test_mutable_default_is_not_reused() -> None:
    first = collect_tags("first")
    second = collect_tags("second")
    assert first == ["first"]
    assert second == ["second"]
    assert first is not second


def test_custom_bucket_appended() -> None:
    initial = ["alpha"]
    result = collect_tags("beta", initial)
    assert result == ["alpha", "beta"]
    assert result is initial


def test_tag_type_mismatch() -> None:
    invalid_tag: object = 123
    with pytest.raises(TypeError, match="new_tag must be a str"):
        collect_tags(invalid_tag)  # type: ignore[arg-type]


def test_bucket_type_mismatch() -> None:
    invalid_bucket: object = "not-a-list"
    with pytest.raises(TypeError, match="bucket must be a list"):
        collect_tags("tag", invalid_bucket)  # type: ignore[arg-type]


def test_whitespace_and_casing() -> None:
    assert collect_tags("  MixedCaseTag  ") == ["mixedcasetag"]
