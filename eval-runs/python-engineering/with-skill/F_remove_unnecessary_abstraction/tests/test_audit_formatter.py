from audit_formatter import format_audit_event


def test_format_audit_event_default_correlation_id():
    assert (
        format_audit_event({"actor": "alice", "action": "ACK", "target": "inc-1"})
        == "alice|ACK|inc-1|NONE"
    )


def test_format_audit_event_with_correlation_id_in_event():
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


def test_format_audit_event_with_explicit_kwarg():
    assert (
        format_audit_event(
            {"actor": "bob", "action": "RESOLVE", "target": "inc-2"},
            correlation_id="corr-99",
        )
        == "bob|RESOLVE|inc-2|corr-99"
    )


def test_format_audit_event_strips_whitespace():
    assert (
        format_audit_event(
            {
                "actor": "  alice  ",
                "action": " ACK ",
                "target": " inc-1 ",
                "correlation_id": " corr-100 ",
            }
        )
        == "alice|ACK|inc-1|corr-100"
    )
