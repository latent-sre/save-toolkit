"""Prove the pinned orchestration and A2A packages coexist without I/O."""

from __future__ import annotations

import json
import platform
from importlib import metadata
from typing import Any, Sequence


PROBE_VERSION = "autogen-a2a-dependency-probe/v1"
EXPECTED_PYTHON = "3.12.10"
EXPECTED_DISTRIBUTIONS = {
    "a2a-sdk": "1.1.2",
    "agent-framework-a2a": "1.0.0b260821",
    "agent-framework-core": "1.16.0",
    "autogen-agentchat": "0.7.5",
}
EXPECTED_SURFACES = {
    "a2a_v1_models": "constructed",
    "agent_framework_a2a": "constructed",
    "agent_framework_workflow": "constructed",
    "autogen_graphflow": "constructed",
}


def expected_report(python_version: str) -> dict[str, Any]:
    """Return a fresh report with the one accepted closed shape."""
    return {
        "distributions": EXPECTED_DISTRIBUTIONS.copy(),
        "probe_version": PROBE_VERSION,
        "python": python_version,
        "surfaces": EXPECTED_SURFACES.copy(),
    }


def validate_report(report: dict[str, Any]) -> dict[str, Any]:
    """Reject drift in the runtime identity or closed output contract."""
    expected = expected_report(EXPECTED_PYTHON)
    if set(report) != set(expected):
        raise ValueError("unexpected top-level dependency probe keys")
    if report["distributions"] != expected["distributions"]:
        raise ValueError("unexpected dependency distributions or versions")
    if report["probe_version"] != expected["probe_version"]:
        raise ValueError("unexpected dependency probe version")
    if report["python"] != expected["python"]:
        raise ValueError("unexpected Python version")
    if report["surfaces"] != expected["surfaces"]:
        raise ValueError("unexpected dependency probe surfaces")
    return report


def _instantiate_surfaces() -> None:
    # Imports stay inside the explicit probe so importing this module is host-safe.
    from a2a.types import (
        AgentCapabilities,
        AgentCard,
        AgentInterface,
        AgentSkill,
        Part,
    )
    from agent_framework import WorkflowBuilder
    from agent_framework.a2a import A2AAgent
    from autogen_agentchat.agents import BaseChatAgent
    from autogen_agentchat.base import Response
    from autogen_agentchat.messages import BaseChatMessage, TextMessage
    from autogen_agentchat.teams import DiGraphBuilder, GraphFlow
    from autogen_core import CancellationToken
    from google.protobuf.struct_pb2 import Struct, Value

    card = AgentCard(
        name="dependency-probe",
        description="Offline constructor probe",
        supported_interfaces=[
            AgentInterface(
                url="http://127.0.0.1:1/a2a/jsonrpc",
                protocol_binding="JSONRPC",
                protocol_version="1.0",
            )
        ],
        version=PROBE_VERSION,
        capabilities=AgentCapabilities(streaming=True),
        default_input_modes=["application/json"],
        default_output_modes=["application/json"],
        skills=[
            AgentSkill(
                id="dependency-probe",
                name="Dependency probe",
                description="Construct the public A2A v1 data surface",
                tags=["offline", "probe"],
                input_modes=["application/json"],
                output_modes=["application/json"],
            )
        ],
    )
    data_part = Part(
        data=Value(
            struct_value=Struct(
                fields={"probe": Value(string_value="constructed")}
            )
        )
    )
    if data_part.WhichOneof("content") != "data":
        raise RuntimeError("A2A v1 Part did not construct its data variant")

    a2a_agent = A2AAgent(
        id="dependency-probe",
        name="dependency-probe",
        description="Offline constructor probe",
        agent_card=card,
        timeout=1.0,
        supported_protocol_bindings=["JSONRPC"],
    )
    WorkflowBuilder(start_executor=a2a_agent, max_iterations=1).build()

    class DeterministicAgent(BaseChatAgent):
        @property
        def produced_message_types(self) -> Sequence[type[BaseChatMessage]]:
            return (TextMessage,)

        async def on_messages(
            self,
            messages: Sequence[BaseChatMessage],
            cancellation_token: CancellationToken,
        ) -> Response:
            del messages, cancellation_token
            return Response(
                chat_message=TextMessage(content="constructed", source=self.name)
            )

        async def on_reset(self, cancellation_token: CancellationToken) -> None:
            del cancellation_token

    first = DeterministicAgent("probe_first", "Offline constructor probe")
    second = DeterministicAgent("probe_second", "Offline constructor probe")
    graph_builder = DiGraphBuilder()
    graph_builder.add_node(first).add_node(second)
    graph_builder.add_edge(first, second)
    graph = graph_builder.build()
    GraphFlow(participants=graph_builder.get_participants(), graph=graph)


def build_report() -> dict[str, Any]:
    """Construct every required public surface and record exact identities."""
    _instantiate_surfaces()
    report = expected_report(platform.python_version())
    report["distributions"] = {
        name: metadata.version(name) for name in EXPECTED_DISTRIBUTIONS
    }
    return validate_report(report)


def main() -> int:
    report = build_report()
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
