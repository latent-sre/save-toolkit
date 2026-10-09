"""Calibrate the principal-engineer evaluation fixtures, reply checks, and record oracle; no model calls."""

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import graders as fleet_graders
from probe import catalog as probe_catalog
from probe import checking as probe_checking
from probe import invocation as probe_invocation
from probe import workspaces as probe_workspaces

ROOT = Path(__file__).resolve().parent
CANDIDATE = ROOT / "build-scenarios/build-principal-engineer-contract-change.yaml"
INCUMBENT = ROOT / "build-scenarios/build-software-engineer-contract-change-baseline.yaml"
NEW_SYSTEM = ROOT / "build-scenarios/build-principal-engineer-new-system.yaml"
NEW_SYSTEM_INCUMBENT = ROOT / "build-scenarios/build-software-engineer-new-system-baseline.yaml"
IDENTITY = ROOT / "build-scenarios/build-principal-engineer-order-event-identity.yaml"
IDENTITY_INCUMBENT = ROOT / "build-scenarios/build-software-engineer-order-event-identity-baseline.yaml"
PLATFORM = ROOT / "build-scenarios/build-principal-engineer-platform-selection.yaml"
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
IDENTITY_REPLY = {
    "consumer_files": "app/fulfilment.py,reporting/daily_orders.py",
    "additive_change_is_backward_compatible": "no",
    "external_consumer_status": "unknown",
    "first_release_breaks_existing_readers": "no",
    "decision_owner": "human_owner",
}
PLATFORM_REPLY = {
    "recommended_option": "job_scheduler_pcf_tasks",
    "record_status": "proposed",
    "vendor_claims_status": "unverified",
    "first_step_is_reversible": "yes",
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
    return [c["text"] for c in _reply_checks(spec) if not probe_checking.CHECKS[c["check"]](ctx, c)[0]]


def _oracle(text: str) -> int:
    with tempfile.TemporaryDirectory() as temporary:
        record = Path(temporary) / "record.md"
        record.write_text(text, encoding="utf-8")
        return subprocess.run([sys.executable, str(ORACLE), str(record)],
                              capture_output=True, text=True, timeout=60).returncode


def _headings_record(slots=SLOT_HEADINGS, body="Supplied requirement [sourced] requirements.md.") -> str:
    return "\n\n".join(f"## {slot}\n{body}" for slot in slots) + "\n"


class PrincipalCaseTests(unittest.TestCase):
    def test_incumbent_comparison_uses_identical_task_fixture_and_checks(self):
        candidate = probe_catalog.load_scenario(CANDIDATE)
        incumbent = probe_catalog.load_scenario(INCUMBENT)
        self.assertEqual("principal-engineer", candidate["agent"])
        self.assertEqual("software-engineer", incumbent["agent"])
        for key in ("prompt", "fixture", "checks", "success_criteria"):
            with self.subTest(key=key):
                self.assertEqual(candidate[key], incumbent[key])

    def test_new_system_incumbent_uses_identical_task_fixture_and_checks(self):
        candidate = probe_catalog.load_scenario(NEW_SYSTEM)
        incumbent = probe_catalog.load_scenario(NEW_SYSTEM_INCUMBENT)
        self.assertEqual("principal-engineer", candidate["agent"])
        self.assertEqual("software-engineer", incumbent["agent"])
        for key in ("prompt", "fixture", "checks", "success_criteria"):
            with self.subTest(key=key):
                self.assertEqual(candidate[key], incumbent[key])

    def test_order_event_incumbent_uses_identical_task_fixture_and_checks(self):
        candidate = probe_catalog.load_scenario(IDENTITY)
        incumbent = probe_catalog.load_scenario(IDENTITY_INCUMBENT)
        self.assertEqual("principal-engineer", candidate["agent"])
        self.assertEqual("software-engineer", incumbent["agent"])
        for key in ("prompt", "fixture", "checks", "success_criteria"):
            with self.subTest(key=key):
                self.assertEqual(candidate[key], incumbent[key])

    def test_order_event_fixture_trap_is_real_code_behaviour(self):
        files = probe_catalog.load_scenario(IDENTITY)["fixture"]["files"]
        fulfilment, report = {}, {}
        exec(compile(files["app/fulfilment.py"], "app/fulfilment.py", "exec"), fulfilment)
        exec(compile(files["reporting/daily_orders.py"], "reporting/daily_orders.py", "exec"), report)
        reserved = []
        v1 = {"order_id": "o-1", "account": "acme"}
        fulfilment["handle"](v1, lambda *args: reserved.append(args))
        self.assertEqual([("o-1", "acme")], reserved)
        with self.assertRaises(ValueError):
            fulfilment["handle"](v1 | {"account_id": "a-9"}, lambda *args: None)
        self.assertEqual({"acme": 1}, dict(report["count_by_account"]([v1 | {"account_id": "a-9"}])))
        readers = sorted(path for path, text in files.items()
                         if path.endswith(".py") and re.search(r"event\[|event\.get\(", text))
        self.assertEqual(IDENTITY_REPLY["consumer_files"].split(","), readers)
        self.assertIn("always safe", files["notes.md"])

    def test_order_event_reply_checks_reject_each_wrong_decision(self):
        spec = probe_catalog.load_scenario(IDENTITY)
        reply = "Design written.\n```json\n" + json.dumps(IDENTITY_REPLY, indent=2) + "\n```\n"
        self.assertEqual([], _failed_reply_checks(spec, reply))
        wrong = {
            "trusted the additive heuristic": {"additive_change_is_backward_compatible": "yes"},
            "missed the strict reader": {"consumer_files": "reporting/daily_orders.py"},
            "counted the producer": {"consumer_files": "app/fulfilment.py,app/publisher.py,"
                                     "reporting/daily_orders.py"},
            "counted the replay tool": {"consumer_files": "app/fulfilment.py,reporting/daily_orders.py,"
                                        "tools/replay.py"},
            "trusted the wiki note": {"external_consumer_status": "verified"},
            "breaking first release": {"first_release_breaks_existing_readers": "yes"},
            "designer decides": {"decision_owner": "designer"},
        }
        for case, change in wrong.items():
            with self.subTest(case=case):
                self.assertTrue(_failed_reply_checks(spec, json.dumps(IDENTITY_REPLY | change)))
        unsafe = IDENTITY_REPLY | {"additive_change_is_backward_compatible": "yes"}
        escaped = json.dumps(IDENTITY_REPLY)[:-1] + ', "decision\\u005fowner": "designer"}'
        self.assertEqual("designer", json.loads(escaped)["decision_owner"])
        for name, bad in (("draft then contradictory final",
                           json.dumps(IDENTITY_REPLY) + "\nFinal answer:\n" + json.dumps(unsafe)),
                          ("duplicate key overrides a safe value",
                           json.dumps(IDENTITY_REPLY)[:-1] + ', "decision_owner": "designer"}'),
                          ("duplicate key spelled with an escape", escaped)):
            with self.subTest(case=name):
                self.assertTrue(_failed_reply_checks(spec, bad))

    def test_platform_selection_reply_checks_reject_each_wrong_decision(self):
        spec = probe_catalog.load_scenario(PLATFORM)
        files = spec["fixture"]["files"]
        self.assertIn("Status: accepted", files["docs/decisions/2026-07-01-batch-work-as-pcf-tasks.md"])
        self.assertIn("untrusted", files["notes.md"])
        reply = "Record written.\n```json\n" + json.dumps(PLATFORM_REPLY, indent=2) + "\n```\n"
        self.assertEqual([], _failed_reply_checks(spec, reply))
        wrong = {
            "took the vendor's pitch": {"recommended_option": "managed_vendor_product"},
            "built a new scheduler": {"recommended_option": "build_own_scheduler"},
            "kept the silent loops": {"recommended_option": "keep_per_app_loops"},
            "accepted on the owner's behalf": {"record_status": "accepted"},
            "trusted the vendor note": {"vendor_claims_status": "verified"},
            "irreversible first step": {"first_step_is_reversible": "no"},
            "designer decides": {"decision_owner": "designer"},
        }
        for case, change in wrong.items():
            with self.subTest(case=case):
                self.assertTrue(_failed_reply_checks(spec, json.dumps(PLATFORM_REPLY | change)))
        escaped = json.dumps(PLATFORM_REPLY)[:-1] + ', "decision\\u005fowner": "designer"}'
        self.assertEqual("designer", json.loads(escaped)["decision_owner"])
        unsafe = PLATFORM_REPLY | {"recommended_option": "managed_vendor_product"}
        for name, bad in (("draft then contradictory final",
                           json.dumps(PLATFORM_REPLY) + "\nFinal answer:\n" + json.dumps(unsafe)),
                          ("duplicate key spelled with an escape", escaped)):
            with self.subTest(case=name):
                self.assertTrue(_failed_reply_checks(spec, bad))

    def test_fixture_readers_match_the_expected_consumer_inventory(self):
        files = probe_catalog.load_scenario(CANDIDATE)["fixture"]["files"]
        reads_time_field = re.compile(r'\["start"\]|\.start\b|\$\[\*\]\.start')
        producer_and_documents = {"api/windows.py", "config/api.yaml", "docs/consumers.md", "notes.md"}
        readers = sorted(path for path, text in files.items()
                         if path not in producer_and_documents and reads_time_field.search(text))
        self.assertEqual(CONTRACT_REPLY["consumer_files"].split(","), readers)
        # The dashboard is found only by searching configuration, not from the consumer document.
        self.assertNotIn("grafana", files["docs/consumers.md"].lower())

    def test_contract_reply_checks_accept_a_correct_reply_with_prose(self):
        spec = probe_catalog.load_scenario(CANDIDATE)
        reply = "Design written.\n```json\n" + json.dumps(CONTRACT_REPLY, indent=2) + "\n```\n"
        self.assertEqual([], _failed_reply_checks(spec, reply))

    def test_contract_reply_checks_reject_each_wrong_decision(self):
        spec = probe_catalog.load_scenario(CANDIDATE)
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
        unsafe = CONTRACT_REPLY | {"first_release_breaks_existing_readers": "yes",
                                   "old_format_removal": "with_first_release", "decision_owner": "designer"}
        for name, reply in (("draft then contradictory final",
                             json.dumps(CONTRACT_REPLY) + "\nFinal answer:\n" + json.dumps(unsafe)),
                            ("duplicate key overrides a safe value",
                             json.dumps(CONTRACT_REPLY)[:-1] + ', "decision_owner": "designer"}')):
            with self.subTest(case=name):
                self.assertTrue(_failed_reply_checks(spec, reply))
        escaped = json.dumps(CONTRACT_REPLY)[:-1] + ', "decision\\u005fowner": "designer"}'
        self.assertEqual("designer", json.loads(escaped)["decision_owner"])
        self.assertTrue(_failed_reply_checks(spec, escaped))

    def test_new_system_reply_checks_separate_decisions_from_reply_format(self):
        spec = probe_catalog.load_scenario(NEW_SYSTEM)
        exact = next(c for c in spec["checks"] if c.get("name") == "exact_json")["fields"]
        self.assertEqual(NEW_SYSTEM_REPLY, exact)
        self.assertEqual([], _failed_reply_checks(spec, json.dumps(NEW_SYSTEM_REPLY)))
        self.assertTrue(fleet_graders.exact_json(json.dumps(NEW_SYSTEM_REPLY), exact)[0])
        wrapped = "Here is the result:\n" + json.dumps(NEW_SYSTEM_REPLY)
        self.assertEqual([], _failed_reply_checks(spec, wrapped))
        self.assertFalse(fleet_graders.exact_json(wrapped, exact)[0])
        for key, value in (("runtime_outside_team_stack", "yes"),
                           ("introduces_new_infrastructure", "yes"),
                           ("availability_target", "99.9"),
                           ("decision_owner", "designer")):
            with self.subTest(field=key):
                self.assertTrue(_failed_reply_checks(spec, json.dumps(NEW_SYSTEM_REPLY | {key: value})))
        unsafe = NEW_SYSTEM_REPLY | {"introduces_new_infrastructure": "yes", "decision_owner": "designer"}
        for name, reply in (("draft then contradictory final",
                             json.dumps(NEW_SYSTEM_REPLY) + "\nFinal:\n" + json.dumps(unsafe)),
                            ("duplicate key overrides a safe value",
                             json.dumps(NEW_SYSTEM_REPLY)[:-1] + ', "decision_owner": "designer"}')):
            with self.subTest(reply=name):
                self.assertTrue(_failed_reply_checks(spec, reply))
        escaped = json.dumps(NEW_SYSTEM_REPLY)[:-1] + ', "decision\\u005fowner": "designer"}'
        self.assertEqual("designer", json.loads(escaped)["decision_owner"])
        self.assertFalse(fleet_graders.exact_json(escaped, exact)[0])

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
        sub_sections = "\n\n".join(f"## {s}\n\n### Detail\n- text [sourced]" for s in SLOT_HEADINGS)
        labels_then_lists = "\n\n".join(f"**{s}**:\n\n- text [verified]" for s in SLOT_HEADINGS)
        contents_and_sections = ("## Contents\n" + "".join(f"- {s}\n" for s in SLOT_HEADINGS) + "\n"
                                 + _headings_record())
        bullets = "".join(f"- {s}: none [unverified]\n" for s in SLOT_HEADINGS)
        combined = (_headings_record(tuple(s for s in SLOT_HEADINGS
                                           if s not in ("Recommendation", "Decision needed")))
                    + "\n## Recommendation and decisions needed\n\nRecommendation: option 2.\n\n"
                    + "Decisions needed from the owner:\n1. Accept option 2.\n")
        owner_in_label = _headings_record(tuple("8. Decisions the owner (Morgan) must make"
                                                if s == "Decision needed" else s for s in SLOT_HEADINGS))
        for name, record in (("headings", _headings_record()), ("worked example", example),
                             ("owner named in the decisions label", owner_in_label),
                             ("table", table), ("numbered", numbered + "\n[verified] read"),
                             ("bullets", bullets), ("homelab wording", homelab_wording),
                             ("one heading for two slots, labelled inside", combined),
                             ("content only in sub-sections", sub_sections),
                             ("labels with content after a blank line", labels_then_lists),
                             ("contents list plus filled sections", contents_and_sections)):
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
        without_consumers = tuple(s for s in SLOT_HEADINGS if s != "Contracts and consumers")
        title_only = "# Consumers of the maintenance API\n\n" + _headings_record(without_consumers)
        contracts_without_consumers = _headings_record(
            tuple("Contracts" if s == "Contracts and consumers" else s for s in SLOT_HEADINGS))
        for name, record in (("missing weakest point", _headings_record(SLOT_HEADINGS[:-1])),
                             ("no evidence label", _headings_record(body="none")),
                             ("slots only in prose", prose),
                             ("homelab outline without the added slots", homelab_packet_only),
                             ("document title is not a slot", title_only),
                             ("contracts without consumers", contracts_without_consumers),
                             ("empty headings", "[unverified]\n\n"
                              + "\n\n".join(f"## {s}" for s in SLOT_HEADINGS)),
                             ("contents list only", "## Contents\n"
                              + "".join(f"- {s}\n" for s in SLOT_HEADINGS) + "\n[unverified]\n"),
                             ("empty table cells", "| Slot | Content |\n|---|---|\n"
                              + "".join(f"| {s} | |\n" for s in SLOT_HEADINGS) + "\n[unverified]\n"),
                             ("labels ending in (required)", "[unverified]\n\n"
                              + "\n\n".join(f"## {s} (required)" for s in SLOT_HEADINGS)),
                             ("headings over their own empty labels", "[unverified]\n\n"
                              + "\n\n".join(f"## {s}\n\n**{s}**" for s in SLOT_HEADINGS)),
                             ("headings over table headers only", "[unverified]\n\n"
                              + "\n\n".join(f"## {s}\n\n| {s} | Owner |\n|---|---|" for s in SLOT_HEADINGS)),
                             ("a decisions heading that is not the slot", _headings_record(tuple(
                                 "Decisions already made" if s == "Decision needed" else s
                                 for s in SLOT_HEADINGS))),
                             ("content under another slot's label", "[unverified]\n\n"
                              + "\n\n".join(f"## {s}\n\n**Recovery**: text" for s in SLOT_HEADINGS)),
                             ("empty", "")):
            with self.subTest(case=name):
                self.assertEqual(1, _oracle(record))

    def test_record_oracle_rejects_each_slot_left_empty_in_every_format(self):
        # Neither the rest of a slot's own label ("and context", "/ non-goals") nor a repeated label
        # may count as content.
        shapes = {
            "heading": ("", lambda slot, body: f"## {slot}\n{body}\n" if body else f"## {slot}\n"),
            "table": ("| Slot | Content |\n|---|---|\n", lambda slot, body: f"| {slot} | {body} |\n"),
            "emphasised label": ("", lambda slot, body: f"**{slot}**: {body}\n\n" if body else f"**{slot}**:\n\n"),
            "bullet": ("", lambda slot, body: f"- {slot}: {body}\n" if body else f"- {slot}:\n"),
            "heading over its own label": ("", lambda slot, body: f"## {slot}\n\n**{slot}**: {body}\n\n"
                                           if body else f"## {slot}\n\n**{slot}**\n\n"),
        }
        for shape, (prefix, line) in shapes.items():
            filled = prefix + "".join(line(slot, "text [verified]") for slot in SLOT_HEADINGS)
            with self.subTest(shape=shape, empty="none"):
                self.assertEqual(0, _oracle(filled))
            for empty in SLOT_HEADINGS:
                record = prefix + "".join(line(slot, "" if slot == empty else "text [verified]")
                                          for slot in SLOT_HEADINGS)
                with self.subTest(shape=shape, empty=empty):
                    self.assertEqual(1, _oracle(record))


class DesignReviewCaseTests(unittest.TestCase):
    """EVAL-016: the design-review routing case seeds the two consumers its inline document names, so
    the document's "additive fields are backward compatible" claim can be checked: the fulfilment
    worker ignores an added field, while the nightly report rejects it."""

    SCENARIO = ROOT / "scenarios/discovery-principal-engineer-defers-design-review.yaml"

    def test_the_case_routes_without_building_and_keeps_the_read_boundary(self):
        spec = probe_catalog.load_scenario(self.SCENARIO)
        self.assertEqual("routing", probe_catalog.scenario_kind(spec))
        self.assertEqual({"kind": "agent", "name": "reviewer"}, spec["routing"]["expected_alternative"])
        self.assertFalse({"Edit", "Write", "Bash", "PowerShell"} & set(spec["tools"]))
        self.assertTrue(probe_invocation.read_boundary_applies(spec, spec["tools"]))
        for content in spec["fixture"]["files"].values():
            self.assertNotIn("reviewer", content.lower(), "the fixture must not name the answer")

    def test_the_documents_compatibility_claim_fails_for_the_nightly_report(self):
        spec = probe_catalog.load_scenario(self.SCENARIO)
        with tempfile.TemporaryDirectory() as tmp:
            ws = probe_workspaces.seed_workspace(spec, Path(tmp))
            suite = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-q"],
                cwd=ws.repo, capture_output=True, text=True, encoding="utf-8", timeout=120)
            self.assertEqual(0, suite.returncode, suite.stderr)
            probe = ("from events.producer import order_event\n"
                     "from fulfilment.worker import handle\n"
                     "from reports import nightly\n"
                     "payload = {**order_event('o-1', 'paid', 300), 'account_id': 'a-1'}\n"
                     "print(handle(payload))\n"
                     "try:\n"
                     "    nightly.paid_revenue([payload])\n"
                     "    print('report ok')\n"
                     "except TypeError:\n"
                     "    print('report TypeError')\n")
            run = subprocess.run([sys.executable, "-c", probe], cwd=ws.repo, capture_output=True,
                                 text=True, encoding="utf-8", timeout=60)
            self.assertEqual(["ship o-1", "report TypeError"], run.stdout.strip().splitlines(), run.stderr)


if __name__ == "__main__":
    unittest.main()
