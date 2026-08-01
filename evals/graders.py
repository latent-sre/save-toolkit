"""Deterministic graders for fleet evals.

Anthropic's eval guidance: prefer deterministic/code-based graders; reserve
model-based judging for genuinely subjective quality. These graders score an
agent's *response text* against a scenario's success criteria. They are a
pragmatic proxy — they check that the load-bearing words/decisions are present,
not prose quality. For nuanced judgment, add a model-based grader (see README).

Each grader returns (passed: bool, detail: str).
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable


def _norm(text: str) -> str:
    return text.lower()


def contains_all(response: str, of: list[str]) -> tuple[bool, str]:
    r = _norm(response)
    missing = [t for t in of if t.lower() not in r]
    return (not missing, "missing: " + ", ".join(missing) if missing else "all present")


def contains_any(response: str, of: list[str]) -> tuple[bool, str]:
    r = _norm(response)
    hit = [t for t in of if t.lower() in r]
    return (bool(hit), "found: " + ", ".join(hit) if hit else "none of: " + ", ".join(of))


def not_contains(response: str, of: list[str]) -> tuple[bool, str]:
    r = _norm(response)
    bad = [t for t in of if t.lower() in r]
    return (not bad, "must-not-appear present: " + ", ".join(bad) if bad else "clean")


def regex(response: str, pattern: str) -> tuple[bool, str]:
    ok = re.search(pattern, response, re.IGNORECASE | re.MULTILINE) is not None
    return (ok, f"/{pattern}/ {'matched' if ok else 'no match'}")


def not_regex(response: str, pattern: str) -> tuple[bool, str]:
    """Passes iff the pattern does NOT match — a negative assertion that needs regex power
    (alternation, word boundaries) rather than plain substrings. Use for "must not propose to
    RUN a state-changing command" style checks where `not_contains` can't express the phrasing."""
    m = re.search(pattern, response, re.IGNORECASE | re.MULTILINE)
    detail = f"matched: {m.group(0)!r}" if m else "absent (good)"
    return (m is None, f"/{pattern}/ {detail}")


def json_artifact_statuses(
    response: str,
    artifacts: list[str],
    allowed_statuses: list[str],
    allowed_evidence: list[str],
    evidence_key: str = "evidence",
) -> tuple[bool, str]:
    """Require one exact JSON object with bounded artifact statuses and evidence values."""

    if not artifacts or any(
        not isinstance(artifact, str) or not artifact.strip() for artifact in artifacts
    ):
        raise ValueError("json_artifact_statuses requires non-empty artifact field names")
    if not allowed_statuses or any(
        not isinstance(status, str) or not status.strip() for status in allowed_statuses
    ):
        raise ValueError("json_artifact_statuses requires non-empty allowed statuses")
    if not allowed_evidence or any(
        not isinstance(evidence, str) or not evidence.strip() for evidence in allowed_evidence
    ):
        raise ValueError("json_artifact_statuses requires non-empty allowed evidence values")
    if not isinstance(evidence_key, str) or not evidence_key.strip():
        raise ValueError("json_artifact_statuses requires a non-empty evidence key")

    duplicate_keys: list[str] = []

    def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
        parsed: dict[str, object] = {}
        for key, value in pairs:
            if key in parsed:
                duplicate_keys.append(key)
            parsed[key] = value
        return parsed

    try:
        payload = json.loads(response, object_pairs_hook=reject_duplicate_keys)
    except json.JSONDecodeError as exc:
        return False, f"response is not one JSON object: {exc.msg}"
    if duplicate_keys:
        return False, f"duplicate JSON field(s): {sorted(set(duplicate_keys))}"
    if not isinstance(payload, dict):
        return False, "response JSON must be an object"

    expected_fields = set(artifacts) | {evidence_key}
    actual_fields = set(payload)
    if actual_fields != expected_fields:
        return False, (
            f"JSON fields mismatch: missing={sorted(expected_fields - actual_fields)}, "
            f"extra={sorted(actual_fields - expected_fields)}"
        )
    allowed = set(allowed_statuses)
    invalid_statuses = {
        artifact: payload[artifact]
        for artifact in artifacts
        if not isinstance(payload[artifact], str) or payload[artifact] not in allowed
    }
    if invalid_statuses:
        return False, f"invalid artifact statuses: {invalid_statuses}"
    evidence = payload[evidence_key]
    if not isinstance(evidence, str) or evidence not in set(allowed_evidence):
        return False, f"invalid {evidence_key} value: {evidence!r}"
    return True, "artifact statuses and evidence match the JSON contract"


REGISTRY: dict[str, Callable[..., tuple[bool, str]]] = {
    "contains_all": contains_all,
    "contains_any": contains_any,
    "not_contains": not_contains,
    "regex": regex,
    "not_regex": not_regex,
    "json_artifact_statuses": json_artifact_statuses,
}


def run_grader(spec: dict, response: str) -> tuple[bool, str]:
    """spec = {type: <name>, ...kwargs}. Dispatches to REGISTRY."""
    kind = spec.get("type")
    fn = REGISTRY.get(kind)
    if fn is None:
        raise ValueError(f"unknown grader type: {kind!r} (known: {', '.join(REGISTRY)})")
    kwargs = {k: v for k, v in spec.items() if k != "type"}
    return fn(response, **kwargs)
