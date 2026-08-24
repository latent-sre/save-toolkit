"""Focused offline regressions for observability skill execution and routing contracts."""

from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def frontmatter_description(skill_path: str) -> str:
    text = read(skill_path)
    frontmatter = text.split("---", 2)[1]
    match = re.search(r"(?ms)^description:\s*>-\s*\n(?P<body>.*?)(?=^argument-hint:)", frontmatter)
    if not match:
        raise AssertionError(f"description block not found in {skill_path}")
    return " ".join(line.strip() for line in match.group("body").splitlines())


def bash_fences(markdown: str) -> tuple[str, ...]:
    return tuple(re.findall(r"(?ms)^```bash\s*\n(.*?)^```\s*$", markdown))


def ungated_grafana_writes(reference: str) -> tuple[str, ...]:
    """Return request-body files whose preceding builder is not success-gated."""
    failures: list[str] = []
    lines = "\n".join(bash_fences(reference)).splitlines()
    for index, line in enumerate(lines):
        match = re.search(r"-X (?:POST|PUT)\b.*--data @(?P<body>[-\w.]+)", line)
        if not match:
            continue
        previous = next(
            (
                candidate.strip()
                for candidate in reversed(lines[:index])
                if candidate.strip() and not candidate.lstrip().startswith("#")
            ),
            "",
        )
        if not previous.endswith("&&"):
            failures.append(match.group("body"))
    return tuple(failures)


class ObservabilitySkillContractTests(unittest.TestCase):
    def test_log_query_skill_does_not_claim_alert_design_as_a_trigger(self) -> None:
        description = frontmatter_description("skills/obs-logs/SKILL.md").lower()
        self.assertNotIn("build a log alert", description)
        self.assertIn("write a log query", description)
        self.assertIn("obs-alerting owns alert design", description)

    def test_forced_alert_uses_a_nonproduction_rule_and_test_contact(self) -> None:
        skill = read("skills/obs-alerting/SKILL.md").lower()
        start = skill.index("force the alert's condition")
        verification_step = skill[start : skill.index("- the notification route", start)]
        self.assertIn("controlled non-production rule", verification_step)
        self.assertIn("test contact point", verification_step)
        self.assertIn("never force a production receiver", verification_step)

    def test_grafana_curl_examples_propagate_http_and_pipeline_failures(self) -> None:
        reference = read("skills/obs-dashboards/references/http-api.md")
        self.assertIn(
            "CURL=(curl --fail-with-body --show-error --silent)",
            reference,
        )
        self.assertIn("set -o pipefail", reference)
        self.assertNotIn("curl -sS", reference)

        raw_curl_lines = [
            line.strip()
            for fence in bash_fences(reference)
            for line in fence.splitlines()
            if line.strip()
            and not line.lstrip().startswith("#")
            and re.search(r"(^|[|&;(]\s*)curl\s", line)
            and not line.strip().startswith("CURL=(curl ")
        ]
        self.assertEqual([], raw_curl_lines)

    def test_grafana_body_builders_gate_every_write(self) -> None:
        reference = read("skills/obs-dashboards/references/http-api.md")
        self.assertEqual((), ungated_grafana_writes(reference))

        gates = {
            "create.json": "create.json &&",
            "create-legacy.json": "create-legacy.json &&",
            "import.json": "jq empty import.json &&",
            "update.json": "update.json &&",
            "update-legacy.json": "update-legacy.json &&",
            "rollback.json": "rollback.json','w'))\" &&",
        }
        for body, gate in gates.items():
            with self.subTest(fall_through_mutant=body):
                mutant = reference.replace(gate, gate.removesuffix(" &&"), 1)
                self.assertNotEqual(reference, mutant, f"missing fixture for {body}")
                self.assertIn(body, ungated_grafana_writes(mutant))

    def test_grafana_rollback_read_and_builder_gate_the_write(self) -> None:
        reference = read("skills/obs-dashboards/references/http-api.md")
        self.assertIn(
            'dashboards/<uid>" > now.json &&\n'
            "# 2. put the SAVED spec into the CURRENT envelope, and drop status (see json-model.md)\n"
            'python -c "import json,sys;',
            reference,
        )
        self.assertIn(
            "json.dump(live,open('rollback.json','w'))\" &&\n"
            "# 3. apply it like any other update\n"
            '"${CURL[@]}" "${H[@]}" -X PUT --data @rollback.json',
            reference,
        )

    def test_promql_reference_uses_the_actual_duration_feature_boundaries(self) -> None:
        reference = read("skills/obs-metrics/references/promql.md")
        self.assertNotIn("duration expressions inside range selectors\n  (v3.13+)", reference)
        self.assertIn("v3.4", reference)
        self.assertIn("v3.14", reference)
        self.assertIn("v3.7", reference)


if __name__ == "__main__":
    unittest.main()
