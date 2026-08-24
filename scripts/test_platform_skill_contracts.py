"""Focused regressions for platform-skill facts that change operator decisions."""

from __future__ import annotations

from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def compact(text: str) -> str:
    return " ".join(text.split())


def rules_match_gcp_boundary(text: str) -> bool:
    return all(
        (
            "GCP migration is approved and in progress" in text,
            "landing runtime is decision-pending" in text,
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


def alloy_google_auth_is_qualified(text: str) -> bool:
    text = compact(text)
    return all(
        (
            'otelcol.exporter.otlp "google"' in text,
            'endpoint = "telemetry.googleapis.com"' in text,
            "auth = otelcol.auth.google.gcp.handler" in text,
            'otelcol.auth.google "gcp"' in text,
            'project = "<project-id>"' in text,
            "--stability.level=public-preview" in text,
            "Application Default Credentials" in text,
            "logs ingestion is Pre-GA" in text,
            "current stable v1.18.1" not in text,
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
    def test_rules_match_the_canonical_gcp_migration_boundary(self) -> None:
        rules = read("docs/rules.md")
        self.assertTrue(rules_match_gcp_boundary(rules))

    def test_cloud_run_revision_guidance_preserves_existing_traffic_policy(self) -> None:
        skill = read("skills/gcp-ops/SKILL.md")
        self.assertTrue(cloud_run_traffic_is_conditional(skill))

    def test_datastream_retry_disagreement_is_not_flattened(self) -> None:
        reference = read("skills/akamai-edge/references/edge-triage.md")
        self.assertTrue(datastream_disagreement_is_preserved(reference))

    def test_traffic_report_preserves_the_vendor_date_disagreement(self) -> None:
        reference = read("skills/akamai-edge/references/edge-triage.md")
        self.assertTrue(traffic_report_date_disagreement_is_preserved(reference))

    def test_alloy_google_auth_is_executable_and_lifecycle_qualified(self) -> None:
        reference = read("skills/obs-pipeline/references/alloy.md")
        self.assertTrue(alloy_google_auth_is_qualified(reference))

    def test_otel_java_reference_dates_instead_of_freezing_current(self) -> None:
        reference = read("skills/obs-pipeline/references/otel-sdk.md")
        self.assertTrue(otel_java_version_is_dated(reference))

    def test_gorouter_keepalive_guidance_names_the_backend_idle_timeout(self) -> None:
        reference = read("skills/pcf-ops/references/router-errors.md")
        self.assertTrue(gorouter_keepalive_is_scoped(reference))

    def test_contract_oracles_reject_named_regressions(self) -> None:
        cases = (
            (
                rules_match_gcp_boundary,
                read("docs/rules.md").replace(
                    "GCP migration is approved and in progress",
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
                alloy_google_auth_is_qualified,
                read("skills/obs-pipeline/references/alloy.md").replace(
                    "auth     = otelcol.auth.google.gcp.handler",
                    "# auth handler omitted",
                    1,
                ),
                "missing Alloy auth handler",
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
