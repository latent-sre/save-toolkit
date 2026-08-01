#!/usr/bin/env python3
"""Validate reduced Codex/Sol reports and emit one fresh-runner attestation.

This reducer runs only from the trusted-main checkout. Candidate output is untrusted data: the
reducer binds both reports to the candidate and evaluator revisions, recomputes their digests and
summaries, rejects raw/model-controlled fields and credential-shaped material, and verifies the
fixed model, sandbox, approval, time-adjacent usage, and required-lane contracts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Mapping, Sequence


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evals import run_codex_conformance as conformance  # noqa: E402
from evals import run_codex_agent_conformance as agent_conformance  # noqa: E402


FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
FORBIDDEN_RAW_KEYS = {"response", "expected", "observed_models", "usage"}
MAX_REPORT_BYTES = 128 * 1024


class ReductionError(ValueError):
    """The supplied reports cannot support a trusted attestation."""


def _reject_raw_fields(value: object) -> None:
    if isinstance(value, Mapping):
        overlap = FORBIDDEN_RAW_KEYS.intersection(value)
        if overlap:
            raise ReductionError(
                f"reduced report contains forbidden raw fields: {sorted(overlap)}"
            )
        for child in value.values():
            _reject_raw_fields(child)
    elif isinstance(value, list):
        for child in value:
            _reject_raw_fields(child)


def _hex64(value: object, label: str) -> str:
    if not isinstance(value, str) or not HEX64.fullmatch(value):
        raise ReductionError(f"{label} must be one lowercase SHA-256 digest")
    return value


def _full_sha(value: str, label: str) -> str:
    if not FULL_SHA.fullmatch(value):
        raise ReductionError(f"{label} must be one full lowercase commit SHA")
    return value


def _expected_evidence_status(summary: Mapping[str, int]) -> str:
    if summary["fail"]:
        return "fail"
    if summary["inconclusive"]:
        return "inconclusive"
    return "pass"


def _trusted_suite_contract(label: str) -> tuple[dict[str, object], str, str | None]:
    """Return the trusted manifest plus exact evaluator digests for one report type."""

    if label == "skill":
        manifest = conformance.load_manifest(conformance.DEFAULT_MANIFEST)
        runner_path = Path(conformance.__file__).resolve()
        base_runner_sha256 = None
    elif label == "agent":
        manifest = agent_conformance.load_manifest(agent_conformance.DEFAULT_MANIFEST)
        runner_path = Path(agent_conformance.__file__).resolve()
        base_runner_sha256 = hashlib.sha256(
            Path(conformance.__file__).resolve().read_bytes()
        ).hexdigest()
    else:
        raise ReductionError(f"unknown report type: {label}")
    return (
        manifest,
        hashlib.sha256(runner_path.read_bytes()).hexdigest(),
        base_runner_sha256,
    )


def _validate_trusted_lane_inventory(
    label: str,
    payload: Mapping[str, object],
    results: Sequence[Mapping[str, object]],
) -> None:
    """Bind a report to every lane and evaluator byte in the trusted-main suite."""

    manifest, runner_sha256, base_runner_sha256 = _trusted_suite_contract(label)
    manifest_sha256 = hashlib.sha256(conformance._canonical_json(manifest)).hexdigest()
    if payload.get("manifest_sha256") != manifest_sha256:
        raise ReductionError(f"{label} report is not bound to the trusted manifest")
    if payload.get("runner_sha256") != runner_sha256:
        raise ReductionError(f"{label} report is not bound to the trusted evaluator bytes")
    if base_runner_sha256 is not None and payload.get("base_runner_sha256") != base_runner_sha256:
        raise ReductionError(f"{label} report is not bound to the trusted base evaluator bytes")

    expected_lanes = {str(item["id"]): item for item in manifest["lanes"]}
    actual_lanes: dict[str, Mapping[str, object]] = {}
    for item in results:
        lane_id = item.get("lane_id")
        if not isinstance(lane_id, str) or lane_id in actual_lanes:
            raise ReductionError(f"{label} report has a missing or duplicate lane ID")
        actual_lanes[lane_id] = item
    if set(actual_lanes) != set(expected_lanes):
        raise ReductionError(f"{label} report lane inventory differs from the trusted manifest")

    for lane_id, expected in expected_lanes.items():
        actual = actual_lanes[lane_id]
        for report_field, manifest_field in (
            ("kind", "kind"),
            ("required", "required"),
            ("requested_model", "model"),
            ("reasoning_effort", "reasoning_effort"),
            ("sandbox", "sandbox"),
            ("approval_policy", "approval_policy"),
        ):
            if actual.get(report_field) != expected[manifest_field]:
                raise ReductionError(
                    f"{label} lane {lane_id!r} differs from the trusted {report_field} contract"
                )
        identity_field = "skill" if label == "skill" else "agent"
        if actual.get(identity_field) != expected[identity_field]:
            raise ReductionError(
                f"{label} lane {lane_id!r} differs from the trusted {identity_field} contract"
            )

    count_field = "installed_skill_count" if label == "skill" else "installed_agent_count"
    expected_count = (
        len(
            list(
                (conformance.REPO_ROOT / conformance.PLUGIN_DIRECTORY / "skills").glob(
                    "*/SKILL.md"
                )
            )
        )
        if label == "skill"
        else len(manifest["agents"])
    )
    if payload.get(count_field) != expected_count:
        raise ReductionError(f"{label} report installed inventory count is incomplete")


def validate_report(
    label: str,
    path: Path,
    *,
    expected_sha256: str,
    candidate_sha: str,
    evaluator_sha: str,
) -> tuple[dict[str, object], dict[str, object]]:
    """Validate one complete reduced report and return safe attestation facts."""

    report_path = conformance._assert_regular_unlinked_file(path, f"{label} reduced report")
    raw = report_path.read_bytes()
    if not raw or len(raw) > MAX_REPORT_BYTES:
        raise ReductionError(f"{label} report violates the trusted-transfer size bound")
    expected_digest = _hex64(expected_sha256, f"{label} expected digest")
    actual_digest = hashlib.sha256(raw).hexdigest()
    if actual_digest != expected_digest:
        raise ReductionError(f"{label} report digest mismatch")
    try:
        text = raw.decode("utf-8")
        payload = json.loads(text)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReductionError(f"{label} report is not one UTF-8 JSON object") from exc
    if not isinstance(payload, dict):
        raise ReductionError(f"{label} report is not one JSON object")
    conformance.assert_no_credential_output(text)
    _reject_raw_fields(payload)

    if payload.get("schema_version") != 1:
        raise ReductionError(f"{label} report schema is unsupported")
    if payload.get("repository_commit") != candidate_sha:
        raise ReductionError(f"{label} report is not bound to the candidate SHA")
    if payload.get("evaluator_commit") != evaluator_sha:
        raise ReductionError(f"{label} report is not bound to the trusted evaluator SHA")
    if payload.get("raw_transcript_persisted") is not False:
        raise ReductionError(f"{label} report claims raw transcript retention")
    for dirty_field in ("plugin_inputs_dirty", "harness_inputs_dirty", "agent_inputs_dirty"):
        if payload.get(dirty_field, False):
            raise ReductionError(f"{label} report has dirty inputs: {dirty_field}")

    expected_limits = {
        "per_lane": dict(conformance.MAX_LANE_USAGE_TOKENS),
        "per_suite": dict(conformance.MAX_SUITE_USAGE_TOKENS),
    }
    if payload.get("usage_limits") != expected_limits:
        raise ReductionError(f"{label} report changed the trusted usage limits")

    results = payload.get("results")
    if not isinstance(results, list) or not results:
        raise ReductionError(f"{label} report has no lane results")
    if any(not isinstance(item, dict) for item in results):
        raise ReductionError(f"{label} report contains a non-object lane result")
    typed_results = [item for item in results if isinstance(item, dict)]
    _validate_trusted_lane_inventory(label, payload, typed_results)
    computed_summary = {
        verdict: sum(item.get("verdict") == verdict for item in typed_results)
        for verdict in ("fail", "inconclusive", "pass")
    }
    if sum(computed_summary.values()) != len(results):
        raise ReductionError(f"{label} report contains an unknown lane verdict")
    if payload.get("summary") != computed_summary:
        raise ReductionError(f"{label} report summary does not match its lanes")
    required = [item for item in typed_results if item.get("required") is True]
    if not required:
        raise ReductionError(f"{label} report has no required lanes")

    computed_usage = {key: 0 for key in conformance.MAX_SUITE_USAGE_TOKENS}
    for item in typed_results:
        if item.get("requested_model") != conformance.SOL_MODEL:
            raise ReductionError(f"{label} report requested an unexpected model")
        if item.get("reasoning_effort") != "high" or item.get("sandbox") != "read-only":
            raise ReductionError(f"{label} report weakened the runtime boundary")
        if item.get("approval_policy") != "never":
            raise ReductionError(f"{label} report weakened the approval boundary")
        _hex64(item.get("oracle_sha256"), f"{label} oracle digest")
        response_sha = item.get("response_sha256")
        if response_sha is not None:
            _hex64(response_sha, f"{label} response digest")
        exposed = item.get("observed_model_exposed")
        verified = item.get("observed_model_verified")
        observed_count = item.get("observed_model_count")
        if (
            not isinstance(exposed, bool)
            or not isinstance(verified, bool)
            or isinstance(observed_count, bool)
            or not isinstance(observed_count, int)
            or observed_count < 0
            or exposed != (observed_count > 0)
            or (verified and not exposed)
        ):
            raise ReductionError(f"{label} lane has inconsistent observed-model evidence")
        if item.get("verdict") == "pass":
            if item.get("response_matched") is not True or response_sha is None:
                raise ReductionError(f"{label} passing lane did not match its oracle")
            if exposed and not verified:
                raise ReductionError(f"{label} passing lane exposed a different model")
            if label == "agent" and not verified:
                raise ReductionError(f"{label} passing lane lacks resolved-model evidence")
        usage = item.get("usage_tokens")
        if not isinstance(usage, dict) or set(usage) != set(conformance.MAX_LANE_USAGE_TOKENS):
            raise ReductionError(f"{label} lane lacks reduced numeric usage")
        for key, limit in conformance.MAX_LANE_USAGE_TOKENS.items():
            amount = usage.get(key)
            if isinstance(amount, bool) or not isinstance(amount, int) or not 0 <= amount <= limit:
                raise ReductionError(f"{label} lane violates the {key} usage limit")
            computed_usage[key] += amount
        if usage["input_tokens"] == 0:
            raise ReductionError(f"{label} lane reports zero input tokens")
    if payload.get("usage_totals") != computed_usage:
        raise ReductionError(f"{label} report usage totals do not match its lanes")
    if any(
        computed_usage[key] > limit
        for key, limit in conformance.MAX_SUITE_USAGE_TOKENS.items()
    ):
        raise ReductionError(f"{label} report violates the suite usage limit")

    evidence = payload.get("evidence")
    if not isinstance(evidence, dict):
        raise ReductionError(f"{label} report lacks typed evidence")
    try:
        conformance.evidence_envelope.validate_envelope(evidence)
    except ValueError as exc:
        raise ReductionError(f"{label} report has an invalid typed evidence envelope: {exc}") from exc
    source = evidence.get("source")
    target = evidence.get("target")
    if not isinstance(source, dict) or source.get("evaluator_revision") != evaluator_sha:
        raise ReductionError(f"{label} typed evidence lacks the evaluator revision")
    if not isinstance(target, dict) or target.get("revision") != candidate_sha:
        raise ReductionError(f"{label} typed evidence lacks the candidate revision")
    expected_producer = {
        "skill": {"name": "codex_skill_conformance", "role": "codex-skill-conformance"},
        "agent": {"name": "codex_agent_conformance", "role": "codex-agent-conformance"},
    }[label]
    if evidence.get("producer") != expected_producer:
        raise ReductionError(f"{label} typed evidence has the wrong producer")
    source_contract = {
        "kind": "codex-sol-conformance",
        "evaluator_revision": evaluator_sha,
        "lane_count": len(typed_results),
        "required_lane_count": len(required),
        "summary": computed_summary,
        "manifest_sha256": payload.get("manifest_sha256"),
        "runner_sha256": payload.get("runner_sha256"),
        "plugin_source_sha256": payload.get("plugin_source_sha256"),
    }
    if any(source.get(key) != value for key, value in source_contract.items()):
        raise ReductionError(f"{label} typed evidence source disagrees with the report")
    expected_tree_digest = payload.get(
        "plugin_source_sha256" if label == "skill" else "agent_source_sha256"
    )
    if target.get("tree_digest") != expected_tree_digest:
        raise ReductionError(f"{label} typed evidence tree digest disagrees with the report")
    evidence_status = _expected_evidence_status(computed_summary)
    if evidence.get("status") != evidence_status:
        raise ReductionError(f"{label} typed evidence status does not match the report")

    required_passed = all(item.get("verdict") == "pass" for item in required)
    facts: dict[str, object] = {
        "sha256": actual_digest,
        "lane_count": len(typed_results),
        "required_lane_count": len(required),
        "summary": computed_summary,
        "evidence_status": evidence_status,
        "requested_models": sorted({str(item["requested_model"]) for item in results}),
        "observed_model_exposed_count": sum(
            bool(item.get("observed_model_exposed")) for item in typed_results
        ),
        "observed_model_verified_count": sum(
            bool(item.get("observed_model_verified")) for item in typed_results
        ),
        "required_lanes_passed": required_passed,
        "usage_totals": computed_usage,
    }
    return payload, facts


def build_attestation(args: argparse.Namespace) -> dict[str, object]:
    candidate_sha = _full_sha(args.candidate_sha, "candidate SHA")
    evaluator_sha = _full_sha(args.evaluator_sha, "evaluator SHA")
    _, skill_facts = validate_report(
        "skill",
        args.skill_report,
        expected_sha256=args.skill_report_sha256,
        candidate_sha=candidate_sha,
        evaluator_sha=evaluator_sha,
    )
    _, agent_facts = validate_report(
        "agent",
        args.agent_report,
        expected_sha256=args.agent_report_sha256,
        candidate_sha=candidate_sha,
        evaluator_sha=evaluator_sha,
    )
    reports = {"skills": skill_facts, "agents": agent_facts}
    required_passed = all(bool(item["required_lanes_passed"]) for item in reports.values())
    expected_job_result = "success" if required_passed else "failure"
    if args.conformance_job_result != expected_job_result:
        raise ReductionError(
            "conformance job result disagrees with the retained required-lane facts"
        )
    statuses = {str(item["evidence_status"]) for item in reports.values()}
    overall_status = (
        "fail" if "fail" in statuses else "inconclusive" if "inconclusive" in statuses else "pass"
    )
    requested_models = sorted(
        {
            model
            for item in reports.values()
            for model in item["requested_models"]  # type: ignore[union-attr]
        }
    )
    return {
        "schema_version": 1,
        "repository": args.repository,
        "workflow_path": ".github/workflows/codex-sol-conformance.yml",
        "workflow_ref": args.workflow_ref,
        "workflow_sha": evaluator_sha,
        "workflow_blob_sha": _full_sha(args.workflow_blob_sha, "workflow blob SHA"),
        "workflow_run_id": args.workflow_run_id,
        "workflow_run_attempt": args.workflow_run_attempt,
        "actor": args.actor,
        "candidate_sha": candidate_sha,
        "canary_ref": args.canary_ref,
        "tree_sha": _full_sha(args.tree_sha, "candidate tree SHA"),
        "status": overall_status,
        "requested_models": requested_models,
        "conformance_job_result": args.conformance_job_result,
        "codex_action_sha": "dd78cb653811af44014baa08fe954e28d32c1bf9",
        "reports": reports,
        "generated_at": datetime.now(UTC).isoformat(),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-report", type=Path, required=True)
    parser.add_argument("--agent-report", type=Path, required=True)
    parser.add_argument("--skill-report-sha256", required=True)
    parser.add_argument("--agent-report-sha256", required=True)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--evaluator-sha", required=True)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--workflow-ref", required=True)
    parser.add_argument("--workflow-blob-sha", required=True)
    parser.add_argument("--workflow-run-id", type=int, required=True)
    parser.add_argument("--workflow-run-attempt", type=int, required=True)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--canary-ref", required=True)
    parser.add_argument("--tree-sha", required=True)
    parser.add_argument(
        "--conformance-job-result", choices=("success", "failure"), required=True
    )
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        attestation = build_attestation(args)
        if args.output.exists() or args.output.is_symlink():
            raise ReductionError(f"refusing to overwrite attestation output: {args.output}")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8", newline="\n") as handle:
            json.dump(attestation, handle, indent=2, sort_keys=True)
            handle.write("\n")
        print(json.dumps(attestation, indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError) as exc:
        print(f"Codex conformance report reduction error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
