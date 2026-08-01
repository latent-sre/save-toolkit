"""Mutation tests for credential-free raw Git tree materialization."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import materialize_git_tree as materializer


class MaterializeGitTreeTests(unittest.TestCase):
    def _git(
        self,
        repository: Path,
        *arguments: str,
        input_bytes: bytes | None = None,
    ) -> str:
        result = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            input=input_bytes,
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            0,
            result.returncode,
            (result.stderr or result.stdout).decode("utf-8", errors="replace"),
        )
        return result.stdout.decode("utf-8", errors="strict").strip()

    def _source(self, root: Path) -> tuple[Path, str]:
        source = root / "source"
        source.mkdir()
        self._git(source, "init")
        self._git(source, "config", "user.name", "Conformance Test")
        self._git(source, "config", "user.email", "conformance@example.invalid")
        files = {
            ".agents/plugins/marketplace.json": b'{"plugins": []}\n',
            ".codex/agents/reviewer.toml": b'name = "reviewer"\n',
            "plugins/sre-agents/.codex-plugin/plugin.json": b'{"name": "sre-agents"}\n',
            "plugins/sre-agents/skills/example/SKILL.md": b"# Exact raw bytes\n",
            "scripts/executable.sh": b"#!/bin/sh\nexit 0\n",
        }
        for relative, data in files.items():
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self._git(source, "add", ".")
        self._git(source, "update-index", "--chmod=+x", "scripts/executable.sh")
        self._git(source, "commit", "-m", "fixture")
        return source, self._git(source, "rev-parse", "HEAD")

    def _object_store(self, root: Path, source: Path) -> Path:
        repository = root / "candidate"
        result = subprocess.run(
            ["git", "clone", "--no-checkout", "--depth=1", str(source), str(repository)],
            capture_output=True,
            check=False,
        )
        self.assertEqual(
            0,
            result.returncode,
            (result.stderr or result.stdout).decode("utf-8", errors="replace"),
        )
        self._git(repository, "remote", "remove", "origin")
        self.assertEqual([".git"], sorted(path.name for path in repository.iterdir()))
        return repository

    @staticmethod
    def _paths() -> list[str]:
        return [
            ".agents/plugins/marketplace.json",
            "plugins/sre-agents",
            ".codex/agents",
        ]

    def test_materializes_selected_raw_blobs_and_binds_clean_head(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source, commit = self._source(root)
            repository = self._object_store(root, source)
            marker = materializer.materialize(repository, commit, self._paths())

            self.assertEqual(commit, marker["repository_commit"])
            self.assertEqual(4, marker["entry_count"])
            self.assertFalse(marker["filters_executed"])
            self.assertFalse(marker["links_materialized"])
            skill_path = repository / "plugins/sre-agents/skills/example/SKILL.md"
            self.assertEqual(b"# Exact raw bytes\n", skill_path.read_bytes())
            self.assertFalse((repository / "scripts/executable.sh").exists())
            self.assertEqual(commit, self._git(repository, "rev-parse", "HEAD"))
            self.assertEqual(
                "",
                self._git(repository, "status", "--porcelain=v1", "--", *self._paths()),
            )
            stored = json.loads(
                (repository / ".git" / materializer.MARKER_NAME).read_text(encoding="utf-8")
            )
            self.assertEqual(marker, stored)
            self.assertEqual(marker, materializer.verify_materialization(repository, self._paths()))

            skill_path.write_bytes(b"# Exact raw bytez\n")
            with self.assertRaisesRegex(materializer.MaterializationError, "bytes differ"):
                materializer.verify_materialization(repository, self._paths())
            skill_path.write_bytes(b"# Exact raw bytes\n")

            stored["filters_executed"] = True
            (repository / ".git" / materializer.MARKER_NAME).write_text(
                json.dumps(stored), encoding="utf-8"
            )
            with self.assertRaisesRegex(materializer.MaterializationError, "marker differs"):
                materializer.verify_materialization(repository, self._paths())

    def test_candidate_lfs_attributes_never_activate_configured_filter(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source, _ = self._source(root)
            attributes = source / "plugins/sre-agents/.gitattributes"
            attributes.write_text("payload.bin filter=lfs\n", encoding="utf-8")
            payload = source / "plugins/sre-agents/payload.bin"
            payload.write_text(
                "version https://git-lfs.github.com/spec/v1\n"
                "oid sha256:0000000000000000000000000000000000000000000000000000000000000000\n"
                "size 1\n",
                encoding="utf-8",
            )
            self._git(source, "add", ".")
            self._git(source, "commit", "-m", "candidate lfs metadata")
            commit = self._git(source, "rev-parse", "HEAD")
            repository = self._object_store(root, source)
            injected_config = {
                "GIT_CONFIG_COUNT": "3",
                "GIT_CONFIG_KEY_0": "filter.lfs.clean",
                "GIT_CONFIG_VALUE_0": "false",
                "GIT_CONFIG_KEY_1": "filter.lfs.smudge",
                "GIT_CONFIG_VALUE_1": "false",
                "GIT_CONFIG_KEY_2": "filter.lfs.required",
                "GIT_CONFIG_VALUE_2": "true",
            }
            with mock.patch.dict(os.environ, injected_config):
                materializer.materialize(repository, commit, self._paths())

            self.assertTrue(
                (repository / "plugins/sre-agents/payload.bin")
                .read_text()
                .startswith("version ")
            )
            self.assertEqual(
                "",
                self._git(repository, "status", "--porcelain=v1", "--", *self._paths()),
            )
            self.assertEqual([], list((repository / ".git/sre-agents-disabled-hooks").iterdir()))

    def test_rejects_a_live_credential_or_retained_remote(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source, commit = self._source(root)
            repository = self._object_store(root, source)
            with mock.patch.dict(os.environ, {"GH_TOKEN": "must-not-survive"}):
                with self.assertRaisesRegex(materializer.MaterializationError, "credential-free"):
                    materializer.materialize(repository, commit, self._paths())

            self._git(repository, "remote", "add", "origin", str(source))
            with self.assertRaisesRegex(materializer.MaterializationError, "retain a remote"):
                materializer.materialize(repository, commit, self._paths())
            self._git(repository, "remote", "remove", "origin")
            self._git(repository, "config", "filter.lfs.process", "must-not-run")
            with self.assertRaisesRegex(materializer.MaterializationError, "unsafe config"):
                materializer.materialize(repository, commit, self._paths())

    def test_rejects_existing_worktree_content_and_missing_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source, commit = self._source(root)
            repository = self._object_store(root, source)
            (repository / "unexpected.txt").write_text("not empty", encoding="utf-8")
            with self.assertRaisesRegex(materializer.MaterializationError, "must be empty"):
                materializer.materialize(repository, commit, self._paths())
            (repository / "unexpected.txt").unlink()
            with self.assertRaisesRegex(materializer.MaterializationError, "absent"):
                materializer.materialize(repository, commit, ["plugins/not-present"])

    def test_rejects_symlinks_and_gitlinks_before_reading_blobs(self) -> None:
        object_id = "0" * 40
        for mode, object_type, size in (
            ("120000", "blob", "6"),
            ("160000", "commit", "-"),
        ):
            raw = f"{mode} {object_type} {object_id} {size}\tunsafe\0".encode()
            with self.assertRaisesRegex(
                materializer.MaterializationError, "linked, submodule, or unsupported"
            ):
                materializer._parse_tree(raw)

    def test_repository_layout_compares_filesystem_identity_not_path_spelling(self) -> None:
        repository = Path("logical-candidate")
        git_directory = repository / ".git"
        with (
            mock.patch.object(
                materializer,
                "_git",
                side_effect=[b"physical-candidate\n", b"physical-candidate/.git\n"],
            ),
            mock.patch.object(Path, "samefile", autospec=True, return_value=True) as samefile,
        ):
            materializer._assert_repository_layout(repository, git_directory)

        self.assertEqual(2, samefile.call_count)

    def test_rejects_traversal_git_metadata_and_case_collisions(self) -> None:
        for path in ("../escape", "/absolute", "safe/../../escape", ".git/config", "a\\b"):
            with self.assertRaises(materializer.MaterializationError, msg=path):
                materializer._validate_requested_path(path)
        object_id = "1" * 40
        raw = (
            f"100644 blob {object_id} 1\tPlugin/file\0"
            f"100644 blob {object_id} 1\tplugin/other\0"
        ).encode()
        with self.assertRaisesRegex(materializer.MaterializationError, "case-colliding"):
            materializer._parse_tree(raw)

    def test_rejects_oversized_and_malformed_cat_file_contracts(self) -> None:
        object_id = "2" * 40
        oversized = (
            f"100644 blob {object_id} {materializer.MAX_FILE_BYTES + 1}\tlarge.bin\0"
        ).encode()
        with self.assertRaisesRegex(materializer.MaterializationError, "size limit"):
            materializer._parse_tree(oversized)
        entry = materializer.TreeEntry("100644", "blob", object_id, 1, "small.bin")
        malformed = f"{object_id} blob 1\n".encode()
        with mock.patch.object(materializer, "_git", return_value=malformed):
            with self.assertRaisesRegex(materializer.MaterializationError, "object contract"):
                materializer._read_blobs(Path("."), [entry])


if __name__ == "__main__":
    unittest.main()
