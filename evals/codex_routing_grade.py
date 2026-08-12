#!/usr/bin/env python3
"""Observational ROUTE-001 grading for Codex Terra trials.

Codex rust-v0.147.0 does not emit an activation trace for filesystem-injected skills.  Skill
positives and near-miss negatives therefore use the existing deterministic response graders only.
Root-scoped delegation is less observable still: V2 spawn is absent from ``codex exec`` JSONL,
``PostToolUse`` does not expose a joinable plaintext delegation task, and ``wait_agent`` reports
mailbox activity rather than semantic root consumption.  Root trials therefore validate the
instrument and required terminal response, skip response graders, and deterministically remain
inconclusive.

The returned verdict owns no prompt, response, path, runtime ID, or parsed trace object.  Only
``RoutingVerdict.as_dict()`` is suitable for persisted campaign evidence.
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
_ROOT_UNOBSERVABLE_REASON = "root-delegation-unobservable-v2"
_RESPONSE_SIZE_REASON = "response-size-limit-exceeded"
# A routing response is expected to be a short operational answer.  These limits are deliberately
# much smaller than the executor's raw-output ceiling and are checked before any non-root grader.
MAX_RESPONSE_BYTES = 256 * 1024
MAX_RESPONSE_LINE_BYTES = 8 * 1024
_SKILL_LIMITATIONS = (
    "Codex 0.147 filesystem skill injection emits no activation trace; exact skill activation "
    "is not asserted.",
    "Near-miss skill negatives are graded from response behavior; target-skill absence is not "
    "asserted.",
    "Raw prompts, responses, paths, and runtime identifiers are not persisted by this verdict.",
)
_ROOT_LIMITATIONS = (
    "Codex 0.147 filesystem skill injection emits no activation trace; exact skill activation "
    "is not asserted.",
    "Root-scoped response graders are not executed because no observed event proves that the "
    "root consumed delegated semantics.",
    "Raw prompts, responses, paths, and runtime identifiers are not persisted by this verdict.",
    "Codex rust-v0.147.0 emits no V2 spawn edge in codex exec JSONL, and PostToolUse does not "
    "expose a joinable plaintext delegation task.",
    "wait_agent is a mailbox notification, not evidence that the root consumed a child's "
    "semantic result.",
    "No observed event proves semantic root consumption; root delegation is reported as "
    "INCONCLUSIVE (root-delegation-unobservable-v2).",
)


@dataclass(frozen=True)
class _ScenarioContract:
    root_scope: bool
    graders: tuple[Mapping[str, object], ...]


def _evidence_mode(root_scope: bool) -> str:
    return _ROOT_UNOBSERVABLE_REASON if root_scope else "observational-response-graders"


def _limitations(root_scope: bool) -> tuple[str, ...]:
    return _ROOT_LIMITATIONS if root_scope else _SKILL_LIMITATIONS


def _result(
    *,
    state: VerdictState,
    root_scope: bool,
    behavior_grades: tuple[BehaviorGrade, ...] = (),
    reason_codes: tuple[str, ...],
) -> RoutingVerdict:
    return RoutingVerdict(
        state=state,
        evidence_mode=_evidence_mode(root_scope),
        behavior_grades=behavior_grades,
        ancestry=None,
        reason_codes=reason_codes,
        limitations=_limitations(root_scope),
    )


def _parse_scenario_contract(scenario: Mapping[str, object]) -> _ScenarioContract:
    if scenario.get("mode") != "discovery":
        raise ValueError("campaign scenario must be discovery mode")
    target = scenario.get("target")
    if not isinstance(target, Mapping) or target.get("kind") != "skill":
        raise ValueError("campaign scenario target must be a skill")
    target_name = target.get("name")
    if not isinstance(target_name, str) or not target_name:
        raise ValueError("campaign scenario target name is invalid")

    routing = scenario.get("routing")
    if not isinstance(routing, Mapping) or routing.get("expect") not in {"fire", "not_fire"}:
        raise ValueError("campaign routing expectation is invalid")
    scope = routing.get("scope")
    if scope not in {None, "root"}:
        raise ValueError("campaign routing scope is invalid")
    root_scope = scope == "root"
    if root_scope:
        if routing.get("expect") != "not_fire":
            raise ValueError("root incident scenario must be a near-miss negative")
        alternative = routing.get("expected_alternative")
        if not isinstance(alternative, Mapping) or dict(alternative) != {
            "kind": "agent",
            "name": "sre",
        }:
            raise ValueError("root incident scenario must require the SRE alternative")

    grader_specs = scenario.get("graders")
    if not isinstance(grader_specs, list) or not grader_specs:
        raise ValueError("campaign scenario requires response graders")
    normalized: list[Mapping[str, object]] = []
    for spec in grader_specs:
        if not isinstance(spec, Mapping):
            raise ValueError("response grader specification must be an object")
        normalized.append(spec)
    return _ScenarioContract(root_scope=root_scope, graders=tuple(normalized))


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
    root_scope: bool,
    trace: codex_harness.ParsedTrace,
    hooks: codex_harness.ParsedHookReceipts,
) -> str | None:
    """Reject forbidden tools and non-root collaboration before routing interpretation."""

    hook_problem = _hook_facts_problem(hooks)
    if hook_problem is not None:
        return hook_problem
    hook_tools = set(hooks.tool_name_counts)
    trace_tools = {fact.tool for fact in trace.collab_tool_facts}
    if trace.command_facts or not hook_tools.issubset(_COLLAB_TOOLS):
        return "forbidden-tool-observed"
    if not trace_tools.issubset(_COLLAB_TOOLS):
        return "forbidden-tool-observed"
    if not root_scope and (
        hooks.hook_event_counts.get("SubagentStart", 0)
        or hooks.agent_type_counts
        or hook_tools
        or trace.collab_tool_facts
    ):
        return "non-root-tool-flow-observed"
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

    root_scope = False
    try:
        contract = _parse_scenario_contract(scenario)
        root_scope = contract.root_scope
    except (TypeError, ValueError):
        return _result(
            state=VerdictState.INCONCLUSIVE,
            root_scope=False,
            reason_codes=("scenario-contract-invalid",),
        )

    instrument_problem = _instrument_problem(
        root_scope=root_scope,
        trace=trace,
        hooks=hooks,
    )
    if trace.terminal != "completed":
        return _result(
            state=VerdictState.INCONCLUSIVE,
            root_scope=root_scope,
            reason_codes=(instrument_problem or "trace-not-completed",),
        )
    response = trace.last_agent_message
    if not isinstance(response, str) or not response:
        return _result(
            state=VerdictState.INCONCLUSIVE,
            root_scope=root_scope,
            reason_codes=(instrument_problem or "response-missing",),
        )

    if root_scope:
        return _result(
            state=VerdictState.INCONCLUSIVE,
            root_scope=True,
            reason_codes=(instrument_problem or _ROOT_UNOBSERVABLE_REASON,),
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
            root_scope=False,
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
            root_scope=root_scope,
            behavior_grades=behavior_grades,
            reason_codes=reasons,
        )
    if instrument_problem is not None:
        return _result(
            state=VerdictState.INCONCLUSIVE,
            root_scope=root_scope,
            behavior_grades=behavior_grades,
            reason_codes=(instrument_problem,),
        )
    if not all(grade.passed for grade in behavior_grades):
        return _result(
            state=VerdictState.FAIL,
            root_scope=root_scope,
            behavior_grades=behavior_grades,
            reason_codes=("behavior-grader-failed",),
        )
    return _result(
        state=VerdictState.PASS,
        root_scope=root_scope,
        behavior_grades=behavior_grades,
        reason_codes=("observational-behavior-pass",),
    )
