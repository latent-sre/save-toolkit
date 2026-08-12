#!/usr/bin/env python3
"""Mutation tests for the protected immutable-release workflow."""

from __future__ import annotations

import unittest
from pathlib import Path

import release_workflow_contract


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"


class ReleaseWorkflowContractTests(unittest.TestCase):
    def test_tracked_workflow_satisfies_the_release_boundary(self) -> None:
        failures = release_workflow_contract.validate_workflow(WORKFLOW.read_text(encoding="utf-8"))
        self.assertEqual([], failures)

    def test_mutations_disarm_the_contract_and_are_detected(self) -> None:
        original = WORKFLOW.read_text(encoding="utf-8")
        mutations = {
            "unpinned action": original.replace(
                "actions/github-script@ed597411d8f924073f98dfc5c65a23a2325f34cd",
                "actions/github-script@v8",
                1,
            ),
            "unsafe trigger": original.replace("  workflow_dispatch:\n", "  pull_request_target:\n", 1),
            "no strict smoke": original.replace("--require-pass", "", 1),
            "candidate checkout in tag job": original.replace(
                "    steps:\n      - name: Mint scoped promotion token",
                "    steps:\n      - uses: actions/checkout@9c091bb21b7c1c1d1991bb908d89e4e9dddfe3e0\n"
                "      - name: Mint scoped promotion token",
                1,
            ),
            "no protected environment": original.replace("    environment: release-tag\n", "", 1),
            "no unknown-outcome state": original.replace("UNKNOWN_OUTCOME", "ordinary failure"),
            "rerun can issue a new write": original.replace(
                "if (process.env.RUN_ATTEMPT !== '1')",
                "if (false)",
                1,
            ),
            "extra top-level write authority": original.replace(
                "  pull-requests: read\n",
                "  pull-requests: read\n  issues: write\n",
                1,
            ),
            "missing actions history read": original.replace("  actions: read\n", "", 1),
            "pending release request can be replaced": original.replace("  queue: max\n", "", 1),
            "packet issuance uses a rerun clock": original.replace(
                "const issuedAt = current.data.created_at;",
                "const issuedAt = new Date().toISOString();",
                1,
            ),
            "packet omits stable issued at": original.replace(
                "            --issued-at \"$ISSUED_AT\" \\\n",
                "",
                1,
            ),
            "prior reservation checks latest attempt only": original.replace(
                "filter: 'all'",
                "filter: 'latest'",
                1,
            ),
            "prior reservation requires prior success": original.replace(
                "job.name === 'Publish protected release tag' && job.conclusion !== 'skipped' && job.started_at",
                "job.name === 'Publish protected release tag' && job.conclusion === 'success'",
                1,
            ),
            "durable reservation write is removed": original.replace(
                "await github.rest.git.createRef({",
                "await github.rest.git.getRef({",
                1,
            ),
            "reservation is not keyed by original run": original.replace(
                "save-toolkit--attempt-v${version}--run-${runId}",
                "save-toolkit--attempt-v${version}",
                1,
            ),
            "reservation can point at another candidate": original.replace(
                "reserved.data.object.sha.toLowerCase() !== candidate",
                "false",
                1,
            ),
            "tag ruleset omits reservation namespace": original.replace(
                "'refs/tags/save-toolkit--v*', 'refs/tags/save-toolkit--attempt-v*'",
                "'refs/tags/save-toolkit--v*'",
                1,
            ),
            "tag job reservation name drifts": original.replace(
                "    name: Publish protected release tag\n",
                "    name: Publish tag\n",
                1,
            ),
            "smoke replay audit name drifts": original.replace(
                "    name: Verify published tag and recovery\n",
                "    name: Published smoke\n",
                1,
            ),
            "smoke can resurrect after prior attempt": original.replace(
                "job.name === 'Verify published tag and recovery' && job.conclusion !== 'skipped' && job.started_at",
                "false",
                1,
            ),
            "packet artifact collides across attempts": original.replace(
                "release-request-attempt-${{ github.run_attempt }}",
                "release-request",
                1,
            ),
            "smoke artifact collides across attempts": original.replace(
                "release-host-smoke-attempt-${{ github.run_attempt }}",
                "release-host-smoke",
                1,
            ),
            "verification artifact collides across attempts": original.replace(
                "immutable-release-verification-attempt-${{ github.run_attempt }}",
                "immutable-release-verification",
                1,
            ),
            "finalizer downloads packet by mutable name": original.replace(
                "artifact-ids: ${{ needs.preflight.outputs.packet_artifact_id }}",
                "name: release-request",
                1,
            ),
            "finalizer downloads smoke by mutable name": original.replace(
                "artifact-ids: ${{ needs.published_smoke.outputs.smoke_artifact_id }}",
                "name: release-host-smoke",
                1,
            ),
            "finalizer skips same-run artifact validation": original.replace(
                "github.rest.actions.listWorkflowRunArtifacts",
                "github.rest.actions.listWorkflowRuns",
                1,
            ),
            "finalizer accepts empty artifact IDs": original.replace(
                "if (![runId, runAttempt, packetId, smokeId].every((value) => /^[1-9][0-9]*$/.test(value || '')))",
                "if (false)",
                1,
            ),
            "finalizer accepts artifacts from different attempts": original.replace(
                "packetAttempt !== smokeAttempt",
                "false",
                1,
            ),
            "finalizer accepts expired producer artifacts": original.replace(
                "packetArtifact.expired !== false || smokeArtifact.expired !== false",
                "false",
                1,
            ),
            "fractional expiry reaches an effect job": original.replace(
                "[0-9]{2}Z$/.test(process.env.EXPIRES_AT || '')",
                "[0-9]{2}(?:\\.[0-9]{1,6})?Z$/.test(process.env.EXPIRES_AT || '')",
                1,
            ),
            "packet expiry accepts equivalent noncanonical text": original.replace(
                "packet.approval?.expires_at !== process.env.EXPIRES_AT",
                "Date.parse(packet.approval?.expires_at) !== Date.parse(process.env.EXPIRES_AT)",
                1,
            ),
            "finalizer trusts installed tree metadata": original.replace(
                "item.source?.details?.installed_tree_matches !== true",
                "false",
                1,
            ),
            "publisher token gains workflow-dispatch authority": original.replace(
                "          repositories: save-toolkit\n",
                "          repositories: save-toolkit\n          permission-actions: write\n",
                1,
            ),
            "ruleset admits another bypass actor": original.replace(
                "bypassActors.length !== 1",
                "bypassActors.length < 1",
                1,
            ),
            "environment admits another reviewer": original.replace(
                "reviewerNames.length !== 1",
                "reviewerNames.length < 1",
                1,
            ),
            "finalizer reuses the tag environment": original.replace(
                "    environment: release-finalize\n",
                "    environment: release-tag\n",
                1,
            ),
            "invalid request skips green": original.replace(
                "    runs-on: ubuntu-24.04\n",
                "    if: github.ref == 'refs/heads/main'\n    runs-on: ubuntu-24.04\n",
                1,
            ),
            "dry-run tag uses substring matching": original.replace(
                "test \"$(grep -Ec '^Tag:[[:space:]]+' \"$RUNNER_TEMP/claude-tag-dry-run.txt\")\" -eq 1",
                "grep -F -- \"$EXPECTED_TAG\" \"$RUNNER_TEMP/claude-tag-dry-run.txt\"",
                1,
            ),
            "failed smoke evidence disappears": original.replace(
                "Retain the published-host evidence\n        if: always()",
                "Retain the published-host evidence",
                1,
            ),
            "smoke loses bound recovery sha": original.replace(
                "    needs:\n      - preflight\n      - publish_tag",
                "    needs: publish_tag",
                1,
            ),
            "release reconciliation accepts extra body": original.replace(
                "(release.body || '') === body",
                "metadata.every((line) => (release.body || '').includes(line))",
                1,
            ),
            "release drops the protected publisher proof": original.replace(
                "`publisher-proof: hmac-sha256:${publisherProof}`",
                "`publisher-proof: missing`",
                1,
            ),
            "publisher proof key becomes a repository variable": original.replace(
                "RELEASE_RECONCILIATION_KEY: ${{ secrets.RELEASE_RECONCILIATION_KEY }}",
                "RELEASE_RECONCILIATION_KEY: ${{ vars.RELEASE_RECONCILIATION_KEY }}",
                1,
            ),
            "immutable release has no propagation window": original.replace(
                "attempt < 6",
                "attempt < 1",
                1,
            ),
            "garbage tag blocks first-release recovery": original.replace(
                "releaseTagPattern.test(item.tag_name)",
                "item.tag_name.startsWith('save-toolkit--v')",
                1,
            ),
            "finalization accepts partial tag annotation": original.replace(
                "tagObject.data.message.trim() !== expectedAnnotation",
                "!tagObject.data.message.includes(`promotion-run-id: ${runId}`)",
                1,
            ),
        }
        for name, mutated in mutations.items():
            with self.subTest(name=name):
                self.assertNotEqual(original, mutated, "mutation matched no workflow bytes")
                self.assertTrue(release_workflow_contract.validate_workflow(mutated))


if __name__ == "__main__":
    unittest.main()
