"""Tests for audit_formatter."""

from audit_formatter import format_audit_event


def test_format_audit_event_default_correlation_id():
    event = {"actor": "alice", "action": "ACK", "target": "inc-1"}
    assert format_audit_event(event) == "alice|ACK|inc-1|NONE"


def test_format_audit_event_with_correlation_id_in_dict():
    event = {
        "actor": "alice",
        "action": "ACK",
        "target": "inc-1",
        "correlation_id": "corr-42",
    }
    assert format_audit_event(event) == "alice|ACK|inc-1|corr-42"


def test_format_audit_event_with_explicit_kwarg():
    event = {"actor": "alice", "action": "ACK", "target": "inc-1"}
    assert format_audit_event(event, correlation_id="req-99") == "alice|ACK|inc-1|req-99"


def test_format_audit_event_empty_or_whitespace_correlation_id():
    event = {
        "actor": " alice ",
        "action": " ACK ",
        "target": " inc-1 ",
        "correlation_id": "   ",
    }
    assert format_audit_event(event) == "alice|ACK|inc-1|NONE"
