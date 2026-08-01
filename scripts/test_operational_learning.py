"""Contract tests for the evidence-bound operational learning loop."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "skills/operational-learning/scripts/knowledge_update.py"
SPEC = importlib.util.spec_from_file_location("knowledge_update", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import machinery failure
    raise RuntimeError(f"cannot load {VALIDATOR_PATH}")
knowledge_update = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(knowledge_update)


class OperationalLearningBaselineTests(unittest.TestCase):
    ARTIFACT_CONTENT = b"# Checkout pool alert\n"
    ARTIFACT_SHA256 = hashlib.sha256(ARTIFACT_CONTENT).hexdigest()
    EXISTING_CONTENT = b"# Existing alert card\n"
    EXISTING_SHA256 = hashlib.sha256(EXISTING_CONTENT).hexdigest()

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.target_root = Path(self.temporary.name)
        existing = self.target_root / "docs/operations/alerts/existing.md"
        existing.parent.mkdir(parents=True)
        existing.write_bytes(self.EXISTING_CONTENT)
        (self.target_root / ".gitattributes").write_text(
            "*.md text eol=lf\n",
            encoding="utf-8",
        )
        (self.target_root / ".gitignore").write_text(
            "docs/operations/alerts/ignored.md\n"
            "docs/operations/alerts/[[]x].md\n",
            encoding="utf-8",
        )
        subprocess.run(
            ["git", "init", "--quiet", str(self.target_root)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(self.target_root),
                "add",
                "--",
                ".gitattributes",
                ".gitignore",
                "docs/operations/alerts/existing.md",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(self.target_root),
                "-c",
                "user.name=Operational Learning Tests",
                "-c",
                "user.email=tests@example.invalid",
                "commit",
                "--quiet",
                "-m",
                "base",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.base_revision = subprocess.run(
            ["git", "-C", str(self.target_root), "rev-parse", "HEAD"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        ).stdout.strip()
        artifact = self.target_root / "docs/operations/alerts/checkout-pool.md"
        artifact.write_bytes(self.ARTIFACT_CONTENT)

    def _validate(self, packet: dict[str, object]) -> None:
        knowledge_update.validate_update(packet, target_root=self.target_root)

    def _valid_update(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "update_id": "ku_checkout_pool_alert",
            "created_at": "2026-08-01T12:00:00Z",
            "target": {
                "repository": "latent-sre/checkout",
                "revision": self.base_revision,
                "service": "checkout",
                "knowledge_roots": ["docs"],
            },
            "trigger": {
                "kind": "alert_added",
                "reference": "alerts/checkout-pool.yaml",
                "state": "approved",
                "trust": "trusted",
            },
            "discovery": {
                "summary": "A pool-saturation alert exists but its runbook link is missing.",
                "evidence_status": "sourced",
                "evidence_ids": ["e1", "e2"],
            },
            "evidence": [
                {
                    "id": "e1",
                    "label": "sourced",
                    "kind": "repository",
                    "locator": "alerts/checkout-pool.yaml",
                    "revision": self.base_revision,
                    "trust": "trusted",
                },
                {
                    "id": "e2",
                    "label": "verified",
                    "kind": "approval",
                    "locator": "review OPS-882",
                    "revision": self.base_revision,
                    "trust": "trusted",
                },
            ],
            "dispositions": [
                {
                    "artifact": "alert_card",
                    "action": "create",
                    "status": "prepared",
                    "owner": "scribe",
                    "path": "docs/operations/alerts/checkout-pool.md",
                    "duplicate_of": None,
                    "base_sha256": None,
                    "artifact_sha256": self.ARTIFACT_SHA256,
                    "reason": "The approved alert needs a durable KB record.",
                    "evidence_ids": ["e1"],
                },
                {
                    "artifact": "runbook",
                    "action": "handoff",
                    "status": "proposed",
                    "owner": "scribe",
                    "path": None,
                    "duplicate_of": None,
                    "base_sha256": None,
                    "artifact_sha256": None,
                    "reason": "The paging alert has no runbook target.",
                    "evidence_ids": ["e1", "e2"],
                },
            ],
            "recommendation": {
                "summary": "Keep the alert proposed until its runbook is reviewed and linked.",
                "owner": "sre-steward",
                "urgency": "next",
                "change_tier": 1,
                "requires_human_approval": False,
                "verification": "Review the alert, card, and runbook links in the same pull request.",
                "rollback": None,
            },
            "limitations": ["The alert has not fired against production traffic."],
        }

    def _assert_hidden_worktree_divergence_rejected(self, index_flag: str) -> None:
        existing = self.target_root / "docs/operations/alerts/existing.md"
        existing.write_bytes(b"# Staged alert card\n")
        subprocess.run(
            [
                "git",
                "-C",
                str(self.target_root),
                "add",
                "--",
                "docs/operations/alerts/existing.md",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(self.target_root),
                "update-index",
                index_flag,
                "docs/operations/alerts/existing.md",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        working_content = b"# Different hidden working-tree card\n"
        existing.write_bytes(working_content)
        packet = self._valid_update()
        packet["dispositions"][0].update(  # type: ignore[index]
            {
                "action": "update",
                "path": "docs/operations/alerts/existing.md",
                "base_sha256": self.EXISTING_SHA256,
                "artifact_sha256": hashlib.sha256(working_content).hexdigest(),
            }
        )
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "not exposed as a tracked modification",
        ):
            self._validate(packet)

    def _duplicate_update(self, duplicate_of: str | None) -> dict[str, object]:
        packet = self._valid_update()
        packet["dispositions"][0].update(  # type: ignore[index]
            {
                "action": "none",
                "status": "duplicate",
                "path": None,
                "duplicate_of": duplicate_of,
                "base_sha256": None,
                "artifact_sha256": None,
                "evidence_ids": ["e1"],
            }
        )
        if duplicate_of is not None:
            packet["evidence"][0]["locator"] = duplicate_of  # type: ignore[index]
        return packet

    def test_learning_skill_schema_and_assets_exist(self) -> None:
        required = (
            Path("skills/operational-learning/SKILL.md"),
            Path("skills/operational-learning/references/disposition-policy.md"),
            Path("skills/operational-learning/assets/service-card-template.md"),
            Path("skills/operational-learning/assets/alert-card-template.md"),
            Path("skills/operational-learning/assets/knowledge-index-template.md"),
            Path("skills/operational-learning/assets/knowledge-update-v1.schema.json"),
            Path("skills/operational-learning/scripts/knowledge_update.py"),
        )
        for relative in required:
            with self.subTest(path=relative.as_posix()):
                self.assertTrue((ROOT / relative).is_file(), f"missing {relative.as_posix()}")

    def test_scribe_has_a_knowledge_closeout_mode(self) -> None:
        scribe = (ROOT / "agents/scribe.md").read_text(encoding="utf-8")
        self.assertIn("Knowledge closeout mode", scribe)
        self.assertIn("operational-learning", scribe)
        self.assertIn("service card", scribe)
        self.assertIn("alert card", scribe)

    def test_operational_producers_emit_learning_dispositions(self) -> None:
        for relative in (
            Path("agents/sre.md"),
            Path("agents/sre-steward.md"),
            Path("skills/service-onboarding/SKILL.md"),
        ):
            with self.subTest(path=relative.as_posix()):
                text = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIn("learning disposition", text.lower())

    def test_valid_packet_round_trips_canonical_json(self) -> None:
        packet = self._valid_update()
        self._validate(packet)
        self.assertEqual(
            b'{"a":"\xc3\xa9","b":1}',
            knowledge_update.canonical_json({"b": 1, "a": "é"}),
        )
        self.assertEqual(
            packet,
            json.loads(knowledge_update.canonical_json(packet).decode("utf-8")),
        )

        boolean_version = self._valid_update()
        boolean_version["schema_version"] = True
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "unsupported schema_version",
        ):
            self._validate(boolean_version)

    def test_created_at_requires_rfc3339_t_separator(self) -> None:
        packet = self._valid_update()
        packet["created_at"] = "2026-08-01 12:00:00Z"
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "RFC3339 UTC timestamp ending in Z",
        ):
            self._validate(packet)

    def test_evidence_label_cannot_upgrade_weakest_source(self) -> None:
        packet = self._valid_update()
        packet["discovery"]["evidence_status"] = "verified"  # type: ignore[index]
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "weakest referenced evidence label",
        ):
            self._validate(packet)

    def test_active_incident_cannot_prepare_documentation(self) -> None:
        packet = self._valid_update()
        packet["trigger"]["kind"] = "incident"  # type: ignore[index]
        packet["trigger"]["state"] = "active"  # type: ignore[index]
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "cannot mark dispositions prepared",
        ):
            self._validate(packet)

    def test_trigger_lifecycle_and_approval_evidence_fail_closed(self) -> None:
        mismatched = self._valid_update()
        mismatched["trigger"]["kind"] = "incident"  # type: ignore[index]
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "invalid for kind 'incident'",
        ):
            self._validate(mismatched)

        proposed = self._valid_update()
        proposed["trigger"]["state"] = "proposed"  # type: ignore[index]
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "cannot mark dispositions prepared",
        ):
            self._validate(proposed)

        untrusted_approval = self._valid_update()
        untrusted_approval["evidence"][1]["trust"] = "untrusted"  # type: ignore[index]
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "trusted approval record",
        ):
            self._validate(untrusted_approval)

        stale_approval = self._valid_update()
        stale_approval["evidence"][1]["revision"] = "b" * 40  # type: ignore[index]
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "trusted approval record bound to target.revision",
        ):
            self._validate(stale_approval)

        resolved_without_incident_record = self._valid_update()
        resolved_without_incident_record["trigger"].update(  # type: ignore[union-attr]
            {"kind": "incident", "state": "resolved", "reference": "INC-882"}
        )
        resolved_without_incident_record["evidence"][1]["kind"] = "human_record"  # type: ignore[index]
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "requires referenced trusted evidence of kind.*incident",
        ):
            self._validate(resolved_without_incident_record)

    def test_target_revision_binding_is_required(self) -> None:
        unbound_discovery = self._valid_update()
        unbound_discovery["evidence"][0]["revision"] = "b" * 40  # type: ignore[index]
        unbound_discovery["evidence"][1]["revision"] = "b" * 40  # type: ignore[index]
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "discovery must reference evidence bound to target.revision",
        ):
            self._validate(unbound_discovery)

        unbound_prepared_change = self._valid_update()
        unbound_prepared_change["evidence"].append(  # type: ignore[union-attr]
            {
                "id": "e3",
                "label": "sourced",
                "kind": "repository",
                "locator": "older alert definition",
                "revision": "b" * 40,
                "trust": "trusted",
            }
        )
        unbound_prepared_change["dispositions"][0]["evidence_ids"] = ["e3"]  # type: ignore[index]
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "prepared change must reference evidence for target.revision",
        ):
            self._validate(unbound_prepared_change)

    def test_prepared_artifact_requires_existing_digest_bound_bytes(self) -> None:
        packet = self._valid_update()
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "prepared dispositions require target_root",
        ):
            knowledge_update.validate_update(packet)

        wrong_digest = self._valid_update()
        wrong_digest["dispositions"][0]["artifact_sha256"] = "0" * 64  # type: ignore[index]
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "prepared artifact digest mismatch",
        ):
            self._validate(wrong_digest)

        missing_artifact = self._valid_update()
        missing_artifact["dispositions"][0]["path"] = (  # type: ignore[index]
            "docs/operations/alerts/missing.md"
        )
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "prepared artifact does not exist",
        ):
            self._validate(missing_artifact)

    def test_prepared_transition_is_a_real_diff_from_target_revision(self) -> None:
        wrong_checkout_revision = self._valid_update()
        wrong_checkout_revision["target"]["revision"] = "b" * 40  # type: ignore[index]
        wrong_checkout_revision["evidence"][0]["revision"] = "b" * 40  # type: ignore[index]
        wrong_checkout_revision["evidence"][1]["revision"] = "b" * 40  # type: ignore[index]
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "target_root HEAD does not match target.revision",
        ):
            self._validate(wrong_checkout_revision)

        unchanged_update = self._valid_update()
        unchanged_update["dispositions"][0].update(  # type: ignore[index]
            {
                "action": "update",
                "path": "docs/operations/alerts/existing.md",
                "base_sha256": self.EXISTING_SHA256,
                "artifact_sha256": self.EXISTING_SHA256,
            }
        )
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "has no reviewable byte change",
        ):
            self._validate(unchanged_update)

        create_over_existing = self._valid_update()
        create_over_existing["dispositions"][0].update(  # type: ignore[index]
            {
                "action": "create",
                "path": "docs/operations/alerts/existing.md",
                "base_sha256": None,
                "artifact_sha256": self.EXISTING_SHA256,
            }
        )
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "prepared create path already exists",
        ):
            self._validate(create_over_existing)

        updated_content = b"# Existing alert card\n\nApproved update.\n"
        updated_sha256 = hashlib.sha256(updated_content).hexdigest()
        (self.target_root / "docs/operations/alerts/existing.md").write_bytes(updated_content)
        valid_update = self._valid_update()
        valid_update["dispositions"][0].update(  # type: ignore[index]
            {
                "action": "update",
                "path": "docs/operations/alerts/existing.md",
                "base_sha256": self.EXISTING_SHA256,
                "artifact_sha256": updated_sha256,
            }
        )
        self._validate(valid_update)

    def test_git_reviewability_respects_text_normalization_and_ignore_rules(self) -> None:
        crlf_content = self.EXISTING_CONTENT.replace(b"\n", b"\r\n")
        crlf_sha256 = hashlib.sha256(crlf_content).hexdigest()
        (self.target_root / "docs/operations/alerts/existing.md").write_bytes(crlf_content)
        normalized_only = self._valid_update()
        normalized_only["dispositions"][0].update(  # type: ignore[index]
            {
                "action": "update",
                "path": "docs/operations/alerts/existing.md",
                "base_sha256": self.EXISTING_SHA256,
                "artifact_sha256": crlf_sha256,
            }
        )
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "has no Git-reviewable change",
        ):
            self._validate(normalized_only)

        ignored_content = b"# Ignored alert card\n"
        ignored_sha256 = hashlib.sha256(ignored_content).hexdigest()
        (self.target_root / "docs/operations/alerts/ignored.md").write_bytes(ignored_content)
        ignored_create = self._valid_update()
        ignored_create["dispositions"][0].update(  # type: ignore[index]
            {
                "action": "create",
                "path": "docs/operations/alerts/ignored.md",
                "base_sha256": None,
                "artifact_sha256": ignored_sha256,
            }
        )
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "has no Git-reviewable change",
        ):
            self._validate(ignored_create)

    def test_prepared_update_rejects_staged_delete_with_untracked_replacement(self) -> None:
        existing = self.target_root / "docs/operations/alerts/existing.md"
        subprocess.run(
            [
                "git",
                "-C",
                str(self.target_root),
                "rm",
                "--quiet",
                "--",
                "docs/operations/alerts/existing.md",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        existing.parent.mkdir(parents=True, exist_ok=True)
        updated_content = b"# Untracked replacement after staged deletion\n"
        existing.write_bytes(updated_content)
        packet = self._valid_update()
        packet["dispositions"][0].update(  # type: ignore[index]
            {
                "action": "update",
                "path": "docs/operations/alerts/existing.md",
                "base_sha256": self.EXISTING_SHA256,
                "artifact_sha256": hashlib.sha256(updated_content).hexdigest(),
            }
        )
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "not exposed as a tracked modification",
        ):
            self._validate(packet)

    def test_prepared_update_rejects_staged_rename_with_untracked_replacement(self) -> None:
        existing = self.target_root / "docs/operations/alerts/existing.md"
        subprocess.run(
            [
                "git",
                "-C",
                str(self.target_root),
                "mv",
                "--",
                "docs/operations/alerts/existing.md",
                "docs/operations/alerts/moved.md",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        updated_content = b"# Untracked replacement after staged rename\n"
        existing.write_bytes(updated_content)
        packet = self._valid_update()
        packet["dispositions"][0].update(  # type: ignore[index]
            {
                "action": "link",
                "path": "docs/operations/alerts/existing.md",
                "base_sha256": self.EXISTING_SHA256,
                "artifact_sha256": hashlib.sha256(updated_content).hexdigest(),
            }
        )
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "not exposed as a tracked modification",
        ):
            self._validate(packet)

    def test_prepared_create_accepts_an_exact_staged_addition(self) -> None:
        subprocess.run(
            [
                "git",
                "-C",
                str(self.target_root),
                "add",
                "--",
                "docs/operations/alerts/checkout-pool.md",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._validate(self._valid_update())

    def test_prepared_update_binds_assume_unchanged_worktree_bytes(self) -> None:
        self._assert_hidden_worktree_divergence_rejected("--assume-unchanged")

    def test_prepared_update_binds_skip_worktree_bytes(self) -> None:
        self._assert_hidden_worktree_divergence_rejected("--skip-worktree")

    def test_prepared_update_accepts_matching_staged_bytes(self) -> None:
        updated_content = b"# Staged and reviewable alert card\n"
        (self.target_root / "docs/operations/alerts/existing.md").write_bytes(updated_content)
        subprocess.run(
            [
                "git",
                "-C",
                str(self.target_root),
                "add",
                "--",
                "docs/operations/alerts/existing.md",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        packet = self._valid_update()
        packet["dispositions"][0].update(  # type: ignore[index]
            {
                "action": "update",
                "path": "docs/operations/alerts/existing.md",
                "base_sha256": self.EXISTING_SHA256,
                "artifact_sha256": hashlib.sha256(updated_content).hexdigest(),
            }
        )
        self._validate(packet)

    def test_git_reviewability_rejects_external_clean_filters(self) -> None:
        attributes = self.target_root / ".gitattributes"
        attributes.write_text(
            "*.md text eol=lf\n"
            "docs/operations/alerts/existing.md filter=knowledge-test\n",
            encoding="utf-8",
        )
        updated_content = b"# Existing alert card\n\nApproved update.\n"
        updated_sha256 = hashlib.sha256(updated_content).hexdigest()
        (self.target_root / "docs/operations/alerts/existing.md").write_bytes(updated_content)
        packet = self._valid_update()
        packet["dispositions"][0].update(  # type: ignore[index]
            {
                "action": "update",
                "path": "docs/operations/alerts/existing.md",
                "base_sha256": self.EXISTING_SHA256,
                "artifact_sha256": updated_sha256,
            }
        )
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "external clean filter",
        ):
            self._validate(packet)

    def test_git_reviewability_uses_literal_pathspecs_and_exact_untracked_output(self) -> None:
        intended_content = b"# Ignored literal pathspec card\n"
        intended_sha256 = hashlib.sha256(intended_content).hexdigest()
        (self.target_root / "docs/operations/alerts/[x].md").write_bytes(intended_content)
        (self.target_root / "docs/operations/alerts/x.md").write_bytes(b"# Unrelated card\n")
        packet = self._valid_update()
        packet["dispositions"][0].update(  # type: ignore[index]
            {
                "action": "create",
                "path": "docs/operations/alerts/[x].md",
                "base_sha256": None,
                "artifact_sha256": intended_sha256,
            }
        )
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "has no Git-reviewable change",
        ):
            self._validate(packet)

    def test_ambiguous_filter_names_are_forced_to_safe_no_ops(self) -> None:
        updated_content = b"# Existing alert card\n\nApproved update.\n"
        updated_sha256 = hashlib.sha256(updated_content).hexdigest()
        (self.target_root / "docs/operations/alerts/existing.md").write_bytes(updated_content)
        for filter_name in ("unspecified", "unset"):
            with self.subTest(filter_name=filter_name):
                (self.target_root / ".gitattributes").write_text(
                    "*.md text eol=lf\n"
                    f"docs/operations/alerts/existing.md filter={filter_name}\n",
                    encoding="utf-8",
                )
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(self.target_root),
                        "config",
                        f"filter.{filter_name}.clean",
                        "definitely-not-an-operational-learning-command",
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                subprocess.run(
                    [
                        "git",
                        "-C",
                        str(self.target_root),
                        "config",
                        f"filter.{filter_name}.required",
                        "true",
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                packet = self._valid_update()
                packet["dispositions"][0].update(  # type: ignore[index]
                    {
                        "action": "update",
                        "path": "docs/operations/alerts/existing.md",
                        "base_sha256": self.EXISTING_SHA256,
                        "artifact_sha256": updated_sha256,
                    }
                )
                self._validate(packet)

    def test_local_git_inspection_scrubs_ambient_git_and_ssh_controls(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "GIT_DIR": "outside",
                "GIT_WORK_TREE": "outside",
                "GIT_CONFIG_COUNT": "1",
                "SSH_AUTH_SOCK": "credential-socket",
                "KEEP_ME": "yes",
            },
            clear=True,
        ):
            environment = knowledge_update._git_environment()
        self.assertEqual("yes", environment["KEEP_ME"])
        self.assertNotIn("GIT_DIR", environment)
        self.assertNotIn("GIT_WORK_TREE", environment)
        self.assertNotIn("GIT_CONFIG_COUNT", environment)
        self.assertNotIn("SSH_AUTH_SOCK", environment)
        self.assertEqual("1", environment["GIT_NO_LAZY_FETCH"])
        self.assertEqual("1", environment["GIT_NO_REPLACE_OBJECTS"])
        self.assertEqual("1", environment["GIT_CONFIG_NOSYSTEM"])
        self.assertEqual(os.devnull, environment["GIT_CONFIG_GLOBAL"])
        self.assertEqual("1", environment["GIT_ATTR_NOSYSTEM"])
        self.assertEqual("1", environment["GIT_LITERAL_PATHSPECS"])
        self.assertEqual("0", environment["GIT_TERMINAL_PROMPT"])
        self.assertEqual("0", environment["GIT_OPTIONAL_LOCKS"])

    def test_bundled_validator_cli_verifies_prepared_artifacts(self) -> None:
        packet_path = self.target_root / "knowledge-update.json"
        packet_path.write_text(json.dumps(self._valid_update()), encoding="utf-8")
        valid = subprocess.run(
            [
                sys.executable,
                str(VALIDATOR_PATH),
                str(packet_path),
                "--target-root",
                str(self.target_root),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        self.assertEqual(0, valid.returncode, valid.stderr)
        self.assertIn("Valid operational knowledge update", valid.stdout)

        missing_root = subprocess.run(
            [sys.executable, str(VALIDATOR_PATH), str(packet_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        self.assertEqual(1, missing_root.returncode)
        self.assertIn("prepared dispositions require target_root", missing_root.stderr)

    def test_tier_two_and_three_require_approval_and_rollback(self) -> None:
        for tier in (2, 3):
            with self.subTest(tier=tier):
                packet = self._valid_update()
                packet["recommendation"]["change_tier"] = tier  # type: ignore[index]
                packet["recommendation"]["requires_human_approval"] = False  # type: ignore[index]
                with self.assertRaisesRegex(
                    knowledge_update.KnowledgeUpdateValidationError,
                    "require human approval",
                ):
                    self._validate(packet)

    def test_scribe_cannot_prepare_non_documentation_effects(self) -> None:
        for artifact in ("observability", "automation", "code", "accepted_risk"):
            with self.subTest(artifact=artifact):
                packet = self._valid_update()
                packet["dispositions"][0].update(  # type: ignore[index]
                    {
                        "artifact": artifact,
                        "action": "update",
                        "status": "prepared",
                        "path": "src/change.txt",
                    }
                )
                with self.assertRaisesRegex(
                    knowledge_update.KnowledgeUpdateValidationError,
                    "cannot be prepared by scribe",
                ):
                    self._validate(packet)

        invalid_handoff = self._valid_update()
        invalid_handoff["dispositions"][0].update(  # type: ignore[index]
            {
                "artifact": "code",
                "action": "update",
                "status": "proposed",
                "path": "src/app.py",
            }
        )
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "requires a pathless handoff",
        ):
            self._validate(invalid_handoff)

        invalid_document_proposal = self._valid_update()
        invalid_document_proposal["dispositions"][0].update(  # type: ignore[index]
            {
                "artifact": "runbook",
                "action": "update",
                "status": "proposed",
                "path": "docs/runbooks/checkout.md",
            }
        )
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "requires a pathless handoff",
        ):
            self._validate(invalid_document_proposal)

    def test_paths_references_and_disposition_transitions_fail_closed(self) -> None:
        unsafe = self._valid_update()
        unsafe["dispositions"][0]["path"] = "../outside.md"  # type: ignore[index]
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "repository-relative POSIX path",
        ):
            self._validate(unsafe)

        noncanonical = self._valid_update()
        noncanonical["dispositions"][0]["path"] = "docs//operations/alerts/card.md"  # type: ignore[index]
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "normalized repository-relative POSIX path",
        ):
            self._validate(noncanonical)

        outside_knowledge_root = self._valid_update()
        outside_knowledge_root["dispositions"][0]["path"] = (  # type: ignore[index]
            "runbooks/checkout.md"
        )
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "outside target.knowledge_roots",
        ):
            self._validate(outside_knowledge_root)

        non_document = self._valid_update()
        non_document["dispositions"][0]["path"] = "docs/.env"  # type: ignore[index]
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "must name a documentation file",
        ):
            self._validate(non_document)

        unknown_evidence = self._valid_update()
        unknown_evidence["dispositions"][0]["evidence_ids"] = ["e99"]  # type: ignore[index]
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "unknown evidence ids",
        ):
            self._validate(unknown_evidence)

        invalid_transition = self._valid_update()
        invalid_transition["dispositions"][0]["action"] = "none"  # type: ignore[index]
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "prepared disposition requires",
        ):
            self._validate(invalid_transition)

        duplicate_create = self._valid_update()
        duplicate_create["dispositions"][0].update(  # type: ignore[index]
            {"status": "duplicate", "action": "create"}
        )
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "duplicate disposition requires action none",
        ):
            self._validate(duplicate_create)

        not_applicable_update = self._valid_update()
        not_applicable_update["dispositions"][0].update(  # type: ignore[index]
            {"status": "not_applicable", "action": "update"}
        )
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "not_applicable disposition requires action none",
        ):
            self._validate(not_applicable_update)

    def test_documentation_duplicate_is_exact_revision_bound_and_existing(self) -> None:
        existing = "docs/operations/alerts/existing.md"
        self._validate(self._duplicate_update(existing))

        missing_locator = self._duplicate_update(None)
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "requires duplicate_of",
        ):
            self._validate(missing_locator)

        missing_artifact = self._duplicate_update("docs/operations/alerts/missing-duplicate.md")
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "duplicate_of does not exist at target.revision",
        ):
            self._validate(missing_artifact)

        outside_root = self._duplicate_update("runbooks/existing.md")
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "duplicate_of is outside target.knowledge_roots",
        ):
            self._validate(outside_root)

        stale_evidence = self._duplicate_update(existing)
        stale_evidence["evidence"][0]["revision"] = "b" * 40  # type: ignore[index]
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "duplicate_of requires matching trusted.*target.revision",
        ):
            self._validate(stale_evidence)

        wrong_evidence_kind = self._duplicate_update(existing)
        wrong_evidence_kind["evidence"][0]["kind"] = "ticket"  # type: ignore[index]
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "documentation duplicate_of requires matching repository evidence",
        ):
            self._validate(wrong_evidence_kind)

        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "documentation duplicate dispositions require target_root",
        ):
            knowledge_update.validate_update(self._duplicate_update(existing))

    def test_credential_shaped_content_and_unknown_fields_are_rejected(self) -> None:
        secret = self._valid_update()
        secret["limitations"].append("password=hunter2")  # type: ignore[union-attr]
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "credential-bearing",
        ):
            self._validate(secret)

        embedded_uri_secret = self._valid_update()
        embedded_uri_secret["limitations"].append(  # type: ignore[union-attr]
            "Do not copy see https://operator:password@example.invalid/path"
        )
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "credential-bearing",
        ):
            self._validate(embedded_uri_secret)

        unknown = self._valid_update()
        unknown["confidence"] = "high"
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "unknown knowledge update fields",
        ):
            self._validate(unknown)

    def test_structured_credentials_are_rejected_in_packets_and_artifacts(self) -> None:
        credential_samples = {
            "pem-private-key": "-----BEGIN OPENSSH PRIVATE KEY-----",
            "pgp-private-key": "-----BEGIN PGP PRIVATE KEY BLOCK-----",
            "aws-secret-assignment": "AWS_SECRET_ACCESS_KEY=fakeSecretValue1234567890",
            "json-secret-assignment": '"client_secret": "fakeClientSecret1234567890"',
            "bearer": "Bearer fakeBearerTokenValue1234567890",
            "jwt": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.c2lnbmF0dXJlMTIz",
            "github": "ghp_" + "a" * 32,
            "aws-access-key": "AKIA" + "A" * 16,
            "slack": "xoxb-1234567890-abcdefghijk",
            "google-api": "AIza" + "a" * 35,
            "stripe": "sk_live_" + "a" * 24,
            "redaction-prefix-cannot-hide-assignment": (
                "token=[REDACTED:token]still-secret"
            ),
            "redaction-prefix-cannot-hide-uri-secret": (
                "https://operator:[REDACTED:password]still-secret@example.invalid"
            ),
        }
        artifact = self.target_root / "docs/operations/alerts/checkout-pool.md"
        for label, sample in credential_samples.items():
            with self.subTest(location="packet", credential=label):
                artifact.write_bytes(self.ARTIFACT_CONTENT)
                packet = self._valid_update()
                packet["limitations"].append(sample)  # type: ignore[union-attr]
                with self.assertRaisesRegex(
                    knowledge_update.KnowledgeUpdateValidationError,
                    "credential-bearing",
                ):
                    self._validate(packet)

            with self.subTest(location="artifact", credential=label):
                content = f"# Checkout pool alert\n\n{sample}\n".encode("utf-8")
                artifact.write_bytes(content)
                packet = self._valid_update()
                packet["dispositions"][0]["artifact_sha256"] = hashlib.sha256(  # type: ignore[index]
                    content
                ).hexdigest()
                with self.assertRaisesRegex(
                    knowledge_update.KnowledgeUpdateValidationError,
                    "prepared artifact looks credential-bearing",
                ):
                    self._validate(packet)

        safe_redactions = (
            "AWS_SECRET_ACCESS_KEY=[REDACTED:aws-secret]",
            "Bearer [REDACTED:bearer-token]",
            "github_token=[REDACTED:github-token]",
            '"client_secret": "[REDACTED:client-secret]"',
            "Do not copy https://operator:[REDACTED:password]@example.invalid/path.",
            "The token=[REDACTED:token]. Rotate it through the approved process.",
            "Authorization: Bearer [REDACTED:bearer-token].",
        )
        for redacted in safe_redactions:
            with self.subTest(location="typed-redaction-helper", value=redacted):
                self.assertFalse(knowledge_update._contains_sensitive_text(redacted))

            with self.subTest(location="typed-redaction-packet", value=redacted):
                artifact.write_bytes(self.ARTIFACT_CONTENT)
                packet = self._valid_update()
                packet["limitations"].append(redacted)  # type: ignore[union-attr]
                self._validate(packet)

            with self.subTest(location="typed-redaction-artifact", value=redacted):
                content = f"# Checkout pool alert\n\n{redacted}\n".encode("utf-8")
                artifact.write_bytes(content)
                packet = self._valid_update()
                packet["dispositions"][0]["artifact_sha256"] = hashlib.sha256(  # type: ignore[index]
                    content
                ).hexdigest()
                self._validate(packet)

    def test_prepared_document_content_rejects_credentials_and_non_utf8(self) -> None:
        artifact = self.target_root / "docs/operations/alerts/checkout-pool.md"
        credential_content = b"# Checkout pool alert\n\npassword=hunter2\n"
        artifact.write_bytes(credential_content)
        credential_packet = self._valid_update()
        credential_packet["dispositions"][0]["artifact_sha256"] = hashlib.sha256(  # type: ignore[index]
            credential_content
        ).hexdigest()
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "prepared artifact looks credential-bearing",
        ):
            self._validate(credential_packet)

        non_utf8_content = b"# Checkout pool alert\n\xff\n"
        artifact.write_bytes(non_utf8_content)
        non_utf8_packet = self._valid_update()
        non_utf8_packet["dispositions"][0]["artifact_sha256"] = hashlib.sha256(  # type: ignore[index]
            non_utf8_content
        ).hexdigest()
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "must be UTF-8",
        ):
            self._validate(non_utf8_packet)

    def test_prepared_document_rejects_hard_links(self) -> None:
        artifact = self.target_root / "docs/operations/alerts/checkout-pool.md"
        artifact.unlink()
        source = self.target_root / "hard-link-source.md"
        source.write_bytes(self.ARTIFACT_CONTENT)
        os.link(source, artifact)
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "must not be hard-linked",
        ):
            self._validate(self._valid_update())

    def test_prepared_artifact_is_rechecked_after_git_inspection(self) -> None:
        artifact = self.target_root / "docs/operations/alerts/checkout-pool.md"
        original = knowledge_update._verify_reviewable_diff

        def mutate_after_review(*args: object, **kwargs: object) -> None:
            original(*args, **kwargs)
            artifact.write_bytes(b"# Changed after Git inspection\n")

        with mock.patch.object(
            knowledge_update,
            "_verify_reviewable_diff",
            side_effect=mutate_after_review,
        ), self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "prepared artifact digest mismatch",
        ):
            self._validate(self._valid_update())

    def test_schema_tracks_executable_validator(self) -> None:
        schema = json.loads(
            (
                ROOT
                / "skills/operational-learning/assets/knowledge-update-v1.schema.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(knowledge_update.SCHEMA_VERSION, schema["properties"]["schema_version"]["const"])
        self.assertEqual(knowledge_update.TOP_LEVEL_FIELDS, set(schema["properties"]))
        self.assertEqual(knowledge_update.TOP_LEVEL_FIELDS, set(schema["required"]))
        self.assertEqual(
            knowledge_update.TRIGGER_KINDS,
            set(schema["properties"]["trigger"]["properties"]["kind"]["enum"]),
        )
        self.assertEqual(
            knowledge_update.TRIGGER_STATES,
            set(schema["properties"]["trigger"]["properties"]["state"]["enum"]),
        )
        self.assertEqual(
            knowledge_update.EVIDENCE_KINDS,
            set(schema["$defs"]["evidence"]["properties"]["kind"]["enum"]),
        )
        self.assertEqual(
            knowledge_update.ARTIFACT_KINDS,
            set(schema["$defs"]["disposition"]["properties"]["artifact"]["enum"]),
        )
        self.assertIn(
            "artifact_sha256",
            schema["$defs"]["disposition"]["required"],
        )
        self.assertIn(
            "base_sha256",
            schema["$defs"]["disposition"]["required"],
        )
        self.assertIn(
            "duplicate_of",
            schema["$defs"]["disposition"]["required"],
        )
        self.assertFalse(schema["additionalProperties"])

    def test_templates_do_not_claim_human_review_or_verification(self) -> None:
        templates = (
            Path("skills/runbook/assets/runbook-template.md"),
            Path("skills/postmortem/assets/postmortem-template.md"),
            Path("skills/operational-learning/assets/service-card-template.md"),
            Path("skills/operational-learning/assets/alert-card-template.md"),
            Path("skills/operational-learning/assets/knowledge-index-template.md"),
        )
        for relative in templates:
            with self.subTest(path=relative.as_posix()):
                rendered = (ROOT / relative).read_text(encoding="utf-8")
                self.assertIn("last_reviewed: null", rendered)
        runbook = (ROOT / templates[0]).read_text(encoding="utf-8")
        self.assertIn("last_verified: null", runbook)


if __name__ == "__main__":
    unittest.main()
