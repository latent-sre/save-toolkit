from tag_collector import collect_tags


def test_single_call() -> None:
    assert collect_tags(" PROD ") == ["prod"]


def test_no_cross_call_state_bleed() -> None:
    first = collect_tags("alpha")
    second = collect_tags("beta")
    assert first == ["alpha"]
    assert second == ["beta"]


def test_explicit_bucket_appended() -> None:
    seed: list[str] = ["initial"]
    result = collect_tags("next", seed)
    assert result == ["initial", "next"]
    assert result is seed


def test_explicit_none_bucket() -> None:
    assert collect_tags("staging", None) == ["staging"]


def test_tag_stripping_and_lowercasing() -> None:
    assert collect_tags("  MiXeD_CaSe  ") == ["mixed_case"]


def test_empty_tag() -> None:
    assert collect_tags("   ") == [""]
