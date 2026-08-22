#!/usr/bin/env python3
"""Contract tests for observational Codex Terra routing verdicts."""
from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codex_harness  # noqa: E402
import codex_routing_grade  # noqa: E402


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


ROOT_THREAD = _digest("root-private-thread")
CHILD_THREAD = _digest("child-private-thread")


def _scenario(*, expect: str = "fire") -> dict[str, object]:
    return {
        "schema_version": 1,
        "id": "private-scenario-id",
        "mode": "discovery",
        "target": {"kind": "skill", "name": "private-target-skill"},
        "prompt": "private prompt that must never be serialized",
        "routing": {"expect": expect},
        "graders": [
            {"type": "contains_all", "of": ["safe-result"]},
            {"type": "not_contains", "of": ["forbidden-result"]},
        ],
    }


def _spawn_fact(
    *,
    item: str = "spawn-private-item",
    sender: str = ROOT_THREAD,
    receivers: tuple[str, ...] = (CHILD_THREAD,),
    tool: str = "spawn_agent",
    status: str = "completed",
    states: dict[str, int] | None = None,
    prompt: str = "private collab prompt",
) -> codex_harness.CollabToolFact:
    return codex_harness.CollabToolFact(
        item_sha256=_digest(item),
        tool=tool,
        status=status,
        sender_thread_sha256=sender,
        receiver_thread_sha256s=receivers,
        prompt_sha256=_digest(prompt),
        agent_state_counts=states if states is not None else {"completed": 1},
    )


def _trace(
    response: str | None = "safe-result",
    *,
    collab_facts: tuple[codex_harness.CollabToolFact, ...] = (),
    command_facts: tuple[codex_harness.CommandFact, ...] = (),
    terminal: str = "completed",
) -> codex_harness.ParsedTrace:
    return codex_harness.ParsedTrace(
        event_count=5,
        terminal=terminal,
        thread_sha256=ROOT_THREAD,
        last_agent_message=response,
        terminal_error_sha256=None,
        usage={
            "cached_input_tokens": 0,
            "cache_write_input_tokens": 0,
            "input_tokens": 10,
            "output_tokens": 5,
            "reasoning_output_tokens": 2,
        },
        command_facts=command_facts,
        collab_tool_facts=collab_facts,
    )


def _command_fact() -> codex_harness.CommandFact:
    return codex_harness.CommandFact(
        item_sha256=_digest("private-command-item"),
        command_sha256=_digest("private-command"),
        output_sha256=_digest("private-command-output"),
        output_bytes=22,
        exit_code=0,
        status="completed",
    )


def _hooks(
    *agent_types: str,
    post_tools: tuple[str, ...] = (),
) -> codex_harness.ParsedHookReceipts:
    subagent_count = len(agent_types)
    counts: dict[str, int] = {}
    for agent_type in agent_types:
        counts[agent_type] = counts.get(agent_type, 0) + 1
    tool_counts: dict[str, int] = {}
    for tool_name in post_tools:
        tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
    post_count = len(post_tools)
    return codex_harness.ParsedHookReceipts(
        receipt_count=1 + subagent_count + post_count,
        tool_receipts=tuple(
            codex_harness.TransientToolReceipt(
                tool_name=tool_name,
                agent_type=None,
                tool_input={"operation": "private collaboration input"},
                tool_response={"status": "private collaboration output"},
            )
            for tool_name in post_tools
        ),
        post_tool_use_facts=tuple(
            codex_harness.PostToolUseFact(
                tool_name=tool_name,
                agent_type=None,
                tool_input_sha256=_digest(f"{tool_name}-private-input"),
                tool_response_sha256=_digest(f"{tool_name}-private-output"),
            )
            for tool_name in post_tools
        ),
        hook_event_counts={
            "SessionStart": 1,
            **({"SubagentStart": subagent_count} if subagent_count else {}),
            **({"PostToolUse": post_count} if post_count else {}),
        },
        model_counts={codex_harness.MODEL: 1 + subagent_count + post_count},
        agent_type_counts=counts,
        tool_name_counts=tool_counts,
    )


def _hooks_with_post_tool() -> codex_harness.ParsedHookReceipts:
    return _hooks(post_tools=("shell_command",))


class ObservationalSkillRoutingTests(unittest.TestCase):
    def test_description_selection_requires_the_exact_bare_skill_name(self) -> None:
        for response, expected_state in (
            ("gcp-ops", codex_routing_grade.VerdictState.PASS),
            (" gcp-ops\n", codex_routing_grade.VerdictState.PASS),
            ("$gcp-ops", codex_routing_grade.VerdictState.FAIL),
            ("gcp-ops because it handles GCP", codex_routing_grade.VerdictState.FAIL),
            ("observability", codex_routing_grade.VerdictState.FAIL),
        ):
            with self.subTest(response=response):
                verdict = codex_routing_grade.grade_description_selection(
                    expected_skill="gcp-ops",
                    trace=_trace(response),
                    hooks=_hooks(),
                )
                self.assertEqual(expected_state, verdict.state)
                self.assertEqual("catalog-description-selection", verdict.evidence_mode)
                self.assertEqual(
                    [expected_state is codex_routing_grade.VerdictState.PASS],
                    [grade.passed for grade in verdict.behavior_grades],
                )
                self.assertTrue(
                    any("does not load" in item for item in verdict.limitations)
                )

    def test_description_selection_fails_closed_on_tool_flow(self) -> None:
        verdict = codex_routing_grade.grade_description_selection(
            expected_skill="gcp-ops",
            trace=_trace("gcp-ops"),
            hooks=_hooks_with_post_tool(),
        )

        self.assertEqual(
            codex_routing_grade.VerdictState.INCONCLUSIVE, verdict.state
        )
        self.assertIn("forbidden-tool-observed", verdict.reason_codes)

    def test_positive_skill_case_passes_only_from_existing_response_graders(self) -> None:
        verdict = codex_routing_grade.grade_trial(
            _scenario(expect="fire"), _trace(), _hooks()
        )

        self.assertEqual(verdict.state, codex_routing_grade.VerdictState.PASS)
        self.assertEqual(verdict.evidence_mode, "observational-response-graders")
        self.assertEqual([grade.passed for grade in verdict.behavior_grades], [True, True])
        self.assertIsNone(verdict.ancestry)
        self.assertTrue(any("no activation trace" in item for item in verdict.limitations))

    def test_non_root_subagent_start_without_tool_receipt_fails_closed(self) -> None:
        verdict = codex_routing_grade.grade_trial(
            _scenario(expect="fire"),
            _trace(),
            _hooks("save-toolkit-sre"),
        )

        self.assertEqual(verdict.state, codex_routing_grade.VerdictState.INCONCLUSIVE)
        self.assertIn("canary-tool-flow-observed", verdict.reason_codes)

    def test_skill_response_grader_failure_is_a_trial_failure(self) -> None:
        verdict = codex_routing_grade.grade_trial(
            _scenario(expect="fire"), _trace("wrong response"), _hooks()
        )

        self.assertEqual(verdict.state, codex_routing_grade.VerdictState.FAIL)
        self.assertEqual([grade.passed for grade in verdict.behavior_grades], [False, True])
        self.assertIn("behavior-grader-failed", verdict.reason_codes)

    def test_every_declared_response_grader_runs(self) -> None:
        scenario = _scenario()
        scenario["graders"] = [
            {"type": "contains_all", "of": ["safe-result"]},
            {"type": "contains_all", "of": ["second-result"]},
            {"type": "not_contains", "of": ["forbidden-result"]},
        ]

        verdict = codex_routing_grade.grade_trial(scenario, _trace(), _hooks())

        self.assertEqual(verdict.state, codex_routing_grade.VerdictState.FAIL)
        self.assertEqual(
            [(grade.index, grade.passed) for grade in verdict.behavior_grades],
            [(0, True), (1, False), (2, True)],
        )

    def test_total_response_limit_short_circuits_before_any_grader(self) -> None:
        response = "safe-result\n" + ("a\n" * 131_073)

        with mock.patch.object(
            codex_routing_grade.graders,
            "run_grader",
            side_effect=AssertionError("oversized response must not reach a grader"),
        ) as run_grader:
            verdict = codex_routing_grade.grade_trial(
                _scenario(), _trace(response), _hooks()
            )

        run_grader.assert_not_called()
        self.assertEqual(verdict.state, codex_routing_grade.VerdictState.INCONCLUSIVE)
        self.assertEqual(verdict.behavior_grades, ())
        self.assertEqual(verdict.reason_codes, ("response-size-limit-exceeded",))

    def test_per_line_response_limit_short_circuits_before_any_grader(self) -> None:
        response = "safe-result\n" + ("a" * 8_193)

        with mock.patch.object(
            codex_routing_grade.graders,
            "run_grader",
            side_effect=AssertionError("oversized response line must not reach a grader"),
        ) as run_grader:
            verdict = codex_routing_grade.grade_trial(
                _scenario(), _trace(response), _hooks()
            )

        run_grader.assert_not_called()
        self.assertEqual(verdict.state, codex_routing_grade.VerdictState.INCONCLUSIVE)
        self.assertEqual(verdict.behavior_grades, ())
        self.assertEqual(verdict.reason_codes, ("response-size-limit-exceeded",))


class FailClosedInstrumentTests(unittest.TestCase):
    def test_any_post_tool_receipt_forces_inconclusive_not_routing_fail(self) -> None:
        verdict = codex_routing_grade.grade_trial(
            _scenario(), _trace("wrong response"), _hooks_with_post_tool()
        )

        self.assertEqual(verdict.state, codex_routing_grade.VerdictState.INCONCLUSIVE)
        self.assertEqual(verdict.reason_codes, ("forbidden-tool-observed",))
        self.assertEqual(
            [grade.passed for grade in verdict.behavior_grades],
            [False, True],
        )

    def test_incomplete_trace_and_invalid_grader_contract_are_inconclusive(self) -> None:
        invalid_scenario = _scenario()
        invalid_scenario["graders"] = [{"type": "not-a-grader"}]
        cases = {
            "failed-turn": (_scenario(), _trace(None, terminal="failed"), "trace-not-completed"),
            "missing-response": (_scenario(), _trace(None), "response-missing"),
            "bad-grader": (invalid_scenario, _trace(), "grader-contract-invalid"),
        }
        for label, (scenario, trace, reason) in cases.items():
            with self.subTest(label=label):
                verdict = codex_routing_grade.grade_trial(scenario, trace, _hooks())
                self.assertEqual(verdict.state, codex_routing_grade.VerdictState.INCONCLUSIVE)
                self.assertIn(reason, verdict.reason_codes)

    def test_instrument_problem_wins_when_response_is_missing(self) -> None:
        verdict = codex_routing_grade.grade_trial(
            _scenario(),
            _trace(None, command_facts=(_command_fact(),)),
            _hooks(),
        )

        self.assertEqual(verdict.state, codex_routing_grade.VerdictState.INCONCLUSIVE)
        self.assertEqual(verdict.reason_codes, ("forbidden-tool-observed",))
        self.assertEqual(verdict.behavior_grades, ())

    def test_persistable_verdict_contains_no_raw_response_prompt_path_or_identifier(self) -> None:
        raw_values = (
            "private-response-marker",
            "private prompt that must never be serialized",
            "/private/routing/SKILL.md",
            "root-private-thread",
            "child-private-thread",
            ROOT_THREAD,
            CHILD_THREAD,
        )
        scenario = _scenario()
        scenario["graders"] = [{"type": "contains_all", "of": [raw_values[0]]}]
        verdict = codex_routing_grade.grade_trial(
            scenario,
            _trace(raw_values[0], collab_facts=(_spawn_fact(),)),
            _hooks("save-toolkit-sre", post_tools=("spawn_agent",)),
        )

        serialized = json.dumps(verdict.as_dict(), sort_keys=True)

        for raw_value in raw_values:
            self.assertNotIn(raw_value, serialized)
        self.assertEqual(verdict.as_dict()["schema_version"], 1)
        self.assertEqual(verdict.as_dict()["state"], "INCONCLUSIVE")
        self.assertIsNone(verdict.as_dict()["ancestry"])
        self.assertEqual(
            verdict.as_dict()["reason_codes"],
            ["canary-tool-flow-observed"],
        )

    def test_verdict_repr_does_not_retain_transient_response(self) -> None:
        raw_response = "safe-result private-response-repr-marker"

        verdict = codex_routing_grade.grade_trial(_scenario(), _trace(raw_response), _hooks())

        self.assertNotIn(raw_response, repr(verdict))

    def test_any_command_fact_is_forbidden_even_without_a_post_tool_receipt(self) -> None:
        verdict = codex_routing_grade.grade_trial(
            _scenario(),
            _trace(command_facts=(_command_fact(),)),
            _hooks(),
        )

        self.assertEqual(verdict.state, codex_routing_grade.VerdictState.INCONCLUSIVE)
        self.assertEqual(verdict.reason_codes, ("forbidden-tool-observed",))
        self.assertEqual(
            [grade.passed for grade in verdict.behavior_grades],
            [True, True],
        )

    def test_canary_forbids_even_an_allowed_collaboration_call(self) -> None:
        verdict = codex_routing_grade.grade_trial(
            _scenario(),
            _trace(collab_facts=(_spawn_fact(),)),
            _hooks("save-toolkit-sre", post_tools=("spawn_agent",)),
        )

        self.assertEqual(verdict.state, codex_routing_grade.VerdictState.INCONCLUSIVE)
        self.assertEqual(verdict.reason_codes, ("canary-tool-flow-observed",))
        self.assertIsNone(verdict.ancestry)

    def test_canary_rejects_shell_filesystem_network_and_unknown_tools(self) -> None:
        for tool_name in ("shell_command", "apply_patch", "web_run", "unknown_tool"):
            with self.subTest(tool_name=tool_name):
                verdict = codex_routing_grade.grade_trial(
                    _scenario(),
                    _trace(collab_facts=(_spawn_fact(),)),
                    _hooks(
                        "save-toolkit-sre",
                        post_tools=("spawn_agent", tool_name),
                    ),
                )

                self.assertEqual(
                    verdict.state,
                    codex_routing_grade.VerdictState.INCONCLUSIVE,
                )
                self.assertEqual(verdict.reason_codes, ("forbidden-tool-observed",))


if __name__ == "__main__":
    unittest.main(verbosity=2)
