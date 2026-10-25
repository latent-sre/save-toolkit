from audit_formatter import format_audit_event


def test_format_audit_event_default_correlation_id() -> None:
    assert (
        format_audit_event({"actor": "alice", "action": "ACK", "target": "inc-1"})
        == "alice|ACK|inc-1|NONE"
    )


def test_format_audit_event_with_correlation_id() -> None:
    assert (
        format_audit_event(
            {
                "actor": "alice",
                "action": "ACK",
                "target": "inc-1",
                "correlation_id": "corr-42",
            }
        )
        == "alice|ACK|inc-1|corr-42"
    )


def test_format_audit_event_strips_whitespace() -> None:
    assert (
        format_audit_event(
            {
                "actor": "  alice  ",
                "action": "  ACK  ",
                "target": "  inc-1  ",
                "correlation_id": "  corr-42  ",
            }
        )
        == "alice|ACK|inc-1|corr-42"
    )


def test_format_audit_event_empty_correlation_id_defaults_to_none() -> None:
    assert (
        format_audit_event(
            {
                "actor": "alice",
                "action": "ACK",
                "target": "inc-1",
                "correlation_id": "   ",
            }
        )
        == "alice|ACK|inc-1|NONE"
    )


def test_format_audit_event_keyword_argument_override() -> None:
    assert (
        format_audit_event(
            {"actor": "alice", "action": "ACK", "target": "inc-1"},
            correlation_id="corr-99",
        )
        == "alice|ACK|inc-1|corr-99"
    )
