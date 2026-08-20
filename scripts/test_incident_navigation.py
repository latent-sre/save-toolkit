"""Mutation-oriented contracts for the uncertain-responder navigation skill."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = Path("skills/incident-navigation/SKILL.md")
SRE_PATH = Path("agents/sre.md")
AGENTS_GUIDE_PATH = Path("AGENTS.md")
README_PATH = Path("README.md")

OUTPUT_SLOTS = (
    "Incident orientation:",
    "Known facts:",
    "Unknowns:",
    "Where to look:",
    "Question:",
    "Signal owner:",
    "First safe check:",
    "If result A:",
    "If result B:",
    "Escalate when:",
    "Documentation gaps:",
    "State changed: no",
)

EXIT_SLOTS = (
    "Exit destination:",
    "Reason category:",
    "Orientation skipped: yes",
    "Preserve state:",
    "State changed: no",
)

SIGNAL_ROUTES = (
    "`pcf-ops`",
    "`gcp-ops`",
    "`akamai-edge`",
    "`obs-alerting`",
    "`obs-metrics`",
    "`obs-logs`",
    "`obs-traces`",
    "`obs-dashboards`",
    "`obs-pipeline`",
    "`database-reliability`",
)

LIVE_OUTPUT_GUARDS = {
    "clarification-first behavior is not forbidden": (
        "do not ask for more information before returning the packet"
    ),
    "missing-evidence search or delegation is not forbidden": (
        "do not search for missing evidence or delegate to retrieve it"
    ),
    "unknown values are not bound to evidence placeholders": (
        "write the required `[unverified]` or `[unverified — not located]` value"
    ),
    "the response is not bound to packet-only output": "the entire response is the packet",
    "code fences are not forbidden in live output": "do not include a code fence",
    "the packet has no exact terminal line": (
        "end the response immediately after `state changed: no`"
    ),
    "the unknown location value is not exact": (
        "the entire `where to look` value is exactly `[unverified — not located]`"
    ),
    "the selected owner may leak into other fields": (
        "the selected canonical owner name appears only in `signal owner`"
    ),
    "the output recipe does not tell the model to copy the labels": (
        "copy the twelve labels below, replace each placeholder"
    ),
    "a supplied uncertainty may be rewritten or expanded": (
        "when the requester supplies one uncertainty, copy its wording verbatim into `question`"
    ),
    "multiple documentation gaps may be combined in one field": (
        "record only the first one in the lookup order above"
    ),
    "URI punctuation is confused with a second source": (
        "uri or path punctuation inside that one source is allowed"
    ),
    "result branches are not closed result classifications": (
        "classify each result as exactly `supports the question`, `does not support the question`, or `result is inconclusive`"
    ),
    "result owner choices are not explicit host-rewritable identities": (
        "choosing `sre`, `service owner`, `incident commander`, or `human owner`"
    ),
    "the packet may grow a thirteenth prose line": (
        "a valid packet has no thirteenth non-empty line"
    ),
    "packet output is not filtered to the twelve labels": (
        "remove every line that does not begin with one of the twelve labels"
    ),
    "an unknown location may still invent a backend": (
        "when the evidence location is unknown, begin the first safe check with `retrieve`"
    ),
    "the terminal byte of the packet is not explicit": (
        "the final character of the response is the `o` in `no`"
    ),
    "unknown impact may be relabeled as unbounded": (
        "unknown impact is not evidence that scope is unbounded"
    ),
    "the first check may diverge from the known location": (
        "the first safe check names the same location as `where to look`"
    ),
    "the escalation field may suppress or misroute escalation": (
        "`never`, `none`, a stable/healthy condition, or an unlisted destination is not an escalation threshold"
    ),
    "an index may displace a supplied answer source": (
        "a supplied evidence source that directly answers the question wins over an index"
    ),
}

DISCOVERY_FIXTURE_BOUNDARY = (
    "Use only the supplied evidence; do not search the repository or delegate evidence retrieval."
)

SCENARIO_EVIDENCE_CONTRACTS = {
    "discovery-incident-navigation-defers-active-known-alert.yaml": (
        "Impact: 72% of checkout requests fail across three regions; trend: growing",
        "with no second use of `72%`",
        "three regions",
        "Fast burn windows:",
        "Slow burn windows:",
        "Runbook:",
    ),
    "discovery-incident-navigation-defers-alert-interpretation.yaml": (
        "Measured failed-request fraction: 0.0004",
        "SLO-permitted failed-request fraction: 0.001",
        "Ratio definition: measured fraction divided by permitted fraction",
        "Owner:",
        "Notification route:",
        "Runbook:",
        "Render the window rule as `1h AND 5m at 14.4x; 6h AND 30m at 6x`",
        "do not call the notification fully verified actionable",
        "window-specific measurements, fire/resolve behavior, notification delivery, and runbook resolution",
        "Return exactly the following thirteen non-empty plaintext field lines",
        "Current verdict: not currently firing; paired-window measurements [unverified]",
        "Threshold boundary: no threshold change is supported by the supplied evidence",
    ),
    "discovery-incident-navigation-defers-approved-change.yaml": (
        "Approved by: release owner",
        "When: 2026-08-20T18:00:00Z",
        "Watching: checkout on-call, six healthy instances and checkout errors for five minutes",
        "Abort if: errors rise for five minutes",
        "Branch protection evidence: enforce_admins=true; required_reviews=2; dismiss_stale=true [verified]",
        "Timing: maintenance window; no freeze in effect [verified]",
        "Comms: checkout stakeholders and checkout on-call notified [verified]",
        "Return only the ten-line production-change-gate verdict packet",
    ),
    "discovery-incident-navigation-defers-incident-command.yaml": (
        "First detected and declaration/cadence anchor: 18:04 UTC",
        "Incident commander: Morgan Lee",
        "Communications lead: Avery Chen",
        "Runbook: ops://checkout/major-incident",
        "Declare `Checkout unavailable` as the incident",
        "Use the canonical status-block labels",
    ),
    "discovery-incident-navigation-defers-known-triage.yaml": (
        "Blast radius: 40% of checkout requests across two regions; trend: growing",
        "with no second use of `40%`",
        "two regions",
        "still growing",
        "checkout-214",
    ),
    "discovery-incident-navigation-defers-security-response.yaml": (
        "checkout integrity scope unknown since 18:04 UTC; unbounded",
        "18:04 credential alert; 18:06 security owner paged",
        "human security incident owner",
    ),
    "discovery-incident-navigation-signal-owner-uncertain.yaml": (
        "Service card: ops://services/checkout",
        "Dashboard: grafana://checkout-latency",
        "Runbook: ops://checkout/latency",
        "Return only the twelve-line orientation packet",
        "Impact is unknown; no evidence says it is unbounded",
        "the supplied dashboard directly answers it",
    ),
    "discovery-uncertain-responder-navigation.yaml": (
        "Evidence item available for human retrieval: checkout p95 latency comparison",
        "Return only the twelve-line orientation packet",
        "Impact is unknown; no evidence says it is unbounded",
        "Question: Is checkout latency elevated relative to its recent baseline?",
        "Documentation gaps: missing service card · proposed owner: service owner",
    ),
    "discovery-resolved-incident-bypasses-navigation.yaml": (
        "Impact:",
        "Timeline:",
        "Root cause:",
        "Action item:",
        "Verification gap:",
        "with no second use of `42%`",
    ),
}

DESTINATION_SKILL_CONTRACTS = {
    Path("skills/production-change-gate/SKILL.md"): (
        "the entire response is the verdict packet",
        "return exactly these ten non-empty field lines as plaintext",
        "Blast radius: <affected scope and worst credible failure>",
        "Verification: <observable success evidence and duration>",
        "Timing/freeze: <window, freeze state, or [unverified]>",
        "Comms: <stakeholders/on-call notification evidence or [unverified]>",
        "do not include a code fence",
        "copy supplied evidence values without upgrading their labels",
        "include both the watcher and the supplied signals",
    ),
    Path("skills/obs-alerting/SKILL.md"): (
        "interpret a known alert definition",
        "return exactly these thirteen non-empty plaintext field lines",
        "Observed bad fraction:",
        "Allowed bad fraction:",
        "Burn rate:",
        "Window rule:",
        "Notification route:",
        "Current verdict:",
        "Notification actionability:",
        "Silence boundary:",
        "Threshold boundary:",
        "Verification gaps:",
    ),
    Path("skills/incident-command/SKILL.md"): (
        "keep `incident`, `severity`, and `status` on the same first line",
        "write `roles` in exactly this order: `investigation=`, `ops=`, `comms=`",
    ),
}

SCENARIO_CONTRACTS = {
    "agent-direct-sre-uncertain-responder-navigation.yaml": (
        "mode: direct",
        "kind: agent",
        "name: sre",
        "type: incident_navigation_contract",
    ),
    "direct-incident-navigation-uncertain-responder.yaml": (
        "mode: direct",
        "kind: skill",
        "name: incident-navigation",
        'State changed: "no"',
    ),
    "direct-incident-navigation-security-escalation.yaml": (
        "mode: direct",
        "name: incident-navigation",
        "security incident owner",
    ),
    "direct-incident-navigation-major-incident-exit.yaml": (
        "mode: direct",
        "name: incident-navigation",
        "incident-command",
    ),
    "direct-incident-navigation-approved-change-exit.yaml": (
        "mode: direct",
        "name: incident-navigation",
        "production-change-gate",
    ),
    "discovery-uncertain-responder-navigation.yaml": (
        "mode: discovery",
        "name: incident-navigation",
        "expect: fire",
        'Question: "Is checkout latency elevated relative to its recent baseline?"',
        'Signal owner: "obs-metrics"',
        'First safe check: "Retrieve checkout p95 latency comparison."',
        'Documentation gaps: "missing service card · proposed owner: service owner"',
    ),
    "discovery-incident-navigation-signal-owner-uncertain.yaml": (
        "mode: discovery",
        "name: incident-navigation",
        "expect: fire",
        'Question: "Is checkout latency elevated relative to its recent baseline?"',
        'Signal owner: "obs-dashboards"',
    ),
    "discovery-incident-navigation-defers-known-triage.yaml": (
        "expect: not_fire",
        "kind: agent",
        "name: sre",
        "type: incident_navigation_no_claimed_execution",
        "type: incident_navigation_exact_fact",
    ),
    "discovery-incident-navigation-defers-incident-command.yaml": (
        "expect: not_fire",
        "kind: skill",
        "name: incident-command",
        "type: incident_navigation_incident_command_contract",
        "required_investigation: checkout on-call",
        "required_ic: Morgan Lee",
    ),
    "discovery-incident-navigation-defers-alert-interpretation.yaml": (
        "expect: not_fire",
        "kind: skill",
        "name: obs-alerting",
        "type: incident_navigation_known_alert_contract",
        'required_observed_fraction: "0.0004"',
        "required_notification_route: PagerDuty checkout-primary",
        "required_current_verdict:",
        "required_verification_gaps:",
    ),
    "discovery-incident-navigation-defers-active-known-alert.yaml": (
        "expect: not_fire",
        "kind: agent",
        "name: sre",
        "type: incident_navigation_no_claimed_execution",
        "type: incident_navigation_exact_fact",
    ),
    "discovery-incident-navigation-defers-production-change.yaml": (
        "expect: not_fire",
        "kind: skill",
        "name: production-change-gate",
    ),
    "discovery-incident-navigation-defers-approved-change.yaml": (
        "expect: not_fire",
        "kind: skill",
        "name: production-change-gate",
    ),
    "discovery-incident-navigation-defers-security-response.yaml": (
        "expect: not_fire",
        "kind: skill",
        "name: incident-command",
    ),
    "discovery-resolved-incident-bypasses-navigation.yaml": (
        "expect: not_fire",
        "kind: agent",
        "name: scribe",
        "type: incident_navigation_exact_fact",
        'required_preceding_line: "## Impact"',
    ),
}


def _frontmatter(text: str) -> str:
    parts = text.split("---", 2)
    return parts[1] if len(parts) == 3 else ""


def contract_failures(
    skill_text: str,
    sre_text: str,
    agents_guide_text: str,
    readme_text: str,
) -> list[str]:
    """Return missing navigation contracts without interpreting Markdown."""

    failures: list[str] = []
    lowered_skill = skill_text.lower()
    normalized_skill = " ".join(lowered_skill.split())
    lowered_sre = sre_text.lower()
    description = _frontmatter(skill_text).lower()

    for slot in OUTPUT_SLOTS:
        if slot not in skill_text:
            failures.append(f"missing output slot: {slot}")
    for slot in EXIT_SLOTS:
        if slot not in skill_text:
            failures.append(f"missing hard-exit slot: {slot}")
    for route in SIGNAL_ROUTES:
        if route not in skill_text:
            failures.append(f"missing signal route: {route}")
    for failure, required_text in LIVE_OUTPUT_GUARDS.items():
        if required_text not in normalized_skill:
            failures.append(failure)

    if "load the `incident-navigation` skill only when" not in lowered_sre:
        failures.append("SRE route is not limited to explicit responder uncertainty")
    if "tier 0" not in lowered_skill:
        failures.append("Tier 0 boundary is absent")
    if "grants no tool or execution authority" not in lowered_skill:
        failures.append("no-authority boundary is absent")
    if "one first safe check" not in lowered_skill:
        failures.append("single-check boundary is absent")
    if "exactly one signal owner" not in normalized_skill:
        failures.append("single-signal-owner boundary is absent")
    if "do not assign severity" not in lowered_skill:
        failures.append("orientation incorrectly owns severity or RCA")
    if "return exactly these twelve non-empty field lines" not in normalized_skill:
        failures.append("orientation packet is not closed to extra fields or prose")
    output_section = skill_text.split("## Output contract", 1)[-1]
    if "```" in output_section:
        failures.append("output template still teaches code fencing")
    if "missing documentation is a finding" not in lowered_skill:
        failures.append("missing-documentation behavior is absent")
    if "security incident owner" not in lowered_skill:
        failures.append("security escalation boundary is absent")
    if "bounded envelope" in lowered_skill:
        failures.append("navigation is coupled to the unaccepted bounded-envelope policy")
    if "help me triage this" in description:
        failures.append("description overlaps ordinary SRE triage")
    if "30 canonical skills" not in agents_guide_text:
        failures.append("AGENTS.md canonical skill count is stale")
    if "30 skills" not in readme_text:
        failures.append("README skill count is stale")
    return failures


def _prompt_block(text: str) -> str:
    """Return the literal ``prompt: |`` body without parsing the rest of the YAML."""

    lines = text.splitlines()
    try:
        start = lines.index("prompt: |") + 1
    except ValueError:
        return ""
    prompt_lines: list[str] = []
    for line in lines[start:]:
        if line and not line.startswith("  "):
            break
        prompt_lines.append(line[2:] if line.startswith("  ") else "")
    return "\n".join(prompt_lines)


def scenario_text_failures(filename: str, text: str) -> list[str]:
    failures: list[str] = []
    prompt = _prompt_block(text)
    normalized_prompt = " ".join(prompt.split())
    if (
        filename.startswith("discovery-")
        and DISCOVERY_FIXTURE_BOUNDARY not in normalized_prompt
    ):
        failures.append(f"{filename}: neutral-fixture boundary is absent")
    for fragment in SCENARIO_EVIDENCE_CONTRACTS.get(filename, ()):
        if fragment not in normalized_prompt:
            failures.append(f"{filename}: missing supplied evidence: {fragment}")
    return failures


def scenario_failures() -> list[str]:
    failures: list[str] = []
    scenario_root = ROOT / "evals" / "scenarios"
    for filename, fragments in SCENARIO_CONTRACTS.items():
        path = scenario_root / filename
        if not path.is_file():
            failures.append(f"missing scenario: {filename}")
            continue
        text = path.read_text(encoding="utf-8")
        for fragment in fragments:
            if fragment not in text:
                failures.append(f"{filename}: missing {fragment}")
        failures.extend(scenario_text_failures(filename, text))
    return failures


def destination_skill_failures() -> list[str]:
    failures: list[str] = []
    for relative_path, fragments in DESTINATION_SKILL_CONTRACTS.items():
        path = ROOT / relative_path
        if not path.is_file():
            failures.append(f"missing destination skill: {relative_path}")
            continue
        text = path.read_text(encoding="utf-8")
        normalized = " ".join(text.split())
        for fragment in fragments:
            if fragment not in text and fragment.casefold() not in normalized.casefold():
                failures.append(f"{relative_path}: missing destination contract: {fragment}")
    return failures


class IncidentNavigationContractTests(unittest.TestCase):
    def _current_failures(self) -> list[str]:
        skill = ROOT / SKILL_PATH
        if not skill.is_file():
            return [f"missing canonical skill: {SKILL_PATH}"]
        return contract_failures(
            skill.read_text(encoding="utf-8"),
            (ROOT / SRE_PATH).read_text(encoding="utf-8"),
            (ROOT / AGENTS_GUIDE_PATH).read_text(encoding="utf-8"),
            (ROOT / README_PATH).read_text(encoding="utf-8"),
        ) + scenario_failures() + destination_skill_failures()

    def test_current_contract(self) -> None:
        self.assertEqual([], self._current_failures())

    def test_output_slot_mutation_is_detected(self) -> None:
        skill = ROOT / SKILL_PATH
        if not skill.is_file():
            self.skipTest("canonical skill is intentionally absent in the red baseline")
        skill_text = skill.read_text(encoding="utf-8")
        mutated = skill_text.replace("First safe check:", "Initial check:", 1)
        failures = contract_failures(
            mutated,
            (ROOT / SRE_PATH).read_text(encoding="utf-8"),
            (ROOT / AGENTS_GUIDE_PATH).read_text(encoding="utf-8"),
            (ROOT / README_PATH).read_text(encoding="utf-8"),
        )
        self.assertIn("missing output slot: First safe check:", failures)

    def test_sre_route_mutation_is_detected(self) -> None:
        skill = ROOT / SKILL_PATH
        if not skill.is_file():
            self.skipTest("canonical skill is intentionally absent in the red baseline")
        sre_text = (ROOT / SRE_PATH).read_text(encoding="utf-8")
        mutated = sre_text.replace(
            "Load the `incident-navigation` skill only when", "Orient inline when"
        )
        failures = contract_failures(
            skill.read_text(encoding="utf-8"),
            mutated,
            (ROOT / AGENTS_GUIDE_PATH).read_text(encoding="utf-8"),
            (ROOT / README_PATH).read_text(encoding="utf-8"),
        )
        self.assertIn(
            "SRE route is not limited to explicit responder uncertainty", failures
        )

    def test_authority_mutation_is_detected(self) -> None:
        skill = ROOT / SKILL_PATH
        if not skill.is_file():
            self.skipTest("canonical skill is intentionally absent in the red baseline")
        skill_text = skill.read_text(encoding="utf-8")
        mutated = skill_text.replace("Tier 0", "safe").replace(
            "grants no tool or execution authority", "is advisory", 1
        )
        failures = contract_failures(
            mutated,
            (ROOT / SRE_PATH).read_text(encoding="utf-8"),
            (ROOT / AGENTS_GUIDE_PATH).read_text(encoding="utf-8"),
            (ROOT / README_PATH).read_text(encoding="utf-8"),
        )
        self.assertIn("Tier 0 boundary is absent", failures)
        self.assertIn("no-authority boundary is absent", failures)

    def test_broad_triage_trigger_mutation_is_detected(self) -> None:
        skill = ROOT / SKILL_PATH
        if not skill.is_file():
            self.skipTest("canonical skill is intentionally absent in the red baseline")
        skill_text = skill.read_text(encoding="utf-8")
        mutated = skill_text.replace(
            "description: >-", "description: >-\n  Help me triage this.", 1
        )
        failures = contract_failures(
            mutated,
            (ROOT / SRE_PATH).read_text(encoding="utf-8"),
            (ROOT / AGENTS_GUIDE_PATH).read_text(encoding="utf-8"),
            (ROOT / README_PATH).read_text(encoding="utf-8"),
        )
        self.assertIn("description overlaps ordinary SRE triage", failures)

    def test_live_output_guard_mutation_is_detected(self) -> None:
        skill = ROOT / SKILL_PATH
        if not skill.is_file():
            self.skipTest("canonical skill is intentionally absent in the red baseline")
        skill_text = skill.read_text(encoding="utf-8")
        mutated = skill_text.replace(
            "The entire response is the packet", "The packet is the main response", 1
        )
        failures = contract_failures(
            mutated,
            (ROOT / SRE_PATH).read_text(encoding="utf-8"),
            (ROOT / AGENTS_GUIDE_PATH).read_text(encoding="utf-8"),
            (ROOT / README_PATH).read_text(encoding="utf-8"),
        )
        self.assertIn("the response is not bound to packet-only output", failures)

    def test_scenario_evidence_mutation_is_detected(self) -> None:
        filename = "discovery-incident-navigation-defers-approved-change.yaml"
        path = ROOT / "evals" / "scenarios" / filename
        text = path.read_text(encoding="utf-8")
        mutated = text.replace("Approved by: release owner", "Approval record: attached", 1)
        failures = scenario_text_failures(filename, mutated)
        self.assertIn(
            f"{filename}: missing supplied evidence: Approved by: release owner",
            failures,
        )

    def test_output_template_fence_mutation_is_detected(self) -> None:
        skill = ROOT / SKILL_PATH
        if not skill.is_file():
            self.skipTest("canonical skill is intentionally absent in the red baseline")
        skill_text = skill.read_text(encoding="utf-8")
        mutated = skill_text.replace(
            "Incident orientation:", "```text\nIncident orientation:", 1
        ).replace("State changed: no", "State changed: no\n```", 1)
        failures = contract_failures(
            mutated,
            (ROOT / SRE_PATH).read_text(encoding="utf-8"),
            (ROOT / AGENTS_GUIDE_PATH).read_text(encoding="utf-8"),
            (ROOT / README_PATH).read_text(encoding="utf-8"),
        )
        self.assertIn("output template still teaches code fencing", failures)

    def test_destination_skill_contract_mutation_is_detected(self) -> None:
        path = ROOT / "skills" / "production-change-gate" / "SKILL.md"
        text = path.read_text(encoding="utf-8")
        mutated = text.replace(
            "The entire response is the verdict packet",
            "The verdict packet should be included",
            1,
        )
        fragments = DESTINATION_SKILL_CONTRACTS[Path("skills/production-change-gate/SKILL.md")]
        normalized = " ".join(mutated.split())
        missing = [
            fragment
            for fragment in fragments
            if fragment not in mutated and fragment.casefold() not in normalized.casefold()
        ]
        self.assertIn("the entire response is the verdict packet", missing)


if __name__ == "__main__":
    unittest.main()
