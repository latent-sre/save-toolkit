"""Audit event formatter."""

from collections.abc import Mapping


def format_audit_event(
    event: Mapping[str, str],
    correlation_id: str | None = None,
) -> str:
    """Format an audit event mapping into a pipe-delimited string.

    Format: <actor>|<action>|<target>|<correlation_id>
    """
    actor = event["actor"].strip()
    action = event["action"].strip()
    target = event["target"].strip()

    if correlation_id is not None:
        raw_corr = correlation_id
    else:
        raw_corr = event.get("correlation_id", "NONE")

    corr = raw_corr.strip() if raw_corr else "NONE"
    if not corr:
        corr = "NONE"

    return f"{actor}|{action}|{target}|{corr}"
