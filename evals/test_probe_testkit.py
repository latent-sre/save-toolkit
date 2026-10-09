"""The shared evals test helpers keep the promises the suites rely on: each caller owns what it gets.

Run directly: python evals/test_probe_testkit.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from probe import catalog as probe_catalog
from probe_testkit import (
    EVALS,
    all_scenarios,
    load_oracle,
    run_python,
    scenario,
    scenario_file,
    tiny_fixture,
    tiny_spec,
    write_tree,
)


class SpecFactoryTests(unittest.TestCase):
    def test_each_tiny_spec_is_a_deep_copy_with_the_given_keys_replaced(self) -> None:
        first = tiny_spec()
        first["fixture"]["files"]["README.md"] = "changed"
        first["checks"].append({"check": "file_exists"})
        self.assertEqual("# tiny\n", tiny_spec()["fixture"]["files"]["README.md"])
        self.assertEqual([{"check": "no_new_commits"}], tiny_spec()["checks"])
        changed = tiny_spec(checks=[], fixture=tiny_fixture(checkout="fork/x"))
        self.assertEqual(([], "fork/x", "# tiny\n"),
                         (changed["checks"], changed["fixture"]["checkout"], changed["fixture"]["files"]["README.md"]))
        self.assertEqual([], probe_catalog.validate_scenario(tiny_spec()))


class ScenarioLoaderTests(unittest.TestCase):
    def test_a_committed_scenario_is_the_runners_parse_and_each_caller_owns_its_copy(self) -> None:
        path = EVALS / "build-scenarios" / "build-scribe-writes-only-docs.yaml"
        loaded = scenario_file(path)
        self.assertEqual(probe_catalog.load_scenario(path), loaded)
        self.assertEqual(loaded, scenario("build-scribe-writes-only-docs"))
        loaded["checks"].clear()
        self.assertTrue(scenario_file(path)["checks"], "an edit to one copy reaches no other caller")

    def test_every_scenario_is_loaded_once_and_copied(self) -> None:
        specs = all_scenarios()
        self.assertEqual([s["id"] for s in probe_catalog.load_all_scenarios()], [s["id"] for s in specs])
        specs[0]["id"] = "edited"
        self.assertNotEqual("edited", all_scenarios()[0]["id"])

    def test_a_patched_scenario_directory_is_not_served_from_the_real_ones(self) -> None:
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(probe_catalog, "SCENARIO_DIR", Path(tmp)), \
                mock.patch.object(probe_catalog, "CONTRACT_SCENARIO_DIR", Path(tmp) / "none"):
            self.assertEqual([], all_scenarios())
        self.assertTrue(all_scenarios())


class FileAndProcessHelperTests(unittest.TestCase):
    def test_write_tree_creates_folders_and_keeps_the_requested_line_endings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(root, write_tree(root, {"a/b/c.txt": "one\ntwo\n", "top.txt": ""}, newline="\n"))
            self.assertEqual(b"one\ntwo\n", (root / "a/b/c.txt").read_bytes())
            self.assertEqual(b"", (root / "top.txt").read_bytes())
            write_tree(root, {"native.txt": "x\n"})
            self.assertEqual(b"x" + os.linesep.encode(), (root / "native.txt").read_bytes())

    def test_run_python_captures_text_bounds_the_run_and_isolates_on_request(self) -> None:
        probe = "import sys; print(sys.flags.isolated, sys.flags.safe_path)"
        self.assertEqual("0 False", run_python(["-c", probe]).stdout.strip())
        self.assertEqual("1 True", run_python(["-c", probe], isolated=True).stdout.strip())
        self.assertEqual(b"raw", run_python(["-c", "print('raw')"], text=False).stdout.strip())
        with self.assertRaises(subprocess.TimeoutExpired):
            run_python(["-c", "import time; time.sleep(30)"], timeout=0.5)

    def test_each_oracle_load_is_a_fresh_module_that_leaves_no_registration(self) -> None:
        path = EVALS / "oracles/incident-writes/probe_checks.py"
        first, second = load_oracle(path), load_oracle(path)
        self.assertIsNot(first, second)
        self.assertIsNot(first.GATE, second.GATE, "module state is never shared between loads")
        self.assertEqual(str(path), first.__file__)
        self.assertNotIn(first.__name__, sys.modules)


if __name__ == "__main__":
    unittest.main()
