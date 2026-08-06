#!/usr/bin/env python3
"""Validate fleet-improvement record shape against the published JSON Schema subset.

The improvement lifecycle (`skills/agent-authoring/references/improvement-lifecycle.md`) is the
fleet's self-learning loop: an agent records a normalized failure, evidence accrues across bounded
attempts, and a **human** (or a protected workflow) promotes or rolls back. Every record under
`evals/improvements/<id>/record.json` is checked against
`skills/agent-authoring/assets/fleet-improvement-v1.schema.json`. This is a structural schema check,
not the parked lifecycle validator.

Scope, stated honestly: this implements the subset of JSON Schema draft 2020-12 the schema actually
uses — `$ref`/`$defs`, `allOf`/`anyOf`/`oneOf`, `if`/`then`/`else`, `type`, `required`,
`properties`, `additionalProperties`, `enum`, `const`, `pattern`, `minimum`/`maximum`,
`minItems`/`maxItems`/`uniqueItems`, `items`, `minLength`/`maxLength`. Draft 2020-12 `format` is
recognized as an annotation and is intentionally not asserted. The root dialect and resource ID are
pinned; nested resource IDs and dialect switches are rejected. JSON values use JSON-semantic
equality, and patterns are restricted to an audited ECMA-262/Python intersection. The deeper semantic
checks the lifecycle names — cumulative budget across attempts, exact-subject revision binding,
append-only history, and external authority — remain parked. The schema checker is fail-closed:
adding a keyword outside this implemented subset, or giving a supported assertion an unsupported
shape, fails Gate A instead of silently weakening validation.

Standard library only. Run by Gate A.
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path
from urllib.parse import unquote_to_bytes

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "skills/agent-authoring/assets/fleet-improvement-v1.schema.json"
RECORDS_GLOB = "evals/improvements/*/record.json"
SUPPORTED_DIALECT = "https://json-schema.org/draft/2020-12/schema"
ROOT_SCHEMA_ID = (
    "https://github.com/latent-sre/save-toolkit/skills/agent-authoring/assets/"
    "fleet-improvement-v1.schema.json"
)

# JSON Schema "type" -> a predicate on a Python value. `integer` and `number` must reject bool,
# which is an int subclass in Python; a schema that says integer does not mean "or True".
_TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: (
        isinstance(v, (int, float))
        and not isinstance(v, bool)
        and (not isinstance(v, float) or math.isfinite(v))
    ),
}


def _json_equal(left: object, right: object) -> bool:
    """Return JSON-value equality, where booleans are not numbers."""

    if left is None or right is None:
        return left is None and right is None
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left is right
    if isinstance(left, (int, float)) or isinstance(right, (int, float)):
        return (
            isinstance(left, (int, float))
            and not isinstance(left, bool)
            and isinstance(right, (int, float))
            and not isinstance(right, bool)
            and left == right
        )
    if isinstance(left, str) or isinstance(right, str):
        return isinstance(left, str) and isinstance(right, str) and left == right
    if isinstance(left, list) or isinstance(right, list):
        return (
            isinstance(left, list)
            and isinstance(right, list)
            and len(left) == len(right)
            and all(_json_equal(a, b) for a, b in zip(left, right))
        )
    if isinstance(left, dict) or isinstance(right, dict):
        return (
            isinstance(left, dict)
            and isinstance(right, dict)
            and left.keys() == right.keys()
            and all(_json_equal(left[key], right[key]) for key in left)
        )
    return False


def _pattern_portability_error(pattern: str) -> str | None:
    """Return why a Python pattern is outside the audited ECMA-262 intersection."""

    in_class = False
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if char == "\\":
            if index + 1 >= len(pattern):
                return None  # The compiler reports the dangling escape with better detail.
            escaped = pattern[index + 1]
            if escaped in "dDsSwW":
                return f"shorthand character class \\{escaped} has divergent Unicode semantics"
            if escaped in "bB":
                return f"word-boundary escape \\{escaped} has divergent Unicode semantics"
            if escaped in "ANUZzG":
                return f"Python-only escape \\{escaped} is unsupported"
            index += 2
            continue
        if char == "[" and not in_class:
            in_class = True
            index += 1
            continue
        if char == "]" and in_class:
            in_class = False
            index += 1
            continue
        if not in_class and char == "(" and pattern.startswith("(?", index):
            if pattern.startswith(("(?:", "(?=", "(?!"), index):
                index += 1
                continue
            if pattern.startswith(("(?P<", "(?P=", "(?#", "(?(", "(?>"), index):
                return "Python-only group construct is unsupported"
            return "group construct outside the conservative ECMA-262/Python intersection"
        if not in_class and (
            pattern.startswith(("*+", "++", "?+"), index)
            or (char == "}" and index + 1 < len(pattern) and pattern[index + 1] == "+")
        ):
            return "Python-only possessive quantifier is unsupported"
        index += 1
    return None


def _translate_ecma_wildcards(pattern: str) -> str:
    """Give Python's wildcard the ECMA-262 line-terminator exclusion set."""

    translated: list[str] = []
    in_class = False
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if char == "\\" and index + 1 < len(pattern):
            translated.extend((char, pattern[index + 1]))
            index += 2
            continue
        if char == "[" and not in_class:
            in_class = True
        elif char == "]" and in_class:
            in_class = False
        if char == "." and not in_class:
            translated.append(r"[^\n\r\u2028\u2029]")
        elif char == "$" and not in_class:
            translated.append(r"\Z")
        else:
            translated.append(char)
        index += 1
    return "".join(translated)


def _compile_pattern(pattern: str) -> re.Pattern[str]:
    portability_error = _pattern_portability_error(pattern)
    if portability_error:
        raise ValueError(portability_error)
    try:
        return re.compile(_translate_ecma_wildcards(pattern), flags=re.ASCII)
    except re.error as exc:
        raise ValueError(f"invalid regular expression: {exc}") from exc

# The bundled checker is deliberately a small, auditable subset rather than a partial implementation
# that silently accepts schemas it cannot enforce. Annotation keywords do not affect validity under
# JSON Schema draft 2020-12; in particular, `format` remains annotation-only unless a validator is
# explicitly configured with a format assertion vocabulary.
_ASSERTION_KEYWORDS = frozenset(
    {
        "$ref",
        "additionalProperties",
        "allOf",
        "anyOf",
        "const",
        "else",
        "enum",
        "if",
        "items",
        "maxItems",
        "maxLength",
        "maximum",
        "minItems",
        "minLength",
        "minimum",
        "oneOf",
        "pattern",
        "properties",
        "required",
        "then",
        "type",
        "uniqueItems",
    }
)
_ANNOTATION_KEYWORDS = frozenset({"$id", "$schema", "description", "format", "title"})
_SCHEMA_CONTAINER_KEYWORDS = frozenset({"$defs", "properties"})
_SCHEMA_SEQUENCE_KEYWORDS = frozenset({"allOf", "anyOf", "oneOf"})
_SCHEMA_SINGLE_KEYWORDS = frozenset({"additionalProperties", "else", "if", "items", "then"})
_SUPPORTED_SCHEMA_KEYWORDS = (
    _ASSERTION_KEYWORDS | _ANNOTATION_KEYWORDS | _SCHEMA_CONTAINER_KEYWORDS
)


def _schema_keyword_errors(
    schema: object,
    path: str = "#",
    root: dict | None = None,
    _visited: set[int] | None = None,
) -> list[str]:
    """Reject unsupported schema features and audit every reachable local ``$ref``."""
    if not isinstance(schema, dict):
        return [f"{path}: expected a schema object, got {type(schema).__name__}"]
    if root is None:
        root = schema
    if _visited is None:
        _visited = set()
    marker = id(schema)
    if marker in _visited:
        return []
    _visited.add(marker)

    errors = [
        f"{path}: unsupported JSON Schema keyword {keyword!r}"
        for keyword in sorted(set(schema) - _SUPPORTED_SCHEMA_KEYWORDS)
    ]

    string_keywords = ("$id", "$ref", "$schema", "description", "format", "pattern", "title")
    for keyword in string_keywords:
        if keyword in schema and not isinstance(schema[keyword], str):
            errors.append(f"{path}/{keyword}: expected a string")
    is_root = schema is root
    if not is_root:
        if "$id" in schema:
            errors.append(
                f"{path}/$id: nested $id resources are unsupported; refs remain rooted at {ROOT_SCHEMA_ID!r}"
            )
        if "$schema" in schema and schema["$schema"] != SUPPORTED_DIALECT:
            errors.append(
                f"{path}/$schema: nested dialect switch is unsupported; expected {SUPPORTED_DIALECT!r}"
            )
    if isinstance(schema.get("$ref"), str):
        ref = schema["$ref"]
        try:
            target = _resolve_ref(ref, root)
        except ValueError as exc:
            errors.append(f"{path}/$ref: {exc}")
        else:
            # A target can live outside a normal schema-bearing keyword (for example beneath an
            # annotation or const object), so resolving alone is not enough: audit the target as a
            # schema too. Object identity makes recursive and mutually recursive local refs finite.
            errors += _schema_keyword_errors(
                target,
                f"{path}/$ref->{ref!r}",
                root,
                _visited,
            )
    if "pattern" in schema and isinstance(schema["pattern"], str):
        try:
            _compile_pattern(schema["pattern"])
        except ValueError as exc:
            errors.append(f"{path}/pattern: {exc}")

    if "type" in schema:
        declared = schema["type"]
        if not isinstance(declared, str) or declared not in _TYPE_CHECKS:
            errors.append(
                f"{path}/type: expected one supported type name, got {declared!r}"
            )

    for keyword in ("minItems", "maxItems", "minLength", "maxLength"):
        if keyword in schema and (
            not isinstance(schema[keyword], int)
            or isinstance(schema[keyword], bool)
            or schema[keyword] < 0
        ):
            errors.append(f"{path}/{keyword}: expected a non-negative integer")
    for lower, upper in (("minItems", "maxItems"), ("minLength", "maxLength")):
        if (
            isinstance(schema.get(lower), int)
            and not isinstance(schema.get(lower), bool)
            and isinstance(schema.get(upper), int)
            and not isinstance(schema.get(upper), bool)
            and schema[lower] > schema[upper]
        ):
            errors.append(f"{path}: {lower} exceeds {upper}")

    for keyword in ("minimum", "maximum"):
        if keyword in schema and (
            not isinstance(schema[keyword], (int, float))
            or isinstance(schema[keyword], bool)
            or (isinstance(schema[keyword], float) and not math.isfinite(schema[keyword]))
        ):
            errors.append(f"{path}/{keyword}: expected a finite number")
    if (
        isinstance(schema.get("minimum"), (int, float))
        and not isinstance(schema.get("minimum"), bool)
        and isinstance(schema.get("maximum"), (int, float))
        and not isinstance(schema.get("maximum"), bool)
        and schema["minimum"] > schema["maximum"]
    ):
        errors.append(f"{path}: minimum exceeds maximum")

    if "uniqueItems" in schema and not isinstance(schema["uniqueItems"], bool):
        errors.append(f"{path}/uniqueItems: expected a boolean")
    if "additionalProperties" in schema and not isinstance(
        schema["additionalProperties"], (bool, dict)
    ):
        errors.append(f"{path}/additionalProperties: expected a boolean or schema object")

    if "required" in schema:
        required = schema["required"]
        if not isinstance(required, list) or not all(isinstance(item, str) for item in required):
            errors.append(f"{path}/required: expected an array of strings")
        elif len(required) != len(set(required)):
            errors.append(f"{path}/required: names must be unique")
    if "enum" in schema:
        enum = schema["enum"]
        if not isinstance(enum, list) or not enum:
            errors.append(f"{path}/enum: expected a non-empty array")
        elif any(
            any(_json_equal(item, previous) for previous in enum[:index])
            for index, item in enumerate(enum)
        ):
            errors.append(f"{path}/enum: values must be unique")

    for keyword in sorted(_SCHEMA_CONTAINER_KEYWORDS & schema.keys()):
        children = schema[keyword]
        if not isinstance(children, dict):
            errors.append(f"{path}/{keyword}: expected an object of schemas")
            continue
        for name, child in children.items():
            errors += _schema_keyword_errors(
                child,
                f"{path}/{keyword}/{name}",
                root,
                _visited,
            )

    for keyword in sorted(_SCHEMA_SEQUENCE_KEYWORDS & schema.keys()):
        children = schema[keyword]
        if not isinstance(children, list):
            errors.append(f"{path}/{keyword}: expected an array of schemas")
            continue
        if not children:
            errors.append(f"{path}/{keyword}: expected at least one schema")
        for index, child in enumerate(children):
            errors += _schema_keyword_errors(
                child,
                f"{path}/{keyword}/{index}",
                root,
                _visited,
            )

    for keyword in sorted(_SCHEMA_SINGLE_KEYWORDS & schema.keys()):
        child = schema[keyword]
        if isinstance(child, dict):
            errors += _schema_keyword_errors(
                child,
                f"{path}/{keyword}",
                root,
                _visited,
            )
        elif keyword != "additionalProperties":
            errors.append(f"{path}/{keyword}: expected a schema object")

    return errors


def _schema_document_errors(schema: object) -> list[str]:
    """Audit one complete schema document, including its fixed dialect and resource identity."""

    errors = _schema_keyword_errors(schema)
    if not isinstance(schema, dict):
        return errors
    if "$schema" not in schema:
        errors.insert(0, f"#: missing required root $schema {SUPPORTED_DIALECT!r}")
    elif schema["$schema"] != SUPPORTED_DIALECT:
        errors.insert(
            0,
            f"#/$schema: unsupported root $schema {schema['$schema']!r}; expected {SUPPORTED_DIALECT!r}",
        )
    if "$id" not in schema:
        errors.insert(0, f"#: missing required root $id {ROOT_SCHEMA_ID!r}")
    elif schema["$id"] != ROOT_SCHEMA_ID:
        errors.insert(
            0,
            f"#/$id: unsupported root $id {schema['$id']!r}; expected {ROOT_SCHEMA_ID!r}",
        )
    return errors


def _resolve_ref(ref: str, root: dict) -> dict:
    """Resolve a local JSON pointer ($ref) against the root schema."""
    if not ref.startswith("#"):
        raise ValueError(f"only local $ref is supported, got {ref!r}")
    if ref == "#":
        return root
    if not ref.startswith("#/"):
        raise ValueError(f"only local JSON Pointer $ref is supported, got {ref!r}")
    encoded_pointer = ref[1:]
    if re.search(r"%(?![0-9A-Fa-f]{2})", encoded_pointer):
        raise ValueError(f"invalid percent escape in $ref {ref!r}")
    try:
        pointer = unquote_to_bytes(encoded_pointer).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"$ref {ref!r} is not valid UTF-8") from exc

    node: object = root
    for token in pointer[1:].split("/"):
        if re.search(r"~(?![01])", token):
            raise ValueError(f"invalid JSON Pointer escape in $ref {ref!r}")
        token = token.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict) and token in node:
            node = node[token]
            continue
        if isinstance(node, list) and re.fullmatch(r"0|[1-9][0-9]*", token):
            index = int(token)
            if index < len(node):
                node = node[index]
                continue
        else:
            raise ValueError(f"unresolvable $ref {ref!r}")
        raise ValueError(f"unresolvable $ref {ref!r}")
    if not isinstance(node, dict):
        raise ValueError(f"$ref {ref!r} does not point at a schema object")
    return node


def _errors(
    value: object,
    schema: dict,
    root: dict,
    path: str,
    _active: set[tuple[int, int]] | None = None,
) -> list[str]:
    """Return every way `value` fails `schema`. Empty list means valid."""

    if _active is None:
        _active = set()
    marker = (id(schema), id(value))
    if marker in _active:
        return [f"{path}: cyclic schema evaluation made no instance progress"]
    _active.add(marker)
    try:
        return _evaluate_errors(value, schema, root, path, _active)
    finally:
        _active.remove(marker)


def _evaluate_errors(
    value: object,
    schema: dict,
    root: dict,
    path: str,
    active: set[tuple[int, int]],
) -> list[str]:
    errs: list[str] = []

    if "$ref" in schema:
        errs += _errors(value, _resolve_ref(schema["$ref"], root), root, path, active)
        # draft 2020-12 evaluates sibling keywords alongside $ref; fall through to the rest.

    if "type" in schema:
        types = schema["type"]
        types = [types] if isinstance(types, str) else types
        if not any(_TYPE_CHECKS[t](value) for t in types):
            errs.append(f"{path}: expected type {schema['type']}, got {type(value).__name__}")
            return errs  # further keywords assume the type; stop to avoid noise

    if "const" in schema and not _json_equal(value, schema["const"]):
        errs.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and not any(_json_equal(value, item) for item in schema["enum"]):
        errs.append(f"{path}: {value!r} not in {schema['enum']}")

    if isinstance(value, str):
        if "pattern" in schema and not _compile_pattern(schema["pattern"]).search(value):
            errs.append(f"{path}: {value!r} does not match /{schema['pattern']}/")
        if "minLength" in schema and len(value) < schema["minLength"]:
            errs.append(f"{path}: shorter than minLength {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errs.append(f"{path}: longer than maxLength {schema['maxLength']}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errs.append(f"{path}: {value} < minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errs.append(f"{path}: {value} > maximum {schema['maximum']}")

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errs.append(f"{path}: {len(value)} items < minItems {schema['minItems']}")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errs.append(f"{path}: {len(value)} items > maxItems {schema['maxItems']}")
        if schema.get("uniqueItems") is True:
            # Items may be dicts/lists (unhashable), so no set — an O(n^2) scan on the small
            # bounded arrays the schema declares (maxItems <= 64) compares by JSON value.
            seen: list[object] = []
            for i, item in enumerate(value):
                if any(_json_equal(item, previous) for previous in seen):
                    errs.append(f"{path}[{i}]: duplicate item violates uniqueItems")
                else:
                    seen.append(item)
        if "items" in schema:
            for i, item in enumerate(value):
                errs += _errors(item, schema["items"], root, f"{path}[{i}]", active)

    if isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                errs.append(f"{path}: missing required '{req}'")
        props = schema.get("properties", {})
        for key, sub in props.items():
            if key in value:
                errs += _errors(value[key], sub, root, f"{path}.{key}", active)
        additional = schema.get("additionalProperties", True)
        extra = sorted(set(value) - set(props))
        if additional is False:
            if extra:
                errs.append(f"{path}: unexpected propert(y/ies): {', '.join(extra)}")
        elif isinstance(additional, dict):
            for key in extra:
                errs += _errors(value[key], additional, root, f"{path}.{key}", active)

    for sub in schema.get("allOf", []):
        errs += _errors(value, sub, root, path, active)
    if "anyOf" in schema:
        if all(_errors(value, sub, root, path, active) for sub in schema["anyOf"]):
            errs.append(f"{path}: matched none of anyOf")
    if "oneOf" in schema:
        matches = sum(
            1 for sub in schema["oneOf"] if not _errors(value, sub, root, path, active)
        )
        if matches != 1:
            errs.append(f"{path}: matched {matches} of oneOf (must be exactly 1)")
    if "if" in schema:
        if not _errors(value, schema["if"], root, path, active):
            if "then" in schema:
                errs += _errors(value, schema["then"], root, path, active)
        elif "else" in schema:
            errs += _errors(value, schema["else"], root, path, active)

    return errs


def _loads_strict_json(text: str) -> object:
    """Parse RFC 8259 JSON; reject Python's non-standard NaN/Infinity extensions."""

    def reject_constant(token: str) -> object:
        raise ValueError(f"non-standard JSON numeric constant {token!r}")

    return json.loads(text, parse_constant=reject_constant)


def check(root: Path = ROOT) -> list[str]:
    try:
        schema = _loads_strict_json(
            (root / SCHEMA.relative_to(ROOT)).read_text(encoding="utf-8")
        )
    except (OSError, ValueError) as exc:
        return [f"{SCHEMA.relative_to(ROOT).as_posix()}: cannot load schema: {exc}"]
    failures = _schema_document_errors(schema)
    if failures:
        return failures
    records = sorted(root.glob(RECORDS_GLOB))
    for record_path in records:
        rel = record_path.relative_to(root).as_posix()
        try:
            record = _loads_strict_json(record_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            failures.append(f"{rel}: cannot parse record: {exc}")
            continue
        failures += _errors(record, schema, schema, rel)
    return failures


def main() -> int:
    failures = check(ROOT)
    if failures:
        print("validate_improvements: FAIL")
        for failure in failures:
            print("  " + failure)
        return 1
    n = len(sorted(ROOT.glob(RECORDS_GLOB)))
    print(f"validate_improvements: PASS ({n} record(s) valid against fleet-improvement-v1)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
