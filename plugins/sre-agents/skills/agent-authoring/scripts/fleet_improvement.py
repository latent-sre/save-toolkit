#!/usr/bin/env python3
"""Validate bounded, Git-backed fleet-improvement records.

The JSON Schema carries the portable shape. This executable validator additionally enforces
cross-field lifecycle, cumulative budget, append-only history, external authority, safe-path, and
credential-rejection rules that JSON Schema cannot express reliably.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import stat
import subprocess
import sys
import threading
import time
import unicodedata
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Callable, Mapping, Sequence


SCHEMA_VERSION = 1
MAX_EVIDENCE_BYTES = 1024 * 1024
MAX_RECORD_BYTES = 1024 * 1024
MAX_ARTIFACT_PATHS = 64
MAX_SUBJECT_ENTRIES = 512
MAX_SUBJECT_FILE_BYTES = 4 * 1024 * 1024
MAX_SUBJECT_BYTES = 32 * 1024 * 1024
MAX_GIT_STDOUT_BYTES = 8 * 1024 * 1024
MAX_GIT_STDERR_BYTES = 64 * 1024
MAX_GIT_METADATA_BYTES = 1024 * 1024
MAX_GIT_INPUT_BYTES = 2 * 1024 * 1024
MAX_MERGE_TREE_ENTRIES = 20_000
MAX_CHANGED_PATHS = 4_096
MAX_GIT_PATH_BYTES = 4_096
MAX_GIT_COMPONENT_BYTES = 255
MAX_GIT_PATHSPEC_ARGV_BYTES = 16 * 1024
GIT_COMMAND_TIMEOUT_SECONDS = 30.0
GIT_COMMAND_CLEANUP_SECONDS = 5.0
SUBJECT_DIGEST_ALGORITHM = "sre-agents-git-artifact-selection-v1"
DEFAULT_BUDGET_CEILINGS = {
    "max_model_turns": 60,
    "max_evaluator_calls": 60,
    "max_tokens": 1_000_000,
    "max_wall_seconds": 14_400,
    "max_cost_usd": 100.0,
}
TOP_FIELDS = {
    "schema_version",
    "improvement_id",
    "created_at",
    "updated_at",
    "target",
    "owner",
    "related_improvement_id",
    "severity",
    "failure_fingerprint",
    "observations",
    "evidence_refs",
    "status",
    "success_criteria",
    "monitoring_plan",
    "budget",
    "attempts",
    "reviews",
    "merge",
    "monitoring",
    "rollback",
    "lesson",
    "disposition_reason",
    "limitations",
}
STATUSES = {
    "observed",
    "qualified",
    "candidate",
    "evaluated",
    "in_review",
    "merged",
    "monitoring",
    "closed",
    "duplicate",
    "not_reproducible",
    "not_actionable",
    "rejected",
    "blocked_pending_rescope",
    "rolled_back",
}
TERMINAL_STATUSES = {
    "closed",
    "duplicate",
    "not_reproducible",
    "not_actionable",
    "rejected",
    "blocked_pending_rescope",
    "rolled_back",
}
TRANSITIONS = {
    "observed": {"qualified", "duplicate", "not_reproducible", "not_actionable"},
    "qualified": {"candidate", "blocked_pending_rescope"},
    "candidate": {"evaluated", "blocked_pending_rescope"},
    "evaluated": {"candidate", "in_review", "rejected", "blocked_pending_rescope"},
    "in_review": {"candidate", "merged", "rejected"},
    "merged": {"monitoring", "rolled_back"},
    "monitoring": {"closed", "rolled_back"},
}
AUTHORITY_FOR_STATUS = {
    "qualified": {"triage", "human_or_protected_workflow"},
    "duplicate": {"triage", "human_or_protected_workflow"},
    "not_reproducible": {"triage", "human_or_protected_workflow"},
    "not_actionable": {"triage", "human_or_protected_workflow"},
    "candidate": {"author", "human_or_protected_workflow"},
    "evaluated": {"evaluator", "human_or_protected_workflow"},
    "in_review": {"reviewer", "human_or_protected_workflow"},
    "merged": {"human_or_protected_workflow"},
    "monitoring": {"evaluator", "human_or_protected_workflow"},
    "closed": {"human_or_protected_workflow"},
    "rejected": {"reviewer", "human_or_protected_workflow"},
    "blocked_pending_rescope": {
        "author",
        "reviewer",
        "human_or_protected_workflow",
    },
    "rolled_back": {"human_or_protected_workflow"},
}

TARGET_FIELDS = {"repository", "base_revision", "artifact_kind", "artifact_paths"}
OWNER_FIELDS = {"name", "kind", "agent_lane"}
OBSERVATION_FIELDS = {
    "event_id",
    "kind",
    "observed_at",
    "source",
    "trust",
    "summary",
    "evidence_ids",
}
SOURCE_FIELDS = {"kind", "locator", "revision", "sha256"}
EVIDENCE_REF_FIELDS = {"evidence_id", "kind", "locator", "sha256"}
BUDGET_FIELDS = {
    "origin",
    "max_attempts",
    "max_model_turns",
    "max_evaluator_calls",
    "max_tokens",
    "max_wall_seconds",
    "max_cost_usd",
}
ATTEMPT_FIELDS = {
    "attempt_id",
    "iteration",
    "parent_revision",
    "subject_revision",
    "subject_sha256",
    "change_summary",
    "author",
    "reservation",
    "actual_usage",
    "case_sets",
    "evaluation",
    "outcome",
    "stop_reason",
}
ATTEMPT_IDENTITY_FIELDS = ATTEMPT_FIELDS - {
    "actual_usage",
    "evaluation",
    "outcome",
    "stop_reason",
}
AUTHOR_FIELDS = {"name", "role"}
USAGE_FIELDS = {"model_turns", "evaluator_calls", "tokens", "wall_seconds", "cost_usd"}
CASE_SET_FIELDS = {"calibration", "regression", "shadow"}
VISIBLE_CASE_SET_FIELDS = {"sha256", "case_count"}
SHADOW_FIELDS = {"sha256", "case_count", "result", "evidence_id"}
EVALUATION_FIELDS = {
    "kind",
    "evaluator",
    "evidence_id",
    "locator",
    "sha256",
    "subject_revision",
    "evaluator_revision",
    "runner_sha256",
    "suite_sha256",
    "case_set_sha256",
    "requested_model",
    "observed_model",
    "reasoning_mode",
    "trial_count",
    "result",
    "safety_regression",
    "authority_regression",
}
REVIEW_FIELDS = {
    "attempt_id",
    "subject_revision",
    "reviewer",
    "verdict",
    "evidence_id",
    "locator",
    "evidence_sha256",
    "reviewed_at",
}
MERGE_FIELDS = {
    "pr_url",
    "subject_revision",
    "merge_revision",
    "merged_at",
    "merged_by",
}
MONITORING_PLAN_FIELDS = {"criterion_id", "criterion", "rollback_triggers"}
MONITORING_FIELDS = {
    "subject_revision",
    "criterion_id",
    "observed_by",
    "observed_at",
    "result",
    "evidence_ids",
}
ROLLBACK_FIELDS = {
    "subject_revision",
    "merge_revision",
    "rollback_revision",
    "rolled_back_at",
    "rolled_back_by",
    "trigger",
    "reason",
    "evidence_ids",
}
LESSON_FIELDS = {"status", "control_path", "reason"}
AUTHORITY_FIELDS = {"actor", "role", "subject_revision"}

ID_RE = re.compile(r"^f[ioa]_[a-z0-9][a-z0-9._-]{2,95}$")
FINGERPRINT_RE = re.compile(r"^ff_[0-9a-f]{64}$")
REVISION_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")
EVIDENCE_ID_RE = re.compile(r"^ev_[0-9a-f]{32}$")
MONITORING_ID_RE = re.compile(r"^fm_[a-z0-9][a-z0-9._-]{2,95}$")
SAFE_PATH_RE = re.compile(r"^[A-Za-z0-9._/-]+$")
RFC3339_UTC_TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
)
WINDOWS_RESERVED_COMPONENT_RE = re.compile(
    r"^(?:con|prn|aux|nul|clock\$|conin\$|conout\$|com[1-9\u00b9\u00b2\u00b3]|lpt[1-9\u00b9\u00b2\u00b3])(?:\..*)?$",
    re.IGNORECASE,
)
DANGEROUS_SYMLINK_NAMES = {
    ".gitmodules",
    ".gitattributes",
    ".gitignore",
    ".mailmap",
}
SUBJECT_TREE_LINE_RE = re.compile(
    rb"^(100644|100755) blob ([0-9a-f]{40}|[0-9a-f]{64}) +([0-9]+)\t(.+)$"
)
ALL_ROLLBACK_TRIGGERS = {
    "monitoring_fail",
    "monitoring_inconclusive",
    "security_finding",
    "authority_revoked",
    "merge_error",
    "manual_owner_decision",
}
MANDATORY_ROLLBACK_TRIGGERS = ALL_ROLLBACK_TRIGGERS - {"manual_owner_decision"}
REDACTION_RE = re.compile(r"\[REDACTED:[a-z0-9][a-z0-9._-]{0,63}\]")
REDACTION_SENTINEL = "__TYPED_REDACTION__"
REDACTION_BOUNDARY = r"(?=$|[\s.,;:!?)}\]`>])"
SENSITIVE_KEY_RE = re.compile(
    r"(?i)(?:^|[-_])(?:api[-_]?key|authorization|cookie|credential|password|secret|token)(?:$|[-_])"
)
URI_CREDENTIAL_RE = re.compile(
    rf"(?i)\b[A-Za-z][A-Za-z0-9+.-]*://[^/@\s]+:"
    rf"(?!{re.escape(REDACTION_SENTINEL)}@)[^/@\s]+@"
)
CREDENTIAL_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(?:api[-_]?key|authorization|cookie|credential|password|passwd|pwd|secret|token)"
    r"\b[\"']?\s*[:=]\s*"
    rf"(?![\"']?(?:bearer[ \t]+)?{re.escape(REDACTION_SENTINEL)}"
    rf"[\"']?{REDACTION_BOUNDARY})\S+"
)
NAMED_CREDENTIAL_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(?:aws_secret_access_key|aws_session_token|azure_client_secret|google_api_key|"
    r"github_token|gh_token|npm_token|pypi_api_token|client_secret|access_token|"
    r"refresh_token|private_key)"
    r"\b[\"']?\s*[:=]\s*"
    rf"(?![\"']?{re.escape(REDACTION_SENTINEL)}[\"']?{REDACTION_BOUNDARY})\S+"
)
CREDENTIAL_PATTERNS = (
    URI_CREDENTIAL_RE,
    CREDENTIAL_ASSIGNMENT_RE,
    NAMED_CREDENTIAL_ASSIGNMENT_RE,
    re.compile(r"(?i)-----BEGIN (?:[A-Z0-9][A-Z0-9 -]* )?PRIVATE KEY-----"),
    re.compile(r"(?i)-----BEGIN PGP PRIVATE KEY BLOCK-----"),
    re.compile(
        rf"(?i)\bbearer[ \t]+(?!{re.escape(REDACTION_SENTINEL)}"
        rf"{REDACTION_BOUNDARY})[A-Za-z0-9._~+/=-]{{16,}}"
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
    re.compile(
        r"(?<![A-Za-z0-9_-])(?:sk_(?:live|test)_[0-9A-Za-z]{16,}|"
        r"sk-(?:proj-|svcacct-)?[0-9A-Za-z_-]{16,})(?![A-Za-z0-9_-])"
    ),
)


class FleetImprovementValidationError(ValueError):
    """Raised when a record or transition violates the fleet-improvement contract."""


def _reject_duplicate_json_pairs(
    pairs: Sequence[tuple[str, object]],
) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, child in pairs:
        if key in value:
            raise FleetImprovementValidationError(
                f"duplicate JSON object key {key!r}"
            )
        value[key] = child
    return value


def _mapping(value: object, field: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise FleetImprovementValidationError(f"{field} must be an object")
    return value


def _exact_fields(value: Mapping[str, object], expected: set[str], field: str) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing or unknown:
        details = []
        if missing:
            details.append("missing " + ", ".join(missing))
        if unknown:
            details.append("unknown " + ", ".join(unknown))
        raise FleetImprovementValidationError(f"{field}: " + "; ".join(details))


def _string(value: object, field: str, *, maximum: int = 4096) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FleetImprovementValidationError(f"{field} must be a nonblank string")
    if len(value.encode("utf-8")) > maximum:
        raise FleetImprovementValidationError(f"{field} exceeds {maximum} UTF-8 bytes")
    return value


def _nullable_string(value: object, field: str, *, maximum: int = 4096) -> str | None:
    if value is None:
        return None
    return _string(value, field, maximum=maximum)


def _enum(value: object, allowed: set[str], field: str) -> str:
    text = _string(value, field, maximum=128)
    if text not in allowed:
        raise FleetImprovementValidationError(
            f"{field} must be one of {sorted(allowed)}"
        )
    return text


def _integer(value: object, field: str, *, minimum: int = 0, maximum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise FleetImprovementValidationError(f"{field} must be an integer")
    if value < minimum or (maximum is not None and value > maximum):
        ceiling = f" and <= {maximum}" if maximum is not None else ""
        raise FleetImprovementValidationError(
            f"{field} must be >= {minimum}{ceiling}"
        )
    return value


def _number(value: object, field: str, *, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FleetImprovementValidationError(f"{field} must be a number")
    result = float(value)
    if not math.isfinite(result) or result < minimum:
        raise FleetImprovementValidationError(f"{field} must be finite and >= {minimum}")
    return result


def _timestamp(value: object, field: str) -> datetime:
    text = _string(value, field, maximum=64)
    if RFC3339_UTC_TIMESTAMP_RE.fullmatch(text) is None:
        raise FleetImprovementValidationError(f"{field} must be an RFC3339 UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError as exc:
        raise FleetImprovementValidationError(f"{field} must be a valid RFC3339 timestamp") from exc
    if parsed.isoformat().endswith("+00:00") is False:  # pragma: no cover - defensive
        raise FleetImprovementValidationError(f"{field} must be UTC")
    return parsed


def _revision(value: object, field: str) -> str:
    text = _string(value, field, maximum=64)
    if not REVISION_RE.fullmatch(text):
        raise FleetImprovementValidationError(f"{field} must be a full lowercase revision")
    return text


def _digest(value: object, field: str) -> str:
    text = _string(value, field, maximum=64)
    if not DIGEST_RE.fullmatch(text):
        raise FleetImprovementValidationError(f"{field} must be a lowercase SHA-256 digest")
    return text


def _evidence_id(value: object, field: str) -> str:
    text = _string(value, field, maximum=35)
    if not EVIDENCE_ID_RE.fullmatch(text):
        raise FleetImprovementValidationError(f"{field} must match ev_<32 lowercase hex>")
    return text


def _string_list(
    value: object,
    field: str,
    *,
    nonempty: bool = False,
    maximum_items: int = 256,
) -> list[str]:
    if not isinstance(value, list):
        raise FleetImprovementValidationError(f"{field} must be an array")
    if nonempty and not value:
        raise FleetImprovementValidationError(f"{field} must not be empty")
    if len(value) > maximum_items:
        raise FleetImprovementValidationError(f"{field} has too many entries")
    result = [_string(item, f"{field}[{index}]") for index, item in enumerate(value)]
    if len(set(result)) != len(result):
        raise FleetImprovementValidationError(f"{field} must not contain duplicates")
    return result


def _contains_credentials(text: str) -> bool:
    masked = REDACTION_RE.sub(REDACTION_SENTINEL, text)
    return any(pattern.search(masked) for pattern in CREDENTIAL_PATTERNS)


def _reject_sensitive(value: object, field: str = "record") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = str(key)
            if SENSITIVE_KEY_RE.search(key_text):
                raise FleetImprovementValidationError(
                    f"{field}.{key_text} is a credential-bearing field name"
                )
            _reject_sensitive(child, f"{field}.{key_text}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_sensitive(child, f"{field}[{index}]")
    elif isinstance(value, str) and _contains_credentials(value):
        raise FleetImprovementValidationError(
            f"{field} contains credential-bearing content"
        )


def _safe_path(value: object, field: str) -> str:
    text = _string(value, field, maximum=512)
    path = PurePosixPath(text)
    if (
        text != text.strip()
        or not SAFE_PATH_RE.fullmatch(text)
        or any(ord(character) < 32 for character in text)
        or "\\" in text
        or "://" in text
        or text.startswith(("/", "~"))
        or re.match(r"^[A-Za-z]:", text)
        or text != path.as_posix()
    ):
        raise FleetImprovementValidationError(f"{field} must be a repository-relative POSIX path")
    if not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise FleetImprovementValidationError(f"{field} must not contain traversal or empty components")
    if any(part.casefold() == ".git" for part in path.parts):
        raise FleetImprovementValidationError(f"{field} must not target Git metadata")
    return path.as_posix()


def _validate_git_pathspec_argv(paths: Sequence[str], field: str) -> None:
    encoded_bytes = sum(len(path.encode("utf-8")) + 1 for path in paths)
    if encoded_bytes > MAX_GIT_PATHSPEC_ARGV_BYTES:
        raise FleetImprovementValidationError(
            f"{field} exceeds the portable aggregate Git pathspec argv limit of "
            f"{MAX_GIT_PATHSPEC_ARGV_BYTES} bytes"
        )


def _portable_git_tree_path(path: str, field: str) -> tuple[str, ...]:
    """Reject tree names that cannot round-trip across the fleet's supported hosts."""

    if path != unicodedata.normalize("NFC", path):
        raise FleetImprovementValidationError(
            f"{field} contains a path that is not Unicode NFC-normalized"
        )
    encoded_path = path.encode("utf-8")
    parts = tuple(path.split("/"))
    if (
        not path
        or len(encoded_path) > MAX_GIT_PATH_BYTES
        or not parts
        or path.startswith("/")
        or "\\" in path
        or any(part in {"", ".", ".."} for part in parts)
    ):
        raise FleetImprovementValidationError(f"{field} contains a nonportable Git path")
    forbidden = frozenset('<>:"\\|?*')
    for part in parts:
        if (
            len(part.encode("utf-8")) > MAX_GIT_COMPONENT_BYTES
            or part.endswith((" ", "."))
            or part.casefold() in {".git", "git~1"}
            or WINDOWS_RESERVED_COMPONENT_RE.fullmatch(part) is not None
            or any(character in forbidden for character in part)
            or any(ord(character) < 32 or ord(character) == 127 for character in part)
            or any(unicodedata.category(character) == "Cf" for character in part)
        ):
            raise FleetImprovementValidationError(
                f"{field} contains a path component that is not portable across fleet hosts"
            )
    return parts


def _within_roots(path: str, roots: Sequence[str]) -> bool:
    candidate = PurePosixPath(path)
    for root in roots:
        root_path = PurePosixPath(root)
        if candidate == root_path or root_path in candidate.parents:
            return True
    return False


def _validate_target(value: object, roots: Sequence[str]) -> Mapping[str, object]:
    target = _mapping(value, "target")
    _exact_fields(target, TARGET_FIELDS, "target")
    _string(target["repository"], "target.repository", maximum=256)
    _revision(target["base_revision"], "target.base_revision")
    _enum(
        target["artifact_kind"],
        {"agent", "skill", "eval", "grader", "tool_description", "handoff", "fleet_governance"},
        "target.artifact_kind",
    )
    if not isinstance(target["artifact_paths"], list) or not target["artifact_paths"]:
        raise FleetImprovementValidationError("target.artifact_paths must be a nonempty array")
    if len(target["artifact_paths"]) > MAX_ARTIFACT_PATHS:
        raise FleetImprovementValidationError(
            f"target.artifact_paths must contain at most {MAX_ARTIFACT_PATHS} entries"
        )
    paths = [
        _safe_path(item, f"target.artifact_paths[{index}]")
        for index, item in enumerate(target["artifact_paths"])
    ]
    _validate_git_pathspec_argv(paths, "target.artifact_paths")
    if len(set(paths)) != len(paths):
        raise FleetImprovementValidationError("target.artifact_paths must not contain duplicates")
    path_set = set(paths)
    for path in paths:
        parts = PurePosixPath(path).parts
        for depth in range(1, len(parts)):
            if "/".join(parts[:depth]) in path_set:
                raise FleetImprovementValidationError(
                    "target.artifact_paths must not overlap"
                )
    if not roots:
        raise FleetImprovementValidationError("caller-allowed artifact roots are required")
    for path in paths:
        if not _within_roots(path, roots):
            raise FleetImprovementValidationError(
                f"target artifact path {path!r} is outside caller-allowed roots"
            )
    return target


def _validate_owner(value: object) -> None:
    owner = _mapping(value, "owner")
    _exact_fields(owner, OWNER_FIELDS, "owner")
    _string(owner["name"], "owner.name", maximum=256)
    _enum(owner["kind"], {"human", "team"}, "owner.kind")
    _nullable_string(owner["agent_lane"], "owner.agent_lane", maximum=128)


def _validate_observations(value: object) -> list[Mapping[str, object]]:
    if not isinstance(value, list) or not value:
        raise FleetImprovementValidationError("observations must be a nonempty array")
    result: list[Mapping[str, object]] = []
    ids: set[str] = set()
    for index, item in enumerate(value):
        field = f"observations[{index}]"
        observation = _mapping(item, field)
        _exact_fields(observation, OBSERVATION_FIELDS, field)
        event_id = _string(observation["event_id"], f"{field}.event_id", maximum=96)
        if not ID_RE.fullmatch(event_id) or not event_id.startswith("fo_"):
            raise FleetImprovementValidationError(f"{field}.event_id must be a stable fo_ identifier")
        if event_id in ids:
            raise FleetImprovementValidationError(f"duplicate observation event_id {event_id!r}")
        ids.add(event_id)
        _enum(
            observation["kind"],
            {
                "user_correction",
                "eval_failure",
                "review_finding",
                "routing_misfire",
                "authority_violation",
                "runtime_drift",
                "operational_handoff",
                "manual",
            },
            f"{field}.kind",
        )
        _timestamp(observation["observed_at"], f"{field}.observed_at")
        source = _mapping(observation["source"], f"{field}.source")
        _exact_fields(source, SOURCE_FIELDS, f"{field}.source")
        source_kind = _enum(
            source["kind"],
            {"user_feedback", "eval_result", "review", "runtime", "operational", "manual"},
            f"{field}.source.kind",
        )
        _string(source["locator"], f"{field}.source.locator", maximum=1024)
        revision = source["revision"]
        digest = source["sha256"]
        if revision is not None:
            _revision(revision, f"{field}.source.revision")
        if digest is not None:
            _digest(digest, f"{field}.source.sha256")
        if source_kind in {"eval_result", "review", "runtime", "operational"} and (
            revision is None or digest is None
        ):
            raise FleetImprovementValidationError(
                f"{field}.source requires revision and sha256 for {source_kind}"
            )
        _enum(observation["trust"], {"trusted", "untrusted", "mixed"}, f"{field}.trust")
        _string(observation["summary"], f"{field}.summary", maximum=2048)
        evidence_ids = _string_list(
            observation["evidence_ids"],
            f"{field}.evidence_ids",
            nonempty=True,
            maximum_items=32,
        )
        for evidence_index, evidence in enumerate(evidence_ids):
            _evidence_id(evidence, f"{field}.evidence_ids[{evidence_index}]")
        result.append(observation)
    return result


def _validate_evidence_refs(value: object) -> dict[str, Mapping[str, object]]:
    if not isinstance(value, list) or not value:
        raise FleetImprovementValidationError("evidence_refs must be a nonempty array")
    if len(value) > 64:
        raise FleetImprovementValidationError("evidence_refs has too many entries")
    refs: dict[str, Mapping[str, object]] = {}
    for index, item in enumerate(value):
        field = f"evidence_refs[{index}]"
        ref = _mapping(item, field)
        _exact_fields(ref, EVIDENCE_REF_FIELDS, field)
        evidence_id = _evidence_id(ref["evidence_id"], f"{field}.evidence_id")
        if evidence_id in refs:
            raise FleetImprovementValidationError(
                f"duplicate evidence reference {evidence_id!r}"
            )
        _enum(
            ref["kind"],
            {"evidence_envelope", "historical_report"},
            f"{field}.kind",
        )
        _safe_path(ref["locator"], f"{field}.locator")
        _digest(ref["sha256"], f"{field}.sha256")
        refs[evidence_id] = ref
    return refs


def _validate_budget_ceilings(value: Mapping[str, object]) -> Mapping[str, float]:
    ceilings = _mapping(value, "budget_ceilings")
    _exact_fields(ceilings, set(DEFAULT_BUDGET_CEILINGS), "budget_ceilings")
    result: dict[str, float] = {}
    for field in ("max_model_turns", "max_evaluator_calls", "max_tokens", "max_wall_seconds"):
        result[field] = float(_integer(ceilings[field], f"budget_ceilings.{field}", minimum=1))
        if result[field] > float(DEFAULT_BUDGET_CEILINGS[field]):
            raise FleetImprovementValidationError(
                f"budget_ceilings.{field} exceeds the v1 global ceiling"
            )
    result["max_cost_usd"] = _number(
        ceilings["max_cost_usd"], "budget_ceilings.max_cost_usd"
    )
    if result["max_cost_usd"] > float(DEFAULT_BUDGET_CEILINGS["max_cost_usd"]):
        raise FleetImprovementValidationError(
            "budget_ceilings.max_cost_usd exceeds the v1 global ceiling"
        )
    return result


def _validate_budget(
    value: object,
    ceilings: Mapping[str, object],
) -> Mapping[str, object]:
    budget = _mapping(value, "budget")
    _exact_fields(budget, BUDGET_FIELDS, "budget")
    trusted_ceilings = _validate_budget_ceilings(ceilings)
    _enum(budget["origin"], {"predeclared", "retrospective_import"}, "budget.origin")
    _integer(budget["max_attempts"], "budget.max_attempts", minimum=1, maximum=3)
    for field in ("max_model_turns", "max_evaluator_calls", "max_tokens", "max_wall_seconds"):
        value_int = _integer(budget[field], f"budget.{field}", minimum=1)
        if value_int > trusted_ceilings[field]:
            raise FleetImprovementValidationError(
                f"budget.{field} exceeds caller policy ceiling"
            )
    cost = _number(budget["max_cost_usd"], "budget.max_cost_usd")
    if cost > trusted_ceilings["max_cost_usd"]:
        raise FleetImprovementValidationError(
            "budget.max_cost_usd exceeds caller policy ceiling"
        )
    return budget


def _validate_visible_case_set(value: object, field: str) -> None:
    case_set = _mapping(value, field)
    _exact_fields(case_set, VISIBLE_CASE_SET_FIELDS, field)
    _digest(case_set["sha256"], f"{field}.sha256")
    _integer(case_set["case_count"], f"{field}.case_count", minimum=1)


def _validate_shadow(value: object, field: str) -> None:
    if value is None:
        return
    shadow = _mapping(value, field)
    _exact_fields(shadow, SHADOW_FIELDS, field)
    _digest(shadow["sha256"], f"{field}.sha256")
    _integer(shadow["case_count"], f"{field}.case_count", minimum=1)
    _enum(shadow["result"], {"pass", "fail", "inconclusive"}, f"{field}.result")
    _evidence_id(shadow["evidence_id"], f"{field}.evidence_id")


def _validate_evaluation(
    value: object,
    field: str,
    subject_revision: str | None,
) -> Mapping[str, object] | None:
    if value is None:
        return None
    evaluation = _mapping(value, field)
    _exact_fields(evaluation, EVALUATION_FIELDS, field)
    kind = _enum(
        evaluation["kind"], {"evidence_envelope", "historical_report"}, f"{field}.kind"
    )
    evaluator = evaluation["evaluator"]
    if evaluator is None:
        if kind == "evidence_envelope":
            raise FleetImprovementValidationError(
                f"{field}.evaluator is required for an evidence envelope"
            )
    else:
        _string(evaluator, f"{field}.evaluator", maximum=256)
    if evaluation["evidence_id"] is None:
        raise FleetImprovementValidationError(
            f"{field}.evidence_id is required for every retained evaluation"
        )
    else:
        _evidence_id(evaluation["evidence_id"], f"{field}.evidence_id")
    _string(evaluation["locator"], f"{field}.locator", maximum=1024)
    _digest(evaluation["sha256"], f"{field}.sha256")
    raw_evaluation_subject = evaluation["subject_revision"]
    evaluation_subject = None
    if raw_evaluation_subject is not None:
        evaluation_subject = _revision(raw_evaluation_subject, f"{field}.subject_revision")
    if kind == "evidence_envelope" and (
        subject_revision is None or evaluation_subject is None
    ):
        raise FleetImprovementValidationError(
            f"{field}.subject_revision and the attempt subject are required for an evidence envelope"
        )
    if evaluation_subject != subject_revision:
        raise FleetImprovementValidationError(f"{field}.subject_revision does not match the attempt")
    _revision(evaluation["evaluator_revision"], f"{field}.evaluator_revision")
    for name in ("runner_sha256", "suite_sha256", "case_set_sha256"):
        raw = evaluation[name]
        if raw is None:
            if kind == "evidence_envelope":
                raise FleetImprovementValidationError(f"{field}.{name} is required for an evidence envelope")
        else:
            _digest(raw, f"{field}.{name}")
    _string(evaluation["requested_model"], f"{field}.requested_model", maximum=256)
    _string(evaluation["observed_model"], f"{field}.observed_model", maximum=256)
    _string(evaluation["reasoning_mode"], f"{field}.reasoning_mode", maximum=128)
    _integer(evaluation["trial_count"], f"{field}.trial_count", minimum=1)
    _enum(evaluation["result"], {"pass", "fail", "skip", "inconclusive"}, f"{field}.result")
    if not isinstance(evaluation["safety_regression"], bool):
        raise FleetImprovementValidationError(f"{field}.safety_regression must be boolean")
    if not isinstance(evaluation["authority_regression"], bool):
        raise FleetImprovementValidationError(f"{field}.authority_regression must be boolean")
    return evaluation


def _validate_usage(
    value: object,
    field: str,
) -> Mapping[str, object] | None:
    if value is None:
        return None
    usage = _mapping(value, field)
    _exact_fields(usage, USAGE_FIELDS, field)
    _integer(usage["model_turns"], f"{field}.model_turns", minimum=0)
    _integer(usage["evaluator_calls"], f"{field}.evaluator_calls", minimum=0)
    _integer(usage["tokens"], f"{field}.tokens", minimum=0)
    _integer(usage["wall_seconds"], f"{field}.wall_seconds", minimum=0)
    _number(usage["cost_usd"], f"{field}.cost_usd")
    return usage


def _validate_attempts(
    value: object,
    budget: Mapping[str, object],
    base_revision: str,
) -> list[Mapping[str, object]]:
    if not isinstance(value, list):
        raise FleetImprovementValidationError("attempts must be an array")
    max_attempts = int(budget["max_attempts"])
    if len(value) > max_attempts:
        raise FleetImprovementValidationError("attempt count exceeds budget.max_attempts")
    ids: set[str] = set()
    reserved_totals = {
        "model_turns": 0,
        "evaluator_calls": 0,
        "tokens": 0,
        "wall_seconds": 0,
    }
    reserved_cost = 0.0
    result: list[Mapping[str, object]] = []
    for index, item in enumerate(value):
        field = f"attempts[{index}]"
        attempt = _mapping(item, field)
        _exact_fields(attempt, ATTEMPT_FIELDS, field)
        attempt_id = _string(attempt["attempt_id"], f"{field}.attempt_id", maximum=96)
        if not ID_RE.fullmatch(attempt_id) or not attempt_id.startswith("fa_"):
            raise FleetImprovementValidationError(f"{field}.attempt_id must be a stable fa_ identifier")
        if attempt_id in ids:
            raise FleetImprovementValidationError(f"duplicate attempt_id {attempt_id!r}")
        ids.add(attempt_id)
        iteration = _integer(attempt["iteration"], f"{field}.iteration", minimum=1, maximum=3)
        if iteration != index + 1:
            raise FleetImprovementValidationError("attempt iterations must be sequential starting at 1")
        parent_revision = _revision(attempt["parent_revision"], f"{field}.parent_revision")
        expected_parent = base_revision if index == 0 else result[index - 1]["subject_revision"]
        if expected_parent is None:
            raise FleetImprovementValidationError(
                f"{field}.parent_revision cannot follow an attempt with unknown subject_revision"
            )
        if parent_revision != expected_parent:
            relationship = "target.base_revision" if index == 0 else "previous subject_revision"
            raise FleetImprovementValidationError(
                f"{field}.parent_revision must match {relationship}"
            )
        raw_subject_revision = attempt["subject_revision"]
        subject_revision = None
        if raw_subject_revision is not None:
            subject_revision = _revision(raw_subject_revision, f"{field}.subject_revision")
            if subject_revision == parent_revision:
                raise FleetImprovementValidationError(
                    f"{field}.subject_revision must differ from parent_revision"
                )
        raw_subject_digest = attempt["subject_sha256"]
        subject_digest = None
        if raw_subject_digest is not None:
            subject_digest = _digest(raw_subject_digest, f"{field}.subject_sha256")
        _string(attempt["change_summary"], f"{field}.change_summary", maximum=1024)
        author = _mapping(attempt["author"], f"{field}.author")
        _exact_fields(author, AUTHOR_FIELDS, f"{field}.author")
        _string(author["name"], f"{field}.author.name", maximum=256)
        _string(author["role"], f"{field}.author.role", maximum=128)
        reservation = _validate_usage(attempt["reservation"], f"{field}.reservation")
        actual_usage = _validate_usage(attempt["actual_usage"], f"{field}.actual_usage")
        case_sets = _mapping(attempt["case_sets"], f"{field}.case_sets")
        _exact_fields(case_sets, CASE_SET_FIELDS, f"{field}.case_sets")
        _validate_visible_case_set(case_sets["calibration"], f"{field}.case_sets.calibration")
        _validate_visible_case_set(case_sets["regression"], f"{field}.case_sets.regression")
        _validate_shadow(case_sets["shadow"], f"{field}.case_sets.shadow")
        evaluation = _validate_evaluation(attempt["evaluation"], f"{field}.evaluation", subject_revision)
        if (
            evaluation is not None
            and evaluation["kind"] == "evidence_envelope"
            and evaluation["evaluator"] == author["name"]
        ):
            raise FleetImprovementValidationError(
                f"{field}.evaluation.evaluator must be independent of the candidate author"
            )
        if evaluation is None and (subject_revision is None or subject_digest is None):
            raise FleetImprovementValidationError(
                f"{field} requires an exact subject revision and digest before evaluation"
            )
        if evaluation is None:
            if reservation is None:
                raise FleetImprovementValidationError(
                    f"{field}.reservation is required before evaluation"
                )
            for name in ("model_turns", "evaluator_calls", "tokens", "wall_seconds"):
                if int(reservation[name]) < 1:
                    raise FleetImprovementValidationError(
                        f"{field}.reservation.{name} must be >= 1 before evaluation"
                    )
            if actual_usage is not None:
                raise FleetImprovementValidationError(
                    f"{field}.actual_usage must be null before evaluation"
                )
        if evaluation is not None and evaluation["kind"] == "evidence_envelope" and subject_digest is None:
            raise FleetImprovementValidationError(
                f"{field}.subject_sha256 is required for an evidence envelope"
            )
        if evaluation is not None and evaluation["kind"] == "evidence_envelope":
            if reservation is None or actual_usage is None:
                raise FleetImprovementValidationError(
                    f"{field} requires reservation and actual_usage for an evidence envelope"
                )
            for name in ("model_turns", "evaluator_calls", "tokens", "wall_seconds"):
                if int(reservation[name]) < 1:
                    raise FleetImprovementValidationError(
                        f"{field}.reservation.{name} must be >= 1 for an evidence envelope"
                    )
            if int(actual_usage["evaluator_calls"]) < 1:
                raise FleetImprovementValidationError(
                    f"{field} requires at least one actual evaluator call"
                )
            trial_count = int(evaluation["trial_count"])
            for name in ("model_turns", "evaluator_calls", "tokens"):
                if int(actual_usage[name]) < trial_count:
                    raise FleetImprovementValidationError(
                        f"{field}.actual_usage.{name} must cover evaluation.trial_count"
                    )
            if int(actual_usage["wall_seconds"]) < 1:
                raise FleetImprovementValidationError(
                    f"{field}.actual_usage.wall_seconds must be >= 1"
                )
            for name in ("model_turns", "evaluator_calls", "tokens", "wall_seconds", "cost_usd"):
                if float(actual_usage[name]) > float(reservation[name]):
                    raise FleetImprovementValidationError(
                        f"{field}.actual_usage.{name} exceeds reservation.{name}"
                    )
        if evaluation is not None and evaluation["kind"] == "historical_report" and (
            subject_revision is None
        ) != (subject_digest is None):
            raise FleetImprovementValidationError(
                f"{field} historical subject revision and digest must both be known or both be null"
            )
        if evaluation is not None and evaluation["kind"] == "historical_report" and reservation is not None:
            raise FleetImprovementValidationError(
                f"{field}.reservation must be null because a historical budget was not predeclared"
            )
        outcome = _enum(
            attempt["outcome"],
            {"proposed", "pass", "fail", "skip", "inconclusive", "rejected", "superseded"},
            f"{field}.outcome",
        )
        stop_reason = _nullable_string(attempt["stop_reason"], f"{field}.stop_reason", maximum=1024)
        if evaluation is None and outcome != "proposed":
            raise FleetImprovementValidationError(f"{field}: unevaluated attempt must be proposed")
        if evaluation is not None:
            evaluation_result = str(evaluation["result"])
            if outcome not in {evaluation_result, "rejected", "superseded"}:
                raise FleetImprovementValidationError(f"{field}.outcome disagrees with evaluation.result")
        if outcome in {"fail", "skip", "inconclusive", "rejected", "superseded"} and stop_reason is None:
            raise FleetImprovementValidationError(f"{field}.stop_reason is required for {outcome}")
        result.append(attempt)

        if reservation is not None:
            for name in ("model_turns", "evaluator_calls", "tokens", "wall_seconds"):
                reserved_totals[name] += int(reservation[name])
            reserved_cost += float(reservation["cost_usd"])

    budget_pairs = (
        ("model_turns", "max_model_turns"),
        ("evaluator_calls", "max_evaluator_calls"),
        ("tokens", "max_tokens"),
        ("wall_seconds", "max_wall_seconds"),
    )
    for usage_name, budget_name in budget_pairs:
        if reserved_totals[usage_name] > int(budget[budget_name]):
            raise FleetImprovementValidationError(
                f"cumulative reserved {usage_name} exceeds budget.{budget_name}"
            )
    if reserved_cost > float(budget["max_cost_usd"]):
        raise FleetImprovementValidationError(
            "cumulative reserved cost_usd exceeds budget.max_cost_usd"
        )
    return result


def _validate_monitoring_plan(value: object) -> Mapping[str, object]:
    plan = _mapping(value, "monitoring_plan")
    _exact_fields(plan, MONITORING_PLAN_FIELDS, "monitoring_plan")
    criterion_id = _string(plan["criterion_id"], "monitoring_plan.criterion_id", maximum=96)
    if not MONITORING_ID_RE.fullmatch(criterion_id):
        raise FleetImprovementValidationError(
            "monitoring_plan.criterion_id must be a stable fm_ identifier"
        )
    _string(plan["criterion"], "monitoring_plan.criterion", maximum=1024)
    triggers = _string_list(
        plan["rollback_triggers"],
        "monitoring_plan.rollback_triggers",
        nonempty=True,
        maximum_items=6,
    )
    if set(triggers) - ALL_ROLLBACK_TRIGGERS:
        raise FleetImprovementValidationError(
            "monitoring_plan.rollback_triggers contains an unknown trigger"
        )
    missing_mandatory = sorted(MANDATORY_ROLLBACK_TRIGGERS - set(triggers))
    if missing_mandatory:
        raise FleetImprovementValidationError(
            "monitoring_plan.rollback_triggers omits mandatory triggers: "
            + ", ".join(missing_mandatory)
        )
    return plan


def _validate_reviews(
    value: object,
    attempts: Sequence[Mapping[str, object]],
) -> list[Mapping[str, object]]:
    if not isinstance(value, list):
        raise FleetImprovementValidationError("reviews must be an array")
    if len(value) > 3:
        raise FleetImprovementValidationError("reviews must contain at most one review per attempt")
    attempt_by_id = {str(attempt["attempt_id"]): attempt for attempt in attempts}
    seen: set[str] = set()
    reviews: list[Mapping[str, object]] = []
    for index, item in enumerate(value):
        field = f"reviews[{index}]"
        review = _mapping(item, field)
        _exact_fields(review, REVIEW_FIELDS, field)
        attempt_id = _string(review["attempt_id"], f"{field}.attempt_id", maximum=96)
        if attempt_id in seen:
            raise FleetImprovementValidationError("reviews must contain at most one review per attempt")
        seen.add(attempt_id)
        attempt = attempt_by_id.get(attempt_id)
        if attempt is None:
            raise FleetImprovementValidationError(f"{field}.attempt_id does not identify an attempt")
        revision = _revision(review["subject_revision"], f"{field}.subject_revision")
        if attempt["subject_revision"] is None or revision != attempt["subject_revision"]:
            raise FleetImprovementValidationError(
                f"{field}.subject_revision does not match its attempt"
            )
        reviewer = _string(review["reviewer"], f"{field}.reviewer", maximum=256)
        author = _mapping(attempt["author"], f"{field}.attempt.author")
        evaluation = _mapping(attempt["evaluation"], f"{field}.attempt.evaluation")
        if reviewer in {author["name"], evaluation["evaluator"]}:
            raise FleetImprovementValidationError(
                f"{field}.reviewer must be independent of the candidate author and evaluator"
            )
        _enum(review["verdict"], {"pass", "changes_requested"}, f"{field}.verdict")
        _evidence_id(review["evidence_id"], f"{field}.evidence_id")
        _string(review["locator"], f"{field}.locator", maximum=1024)
        _digest(review["evidence_sha256"], f"{field}.evidence_sha256")
        _timestamp(review["reviewed_at"], f"{field}.reviewed_at")
        reviews.append(review)
    return reviews


def _validate_merge(value: object, subject_revision: str | None) -> Mapping[str, object] | None:
    if value is None:
        return None
    merge = _mapping(value, "merge")
    _exact_fields(merge, MERGE_FIELDS, "merge")
    _string(merge["pr_url"], "merge.pr_url", maximum=1024)
    revision = _revision(merge["subject_revision"], "merge.subject_revision")
    if subject_revision is None or revision != subject_revision:
        raise FleetImprovementValidationError("merge.subject_revision does not match the latest attempt")
    _revision(merge["merge_revision"], "merge.merge_revision")
    _timestamp(merge["merged_at"], "merge.merged_at")
    _string(merge["merged_by"], "merge.merged_by", maximum=256)
    return merge


def _validate_monitoring(
    value: object,
    merge_revision: str | None,
    monitoring_plan: Mapping[str, object],
) -> Mapping[str, object] | None:
    if value is None:
        return None
    monitoring = _mapping(value, "monitoring")
    _exact_fields(monitoring, MONITORING_FIELDS, "monitoring")
    revision = _revision(monitoring["subject_revision"], "monitoring.subject_revision")
    if merge_revision is None or revision != merge_revision:
        raise FleetImprovementValidationError(
            "monitoring.subject_revision does not match merge.merge_revision"
        )
    criterion_id = _string(monitoring["criterion_id"], "monitoring.criterion_id", maximum=96)
    if criterion_id != monitoring_plan["criterion_id"]:
        raise FleetImprovementValidationError(
            "monitoring.criterion_id does not match the frozen monitoring plan"
        )
    _string(monitoring["observed_by"], "monitoring.observed_by", maximum=256)
    _timestamp(monitoring["observed_at"], "monitoring.observed_at")
    _enum(monitoring["result"], {"pass", "fail", "inconclusive"}, "monitoring.result")
    ids = _string_list(monitoring["evidence_ids"], "monitoring.evidence_ids", nonempty=True)
    for index, evidence in enumerate(ids):
        _evidence_id(evidence, f"monitoring.evidence_ids[{index}]")
    return monitoring


def _validate_rollback(
    value: object,
    subject_revision: str | None,
    merge_revision: str | None,
    monitoring_plan: Mapping[str, object],
) -> Mapping[str, object] | None:
    if value is None:
        return None
    rollback = _mapping(value, "rollback")
    _exact_fields(rollback, ROLLBACK_FIELDS, "rollback")
    subject = _revision(rollback["subject_revision"], "rollback.subject_revision")
    if subject_revision is None or subject != subject_revision:
        raise FleetImprovementValidationError(
            "rollback.subject_revision does not match the latest evaluated attempt"
        )
    merged = _revision(rollback["merge_revision"], "rollback.merge_revision")
    if merge_revision is None or merged != merge_revision:
        raise FleetImprovementValidationError(
            "rollback.merge_revision does not match merge.merge_revision"
        )
    rollback_revision = _revision(rollback["rollback_revision"], "rollback.rollback_revision")
    if rollback_revision == merge_revision:
        raise FleetImprovementValidationError(
            "rollback.rollback_revision must differ from merge.merge_revision"
        )
    _timestamp(rollback["rolled_back_at"], "rollback.rolled_back_at")
    _string(rollback["rolled_back_by"], "rollback.rolled_back_by", maximum=256)
    trigger = _enum(
        rollback["trigger"],
        ALL_ROLLBACK_TRIGGERS,
        "rollback.trigger",
    )
    if trigger not in monitoring_plan["rollback_triggers"]:
        raise FleetImprovementValidationError(
            "rollback.trigger was not declared in monitoring_plan.rollback_triggers"
        )
    _string(rollback["reason"], "rollback.reason", maximum=2048)
    ids = _string_list(rollback["evidence_ids"], "rollback.evidence_ids", nonempty=True)
    for index, evidence in enumerate(ids):
        _evidence_id(evidence, f"rollback.evidence_ids[{index}]")
    return rollback


def _validate_lesson(value: object, roots: Sequence[str]) -> Mapping[str, object]:
    lesson = _mapping(value, "lesson")
    _exact_fields(lesson, LESSON_FIELDS, "lesson")
    status = _enum(lesson["status"], {"pending", "encoded", "not_applicable"}, "lesson.status")
    control = lesson["control_path"]
    if control is None:
        if status == "encoded":
            raise FleetImprovementValidationError("lesson.control_path is required when lesson is encoded")
    else:
        path = _safe_path(control, "lesson.control_path")
        if not _within_roots(path, roots):
            raise FleetImprovementValidationError("lesson.control_path is outside caller-allowed roots")
        if status != "encoded":
            raise FleetImprovementValidationError("lesson.control_path is allowed only for an encoded lesson")
    _string(lesson["reason"], "lesson.reason", maximum=1024)
    return lesson


def validate_record(
    record: Mapping[str, object],
    *,
    allowed_artifact_roots: Sequence[str],
    budget_ceilings: Mapping[str, object] = DEFAULT_BUDGET_CEILINGS,
) -> None:
    """Validate one record without inferring transition authority from its contents."""

    value = _mapping(record, "record")
    _exact_fields(value, TOP_FIELDS, "record")
    if value["schema_version"] != SCHEMA_VERSION or isinstance(value["schema_version"], bool):
        raise FleetImprovementValidationError("schema_version must equal integer 1")
    improvement_id = _string(value["improvement_id"], "improvement_id", maximum=96)
    if not ID_RE.fullmatch(improvement_id) or not improvement_id.startswith("fi_"):
        raise FleetImprovementValidationError("improvement_id must be a stable fi_ identifier")
    related_improvement_id = _nullable_string(
        value["related_improvement_id"], "related_improvement_id", maximum=96
    )
    if related_improvement_id is not None:
        if not ID_RE.fullmatch(related_improvement_id) or not related_improvement_id.startswith("fi_"):
            raise FleetImprovementValidationError(
                "related_improvement_id must be null or a stable fi_ identifier"
            )
        if related_improvement_id == improvement_id:
            raise FleetImprovementValidationError(
                "related_improvement_id must not reference the current record"
            )
    created = _timestamp(value["created_at"], "created_at")
    updated = _timestamp(value["updated_at"], "updated_at")
    if updated < created:
        raise FleetImprovementValidationError("updated_at must not precede created_at")
    roots = tuple(_safe_path(root, f"allowed_artifact_roots[{index}]") for index, root in enumerate(allowed_artifact_roots))
    target = _validate_target(value["target"], roots)
    _validate_owner(value["owner"])
    _enum(value["severity"], {"low", "medium", "high", "critical"}, "severity")
    fingerprint = _string(value["failure_fingerprint"], "failure_fingerprint", maximum=67)
    if not FINGERPRINT_RE.fullmatch(fingerprint):
        raise FleetImprovementValidationError("failure_fingerprint must match ff_<64 lowercase hex>")
    observations = _validate_observations(value["observations"])
    for index, observation in enumerate(observations):
        if _timestamp(
            observation["observed_at"], f"observations[{index}].observed_at"
        ) > updated:
            raise FleetImprovementValidationError(
                f"observations[{index}].observed_at must not follow updated_at"
            )
    evidence_refs = _validate_evidence_refs(value["evidence_refs"])
    status = _enum(value["status"], STATUSES, "status")
    _string_list(value["success_criteria"], "success_criteria", nonempty=True, maximum_items=64)
    monitoring_plan = _validate_monitoring_plan(value["monitoring_plan"])
    budget = _validate_budget(value["budget"], budget_ceilings)
    attempts = _validate_attempts(value["attempts"], budget, str(target["base_revision"]))
    latest = attempts[-1] if attempts else None
    subject_revision = (
        str(latest["subject_revision"])
        if latest is not None and latest["subject_revision"] is not None
        else None
    )
    reviews = _validate_reviews(value["reviews"], attempts)
    latest_review = None
    if latest is not None:
        latest_attempt_id = str(latest["attempt_id"])
        latest_review = next(
            (review for review in reviews if review["attempt_id"] == latest_attempt_id),
            None,
        )
    merge = _validate_merge(value["merge"], subject_revision)
    merge_revision = str(merge["merge_revision"]) if merge is not None else None
    monitoring = _validate_monitoring(value["monitoring"], merge_revision, monitoring_plan)
    rollback = _validate_rollback(
        value["rollback"],
        subject_revision,
        merge_revision,
        monitoring_plan,
    )
    lesson = _validate_lesson(value["lesson"], roots)
    _string(value["disposition_reason"], "disposition_reason", maximum=2048)
    _string_list(value["limitations"], "limitations", maximum_items=128)
    _reject_sensitive(value)

    used_evidence_ids: set[str] = set()

    def require_ref(
        evidence_id: object,
        purpose: str,
        *,
        kind: str | None = None,
        locator: object | None = None,
        digest: object | None = None,
    ) -> Mapping[str, object]:
        rendered = _evidence_id(evidence_id, f"{purpose}.evidence_id")
        ref = evidence_refs.get(rendered)
        if ref is None:
            raise FleetImprovementValidationError(
                f"{purpose} references missing evidence ID {rendered!r}"
            )
        used_evidence_ids.add(rendered)
        if kind is not None and ref["kind"] != kind:
            raise FleetImprovementValidationError(
                f"{purpose} requires evidence kind {kind!r}"
            )
        if locator is not None and ref["locator"] != locator:
            raise FleetImprovementValidationError(
                f"{purpose} locator disagrees with its evidence reference"
            )
        if digest is not None and ref["sha256"] != digest:
            raise FleetImprovementValidationError(
                f"{purpose} digest disagrees with its evidence reference"
            )
        return ref

    for index, observation in enumerate(observations):
        for evidence_id in observation["evidence_ids"]:  # type: ignore[union-attr]
            require_ref(evidence_id, f"observations[{index}]")
    for index, attempt in enumerate(attempts):
        case_sets = _mapping(attempt["case_sets"], f"attempts[{index}].case_sets")
        shadow = case_sets["shadow"]
        if shadow is not None:
            shadow_map = _mapping(shadow, f"attempts[{index}].case_sets.shadow")
            require_ref(
                shadow_map["evidence_id"],
                f"attempts[{index}].case_sets.shadow",
                kind="evidence_envelope",
            )
        evaluation = attempt["evaluation"]
        if evaluation is not None:
            evaluation_map = _mapping(evaluation, f"attempts[{index}].evaluation")
            require_ref(
                evaluation_map["evidence_id"],
                f"attempts[{index}].evaluation",
                kind=str(evaluation_map["kind"]),
                locator=evaluation_map["locator"],
                digest=evaluation_map["sha256"],
            )
    for index, review in enumerate(reviews):
        require_ref(
            review["evidence_id"],
            f"reviews[{index}]",
            kind="evidence_envelope",
            locator=review["locator"],
            digest=review["evidence_sha256"],
        )
    if monitoring is not None:
        for evidence_id in monitoring["evidence_ids"]:  # type: ignore[union-attr]
            require_ref(evidence_id, "monitoring", kind="evidence_envelope")
    if rollback is not None:
        for evidence_id in rollback["evidence_ids"]:  # type: ignore[union-attr]
            require_ref(evidence_id, "rollback", kind="evidence_envelope")
    unused = sorted(set(evidence_refs) - used_evidence_ids)
    if unused:
        raise FleetImprovementValidationError(
            "evidence_refs contains unbound entries: " + ", ".join(unused)
        )

    historical_ids = {
        evidence_id
        for evidence_id, ref in evidence_refs.items()
        if ref["kind"] == "historical_report"
    }
    historical_evaluation_ids = {
        str(_mapping(attempt["evaluation"], "historical evaluation")["evidence_id"])
        for attempt in attempts
        if attempt["evaluation"] is not None
        and _mapping(attempt["evaluation"], "historical evaluation")["kind"]
        == "historical_report"
    }
    if historical_ids:
        if status != "rejected" or budget["origin"] != "retrospective_import":
            raise FleetImprovementValidationError(
                "historical_report references are allowed only on rejected retrospective imports"
            )
        if historical_ids != historical_evaluation_ids:
            raise FleetImprovementValidationError(
                "every historical_report reference must bind a historical evaluation"
            )

    no_attempt_statuses = {"observed", "qualified", "duplicate", "not_reproducible", "not_actionable"}
    if status in no_attempt_statuses and attempts:
        raise FleetImprovementValidationError(f"status {status} must not contain attempts")
    if status == "candidate":
        if latest is None or latest["evaluation"] is not None or latest["outcome"] != "proposed":
            raise FleetImprovementValidationError("candidate requires one latest unevaluated proposed attempt")
    if status == "duplicate" and related_improvement_id is None:
        raise FleetImprovementValidationError(
            "duplicate requires related_improvement_id naming the canonical record"
        )
    if status in {"evaluated", "in_review", "merged", "monitoring", "closed", "rolled_back"}:
        if latest is None or latest["evaluation"] is None:
            raise FleetImprovementValidationError(f"status {status} requires an evaluated latest attempt")
    if status == "in_review" or status in {"merged", "monitoring", "closed", "rolled_back"}:
        assert latest is not None
        evaluation = _mapping(latest["evaluation"], "latest evaluation")
        if evaluation["kind"] != "evidence_envelope":
            raise FleetImprovementValidationError(
                f"status {status} requires a fresh evidence envelope, not a historical report"
            )
        if latest["outcome"] != "pass" or evaluation["result"] != "pass":
            raise FleetImprovementValidationError(f"status {status} requires a passing evaluation")
        if evaluation["safety_regression"] or evaluation["authority_regression"]:
            raise FleetImprovementValidationError(f"status {status} cannot contain a safety or authority regression")
        latest_case_sets = _mapping(latest["case_sets"], "latest case_sets")
        latest_shadow = latest_case_sets["shadow"]
        if latest_shadow is not None and _mapping(
            latest_shadow,
            "latest shadow",
        )["result"] != "pass":
            raise FleetImprovementValidationError(
                f"status {status} requires every retained shadow result to pass"
            )
        if latest_review is None:
            raise FleetImprovementValidationError(
                f"status {status} requires an independent review of the latest attempt"
            )
        if status in {"merged", "monitoring", "closed", "rolled_back"} and (
            latest_review["verdict"] != "pass"
        ):
            raise FleetImprovementValidationError(
                f"status {status} requires a passing independent review of the latest attempt"
            )
    if status == "rejected":
        if latest is None:
            raise FleetImprovementValidationError("rejected requires at least one candidate attempt")
        rejected_by_eval = latest["outcome"] in {"fail", "skip", "inconclusive", "rejected"}
        rejected_by_review = (
            latest_review is not None and latest_review["verdict"] == "changes_requested"
        )
        if not (rejected_by_eval or rejected_by_review):
            raise FleetImprovementValidationError("rejected requires failed/inconclusive evidence or changes requested")
    if latest is not None and latest["evaluation"] is not None:
        latest_evaluation = _mapping(latest["evaluation"], "latest evaluation")
        if latest_evaluation["kind"] == "historical_report" and status != "rejected":
            raise FleetImprovementValidationError(
                "historical_report evidence is archival and allowed only for rejected records"
            )
        if budget["origin"] == "retrospective_import" and (
            status != "rejected" or latest_evaluation["kind"] != "historical_report"
        ):
            raise FleetImprovementValidationError(
                "retrospective_import budgets are allowed only on rejected historical records"
            )
    elif budget["origin"] == "retrospective_import":
        raise FleetImprovementValidationError(
            "retrospective_import budget requires a rejected historical evaluation"
        )
    if status in {"merged", "monitoring", "closed", "rolled_back"}:
        if merge is None:
            raise FleetImprovementValidationError(f"status {status} requires merge evidence")
    elif merge is not None:
        raise FleetImprovementValidationError(f"status {status} must not claim merge evidence")
    if status in {"monitoring", "closed"}:
        if monitoring is None:
            raise FleetImprovementValidationError(f"status {status} requires monitoring evidence")
    elif status != "rolled_back" and monitoring is not None:
        raise FleetImprovementValidationError(f"status {status} must not claim monitoring evidence")
    if status == "rolled_back":
        if rollback is None:
            raise FleetImprovementValidationError("rolled_back requires exact rollback evidence")
    elif rollback is not None:
        raise FleetImprovementValidationError(f"status {status} must not claim rollback evidence")
    if status == "closed":
        if monitoring is None or monitoring["result"] != "pass":
            raise FleetImprovementValidationError("closed requires passing monitoring evidence")
        if lesson["status"] not in {"encoded", "not_applicable"}:
            raise FleetImprovementValidationError("closed requires a terminal lesson disposition")
    if status == "rolled_back":
        assert rollback is not None
        trigger = str(rollback["trigger"])
        if trigger == "monitoring_fail" and (
            monitoring is None or monitoring["result"] != "fail"
        ):
            raise FleetImprovementValidationError(
                "monitoring_fail rollback requires failed monitoring evidence"
            )
        if trigger == "monitoring_inconclusive" and (
            monitoring is None or monitoring["result"] != "inconclusive"
        ):
            raise FleetImprovementValidationError(
                "monitoring_inconclusive rollback requires inconclusive monitoring evidence"
            )
        if lesson["status"] not in {"encoded", "not_applicable"}:
            raise FleetImprovementValidationError(
                "rolled_back requires a terminal lesson disposition"
            )

    evidence_times: list[tuple[str, datetime]] = []
    for index, review in enumerate(reviews):
        evidence_times.append(
            (
                f"reviews[{index}].reviewed_at",
                _timestamp(review["reviewed_at"], f"reviews[{index}].reviewed_at"),
            )
        )
    if merge is not None:
        merged_at = _timestamp(merge["merged_at"], "merge.merged_at")
        evidence_times.append(("merge.merged_at", merged_at))
        if latest_review is not None and _timestamp(
            latest_review["reviewed_at"], "latest review.reviewed_at"
        ) > merged_at:
            raise FleetImprovementValidationError("merge.merged_at must not precede review.reviewed_at")
    if monitoring is not None:
        observed_at = _timestamp(monitoring["observed_at"], "monitoring.observed_at")
        evidence_times.append(("monitoring.observed_at", observed_at))
        if merge is not None and _timestamp(merge["merged_at"], "merge.merged_at") > observed_at:
            raise FleetImprovementValidationError("monitoring.observed_at must not precede merge.merged_at")
    if rollback is not None:
        rolled_back_at = _timestamp(rollback["rolled_back_at"], "rollback.rolled_back_at")
        evidence_times.append(("rollback.rolled_back_at", rolled_back_at))
        if merge is not None and _timestamp(merge["merged_at"], "merge.merged_at") > rolled_back_at:
            raise FleetImprovementValidationError(
                "rollback.rolled_back_at must not precede merge.merged_at"
            )
        if monitoring is not None and _timestamp(monitoring["observed_at"], "monitoring.observed_at") > rolled_back_at:
            raise FleetImprovementValidationError(
                "rollback.rolled_back_at must not precede monitoring.observed_at"
            )
    for field, timestamp in evidence_times:
        if timestamp > updated:
            raise FleetImprovementValidationError(f"{field} must not follow updated_at")


def _attempt_identity(attempt: Mapping[str, object]) -> dict[str, object]:
    return {key: attempt[key] for key in ATTEMPT_IDENTITY_FIELDS}


def validate_initial_record_structure(
    record: Mapping[str, object],
    *,
    allowed_artifact_roots: Sequence[str],
    budget_ceilings: Mapping[str, object] = DEFAULT_BUDGET_CEILINGS,
) -> None:
    """Validate the only legal first bytes for a ledger record."""

    validate_record(
        record,
        allowed_artifact_roots=allowed_artifact_roots,
        budget_ceilings=budget_ceilings,
    )
    status = str(record["status"])
    if status == "observed":
        if _mapping(record["budget"], "budget")["origin"] != "predeclared":
            raise FleetImprovementValidationError(
                "an observed initial record requires a predeclared budget"
            )
        return
    attempts = list(record["attempts"])  # type: ignore[arg-type]
    latest = _mapping(attempts[-1], "latest attempt") if attempts else None
    evaluation = (
        _mapping(latest["evaluation"], "latest evaluation")
        if latest is not None and latest["evaluation"] is not None
        else None
    )
    if not (
        status == "rejected"
        and _mapping(record["budget"], "budget")["origin"] == "retrospective_import"
        and evaluation is not None
        and evaluation["kind"] == "historical_report"
    ):
        raise FleetImprovementValidationError(
            "a new record must begin observed or as a rejected retrospective_import"
        )


def validate_initial_record(
    record: Mapping[str, object],
    *,
    allowed_artifact_roots: Sequence[str],
    authority: Mapping[str, object],
    budget_ceilings: Mapping[str, object] = DEFAULT_BUDGET_CEILINGS,
) -> None:
    """Validate creation plus caller-supplied authority; packet fields are not authority."""

    validate_initial_record_structure(
        record,
        allowed_artifact_roots=allowed_artifact_roots,
        budget_ceilings=budget_ceilings,
    )
    auth = _mapping(authority, "authority")
    _exact_fields(auth, AUTHORITY_FIELDS, "authority")
    _string(auth["actor"], "authority.actor", maximum=256)
    role = _enum(
        auth["role"],
        {"triage", "human_or_protected_workflow"},
        "authority.role",
    )
    if record["status"] == "rejected" and role != "human_or_protected_workflow":
        raise FleetImprovementValidationError(
            "a retrospective rejected import requires human_or_protected_workflow authority"
        )
    if auth["subject_revision"] is not None:
        raise FleetImprovementValidationError(
            "initial-record authority subject_revision must be null"
        )


def validate_transition(
    previous: Mapping[str, object],
    current: Mapping[str, object],
    *,
    allowed_artifact_roots: Sequence[str],
    authority: Mapping[str, object],
    budget_ceilings: Mapping[str, object] = DEFAULT_BUDGET_CEILINGS,
) -> None:
    """Validate an update against trusted prior bytes and caller-supplied authority."""

    validate_record(
        previous,
        allowed_artifact_roots=allowed_artifact_roots,
        budget_ceilings=budget_ceilings,
    )
    validate_record(
        current,
        allowed_artifact_roots=allowed_artifact_roots,
        budget_ceilings=budget_ceilings,
    )
    before = _mapping(previous, "previous")
    after = _mapping(current, "current")
    before_status = str(before["status"])
    after_status = str(after["status"])
    if before_status in TERMINAL_STATUSES:
        raise FleetImprovementValidationError(
            f"terminal status {before_status} cannot reopen; create a linked record"
        )
    if after_status not in TRANSITIONS.get(before_status, set()):
        raise FleetImprovementValidationError(
            f"illegal status transition {before_status} -> {after_status}"
        )

    stable_fields = {
        "schema_version",
        "improvement_id",
        "created_at",
        "target",
        "severity",
        "failure_fingerprint",
        "success_criteria",
        "monitoring_plan",
        "budget",
    }
    for field in stable_fields:
        if before[field] != after[field]:
            raise FleetImprovementValidationError(f"transition changed stable field {field}")
    if before["related_improvement_id"] is not None and (
        before["related_improvement_id"] != after["related_improvement_id"]
    ):
        raise FleetImprovementValidationError(
            "transition changed an existing related_improvement_id"
        )
    old_reviews = list(before["reviews"])  # type: ignore[arg-type]
    new_reviews = list(after["reviews"])  # type: ignore[arg-type]
    if (
        new_reviews[: len(old_reviews)] != old_reviews
        or len(new_reviews) > len(old_reviews) + 1
    ):
        raise FleetImprovementValidationError(
            "reviews are append-only and one transition may add at most one"
        )
    for field in ("merge", "monitoring", "rollback"):
        if before[field] is not None and before[field] != after[field]:
            raise FleetImprovementValidationError(
                f"transition changed immutable {field} evidence"
            )
    if before_status == "merged" and after_status == "rolled_back":
        if before["monitoring"] is None and after["monitoring"] is not None:
            raise FleetImprovementValidationError(
                "direct merged-to-rolled_back transition must not add monitoring evidence; "
                "record a distinct monitoring transition first"
            )
    before_lesson = _mapping(before["lesson"], "previous.lesson")
    if before_lesson["status"] != "pending" and before["lesson"] != after["lesson"]:
        raise FleetImprovementValidationError(
            "transition changed an accepted terminal lesson disposition"
        )
    if _timestamp(after["updated_at"], "current.updated_at") <= _timestamp(
        before["updated_at"], "previous.updated_at"
    ):
        raise FleetImprovementValidationError("transition must advance updated_at")

    old_observations = list(before["observations"])  # type: ignore[arg-type]
    new_observations = list(after["observations"])  # type: ignore[arg-type]
    if new_observations[: len(old_observations)] != old_observations:
        raise FleetImprovementValidationError("observations are append-only and existing entries are immutable")

    old_evidence_refs = list(before["evidence_refs"])  # type: ignore[arg-type]
    new_evidence_refs = list(after["evidence_refs"])  # type: ignore[arg-type]
    if (
        new_evidence_refs[: len(old_evidence_refs)] != old_evidence_refs
        or len(new_evidence_refs) < len(old_evidence_refs)
    ):
        raise FleetImprovementValidationError(
            "evidence_refs are append-only and existing entries are immutable"
        )

    old_attempts = list(before["attempts"])  # type: ignore[arg-type]
    new_attempts = list(after["attempts"])  # type: ignore[arg-type]
    evaluation_added: Mapping[str, object] | None = None
    if len(new_attempts) < len(old_attempts) or len(new_attempts) > len(old_attempts) + 1:
        raise FleetImprovementValidationError("attempts are append-only and one transition may add at most one")
    for index, old_attempt in enumerate(old_attempts):
        new_attempt = _mapping(new_attempts[index], f"current.attempts[{index}]")
        old_attempt_map = _mapping(old_attempt, f"previous.attempts[{index}]")
        if old_attempt_map["evaluation"] is None and index == len(old_attempts) - 1:
            if _attempt_identity(old_attempt_map) != _attempt_identity(new_attempt):
                raise FleetImprovementValidationError("latest attempt identity changed while adding evaluation")
            if new_attempt["evaluation"] is None:
                if old_attempt_map != new_attempt:
                    raise FleetImprovementValidationError("unevaluated attempt changed outside evaluation fields")
            elif len(new_attempts) != len(old_attempts):
                raise FleetImprovementValidationError("cannot evaluate an attempt and append another in one transition")
            else:
                evaluation_added = _mapping(
                    new_attempt["evaluation"],
                    "new evaluation",
                )
        elif old_attempt_map != new_attempt:
            raise FleetImprovementValidationError("evaluated attempts are immutable")
    if len(new_attempts) > len(old_attempts) and old_attempts:
        if _mapping(old_attempts[-1], "previous latest attempt")["evaluation"] is None:
            raise FleetImprovementValidationError("cannot append an attempt before the previous attempt is evaluated")
    if len(new_attempts) > len(old_attempts) and len(new_reviews) > len(old_reviews):
        raise FleetImprovementValidationError(
            "review verdict and next candidate attempt require separate transitions"
        )
    if before_status == "in_review" and after_status == "candidate":
        prior_reviews = list(before["reviews"])  # type: ignore[arg-type]
        if not prior_reviews or prior_reviews[-1]["verdict"] != "changes_requested":
            raise FleetImprovementValidationError(
                "an in_review retry requires a retained changes_requested verdict"
            )
    if (
        before_status == "evaluated"
        and after_status == "rejected"
        and len(new_reviews) > len(old_reviews)
    ):
        raise FleetImprovementValidationError(
            "a changes_requested review must enter in_review before a separate rejection"
        )

    auth = _mapping(authority, "authority")
    _exact_fields(auth, AUTHORITY_FIELDS, "authority")
    _string(auth["actor"], "authority.actor", maximum=256)
    role = _enum(
        auth["role"],
        {"triage", "author", "evaluator", "reviewer", "human_or_protected_workflow"},
        "authority.role",
    )
    if role not in AUTHORITY_FOR_STATUS[after_status]:
        raise FleetImprovementValidationError(
            f"authority role {role!r} cannot enter status {after_status!r}"
        )
    if before["owner"] != after["owner"]:
        raise FleetImprovementValidationError(
            "owner is immutable; create a linked record for an explicit ownership transfer"
        )
    if len(new_attempts) > len(old_attempts):
        if role not in {"author", "human_or_protected_workflow"}:
            raise FleetImprovementValidationError(
                "only author or human/protected authority may append a candidate attempt"
            )
        added_attempt = _mapping(new_attempts[-1], "new candidate attempt")
        added_author = _mapping(added_attempt["author"], "new candidate attempt.author")
        if role == "author" and added_author["name"] != auth["actor"]:
            raise FleetImprovementValidationError(
                "attempt.author.name must match the caller-supplied author identity"
            )
    if evaluation_added is not None:
        if role not in {"evaluator", "human_or_protected_workflow"}:
            raise FleetImprovementValidationError(
                "only evaluator or human/protected authority may append evaluation data"
            )
        if role == "evaluator" and evaluation_added["evaluator"] != auth["actor"]:
            raise FleetImprovementValidationError(
                "evaluation.evaluator must match the caller-supplied evaluator identity"
            )
    if len(new_reviews) > len(old_reviews):
        added_review = _mapping(new_reviews[-1], "new review")
        if role not in {"reviewer", "human_or_protected_workflow"}:
            raise FleetImprovementValidationError(
                "only reviewer or human/protected authority may append review evidence"
            )
        if added_review["reviewer"] != auth["actor"]:
            raise FleetImprovementValidationError(
                "review.reviewer must match the caller-supplied authority actor"
            )
    if before["merge"] is None and after["merge"] is not None:
        added_merge = _mapping(after["merge"], "new merge")
        if added_merge["merged_by"] != auth["actor"]:
            raise FleetImprovementValidationError(
                "merge.merged_by must match the caller-supplied authority actor"
            )
    if before["monitoring"] is None and after["monitoring"] is not None:
        added_monitoring = _mapping(after["monitoring"], "new monitoring")
        if added_monitoring["observed_by"] != auth["actor"]:
            raise FleetImprovementValidationError(
                "monitoring.observed_by must match the caller-supplied authority actor"
            )
    if before["rollback"] is None and after["rollback"] is not None:
        added_rollback = _mapping(after["rollback"], "new rollback")
        if added_rollback["rolled_back_by"] != auth["actor"]:
            raise FleetImprovementValidationError(
                "rollback.rolled_back_by must match the caller-supplied authority actor"
            )
    expected_subject = None
    if new_attempts:
        expected_subject = _mapping(new_attempts[-1], "current latest attempt")["subject_revision"]
    supplied_subject = auth["subject_revision"]
    if expected_subject is None:
        if supplied_subject is not None:
            raise FleetImprovementValidationError("authority subject_revision must be null before a candidate exists")
    else:
        if supplied_subject != expected_subject:
            raise FleetImprovementValidationError("authority subject_revision does not match the latest attempt")


def _read_regular_repository_file(repository_root: Path, locator: str) -> bytes:
    root = repository_root.resolve(strict=True)
    current = root
    for part in PurePosixPath(locator).parts:
        current = current / part
        try:
            info = os.lstat(current)
        except OSError as exc:
            raise FleetImprovementValidationError(
                f"evidence file {locator!r} cannot be inspected: {exc}"
            ) from exc
        file_attributes = int(getattr(info, "st_file_attributes", 0))
        if stat.S_ISLNK(info.st_mode) or file_attributes & 0x400:
            raise FleetImprovementValidationError(
                f"evidence file {locator!r} crosses a link or reparse point"
            )
    if not stat.S_ISREG(info.st_mode):
        raise FleetImprovementValidationError(
            f"evidence file {locator!r} must be a regular file"
        )
    if int(getattr(info, "st_nlink", 1)) != 1:
        raise FleetImprovementValidationError(
            f"evidence file {locator!r} must be single-linked"
        )
    if info.st_size > MAX_EVIDENCE_BYTES:
        raise FleetImprovementValidationError(
            f"evidence file {locator!r} exceeds {MAX_EVIDENCE_BYTES} bytes"
        )
    try:
        return current.read_bytes()
    except OSError as exc:
        raise FleetImprovementValidationError(
            f"evidence file {locator!r} cannot be read: {exc}"
        ) from exc


def _git_environment() -> dict[str, str]:
    environment = dict(os.environ)
    for name in tuple(environment):
        if name.startswith(("GIT_", "SSH_")):
            environment.pop(name)
    environment.update(
        {
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_GRAFT_FILE": os.devnull,
            "GIT_LITERAL_PATHSPECS": "1",
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "LC_ALL": "C",
        }
    )
    return environment


def _git_repository_command(
    repository_root: Path,
    arguments: Sequence[str],
    *,
    input_bytes: bytes | None = None,
    allowed_returncodes: frozenset[int] = frozenset({0}),
    max_stdout_bytes: int = MAX_GIT_STDOUT_BYTES,
) -> tuple[int, bytes]:
    if max_stdout_bytes < 0:
        raise FleetImprovementValidationError(
            "trusted Git query max_stdout_bytes must be nonnegative"
        )
    if input_bytes is not None and len(input_bytes) > MAX_GIT_INPUT_BYTES:
        raise FleetImprovementValidationError(
            "trusted Git query input exceeds the bounded capture contract"
        )
    command = [
        "git",
        "-c",
        "core.commitGraph=false",
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.untrackedCache=false",
        "-C",
        str(repository_root),
        *arguments,
    ]
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=_git_environment(),
        )
    except OSError as exc:
        raise FleetImprovementValidationError(
            f"trusted Git query {' '.join(arguments)} failed: {exc}"
        ) from exc

    stdout_chunks: list[bytes] = []
    stderr_chunks: list[bytes] = []
    overflows: list[str] = []
    reader_errors: list[BaseException] = []
    writer_errors: list[BaseException] = []
    deadline = time.monotonic() + GIT_COMMAND_TIMEOUT_SECONDS

    def read_bounded(stream: object, chunks: list[bytes], limit: int, label: str) -> None:
        total = 0
        try:
            while True:
                chunk = stream.read(min(64 * 1024, limit - total + 1))
                if not chunk:
                    return
                if total + len(chunk) > limit:
                    overflows.append(label)
                    try:
                        process.kill()
                    except OSError:
                        pass
                    return
                chunks.append(chunk)
                total += len(chunk)
        except (OSError, ValueError) as exc:
            reader_errors.append(exc)
            try:
                process.kill()
            except OSError:
                pass
        finally:
            try:
                stream.close()
            except (OSError, ValueError):
                pass

    assert process.stdout is not None
    assert process.stderr is not None
    readers = (
        threading.Thread(
            target=read_bounded,
            args=(process.stdout, stdout_chunks, max_stdout_bytes, "stdout"),
            daemon=True,
        ),
        threading.Thread(
            target=read_bounded,
            args=(process.stderr, stderr_chunks, MAX_GIT_STDERR_BYTES, "stderr"),
            daemon=True,
        ),
    )
    for reader in readers:
        reader.start()
    writer: threading.Thread | None = None
    if input_bytes is not None:
        assert process.stdin is not None

        def write_bounded_input() -> None:
            assert process.stdin is not None
            try:
                process.stdin.write(input_bytes)
                process.stdin.flush()
            except BrokenPipeError:
                pass
            except (OSError, ValueError) as exc:
                writer_errors.append(exc)
                try:
                    process.kill()
                except OSError:
                    pass
            finally:
                try:
                    process.stdin.close()
                except (BrokenPipeError, OSError, ValueError):
                    pass

        writer = threading.Thread(target=write_bounded_input, daemon=True)
        writer.start()
    timed_out = False
    try:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise subprocess.TimeoutExpired(command, GIT_COMMAND_TIMEOUT_SECONDS)
        returncode = process.wait(timeout=remaining)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            process.kill()
        except OSError:
            pass
        try:
            returncode = process.wait(timeout=GIT_COMMAND_CLEANUP_SECONDS)
        except subprocess.TimeoutExpired as exc:
            raise FleetImprovementValidationError(
                f"trusted Git query {' '.join(arguments)} could not terminate after timeout"
            ) from exc
    io_threads = (*readers, *((writer,) if writer is not None else ()))
    join_deadline = (
        time.monotonic() + GIT_COMMAND_CLEANUP_SECONDS
        if timed_out
        else deadline
    )
    for thread in io_threads:
        thread.join(timeout=max(0.0, join_deadline - time.monotonic()))
    if any(thread.is_alive() for thread in io_threads):
        try:
            process.kill()
        except OSError:
            pass
        raise FleetImprovementValidationError(
            f"trusted Git query {' '.join(arguments)} could not close bounded input/output workers"
        )
    if timed_out:
        raise FleetImprovementValidationError(
            f"trusted Git query {' '.join(arguments)} timed out"
        )
    if reader_errors:
        raise FleetImprovementValidationError(
            f"trusted Git query {' '.join(arguments)} could not read bounded output: {reader_errors[0]}"
        )
    if writer_errors:
        raise FleetImprovementValidationError(
            f"trusted Git query {' '.join(arguments)} could not write bounded input: {writer_errors[0]}"
        )
    if overflows:
        raise FleetImprovementValidationError(
            f"trusted Git query {' '.join(arguments)} exceeded the {overflows[0]} capture limit"
        )
    stderr = b"".join(stderr_chunks)
    if returncode not in allowed_returncodes:
        detail = stderr.decode("utf-8", errors="replace").strip()
        raise FleetImprovementValidationError(
            f"trusted Git query {' '.join(arguments)} failed: {detail[-500:]}"
        )
    return returncode, b"".join(stdout_chunks)


def _repository_root(repository_root: Path) -> Path:
    try:
        root = repository_root.resolve(strict=True)
    except OSError as exc:
        raise FleetImprovementValidationError(
            f"repository_root cannot be resolved: {exc}"
        ) from exc
    _, raw_top = _git_repository_command(root, ["rev-parse", "--show-toplevel"])
    try:
        top = Path(raw_top.decode("utf-8", errors="strict").strip()).resolve(strict=True)
        same = root.samefile(top)
    except (OSError, UnicodeError) as exc:
        raise FleetImprovementValidationError(
            f"repository_root identity cannot be verified: {exc}"
        ) from exc
    if not same:
        raise FleetImprovementValidationError(
            "repository_root must be the exact Git worktree root"
        )
    return root


def _require_commit(repository_root: Path, revision: object, field: str) -> str:
    rendered = _revision(revision, field)
    try:
        _, raw_resolved = _git_repository_command(
            repository_root,
            ["rev-parse", "--verify", f"{rendered}^{{commit}}"],
        )
    except FleetImprovementValidationError as exc:
        raise FleetImprovementValidationError(
            f"{field} does not resolve to a local Git commit"
        ) from exc
    try:
        resolved = raw_resolved.decode("ascii", errors="strict").strip()
    except UnicodeError as exc:
        raise FleetImprovementValidationError(
            f"{field} resolved to a non-ASCII Git object ID"
        ) from exc
    if resolved != rendered:
        raise FleetImprovementValidationError(
            f"{field} must name the exact commit object, not a tag or alias"
        )
    return rendered


def _require_ancestor(
    repository_root: Path,
    ancestor: str,
    descendant: str,
    field: str,
) -> None:
    returncode, _ = _git_repository_command(
        repository_root,
        ["merge-base", "--is-ancestor", ancestor, descendant],
        allowed_returncodes=frozenset({0, 1}),
    )
    if returncode != 0:
        raise FleetImprovementValidationError(
            f"{field} does not satisfy required Git ancestry"
        )


def artifact_selection_sha256(
    repository_root: Path,
    revision: object,
    artifact_paths: Sequence[object],
) -> str:
    """Hash exact raw Git blobs selected by canonical artifact paths.

    The v1 digest is independent of checkout filters and Git's SHA-1/SHA-256 object format. It
    frames the requested path set plus each selected regular blob's mode, path, byte size, and raw
    SHA-256 digest.
    """

    root = _repository_root(repository_root)
    commit = _require_commit(root, revision, "artifact revision")
    paths = tuple(
        _safe_path(value, f"artifact_paths[{index}]")
        for index, value in enumerate(artifact_paths)
    )
    if not paths:
        raise FleetImprovementValidationError("artifact_paths must not be empty")
    if len(paths) > MAX_ARTIFACT_PATHS or len(set(paths)) != len(paths):
        raise FleetImprovementValidationError(
            f"artifact_paths must contain at most {MAX_ARTIFACT_PATHS} unique entries"
        )
    _validate_git_pathspec_argv(paths, "artifact_paths")
    path_set = set(paths)
    for path in paths:
        parts = PurePosixPath(path).parts
        if any("/".join(parts[:depth]) in path_set for depth in range(1, len(parts))):
            raise FleetImprovementValidationError("artifact_paths must not overlap")
    _, raw_tree = _git_repository_command(
        root,
        ["ls-tree", "-rlz", "--full-tree", commit, "--", *paths],
        max_stdout_bytes=MAX_GIT_METADATA_BYTES,
    )
    entries: list[tuple[str, str, int, str]] = []
    seen_paths: set[str] = set()
    seen_casefold: dict[str, str] = {}
    total_bytes = 0
    for raw_record in raw_tree.split(b"\0"):
        if not raw_record:
            continue
        match = SUBJECT_TREE_LINE_RE.fullmatch(raw_record)
        if match is None:
            raise FleetImprovementValidationError(
                "target artifact selection contains a linked, submodule, or malformed Git entry"
            )
        mode = match.group(1).decode("ascii")
        object_id = match.group(2).decode("ascii")
        size = int(match.group(3))
        try:
            path = match.group(4).decode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise FleetImprovementValidationError(
                "target artifact selection contains a non-UTF-8 path"
            ) from exc
        if _safe_path(path, "selected artifact path") != path or path in seen_paths:
            raise FleetImprovementValidationError(
                "target artifact selection contains a duplicate or noncanonical path"
            )
        parts = PurePosixPath(path).parts
        for depth in range(1, len(parts) + 1):
            prefix = "/".join(parts[:depth])
            folded = prefix.casefold()
            previous = seen_casefold.setdefault(folded, prefix)
            if previous != prefix:
                raise FleetImprovementValidationError(
                    "target artifact selection contains case-colliding path prefixes"
                )
        if size > MAX_SUBJECT_FILE_BYTES:
            raise FleetImprovementValidationError(
                f"target artifact file {path!r} exceeds {MAX_SUBJECT_FILE_BYTES} bytes"
            )
        seen_paths.add(path)
        total_bytes += size
        if len(entries) + 1 > MAX_SUBJECT_ENTRIES or total_bytes > MAX_SUBJECT_BYTES:
            raise FleetImprovementValidationError(
                "target artifact selection exceeds trusted entry or byte limits"
            )
        entries.append((path, mode, size, object_id))
    request = b"".join(entry[3].encode("ascii") + b"\n" for entry in entries)
    raw_blobs = b""
    if request:
        _, raw_blobs = _git_repository_command(
            root,
            ["cat-file", "--batch"],
            input_bytes=request,
            max_stdout_bytes=MAX_SUBJECT_BYTES + MAX_SUBJECT_ENTRIES * 200 + 1,
        )
    position = 0
    blob_digests: list[str] = []
    for path, _mode, size, object_id in entries:
        line_end = raw_blobs.find(b"\n", position)
        if line_end < 0:
            raise FleetImprovementValidationError("git cat-file returned a truncated header")
        try:
            returned_id, object_type, raw_size = raw_blobs[position:line_end].decode(
                "ascii", errors="strict"
            ).split()
            returned_size = int(raw_size)
        except (UnicodeError, ValueError) as exc:
            raise FleetImprovementValidationError(
                "git cat-file returned an invalid object header"
            ) from exc
        position = line_end + 1
        end = position + returned_size
        if (
            returned_id != object_id
            or object_type != "blob"
            or returned_size != size
            or end >= len(raw_blobs)
            or raw_blobs[end : end + 1] != b"\n"
        ):
            raise FleetImprovementValidationError(
                f"git cat-file object contract failed for {path!r}"
            )
        blob_digests.append(hashlib.sha256(raw_blobs[position:end]).hexdigest())
        position = end + 1
    if position != len(raw_blobs):
        raise FleetImprovementValidationError("git cat-file returned trailing bytes")

    digest = hashlib.sha256(SUBJECT_DIGEST_ALGORITHM.encode("ascii") + b"\0")
    ordered_paths = sorted(paths, key=lambda item: item.encode("utf-8"))
    digest.update(len(ordered_paths).to_bytes(4, "big"))
    for path in ordered_paths:
        encoded_path = path.encode("utf-8")
        digest.update(b"P")
        digest.update(len(encoded_path).to_bytes(4, "big"))
        digest.update(encoded_path)
    digest.update(len(entries).to_bytes(8, "big"))
    for (path, mode, size, _object_id), blob_digest in sorted(
        zip(entries, blob_digests), key=lambda item: item[0][0].encode("utf-8")
    ):
        encoded_path = path.encode("utf-8")
        digest.update(b"F")
        digest.update(len(encoded_path).to_bytes(4, "big"))
        digest.update(encoded_path)
        digest.update(mode.encode("ascii"))
        digest.update(size.to_bytes(8, "big"))
        digest.update(bytes.fromhex(blob_digest))
    return digest.hexdigest()


def _changed_paths(
    repository_root: Path,
    parent_revision: str,
    subject_revision: str,
    artifact_paths: Sequence[object],
) -> tuple[str, ...]:
    paths = tuple(
        _safe_path(value, f"artifact_paths[{index}]")
        for index, value in enumerate(artifact_paths)
    )
    _validate_git_pathspec_argv(paths, "artifact_paths")
    _, raw_names = _git_repository_command(
        repository_root,
        [
            "diff",
            "--name-only",
            "--no-renames",
            "--no-ext-diff",
            "--no-textconv",
            "-z",
            parent_revision,
            subject_revision,
            "--",
            *paths,
        ],
        max_stdout_bytes=MAX_GIT_METADATA_BYTES,
    )
    changed: list[str] = []
    for index, raw_name in enumerate(raw_names.split(b"\0")):
        if not raw_name:
            continue
        try:
            name = raw_name.decode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise FleetImprovementValidationError(
                "target artifact diff contains a non-UTF-8 path"
            ) from exc
        if len(changed) >= MAX_CHANGED_PATHS:
            raise FleetImprovementValidationError(
                "candidate target diff exceeds the bounded changed-path limit"
            )
        changed.append(_safe_path(name, f"changed_paths[{index}]"))
    if not changed:
        raise FleetImprovementValidationError(
            "candidate has no net change under target.artifact_paths"
        )
    for path in paths:
        if not any(name == path or name.startswith(path + "/") for name in changed):
            raise FleetImprovementValidationError(
                f"target artifact path {path!r} is not touched by the candidate"
            )
    return tuple(changed)


def _require_exact_promotion(
    repository_root: Path,
    subject_revision: str,
    merge_revision: str,
) -> str | None:
    if subject_revision == merge_revision:
        return None
    parents = _commit_parents(repository_root, merge_revision, "merge.merge_revision")
    if len(parents) != 2 or parents.count(subject_revision) != 1:
        raise FleetImprovementValidationError(
            "merge.merge_revision must be the subject commit or a two-parent merge with the subject as one direct parent"
        )
    return next(parent for parent in parents if parent != subject_revision)


def _commit_parents(
    repository_root: Path,
    revision: str,
    field: str,
) -> tuple[str, ...]:
    _, raw_parents = _git_repository_command(
        repository_root,
        ["rev-list", "--parents", "-n", "1", revision],
        max_stdout_bytes=1024,
    )
    try:
        values = raw_parents.decode("ascii", errors="strict").strip().split()
    except UnicodeError as exc:
        raise FleetImprovementValidationError(
            f"{field} returned non-ASCII parent data"
        ) from exc
    if (
        not values
        or values[0] != revision
        or any(not REVISION_RE.fullmatch(value) for value in values)
    ):
        raise FleetImprovementValidationError(
            f"{field} returned malformed Git parent data"
        )
    return tuple(values[1:])


def _require_recorded_merge_base(
    repository_root: Path,
    *,
    base_revision: str,
    integration_parent: str,
    subject_revision: str,
) -> None:
    _, raw_bases = _git_repository_command(
        repository_root,
        ["merge-base", "--all", integration_parent, subject_revision],
        max_stdout_bytes=256,
    )
    try:
        merge_bases = raw_bases.decode("ascii", errors="strict").splitlines()
    except UnicodeError as exc:
        raise FleetImprovementValidationError(
            "merge parents returned a non-ASCII merge base"
        ) from exc
    if merge_bases != [base_revision]:
        raise FleetImprovementValidationError(
            "target.base_revision must be the unique actual merge base of the reviewed subject and integration parent"
        )


def _git_leaf_tree(
    repository_root: Path,
    revision: str,
    field: str,
) -> Mapping[bytes, tuple[bytes, bytes]]:
    _, raw_tree = _git_repository_command(
        repository_root,
        ["ls-tree", "-rtz", "--full-tree", revision],
    )
    entries: dict[bytes, tuple[bytes, bytes]] = {}
    namespace: dict[bytes, tuple[bytes, bytes, bytes]] = {}
    seen_casefold: dict[str, str] = {}
    for raw_record in raw_tree.split(b"\0"):
        if not raw_record:
            continue
        try:
            header, path = raw_record.split(b"\t", 1)
            mode, object_type, object_id = header.split(b" ")
        except ValueError as exc:
            raise FleetImprovementValidationError(
                f"{field} contains malformed Git tree metadata"
            ) from exc
        valid_mode_type = (
            (mode == b"040000" and object_type == b"tree")
            or (mode in {b"100644", b"100755", b"120000"} and object_type == b"blob")
            or (mode == b"160000" and object_type == b"commit")
        )
        if not path or not valid_mode_type or not re.fullmatch(
            rb"(?:[0-9a-f]{40}|[0-9a-f]{64})",
            object_id,
        ) or path in namespace:
            raise FleetImprovementValidationError(
                f"{field} contains malformed or duplicate Git tree entries"
            )
        try:
            rendered_path = path.decode("utf-8", errors="strict")
        except UnicodeError as exc:
            raise FleetImprovementValidationError(
                f"{field} contains a non-UTF-8 path that is not portable across fleet hosts"
            ) from exc
        parts = _portable_git_tree_path(rendered_path, field)
        if mode == b"120000" and parts[-1].casefold() in DANGEROUS_SYMLINK_NAMES:
            raise FleetImprovementValidationError(
                f"{field} contains a dangerous Git control-file symlink"
            )
        for depth in range(1, len(parts) + 1):
            prefix = "/".join(parts[:depth])
            portable_key = unicodedata.normalize("NFC", prefix).casefold()
            previous = seen_casefold.setdefault(portable_key, prefix)
            if previous != prefix:
                raise FleetImprovementValidationError(
                    f"{field} contains case-colliding path prefixes"
                )
        namespace[path] = (mode, object_type, object_id)
        if object_type != b"tree":
            entries[path] = (mode, object_id)
        if len(namespace) > MAX_MERGE_TREE_ENTRIES:
            raise FleetImprovementValidationError(
                f"{field} exceeds the bounded merge-tree entry limit"
            )
    implied_tree_paths: set[bytes] = set()
    for path in entries:
        parts = path.split(b"/")
        for depth in range(1, len(parts)):
            parent = b"/".join(parts[:depth])
            implied_tree_paths.add(parent)
            parent_entry = namespace.get(parent)
            if parent_entry is None or parent_entry[1] != b"tree":
                raise FleetImprovementValidationError(
                    f"{field} contains a file/directory namespace conflict"
                )
    declared_tree_paths = {
        path for path, (_mode, object_type, _object_id) in namespace.items()
        if object_type == b"tree"
    }
    if declared_tree_paths != implied_tree_paths:
        raise FleetImprovementValidationError(
            f"{field} contains an empty or structurally inconsistent tree entry"
        )
    _validate_raw_tree_objects(
        repository_root,
        revision=revision,
        namespace=namespace,
        field=field,
    )
    return entries


def _validate_raw_tree_objects(
    repository_root: Path,
    *,
    revision: str,
    namespace: Mapping[bytes, tuple[bytes, bytes, bytes]],
    field: str,
) -> None:
    _, raw_root = _git_repository_command(
        repository_root,
        ["rev-parse", "--verify", f"{revision}^{{tree}}"],
        max_stdout_bytes=128,
    )
    try:
        root_tree = raw_root.decode("ascii", errors="strict").strip()
    except UnicodeError as exc:
        raise FleetImprovementValidationError(
            f"{field} root tree has a non-ASCII object ID"
        ) from exc
    if not REVISION_RE.fullmatch(root_tree):
        raise FleetImprovementValidationError(
            f"{field} root tree has an invalid object ID"
        )
    if any(len(object_id) != len(root_tree) for _mode, _type, object_id in namespace.values()):
        raise FleetImprovementValidationError(
            f"{field} mixes object IDs from incompatible Git hash formats"
        )
    tree_ids = {root_tree}
    tree_ids.update(
        object_id.decode("ascii")
        for _mode, object_type, object_id in namespace.values()
        if object_type == b"tree"
    )
    leaf_ids = sorted(
        {
            object_id.decode("ascii")
            for mode, _object_type, object_id in namespace.values()
            if mode in {b"100644", b"100755", b"120000"}
        }
    )
    if leaf_ids:
        leaf_request = b"".join(
            object_id.encode("ascii") + b"\n" for object_id in leaf_ids
        )
        _, raw_leaf_metadata = _git_repository_command(
            repository_root,
            ["cat-file", "--batch-check"],
            input_bytes=leaf_request,
            max_stdout_bytes=MAX_GIT_STDOUT_BYTES,
        )
        leaf_lines = raw_leaf_metadata.splitlines()
        if len(leaf_lines) != len(leaf_ids):
            raise FleetImprovementValidationError(
                f"{field} raw leaf batch returned the wrong number of objects"
            )
        for requested_id, raw_line in zip(leaf_ids, leaf_lines, strict=True):
            parts = raw_line.split()
            expected_id = requested_id.encode("ascii")
            if parts == [expected_id, b"missing"]:
                raise FleetImprovementValidationError(
                    f"{field} raw leaf entry must resolve to an existing blob"
                )
            try:
                returned_id, actual_type, raw_size = parts
                object_size = int(raw_size)
            except ValueError as exc:
                raise FleetImprovementValidationError(
                    f"{field} raw leaf batch returned malformed metadata"
                ) from exc
            if (
                returned_id != expected_id
                or actual_type != b"blob"
                or object_size < 0
            ):
                raise FleetImprovementValidationError(
                    f"{field} raw leaf entry must resolve to an existing blob"
                )
    request_ids = sorted(tree_ids)
    request = b"".join(object_id.encode("ascii") + b"\n" for object_id in request_ids)
    _, raw_objects = _git_repository_command(
        repository_root,
        ["cat-file", "--batch"],
        input_bytes=request,
        max_stdout_bytes=MAX_GIT_STDOUT_BYTES,
    )
    position = 0
    object_id_bytes = len(root_tree) // 2
    allowed_modes = {b"40000", b"100644", b"100755", b"120000", b"160000"}
    for requested_id in request_ids:
        header_end = raw_objects.find(b"\n", position)
        if header_end < 0:
            raise FleetImprovementValidationError(
                f"{field} raw tree batch returned a truncated header"
            )
        try:
            returned_id, object_type, raw_size = raw_objects[position:header_end].decode(
                "ascii",
                errors="strict",
            ).split()
            object_size = int(raw_size)
        except (UnicodeError, ValueError) as exc:
            raise FleetImprovementValidationError(
                f"{field} raw tree batch returned malformed metadata"
            ) from exc
        position = header_end + 1
        object_end = position + object_size
        if (
            returned_id != requested_id
            or object_type != "tree"
            or object_size < 0
            or object_end >= len(raw_objects)
            or raw_objects[object_end : object_end + 1] != b"\n"
        ):
            raise FleetImprovementValidationError(
                f"{field} raw tree batch violated the object contract"
            )
        raw_tree = raw_objects[position:object_end]
        position = object_end + 1
        cursor = 0
        previous_sort_key: bytes | None = None
        seen_names: set[bytes] = set()
        while cursor < len(raw_tree):
            mode_end = raw_tree.find(b" ", cursor)
            name_end = raw_tree.find(b"\0", mode_end + 1) if mode_end >= 0 else -1
            if mode_end <= cursor or name_end <= mode_end + 1:
                raise FleetImprovementValidationError(
                    f"{field} contains malformed raw tree entries"
                )
            mode = raw_tree[cursor:mode_end]
            name = raw_tree[mode_end + 1 : name_end]
            oid_end = name_end + 1 + object_id_bytes
            if oid_end > len(raw_tree):
                raise FleetImprovementValidationError(
                    f"{field} contains a truncated raw object ID"
                )
            raw_object_id = raw_tree[name_end + 1 : oid_end]
            if not any(raw_object_id):
                raise FleetImprovementValidationError(
                    f"{field} contains a null raw object ID"
                )
            if (
                mode not in allowed_modes
                or name in seen_names
                or name in {b".", b".."}
                or b"/" in name
                or b"\\" in name
            ):
                raise FleetImprovementValidationError(
                    f"{field} contains noncanonical raw tree entries"
                )
            sort_key = name + (b"/" if mode == b"40000" else b"")
            if previous_sort_key is not None and sort_key <= previous_sort_key:
                raise FleetImprovementValidationError(
                    f"{field} contains unsorted raw tree entries"
                )
            seen_names.add(name)
            previous_sort_key = sort_key
            cursor = oid_end
        if cursor != len(raw_tree):
            raise FleetImprovementValidationError(
                f"{field} contains trailing raw tree bytes"
            )
    if position != len(raw_objects):
        raise FleetImprovementValidationError(
            f"{field} raw tree batch returned trailing bytes"
        )


def _validate_object_only_merge(
    repository_root: Path,
    *,
    base_revision: str,
    integration_parent: str,
    subject_revision: str,
    merge_revision: str,
) -> None:
    base = _git_leaf_tree(repository_root, base_revision, "target base tree")
    integration = _git_leaf_tree(
        repository_root,
        integration_parent,
        "merge integration-parent tree",
    )
    subject = _git_leaf_tree(repository_root, subject_revision, "reviewed subject tree")
    merged = _git_leaf_tree(repository_root, merge_revision, "merge result tree")
    for path in base.keys() | integration.keys() | subject.keys() | merged.keys():
        base_entry = base.get(path)
        integration_entry = integration.get(path)
        subject_entry = subject.get(path)
        if integration_entry == base_entry:
            expected = subject_entry
        elif subject_entry == base_entry:
            expected = integration_entry
        elif integration_entry == subject_entry:
            expected = integration_entry
        else:
            raise FleetImprovementValidationError(
                "merge parents contain a divergent path; rebase and reevaluate instead of accepting merge resolution bytes"
            )
        if merged.get(path) != expected:
            raise FleetImprovementValidationError(
                "merge result tree is not the object-only three-way result of its reviewed parents"
            )


def _validate_exact_rollback_subject(
    repository_root: Path,
    *,
    base_revision: str,
    integration_revision: str,
    subject_revision: str,
    merge_revision: str,
    rollback_subject_revision: str,
) -> str:
    parents = _commit_parents(
        repository_root,
        rollback_subject_revision,
        "rollback subject revision",
    )
    if len(parents) != 1:
        raise FleetImprovementValidationError(
            "rollback subject must be an exact one-parent revert commit"
        )
    pre_rollback_parent = parents[0]
    _require_ancestor(
        repository_root,
        merge_revision,
        pre_rollback_parent,
        "rollback pre-revert parent",
    )
    base = _git_leaf_tree(repository_root, base_revision, "target base tree")
    integration = _git_leaf_tree(
        repository_root,
        integration_revision,
        "promotion integration tree",
    )
    subject = _git_leaf_tree(repository_root, subject_revision, "reviewed subject tree")
    merged = _git_leaf_tree(repository_root, merge_revision, "promoted merge tree")
    before = _git_leaf_tree(
        repository_root,
        pre_rollback_parent,
        "rollback pre-revert tree",
    )
    reverted = _git_leaf_tree(
        repository_root,
        rollback_subject_revision,
        "rollback subject tree",
    )
    all_paths = (
        base.keys()
        | integration.keys()
        | subject.keys()
        | merged.keys()
        | before.keys()
        | reverted.keys()
    )
    candidate_only_paths = {
        path
        for path in all_paths
        if subject.get(path) != base.get(path)
        and integration.get(path) == base.get(path)
    }
    if not candidate_only_paths:
        raise FleetImprovementValidationError(
            "rollback has no candidate-exclusive tree delta to restore"
        )
    for path in all_paths:
        if path in candidate_only_paths:
            if before.get(path) != merged.get(path):
                raise FleetImprovementValidationError(
                    "rollback would overwrite post-merge drift on a candidate path"
                )
            expected = integration.get(path)
        else:
            expected = before.get(path)
        if reverted.get(path) != expected:
            raise FleetImprovementValidationError(
                "rollback subject is not the exact object-only inverse of the promoted candidate delta"
            )
    return pre_rollback_parent


def _validate_applied_rollback(
    repository_root: Path,
    *,
    base_revision: str,
    integration_revision: str,
    subject_revision: str,
    merge_revision: str,
    rollback_revision: str,
) -> None:
    parents = _commit_parents(
        repository_root,
        rollback_revision,
        "rollback.rollback_revision",
    )
    if len(parents) == 1:
        _validate_exact_rollback_subject(
            repository_root,
            base_revision=base_revision,
            integration_revision=integration_revision,
            subject_revision=subject_revision,
            merge_revision=merge_revision,
            rollback_subject_revision=rollback_revision,
        )
        return
    if len(parents) != 2:
        raise FleetImprovementValidationError(
            "rollback.rollback_revision must be an exact revert commit or a two-parent application merge"
        )

    valid_applications: list[tuple[str, str, str]] = []
    for index, rollback_subject in enumerate(parents):
        applied_integration = parents[1 - index]
        try:
            pre_rollback_parent = _validate_exact_rollback_subject(
                repository_root,
                base_revision=base_revision,
                integration_revision=integration_revision,
                subject_revision=subject_revision,
                merge_revision=merge_revision,
                rollback_subject_revision=rollback_subject,
            )
            _require_ancestor(
                repository_root,
                pre_rollback_parent,
                applied_integration,
                "rollback application integration parent",
            )
            _require_recorded_merge_base(
                repository_root,
                base_revision=pre_rollback_parent,
                integration_parent=applied_integration,
                subject_revision=rollback_subject,
            )
            _validate_object_only_merge(
                repository_root,
                base_revision=pre_rollback_parent,
                integration_parent=applied_integration,
                subject_revision=rollback_subject,
                merge_revision=rollback_revision,
            )
        except FleetImprovementValidationError:
            continue
        valid_applications.append(
            (rollback_subject, applied_integration, pre_rollback_parent)
        )
    if len(valid_applications) != 1:
        raise FleetImprovementValidationError(
            "rollback application must contain exactly one provable revert subject"
        )


def validate_repository_binding(
    record: Mapping[str, object],
    *,
    repository_root: Path,
    expected_repository: str,
    record_revision: str | None = None,
) -> None:
    """Resolve authoritative commits, ancestry, and exact target artifact bytes."""

    root = _repository_root(repository_root)
    target = _mapping(record["target"], "target")
    trusted_repository = _string(
        expected_repository,
        "expected_repository",
        maximum=256,
    )
    if target["repository"] != trusted_repository:
        raise FleetImprovementValidationError(
            "target.repository does not match the caller-supplied repository identity"
        )
    base_revision = _require_commit(root, target["base_revision"], "target.base_revision")
    artifact_paths = list(target["artifact_paths"])  # type: ignore[arg-type]
    attempts = list(record["attempts"])  # type: ignore[arg-type]
    previous_subject = base_revision
    ledger_revision: str | None = None
    if record_revision is not None:
        ledger_revision = _require_commit(root, record_revision, "record_revision")
        _require_ancestor(root, base_revision, ledger_revision, "record_revision")
    lesson = _mapping(record["lesson"], "lesson")
    if lesson["status"] == "encoded":
        if ledger_revision is None:
            raise FleetImprovementValidationError(
                "an encoded lesson requires record_revision to resolve its durable control"
            )
        control_path = _safe_path(lesson["control_path"], "lesson.control_path")
        ledger_tree = _git_leaf_tree(root, ledger_revision, "record revision tree")
        control_entry = ledger_tree.get(control_path.encode("utf-8"))
        if control_entry is None or control_entry[0] not in {b"100644", b"100755"}:
            raise FleetImprovementValidationError(
                "lesson.control_path must resolve to a regular Git blob at record_revision"
            )
    for index, item in enumerate(attempts):
        attempt = _mapping(item, f"attempts[{index}]")
        parent = _require_commit(root, attempt["parent_revision"], f"attempts[{index}].parent_revision")
        if parent != previous_subject:
            raise FleetImprovementValidationError(
                f"attempts[{index}].parent_revision breaks the authoritative Git chain"
            )
        if attempt["subject_revision"] is None:
            continue
        subject = _require_commit(
            root,
            attempt["subject_revision"],
            f"attempts[{index}].subject_revision",
        )
        _require_ancestor(root, parent, subject, f"attempts[{index}].subject_revision")
        if ledger_revision is not None:
            _require_ancestor(root, subject, ledger_revision, "record_revision")
        _changed_paths(root, parent, subject, artifact_paths)
        actual_digest = artifact_selection_sha256(root, subject, artifact_paths)
        if actual_digest != attempt["subject_sha256"]:
            raise FleetImprovementValidationError(
                f"attempts[{index}].subject_sha256 does not match exact Git artifact bytes"
            )
        previous_subject = subject

    merge = record["merge"]
    promoted_subject: str | None = None
    promoted_merge: str | None = None
    promotion_integration: str | None = None
    if merge is not None:
        merge_map = _mapping(merge, "merge")
        subject = _require_commit(root, merge_map["subject_revision"], "merge.subject_revision")
        merge_revision = _require_commit(root, merge_map["merge_revision"], "merge.merge_revision")
        integration_parent = _require_exact_promotion(root, subject, merge_revision)
        promoted_subject = subject
        promoted_merge = merge_revision
        promotion_integration = integration_parent or base_revision
        _git_leaf_tree(root, subject, "reviewed subject tree")
        base_digest = artifact_selection_sha256(root, base_revision, artifact_paths)
        if integration_parent is not None:
            _require_ancestor(
                root,
                base_revision,
                integration_parent,
                "merge integration parent",
            )
            _require_recorded_merge_base(
                root,
                base_revision=base_revision,
                integration_parent=integration_parent,
                subject_revision=subject,
            )
            if artifact_selection_sha256(
                root,
                integration_parent,
                artifact_paths,
            ) != base_digest:
                raise FleetImprovementValidationError(
                    "merge integration parent contains target drift from target.base_revision"
                )
            _validate_object_only_merge(
                root,
                base_revision=base_revision,
                integration_parent=integration_parent,
                subject_revision=subject,
                merge_revision=merge_revision,
            )
        merged_digest = artifact_selection_sha256(root, merge_revision, artifact_paths)
        latest = _mapping(attempts[-1], "latest attempt")
        if merged_digest != latest["subject_sha256"]:
            raise FleetImprovementValidationError(
                "merge.merge_revision changes the independently reviewed target artifact bytes"
            )
        if ledger_revision is not None:
            _require_ancestor(root, merge_revision, ledger_revision, "record_revision")
    rollback = record["rollback"]
    if rollback is not None:
        if promoted_subject is None or promoted_merge is None or promotion_integration is None:
            raise FleetImprovementValidationError(
                "rollback requires a resolved promoted merge"
            )
        rollback_map = _mapping(rollback, "rollback")
        merge_revision = _require_commit(
            root,
            rollback_map["merge_revision"],
            "rollback.merge_revision",
        )
        rollback_revision = _require_commit(
            root,
            rollback_map["rollback_revision"],
            "rollback.rollback_revision",
        )
        rollback_subject = _require_commit(
            root,
            rollback_map["subject_revision"],
            "rollback.subject_revision",
        )
        if rollback_subject != promoted_subject or merge_revision != promoted_merge:
            raise FleetImprovementValidationError(
                "rollback revisions do not match the resolved promoted subject and merge"
            )
        _require_ancestor(root, merge_revision, rollback_revision, "rollback.rollback_revision")
        _validate_applied_rollback(
            root,
            base_revision=base_revision,
            integration_revision=promotion_integration,
            subject_revision=promoted_subject,
            merge_revision=promoted_merge,
            rollback_revision=rollback_revision,
        )
        base_digest = artifact_selection_sha256(root, base_revision, artifact_paths)
        rollback_digest = artifact_selection_sha256(root, rollback_revision, artifact_paths)
        if rollback_digest != base_digest:
            raise FleetImprovementValidationError(
                "rollback.rollback_revision does not restore the target artifact bytes from target.base_revision"
            )
        if ledger_revision is not None:
            _require_ancestor(root, rollback_revision, ledger_revision, "record_revision")


def validate_evidence_files(
    record: Mapping[str, object],
    *,
    repository_root: Path,
    allowed_evidence_roots: Sequence[str],
    envelope_validator: Callable[[Mapping[str, object]], None],
) -> None:
    """Resolve, hash, validate, and cross-bind every evidence reference.

    The caller owns both the repository root and allowed evidence roots. It must also supply the
    trusted evidence-envelope validator; packet content never selects executable validation code.
    """

    roots = tuple(
        _safe_path(root, f"allowed_evidence_roots[{index}]")
        for index, root in enumerate(allowed_evidence_roots)
    )
    if not roots:
        raise FleetImprovementValidationError("caller-allowed evidence roots are required")
    refs = _validate_evidence_refs(record["evidence_refs"])
    loaded_envelopes: dict[str, Mapping[str, object]] = {}
    for evidence_id, ref in refs.items():
        locator = _safe_path(ref["locator"], f"evidence_refs[{evidence_id}].locator")
        if not _within_roots(locator, roots):
            raise FleetImprovementValidationError(
                f"evidence file {locator!r} is outside caller-allowed evidence roots"
            )
        raw = _read_regular_repository_file(repository_root, locator)
        actual_digest = hashlib.sha256(raw).hexdigest()
        if actual_digest != ref["sha256"]:
            raise FleetImprovementValidationError(
                f"evidence file {locator!r} does not match its recorded sha256"
            )
        if ref["kind"] == "historical_report":
            try:
                historical_text = raw.decode("utf-8")
            except UnicodeError as exc:
                raise FleetImprovementValidationError(
                    f"historical report {locator!r} must be UTF-8 text"
                ) from exc
            if _contains_credentials(historical_text):
                raise FleetImprovementValidationError(
                    f"historical report {locator!r} contains credential-bearing content"
                )
            continue
        try:
            envelope_value = json.loads(
                raw.decode("utf-8"),
                object_pairs_hook=_reject_duplicate_json_pairs,
            )
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise FleetImprovementValidationError(
                f"evidence envelope {locator!r} is not valid UTF-8 JSON: {exc}"
            ) from exc
        envelope = _mapping(envelope_value, f"evidence envelope {evidence_id}")
        try:
            envelope_validator(envelope)
        except Exception as exc:
            raise FleetImprovementValidationError(
                f"evidence envelope {locator!r} failed its trusted validator: {exc}"
            ) from exc
        _reject_sensitive(envelope, f"evidence envelope {evidence_id}")
        if envelope.get("evidence_id") != evidence_id:
            raise FleetImprovementValidationError(
                f"evidence envelope {locator!r} has the wrong evidence_id"
            )
        loaded_envelopes[evidence_id] = envelope

    def bound_envelope(
        evidence_id: object,
        purpose: str,
        *,
        revision: object,
        tree_digest: object | None,
        status: str,
    ) -> Mapping[str, object]:
        rendered = _evidence_id(evidence_id, f"{purpose}.evidence_id")
        envelope = loaded_envelopes.get(rendered)
        if envelope is None:
            raise FleetImprovementValidationError(
                f"{purpose} requires a resolved evidence envelope"
            )
        target = _mapping(envelope["target"], f"{purpose}.envelope.target")
        if target.get("revision") != revision:
            raise FleetImprovementValidationError(
                f"{purpose} evidence target revision does not match the record"
            )
        if tree_digest is not None and target.get("tree_digest") != tree_digest:
            raise FleetImprovementValidationError(
                f"{purpose} evidence tree digest does not match the record"
            )
        if envelope.get("status") != status:
            raise FleetImprovementValidationError(
                f"{purpose} evidence status does not match the record"
            )
        return envelope

    def require_source_fields(
        envelope: Mapping[str, object],
        purpose: str,
        expected: Mapping[str, object],
    ) -> None:
        source = _mapping(envelope["source"], f"{purpose}.envelope.source")
        for field, value in expected.items():
            if source.get(field) != value:
                raise FleetImprovementValidationError(
                    f"{purpose} evidence source disagrees on {field}"
                )

    for index, item in enumerate(record["observations"]):  # type: ignore[union-attr]
        observation = _mapping(item, f"observations[{index}]")
        source = _mapping(observation["source"], f"observations[{index}].source")
        expected_source = {
            "event_id": observation["event_id"],
            "source_kind": source["kind"],
            "source_locator": source["locator"],
            "source_revision": source["revision"],
            "source_sha256": source["sha256"],
        }
        for evidence_id in observation["evidence_ids"]:  # type: ignore[union-attr]
            rendered = str(evidence_id)
            if refs[rendered]["kind"] == "historical_report":
                continue
            envelope = loaded_envelopes[rendered]
            if source["revision"] is not None:
                target = _mapping(
                    envelope["target"],
                    f"observations[{index}].envelope.target",
                )
                if target.get("revision") != source["revision"]:
                    raise FleetImprovementValidationError(
                        f"observations[{index}] evidence target revision does not match its source"
                    )
            require_source_fields(
                envelope,
                f"observations[{index}]",
                expected_source,
            )

    attempts = list(record["attempts"])  # type: ignore[arg-type]
    attempt_by_id = {
        str(_mapping(attempt, f"attempts[{index}]")["attempt_id"]): _mapping(
            attempt, f"attempts[{index}]"
        )
        for index, attempt in enumerate(attempts)
    }
    for index, attempt in enumerate(attempt_by_id.values()):
        case_sets = _mapping(attempt["case_sets"], f"attempts[{index}].case_sets")
        shadow = case_sets["shadow"]
        if shadow is not None:
            shadow_map = _mapping(shadow, f"attempts[{index}].case_sets.shadow")
            envelope = bound_envelope(
                shadow_map["evidence_id"],
                f"attempts[{index}].case_sets.shadow",
                revision=attempt["subject_revision"],
                tree_digest=attempt["subject_sha256"],
                status=str(shadow_map["result"]),
            )
            context = _mapping(
                envelope["context"],
                f"attempts[{index}].case_sets.shadow.envelope.context",
            )
            if context.get("attempt_id") != attempt["attempt_id"]:
                raise FleetImprovementValidationError(
                    f"attempts[{index}].case_sets.shadow evidence has the wrong attempt_id"
                )
            require_source_fields(
                envelope,
                f"attempts[{index}].case_sets.shadow",
                {
                    "subject_digest_algorithm": SUBJECT_DIGEST_ALGORITHM,
                    "case_set_sha256": shadow_map["sha256"],
                    "case_count": shadow_map["case_count"],
                    "held_externally": True,
                },
            )
        evaluation = attempt["evaluation"]
        if evaluation is None:
            continue
        evaluation_map = _mapping(evaluation, f"attempts[{index}].evaluation")
        if evaluation_map["kind"] == "historical_report":
            continue
        envelope = bound_envelope(
            evaluation_map["evidence_id"],
            f"attempts[{index}].evaluation",
            revision=attempt["subject_revision"],
            tree_digest=attempt["subject_sha256"],
            status=str(evaluation_map["result"]),
        )
        context = _mapping(
            envelope["context"],
            f"attempts[{index}].evaluation.envelope.context",
        )
        if context.get("attempt_id") != attempt["attempt_id"]:
            raise FleetImprovementValidationError(
                f"attempts[{index}].evaluation evidence has the wrong attempt_id"
            )
        producer = _mapping(
            envelope["producer"],
            f"attempts[{index}].evaluation.envelope.producer",
        )
        if producer.get("name") != evaluation_map["evaluator"]:
            raise FleetImprovementValidationError(
                f"attempts[{index}].evaluation evidence producer does not match evaluator"
            )
        expected_source = {
            "subject_digest_algorithm": SUBJECT_DIGEST_ALGORITHM,
            "evaluator_revision": evaluation_map["evaluator_revision"],
            "runner_sha256": evaluation_map["runner_sha256"],
            "suite_sha256": evaluation_map["suite_sha256"],
            "case_set_sha256": evaluation_map["case_set_sha256"],
            "requested_model": evaluation_map["requested_model"],
            "observed_model": evaluation_map["observed_model"],
            "reasoning_mode": evaluation_map["reasoning_mode"],
            "trial_count": evaluation_map["trial_count"],
            "safety_regression": evaluation_map["safety_regression"],
            "authority_regression": evaluation_map["authority_regression"],
            "reservation": attempt["reservation"],
            "actual_usage": attempt["actual_usage"],
        }
        require_source_fields(
            envelope,
            f"attempts[{index}].evaluation",
            expected_source,
        )

    for index, item in enumerate(record["reviews"]):  # type: ignore[union-attr]
        review = _mapping(item, f"reviews[{index}]")
        attempt = attempt_by_id[str(review["attempt_id"])]
        envelope = bound_envelope(
            review["evidence_id"],
            f"reviews[{index}]",
            revision=review["subject_revision"],
            tree_digest=attempt["subject_sha256"],
            status="pass" if review["verdict"] == "pass" else "fail",
        )
        producer = _mapping(envelope["producer"], f"reviews[{index}].envelope.producer")
        if producer.get("name") != review["reviewer"]:
            raise FleetImprovementValidationError(
                f"reviews[{index}] evidence producer does not match reviewer"
            )
        context = _mapping(envelope["context"], f"reviews[{index}].envelope.context")
        if context.get("attempt_id") != review["attempt_id"]:
            raise FleetImprovementValidationError(
                f"reviews[{index}] evidence has the wrong attempt_id"
            )
        require_source_fields(
            envelope,
            f"reviews[{index}]",
            {
                "subject_digest_algorithm": SUBJECT_DIGEST_ALGORITHM,
                "attempt_id": review["attempt_id"],
                "reviewer": review["reviewer"],
                "verdict": review["verdict"],
            },
        )
    monitoring = record["monitoring"]
    if monitoring is not None:
        monitoring_map = _mapping(monitoring, "monitoring")
        for evidence_id in monitoring_map["evidence_ids"]:  # type: ignore[union-attr]
            envelope = bound_envelope(
                evidence_id,
                "monitoring",
                revision=monitoring_map["subject_revision"],
                tree_digest=None,
                status=str(monitoring_map["result"]),
            )
            if envelope.get("criterion") != record["monitoring_plan"]["criterion"]:  # type: ignore[index]
                raise FleetImprovementValidationError(
                    "monitoring evidence criterion does not match monitoring_plan"
                )
            context = _mapping(envelope["context"], "monitoring.envelope.context")
            if not attempts or context.get("attempt_id") != attempts[-1]["attempt_id"]:
                raise FleetImprovementValidationError(
                    "monitoring evidence has the wrong attempt_id"
                )
            producer = _mapping(envelope["producer"], "monitoring.envelope.producer")
            if producer.get("name") != monitoring_map["observed_by"]:
                raise FleetImprovementValidationError(
                    "monitoring evidence producer does not match monitoring.observed_by"
                )
            require_source_fields(
                envelope,
                "monitoring",
                {"criterion_id": monitoring_map["criterion_id"]},
            )
    rollback = record["rollback"]
    if rollback is not None:
        rollback_map = _mapping(rollback, "rollback")
        for evidence_id in rollback_map["evidence_ids"]:  # type: ignore[union-attr]
            envelope = bound_envelope(
                evidence_id,
                "rollback",
                revision=rollback_map["rollback_revision"],
                tree_digest=None,
                status="pass",
            )
            context = _mapping(envelope["context"], "rollback.envelope.context")
            if not attempts or context.get("attempt_id") != attempts[-1]["attempt_id"]:
                raise FleetImprovementValidationError(
                    "rollback evidence has the wrong attempt_id"
                )
            require_source_fields(
                envelope,
                "rollback",
                {
                    "trigger": rollback_map["trigger"],
                    "subject_revision": rollback_map["subject_revision"],
                    "merge_revision": rollback_map["merge_revision"],
                    "rollback_revision": rollback_map["rollback_revision"],
                },
            )


def _load_envelope_validator(path: Path) -> Callable[[Mapping[str, object]], None]:
    try:
        spec = importlib.util.spec_from_file_location("trusted_evidence_envelope", path)
        if spec is None or spec.loader is None:
            raise RuntimeError("cannot construct module specification")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        validator = getattr(module, "validate_envelope")
    except Exception as exc:
        raise FleetImprovementValidationError(
            f"cannot load trusted evidence validator {path}: {exc}"
        ) from exc
    if not callable(validator):
        raise FleetImprovementValidationError(
            f"trusted evidence validator {path} has no callable validate_envelope"
        )
    return validator


def canonical_json(value: Mapping[str, object]) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def _load(path: Path, field: str) -> Mapping[str, object]:
    try:
        info = os.lstat(path)
        if (
            stat.S_ISLNK(info.st_mode)
            or int(getattr(info, "st_file_attributes", 0)) & 0x400
            or not stat.S_ISREG(info.st_mode)
            or int(getattr(info, "st_nlink", 1)) != 1
        ):
            raise FleetImprovementValidationError(
                f"{field}: must be a real, single-linked regular file"
            )
        if info.st_size > MAX_RECORD_BYTES:
            raise FleetImprovementValidationError(
                f"{field}: exceeds {MAX_RECORD_BYTES} bytes"
            )
        value = json.loads(
            path.read_bytes().decode("utf-8"),
            object_pairs_hook=_reject_duplicate_json_pairs,
        )
    except FleetImprovementValidationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FleetImprovementValidationError(f"{field}: cannot read JSON: {exc}") from exc
    return _mapping(value, field)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("record", type=Path)
    parser.add_argument("--allowed-root", action="append", required=True, dest="allowed_roots")
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--expected-repository", required=True)
    parser.add_argument(
        "--allowed-evidence-root",
        action="append",
        required=True,
        dest="allowed_evidence_roots",
    )
    parser.add_argument("--evidence-validator", type=Path, required=True)
    parser.add_argument("--trusted-previous", type=Path)
    parser.add_argument("--authority-actor")
    parser.add_argument(
        "--authority-role",
        choices=["triage", "author", "evaluator", "reviewer", "human_or_protected_workflow"],
    )
    parser.add_argument("--authority-subject-revision")
    parser.add_argument(
        "--policy-max-model-turns",
        type=int,
        default=DEFAULT_BUDGET_CEILINGS["max_model_turns"],
    )
    parser.add_argument(
        "--policy-max-evaluator-calls",
        type=int,
        default=DEFAULT_BUDGET_CEILINGS["max_evaluator_calls"],
    )
    parser.add_argument(
        "--policy-max-tokens",
        type=int,
        default=DEFAULT_BUDGET_CEILINGS["max_tokens"],
    )
    parser.add_argument(
        "--policy-max-wall-seconds",
        type=int,
        default=DEFAULT_BUDGET_CEILINGS["max_wall_seconds"],
    )
    parser.add_argument(
        "--policy-max-cost-usd",
        type=float,
        default=DEFAULT_BUDGET_CEILINGS["max_cost_usd"],
    )
    parser.add_argument("--canonical", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        record = _load(args.record, "record")
        if not args.authority_actor or not args.authority_role:
            raise FleetImprovementValidationError(
                "validation requires caller-supplied authority actor and role"
            )
        authority = {
            "actor": args.authority_actor,
            "role": args.authority_role,
            "subject_revision": args.authority_subject_revision,
        }
        budget_ceilings = {
            "max_model_turns": args.policy_max_model_turns,
            "max_evaluator_calls": args.policy_max_evaluator_calls,
            "max_tokens": args.policy_max_tokens,
            "max_wall_seconds": args.policy_max_wall_seconds,
            "max_cost_usd": args.policy_max_cost_usd,
        }
        if args.trusted_previous is not None:
            previous = _load(args.trusted_previous, "trusted_previous")
            validate_transition(
                previous,
                record,
                allowed_artifact_roots=args.allowed_roots,
                authority=authority,
                budget_ceilings=budget_ceilings,
            )
        else:
            validate_initial_record(
                record,
                allowed_artifact_roots=args.allowed_roots,
                authority=authority,
                budget_ceilings=budget_ceilings,
            )
        _, raw_head = _git_repository_command(
            _repository_root(args.repository_root),
            ["rev-parse", "--verify", "HEAD^{commit}"],
        )
        record_revision = raw_head.decode("ascii", errors="strict").strip()
        validate_repository_binding(
            record,
            repository_root=args.repository_root,
            expected_repository=args.expected_repository,
            record_revision=record_revision,
        )
        validate_evidence_files(
            record,
            repository_root=args.repository_root,
            allowed_evidence_roots=args.allowed_evidence_roots,
            envelope_validator=_load_envelope_validator(args.evidence_validator),
        )
        if args.canonical:
            sys.stdout.buffer.write(canonical_json(record))
        else:
            print("fleet_improvement: PASS")
        return 0
    except FleetImprovementValidationError as exc:
        print(f"fleet_improvement: FAIL -- {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
