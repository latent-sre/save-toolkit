"""Contract tests for the mutation guard — the detector that proves other detectors fire."""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

import mutation_guard


ROOT = Path(__file__).resolve().parents[1]

HONEST_MODULE = '''\
"""A tiny module under test."""


def gate(findings, opted_in):
    return 1 if (findings and opted_in) else 0
'''

HONEST_TEST = '''\
import os, sys, unittest
# Resolve from __file__, exactly as every real test in this repo does. A baked absolute path
# would reach OUTSIDE the isolated worktree and import unmutated code, making every mutant
# falsely survive.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import subject


class T(unittest.TestCase):
    def test_gate_requires_both(self):
        self.assertEqual(1, subject.gate(["x"], True))
        self.assertEqual(0, subject.gate([], True))
        self.assertEqual(0, subject.gate(["x"], False))


if __name__ == "__main__":
    unittest.main()
'''

# Exercises the same function but never pins the `findings and` half of the contract — exactly the
# shape of the test this guard exists to catch.
BLIND_TEST = '''\
import os, sys, unittest
# Resolve from __file__, exactly as every real test in this repo does. A baked absolute path
# would reach OUTSIDE the isolated worktree and import unmutated code, making every mutant
# falsely survive.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import subject


class T(unittest.TestCase):
    def test_gate_returns_one_when_opted_in_with_findings(self):
        self.assertEqual(1, subject.gate(["x"], True))


if __name__ == "__main__":
    unittest.main()
'''

# A second module, enrolled as an *inferred* subject by the `.py` string a test names. Its two
# functions are deliberately ordered: walk order puts `unpinned`'s mutants at indices 0 and 1, so a
# `--limit 1` sample selects only a surviving mutant even though the test genuinely exercises the
# module through `pinned`.
OTHER_MODULE = '''\
"""A second module reached through a path string rather than a sibling name."""


def unpinned(a, b):
    return bool(a and b)


def pinned(a, b):
    return bool(a and b)
'''

# Imports and exercises OTHER_MODULE. `pinned` is fully contract-pinned, so an unbounded sweep kills
# mutants 2 and 3 and the module is provably exercised.
EXERCISES_OTHER_TEST = '''\
import os, sys, unittest
# Resolve from __file__, exactly as every real test in this repo does. A baked absolute path
# would reach OUTSIDE the isolated worktree and import unmutated code, making every mutant
# falsely survive.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import subject
import other

INFERRED_SUBJECT = "scripts/other.py"


class T(unittest.TestCase):
    def test_gate_requires_both(self):
        self.assertEqual(1, subject.gate(["x"], True))
        self.assertEqual(0, subject.gate([], True))
        self.assertEqual(0, subject.gate(["x"], False))

    def test_pinned_requires_both_operands(self):
        self.assertTrue(other.pinned(True, True))
        self.assertFalse(other.pinned(False, True))
        self.assertFalse(other.pinned(True, False))

    def test_unpinned_is_only_half_exercised(self):
        self.assertTrue(other.unpinned(True, True))


if __name__ == "__main__":
    unittest.main()
'''

# Names OTHER_MODULE's path but never imports it — the genuine "the test never exercises it" shape
# the collapse exists for.
NAMES_OTHER_WITHOUT_IMPORTING_TEST = '''\
import os, sys, unittest
# Resolve from __file__, exactly as every real test in this repo does. A baked absolute path
# would reach OUTSIDE the isolated worktree and import unmutated code, making every mutant
# falsely survive.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import subject

INFERRED_SUBJECT = "scripts/other.py"


class T(unittest.TestCase):
    def test_gate_requires_both(self):
        self.assertEqual(1, subject.gate(["x"], True))
        self.assertEqual(0, subject.gate([], True))
        self.assertEqual(0, subject.gate(["x"], False))


if __name__ == "__main__":
    unittest.main()
'''


# Fixtures for ImportDiscoveryTests. Each reaches its subject the way a real test in this repo
# does, and in a way the pre-import-following discovery could not see.
WIDGET_IMPORTER = '''\
import os, sys, unittest
# Resolve from __file__, exactly as every real test in this repo does. A baked absolute path
# would reach OUTSIDE the isolated worktree and import unmutated code, making every mutant
# falsely survive.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import widget


class T(unittest.TestCase):
    def test_f(self):
        self.assertEqual(1, widget.f())
'''

# Names the module by BARE basename only, as a path-joined subject looks to the AST.
BASENAME_NAMER = '''\
import unittest

NAME = "converter.py"


class T(unittest.TestCase):
    def test_noop(self):
        pass
'''

# Imports another TEST module, which import-following must not enroll as a subject.
HELPER_IMPORTER = '''\
import os, sys, unittest
# Resolve from __file__, exactly as every real test in this repo does. A baked absolute path
# would reach OUTSIDE the isolated worktree and import unmutated code, making every mutant
# falsely survive.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import test_helper


class T(unittest.TestCase):
    def test_v(self):
        self.assertEqual(1, test_helper.VALUE)
'''


# Contains a glob literal, as real tests do. Must NOT enrol bundled scripts as subjects.
GLOB_LITERAL_NAMER = '''\
import unittest

PATTERN = "*.py"


class T(unittest.TestCase):
    def test_noop(self):
        pass
'''

# Exits 0 only if the process cwd is the root of the tree containing this file.
CWD_PROBE = '''\
import os, pathlib, sys, unittest

EXPECTED = pathlib.Path(__file__).resolve().parents[1]


class T(unittest.TestCase):
    def test_cwd_is_my_own_tree_root(self):
        assert pathlib.Path(os.getcwd()).resolve() == EXPECTED, (os.getcwd(), str(EXPECTED))


if __name__ == "__main__":
    unittest.main()
'''


def _git_repository(case: unittest.TestCase, files: dict[str, str]) -> Path:
    """A committed, clean throwaway repository holding exactly *files*.

    Each body is `%`-formatted with `dir` bound to the repository's `scripts/` directory, so a test
    body can put that directory on `sys.path`. The commit matters: the guard refuses a dirty tree.
    """

    temporary = tempfile.TemporaryDirectory()
    case.addCleanup(temporary.cleanup)
    root = Path(temporary.name)
    for relative, body in files.items():
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body % {"dir": str(root / "scripts")}, encoding="utf-8")
    for args in (
        ["init", "--quiet", "."],
        ["add", "--all"],
        ["-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-qm", "base"],
    ):
        subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    return root


def _run_guard(root: Path, *extra: str) -> tuple[int, str]:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts/mutation_guard.py"), "--root", str(root), *extra],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    return completed.returncode, completed.stdout + completed.stderr


class MutantGenerationTests(unittest.TestCase):
    def test_boolean_operand_drop_reproduces_the_real_world_mutation(self) -> None:
        """The F3 mutation — `findings and args.fail_on_drift` losing its left operand — must be
        one of the mutants this guard generates, or it could not have caught the original bug."""
        mutants = mutation_guard.mutants(HONEST_MODULE)
        rendered = [m.mutated_source for m in mutants]
        self.assertTrue(
            any("return 1 if opted_in else 0" in source for source in rendered),
            "boolean-operand drop is missing; the guard cannot reproduce the F3 mutation",
        )
        self.assertTrue(
            any("return 1 if findings else 0" in source for source in rendered),
            "the mirror operand drop is missing",
        )

    def test_every_mutant_is_valid_python_and_distinct_from_the_original(self) -> None:
        mutants = mutation_guard.mutants(HONEST_MODULE)
        self.assertTrue(mutants)
        # Compare against the unparse-normalized original, not the raw source: every mutant is an
        # unparse round-trip that renormalizes docstring quoting, so `!= HONEST_MODULE` would hold
        # even for a mutant that changed nothing. That assertion could never fail.
        normalized = mutation_guard.normalized_source(HONEST_MODULE)
        seen = set()
        for mutant in mutants:
            compile(mutant.mutated_source, "<mutant>", "exec")
            self.assertNotEqual(normalized, mutant.mutated_source)
            seen.add(mutant.mutated_source)
        self.assertEqual(len(seen), len(mutants), "mutants must be deduplicated")

    def test_a_bounded_sample_spans_the_file_instead_of_its_shallowest_prefix(self) -> None:
        """A prefix-truncated budget only ever mutates the first sites in walk order."""
        source = "def f(a, b, c, d, e, f, g, h):\n" + "".join(
            f"    x{i} = {chr(97 + i)} and {chr(98 + i)}\n" for i in range(8)
        )
        every = mutants_of = mutation_guard.mutants(source)
        self.assertGreater(len(every), 6)
        sampled = mutation_guard.mutants(source, limit=3)
        self.assertEqual(3, len(sampled))
        last_line = max(m.lineno for m in mutants_of)
        self.assertGreater(
            max(m.lineno for m in sampled),
            min(m.lineno for m in every),
            "a bounded sample must reach past the first site",
        )
        self.assertEqual(
            last_line,
            max(m.lineno for m in sampled),
            "a bounded sample must include the deepest site, not stop at a prefix",
        )

    def test_the_default_budget_is_unbounded_because_this_is_not_a_gate_step(self) -> None:
        self.assertEqual(0, mutation_guard.DEFAULT_LIMIT)

    def test_generation_is_deterministic(self) -> None:
        first = [m.mutated_source for m in mutation_guard.mutants(HONEST_MODULE)]
        second = [m.mutated_source for m in mutation_guard.mutants(HONEST_MODULE)]
        self.assertEqual(first, second)


class SurvivorDetectionTests(unittest.TestCase):
    def _fixture(self, test_body: str) -> tuple[Path, Path]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        module = root / "subject.py"
        module.write_text(HONEST_MODULE, encoding="utf-8")
        test = root / "test_subject.py"
        test.write_text(test_body % {"dir": str(root)}, encoding="utf-8")
        return module, test

    def test_a_test_that_pins_the_contract_leaves_no_survivor(self) -> None:
        module, test = self._fixture(HONEST_TEST)
        # Assert the fixture actually runs and passes first. Without this, a fixture that never
        # executed would also yield [] survivors and this test would pass proving nothing — the
        # exact vacuous-assertion shape this whole suite exists to detect.
        self.assertTrue(mutation_guard.run_test(test), "fixture test must pass unmutated")
        survivors = mutation_guard.surviving_mutants(module, test)
        self.assertEqual([], [s.description for s in survivors])

    def test_a_suite_failing_for_non_mutation_reasons_is_unverifiable_not_clean(self) -> None:
        """The guard's own false-green path. If the test fails for any reason other than the
        mutation — a missing dependency, a wrong cwd, an import error — then every mutant looks
        killed and the tool would report PASS while proving nothing about the suite."""
        module, test = self._fixture(HONEST_TEST)
        test.write_text("import does_not_exist_anywhere\n", encoding="utf-8")

        self.assertFalse(mutation_guard.run_test(test))
        with self.assertRaises(mutation_guard.UnverifiablePair):
            mutation_guard.surviving_mutants(module, test)

    def test_a_test_that_asserts_less_than_it_claims_leaves_a_survivor(self) -> None:
        """This is the whole point: the blind test passes, and passes just as happily against a
        gate that ignores `findings` entirely."""
        module, test = self._fixture(BLIND_TEST)
        survivors = mutation_guard.surviving_mutants(module, test)
        self.assertTrue(survivors, "a test asserting less than its contract must leave a survivor")
        self.assertTrue(
            any("opted_in" in s.mutated_source for s in survivors),
            f"expected the dropped-operand survivor, got {[s.description for s in survivors]}",
        )

    def test_the_module_is_restored_byte_for_byte_afterwards(self) -> None:
        """The guard rewrites the file under test in place. If it ever fails to restore it, it
        would silently corrupt the tree it was invoked to protect."""
        module, test = self._fixture(BLIND_TEST)
        before = module.read_bytes()
        mutation_guard.surviving_mutants(module, test)
        self.assertEqual(before, module.read_bytes())


class MainReportingTests(unittest.TestCase):
    """Exit-code and headline contracts for the CLI.

    These exist because the incident that created this tool was an untested CLI exit contract in
    a `main()`, and the tool's first version repeated it: every reporting decision lived in
    `main()` with no test at all.
    """

    def _repository(self, test_body: str) -> Path:
        return _git_repository(
            self,
            {"scripts/subject.py": HONEST_MODULE, "scripts/test_subject.py": test_body},
        )

    def _run_main(self, root: Path, *extra: str) -> tuple[int, str]:
        return _run_guard(root, "--module", "scripts/subject.py", *extra)

    def test_a_suite_that_kills_every_mutant_passes_with_exit_zero(self) -> None:
        code, output = self._run_main(self._repository(HONEST_TEST))
        self.assertEqual(0, code, output)
        self.assertIn("PASS", output)

    def test_a_sibling_pair_reports_one_named_survivor_not_an_inventory(self) -> None:
        """Even when later mutants would survive, the CLI creates one lead and stops."""
        code, output = self._run_main(self._repository(BLIND_TEST))
        self.assertEqual(mutation_guard.EXIT_SURVIVORS, code, output)
        self.assertIn("surviving mutant", output)
        self.assertEqual(1, output.count("survived test_subject.py"), output)
        self.assertIn("Further mutants are intentionally not executed or inventoried", output)
        self.assertNotIn("unexercised", output)
        self.assertNotIn("PASS", output)

    def test_cli_stops_execution_after_first_surviving_mutant(self) -> None:
        """The one-lead contract bounds execution, not merely the printed survivor list."""
        with tempfile.TemporaryDirectory() as temporary:
            counter = Path(temporary) / "test-runs.txt"
            counting_test = BLIND_TEST.replace(
                "import os, sys, unittest\n",
                "import os, sys, unittest\n"
                f"with open({str(counter)!r}, 'a', encoding='utf-8') as stream:\n"
                "    stream.write('run\\n')\n",
            )

            code, output = self._run_main(self._repository(counting_test))

            self.assertEqual(mutation_guard.EXIT_SURVIVORS, code, output)
            self.assertEqual(
                2,
                len(counter.read_text(encoding="utf-8").splitlines()),
                "expected one baseline run and one surviving-mutant run, then an immediate stop",
            )

    def test_an_unverifiable_pair_never_reports_pass(self) -> None:
        root = self._repository(HONEST_TEST)
        (root / "scripts" / "test_subject.py").write_text(
            "import missing_module_xyz\n", encoding="utf-8"
        )
        subprocess.run(
            ["git", "-C", str(root), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
             "commit", "-aqm", "break"],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        code, output = self._run_main(root)
        self.assertEqual(mutation_guard.EXIT_INCONCLUSIVE, code, output)
        self.assertIn("INCONCLUSIVE", output)
        self.assertNotIn("PASS", output)

    def test_a_dirty_tree_is_refused_and_distinguishable_from_inconclusive(self) -> None:
        root = self._repository(HONEST_TEST)
        (root / "scripts" / "subject.py").write_text("# edited\n", encoding="utf-8")
        code, output = self._run_main(root)
        self.assertEqual(mutation_guard.EXIT_REFUSED, code, output)
        self.assertNotEqual(mutation_guard.EXIT_INCONCLUSIVE, mutation_guard.EXIT_REFUSED)
        self.assertIn("dirty", output)

    def test_a_negative_limit_is_rejected_rather_than_passing_over_zero_mutants(self) -> None:
        """A one-character typo previously selected zero mutants and still printed PASS, exit 0."""
        code, output = self._run_main(self._repository(HONEST_TEST), "--limit", "-1")
        self.assertNotEqual(0, code)
        self.assertNotIn("PASS", output)


class ExitStatusTests(unittest.TestCase):
    """Every outcome this tool can reach must be told apart by its exit status alone.

    That is the tool's own stated design — a collapsed exit status cannot distinguish "refused to
    run" from "ran and proved nothing", which is the disarmed-gate shape this repository forbids for
    the readonly guard. An invalid `--limit` broke it: argparse exits 2 for every usage error, and 2
    is `EXIT_REFUSED`, so a rejected flag was indistinguishable from a dirty working tree.
    """

    def _repository(self) -> Path:
        return _git_repository(
            self,
            {"scripts/subject.py": HONEST_MODULE, "scripts/test_subject.py": HONEST_TEST},
        )

    def test_the_documented_exit_codes_are_pairwise_distinct(self) -> None:
        codes = {
            "clean": 0,
            "survivors": mutation_guard.EXIT_SURVIVORS,
            "refused": mutation_guard.EXIT_REFUSED,
            "inconclusive": mutation_guard.EXIT_INCONCLUSIVE,
            "usage": mutation_guard.EXIT_USAGE,
        }
        self.assertEqual(
            len(codes),
            len(set(codes.values())),
            f"exit statuses collide and cannot be told apart: {codes}",
        )

    def test_one_explicit_module_is_required(self) -> None:
        """An omitted target must be usage failure, never an accidental fleet-wide sweep."""
        code, output = _run_guard(self._repository())
        self.assertEqual(mutation_guard.EXIT_USAGE, code, output)
        self.assertIn("--module", output)

    def test_a_negative_limit_exits_usage_not_refused(self) -> None:
        code, output = self._run_guard_here("--limit", "-1")
        self.assertEqual(mutation_guard.EXIT_USAGE, code, output)
        self.assertNotEqual(mutation_guard.EXIT_REFUSED, code, output)

    def test_a_non_integer_limit_exits_usage_not_refused(self) -> None:
        code, output = self._run_guard_here("--limit", "half")
        self.assertEqual(mutation_guard.EXIT_USAGE, code, output)

    def test_zero_limit_removes_the_sample_cap_for_the_named_module(self) -> None:
        """Zero keeps the full named-module population available; it is not a fleet target."""
        code, output = self._run_guard_here("--limit", "0")
        self.assertEqual(0, code, output)
        self.assertNotIn("usage:", output.lower())

    def test_an_unknown_flag_exits_usage_not_refused(self) -> None:
        """Any argparse usage error takes the same path, so none of them may impersonate a refusal
        to run over a dirty tree."""
        code, output = self._run_guard_here("--not-a-flag")
        self.assertEqual(mutation_guard.EXIT_USAGE, code, output)

    def test_help_still_exits_zero(self) -> None:
        """Remapping argparse's exit must not capture `--help`, which is a successful run."""
        code, output = self._run_guard_here("--help")
        self.assertEqual(0, code, output)
        self.assertIn("--limit", output)

    def _run_guard_here(self, *extra: str) -> tuple[int, str]:
        return _run_guard(
            self._repository(), "--module", "scripts/subject.py", *extra
        )


class SingleSurvivorTests(unittest.TestCase):
    """A run reports one observed survivor and never infers aggregate coverage from it."""

    def _repository(self, test_body: str) -> Path:
        return _git_repository(
            self,
            {
                "scripts/subject.py": HONEST_MODULE,
                "scripts/other.py": OTHER_MODULE,
                "scripts/test_subject.py": test_body,
            },
        )

    def test_a_sampled_run_never_claims_a_module_is_unexercised(self) -> None:
        # --limit 1 selects mutant index 0, which is a survivor in `unpinned`. The test still
        # exercises other.py — an unbounded sweep kills the two `pinned` mutants — so the sampled
        # all-survivor result must be reported as the survivor it is, never as a negative claim.
        root = self._repository(EXERCISES_OTHER_TEST)
        code, output = _run_guard(
            root, "--module", "scripts/other.py", "--limit", "1"
        )
        self.assertNotIn("unexercised -- scripts/other.py", output)
        self.assertNotIn("probably never exercises it", output)
        self.assertEqual(mutation_guard.EXIT_SURVIVORS, code, output)
        self.assertIn("scripts/other.py:5", output)

    def test_the_same_pair_is_provably_exercised_on_an_unbounded_run(self) -> None:
        """Pins the premise of the test above. If `pinned` ever stopped being contract-pinned, the
        module really would be unexercised and the assertion above would prove nothing."""
        root = self._repository(EXERCISES_OTHER_TEST)
        survivors = mutation_guard.surviving_mutants(
            root / "scripts/other.py", root / "scripts/test_subject.py"
        )
        self.assertEqual(2, len(survivors))
        self.assertEqual({5}, {mutant.lineno for mutant in survivors})
        code, output = _run_guard(root, "--module", "scripts/other.py")
        self.assertEqual(mutation_guard.EXIT_SURVIVORS, code, output)
        self.assertNotIn("probably never exercises it", output)
        # The CLI intentionally emits only one named survivor instead of inventorying both.
        self.assertEqual(1, output.count("scripts/other.py:5"), output)
        self.assertEqual(0, output.count("scripts/other.py:9"), output)

    def test_an_unexercised_pair_still_stops_at_one_observed_survivor(self) -> None:
        """Even a likely-bad inferred pairing does not justify inventorying the population."""
        root = self._repository(NAMES_OTHER_WITHOUT_IMPORTING_TEST)
        code, output = _run_guard(root, "--module", "scripts/other.py")
        self.assertEqual(mutation_guard.EXIT_SURVIVORS, code, output)
        self.assertIn("surviving mutant", output)
        self.assertNotIn("probably never exercises it", output)
        self.assertNotIn("PASS", output)
        self.assertEqual(1, output.count("survived test_subject.py"), output)

    def test_a_bounded_run_of_the_unexercised_pair_reports_survivors_instead(self) -> None:
        """Bounded, the same genuinely-unexercised pair may not borrow the unbounded conclusion: it
        reports what it observed — surviving mutants — rather than a claim it cannot support."""
        root = self._repository(NAMES_OTHER_WITHOUT_IMPORTING_TEST)
        code, output = _run_guard(
            root, "--module", "scripts/other.py", "--limit", "1"
        )
        self.assertEqual(mutation_guard.EXIT_SURVIVORS, code, output)
        self.assertNotIn("probably never exercises it", output)


class NonCanonicalRootTests(unittest.TestCase):
    """A `--root` that is not already canonical must not kill the sweep.

    `discover` resolves a literal `.py` subject, but sibling subjects and every reported path come
    from the root as given. When those disagree, `module.relative_to(args.root)` raises ValueError
    and the run dies partway with a traceback instead of a verdict. The default root is
    `Path(__file__).resolve().parents[1]` — already canonical — so this never showed up locally;
    macOS hands out `/var/...` that resolves to `/private/var/...` and Windows hands out 8.3 short
    paths, and CI failed on both the first time a fixture passed a temp directory as `--root`.
    """

    def test_a_symlinked_root_still_produces_a_verdict(self) -> None:
        root = _git_repository(
            self,
            {
                "scripts/subject.py": HONEST_MODULE,
                "scripts/other.py": OTHER_MODULE,
                "scripts/test_subject.py": EXERCISES_OTHER_TEST,
            },
        )
        link = root.parent / (root.name + "-link")
        try:
            link.symlink_to(root, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:  # unprivileged Windows
            self.skipTest(f"symlinks unavailable on this host: {exc}")
        self.addCleanup(link.unlink)

        code, output = _run_guard(link, "--module", "scripts/other.py")
        self.assertNotIn("Traceback", output, "a non-canonical root must not crash the run")
        self.assertNotIn("ValueError", output)
        # The literal subject must still be found and reported, not silently lost with the crash.
        self.assertIn("scripts/other.py", output)
        self.assertEqual(mutation_guard.EXIT_SURVIVORS, code, output)


class SamplingHonestyTests(unittest.TestCase):
    """`--limit` must not imply that a bounded run covers any named mutant."""

    @staticmethod
    def _prose(documentation: str | None) -> str:
        """Docstring text with wrapping collapsed, so an assertion pins wording not line breaks."""

        return " ".join((documentation or "").split())

    def test_the_sampling_docstring_does_not_imply_bounded_coverage(self) -> None:
        """The docstring said only a *prefix* budget would exclude the motivating mutant, which
        invites the reader to infer that the evenly spaced sample includes it. It does not."""
        documentation = self._prose(mutation_guard.mutants.__doc__)
        self.assertIn("evenly spaced sample can still miss", documentation)
        self.assertIn("unbounded selection contains every generated mutant", documentation)
        self.assertIn("CLI still stops executing as soon as one survives", documentation)

    def test_the_module_docstring_promises_execution_stops_at_one_survivor(self) -> None:
        documentation = self._prose(mutation_guard.__doc__)
        self.assertIn("stops executing mutants as soon as it finds that first survivor", documentation)
        self.assertNotIn("probably never exercises it", documentation)


class DiscoveryTests(unittest.TestCase):
    def test_subjects_are_derived_from_the_repository_not_a_hand_kept_list(self) -> None:
        """A new test file must enrol its subject without anyone editing this guard."""
        pairs = dict(mutation_guard.discover(ROOT))
        rendered = {
            test.relative_to(ROOT).as_posix(): sorted(
                subject.path.relative_to(ROOT).as_posix() for subject in subjects
            )
            for test, subjects in pairs.items()
        }
        self.assertIn(
            "skills/obs-dashboards/scripts/dashboard_hygiene.py",
            rendered.get("scripts/test_dashboard_hygiene.py", []),
            "path-loaded bundle scripts must be discovered from the test's own source",
        )
        self.assertIn(
            "scripts/validate_fleet.py",
            rendered.get("scripts/test_validate_fleet.py", []),
            "the sibling test_X.py -> X.py convention must be discovered",
        )
        self.assertNotIn(
            "scripts/test_dashboard_hygiene.py",
            rendered.get("scripts/test_mutation_guard.py", []),
            "a test file is never a mutation subject; mutating a test proves nothing",
        )

    def test_test_files_without_a_subject_are_reported_not_dropped(self) -> None:
        """A test whose subject cannot be derived must surface. Silently skipping it is how this
        repository once shipped a test file that was wired into nothing and ran nowhere."""
        every = {test.name for test, _ in mutation_guard.discover(ROOT)}
        self.assertIn("test_readonly_guard.py", every, "discovery must not drop test files")
        # Assert the property, not a filename: anything reported unresolved must genuinely have
        # no sibling module on disk under either spelling. Pinning a name would rot the moment a
        # subject became derivable — which is exactly what just happened to readonly-guard.py.
        for test in mutation_guard.unresolved(ROOT):
            with self.subTest(test=test.name):
                stem = test.name[len("test_") :]
                self.assertFalse(test.with_name(stem).is_file())
                self.assertFalse(test.with_name(stem.replace("_", "-")).is_file())

    def test_the_hyphenated_sibling_spelling_resolves(self) -> None:
        """scripts/readonly-guard.py is a real module whose test is test_readonly_guard.py. The
        underscore-only convention missed it, leaving the fleet's fail-closed security guard with
        no derived subject while an unrelated eval test enrolled it as a false one."""
        subjects = {
            test.name: {subject.path.name: subject.origin for subject in subjects}
            for test, subjects in mutation_guard.discover(ROOT)
        }
        self.assertEqual(
            "sibling", subjects["test_readonly_guard.py"].get("readonly-guard.py")
        )

    def test_guard_is_not_a_gate_step(self) -> None:
        """Gate A must never turn the optional helper into routine work."""
        gate = (ROOT / "scripts/gate_a.py").read_text(encoding="utf-8")
        self.assertNotIn("mutation_guard.py", gate)

class InconclusiveVerdictTests(unittest.TestCase):
    """`blind` must reach the verdict, not just the printout."""

    def test_blind_test_files_alone_make_a_run_inconclusive(self) -> None:
        # The regression: this returned False, so a run in which NO subject could be derived for
        # any test file still printed PASS.
        self.assertTrue(mutation_guard.is_inconclusive([], ["scripts/test_x.py"], 12))

    def test_a_fully_inspected_run_is_conclusive(self) -> None:
        # The complement matters as much: if this returned True the tool could never say PASS, and
        # the assertion above would pass for the wrong reason.
        self.assertFalse(mutation_guard.is_inconclusive([], [], 12))

    def test_each_uninspected_bucket_is_sufficient_on_its_own(self) -> None:
        for label, args in (
            ("unverifiable", (["pair"], [], 12)),
            ("blind", ([], ["test"], 12)),
            ("nothing attempted", ([], [], 0)),
        ):
            with self.subTest(bucket=label):
                self.assertTrue(mutation_guard.is_inconclusive(*args))


class TerminationRestoreTests(unittest.TestCase):
    """SIGTERM must unwind through the in-place restore rather than skipping it.

    A harness timeout killed a real sweep of scripts/gate_a.py and left
    `if __name__ != '__main__':` on disk. Run as a script that condition is false, so main() never
    executed: the gate printed nothing and exited 0, reading as a perfect pass.
    """

    def test_sigterm_is_converted_into_an_exception(self) -> None:
        if not hasattr(signal, "SIGTERM"):  # pragma: no cover - platform without SIGTERM
            self.skipTest("SIGTERM unavailable on this platform")
        previous = signal.getsignal(signal.SIGTERM)
        try:
            mutation_guard._restore_on_termination()
            installed = signal.getsignal(signal.SIGTERM)
            self.assertNotEqual(
                previous, installed, "SIGTERM disposition unchanged; the restore would be skipped"
            )
            # Default disposition terminates without running `finally`; the handler must raise so
            # the existing restore path executes on the way out.
            with self.assertRaises(KeyboardInterrupt):
                installed(signal.SIGTERM, None)
        finally:
            signal.signal(signal.SIGTERM, previous)


class ImportDiscoveryTests(unittest.TestCase):
    """A test's imports are the strongest statement of what it exercises.

    Discovery used only the sibling filename and `.py` literals resolved against the root, so real
    subjects scored as no-subject-at-all: `generate_platform_adapters.py` (735 lines, the single
    generator behind every host projection, reached as `import generate_platform_adapters as
    adapters`), `check_plan_status.py` (sibling-name mismatch), and a skill-bundled converter
    reached by path-joining, where the AST sees only the bare basename. Each had a dedicated test
    file and zero mutation coverage.
    """

    def test_an_imported_module_becomes_a_subject(self) -> None:
        root = _git_repository(self, {
            "scripts/subject.py": HONEST_MODULE,
            "scripts/widget.py": "def f():\n    return 1\n",
            "scripts/test_gizmo.py": WIDGET_IMPORTER,
        })
        found = {
            test.name: [(subject.path.name, subject.origin) for subject in subjects]
            for test, subjects in mutation_guard.discover(root)
        }
        self.assertIn(("widget.py", "import"), found["test_gizmo.py"])

    def test_a_bare_basename_literal_resolves_under_a_skill_bundle(self) -> None:
        root = _git_repository(self, {
            "scripts/subject.py": HONEST_MODULE,
            "skills/thing/scripts/converter.py": "def f():\n    return 1\n",
            "scripts/test_converting.py": BASENAME_NAMER,
        })
        found = {
            test.name: [(subject.path.name, subject.origin) for subject in subjects]
            for test, subjects in mutation_guard.discover(root)
        }
        self.assertIn(("converter.py", "literal"), found["test_converting.py"])

    def test_a_test_file_is_never_its_own_subject(self) -> None:
        """Import-following made this reachable in a way it was not before: test modules in this
        repository import one another's helpers, and mutating a test proves nothing."""
        root = _git_repository(self, {
            "scripts/subject.py": HONEST_MODULE,
            "scripts/test_helper.py": "VALUE = 1\n",
            "scripts/test_uses_helper.py": HELPER_IMPORTER,
        })
        for test, subjects in mutation_guard.discover(root):
            for subject in subjects:
                self.assertFalse(
                    subject.path.name.startswith("test_"),
                    f"{test.name} took {subject.path.name} as a subject",
                )

    def test_the_live_tree_has_no_tractable_blind_files(self) -> None:
        """Only non-module contract suites or .sh/.json subjects remain unresolved."""
        # Inventory of what legitimately has no importable subject module: contract suites whose
        # subjects are .md/.yaml/.json, and .sh/.json wiring. Updated 2026-08-26 -- it had drifted
        # in both directions and nothing noticed, because CI ran no component tests.
        # `test_hook_wiring.py` became resolvable and was never removed. `test_graph_contracts.py`
        # left this list on 2026-08-26 for the same reason: it now imports `validate_fleet` to
        # assert the conditional-handoff contract, so the sweep resolves a real subject module for
        # it and it is no longer blind.
        self.assertEqual(
            {
                "test_observability_skill_contracts.py",
                "test_platform_skill_contracts.py",
                "test_release_skill_contracts.py",
                "test_runbook_schema.py",
            },
            {path.name for path in mutation_guard.unresolved(ROOT)},
        )

class IsolationTests(unittest.TestCase):
    """The sweep must never write to the caller's tree, and must never quietly fall back to it."""

    def test_the_worktree_is_separate_and_is_cleaned_up(self) -> None:
        root = _git_repository(self, {
            "scripts/subject.py": HONEST_MODULE,
            "scripts/test_subject.py": HONEST_TEST,
        })
        with mutation_guard.isolated_checkout(root) as isolated:
            self.assertNotEqual(root.resolve(), isolated.resolve())
            self.assertTrue((isolated / "scripts/subject.py").is_file(), "HEAD not checked out")
            # Writing here must not touch the original -- that is the entire guarantee.
            (isolated / "scripts/subject.py").write_text("mutated\n", encoding="utf-8")
            self.assertEqual(
                HONEST_MODULE,
                (root / "scripts/subject.py").read_text(encoding="utf-8"),
                "a write inside the worktree reached the caller's tree",
            )
        self.assertFalse(isolated.exists(), "worktree survived the context manager")
        listed = subprocess.run(
            ["git", "-C", str(root), "worktree", "list"],
            capture_output=True, text=True, check=False,
        ).stdout
        self.assertNotIn("tree", listed.replace(str(root), ""), "stale worktree record left behind")

    def test_a_failure_to_isolate_refuses_instead_of_falling_back(self) -> None:
        """Fail closed. Falling back to in-place mutation on the one path where we have just
        learned the environment is misbehaving is the worst possible moment to start writing to
        the real tree."""
        root = _git_repository(self, {
            "scripts/subject.py": HONEST_MODULE,
            "scripts/test_subject.py": HONEST_TEST,
        })
        real_run = subprocess.run

        def fail_worktree_add(argv, *args, **kwargs):
            if "worktree" in argv and "add" in argv:
                return subprocess.CompletedProcess(argv, 1, "", "fatal: injected failure")
            return real_run(argv, *args, **kwargs)

        with unittest.mock.patch.object(mutation_guard.subprocess, "run", fail_worktree_add):
            with self.assertRaisesRegex(RuntimeError, "refusing to mutate"):
                with mutation_guard.isolated_checkout(root):
                    self.fail("isolation reported success after worktree add failed")
        self.assertEqual(
            HONEST_MODULE,
            (root / "scripts/subject.py").read_text(encoding="utf-8"),
            "the caller's tree was touched on the failure path",
        )

    def test_a_symlinked_temp_dir_does_not_break_relative_path_reporting(self) -> None:
        """The yielded worktree path must be canonical, not as `mkdtemp` handed it over.

        `discover` resolves every candidate it returns, so a caller computing
        `module.relative_to(root)` needs both sides canonicalized the same way. macOS `mkdtemp`
        returns `/var/...` which resolves to `/private/var/...`, and Windows returns 8.3 short
        paths — so an unresolved yield raised "is not in the subpath of" on both CI legs while
        passing on Linux, where /tmp is not a symlink.

        Reproduced here by pointing TMPDIR at a symlink, which is precisely the macOS shape, so the
        Linux leg covers this class from now on rather than discovering it in CI a third time.
        """
        if not hasattr(os, "symlink"):  # pragma: no cover - platform without symlinks
            self.skipTest("symlinks unavailable")
        root = _git_repository(self, {
            "scripts/subject.py": HONEST_MODULE,
            "scripts/test_subject.py": HONEST_TEST,
        })
        staging = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, staging, True)
        (staging / "realtmp").mkdir()
        aliased = staging / "tmp"
        try:
            os.symlink(staging / "realtmp", aliased, target_is_directory=True)
        except (OSError, NotImplementedError):  # pragma: no cover - unprivileged Windows
            self.skipTest("cannot create a directory symlink here")
        self.assertNotEqual(aliased.resolve(), aliased, "fixture TMPDIR is not actually aliased")

        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts/mutation_guard.py"),
             "--root", str(root), "--module", "scripts/subject.py", "--limit", "3"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False,
            env={**os.environ, "TMPDIR": str(aliased)},
        )
        output = completed.stdout + completed.stderr
        self.assertNotIn("is not in the subpath", output, output[-600:])
        self.assertNotIn("Traceback", output, output[-600:])

    def test_a_glob_literal_does_not_enrol_every_bundled_script(self) -> None:
        """`"*.py"` is an ordinary literal in a test, not a subject pattern.

        Interpolating it into the bundle glob enrolled every skill-bundled script as a subject of
        whichever test happened to mention it — six modules that test makes no claim about. The
        bogus pairs then fail their own normalized baseline, so the sweep reports unverifiable
        pairs instead of testing the real module.
        """
        root = _git_repository(self, {
            "scripts/subject.py": HONEST_MODULE,
            "skills/thing/scripts/bundled.py": "def f():\n    return 1\n",
            "scripts/test_globby.py": GLOB_LITERAL_NAMER,
        })
        found = {
            test.name: [subject.path.name for subject in subjects]
            for test, subjects in mutation_guard.discover(root)
        }
        self.assertNotIn("bundled.py", found["test_globby.py"], found["test_globby.py"])

    def test_the_live_generator_test_is_not_paired_with_skill_scripts(self) -> None:
        """The live instance of the bug above: `test_platform_adapters.py` contains two `"*.py"`
        literals and was paired with six unrelated skill modules."""
        paired = {
            subject.path.name
            for test, subjects in mutation_guard.discover(ROOT)
            if test.name == "test_platform_adapters.py"
            for subject in subjects
        }
        self.assertEqual({"generate_platform_adapters.py"}, paired)

    def test_a_test_runs_from_the_root_of_its_own_tree(self) -> None:
        """With isolation, cwd must follow the test into the worktree.

        `run_test` used the module-level ROOT — the caller's real checkout — so a mutated test
        inside the throwaway worktree was launched with the LIVE repository as its working
        directory, and anything resolving a repo file relative to cwd read unmutated bytes.
        """
        root = _git_repository(self, {
            "scripts/subject.py": HONEST_MODULE,
            "scripts/test_cwd_probe.py": CWD_PROBE,
        })
        # The probe exits 0 only when its cwd is the root of the tree holding it.
        self.assertTrue(mutation_guard.run_test(root / "scripts/test_cwd_probe.py"))
        self.assertNotEqual(root.resolve(), ROOT, "fixture must not be the live repo")

    def test_an_absolute_module_path_still_matches_under_isolation(self) -> None:
        """`--module` must work with an absolute path, not only a relative one.

        `_run_sweep` compares discovered modules against `(args.root / args.module).resolve()`,
        and by then the root is the isolated worktree. Joining an ABSOLUTE right operand discards
        the left -- `Path("/worktree") / "/repo/scripts/x.py"` is `/repo/scripts/x.py` -- so the
        comparison pointed outside the worktree, matched nothing, and the run exited
        "no test/module pair matched". Relative paths kept working, which is what hid it.
        """
        root = _git_repository(self, {
            "scripts/subject.py": HONEST_MODULE,
            "scripts/test_subject.py": HONEST_TEST,
        })
        absolute = (root / "scripts/subject.py").resolve()
        self.assertTrue(absolute.is_absolute(), "fixture must exercise the absolute spelling")
        code, output = _run_guard(root, "--module", str(absolute), "--limit", "2")
        self.assertNotIn("no test/module pair matched", output)
        self.assertNotEqual(mutation_guard.EXIT_REFUSED, code, output)
        # And it must select the SAME pair the relative spelling does, not merely avoid refusing.
        relative_code, relative_output = _run_guard(root, "--module", "scripts/subject.py", "--limit", "2")
        self.assertEqual(relative_code, code, f"absolute={output!r} relative={relative_output!r}")

    def test_a_module_outside_the_repository_is_named_as_such(self) -> None:
        """It used to fall through to the generic no-pair refusal, which reads as "your module has
        no tests" rather than "that path is not in this repository"."""
        root = _git_repository(self, {
            "scripts/subject.py": HONEST_MODULE,
            "scripts/test_subject.py": HONEST_TEST,
        })
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, outside, True)
        stray = outside / "stray.py"
        stray.write_text("x = 1\n", encoding="utf-8")
        code, output = _run_guard(root, "--module", str(stray))
        self.assertEqual(mutation_guard.EXIT_REFUSED, code, output)
        self.assertIn("outside", output)

    def test_a_dirty_tree_is_still_refused(self) -> None:
        """Now for honesty rather than recovery: a worktree is pinned at HEAD, so uncommitted
        changes would go untested while the report implied otherwise."""
        root = _git_repository(self, {
            "scripts/subject.py": HONEST_MODULE,
            "scripts/test_subject.py": HONEST_TEST,
        })
        (root / "scripts/subject.py").write_text(HONEST_MODULE + "\n# edit\n", encoding="utf-8")
        code, output = _run_guard(root, "--module", "scripts/subject.py")
        self.assertEqual(mutation_guard.EXIT_REFUSED, code, output)
        self.assertIn("working tree is dirty", output)

if __name__ == "__main__":
    unittest.main()
