from audit_formatter import format_audit_event


def test_format_audit_event_default():
    assert format_audit_event({'actor': 'alice', 'action': 'ACK', 'target': 'inc-1'}) == 'alice|ACK|inc-1|NONE'


def test_format_audit_event_with_event_correlation_id():
    assert (
        format_audit_event({'actor': 'alice', 'action': 'ACK', 'target': 'inc-1', 'correlation_id': 'cid-123'})
        == 'alice|ACK|inc-1|cid-123'
    )


def test_format_audit_event_with_explicit_argument():
    assert (
        format_audit_event({'actor': 'bob ', 'action': 'RESOLVE', 'target': 'inc-2 '}, correlation_id='cid-456')
        == 'bob|RESOLVE|inc-2|cid-456'
    )
