#!/usr/bin/env python3
"""Focused source-contract regressions for accepted GRAPH-001 findings."""

from __future__ import annotations

import unittest
from pathlib import Path

import validate_fleet


ROOT = Path(__file__).resolve().parents[1]
AGENTS = tuple(sorted((ROOT / "agents").glob("*.md")))
SRE_HANDOFF = ROOT / "skills/investigation-depth/references/incident-handoff.md"


def _compact(text: str) -> str:
    return " ".join(text.split())


def _agent_contract_text(path: Path) -> str:
    """Return always-loaded agent text plus any predicate-loaded contract under test."""

    text = path.read_text(encoding="utf-8")
    if path.name == "sre.md":
        contract = validate_fleet._resolve_handoff_contract(ROOT, path.stem, text)
        if contract is not None and contract != text:
            text += "\n" + contract
    return _compact(text)


class GraphContractTests(unittest.TestCase):
    def test_sre_and_engineering_ladders_are_separate_context_routers(self) -> None:
        sre_agent = _compact((ROOT / "agents/sre.md").read_text(encoding="utf-8"))
        engineering = _compact((ROOT / "skills/eng-ladder/SKILL.md").read_text(encoding="utf-8"))
        incident_command = _compact(
            (ROOT / "skills/incident-command/SKILL.md").read_text(encoding="utf-8")
        )
        sre_ladder_path = ROOT / "skills/investigation-depth/SKILL.md"

        self.assertTrue(sre_ladder_path.is_file(), "the investigation-depth router must exist")
        sre_ladder = _compact(sre_ladder_path.read_text(encoding="utf-8"))

        self.assertIn("`investigation-depth`", sre_agent)
        self.assertNotIn("`eng-ladder`", sre_agent)
        self.assertNotIn("The SRE track", engineering)
        self.assertNotIn("responder", engineering.lower())
        self.assertIn("`investigation-depth` owns investigation-depth selection", incident_command)
        for retired_reference in (
            "responder.md",
            "investigator.md",
            "elite.md",
            "golden-signals.md",
        ):
            with self.subTest(retired_reference=retired_reference):
                self.assertFalse(
                    (ROOT / "skills/eng-ladder/references" / retired_reference).exists(),
                    "incident-mode references must not return to the engineering ladder",
                )
        for name in (
            "first-response.md",
            "hypothesis-investigation.md",
            "systemic-failure.md",
            "signal-characterization.md",
            "recovery-lifecycle.md",
            "incident-handoff.md",
        ):
            with self.subTest(reference=name):
                self.assertIn(f"references/{name}", sre_ladder)
                self.assertTrue((ROOT / "skills/investigation-depth/references" / name).is_file())

    def test_sre_support_span_closeout_and_heavy_context_are_predicate_keyed(self) -> None:
        sre_agent = _compact((ROOT / "agents/sre.md").read_text(encoding="utf-8"))
        sre_ladder = _compact((ROOT / "skills/investigation-depth/SKILL.md").read_text(encoding="utf-8"))
        fleet_guide = _compact((ROOT / "AGENTS.md").read_text(encoding="utf-8"))
        triage_scenario = (
            ROOT / "evals/scenarios/agent-direct-sre-readonly-triage.yaml"
        ).read_text(
            encoding="utf-8"
        )
        drill_packets = (
            ROOT
            / "skills/incident-drill/assets/scenarios/checkout-payments-timeout/packets.md"
        ).read_text(encoding="utf-8")

        for token in (
            "Bounded assist is the default",
            "Stop after the requested evidence slice",
            "Enter sustained response only when",
            "explicitly assigns lifecycle support",
            "human SRE or incident commander remains the operational owner",
            "Do not classify those candidates as learning dispositions",
            "a terminal incident state is recorded",
            "explicitly asks for operational closeout",
        ):
            with self.subTest(token=token):
                self.assertIn(token, sre_agent)

        self.assertIn("recovery-lifecycle.md", sre_ladder)
        self.assertIn("incident-handoff.md", sre_ladder)
        self.assertIn(
            "Bounded incident assistance; owns the technical record through recovery only when assigned",
            fleet_guide,
        )
        self.assertNotIn("Every new operational fact", sre_agent)
        self.assertNotIn("Learning dispositions:", sre_agent)
        self.assertNotIn("incident-state/v2", sre_agent)
        self.assertNotIn("→ Handing to:", sre_agent)
        self.assertNotIn(
            "Names the recommendation owner, urgency, approval, verification, rollback, and learning dispositions",
            triage_scenario,
        )
        self.assertIn(
            r'pattern: "(?im)^\\s*learning dispositions?\\s*:"', triage_scenario
        )
        self.assertIn('of: ["incident-state/v2", "→ handing to:"]', triage_scenario)
        self.assertNotIn("Learning dispositions (incident still live", drill_packets)
        self.assertIn(
            "Durable discovery candidates (incident still live — evidence only, not dispositions)",
            drill_packets,
        )

        recovery = _compact(
            (ROOT / "skills/investigation-depth/references/recovery-lifecycle.md").read_text(
                encoding="utf-8"
            )
        )
        handoff = _compact(SRE_HANDOFF.read_text(encoding="utf-8"))
        self.assertIn("incident-state/v2", recovery)
        self.assertIn("→ Handing to:", handoff)

    def test_documented_ungranted_handoffs_return_to_the_caller(self) -> None:
        expected = {
            "agent-engineer.md": ("reviewer", "software-engineer"),
            "observability-engineer.md": ("software-engineer",),
            "sre.md": ("software-engineer",),
            "software-engineer.md": ("sre", "observability-engineer"),
        }
        for filename, lanes in expected.items():
            text = _compact((ROOT / "agents" / filename).read_text(encoding="utf-8"))
            for lane in lanes:
                with self.subTest(agent=filename, lane=lane):
                    self.assertIn(
                        f"This role cannot invoke `{lane}`; the recommendation returns to the caller, who dispatches it.",
                        text,
                    )

    def test_software_engineer_review_cycle_is_bounded_and_terminal(self) -> None:
        text = _compact((ROOT / "agents/software-engineer.md").read_text(encoding="utf-8"))
        for token in (
            "numeric maximum review/fix rounds",
            "elapsed-time or cost budget",
            "accepted exact candidate",
            "no progress or inconclusive verification",
            "stale candidate requiring fresh review",
            "budget exhausted",
            "safety or authority stop",
            "does not reset the review budget",
        ):
            with self.subTest(token=token):
                self.assertIn(token, text)

    def test_software_engineer_loads_obs_pipeline_for_app_instrumentation(self) -> None:
        software_engineer = _compact(
            (ROOT / "agents/software-engineer.md").read_text(encoding="utf-8")
        )
        obs_pipeline = _compact(
            (ROOT / "skills/obs-pipeline/SKILL.md").read_text(encoding="utf-8")
        )

        self.assertIn(
            "app-side instrumentation changes to the `software-engineer` agent",
            obs_pipeline,
            "obs-pipeline must keep application-code ownership with software-engineer",
        )
        self.assertIn(
            "`obs-pipeline` — before app-side OpenTelemetry instrumentation",
            software_engineer,
            "software-engineer must load the telemetry contract before changing app emission",
        )

    def test_missing_readiness_record_keeps_onboarding_unverified(self) -> None:
        lifecycle = _compact(
            (ROOT / "skills/service-lifecycle/SKILL.md").read_text(encoding="utf-8")
        )
        audit = _compact(
            (ROOT / "skills/service-readiness-audit/SKILL.md").read_text(encoding="utf-8")
        )

        self.assertIn("emit an **evidence-bound handoff** to `scribe`", lifecycle)
        self.assertIn("report onboarding as **unverified**", audit)
        self.assertIn("continue inspecting applicable controls", audit)
        self.assertNotIn("appears never to have been onboarded", audit)

    def test_missing_taint_contracts_carry_source_trust_and_claim_taint(self) -> None:
        for filename in ("agent-engineer.md", "researcher.md", "repository-investigator.md"):
            text = _compact((ROOT / "agents" / filename).read_text(encoding="utf-8"))
            with self.subTest(agent=filename):
                self.assertIn("Inputs/source trust:", text)
                self.assertIn("Missing or unlabeled trust defaults to `[UNTRUSTED]`", text)
                self.assertIn("claim-level `[UNTRUSTED]`", text)

    def test_authoring_method_requires_portable_lineage_and_delegate_failure_state(self) -> None:
        text = _compact(
            (ROOT / "skills/agent-authoring/references/roster.md").read_text(encoding="utf-8")
        )
        for token in (
            "Run/attempt",
            "requested and resolved model identity",
            "empty, malformed, partial, timed-out, or killed return",
            "failed attempt rather than success",
            "No background scheduler, lease, stale-worker detector, or heartbeat is implied",
        ):
            with self.subTest(token=token):
                self.assertIn(token, text)

    def test_instrumentation_prerequisite_crosses_incident_templates(self) -> None:
        postmortem_skill = (ROOT / "skills/postmortem/SKILL.md").read_text(encoding="utf-8")
        postmortem_template = (
            ROOT / "skills/postmortem/assets/postmortem-template.md"
        ).read_text(encoding="utf-8")
        incident_status = (
            ROOT / "skills/incident-command/references/command-and-communications.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Instrumentation prerequisite", postmortem_template)
        self.assertIn("instrumentation prerequisite", postmortem_skill.lower())
        self.assertIn("Instrumentation prerequisite", incident_status)
        self.assertIn("ready|blocked", incident_status)

    def test_no_incident_terminal_is_enumerated_and_propose_only(self) -> None:
        lifecycle = _compact(
            (
                ROOT / "skills/investigation-depth/references/recovery-lifecycle.md"
            ).read_text(encoding="utf-8")
        )
        sre_ladder = _compact(
            (ROOT / "skills/investigation-depth/SKILL.md").read_text(encoding="utf-8")
        )
        first_response = _compact(
            (
                ROOT / "skills/investigation-depth/references/first-response.md"
            ).read_text(encoding="utf-8")
        )
        for terminal in ("`resolved`", "`escalated-security`", "`no-incident`"):
            with self.subTest(terminal=terminal):
                self.assertIn(terminal, lifecycle)
        self.assertIn("never records it unprompted", lifecycle)
        for token in (
            "no-incident",
            "a human confirms it",
            "recovered on its own",
            "signals are arriving",
        ):
            with self.subTest(router_token=token):
                self.assertIn(token, sre_ladder)
        self.assertIn("no-incident", first_response)
        command_comms = _compact(
            (
                ROOT / "skills/incident-command/references/command-and-communications.md"
            ).read_text(encoding="utf-8")
        )
        self.assertIn(
            "no-incident",
            command_comms,
            "a declared incident that was never an incident needs a closure path in the "
            "skill that owns closing, or it can only be falsified as resolved",
        )


if __name__ == "__main__":
    unittest.main()
