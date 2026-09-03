#!/usr/bin/env python3
"""Red-first contract for the Gate A weight-totals check."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_weight


class WeightEvaluationTests(unittest.TestCase):
    def test_measured_at_ceiling_passes(self) -> None:
        rows, failed = check_weight.evaluate({"x": 100}, {"x": 100})
        self.assertEqual([], failed)
        self.assertEqual([("x", 100, 100, 0)], rows)

    def test_measured_over_ceiling_fails(self) -> None:
        rows, failed = check_weight.evaluate({"x": 101}, {"x": 100})
        self.assertEqual(["x"], failed)
        self.assertEqual([("x", 101, 100, -1)], rows)

    def test_measured_under_ceiling_passes_with_headroom(self) -> None:
        rows, failed = check_weight.evaluate({"x": 90}, {"x": 100})
        self.assertEqual([], failed)
        self.assertEqual(10, rows[0][3])

    def test_one_over_ceiling_total_fails_the_whole_check_even_when_others_are_fine(self) -> None:
        rows, failed = check_weight.evaluate(
            {"a": 1, "b": 999}, {"a": 100, "b": 100}
        )
        self.assertEqual(["b"], failed)
        self.assertEqual(2, len(rows))

    def test_measure_returns_the_three_named_totals_the_real_ceilings_expect(self) -> None:
        weights = check_weight.load_weights()
        measured = check_weight.measure()
        self.assertEqual(set(weights), set(measured))

    def test_a_missing_or_misspelled_ceiling_is_not_a_silent_pass(self) -> None:
        """Codex review of PR #222: evaluate iterates the ceilings, so a deleted key retires itself."""
        measured = check_weight.measure()
        self.assertIsNone(check_weight.ceiling_problem(measured, check_weight.load_weights()))
        for broken, marker in (
            ({k: v for k, v in check_weight.load_weights().items() if k != "agents_bytes"}, "agents_bytes"),
            ({**{k: v for k, v in check_weight.load_weights().items() if k != "skills_bytes"},
              "skill_bytes": 1}, "skill_bytes"),
        ):
            problem = check_weight.ceiling_problem(measured, broken)
            self.assertIsNotNone(problem, broken)
            self.assertIn(marker, problem)
            # ...and the silent pass it used to produce: the dropped total is judged by nothing.
            self.assertNotIn(marker, check_weight.evaluate(measured, broken)[1])


if __name__ == "__main__":
    unittest.main()


class TrackedFilesOnlyTests(unittest.TestCase):
    """The totals count what git tracks; bytecode a test run leaves beside a skill script is not weight."""

    def test_untracked_bytecode_does_not_count(self) -> None:
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "skills" / "s" / "scripts" / "__pycache__").mkdir(parents=True)
            (root / "skills" / "s" / "SKILL.md").write_text("x" * 100, encoding="utf-8")
            (root / "skills" / "s" / "scripts" / "__pycache__" / "t.pyc").write_bytes(b"y" * 5000)
            (root / "evals").mkdir()
            (root / "agents").mkdir()
            # No git here: the fallback must still exclude the cache.
            self.assertEqual(100, check_weight.measure(root)["skills_bytes"])
            # With git: only tracked files count, so an untracked sibling is invisible too.
            subprocess.run(["git", "-C", tmp, "init", "-q"], check=True)
            subprocess.run(["git", "-C", tmp, "add", "skills/s/SKILL.md"], check=True)
            (root / "skills" / "s" / "untracked.md").write_text("z" * 700, encoding="utf-8")
            self.assertEqual(100, check_weight.measure(root)["skills_bytes"])

    def test_real_tree_measures_only_tracked_skill_bytes(self) -> None:
        import subprocess
        tracked = subprocess.run(
            ["git", "-C", str(check_weight.ROOT), "ls-files", "-z", "--", "skills"],
            capture_output=True, text=True, encoding="utf-8", check=True,
        ).stdout.split("\0")
        expected = sum((check_weight.ROOT / n).stat().st_size for n in tracked if n)
        self.assertEqual(expected, check_weight.measure()["skills_bytes"])

    def _git(self, cwd: Path, *args: str) -> None:
        import subprocess
        # A throwaway repository: give it an identity and no signing, so the seed commit works on a
        # CI runner with no git config and on a workstation whose global config signs commits.
        identity = ["-c", "user.name=test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false"]
        subprocess.run(["git", "-C", str(cwd), *identity, *args], check=True, capture_output=True, text=True)

    def _init_toolkit(self, root: Path, commit: bool = True) -> None:
        import subprocess
        (root / "skills").mkdir(parents=True, exist_ok=True)
        (root / "evals").mkdir(parents=True, exist_ok=True)
        (root / "agents").mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)

    def test_unstaged_deletion_of_a_committed_file_counts_only_what_remains(self) -> None:
        """Codex review of #223: git ls-files lists the index, not the working tree."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_toolkit(root)
            (root / "skills" / "s").mkdir(parents=True)
            (root / "skills" / "s" / "SKILL.md").write_text("x" * 100, encoding="utf-8")
            (root / "skills" / "s" / "other.md").write_text("y" * 50, encoding="utf-8")
            self._git(root, "add", "skills")
            self._git(root, "commit", "-q", "-m", "seed")
            (root / "skills" / "s" / "SKILL.md").unlink()  # unstaged deletion
            self.assertEqual(50, check_weight.measure(root)["skills_bytes"])

    def test_unstaged_rename_counts_neither_old_nor_new_path(self) -> None:
        """Codex review of #223: a rename without `git add` leaves the old cached path absent and
        the new path untracked, so it should count zero, not raise."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_toolkit(root)
            (root / "skills" / "s").mkdir(parents=True)
            (root / "skills" / "s" / "SKILL.md").write_text("x" * 100, encoding="utf-8")
            self._git(root, "add", "skills")
            self._git(root, "commit", "-q", "-m", "seed")
            (root / "skills" / "s" / "SKILL.md").unlink()
            (root / "skills" / "s" / "RENAMED.md").write_text("x" * 100, encoding="utf-8")
            self.assertEqual(0, check_weight.measure(root)["skills_bytes"])

    def test_untracked_copy_inside_an_enclosing_repository_falls_back_to_filesystem(self) -> None:
        """Codex review of #223: a Git-less copy of the toolkit sitting untracked inside another
        repository must not be measured by that enclosing repository's (empty) `ls-files`."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            outer = Path(tmp)
            self._git(outer, "init", "-q")
            root = outer / "toolkit"
            (root / "skills" / "s").mkdir(parents=True)
            (root / "evals").mkdir(parents=True)
            (root / "agents").mkdir(parents=True)
            (root / "skills" / "s" / "SKILL.md").write_text("x" * 100, encoding="utf-8")
            (root / "agents" / "x.md").write_text("a" * 30, encoding="utf-8")
            (root / "evals" / "t.py").write_text("print(1)\nprint(2)\n", encoding="utf-8")
            # Deliberately not added to the outer repo: an untracked subtree.
            measured = check_weight.measure(root)
            self.assertEqual(100, measured["skills_bytes"])
            self.assertEqual(30, measured["agents_bytes"])
            self.assertEqual(2, measured["evals_python_lines"])

    def test_agents_total_is_top_level_only(self) -> None:
        """The documented metric is `agents/*.md`; a tracked file under a subdirectory is not it."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._init_toolkit(root)
            (root / "agents" / "sub").mkdir(parents=True)
            (root / "agents" / "x.md").write_text("a" * 40, encoding="utf-8")
            (root / "agents" / "sub" / "y.md").write_text("b" * 999, encoding="utf-8")
            self._git(root, "add", "agents")
            self._git(root, "commit", "-q", "-m", "seed")
            self.assertEqual(40, check_weight.measure(root)["agents_bytes"])
