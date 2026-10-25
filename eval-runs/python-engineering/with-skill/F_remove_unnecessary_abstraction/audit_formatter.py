def format_audit_event(event: dict[str, str], correlation_id: str | None = None) -> str:
    """Format an audit event into a pipe-delimited string with an optional correlation ID.

    Fields are trimmed of leading/trailing whitespace. If correlation_id is not provided,
    it defaults to 'NONE'.
    """
    actor = event["actor"].strip()
    action = event["action"].strip()
    target = event["target"].strip()
    cid = (
        correlation_id.strip()
        if correlation_id is not None
        else event.get("correlation_id", "NONE").strip()
    )
    return f"{actor}|{action}|{target}|{cid}"
