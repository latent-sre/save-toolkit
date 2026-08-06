#!/usr/bin/env python3
"""Validate fleet-improvement records — makes the self-learning loop's contract ENFORCED.

The improvement lifecycle (`skills/agent-authoring/references/improvement-lifecycle.md`) is the
fleet's self-learning loop: an agent records a normalized failure, evidence accrues across bounded
attempts, and a **human** (or a protected workflow) promotes or rolls back. This validator does not
change that safety invariant — there is still no unsupervised self-modification. It only makes the
loop *live* instead of aspirational: every record under `evals/improvements/<id>/record.json` is now
checked against `skills/agent-authoring/assets/fleet-improvement-v1.schema.json`, which previously
had `validator: null` and so was enforced by nothing.

Scope, stated honestly: this implements the subset of JSON Schema draft 2020-12 the schema actually
uses — `$ref`/`$defs`, `allOf`/`anyOf`/`oneOf`, `if`/`then`/`else`, `type`, `required`,
`properties`, `additionalProperties`, `enum`, `const`, `pattern`, `minimum`/`maximum`,
`minItems`/`maxItems`, `items`, `minLength`/`maxLength`. The deeper semantic checks the lifecycle
names — cumulative budget across attempts, exact-subject revision binding, append-only history,
external-authority — are not expressible in JSON Schema and remain a documented next layer. This gate
enforces the schema-expressible contract; it does not claim to be the full lifecycle validator.

Standard library only. Run by Gate A.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "skills/agent-authoring/assets/fleet-improvement-v1.schema.json"
RECORDS_GLOB = "evals/improvements/*/record.json"

# JSON Schema "type" -> a predicate on a Python value. `integer` and `number` must reject bool,
# which is an int subclass in Python; a schema that says integer does not mean "or True".
_TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
}


def _resolve_ref(ref: str, root: dict) -> dict:
    """Resolve a local JSON pointer ($ref) against the root schema."""
    if not ref.startswith("#"):
        raise ValueError(f"only local $ref is supported, got {ref!r}")
    node: object = root
    for token in ref.lstrip("#/").split("/"):
        if not token:
            continue
        token = token.replace("~1", "/").replace("~0", "~")
        if not isinstance(node, dict) or token not in node:
            raise ValueError(f"unresolvable $ref {ref!r}")
        node = node[token]
    if not isinstance(node, dict):
        raise ValueError(f"$ref {ref!r} does not point at a schema object")
    return node


def _errors(value: object, schema: dict, root: dict, path: str) -> list[str]:
    """Return every way `value` fails `schema`. Empty list means valid."""
    errs: list[str] = []

    if "$ref" in schema:
        errs += _errors(value, _resolve_ref(schema["$ref"], root), root, path)
        # draft 2020-12 evaluates sibling keywords alongside $ref; fall through to the rest.

    if "type" in schema:
        types = schema["type"]
        types = [types] if isinstance(types, str) else types
        if not any(_TYPE_CHECKS[t](value) for t in types):
            errs.append(f"{path}: expected type {schema['type']}, got {type(value).__name__}")
            return errs  # further keywords assume the type; stop to avoid noise

    if "const" in schema and value != schema["const"]:
        errs.append(f"{path}: must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errs.append(f"{path}: {value!r} not in {schema['enum']}")

    if isinstance(value, str):
        if "pattern" in schema and not re.search(schema["pattern"], value):
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
        if "items" in schema:
            for i, item in enumerate(value):
                errs += _errors(item, schema["items"], root, f"{path}[{i}]")

    if isinstance(value, dict):
        for req in schema.get("required", []):
            if req not in value:
                errs.append(f"{path}: missing required '{req}'")
        props = schema.get("properties", {})
        for key, sub in props.items():
            if key in value:
                errs += _errors(value[key], sub, root, f"{path}.{key}")
        if schema.get("additionalProperties") is False:
            extra = sorted(set(value) - set(props))
            if extra:
                errs.append(f"{path}: unexpected propert(y/ies): {', '.join(extra)}")

    for sub in schema.get("allOf", []):
        errs += _errors(value, sub, root, path)
    if "anyOf" in schema:
        if all(_errors(value, sub, root, path) for sub in schema["anyOf"]):
            errs.append(f"{path}: matched none of anyOf")
    if "oneOf" in schema:
        matches = sum(1 for sub in schema["oneOf"] if not _errors(value, sub, root, path))
        if matches != 1:
            errs.append(f"{path}: matched {matches} of oneOf (must be exactly 1)")
    if "if" in schema:
        if not _errors(value, schema["if"], root, path):
            if "then" in schema:
                errs += _errors(value, schema["then"], root, path)
        elif "else" in schema:
            errs += _errors(value, schema["else"], root, path)

    return errs


def check(root: Path = ROOT) -> list[str]:
    try:
        schema = json.loads((root / SCHEMA.relative_to(ROOT)).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{SCHEMA.relative_to(ROOT).as_posix()}: cannot load schema: {exc}"]
    failures: list[str] = []
    records = sorted(root.glob(RECORDS_GLOB))
    for record_path in records:
        rel = record_path.relative_to(root).as_posix()
        try:
            record = json.loads(record_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
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
