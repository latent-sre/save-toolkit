#!/usr/bin/env python3
"""Observational ROUTE-001 grading for Codex Terra trials.

The evaluator accepts no provider-native activation trace for filesystem-injected skills. Skill
behavior therefore uses the existing deterministic response graders only.
The separate target-blind development probe scores one exact catalog-description selection and does
not claim that Codex invoked or loaded the selected skill.

The returned verdict owns no prompt, response, path, runtime ID, or parsed trace object.  Only
``RoutingVerdict.as_dict()`` is suitable for persisted sanitized probe evidence.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

import codex_harness
import graders


class VerdictState(str, Enum):
    """Closed trial states used by the fail-closed routing instrument."""

    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass(frozen=True)
class BehaviorGrade:
    """Persistable result of one existing response grader, without its raw detail."""

    index: int
    passed: bool

    def as_dict(self) -> dict[str, object]:
        return {"index": self.index, "passed": self.passed}


@dataclass(frozen=True)
class RoutingVerdict:
    """Serializable routing verdict containing bounded facts and fixed limitations only."""

    state: VerdictState
    evidence_mode: str
    behavior_grades: tuple[BehaviorGrade, ...]
    ancestry: None
    reason_codes: tuple[str, ...]
    limitations: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        """Return the sole persistence shape; transient trial content is not retained."""

        passed_count = sum(grade.passed for grade in self.behavior_grades)
        return {
            "schema_version": 1,
            "state": self.state.value,
            "evidence_mode": self.evidence_mode,
            "behavior": {
                "grader_count": len(self.behavior_grades),
                "passed_count": passed_count,
                "graders": [grade.as_dict() for grade in self.behavior_grades],
            },
            "ancestry": None,
            "reason_codes": list(self.reason_codes),
            "limitations": list(self.limitations),
        }


_HOOK_EVENTS = {"SessionStart", "SubagentStart", "PostToolUse"}
_COLLAB_TOOLS = {"spawn_agent", "wait", "send_input", "close_agent"}
_RESPONSE_SIZE_REASON = "response-size-limit-exceeded"
# A routing response is expected to be a short operational answer.  These limits are deliberately
# much smaller than the executor's raw-output ceiling and are checked before any response grader.
MAX_RESPONSE_BYTES = 256 * 1024
MAX_RESPONSE_LINE_BYTES = 8 * 1024
_SKILL_LIMITATIONS = (
    "The Codex 0.148 probe accepts no activation trace for filesystem-injected skills; exact "
    "activation "
    "is not asserted.",
    "Raw prompts, responses, paths, and runtime identifiers are not persisted by this verdict.",
)
_DESCRIPTION_SELECTION_LIMITATIONS = (
    "This probe measures selection from the rendered skill catalog; it does not load or grade the "
    "selected skill body.",
    "The selected name is observed from the final response, not from a provider-native skill "
    "activation event.",
    "Raw prompts, responses, paths, and runtime identifiers are not persisted by this verdict.",
)


@dataclass(frozen=True)
class _ScenarioContract:
    graders: tuple[Mapping[str, object], ...]


def _result(
    *,
    state: VerdictState,
    behavior_grades: tuple[BehaviorGrade, ...] = (),
    reason_codes: tuple[str, ...],
) -> RoutingVerdict:
    return RoutingVerdict(
        state=state,
        evidence_mode="observational-response-graders",
        behavior_grades=behavior_grades,
        ancestry=None,
        reason_codes=reason_codes,
        limitations=_SKILL_LIMITATIONS,
    )


def _parse_scenario_contract(scenario: Mapping[str, object]) -> _ScenarioContract:
    if scenario.get("mode") != "discovery":
        raise ValueError("probe scenario must be discovery mode")
    target = scenario.get("target")
    if not isinstance(target, Mapping) or target.get("kind") != "skill":
        raise ValueError("probe scenario target must be a skill")
    target_name = target.get("name")
    if not isinstance(target_name, str) or not target_name:
        raise ValueError("probe scenario target name is invalid")

    routing = scenario.get("routing")
    if (
        not isinstance(routing, Mapping)
        or routing.get("expect") != "fire"
        or routing.get("scope") is not None
    ):
        raise ValueError("probe routing contract must be one non-root positive")

    grader_specs = scenario.get("graders")
    if not isinstance(grader_specs, list) or not grader_specs:
        raise ValueError("probe scenario requires response graders")
    normalized: list[Mapping[str, object]] = []
    for spec in grader_specs:
        if not isinstance(spec, Mapping):
            raise ValueError("response grader specification must be an object")
        normalized.append(spec)
    return _ScenarioContract(graders=tuple(normalized))


def _valid_counts(values: Mapping[str, int]) -> bool:
    return all(
        isinstance(key, str)
        and bool(key)
        and isinstance(count, int)
        and not isinstance(count, bool)
        and count > 0
        for key, count in values.items()
    )


def _hook_facts_problem(hooks: codex_harness.ParsedHookReceipts) -> str | None:
    """Validate redundant sanitized hook counts before interpreting their meaning."""

    if (
        isinstance(hooks.receipt_count, bool)
        or not isinstance(hooks.receipt_count, int)
        or hooks.receipt_count < 1
        or not _valid_counts(hooks.hook_event_counts)
        or not set(hooks.hook_event_counts).issubset(_HOOK_EVENTS)
        or hooks.hook_event_counts.get("SessionStart") != 1
        or hooks.receipt_count != sum(hooks.hook_event_counts.values())
    ):
        return "hook-facts-inconsistent"
    if hooks.model_counts != {codex_harness.MODEL: hooks.receipt_count}:
        return "hook-facts-inconsistent"

    subagent_count = hooks.hook_event_counts.get("SubagentStart", 0)
    if not _valid_counts(hooks.agent_type_counts) and hooks.agent_type_counts:
        return "hook-facts-inconsistent"
    if sum(hooks.agent_type_counts.values()) != subagent_count:
        return "hook-facts-inconsistent"

    post_count = hooks.hook_event_counts.get("PostToolUse", 0)
    if post_count == 0:
        if hooks.tool_name_counts or hooks.tool_receipts or hooks.post_tool_use_facts:
            return "hook-facts-inconsistent"
        return None
    if (
        not _valid_counts(hooks.tool_name_counts)
        or sum(hooks.tool_name_counts.values()) != post_count
        or len(hooks.tool_receipts) != post_count
        or len(hooks.post_tool_use_facts) != post_count
    ):
        return "hook-facts-inconsistent"
    expected_tools = Counter(hooks.tool_name_counts)
    if Counter(fact.tool_name for fact in hooks.post_tool_use_facts) != expected_tools:
        return "hook-facts-inconsistent"
    if Counter(receipt.tool_name for receipt in hooks.tool_receipts) != expected_tools:
        return "hook-facts-inconsistent"
    return None


def _instrument_problem(
    *,
    trace: codex_harness.ParsedTrace,
    hooks: codex_harness.ParsedHookReceipts,
) -> str | None:
    """Reject every model tool or collaboration event before grading."""

    hook_problem = _hook_facts_problem(hooks)
    if hook_problem is not None:
        return hook_problem
    hook_tools = set(hooks.tool_name_counts)
    trace_tools = {fact.tool for fact in trace.collab_tool_facts}
    if trace.command_facts or not hook_tools.issubset(_COLLAB_TOOLS):
        return "forbidden-tool-observed"
    if not trace_tools.issubset(_COLLAB_TOOLS):
        return "forbidden-tool-observed"
    if (
        hooks.hook_event_counts.get("SubagentStart", 0)
        or hooks.agent_type_counts
        or hook_tools
        or trace.collab_tool_facts
    ):
        return "canary-tool-flow-observed"
    return None


def _run_behavior_graders(
    specs: tuple[Mapping[str, object], ...], response: str
) -> tuple[tuple[BehaviorGrade, ...], str | None]:
    results: list[BehaviorGrade] = []
    try:
        for index, spec in enumerate(specs):
            passed, _detail = graders.run_grader(dict(spec), response)
            results.append(BehaviorGrade(index=index, passed=passed))
    # The grader-dispatch boundary must fail closed without persisting raw detail.
    except Exception:
        return tuple(results), "grader-contract-invalid"
    return tuple(results), None


def _response_size_problem(response: str) -> str | None:
    """Apply linear byte and line bounds before dispatching any response grader."""

    encoded = response.encode("utf-8")
    if len(encoded) > MAX_RESPONSE_BYTES:
        return _RESPONSE_SIZE_REASON
    if any(len(line) > MAX_RESPONSE_LINE_BYTES for line in encoded.split(b"\n")):
        return _RESPONSE_SIZE_REASON
    return None


def grade_trial(
    scenario: Mapping[str, object],
    trace: codex_harness.ParsedTrace,
    hooks: codex_harness.ParsedHookReceipts,
) -> RoutingVerdict:
    """Grade one Terra trial without asserting unobservable filesystem-skill activation."""

    try:
        contract = _parse_scenario_contract(scenario)
    except (TypeError, ValueError):
        return _result(
            state=VerdictState.INCONCLUSIVE,
            reason_codes=("scenario-contract-invalid",),
        )

    instrument_problem = _instrument_problem(
        trace=trace,
        hooks=hooks,
    )
    if trace.terminal != "completed":
        return _result(
            state=VerdictState.INCONCLUSIVE,
            reason_codes=(instrument_problem or "trace-not-completed",),
        )
    response = trace.last_agent_message
    if not isinstance(response, str) or not response:
        return _result(
            state=VerdictState.INCONCLUSIVE,
            reason_codes=(instrument_problem or "response-missing",),
        )

    response_size_problem = _response_size_problem(response)
    if response_size_problem is not None:
        reasons = (
            (instrument_problem, response_size_problem)
            if instrument_problem is not None
            else (response_size_problem,)
        )
        return _result(
            state=VerdictState.INCONCLUSIVE,
            reason_codes=reasons,
        )

    behavior_grades, grader_problem = _run_behavior_graders(contract.graders, response)
    if grader_problem is not None:
        reasons = (
            (instrument_problem, grader_problem)
            if instrument_problem is not None
            else (grader_problem,)
        )
        return _result(
            state=VerdictState.INCONCLUSIVE,
            behavior_grades=behavior_grades,
            reason_codes=reasons,
        )
    if instrument_problem is not None:
        return _result(
            state=VerdictState.INCONCLUSIVE,
            behavior_grades=behavior_grades,
            reason_codes=(instrument_problem,),
        )
    if not all(grade.passed for grade in behavior_grades):
        return _result(
            state=VerdictState.FAIL,
            behavior_grades=behavior_grades,
            reason_codes=("behavior-grader-failed",),
        )
    return _result(
        state=VerdictState.PASS,
        behavior_grades=behavior_grades,
        reason_codes=("observational-behavior-pass",),
    )


def grade_description_selection(
    *,
    expected_skill: str,
    trace: codex_harness.ParsedTrace,
    hooks: codex_harness.ParsedHookReceipts,
) -> RoutingVerdict:
    """Grade the target-blind catalog-selection probe without loading a skill body."""

    if (
        not isinstance(expected_skill, str)
        or not expected_skill
        or expected_skill.strip() != expected_skill
    ):
        return RoutingVerdict(
            state=VerdictState.INCONCLUSIVE,
            evidence_mode="catalog-description-selection",
            behavior_grades=(),
            ancestry=None,
            reason_codes=("description-target-invalid",),
            limitations=_DESCRIPTION_SELECTION_LIMITATIONS,
        )
    instrument_problem = _instrument_problem(
        trace=trace,
        hooks=hooks,
    )
    response = trace.last_agent_message
    if trace.terminal != "completed" or not isinstance(response, str) or not response:
        return RoutingVerdict(
            state=VerdictState.INCONCLUSIVE,
            evidence_mode="catalog-description-selection",
            behavior_grades=(),
            ancestry=None,
            reason_codes=(instrument_problem or "description-response-missing",),
            limitations=_DESCRIPTION_SELECTION_LIMITATIONS,
        )
    size_problem = _response_size_problem(response)
    if instrument_problem is not None or size_problem is not None:
        return RoutingVerdict(
            state=VerdictState.INCONCLUSIVE,
            evidence_mode="catalog-description-selection",
            behavior_grades=(),
            ancestry=None,
            reason_codes=(instrument_problem or size_problem,),
            limitations=_DESCRIPTION_SELECTION_LIMITATIONS,
        )
    passed = response.strip() == expected_skill
    return RoutingVerdict(
        state=VerdictState.PASS if passed else VerdictState.FAIL,
        evidence_mode="catalog-description-selection",
        behavior_grades=(BehaviorGrade(index=0, passed=passed),),
        ancestry=None,
        reason_codes=(
            "description-selection-pass" if passed else "description-selection-failed",
        ),
        limitations=_DESCRIPTION_SELECTION_LIMITATIONS,
    )
