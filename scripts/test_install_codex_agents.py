"""Offline tests for conflict-safe Codex agent synchronization."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import install_codex_agents as installer


class CodexInstallerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        base = Path(self.temporary.name)
        self.source = base / "source"
        self.target = base / "target"
        self.source.mkdir()
        self.source.joinpath("sre.toml").write_text("name = \"sre\"\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_fresh_install_and_check_are_idempotent(self) -> None:
        plan = installer.build_sync_plan(self.source, self.target)
        self.assertEqual(1, len(plan.writes))
        installer.apply_sync_plan(plan)
        self.assertFalse(installer.build_sync_plan(self.source, self.target).out_of_sync)
        self.assertTrue((self.target / "sre.toml").read_text(encoding="utf-8").startswith(installer.INSTALL_MARKER))

    def test_unmanaged_collision_blocks_entire_plan(self) -> None:
        self.target.mkdir()
        self.target.joinpath("sre.toml").write_text("user-owned = true\n", encoding="utf-8")
        plan = installer.build_sync_plan(self.source, self.target)
        self.assertEqual((self.target / "sre.toml",), plan.conflicts)
        with self.assertRaises(ValueError):
            installer.apply_sync_plan(plan)
        self.assertEqual("user-owned = true\n", (self.target / "sre.toml").read_text(encoding="utf-8"))

    def test_exact_unmarked_copy_is_adopted(self) -> None:
        self.target.mkdir()
        source_bytes = (self.source / "sre.toml").read_bytes()
        self.target.joinpath("sre.toml").write_bytes(source_bytes)
        plan = installer.build_sync_plan(self.source, self.target)
        self.assertEqual(1, len(plan.writes))
        self.assertFalse(plan.conflicts)

    def test_only_managed_stale_files_are_pruned(self) -> None:
        self.target.mkdir()
        self.target.joinpath("retired.toml").write_text(installer.INSTALL_MARKER + "\n", encoding="utf-8")
        self.target.joinpath("personal.toml").write_text("name = \"personal\"\n", encoding="utf-8")
        plan = installer.build_sync_plan(self.source, self.target)
        self.assertEqual((self.target / "retired.toml",), tuple(item.path for item in plan.removals))
        installer.apply_sync_plan(plan)
        self.assertTrue((self.target / "personal.toml").exists())

    def test_fresh_target_created_after_preflight_is_not_overwritten(self) -> None:
        plan = installer.build_sync_plan(self.source, self.target)
        self.target.mkdir()
        target = self.target / "sre.toml"
        target.write_text("user-owned = true\n", encoding="utf-8")
        with self.assertRaises(installer.ConcurrentChangeError):
            installer.apply_sync_plan(plan)
        self.assertEqual("user-owned = true\n", target.read_text(encoding="utf-8"))

    def test_managed_target_replaced_after_preflight_is_restored_not_overwritten(self) -> None:
        first = installer.build_sync_plan(self.source, self.target)
        installer.apply_sync_plan(first)
        self.source.joinpath("sre.toml").write_text("name = \"sre\"\nchanged = true\n", encoding="utf-8")
        plan = installer.build_sync_plan(self.source, self.target)
        target = self.target / "sre.toml"
        target.write_text("user-owned = true\n", encoding="utf-8")
        with self.assertRaises(installer.ConcurrentChangeError):
            installer.apply_sync_plan(plan)
        self.assertEqual("user-owned = true\n", target.read_text(encoding="utf-8"))

    def test_stale_target_replaced_after_preflight_is_not_deleted(self) -> None:
        self.target.mkdir()
        target = self.target / "retired.toml"
        target.write_text(installer.INSTALL_MARKER + "\n", encoding="utf-8")
        plan = installer.build_sync_plan(self.source, self.target)
        target.write_text("user-owned = true\n", encoding="utf-8")
        with self.assertRaises(installer.ConcurrentChangeError):
            installer.apply_sync_plan(plan)
        self.assertEqual("user-owned = true\n", target.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
