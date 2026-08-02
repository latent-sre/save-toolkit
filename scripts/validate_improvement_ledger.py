#!/usr/bin/env python3
"""Validate every bounded fleet-improvement record and its Git-backed lifecycle history."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
LEDGER_ROOT = Path("evals/improvements")
VALIDATOR_PATH = ROOT / "skills/agent-authoring/scripts/fleet_improvement.py"
ENVELOPE_VALIDATOR_PATH = ROOT / "scripts/evidence_envelope.py"
ALLOWED_ARTIFACT_ROOTS = (
    "agents",
    "skills",
    "evals",
    "scripts",
    "schemas",
    "hooks",
    "commands",
)
ALLOWED_EVIDENCE_ROOTS = ("evals/evidence", "evals/baselines")
IMPROVEMENT_ID_RE = re.compile(r"^fi_[a-z0-9][a-z0-9._-]{2,95}$")
MAX_RECORD_BYTES = 1024 * 1024
MAX_RECORD_REVISIONS = 128
EXPECTED_REPOSITORY = "latent-sre/sre-agents"
LEDGER_BUDGET_CEILINGS = {
    "max_model_turns": 60,
    "max_evaluator_calls": 60,
    "max_tokens": 1_000_000,
    "max_wall_seconds": 14_400,
    "max_cost_usd": 100.0,
}


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fleet_improvement = _load_module(VALIDATOR_PATH, "fleet_improvement_ledger")
evidence_envelope = _load_module(ENVELOPE_VALIDATOR_PATH, "evidence_envelope_ledger")


class LedgerValidationError(ValueError):
    """Raised when the repository ledger violates its structural or history contract."""


def _reject_duplicate_json_pairs(
    pairs: Sequence[tuple[str, object]],
) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, child in pairs:
        if key in value:
            raise LedgerValidationError(f"duplicate JSON object key {key!r}")
        value[key] = child
    return value


def _is_reparse(info: os.stat_result) -> bool:
    return stat.S_ISLNK(info.st_mode) or bool(
        int(getattr(info, "st_file_attributes", 0)) & 0x400
    )


def discover_records(repository_root: Path) -> list[Path]:
    ledger = repository_root / LEDGER_ROOT
    current = repository_root
    for part in LEDGER_ROOT.parts:
        current = current / part
        relative = current.relative_to(repository_root).as_posix()
        try:
            info = os.lstat(current)
        except OSError as exc:
            raise LedgerValidationError(f"{relative}: cannot inspect: {exc}") from exc
        if _is_reparse(info) or not stat.S_ISDIR(info.st_mode):
            raise LedgerValidationError(
                f"{relative}: must be a real directory, not a link/reparse point"
            )
    records: list[Path] = []
    with os.scandir(ledger) as directories:
        for directory in sorted(directories, key=lambda entry: entry.name):
            info = os.lstat(directory.path)
            relative_directory = LEDGER_ROOT / directory.name
            if _is_reparse(info) or not stat.S_ISDIR(info.st_mode):
                raise LedgerValidationError(
                    f"{relative_directory.as_posix()}: only real improvement directories are allowed"
                )
            if not IMPROVEMENT_ID_RE.fullmatch(directory.name):
                raise LedgerValidationError(
                    f"{relative_directory.as_posix()}: directory must be a stable fi_ identifier"
                )
            entries: list[os.DirEntry[str]]
            with os.scandir(directory.path) as children:
                entries = sorted(children, key=lambda entry: entry.name)
            if [entry.name for entry in entries] != ["record.json"]:
                raise LedgerValidationError(
                    f"{relative_directory.as_posix()}: must contain exactly record.json"
                )
            record_entry = entries[0]
            record_info = os.lstat(record_entry.path)
            relative_record = relative_directory / "record.json"
            if _is_reparse(record_info) or not stat.S_ISREG(record_info.st_mode):
                raise LedgerValidationError(
                    f"{relative_record.as_posix()}: must be a real regular file"
                )
            if int(getattr(record_info, "st_nlink", 1)) != 1:
                raise LedgerValidationError(
                    f"{relative_record.as_posix()}: must be single-linked"
                )
            if record_info.st_size > MAX_RECORD_BYTES:
                raise LedgerValidationError(
                    f"{relative_record.as_posix()}: exceeds {MAX_RECORD_BYTES} bytes"
                )
            records.append(relative_record)
    if not records:
        raise LedgerValidationError(f"{LEDGER_ROOT.as_posix()}: contains no records")
    return records


def _git(repository_root: Path, argv: Sequence[str], *, check: bool = True) -> bytes:
    allowed = frozenset({0}) if check else frozenset({0, 1})
    try:
        _returncode, output = fleet_improvement._git_repository_command(
            repository_root,
            argv,
            allowed_returncodes=allowed,
        )
    except fleet_improvement.FleetImprovementValidationError as exc:
        raise LedgerValidationError(str(exc)) from exc
    return output


def _load_record_bytes(raw: bytes, label: str) -> Mapping[str, object]:
    if len(raw) > MAX_RECORD_BYTES:
        raise LedgerValidationError(f"{label}: exceeds {MAX_RECORD_BYTES} bytes")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_json_pairs,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise LedgerValidationError(f"{label}: invalid UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise LedgerValidationError(f"{label}: record must be an object")
    return value


def _history_bytes(repository_root: Path, path: Path) -> list[tuple[str, bytes]]:
    rendered = path.as_posix()
    commits = _git(
        repository_root,
        [
            "log",
            "--full-history",
            "--topo-order",
            "--reverse",
            "--no-renames",
            "--format=%H",
            "--",
            rendered,
        ],
    ).decode("ascii", errors="strict").splitlines()
    if len(commits) > MAX_RECORD_REVISIONS:
        raise LedgerValidationError(
            f"{rendered}: exceeds {MAX_RECORD_REVISIONS} retained lifecycle revisions"
        )
    for previous, current in zip(commits, commits[1:]):
        try:
            returncode, _ = fleet_improvement._git_repository_command(
                repository_root,
                ["merge-base", "--is-ancestor", previous, current],
                allowed_returncodes=frozenset({0, 1}),
                max_stdout_bytes=0,
            )
        except fleet_improvement.FleetImprovementValidationError as exc:
            raise LedgerValidationError(str(exc)) from exc
        if returncode != 0:
            raise LedgerValidationError(
                f"{rendered}: lifecycle revisions must form one linear Git history"
            )
    history: list[tuple[str, bytes]] = []
    for commit in commits:
        raw = _git(repository_root, ["show", f"{commit}:{rendered}"])
        if not history or history[-1][1] != raw:
            history.append((commit, raw))
    working = (repository_root / path).read_bytes()
    if not history or history[-1][1] != working:
        history.append(("working-tree", working))
    return history


def _synthetic_authority(
    previous: Mapping[str, object],
    current: Mapping[str, object],
) -> Mapping[str, object]:
    status = str(current["status"])
    role_by_status = {
        "qualified": "triage",
        "duplicate": "triage",
        "not_reproducible": "triage",
        "not_actionable": "triage",
        "candidate": "author",
        "evaluated": "evaluator",
        "in_review": "reviewer",
        "merged": "human_or_protected_workflow",
        "monitoring": "evaluator",
        "closed": "human_or_protected_workflow",
        "rejected": "reviewer",
        "blocked_pending_rescope": "author",
        "rolled_back": "human_or_protected_workflow",
    }
    role = role_by_status[status]
    actor = "repository-history"
    old_reviews = list(previous["reviews"])  # type: ignore[arg-type]
    new_reviews = list(current["reviews"])  # type: ignore[arg-type]
    if len(new_reviews) > len(old_reviews):
        actor = str(new_reviews[-1]["reviewer"])
    old_attempts = list(previous["attempts"])  # type: ignore[arg-type]
    attempts = list(current["attempts"])  # type: ignore[arg-type]
    if len(attempts) > len(old_attempts):
        actor = str(attempts[-1]["author"]["name"])
    elif old_attempts and attempts:
        old_evaluation = old_attempts[-1]["evaluation"]
        new_evaluation = attempts[-1]["evaluation"]
        if old_evaluation is None and new_evaluation is not None:
            actor = str(new_evaluation["evaluator"])
    if previous["merge"] is None and current["merge"] is not None:
        actor = str(current["merge"]["merged_by"])
    if previous["monitoring"] is None and current["monitoring"] is not None:
        actor = str(current["monitoring"]["observed_by"])
    if previous["rollback"] is None and current["rollback"] is not None:
        actor = str(current["rollback"]["rolled_back_by"])
    subject_revision = attempts[-1]["subject_revision"] if attempts else None
    return {
        "actor": actor,
        "role": role,
        "subject_revision": subject_revision,
    }


def _validate_cross_record_uniqueness(
    records: Mapping[str, Mapping[str, object]],
) -> None:
    fingerprints: dict[str, list[Mapping[str, object]]] = {}
    event_owners: dict[str, str] = {}
    evidence_owners: dict[str, str] = {}
    for improvement_id, record in records.items():
        fingerprints.setdefault(str(record["failure_fingerprint"]), []).append(record)
        for observation in record["observations"]:  # type: ignore[union-attr]
            event_id = str(observation["event_id"])
            previous = event_owners.setdefault(event_id, improvement_id)
            if previous != improvement_id:
                raise LedgerValidationError(
                    f"observation event_id {event_id!r} is reused by {previous} and {improvement_id}"
                )
        for evidence_ref in record["evidence_refs"]:  # type: ignore[union-attr]
            evidence_id = str(evidence_ref["evidence_id"])
            previous = evidence_owners.setdefault(evidence_id, improvement_id)
            if previous != improvement_id:
                raise LedgerValidationError(
                    f"evidence_id {evidence_id!r} is reused by {previous} and {improvement_id}"
                )

    for fingerprint, group in fingerprints.items():
        canonical = [record for record in group if record["status"] != "duplicate"]
        duplicates = [record for record in group if record["status"] == "duplicate"]
        if len(canonical) != 1:
            identifiers = sorted(str(record["improvement_id"]) for record in group)
            raise LedgerValidationError(
                f"failure_fingerprint {fingerprint} must have exactly one canonical record: "
                + ", ".join(identifiers)
            )
        canonical_id = str(canonical[0]["improvement_id"])
        for duplicate in duplicates:
            if duplicate["related_improvement_id"] != canonical_id:
                raise LedgerValidationError(
                    f"duplicate {duplicate['improvement_id']} must link canonical record {canonical_id}"
                )

    for improvement_id, record in records.items():
        if record["status"] != "duplicate":
            continue
        related_id = str(record["related_improvement_id"])
        related = records.get(related_id)
        if related is None:
            raise LedgerValidationError(
                f"duplicate {improvement_id} references missing canonical record {related_id}"
            )
        if related["status"] == "duplicate" or (
            related["failure_fingerprint"] != record["failure_fingerprint"]
        ):
            raise LedgerValidationError(
                f"duplicate {improvement_id} must reference a non-duplicate record with the same fingerprint"
            )


def validate_ledger(repository_root: Path) -> None:
    try:
        root = fleet_improvement._repository_root(repository_root)
    except fleet_improvement.FleetImprovementValidationError as exc:
        raise LedgerValidationError(str(exc)) from exc
    inside = _git(root, ["rev-parse", "--is-inside-work-tree"]).decode("ascii").strip()
    if inside != "true":
        raise LedgerValidationError(f"{root}: not a Git worktree")
    shallow = _git(root, ["rev-parse", "--is-shallow-repository"]).decode("ascii").strip()
    if shallow != "false":
        raise LedgerValidationError(
            "complete Git history is required to prove record creation, transitions, and deletions"
        )
    deleted = _git(
        root,
        [
            "log",
            "--full-history",
            "--diff-merges=separate",
            "--no-renames",
            "--diff-filter=D",
            "--name-only",
            "-z",
            "--format=",
            "--",
            LEDGER_ROOT.as_posix(),
        ],
    )
    try:
        deleted_paths = [
            raw_path.decode("utf-8", errors="strict")
            for raw_path in deleted.split(b"\0")
            if raw_path
        ]
    except UnicodeError as exc:
        raise LedgerValidationError(
            "ledger deletion history contains a non-UTF-8 path"
        ) from exc
    deleted_records = sorted(
        {path for path in deleted_paths if path.endswith("/record.json")}
    )
    if deleted_records:
        raise LedgerValidationError(
            "ledger records are append-only and Git history contains deletions: "
            + ", ".join(deleted_records)
        )

    current_records: dict[str, Mapping[str, object]] = {}
    pending_evidence: list[tuple[Path, Mapping[str, object]]] = []
    for path in discover_records(root):
        history = _history_bytes(root, path)
        decoded = [
            (revision, _load_record_bytes(raw, f"{path.as_posix()}@{revision}"))
            for revision, raw in history
        ]
        directory_id = path.parent.name
        for revision, record in decoded:
            if record.get("improvement_id") != directory_id:
                raise LedgerValidationError(
                    f"{path.as_posix()}@{revision}: directory ID disagrees with improvement_id"
                )
        first_revision, first = decoded[0]
        try:
            fleet_improvement.validate_initial_record_structure(
                first,
                allowed_artifact_roots=ALLOWED_ARTIFACT_ROOTS,
                budget_ceilings=LEDGER_BUDGET_CEILINGS,
            )
            for (previous_revision, previous), (current_revision, current) in zip(
                decoded, decoded[1:]
            ):
                fleet_improvement.validate_transition(
                    previous,
                    current,
                    allowed_artifact_roots=ALLOWED_ARTIFACT_ROOTS,
                    authority=_synthetic_authority(previous, current),
                    budget_ceilings=LEDGER_BUDGET_CEILINGS,
                )
            for revision, record in decoded:
                binding_revision = revision
                if binding_revision == "working-tree":
                    binding_revision = _git(
                        root,
                        ["rev-parse", "--verify", "HEAD^{commit}"],
                    ).decode("ascii", errors="strict").strip()
                fleet_improvement.validate_repository_binding(
                    record,
                    repository_root=root,
                    expected_repository=EXPECTED_REPOSITORY,
                    record_revision=binding_revision,
                )
        except (fleet_improvement.FleetImprovementValidationError, KeyError) as exc:
            raise LedgerValidationError(
                f"{path.as_posix()} history beginning {first_revision}: {exc}"
            ) from exc
        current = decoded[-1][1]
        current_records[directory_id] = current
        pending_evidence.append((path, current))

    _validate_cross_record_uniqueness(current_records)
    for path, record in pending_evidence:
        try:
            fleet_improvement.validate_evidence_files(
                record,
                repository_root=root,
                allowed_evidence_roots=ALLOWED_EVIDENCE_ROOTS,
                envelope_validator=evidence_envelope.validate_envelope,
            )
        except (fleet_improvement.FleetImprovementValidationError, KeyError) as exc:
            raise LedgerValidationError(f"{path.as_posix()}: {exc}") from exc


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, default=ROOT)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        validate_ledger(args.repository_root)
    except (OSError, RuntimeError, LedgerValidationError) as exc:
        print(f"validate_improvement_ledger: FAIL -- {exc}", file=sys.stderr)
        return 1
    print("validate_improvement_ledger: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
