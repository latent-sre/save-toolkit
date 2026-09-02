from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator, Mapping, Sequence
from contextlib import AbstractContextManager
from dataclasses import asdict, dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.sqlite import SqliteSaver

from runner.events import BoundaryEventStore

from runner.models import CONTRACT_VERSION, STATE_SCHEMA_VERSION
from runner.validation import validate_source_revision


class CheckpointIncompatible(RuntimeError):
    def __init__(self, mismatches: dict[str, tuple[str, str]]) -> None:
        super().__init__(f"checkpoint fingerprint mismatch: {', '.join(sorted(mismatches))}")
        self.mismatches = mismatches


@dataclass(frozen=True)
class CheckpointFingerprint:
    contract_version: str
    state_schema: str
    source_revision: str
    langgraph_version: str
    sqlite_saver_version: str

    @classmethod
    def current(cls, source_revision: str) -> "CheckpointFingerprint":
        validate_source_revision(source_revision)
        return cls(
            contract_version=CONTRACT_VERSION,
            state_schema=STATE_SCHEMA_VERSION,
            source_revision=source_revision,
            langgraph_version=version("langgraph"),
            sqlite_saver_version=version("langgraph-checkpoint-sqlite"),
        )


class ObservedCheckpointSaver(BaseCheckpointSaver[Any]):
    """Delegate to the real saver while recording the exact checkpoint writes."""

    def __init__(
        self,
        delegate: SqliteSaver,
        events: BoundaryEventStore,
        event_state: Mapping[str, object],
    ) -> None:
        super().__init__(serde=delegate.serde)
        self.delegate = delegate
        self.events = events
        self.event_state = dict(event_state)

    @property
    def config_specs(self) -> list[Any]:
        return self.delegate.config_specs

    def get_tuple(self, config: Any) -> Any:
        return self.delegate.get_tuple(config)

    def list(
        self,
        config: Any,
        *,
        filter: dict[str, Any] | None = None,
        before: Any = None,
        limit: int | None = None,
    ) -> Iterator[Any]:
        return self.delegate.list(config, filter=filter, before=before, limit=limit)

    def put(
        self,
        config: Any,
        checkpoint: Any,
        metadata: Any,
        new_versions: Any,
    ) -> Any:
        checkpoint_id = checkpoint.get("id")
        if not isinstance(checkpoint_id, str) or not checkpoint_id:
            raise ValueError("checkpoint write lacks a checkpoint ID")
        self.events.emit(
            "checkpoint.write_started",
            self.event_state,
            {"operation": "write"},
            node_id="checkpoint-store",
            checkpoint_id=checkpoint_id,
        )
        try:
            result = self.delegate.put(config, checkpoint, metadata, new_versions)
        except Exception:
            configurable = config.get("configurable", {})
            probe_config = {
                "configurable": {
                    **configurable,
                    "checkpoint_id": checkpoint_id,
                }
            }
            try:
                committed = self.delegate.get_tuple(probe_config) is not None
            except Exception:
                committed = None
            if committed is True:
                self.events.emit(
                    "checkpoint.write_completed",
                    self.event_state,
                    {"operation": "write", "result": "recorded"},
                    node_id="checkpoint-store",
                    checkpoint_id=checkpoint_id,
                )
            elif committed is False:
                self.events.emit(
                    "checkpoint.write_failed",
                    self.event_state,
                    {"operation": "write", "result": "failed"},
                    node_id="checkpoint-store",
                    checkpoint_id=checkpoint_id,
                    failure_plane="checkpoint-store",
                    error_class="checkpoint-write-failed",
                )
            raise
        self.events.emit(
            "checkpoint.write_completed",
            self.event_state,
            {"operation": "write", "result": "recorded"},
            node_id="checkpoint-store",
            checkpoint_id=checkpoint_id,
        )
        return result

    def put_writes(
        self,
        config: Any,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        self.delegate.put_writes(config, writes, task_id, task_path)

    def delete_thread(self, thread_id: str) -> None:
        self.delegate.delete_thread(thread_id)

    def get_next_version(self, current: Any, channel: Any) -> Any:
        return self.delegate.get_next_version(current, channel)


def reconcile_interrupted_checkpoint_events(
    saver: SqliteSaver,
    events: BoundaryEventStore,
    event_state: Mapping[str, object],
) -> str | None:
    """Close crash-interrupted write/resume evidence from durable saver state."""

    thread_id = event_state.get("thread_id")
    if not isinstance(thread_id, str):
        raise ValueError("checkpoint recovery requires a thread_id")
    config = {"configurable": {"thread_id": thread_id}}
    saver_ids = []
    for item in reversed(list(saver.list(config))):
        configurable = item.config.get("configurable", {})
        checkpoint_id = configurable.get("checkpoint_id")
        if not isinstance(checkpoint_id, str) or not checkpoint_id:
            raise RuntimeError("configured SQLite saver returned a checkpoint without an ID")
        saver_ids.append(checkpoint_id)
    saver_positions = {checkpoint_id: index for index, checkpoint_id in enumerate(saver_ids)}

    projected = events.project()
    pending_writes: dict[str, Mapping[str, object]] = {}
    failed_write_ids: set[str] = set()
    for event in projected:
        event_type = event["event_type"]
        checkpoint_id = event["checkpoint_id"]
        if event_type == "checkpoint.write_started":
            if not isinstance(checkpoint_id, str) or checkpoint_id in pending_writes:
                raise RuntimeError("checkpoint evidence contains an overlapping write")
            pending_writes[checkpoint_id] = event
        elif event_type in {"checkpoint.write_completed", "checkpoint.write_failed"}:
            if not isinstance(checkpoint_id, str) or checkpoint_id not in pending_writes:
                raise RuntimeError("checkpoint evidence contains an unpaired write result")
            pending_writes.pop(checkpoint_id)
            if event_type == "checkpoint.write_failed":
                failed_write_ids.add(checkpoint_id)
    contradiction = failed_write_ids & set(saver_ids)
    if contradiction:
        raise RuntimeError("failed checkpoint write is present in the configured saver")
    for checkpoint_id, started in sorted(
        pending_writes.items(), key=lambda item: int(item[1]["sequence"])
    ):
        if checkpoint_id in saver_positions:
            events.emit(
                "checkpoint.write_completed",
                event_state,
                {"operation": "write", "result": "recorded"},
                node_id="checkpoint-store",
                checkpoint_id=checkpoint_id,
            )
        else:
            events.emit(
                "checkpoint.write_failed",
                event_state,
                {"operation": "write", "result": "failed"},
                node_id="checkpoint-store",
                checkpoint_id=checkpoint_id,
                failure_plane="checkpoint-store",
                error_class="checkpoint-write-interrupted",
            )

    projected = events.project()
    pending_resume: Mapping[str, object] | None = None
    last_successful_source: str | None = None
    for event in projected:
        event_type = event["event_type"]
        if event_type == "checkpoint.resume_started":
            if pending_resume is not None:
                raise RuntimeError("checkpoint evidence contains overlapping resumes")
            pending_resume = event
        elif event_type in {"checkpoint.resume_completed", "checkpoint.resume_failed"}:
            if pending_resume is None:
                raise RuntimeError("checkpoint evidence contains an unpaired resume result")
            source_id = pending_resume["checkpoint_id"]
            result_id = event["checkpoint_id"]
            if not isinstance(source_id, str) or not isinstance(result_id, str):
                raise RuntimeError("checkpoint resume evidence lacks an ID")
            if event_type == "checkpoint.resume_completed":
                if (
                    source_id not in saver_positions
                    or result_id not in saver_positions
                    or saver_positions[result_id] <= saver_positions[source_id]
                ):
                    raise RuntimeError("checkpoint resume result is not a recorded descendant")
                last_successful_source = source_id
            elif result_id != source_id:
                raise RuntimeError("failed checkpoint resume must name its source")
            pending_resume = None

    if pending_resume is not None:
        source_id = pending_resume["checkpoint_id"]
        if not isinstance(source_id, str) or source_id not in saver_positions:
            raise RuntimeError("interrupted checkpoint resume source is absent from saver")
        latest_id = saver_ids[-1]
        if saver_positions[latest_id] > saver_positions[source_id]:
            events.emit(
                "checkpoint.resume_completed",
                event_state,
                {"operation": "resume", "result": "completed"},
                node_id="terminal",
                checkpoint_id=latest_id,
            )
            last_successful_source = source_id
        else:
            events.emit(
                "checkpoint.resume_failed",
                event_state,
                {"operation": "resume", "result": "failed"},
                node_id="terminal",
                checkpoint_id=source_id,
                failure_plane="checkpoint-store",
                error_class="checkpoint-resume-interrupted",
            )
    return last_successful_source


class CheckpointStore(AbstractContextManager[SqliteSaver]):
    def __init__(self, path: Path, fingerprint: CheckpointFingerprint) -> None:
        self.path = path
        self.fingerprint = fingerprint
        self._saver_context: Any = None
        self._saver: SqliteSaver | None = None

    def __enter__(self) -> SqliteSaver:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._validate_or_initialize()
        self._saver_context = SqliteSaver.from_conn_string(str(self.path))
        self._saver = self._saver_context.__enter__()
        return self._saver

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> bool | None:
        if self._saver_context is None:
            return None
        return self._saver_context.__exit__(exc_type, exc, traceback)

    def _validate_or_initialize(self) -> None:
        expected = asdict(self.fingerprint)
        with sqlite3.connect(self.path, timeout=5.0) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS graph_runtime_metadata (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    fingerprint_json TEXT NOT NULL
                )
                """
            )
            row = connection.execute(
                "SELECT fingerprint_json FROM graph_runtime_metadata WHERE singleton = 1"
            ).fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO graph_runtime_metadata(singleton, fingerprint_json) VALUES (1, ?)",
                    (json.dumps(expected, sort_keys=True, separators=(",", ":")),),
                )
                return
            actual = json.loads(row[0])
            mismatches = {
                key: (str(actual.get(key)), str(value))
                for key, value in expected.items()
                if actual.get(key) != value
            }
            if mismatches:
                raise CheckpointIncompatible(mismatches)

    @staticmethod
    def read_fingerprint(path: Path) -> CheckpointFingerprint:
        with sqlite3.connect(path, timeout=5.0) as connection:
            row = connection.execute(
                "SELECT fingerprint_json FROM graph_runtime_metadata WHERE singleton = 1"
            ).fetchone()
        if row is None:
            raise ValueError("checkpoint fingerprint is missing")
        return CheckpointFingerprint(**json.loads(row[0]))
