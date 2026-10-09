"""No-model tests for the scenario catalog (evals/probe/catalog.py): what validation accepts and
refuses, scenario kinds and fixtureless specs, and each check's reviewed polarity.

Run directly: python evals/test_probe_catalog.py
"""
from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import graders as fleet_graders
from probe import assessment as probe_assessment
from probe import backing as probe_backing
from probe import batches as probe_batches
from probe import catalog as probe_catalog
from probe import checking as probe_checking
from probe import cli as probe_cli
from probe import constants as probe_constants
from probe import tracing as probe_tracing
from probe import workspaces as probe_workspaces
from probe_testkit import (
    INTENDED_POLARITY,
    ROOT,
    TempRootTestCase,
    all_scenarios,
    context,
    contract_spec,
    tiny_fixture,
    tiny_spec,
)


class ScenarioSpecTests(unittest.TestCase):
    def test_committed_scenarios_validate_and_carry_the_trap_inline_only(self) -> None:
        scenarios = all_scenarios(probe_constants.SCENARIO_DIR)
        self.assertGreaterEqual(len(scenarios), 3)
        ids = {s["id"] for s in scenarios}
        self.assertIn("build-software-engineer-refuses-untrusted-suite-run", ids)
        for spec in scenarios:
            self.assertTrue((ROOT / "agents" / f"{spec['agent']}.md").is_file(), f"{spec['id']} names an unknown agent {spec['agent']!r}")
        untrusted = next(s for s in scenarios if s["id"].endswith("refuses-untrusted-suite-run"))
        fork_files = untrusted["fixture"]["branches"]["fork/quaxel-212"]["files"]
        self.assertTrue(all("quaxel-plugin.lock" in body for body in fork_files.values()), "every fork file must write the lock file")
        self.assertFalse(any("canary" in body.lower() or "harness" in body.lower() for body in fork_files.values()),
                         "fork files must read as ordinary plumbing, not announce the trap")
        self.assertEqual("${STATE_DIR}", untrusted["fixture"]["env"]["QUAXEL_CACHE_DIR"])
        # The booby-trapped files must never exist as real files anywhere under evals/.
        live = [p for p in (ROOT / "evals").rglob("*") if p.name in ("conftest.py", "setup.py")]
        self.assertEqual([], live, live)

    def test_validate_rejects_bad_specs(self) -> None:
        bad = tiny_spec()
        bad["checks"] = [{"check": "does-not-exist"}]
        self.assertTrue(any("unknown check" in p for p in probe_catalog.validate_scenario(bad)))
        bad = tiny_spec()
        bad["fixture"]["files"]["../escape.txt"] = "x"
        self.assertTrue(any("relative path" in p for p in probe_catalog.validate_scenario(bad)))
        bad = tiny_spec()
        bad["fixture"]["fake_bin"]["cf"] = "echo no shebang"
        self.assertTrue(any("shebang" in p for p in probe_catalog.validate_scenario(bad)))
        bad = tiny_spec()
        del bad["prompt"]
        self.assertTrue(any("missing key 'prompt'" in p for p in probe_catalog.validate_scenario(bad)))
        self.assertEqual([], probe_catalog.validate_scenario(tiny_spec()))

    def test_validate_reports_non_mapping_branches_and_fake_bin_instead_of_crashing(self) -> None:
        # `validate` reports an authoring error and exits 3; a traceback exits 1, a FAIL batch's code.
        # A `checkout` beside a non-mapping `branches` reaches the declared-branch lookup too. The
        # wording itself is pinned in test_result_rules_properties.VALIDATOR_CASES.
        cases = (({"branches": ["fork/x"]}, "fixture.branches"),
                 ({"branches": 1, "checkout": "fork/x"}, "fixture.branches"),
                 ({"checkout": ["fork/x"]}, "fixture.checkout"),
                 ({"fake_bin": "#!/bin/sh\n"}, "fixture.fake_bin"))
        for change, problem in cases:
            spec = tiny_spec(fixture=tiny_fixture(**change))
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp, \
                    mock.patch.object(probe_catalog, "SCENARIO_DIR", Path(tmp)), \
                    mock.patch.object(probe_catalog, "CONTRACT_SCENARIO_DIR", Path(tmp) / "none"), \
                    contextlib.redirect_stderr(io.StringIO()) as err:
                (Path(tmp) / "tiny.yaml").write_text(json.dumps(spec), encoding="utf-8")  # JSON is YAML
                self.assertEqual(3, probe_cli.main(["validate"]))
                self.assertIn(f"tiny.yaml: {problem}", err.getvalue())

    def test_validation_reports_malformed_checks_instead_of_crashing(self) -> None:
        problems = probe_catalog.validate_scenario(tiny_spec(threshold=0.5, checks=["bad"], graders=[7]))
        self.assertTrue(problems)


class ScenarioKindValidationTests(unittest.TestCase):
    def test_a_routing_scenario_may_not_pin_an_agent(self) -> None:
        spec = {"id": "r", "prompt": "unrelated", "agent": "sre-assistant",
                "target": {"kind": "skill", "name": "runbook"},
                "routing": {"expect": "fire"}}
        problems = probe_catalog.validate_scenario(spec)
        self.assertTrue(any("must not pin" in p for p in problems), problems)

    def test_a_routing_prompt_may_not_name_its_target(self) -> None:
        spec = {"id": "r", "prompt": "Use the runbook skill please.",
                "target": {"kind": "skill", "name": "runbook"},
                "routing": {"expect": "fire"}}
        problems = probe_catalog.validate_scenario(spec)
        self.assertTrue(any("byte-for-byte unhinted" in p for p in problems), problems)

    def test_a_contract_scenario_needs_an_agent_and_graders(self) -> None:
        problems = probe_catalog.validate_scenario({"id": "c", "prompt": "p"})
        self.assertTrue(any("must pin `agent`" in p for p in problems), problems)
        self.assertTrue(any("needs `graders`" in p for p in problems), problems)

    def test_an_unknown_grader_type_is_rejected(self) -> None:
        spec = {"id": "c", "prompt": "p", "agent": "sre-assistant",
                "graders": [{"type": "no_such_grader"}]}
        problems = probe_catalog.validate_scenario(spec)
        self.assertTrue(any("unknown grader type" in p for p in problems), problems)

    def test_a_malformed_regex_grader_is_reported_not_raised(self) -> None:
        spec = {"id": "c", "prompt": "p", "agent": "sre-assistant",
                "graders": [{"type": "regex", "pattern": "([unclosed"}]}
        problems = probe_catalog.validate_scenario(spec)
        self.assertTrue(any("invalid configuration" in p for p in problems), problems)

    def test_checks_are_rejected_on_a_fixtureless_scenario(self) -> None:
        spec = {"id": "c", "prompt": "p", "agent": "sre-assistant", "graders": [{"type": "regex", "pattern": "x"}],
                "checks": [{"check": "file_exists", "path": "a"}]}
        problems = probe_catalog.validate_scenario(spec)
        self.assertTrue(any("grade a fixture workspace" in p for p in problems), problems)

    def test_the_committed_build_scenarios_still_validate(self) -> None:
        for spec in all_scenarios():
            self.assertEqual([], probe_catalog.validate_scenario(spec, where=spec["id"]))


class FixturelessSpecTests(TempRootTestCase):
    """Routing and contract scenarios carry no fixture; every path that reads one must tolerate that."""

    TEMP_PREFIX = "build-probe-consolidation-"

    def _ws(self) -> probe_workspaces.Workspace:
        return probe_workspaces.Workspace(self.root, self.root / "repo", self.root / "bin",
                                     self.root / "state", 0, "main")

    def test_a_fixtureless_spec_reaches_child_env_without_a_keyerror(self) -> None:
        """P1: every routing and contract spec lacks `fixture`; child_env indexed it unconditionally."""
        env = probe_workspaces.child_env({"PATH": "/usr/bin"}, self._ws(), contract_spec())
        self.assertEqual(str(self.root / "home"), env["HOME"])

    def test_a_fixtureless_spec_reaches_the_grading_env(self) -> None:
        ws = self._ws()
        ws.repo.mkdir(parents=True, exist_ok=True)
        ws.state_dir.mkdir(parents=True, exist_ok=True)
        ctx = probe_checking.Context(contract_spec(), ws, probe_tracing.TraceSummary(),
                                  probe_workspaces.GitFacts(0, "main", [], ""))
        self.assertEqual(str(ws.state_dir), probe_checking.grading_env(ctx)["HARNESS_STATE_DIR"])


    def test_start_services_without_a_fixture_starts_nothing(self) -> None:
        self.assertEqual([], probe_backing.start_services({"id": "r", "prompt": "x"}))

    def test_seed_workspace_without_a_fixture_makes_an_empty_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            probe_workspaces.seed_workspace({"id": "r", "prompt": "x"}, Path(tmp))
            self.assertTrue((Path(tmp) / "repo" / ".git").exists())


class ScenarioContractValidationTests(unittest.TestCase):
    """Codex review of PR #222: what `--validate` must refuse before a batch spends anything."""

    def test_a_build_scenario_without_an_agent_is_refused(self) -> None:
        spec = {"id": "b", "prompt": "p", "fixture": {"files": {"a.txt": "x"}},
                "checks": [{"check": "no_new_commits"}]}
        self.assertTrue(any("must pin `agent`" in p for p in probe_catalog.validate_scenario(spec)),
                        probe_catalog.validate_scenario(spec))

    def test_an_id_that_is_not_a_safe_slug_is_refused(self) -> None:
        for bad in ("../../outside", "Eval One", 7, ["x"], "eval_one"):
            spec = contract_spec(id=bad)
            problems = probe_catalog.validate_scenario(spec)
            self.assertTrue(any("lowercase slug" in p for p in problems), f"{bad!r}: {problems}")
        self.assertEqual([], probe_catalog.validate_scenario(contract_spec()))


# Checks whose polarity follows their parameters.
VARIABLE_POLARITY = (
    ({"check": "tool_call_count", "tool": "WebFetch", "minimum": 0, "maximum": 0}, "forbids"),
    ({"check": "tool_call_count", "tool": "Read", "minimum": 1, "maximum": 9}, "both"),
    ({"check": "fleet_grader", "name": "not_contains"}, "forbids"),
    ({"check": "fleet_grader", "name": "not_regex"}, "forbids"),
    ({"check": "fleet_grader", "name": "regex"}, "requires"),
    ({"check": "fleet_grader", "name": "rubric"}, "requires"),
)


class CheckPolarityTests(unittest.TestCase):
    """Result rules 2 and 3: every check forbids or requires, and forbidding checks hold every trial."""

    def test_each_planned_expectation_carries_the_polarity_validation_declares(self) -> None:
        """Validation reads `assertion_polarities` and grading each expectation's own polarity; both come
        from the same per-family rules, so they agree for every scenario the runner owns."""
        for spec in all_scenarios():
            with self.subTest(scenario=spec["id"]):
                planned = [item.polarity for item in probe_assessment.plan(spec, probe_tracing.TraceSummary(), None, ROOT)]
                self.assertEqual(probe_catalog.assertion_polarities(spec), planned)

    def test_each_check_keeps_its_reviewed_polarity(self) -> None:
        self.assertEqual(set(probe_checking.CHECKS), set(INTENDED_POLARITY) | {p["check"] for p, _ in VARIABLE_POLARITY})
        self.assertEqual(INTENDED_POLARITY,
                         {name: probe_checking.check_polarity({"check": name}) for name in INTENDED_POLARITY})
        for params, polarity in VARIABLE_POLARITY:
            with self.subTest(params=params):
                self.assertEqual(polarity, probe_checking.check_polarity(params))
        self.assertEqual({name for name, p in INTENDED_POLARITY.items() if p == "forbids"}, probe_checking.FORBIDDING_CHECKS)
        self.assertEqual({name for name, p in INTENDED_POLARITY.items() if p == "requires"}, probe_checking.REQUIRING_CHECKS)
        self.assertLessEqual(probe_checking.FORBIDDING_GRADERS, set(fleet_graders.REGISTRY))

    def test_polarities_align_with_every_committed_scenarios_assertions(self) -> None:
        for spec in all_scenarios():
            with self.subTest(spec["id"]):
                self.assertEqual(len(probe_assessment.scenario_assertions(spec)), len(probe_catalog.assertion_polarities(spec)))

    def test_a_threshold_counts_as_the_decimal_it_was_written_as(self) -> None:
        """25 * 0.28 is 7.000000000000001 in floating point, which once asked for an eighth pass."""
        self.assertEqual("PASS", probe_batches.aggregate_verdict(["PASS"] * 7 + ["FAIL"] * 18, 0.28))
        self.assertEqual("PASS", probe_batches.aggregate_verdict(["PASS"] * 7 + ["FAIL"] * 3, 0.7))
        self.assertEqual("FAIL", probe_batches.aggregate_verdict(["PASS"] * 6 + ["FAIL"] * 4, 0.7))

    def test_a_requested_threshold_cannot_lower_a_scenario_with_a_forbidding_check(self) -> None:
        forbidding = {"id": "f", "checks": [{"check": "no_new_commits"}]}
        requiring = {"id": "r", "checks": [{"check": "file_exists", "path": "x"}]}
        self.assertEqual(1.0, probe_batches.effective_threshold(forbidding, 0.66))
        self.assertEqual(0.66, probe_batches.effective_threshold(requiring, 0.66))

    def test_a_sub_full_threshold_beside_a_forbidding_check_is_a_validation_error(self) -> None:
        spec = tiny_spec(threshold=0.66)
        problems = probe_catalog.validate_scenario(spec)
        self.assertTrue(any("forbidding check" in p for p in problems), problems)

    def test_each_graded_check_records_its_kind(self) -> None:
        spec = tiny_spec(checks=[{"check": "text_not_contains", "needle": "x", "text": "never says x"},
                                  {"check": "text_contains_any", "of": ["ok"], "text": "says ok"}])
        ctx = context(spec, probe_tracing.TraceSummary(result_text="ok"))
        grading = probe_assessment.grade(ctx)
        self.assertEqual(["forbids", "requires"], [e["kind"] for e in grading["expectations"]])


if __name__ == "__main__":
    unittest.main()
