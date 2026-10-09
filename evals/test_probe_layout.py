"""No-model tests for the saved-run layout (evals/probe/layout.py): how a folder's number reads back,
and that every reader of an iteration finds the same runs and attempts in it.

Run directly: python evals/test_probe_layout.py
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import compare_runs
import turn_counts
from probe import layout as probe_layout
from probe import rescoring as probe_rescoring
from probe import trials as probe_trials


class FolderNumberTests(unittest.TestCase):
    def test_a_number_reads_back_only_as_the_runner_writes_it(self) -> None:
        for name, expected in (("run-1", 1), ("run-12", 12), ("run-01", None), ("run-0", None), ("run-", None),
                               ("run-1-old", None), ("run-²", None), ("run-\u0661", None), ("1", None)):
            with self.subTest(name=name):
                self.assertEqual(expected, probe_layout.number(name, "run-"))
        self.assertEqual((3, None, None), tuple(probe_layout.number(name) for name in ("3", "03", "x")))

    def test_the_next_free_number_counts_only_numbers_the_runner_wrote(self) -> None:
        """`isdigit()` also accepts `01` and `²`; `int("²")` then raised mid-publication."""
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("1", "3", "07", "0", "²", "notes"):
                (Path(tmp) / name).mkdir()
            self.assertEqual({1, 3}, probe_layout.taken(Path(tmp)))
            self.assertEqual(4, probe_layout.next_number(Path(tmp)))
        self.assertEqual(1, probe_layout.next_number(Path(tmp) / "absent"))


class OneReadingOfAnIterationTests(unittest.TestCase):
    """The regrade and rescore, the run comparison, the turn-count summary and the spend cap each
    listed an iteration's runs with their own rule: a rescore graded `run-01` beside `run-1` as a
    second run 1, and the turn counts and the cap counted an operator's `run-1-old` copies."""

    SPEC = {"id": "s", "prompt": "p"}

    def _iteration(self, root: Path) -> Path:
        label = root / "eval-s" / "lab"
        timing = json.dumps({"num_turns": 5, "trial_duration_seconds": 1, "known_cost_usd": 0.1,
                             "cost_complete": True})
        for folder in ("run-1", "run-01", "run-0", "run-1-old", "attempts/run-1/1", "attempts/run-1/01",
                       "attempts/run-1-old/1"):
            (label / folder / "outputs").mkdir(parents=True)
            (label / folder / "outputs" / "trace-summary.json").write_text("{}", encoding="utf-8")
            (label / folder / "timing.json").write_text(timing, encoding="utf-8")
        return root

    def test_every_reader_finds_one_published_run_and_one_kept_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            iteration = self._iteration(Path(tmp))
            graded: list[str] = []

            def regrade_run(run_dir: Path, _spec: dict, **_kwargs: object) -> dict:
                graded.append(run_dir.relative_to(iteration).as_posix())
                return {"status": "PASS", "summary": {"passed": 1, "total": 1}, "scenario_sha256": "x",
                        "plugin_source_sha256": "y", "runtime": None, "models": [], "inconclusive": None}

            with mock.patch.object(probe_rescoring, "regrade_run", regrade_run):
                rows = probe_rescoring.regrade(iteration, [self.SPEC])
            skipped = json.loads(next(iteration.glob("regrade-*.json")).read_text(encoding="utf-8"))["skipped"]
            observed = turn_counts.collect(iteration, set())["s"]
            costs = probe_trials.kept_attempt_costs(iteration, "lab", ["s"], None)
            folders = [(f.relative_to(iteration).as_posix(), slot, k)
                       for f, slot, k in compare_runs._attempt_folders(iteration / "eval-s" / "lab")]
        self.assertEqual(["eval-s/lab/run-1"], graded)
        self.assertEqual([1], [row["run"] for row in rows])
        self.assertEqual(["eval-s/lab/run-0", "eval-s/lab/run-01", "eval-s/lab/run-1-old"],
                         skipped["other_run_folders"])
        self.assertEqual(([5, 5], 1), (observed.turns, observed.retained))
        self.assertEqual(1, len(costs))
        self.assertEqual([("eval-s/lab/run-1", 1, None), ("eval-s/lab/attempts/run-1/1", 1, 1)], folders)


if __name__ == "__main__":
    unittest.main()
