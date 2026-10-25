def format_audit_event(event: dict[str, str], correlation_id: str | None = None) -> str:
    actor = event['actor'].strip()
    action = event['action'].strip()
    target = event['target'].strip()
    cid = correlation_id if correlation_id is not None else event.get('correlation_id', 'NONE')
    if cid is None:
        cid = 'NONE'
    return f'{actor}|{action}|{target}|{cid.strip()}'
