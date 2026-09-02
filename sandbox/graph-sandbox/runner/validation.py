from __future__ import annotations

import re
from collections.abc import Mapping


ATOMIC_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{0,127}\Z")
DERIVED_ID_PATTERN = re.compile(
    r"[a-z0-9][a-z0-9._-]{0,127}(?::[a-z0-9][a-z0-9._-]{0,127})*\Z"
)
SOURCE_REVISION_PATTERN = re.compile(r"[0-9a-f]{40}\Z")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}\Z")
RFC3339_UTC_PATTERN = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?Z\Z"
)


def validate_atomic_id(value: object, field: str) -> str:
    if not isinstance(value, str) or not ATOMIC_ID_PATTERN.fullmatch(value):
        raise ValueError(f"{field} must be a valid atomic identity")
    return value


def validate_derived_id(value: object, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) > 511
        or not DERIVED_ID_PATTERN.fullmatch(value)
    ):
        raise ValueError(f"{field} must be a valid derived identity")
    return value


def validate_source_revision(value: object) -> str:
    if not isinstance(value, str) or not SOURCE_REVISION_PATTERN.fullmatch(value):
        raise ValueError("source_revision must be exactly 40 lowercase hexadecimal characters")
    return value


def validate_sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value):
        raise ValueError(f"{field} must be exactly 64 lowercase hexadecimal characters")
    return value


def require_closed_mapping(
    value: object,
    *,
    field: str,
    required: set[str],
    optional: set[str] | None = None,
) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    allowed = required | (optional or set())
    missing = required - set(value)
    extra = set(value) - allowed
    if missing:
        raise ValueError(f"{field} missing fields: {', '.join(sorted(missing))}")
    if extra:
        raise ValueError(f"{field} has unexpected fields: {', '.join(sorted(extra))}")
    return value
