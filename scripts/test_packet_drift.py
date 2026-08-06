"""Contract tests for the operational-learning packet drift and freshness watch."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WATCH_PATH = ROOT / "skills/operational-learning/scripts/packet_drift.py"


class PacketDriftTests(unittest.TestCase):
    """The watch answers one question per packet: has the ground moved under pending work?

    Every test here pins a decision that would otherwise be silently reversible: advisory by
    default, loud on an unreadable repository, and never reporting a clean result for evidence
    it could not actually inspect.
    """

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.repository = Path(self.temporary.name) / "checkout"
        self.repository.mkdir()
        self._git("init", "--quiet", ".")
        (self.repository / "deploy").mkdir()
        self._write("deploy/checkout.yaml", "name: checkout\n")
        self._write("deploy/other.yaml", "name: other\n")
        self._commit("base")
        self.base_revision = self._git("rev-parse", "HEAD")
        self.packet_path = Path(self.temporary.name) / "packet.json"

    def _git(self, *args: str) -> str:
        return subprocess.run(
            [
                "git",
                "-C",
                str(self.repository),
                "-c",
                "user.name=Packet Drift Tests",
                "-c",
                "user.email=tests@example.invalid",
                *args,
            ],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        ).stdout.strip()

    def _write(self, relative: str, content: str) -> None:
        (self.repository / relative).write_text(content, encoding="utf-8")

    def _commit(self, message: str) -> None:
        self._git("add", "--all")
        self._git("commit", "--quiet", "-m", message)

    def _packet(self, **overrides: object) -> dict[str, object]:
        packet: dict[str, object] = {
            "schema_version": 3,
            "update_id": "ku_checkout_application_approved",
            "created_at": "2026-08-01T12:00:00Z",
            "target": {
                "repository": "latent-sre/checkout",
                "revision": self.base_revision,
                "component_id": "checkout",
                "component_kind": "application",
                "display_name": "Checkout",
                "environment": "production",
                "definition_locator": "deploy/checkout.yaml",
                "knowledge_roots": ["docs"],
            },
            "trigger": {
                "kind": "component_added",
                "reference": "change/OPS-882",
                "state": "approved",
                "trust": "trusted",
            },
            "discovery": {
                "summary": "The approved application needs runbook closeout.",
                "evidence_status": "sourced",
                "evidence_ids": ["e1"],
            },
            "evidence": [
                {
                    "id": "e1",
                    "label": "sourced",
                    "kind": "repository",
                    "locator": "deploy/checkout.yaml",
                    "revision": self.base_revision,
                    "trust": "trusted",
                }
            ],
            "dispositions": [
                {
                    "artifact": "runbook",
                    "action": "handoff",
                    "status": "proposed",
                    "owner": "scribe",
                    "path": None,
                    "duplicate_of": None,
                    "base_sha256": None,
                    "artifact_sha256": None,
                    "reason": "Prepare the missing operating procedure.",
                    "evidence_ids": ["e1"],
                }
            ],
            "recommendation": {
                "summary": "Prepare and review the runbook.",
                "owner": "service-owner",
                "urgency": "next",
                "change_tier": 1,
                "requires_human_approval": False,
                "verification": "Review the documentation against the definition.",
                "rollback": None,
            },
            "limitations": [],
            "freshness": {"review_at": None, "expires_at": None},
        }
        packet.update(overrides)
        self.packet_path.write_text(json.dumps(packet), encoding="utf-8")
        return packet

    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(WATCH_PATH), str(self.packet_path), "--root", str(self.repository), *args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )

    def test_pending_packet_with_untouched_evidence_reports_no_drift(self) -> None:
        self._packet()
        result = self._run()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("no pending packet", result.stdout.lower())

    def test_commit_touching_pending_evidence_is_reported_but_stays_advisory(self) -> None:
        self._write("deploy/checkout.yaml", "name: checkout\nreplicas: 3\n")
        self._commit("scale checkout")
        self._packet()

        result = self._run()
        # Advisory by default is the whole posture: drift is a prompt to look, not a defect.
        # A non-zero exit here would make this unwireable into an existing pipeline.
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("ku_checkout_application_approved", result.stdout)
        self.assertIn("deploy/checkout.yaml", result.stdout)

    def test_commit_touching_an_unrelated_path_is_not_reported(self) -> None:
        self._write("deploy/other.yaml", "name: other\nreplicas: 9\n")
        self._commit("scale other")
        self._packet()

        result = self._run()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("no pending packet", result.stdout.lower())

    def test_fail_on_drift_turns_a_finding_into_a_nonzero_exit(self) -> None:
        self._write("deploy/checkout.yaml", "name: checkout\nreplicas: 3\n")
        self._commit("scale checkout")
        self._packet()

        self.assertEqual(1, self._run("--fail-on-drift").returncode)

    def test_fail_on_drift_still_exits_zero_when_there_is_nothing_to_report(self) -> None:
        """The half of the gate contract that is easy to lose: the flag must key on findings, not
        merely on being passed. Without this, mutating the exit expression to
        `1 if args.fail_on_drift else 0` fails every clean sweep and no test notices."""
        self._packet()

        result = self._run("--fail-on-drift")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("no pending packet", result.stdout.lower())

    def test_settled_packet_without_pending_dispositions_is_not_watched(self) -> None:
        self._write("deploy/checkout.yaml", "name: checkout\nreplicas: 3\n")
        self._commit("scale checkout")
        packet = self._packet()
        packet["dispositions"][0].update(  # type: ignore[index]
            {"action": "none", "status": "not_applicable", "duplicate_of": None}
        )
        self.packet_path.write_text(json.dumps(packet), encoding="utf-8")

        result = self._run()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("no pending packet", result.stdout.lower())

    def test_unreadable_repository_exits_two_rather_than_reporting_clean(self) -> None:
        """A git failure is not 'no drift'. Reporting OK here would hand --fail-on-drift a
        green run over a repository nobody could read."""
        self._packet()
        not_a_repository = Path(self.temporary.name) / "empty"
        not_a_repository.mkdir()
        result = subprocess.run(
            [
                sys.executable,
                str(WATCH_PATH),
                str(self.packet_path),
                "--root",
                str(not_a_repository),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        self.assertEqual(2, result.returncode)
        self.assertNotIn("no pending packet", result.stdout.lower())
        # Assert on this watch's own diagnostic, not the bare exit code: a missing interpreter
        # or a mistyped script path also exits 2, and would make this test pass over nothing.
        self.assertIn("packet_drift:", result.stderr)

    def test_revision_absent_from_the_checkout_exits_two(self) -> None:
        self._packet(
            target={
                "repository": "latent-sre/checkout",
                "revision": "0" * 40,
                "component_id": "checkout",
                "component_kind": "application",
                "display_name": "Checkout",
                "environment": None,
                "definition_locator": None,
                "knowledge_roots": ["docs"],
            }
        )
        result = self._run()
        self.assertEqual(2, result.returncode)
        self.assertIn("revision", result.stderr.lower())

    def test_unsafe_locator_is_reported_unwatchable_not_silently_dropped(self) -> None:
        packet = self._packet()
        packet["evidence"][0]["locator"] = "../../etc/passwd"  # type: ignore[index]
        self.packet_path.write_text(json.dumps(packet), encoding="utf-8")

        result = self._run()
        self.assertEqual(0, result.returncode, result.stderr)
        # Silently dropping it would read as "checked, clean" for evidence never inspected.
        self.assertIn("unwatchable", result.stdout.lower())
        self.assertIn("../../etc/passwd", result.stdout)

    def test_glob_locator_is_never_expanded_into_paths_the_packet_did_not_cite(self) -> None:
        """A locator is untrusted free text. `_safe_relative_path` accepts `*`, `[a-z]`, and
        `:(glob)` — they are legal path characters — so nothing but a literal pathspec stops Git
        from matching files the packet never cited and reporting them as its own evidence."""
        self._write("deploy/other.yaml", "name: other\nreplicas: 9\n")
        self._commit("scale other")
        packet = self._packet()
        packet["evidence"][0]["locator"] = "deploy/*.yaml"  # type: ignore[index]
        self.packet_path.write_text(json.dumps(packet), encoding="utf-8")

        findings = json.loads(self._run("--json").stdout)
        self.assertEqual(1, len(findings))
        self.assertEqual([], findings[0]["drifted_paths"])
        self.assertEqual(["deploy/*.yaml"], findings[0]["unwatchable_locators"])

    def test_locator_git_has_never_tracked_is_unwatchable_not_clean(self) -> None:
        """An empty log for a path Git has never heard of is not evidence of no drift. Treating
        it as clean is the same false green this watch exits 2 to avoid elsewhere."""
        packet = self._packet()
        packet["evidence"][0]["locator"] = "deploy/never-existed.yaml"  # type: ignore[index]
        self.packet_path.write_text(json.dumps(packet), encoding="utf-8")

        findings = json.loads(self._run("--json").stdout)
        self.assertEqual(1, len(findings))
        self.assertEqual([], findings[0]["drifted_paths"])
        self.assertEqual(["deploy/never-existed.yaml"], findings[0]["unwatchable_locators"])

    def test_untracked_file_on_disk_is_unwatchable_not_clean(self) -> None:
        """Existing on disk is not the same as Git being able to report history for it. An
        untracked or ignored path yields an empty log for the same reason a never-tracked one
        does, so deciding watchability from the filesystem re-opens the false-clean hole."""
        self._write("deploy/untracked.yaml", "name: untracked\n")
        packet = self._packet()
        packet["evidence"][0]["locator"] = "deploy/untracked.yaml"  # type: ignore[index]
        self.packet_path.write_text(json.dumps(packet), encoding="utf-8")

        findings = json.loads(self._run("--json").stdout)
        self.assertEqual(1, len(findings))
        self.assertEqual([], findings[0]["drifted_paths"])
        self.assertEqual(["deploy/untracked.yaml"], findings[0]["unwatchable_locators"])

    def test_deleted_evidence_path_still_counts_as_drift(self) -> None:
        """Deleting the file the packet reasoned about is the strongest possible drift signal.
        It must not fall through the never-tracked check into 'unwatchable'."""
        self._git("rm", "--quiet", "deploy/checkout.yaml")
        self._commit("drop checkout definition")
        self._packet()

        findings = json.loads(self._run("--json").stdout)
        self.assertEqual(1, len(findings))
        self.assertEqual(["deploy/checkout.yaml"], findings[0]["drifted_paths"])
        self.assertEqual([], findings[0]["unwatchable_locators"])

    def test_expired_and_due_freshness_deadlines_are_reported(self) -> None:
        self._packet(
            freshness={"review_at": "2026-09-01T00:00:00Z", "expires_at": "2026-10-01T00:00:00Z"}
        )

        before = self._run("--now", "2026-08-15T00:00:00Z")
        self.assertEqual(0, before.returncode, before.stderr)
        self.assertIn("no pending packet", before.stdout.lower())

        due = self._run("--now", "2026-09-15T00:00:00Z")
        self.assertIn("review", due.stdout.lower())
        self.assertNotIn("expired", due.stdout.lower())

        expired = self._run("--now", "2026-11-15T00:00:00Z")
        self.assertIn("expired", expired.stdout.lower())
        self.assertEqual(1, self._run("--now", "2026-11-15T00:00:00Z", "--fail-on-drift").returncode)

    def test_settled_packet_freshness_is_not_watched(self) -> None:
        packet = self._packet(
            freshness={"review_at": None, "expires_at": "2026-10-01T00:00:00Z"}
        )
        packet["dispositions"][0].update(  # type: ignore[index]
            {"action": "none", "status": "not_applicable"}
        )
        self.packet_path.write_text(json.dumps(packet), encoding="utf-8")

        result = self._run("--now", "2026-11-15T00:00:00Z")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("no pending packet", result.stdout.lower())

    def test_v2_packet_without_freshness_is_watched_for_git_drift_only(self) -> None:
        self._write("deploy/checkout.yaml", "name: checkout\nreplicas: 3\n")
        self._commit("scale checkout")
        packet = self._packet()
        del packet["freshness"]
        packet["schema_version"] = 2
        self.packet_path.write_text(json.dumps(packet), encoding="utf-8")

        result = self._run("--now", "2030-01-01T00:00:00Z")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("deploy/checkout.yaml", result.stdout)
        self.assertNotIn("expired", result.stdout.lower())

    def test_json_output_is_machine_readable(self) -> None:
        self._write("deploy/checkout.yaml", "name: checkout\nreplicas: 3\n")
        self._commit("scale checkout")
        self._packet()

        result = self._run("--json")
        self.assertEqual(0, result.returncode, result.stderr)
        findings = json.loads(result.stdout)
        self.assertEqual(1, len(findings))
        self.assertEqual("ku_checkout_application_approved", findings[0]["update_id"])
        self.assertEqual(["deploy/checkout.yaml"], findings[0]["drifted_paths"])
        self.assertEqual(1, findings[0]["commit_count"])
        self.assertEqual([], findings[0]["unwatchable_locators"])

    def test_one_unreadable_packet_does_not_discard_the_rest_of_the_batch(self) -> None:
        """A nightly sweep passes many packets. One corrupt file must not bury the genuine
        review prompts already computed for every other packet — it must be reported alongside
        them, with the run still exiting 2 so the corruption is never mistaken for a clean pass."""
        self._write("deploy/checkout.yaml", "name: checkout\nreplicas: 3\n")
        self._commit("scale checkout")
        self._packet()
        broken = self.packet_path.parent / "broken.json"
        broken.write_text("{not json", encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                str(WATCH_PATH),
                str(broken),
                str(self.packet_path),
                "--root",
                str(self.repository),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        self.assertEqual(2, result.returncode)
        self.assertIn("packet_drift:", result.stderr)
        # The healthy packet's finding survives the unreadable one.
        self.assertIn("ku_checkout_application_approved", result.stdout)
        self.assertIn("deploy/checkout.yaml", result.stdout)

    def test_json_commit_list_is_not_silently_truncated(self) -> None:
        """commit_count counts distinct SHAs while commits holds (path, commit) pairs, so a
        consumer cannot infer truncation by comparing their lengths. Either every commit is
        present or the payload says outright that some were dropped."""
        for index in range(7):
            self._write("deploy/checkout.yaml", f"name: checkout\nreplicas: {index}\n")
            self._commit(f"scale checkout {index}")
        self._packet()

        findings = json.loads(self._run("--json").stdout)
        self.assertEqual(7, findings[0]["commit_count"])
        self.assertEqual(7, len(findings[0]["commits"]))
        self.assertFalse(findings[0]["commits_truncated"])

    def test_malformed_packet_exits_two(self) -> None:
        self.packet_path.write_text("{not json", encoding="utf-8")
        result = self._run()
        self.assertEqual(2, result.returncode)
        self.assertIn("packet_drift:", result.stderr)


if __name__ == "__main__":
    unittest.main()
