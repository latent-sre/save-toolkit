#!/usr/bin/env python3
"""Build the reviewed Codex 0.148 Terra catalog with no local-file tools."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path


MODEL = "gpt-5.6-terra"
MAX_CATALOG_BYTES = 8 * 1024 * 1024
EXPECTED_SOURCE_ENTRY_SHA256 = (
    "3a934e842c9b6a813dfe04ec826da0b79dcfc9b3187696d4b2c1b7110cdb811c"
)
EXPECTED_TRANSFORMED_ENTRY_SHA256 = (
    "1c03b5e12771bc6e961c0fac20830a0a2c5fcca011793ec985d24aa4d41140e9"
)
EXPECTED_SAFE_CATALOG_SHA256 = (
    "b5122f71336f146cb6c656167e7f3258a9e4735583b95435f808261562bb646f"
)
CHANGED_FIELDS = (
    "apply_patch_tool_type",
    "experimental_supported_tools",
    "supports_search_tool",
    "tool_mode",
)


class CatalogError(ValueError):
    """The installed model catalog did not match the reviewed transform boundary."""


@dataclass(frozen=True)
class CatalogReceipt:
    """Persistable catalog facts without model instructions or filesystem paths."""

    model: str
    source_entry_sha256: str
    transformed_entry_sha256: str
    safe_catalog_sha256: str
    source_field_count: int
    changed_fields: tuple[str, ...]


def _reject_json_constant(value: str) -> object:
    raise ValueError(f"non-standard JSON constant {value!r}")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, child in pairs:
        if key in value:
            raise ValueError("duplicate JSON object key")
        value[key] = child
    return value


def _canonical(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CatalogError("model catalog is not canonical JSON data") from exc


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def build_safe_catalog(raw: bytes) -> tuple[bytes, CatalogReceipt]:
    """Reduce exact bundled Terra metadata to the reviewed no-local-file-tools entry."""

    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_CATALOG_BYTES:
        raise CatalogError("bundled model catalog is empty or oversized")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise CatalogError("bundled model catalog is not one strict UTF-8 JSON object") from exc
    if not isinstance(value, dict) or set(value) != {"models"}:
        raise CatalogError("bundled model catalog has the wrong top-level shape")
    models = value["models"]
    if not isinstance(models, list):
        raise CatalogError("bundled model catalog models must be a list")
    matches = [item for item in models if isinstance(item, dict) and item.get("slug") == MODEL]
    if len(matches) != 1:
        raise CatalogError("bundled model catalog must contain exactly one authorized model")
    source = matches[0]
    expected_source_values = {
        "tool_mode": "code_mode_only",
        "apply_patch_tool_type": "freeform",
        "shell_type": "shell_command",
        "supports_search_tool": True,
    }
    if any(source.get(key) != expected for key, expected in expected_source_values.items()):
        raise CatalogError("authorized model tool metadata drifted")
    if not isinstance(source.get("experimental_supported_tools"), list):
        raise CatalogError("authorized model experimental tools must be a list")
    source_sha256 = _sha256(_canonical(source))
    if source_sha256 != EXPECTED_SOURCE_ENTRY_SHA256:
        raise CatalogError("authorized model entry differs from the reviewed Codex 0.148 bytes")

    transformed = copy.deepcopy(source)
    transformed.update(
        {
            "apply_patch_tool_type": None,
            "experimental_supported_tools": [],
            "supports_search_tool": False,
            "tool_mode": None,
        }
    )
    for key, child in source.items():
        if key not in CHANGED_FIELDS and transformed.get(key) != child:
            raise CatalogError("model catalog transform changed an unreviewed field")
    transformed_sha256 = _sha256(_canonical(transformed))
    if transformed_sha256 != EXPECTED_TRANSFORMED_ENTRY_SHA256:
        raise CatalogError("safe model entry differs from the reviewed transform")
    encoded = _canonical({"models": [transformed]})
    catalog_sha256 = _sha256(encoded)
    if catalog_sha256 != EXPECTED_SAFE_CATALOG_SHA256:
        raise CatalogError("safe model catalog differs from the reviewed transform")
    return encoded, CatalogReceipt(
        model=MODEL,
        source_entry_sha256=source_sha256,
        transformed_entry_sha256=transformed_sha256,
        safe_catalog_sha256=catalog_sha256,
        source_field_count=len(source),
        changed_fields=CHANGED_FIELDS,
    )


def _ordinary_parent(path: Path) -> Path:
    try:
        parent = path.parent.resolve(strict=True)
    except OSError as exc:
        raise CatalogError("safe catalog parent must already exist") from exc
    if (
        path.parent.is_symlink()
        or not path.parent.is_dir()
        or parent != path.parent.absolute()
    ):
        raise CatalogError("safe catalog parent must be an ordinary directory")
    return parent


def write_safe_catalog(raw: bytes, destination: Path) -> CatalogReceipt:
    """Create the reviewed catalog once in a caller-owned disposable directory."""

    target = Path(destination)
    if target.name != "route-models.json":
        raise CatalogError("safe catalog must use the fixed filename")
    parent = _ordinary_parent(target)
    target = parent / target.name
    encoded, receipt = build_safe_catalog(raw)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_BINARY", 0)
    descriptor = os.open(target, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            target.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    try:
        metadata = target.lstat()
        actual = target.read_bytes()
    except OSError as exc:
        raise CatalogError("safe catalog could not be verified after creation") from exc
    if (
        target.is_symlink()
        or not target.is_file()
        or getattr(metadata, "st_nlink", 1) != 1
        or actual != encoded
    ):
        raise CatalogError("safe catalog changed during publication")
    return receipt
