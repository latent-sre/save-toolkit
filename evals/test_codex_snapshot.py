#!/usr/bin/env python3
"""Contract tests for exact-Git ROUTE-001 snapshots and neutral Codex staging."""
from __future__ import annotations

import io
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock


sys.path.insert(0, str(Path(__file__).resolve().parent))
import codex_snapshot  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
BEFORE = "a39a81f33f7ad7325c52d883822bbbdd80c7ed28"
CURRENT = "7aef80aede95394f6c4237ed2aedb911e141c3c0"


def _json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _valid_files(*, version: str = "0.1.0") -> dict[str, bytes]:
    return {
        ".agents/plugins/marketplace.json": _json_bytes(
            {
                "name": "latent-sre",
                "plugins": [
                    {
                        "name": "save-toolkit",
                        "source": {
                            "source": "local",
                            "path": "./plugins/save-toolkit",
                        },
                    }
                ],
            }
        ),
        "plugin.json": _json_bytes(
            {
                "name": "save-toolkit",
                "version": version,
            }
        ),
        "plugins/save-toolkit/.codex-plugin/plugin.json": _json_bytes(
            {
                "name": "save-toolkit",
                "version": version,
                "skills": "./skills/",
            }
        ),
        "plugins/save-toolkit/skills/demo/SKILL.md": b"---\nname: demo\n---\n# Demo\n",
        ".codex/agents/save-toolkit-demo.toml": (
            b'name = "save-toolkit-demo"\n'
            b'description = "demo"\n'
            b'sandbox_mode = "workspace-write"\n'
            b"developer_instructions = '''\nDemo instructions.\n'''\n"
        ),
    }


def _tar_bytes(
    files: dict[str, bytes] | None = None,
    *,
    sha: str = CURRENT,
    extra_members: list[tuple[tarfile.TarInfo, bytes | None]] | None = None,
) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(
        fileobj=buffer,
        mode="w",
        format=tarfile.PAX_FORMAT,
        pax_headers={"comment": sha},
    ) as archive:
        for name, content in (files or {}).items():
            member = tarfile.TarInfo(name)
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))
        for member, content in extra_members or []:
            if content is not None:
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))
            else:
                archive.addfile(member)
    return buffer.getvalue()


def _completed(archive: bytes) -> subprocess.CompletedProcess[bytes]:
    return subprocess.CompletedProcess(args=(), returncode=0, stdout=archive, stderr=b"")


def _materialize_mocked(
    destination: Path,
    *,
    archive: bytes | None = None,
    sha: str = CURRENT,
    fixture_root: Path | None = None,
) -> codex_snapshot.SnapshotReceipt:
    payload = archive if archive is not None else _tar_bytes(_valid_files(), sha=sha)
    git_executable = (fixture_root or destination.parent) / (
        "test-git.exe" if sys.platform == "win32" else "test-git"
    )
    git_executable.write_bytes(b"fixed test git executable")
    git_digest = hashlib.sha256(git_executable.read_bytes()).hexdigest()
    try:
        expected_files = codex_snapshot._parse_archive(payload, sha)
        expected_tree = codex_snapshot._tree_sha256(expected_files)
    except codex_snapshot.SnapshotError:
        expected_tree = "0" * 64
    with (
        mock.patch.object(codex_snapshot, "GIT_EXECUTABLE_PATH", git_executable.resolve()),
        mock.patch.object(codex_snapshot, "GIT_EXECUTABLE_SHA256", git_digest),
        mock.patch.object(
            codex_snapshot, "EXPECTED_SNAPSHOT_TREE_SHA256", {sha: expected_tree}
        ),
        mock.patch.object(codex_snapshot.subprocess, "run", return_value=_completed(payload)),
    ):
        return codex_snapshot.materialize_snapshot(
            ROOT, sha, destination, git_executable=git_executable
        )


class MaterializeSnapshotTests(unittest.TestCase):
    def test_materialization_uses_the_caller_supplied_bounded_git_runner(self) -> None:
        files = _valid_files()
        archive = _tar_bytes(files)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(strict=True)
            destination = root / "snapshot"
            destination.mkdir()
            git_executable = root / ("git.exe" if sys.platform == "win32" else "git")
            git_executable.write_bytes(b"fixed test git executable")
            runner = mock.Mock(return_value=_completed(archive))
            with (
                mock.patch.object(codex_snapshot, "GIT_EXECUTABLE_PATH", git_executable.resolve()),
                mock.patch.object(
                    codex_snapshot,
                    "GIT_EXECUTABLE_SHA256",
                    hashlib.sha256(git_executable.read_bytes()).hexdigest(),
                ),
                mock.patch.object(
                    codex_snapshot,
                    "EXPECTED_SNAPSHOT_TREE_SHA256",
                    {CURRENT: codex_snapshot._tree_sha256(files)},
                ),
            ):
                codex_snapshot.materialize_snapshot(
                    ROOT,
                    CURRENT,
                    destination,
                    git_executable=git_executable,
                    command_runner=runner,
                )

        self.assertEqual(1, runner.call_count)

    def test_materialization_requires_pinned_absolute_git_and_scrubbed_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(strict=True)
            destination = root / "snapshot"
            destination.mkdir()
            git_executable = root / ("git.exe" if sys.platform == "win32" else "git")
            git_executable.write_bytes(b"fixed test git executable")
            expected_digest = hashlib.sha256(git_executable.read_bytes()).hexdigest()
            with (
                mock.patch.object(
                    codex_snapshot, "GIT_EXECUTABLE_PATH", git_executable.resolve()
                ),
                mock.patch.object(
                    codex_snapshot, "GIT_EXECUTABLE_SHA256", expected_digest
                ),
                mock.patch.object(
                    codex_snapshot,
                    "EXPECTED_SNAPSHOT_TREE_SHA256",
                    {CURRENT: codex_snapshot._tree_sha256(_valid_files())},
                ),
                mock.patch.object(
                    codex_snapshot.subprocess,
                    "run",
                    return_value=_completed(_tar_bytes(_valid_files())),
                ) as run,
            ):
                codex_snapshot.materialize_snapshot(
                    ROOT,
                    CURRENT,
                    destination,
                    git_executable=git_executable,
                )

            command = run.call_args.args[0]
            options = run.call_args.kwargs
            self.assertEqual(str(git_executable.resolve()), command[0])
            self.assertEqual(destination.resolve(), options["cwd"])
            self.assertEqual("1", options["env"]["GIT_CONFIG_NOSYSTEM"])
            self.assertEqual("1", options["env"]["GIT_NO_REPLACE_OBJECTS"])
            self.assertEqual("0", options["env"]["GIT_CONFIG_COUNT"])
            self.assertTrue(Path(options["env"]["COMSPEC"]).is_absolute())
            self.assertTrue(options["env"]["PATH"])
            self.assertNotIn(str(ROOT.resolve()), json.dumps(options["env"]))

    def test_materializes_only_the_fixed_git_archive_paths_create_only(self) -> None:
        files = _valid_files()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(strict=True)
            destination = root / "snapshot"
            destination.mkdir()
            git_executable = root / ("git.exe" if sys.platform == "win32" else "git")
            git_executable.write_bytes(b"fixed test git executable")
            with (
                mock.patch.object(
                    codex_snapshot, "GIT_EXECUTABLE_PATH", git_executable.resolve()
                ),
                mock.patch.object(
                    codex_snapshot,
                    "GIT_EXECUTABLE_SHA256",
                    hashlib.sha256(git_executable.read_bytes()).hexdigest(),
                ),
                mock.patch.object(
                    codex_snapshot,
                    "EXPECTED_SNAPSHOT_TREE_SHA256",
                    {CURRENT: codex_snapshot._tree_sha256(files)},
                ),
                mock.patch.object(
                    codex_snapshot.subprocess,
                    "run",
                    return_value=_completed(_tar_bytes(files)),
                ) as run,
            ):
                receipt = codex_snapshot.materialize_snapshot(
                    ROOT, CURRENT, destination, git_executable=git_executable
                )

            command = run.call_args.args[0]
            self.assertEqual(
                [
                    str(git_executable.resolve()),
                    "--no-pager",
                    "--no-replace-objects",
                    f"--git-dir={ROOT.resolve() / '.git'}",
                    "archive",
                    "--format=tar",
                    CURRENT,
                    "--",
                    ".agents/plugins/marketplace.json",
                    "plugins/save-toolkit",
                    ".codex/agents",
                    "plugin.json",
                ],
                command,
            )
            actual = {
                path.relative_to(destination).as_posix(): path.read_bytes()
                for path in destination.rglob("*")
                if path.is_file()
            }

        self.assertEqual(files, actual)
        self.assertEqual(CURRENT, receipt.commit_sha)
        self.assertEqual(len(files), receipt.file_count)
        self.assertEqual(sum(map(len, files.values())), receipt.total_bytes)
        self.assertRegex(receipt.tree_sha256, r"^[0-9a-f]{64}$")
        self.assertNotIn(str(ROOT), repr(receipt))

    def test_materializes_both_real_route_git_objects(self) -> None:
        resolved_git = shutil.which("git")
        if resolved_git is None:
            self.skipTest("Git is unavailable")
        git_executable = Path(resolved_git).resolve(strict=True)
        git_digest = hashlib.sha256(git_executable.read_bytes()).hexdigest()
        for sha in (BEFORE, CURRENT):
            with self.subTest(sha=sha), tempfile.TemporaryDirectory() as temporary:
                destination = Path(temporary).resolve(strict=True) / "snapshot"
                destination.mkdir()
                with (
                    mock.patch.object(codex_snapshot, "GIT_EXECUTABLE_PATH", git_executable),
                    mock.patch.object(codex_snapshot, "GIT_EXECUTABLE_SHA256", git_digest),
                ):
                    receipt = codex_snapshot.materialize_snapshot(
                        ROOT, sha, destination, git_executable=git_executable
                    )

                self.assertEqual(sha, receipt.commit_sha)
                self.assertGreater(receipt.file_count, 10)
                self.assertTrue((destination / ".agents/plugins/marketplace.json").is_file())
                self.assertTrue((destination / "plugin.json").is_file())
                self.assertTrue(
                    (destination / "plugins/save-toolkit/.codex-plugin/plugin.json").is_file()
                )

    def test_rejects_any_revision_outside_the_two_fixed_full_shas(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary).resolve(strict=True) / "snapshot"
            destination.mkdir()
            for revision in ("main", CURRENT[:12], "f" * 40, CURRENT.upper()):
                with self.subTest(revision=revision):
                    with self.assertRaises(codex_snapshot.SnapshotError):
                        codex_snapshot.materialize_snapshot(ROOT, revision, destination)

    def test_rejects_a_different_repository_root_before_running_git(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            other = Path(temporary).resolve(strict=True) / "other"
            other.mkdir()
            destination = Path(temporary).resolve(strict=True) / "snapshot"
            destination.mkdir()
            with mock.patch.object(codex_snapshot.subprocess, "run") as run:
                with self.assertRaises(codex_snapshot.SnapshotError):
                    codex_snapshot.materialize_snapshot(other, CURRENT, destination)
            run.assert_not_called()

    def test_rejects_git_failure_missing_or_mismatched_commit_proof(self) -> None:
        cases = {
            "git-failure": subprocess.CompletedProcess(
                args=(), returncode=128, stdout=b"", stderr=b"private diagnostic"
            ),
            "missing-proof": _completed(_tar_bytes(_valid_files(), sha="")),
            "wrong-proof": _completed(_tar_bytes(_valid_files(), sha=BEFORE)),
        }
        for label, result in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                destination = Path(temporary).resolve(strict=True) / "snapshot"
                destination.mkdir()
                with mock.patch.object(codex_snapshot.subprocess, "run", return_value=result):
                    with self.assertRaises(codex_snapshot.SnapshotError) as caught:
                        codex_snapshot.materialize_snapshot(ROOT, CURRENT, destination)
                self.assertNotIn("private diagnostic", str(caught.exception))
                self.assertEqual([], list(destination.iterdir()))

    def test_rejects_unsafe_or_out_of_scope_member_names(self) -> None:
        cases = {
            "absolute": "/outside",
            "windows-absolute": "C:/outside",
            "traversal": "plugins/save-toolkit/skills/../outside",
            "backslash": r"plugins\save-toolkit\skills\outside",
            "dot-segment": "plugins/save-toolkit/./outside",
            "double-separator": "plugins/save-toolkit//outside",
            "out-of-scope": "AGENTS.md",
        }
        for label, name in cases.items():
            files = _valid_files()
            files[name] = b"unsafe"
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                destination = Path(temporary).resolve(strict=True) / "snapshot"
                destination.mkdir()
                with self.assertRaises(codex_snapshot.SnapshotError):
                    _materialize_mocked(destination, archive=_tar_bytes(files))
                self.assertEqual([], list(destination.iterdir()))

    def test_rejects_duplicate_and_casefold_colliding_names(self) -> None:
        duplicate = tarfile.TarInfo("plugins/save-toolkit/skills/demo/SKILL.md")
        casefold = tarfile.TarInfo(".codex/agents/SAVE-TOOLKIT-DEMO.TOML")
        for label, member in (("duplicate", duplicate), ("casefold", casefold)):
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                destination = Path(temporary).resolve(strict=True) / "snapshot"
                destination.mkdir()
                archive = _tar_bytes(
                    _valid_files(), extra_members=[(member, b"collision")]
                )
                with self.assertRaises(codex_snapshot.SnapshotError):
                    _materialize_mocked(destination, archive=archive)
                self.assertEqual([], list(destination.iterdir()))

    def test_rejects_links_devices_fifo_and_other_nonordinary_members(self) -> None:
        cases = {
            "symlink": tarfile.SYMTYPE,
            "hardlink": tarfile.LNKTYPE,
            "character-device": tarfile.CHRTYPE,
            "block-device": tarfile.BLKTYPE,
            "fifo": tarfile.FIFOTYPE,
        }
        for label, member_type in cases.items():
            member = tarfile.TarInfo("plugins/save-toolkit/skills/demo/unsafe")
            member.type = member_type
            member.linkname = "plugin.json"
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                destination = Path(temporary).resolve(strict=True) / "snapshot"
                destination.mkdir()
                archive = _tar_bytes(_valid_files(), extra_members=[(member, None)])
                with self.assertRaises(codex_snapshot.SnapshotError):
                    _materialize_mocked(destination, archive=archive)
                self.assertEqual([], list(destination.iterdir()))

    def test_rejects_empty_archive_empty_file_and_oversize_input(self) -> None:
        empty_file = _valid_files()
        empty_file["plugins/save-toolkit/skills/demo/empty.txt"] = b""
        oversize = _valid_files()
        oversize["plugins/save-toolkit/skills/demo/large.bin"] = b"x" * 11
        cases = {
            "empty-archive": _tar_bytes({}, sha=CURRENT),
            "empty-file": _tar_bytes(empty_file),
            "oversize-file": _tar_bytes(oversize),
        }
        for label, archive in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                destination = Path(temporary).resolve(strict=True) / "snapshot"
                destination.mkdir()
                limit = 10 if label == "oversize-file" else codex_snapshot.MAX_FILE_BYTES
                with mock.patch.object(codex_snapshot, "MAX_FILE_BYTES", limit):
                    with self.assertRaises(codex_snapshot.SnapshotError):
                        _materialize_mocked(destination, archive=archive)
                self.assertEqual([], list(destination.iterdir()))

        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary).resolve(strict=True) / "snapshot"
            destination.mkdir()
            archive = _tar_bytes(_valid_files())
            with mock.patch.object(codex_snapshot, "MAX_ARCHIVE_BYTES", len(archive) - 1):
                with self.assertRaises(codex_snapshot.SnapshotError):
                    _materialize_mocked(destination, archive=archive)

    def test_rejects_missing_malformed_or_inconsistent_manifests_before_write(self) -> None:
        missing = _valid_files()
        del missing["plugin.json"]
        malformed = _valid_files()
        malformed[".agents/plugins/marketplace.json"] = b"[]"
        inconsistent = _valid_files()
        inconsistent["plugins/save-toolkit/.codex-plugin/plugin.json"] = _json_bytes(
            {"name": "save-toolkit", "version": "9.9.9", "skills": "./skills/"}
        )
        duplicate_key = _valid_files()
        duplicate_key["plugin.json"] = b'{"name":"save-toolkit","name":"other","version":"0.1.0"}'
        for label, files in {
            "missing": missing,
            "malformed": malformed,
            "inconsistent": inconsistent,
            "duplicate-json-key": duplicate_key,
        }.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                destination = Path(temporary).resolve(strict=True) / "snapshot"
                destination.mkdir()
                with self.assertRaises(codex_snapshot.SnapshotError):
                    _materialize_mocked(destination, archive=_tar_bytes(files))
                self.assertEqual([], list(destination.iterdir()))

    def test_destination_must_be_an_empty_normal_directory_outside_the_repo(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(strict=True)
            nonempty = root / "nonempty"
            nonempty.mkdir()
            (nonempty / "owned.txt").write_text("keep", encoding="utf-8")
            missing = root / "missing"
            regular_file = root / "file"
            regular_file.write_text("keep", encoding="utf-8")
            for label, destination in {
                "nonempty": nonempty,
                "missing": missing,
                "file": regular_file,
                "repository": ROOT,
            }.items():
                with self.subTest(label=label):
                    with self.assertRaises(codex_snapshot.SnapshotError):
                        _materialize_mocked(destination, fixture_root=root)
            self.assertEqual("keep", (nonempty / "owned.txt").read_text(encoding="utf-8"))
            self.assertEqual("keep", regular_file.read_text(encoding="utf-8"))


class NeutralProjectStageTests(unittest.TestCase):
    def _snapshot(self, root: Path) -> tuple[Path, dict[str, bytes]]:
        files = _valid_files()
        snapshot = root / "snapshot"
        snapshot.mkdir()
        _materialize_mocked(snapshot, archive=_tar_bytes(files))
        return snapshot, files

    def test_stages_only_skills_and_agents_with_exact_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(strict=True)
            snapshot, files = self._snapshot(root)
            workspace = root / "workspace"
            workspace.mkdir()

            receipt = codex_snapshot.stage_neutral_project(snapshot, workspace)

            actual = {
                path.relative_to(workspace).as_posix(): path.read_bytes()
                for path in workspace.rglob("*")
                if path.is_file()
            }
            expected = {
                ".agents/skills/demo/SKILL.md": files[
                    "plugins/save-toolkit/skills/demo/SKILL.md"
                ],
                ".codex/agents/save-toolkit-demo.toml": (
                    b'name = "save-toolkit-demo"\n'
                    b'description = "demo"\n'
                    b"developer_instructions = '''\nDemo instructions.\n'''\n"
                ),
            }

        self.assertEqual(expected, actual)
        self.assertEqual(1, receipt.skill_file_count)
        self.assertEqual(1, receipt.agent_file_count)
        self.assertEqual(1, receipt.transformed_agent_file_count)
        self.assertEqual(sum(map(len, expected.values())), receipt.total_bytes)
        self.assertRegex(receipt.skill_tree_sha256, r"^[0-9a-f]{64}$")
        self.assertRegex(receipt.source_agent_tree_sha256, r"^[0-9a-f]{64}$")
        self.assertRegex(receipt.staged_agent_tree_sha256, r"^[0-9a-f]{64}$")
        self.assertNotEqual(
            receipt.source_agent_tree_sha256, receipt.staged_agent_tree_sha256
        )
        self.assertRegex(receipt.project_tree_sha256, r"^[0-9a-f]{64}$")
        self.assertNotIn("SKILL.md", repr(receipt))

    def test_stages_both_real_route_snapshots_and_transforms_every_agent(self) -> None:
        resolved_git = shutil.which("git")
        if resolved_git is None:
            self.skipTest("Git is unavailable")
        git_executable = Path(resolved_git).resolve(strict=True)
        git_digest = hashlib.sha256(git_executable.read_bytes()).hexdigest()
        for sha in (BEFORE, CURRENT):
            with self.subTest(sha=sha), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve(strict=True)
                snapshot = root / "snapshot"
                snapshot.mkdir()
                with (
                    mock.patch.object(codex_snapshot, "GIT_EXECUTABLE_PATH", git_executable),
                    mock.patch.object(codex_snapshot, "GIT_EXECUTABLE_SHA256", git_digest),
                ):
                    codex_snapshot.materialize_snapshot(
                        ROOT, sha, snapshot, git_executable=git_executable
                    )
                workspace = root / "workspace"
                workspace.mkdir()

                receipt = codex_snapshot.stage_neutral_project(snapshot, workspace)

                staged_agents = sorted((workspace / ".codex/agents").glob("*.toml"))
                self.assertEqual(receipt.agent_file_count, len(staged_agents))
                self.assertEqual(
                    receipt.agent_file_count, receipt.transformed_agent_file_count
                )
                self.assertGreater(receipt.skill_file_count, receipt.agent_file_count)
                self.assertNotEqual(
                    receipt.source_agent_tree_sha256,
                    receipt.staged_agent_tree_sha256,
                )
                for agent in staged_agents:
                    self.assertFalse(
                        any(
                            line.startswith(b"sandbox_mode")
                            for line in agent.read_bytes().splitlines()
                        ),
                        agent.name,
                    )

    def test_requires_nonempty_skill_and_agent_sets(self) -> None:
        for missing in ("skills", "agents"):
            with self.subTest(missing=missing), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve(strict=True)
                snapshot, _files = self._snapshot(root)
                target = (
                    snapshot / "plugins/save-toolkit/skills/demo/SKILL.md"
                    if missing == "skills"
                    else snapshot / ".codex/agents/save-toolkit-demo.toml"
                )
                target.unlink()
                workspace = root / "workspace"
                workspace.mkdir()

                with self.assertRaises(codex_snapshot.SnapshotError):
                    codex_snapshot.stage_neutral_project(snapshot, workspace)
                self.assertEqual([], list(workspace.iterdir()))

    def test_rejects_non_neutral_or_prepopulated_target_roots_create_only(self) -> None:
        cases = {
            "instructions": ("AGENTS.md", b"untrusted instructions"),
            "existing-skill": (".agents/skills/demo/SKILL.md", b"old"),
            "existing-agent": (".codex/agents/save-toolkit-demo.toml", b"old"),
        }
        for label, (relative, content) in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve(strict=True)
                snapshot, _files = self._snapshot(root)
                workspace = root / "workspace"
                target = workspace / relative
                target.parent.mkdir(parents=True)
                target.write_bytes(content)

                with self.assertRaises(codex_snapshot.SnapshotError):
                    codex_snapshot.stage_neutral_project(snapshot, workspace)
                self.assertEqual(content, target.read_bytes())

    def test_rejects_source_or_workspace_link_indirection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(strict=True)
            snapshot, _files = self._snapshot(root)
            real_skills = snapshot / "plugins/save-toolkit/skills-real"
            source_skills = snapshot / "plugins/save-toolkit/skills"
            source_skills.rename(real_skills)
            try:
                source_skills.symlink_to(real_skills, target_is_directory=True)
            except OSError as exc:
                self.skipTest(f"directory symlinks unavailable: {exc}")
            workspace = root / "workspace"
            workspace.mkdir()

            with self.assertRaises(codex_snapshot.SnapshotError):
                codex_snapshot.stage_neutral_project(snapshot, workspace)

    def test_reparse_signal_on_an_intermediate_source_component_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(strict=True)
            snapshot, _files = self._snapshot(root)
            workspace = root / "workspace"
            workspace.mkdir()
            indirect = (snapshot / "plugins").resolve()
            original = codex_snapshot._is_link_or_reparse

            def is_indirect(path: Path) -> bool:
                return path.resolve() == indirect or original(path)

            with mock.patch.object(
                codex_snapshot, "_is_link_or_reparse", side_effect=is_indirect
            ):
                with self.assertRaises(codex_snapshot.SnapshotError):
                    codex_snapshot.stage_neutral_project(snapshot, workspace)

    def test_post_copy_mutation_is_detected_as_exact_copy_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(strict=True)
            snapshot, _files = self._snapshot(root)
            workspace = root / "workspace"
            workspace.mkdir()
            original = codex_snapshot._copy_plan_create_only

            def corrupt_after_copy(*args: object, **kwargs: object) -> None:
                original(*args, **kwargs)
                target = workspace / ".agents/skills/demo/SKILL.md"
                target.write_bytes(b"drift")

            with mock.patch.object(
                codex_snapshot, "_copy_plan_create_only", side_effect=corrupt_after_copy
            ):
                with self.assertRaises(codex_snapshot.SnapshotError):
                    codex_snapshot.stage_neutral_project(snapshot, workspace)

    def test_post_stage_verifier_detects_later_workspace_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(strict=True)
            snapshot, _files = self._snapshot(root)
            workspace = root / "workspace"
            workspace.mkdir()
            receipt = codex_snapshot.stage_neutral_project(snapshot, workspace)

            codex_snapshot.verify_staged_project(snapshot, workspace, receipt)
            (workspace / ".agents/skills/demo/SKILL.md").write_bytes(b"later drift")

            with self.assertRaises(codex_snapshot.SnapshotError):
                codex_snapshot.verify_staged_project(snapshot, workspace, receipt)

    def test_post_stage_verifier_rejects_a_late_git_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(strict=True)
            snapshot, _files = self._snapshot(root)
            workspace = root / "workspace"
            workspace.mkdir()
            receipt = codex_snapshot.stage_neutral_project(snapshot, workspace)
            (workspace / ".git").mkdir()

            with self.assertRaises(codex_snapshot.SnapshotError):
                codex_snapshot.verify_staged_project(snapshot, workspace, receipt)

    def test_agent_transform_cannot_change_any_other_byte(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(strict=True)
            snapshot, _files = self._snapshot(root)
            workspace = root / "workspace"
            workspace.mkdir()
            source = (
                snapshot / ".codex/agents/save-toolkit-demo.toml"
            ).read_bytes()
            malicious = source.replace(b'sandbox_mode = "workspace-write"\n', b"")
            malicious = malicious.replace(b"Demo instructions.", b"Changed instructions.")

            with mock.patch.object(
                codex_snapshot, "transform_agent_toml", return_value=malicious
            ):
                with self.assertRaises(codex_snapshot.SnapshotError):
                    codex_snapshot.stage_neutral_project(snapshot, workspace)


class AgentTransformTests(unittest.TestCase):
    def test_removes_exactly_one_top_level_sandbox_assignment(self) -> None:
        source = (
            b"# generated\n"
            b'name = "save-toolkit-demo"\n'
            b'description = "demo"\n'
            b'sandbox_mode = "read-only"\n'
            b"developer_instructions = '''\n"
            b'- prose mentions `sandbox_mode = "read-only"` without assigning it\n'
            b"'''\n"
        )
        expected = source.replace(b'sandbox_mode = "read-only"\n', b"", 1)

        transformed = codex_snapshot.transform_agent_toml(source)

        self.assertEqual(expected, transformed)

    def test_missing_duplicate_or_malformed_sandbox_assignment_is_rejected(self) -> None:
        prefix = b'name = "save-toolkit-demo"\n'
        suffix = b"developer_instructions = '''\nDemo.\n'''\n"
        cases = {
            "missing": prefix + suffix,
            "duplicate": (
                prefix
                + b'sandbox_mode = "read-only"\n'
                + b'sandbox_mode = "workspace-write"\n'
                + suffix
            ),
            "malformed-type": prefix + b'sandbox_mode = ["read-only"]\n' + suffix,
            "malformed-spacing": prefix + b'sandbox_mode="read-only"\n' + suffix,
        }
        for label, source in cases.items():
            with self.subTest(label=label):
                with self.assertRaises(codex_snapshot.SnapshotError):
                    codex_snapshot.transform_agent_toml(source)

    def test_extra_custom_agent_configuration_is_rejected(self) -> None:
        source = (
            b'name = "save-toolkit-demo"\n'
            b'description = "demo"\n'
            b'sandbox_mode = "read-only"\n'
            b"developer_instructions = '''\nDemo.\n'''\n"
            b"[features]\n"
            b"shell_tool = true\n"
        )

        with self.assertRaisesRegex(
            codex_snapshot.SnapshotError,
            "unsupported configuration fields",
        ):
            codex_snapshot.transform_agent_toml(source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
