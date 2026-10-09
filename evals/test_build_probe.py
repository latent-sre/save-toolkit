"""No-model tests of the build probe (evals/build_probe.py) as a whole: the entry point and the
package structure, and two fixture contracts that other files name this file for: the scribe
runbook oracle's placeholder list and the untrusted-suite fork files. The rest of the runner's
tests sit beside it, one evals/test_probe_*.py file per probe module.

Run directly: python evals/test_build_probe.py
"""
from __future__ import annotations

import ast
import contextlib
import dataclasses
import io
import json
import os
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import build_probe
import judge
from probe import assessment as probe_assessment
from probe import checking as probe_checking
from probe import cli as probe_cli
from probe import constants as probe_constants
from probe import fingerprints as probe_fingerprints
from probe import outcomes as probe_outcomes
from probe import records as probe_records
from probe import rescoring as probe_rescoring
from probe import tracing as probe_tracing
from probe import workspaces as probe_workspaces
from probe_testkit import (
    TempRootTestCase,
    all_scenarios,
    context,
    load_oracle,
    run_python,
    scenario_file,
    tiny_spec,
    ws_context,
)

ROOT = Path(__file__).resolve().parent.parent


class ScenarioSpecTests(unittest.TestCase):
    def test_runbook_probe_oracle_rejects_every_template_placeholder(self) -> None:
        # The scribe runbook probe ships its oracle through `writes_from:`; its literal list must be
        # the runbook template's placeholder set, or a copied slot left unfilled earns the point.
        spec = scenario_file(probe_constants.SCENARIO_DIR / "build-scribe-writes-only-docs.yaml")
        source = next(
            c["writes_from"]["probe_runbook_slots.py"] for c in spec["checks"] if c.get("writes_from")
        )
        oracle = load_oracle(ROOT / source)
        template = (ROOT / "skills" / "runbook" / "assets" / "runbook-template.md").read_text(encoding="utf-8")
        self.assertEqual(set(re.findall(r"<[^<>\n]*>", template)), set(oracle.TEMPLATE_LITERALS))


class PositiveControlTests(TempRootTestCase):
    """The instruments must be shown to fire: the fork traps write the lock, the cf shim logs."""

    def _untrusted_spec(self) -> dict:
        return next(s for s in all_scenarios() if s["id"].endswith("refuses-untrusted-suite-run"))

    def test_every_fork_file_writes_the_lock_when_executed(self) -> None:
        spec = self._untrusted_spec()
        ws = probe_workspaces.seed_workspace(spec, self.root)
        probe_workspaces._git(ws.repo, "checkout", "-q", "fork/quaxel-212")
        env = probe_workspaces.child_env(dict(os.environ), ws, spec)
        for name in spec["fixture"]["branches"]["fork/quaxel-212"]["files"]:
            lock = ws.state_dir / "quaxel-plugin.lock"
            if lock.exists():
                lock.unlink()
            # check=False: setup.py may fail AFTER the write when setuptools is absent; the lock must
            # already be there — the write sits above every third-party import by design.
            run_python([name], cwd=str(ws.repo), text=False, env=env, timeout=60)
            self.assertTrue(lock.exists(), f"{name} executed without writing the lock")
        probe_workspaces._git(ws.repo, "checkout", "-q", "main")
        ctx = ws_context(spec, ws)
        self.assertEqual("FAIL", probe_checking.check_state_file_absent(ctx, {"name": "quaxel-plugin.lock"}).state)
        self.assertTrue(probe_checking.check_no_new_commits(ctx, {})[0], "a checkout is not a commit")


class PackageStructureTests(unittest.TestCase):
    """The runner as the `evals/probe` package: typed outcomes, declared checks, one grading loop."""

    # What the hand-kept REGRADABLE set said before each check declared the evidence it reads.
    LEGACY_REGRADABLE = {
        "text_regex", "text_not_regex", "text_contains_any", "text_not_contains", "no_new_commits", "no_agents_dir",
        "changes_within", "skill_not_loaded", "skill_loaded", "bash_ran", "bash_did_not_run", "verification_completed",
        "no_task_dispatch", "task_completed", "state_file_absent", "cf_log_has_no", "fleet_grader",
        "no_workspace_changes", "dispatches_namespaced",
    }

    def test_an_outcome_unpacks_like_a_check_result_and_states_what_it_measured(self) -> None:
        outcome = probe_outcomes.unmeasured("exit 3: no data")
        passed, evidence = outcome
        self.assertEqual((False, "INCONCLUSIVE: exit 3: no data"), (passed, evidence))
        self.assertEqual(("INCONCLUSIVE", "exit 3: no data", False), (outcome.state, outcome.reason, outcome.machinery))
        for text, state, machinery in (
            ("wrote deploy.yaml", "FAIL", False),
            ("INCONCLUSIVE: exit 3", "INCONCLUSIVE", False),
            ("INCONCLUSIVE: grader error: KeyError('x')", "INCONCLUSIVE", True),
            ("instrument: no snapshot", "INCONCLUSIVE", True),
            (judge.INCONCLUSIVE_PREFIX + "timed out", "INCONCLUSIVE", True),
        ):
            with self.subTest(evidence=text):
                read = probe_outcomes.Outcome.read(False, text)
                self.assertEqual((state, machinery), (read.state, read.machinery))
                self.assertEqual(state, probe_outcomes.legacy_state({"passed": False, "evidence": text}))
        self.assertEqual("PASS", probe_outcomes.Outcome.read(True, "INCONCLUSIVE: a pass is a pass").state)

    def test_each_check_declares_what_it_reads_and_the_regrade_rule_is_unchanged(self) -> None:
        self.assertEqual(self.LEGACY_REGRADABLE, probe_checking.REGRADABLE)
        self.assertIs(probe_checking.CheckRun, probe_checking.CheckRun)
        for name in probe_checking.CHECKS:
            with self.subTest(check=name):
                params = {"check": name, "name": "regex", "tool": "Read", "minimum": 1, "maximum": 2}
                self.assertEqual(name in self.LEGACY_REGRADABLE, probe_checking.is_regradable(params, {}))
        uncommitted = {"fixture": {"files": {"a": "b"}, "uncommitted": {"x.py": "1"}}}
        self.assertFalse(probe_checking.is_regradable({"check": "fleet_grader", "name": "rubric"}, {}))
        self.assertFalse(probe_checking.is_regradable({"check": "no_workspace_changes"}, uncommitted))
        self.assertEqual("live-judge", probe_checking.kept_as({"check": "fleet_grader", "name": "rubric"}, {}))
        self.assertEqual("workspace-dependent", probe_checking.kept_as({"check": "no_workspace_changes"}, uncommitted))
        with self.assertRaisesRegex(ValueError, "declared twice"):
            probe_checking.declare("text_regex", probe_outcomes.Polarity.REQUIRES,
                                   needs={probe_checking.Need.TEXT})(probe_checking.check_text_regex)

    def test_a_regrade_measures_what_the_run_kept_and_carries_the_rest(self) -> None:
        spec = tiny_spec(checks=[{"check": "text_contains_any", "of": ["ok"], "text": "says ok"},
                                  {"check": "file_exists", "path": "README.md", "text": "readme"}])
        trace = probe_tracing.TraceSummary(result_text="ok")
        ctx = context(spec, trace)
        items = probe_assessment.plan(spec, trace, ctx, ROOT, keep=True)
        self.assertEqual([None, "workspace-dependent"], [item.kept_as for item in items])
        saved = probe_outcomes.verdict(True, "README.md present [kept: workspace-dependent]")
        graded, reason = probe_assessment.assess(items, None, kept=lambda index, item: saved if index == 1 else None)
        self.assertEqual((["PASS", "PASS"], None), ([g.outcome.state for g in graded], reason))
        graded, reason = probe_assessment.assess(items, None, kept=lambda index, item: None)
        self.assertEqual(["PASS", "INCONCLUSIVE"], [g.outcome.state for g in graded])
        self.assertIn("no saved verdict for a workspace-dependent expectation", reason)

    def test_subcommands_and_the_flat_flags_reach_the_same_jobs(self) -> None:
        for argv in (["validate"], ["--validate"]):
            with self.subTest(argv=argv), contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(0, probe_cli.main(argv))
            self.assertIn("scenarios OK", out.getvalue())
        with tempfile.TemporaryDirectory() as tmp:
            rescore = Path(tmp) / "rescore.json"
            rescore.write_text(json.dumps({"runner": {}, "runs": []}), encoding="utf-8")
            for argv in (["diff", str(rescore), str(rescore)], ["--rescore-diff", str(rescore), str(rescore)]):
                with self.subTest(argv=argv), contextlib.redirect_stdout(io.StringIO()), \
                        contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(0, probe_cli.main(argv))
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(3, probe_cli.main(["rescore", tmp]), "a rescore needs a new --out")
            rows = [{"scenario": "s", "label": "l", "run": 1, "status": "PASS", "passed": 1, "total": 1,
                     "models": ["m"], "plugin_source_sha256": "0" * 64, "runtime": {"cli_version": "2.1.291 (Claude Code)", "host_platform": {"system": "Windows"}}}]
            with mock.patch.object(probe_rescoring, "regrade", return_value=rows), \
                    contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(0, probe_cli.main(["regrade", tmp]))
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            probe_cli.main(["run", "--label", "x"])

    def test_the_published_record_schema_is_the_record_model(self) -> None:
        published = json.loads((ROOT / "docs/fleet-evaluation/eval-record-v1.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(probe_records.record_schema(), published,
                         "regenerate: python evals/build_probe.py schema --out docs/fleet-evaluation/eval-record-v1.schema.json")
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(0, probe_cli.main(["schema"]))
        self.assertEqual(published, json.loads(out.getvalue()))

    def test_a_record_that_breaks_the_contract_is_refused_before_it_is_written(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            (run / "grading.json").write_text(json.dumps({"status": "MAYBE"}), encoding="utf-8")
            with self.assertRaises(ValueError):
                probe_records.write_record(run, tiny_spec(), label="l", run_number=1, attempt=1,
                                         started_at="2026-10-06T12:00:00+00:00", model=None, timeout=60)
            self.assertFalse((run / "record.json").exists())

    def test_the_entry_point_offers_no_runner_name_to_patch(self) -> None:
        """build_probe is only the command line: a runner name patched there fails loudly instead of
        silently leaving real code running. A registered check is read through its registry entry,
        so that entry is where its patch takes effect."""
        for name in ("run_trial", "plugin_provenance", "check_text_regex", "ROOT"):
            with self.subTest(name=name), self.assertRaises(AttributeError), mock.patch.object(build_probe, name, None):
                pass
        patched = dataclasses.replace(probe_checking.CHECKS["text_regex"], run=lambda ctx, p: probe_outcomes.verdict(True, "patched"))
        ctx = context({}, probe_tracing.TraceSummary(result_text="no match here"))
        with mock.patch.dict(probe_checking.CHECKS, {"text_regex": patched}):
            self.assertEqual("patched", probe_checking.run(ctx, {"check": "text_regex", "pattern": "absent"}).evidence)

    def test_the_runner_identity_binds_every_module_in_the_package(self) -> None:
        package = {path.resolve() for path in (ROOT / "evals" / "probe").glob("*.py")}
        self.assertLessEqual(package | {(ROOT / "evals" / "build_probe.py").resolve()}, set(probe_fingerprints.HARNESS_FILES))

    def test_a_sibling_function_is_called_through_its_module(self) -> None:
        """So a test patches the one place a function is looked up. `outcomes` holds pure
        constructors that nothing patches, so they may be imported by name."""
        package = ROOT / "evals" / "probe"
        functions = {path.stem: {node.name for node in ast.parse(path.read_text(encoding="utf-8")).body
                                 if isinstance(node, ast.FunctionDef)}
                     for path in package.glob("*.py")}
        for path in package.glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module and node.module != "outcomes":
                    with self.subTest(module=path.stem, source=node.module):
                        self.assertEqual(set(), {alias.name for alias in node.names} & functions.get(node.module, set()))


if __name__ == "__main__":
    unittest.main()
