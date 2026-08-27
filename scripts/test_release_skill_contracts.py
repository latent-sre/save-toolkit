"""Focused regressions for release and onboarding decisions that affect production safety."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def compact(text: str) -> str:
    return " ".join(text.split())


def between(text: str, start: str, end: str) -> str:
    if start not in text:
        return ""
    remainder = text.split(start, 1)[1]
    if end not in remainder:
        return ""
    return compact(remainder.split(end, 1)[0])


def source_identity_uses_commit_id(text: str, required_phrases: tuple[str, ...]) -> bool:
    text = compact(text)
    return all(phrase in text for phrase in required_phrases) and "SHA" not in text


def release_verdict_preserves_source_and_artifact(text: str) -> bool:
    verdict = between(text, "## Verdict", "## Notes")
    return all(
        (
            "Candidate commit ID: <exact source commit ID>" in verdict,
            "Artifact identity: <immutable digest or non-replaceable object/version identity>"
            in verdict,
            "Candidate commit ID/artifact" not in verdict,
        )
    )


def production_verdict_preserves_source_and_artifact(text: str) -> bool:
    verdict = between(text, "## Verdict", "## Read only the conditional material")
    return all(
        (
            "Candidate commit ID: <exact source commit ID | not applicable>" in verdict,
            "Artifact identity: <immutable digest or non-replaceable object/version identity | "
            "not applicable>" in verdict,
            "Release-readiness record: <release-gate evidence for this candidate/target | not "
            "applicable>" in verdict,
        )
    )


def production_approval_is_time_and_state_bound(text: str) -> bool:
    checklist = between(text, "## Checklist", "## Verdict")
    verdict = between(text, "## Verdict", "## Execution result")
    return all(
        (
            "Valid until: <UTC | not applicable for Tier 0/1>" in verdict,
            "Immediately before execution" in checklist,
            "approval has not expired" in checklist,
            "candidate, artifact, or configuration identity" in checklist,
            "BLOCKED and re-enters this gate" in checklist,
        )
    )


def production_execution_has_a_return_edge(text: str) -> bool:
    result = between(text, "## Execution result", "## Read only the conditional material")
    return all(
        (
            "Execution outcome: <executed | not executed | UNKNOWN>" in result,
            "Receipt/operation ID: <durable receipt or operation ID | unavailable>" in result,
            "Reconciliation: <owner + read-after-write query | not applicable>" in result,
            "Do not infer `not executed` from a missing response" in result,
            "must not be retried or re-issued" in result,
            "human executor or protected automation returns" in result,
        )
    )


def incident_envelope_is_time_and_state_bound(text: str) -> bool:
    core = between(text, "## Never skipped, even at P1", "## Deferred to post-incident reconciliation")
    return all(
        (
            "Valid until" in core,
            "current target and candidate/configuration identity" in core,
            "expired envelope" in core,
            "re-enters approval" in core,
        )
    )


def incident_effect_has_a_return_edge(text: str) -> bool:
    core = between(text, "## Never skipped, even at P1", "## Deferred to post-incident reconciliation")
    deferred = compact(text.split("## Deferred to post-incident reconciliation", 1)[1])
    return all(
        (
            "`executed`, `not executed`, or `UNKNOWN`" in core,
            "named reconciliation owner and read-after-write query" in core,
            "never retried or re-issued" in core,
            "Effect-outcome reconciliation is never deferred" in deferred,
        )
    )


def merge_p2_scope_tracks_candidate_behavior(text: str) -> bool:
    text = between(text, "### Severity rubric (what blocks)", "```text")
    return all(
        (
            "introduced or worsened by the candidate" in text,
            "materially overlaps changed behavior" in text,
            "unrelated pre-existing P2" in text,
            "block only if the change touches the same lines" not in text,
        )
    )


def merge_size_rule_preserves_atomicity(text: str) -> bool:
    text = between(text, "**Scoped & clean**", "**Docs/ops updated**")
    return all(
        (
            "size or mixed concerns materially prevent reliable review" in text,
            "smallest independently safe change" in text,
            "state what split or additional evidence clears the block" in text,
            "solely for size" not in text,
            "~400 LOC" not in text,
        )
    )


def service_onboarding_is_runtime_and_workload_aware(text: str) -> bool:
    dependencies = text.split("1. **Deploy spec & health**", 1)[0]
    step_one = between(text, "1. **Deploy spec & health**", "2. **Instrument**")
    step_three = between(text, "3. **Ship telemetry**", "4. **Dashboard**")
    step_five = between(text, "5. **Alerts**", "6. **SLO**")
    return all(
        (
            "Load `stack-profile` before step 1" in dependencies,
            "runtime-appropriate, version-controlled deployment specification" in step_one,
            "`manifest.yml` for PCF" in step_one,
            "pinned service configuration or infrastructure as code for Cloud Run" in step_one,
            "workload-appropriate health, readiness, or success check" in step_one,
            "user-serving workload" in step_one,
            "Configure minimum instances only when the approved SLO, latency, or "
            "availability plan requires them" in step_one,
            "otherwise preserve the runtime's scale-to-zero policy where supported" in step_one,
            "require at least two instances" not in step_one,
            "destinations selected by `stack-profile` and `obs-pipeline`" in step_three,
            "request-based service" in step_five,
            "scheduled or asynchronous workload" in step_five,
            "freshness, completion, or failure alert" in step_five,
            "saturation alert when the workload has a meaningful saturation signal" in step_five,
        )
    )


def pcf_canary_guidance_matches_current_contract(text: str) -> bool:
    built_in = between(text, "A canary can advance", "`--max-in-flight")
    version_gate = between(
        text,
        "## Version and target gates",
        "If either version or target behavior is unknown",
    )
    return all(
        (
            "Canary deployment requires cf CLI v8.8.0 or later and CAPI v3.173.0 "
            "or later" in version_gate,
            "`--instance-steps` additionally requires CAPI v3.189.0 or later" in version_gate,
            "For each additional canary instance created after the first" in built_in,
            "one pre-deployment instance is removed" in built_in,
            "arrived in cf CLI v8.10.0" not in version_gate,
            "arrived in v8.16.0" not in version_gate,
            "each later step removes one pre-deployment instance" not in built_in,
        )
    )


def tier_two_rollback_names_irreversible_effects(text: str) -> bool:
    marker = "**Rollback**"
    text = compact(text.split(marker, 1)[1]).replace("> ", "") if marker in text else ""
    return all(
        (
            "restores the desired instance count" in text,
            "does not reverse in-flight requests, external effects, or transient "
            "rebalancing" in text,
            "no state carried" not in text,
            "exact inverse" not in text,
            "fully reverses" not in text,
        )
    )


def incident_fast_path_keeps_tier_three_out(text: str) -> bool:
    marker = "The fast path narrows paperwork, never authority:"
    text = compact(text.split(marker, 1)[1]) if marker in text else ""
    return all(
        (
            "covered Tier 2 execution" in text,
            "Tier 3 remains on the full gate" in text,
            "Tier 2/3 execution remains" not in text,
            "Tier 3 also uses this fast path" not in text,
            "Tier 3 may use this fast path" not in text,
        )
    )


class ReleaseSkillContractTests(unittest.TestCase):
    def test_source_candidates_use_commit_id_terminology(self) -> None:
        contracts = {
            "skills/merge-gate/SKILL.md": (
                "exact commit ID",
                "record the commit ID it ran at",
                "If that commit ID != `HEAD`",
                "Candidate commit ID: <exact PR-head commit ID>",
                "Exact-commit-ID independent review",
            ),
            "skills/release-gate/SKILL.md": (
                "exact candidate commit ID",
                "Candidate commit ID: <exact source commit ID>",
            ),
            "skills/production-change-gate/SKILL.md": (
                "exact candidate commit ID",
            ),
            "skills/production-change-gate/references/incident-fast-path.md": (
                "exact candidate commit ID",
            ),
        }
        for path, phrases in contracts.items():
            with self.subTest(path=path):
                self.assertTrue(source_identity_uses_commit_id(read(path), phrases))

    def test_gate_verdicts_preserve_source_and_artifact_identities(self) -> None:
        self.assertTrue(
            release_verdict_preserves_source_and_artifact(
                read("skills/release-gate/SKILL.md")
            )
        )
        self.assertTrue(
            production_verdict_preserves_source_and_artifact(
                read("skills/production-change-gate/SKILL.md")
            )
        )

    def test_production_approvals_expire_and_recheck_resumed_state(self) -> None:
        production = read("skills/production-change-gate/SKILL.md")
        incident = read("skills/production-change-gate/references/incident-fast-path.md")
        self.assertTrue(production_approval_is_time_and_state_bound(production))
        self.assertTrue(incident_envelope_is_time_and_state_bound(incident))

    def test_human_execution_returns_an_owned_result(self) -> None:
        production = read("skills/production-change-gate/SKILL.md")
        incident = read("skills/production-change-gate/references/incident-fast-path.md")
        self.assertTrue(production_execution_has_a_return_edge(production))
        self.assertTrue(incident_effect_has_a_return_edge(incident))

    def test_merge_p2_scope_tracks_candidate_behavior(self) -> None:
        self.assertTrue(
            merge_p2_scope_tracks_candidate_behavior(read("skills/merge-gate/SKILL.md"))
        )

    def test_merge_size_rule_preserves_atomic_changes(self) -> None:
        self.assertTrue(merge_size_rule_preserves_atomicity(read("skills/merge-gate/SKILL.md")))

    def test_service_onboarding_is_runtime_and_workload_aware(self) -> None:
        self.assertTrue(
            service_onboarding_is_runtime_and_workload_aware(
                read("skills/service-lifecycle/SKILL.md")
            )
        )

    def test_pcf_canary_guidance_matches_current_contract(self) -> None:
        self.assertTrue(
            pcf_canary_guidance_matches_current_contract(
                read("skills/pcf-deploy/references/rolling-canary-and-revisions.md")
            )
        )

    def test_tier_two_rollback_does_not_claim_full_state_reversal(self) -> None:
        self.assertTrue(
            tier_two_rollback_names_irreversible_effects(
                read("skills/production-change-gate/references/tier-2-approval-example.md")
            )
        )

    def test_incident_fast_path_keeps_tier_three_on_full_gate(self) -> None:
        self.assertTrue(
            incident_fast_path_keeps_tier_three_out(
                read("skills/production-change-gate/references/incident-fast-path.md")
            )
        )

    def test_contract_oracles_reject_named_regressions(self) -> None:
        merge = read("skills/merge-gate/SKILL.md")
        release = read("skills/release-gate/SKILL.md")
        production = read("skills/production-change-gate/SKILL.md")
        onboarding = read("skills/service-lifecycle/SKILL.md")
        canary = read("skills/pcf-deploy/references/rolling-canary-and-revisions.md")
        rollback = read("skills/production-change-gate/references/tier-2-approval-example.md")
        incident = read("skills/production-change-gate/references/incident-fast-path.md")
        merge_identity = lambda candidate: source_identity_uses_commit_id(
            candidate,
            (
                "exact commit ID",
                "record the commit ID it ran at",
                "If that commit ID != `HEAD`",
                "Candidate commit ID: <exact PR-head commit ID>",
                "Exact-commit-ID independent review",
            ),
        )
        cases = (
            (
                merge_identity,
                merge.replace("commit ID", "SHA", 1),
                "source identity renamed to SHA",
            ),
            (
                merge_identity,
                merge.replace("record the commit ID it ran at", "record the revision it ran at", 1),
                "one source identity field loses commit ID",
            ),
            (
                release_verdict_preserves_source_and_artifact,
                release.replace(
                    "Artifact identity: <immutable digest or non-replaceable object/version "
                    "identity>\n",
                    "",
                    1,
                ),
                "release verdict omits artifact identity",
            ),
            (
                production_verdict_preserves_source_and_artifact,
                production.replace(
                    "Candidate commit ID: <exact source commit ID | not applicable>",
                    "Artifact identity: <exact source commit ID | not applicable>",
                    1,
                ),
                "production verdict swaps source identity label",
            ),
            (
                production_approval_is_time_and_state_bound,
                production.replace(
                    "Valid until: <UTC | not applicable for Tier 0/1>", "", 1
                ),
                "production approval loses its expiry",
            ),
            (
                production_execution_has_a_return_edge,
                production.replace(
                    "Execution outcome: <executed | not executed | UNKNOWN>",
                    "Execution outcome: <complete>",
                    1,
                ),
                "production effect result loses its unknown outcome",
            ),
            (
                merge_p2_scope_tracks_candidate_behavior,
                merge.replace("introduced or worsened by the candidate", "found during review", 1),
                "candidate causality removed",
            ),
            (
                merge_size_rule_preserves_atomicity,
                merge.replace("materially prevent reliable review", "make review longer", 1),
                "size block no longer tied to review reliability",
            ),
            (
                service_onboarding_is_runtime_and_workload_aware,
                onboarding.replace(
                    "Load `stack-profile` before step 1", "Consult the stack later", 1
                ),
                "stack loaded after runtime assumptions",
            ),
            (
                service_onboarding_is_runtime_and_workload_aware,
                onboarding.replace(
                    "Configure minimum instances only when the\n"
                    "   approved SLO, latency, or availability plan requires them; otherwise "
                    "preserve the runtime's\n   scale-to-zero policy where supported",
                    "Require at least two instances whenever the runtime supports them",
                    1,
                ),
                "optional minimum instances become mandatory",
            ),
            (
                service_onboarding_is_runtime_and_workload_aware,
                onboarding.replace("scheduled or\n   asynchronous workload", "service", 1),
                "non-request workload branch removed",
            ),
            (
                pcf_canary_guidance_matches_current_contract,
                canary.replace("CAPI v3.189.0 or later", "a recent CAPI", 1),
                "instance-step CAPI floor removed",
            ),
            (
                pcf_canary_guidance_matches_current_contract,
                canary.replace(
                    "`--instance-steps` additionally requires CAPI v3.189.0 or later",
                    "`--max-in-flight` additionally requires CAPI v3.189.0 or later",
                    1,
                ),
                "instance-step CAPI floor assigned to a different flag",
            ),
            (
                pcf_canary_guidance_matches_current_contract,
                canary.replace(
                    "For each\nadditional canary instance created after the first",
                    "For each later step",
                    1,
                ),
                "instance semantics collapsed to step semantics",
            ),
            (
                tier_two_rollback_names_irreversible_effects,
                rollback.replace(
                    "does not\n> reverse in-flight requests, external effects, or transient "
                    "rebalancing",
                    "is an exact inverse with no state carried",
                    1,
                ),
                "rollback overclaims full reversal",
            ),
            (
                tier_two_rollback_names_irreversible_effects,
                rollback + "\nThis rollback is an exact inverse of the live action.\n",
                "later rollback contradiction",
            ),
            (
                incident_fast_path_keeps_tier_three_out,
                incident.replace(
                    "Tier 3 remains on the full gate", "Tier 3 also uses this path", 1
                ),
                "tier three included in incident fast path",
            ),
            (
                incident_fast_path_keeps_tier_three_out,
                incident + "\nTier 3 also uses this fast path.\n",
                "later tier three contradiction",
            ),
            (
                incident_envelope_is_time_and_state_bound,
                incident.replace("Valid until", "Recorded at", 1),
                "incident envelope loses its expiry",
            ),
            (
                incident_effect_has_a_return_edge,
                incident.replace("or `UNKNOWN`.", "or `complete`.", 1),
                "incident effect result loses its unknown outcome",
            ),
        )
        for oracle, mutant, name in cases:
            with self.subTest(mutant=name):
                self.assertFalse(oracle(mutant))


if __name__ == "__main__":
    unittest.main()
