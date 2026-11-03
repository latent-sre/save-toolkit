"""An attempt's life as a state machine written to attempt.json (stage 3 of the runner rewrite)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from probe import attempt as attempts
from probe.attempt import Attempt, IllegalTransition, Phase
from probe.records import AttemptState


def _saved(run_dir: Path) -> dict:
    return json.loads((run_dir / "attempt.json").read_text(encoding="utf-8"))


def test_an_attempt_records_each_phase_it_passes_through(tmp_path: Path) -> None:
    life = Attempt.begin(tmp_path, 3)
    assert _saved(tmp_path)["phase"] == "prepared" and _saved(tmp_path)["state"] == "final"
    for phase in (Phase.SERVED, Phase.SEEDED, Phase.INVOKED, Phase.OBSERVED, Phase.GRADED, Phase.PUBLISHED):
        life.advance(phase)
    saved = _saved(tmp_path)
    assert saved["attempt"] == 3 and saved["state"] == "final" and saved["phase"] == "published"
    assert [p["phase"] for p in saved["phases"]] == [
        "prepared",
        "served",
        "seeded",
        "invoked",
        "observed",
        "graded",
        "published",
    ]
    assert all(p["at"] for p in saved["phases"])


def test_a_step_the_runner_skipped_is_a_defect_not_a_record(tmp_path: Path) -> None:
    life = Attempt.begin(tmp_path, 1)
    with pytest.raises(IllegalTransition):
        life.advance(Phase.SEEDED)
    assert _saved(tmp_path)["phase"] == "prepared", "nothing is recorded for a refused move"
    life.advance(Phase.SERVED)
    life.advance(Phase.SEEDED)
    life.advance(Phase.OBSERVED)  # a backing service that never starts skips the CLI
    assert _saved(tmp_path)["phase"] == "observed"


def test_an_attempt_that_raised_shows_where_it_stopped(tmp_path: Path) -> None:
    life = Attempt.begin(tmp_path, 2)
    life.advance(Phase.SERVED)
    life.advance(Phase.INCOMPLETE, "RuntimeError: fixture unavailable")
    saved = _saved(tmp_path)
    assert saved["state"] == AttemptState.INCOMPLETE and saved["reason"] == "RuntimeError: fixture unavailable"
    assert [p["phase"] for p in saved["phases"]] == ["prepared", "served", "incomplete"]
    assert saved["phases"][-1]["note"] == "RuntimeError: fixture unavailable"
    with pytest.raises(IllegalTransition):
        life.advance(Phase.PUBLISHED)


def test_void_and_stopped_are_reachable_from_grading_and_still_publish(tmp_path: Path) -> None:
    for failure, note in ((Phase.VOID, "plugin inputs changed"), (Phase.STOPPED, "grader error: x")):
        run = tmp_path / failure
        run.mkdir()
        life = Attempt.begin(run, 1)
        for phase in (Phase.SERVED, Phase.SEEDED, Phase.INVOKED, Phase.OBSERVED, Phase.GRADED):
            life.advance(phase)
        life.advance(failure, note)
        life.advance(Phase.PUBLISHED)
        saved = _saved(run)
        assert saved["state"] == "final" and [p["phase"] for p in saved["phases"]][-2:] == [failure, "published"]
        assert saved["phases"][-2]["note"] == note


def test_a_later_state_write_keeps_the_phase_log(tmp_path: Path) -> None:
    """`_keep_attempt` renames an attempt and writes its final state without the machine; the log
    it recorded must survive that write."""
    life = Attempt.begin(tmp_path, 4)
    life.advance(Phase.SERVED)
    attempts.record_state(tmp_path, 4, AttemptState.SUPERSEDED, "replaced by attempt 5")
    saved = _saved(tmp_path)
    assert saved["state"] == "superseded" and saved["reason"] == "replaced by attempt 5"
    assert saved["phase"] == "served" and [p["phase"] for p in saved["phases"]] == ["prepared", "served"]
    read = Attempt.read(tmp_path)
    assert read is not None and read.number == 4 and read.phase is Phase.SERVED and len(read.phases) == 2


def test_an_older_attempt_file_without_phases_is_read_as_none_and_kept_as_written(tmp_path: Path) -> None:
    (tmp_path / "attempt.json").write_text(json.dumps({"attempt": 1, "state": "final", "recorded_at": "x"}))
    assert Attempt.read(tmp_path) is None
    attempts.record_state(tmp_path, 1, AttemptState.INCOMPLETE, "raised")
    saved = _saved(tmp_path)
    assert saved["state"] == "incomplete" and "phase" not in saved and "phases" not in saved
