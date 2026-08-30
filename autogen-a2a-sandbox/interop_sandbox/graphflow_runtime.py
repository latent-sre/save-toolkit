"""Deterministic AutoGen GraphFlow analysis for the canary evidence drill."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.conditions import SourceMatchTermination
from autogen_agentchat.messages import BaseChatMessage, TextMessage
from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
from autogen_core import CancellationToken

from .contracts import (
    ANALYZER_IDS,
    AnalysisRequest,
    EvidenceSnapshot,
    canonical_json_bytes,
    canonical_sha256,
    to_plain_object,
)


GRAPH_STATE_VERSION = "canary-analysis-state/v1"
NODE_IDS = (
    "ingest",
    *ANALYZER_IDS,
    "join",
    "reconcile",
    "synthesize",
    "input_required",
)


@dataclass(frozen=True, slots=True)
class Finding:
    """One deterministic analyzer's closed finding set."""

    analyzer_id: str
    basis: tuple[str, ...]
    contradictions: tuple[str, ...]
    halt_reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Reduction:
    """Stable merge of the exact three analyzer findings."""

    analyzer_ids: tuple[str, ...]
    basis: tuple[str, ...]
    contradictions: tuple[str, ...]
    halt_reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NodeEvidence:
    """Bounded call and input-shape evidence for one graph node."""

    node_id: str
    call_count: int
    observed_input_fields: tuple[tuple[str, ...], ...]


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    """Immutable GraphFlow-layer outcome; transport mapping happens later."""

    request_version: str
    run_id: str
    case_id: str
    case_digest: str
    source_revision: str
    candidate_revision: str
    status: str
    recommendation: str | None
    basis: tuple[str, ...]
    resolved_contradictions: tuple[str, ...]
    unresolved_contradictions: tuple[str, ...]
    reconciliation_attempts: int
    graph_state_sha256: str | None
    state_path: Path | None
    route_evidence: tuple[str, ...]
    node_evidence: tuple[NodeEvidence, ...]
    graph_edges: tuple[tuple[str, str], ...]
    graph_leaf_nodes: tuple[str, ...]
    graph_has_cycle_with_exit: bool


class SlowAnalyzerControl:
    """Controllable gate used to prove AutoGen cancellation without sleeps."""

    def __init__(self) -> None:
        self.started = asyncio.Event()
        self._release = asyncio.Event()

    def release(self) -> None:
        self._release.set()

    async def wait(self, cancellation_token: CancellationToken) -> None:
        self.started.set()
        pending = asyncio.create_task(self._release.wait())
        cancellation_token.link_future(pending)
        await pending


def stable_reduce_findings(findings: Iterable[Finding]) -> Reduction:
    """Merge findings in the contract's closed analyzer-ID order."""

    by_id: dict[str, Finding] = {}
    for finding in findings:
        if finding.analyzer_id not in ANALYZER_IDS:
            raise ValueError(f"unknown analyzer ID: {finding.analyzer_id}")
        if finding.analyzer_id in by_id:
            raise ValueError(f"duplicate analyzer finding: {finding.analyzer_id}")
        by_id[finding.analyzer_id] = finding
    missing = tuple(analyzer_id for analyzer_id in ANALYZER_IDS if analyzer_id not in by_id)
    if missing:
        raise ValueError(f"missing analyzer findings: {missing}")

    ordered = tuple(by_id[analyzer_id] for analyzer_id in ANALYZER_IDS)
    return Reduction(
        analyzer_ids=ANALYZER_IDS,
        basis=tuple(token for finding in ordered for token in finding.basis),
        contradictions=tuple(
            sorted({token for finding in ordered for token in finding.contradictions})
        ),
        halt_reasons=tuple(
            sorted({token for finding in ordered for token in finding.halt_reasons})
        ),
    )


def route_synthesize(message: BaseChatMessage) -> bool:
    """Select the sole recommendation-producing exit."""

    return _route_from_message(message) == "synthesize"


def route_reconcile(message: BaseChatMessage) -> bool:
    """Select the one allowed reconciliation pass."""

    return _route_from_message(message) == "reconcile"


def route_input_required(message: BaseChatMessage) -> bool:
    """Select the non-recommendation exit for unresolved evidence."""

    return _route_from_message(message) == "input_required"


class _DeterministicAgent(BaseChatAgent):
    def __init__(self, name: str, description: str) -> None:
        super().__init__(name=name, description=description)
        self._call_count = 0
        self._observed_input_fields: list[tuple[str, ...]] = []

    @property
    def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
        return (TextMessage,)

    def _record_call(self, payload: Mapping[str, object]) -> None:
        self._call_count += 1
        self._observed_input_fields.append(tuple(sorted(payload)))

    async def on_reset(self, cancellation_token: CancellationToken) -> None:
        del cancellation_token
        self._call_count = 0
        self._observed_input_fields.clear()
        self._reset_extra_state()

    async def save_state(self) -> Mapping[str, Any]:
        return {
            "call_count": self._call_count,
            "observed_input_fields": [list(fields) for fields in self._observed_input_fields],
            "state_version": "deterministic-agent-state/v1",
            "extra": self._save_extra_state(),
        }

    async def load_state(self, state: Mapping[str, Any]) -> None:
        if set(state) != {
            "call_count",
            "observed_input_fields",
            "state_version",
            "extra",
        }:
            raise ValueError(f"invalid saved state for {self.name}")
        if state["state_version"] != "deterministic-agent-state/v1":
            raise ValueError(f"unsupported saved state for {self.name}")
        call_count = state["call_count"]
        observed = state["observed_input_fields"]
        if type(call_count) is not int or call_count < 0 or type(observed) is not list:
            raise ValueError(f"invalid saved counters for {self.name}")
        input_fields: list[tuple[str, ...]] = []
        for entry in observed:
            if type(entry) is not list or not all(type(item) is str for item in entry):
                raise ValueError(f"invalid saved input fields for {self.name}")
            input_fields.append(tuple(entry))
        self._call_count = call_count
        self._observed_input_fields = input_fields
        self._load_extra_state(state["extra"])

    def _save_extra_state(self) -> object:
        return {}

    def _load_extra_state(self, state: object) -> None:
        if state != {}:
            raise ValueError(f"invalid extra state for {self.name}")

    def _reset_extra_state(self) -> None:
        pass


class _IngestAgent(_DeterministicAgent):
    def __init__(self, sanitized_input: Mapping[str, object]) -> None:
        super().__init__("ingest", "Validate and emit the sanitized analysis input")
        self._sanitized_input = dict(sanitized_input)

    async def on_messages(
        self,
        messages: Sequence[BaseChatMessage],
        cancellation_token: CancellationToken,
    ) -> Response:
        del cancellation_token
        payload = _latest_payload(messages, "user")
        self._record_call(payload)
        if payload != self._sanitized_input:
            raise ValueError("GraphFlow input does not match the sanitized validated request")
        return _response(self.name, payload)


class _AnalyzerAgent(_DeterministicAgent):
    def __init__(
        self,
        analyzer_id: str,
        *,
        slow: bool,
        slow_control: SlowAnalyzerControl,
    ) -> None:
        super().__init__(analyzer_id, f"Deterministic {analyzer_id} evidence analysis")
        self._analyzer_id = analyzer_id
        self._slow = slow
        self._slow_control = slow_control

    async def on_messages(
        self,
        messages: Sequence[BaseChatMessage],
        cancellation_token: CancellationToken,
    ) -> Response:
        payload = _latest_payload(messages, "ingest")
        self._record_call(payload)
        _require_fields(payload, {"kind", "candidate", "evidence"}, "analysis input")
        if self._slow:
            try:
                await self._slow_control.wait(cancellation_token)
            except asyncio.CancelledError:
                raise

        evidence = payload["evidence"]
        if type(evidence) is not dict:
            raise ValueError("analysis evidence must be an object")
        finding = _analyze(self._analyzer_id, evidence)
        return _response(
            self.name,
            {
                "analyzer_id": finding.analyzer_id,
                "basis": list(finding.basis),
                "contradictions": list(finding.contradictions),
                "halt_reasons": list(finding.halt_reasons),
                "kind": "finding",
            },
        )


class _JoinAgent(_DeterministicAgent):
    def __init__(self, *, reconciliation_available: bool) -> None:
        super().__init__("join", "Stable all-join and bounded route selection")
        self._findings: dict[str, Finding] = {}
        self._initial_contradictions: tuple[str, ...] = ()
        self._reconciliation_available = reconciliation_available

    async def on_messages(
        self,
        messages: Sequence[BaseChatMessage],
        cancellation_token: CancellationToken,
    ) -> Response:
        del cancellation_token
        reconciliation_messages = [
            message for message in messages if message.source == "reconcile"
        ]
        if reconciliation_messages:
            payload = _decode_text_message(reconciliation_messages[-1])
            self._record_call(payload)
            return _response(self.name, self._join_reconciled(payload))

        finding_messages = [
            message for message in messages if message.source in ANALYZER_IDS
        ]
        if len(finding_messages) != len(ANALYZER_IDS):
            raise ValueError("join did not receive exactly three analyzer findings")
        self._record_call({"kind": "findings"})
        self._findings = {
            finding.analyzer_id: finding
            for finding in (_finding_from_message(message) for message in finding_messages)
        }
        reduction = stable_reduce_findings(self._findings.values())
        self._initial_contradictions = reduction.contradictions
        route = (
            "synthesize"
            if not reduction.contradictions
            else "reconcile"
            if self._reconciliation_available
            else "input_required"
        )
        return _response(
            self.name,
            _join_response(
                reduction,
                route=route,
                resolved=(),
                reconciliation_attempts=0,
            ),
        )

    def _join_reconciled(self, payload: Mapping[str, object]) -> Mapping[str, object]:
        _require_fields(payload, {"attempt", "evidence", "kind"}, "reconciliation")
        if payload["kind"] != "reconciliation" or payload["attempt"] != 1:
            raise ValueError("reconciliation must be the one allowed attempt")
        evidence = payload["evidence"]
        if type(evidence) is not dict:
            raise ValueError("reconciled evidence must be an object")
        findings = tuple(_analyze(analyzer_id, evidence) for analyzer_id in ANALYZER_IDS)
        reduction = stable_reduce_findings(findings)
        resolved = tuple(sorted(set(self._initial_contradictions) - set(reduction.contradictions)))
        route = "synthesize" if not reduction.contradictions else "input_required"
        return _join_response(
            reduction,
            route=route,
            resolved=resolved,
            reconciliation_attempts=1,
        )

    def _save_extra_state(self) -> object:
        return {
            "findings": {
                analyzer_id: _finding_to_object(finding)
                for analyzer_id, finding in sorted(self._findings.items())
            },
            "initial_contradictions": list(self._initial_contradictions),
        }

    def _load_extra_state(self, state: object) -> None:
        if type(state) is not dict or set(state) != {
            "findings",
            "initial_contradictions",
        }:
            raise ValueError("invalid saved join state")
        findings_value = state["findings"]
        contradictions = state["initial_contradictions"]
        if type(findings_value) is not dict or type(contradictions) is not list:
            raise ValueError("invalid saved join findings")
        self._findings = {
            analyzer_id: _finding_from_object(value)
            for analyzer_id, value in findings_value.items()
        }
        self._initial_contradictions = _string_tuple(
            contradictions, "saved join contradictions"
        )

    def _reset_extra_state(self) -> None:
        self._findings.clear()
        self._initial_contradictions = ()


class _ReconcileAgent(_DeterministicAgent):
    def __init__(self, evidence: EvidenceSnapshot | None) -> None:
        super().__init__("reconcile", "Apply the sole complete replacement evidence snapshot")
        self._evidence = evidence

    async def on_messages(
        self,
        messages: Sequence[BaseChatMessage],
        cancellation_token: CancellationToken,
    ) -> Response:
        del cancellation_token
        payload = _latest_payload(messages, "join")
        self._record_call(payload)
        if payload.get("route") != "reconcile" or payload.get("reconciliation_attempts") != 0:
            raise ValueError("reconcile received an invalid route or repeated attempt")
        if self._evidence is None:
            raise ValueError("reconciliation route has no replacement evidence")
        return _response(
            self.name,
            {
                "attempt": 1,
                "evidence": to_plain_object(self._evidence),
                "kind": "reconciliation",
            },
        )


class _OutcomeAgent(_DeterministicAgent):
    def __init__(self, name: str, expected_route: str, status: str) -> None:
        super().__init__(name, f"Emit the terminal {status} GraphFlow outcome")
        self._expected_route = expected_route
        self._status = status

    async def on_messages(
        self,
        messages: Sequence[BaseChatMessage],
        cancellation_token: CancellationToken,
    ) -> Response:
        del cancellation_token
        payload = _latest_payload(messages, "join")
        self._record_call(payload)
        if payload.get("route") != self._expected_route:
            raise ValueError(f"{self.name} received the wrong join route")
        recommendation = payload.get("recommendation")
        if self._status == "INPUT_REQUIRED":
            recommendation = None
        elif recommendation not in ("ADVANCE_CANARY", "HALT_CANARY"):
            raise ValueError("completed synthesis requires a closed recommendation")
        return _response(
            self.name,
            {
                "basis": payload["basis"],
                "kind": "outcome",
                "recommendation": recommendation,
                "reconciliation_attempts": payload["reconciliation_attempts"],
                "resolved_contradictions": payload["resolved_contradictions"],
                "status": self._status,
                "unresolved_contradictions": payload["unresolved_contradictions"],
            },
        )


@dataclass(slots=True)
class _RuntimeBundle:
    team: GraphFlow
    graph: Any
    agents: tuple[_DeterministicAgent, ...]


async def run_analysis(
    request: AnalysisRequest,
    *,
    state_directory: str | Path,
    cancellation_token: CancellationToken | None = None,
    slow_control: SlowAnalyzerControl | None = None,
) -> AnalysisResult:
    """Run, checkpoint at the first join, reload a fresh team, and continue."""

    if not isinstance(request, AnalysisRequest):
        raise TypeError("request must be a validated AnalysisRequest")
    state_root = Path(state_directory)
    if not state_root.is_dir():
        raise ValueError("state_directory must be an existing directory")
    token = CancellationToken() if cancellation_token is None else cancellation_token
    control = SlowAnalyzerControl() if slow_control is None else slow_control
    sanitized_input = _sanitized_input(request)
    first = _build_runtime(request, sanitized_input, control, pause_at_join=True)
    topology = _topology(first.graph)

    try:
        first_result = await first.team.run(
            task=canonical_json_bytes(sanitized_input).decode("utf-8"),
            cancellation_token=token,
        )
    except asyncio.CancelledError:
        return _cancelled_result(request, first, topology)

    if not any(
        isinstance(message, TextMessage) and message.source == "join"
        for message in first_result.messages
    ):
        raise RuntimeError("GraphFlow did not quiesce at the first join")

    team_state = await first.team.save_state()
    state_object = {
        "candidate_revision": request.candidate_revision,
        "case_digest": request.case_digest,
        "case_id": request.case_id,
        "run_id": request.run_id,
        "source_revision": request.source_revision,
        "state_version": GRAPH_STATE_VERSION,
        "team_state": team_state,
    }
    state_path = state_root / f"{request.run_id}.graphflow-state.json"
    state_bytes = canonical_json_bytes(state_object)
    _atomic_write(state_path, state_bytes)
    state_sha256 = canonical_sha256(state_object)

    fresh = _build_runtime(request, sanitized_input, control, pause_at_join=False)
    persisted = json.loads(state_path.read_bytes())
    if canonical_sha256(persisted) != state_sha256:
        raise RuntimeError("persisted GraphFlow state digest mismatch")
    _validate_state_lineage(persisted, request)
    await fresh.team.load_state(persisted["team_state"])
    resumed_result = await fresh.team.run(cancellation_token=token)
    outcome = _outcome_from_messages(resumed_result.messages)
    route_evidence = _route_evidence((*first_result.messages, *resumed_result.messages))
    return AnalysisResult(
        request_version=request.request_version,
        run_id=request.run_id,
        case_id=request.case_id,
        case_digest=request.case_digest,
        source_revision=request.source_revision,
        candidate_revision=request.candidate_revision,
        status=outcome["status"],
        recommendation=outcome["recommendation"],
        basis=_string_tuple(outcome["basis"], "outcome basis"),
        resolved_contradictions=_string_tuple(
            outcome["resolved_contradictions"], "resolved contradictions"
        ),
        unresolved_contradictions=_string_tuple(
            outcome["unresolved_contradictions"], "unresolved contradictions"
        ),
        reconciliation_attempts=_bounded_attempt(outcome["reconciliation_attempts"]),
        graph_state_sha256=state_sha256,
        state_path=state_path,
        route_evidence=route_evidence,
        node_evidence=_node_evidence(fresh.agents),
        graph_edges=topology[0],
        graph_leaf_nodes=topology[1],
        graph_has_cycle_with_exit=topology[2],
    )


def _build_runtime(
    request: AnalysisRequest,
    sanitized_input: Mapping[str, object],
    slow_control: SlowAnalyzerControl,
    *,
    pause_at_join: bool,
) -> _RuntimeBundle:
    ingest = _IngestAgent(sanitized_input)
    analyzers = tuple(
        _AnalyzerAgent(
            analyzer_id,
            slow=request.case.fault.slow_analyzer == analyzer_id,
            slow_control=slow_control,
        )
        for analyzer_id in ANALYZER_IDS
    )
    join = _JoinAgent(reconciliation_available=request.case.reconciliation is not None)
    reconcile = _ReconcileAgent(request.case.reconciliation)
    synthesize = _OutcomeAgent("synthesize", "synthesize", "COMPLETED")
    input_required = _OutcomeAgent(
        "input_required", "input_required", "INPUT_REQUIRED"
    )
    agents = (ingest, *analyzers, join, reconcile, synthesize, input_required)

    builder = DiGraphBuilder()
    for agent in agents:
        builder.add_node(agent)
    for analyzer in analyzers:
        builder.add_edge(ingest, analyzer)
        builder.add_edge(
            analyzer,
            join,
            activation_group="analysis",
            activation_condition="all",
        )
    builder.add_edge(join, synthesize, condition=route_synthesize)
    builder.add_edge(join, reconcile, condition=route_reconcile)
    builder.add_edge(join, input_required, condition=route_input_required)
    builder.add_edge(
        reconcile,
        join,
        activation_group="reconciliation",
        activation_condition="any",
    )
    builder.set_entry_point(ingest)
    graph = builder.build()
    termination = SourceMatchTermination(sources=["join"]) if pause_at_join else None
    team = GraphFlow(
        participants=builder.get_participants(),
        graph=graph,
        termination_condition=termination,
        max_turns=12,
    )
    return _RuntimeBundle(team=team, graph=graph, agents=agents)


def _sanitized_input(request: AnalysisRequest) -> Mapping[str, object]:
    return {
        "candidate": to_plain_object(request.case.candidate),
        "evidence": to_plain_object(request.case.evidence),
        "kind": "analysis_input",
    }


def _analyze(analyzer_id: str, evidence: Mapping[str, object]) -> Finding:
    if analyzer_id not in ANALYZER_IDS:
        raise ValueError(f"unknown analyzer ID: {analyzer_id}")
    domain = analyzer_id.removesuffix("_analyzer")
    value = evidence.get(domain)
    if type(value) is not dict:
        raise ValueError(f"missing {domain} evidence")
    if domain == "slo":
        return _analyze_slo(value)
    if domain == "deployment":
        return _analyze_deployment(value)
    return _analyze_dependency(value)


def _analyze_slo(value: Mapping[str, object]) -> Finding:
    if value["age_seconds"] > value["freshness_limit_seconds"]:
        return Finding("slo_analyzer", (), ("slo.stale",), ())
    confirmed_regression = (
        value["canary_error_ppm"] >= value["baseline_error_ppm"] * 2
        or value["burn_rate_milli"] >= 2_000
    )
    if confirmed_regression:
        return Finding(
            "slo_analyzer",
            ("slo.confirmed_regression",),
            (),
            ("slo.confirmed_regression",),
        )
    return Finding("slo_analyzer", ("slo.within_budget",), (), ())


def _analyze_deployment(value: Mapping[str, object]) -> Finding:
    contradictions: list[str] = []
    if value["age_seconds"] > value["freshness_limit_seconds"]:
        contradictions.append("deployment.stale")
    if value["configuration_drift"]:
        contradictions.append("deployment.configuration_drift")
    if not value["candidate_only_change"]:
        contradictions.append("deployment.candidate_not_isolated")
    basis = (
        ("deployment.rollback_ready",)
        if value["rollback_ready"]
        else ("deployment.rollback_unready",)
    )
    halt = () if value["rollback_ready"] else ("deployment.rollback_unready",)
    return Finding(
        "deployment_analyzer",
        basis,
        tuple(sorted(contradictions)),
        halt,
    )


def _analyze_dependency(value: Mapping[str, object]) -> Finding:
    contradictions: list[str] = []
    if value["age_seconds"] > value["freshness_limit_seconds"]:
        contradictions.append("dependency.stale")
    if value["canary_impacted"] and not value["baseline_impacted"]:
        contradictions.append("dependency.canary_only_impact")
    basis = () if contradictions else ("dependency.healthy",)
    return Finding(
        "dependency_analyzer",
        basis,
        tuple(sorted(contradictions)),
        (),
    )


def _join_response(
    reduction: Reduction,
    *,
    route: str,
    resolved: tuple[str, ...],
    reconciliation_attempts: int,
) -> Mapping[str, object]:
    recommendation: str | None = None
    if route == "synthesize":
        recommendation = (
            "HALT_CANARY" if reduction.halt_reasons else "ADVANCE_CANARY"
        )
    return {
        "basis": list(reduction.basis),
        "kind": "join",
        "recommendation": recommendation,
        "reconciliation_attempts": reconciliation_attempts,
        "resolved_contradictions": list(resolved),
        "route": route,
        "unresolved_contradictions": list(reduction.contradictions),
    }


def _finding_from_message(message: BaseChatMessage) -> Finding:
    return _finding_from_object(_decode_text_message(message))


def _finding_to_object(finding: Finding) -> Mapping[str, object]:
    return {
        "analyzer_id": finding.analyzer_id,
        "basis": list(finding.basis),
        "contradictions": list(finding.contradictions),
        "halt_reasons": list(finding.halt_reasons),
        "kind": "finding",
    }


def _finding_from_object(value: object) -> Finding:
    if type(value) is not dict:
        raise ValueError("finding must be an object")
    _require_fields(
        value,
        {"analyzer_id", "basis", "contradictions", "halt_reasons", "kind"},
        "finding",
    )
    if value["kind"] != "finding" or type(value["analyzer_id"]) is not str:
        raise ValueError("invalid finding identity")
    return Finding(
        analyzer_id=value["analyzer_id"],
        basis=_string_tuple(value["basis"], "finding basis"),
        contradictions=_string_tuple(value["contradictions"], "finding contradictions"),
        halt_reasons=_string_tuple(value["halt_reasons"], "finding halt reasons"),
    )


def _response(source: str, payload: Mapping[str, object]) -> Response:
    return Response(
        chat_message=TextMessage(
            content=canonical_json_bytes(payload).decode("utf-8"),
            source=source,
        )
    )


def _latest_payload(
    messages: Sequence[BaseChatMessage], source: str
) -> Mapping[str, object]:
    for message in reversed(messages):
        if message.source == source:
            return _decode_text_message(message)
    raise ValueError(f"missing message from {source}")


def _decode_text_message(message: BaseChatMessage) -> Mapping[str, object]:
    if not isinstance(message, TextMessage) or type(message.content) is not str:
        raise ValueError("GraphFlow agents accept only text JSON messages")
    try:
        value = json.loads(message.content)
    except json.JSONDecodeError as exc:
        raise ValueError("GraphFlow message is not JSON") from exc
    if type(value) is not dict:
        raise ValueError("GraphFlow message must be a JSON object")
    return value


def _route_from_message(message: BaseChatMessage) -> str | None:
    payload = _decode_text_message(message)
    if payload.get("kind") != "join":
        return None
    route = payload.get("route")
    return route if type(route) is str else None


def _outcome_from_messages(messages: Sequence[BaseChatMessage]) -> Mapping[str, object]:
    for message in reversed(messages):
        if message.source in ("synthesize", "input_required"):
            payload = _decode_text_message(message)
            _require_fields(
                payload,
                {
                    "basis",
                    "kind",
                    "recommendation",
                    "reconciliation_attempts",
                    "resolved_contradictions",
                    "status",
                    "unresolved_contradictions",
                },
                "outcome",
            )
            if payload["kind"] != "outcome":
                raise ValueError("terminal message is not an outcome")
            return payload
    raise RuntimeError("GraphFlow resume did not produce a terminal outcome")


def _route_evidence(messages: Sequence[BaseChatMessage]) -> tuple[str, ...]:
    evidence: list[str] = []
    for message in messages:
        if not isinstance(message, TextMessage) or type(message.content) is not str:
            continue
        try:
            payload = json.loads(message.content)
        except json.JSONDecodeError:
            continue
        if type(payload) is not dict:
            continue
        if payload.get("kind") == "join" and type(payload.get("route")) is str:
            evidence.append(f"join.{payload['route']}")
        elif payload.get("kind") == "reconciliation":
            evidence.append("reconcile.join")
        elif payload.get("kind") == "outcome":
            evidence.append(
                "synthesize.exit"
                if payload.get("status") == "COMPLETED"
                else "input_required.exit"
            )
    return tuple(evidence)


def _node_evidence(
    agents: Sequence[_DeterministicAgent],
) -> tuple[NodeEvidence, ...]:
    by_name = {agent.name: agent for agent in agents}
    return tuple(
        NodeEvidence(
            node_id=node_id,
            call_count=by_name[node_id]._call_count,
            observed_input_fields=tuple(by_name[node_id]._observed_input_fields),
        )
        for node_id in NODE_IDS
    )


def _topology(graph: Any) -> tuple[tuple[tuple[str, str], ...], tuple[str, ...], bool]:
    edges = tuple(
        sorted(
            (source, edge.target)
            for source, node in graph.nodes.items()
            for edge in node.edges
        )
    )
    return (
        edges,
        tuple(sorted(graph.get_leaf_nodes())),
        graph.has_cycles_with_exit(),
    )


def _cancelled_result(
    request: AnalysisRequest,
    runtime: _RuntimeBundle,
    topology: tuple[tuple[tuple[str, str], ...], tuple[str, ...], bool],
) -> AnalysisResult:
    canceled = tuple(
        f"{agent.name}.canceled"
        for agent in runtime.agents
        if isinstance(agent, _AnalyzerAgent)
        and agent._slow
        and agent._call_count == 1
    )
    return AnalysisResult(
        request_version=request.request_version,
        run_id=request.run_id,
        case_id=request.case_id,
        case_digest=request.case_digest,
        source_revision=request.source_revision,
        candidate_revision=request.candidate_revision,
        status="CANCELED",
        recommendation=None,
        basis=(),
        resolved_contradictions=(),
        unresolved_contradictions=(),
        reconciliation_attempts=0,
        graph_state_sha256=None,
        state_path=None,
        route_evidence=canceled,
        node_evidence=_node_evidence(runtime.agents),
        graph_edges=topology[0],
        graph_leaf_nodes=topology[1],
        graph_has_cycle_with_exit=topology[2],
    )


def _atomic_write(path: Path, value: bytes) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(value)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _validate_state_lineage(
    state: Mapping[str, object], request: AnalysisRequest
) -> None:
    expected = {
        "candidate_revision": request.candidate_revision,
        "case_digest": request.case_digest,
        "case_id": request.case_id,
        "run_id": request.run_id,
        "source_revision": request.source_revision,
        "state_version": GRAPH_STATE_VERSION,
    }
    if set(state) != {*expected, "team_state"}:
        raise RuntimeError("persisted GraphFlow state shape mismatch")
    for field, value in expected.items():
        if state[field] != value:
            raise RuntimeError(f"persisted GraphFlow state {field} mismatch")
    if type(state["team_state"]) is not dict:
        raise RuntimeError("persisted GraphFlow team state is not an object")


def _require_fields(
    value: Mapping[str, object], expected: set[str], label: str
) -> None:
    if set(value) != expected:
        raise ValueError(f"{label} has missing or unknown fields")


def _string_tuple(value: object, label: str) -> tuple[str, ...]:
    if type(value) is not list or not all(type(item) is str for item in value):
        raise ValueError(f"{label} must be an array of strings")
    return tuple(value)


def _bounded_attempt(value: object) -> int:
    if type(value) is not int or value not in (0, 1):
        raise ValueError("reconciliation attempt must be 0 or 1")
    return value
