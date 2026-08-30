from __future__ import annotations

import json
import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from runner.validation import (
    validate_atomic_id,
    validate_derived_id,
    validate_sha256,
    validate_source_revision,
)


def _epoch_ms() -> int:
    return time.time_ns() // 1_000_000


@dataclass(frozen=True)
class DurableWallTimeBudget:
    """An identity-bound wall-clock deadline that survives runner processes."""

    path: Path
    started_epoch_ms: int
    deadline_epoch_ms: int
    limit_ms: int
    clock_ms: Callable[[], int]

    @classmethod
    def acquire(
        cls,
        path: Path,
        *,
        run_id: str,
        thread_id: str,
        source_revision: str,
        case_digest: str,
        limit_ms: int,
        clock_ms: Callable[[], int] = _epoch_ms,
    ) -> "DurableWallTimeBudget":
        validate_atomic_id(run_id, "run_id")
        validate_derived_id(thread_id, "thread_id")
        validate_source_revision(source_revision)
        validate_sha256(case_digest, "case_digest")
        if isinstance(limit_ms, bool) or not isinstance(limit_ms, int) or limit_ms <= 0:
            raise ValueError("wall-time limit must be a positive integer")
        if not path.is_absolute():
            raise ValueError("wall-time budget path must be absolute")
        now_ms = clock_ms()
        if isinstance(now_ms, bool) or not isinstance(now_ms, int) or now_ms < 0:
            raise ValueError("wall-time clock must return non-negative integer milliseconds")

        identity = {
            "budget_version": "graph-wall-time-budget/v1",
            "run_id": run_id,
            "thread_id": thread_id,
            "source_revision": source_revision,
            "case_digest": case_digest,
            "limit_ms": limit_ms,
        }
        encoded_identity = json.dumps(identity, sort_keys=True, separators=(",", ":"))
        path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(path, timeout=5.0) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS durable_wall_time_budget (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    identity_json TEXT NOT NULL,
                    started_epoch_ms INTEGER NOT NULL,
                    deadline_epoch_ms INTEGER NOT NULL
                )
                """
            )
            row = connection.execute(
                """
                SELECT identity_json, started_epoch_ms, deadline_epoch_ms
                FROM durable_wall_time_budget
                WHERE singleton = 1
                """
            ).fetchone()
            if row is None:
                started_epoch_ms = now_ms
                deadline_epoch_ms = now_ms + limit_ms
                connection.execute(
                    """
                    INSERT INTO durable_wall_time_budget(
                        singleton, identity_json, started_epoch_ms, deadline_epoch_ms
                    ) VALUES (1, ?, ?, ?)
                    """,
                    (encoded_identity, started_epoch_ms, deadline_epoch_ms),
                )
            else:
                actual_identity, started_epoch_ms, deadline_epoch_ms = row
                if actual_identity != encoded_identity:
                    raise ValueError("wall-time budget identity mismatch")
                if (
                    isinstance(started_epoch_ms, bool)
                    or not isinstance(started_epoch_ms, int)
                    or isinstance(deadline_epoch_ms, bool)
                    or not isinstance(deadline_epoch_ms, int)
                    or deadline_epoch_ms - started_epoch_ms != limit_ms
                ):
                    raise ValueError("wall-time budget record is invalid")

        return cls(path, started_epoch_ms, deadline_epoch_ms, limit_ms, clock_ms)

    def elapsed_ms(self) -> int:
        return max(0, self.clock_ms() - self.started_epoch_ms)

    def remaining_ms(self) -> int:
        return max(0, self.deadline_epoch_ms - self.clock_ms())
