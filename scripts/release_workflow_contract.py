#!/usr/bin/env python3
"""Static fail-closed checks for the exact-SHA release workflow.

The validator intentionally implements only repository-specific predicates with the standard
library. GitHub still owns YAML parsing and runtime semantics; a green static check is not evidence
that the protected environments, App permissions, tag ruleset, or immutable-release setting exist.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


ACTION_SHA = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_JOBS = (
    "preflight",
    "publish_tag",
    "published_smoke",
    "finalize_release",
    "verify_release",
)
EFFECT_ENVIRONMENTS = {
    "publish_tag": "release-tag",
    "finalize_release": "release-finalize",
}
EFFECT_JOBS = tuple(EFFECT_ENVIRONMENTS)
REQUIRED_MARKERS = (
    "candidate_sha:",
    "version:",
    "expires_at:",
    "recovery_tag:",
    "review_evidence:",
    "github.run_id",
    "github.run_attempt",
    "github.rest.actions.getWorkflowRun",
    "current.data.created_at",
    "github.rest.actions.listWorkflowRuns",
    "github.rest.actions.listJobsForWorkflowRun",
    "filter: 'all'",
    "job.name === 'Publish protected release tag'",
    "job.started_at",
    "github.rest.actions.listJobsForWorkflowRunAttempt",
    "github.rest.actions.listWorkflowRunArtifacts",
    "github.workflow_ref",
    "github.workflow_sha",
    "RELEASE_REQUEST_ACTOR",
    "RELEASE_ENVIRONMENT_REVIEWER",
    "RELEASE_RECONCILIATION_KEY",
    "RELEASE_TAG_RULESET_ID",
    "save-toolkit--v",
    "refs/tags/save-toolkit--v*",
    "refs/tags/save-toolkit--attempt-v*",
    "reservationTag",
    "github.rest.git.listMatchingRefs",
    "/immutable-releases",
    "UNKNOWN_OUTCOME",
    "--marketplace-source",
    "--issued-at",
    "--require-pass",
    "--allow-vscode-file-probe-without-cli",
    "gh release verify",
    "expectedEvidenceIds",
    "/tmp/save-toolkit-host-probe-",
    "recovery-host-smoke.json",
    "release.name === releaseName",
    "(release.body || '') === body",
    "publisher-proof: hmac-sha256:",
    "permissions.actions !== 'read'",
    "ruleset bypass actors are hidden from this least-privileged token",
    "attempt < 6",
    "release remained non-immutable after bounded reconciliation",
    "releaseTagPattern.test(item.tag_name)",
    "tagObject.data.message.trim() !== expectedAnnotation",
    "grep -Ec '^Tag:[[:space:]]+'",
    "sed -n 's/^Tag:[[:space:]]*//p'",
    "packet.approval?.issued_at !== process.env.ISSUED_AT",
    "packet.approval?.expires_at !== process.env.EXPIRES_AT",
    "marketplace_checkout_clean",
    "installed_tree_matches",
    "artifact-ids: ${{ needs.preflight.outputs.packet_artifact_id }}",
    "artifact-ids: ${{ needs.published_smoke.outputs.smoke_artifact_id }}",
)


def _job_block(workflow: str, job: str) -> str | None:
    match = re.search(rf"(?m)^  {re.escape(job)}:[ \t]*$", workflow)
    if match is None:
        return None
    following = re.search(r"(?m)^  [A-Za-z0-9_-]+:[ \t]*$", workflow[match.end() :])
    end = match.end() + following.start() if following else len(workflow)
    return workflow[match.start() : end]


def _run_bodies(workflow: str) -> list[str]:
    lines = workflow.splitlines()
    bodies: list[str] = []
    index = 0
    while index < len(lines):
        match = re.match(r"^(?P<indent> +)run:\s*(?P<value>.*)$", lines[index])
        if match is None:
            index += 1
            continue
        indent = len(match.group("indent"))
        value = match.group("value")
        body = [] if value in {"|", ">", "|-", ">-"} else [value]
        index += 1
        while index < len(lines):
            line = lines[index]
            line_indent = len(line) - len(line.lstrip(" "))
            if line.strip() and line_indent <= indent:
                break
            body.append(line)
            index += 1
        bodies.append("\n".join(body))
    return bodies


def _top_level_mapping(workflow: str, key: str) -> dict[str, str] | None:
    match = re.search(rf"(?m)^{re.escape(key)}:[ \t]*$", workflow)
    if match is None:
        return None
    following = re.search(r"(?m)^[A-Za-z0-9_-]+:[ \t]*$", workflow[match.end() :])
    end = match.end() + following.start() if following else len(workflow)
    entries = re.findall(
        r"(?m)^  (?P<name>[a-z][a-z-]*):[ \t]*(?P<value>[^#\s]+)[ \t]*(?:#.*)?$",
        workflow[match.end() : end],
    )
    return dict(entries)


def validate_workflow(workflow: str) -> list[str]:
    failures: list[str] = []
    if not re.search(r"(?m)^on:[ \t]*\n  workflow_dispatch:[ \t]*$", workflow):
        failures.append("the only supported entrypoint is workflow_dispatch")
    for trigger in ("push", "pull_request", "pull_request_target", "schedule", "workflow_call"):
        if re.search(rf"(?m)^  {trigger}:[ \t]*$", workflow):
            failures.append(f"unsafe or unintended release trigger is present: {trigger}")
    expected_permissions = {"actions": "read", "contents": "read", "pull-requests": "read"}
    if _top_level_mapping(workflow, "permissions") != expected_permissions:
        failures.append(
            "top-level GITHUB_TOKEN permissions must be exactly actions: read, contents: read, "
            "and pull-requests: read"
        )
    if re.search(r"(?m)^    permissions:", workflow):
        failures.append("release jobs must not broaden GITHUB_TOKEN permissions")
    if (
        "cancel-in-progress: false" not in workflow
        or "group: save-toolkit-release" not in workflow
        or "queue: max" not in workflow
    ):
        failures.append("release effects must be serialized in a non-replacing queue")

    for marker in REQUIRED_MARKERS:
        if marker not in workflow:
            failures.append(f"required release-boundary marker is missing: {marker}")

    for match in re.finditer(r"(?m)^\s*-?\s*uses:\s*([^@\s]+)@([^\s#]+)", workflow):
        action, reference = match.groups()
        if ACTION_SHA.fullmatch(reference) is None:
            failures.append(f"action is not pinned by full commit SHA: {action}@{reference}")

    blocks: dict[str, str] = {}
    for job in EXPECTED_JOBS:
        block = _job_block(workflow, job)
        if block is None:
            failures.append(f"required release job is missing: {job}")
            continue
        blocks[job] = block
        if "runs-on: ubuntu-24.04" not in block:
            failures.append(f"release job does not pin ubuntu-24.04: {job}")
        if re.search(r"(?m)^    timeout-minutes: [1-9][0-9]*$", block) is None:
            failures.append(f"release job has no explicit timeout: {job}")

    preflight = blocks.get("preflight", "")
    if re.search(r"(?m)^    if:", preflight):
        failures.append("preflight must fail invalid dispatches explicitly, not skip the job")

    for job in EFFECT_JOBS:
        block = blocks.get(job, "")
        expected_environment = EFFECT_ENVIRONMENTS[job]
        if f"environment: {expected_environment}" not in block:
            failures.append(
                f"external-effect job is not protected by {expected_environment}: {job}"
            )
        if "actions/checkout@" in block:
            failures.append(f"external-effect job must not check out candidate bytes: {job}")
        if re.search(r"(?m)^        run:", block):
            failures.append(f"external-effect job must not execute checkout scripts: {job}")
        if "actions/create-github-app-token@" not in block:
            failures.append(f"external-effect job does not mint the scoped App token: {job}")
        if "actions/github-script@" not in block:
            failures.append(f"external-effect job does not use the pinned API client: {job}")
        if "RUN_ATTEMPT: ${{ github.run_attempt }}" not in block or (
            "if (process.env.RUN_ATTEMPT !== '1')" not in block
        ):
            failures.append(
                f"external-effect job can issue a new write during a rerun: {job}"
            )
        if "bypassActors.length !== 1" not in block or "excludes.length !== 0" not in block:
            failures.append(
                f"external-effect job does not require one exclusive App bypass and no ref exclusions: {job}"
            )
        if "reviewerNames.length !== 1" not in block:
            failures.append(
                f"external-effect job does not require exactly one configured environment reviewer: {job}"
            )
        if "refs/tags/save-toolkit--attempt-v*" not in block:
            failures.append(f"external-effect job does not enforce the reservation namespace: {job}")

    publish = blocks.get("publish_tag", "")
    if not re.search(r"(?m)^    name: Publish protected release tag$", publish):
        failures.append("tag effect job must have the stable reservation name")
    reservation = publish.find("github.rest.actions.listJobsForWorkflowRun")
    create_tag = publish.find("github.rest.git.createTag")
    if reservation < 0 or create_tag < 0 or reservation > create_tag:
        failures.append("prior-run version reservation must be checked before the first tag write")
    else:
        reservation_block = publish[reservation:create_tag]
        for marker in ("filter: 'all'", "job.conclusion !== 'skipped'", "job.started_at"):
            if marker not in reservation_block:
                failures.append(
                    f"prior-run version reservation is not fail-closed for every attempt: {marker}"
                )
        if "String(prior.id) === runId" not in publish:
            failures.append("prior-run version reservation does not exclude only the current run")
    reservation_write = publish.find("await github.rest.git.createRef({")
    if reservation_write < 0 or create_tag < 0 or reservation_write > create_tag:
        failures.append("protected version reservation must be written before the release tag object")
    for marker in (
        "save-toolkit--attempt-v${version}--run-${runId}",
        "reservation.object.sha?.toLowerCase() !== candidate",
        "reserved.data.object.sha.toLowerCase() !== candidate",
    ):
        if marker not in publish:
            failures.append(f"protected version reservation is not exact: {marker}")

    smoke = blocks.get("published_smoke", "")
    if not re.search(r"(?m)^    name: Verify published tag and recovery$", smoke):
        failures.append("published smoke job must have a stable replay-audit name")
    if smoke.find("github.rest.actions.listJobsForWorkflowRunAttempt") > smoke.find(
        "python scripts/host_install_probe.py"
    ):
        failures.append("earlier smoke attempts must be checked before another host probe")
    smoke_guard_end = smoke.find("python scripts/host_install_probe.py")
    smoke_guard = smoke[:smoke_guard_end] if smoke_guard_end >= 0 else ""
    if (
        "job.name === 'Verify published tag and recovery' && job.conclusion !== 'skipped' && job.started_at"
        not in smoke_guard
    ):
        failures.append("published smoke can replay after an earlier attempt started")
    if not re.search(r"(?m)^      - publish_tag$", smoke):
        failures.append("published smoke must consume the protected remote tag")
    if not re.search(r"(?m)^      - preflight$", smoke):
        failures.append("published smoke must consume the bound recovery SHA from preflight")
    if smoke.count("--require-pass") != 2:
        failures.append("candidate and prior-release host probes must both be strict")
    if "Retain the published-host evidence\n        if: always()" not in smoke:
        failures.append("failed published-host evidence must still be retained")
    finalize = blocks.get("finalize_release", "")
    if "RELEASE_RECONCILIATION_KEY: ${{ secrets.RELEASE_RECONCILIATION_KEY }}" not in finalize:
        failures.append("release reconciliation key must come from the protected environment secrets")
    if not re.search(r"(?m)^      - published_smoke$", finalize):
        failures.append("release finalization must wait for the published-tag smoke")
    if not re.search(r"(?m)^      - preflight$", finalize):
        failures.append("release finalization must consume the exact preflight packet")
    artifact_binding = finalize.find("name: Validate exact same-run producer artifact IDs")
    packet_download = finalize.find("name: Download the reviewed release packet")
    if artifact_binding < 0 or packet_download < 0 or artifact_binding > packet_download:
        failures.append("producer artifact IDs must be validated before either artifact download")
    else:
        binding_block = finalize[artifact_binding:packet_download]
        for marker in (
            "/^[1-9][0-9]*$/.test",
            "github.rest.actions.listWorkflowRunArtifacts",
            "release-request-attempt-",
            "release-host-smoke-attempt-",
            "packetAttempt !== smokeAttempt",
            "packetArtifact.expired !== false",
            "smokeArtifact.expired !== false",
        ):
            if marker not in binding_block:
                failures.append(
                    f"producer artifact binding is not exact and fail-closed: {marker}"
                )
    verify = blocks.get("verify_release", "")
    if "needs: finalize_release" not in verify:
        failures.append("immutable-release verification must wait for finalization")
    if "Retain immutable-release verification\n        if: always()" not in verify:
        failures.append("failed immutable-release verification evidence must still be retained")

    artifact_names = (
        "release-request-attempt-${{ github.run_attempt }}",
        "release-host-smoke-attempt-${{ github.run_attempt }}",
        "immutable-release-verification-attempt-${{ github.run_attempt }}",
    )
    for name in artifact_names:
        if workflow.count(name) != 1:
            failures.append(f"artifact name is not uniquely attempt-addressed: {name}")
    if "(?:\\.[0-9]{1,6})?Z" in workflow:
        failures.append("effect jobs accept noncanonical fractional UTC timestamps")
    if finalize.count("marketplace_checkout_clean !== true") != 1 or finalize.count(
        "installed_tree_matches !== true"
    ) != 1:
        failures.append("finalization does not require exact clean installed-tree evidence")

    if re.search(r"(?m)^\s+permission-actions:\s*(?:write|admin)\s*$", workflow):
        failures.append("publisher token must not receive workflow-dispatch authority")

    # Expressions are safe in env/with/if fields, but never splice dispatch input directly into a
    # shell program. Each run step receives those values through an environment variable instead.
    for body in _run_bodies(workflow):
        if "${{ inputs." in body or "${{ github.event." in body:
            failures.append("dispatch input is interpolated directly into a run step")

    return failures


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "workflow",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parents[1] / ".github" / "workflows" / "release.yml",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        workflow = args.workflow.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        print(f"release workflow contract: could not read {args.workflow}: {exc}", file=sys.stderr)
        return 2
    failures = validate_workflow(workflow)
    for failure in failures:
        print(f"FAIL: {failure}")
    if failures:
        print(f"Release workflow contract: FAIL ({len(failures)} issue(s))")
        return 1
    print("Release workflow contract: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
