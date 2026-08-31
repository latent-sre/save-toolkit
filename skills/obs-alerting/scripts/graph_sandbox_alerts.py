#!/usr/bin/env python3
"""Evaluate the synthetic GRAPH-003 alert against verified graph-sandbox bundles.

The evaluator is intentionally deployment-free. It reads evidence already published by
``graph-sandbox/activate.py`` and emits a deterministic timeline for the one synthetic page:
``GraphSandboxRunNeedsAction``. It never contacts Grafana, a notification route, or a live system.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Iterable, Mapping


CONTRACT_VERSION = "checkout-payments-timeout-drill/v1"
EVIDENCE_VERSION = "graph-evidence/v2"
EVENT_VERSION = "graph-boundary-event/v2"
SANDBOX_VERSION = "graph-sandbox/v1"
VERIFICATION_VERSIONS = {
    "graph-sandbox-host-verification/v1",
    "graph-sandbox-host-verification/v2",
}
TERMINAL_EVENTS = {"run.terminal", "run.cancelled", "run.inconclusive"}
TERMINAL_EFFECT_STATES = {"RECEIPT_RECORDED", "RECONCILED", "UNKNOWN"}
CHECKSUM_LINE_RE = re.compile(r"([0-9a-f]{64})  ([^\r\n]+)")
REQUIRED_BUNDLE_ARTIFACTS = {
    "effects.jsonl",
    "events.jsonl",
    "manifest.json",
    "verification.json",
}


class EvidenceError(ValueError):
    """Raised when an input cannot be trusted as one verified sandbox evidence bundle."""


def _verify_checksums(directory: Path) -> set[str]:
    checksum_path = directory / "checksums.sha256"
    try:
        lines = checksum_path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise EvidenceError(f"checksums.sha256 is not readable UTF-8 text: {exc}") from exc
    if not lines:
        raise EvidenceError("checksums.sha256 must not be empty")

    names: set[str] = set()
    for line_number, line in enumerate(lines, start=1):
        match = CHECKSUM_LINE_RE.fullmatch(line)
        if match is None:
            raise EvidenceError(
                f"checksums.sha256:{line_number} must be lowercase SHA-256, two spaces, and path"
            )
        expected, name = match.groups()
        relative = PurePosixPath(name)
        if (
            relative.is_absolute()
            or relative.as_posix() != name
            or ".." in relative.parts
            or "\\" in name
        ):
            raise EvidenceError(f"checksums.sha256:{line_number} has an unsafe artifact path")
        if name in names:
            raise EvidenceError(f"checksums.sha256 contains duplicate artifact {name!r}")

        artifact = directory.joinpath(*relative.parts).resolve()
        if not artifact.is_relative_to(directory) or not artifact.is_file():
            raise EvidenceError(f"checksum artifact is missing or outside the bundle: {name!r}")
        actual = hashlib.sha256(artifact.read_bytes()).hexdigest()
        if actual != expected:
            raise EvidenceError(f"checksum mismatch for artifact {name!r}")
        names.add(name)

    missing = REQUIRED_BUNDLE_ARTIFACTS - names
    if missing:
        raise EvidenceError(f"checksums.sha256 omits required artifacts: {sorted(missing)}")
    return names


def _read_json(path: Path, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"{label} is not readable UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"{label} must be one JSON object")
    return value


def _read_jsonl(path: Path, label: str, *, allow_empty: bool = False) -> list[dict[str, object]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise EvidenceError(f"{label} is not readable UTF-8 JSONL: {exc}") from exc
    if not lines and not allow_empty:
        raise EvidenceError(f"{label} must not be empty")
    records: list[dict[str, object]] = []
    for line_number, line in enumerate(lines, start=1):
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EvidenceError(f"{label}:{line_number} is invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise EvidenceError(f"{label}:{line_number} must be one JSON object")
        records.append(value)
    return records


def _required(mapping: Mapping[str, object], key: str, expected: type, label: str):
    value = mapping.get(key)
    if not isinstance(value, expected):
        raise EvidenceError(f"{label}.{key} must be {expected.__name__}")
    return value


def _timestamp(value: object, label: str) -> datetime:
    if not isinstance(value, str):
        raise EvidenceError(f"{label} must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise EvidenceError(f"{label} is not an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise EvidenceError(f"{label} must carry a timezone")
    return parsed


def _bounded_strings(values: Iterable[object]) -> list[str]:
    return sorted({value for value in values if isinstance(value, str) and value})


def _terminal_effects(
    effects: list[dict[str, object]], label: str
) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = {}
    for index, effect in enumerate(effects, start=1):
        effect_id = _required(effect, "effect_id", str, f"{label}:{index}")
        state = _required(effect, "effect_state", str, f"{label}:{index}")
        sequence = effect.get("sequence")
        if not isinstance(sequence, int) or sequence < 1:
            raise EvidenceError(f"{label}:{index}.sequence must be a positive integer")
        if state not in {"PREPARED", "DISPATCHED", *TERMINAL_EFFECT_STATES}:
            raise EvidenceError(f"{label}:{index}.effect_state is not in the closed vocabulary")
        grouped.setdefault(effect_id, []).append(effect)

    terminal: dict[str, dict[str, object]] = {}
    for effect_id, records in grouped.items():
        ordered = sorted(records, key=lambda record: int(record["sequence"]))
        sequences = [int(record["sequence"]) for record in ordered]
        if sequences != list(range(1, len(sequences) + 1)):
            raise EvidenceError(f"{label}: effect {effect_id!r} sequences are not contiguous")
        state = str(ordered[-1]["effect_state"])
        if state not in TERMINAL_EFFECT_STATES:
            raise EvidenceError(f"{label}: effect {effect_id!r} has no terminal state")
        authoritative_result_id = None
        if state in {"RECEIPT_RECORDED", "RECONCILED"}:
            receipt = ordered[-1].get("receipt")
            if not isinstance(receipt, dict):
                raise EvidenceError(f"{label}: effect {effect_id!r} lacks an authoritative receipt")
            authoritative_result_id = _required(
                receipt,
                "authoritative_result_id",
                str,
                f"{label}: effect {effect_id!r}.receipt",
            )
        terminal[effect_id] = {
            "authoritative_result_id": authoritative_result_id,
            "state": state,
        }
    return terminal


def _load_bundle(directory: Path) -> dict[str, object]:
    directory = Path(directory).resolve()
    if not directory.is_dir():
        raise EvidenceError(f"evidence directory does not exist: {directory}")

    checksum_names = _verify_checksums(directory)
    manifest = _read_json(directory / "manifest.json", f"{directory}/manifest.json")
    verification = _read_json(
        directory / "verification.json", f"{directory}/verification.json"
    )
    events = _read_jsonl(directory / "events.jsonl", f"{directory}/events.jsonl")
    effects = _read_jsonl(
        directory / "effects.jsonl", f"{directory}/effects.jsonl", allow_empty=True
    )

    run_id = _required(manifest, "run_id", str, "manifest")
    case_id = _required(manifest, "case_id", str, "manifest")
    source_revision = _required(manifest, "source_revision", str, "manifest")
    outcome = _required(manifest, "outcome", str, "manifest")
    started = _timestamp(manifest.get("started_at"), "manifest.started_at")
    ended = _timestamp(manifest.get("ended_at"), "manifest.ended_at")
    artifacts = manifest.get("artifacts")
    if (
        not isinstance(artifacts, list)
        or not artifacts
        or not all(isinstance(name, str) and name for name in artifacts)
        or len(artifacts) != len(set(artifacts))
    ):
        raise EvidenceError("manifest.artifacts must be a non-empty unique string list")
    expected_checksums = set(artifacts) | {"manifest.json"}
    if checksum_names != expected_checksums:
        raise EvidenceError("checksum inventory does not exactly match manifest.artifacts")
    if ended < started:
        raise EvidenceError("manifest.ended_at precedes manifest.started_at")
    if (
        manifest.get("contract_version") != CONTRACT_VERSION
        or manifest.get("evidence_version") != EVIDENCE_VERSION
        or manifest.get("sandbox_version") != SANDBOX_VERSION
    ):
        raise EvidenceError("manifest contract/evidence/sandbox version mismatch")
    if len(source_revision) != 40 or any(character not in "0123456789abcdef" for character in source_revision):
        raise EvidenceError("manifest.source_revision must be 40 lowercase hexadecimal characters")

    verification_version = verification.get("verification_version")
    snapshot_role = verification.get("snapshot_role")
    if (
        verification_version not in VERIFICATION_VERSIONS
        or verification.get("run_id") != run_id
        or verification.get("source_revision") != source_revision
    ):
        raise EvidenceError("verification identity does not match manifest")
    if verification_version == "graph-sandbox-host-verification/v1":
        if snapshot_role is not None:
            raise EvidenceError("v1 verification cannot carry a snapshot role")
    elif (
        snapshot_role not in {"UNKNOWN", "RECONCILED"}
        or (snapshot_role == "UNKNOWN" and outcome != "UNKNOWN")
        or (snapshot_role == "RECONCILED" and outcome != "SUCCEEDED")
        or verification.get("runner_container_exit")
        != {"Status": "exited", "ExitCode": 0, "OOMKilled": False}
    ):
        raise EvidenceError("v2 verification snapshot role contradicts manifest")
    expected_exit = 0 if outcome == "SUCCEEDED" else 2
    if verification.get("exit_code") != expected_exit:
        raise EvidenceError("verification exit_code contradicts manifest outcome")

    sequences: list[int] = []
    for index, event in enumerate(events, start=1):
        sequence = event.get("sequence")
        if not isinstance(sequence, int) or sequence < 1:
            raise EvidenceError(f"events.jsonl:{index}.sequence must be a positive integer")
        sequences.append(sequence)
        if (
            event.get("event_version") != EVENT_VERSION
            or event.get("run_id") != run_id
            or event.get("case_id") != case_id
            or event.get("source_revision") != source_revision
            or event.get("contract_version") != CONTRACT_VERSION
            or event.get("sandbox_version") != SANDBOX_VERSION
        ):
            raise EvidenceError(f"events.jsonl:{index} identity does not match manifest")
        _timestamp(event.get("time_utc"), f"events.jsonl:{index}.time_utc")
    if sequences != list(range(1, len(events) + 1)):
        raise EvidenceError("events.jsonl sequences must be contiguous from one")
    if [event.get("event_type") for event in events[:2]] != ["run.accepted", "run.started"]:
        raise EvidenceError("events.jsonl run start prefix must be run.accepted, run.started")
    terminal_events = [event for event in events if event.get("event_type") in TERMINAL_EVENTS]
    if len(terminal_events) != 1 or terminal_events[0] is not events[-1]:
        raise EvidenceError("events.jsonl must contain exactly one final terminal run event")

    terminal_data = events[-1].get("data")
    if not isinstance(terminal_data, dict) or terminal_data.get("outcome") != outcome:
        raise EvidenceError("terminal event outcome does not match manifest")

    terminal_effects = _terminal_effects(effects, "effects.jsonl")
    if outcome == "SUCCEEDED":
        authoritative_result_id = manifest.get("authoritative_result_id")
        if not isinstance(authoritative_result_id, str) or not authoritative_result_id:
            raise EvidenceError("SUCCEEDED manifest lacks an authoritative result")
        if (
            events[-1].get("event_type") != "run.terminal"
            or terminal_data.get("authoritative_result_id") != authoritative_result_id
        ):
            raise EvidenceError("SUCCEEDED terminal event lacks the authoritative result")
        authoritative_effects = [
            (effect_id, terminal)
            for effect_id, terminal in terminal_effects.items()
            if terminal["state"] in {"RECEIPT_RECORDED", "RECONCILED"}
            and terminal["authoritative_result_id"] == authoritative_result_id
        ]
        if len(authoritative_effects) != 1:
            raise EvidenceError("SUCCEEDED bundle must contain one authoritative effect receipt")
        effect_id, authoritative_effect = authoritative_effects[0]
        expected_event_type = (
            "effect.reconciled"
            if authoritative_effect["state"] == "RECONCILED"
            else "effect.receipt_recorded"
        )
        matching_events = [
            event
            for event in events
            if event.get("event_type") == expected_event_type
            and event.get("effect_id") == effect_id
            and isinstance(event.get("data"), dict)
            and event["data"].get("authoritative_result_id") == authoritative_result_id
        ]
        if len(matching_events) != 1:
            raise EvidenceError("SUCCEEDED events lack the authoritative effect receipt")

    event_types = Counter(str(event.get("event_type")) for event in events)
    terminal_time = _timestamp(events[-1].get("time_utc"), "terminal event time")
    checkpoint_times = [
        _timestamp(event.get("time_utc"), "checkpoint completion time")
        for event in events
        if event.get("event_type") == "checkpoint.write_completed"
    ]
    checkpoint_age = None
    if checkpoint_times:
        checkpoint_age = max(0.0, (terminal_time - max(checkpoint_times)).total_seconds())

    approval_events = [
        event for event in events if str(event.get("event_type", "")).startswith("approval.")
    ]
    approval_wait = None
    if len(approval_events) >= 2:
        approval_wait = max(
            0.0,
            (
                _timestamp(approval_events[-1].get("time_utc"), "approval decision time")
                - _timestamp(approval_events[0].get("time_utc"), "approval request time")
            ).total_seconds(),
        )

    return {
        "path": directory.as_posix(),
        "run_id": run_id,
        "case_id": case_id,
        "source_revision": source_revision,
        "outcome": outcome,
        "snapshot_role": snapshot_role,
        "started_at": manifest["started_at"],
        "ended_at": manifest["ended_at"],
        "ended_sort": ended,
        "duration_seconds": round((ended - started).total_seconds(), 6),
        "failure_planes": _bounded_strings(event.get("failure_plane") for event in events),
        "error_classes": _bounded_strings(event.get("error_class") for event in events),
        "event_counts": dict(sorted(event_types.items())),
        "approval_wait_seconds": None if approval_wait is None else round(approval_wait, 6),
        "checkpoint_completion_age_seconds": (
            None if checkpoint_age is None else round(checkpoint_age, 6)
        ),
        "event_records": events,
        "effect_records": effects,
        "terminal_effects": terminal_effects,
    }


def _validate_same_run_snapshot(
    earlier: Mapping[str, object], later: Mapping[str, object]
) -> None:
    run_id = str(earlier["run_id"])
    if (
        earlier["case_id"] != later["case_id"]
        or earlier["source_revision"] != later["source_revision"]
        or earlier["started_at"] != later["started_at"]
    ):
        raise EvidenceError(f"run {run_id!r} snapshots disagree on immutable identity")
    if later["ended_sort"] <= earlier["ended_sort"]:
        raise EvidenceError(f"run {run_id!r} snapshots are not strictly ordered")
    if earlier["outcome"] != "UNKNOWN" or later["outcome"] != "SUCCEEDED":
        raise EvidenceError(f"run {run_id!r} has an unsupported snapshot outcome transition")
    if (
        earlier.get("snapshot_role") is not None
        or later.get("snapshot_role") is not None
    ) and (
        earlier.get("snapshot_role") != "UNKNOWN"
        or later.get("snapshot_role") != "RECONCILED"
    ):
        raise EvidenceError(f"run {run_id!r} snapshot roles are invalid")

    earlier_events = list(earlier["event_records"])
    later_events = list(later["event_records"])
    if (
        len(later_events) <= len(earlier_events)
        or earlier_events[:-1] != later_events[: len(earlier_events) - 1]
    ):
        raise EvidenceError(f"run {run_id!r} later snapshot does not extend event history")
    earlier_effects = list(earlier["effect_records"])
    later_effects = list(later["effect_records"])
    if (
        len(later_effects) <= len(earlier_effects)
        or earlier_effects != later_effects[: len(earlier_effects)]
    ):
        raise EvidenceError(f"run {run_id!r} later snapshot does not extend effect history")

    earlier_terminal = dict(earlier["terminal_effects"])
    later_terminal = dict(later["terminal_effects"])
    if set(earlier_terminal) != set(later_terminal) or any(
        terminal["state"] != "UNKNOWN" for terminal in earlier_terminal.values()
    ):
        raise EvidenceError(f"run {run_id!r} earlier snapshot is not unresolved UNKNOWN evidence")
    if any(
        later_terminal[effect_id]["state"] != "RECONCILED"
        for effect_id in earlier_terminal
    ):
        raise EvidenceError(f"run {run_id!r} later snapshot does not reconcile the same effect")


def evaluate_timeline(evidence_directories: Iterable[Path]) -> dict[str, object]:
    """Return observations and state transitions for a chronological evidence timeline."""

    bundles = [_load_bundle(Path(directory)) for directory in evidence_directories]
    if not bundles:
        raise EvidenceError("at least one evidence directory is required")
    bundles.sort(key=lambda bundle: (bundle["ended_sort"], str(bundle["run_id"])))
    latest_by_run: dict[str, Mapping[str, object]] = {}
    for bundle in bundles:
        run_id = str(bundle["run_id"])
        earlier = latest_by_run.get(run_id)
        if earlier is not None:
            _validate_same_run_snapshot(earlier, bundle)
        latest_by_run[run_id] = bundle

    unresolved: set[str] = set()
    observations: list[dict[str, object]] = []
    transitions: list[dict[str, object]] = []
    prior_state = "NOT_EVALUATED"
    for bundle in bundles:
        for effect_id, terminal in dict(bundle["terminal_effects"]).items():
            effect_state = terminal["state"]
            if effect_state == "UNKNOWN":
                unresolved.add(effect_id)
            elif effect_state in {"RECEIPT_RECORDED", "RECONCILED"}:
                unresolved.discard(effect_id)
        state = (
            "FIRING"
            if bundle["outcome"] != "SUCCEEDED" or unresolved
            else "RESOLVED"
        )
        observation = {
            key: value
            for key, value in bundle.items()
            if key not in {"effect_records", "ended_sort", "event_records", "terminal_effects"}
        }
        observation.update(
            {
                "alert_state": state,
                "unresolved_unknown_effects": len(unresolved),
                "unresolved_effect_ids": sorted(unresolved),
            }
        )
        observations.append(observation)
        if state != prior_state:
            transitions.append(
                {
                    "at_run_id": bundle["run_id"],
                    "transition": f"{prior_state}->{state}",
                }
            )
            prior_state = state

    final = observations[-1]
    return {
        "evaluation_version": "graph-sandbox-alert-evaluation/v1",
        "rule": {
            "name": "GraphSandboxRunNeedsAction",
            "severity": "page",
            "owner": "sre",
            "first_action": (
                "Inspect the latest verified evidence bundle and follow the matching "
                "failure-plane branch in the graph-sandbox operations runbook."
            ),
            "notification_route": None,
        },
        "observations": observations,
        "transitions": transitions,
        "final_alert": {
            "state": final["alert_state"],
            "run_id": final["run_id"],
            "unresolved_unknown_effects": final["unresolved_unknown_effects"],
            "unresolved_effect_ids": final["unresolved_effect_ids"],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate GraphSandboxRunNeedsAction against one or more verified graph-sandbox "
            "evidence directories. Inputs are ordered by manifest.ended_at."
        )
    )
    parser.add_argument("evidence_directory", nargs="+", type=Path)
    args = parser.parse_args(argv)
    try:
        result = evaluate_timeline(args.evidence_directory)
    except EvidenceError as exc:
        print(f"graph_sandbox_alerts: FAIL: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
