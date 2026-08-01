#!/usr/bin/env python3
"""Validate evidence-bound operational knowledge update packets from the plugin bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence


SCHEMA_VERSION = 1
TOP_LEVEL_FIELDS = {
    "schema_version",
    "update_id",
    "created_at",
    "target",
    "trigger",
    "discovery",
    "evidence",
    "dispositions",
    "recommendation",
    "limitations",
}
TRIGGER_KINDS = {
    "incident",
    "alert_added",
    "alert_changed",
    "service_added",
    "service_changed",
    "drill",
    "audit",
    "manual",
}
TRIGGER_STATES = {
    "active",
    "resolved",
    "proposed",
    "approved",
    "completed",
    "not_applicable",
}
TRIGGER_STATES_BY_KIND = {
    "incident": {"active", "resolved", "not_applicable"},
    "alert_added": {"proposed", "approved", "not_applicable"},
    "alert_changed": {"proposed", "approved", "not_applicable"},
    "service_added": {"proposed", "approved", "not_applicable"},
    "service_changed": {"proposed", "approved", "not_applicable"},
    "drill": {"completed", "not_applicable"},
    "audit": {"completed", "not_applicable"},
    "manual": {"proposed", "approved", "completed", "not_applicable"},
}
PREPARATION_ALLOWED_STATES = {"resolved", "approved", "completed"}
REQUIRED_LIFECYCLE_EVIDENCE = {
    ("incident", "resolved"): {"incident"},
    ("drill", "completed"): {"execution_record"},
}
TRUST_LEVELS = {"trusted", "untrusted"}
EVIDENCE_LABELS = {"verified", "sourced", "unverified"}
EVIDENCE_KINDS = {
    "repository",
    "incident",
    "alert",
    "dashboard",
    "ticket",
    "execution_record",
    "approval",
    "human_record",
    "other",
}
ARTIFACT_KINDS = {
    "runbook",
    "postmortem",
    "service_card",
    "alert_card",
    "knowledge_index",
    "observability",
    "automation",
    "code",
    "accepted_risk",
}
DOCUMENTATION_ARTIFACTS = {
    "runbook",
    "postmortem",
    "service_card",
    "alert_card",
    "knowledge_index",
}
DOCUMENTATION_EXTENSIONS = {".md", ".mdx", ".rst", ".adoc"}
MAX_PREPARED_ARTIFACT_BYTES = 4 * 1024 * 1024
DISPOSITION_ACTIONS = {"create", "update", "link", "handoff", "none"}
DISPOSITION_STATUSES = {
    "prepared",
    "proposed",
    "blocked",
    "duplicate",
    "not_applicable",
}
URGENCIES = {"immediate", "next", "backlog", "none"}
UPDATE_ID_RE = re.compile(r"^ku_[a-z0-9][a-z0-9._-]{2,95}$")
EVIDENCE_ID_RE = re.compile(r"^e[1-9][0-9]*$")
CONTENT_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
GIT_REVISION_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
RFC3339_UTC_TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
)
TYPED_REDACTION_RE = re.compile(r"\[REDACTED:[a-z0-9][a-z0-9._-]{0,63}\]")
TYPED_REDACTION_SENTINEL = "__TYPED_REDACTION__"
TYPED_REDACTION_BOUNDARY = r"(?=$|[\s.,;:!?)}\]`>])"
URI_CREDENTIAL_RE = re.compile(
    rf"(?i)\b[A-Za-z][A-Za-z0-9+.-]*://[^/@\s]+:"
    rf"(?!{re.escape(TYPED_REDACTION_SENTINEL)}@)[^/@\s]+@"
)
CREDENTIAL_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(?:api[-_]?key|authorization|cookie|credential|password|secret|token)"
    r"\b[\"']?\s*[:=]\s*"
    rf"(?![\"']?(?:bearer[ \t]+)?{re.escape(TYPED_REDACTION_SENTINEL)}"
    rf"[\"']?{TYPED_REDACTION_BOUNDARY})\S+"
)
NAMED_CREDENTIAL_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(?:aws_secret_access_key|aws_session_token|azure_client_secret|google_api_key|"
    r"github_token|gh_token|npm_token|pypi_api_token|client_secret|access_token|"
    r"refresh_token|private_key)"
    r"\b[\"']?\s*[:=]\s*"
    rf"(?![\"']?{re.escape(TYPED_REDACTION_SENTINEL)}[\"']?"
    rf"{TYPED_REDACTION_BOUNDARY})\S+"
)
STRUCTURED_CREDENTIAL_RES = (
    re.compile(r"(?i)-----BEGIN (?:[A-Z0-9][A-Z0-9 -]* )?PRIVATE KEY-----"),
    re.compile(r"(?i)-----BEGIN PGP PRIVATE KEY BLOCK-----"),
    re.compile(
        rf"(?i)\bbearer[ \t]+(?!{re.escape(TYPED_REDACTION_SENTINEL)}"
        rf"{TYPED_REDACTION_BOUNDARY})[A-Za-z0-9._~+/=-]{{16,}}"
    ),
    re.compile(
        r"(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\."
        r"[A-Za-z0-9_-]{8,}(?![A-Za-z0-9_-])"
    ),
    re.compile(
        r"(?<![A-Za-z0-9_])(?:gh[pousr]_[A-Za-z0-9]{20,255}|"
        r"github_pat_[A-Za-z0-9_]{20,255})(?![A-Za-z0-9_])"
    ),
    re.compile(r"(?<![A-Z0-9])(?:AKIA|ASIA)[A-Z0-9]{16}(?![A-Z0-9])"),
    re.compile(r"(?<![A-Za-z0-9])xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"(?<![A-Za-z0-9_-])AIza[0-9A-Za-z_-]{35}(?![A-Za-z0-9_-])"),
    re.compile(r"(?<![A-Za-z0-9_])sk_(?:live|test)_[0-9A-Za-z]{16,}"),
)
SAFE_GIT_WORKTREE_CONFIG = (
    "-c",
    "core.fsmonitor=false",
    "-c",
    "core.untrackedCache=false",
    "-c",
    "filter.unspecified.clean=",
    "-c",
    "filter.unspecified.process=",
    "-c",
    "filter.unspecified.required=false",
    "-c",
    "filter.unset.clean=",
    "-c",
    "filter.unset.process=",
    "-c",
    "filter.unset.required=false",
)


class KnowledgeUpdateValidationError(ValueError):
    """Raised when a knowledge update violates the v1 contract."""


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise KnowledgeUpdateValidationError(f"{field} must be an object")
    return value


def _exact_fields(value: Mapping[str, object], fields: set[str], name: str) -> None:
    unknown = set(value) - fields
    missing = fields - set(value)
    if unknown:
        raise KnowledgeUpdateValidationError(f"unknown {name} fields: {sorted(unknown)}")
    if missing:
        raise KnowledgeUpdateValidationError(f"missing {name} fields: {sorted(missing)}")


def _string(value: object, field: str, *, maximum: int = 4096) -> str:
    if not isinstance(value, str) or not value.strip():
        raise KnowledgeUpdateValidationError(f"{field} must be a non-empty string")
    if len(value) > maximum:
        raise KnowledgeUpdateValidationError(f"{field} exceeds {maximum} characters")
    return value


def _nullable_string(value: object, field: str, *, maximum: int = 4096) -> str | None:
    if value is None:
        return None
    return _string(value, field, maximum=maximum)


def _string_list(value: object, field: str, *, nonempty: bool = False) -> list[str]:
    if not isinstance(value, list) or not all(
        isinstance(item, str) and item.strip() for item in value
    ):
        raise KnowledgeUpdateValidationError(f"{field} must be an array of non-empty strings")
    if nonempty and not value:
        raise KnowledgeUpdateValidationError(f"{field} must contain at least one item")
    if len(set(value)) != len(value):
        raise KnowledgeUpdateValidationError(f"{field} must not contain duplicates")
    return value


def _timestamp(value: object, field: str) -> str:
    rendered = _string(value, field, maximum=64)
    if not RFC3339_UTC_TIMESTAMP_RE.fullmatch(rendered):
        raise KnowledgeUpdateValidationError(f"{field} must be an RFC3339 UTC timestamp ending in Z")
    try:
        datetime.fromisoformat(rendered[:-1] + "+00:00")
    except ValueError as exc:
        raise KnowledgeUpdateValidationError(f"{field} is not a valid timestamp") from exc
    return rendered


def _enum(value: object, allowed: set[str], field: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise KnowledgeUpdateValidationError(f"{field} must be one of {sorted(allowed)}")
    return value


def _reject_sensitive_values(value: object, path: str = "packet") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            _reject_sensitive_values(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_sensitive_values(child, f"{path}[{index}]")
    elif isinstance(value, str) and _contains_sensitive_text(value):
        raise KnowledgeUpdateValidationError(
            f"{path} looks credential-bearing; use a typed [REDACTED:<kind>] marker"
        )


def _contains_sensitive_text(value: str) -> bool:
    masked = TYPED_REDACTION_RE.sub(TYPED_REDACTION_SENTINEL, value)
    return bool(
        URI_CREDENTIAL_RE.search(masked)
        or CREDENTIAL_ASSIGNMENT_RE.search(masked)
        or NAMED_CREDENTIAL_ASSIGNMENT_RE.search(masked)
        or any(pattern.search(masked) for pattern in STRUCTURED_CREDENTIAL_RES)
    )


def _safe_relative_path(value: object, field: str) -> str:
    rendered = _string(value, field, maximum=512)
    candidate = PurePosixPath(rendered)
    if (
        rendered != rendered.strip()
        or any(ord(character) < 32 for character in rendered)
        or rendered.startswith("/")
        or "\\" in rendered
        or "://" in rendered
        or (candidate.parts and candidate.parts[0].endswith(":"))
        or any(part in {"", ".", ".."} for part in candidate.parts)
        or rendered != candidate.as_posix()
    ):
        raise KnowledgeUpdateValidationError(
            f"{field} must be a normalized repository-relative POSIX path"
        )
    return rendered


def _is_link_or_reparse(path: Path) -> bool:
    try:
        attributes = path.lstat()
    except OSError as exc:
        raise KnowledgeUpdateValidationError(f"cannot inspect prepared artifact path {path}: {exc}") from exc
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return stat.S_ISLNK(attributes.st_mode) or bool(
        getattr(attributes, "st_file_attributes", 0) & reparse_flag
    )


def _verify_prepared_artifact(target_root: Path, relative: str, expected_sha256: str) -> bytes:
    supplied_root = target_root.absolute()
    if not supplied_root.exists() or not supplied_root.is_dir():
        raise KnowledgeUpdateValidationError("target_root must be an existing directory")
    if _is_link_or_reparse(supplied_root):
        raise KnowledgeUpdateValidationError("target_root must not be a link/reparse point")
    try:
        root = supplied_root.resolve(strict=True)
    except OSError as exc:
        raise KnowledgeUpdateValidationError(f"target_root cannot be resolved: {exc}") from exc
    if not root.is_dir() or _is_link_or_reparse(root):
        raise KnowledgeUpdateValidationError("target_root must be an ordinary directory")

    current = root
    parts = PurePosixPath(relative).parts
    for index, part in enumerate(parts):
        current = current / part
        if not current.exists() and not current.is_symlink():
            raise KnowledgeUpdateValidationError(
                f"prepared artifact does not exist under target_root: {relative}"
            )
        if _is_link_or_reparse(current):
            raise KnowledgeUpdateValidationError(
                f"prepared artifact path traverses a link/reparse point: {relative}"
            )
        if index < len(parts) - 1 and not current.is_dir():
            raise KnowledgeUpdateValidationError(
                f"prepared artifact parent is not a directory: {relative}"
            )
    if not current.is_file():
        raise KnowledgeUpdateValidationError(
            f"prepared artifact is not an ordinary file: {relative}"
        )
    metadata = current.stat()
    if metadata.st_nlink != 1:
        raise KnowledgeUpdateValidationError(
            f"prepared artifact must not be hard-linked: {relative}"
        )
    if metadata.st_size > MAX_PREPARED_ARTIFACT_BYTES:
        raise KnowledgeUpdateValidationError(
            f"prepared artifact exceeds {MAX_PREPARED_ARTIFACT_BYTES} bytes: {relative}"
        )

    digest = hashlib.sha256()
    content = bytearray()
    bytes_read = 0
    try:
        with current.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                bytes_read += len(chunk)
                if bytes_read > MAX_PREPARED_ARTIFACT_BYTES:
                    raise KnowledgeUpdateValidationError(
                        f"prepared artifact exceeds {MAX_PREPARED_ARTIFACT_BYTES} bytes: {relative}"
                    )
                digest.update(chunk)
                content.extend(chunk)
    except OSError as exc:
        raise KnowledgeUpdateValidationError(
            f"cannot read prepared artifact {relative}: {exc}"
        ) from exc
    actual_sha256 = digest.hexdigest()
    if actual_sha256 != expected_sha256:
        raise KnowledgeUpdateValidationError(
            f"prepared artifact digest mismatch for {relative}"
        )
    try:
        rendered = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise KnowledgeUpdateValidationError(
            f"prepared documentation artifact must be UTF-8: {relative}"
        ) from exc
    if _contains_sensitive_text(rendered):
        raise KnowledgeUpdateValidationError(
            f"prepared artifact looks credential-bearing; use typed [REDACTED:<kind>] markers: {relative}"
        )
    return bytes(content)


def _git_environment() -> dict[str, str]:
    environment = dict(os.environ)
    for name in tuple(environment):
        if name.startswith(("GIT_", "SSH_")):
            environment.pop(name)
    environment.update(
        {
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_LITERAL_PATHSPECS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "LC_ALL": "C",
        }
    )
    return environment


def _local_git_command(
    root: Path,
    args: Sequence[str],
    *,
    input_data: bytes | None = None,
) -> subprocess.CompletedProcess[bytes]:
    input_options = (
        {"stdin": subprocess.DEVNULL}
        if input_data is None
        else {"input": input_data}
    )
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=30,
            check=False,
            env=_git_environment(),
            **input_options,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise KnowledgeUpdateValidationError(
            f"cannot inspect prepared artifact base with local Git: {exc}"
        ) from exc


def _run_local_git(
    root: Path,
    args: Sequence[str],
    *,
    input_data: bytes | None = None,
) -> bytes:
    completed = _local_git_command(root, args, input_data=input_data)
    if completed.returncode != 0:
        raise KnowledgeUpdateValidationError(
            f"local Git inspection failed for prepared artifact ({' '.join(args[:2])})"
        )
    return completed.stdout


def _git_base_blob(root: Path, revision: str, relative: str) -> tuple[bytes, str] | None:
    tree_entry = _run_local_git(
        root,
        ["ls-tree", "-z", "--full-tree", revision, "--", relative],
    )
    if not tree_entry:
        return None
    records = tree_entry.split(b"\0")
    if len(records) != 2 or records[1] != b"" or b"\t" not in records[0]:
        raise KnowledgeUpdateValidationError(
            f"cannot determine exact base artifact entry: {relative}"
        )
    metadata, observed_path = records[0].split(b"\t", 1)
    fields = metadata.split(b" ")
    if len(fields) != 3 or observed_path != os.fsencode(relative):
        raise KnowledgeUpdateValidationError(
            f"cannot determine exact base artifact entry: {relative}"
        )
    object_mode, object_type, object_name = fields
    if object_type != b"blob" or object_mode not in {b"100644", b"100755"}:
        raise KnowledgeUpdateValidationError(
            f"base artifact is not a regular Git blob: {relative}"
        )
    object_id = object_name.decode("ascii", errors="strict")
    size_bytes = _run_local_git(root, ["cat-file", "-s", object_id])
    try:
        size = int((size_bytes or b"").strip())
    except ValueError as exc:
        raise KnowledgeUpdateValidationError(
            f"cannot determine base artifact size: {relative}"
        ) from exc
    if size > MAX_PREPARED_ARTIFACT_BYTES:
        raise KnowledgeUpdateValidationError(
            f"base artifact exceeds {MAX_PREPARED_ARTIFACT_BYTES} bytes: {relative}"
        )
    content = _run_local_git(root, ["cat-file", "blob", object_id])
    if content is None or len(content) != size:
        raise KnowledgeUpdateValidationError(
            f"base artifact byte count changed during inspection: {relative}"
        )
    return content, object_id


def _verified_git_root(target_root: Path, target_revision: str) -> Path:
    supplied_root = target_root.absolute()
    if not supplied_root.exists() or not supplied_root.is_dir():
        raise KnowledgeUpdateValidationError("target_root must be an existing directory")
    if _is_link_or_reparse(supplied_root):
        raise KnowledgeUpdateValidationError("target_root must not be a link/reparse point")
    try:
        root = supplied_root.resolve(strict=True)
    except OSError as exc:
        raise KnowledgeUpdateValidationError(f"target_root cannot be resolved: {exc}") from exc
    if not root.is_dir() or _is_link_or_reparse(root):
        raise KnowledgeUpdateValidationError("target_root must be an ordinary directory")

    top_level = _run_local_git(root, ["rev-parse", "--show-toplevel"])
    try:
        observed_root = Path(top_level.decode("utf-8", errors="strict").strip()).resolve(
            strict=True
        )
    except (OSError, UnicodeError) as exc:
        raise KnowledgeUpdateValidationError("cannot resolve the target checkout's Git root") from exc
    if observed_root != root:
        raise KnowledgeUpdateValidationError("target_root must be the exact Git worktree root")
    observed_revision = _run_local_git(
        root,
        ["rev-parse", "--verify", "HEAD"],
    ).decode("ascii", errors="strict").strip()
    if observed_revision != target_revision:
        raise KnowledgeUpdateValidationError(
            "target_root HEAD does not match target.revision"
        )
    return root


def _verify_duplicate_artifact(
    target_root: Path,
    target_revision: str,
    relative: str,
) -> None:
    root = _verified_git_root(target_root, target_revision)
    if _git_base_blob(root, target_revision, relative) is None:
        raise KnowledgeUpdateValidationError(
            f"documentation duplicate_of does not exist at target.revision: {relative}"
        )


def _verify_git_reviewable_change(
    root: Path,
    target_revision: str,
    relative: str,
    action: str,
    base_object_id: str | None,
    artifact_content: bytes,
) -> None:
    """Require the working artifact to appear in Git's ordinary review surface."""
    attribute = _run_local_git(root, ["check-attr", "-z", "filter", "--", relative])
    fields = (attribute or b"").split(b"\0")
    if len(fields) != 4 or fields[1] != b"filter" or fields[3] != b"":
        raise KnowledgeUpdateValidationError(
            f"cannot determine Git filter attributes for prepared artifact: {relative}"
        )
    if fields[2] not in {b"unspecified", b"unset"}:
        raise KnowledgeUpdateValidationError(
            f"prepared artifact uses an external clean filter and cannot be inspected safely: {relative}"
        )

    artifact_object_id = _run_local_git(
        root,
        [
            "--no-pager",
            *SAFE_GIT_WORKTREE_CONFIG,
            "hash-object",
            f"--path={relative}",
            "--stdin",
        ],
        input_data=artifact_content,
    ).decode("ascii", errors="strict").strip()
    if not GIT_REVISION_RE.fullmatch(artifact_object_id):
        raise KnowledgeUpdateValidationError(
            f"local Git returned an invalid object ID for prepared artifact: {relative}"
        )
    if base_object_id is not None and artifact_object_id == base_object_id:
        raise KnowledgeUpdateValidationError(
            f"prepared artifact has no Git-reviewable change: {relative}"
        )

    raw_diff = _run_local_git(
        root,
        [
            "--no-pager",
            *SAFE_GIT_WORKTREE_CONFIG,
            "diff",
            "--raw",
            "-z",
            "--abbrev=64",
            "--no-renames",
            "--no-ext-diff",
            "--no-textconv",
            target_revision,
            "--",
            relative,
        ],
    )
    if raw_diff:
        fields = raw_diff.split(b"\0")
        if len(fields) != 3 or fields[2] != b"" or fields[1] != os.fsencode(relative):
            raise KnowledgeUpdateValidationError(
                f"local Git returned a malformed review record for prepared artifact: {relative}"
            )
        metadata = fields[0]
        if not metadata.startswith(b":"):
            raise KnowledgeUpdateValidationError(
                f"local Git returned a malformed review record for prepared artifact: {relative}"
            )
        parts = metadata[1:].split(b" ")
        if len(parts) != 5:
            raise KnowledgeUpdateValidationError(
                f"local Git returned a malformed review record for prepared artifact: {relative}"
            )
        old_mode, new_mode, old_object, new_object, change_status = parts
        try:
            old_object_id = old_object.decode("ascii", errors="strict")
            new_object_id = new_object.decode("ascii", errors="strict")
        except UnicodeDecodeError as exc:
            raise KnowledgeUpdateValidationError(
                f"local Git returned a malformed review record for prepared artifact: {relative}"
            ) from exc
        if not GIT_REVISION_RE.fullmatch(old_object_id) or not GIT_REVISION_RE.fullmatch(
            new_object_id
        ):
            raise KnowledgeUpdateValidationError(
                f"local Git returned a malformed review record for prepared artifact: {relative}"
            )
        regular_modes = {b"100644", b"100755"}
        expected_status = b"A" if action == "create" else b"M"
        expected_old_modes = {b"000000"} if action == "create" else regular_modes
        expected_old_object = "0" * len(old_object_id) if action == "create" else base_object_id
        new_object_is_unknown = new_object_id == "0" * len(new_object_id)
        if (
            change_status != expected_status
            or old_mode not in expected_old_modes
            or new_mode not in regular_modes
            or old_object_id != expected_old_object
            or (not new_object_is_unknown and new_object_id != artifact_object_id)
        ):
            expectation = "a tracked addition" if action == "create" else "a tracked modification"
            raise KnowledgeUpdateValidationError(
                f"prepared {action} is not exposed as {expectation}: {relative}"
            )
        return

    if action == "create":
        untracked = _run_local_git(
            root,
            [
                "--no-pager",
                *SAFE_GIT_WORKTREE_CONFIG,
                "ls-files",
                "--others",
                "--exclude-standard",
                "-z",
                "--",
                relative,
            ],
        )
        if untracked == os.fsencode(relative) + b"\0":
            return
        if untracked:
            raise KnowledgeUpdateValidationError(
                f"local Git returned an unexpected review path for prepared artifact: {relative}"
            )

    raise KnowledgeUpdateValidationError(
        f"prepared artifact has no Git-reviewable change: {relative}"
    )


def _verify_reviewable_diff(
    target_root: Path,
    target_revision: str,
    relative: str,
    action: str,
    base_sha256: object,
    artifact_sha256: str,
    artifact_content: bytes,
) -> None:
    root = _verified_git_root(target_root, target_revision)

    base_entry = _git_base_blob(root, target_revision, relative)
    if action == "create":
        if base_sha256 is not None:
            raise KnowledgeUpdateValidationError(
                "a prepared create disposition requires base_sha256 null"
            )
        if base_entry is not None:
            raise KnowledgeUpdateValidationError(
                f"prepared create path already exists at target.revision: {relative}"
            )
        _verify_git_reviewable_change(
            root,
            target_revision,
            relative,
            action,
            None,
            artifact_content,
        )
        return

    if base_entry is None:
        raise KnowledgeUpdateValidationError(
            f"prepared {action} path does not exist at target.revision: {relative}"
        )
    base_content, base_object_id = base_entry
    expected_base_sha256 = _string(base_sha256, "base_sha256", maximum=64)
    if not CONTENT_SHA256_RE.fullmatch(expected_base_sha256):
        raise KnowledgeUpdateValidationError("base_sha256 must be lowercase SHA-256")
    actual_base_sha256 = hashlib.sha256(base_content).hexdigest()
    if actual_base_sha256 != expected_base_sha256:
        raise KnowledgeUpdateValidationError(
            f"base artifact digest mismatch for {relative}"
        )
    if actual_base_sha256 == artifact_sha256:
        raise KnowledgeUpdateValidationError(
            f"prepared {action} has no reviewable byte change: {relative}"
        )
    _verify_git_reviewable_change(
        root,
        target_revision,
        relative,
        action,
        base_object_id,
        artifact_content,
    )


def _validate_evidence(value: object) -> dict[str, Mapping[str, object]]:
    if not isinstance(value, list) or not value:
        raise KnowledgeUpdateValidationError("evidence must contain at least one record")
    records: dict[str, Mapping[str, object]] = {}
    fields = {"id", "label", "kind", "locator", "revision", "trust"}
    for index, raw in enumerate(value):
        item = _mapping(raw, f"evidence[{index}]")
        _exact_fields(item, fields, f"evidence[{index}]")
        evidence_id = _string(item["id"], f"evidence[{index}].id", maximum=32)
        if not EVIDENCE_ID_RE.fullmatch(evidence_id):
            raise KnowledgeUpdateValidationError(
                f"evidence[{index}].id must match e<positive integer>"
            )
        if evidence_id in records:
            raise KnowledgeUpdateValidationError(f"duplicate evidence id: {evidence_id}")
        _enum(item["label"], EVIDENCE_LABELS, f"evidence[{index}].label")
        _enum(item["kind"], EVIDENCE_KINDS, f"evidence[{index}].kind")
        _string(item["locator"], f"evidence[{index}].locator", maximum=2048)
        _nullable_string(item["revision"], f"evidence[{index}].revision", maximum=256)
        _enum(item["trust"], TRUST_LEVELS, f"evidence[{index}].trust")
        records[evidence_id] = item
    return records


def _resolve_evidence_ids(
    value: object,
    field: str,
    evidence: Mapping[str, Mapping[str, object]],
) -> list[str]:
    ids = _string_list(value, field, nonempty=True)
    missing = sorted(set(ids) - set(evidence))
    if missing:
        raise KnowledgeUpdateValidationError(f"{field} references unknown evidence ids: {missing}")
    return ids


def _validate_dispositions(
    value: object,
    evidence: Mapping[str, Mapping[str, object]],
    *,
    trigger_state: str,
    target_revision: str,
    knowledge_roots: list[str],
    target_root: Path | None,
) -> None:
    if not isinstance(value, list) or not value:
        raise KnowledgeUpdateValidationError(
            "dispositions must contain at least one explicit outcome"
        )
    fields = {
        "artifact",
        "action",
        "status",
        "owner",
        "path",
        "duplicate_of",
        "base_sha256",
        "artifact_sha256",
        "reason",
        "evidence_ids",
    }
    for index, raw in enumerate(value):
        item = _mapping(raw, f"dispositions[{index}]")
        _exact_fields(item, fields, f"dispositions[{index}]")
        artifact = _enum(item["artifact"], ARTIFACT_KINDS, f"dispositions[{index}].artifact")
        action = _enum(item["action"], DISPOSITION_ACTIONS, f"dispositions[{index}].action")
        status = _enum(item["status"], DISPOSITION_STATUSES, f"dispositions[{index}].status")
        _string(item["owner"], f"dispositions[{index}].owner", maximum=256)
        _string(item["reason"], f"dispositions[{index}].reason", maximum=2000)
        disposition_evidence_ids = _resolve_evidence_ids(
            item["evidence_ids"], f"dispositions[{index}].evidence_ids", evidence
        )
        path = item["path"]
        if path is not None:
            path = _safe_relative_path(path, f"dispositions[{index}].path")
        duplicate_of = item["duplicate_of"]
        if duplicate_of is not None:
            duplicate_of = _string(
                duplicate_of,
                f"dispositions[{index}].duplicate_of",
                maximum=2048,
            )
        artifact_sha256 = item["artifact_sha256"]
        base_sha256 = item["base_sha256"]

        if status == "prepared":
            if artifact not in DOCUMENTATION_ARTIFACTS:
                raise KnowledgeUpdateValidationError(
                    f"non-documentation artifact {artifact!r} cannot be prepared by scribe"
                )
            if trigger_state not in PREPARATION_ALLOWED_STATES:
                raise KnowledgeUpdateValidationError(
                    f"trigger state {trigger_state!r} cannot mark dispositions prepared"
                )
            if action not in {"create", "update", "link"} or path is None:
                raise KnowledgeUpdateValidationError(
                    "a prepared disposition requires create/update/link and a repository path"
                )
            if PurePosixPath(path).suffix.lower() not in DOCUMENTATION_EXTENSIONS:
                raise KnowledgeUpdateValidationError(
                    f"dispositions[{index}].path must name a documentation file"
                )
            if not any(path.startswith(f"{root}/") for root in knowledge_roots):
                raise KnowledgeUpdateValidationError(
                    f"dispositions[{index}].path is outside target.knowledge_roots"
                )
            if not any(
                evidence[evidence_id]["revision"] == target_revision
                for evidence_id in disposition_evidence_ids
            ):
                raise KnowledgeUpdateValidationError(
                    f"dispositions[{index}] prepared change must reference evidence for "
                    "target.revision"
                )
            artifact_digest = _string(
                artifact_sha256,
                f"dispositions[{index}].artifact_sha256",
                maximum=64,
            )
            if not CONTENT_SHA256_RE.fullmatch(artifact_digest):
                raise KnowledgeUpdateValidationError(
                    f"dispositions[{index}].artifact_sha256 must be lowercase SHA-256"
                )
            if target_root is None:
                raise KnowledgeUpdateValidationError(
                    "prepared dispositions require target_root for artifact verification"
                )
            artifact_content = _verify_prepared_artifact(target_root, path, artifact_digest)
            _verify_reviewable_diff(
                target_root,
                target_revision,
                path,
                action,
                base_sha256,
                artifact_digest,
                artifact_content,
            )
            _verify_prepared_artifact(target_root, path, artifact_digest)
        if action == "none" and status not in {"duplicate", "not_applicable"}:
            raise KnowledgeUpdateValidationError(
                "a none disposition must be duplicate or not_applicable"
            )
        if action == "handoff" and status not in {"proposed", "blocked"}:
            raise KnowledgeUpdateValidationError(
                "a handoff disposition must be proposed or blocked"
            )
        if status in {"proposed", "blocked"} and (action != "handoff" or path is not None):
            raise KnowledgeUpdateValidationError(
                f"a {status} disposition requires a pathless handoff"
            )
        if status == "duplicate":
            if action != "none" or path is not None:
                raise KnowledgeUpdateValidationError(
                    "a duplicate disposition requires action none and a null path"
                )
            if duplicate_of is None:
                raise KnowledgeUpdateValidationError(
                    "a duplicate disposition requires duplicate_of"
                )
            matching_duplicate_evidence = [
                evidence[evidence_id]
                for evidence_id in disposition_evidence_ids
                if evidence[evidence_id]["locator"] == duplicate_of
                and evidence[evidence_id]["revision"] == target_revision
                and evidence[evidence_id]["trust"] == "trusted"
                and evidence[evidence_id]["label"] in {"verified", "sourced"}
            ]
            if not matching_duplicate_evidence:
                raise KnowledgeUpdateValidationError(
                    "duplicate_of requires matching trusted sourced/verified evidence bound to "
                    "target.revision"
                )
            if artifact in DOCUMENTATION_ARTIFACTS:
                duplicate_path = _safe_relative_path(
                    duplicate_of,
                    f"dispositions[{index}].duplicate_of",
                )
                if PurePosixPath(duplicate_path).suffix.lower() not in DOCUMENTATION_EXTENSIONS:
                    raise KnowledgeUpdateValidationError(
                        f"dispositions[{index}].duplicate_of must name a documentation file"
                    )
                if not any(
                    duplicate_path.startswith(f"{root}/") for root in knowledge_roots
                ):
                    raise KnowledgeUpdateValidationError(
                        f"dispositions[{index}].duplicate_of is outside target.knowledge_roots"
                    )
                if not any(
                    record["kind"] == "repository" for record in matching_duplicate_evidence
                ):
                    raise KnowledgeUpdateValidationError(
                        "documentation duplicate_of requires matching repository evidence"
                    )
                if target_root is None:
                    raise KnowledgeUpdateValidationError(
                        "documentation duplicate dispositions require target_root"
                    )
                _verify_duplicate_artifact(
                    target_root,
                    target_revision,
                    duplicate_path,
                )
        if status == "not_applicable" and (action != "none" or path is not None):
            raise KnowledgeUpdateValidationError(
                "a not_applicable disposition requires action none and a null path"
            )
        if status != "prepared" and (base_sha256 is not None or artifact_sha256 is not None):
            raise KnowledgeUpdateValidationError(
                f"dispositions[{index}] digests must be null unless status is prepared"
            )
        if status != "duplicate" and duplicate_of is not None:
            raise KnowledgeUpdateValidationError(
                f"dispositions[{index}].duplicate_of must be null unless status is duplicate"
            )


def validate_update(update: Mapping[str, object], *, target_root: Path | None = None) -> None:
    """Validate one operational knowledge update packet."""

    _exact_fields(update, TOP_LEVEL_FIELDS, "knowledge update")
    if type(update["schema_version"]) is not int or update["schema_version"] != SCHEMA_VERSION:
        raise KnowledgeUpdateValidationError(
            f"unsupported schema_version: {update['schema_version']!r}"
        )
    update_id = _string(update["update_id"], "update_id", maximum=99)
    if not UPDATE_ID_RE.fullmatch(update_id):
        raise KnowledgeUpdateValidationError(
            "update_id must match ku_<lowercase stable identifier>"
        )
    _timestamp(update["created_at"], "created_at")

    target = _mapping(update["target"], "target")
    _exact_fields(target, {"repository", "revision", "service", "knowledge_roots"}, "target")
    _string(target["repository"], "target.repository", maximum=512)
    target_revision = _string(target["revision"], "target.revision", maximum=256)
    if not GIT_REVISION_RE.fullmatch(target_revision):
        raise KnowledgeUpdateValidationError(
            "target.revision must be a full lowercase Git object ID"
        )
    _string(target["service"], "target.service", maximum=256)
    knowledge_roots = [
        _safe_relative_path(root, f"target.knowledge_roots[{index}]")
        for index, root in enumerate(
            _string_list(target["knowledge_roots"], "target.knowledge_roots", nonempty=True)
        )
    ]

    trigger = _mapping(update["trigger"], "trigger")
    _exact_fields(trigger, {"kind", "reference", "state", "trust"}, "trigger")
    trigger_kind = _enum(trigger["kind"], TRIGGER_KINDS, "trigger.kind")
    _string(trigger["reference"], "trigger.reference", maximum=512)
    trigger_state = _enum(trigger["state"], TRIGGER_STATES, "trigger.state")
    trigger_trust = _enum(trigger["trust"], TRUST_LEVELS, "trigger.trust")
    if trigger_state not in TRIGGER_STATES_BY_KIND[trigger_kind]:
        raise KnowledgeUpdateValidationError(
            f"trigger state {trigger_state!r} is invalid for kind {trigger_kind!r}"
        )

    evidence = _validate_evidence(update["evidence"])

    discovery = _mapping(update["discovery"], "discovery")
    _exact_fields(discovery, {"summary", "evidence_status", "evidence_ids"}, "discovery")
    _string(discovery["summary"], "discovery.summary", maximum=2000)
    claimed_label = _enum(
        discovery["evidence_status"], EVIDENCE_LABELS, "discovery.evidence_status"
    )
    discovery_ids = _resolve_evidence_ids(
        discovery["evidence_ids"], "discovery.evidence_ids", evidence
    )
    if not any(evidence[evidence_id]["revision"] == target_revision for evidence_id in discovery_ids):
        raise KnowledgeUpdateValidationError(
            "discovery must reference evidence bound to target.revision"
        )
    if trigger_state == "approved" and not any(
        evidence[evidence_id]["kind"] == "approval"
        and evidence[evidence_id]["trust"] == "trusted"
        and evidence[evidence_id]["label"] in {"verified", "sourced"}
        and evidence[evidence_id]["revision"] == target_revision
        for evidence_id in discovery_ids
    ):
        raise KnowledgeUpdateValidationError(
            "approved trigger requires a referenced trusted approval record bound to target.revision"
        )
    required_lifecycle_kinds = REQUIRED_LIFECYCLE_EVIDENCE.get(
        (trigger_kind, trigger_state)
    )
    if required_lifecycle_kinds and not any(
        evidence[evidence_id]["kind"] in required_lifecycle_kinds
        and evidence[evidence_id]["trust"] == "trusted"
        and evidence[evidence_id]["label"] in {"verified", "sourced"}
        for evidence_id in discovery_ids
    ):
        raise KnowledgeUpdateValidationError(
            f"{trigger_kind} trigger state {trigger_state!r} requires referenced trusted "
            f"evidence of kind {sorted(required_lifecycle_kinds)}"
        )
    if trigger_state in PREPARATION_ALLOWED_STATES:
        trusted_ids = [
            evidence_id
            for evidence_id in discovery_ids
            if evidence[evidence_id]["trust"] == "trusted"
            and evidence[evidence_id]["label"] in {"verified", "sourced"}
        ]
        if trigger_trust != "trusted" or not trusted_ids:
            raise KnowledgeUpdateValidationError(
                f"trigger state {trigger_state!r} requires trusted sourced/verified evidence"
            )
    label_rank = {"unverified": 0, "sourced": 1, "verified": 2}
    weakest = min(
        (str(evidence[evidence_id]["label"]) for evidence_id in discovery_ids),
        key=label_rank.__getitem__,
    )
    if claimed_label != weakest:
        raise KnowledgeUpdateValidationError(
            "discovery.evidence_status must equal the weakest referenced evidence label "
            f"({weakest})"
        )

    _validate_dispositions(
        update["dispositions"],
        evidence,
        trigger_state=trigger_state,
        target_revision=target_revision,
        knowledge_roots=knowledge_roots,
        target_root=target_root,
    )

    recommendation = _mapping(update["recommendation"], "recommendation")
    recommendation_fields = {
        "summary",
        "owner",
        "urgency",
        "change_tier",
        "requires_human_approval",
        "verification",
        "rollback",
    }
    _exact_fields(recommendation, recommendation_fields, "recommendation")
    _string(recommendation["summary"], "recommendation.summary", maximum=2000)
    _string(recommendation["owner"], "recommendation.owner", maximum=256)
    _enum(recommendation["urgency"], URGENCIES, "recommendation.urgency")
    tier = recommendation["change_tier"]
    if not isinstance(tier, int) or isinstance(tier, bool) or tier not in {0, 1, 2, 3}:
        raise KnowledgeUpdateValidationError("recommendation.change_tier must be 0, 1, 2, or 3")
    approval = recommendation["requires_human_approval"]
    if not isinstance(approval, bool):
        raise KnowledgeUpdateValidationError(
            "recommendation.requires_human_approval must be a boolean"
        )
    _string(recommendation["verification"], "recommendation.verification", maximum=2000)
    rollback = _nullable_string(
        recommendation["rollback"], "recommendation.rollback", maximum=2000
    )
    if tier in {2, 3} and (not approval or rollback is None):
        raise KnowledgeUpdateValidationError(
            "Tier 2/3 recommendations require human approval and a rollback/recovery statement"
        )

    _string_list(update["limitations"], "limitations")
    _reject_sensitive_values(update)


def canonical_json(value: Mapping[str, object]) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="knowledge update JSON file")
    parser.add_argument(
        "--target-root",
        type=Path,
        help=(
            "target checkout root; required when any disposition is prepared or names a "
            "documentation duplicate"
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        data = json.loads(args.path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise KnowledgeUpdateValidationError("knowledge update must be a JSON object")
        validate_update(data, target_root=args.target_root)
    except (OSError, json.JSONDecodeError, KnowledgeUpdateValidationError) as exc:
        print(f"invalid knowledge update: {exc}", file=sys.stderr)
        return 1
    print(f"Valid operational knowledge update: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
