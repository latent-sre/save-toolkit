"""Audit event formatting utilities."""


def format_audit_event(event: dict[str, str], correlation_id: str | None = None) -> str:
    """Format an audit event into a pipe-delimited string.

    Format: actor|action|target|correlation_id
    If correlation_id is omitted or blank, it defaults to 'NONE'.
    """
    actor = event["actor"].strip()
    action = event["action"].strip()
    target = event["target"].strip()

    raw_cid = correlation_id if correlation_id is not None else event.get("correlation_id")
    cleaned_cid = raw_cid.strip() if raw_cid is not None else ""
    cid = cleaned_cid if cleaned_cid else "NONE"

    return f"{actor}|{action}|{target}|{cid}"
