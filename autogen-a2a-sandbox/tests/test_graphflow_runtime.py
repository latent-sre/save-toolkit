from __future__ import annotations

import asyncio
import itertools
import json
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch


SANDBOX_ROOT = Path(__file__).resolve().parents[1]
CASES_ROOT = SANDBOX_ROOT / "cases"
sys.path.insert(0, str(SANDBOX_ROOT))

from autogen_agentchat.teams import GraphFlow  # noqa: E402
from autogen_core import CancellationToken  # noqa: E402

from interop_sandbox.contracts import (  # noqa: E402
    ANALYZER_IDS,
    AnalysisRequest,
    canonical_json_bytes,
    canonical_sha256,
    to_plain_object,
    validate_analysis_request,
    verify_case_manifest,
)
from interop_sandbox.graphflow_runtime import (  # noqa: E402
    Finding,
    SlowAnalyzerControl,
    route_input_required,
    route_reconcile,
    route_synthesize,
    run_analysis,
    stable_reduce_findings,
)


SOURCE_REVISION = "0123456789abcdef0123456789abcdef01234567"


def _requests_by_case() -> dict[str, AnalysisRequest]:
    requests: dict[str, AnalysisRequest] = {}
    for case in verify_case_manifest(CASES_ROOT):
        requests[case.case_id] = validate_analysis_request(
            {
                "request_version": "canary-analysis-request/v1",
                "run_id": case.case_id,
                "source_revision": SOURCE_REVISION,
                "case_id": case.case_id,
                "case_digest": canonical_sha256(case),
                "candidate_revision": case.candidate.candidate_revision,
                "case": to_plain_object(case),
            }
        )
    return requests


def _calls(result: object) -> dict[str, int]:
    return {
        node.node_id: node.call_count  # type: ignore[attr-defined]
        for node in result.node_evidence  # type: ignore[attr-defined]
    }


class StableReducerTests(unittest.TestCase):
    def test_findings_merge_by_stable_analyzer_id_for_every_input_permutation(self) -> None:
        findings = (
            Finding(
                analyzer_id="dependency_analyzer",
                basis=("dependency.healthy",),
                contradictions=(),
                halt_reasons=(),
            ),
            Finding(
                analyzer_id="slo_analyzer",
                basis=("slo.within_budget",),
                contradictions=(),
                halt_reasons=(),
            ),
            Finding(
                analyzer_id="deployment_analyzer",
                basis=("deployment.rollback_ready",),
                contradictions=(),
                halt_reasons=(),
            ),
        )

        reductions = {
            stable_reduce_findings(permutation)
            for permutation in itertools.permutations(findings)
        }

        self.assertEqual(len(reductions), 1)
        reduction = reductions.pop()
        self.assertEqual(
            reduction.basis,
            (
                "slo.within_budget",
                "deployment.rollback_ready",
                "dependency.healthy",
            ),
        )
        self.assertEqual(reduction.analyzer_ids, ANALYZER_IDS)

    def test_reducer_rejects_missing_duplicate_or_unknown_analyzers(self) -> None:
        one = Finding("slo_analyzer", (), (), ())
        duplicate = (one, one, Finding("deployment_analyzer", (), (), ()))
        unknown = (
            one,
            Finding("deployment_analyzer", (), (), ()),
            Finding("unexpected", (), (), ()),
        )

        for invalid in (duplicate, unknown):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    stable_reduce_findings(invalid)


class GraphFlowRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.requests = _requests_by_case()

    async def _run(self, case_id: str):
        with tempfile.TemporaryDirectory() as temporary:
            state_directory = Path(temporary)
            result = await run_analysis(
                self.requests[case_id], state_directory=state_directory
            )
            state_bytes = result.state_path.read_bytes()
            state_object = json.loads(state_bytes)
            self.assertEqual(state_bytes, canonical_json_bytes(state_object))
            self.assertEqual(result.graph_state_sha256, canonical_sha256(state_object))
            self.assertEqual(state_object["state_version"], "canary-analysis-state/v1")
            self.assertEqual(state_object["run_id"], case_id)
            return result

    async def test_healthy_case_advances_after_real_checkpoint_resume(self) -> None:
        save_team_ids: list[int] = []
        load_team_ids: list[int] = []
        real_save_state = GraphFlow.save_state
        real_load_state = GraphFlow.load_state

        async def tracked_save_state(team: GraphFlow):
            save_team_ids.append(id(team))
            return await real_save_state(team)

        async def tracked_load_state(team: GraphFlow, state):
            load_team_ids.append(id(team))
            return await real_load_state(team, state)

        with patch.object(GraphFlow, "save_state", tracked_save_state), patch.object(
            GraphFlow, "load_state", tracked_load_state
        ):
            result = await self._run("mission-healthy-001")

        self.assertEqual(result.status, "COMPLETED")
        self.assertEqual(result.recommendation, "ADVANCE_CANARY")
        self.assertEqual(
            result.basis,
            (
                "slo.within_budget",
                "deployment.rollback_ready",
                "dependency.healthy",
            ),
        )
        self.assertEqual(result.route_evidence, ("join.synthesize", "synthesize.exit"))
        self.assertEqual(len(save_team_ids), 1)
        self.assertEqual(len(load_team_ids), 1)
        self.assertNotEqual(save_team_ids[0], load_team_ids[0])
        self.assertEqual(_calls(result)["slo_analyzer"], 1)
        with self.assertRaises(FrozenInstanceError):
            result.status = "CHANGED"  # type: ignore[misc]

    async def test_confirmed_regression_halts_without_reconciliation(self) -> None:
        result = await self._run("confirmed-regression-001")

        self.assertEqual((result.status, result.recommendation), ("COMPLETED", "HALT_CANARY"))
        self.assertEqual(result.reconciliation_attempts, 0)
        self.assertIn("slo.confirmed_regression", result.basis)
        self.assertEqual(_calls(result)["reconcile"], 0)

    async def test_stale_evidence_reconciles_exactly_once(self) -> None:
        result = await self._run("stale-evidence-reconciled-001")

        self.assertEqual((result.status, result.recommendation), ("COMPLETED", "ADVANCE_CANARY"))
        self.assertEqual(result.reconciliation_attempts, 1)
        self.assertEqual(result.resolved_contradictions, ("slo.stale",))
        self.assertEqual(result.unresolved_contradictions, ())
        self.assertEqual(
            result.route_evidence,
            ("join.reconcile", "reconcile.join", "join.synthesize", "synthesize.exit"),
        )
        calls = _calls(result)
        self.assertEqual(calls["reconcile"], 1)
        self.assertEqual(calls["join"], 2)
        for analyzer_id in ANALYZER_IDS:
            self.assertEqual(calls[analyzer_id], 1)

    async def test_unresolved_contradiction_requires_input_without_recommendation(self) -> None:
        result = await self._run("unresolved-contradiction-001")

        self.assertEqual(result.status, "INPUT_REQUIRED")
        self.assertIsNone(result.recommendation)
        self.assertEqual(result.reconciliation_attempts, 1)
        self.assertEqual(
            result.unresolved_contradictions,
            ("dependency.canary_only_impact",),
        )
        self.assertEqual(_calls(result)["reconcile"], 1)
        self.assertEqual(_calls(result)["input_required"], 1)

    async def test_checkpoint_resume_does_not_call_completed_analyzers_twice(self) -> None:
        result = await self._run("checkpoint-resume-001")

        self.assertEqual((result.status, result.recommendation), ("COMPLETED", "ADVANCE_CANARY"))
        for analyzer_id in ANALYZER_IDS:
            self.assertEqual(_calls(result)[analyzer_id], 1)
        self.assertEqual(_calls(result)["ingest"], 1)
        self.assertEqual(_calls(result)["join"], 1)
        self.assertEqual(_calls(result)["synthesize"], 1)

    async def test_analyzers_receive_only_candidate_and_evidence_data(self) -> None:
        result = await self._run("checkpoint-resume-001")
        evidence_by_node = {node.node_id: node for node in result.node_evidence}

        for analyzer_id in ANALYZER_IDS:
            self.assertEqual(
                evidence_by_node[analyzer_id].observed_input_fields,
                (("candidate", "evidence", "kind"),),
            )
        self.assertNotIn("autogen_ext", sys.modules)
        self.assertNotIn("openai", sys.modules)

    async def test_slow_analyzer_is_cancelable_through_autogen_token(self) -> None:
        token = CancellationToken()
        control = SlowAnalyzerControl()

        with tempfile.TemporaryDirectory() as temporary:
            run = asyncio.create_task(
                run_analysis(
                    self.requests["slow-analysis-cancel-001"],
                    state_directory=Path(temporary),
                    cancellation_token=token,
                    slow_control=control,
                )
            )
            await asyncio.wait_for(control.started.wait(), timeout=2)
            token.cancel()
            result = await asyncio.wait_for(run, timeout=2)

            self.assertEqual(result.status, "CANCELED")
            self.assertIsNone(result.recommendation)
            self.assertIsNone(result.graph_state_sha256)
            self.assertIsNone(result.state_path)
            self.assertEqual(result.route_evidence, ("dependency_analyzer.canceled",))
            self.assertEqual(list(Path(temporary).iterdir()), [])

    async def test_result_reports_actual_graph_cycle_and_reachable_exits(self) -> None:
        result = await self._run("mission-healthy-001")

        self.assertTrue(result.graph_has_cycle_with_exit)
        self.assertEqual(
            result.graph_leaf_nodes,
            ("input_required", "synthesize"),
        )
        self.assertIn(("join", "reconcile"), result.graph_edges)
        self.assertIn(("reconcile", "join"), result.graph_edges)
        self.assertIn(("join", "synthesize"), result.graph_edges)
        self.assertIn(("join", "input_required"), result.graph_edges)

    def test_route_predicates_are_named_module_level_functions(self) -> None:
        predicates = (route_synthesize, route_reconcile, route_input_required)

        self.assertEqual(
            tuple(predicate.__name__ for predicate in predicates),
            ("route_synthesize", "route_reconcile", "route_input_required"),
        )
        self.assertTrue(
            all(
                predicate.__module__ == "interop_sandbox.graphflow_runtime"
                for predicate in predicates
            )
        )


if __name__ == "__main__":
    unittest.main()
