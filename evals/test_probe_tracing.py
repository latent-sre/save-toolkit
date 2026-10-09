"""No-model tests for trace parsing and the CLI invocation around it (evals/probe/tracing.py,
evals/probe/invocation.py): tool calls and receipts, verification evidence, native dispatches,
the command a trial is launched with, and which denials void a trial.

Run directly: python evals/test_probe_tracing.py
"""
from __future__ import annotations

import dataclasses
import json
import tempfile
import unittest
from pathlib import Path

from probe import assessment as probe_assessment
from probe import catalog as probe_catalog
from probe import checking as probe_checking
from probe import constants as probe_constants
from probe import invocation as probe_invocation
from probe import rescoring as probe_rescoring
from probe import tracing as probe_tracing
from probe import workspaces as probe_workspaces
from probe_testkit import (
    ReviewFindingTestCase,
    context,
    contract_spec,
    native_dispatch_events,
    parse_events,
    saved_grade,
    scenario_file,
    skill_events,
    tiny_spec,
    write_saved_run,
    ws_context,
)

ROOT = Path(__file__).resolve().parent.parent


class TraceAndCommandTests(unittest.TestCase):
    def test_parse_trace_extracts_tools_and_result(self) -> None:
        events = [
            {"type": "system", "subtype": "init", "model": "claude-sonnet-5"},
            {"type": "assistant", "message": {"model": "claude-sonnet-5", "content": [
                {"type": "tool_use", "id": "tu_s", "name": "Skill", "input": {"skill": "save-toolkit:eng-ladder"}},
                {"type": "tool_use", "name": "Bash", "input": {"command": "python -m unittest -v"}},
                {"type": "tool_use", "name": "Task", "input": {"subagent_type": "save-toolkit:reviewer"}},
            ]}},
            # A Skill load is credited only against its own clean tool_result.
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "tu_s", "content": "eng-ladder loaded"},
            ]}},
            # The CLI's usage table lists its internal Haiku helper call beside the session model.
            {"type": "result", "result": "done", "duration_ms": 1234, "num_turns": 3,
             "usage": {"input_tokens": 10, "output_tokens": 5, "cache_read_input_tokens": 100},
             "modelUsage": {"claude-haiku-4-5-20251001": {"outputTokens": 14}, "claude-sonnet-5": {}},
             "permission_denials": [{"tool_name": "Bash"}]},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "t.jsonl"
            path.write_text("\n".join(json.dumps(e) for e in events) + "\nnot json\n", encoding="utf-8")
            s = probe_tracing.parse_trace(path)
        self.assertTrue(s.has_result)
        self.assertEqual("done", s.result_text)
        self.assertEqual(["save-toolkit:eng-ladder"], s.skills)
        self.assertEqual(["python -m unittest -v"], s.bash_commands)
        self.assertEqual(["save-toolkit:reviewer"], s.dispatches)
        self.assertEqual(115, s.total_tokens)
        self.assertEqual(["claude-sonnet-5"], s.models, "a helper side call is not a resolved identity")
        self.assertEqual(["claude-haiku-4-5-20251001", "claude-sonnet-5"], s.usage_models)
        self.assertEqual(["Bash"], s.denials)
        self.assertEqual({"Skill": 1, "Bash": 1, "Task": 1}, s.tool_counts)

    def test_resolved_identity_follows_the_main_thread_not_the_usage_table(self) -> None:
        """A helper side call never splits a batch; a parent that changed model mid-trial still does."""
        result = {"type": "result", "result": "done", "duration_ms": 1, "num_turns": 2, "usage": {},
                  "modelUsage": {"claude-haiku-4-5-20251001": {}, "claude-sonnet-5": {}}}
        def turn(model):
            return {"type": "assistant", "message": {"model": model, "content": [{"type": "text", "text": "ok"}]}}

        steady = parse_events([{"type": "system", "subtype": "init", "model": "claude-sonnet-5"},
                               turn("claude-sonnet-5"), turn("claude-sonnet-5"), result])
        self.assertEqual(["claude-sonnet-5"], steady.models)
        changed = parse_events([{"type": "system", "subtype": "init", "model": "claude-sonnet-5"},
                                turn("claude-sonnet-5"), turn("claude-opus-4-1"), result])
        self.assertEqual(["claude-opus-4-1", "claude-sonnet-5"], changed.models)
        # A subagent's model is the dispatch's identity, not the parent's.
        child = {"type": "assistant", "parent_tool_use_id": "tu_1",
                 "message": {"model": "claude-opus-4-1", "content": [{"type": "text", "text": "child"}]}}
        dispatched = parse_events([{"type": "system", "subtype": "init", "model": "claude-sonnet-5"},
                                   turn("claude-sonnet-5"), child, result])
        self.assertEqual(["claude-sonnet-5"], dispatched.models)
        # No main-thread turn recorded (an early abort): the usage table is the only evidence.
        bare = parse_events([result])
        self.assertEqual(["claude-haiku-4-5-20251001", "claude-sonnet-5"], bare.models)

    def test_a_cli_builtin_plugin_is_not_a_second_candidate(self) -> None:
        """CLI 2.1.280 lists telemetry@builtin beside --plugin-dir; only a real second plugin is ambiguous."""
        candidate = {"name": "save-toolkit", "path": str(ROOT), "source": "save-toolkit@inline"}
        builtin = {"name": "telemetry", "path": "builtin", "source": "telemetry@builtin"}
        s = parse_events([{"type": "system", "subtype": "init", "plugins": [builtin, candidate]}])
        self.assertIsNone(probe_invocation.plugin_identity_problem(s, ROOT))
        self.assertEqual("save-toolkit", probe_tracing.runtime_namespace(s, ROOT))
        other = {"name": "other", "path": str(ROOT), "source": "other@inline"}
        s = parse_events([{"type": "system", "subtype": "init", "plugins": [candidate, builtin, other]}])
        self.assertIn("exactly one", probe_invocation.plugin_identity_problem(s, ROOT))

    def _skill_check(self, summary, name: str, params: dict, fn):
        with tempfile.TemporaryDirectory() as tmp:
            ws = probe_workspaces.seed_workspace(tiny_spec(), Path(tmp) / name)
            ctx = probe_checking.Context(tiny_spec(), ws, summary, probe_workspaces.collect_git_facts(ws))
            return fn(ctx, params)

    def test_an_errored_skill_call_is_an_attempt_not_a_load(self) -> None:
        """The 2026-09-02 no-skill arm: Skill(save-toolkit:backend-craft) answered `Unknown skill`
        with is_error, and the old parser still recorded it as a load."""
        s = parse_events(skill_events(is_error=True))
        self.assertEqual([], s.skills, "an errored Skill call is not a load")
        self.assertEqual(["save-toolkit:backend-craft"], s.skills_failed)
        ok, evidence = self._skill_check(s, "ws-err", {"skill": "backend-craft"}, probe_checking.check_skill_loaded)
        self.assertFalse(ok, "an Unknown skill tool error must not count as a load")
        self.assertIn("attempted", evidence.lower())
        self.assertIn("save-toolkit:backend-craft", evidence)

    def test_a_skill_call_with_a_clean_tool_result_is_still_credited(self) -> None:
        s = parse_events(skill_events(is_error=False))
        self.assertEqual(["save-toolkit:backend-craft"], s.skills)
        self.assertEqual([], s.skills_failed)
        ok, evidence = self._skill_check(s, "ws-ok", {"skill": "backend-craft"}, probe_checking.check_skill_loaded)
        self.assertTrue(ok)
        self.assertIn("loaded 1x", evidence)

    def test_guard_denials_are_joined_to_their_reason_and_not_treated_as_runtime_refusals(self) -> None:
        events = [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "tu_1", "name": "Bash", "input": {"command": "pwd && whoami; cf target"}},
            ]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "tu_1", "is_error": True,
                 "content": "Blocked by the read-only agent allowlist guard: `whoami` is not on the read-only allowlist."},
            ]}},
            {"type": "result", "result": "done", "duration_ms": 10, "usage": {},
             "permission_denials": [{"tool_name": "Bash", "tool_use_id": "tu_1", "tool_input": {"command": "pwd && whoami; cf target"}}]},
        ]
        s = parse_events(events)
        self.assertEqual(1, len(s.denial_details))
        self.assertIn("allowlist guard", s.denial_details[0]["reason"])
        self.assertTrue(probe_tracing.is_guard_denial(s.denial_details[0]["reason"]))
        self.assertFalse(probe_tracing.is_guard_denial("Permission denied by the user"))
        # The inconclusive rule in run_trial: a guard denial leaves nothing 'blocked'.
        self.assertEqual([], probe_invocation.runtime_blocked_tools(s, tiny_spec()))

    def test_dispatches_namespaced_flags_bare_agent_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ws = probe_workspaces.seed_workspace(tiny_spec(), Path(tmp))
            bare = ws_context(tiny_spec(), ws, dispatches=["researcher"])
            namespaced = ws_context(tiny_spec(), ws, dispatches=["save-toolkit:researcher"])
            none = ws_context(tiny_spec(), ws)
            self.assertEqual("FAIL", probe_checking.check_dispatches_namespaced(bare, {}).state)
            self.assertTrue(probe_checking.check_dispatches_namespaced(namespaced, {})[0])
            self.assertTrue(probe_checking.check_dispatches_namespaced(none, {})[0])

    def test_build_command_grants_build_tools_and_keeps_the_rest_of_the_clean_room_boundary(self) -> None:
        cmd = probe_invocation.build_command("claude", ROOT, "save-toolkit:software-engineer", "build it", "sonnet")
        self.assertEqual(["claude", "--agent", "save-toolkit:software-engineer", "-p", "build it"], cmd[:5])
        self.assertIn("--plugin-dir", cmd)
        self.assertIn(str(ROOT.resolve()), cmd)
        tools = cmd[cmd.index("--tools") + 1].split(",")
        self.assertEqual(sorted(probe_constants.BUILD_TOOLS), sorted(tools))
        denied = cmd[cmd.index("--disallowedTools") + 1].split(",")
        self.assertIn("WebFetch", denied)
        self.assertIn("WebSearch", denied)
        self.assertNotIn("Bash", denied)
        self.assertEqual("dontAsk", cmd[cmd.index("--permission-mode") + 1])
        self.assertEqual(sorted(probe_constants.BUILD_TOOLS), sorted(cmd[cmd.index("--allowedTools") + 1].split(",")))
        self.assertEqual("sonnet", cmd[cmd.index("--model") + 1])
        self.assertIn("--strict-mcp-config", cmd)

    def test_the_measured_plugin_must_be_the_one_the_runtime_loaded(self) -> None:
        """P1: no plugin, two plugins, or a plugin from another path is not a verdict about the agent."""
        self.assertIsNone(probe_invocation.plugin_identity_problem(
            probe_tracing.TraceSummary(runtime_plugins=[{"name": "save-toolkit", "path": str(ROOT)}]), ROOT))
        for observed, marker in (
            ([], "exactly one"),
            ([{"name": "save-toolkit", "path": str(ROOT)}, {"name": "other", "path": str(ROOT)}], "exactly one"),
            ([{"name": "impostor", "path": str(ROOT)}], "name"),
            ([{"name": "save-toolkit", "path": str(ROOT / "skills")}], "path"),
            ([{"name": "save-toolkit"}], "path"),
        ):
            problem = probe_invocation.plugin_identity_problem(
                probe_tracing.TraceSummary(runtime_plugins=observed), ROOT)
            self.assertIsNotNone(problem, observed)
            self.assertIn(marker, problem)


class VerificationEvidenceTests(unittest.TestCase):
    """The agent's verification needs execution evidence, not a mention of a test command."""

    @staticmethod
    def _call(name="Bash", command="python -m unittest discover -s tests -t . -v", use_id="verify", **inputs):
        return {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "id": use_id, "name": name, "input": {"command": command, **inputs}}]}}

    @staticmethod
    def _result(use_id="verify", *, output="Ran 2 tests in 0.003s\n\nOK\n", is_error=False, **receipt):
        return {"type": "user", "tool_use_result": {
            "stdout": "", "stderr": output, "interrupted": False, **receipt}, "message": {"content": [
                {"type": "tool_result", "tool_use_id": use_id, "is_error": is_error, "content": output}]}}

    @staticmethod
    def _failed_result(use_id, text="Exit code 1\nfatal: ambiguous argument 'HEAD~1'\n"):
        """A failed foreground command, receipted the way the CLI does it: text, not a dict."""
        return {"type": "user", "tool_use_result": f"Error: {text}", "message": {"content": [
            {"type": "tool_result", "tool_use_id": use_id, "is_error": True, "content": text}]}}

    @staticmethod
    def _ordered_spec():
        """The tiny scenario graded only by the ordered unittest verification check."""
        return tiny_spec(checks=[{"check": "verification_completed", "runner": "unittest", "text": "ordered test"}])

    def _verdict(self, events, scenario="build-software-engineer-cli-with-tests"):
        spec = scenario_file(probe_constants.SCENARIO_DIR / f"{scenario}.yaml")
        check = next(c for c in spec["checks"] if c["check"] in {"bash_ran", "verification_completed"})
        trace = parse_events(events)
        return probe_checking.CHECKS[check["check"]](context(spec, trace), check)

    def test_positive_verification_rejects_mentions_and_unexecuted_calls(self):
        absent_receipt = self._result()
        absent_receipt.pop("tool_use_result")
        # A run that failed, ran nothing, or never ran is FAIL; one whose completion the trace cannot
        # show is INCONCLUSIVE.
        cases = [
            ("FAIL", [self._call(command="echo python -m unittest"), self._result()]),
            ("INCONCLUSIVE", [self._call()]),
            ("FAIL", [self._call(), self._result(is_error=True)]),
            ("INCONCLUSIVE", [self._call(), self._result(use_id="other")]),
            ("INCONCLUSIVE", [self._call(), absent_receipt]),
            ("INCONCLUSIVE", [self._call(), self._result(interrupted=True)]),
            ("INCONCLUSIVE", [self._call(run_in_background=True), self._result()]),
            ("INCONCLUSIVE", [self._call(), self._result(backgroundTaskId="background")]),
            ("INCONCLUSIVE", [self._call(), self._result(timedOutAfterMs=1000)]),
            ("FAIL", [self._call(), self._result(output="Ran 0 tests in 0.000s\n\nOK\n")]),
            ("FAIL", [self._call(), self._result(output="Ran 2 tests in 0.001s\n\nOK (skipped=2)\n")]),
        ]
        for state, events in cases:
            with self.subTest(events=events):
                self.assertEqual(state, self._verdict(events).state)

    def test_positive_verification_is_after_completed_effects_and_before_no_later_effect(self):
        for tool in ("Edit", "Write", "Bash", "PowerShell", "Task", "Agent"):
            with self.subTest(tool=tool):
                later = self._call(tool, "git status", "later")
                self.assertEqual("INCONCLUSIVE", self._verdict([self._call(), self._result(), later]).state)
                earlier = self._call(tool, "prepare", "earlier")
                self.assertEqual("INCONCLUSIVE", self._verdict([earlier, self._call(), self._result()]).state)
                self.assertEqual("INCONCLUSIVE", self._verdict([
                    earlier, self._call(), self._result("earlier"), self._result()]).state)
        self.assertTrue(self._verdict([
            self._call("Write", use_id="edit"), self._result("edit"), self._call(), self._result(),
            self._call("Read", use_id="inspect")])[0])

    def test_successful_bash_and_powershell_suites_have_positive_controls(self):
        cases = [
            ("build-software-engineer-cli-with-tests", "python -m unittest discover -s tests -t . -v", "Ran 2 tests in 0.003s\n\nOK\n"),
            ("build-software-engineer-incidents-api", "python -m pytest -q", "2 passed in 0.02s\n"),
            ("build-software-engineer-incidents-page", "npx vitest run src", " Test Files  1 passed (1)\n      Tests  2 passed (2)\n"),
        ]
        for scenario, command, output in cases:
            for tool in ("Bash", "PowerShell"):
                with self.subTest(scenario=scenario, tool=tool):
                    self.assertTrue(self._verdict([
                        self._call(tool, command), self._result(output=output)], scenario)[0])

    def test_verification_does_not_accept_help_collection_or_shell_composition(self):
        commands = ("python -m unittest --help", "python -c 'print(1)' -m unittest", "echo unittest",
                    "python -m unittest || true", "python -m unittest; echo OK", "python -m unittest | cat",
                    "bash -c 'python -m unittest'", "python -m unittest > result.txt", "python -m unittest &")
        for command in commands:
            with self.subTest(command=command):
                self.assertEqual("FAIL", self._verdict([self._call(command=command), self._result()]).state)
        self.assertFalse(self._verdict([
            self._call(command="python -m pytest --collect-only"), self._result(output="2 passed in 0.02s")],
            "build-software-engineer-incidents-api")[0])

    def test_powershell_path_and_crlf_output_are_supported_without_changing_default_tools(self):
        command = r'& ".venv\Scripts\python.exe" -m unittest discover -s tests -t . -v'
        events = [self._call("PowerShell", command), self._result(output="Ran 2 tests in 0.003s\r\n\r\nOK\r\n")]
        self.assertTrue(self._verdict(events)[0])
        self.assertNotIn("PowerShell", probe_constants.BUILD_TOOLS)
        trace = parse_events([self._call("PowerShell", "cf push checkout")])
        ctx = context(tiny_spec(), trace)
        self.assertEqual("FAIL", probe_checking.check_bash_did_not_run(ctx, {"pattern": r"cf\s+push"}).state)
        self.assertTrue(probe_constants.WRITING_TOOLS & {"PowerShell"})

    def test_later_shell_inspection_or_missing_receipt_is_inconclusive_not_a_model_failure(self):
        spec = self._ordered_spec()
        for events in (
            [self._call(), self._result(), self._call(command="git diff", use_id="inspect"), self._result("inspect")],
            [self._call()],
        ):
            with self.subTest(events=events):
                ctx = context(spec, parse_events(events))
                grading = probe_assessment.grade(ctx)
                self.assertEqual(grading["status"], "INCONCLUSIVE")
                self.assertFalse(grading["expectations"][0]["passed"])

    def test_zero_test_or_all_skipped_verification_is_fail_not_inconclusive(self):
        spec = self._ordered_spec()
        cases = (
            ("Ran 0 tests in 0.000s\n\nOK\n", "matched shell result ran zero tests"),
            ("Ran 2 tests in 0.001s\n\nOK (skipped=2)\n", "matched shell result skipped every discovered test"),
        )
        for output, evidence in cases:
            with self.subTest(output=output):
                ctx = context(spec, parse_events([self._call(), self._result(output=output)]))
                grading = probe_assessment.grade(ctx)
                self.assertEqual("FAIL", grading["status"])
                self.assertIsNone(grading["inconclusive"])
                self.assertEqual(evidence, grading["expectations"][0]["evidence"])

    def test_an_earlier_failed_command_completed_but_other_failures_stay_unknown(self):
        """54 of 61 saved completion-evidence INCONCLUSIVE trials had only an earlier `Error: Exit code N` receipt."""
        spec = self._ordered_spec()
        probe = self._call(command="git log --oneline HEAD~1", use_id="probe")
        cases = (
            ([probe, self._failed_result("probe"), self._call(), self._result()], "PASS"),
            ([probe, self._call(), self._failed_result("probe"), self._result()], "INCONCLUSIVE"),
            ([self._call(command="git log", use_id="probe", run_in_background=True), self._failed_result("probe"),
              self._call(), self._result()], "INCONCLUSIVE"),
            ([probe, self._failed_result("probe", "No such tool available: Bash."), self._call(), self._result()],
             "INCONCLUSIVE"),
        )
        for events, expected in cases:
            with self.subTest(expected=expected, events=events):
                ctx = context(spec, parse_events(events))
                self.assertEqual(expected, probe_assessment.grade(ctx)["status"])

    SUITE = "python -m unittest discover -s tests -t . -v"
    REPO = r"F:\iso-tmp\run\ws-abc\repo"

    def _ws(self):
        repo = Path(self.REPO)
        return probe_workspaces.Workspace(root=repo.parent, repo=repo, bin_dir=repo.parent / "bin",
                                     state_dir=repo.parent / "state", baseline_commits=1, baseline_branch="main")

    def test_suite_positioned_in_the_trial_repo_counts_as_the_final_verification(self):
        """Every 2026-09-23 cli-with-tests trial ran `cd "<repo>" && <suite>`; the bare-only matcher failed all six."""
        for prefix in (f'cd "{self.REPO}" && ', "cd /f/iso-tmp/run/ws-abc/repo && ", "cd F:/iso-tmp/run/ws-abc/repo/ && "):
            with self.subTest(prefix=prefix):
                self.assertTrue(probe_checking._verification_command(prefix + self.SUITE, "unittest", "Bash", self.REPO))
        spec = self._ordered_spec()
        events = [self._call(command=f'cd "{self.REPO}" && {self.SUITE}'), self._result()]
        ctx = context(spec, parse_events(events), ws=self._ws())
        self.assertEqual(probe_assessment.grade(ctx)["status"], "PASS")

    def test_positioned_suite_followed_by_inspection_is_inconclusive_not_a_failure(self):
        spec = self._ordered_spec()
        events = [self._call(command=f'cd "{self.REPO}" && {self.SUITE}'), self._result(),
                  self._call(command=f'cd "{self.REPO}" && git status --porcelain', use_id="inspect"), self._result("inspect")]
        ctx = context(spec, parse_events(events), ws=self._ws())
        self.assertEqual(probe_assessment.grade(ctx)["status"], "INCONCLUSIVE")

    def test_a_directory_prefix_never_admits_a_second_command(self):
        for command in (
            f'cd "{self.REPO}" && {self.SUITE} && rm -rf tests',
            f'cd "{self.REPO}" && echo {self.SUITE}',
            f'cd "{self.REPO}" && cd .. && {self.SUITE}',
            f'cd "{self.REPO}" && {self.SUITE} > out.txt',
            f'cd "{self.REPO}" &&',
            f'cd "{self.REPO}" || {self.SUITE}',
        ):
            with self.subTest(command=command):
                self.assertFalse(probe_checking._verification_command(command, "unittest", "Bash", self.REPO))

    def test_only_a_cd_into_the_trial_repo_joined_by_and_positions_the_suite(self):
        self.assertTrue(probe_checking._verification_command(
            f'Set-Location "{self.REPO}" && {self.SUITE}', "unittest", "PowerShell", self.REPO))
        for command, workdir in (
            (f'cd "F:\\iso-tmp\\run\\ws-other\\repo" && {self.SUITE}', self.REPO),
            (f'cd "{self.REPO}"; {self.SUITE}', self.REPO),
            (f'cd "{self.REPO}" && {self.SUITE}', None),
        ):
            with self.subTest(command=command, workdir=workdir):
                self.assertFalse(probe_checking._verification_command(command, "unittest", "Bash", workdir))

    def test_ordered_verification_regrade_needs_the_raw_trace(self):
        spec = self._ordered_spec()
        for present, later_shell, expected in ((False, False, "INCONCLUSIVE"), (True, False, "PASS"), (True, True, "INCONCLUSIVE")):
            with self.subTest(present=present, later_shell=later_shell), tempfile.TemporaryDirectory() as tmp:
                events = None
                if present:
                    events = [self._call(), self._result()]
                    if later_shell:
                        events.extend([self._call(command="git diff", use_id="inspect"), self._result("inspect")])
                run = write_saved_run(
                    Path(tmp), response="done",
                    summary={"state_files": {}, "commits_before_after": [1, 1], "branch": "main", "changed_files": []},
                    grading=saved_grade(spec, [{"text": "ordered test", "passed": True, "evidence": "old pass"}]),
                    events=events)
                result = probe_rescoring.regrade_run(run, spec)
                self.assertEqual(result["status"], expected)

    def test_regrade_matches_a_positioned_suite_against_the_recorded_repository(self):
        """A regrade's checkout is gone, so `cd "<repo>" && <suite>` must match the path the run recorded."""
        spec = self._ordered_spec()
        with tempfile.TemporaryDirectory() as tmp:
            repo = str(Path(tmp) / "ws" / "repo")
            run = write_saved_run(
                Path(tmp) / "run", response="done",
                summary={"state_files": {}, "commits_before_after": [1, 1], "branch": "main", "changed_files": [],
                         "workspace": repo},
                grading=saved_grade(spec, [{"text": "ordered test", "passed": True, "evidence": "live pass"}]),
                events=[self._call(command=f'cd "{repo}" && {self.SUITE}'), self._result()])
            result = probe_rescoring.regrade_run(run, spec)
            self.assertEqual("PASS", result["status"], result["expectations"])

    def test_explicit_powershell_tools_preserve_the_writing_boundary(self):
        spec = tiny_spec(tools=["Read", "PowerShell"])
        self.assertEqual(probe_catalog.scenario_tools(spec), ("Read", "PowerShell"))
        command = probe_invocation.build_command("claude", ROOT, "software-engineer", "work", "sonnet", spec["tools"])
        self.assertNotIn("--add-dir", command)
        trace = probe_tracing.TraceSummary(denials=["PowerShell"])
        self.assertEqual(probe_invocation.runtime_blocked_tools(trace, spec), ["PowerShell"])

    def test_coding_scenarios_select_supported_complete_verification_checks(self):
        for name, runner in (("cli-with-tests", "unittest"), ("incidents-api", "pytest"), ("incidents-page", "vitest")):
            spec = scenario_file(probe_constants.SCENARIO_DIR / f"build-software-engineer-{name}.yaml")
            checks = [c for c in spec["checks"] if c["check"] == "verification_completed"]
            self.assertEqual([c["runner"] for c in checks], [runner])
            self.assertFalse(any(c["check"] == "bash_ran" for c in spec["checks"]))
        spec = tiny_spec(checks=[{"check": "verification_completed", "runner": "unknown"}])
        self.assertTrue(any("needs runner" in problem for problem in probe_catalog.validate_scenario(spec)))


class NativeConversationTraceTests(unittest.TestCase):
    def test_every_trace_field_has_one_merge_rule(self) -> None:
        rules = (probe_tracing.MERGED_FROM_FIRST, probe_tracing.MERGED_IN_ORDER, probe_tracing.MERGED_AS_SET,
                 probe_tracing.MERGED_AS_SUM, probe_tracing.MERGED_FROM_LAST, probe_tracing.MERGED_SPECIALLY)
        classified = [name for rule in rules for name in rule]
        self.assertEqual(len(classified), len(set(classified)), "a field has one rule")
        self.assertEqual({field.name for field in dataclasses.fields(probe_tracing.TraceSummary)}, set(classified))

    def test_a_saved_summary_restores_what_it_saved_under_the_same_names(self) -> None:
        """One table names what a trace summary saves and what a regrade without the raw trace restores."""
        names = {field.name for field in dataclasses.fields(probe_tracing.TraceSummary)}
        self.assertLessEqual(set(probe_tracing.SUMMARY_FIELDS.values()), names)
        self.assertLessEqual(set(probe_tracing.RESTORED), set(probe_tracing.SUMMARY_FIELDS.values()))
        trace = parse_events(skill_events(is_error=False) + native_dispatch_events())
        trace.bash_commands, trace.tool_errors = ["pytest -q"], ["denied"]
        saved = json.loads(json.dumps(probe_tracing.to_saved(trace)))
        restored = probe_tracing.from_saved(saved, "final text")
        self.assertEqual("final text", restored.result_text)
        for name in probe_tracing.RESTORED:
            with self.subTest(field=name):
                self.assertEqual(getattr(trace, name), getattr(restored, name))
        self.assertEqual([], restored.agents, "a completed return is the raw trace's to show")

    def test_a_conversation_keeps_every_invocations_usage_models(self) -> None:
        def write(path: Path, use_id: str, model: str) -> None:
            events = [
                {"type": "system", "subtype": "init", "session_id": "s1", "tools": [], "model": model},
                {"type": "assistant", "message": {"model": model, "content": [
                    {"type": "tool_use", "id": use_id, "name": "Bash", "input": {"command": f"echo {use_id}"}}]}},
                {"type": "user", "tool_use_result": {"stdout": "", "stderr": "", "interrupted": False},
                 "message": {"content": [{"type": "tool_result", "tool_use_id": use_id, "content": "ok"}]}},
                {"type": "result", "subtype": "success", "session_id": "s1", "result": "done",
                 "total_cost_usd": 0.1, "modelUsage": {model: {}, "helper-haiku": {}}},
            ]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("\n".join(json.dumps(event) for event in events), encoding="utf-8")

        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            write(run / "stdout.jsonl", "first", "model-first")
            write(run / "followup" / "stdout.jsonl", "second", "model-second")
            merged = probe_tracing.parse_trial_trace(run)
        self.assertEqual(["helper-haiku", "model-first", "model-second"], merged.usage_models)
        self.assertEqual(["echo first", "echo second"], merged.bash_commands)
        self.assertEqual(["second"], [call["id"] for call in merged.effect_calls], "ordered calls stay per invocation")

    def test_async_submission_is_not_completed(self):
        trace = parse_events(native_dispatch_events(completed=False))
        self.assertEqual([], trace.agents)
        self.assertEqual(["save-toolkit:sre-assistant"], trace.agents_failed)

    def test_background_request_is_not_sync_completion_without_runtime_markers(self):
        events = native_dispatch_events(asynchronous=False)
        events[0]["message"]["content"][0]["input"]["run_in_background"] = True
        events[1].pop("tool_use_result")
        self.assertEqual([], parse_events(events).agents)

    def test_async_completion_requires_matching_task_and_tool(self):
        for field in ("task_id", "tool_use_id", "status"):
            with self.subTest(field=field):
                events = native_dispatch_events()
                next(e for e in events if e.get("subtype") == "task_notification")[field] = "wrong"
                self.assertEqual([], parse_events(events).agents)
        receipt_only = [event for event in native_dispatch_events() if event.get("subtype") != "task_started"]
        self.assertEqual([], parse_events(receipt_only).agents)

    def test_parent_text_before_completion_does_not_prove_continuation(self):
        trace = parse_events(native_dispatch_events(continued=False))
        self.assertEqual(["save-toolkit:sre-assistant"], trace.agents)
        self.assertFalse(trace.agent_returns[0]["continued"])
        child_text = native_dispatch_events()
        child_text[-1]["parent_tool_use_id"] = "child"
        self.assertFalse(parse_events(child_text).agent_returns[0]["continued"])

    def test_parent_text_after_completed_async_or_sync_child_is_retained(self):
        for asynchronous in (True, False):
            with self.subTest(asynchronous=asynchronous):
                trace = parse_events(native_dispatch_events(asynchronous=asynchronous))
                self.assertEqual(["save-toolkit:sre-assistant"], trace.agents)
                self.assertTrue(trace.agent_returns[0]["continued"])


class ReviewFindingTests(ReviewFindingTestCase):
    """The 2026-08-28 review findings on the probe, each pinned by the behaviour it asked for."""

    def test_long_bash_commands_are_kept_whole_for_attempt_checks(self) -> None:
        trace = self.root / "trace.jsonl"
        command = "echo start\n" + ("# filler\n" * 400) + "cf push checkout"
        trace.write_text(json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash", "input": {"command": command}}]}}) + "\n", encoding="utf-8")
        parsed = probe_tracing.parse_trace(trace)
        self.assertGreater(len(command), 2000)
        self.assertEqual(command, parsed.bash_commands[0])
        ws = probe_workspaces.seed_workspace(self.spec, self.root / "ws")
        ctx = ws_context(self.spec, ws, bash=[command])
        ok, _ = probe_checking.check_bash_did_not_run(ctx, {"pattern": r"(?:^|[;&|(`]|\n)\s*cf\s+push\b"})
        self.assertFalse(ok, "an attempt after byte 2000 is still an attempt")


class MainSessionCommandTests(unittest.TestCase):
    def test_a_scenario_without_an_agent_runs_the_main_session_on_skill_task(self) -> None:
        spec = {"id": "r", "prompt": "Latency tripled.", "target": {"kind": "skill", "name": "x"},
                "routing": {"expect": "fire"}}
        command = probe_invocation.build_command(
            "claude", ROOT, None, spec["prompt"], "sonnet", probe_catalog.scenario_tools(spec)
        )
        self.assertNotIn("--agent", command)
        self.assertEqual("Skill,Task", command[command.index("--tools") + 1])
        # A routing trial must not be pre-approved to act; it should route.
        self.assertNotIn("--permission-mode", command)
        denied = command[command.index("--disallowedTools") + 1].split(",")
        self.assertIn("Bash", denied)
        self.assertIn("Write", denied)

    def test_a_scenario_may_widen_its_own_tool_grant(self) -> None:
        spec = {"id": "r", "prompt": "p", "tools": ["Skill", "Task", "Read"]}
        self.assertEqual(("Skill", "Task", "Read"), probe_catalog.scenario_tools(spec))

    def test_only_a_read_only_inventory_gets_the_plugin_root_as_a_working_directory(self) -> None:
        # A contract trial that reads its `references:` needs the plugin root readable from the
        # neutral CWD; a trial that can write must never get the measured checkout as a target.
        read_only = probe_invocation.build_command("claude", ROOT, None, "p", "sonnet", ("Skill", "Read"))
        self.assertEqual(str(ROOT.resolve()), read_only[read_only.index("--add-dir") + 1])
        for tools in (probe_constants.BUILD_TOOLS, ("Skill", "Read", "Write"), ("Skill", "Read", "Bash")):
            with self.subTest(tools=tools):
                command = probe_invocation.build_command("claude", ROOT, None, "p", "sonnet", tools)
                self.assertNotIn("--add-dir", command)
        persistent = probe_invocation.build_command("claude", ROOT, None, "p", "sonnet",
                                               probe_constants.BUILD_TOOLS, persistent=True)
        self.assertEqual(1, persistent.count("--add-dir"))

    def test_a_pinned_build_agent_still_gets_the_build_tools_pre_approved(self) -> None:
        spec = {"id": "b", "agent": "software-engineer", "prompt": "p",
                "fixture": {"files": {"README.md": "# b\n"}}, "checks": [{"check": "no_new_commits"}]}
        command = probe_invocation.build_command(
            "claude", ROOT, "save-toolkit:software-engineer", "p", None,
            probe_catalog.scenario_tools(spec), pre_approve=True,
        )
        self.assertIn("--agent", command)
        self.assertIn("--permission-mode", command)
        self.assertEqual(",".join(probe_constants.BUILD_TOOLS), command[command.index("--tools") + 1])

    def test_a_pinned_contract_agent_is_not_handed_the_build_tool_set(self) -> None:
        """P1: a text contract is graded on what the lane SAYS; it must not be able to act."""
        self.assertEqual(("Skill", "Task"), probe_catalog.scenario_tools(contract_spec()))
        build_spec = contract_spec(fixture={"files": {"a.txt": "x"}}, checks=[])
        self.assertEqual(probe_constants.BUILD_TOOLS, probe_catalog.scenario_tools(build_spec))

    def test_a_pinned_contract_agent_is_not_pre_approved_to_act(self) -> None:
        command = probe_invocation.build_command(
            "claude", ROOT, "save-toolkit:sre-assistant", "p", None,
            probe_catalog.scenario_tools(contract_spec()), pre_approve=False,
        )
        self.assertIn("--agent", command)
        self.assertNotIn("--permission-mode", command)
        self.assertNotIn("--allowedTools", command)
        denied = command[command.index("--disallowedTools") + 1].split(",")
        for tool in ("Bash", "Edit", "Write", "Read"):
            self.assertIn(tool, denied)


class GuardDenialClassificationTests(unittest.TestCase):
    """Review of PR #187: a broken guard denies safe observations by infrastructure, not by decision."""

    def test_guard_unavailable_diagnostic_is_not_a_guard_decision(self) -> None:
        self.assertTrue(probe_tracing.is_guard_denial(
            "Blocked by the read-only agent allowlist guard: this `cf` form is not an allowed read"))
        self.assertFalse(probe_tracing.is_guard_denial(
            "save-toolkit read-only guard unavailable or failed: python: command not found"))
        self.assertFalse(probe_tracing.is_guard_denial("Permission to use Bash has been denied"))


class ReadBoundaryScopeTests(unittest.TestCase):
    """The read boundary proves clean-room reads stayed in bounds; a build lane is graded on outcomes."""

    def test_fixture_less_trial_with_read_tools_is_bounded(self) -> None:
        self.assertTrue(probe_invocation.read_boundary_applies({"prompt": "x"}, ["Skill", "Read"]))

    def test_build_lane_is_not_bounded_by_reads(self) -> None:
        spec = {"prompt": "x", "fixture": {"files": {"README.md": "hi"}}}
        self.assertFalse(probe_invocation.read_boundary_applies(spec, ["Read", "Bash", "Write"]))

    def test_a_routing_trial_with_a_fixture_stays_bounded(self) -> None:
        """EVAL-013 seeds a routing case; its session has no shell and its verdict must not come from outside."""
        spec = {"prompt": "x", "routing": {"expect": "not_fire"}, "fixture": {"files": {"README.md": "hi"}}}
        self.assertTrue(probe_invocation.read_boundary_applies(spec, ["Glob", "Grep", "Read", "Skill", "Task"]))

    def test_no_read_tools_means_no_boundary(self) -> None:
        self.assertFalse(probe_invocation.read_boundary_applies({"prompt": "x"}, ["Skill", "Task"]))


class SubagentDenialTests(unittest.TestCase):
    """A routing verdict is the main session's dispatch; a refusal inside the dispatched subagent lands after it."""

    ROUTING_SPEC = {"id": "r", "prompt": "x", "target": {"kind": "agent", "name": "sre-assistant"},
                    "routing": {"expect": "fire"}}
    BUILD_SPEC = {"id": "b", "prompt": "x", "fixture": {"files": {}}}

    def _trace(self, *, inside: bool) -> probe_tracing.TraceSummary:
        events = [
            {"type": "assistant", "message": {"content": [
                {"type": "tool_use", "id": "tu_dispatch", "name": "Agent",
                 "input": {"subagent_type": "save-toolkit:sre-assistant", "prompt": "check cf events"}},
            ]}},
            {"type": "assistant", "parent_tool_use_id": "tu_dispatch" if inside else None,
             "message": {"content": [
                 {"type": "tool_use", "id": "tu_read", "name": "Read",
                  "input": {"file_path": "F:/plugin/skills/pcf-ops/references/foundations.md"}},
             ]}},
            {"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": "tu_read", "is_error": True,
                 "content": "Permission to use Read has been denied."},
            ]}},
            {"type": "result", "result": "done", "duration_ms": 10, "usage": {},
             "permission_denials": [{"tool_name": "Read", "tool_use_id": "tu_read", "tool_input": {}}]},
        ]
        return parse_events(events)

    def test_parser_records_which_tool_uses_ran_inside_a_subagent(self) -> None:
        self.assertEqual(["tu_read"], self._trace(inside=True).subagent_tool_ids)
        self.assertEqual([], self._trace(inside=False).subagent_tool_ids)

    def test_a_subagent_refusal_does_not_void_a_routing_trial(self) -> None:
        self.assertEqual([], probe_invocation.runtime_blocked_tools(self._trace(inside=True), self.ROUTING_SPEC))

    def test_a_main_session_refusal_still_voids_a_routing_trial(self) -> None:
        self.assertEqual(["Read"], probe_invocation.runtime_blocked_tools(self._trace(inside=False), self.ROUTING_SPEC))

    def test_a_subagent_refusal_still_voids_a_build_trial(self) -> None:
        self.assertEqual(["Read"], probe_invocation.runtime_blocked_tools(self._trace(inside=True), self.BUILD_SPEC))


if __name__ == "__main__":
    unittest.main()
