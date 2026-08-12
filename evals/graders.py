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


def distinct_command_flag_targets(
    response: str,
    command: str,
    flag: str,
    count: int,
) -> tuple[bool, str]:
    """Require distinct assignment targets on separate literal commands, without regex."""

    if not isinstance(command, str) or not command:
        raise ValueError("distinct_command_flag_targets requires a non-empty command")
    if not isinstance(flag, str) or not flag:
        raise ValueError("distinct_command_flag_targets requires a non-empty flag")
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise ValueError("distinct_command_flag_targets count must be an integer >= 1")

    haystack = _norm(response)
    command_needle = _norm(command)
    flag_needle = _norm(flag)
    targets: list[str] = []
    cursor = 0
    while True:
        command_start = haystack.find(command_needle, cursor)
        if command_start < 0:
            break
        next_command = haystack.find(
            command_needle,
            command_start + len(command_needle),
        )
        command_end = next_command if next_command >= 0 else len(haystack)
        flag_start = haystack.find(
            flag_needle,
            command_start + len(command_needle),
            command_end,
        )
        if flag_start >= 0:
            value_start = flag_start + len(flag_needle)
            while value_start < command_end and haystack[value_start].isspace():
                value_start += 1
            value_end = value_start
            while (
                value_end < command_end
                and not haystack[value_end].isspace()
                and haystack[value_end] not in "`'\";,()[]{}"
            ):
                value_end += 1
            value = haystack[value_start:value_end].strip(".:").lstrip("=")
            target = value.split("=", 1)[0].replace("<", "").replace(">", "")
            if target:
                targets.append(target)
        if next_command < 0:
            break
        cursor = next_command

    distinct_count = len(set(targets))
    return (
        distinct_count >= count,
        f"found {distinct_count} distinct command flag target(s), need at least {count}",
    )


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


def _literal_field_occurrences(label: str, lines: list[str]) -> list[str]:
    """Return values from exact ``Label: value`` lines, tolerating display-only Markdown.

    Prefix matching is intentionally insufficient: ``Verdict summary: ...`` must not satisfy a
    ``Verdict`` field merely because both begin with the same word. The label must be followed by
    optional whitespace and then the colon. Leading list markers, blockquote markers, headings, and
    a single layer of `*`/`_`/`**`/`__`/`` ` `` decoration around the label are accepted because
    they are display formatting, not part of the value.
    """
    literal_label = re.escape(label)
    decoration = r"\*\*|__|\*|_|`"
    pattern = re.compile(
        r"^\s*(?:>\s*)*(?:(?:[-*+]|\d+[.)])\s+)?(?:#{1,6}\s+)?(?:"
        rf"(?P<outside>{decoration}){literal_label}(?P=outside)\s*:|"
        rf"(?P<inside>{decoration}){literal_label}\s*:(?P=inside)|"
        rf"{literal_label}\s*:"
        r")\s*(?P<value>.*?)\s*$",
        re.IGNORECASE,
    )
    return [match.group("value").strip() for line in lines if (match := pattern.match(line))]


def exact_fields(response: str, fields: dict) -> tuple[bool, str]:
    """Require each declared ``Label: value`` field to appear exactly once with its exact value.

    A closed literal-field assertion for structured packets: unlike `contains_all`, it rejects a
    prefix match on the label, a duplicated field, and a value that merely contains the expected
    text. Display-only Markdown around the label is tolerated; the value is compared verbatim.
    """
    if not isinstance(fields, dict) or not fields:
        raise ValueError("exact_fields requires a non-empty {label: value} mapping")
    for label, value in fields.items():
        if not isinstance(label, str) or not label.strip():
            raise ValueError("exact_fields labels must be non-empty strings")
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"exact_fields[{label!r}] must be a non-empty exact string value")
    lines = response.splitlines()
    problems: list[str] = []
    for label, expected in fields.items():
        occurrences = _literal_field_occurrences(label, lines)
        if len(occurrences) != 1:
            problems.append(f"{label}: found {len(occurrences)} occurrence(s), need exactly 1")
            continue
        actual = occurrences[0]
        if actual != expected:
            problems.append(f"{label}: value {actual!r} != {expected!r}")
    return (not problems, "all exact fields matched" if not problems else "; ".join(problems))


REGISTRY: dict[str, Callable[..., tuple[bool, str]]] = {
    "contains_all": contains_all,
    "contains_any": contains_any,
    "distinct_command_flag_targets": distinct_command_flag_targets,
    "not_contains": not_contains,
    "regex": regex,
    "not_regex": not_regex,
    "json_artifact_statuses": json_artifact_statuses,
    "exact_fields": exact_fields,
}


def run_grader(spec: dict, response: str) -> tuple[bool, str]:
    """spec = {type: <name>, ...kwargs}. Dispatches to REGISTRY."""
    kind = spec.get("type")
    fn = REGISTRY.get(kind)
    if fn is None:
        raise ValueError(f"unknown grader type: {kind!r} (known: {', '.join(REGISTRY)})")
    kwargs = {k: v for k, v in spec.items() if k != "type"}
    return fn(response, **kwargs)
