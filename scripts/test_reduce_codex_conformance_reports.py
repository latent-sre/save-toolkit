"""Regression tests for fresh-runner Codex/Sol report reduction."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import reduce_codex_conformance_reports as reducer


class CodexReportReducerTests(unittest.TestCase):
    candidate_sha = "a" * 40
    evaluator_sha = "b" * 40

    def _report(self, label: str, *, status: str = "pass") -> dict[str, object]:
        if label == "skill":
            manifest = reducer.conformance.load_manifest(
                reducer.conformance.DEFAULT_MANIFEST
            )
            runner = Path(reducer.conformance.__file__).resolve()
        else:
            manifest = reducer.agent_conformance.load_manifest(
                reducer.agent_conformance.DEFAULT_MANIFEST
            )
            runner = Path(reducer.agent_conformance.__file__).resolve()
        results: list[dict[str, object]] = []
        totals = {key: 0 for key in reducer.conformance.MAX_SUITE_USAGE_TOKENS}
        for lane in manifest["lanes"]:
            usage = {key: 0 for key in reducer.conformance.MAX_LANE_USAGE_TOKENS}
            usage["input_tokens"] = 10
            totals["input_tokens"] += 10
            result = {
                "lane_id": lane["id"],
                "kind": lane["kind"],
                "verdict": status,
                "required": lane["required"],
                "requested_model": lane["model"],
                "reasoning_effort": lane["reasoning_effort"],
                "sandbox": lane["sandbox"],
                "approval_policy": lane["approval_policy"],
                "oracle_sha256": "c" * 64,
                "response_sha256": "d" * 64,
                "response_matched": status == "pass",
                "observed_model_exposed": True,
                "observed_model_verified": True,
                "observed_model_count": 1,
                "usage_tokens": usage,
                "cli_version": "0.145.0",
            }
            result["skill" if label == "skill" else "agent"] = lane[
                "skill" if label == "skill" else "agent"
            ]
            results.append(result)
        summary = {"fail": 0, "inconclusive": 0, "pass": 0}
        summary[status] = len(results)
        report: dict[str, object] = {
            "schema_version": 1,
            "started_at": "2026-07-31T12:00:00Z",
            "generated_at": "2026-07-31T12:00:01Z",
            "repository_commit": self.candidate_sha,
            "evaluator_commit": self.evaluator_sha,
            "raw_transcript_persisted": False,
            "plugin_inputs_dirty": False,
            "harness_inputs_dirty": False,
            "manifest_sha256": hashlib.sha256(
                reducer.conformance._canonical_json(manifest)
            ).hexdigest(),
            "runner_sha256": hashlib.sha256(runner.read_bytes()).hexdigest(),
            "plugin_source_sha256": "1" * 64,
            "usage_limits": {
                "per_lane": dict(reducer.conformance.MAX_LANE_USAGE_TOKENS),
                "per_suite": dict(reducer.conformance.MAX_SUITE_USAGE_TOKENS),
            },
            "usage_totals": totals,
            "summary": summary,
            "results": results,
        }
        source_extra: dict[str, object] = {}
        if label == "skill":
            report["installed_skill_count"] = len(
                list(
                    (
                        reducer.conformance.REPO_ROOT
                        / reducer.conformance.PLUGIN_DIRECTORY
                        / "skills"
                    ).glob("*/SKILL.md")
                )
            )
            producer = "codex_skill_conformance"
            role = "codex-skill-conformance"
            tree_digest = report["plugin_source_sha256"]
        else:
            report["agent_inputs_dirty"] = False
            report["base_runner_sha256"] = hashlib.sha256(
                Path(reducer.conformance.__file__).resolve().read_bytes()
            ).hexdigest()
            report["agent_source_sha256"] = "2" * 64
            report["installed_agent_sha256"] = "3" * 64
            report["installed_agent_count"] = len(manifest["agents"])
            producer = "codex_agent_conformance"
            role = "codex-agent-conformance"
            tree_digest = report["agent_source_sha256"]
            source_extra = {
                "agent_source_sha256": report["agent_source_sha256"],
                "installed_agent_sha256": report["installed_agent_sha256"],
                "agent_count": report["installed_agent_count"],
            }
        report["evidence"] = reducer.conformance.build_conformance_evidence(
            report,
            producer=producer,
            role=role,
            target_root=Path("candidate"),
            tree_digest=str(tree_digest),
            criterion="trusted test criterion",
            source_extra=source_extra,
        )
        return report

    @staticmethod
    def _write(path: Path, report: dict[str, object]) -> str:
        raw = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode("utf-8")
        path.write_bytes(raw)
        return hashlib.sha256(raw).hexdigest()

    def _args(self, skill: Path, agent: Path, skill_sha: str, agent_sha: str) -> argparse.Namespace:
        return argparse.Namespace(
            skill_report=skill,
            agent_report=agent,
            skill_report_sha256=skill_sha,
            agent_report_sha256=agent_sha,
            candidate_sha=self.candidate_sha,
            evaluator_sha=self.evaluator_sha,
            repository="latent-sre/sre-agents",
            workflow_ref="refs/heads/main",
            workflow_blob_sha="e" * 40,
            workflow_run_id=123,
            workflow_run_attempt=1,
            actor="reviewer",
            canary_ref=f"canary/review/{self.candidate_sha}",
            tree_sha="f" * 40,
            conformance_job_result="success",
            output=skill.parent / "attestation.json",
        )

    def test_valid_reports_produce_inspectable_attestation_facts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            skill = root / "skills.json"
            agent = root / "agents.json"
            skill_sha = self._write(skill, self._report("skill"))
            agent_sha = self._write(agent, self._report("agent"))
            attestation = reducer.build_attestation(
                self._args(skill, agent, skill_sha, agent_sha)
            )
        self.assertEqual("pass", attestation["status"])
        self.assertEqual([reducer.conformance.SOL_MODEL], attestation["requested_models"])
        self.assertEqual(skill_sha, attestation["reports"]["skills"]["sha256"])
        self.assertEqual(
            10 * attestation["reports"]["agents"]["lane_count"],
            attestation["reports"]["agents"]["usage_totals"]["input_tokens"],
        )

    def test_raw_response_field_is_rejected_even_when_digest_matches(self) -> None:
        report = self._report("skill")
        report["results"][0]["response"] = {"secret": "model text"}
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary).resolve() / "report.json"
            digest = self._write(path, report)
            with self.assertRaisesRegex(reducer.ReductionError, "forbidden raw fields"):
                reducer.validate_report(
                    "skill",
                    path,
                    expected_sha256=digest,
                    candidate_sha=self.candidate_sha,
                    evaluator_sha=self.evaluator_sha,
                )

    def test_digest_and_revision_mismatches_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary).resolve() / "report.json"
            digest = self._write(path, self._report("skill"))
            with self.assertRaisesRegex(reducer.ReductionError, "digest mismatch"):
                reducer.validate_report(
                    "skill",
                    path,
                    expected_sha256="0" * 64,
                    candidate_sha=self.candidate_sha,
                    evaluator_sha=self.evaluator_sha,
                )
            with self.assertRaisesRegex(reducer.ReductionError, "candidate SHA"):
                reducer.validate_report(
                    "skill",
                    path,
                    expected_sha256=digest,
                    candidate_sha="1" * 40,
                    evaluator_sha=self.evaluator_sha,
                )

    def test_usage_overage_and_job_result_disagreement_are_rejected(self) -> None:
        report = self._report("skill")
        report["results"][0]["usage_tokens"]["input_tokens"] = (
            reducer.conformance.MAX_LANE_USAGE_TOKENS["input_tokens"] + 1
        )
        report["usage_totals"]["input_tokens"] = report["results"][0]["usage_tokens"][
            "input_tokens"
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            over = root / "over.json"
            digest = self._write(over, report)
            with self.assertRaisesRegex(reducer.ReductionError, "usage limit"):
                reducer.validate_report(
                    "skill",
                    over,
                    expected_sha256=digest,
                    candidate_sha=self.candidate_sha,
                    evaluator_sha=self.evaluator_sha,
                )

            passing_skill = self._report("skill")
            passing_agent = self._report("agent")
            skill = root / "skills.json"
            agent = root / "agents.json"
            skill_sha = self._write(skill, passing_skill)
            agent_sha = self._write(agent, passing_agent)
            args = self._args(skill, agent, skill_sha, agent_sha)
            args.conformance_job_result = "failure"
            with self.assertRaisesRegex(reducer.ReductionError, "job result disagrees"):
                reducer.build_attestation(args)

    def test_cli_writes_new_attestation_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            skill = root / "skills.json"
            agent = root / "agents.json"
            skill_sha = self._write(skill, self._report("skill"))
            agent_sha = self._write(agent, self._report("agent"))
            output = root / "attestation.json"
            argv = [
                "--skill-report", str(skill),
                "--agent-report", str(agent),
                "--skill-report-sha256", skill_sha,
                "--agent-report-sha256", agent_sha,
                "--candidate-sha", self.candidate_sha,
                "--evaluator-sha", self.evaluator_sha,
                "--repository", "latent-sre/sre-agents",
                "--workflow-ref", "refs/heads/main",
                "--workflow-blob-sha", "e" * 40,
                "--workflow-run-id", "123",
                "--workflow-run-attempt", "1",
                "--actor", "reviewer",
                "--canary-ref", f"canary/review/{self.candidate_sha}",
                "--tree-sha", "f" * 40,
                "--conformance-job-result", "success",
                "--output", str(output),
            ]
            stdout = io.StringIO()
            stderr = io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                first = reducer.main(argv)
                second = reducer.main(argv)
            self.assertEqual(0, first)
            self.assertEqual("pass", json.loads(output.read_text(encoding="utf-8"))["status"])
            self.assertEqual(2, second)
            self.assertIn("refusing to overwrite", stderr.getvalue())

    def test_truncated_or_swapped_suite_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            truncated = self._report("skill")
            truncated["results"].pop()
            path = root / "truncated.json"
            digest = self._write(path, truncated)
            with self.assertRaisesRegex(reducer.ReductionError, "lane inventory"):
                reducer.validate_report(
                    "skill",
                    path,
                    expected_sha256=digest,
                    candidate_sha=self.candidate_sha,
                    evaluator_sha=self.evaluator_sha,
                )

            agent = self._report("agent")
            digest = self._write(path, agent)
            with self.assertRaisesRegex(reducer.ReductionError, "trusted manifest"):
                reducer.validate_report(
                    "skill",
                    path,
                    expected_sha256=digest,
                    candidate_sha=self.candidate_sha,
                    evaluator_sha=self.evaluator_sha,
                )


if __name__ == "__main__":
    unittest.main()
