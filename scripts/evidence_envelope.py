#!/usr/bin/env python3
"""Create and validate versioned, machine-readable fleet evidence envelopes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import stat
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence


SCHEMA_VERSION = 1
STATUSES = {"pass", "fail", "inconclusive", "skip"}
TOP_LEVEL_FIELDS = {
    "schema_version",
    "evidence_id",
    "producer",
    "context",
    "target",
    "criterion",
    "status",
    "started_at",
    "ended_at",
    "command",
    "source",
    "environment",
    "isolation",
    "artifacts",
    "limitations",
}
SENSITIVE_KEY_FRAGMENTS = {
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "credential",
    "password",
    "secret",
    "token",
}
EVIDENCE_ID_RE = re.compile(r"^ev_[0-9a-f]{32}$")
CONTEXT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RFC3339_UTC_TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
)
SENSITIVE_ARG_RE = re.compile(
    r"(?i)(?:^|[-_])(?:api[-_]?key|authorization|cookie|credential|password|secret|token)(?:$|[=_-])"
)
URI_CREDENTIAL_RE = re.compile(
    r"(?i)(?:^|=)[A-Za-z][A-Za-z0-9+.-]*://[^/@\s]+:[^/@\s]+@"
)


class EnvelopeValidationError(ValueError):
    """Raised when evidence does not satisfy the strict schema."""


def _reject_duplicate_json_pairs(
    pairs: Sequence[tuple[str, object]],
) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, child in pairs:
        if key in value:
            raise EnvelopeValidationError(f"duplicate JSON object key {key!r}")
        value[key] = child
    return value


def format_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise EnvelopeValidationError("evidence timestamps must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or RFC3339_UTC_TIMESTAMP_RE.fullmatch(value) is None:
        raise EnvelopeValidationError(f"{field} must be an RFC3339 UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise EnvelopeValidationError(f"{field} is not a valid timestamp") from exc
    return parsed.astimezone(timezone.utc)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class TreeDigestError(ValueError):
    """A source snapshot could not be hashed under the tree-digest rules."""


# Kept byte-compatible with the retired scripts/verification_sandbox.py implementation -- the
# `save-toolkit-verification-tree-v1` prefix and the D/F framing are part of the digest, so any
# already-recorded digest in a dated evidence packet still verifies against this code.
TREE_DIGEST_PREFIX = b"save-toolkit-verification-tree-v1\0"
MAX_TREE_FILES = 100_000
MAX_TREE_BYTES = 10 * 1024 * 1024 * 1024
FILE_ATTRIBUTE_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


def _is_indirection(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError as exc:
        raise TreeDigestError(f"cannot inspect path metadata: {path}") from exc
    return path.is_symlink() or bool(
        getattr(info, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT
    )


def _absolute_without_indirection(path: Path, label: str) -> Path:
    """Resolve an absolute path only after rejecting linked/reparsed existing ancestors."""

    absolute = Path(os.path.abspath(path.expanduser()))
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        if not current.exists() and not current.is_symlink():
            break
        if _is_indirection(current):
            raise TreeDigestError(f"{label} must not traverse a link or reparse point: {current}")
    return absolute.resolve()


def tree_digest(root: Path) -> str:
    """Hash a bounded ordinary-file tree without following links or executing target code."""

    root = _absolute_without_indirection(root, "source")
    if not root.is_dir() or _is_indirection(root):
        raise TreeDigestError("source must be an ordinary directory, not a link or reparse point")
    if root.name.casefold() == ".git":
        raise TreeDigestError("source snapshots must not expose .git metadata")
    digest = hashlib.sha256(TREE_DIGEST_PREFIX)
    file_count = 0
    byte_count = 0

    def visit(directory: Path) -> None:
        nonlocal file_count, byte_count
        try:
            entries = sorted(directory.iterdir(), key=lambda item: item.name)
        except OSError as exc:
            raise TreeDigestError(f"cannot enumerate source tree: {directory}") from exc
        for entry in entries:
            relative = entry.relative_to(root).as_posix()
            if entry.name.casefold() == ".git":
                raise TreeDigestError("source snapshots must not expose .git metadata")
            if _is_indirection(entry):
                raise TreeDigestError(
                    f"source snapshots must not contain links or reparse points: {relative}"
                )
            try:
                info = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise TreeDigestError(f"cannot stat source entry: {relative}") from exc
            encoded = relative.encode("utf-8", errors="surrogatepass")
            if stat.S_ISDIR(info.st_mode):
                digest.update(b"D\0" + encoded + b"\0")
                visit(entry)
                continue
            if not stat.S_ISREG(info.st_mode):
                raise TreeDigestError(
                    f"source snapshots may contain only files and directories: {relative}"
                )
            file_count += 1
            byte_count += info.st_size
            if file_count > MAX_TREE_FILES or byte_count > MAX_TREE_BYTES:
                raise TreeDigestError("source snapshot exceeds the verification tree limit")
            content_digest = sha256_file(entry)
            after = entry.stat(follow_symlinks=False)
            if (info.st_size, info.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise TreeDigestError(f"source changed while it was being hashed: {relative}")
            digest.update(
                b"F\0"
                + encoded
                + b"\0"
                + str(info.st_size).encode("ascii")
                + b"\0"
                + bytes.fromhex(content_digest)
            )

    visit(root)
    return digest.hexdigest()


def _default_environment() -> dict[str, str]:
    return {
        "platform": platform.platform(),
        "python": platform.python_version(),
    }


def new_envelope(
    *,
    producer: str,
    role: str,
    target_root: str,
    target_revision: str,
    criterion: str,
    status: str,
    started_at: datetime,
    ended_at: datetime,
    command_argv: Sequence[str] | None = None,
    command_cwd: str | None = None,
    exit_code: int | None = None,
    source: Mapping[str, object] | None = None,
    run_id: str | None = None,
    task_id: str | None = None,
    attempt_id: str | None = None,
    tree_digest: str | None = None,
    environment: Mapping[str, object] | None = None,
    isolation: Mapping[str, object] | None = None,
    artifacts: Sequence[Mapping[str, object]] = (),
    limitations: Sequence[str] = (),
    evidence_id: str | None = None,
) -> dict[str, object]:
    command: dict[str, object] | None = None
    if command_argv is not None:
        command = {
            "argv": list(command_argv),
            "cwd": command_cwd or target_root,
            "exit_code": exit_code,
        }
    envelope: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "evidence_id": evidence_id or f"ev_{uuid.uuid4().hex}",
        "producer": {"name": producer, "role": role},
        "context": {
            "run_id": run_id,
            "task_id": task_id,
            "attempt_id": attempt_id,
        },
        "target": {
            "root": target_root,
            "revision": target_revision,
            "tree_digest": tree_digest,
        },
        "criterion": criterion,
        "status": status,
        "started_at": format_timestamp(started_at),
        "ended_at": format_timestamp(ended_at),
        "command": command,
        "source": dict(source) if source is not None else None,
        "environment": dict(environment) if environment is not None else _default_environment(),
        "isolation": dict(isolation or {}),
        "artifacts": [dict(artifact) for artifact in artifacts],
        "limitations": list(limitations),
    }
    validate_envelope(envelope)
    return envelope


def _require_mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise EnvelopeValidationError(f"{field} must be an object")
    return value


def _require_nonempty_string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EnvelopeValidationError(f"{field} must be a non-empty string")
    return value


def _reject_sensitive_keys(value: object, path: str = "environment") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            normalized = str(key).lower().replace("-", "_")
            if (
                normalized == "tokens"
                and path in {"source.reservation", "source.actual_usage"}
                and isinstance(child, int)
                and not isinstance(child, bool)
                and child >= 0
            ):
                continue
            if any(fragment in normalized for fragment in SENSITIVE_KEY_FRAGMENTS):
                raise EnvelopeValidationError(
                    f"{path}.{key} looks secret-bearing; evidence must not contain credentials"
                )
            _reject_sensitive_keys(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_sensitive_keys(child, f"{path}[{index}]")


def _reject_sensitive_argv(argv: Sequence[str]) -> None:
    for index, item in enumerate(argv):
        if SENSITIVE_ARG_RE.search(item) or URI_CREDENTIAL_RE.search(item):
            raise EnvelopeValidationError(
                f"command.argv[{index}] looks credential-bearing; record a redacted command"
            )


def validate_envelope(envelope: Mapping[str, object]) -> None:
    unknown = set(envelope) - TOP_LEVEL_FIELDS
    missing = TOP_LEVEL_FIELDS - set(envelope)
    if unknown:
        raise EnvelopeValidationError(f"unknown evidence fields: {sorted(unknown)}")
    if missing:
        raise EnvelopeValidationError(f"missing evidence fields: {sorted(missing)}")
    if envelope["schema_version"] != SCHEMA_VERSION:
        raise EnvelopeValidationError(
            f"unsupported evidence schema_version: {envelope['schema_version']!r}"
        )

    evidence_id = _require_nonempty_string(envelope["evidence_id"], "evidence_id")
    if not EVIDENCE_ID_RE.fullmatch(evidence_id):
        raise EnvelopeValidationError("evidence_id must match ev_<32 lowercase hex characters>")

    producer = _require_mapping(envelope["producer"], "producer")
    if set(producer) != {"name", "role"}:
        raise EnvelopeValidationError("producer must contain exactly name and role")
    _require_nonempty_string(producer["name"], "producer.name")
    _require_nonempty_string(producer["role"], "producer.role")

    context = _require_mapping(envelope["context"], "context")
    if set(context) != {"run_id", "task_id", "attempt_id"}:
        raise EnvelopeValidationError("context must contain exactly run_id, task_id, and attempt_id")
    for field, value in context.items():
        if value is not None and (
            not isinstance(value, str) or not CONTEXT_ID_RE.fullmatch(value)
        ):
            raise EnvelopeValidationError(f"context.{field} has an invalid identifier")

    target = _require_mapping(envelope["target"], "target")
    if set(target) != {"root", "revision", "tree_digest"}:
        raise EnvelopeValidationError("target must contain exactly root, revision, and tree_digest")
    _require_nonempty_string(target["root"], "target.root")
    _require_nonempty_string(target["revision"], "target.revision")
    if target["tree_digest"] is not None and (
        not isinstance(target["tree_digest"], str)
        or not SHA256_RE.fullmatch(target["tree_digest"])
    ):
        raise EnvelopeValidationError("target.tree_digest must be a lowercase SHA-256 digest")

    _require_nonempty_string(envelope["criterion"], "criterion")
    if envelope["status"] not in STATUSES:
        raise EnvelopeValidationError(f"unknown evidence status: {envelope['status']!r}")
    started = parse_timestamp(envelope["started_at"], "started_at")
    ended = parse_timestamp(envelope["ended_at"], "ended_at")
    if ended < started:
        raise EnvelopeValidationError("ended_at cannot precede started_at")

    command = envelope["command"]
    if command is not None:
        command_map = _require_mapping(command, "command")
        if set(command_map) != {"argv", "cwd", "exit_code"}:
            raise EnvelopeValidationError("command must contain exactly argv, cwd, and exit_code")
        argv = command_map["argv"]
        if (
            not isinstance(argv, list)
            or not argv
            or not all(isinstance(item, str) and item for item in argv)
        ):
            raise EnvelopeValidationError("command.argv must be a non-empty array of strings")
        _reject_sensitive_argv(argv)
        _require_nonempty_string(command_map["cwd"], "command.cwd")
        exit_code = command_map["exit_code"]
        if exit_code is not None and (not isinstance(exit_code, int) or isinstance(exit_code, bool)):
            raise EnvelopeValidationError("command.exit_code must be an integer or null")

    source = envelope["source"]
    if source is not None:
        _require_mapping(source, "source")
        _reject_sensitive_keys(source, "source")

    environment = _require_mapping(envelope["environment"], "environment")
    isolation = _require_mapping(envelope["isolation"], "isolation")
    _reject_sensitive_keys(environment)
    _reject_sensitive_keys(isolation, "isolation")

    artifacts = envelope["artifacts"]
    if not isinstance(artifacts, list):
        raise EnvelopeValidationError("artifacts must be an array")
    for index, artifact in enumerate(artifacts):
        item = _require_mapping(artifact, f"artifacts[{index}]")
        if set(item) != {"path", "sha256", "size"}:
            raise EnvelopeValidationError(
                f"artifacts[{index}] must contain exactly path, sha256, and size"
            )
        _require_nonempty_string(item["path"], f"artifacts[{index}].path")
        if not isinstance(item["sha256"], str) or not SHA256_RE.fullmatch(item["sha256"]):
            raise EnvelopeValidationError(f"artifacts[{index}].sha256 is invalid")
        if not isinstance(item["size"], int) or isinstance(item["size"], bool) or item["size"] < 0:
            raise EnvelopeValidationError(
                f"artifacts[{index}].size must be a non-negative integer"
            )

    limitations = envelope["limitations"]
    if not isinstance(limitations, list) or not all(
        isinstance(item, str) and item.strip() for item in limitations
    ):
        raise EnvelopeValidationError("limitations must be an array of non-empty strings")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="validate one evidence JSON file")
    validate.add_argument("path", type=Path)
    digest = subparsers.add_parser("digest", help="print a file's SHA-256 digest")
    digest.add_argument("path", type=Path)
    tree = subparsers.add_parser("tree-digest", help="hash a link-free source snapshot")
    tree.add_argument("path", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "digest":
            print(sha256_file(args.path))
            return 0
        if args.command == "tree-digest":
            print(tree_digest(args.path))
            return 0
        data = json.loads(
            args.path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_json_pairs,
        )
        if not isinstance(data, dict):
            raise EnvelopeValidationError("evidence document must be a JSON object")
        validate_envelope(data)
    except (OSError, json.JSONDecodeError, EnvelopeValidationError, ValueError) as exc:
        print(f"invalid evidence: {exc}", file=sys.stderr)
        return 1
    print(f"Valid evidence envelope: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
