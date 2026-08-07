"""Contract tests for the mutation guard — the detector that proves other detectors fire."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import textwrap
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


class DiscoveryTests(unittest.TestCase):
    def test_subjects_are_derived_from_the_repository_not_a_hand_kept_list(self) -> None:
        """A new test file must enrol its subject without anyone editing this guard."""
        pairs = dict(mutation_guard.discover(ROOT))
        rendered = {
            test.relative_to(ROOT).as_posix(): sorted(
                module.relative_to(ROOT).as_posix() for module in modules
            )
            for test, modules in pairs.items()
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
        blind = {path.name for path in mutation_guard.unresolved(ROOT)}
        every = {test.name for test, _ in mutation_guard.discover(ROOT)}
        self.assertIn("test_readonly_guard.py", every, "discovery must not drop test files")
        self.assertIn(
            "test_readonly_guard.py",
            blind,
            "the hyphenated readonly-guard.py subject is not derivable and must be reported",
        )

    def test_guard_is_documented_as_a_deliberate_run_not_a_gate_step(self) -> None:
        """A full sweep runs the whole suite once per mutant, so it is far too slow for a
        per-push gate. It follows the routing-eval precedent: deliberate, documented, never CI.
        Gate A still proves the guard itself works, because this file is auto-discovered."""
        gate = (ROOT / "scripts/gate_a.py").read_text(encoding="utf-8")
        self.assertNotIn("mutation_guard.py", gate)
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("mutation_guard.py", agents)


if __name__ == "__main__":
    unittest.main()
