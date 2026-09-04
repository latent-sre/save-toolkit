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
import math
import re
import shlex
from collections.abc import Callable


def _norm(text: str) -> str:
    return text.lower()


def _duplicate_key_hook(
    duplicate_keys: list[str],
) -> Callable[[list[tuple[str, object]]], dict[str, object]]:
    """Build a JSON object hook that records duplicate fields while decoding."""

    def reject(pairs: list[tuple[str, object]]) -> dict[str, object]:
        payload: dict[str, object] = {}
        for key, value in pairs:
            if key in payload:
                duplicate_keys.append(key)
            payload[key] = value
        return payload

    return reject


# A backslash ending a line joins it to the next one -- and joins it with NO separator, so
# `serv\<newline>ices` is the single word `services`. Substituting a space here instead of the
# empty string would split that word and miss the command, which is why this is not redundant with
# the generic backslash handling below. Optional trailing horizontal space is accepted too: a real
# shell would not continue that line, but a human reading the transcript sees one command either
# way, and erring toward detection is the safe direction for a rejection check.
#
# No `\r?` here: the caller has already split the response with `splitlines()`, which consumes CR,
# CRLF, and LF alike and drops the terminator, so no carriage return can reach this pattern. A
# `\r?` was written here first and proved unkillable by any fixture -- it was unreachable, not
# defensive, and a branch no input can take is worse than absent when it implies coverage.
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


def _strict_json_value_problem(
    value: object,
    path: str = "$",
    active_containers: set[int] | None = None,
) -> str | None:
    """Return why a configured/decoded value is not finite strict JSON, if anything."""
    if value is None or type(value) in (str, bool, int):
        return None
    if type(value) is float:
        return None if math.isfinite(value) else f"{path}: number must be finite"
    if type(value) not in (list, dict):
        return f"{path}: unsupported {type(value).__name__} value"

    active = active_containers if active_containers is not None else set()
    identity = id(value)
    if identity in active:
        return f"{path}: circular container"
    active.add(identity)
    try:
        if type(value) is list:
            for index, item in enumerate(value):
                problem = _strict_json_value_problem(item, f"{path}[{index}]", active)
                if problem:
                    return problem
            return None

        for key, item in value.items():
            if type(key) is not str:
                return f"{path}: object key must be a string, got {type(key).__name__}"
            problem = _strict_json_value_problem(item, f"{path}[{ascii(key)}]", active)
            if problem:
                return problem
        return None
    finally:
        active.remove(identity)


def _strict_json_equal(actual: object, expected: object) -> bool:
    """Compare JSON values without Python's bool/int or nested coercive equality."""
    if type(actual) is not type(expected):
        return False
    if type(expected) is list:
        return len(actual) == len(expected) and all(
            _strict_json_equal(actual_item, expected_item)
            for actual_item, expected_item in zip(actual, expected, strict=True)
        )
    if type(expected) is dict:
        return actual.keys() == expected.keys() and all(
            _strict_json_equal(actual[key], expected[key]) for key in expected
        )
    return actual == expected


def _validate_exact_json_fields(fields: dict, grader_name: str) -> None:
    """Validate the configured exact JSON object independently of any response text."""
    if not isinstance(fields, dict) or not fields:
        raise ValueError(f"{grader_name} requires a non-empty fields mapping")
    if any(not isinstance(key, str) or not key.strip() for key in fields):
        raise ValueError(f"{grader_name} field names must be non-empty strings")
    try:
        config_problem = _strict_json_value_problem(fields)
    except RecursionError:
        raise ValueError(f"{grader_name} fields exceed safe JSON nesting") from None
    if config_problem:
        raise ValueError(
            f"{grader_name} fields must be finite strict JSON: {config_problem}"
        )
    try:
        json.dumps(fields, allow_nan=False)
    except (TypeError, ValueError):
        raise ValueError(
            f"{grader_name} fields must be encodable as finite strict JSON"
        ) from None


def exact_json(response: str, fields: dict) -> tuple[bool, str]:
    """Require one whole-response JSON object with the exact keys, types, and values.

    This is the closed decision-packet form for authority-bearing evals. Natural-language
    affirmations and denials are intentionally outside the contract: prose, fences, duplicate
    keys, missing or extra fields, and type-coercible values all fail closed.
    """
    _validate_exact_json_fields(fields, "exact_json")

    duplicate_keys: list[str] = []

    def reject_nonstandard_constant(constant: str) -> None:
        raise ValueError(f"non-standard JSON constant {constant}")

    try:
        payload = json.loads(
            response,
            object_pairs_hook=_duplicate_key_hook(duplicate_keys),
            parse_constant=reject_nonstandard_constant,
        )
    except json.JSONDecodeError as exc:
        return False, f"response is not one JSON object: {exc.msg}"
    except (ValueError, RecursionError) as exc:
        return False, f"response is not strict JSON: {exc}"
    if duplicate_keys:
        return False, f"duplicate JSON field(s): {sorted(set(duplicate_keys))!a}"
    if not isinstance(payload, dict):
        return False, "response JSON must be an object"
    try:
        response_problem = _strict_json_value_problem(payload)
    except RecursionError:
        return False, "response JSON exceeds safe nesting"
    if response_problem:
        return False, f"response is not finite strict JSON: {response_problem}"

    expected_keys = set(fields)
    actual_keys = set(payload)
    if actual_keys != expected_keys:
        return False, (
            f"JSON fields mismatch: missing={sorted(expected_keys - actual_keys)!a}, "
            f"extra={sorted(actual_keys - expected_keys)!a}"
        )
    try:
        wrong = {
            field: payload[field]
            for field, expected in fields.items()
            if not _strict_json_equal(payload[field], expected)
        }
    except RecursionError:
        return False, "response JSON exceeds safe comparison nesting"
    return (
        not wrong,
        "all exact JSON fields matched" if not wrong else f"JSON value mismatch: {wrong!a}",
    )


def rubric(response: str, name: str, params: dict | None = None) -> tuple[bool, str]:
    """Delegate a natural-language policy judgment to the calibrated LLM judge (evals/judge.py).

    The nine graders this replaces tried to decide voice, authority, and ordering questions with
    regexes over English negation; see evals/rubrics.yaml for the rubric text they were replaced
    with and evals/rubrics-calibration.yaml for the adversarial corpus judges are checked against.
    This grader itself stays deterministic and offline: it validates the spec (rubric exists,
    params match exactly) and short-circuits an empty response (the `--validate` path) without
    ever spawning a model. `judge` is imported lazily so that validating or running every OTHER
    grader never pulls in PyYAML or the clean-room subprocess machinery.
    """
    import judge as _judge  # local import -- see docstring

    params = params or {}
    rubrics = _judge.load_rubrics()
    _judge.validate_params(name, rubrics, params)
    if not response:
        return False, "empty response"
    return _judge.judge(response, name, params)


REGISTRY: dict[str, Callable[..., tuple[bool, str]]] = {
    "contains_all": contains_all,
    "contains_any": contains_any,
    "not_contains": not_contains,
    "regex": regex,
    "not_regex": not_regex,
    "exact_fields": exact_fields,
    "exact_json": exact_json,
    "rubric": rubric,
}


def run_grader(spec: dict, response: str) -> tuple[bool, str]:
    """spec = {type: <name>, ...kwargs}. Dispatches to REGISTRY."""
    kind = spec.get("type")
    fn = REGISTRY.get(kind)
    if fn is None:
        raise ValueError(f"unknown grader type: {kind!r} (known: {', '.join(REGISTRY)})")
    kwargs = {k: v for k, v in spec.items() if k != "type"}
    return fn(response, **kwargs)
