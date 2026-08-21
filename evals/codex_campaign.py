#!/usr/bin/env python3
"""Crash-safe, sequential execution state for the fixed 48-trial ROUTE-001 campaign.

Only sanitized :class:`codex_trial.TrialResult` dictionaries may cross this boundary.  A durable
``started`` row is written before every account turn.  If the process dies before the matching
terminal row, reopening the journal reports an unknown outcome and refuses automatic replay.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

import codex_harness
import run_codex_routing


MAX_LEDGER_BYTES = 1024 * 1024
MAX_RESULT_BYTES = 1024 * 1024
SHA256_RE = run_codex_routing.SHA256_RE
IMAGE_ID_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
LOCK_DIRECTORY = ".campaign.lock"


class CampaignContractError(ValueError):
    """The campaign state cannot be proved to match the fixed execution contract."""


class UnknownOutcomeError(CampaignContractError):
    """A paid call may have started but lacks a trustworthy terminal record."""


class CampaignBusyError(CampaignContractError):
    """Another invocation, or a crash-stale lock, owns the campaign root."""


def _is_link_or_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def _canonical_json(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("utf-8")


def _reject_constant(value: str) -> object:
    raise CampaignContractError(f"non-JSON numeric constant {value}")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise CampaignContractError(f"duplicate JSON key {key}")
        result[key] = value
    return result


def _strict_json(raw: bytes, *, label: str) -> object:
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CampaignContractError(f"{label} must be strict UTF-8 JSON") from exc


def _write_all(fd: int, raw: bytes) -> None:
    view = memoryview(raw)
    while view:
        written = os.write(fd, view)
        if written <= 0:
            raise OSError("short write")
        view = view[written:]


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(path, flags)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@dataclass
class CampaignLock:
    """Hold one fail-closed, process-crash-visible lock for a campaign root."""

    root: Path
    held: bool = False

    @property
    def path(self) -> Path:
        return self.root / LOCK_DIRECTORY

    def __enter__(self) -> "CampaignLock":
        candidate = Path(self.root)
        if not candidate.is_absolute() or _is_link_or_reparse(candidate):
            raise CampaignContractError(
                "campaign root must be an ordinary absolute directory"
            )
        try:
            metadata = candidate.lstat()
        except OSError as exc:
            raise CampaignContractError("campaign root is unavailable") from exc
        if not stat.S_ISDIR(metadata.st_mode):
            raise CampaignContractError("campaign root must be an ordinary directory")
        if os.name != "nt" and metadata.st_mode & 0o077:
            raise CampaignContractError("campaign root must be private to its owner")
        self.root = candidate
        try:
            self.path.mkdir(mode=0o700)
        except FileExistsError as exc:
            raise CampaignBusyError(
                "campaign root is locked; reconcile a stale lock before retrying"
            ) from exc
        except OSError as exc:
            raise CampaignContractError("campaign lock could not be created") from exc
        try:
            _fsync_directory(candidate)
        except OSError as exc:
            raise CampaignContractError("campaign lock could not be made durable") from exc
        self.held = True
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        del traceback
        if not self.held:
            return
        try:
            self.path.rmdir()
            _fsync_directory(self.root)
        except OSError as cleanup_error:
            self.held = False
            if exc_type is None:
                raise CampaignContractError(
                    "campaign lock could not be released; reconcile it before retrying"
                ) from cleanup_error
            return
        self.held = False

    def require(self, root: Path) -> None:
        if not self.held or Path(root) != self.root or not self.path.is_dir():
            raise CampaignContractError("campaign journal requires its held campaign lock")


def _create_file(path: Path, raw: bytes, *, mode: int = 0o600) -> None:
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_BINARY", 0)
    )
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, mode)
    try:
        _write_all(fd, raw)
        os.fsync(fd)
    finally:
        os.close(fd)
    _fsync_directory(path.parent)


def _append_file(path: Path, raw: bytes) -> None:
    flags = (
        os.O_WRONLY
        | os.O_APPEND
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_BINARY", 0)
    )
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags)
    try:
        _write_all(fd, raw)
        os.fsync(fd)
    finally:
        os.close(fd)


def _read_stable(path: Path, *, maximum: int, label: str) -> bytes:
    if _is_link_or_reparse(path):
        raise CampaignContractError(f"{label} must not be a link or reparse point")
    try:
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_size > maximum:
            raise CampaignContractError(f"{label} is not one bounded ordinary file")
        raw = path.read_bytes()
        after = path.lstat()
    except OSError as exc:
        raise CampaignContractError(f"{label} could not be read") from exc
    if (
        before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or before.st_ino != after.st_ino
        or before.st_dev != after.st_dev
        or len(raw) != after.st_size
    ):
        raise CampaignContractError(f"{label} changed while it was read")
    return raw


def _coordinate(spec: codex_harness.TrialSpec) -> dict[str, object]:
    return {
        "scenario_id": spec.scenario_id,
        "cohort": spec.cohort,
        "revision": spec.revision,
        "trial": spec.trial,
        "scenario_sha256": spec.scenario_sha256,
    }


def _coordinate_key(spec: codex_harness.TrialSpec) -> str:
    return hashlib.sha256(_canonical_json(_coordinate(spec))).hexdigest()[:20]


def validate_campaign_plan(plan: Sequence[codex_harness.TrialSpec]) -> None:
    """Require the exact ordered 48-call plan; prefixes and duplicated coordinates are invalid."""

    manifest = run_codex_routing.load_manifest(run_codex_routing.LINUX_MANIFEST_PATH)
    expected = run_codex_routing.campaign_plan(
        manifest, run_codex_routing.CURRENT_REVISION
    )
    if len(plan) != 48 or list(plan) != expected:
        raise CampaignContractError("campaign plan must be the exact ordered 48-call plan")


def _campaign_contract(
    plan: Sequence[codex_harness.TrialSpec],
    manifest_sha256: str,
    container_image_id: str,
) -> dict[str, object]:
    if not isinstance(manifest_sha256, str) or not SHA256_RE.fullmatch(manifest_sha256):
        raise CampaignContractError("manifest_sha256 must be one lowercase SHA-256")
    if not isinstance(container_image_id, str) or not IMAGE_ID_RE.fullmatch(
        container_image_id
    ):
        raise CampaignContractError("container_image_id must be one immutable image ID")
    validate_campaign_plan(plan)
    return {
        "schema_version": 1,
        "campaign": "route-001-codex-terra-linux-v1",
        "manifest_sha256": manifest_sha256,
        "container_image_id": container_image_id,
        "planned_trials": len(plan),
        "plan": [_coordinate(spec) for spec in plan],
        "authority": {
            "independent_evaluator": False,
            "baseline_eligible": False,
            "release_granted": False,
        },
    }


def _validate_result(
    result: Mapping[str, object],
    *,
    spec: codex_harness.TrialSpec,
    manifest_sha256: str,
) -> None:
    scenario = result.get("scenario")
    authority = result.get("authority")
    if result.get("schema_version") != 1 or not isinstance(scenario, Mapping):
        raise CampaignContractError("trial result has an invalid schema")
    expected = {
        "id": spec.scenario_id,
        "cohort": spec.cohort,
        "revision": spec.revision,
        "trial": spec.trial,
        "manifest_sha256": manifest_sha256,
        "scenario_sha256": spec.scenario_sha256,
    }
    if any(scenario.get(key) != value for key, value in expected.items()):
        raise CampaignContractError("trial result coordinate does not match the plan")
    if result.get("state") not in {"PASS", "FAIL", "INCONCLUSIVE"}:
        raise CampaignContractError("trial result has an invalid state")
    if not isinstance(authority, Mapping) or any(
        authority.get(key) is not False
        for key in ("independent_evaluator", "baseline_eligible", "release_granted")
    ):
        raise CampaignContractError("trial result attempts to widen authority")


@dataclass
class CampaignJournal:
    root: Path
    plan: tuple[codex_harness.TrialSpec, ...]
    manifest_sha256: str
    container_image_id: str
    lock: CampaignLock
    completed: int = 0
    unknown_outcome: bool = False
    inconclusive_result: bool = False

    @property
    def contract_path(self) -> Path:
        return self.root / "campaign.json"

    @property
    def ledger_path(self) -> Path:
        return self.root / "ledger.jsonl"

    @property
    def results_root(self) -> Path:
        return self.root / "results"

    @classmethod
    def create(
        cls,
        root: Path,
        *,
        plan: Sequence[codex_harness.TrialSpec],
        manifest_sha256: str,
        container_image_id: str,
        lock: CampaignLock,
    ) -> "CampaignJournal":
        candidate = Path(root)
        lock.require(candidate)
        if not candidate.is_absolute() or _is_link_or_reparse(candidate):
            raise CampaignContractError("campaign root must be an ordinary absolute directory")
        try:
            metadata = candidate.lstat()
            entries = {entry.name for entry in candidate.iterdir()}
            if not stat.S_ISDIR(metadata.st_mode) or entries != {LOCK_DIRECTORY}:
                raise CampaignContractError(
                    "campaign root must be precreated and empty except for its held lock"
                )
        except OSError as exc:
            raise CampaignContractError("campaign root is unavailable") from exc
        if os.name != "nt" and metadata.st_mode & 0o077:
            raise CampaignContractError("campaign root must be private to its owner")
        frozen = tuple(plan)
        contract = _campaign_contract(frozen, manifest_sha256, container_image_id)
        results = candidate / "results"
        results.mkdir(mode=0o700)
        _fsync_directory(candidate)
        _create_file(candidate / "campaign.json", _canonical_json(contract))
        _create_file(candidate / "ledger.jsonl", b"")
        return cls(candidate, frozen, manifest_sha256, container_image_id, lock)

    @classmethod
    def open(
        cls,
        root: Path,
        *,
        plan: Sequence[codex_harness.TrialSpec],
        manifest_sha256: str,
        container_image_id: str,
        lock: CampaignLock,
    ) -> "CampaignJournal":
        candidate = Path(root)
        lock.require(candidate)
        frozen = tuple(plan)
        expected = _canonical_json(
            _campaign_contract(frozen, manifest_sha256, container_image_id)
        )
        if _read_stable(
            candidate / "campaign.json", maximum=MAX_LEDGER_BYTES, label="campaign contract"
        ) != expected:
            raise CampaignContractError("campaign contract bytes do not match the fixed plan")
        results_root = candidate / "results"
        if _is_link_or_reparse(results_root) or not results_root.is_dir():
            raise CampaignContractError("campaign results root is redirected or missing")
        ledger = _read_stable(
            candidate / "ledger.jsonl", maximum=MAX_LEDGER_BYTES, label="campaign ledger"
        )
        instance = cls(
            candidate, frozen, manifest_sha256, container_image_id, lock
        )
        active: int | None = None
        terminal: set[int] = set()
        for line_number, line in enumerate(ledger.splitlines(), start=1):
            if instance.inconclusive_result:
                raise CampaignContractError(
                    "campaign ledger continues after an inconclusive result"
                )
            if not line or len(line) > 64 * 1024:
                raise CampaignContractError("campaign ledger has an invalid line")
            event = _strict_json(line, label=f"campaign ledger line {line_number}")
            if not isinstance(event, dict) or set(event) != {
                "schema_version",
                "event",
                "index",
                "coordinate",
                "manifest_sha256",
                "container_image_id",
                "result",
            }:
                raise CampaignContractError("campaign ledger event has an invalid schema")
            index = event.get("index")
            if (
                event.get("schema_version") != 1
                or not isinstance(index, int)
                or isinstance(index, bool)
                or index < 0
                or index >= len(frozen)
                or event.get("manifest_sha256") != manifest_sha256
                or event.get("container_image_id") != container_image_id
                or event.get("coordinate") != _coordinate(frozen[index])
            ):
                raise CampaignContractError("campaign ledger event does not match the plan")
            kind = event.get("event")
            if kind == "started":
                if event.get("result") is not None or active is not None or index != len(terminal):
                    raise CampaignContractError("campaign ledger has an invalid started event")
                active = index
                continue
            if kind not in {"finished", "unknown"} or active != index or index in terminal:
                raise CampaignContractError("campaign ledger has an invalid terminal event")
            active = None
            if kind == "unknown":
                if event.get("result") is not None:
                    raise CampaignContractError("unknown event must not claim a result")
                instance.unknown_outcome = True
                terminal.add(index)
                continue
            result_ref = event.get("result")
            if not isinstance(result_ref, dict) or set(result_ref) != {"path", "sha256"}:
                raise CampaignContractError("finished event lacks one result reference")
            expected_name = f"{index:02d}-{_coordinate_key(frozen[index])}.json"
            if result_ref.get("path") != expected_name or not isinstance(
                result_ref.get("sha256"), str
            ) or not SHA256_RE.fullmatch(str(result_ref["sha256"])):
                raise CampaignContractError("finished event has an invalid result reference")
            raw = _read_stable(
                results_root / expected_name,
                maximum=MAX_RESULT_BYTES,
                label="campaign result",
            )
            if hashlib.sha256(raw).hexdigest() != result_ref["sha256"]:
                raise CampaignContractError("campaign result digest does not match the ledger")
            parsed = _strict_json(raw, label="campaign result")
            if not isinstance(parsed, dict):
                raise CampaignContractError("campaign result must be a JSON object")
            _validate_result(parsed, spec=frozen[index], manifest_sha256=manifest_sha256)
            if parsed.get("state") == "INCONCLUSIVE":
                instance.inconclusive_result = True
            terminal.add(index)
            instance.completed += 1
        if active is not None:
            instance.unknown_outcome = True
        if terminal and terminal != set(range(max(terminal) + 1)):
            raise CampaignContractError("campaign terminal events are not a strict prefix")
        return instance

    def _event(self, kind: str, index: int, result: object) -> dict[str, object]:
        return {
            "schema_version": 1,
            "event": kind,
            "index": index,
            "coordinate": _coordinate(self.plan[index]),
            "manifest_sha256": self.manifest_sha256,
            "container_image_id": self.container_image_id,
            "result": result,
        }

    def _require_active(self) -> None:
        self.lock.require(self.root)

    def begin(self, spec: codex_harness.TrialSpec) -> None:
        self._require_active()
        if self.unknown_outcome:
            raise UnknownOutcomeError("campaign has an unreconciled unknown outcome")
        if self.inconclusive_result:
            raise CampaignContractError("campaign has a durable inconclusive result")
        if self.completed >= len(self.plan) or spec != self.plan[self.completed]:
            raise CampaignContractError("campaign trial is not the next fixed coordinate")
        _append_file(
            self.ledger_path,
            _canonical_json(self._event("started", self.completed, None)),
        )

    def _record_unknown(self, index: int) -> None:
        _append_file(
            self.ledger_path, _canonical_json(self._event("unknown", index, None))
        )
        self.unknown_outcome = True

    def finish(self, spec: codex_harness.TrialSpec, result: Mapping[str, object]) -> None:
        self._require_active()
        index = self.completed
        if index >= len(self.plan) or spec != self.plan[index]:
            raise CampaignContractError("campaign result is not the next fixed coordinate")
        _validate_result(result, spec=spec, manifest_sha256=self.manifest_sha256)
        raw = _canonical_json(result)
        if len(raw) > MAX_RESULT_BYTES:
            raise CampaignContractError("campaign result exceeds the fixed size bound")
        name = f"{index:02d}-{_coordinate_key(spec)}.json"
        _create_file(self.results_root / name, raw)
        digest = hashlib.sha256(raw).hexdigest()
        _append_file(
            self.ledger_path,
            _canonical_json(
                self._event("finished", index, {"path": name, "sha256": digest})
            ),
        )
        self.completed += 1
        if result.get("state") == "INCONCLUSIVE":
            self.inconclusive_result = True

    def run_next(
        self, runner: Callable[[codex_harness.TrialSpec], Mapping[str, object]]
    ) -> Mapping[str, object]:
        self._require_active()
        if self.unknown_outcome:
            raise UnknownOutcomeError("campaign has an unreconciled unknown outcome")
        if self.inconclusive_result:
            raise CampaignContractError("campaign has a durable inconclusive result")
        if self.completed >= len(self.plan):
            raise CampaignContractError("campaign is already complete")
        index = self.completed
        spec = self.plan[index]
        self.begin(spec)
        try:
            result = runner(spec)
            self.finish(spec, result)
        except BaseException:
            self._record_unknown(index)
            raise
        return result


def run_campaign(
    journal: CampaignJournal,
    runner: Callable[[codex_harness.TrialSpec], Mapping[str, object]],
) -> dict[str, object]:
    """Run one call at a time, stopping immediately on instrument uncertainty."""

    journal._require_active()
    while (
        not journal.unknown_outcome
        and not journal.inconclusive_result
        and journal.completed < len(journal.plan)
    ):
        result = journal.run_next(runner)
        if result.get("state") == "INCONCLUSIVE":
            break
    status = (
        "complete"
        if journal.completed == len(journal.plan)
        and not journal.unknown_outcome
        and not journal.inconclusive_result
        else "blocked"
    )
    return {
        "schema_version": 1,
        "campaign": "route-001-codex-terra-linux-v1",
        "container_image_id": journal.container_image_id,
        "status": status,
        "planned_trials": len(journal.plan),
        "completed_trials": journal.completed,
        "unknown_outcome": journal.unknown_outcome,
        "inconclusive_result": journal.inconclusive_result,
        "authority": {
            "independent_evaluator": False,
            "baseline_eligible": False,
            "release_granted": False,
        },
    }
