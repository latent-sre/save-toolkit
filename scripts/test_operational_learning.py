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
MIGRATION_PATH = ROOT / "skills/operational-learning/scripts/migrate_v1_to_v2.py"
MIGRATION_V3_PATH = ROOT / "skills/operational-learning/scripts/migrate_v2_to_v3.py"
SPEC = importlib.util.spec_from_file_location("knowledge_update", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import machinery failure
    raise RuntimeError(f"cannot load {VALIDATOR_PATH}")
knowledge_update = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(knowledge_update)


def _approved_artifact_rules(rules: list[dict]) -> dict[tuple[str, str], set[str]]:
    """Index a schema's top-level allOf by the artifacts each approved trigger kind must carry."""

    encoded: dict[tuple[str, str], set[str]] = {}
    for rule in rules:
        trigger_properties = (
            rule.get("if", {})
            .get("properties", {})
            .get("trigger", {})
            .get("properties", {})
        )
        kind_rule = trigger_properties.get("kind", {})
        state_rule = trigger_properties.get("state", {})
        disposition_rule = rule.get("then", {}).get("properties", {}).get("dispositions", {})
        if state_rule.get("const") == "approved" and "enum" in kind_rule:
            artifacts = {
                constraint["contains"]["properties"]["artifact"]["const"]
                for constraint in disposition_rule.get("allOf", [])
            }
            for trigger_kind in kind_rule["enum"]:
                encoded[(trigger_kind, "approved")] = artifacts
    return encoded


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
        knowledge_update.validate_update(
            packet,
            target_root=self.target_root,
            allowed_knowledge_roots=("docs",),
        )

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
                {
                    "artifact": "service_card",
                    "action": "handoff",
                    "status": "proposed",
                    "owner": "scribe",
                    "path": None,
                    "duplicate_of": None,
                    "base_sha256": None,
                    "artifact_sha256": None,
                    "reason": "Link the approved alert from the service card.",
                    "evidence_ids": ["e1", "e2"],
                },
            ],
            "recommendation": {
                "summary": "Keep the alert proposed until its runbook is reviewed and linked.",
                "owner": "observability-engineer",
                "urgency": "next",
                "change_tier": 1,
                "requires_human_approval": False,
                "verification": "Review the alert, card, and runbook links in the same pull request.",
                "rollback": None,
            },
            "limitations": ["The alert has not fired against production traffic."],
        }

    def _valid_v2_application_update(self) -> dict[str, object]:
        packet = self._valid_update()
        packet["schema_version"] = 2
        packet["target"] = {
            "repository": "latent-sre/checkout",
            "revision": self.base_revision,
            "component_id": "checkout",
            "component_kind": "application",
            "display_name": "Checkout",
            "environment": "production",
            "definition_locator": "deploy/checkout.yaml",
            "knowledge_roots": ["docs"],
        }
        packet["trigger"]["kind"] = "component_added"  # type: ignore[index]
        for disposition, artifact in zip(  # type: ignore[assignment]
            packet["dispositions"],
            ("service_card", "knowledge_index", "runbook"),
            strict=True,
        ):
            disposition.update(
                {
                    "artifact": artifact,
                    "action": "handoff",
                    "status": "proposed",
                    "path": None,
                    "duplicate_of": None,
                    "base_sha256": None,
                    "artifact_sha256": None,
                    "evidence_ids": ["e1", "e2"],
                }
            )
        return packet

    def _valid_v3_application_update(self) -> dict[str, object]:
        packet = self._valid_v2_application_update()
        packet["schema_version"] = 3
        packet["freshness"] = {
            "review_at": "2026-11-01T00:00:00Z",
            "expires_at": "2027-02-01T00:00:00Z",
        }
        return packet

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

    def _assert_entrypoint_rejects_non_object_json(self, migration: Path) -> None:
        """Drive one migration CLI's main() with every non-object JSON type.

        The exit status proves nothing on its own: with main()'s isinstance check deleted,
        each of these inputs still exits 1 -- v2-to-v3 through "migration requires
        schema_version 2", v1-to-v2 through a field-set error for the iterable values and an
        uncaught TypeError for the rest. Only the documented stderr line, and the absence of
        any migrated bytes, tell the check apart from whatever error happens to come next.
        """

        packet_path = self.target_root / "non-object.json"
        output_path = self.target_root / "migrated.json"
        for value in ([], "packet", 3, None, True):
            with self.subTest(value=value):
                packet_path.write_text(json.dumps(value), encoding="utf-8")
                result = subprocess.run(
                    [
                        sys.executable,
                        str(migration),
                        str(packet_path),
                        "--output",
                        str(output_path),
                        "--target-root",
                        str(self.target_root),
                        "--allowed-knowledge-root",
                        "docs",
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False,
                )
                self.assertEqual(1, result.returncode, result.stderr)
                self.assertEqual(
                    "migration failed: knowledge update must be a JSON object",
                    result.stderr.strip(),
                )
                self.assertEqual("", result.stdout)
                self.assertFalse(output_path.exists())

    def test_learning_skill_schema_and_assets_exist(self) -> None:
        required = (
            Path("skills/operational-learning/SKILL.md"),
            Path("skills/operational-learning/references/disposition-policy.md"),
            Path("skills/operational-learning/assets/service-card-template.md"),
            Path("skills/operational-learning/assets/alert-card-template.md"),
            Path("skills/operational-learning/assets/knowledge-index-template.md"),
            Path("skills/operational-learning/assets/knowledge-update-v1.schema.json"),
            Path("skills/operational-learning/assets/knowledge-update-v2.schema.json"),
            Path("skills/operational-learning/assets/knowledge-update-v3.schema.json"),
            Path("skills/operational-learning/assets/examples/knowledge-update-v1-service.json"),
            Path("skills/operational-learning/assets/examples/knowledge-update-v2-application.json"),
            Path("skills/operational-learning/assets/examples/knowledge-update-v3-application.json"),
            Path("skills/operational-learning/scripts/knowledge_update.py"),
            Path("skills/operational-learning/scripts/migrate_v1_to_v2.py"),
            Path("skills/operational-learning/scripts/migrate_v2_to_v3.py"),
            Path("skills/operational-learning/scripts/packet_drift.py"),
            Path("schemas/catalog-v1.json"),
            Path("docs/schema-compatibility.md"),
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
            Path("agents/observability-engineer.md"),
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

    def test_v2_application_packet_validates(self) -> None:
        packet = self._valid_v2_application_update()
        self._validate(packet)

        invalid_kind = self._valid_v2_application_update()
        invalid_kind["target"]["component_kind"] = "mystery"  # type: ignore[index]
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "target.component_kind",
        ):
            self._validate(invalid_kind)

        legacy_trigger = self._valid_v2_application_update()
        legacy_trigger["trigger"]["kind"] = "service_added"  # type: ignore[index]
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "trigger.kind",
        ):
            self._validate(legacy_trigger)

    def test_v3_freshness_deadlines_are_forward_and_ordered(self) -> None:
        self._validate(self._valid_v3_application_update())

        # Both deadlines stay nullable. Migration cannot invent a review cadence any more than it
        # can invent environment or definition_locator, and a guessed deadline is worse than none.
        unset = self._valid_v3_application_update()
        unset["freshness"] = {"review_at": None, "expires_at": None}
        self._validate(unset)

        # "Forward" is the whole point: a deadline already past when the packet was written
        # documents nothing and would make every freshness sweep fire on arrival.
        for field in ("review_at", "expires_at"):
            with self.subTest(field=field):
                backdated = self._valid_v3_application_update()
                backdated["freshness"][field] = "2020-01-01T00:00:00Z"  # type: ignore[index]
                with self.assertRaisesRegex(
                    knowledge_update.KnowledgeUpdateValidationError,
                    f"freshness.{field} must be after created_at",
                ):
                    self._validate(backdated)

        inverted = self._valid_v3_application_update()
        inverted["freshness"] = {
            "review_at": "2027-02-01T00:00:00Z",
            "expires_at": "2026-11-01T00:00:00Z",
        }
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "freshness.review_at must not be after freshness.expires_at",
        ):
            self._validate(inverted)

        unknown = self._valid_v3_application_update()
        unknown["freshness"]["retain_until"] = "2028-01-01T00:00:00Z"  # type: ignore[index]
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "unknown freshness fields",
        ):
            self._validate(unknown)

        naive = self._valid_v3_application_update()
        naive["freshness"]["expires_at"] = "2027-02-01"  # type: ignore[index]
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "freshness.expires_at must be an RFC3339 UTC timestamp",
        ):
            self._validate(naive)

    def test_published_v1_and_v2_never_gain_the_v3_freshness_field(self) -> None:
        """v1 and v2 are published and closed; a new field on either is a shape break, not a bonus."""
        for builder in (self._valid_update, self._valid_v2_application_update):
            packet = builder()
            packet["freshness"] = {"review_at": None, "expires_at": None}
            with self.subTest(schema_version=packet["schema_version"]):
                with self.assertRaisesRegex(
                    knowledge_update.KnowledgeUpdateValidationError,
                    "unknown knowledge update fields",
                ):
                    self._validate(packet)

        missing = self._valid_v3_application_update()
        del missing["freshness"]
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "missing knowledge update fields",
        ):
            self._validate(missing)

        # A packet with no schema_version at all must still report the ordinary missing-field
        # error rather than tripping the version-keyed field lookup.
        versionless = self._valid_update()
        del versionless["schema_version"]
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "missing knowledge update fields",
        ):
            self._validate(versionless)

    def test_v2_to_v3_migration_is_deterministic_and_leaves_deadlines_unset(self) -> None:
        spec = importlib.util.spec_from_file_location("migrate_v2_to_v3", MIGRATION_V3_PATH)
        assert spec is not None and spec.loader is not None
        migration = importlib.util.module_from_spec(spec)
        sys.modules["knowledge_update"] = knowledge_update
        spec.loader.exec_module(migration)

        source = self._valid_v2_application_update()
        context = {
            "target_root": self.target_root,
            "allowed_knowledge_roots": ("docs",),
        }
        migrated = migration.migrate(source, **context)
        self.assertEqual(2, source["schema_version"])
        self.assertNotIn("freshness", source)
        self.assertEqual(3, migrated["schema_version"])
        self.assertEqual({"review_at": None, "expires_at": None}, migrated["freshness"])
        self.assertEqual(migrated, migration.migrate(source, **context))
        self._validate(migrated)

        with self.assertRaisesRegex(ValueError, "schema_version 2"):
            migration.migrate(migrated, **context)

        invalid_source = self._valid_v2_application_update()
        invalid_source["evidence"] = []
        with self.assertRaisesRegex(ValueError, "migrated packet failed v3 validation"):
            migration.migrate(invalid_source, **context)

    def test_v1_to_v2_migration_is_deterministic_and_valid(self) -> None:
        spec = importlib.util.spec_from_file_location("migrate_v1_to_v2", MIGRATION_PATH)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader if spec else None)
        assert spec is not None and spec.loader is not None
        migration = importlib.util.module_from_spec(spec)
        sys.modules["knowledge_update"] = knowledge_update
        spec.loader.exec_module(migration)

        source = self._valid_update()
        context = {
            "target_root": self.target_root,
            "allowed_knowledge_roots": ("docs",),
        }
        migrated = migration.migrate(source, **context)
        self.assertEqual(1, source["schema_version"])
        self.assertEqual(2, migrated["schema_version"])
        self.assertEqual("checkout", migrated["target"]["component_id"])
        self.assertEqual("service", migrated["target"]["component_kind"])
        self.assertEqual("alert_added", migrated["trigger"]["kind"])
        self.assertEqual(migrated, migration.migrate(source, **context))
        self._validate(migrated)

        with self.assertRaisesRegex(ValueError, "schema_version 1"):
            migration.migrate(migrated, **context)

        invalid_source = self._valid_update()
        invalid_source["evidence"] = []
        with self.assertRaisesRegex(
            ValueError, "migrated packet failed v2 validation"
        ):
            migration.migrate(invalid_source, **context)

        prepared_without_worktree = self._valid_update()
        with self.assertRaisesRegex(
            ValueError, "prepared dispositions require target_root"
        ):
            migration.migrate(prepared_without_worktree)

        # Documentation duplicates need the same checkout context as prepared dispositions.
        # validate_update's copy of this rule is covered elsewhere; bind the MIGRATION path too,
        # because the CLI help and the compatibility policy both promise it here.
        duplicate_without_worktree = self._duplicate_update("docs/operations/alerts/existing.md")
        with self.assertRaisesRegex(
            ValueError, "documentation duplicate dispositions require target_root"
        ):
            migration.migrate(duplicate_without_worktree)

    # The two migration tests above call migrate() directly, so neither reaches the guard that
    # main() puts in front of it. These two cover that entrypoint boundary instead.
    def test_v1_to_v2_entrypoint_rejects_non_object_json(self) -> None:
        self._assert_entrypoint_rejects_non_object_json(MIGRATION_PATH)

    def test_v2_to_v3_entrypoint_rejects_non_object_json(self) -> None:
        self._assert_entrypoint_rejects_non_object_json(MIGRATION_V3_PATH)

    def test_schema_catalog_and_examples_are_current(self) -> None:
        def iter_refs(value: object):
            if isinstance(value, dict):
                for key, child in value.items():
                    if key == "$ref" and isinstance(child, str):
                        yield child
                    yield from iter_refs(child)
            elif isinstance(value, list):
                for child in value:
                    yield from iter_refs(child)

        def resolve_pointer(document: object, fragment: str) -> object:
            current = document
            if not fragment:
                return current
            self.assertTrue(fragment.startswith("/"), f"invalid JSON pointer: #{fragment}")
            for raw_part in fragment[1:].split("/"):
                part = raw_part.replace("~1", "/").replace("~0", "~")
                if isinstance(current, list):
                    current = current[int(part)]
                else:
                    self.assertIsInstance(current, dict)
                    current = current[part]  # type: ignore[index]
            return current

        catalog = json.loads((ROOT / "schemas/catalog-v1.json").read_text(encoding="utf-8"))
        self.assertEqual(1, catalog["schema_version"])
        entries = catalog["schemas"]
        ids = [entry["id"] for entry in entries]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("operational-knowledge-update-v2", ids)
        self.assertIn("operational-knowledge-update-v3", ids)

        # The catalog is what readers consult for "which version do writers emit". Binding it to
        # the validator's own constant means a version bump cannot ship as an unpublished schema,
        # and exactly one knowledge-update version can ever be `current`.
        knowledge_entries = [
            entry for entry in entries if entry["id"].startswith("operational-knowledge-update-v")
        ]
        current_entries = [
            entry for entry in knowledge_entries if entry["status"] == "current"
        ]
        self.assertEqual(1, len(current_entries))
        self.assertEqual(
            knowledge_update.CURRENT_SCHEMA_VERSION, current_entries[0]["version"]
        )
        self.assertEqual(
            {version: "supported" for version in (1, knowledge_update.COMPONENT_SCHEMA_VERSION)}
            | {knowledge_update.CURRENT_SCHEMA_VERSION: "current"},
            {entry["version"]: entry["status"] for entry in knowledge_entries},
        )
        for entry in knowledge_entries:
            with self.subTest(schema=entry["id"]):
                self.assertEqual(
                    "skills/operational-learning/scripts/knowledge_update.py",
                    entry["validator"],
                )
        self.assertEqual(len(entries), len({entry["uri"] for entry in entries}))
        self.assertEqual(len(entries), len({entry["canonical_path"] for entry in entries}))

        for entry in entries:
            with self.subTest(schema=entry["id"]):
                self.assertEqual(
                    {
                        "id",
                        "uri",
                        "version",
                        "status",
                        "canonical_path",
                        "validator",
                        "generated_projections",
                    },
                    set(entry),
                )
                self.assertIsInstance(entry["version"], int)
                self.assertGreater(entry["version"], 0)
                self.assertIn(
                    entry["status"], {"active", "current", "supported", "contract-only"}
                )
                canonical = ROOT / entry["canonical_path"]
                self.assertTrue(canonical.is_file())
                schema = json.loads(canonical.read_text(encoding="utf-8"))
                self.assertEqual(entry["uri"], schema["$id"])
                for reference in iter_refs(schema):
                    resource, separator, fragment = reference.partition("#")
                    referenced_path = canonical if not resource else canonical.parent / resource
                    self.assertTrue(referenced_path.is_file(), f"missing $ref target: {reference}")
                    referenced_document = json.loads(
                        referenced_path.read_text(encoding="utf-8")
                    )
                    if separator:
                        resolve_pointer(referenced_document, fragment)
                for projection in entry["generated_projections"]:
                    self.assertEqual(
                        canonical.read_bytes(),
                        (ROOT / projection).read_bytes(),
                        f"generated schema projection drift: {projection}",
                    )

        for relative in (
            "skills/operational-learning/assets/examples/knowledge-update-v1-service.json",
            "skills/operational-learning/assets/examples/knowledge-update-v2-application.json",
            "skills/operational-learning/assets/examples/knowledge-update-v3-application.json",
        ):
            with self.subTest(fixture=relative):
                packet = json.loads((ROOT / relative).read_text(encoding="utf-8"))
                knowledge_update.validate_update(packet)

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
            "active incident dispositions must remain proposed or blocked",
        ):
            self._validate(packet)

    def test_active_incident_allows_only_nonterminal_dispositions(self) -> None:
        packet = self._valid_update()
        packet["trigger"].update(  # type: ignore[union-attr]
            {"kind": "incident", "state": "active", "trust": "untrusted"}
        )
        packet["dispositions"] = [
            {
                "artifact": "postmortem",
                "action": "none",
                "status": "not_applicable",
                "owner": "scribe",
                "path": None,
                "duplicate_of": None,
                "base_sha256": None,
                "artifact_sha256": None,
                "reason": "The incident is still active.",
                "evidence_ids": ["e1"],
            }
        ]
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "active incident dispositions must remain proposed or blocked",
        ):
            self._validate(packet)

        packet["dispositions"] = [
            {
                "artifact": "postmortem",
                "action": "handoff",
                "status": "proposed",
                "owner": "scribe",
                "path": None,
                "duplicate_of": None,
                "base_sha256": None,
                "artifact_sha256": None,
                "reason": "Defer retrospective work until the incident is resolved.",
                "evidence_ids": ["e1"],
            }
        ]
        self._validate(packet)

    def test_approved_triggers_require_their_artifact_disposition_set(self) -> None:
        approved_alert = self._valid_update()
        approved_alert["dispositions"] = [approved_alert["dispositions"][0]]  # type: ignore[index]
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "alert_added.*missing required artifact dispositions.*runbook.*service_card",
        ):
            self._validate(approved_alert)

        approved_service = self._valid_update()
        approved_service["trigger"]["kind"] = "service_added"  # type: ignore[index]
        approved_service["dispositions"] = [
            {
                "artifact": "code",
                "action": "none",
                "status": "not_applicable",
                "owner": "sde",
                "path": None,
                "duplicate_of": None,
                "base_sha256": None,
                "artifact_sha256": None,
                "reason": "No code change belongs in documentation closeout.",
                "evidence_ids": ["e1"],
            }
        ]
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "service_added.*missing required artifact dispositions.*knowledge_index.*runbook.*service_card",
        ):
            self._validate(approved_service)

        approved_service["dispositions"] = [
            {
                "artifact": artifact,
                "action": "handoff",
                "status": "proposed",
                "owner": "scribe",
                "path": None,
                "duplicate_of": None,
                "base_sha256": None,
                "artifact_sha256": None,
                "reason": f"Prepare the {artifact} in a reviewable documentation diff.",
                "evidence_ids": ["e1", "e2"],
            }
            for artifact in ("service_card", "knowledge_index", "runbook")
        ]
        self._validate(approved_service)

    def test_prepared_paths_require_caller_trusted_knowledge_roots(self) -> None:
        packet = self._valid_update()
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            "prepared dispositions require caller-trusted allowed_knowledge_roots",
        ):
            knowledge_update.validate_update(packet, target_root=self.target_root)

        untrusted_packet_root = self._valid_update()
        untrusted_packet_root["target"]["knowledge_roots"] = ["agents"]  # type: ignore[index]
        untrusted_packet_root["dispositions"][0]["path"] = "agents/sre.md"  # type: ignore[index]
        with self.assertRaisesRegex(
            knowledge_update.KnowledgeUpdateValidationError,
            r"dispositions\[0\].path is outside caller-trusted allowed_knowledge_roots",
        ):
            knowledge_update.validate_update(
                untrusted_packet_root,
                target_root=self.target_root,
                allowed_knowledge_roots=("docs",),
            )

        packet_scope_can_be_broader_than_caller_scope = self._valid_update()
        knowledge_update.validate_update(
            packet_scope_can_be_broader_than_caller_scope,
            target_root=self.target_root,
            allowed_knowledge_roots=("docs/operations/alerts",),
        )

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
                "--allowed-knowledge-root",
                "docs",
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

        missing_allowed_root = subprocess.run(
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
        self.assertEqual(1, missing_allowed_root.returncode)
        self.assertIn(
            "prepared dispositions require caller-trusted allowed_knowledge_roots",
            missing_allowed_root.stderr,
        )

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
            knowledge_update.RFC3339_UTC_TIMESTAMP_RE.pattern,
            schema["properties"]["created_at"]["pattern"],
        )
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
        encoded_required_artifacts: dict[tuple[str, str], set[str]] = {}
        active_incident_statuses: set[str] | None = None
        for rule in schema["allOf"]:
            trigger_properties = (
                rule.get("if", {})
                .get("properties", {})
                .get("trigger", {})
                .get("properties", {})
            )
            kind_rule = trigger_properties.get("kind", {})
            state_rule = trigger_properties.get("state", {})
            disposition_rule = (
                rule.get("then", {})
                .get("properties", {})
                .get("dispositions", {})
            )
            if state_rule.get("const") == "approved" and "enum" in kind_rule:
                artifacts = {
                    constraint["contains"]["properties"]["artifact"]["const"]
                    for constraint in disposition_rule.get("allOf", [])
                }
                for trigger_kind in kind_rule["enum"]:
                    encoded_required_artifacts[(trigger_kind, "approved")] = artifacts
            if (
                kind_rule.get("const") == "incident"
                and state_rule.get("const") == "active"
            ):
                active_incident_statuses = set(
                    disposition_rule["items"]["properties"]["status"]["enum"]
                )
        self.assertEqual(
            knowledge_update.REQUIRED_ARTIFACT_DISPOSITIONS,
            encoded_required_artifacts,
        )
        self.assertEqual({"proposed", "blocked"}, active_incident_statuses)
        self.assertIn(
            "not write authority",
            schema["properties"]["target"]["properties"]["knowledge_roots"]["description"],
        )
        self.assertFalse(schema["additionalProperties"])

    def test_v3_schema_inherits_every_applicable_earlier_approved_artifact_rule(self) -> None:
        """v3 is the current write format, so its standalone contract must stay as strict as the
        versions it reuses. The catalog test only proves each `$ref` resolves — deleting one would
        weaken the published schema with every other test still green.
        """
        assets = ROOT / "skills/operational-learning/assets"
        documents = {
            name: json.loads((assets / name).read_text(encoding="utf-8"))
            for name in (
                "knowledge-update-v1.schema.json",
                "knowledge-update-v2.schema.json",
                "knowledge-update-v3.schema.json",
            )
        }
        v3 = documents["knowledge-update-v3.schema.json"]

        effective: list[dict] = []
        for rule in v3["allOf"]:
            reference = rule.get("$ref")
            if reference is None:
                effective.append(rule)
                continue
            source, _, pointer = reference.partition("#/allOf/")
            self.assertIn(source, documents, f"unexpected v3 allOf ref: {reference}")
            effective.append(documents[source]["allOf"][int(pointer)])

        # v3 reuses v2's trigger definition by reference, so v2 is where its kinds are declared.
        self.assertEqual(
            "knowledge-update-v2.schema.json#/$defs/trigger",
            v3["properties"]["trigger"]["$ref"],
        )
        v3_kinds = set(
            documents["knowledge-update-v2.schema.json"]["$defs"]["trigger"]["properties"]["kind"][
                "enum"
            ]
        )
        v3_rules = _approved_artifact_rules(effective)
        inherited = _approved_artifact_rules(
            documents["knowledge-update-v1.schema.json"]["allOf"]
        ) | _approved_artifact_rules(
            [
                rule
                for rule in documents["knowledge-update-v2.schema.json"]["allOf"]
                if "$ref" not in rule
            ]
        )
        self.assertTrue(inherited, "no approved-artifact rules found in v1/v2")
        for (kind, state), artifacts in inherited.items():
            if kind not in v3_kinds:
                continue
            with self.subTest(trigger_kind=kind):
                self.assertIn(
                    (kind, state),
                    v3_rules,
                    f"v3 dropped the approved-artifact rule for {kind!r}",
                )
                self.assertTrue(
                    artifacts <= v3_rules[(kind, state)],
                    f"v3 weakened the required artifacts for {kind!r}: "
                    f"{sorted(artifacts - v3_rules[(kind, state)])} missing",
                )

    def test_v2_schema_inherits_every_applicable_v1_approved_artifact_rule(self) -> None:
        assets = ROOT / "skills/operational-learning/assets"
        v1 = json.loads(
            (assets / "knowledge-update-v1.schema.json").read_text(encoding="utf-8")
        )
        v2 = json.loads(
            (assets / "knowledge-update-v2.schema.json").read_text(encoding="utf-8")
        )

        approved_artifact_rules = _approved_artifact_rules

        ref_prefix = "knowledge-update-v1.schema.json#/allOf/"
        effective_v2_rules: list[dict] = []
        for rule in v2["allOf"]:
            reference = rule.get("$ref")
            if reference is None:
                effective_v2_rules.append(rule)
                continue
            self.assertTrue(
                reference.startswith(ref_prefix),
                f"unexpected v2 top-level allOf ref: {reference}",
            )
            effective_v2_rules.append(v1["allOf"][int(reference[len(ref_prefix) :])])

        v1_rules = approved_artifact_rules(v1["allOf"])
        v2_rules = approved_artifact_rules(effective_v2_rules)
        v2_trigger_kinds = set(v2["$defs"]["trigger"]["properties"]["kind"]["enum"])
        self.assertTrue(v1_rules, "v1 schema encodes no approved-artifact rules")
        for (kind, state), artifacts in v1_rules.items():
            if kind not in v2_trigger_kinds:
                continue
            self.assertIn(
                (kind, state),
                v2_rules,
                f"v2 schema dropped the v1 approved-artifact rule for {kind!r}; "
                "the standalone JSON Schema contract must stay as strict as v1",
            )
            self.assertTrue(
                artifacts <= v2_rules[(kind, state)],
                f"v2 schema weakened required artifacts for {kind!r}: "
                f"{sorted(v2_rules[(kind, state)])} lost {sorted(artifacts)}",
            )

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
