#!/usr/bin/env python3
"""Repository-corpus tests for the bounded fleet-improvement ledger."""

from __future__ import annotations

import importlib.util
import copy
import json
import os
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ledger = _load(ROOT / "scripts/validate_improvement_ledger.py", "improvement_ledger")
fixtures = _load(ROOT / "scripts/test_fleet_improvement.py", "fleet_improvement_fixtures")


class ImprovementLedgerTests(unittest.TestCase):
    def _temporary_repository(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        root = Path(temporary.name)
        subprocess.run(["git", "init", "--quiet"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.email", "ledger@example.invalid"], cwd=root, check=True)
        subprocess.run(["git", "config", "user.name", "Ledger Test"], cwd=root, check=True)
        subprocess.run(
            ["git", "commit", "--quiet", "--allow-empty", "-m", "initial"],
            cwd=root,
            check=True,
        )
        (root / "evals/improvements/fi_agent_routing_discovery").mkdir(parents=True)
        return temporary, root

    @staticmethod
    def _head(root: Path) -> str:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip()

    def _bind_base(self, root: Path, record: dict[str, object]) -> None:
        record["target"]["base_revision"] = self._head(root)  # type: ignore[index]

    def test_current_repository_corpus_passes(self) -> None:
        ledger.validate_ledger(ROOT)

    def test_new_promoted_record_is_rejected_before_evidence_resolution(self) -> None:
        temporary, root = self._temporary_repository()
        try:
            record = fixtures._record("closed")
            path = root / "evals/improvements/fi_agent_routing_discovery/record.json"
            path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaisesRegex(
                ledger.LedgerValidationError,
                "must begin observed",
            ):
                ledger.validate_ledger(root)
        finally:
            temporary.cleanup()

    def test_retained_git_history_and_working_transition_are_replayed(self) -> None:
        temporary, root = self._temporary_repository()
        try:
            path = root / "evals/improvements/fi_agent_routing_discovery/record.json"
            observed = fixtures._record("observed")
            self._bind_base(root, observed)
            fixtures._materialize_evidence_envelopes(root, observed)
            path.write_text(json.dumps(observed), encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "--quiet", "-m", "record observation"],
                cwd=root,
                check=True,
            )

            qualified = fixtures._record("qualified")
            qualified["target"]["base_revision"] = observed["target"]["base_revision"]  # type: ignore[index]
            prior = datetime.fromisoformat(str(observed["updated_at"]).replace("Z", "+00:00"))
            qualified["updated_at"] = (prior + timedelta(seconds=1)).isoformat().replace(
                "+00:00", "Z"
            )
            qualified["disposition_reason"] = "The recurring fingerprint is qualified."
            fixtures._materialize_evidence_envelopes(root, qualified)
            path.write_text(json.dumps(qualified), encoding="utf-8")

            history = ledger._history_bytes(
                root,
                Path("evals/improvements/fi_agent_routing_discovery/record.json"),
            )
            self.assertEqual([label for label, _ in history][-1], "working-tree")
            self.assertEqual(len(history), 2)
            ledger.validate_ledger(root)
        finally:
            temporary.cleanup()

    def test_first_revision_authority_shape_is_not_bypassed(self) -> None:
        temporary, root = self._temporary_repository()
        try:
            record = fixtures._record("observed")
            self._bind_base(root, record)
            fixtures._materialize_evidence_envelopes(root, record)
            path = root / "evals/improvements/fi_agent_routing_discovery/record.json"
            path.write_text(json.dumps(record), encoding="utf-8")

            with mock.patch.object(
                ledger,
                "_synthetic_initial_authority",
                return_value={
                    "actor": "repository-history",
                    "role": "author",
                    "subject_revision": None,
                },
                create=True,
            ):
                with self.assertRaisesRegex(
                    ledger.LedgerValidationError,
                    "authority.role",
                ):
                    ledger.validate_ledger(root)
        finally:
            temporary.cleanup()

    def test_any_record_deletion_retained_in_git_history_is_rejected(self) -> None:
        temporary, root = self._temporary_repository()
        try:
            path = root / "evals/improvements/fi_agent_routing_discovery/record.json"
            record = fixtures._record("observed")
            fixtures._materialize_evidence_envelopes(root, record)
            path.write_text(json.dumps(record), encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "--quiet", "-m", "record observation"],
                cwd=root,
                check=True,
            )
            path.unlink()
            subprocess.run(["git", "add", "-u"], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "--quiet", "-m", "delete record"],
                cwd=root,
                check=True,
            )
            path.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaisesRegex(
                ledger.LedgerValidationError,
                "Git history contains deletions",
            ):
                ledger.validate_ledger(root)
        finally:
            temporary.cleanup()

    def test_record_deletion_on_merged_side_history_is_rejected(self) -> None:
        temporary, root = self._temporary_repository()
        try:
            main_branch = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            ).stdout.strip()
            subprocess.run(
                ["git", "checkout", "--quiet", "-b", "ghost-ledger-history"],
                cwd=root,
                check=True,
            )
            path = root / "evals/improvements/fi_agent_routing_discovery/record.json"
            path.write_text(json.dumps(fixtures._record("observed")), encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "--quiet", "-m", "add ghost ledger record"],
                cwd=root,
                check=True,
            )
            path.unlink()
            subprocess.run(["git", "add", "-u"], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "--quiet", "-m", "delete ghost ledger record"],
                cwd=root,
                check=True,
            )
            subprocess.run(
                ["git", "checkout", "--quiet", main_branch],
                cwd=root,
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "merge",
                    "--quiet",
                    "--no-ff",
                    "-m",
                    "merge hidden ledger history",
                    "ghost-ledger-history",
                ],
                cwd=root,
                check=True,
            )
            with self.assertRaisesRegex(
                ledger.LedgerValidationError,
                "Git history contains deletions",
            ):
                ledger.validate_ledger(root)
        finally:
            temporary.cleanup()

    def test_record_deletion_introduced_only_by_merge_result_is_rejected(self) -> None:
        temporary, root = self._temporary_repository()
        try:
            relative_path = Path(
                "evals/improvements/fi_agent_routing_discovery/record.json"
            )
            path = root / relative_path
            record = fixtures._record("observed")
            self._bind_base(root, record)
            fixtures._materialize_evidence_envelopes(root, record)
            rendered = json.dumps(record)
            path.write_text(rendered, encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "--quiet", "-m", "record observation"],
                cwd=root,
                check=True,
            )

            main_branch = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            ).stdout.strip()
            subprocess.run(
                ["git", "checkout", "--quiet", "-b", "retains-record"],
                cwd=root,
                check=True,
            )
            (root / "side-change.txt").write_text("side\n", encoding="utf-8")
            subprocess.run(["git", "add", "side-change.txt"], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "--quiet", "-m", "side change"],
                cwd=root,
                check=True,
            )
            side_parent = self._head(root)

            subprocess.run(
                ["git", "checkout", "--quiet", main_branch],
                cwd=root,
                check=True,
            )
            (root / "main-change.txt").write_text("main\n", encoding="utf-8")
            subprocess.run(["git", "add", "main-change.txt"], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "--quiet", "-m", "main change"],
                cwd=root,
                check=True,
            )
            main_parent = self._head(root)

            subprocess.run(
                [
                    "git",
                    "merge",
                    "--quiet",
                    "--no-ff",
                    "--no-commit",
                    "retains-record",
                ],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            path.unlink()
            subprocess.run(
                ["git", "add", "-u", "--", relative_path.as_posix()],
                cwd=root,
                check=True,
            )
            subprocess.run(
                ["git", "commit", "--quiet", "-m", "merge with record deletion"],
                cwd=root,
                check=True,
            )
            parents = subprocess.run(
                ["git", "show", "-s", "--format=%P", "HEAD"],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            ).stdout.split()
            self.assertEqual([main_parent, side_parent], parents)
            for parent in parents:
                retained = subprocess.run(
                    ["git", "cat-file", "-e", f"{parent}:{relative_path.as_posix()}"],
                    cwd=root,
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                self.assertEqual(0, retained.returncode)
            deleted = subprocess.run(
                ["git", "cat-file", "-e", f"HEAD:{relative_path.as_posix()}"],
                cwd=root,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.assertNotEqual(0, deleted.returncode)

            path.write_text(rendered, encoding="utf-8")
            with self.assertRaisesRegex(
                ledger.LedgerValidationError,
                "Git history contains deletions",
            ):
                ledger.validate_ledger(root)
        finally:
            temporary.cleanup()

    def test_duplicate_json_object_keys_in_record_are_rejected(self) -> None:
        temporary, root = self._temporary_repository()
        try:
            record = fixtures._record("observed")
            self._bind_base(root, record)
            fixtures._materialize_evidence_envelopes(root, record)
            rendered = json.dumps(record)
            expected = '"improvement_id": "fi_agent_routing_discovery"'
            self.assertEqual(1, rendered.count(expected))
            rendered = rendered.replace(
                expected,
                '"improvement_id": "fi_shadowed_record", ' + expected,
                1,
            )
            path = root / "evals/improvements/fi_agent_routing_discovery/record.json"
            path.write_text(rendered, encoding="utf-8")

            with self.assertRaisesRegex(
                ledger.LedgerValidationError,
                "duplicate JSON object key.*improvement_id",
            ):
                ledger.validate_ledger(root)
        finally:
            temporary.cleanup()

    def test_shallow_repository_is_rejected(self) -> None:
        temporary, root = self._temporary_repository()
        clone_parent = tempfile.TemporaryDirectory()
        try:
            path = root / "evals/improvements/fi_agent_routing_discovery/record.json"
            record = fixtures._record("observed")
            fixtures._materialize_evidence_envelopes(root, record)
            path.write_text(json.dumps(record), encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=root, check=True)
            subprocess.run(
                ["git", "commit", "--quiet", "-m", "record observation"],
                cwd=root,
                check=True,
            )
            clone = Path(clone_parent.name) / "shallow"
            subprocess.run(
                [
                    "git",
                    "clone",
                    "--quiet",
                    "--depth",
                    "1",
                    "--no-local",
                    str(root),
                    str(clone),
                ],
                check=True,
            )
            with self.assertRaisesRegex(
                ledger.LedgerValidationError,
                "complete Git history is required",
            ):
                ledger.validate_ledger(clone)
        finally:
            clone_parent.cleanup()
            temporary.cleanup()

    def test_directory_id_and_exact_contents_are_enforced(self) -> None:
        temporary, root = self._temporary_repository()
        try:
            record = fixtures._record("observed")
            record["improvement_id"] = "fi_different_record"
            directory = root / "evals/improvements/fi_agent_routing_discovery"
            (directory / "record.json").write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaisesRegex(ledger.LedgerValidationError, "directory ID"):
                ledger.validate_ledger(root)

            (directory / "notes.txt").write_text("not allowed", encoding="utf-8")
            with self.assertRaisesRegex(ledger.LedgerValidationError, "exactly record.json"):
                ledger.discover_records(root)
        finally:
            temporary.cleanup()

    def test_hardlinked_record_is_rejected_when_supported(self) -> None:
        temporary, root = self._temporary_repository()
        try:
            directory = root / "evals/improvements/fi_agent_routing_discovery"
            source = root / "source.json"
            source.write_text(json.dumps(fixtures._record("observed")), encoding="utf-8")
            try:
                os.link(source, directory / "record.json")
            except OSError as exc:
                self.skipTest(f"hard links unavailable: {exc}")
            with self.assertRaisesRegex(ledger.LedgerValidationError, "single-linked"):
                ledger.discover_records(root)
        finally:
            temporary.cleanup()

    def test_ledger_ancestor_link_is_rejected_when_supported(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        target = tempfile.TemporaryDirectory()
        try:
            root = Path(temporary.name)
            outside = Path(target.name)
            (outside / "improvements").mkdir()
            try:
                (root / "evals").symlink_to(outside, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"directory links unavailable: {exc}")
            with self.assertRaisesRegex(
                ledger.LedgerValidationError,
                "not a link/reparse point",
            ):
                ledger.discover_records(root)
        finally:
            target.cleanup()
            temporary.cleanup()

    def test_duplicate_fingerprint_requires_one_linked_canonical_record(self) -> None:
        first = fixtures._record("observed")
        second = copy.deepcopy(first)
        second["improvement_id"] = "fi_second_learning_record"
        second["observations"][0]["event_id"] = "fo_second_learning_event"  # type: ignore[index]
        old_evidence_id = second["evidence_refs"][0]["evidence_id"]  # type: ignore[index]
        new_evidence_id = "ev_22222222222222222222222222222222"
        second["evidence_refs"][0]["evidence_id"] = new_evidence_id  # type: ignore[index]
        second["observations"][0]["evidence_ids"] = [new_evidence_id]  # type: ignore[index]
        self.assertNotEqual(old_evidence_id, new_evidence_id)
        with self.assertRaisesRegex(
            ledger.LedgerValidationError,
            "must have exactly one canonical record",
        ):
            ledger._validate_cross_record_uniqueness(
                {
                    str(first["improvement_id"]): first,
                    str(second["improvement_id"]): second,
                }
            )

    def test_event_and_evidence_ids_are_unique_across_records(self) -> None:
        first = fixtures._record("observed")
        second = copy.deepcopy(first)
        second["improvement_id"] = "fi_second_learning_record"
        second["failure_fingerprint"] = "ff_" + "2" * 64
        with self.assertRaisesRegex(ledger.LedgerValidationError, "event_id"):
            ledger._validate_cross_record_uniqueness(
                {
                    str(first["improvement_id"]): first,
                    str(second["improvement_id"]): second,
                }
            )

        second["observations"][0]["event_id"] = "fo_second_learning_event"  # type: ignore[index]
        with self.assertRaisesRegex(ledger.LedgerValidationError, "evidence_id"):
            ledger._validate_cross_record_uniqueness(
                {
                    str(first["improvement_id"]): first,
                    str(second["improvement_id"]): second,
                }
            )

    def test_history_authority_uses_retained_artifact_identities(self) -> None:
        cases = (
            ("qualified", "candidate", "author", "prompt-engineer"),
            ("candidate", "evaluated", "evaluator", "protected-evaluator"),
            ("evaluated", "in_review", "reviewer", "reviewer"),
            ("in_review", "merged", "human_or_protected_workflow", "maintainer"),
            ("merged", "monitoring", "evaluator", "protected-monitor"),
            ("merged", "rolled_back", "human_or_protected_workflow", "maintainer"),
        )
        for previous_status, current_status, role, actor in cases:
            with self.subTest(transition=f"{previous_status}->{current_status}"):
                authority = ledger._synthetic_authority(
                    fixtures._record(previous_status),
                    fixtures._record(current_status),
                )
                self.assertEqual(role, authority["role"])
                self.assertEqual(actor, authority["actor"])

    def test_initial_history_authority_uses_creation_roles(self) -> None:
        pilot = json.loads(fixtures.PILOT_PATH.read_text(encoding="utf-8"))
        cases = (
            (fixtures._record("observed"), "triage"),
            (pilot, "human_or_protected_workflow"),
        )
        for record, role in cases:
            with self.subTest(status=record["status"]):
                self.assertEqual(
                    {
                        "actor": "repository-history",
                        "role": role,
                        "subject_revision": None,
                    },
                    ledger._synthetic_initial_authority(record),
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
