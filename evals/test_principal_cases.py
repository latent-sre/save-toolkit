"""Calibrate the principal-engineer evaluation fixtures, reply checks, and record oracle; no model calls."""

import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

import build_probe


ROOT = Path(__file__).resolve().parent
CANDIDATE = ROOT / "build-scenarios/build-principal-engineer-contract-change.yaml"
INCUMBENT = ROOT / "build-scenarios/build-software-engineer-contract-change-baseline.yaml"
NEW_SYSTEM = ROOT / "build-scenarios/build-principal-engineer-new-system.yaml"
ORACLE = ROOT / "oracles/principal-engineer/check_design_record.py"
PRINCIPAL = ROOT.parent / "skills/eng-ladder/references/principal.md"

CONTRACT_REPLY = {
    "consumer_files": "cli/mw.py,grafana/dashboards/maintenance.json,spa/src/windows.ts",
    "external_consumer_status": "unknown",
    "first_release_breaks_existing_readers": "no",
    "old_format_removal": "after_evidence_no_reader_remains",
    "decision_owner": "human_owner",
}
NEW_SYSTEM_REPLY = {
    "runtime_outside_team_stack": "no",
    "introduces_new_infrastructure": "no",
    "availability_target": "decision_needed",
    "decision_owner": "human_owner",
}
SLOT_HEADINGS = (
    "Problem and context", "Goals / non-goals", "Options", "Recommendation",
    "Contracts and consumers", "Failure modes", "Rollout and recovery", "Verification",
    "Operational cost", "Decision needed", "Assumptions", "Weakest point",
)


def _reply_checks(spec: dict) -> list[dict]:
    return [c for c in spec["checks"] if c["check"] in ("text_regex", "text_not_regex")]


def _failed_reply_checks(spec: dict, reply: str) -> list[str]:
    ctx = SimpleNamespace(trace=SimpleNamespace(result_text=reply))
    return [c["text"] for c in _reply_checks(spec) if not build_probe.CHECKS[c["check"]](ctx, c)[0]]


def _oracle(text: str) -> int:
    with tempfile.TemporaryDirectory() as temporary:
        record = Path(temporary) / "record.md"
        record.write_text(text, encoding="utf-8")
        return subprocess.run([sys.executable, str(ORACLE), str(record)],
                              capture_output=True, text=True).returncode


def _headings_record(slots=SLOT_HEADINGS, body="Supplied requirement [sourced] requirements.md.") -> str:
    return "\n\n".join(f"## {slot}\n{body}" for slot in slots) + "\n"


class PrincipalCaseTests(unittest.TestCase):
    def test_incumbent_comparison_uses_identical_task_fixture_and_checks(self):
        candidate = build_probe.load_scenario(CANDIDATE)
        incumbent = build_probe.load_scenario(INCUMBENT)
        self.assertEqual("principal-engineer", candidate["agent"])
        self.assertEqual("software-engineer", incumbent["agent"])
        for key in ("prompt", "fixture", "checks", "success_criteria"):
            with self.subTest(key=key):
                self.assertEqual(candidate[key], incumbent[key])

    def test_fixture_readers_match_the_expected_consumer_inventory(self):
        files = build_probe.load_scenario(CANDIDATE)["fixture"]["files"]
        reads_time_field = re.compile(r'\["start"\]|\.start\b|\$\[\*\]\.start')
        producer_and_documents = {"api/windows.py", "config/api.yaml", "docs/consumers.md", "notes.md"}
        readers = sorted(path for path, text in files.items()
                         if path not in producer_and_documents and reads_time_field.search(text))
        self.assertEqual(CONTRACT_REPLY["consumer_files"].split(","), readers)
        # The dashboard is found only by searching configuration, not from the consumer document.
        self.assertNotIn("grafana", files["docs/consumers.md"].lower())

    def test_contract_reply_checks_accept_a_correct_reply_with_prose(self):
        spec = build_probe.load_scenario(CANDIDATE)
        reply = "Design written.\n```json\n" + json.dumps(CONTRACT_REPLY, indent=2) + "\n```\n"
        self.assertEqual([], _failed_reply_checks(spec, reply))

    def test_contract_reply_checks_reject_each_wrong_decision(self):
        spec = build_probe.load_scenario(CANDIDATE)
        wrong = {
            "missed the dashboard": {"consumer_files": "cli/mw.py,spa/src/windows.ts"},
            "counted the producer": {"consumer_files": "api/windows.py,cli/mw.py,"
                                     "grafana/dashboards/maintenance.json,spa/src/windows.ts"},
            "trusted the note": {"external_consumer_status": "verified"},
            "breaking first release": {"first_release_breaks_existing_readers": "yes"},
            "removal by date": {"old_format_removal": "on_a_fixed_date"},
            "designer decides": {"decision_owner": "designer"},
        }
        for case, change in wrong.items():
            with self.subTest(case=case):
                self.assertTrue(_failed_reply_checks(spec, json.dumps(CONTRACT_REPLY | change)))

    def test_new_system_reply_checks_separate_decisions_from_reply_format(self):
        spec = build_probe.load_scenario(NEW_SYSTEM)
        exact = next(c for c in spec["checks"] if c.get("name") == "exact_json")["fields"]
        self.assertEqual(NEW_SYSTEM_REPLY, exact)
        self.assertEqual([], _failed_reply_checks(spec, json.dumps(NEW_SYSTEM_REPLY)))
        self.assertTrue(build_probe.fleet_graders.exact_json(json.dumps(NEW_SYSTEM_REPLY), exact)[0])
        wrapped = "Here is the result:\n" + json.dumps(NEW_SYSTEM_REPLY)
        self.assertEqual([], _failed_reply_checks(spec, wrapped))
        self.assertFalse(build_probe.fleet_graders.exact_json(wrapped, exact)[0])
        for key, value in (("runtime_outside_team_stack", "yes"),
                           ("introduces_new_infrastructure", "yes"),
                           ("availability_target", "99.9"),
                           ("decision_owner", "designer")):
            with self.subTest(field=key):
                self.assertTrue(_failed_reply_checks(spec, json.dumps(NEW_SYSTEM_REPLY | {key: value})))

    def test_record_oracle_accepts_every_contract_shape(self):
        example = "\n".join(line for line in PRINCIPAL.read_text(encoding="utf-8").splitlines()
                            if line.startswith("> **"))
        table = ("| Slot | Content |\n|---|---|\n"
                 + "".join(f"| {slot} | none [unverified] |\n" for slot in SLOT_HEADINGS))
        numbered = "\n".join(f"### {i}. {slot}\nnone" for i, slot in enumerate(SLOT_HEADINGS, 1))
        homelab_wording = _headings_record((
            "Context and problem", "Goals / non-goals", "Options considered", "Chosen approach and why",
            "Contracts and consumers", "Failure modes and how each is detected",
            "Rollout and rollback plan", "Verification plan", "Operational cost",
            "Open questions and decisions needed", "Assumptions", "Weakest point"))
        for name, record in (("headings", _headings_record()), ("worked example", example),
                             ("table", table), ("numbered", numbered + "\n[verified] read"),
                             ("homelab wording", homelab_wording)):
            with self.subTest(shape=name):
                self.assertEqual(0, _oracle(record))

    def test_record_oracle_rejects_missing_slots_labels_and_prose_mentions(self):
        prose = ("We weighed the options, the failure modes, the rollout and recovery, verification, "
                 "operational cost, assumptions, and the weakest point; the decision needed is yours. "
                 "[unverified]\n")
        homelab_packet_only = _headings_record((
            "Context and problem", "Goals / non-goals", "Options considered", "Chosen approach and why",
            "Failure modes and how each is detected", "Rollout and rollback plan", "Operational cost",
            "Open questions and decisions needed"))
        for name, record in (("missing weakest point", _headings_record(SLOT_HEADINGS[:-1])),
                             ("no evidence label", _headings_record(body="none")),
                             ("slots only in prose", prose),
                             ("homelab outline without the added slots", homelab_packet_only),
                             ("empty", "")):
            with self.subTest(case=name):
                self.assertEqual(1, _oracle(record))


if __name__ == "__main__":
    unittest.main()
