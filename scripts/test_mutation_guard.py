"""Contract tests for the mutation guard — the detector that proves other detectors fire."""

from __future__ import annotations

import signal
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import mutation_guard


ROOT = Path(__file__).resolve().parents[1]

HONEST_MODULE = '''\
"""A tiny module under test."""


def gate(findings, opted_in):
    return 1 if (findings and opted_in) else 0
'''

HONEST_TEST = '''\
import sys, unittest
sys.path.insert(0, %(dir)r)
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
import sys, unittest
sys.path.insert(0, %(dir)r)
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
import sys, unittest
sys.path.insert(0, %(dir)r)
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
import sys, unittest
sys.path.insert(0, %(dir)r)
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
        """A prefix-truncated budget only ever mutates the first sites in walk order. On the real
        packet_drift.py the motivating mutant sits at index 35 of 48, so a prefix of 12 would never
        generate the very mutation this guard cites as its demonstration."""
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
        return _run_guard(root, *extra)

    def test_a_suite_that_kills_every_mutant_passes_with_exit_zero(self) -> None:
        code, output = self._run_main(self._repository(HONEST_TEST))
        self.assertEqual(0, code, output)
        self.assertIn("PASS", output)

    def test_a_sibling_pair_that_notices_nothing_is_a_finding_not_a_collapse(self) -> None:
        """The most severe result this tool can produce. The repository's own naming convention
        asserts the link, so total survival means the test proves nothing — it must never be
        filed beside inferred path-string artifacts."""
        code, output = self._run_main(self._repository(BLIND_TEST))
        self.assertEqual(mutation_guard.EXIT_SURVIVORS, code, output)
        self.assertIn("surviving mutant", output)
        self.assertNotIn("unexercised", output)
        self.assertNotIn("PASS", output)

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

    def test_a_negative_limit_exits_usage_not_refused(self) -> None:
        code, output = self._run_guard_here("--limit", "-1")
        self.assertEqual(mutation_guard.EXIT_USAGE, code, output)
        self.assertNotEqual(mutation_guard.EXIT_REFUSED, code, output)

    def test_a_non_integer_limit_exits_usage_not_refused(self) -> None:
        code, output = self._run_guard_here("--limit", "half")
        self.assertEqual(mutation_guard.EXIT_USAGE, code, output)

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
        return _run_guard(self._repository(), *extra)


class SampledCollapseTests(unittest.TestCase):
    """A sampled all-survivor result may never be reported as "the test never exercises it".

    The collapse rule was `len(survivors) == tried`, where under `--limit` *tried* is the sample
    size rather than the mutant population. A module the test genuinely exercises could therefore be
    labelled unexercised because the one or two mutants that happened to be sampled survived — the
    tool asserting a strong negative from a bounded observation, which is the same overclaim it
    exists to detect.
    """

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
        code, output = _run_guard(root, "--limit", "1")
        self.assertNotIn("unexercised -- scripts/other.py", output)
        self.assertNotIn("probably never exercises it", output)
        self.assertEqual(mutation_guard.EXIT_SURVIVORS, code, output)
        self.assertIn("scripts/other.py:5", output)

    def test_the_same_pair_is_provably_exercised_on_an_unbounded_run(self) -> None:
        """Pins the premise of the test above. If `pinned` ever stopped being contract-pinned, the
        module really would be unexercised and the assertion above would prove nothing."""
        root = self._repository(EXERCISES_OTHER_TEST)
        code, output = _run_guard(root)
        self.assertEqual(mutation_guard.EXIT_SURVIVORS, code, output)
        self.assertNotIn("probably never exercises it", output)
        # Exactly the two `unpinned` operand drops survive; the two `pinned` drops are killed.
        self.assertEqual(2, output.count("scripts/other.py:5"), output)
        self.assertEqual(0, output.count("scripts/other.py:9"), output)

    def test_an_unbounded_run_still_collapses_a_genuinely_unexercised_pair(self) -> None:
        """The narrowing must not delete the rule. An inferred subject the test never imports still
        collapses to one message on an unbounded run, and never reports PASS."""
        root = self._repository(NAMES_OTHER_WITHOUT_IMPORTING_TEST)
        code, output = _run_guard(root)
        self.assertEqual(mutation_guard.EXIT_INCONCLUSIVE, code, output)
        self.assertIn("probably never exercises it", output)
        self.assertNotIn("PASS", output)
        self.assertEqual(1, output.count("probably never exercises it"), output)

    def test_a_bounded_run_of_the_unexercised_pair_reports_survivors_instead(self) -> None:
        """Bounded, the same genuinely-unexercised pair may not borrow the unbounded conclusion: it
        reports what it observed — surviving mutants — rather than a claim it cannot support."""
        root = self._repository(NAMES_OTHER_WITHOUT_IMPORTING_TEST)
        code, output = _run_guard(root, "--limit", "1")
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

        code, output = _run_guard(link)
        self.assertNotIn("Traceback", output, "a non-canonical root must not crash the sweep")
        self.assertNotIn("ValueError", output)
        # The literal subject must still be found and reported, not silently lost with the crash.
        self.assertIn("scripts/other.py", output)
        self.assertEqual(mutation_guard.EXIT_SURVIVORS, code, output)


class SamplingHonestyTests(unittest.TestCase):
    """`--limit` must not be documented in a way that implies a bounded run covers a named mutant.

    Even spacing fixed the *prefix* failure — a budget that only ever mutates the shallowest sites.
    It did not make a bounded run complete, and the guard's own demonstration case proves it: the
    motivating mutant is index 35 of 48, and an evenly spaced sample of 12 lands on 34 and 38.
    """

    def test_an_evenly_spaced_sample_can_still_miss_the_motivating_index(self) -> None:
        source = "def f():\n" + "".join(f"    x{i} = a{i} and b{i}\n" for i in range(24))
        every = mutation_guard.mutants(source)
        self.assertEqual(48, len(every), "fixture must reproduce the demonstration population")
        chosen = [every.index(mutant) for mutant in mutation_guard.mutants(source, limit=12)]
        self.assertEqual([0, 4, 9, 13, 17, 21, 26, 30, 34, 38, 43, 47], chosen)
        self.assertNotIn(
            35,
            chosen,
            "even spacing brackets index 35 without selecting it; a bounded run is a sample",
        )

    @staticmethod
    def _prose(documentation: str | None) -> str:
        """Docstring text with wrapping collapsed, so an assertion pins wording not line breaks."""

        return " ".join((documentation or "").split())

    def test_the_sampling_docstring_does_not_imply_bounded_coverage(self) -> None:
        """The docstring said only a *prefix* budget would exclude the motivating mutant, which
        invites the reader to infer that the evenly spaced sample includes it. It does not."""
        documentation = self._prose(mutation_guard.mutants.__doc__)
        self.assertIn("evenly spaced sample can still miss", documentation)
        self.assertIn("unbounded run", documentation)

    def test_the_module_docstring_scopes_the_unexercised_claim_to_unbounded_runs(self) -> None:
        documentation = self._prose(mutation_guard.__doc__)
        self.assertIn("unbounded run", documentation)
        self.assertIn("probably never exercises it", documentation)


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
            "skills/operational-learning/scripts/packet_drift.py",
            rendered.get("scripts/test_packet_drift.py", []),
            "path-loaded bundle scripts must be discovered from the test's own source",
        )
        self.assertIn(
            "scripts/validate_fleet.py",
            rendered.get("scripts/test_validate_fleet.py", []),
            "the sibling test_X.py -> X.py convention must be discovered",
        )
        self.assertNotIn(
            "scripts/test_packet_drift.py",
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

    def test_guard_is_documented_as_a_deliberate_run_not_a_gate_step(self) -> None:
        """A full sweep runs the whole suite once per mutant, so it is far too slow for a
        per-push gate. It follows the routing-eval precedent: deliberate, documented, never CI.
        Gate A still proves the guard itself works, because this file is auto-discovered."""
        gate = (ROOT / "scripts/gate_a.py").read_text(encoding="utf-8")
        self.assertNotIn("mutation_guard.py", gate)
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("mutation_guard.py", agents)


class InconclusiveVerdictTests(unittest.TestCase):
    """`blind` must reach the verdict, not just the printout."""

    def test_blind_test_files_alone_make_a_run_inconclusive(self) -> None:
        # The regression: this returned False, so a run in which NO subject could be derived for
        # any test file still printed PASS.
        self.assertTrue(mutation_guard.is_inconclusive([], [], ["scripts/test_x.py"], 12))

    def test_a_fully_inspected_run_is_conclusive(self) -> None:
        # The complement matters as much: if this returned True the tool could never say PASS, and
        # the assertion above would pass for the wrong reason.
        self.assertFalse(mutation_guard.is_inconclusive([], [], [], 12))

    def test_each_uninspected_bucket_is_sufficient_on_its_own(self) -> None:
        for label, args in (
            ("unverifiable", (["pair"], [], [], 12)),
            ("unexercised", ([], ["pair"], [], 12)),
            ("blind", ([], [], ["test"], 12)),
            ("nothing attempted", ([], [], [], 0)),
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


if __name__ == "__main__":
    unittest.main()
