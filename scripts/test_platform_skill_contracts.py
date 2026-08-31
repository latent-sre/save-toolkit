"""Focused regressions for platform-skill facts that change operator decisions."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def compact(text: str) -> str:
    return " ".join(text.split())


def stack_profile_preserves_gcp_boundary(text: str) -> bool:
    return all(
        (
            "GCP migration is in progress" in text,
            "GCP is an approved target" in text,
            "landing runtime is **decision-pending**" in text,
            "No self-managed Kubernetes" in text,
            "GCP under evaluation for late 2026 is not a target today" not in text,
            "do not suggest Kubernetes, cloud-managed services" not in text,
        )
    )


def cloud_run_traffic_is_conditional(text: str) -> bool:
    text = compact(text)
    return all(
        (
            "existing traffic split" in text,
            "previous-revision assignment persists" in text,
            "--no-traffic" in text,
            "until traffic is explicitly assigned" in text,
            "--to-revisions <revision>=<percentage>" in text,
            "--to-latest" in text,
            "100% to the latest revision" in text,
            "by default traffic routes to the latest healthy revision" not in text,
        )
    )


def cloud_run_rollback_restores_policy_without_inverse_claim(text: str) -> bool:
    start = text.index("## Mitigation you recommend (never run): traffic rollback")
    section = compact(text[start : text.index("## Credential-bearing reads", start)])
    return all(
        (
            "restores the intended prior traffic allocation or `--to-latest` tracking policy"
            in section,
            "Traffic changes are not instantaneous" in section,
            "in-flight requests may land on either revision" in section,
            "equally exact inverse command" not in section,
        )
    )


def frontend_mantine_guidance_is_react_scoped(text: str) -> bool:
    start = text.index("## Decisions this fleet has made")
    section = compact(text[start : text.index("## Testing & quality gate", start)])
    return all(
        (
            "**React targets only:**" in section,
            "`@mantine/hooks` and `@mantine/form` are React packages" in section,
            "Do not recommend Mantine packages for Vue or another non-React target" in section,
            "Mantine's *hooks* and `@mantine/form` ship no CSS and mix freely" not in section,
        )
    )


def datastream_disagreement_is_preserved(text: str) -> bool:
    start = text.index("**Delivery drops are real**")
    section = compact(text[start : text.index("## Offload", start)])
    return all(
        (
            "documentation disagrees" in section,
            "up to 10 attempts within 5 minutes" in section,
            "lost after 3 unsuccessful retries" in section,
            "exact retry budget is therefore `[unverified]`" in section,
            "there is no backup copy" in section,
        )
    )


def traffic_report_date_disagreement_is_preserved(text: str) -> bool:
    text = compact(text)
    return all(
        (
            "planning changelog says" in text,
            "effective **2025-11-05**" in text,
            "current Traffic report page records **2025-11-06**" in text,
            "exact effective day is `[unverified]`" in text,
        )
    )


def alloy_google_otlp_pipeline_is_executable_and_qualified(text: str) -> bool:
    text = compact(text)
    return all(
        (
            "traces = [otelcol.processor.batch.default.input]" in text,
            "metrics = [otelcol.processor.batch.default.input]" in text,
            "logs = [otelcol.processor.batch.default.input]" in text,
            "traces = [otelcol.exporter.otlp.default.input]" in text,
            "metrics = [otelcol.exporter.otlp.default.input]" in text,
            "logs = [otelcol.exporter.otlp.default.input]" in text,
            'replace the generic `otelcol.exporter.otlp "default"` block above' in text,
            'endpoint = "telemetry.googleapis.com:443"' in text,
            "auth = otelcol.auth.google.gcp.handler" in text,
            'otelcol.auth.google "gcp"' in text,
            'project = "<project-id>"' in text,
            "--stability.level=public-preview" in text,
            "Application Default Credentials" in text,
            "logs ingestion is Pre-GA" in text,
            "current stable v1.18.1" not in text,
        )
    )


def gcp_trace_endpoint_matches_alloy_transport(trace: str, alloy: str) -> bool:
    trace = compact(trace)
    alloy = compact(alloy)
    return all(
        (
            "for Alloy's gRPC `otelcol.exporter.otlp`, use `telemetry.googleapis.com:443`"
            in trace,
            "an OTLP/HTTP exporter instead uses the root URL `https://telemetry.googleapis.com`"
            in trace,
            "Alloy component and authentication shapes stay delegated to the `obs-pipeline` skill"
            in trace,
            'endpoint = "telemetry.googleapis.com:443"' in alloy,
            "endpoint: https://telemetry.googleapis.com" not in trace,
        )
    )


def alloy_docker_validation_is_bounded(text: str) -> bool:
    start = text.index("## Debugging a running Alloy")
    section = compact(text[start : text.index("## Backpressure", start)])
    return all(
        (
            "Docker is the local fallback when the Alloy binary is unavailable" in section,
            "docker run --rm --network none -i grafana/alloy:<pinned-version>" in section,
            "validate --stability.level=public-preview /dev/stdin" in section,
            "Record the image reference, `alloy --version`, command, exit status, and diagnostics"
            in section,
            "static validation" in section,
            "does not prove DNS, TCP, TLS, authentication, or telemetry delivery" in section,
            "Docker socket" in section,
        )
    )


def docker_verification_policy_is_bounded(text: str) -> bool:
    text = compact(text)
    return all(
        (
            "Docker-backed local verification is allowed and recommended" in text,
            "already has Bash or execute authority" in text,
            "official image exercises the real tool or runtime" in text,
            "Pin an exact image version" in text,
            "`--rm`" in text,
            "`--network none` by default" in text,
            "read-only bind mount or stdin" in text,
            "never mount the Docker socket or forward credentials" in text,
            "does not grant production-change authority" in text,
            "static validation does not prove runtime connectivity" in text,
        )
    )


def postmortem_causal_method_is_consistent(scribe: str, skill: str, template: str) -> bool:
    return all(
        (
            "Causal analysis selected to fit the evidence" in scribe,
            "five whys" not in scribe.lower(),
            "Five Whys is one option, not a required" in skill,
            "Method: <Five Whys, fault tree, causal graph, or another method suited to the evidence>"
            in template,
        )
    )


def otel_java_version_is_dated(text: str) -> bool:
    return (
        "current release" not in text
        and "reviewed against 2.31.1 on 2026-08-24" in text
    )


def gorouter_keepalive_is_scoped(text: str) -> bool:
    text = compact(text)
    return all(
        (
            "backend-connection idle timeout" in text,
            "frontend idle timeout is separate" in text,
            "app server's keep-alive idle timeout **> 90s**" in text,
            "Gorouter side is a hardcoded 90s" not in text,
        )
    )


class PlatformSkillContractTests(unittest.TestCase):
    def test_stack_profile_preserves_the_gcp_migration_boundary(self) -> None:
        profile = read("skills/stack-profile/SKILL.md")
        self.assertTrue(stack_profile_preserves_gcp_boundary(profile))

    def test_cloud_run_revision_guidance_preserves_existing_traffic_policy(self) -> None:
        skill = read("skills/gcp-ops/SKILL.md")
        self.assertTrue(cloud_run_traffic_is_conditional(skill))

    def test_cloud_run_rollback_restores_policy_without_claiming_an_exact_inverse(self) -> None:
        self.assertTrue(
            cloud_run_rollback_restores_policy_without_inverse_claim(
                read("skills/gcp-ops/SKILL.md")
            )
        )

    def test_frontend_mantine_guidance_is_scoped_to_react_targets(self) -> None:
        self.assertTrue(
            frontend_mantine_guidance_is_react_scoped(
                read("skills/frontend-craft/SKILL.md")
            )
        )

    def test_datastream_retry_disagreement_is_not_flattened(self) -> None:
        reference = read("skills/akamai-edge/references/edge-triage.md")
        self.assertTrue(datastream_disagreement_is_preserved(reference))

    def test_traffic_report_preserves_the_vendor_date_disagreement(self) -> None:
        reference = read("skills/akamai-edge/references/edge-triage.md")
        self.assertTrue(traffic_report_date_disagreement_is_preserved(reference))

    def test_alloy_google_otlp_pipeline_is_executable_and_lifecycle_qualified(self) -> None:
        reference = read("skills/obs-pipeline/references/alloy.md")
        self.assertTrue(alloy_google_otlp_pipeline_is_executable_and_qualified(reference))

    def test_gcp_trace_reference_uses_the_alloy_grpc_endpoint_shape(self) -> None:
        trace = read("skills/obs-traces/references/gcp-trace.md")
        alloy = read("skills/obs-pipeline/references/alloy.md")
        self.assertTrue(
            gcp_trace_endpoint_matches_alloy_transport(trace, alloy)
        )
        alloy_grpc_url_mutant = trace.replace(
            "telemetry.googleapis.com:443",
            "https://telemetry.googleapis.com",
            1,
        )
        self.assertFalse(
            gcp_trace_endpoint_matches_alloy_transport(alloy_grpc_url_mutant, alloy)
        )

    def test_alloy_docker_validation_recipe_is_isolated_and_evidence_bounded(self) -> None:
        reference = read("skills/obs-pipeline/references/alloy.md")
        self.assertTrue(alloy_docker_validation_is_bounded(reference))

    def test_general_docker_verification_policy_preserves_authority_and_evidence_boundaries(self) -> None:
        self.assertTrue(docker_verification_policy_is_bounded(read("docs/docker-verification.md")))

    def test_scribe_and_postmortem_skill_agree_on_evidence_selected_causal_analysis(self) -> None:
        scribe = read("agents/scribe.md")
        skill = read("skills/postmortem/SKILL.md")
        template = read("skills/postmortem/assets/postmortem-template.md")
        self.assertTrue(
            postmortem_causal_method_is_consistent(scribe, skill, template)
        )
        five_whys_only_mutant = scribe.replace(
            "Causal analysis selected to fit the evidence",
            "Five whys",
            1,
        )
        self.assertFalse(
            postmortem_causal_method_is_consistent(five_whys_only_mutant, skill, template)
        )
        mandatory_five_whys_mutant = scribe.replace(
            "Causal analysis selected to fit the evidence",
            "Causal analysis selected to fit the evidence, including mandatory Five Whys",
            1,
        )
        self.assertFalse(
            postmortem_causal_method_is_consistent(
                mandatory_five_whys_mutant,
                skill,
                template,
            )
        )

    def test_otel_java_reference_dates_instead_of_freezing_current(self) -> None:
        reference = read("skills/obs-pipeline/references/otel-sdk.md")
        self.assertTrue(otel_java_version_is_dated(reference))

    def test_gorouter_keepalive_guidance_names_the_backend_idle_timeout(self) -> None:
        reference = read("skills/pcf-ops/references/router-errors.md")
        self.assertTrue(gorouter_keepalive_is_scoped(reference))

    def test_contract_oracles_reject_named_regressions(self) -> None:
        cases = (
            (
                stack_profile_preserves_gcp_boundary,
                read("skills/stack-profile/SKILL.md").replace(
                    "GCP migration is in progress",
                    "GCP under evaluation for late 2026 is not a target today",
                    1,
                ),
                "stale GCP boundary",
            ),
            (
                cloud_run_traffic_is_conditional,
                read("skills/gcp-ops/SKILL.md").replace("existing traffic split", "traffic plan", 1),
                "missing persistent split",
            ),
            (
                cloud_run_traffic_is_conditional,
                read("skills/gcp-ops/SKILL.md").replace("`--no-traffic`", "an unrouted deploy", 1),
                "missing no-traffic exception",
            ),
            (
                cloud_run_traffic_is_conditional,
                read("skills/gcp-ops/SKILL.md").replace(
                    "--to-revisions <revision>=<percentage>",
                    "a rollout command",
                    1,
                ),
                "missing staged traffic branch",
            ),
            (
                cloud_run_rollback_restores_policy_without_inverse_claim,
                read("skills/gcp-ops/SKILL.md").replace(
                    "restores the intended prior traffic allocation or `--to-latest`\ntracking policy",
                    "is an equally exact inverse command",
                    1,
                ),
                "Cloud Run rollback overclaims exact reversal",
            ),
            (
                frontend_mantine_guidance_is_react_scoped,
                read("skills/frontend-craft/SKILL.md").replace(
                    "**React targets only:**",
                    "**Any frontend:**",
                    1,
                ),
                "React-only Mantine guidance leaks into Vue",
            ),
            (
                datastream_disagreement_is_preserved,
                read("skills/akamai-edge/references/edge-triage.md").replace(
                    "documentation disagrees",
                    "documentation agrees",
                    1,
                ),
                "flattened retry disagreement",
            ),
            (
                datastream_disagreement_is_preserved,
                read("skills/akamai-edge/references/edge-triage.md")
                .replace("up to 10 attempts within 5 minutes", "multiple retries", 1)
                .replace("lost after 3\n  unsuccessful retries", "lost after several retries", 1),
                "missing conflicting retry counts",
            ),
            (
                traffic_report_date_disagreement_is_preserved,
                read("skills/akamai-edge/references/edge-triage.md").replace(
                    "current Traffic\nreport page records **2025-11-06**",
                    "current Traffic report page agrees",
                    1,
                ),
                "flattened report-date disagreement",
            ),
            (
                alloy_google_otlp_pipeline_is_executable_and_qualified,
                read("skills/obs-pipeline/references/alloy.md").replace(
                    "auth     = otelcol.auth.google.gcp.handler",
                    "# auth handler omitted",
                    1,
                ),
                "missing Alloy auth handler",
            ),
            (
                alloy_google_otlp_pipeline_is_executable_and_qualified,
                read("skills/obs-pipeline/references/alloy.md").replace(
                    'endpoint = "telemetry.googleapis.com:443"',
                    'endpoint = "telemetry.googleapis.com"',
                    1,
                ),
                "missing Alloy Google OTLP port",
            ),
            (
                alloy_google_otlp_pipeline_is_executable_and_qualified,
                read("skills/obs-pipeline/references/alloy.md").replace(
                    "metrics = [otelcol.exporter.otlp.default.input]",
                    "# metrics exporter output omitted",
                    1,
                ),
                "disconnected Alloy metrics output",
            ),
            (
                alloy_docker_validation_is_bounded,
                read("skills/obs-pipeline/references/alloy.md").replace(
                    "--network none",
                    "--network bridge",
                    1,
                ),
                "network-enabled Alloy validation container",
            ),
            (
                alloy_docker_validation_is_bounded,
                read("skills/obs-pipeline/references/alloy.md").replace(
                    "does not prove\n  DNS, TCP, TLS, authentication, or telemetry delivery",
                    "proves the exporter works end to end",
                    1,
                ),
                "overstated Alloy static-validation evidence",
            ),
            (
                docker_verification_policy_is_bounded,
                read("docs/docker-verification.md").replace(
                    "`--network none` by default", "the default network", 1
                ),
                "network-enabled general Docker verification",
            ),
            (
                docker_verification_policy_is_bounded,
                read("docs/docker-verification.md").replace(
                    "already has Bash\nor execute authority",
                    "can request execution after selecting Docker",
                    1,
                ),
                "Docker prose widens lane authority",
            ),
            (
                otel_java_version_is_dated,
                read("skills/obs-pipeline/references/otel-sdk.md").replace(
                    "reviewed against 2.31.1 on 2026-08-24",
                    "current release is 2.31.x",
                    1,
                ),
                "moving Java version",
            ),
            (
                gorouter_keepalive_is_scoped,
                read("skills/pcf-ops/references/router-errors.md").replace(
                    "backend-connection idle timeout",
                    "keepalive",
                    1,
                ),
                "unscoped Gorouter timeout",
            ),
        )
        for oracle, mutant, name in cases:
            with self.subTest(mutant=name):
                self.assertFalse(oracle(mutant))


if __name__ == "__main__":
    unittest.main()
