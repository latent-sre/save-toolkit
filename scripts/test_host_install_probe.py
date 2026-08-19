"""Safety and schema tests for the disposable host install probe."""

from __future__ import annotations

import hashlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import evidence_envelope
import fleet_doctor
import host_install_probe as probe
import install_codex_agents


REPO = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 4, tzinfo=timezone.utc)
RELEASE_SOURCE = "latent-sre/save-toolkit@save-toolkit--v1.2.3"
REPOSITORY_VERSION = json.loads(
    REPO.joinpath(".claude-plugin", "plugin.json").read_text(encoding="utf-8")
)["version"]

_RELEASE_FIXTURE_FILES = {
    ".claude-plugin/plugin.json": b'{"name":"save-toolkit","version":"1.2.3"}\n',
    "plugin.json": b'{"name":"save-toolkit","version":"1.2.3"}\n',
    "skills/fixture/SKILL.md": b"release fixture\r\n",
    "plugins/save-toolkit/.codex-plugin/plugin.json": (
        b'{"name":"save-toolkit","version":"1.2.3"}\n'
    ),
    "plugins/save-toolkit/skills/fixture/SKILL.md": b"release fixture\r\n",
}


def _write_release_checkout(checkout: Path, *, host: str) -> Path:
    """Materialize a tiny remote-checkout fixture and return the host's plugin source root."""

    checkout.mkdir(parents=True, exist_ok=True)
    checkout.joinpath(".git").mkdir()
    for relative, content in _RELEASE_FIXTURE_FILES.items():
        destination = checkout / Path(relative)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
    if host == "claude":
        return checkout
    if host == "codex":
        return checkout / "plugins" / "save-toolkit"
    raise AssertionError(f"unknown release checkout host: {host}")


def _write_installed_fixture(source: Path, installed: Path, variant: str = "exact") -> None:
    if variant == "missing-root":
        return
    shutil.copytree(source, installed, ignore=shutil.ignore_patterns(".git"))
    payload = installed / "skills" / "fixture" / "SKILL.md"
    if variant == "missing":
        payload.unlink()
    elif variant == "extra":
        installed.joinpath("unexpected.txt").write_text("extra\n", encoding="utf-8")
    elif variant == "changed":
        payload.write_bytes(b"changed byte\n")
    elif variant == "indirect":
        installed.joinpath("indirect.txt").write_text("ordinary fixture\n", encoding="utf-8")
    elif variant != "exact":
        raise AssertionError(f"unknown installed-tree fixture variant: {variant}")


def _mutate_source_fixture(source: Path, variant: str) -> None:
    """Make source and installed bytes agree on a tree that is not the tagged tree."""

    payload = source / "skills" / "fixture" / "SKILL.md"
    if variant == "extra":
        source.joinpath("ignored-extra.txt").write_text("not in HEAD\n", encoding="utf-8")
    elif variant == "changed":
        payload.write_bytes(b"same non-HEAD bytes\n")
    elif variant == "missing":
        payload.unlink()
    elif variant == "empty":
        for entry in tuple(source.iterdir()):
            if entry.name == ".git":
                continue
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()
    else:
        raise AssertionError(f"unknown source-tree fixture variant: {variant}")


def _git_blob_oid(content: bytes, *, object_id_length: int = 40) -> str:
    payload = b"blob " + str(len(content)).encode("ascii") + b"\0" + content
    if object_id_length == 40:
        return hashlib.sha1(payload, usedforsecurity=False).hexdigest()
    if object_id_length == 64:
        return hashlib.sha256(payload).hexdigest()
    raise AssertionError(f"unsupported Git object id length: {object_id_length}")


def _git_tree_output(variant: str = "exact", *, object_id_length: int = 40) -> str:
    entries = [
        [
            "100644",
            "blob",
            _git_blob_oid(content, object_id_length=object_id_length),
            relative,
        ]
        for relative, content in sorted(_RELEASE_FIXTURE_FILES.items())
    ]
    selected = {
        "skills/fixture/SKILL.md",
        "plugins/save-toolkit/skills/fixture/SKILL.md",
    }
    manifests = {
        ".claude-plugin/plugin.json",
        "plugins/save-toolkit/.codex-plugin/plugin.json",
    }
    if variant in {"symlink", "gitlink", "special", "head-diff", "changed-claude"}:
        for entry in entries:
            if entry[3] not in selected:
                continue
            if variant == "symlink":
                entry[0] = "120000"
            elif variant == "gitlink":
                entry[0], entry[1], entry[2] = (
                    "160000",
                    "commit",
                    "b" * object_id_length,
                )
            elif variant == "special":
                entry[0] = "100664"
            elif variant == "head-diff":
                entry[2] = "b" * object_id_length
            elif entry[3] == "skills/fixture/SKILL.md":
                entry[2] = _git_blob_oid(
                    b"same non-HEAD bytes\n", object_id_length=object_id_length
                )
    elif variant == "executable":
        for entry in entries:
            if entry[3] in selected:
                entry[0] = "100755"
    elif variant == "non-blob-type":
        for entry in entries:
            if entry[3] in selected:
                entry[1] = "tree"
    elif variant == "casefold-collision":
        entries.extend(
            [entry[:3] + [entry[3].casefold()] for entry in entries if entry[3] in selected]
        )
    elif variant == "duplicate":
        entries.extend([entry.copy() for entry in entries if entry[3] in selected])
    elif variant == "unsafe":
        entries.extend(
            [
                [
                    "100644",
                    "blob",
                    _git_blob_oid(b"unsafe\n", object_id_length=object_id_length),
                    "../escape",
                ],
                [
                    "100644",
                    "blob",
                    _git_blob_oid(b"unsafe\n", object_id_length=object_id_length),
                    "plugins/save-toolkit/../escape",
                ],
            ]
        )
    elif variant == "empty":
        entries = []
    elif variant == "missing-manifest":
        entries = [entry for entry in entries if entry[3] not in manifests]
    elif variant == "malformed":
        return "not-a-tree-record\0"
    elif variant == "replacement-character":
        return (
            "100644 blob "
            + "a" * object_id_length
            + "\tbad-\ufffd-name\0"
        )
    elif variant != "exact":
        raise AssertionError(f"unknown Git tree fixture variant: {variant}")
    return "".join(" ".join(entry[:3]) + "\t" + entry[3] + "\0" for entry in entries)


def git_with_tree_variant(variant: str, *, object_id_length: int = 40):
    revision = "a" * object_id_length

    def run(argv: tuple[str, ...]) -> probe.CommandResult:
        if tuple(argv[-2:]) == ("rev-parse", "HEAD"):
            return probe.CommandResult(0, revision + "\n", "")
        if tuple(argv[-3:]) == ("rev-parse", "--verify", "HEAD^{commit}"):
            return probe.CommandResult(0, revision + "\n", "")
        if tuple(argv[-2:]) == ("status", "--short"):
            return probe.CommandResult(0, "", "")
        if tuple(argv[-4:-1]) == ("ls-tree", "-rz", "--full-tree"):
            return probe.CommandResult(
                0,
                _git_tree_output(variant, object_id_length=object_id_length),
                "",
            )
        raise AssertionError(f"unexpected git argv: {argv!r}")

    return run


def fake_git(argv: tuple[str, ...]) -> probe.CommandResult:
    return git_with_tree_variant("exact")(argv)


def git_with_switched_head(argv: tuple[str, ...]) -> probe.CommandResult:
    if tuple(argv[-2:]) == ("rev-parse", "HEAD"):
        return probe.CommandResult(0, "a" * 40 + "\n", "")
    if tuple(argv[-3:]) == ("rev-parse", "--verify", "HEAD^{commit}"):
        return probe.CommandResult(0, "a" * 40 + "\n", "")
    if tuple(argv[-2:]) == ("status", "--short"):
        return probe.CommandResult(0, "", "")
    if tuple(argv[-4:-1]) == ("ls-tree", "-rz", "--full-tree"):
        variant = "changed-claude" if argv[-1] == "HEAD" else "exact"
        return probe.CommandResult(0, _git_tree_output(variant), "")
    raise AssertionError(f"unexpected git argv: {argv!r}")


def git_with_dirty_marketplace(argv: tuple[str, ...]) -> probe.CommandResult:
    if tuple(argv[-3:]) == ("rev-parse", "--verify", "HEAD^{commit}"):
        return probe.CommandResult(0, "a" * 40 + "\n", "")
    if tuple(argv[-4:-1]) == ("ls-tree", "-rz", "--full-tree"):
        return probe.CommandResult(0, _git_tree_output("head-diff"), "")
    if tuple(argv[-2:]) == ("rev-parse", "HEAD"):
        return probe.CommandResult(0, "a" * 40 + "\n", "")
    if tuple(argv[-2:]) == ("status", "--short"):
        checkout = Path(argv[argv.index("-C") + 1]).resolve()
        if checkout != REPO.resolve():
            return probe.CommandResult(0, " M plugin.json\n", "")
        return probe.CommandResult(0, "", "")
    raise AssertionError(f"unexpected git argv: {argv!r}")


def version_only_run(argv: tuple[str, ...], env: object) -> probe.CommandResult:
    if tuple(argv[1:]) == ("--version",):
        return probe.CommandResult(0, "test-cli 1.0\n", "")
    raise AssertionError(f"unexpected CLI argv: {argv!r}")


def absent_which(command: str) -> None:
    return None


def make_which(**hosts: str):
    return lambda command: hosts.get(command)


def copilot_run(state: dict[str, object], envs: list[object]):
    def run(argv: tuple[str, ...], env: object) -> probe.CommandResult:
        envs.append(env)
        tail = tuple(argv[1:])
        if tail == ("--version",):
            return probe.CommandResult(0, "GitHub Copilot CLI 1.0.78\n", "")
        if tail[:3] == ("plugin", "marketplace", "add"):
            return probe.CommandResult(state["add_rc"], "", "")  # type: ignore[arg-type]
        if tail == ("plugin", "install", probe.COPILOT_PLUGIN_ID):
            state["installed"] = state["add_rc"] == 0
            return probe.CommandResult(state["install_rc"], "", "")  # type: ignore[arg-type]
        if tail == ("plugin", "list"):
            row = (
                "Installed plugins:\n  • save-toolkit@latent-sre (v1.0.0)\n"
                if state["installed"]
                else "No plugins installed.\n"
            )
            return probe.CommandResult(0, row, "")
        if tail == ("plugin", "uninstall", probe.COPILOT_PLUGIN_ID):
            if state["uninstall_rc"] == 0 and not state["residue"]:
                state["installed"] = False
            return probe.CommandResult(state["uninstall_rc"], "", "")  # type: ignore[arg-type]
        raise AssertionError(f"unexpected argv: {argv!r}")

    return run


def codex_run(
    state: dict[str, object], calls: list[tuple[str, ...]], envs: list[object]
):
    def run(argv: tuple[str, ...], env: object) -> probe.CommandResult:
        calls.append(argv)
        envs.append(env)
        tail = tuple(argv[1:])
        if tail == ("--version",):
            return probe.CommandResult(0, "codex-cli 0.147.0\n", "")
        if tail[:3] == ("plugin", "marketplace", "add"):
            if state.get("add_rc", 0) == 0:
                state["marketplace"] = True
                if tail[-1] == RELEASE_SOURCE:
                    checkout = (
                        Path(env["CODEX_HOME"])  # type: ignore[index]
                        / ".tmp"
                        / "marketplaces"
                        / probe.MARKETPLACE_NAME
                    )
                    state["checkout_path"] = checkout
                    state["plugin_source_path"] = _write_release_checkout(
                        checkout, host="codex"
                    )
                    source_variant = state.get("source_variant")
                    if isinstance(source_variant, str):
                        _mutate_source_fixture(
                            state["plugin_source_path"], source_variant  # type: ignore[arg-type]
                        )
            return probe.CommandResult(state.get("add_rc", 0), "", "")  # type: ignore[arg-type]
        if tail == ("plugin", "add", probe.CODEX_PLUGIN_ID):
            returncode = state.get("install_rc", 0)
            if returncode == 0 and state.get("add_rc", 0) == 0:
                state["installed"] = True
                source = state.get("plugin_source_path")
                if isinstance(source, Path):
                    cache = (
                        Path(env["CODEX_HOME"])  # type: ignore[index]
                        / "plugins"
                        / "cache"
                        / "latent-sre"
                        / "save-toolkit"
                        / "1.2.3"
                    )
                    state["installed_cache_path"] = cache
                    _write_installed_fixture(
                        source, cache, str(state.get("tree_variant", "exact"))
                    )
            return probe.CommandResult(returncode, "", "")  # type: ignore[arg-type]
        if tail == ("plugin", "list", "--json"):
            returncode = state.get("list_rc", 0)
            if state.get("malformed_json"):
                return probe.CommandResult(returncode, "{", "")  # type: ignore[arg-type]
            installed = bool(state.get("installed"))
            row = {
                "pluginId": state.get("inventory_plugin_id", probe.CODEX_PLUGIN_ID),
                "name": state.get("inventory_name", "save-toolkit"),
                "marketplaceName": state.get("inventory_marketplace", "latent-sre"),
                "version": str(state.get("version", REPOSITORY_VERSION)),
                "installed": state.get("inventory_installed", True),
                "enabled": state.get("inventory_enabled", True),
            }
            row_count = int(state.get("inventory_row_count", 1))
            rows = [row.copy() for _ in range(row_count)] if installed else []
            return probe.CommandResult(  # type: ignore[arg-type]
                returncode, json.dumps({"installed": rows, "available": []}), ""
            )
        if tail == ("plugin", "remove", probe.CODEX_PLUGIN_ID):
            returncode = state.get("uninstall_rc", 0)
            if returncode == 0 and not state.get("residue"):
                state["installed"] = False
            return probe.CommandResult(returncode, "", "")  # type: ignore[arg-type]
        if tail == ("plugin", "marketplace", "remove", "latent-sre"):
            returncode = state.get("marketplace_remove_rc", 0)
            if returncode == 0 and not state.get("marketplace_residue"):
                state["marketplace"] = False
            return probe.CommandResult(returncode, "", "")  # type: ignore[arg-type]
        if tail == ("plugin", "marketplace", "list", "--json"):
            rows = [{"name": "latent-sre"}] if state.get("marketplace") else []
            return probe.CommandResult(0, json.dumps({"marketplaces": rows}), "")
        raise AssertionError(f"unexpected argv: {argv!r}")

    return run


def checks_by_id(report: dict[str, object]) -> dict[str, dict[str, object]]:
    return {item["criterion"]: item for item in report["evidence"]}  # type: ignore[index]


class TargetValidationTests(unittest.TestCase):
    def test_rejects_repo_user_and_nonempty_locations(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            home = base / "home"
            home.mkdir()
            non_empty = base / "non-empty"
            non_empty.mkdir()
            non_empty.joinpath("file.txt").write_text("x", encoding="utf-8")
            rejected = (
                REPO,
                REPO / "inside-repo",
                home,
                home / ".codex" / "probe",
                non_empty,
                Path(base.anchor),
            )
            for target in rejected:
                with self.subTest(target=target):
                    with self.assertRaises(ValueError):
                        probe._validate_target(target, root=REPO, home=home)

    def test_accepts_fresh_child_and_creates_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            home = base / "home"
            home.mkdir()
            target = probe._validate_target(base / "fresh" / "target", root=REPO, home=home)
            self.assertTrue(target.is_dir())
            self.assertFalse(any(target.iterdir()))

    @unittest.skipIf(os.name == "nt", "symlink creation requires privilege on Windows")
    def test_os_resolved_ancestor_symlink_is_accepted(self) -> None:
        # macOS tempdirs live under /var, a symlink to /private/var; the probe target is created
        # fresh and removed afterwards, so resolved ancestors must not be rejected.
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            real = base / "real"
            real.mkdir()
            (base / "link").symlink_to(real, target_is_directory=True)
            home = base / "home"
            home.mkdir()
            target = probe._validate_target(base / "link" / "child" / "target", root=REPO, home=home)
            self.assertEqual(real / "child" / "target", target)
            self.assertTrue(target.is_dir())

    @unittest.skipIf(os.name == "nt", "symlink creation requires privilege on Windows")
    def test_target_that_is_itself_a_link_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary).resolve()
            real = base / "real"
            real.mkdir()
            (base / "linked-target").symlink_to(real, target_is_directory=True)
            home = base / "home"
            home.mkdir()
            with self.assertRaisesRegex(ValueError, "must not itself be a link"):
                probe._validate_target(base / "linked-target", root=REPO, home=home)

    def test_unknown_or_empty_host_selection_fails_before_any_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "target"
            for hosts in (("emacs",), ()):
                with self.subTest(hosts=hosts):
                    with self.assertRaises(ValueError):
                        probe.collect_report(
                            REPO, target=target, hosts=hosts, git_run=fake_git, now=NOW
                        )
            self.assertFalse(target.exists())


class CommandAllowlistTests(unittest.TestCase):
    def test_scoped_install_verbs_only(self) -> None:
        for argv in (
            ("claude", "--version"),
            ("codex", "--version"),
            ("code", "--version"),
            ("claude", "plugin", "list", "--json"),
            ("claude", "plugin", "marketplace", "add", str(REPO)),
            ("claude", "plugin", "marketplace", "list", "--json"),
            ("claude", "plugin", "marketplace", "remove", "latent-sre"),
            ("claude", "plugin", "install", "save-toolkit@latent-sre"),
            ("claude", "plugin", "uninstall", "save-toolkit@latent-sre"),
            ("copilot", "plugin", "list"),
            ("copilot", "plugin", "marketplace", "add", str(REPO)),
            ("copilot", "plugin", "install", "save-toolkit@latent-sre"),
            ("copilot", "plugin", "uninstall", "save-toolkit@latent-sre"),
        ):
            with self.subTest(argv=argv):
                probe._assert_probe_command(argv, root=REPO)

    def test_release_source_binds_claude_and_codex_verbs(self) -> None:
        for argv in (
            ("claude", "plugin", "marketplace", "add", RELEASE_SOURCE),
            ("codex", "plugin", "marketplace", "add", RELEASE_SOURCE),
            ("codex", "plugin", "add", "save-toolkit@latent-sre"),
            ("codex", "plugin", "list", "--json"),
            ("codex", "plugin", "remove", "save-toolkit@latent-sre"),
            ("codex", "plugin", "marketplace", "list", "--json"),
            ("codex", "plugin", "marketplace", "remove", "latent-sre"),
        ):
            with self.subTest(argv=argv):
                probe._assert_probe_command(
                    argv, root=REPO, marketplace_source=RELEASE_SOURCE
                )

    def test_release_source_rejects_unpinned_other_and_non_semver_refs(self) -> None:
        rejected = (
            "latent-sre/save-toolkit",
            "latent-sre/save-toolkit@main",
            "latent-sre/save-toolkit@save-toolkit--v01.2.3",
            "other/save-toolkit@save-toolkit--v1.2.3",
            "latent-sre/other@save-toolkit--v1.2.3",
            "https://github.com/latent-sre/save-toolkit@save-toolkit--v1.2.3",
        )
        for source in rejected:
            with self.subTest(source=source):
                with self.assertRaisesRegex(ValueError, "marketplace source"):
                    probe._normalize_marketplace_source(source, root=REPO)

    def test_rejects_model_sessions_remote_sources_and_drift(self) -> None:
        for argv in (
            ("claude", "-p", "say hi"),
            ("codex", "exec", "inspect this repo"),
            ("claude", "plugin", "marketplace", "add", "https://example.com/market"),
            ("claude", "plugin", "install", "save-toolkit"),
            ("claude", "plugin", "uninstall", "other-plugin@latent-sre"),
            ("codex", "plugin", "install", "save-toolkit@latent-sre"),
            ("copilot", "plugin", "marketplace", "add", "https://example.com/market"),
            ("copilot", "plugin", "install", "save-toolkit"),
            ("copilot", "--plugin-dir", str(REPO)),
            ("sh", "-c", "claude plugin list"),
            ("git", "rev-parse", "HEAD"),
        ):
            with self.subTest(argv=argv):
                with self.assertRaisesRegex(ValueError, "scoped allowlist"):
                    probe._assert_probe_command(argv, root=REPO)


class GitProvenanceCommandTests(unittest.TestCase):
    def _object_command(self, checkout: Path, *tail: str) -> tuple[str, ...]:
        return (
            "git",
            "--no-optional-locks",
            "--no-replace-objects",
            f"--git-dir={checkout / '.git'}",
            f"--work-tree={checkout}",
            *tail,
        )

    def test_accepts_only_repository_checks_and_exact_object_reads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            checkout = Path(temporary) / "checkout"
            checkout.joinpath(".git").mkdir(parents=True)
            accepted = (
                ("git", "--no-optional-locks", "-C", str(REPO), "rev-parse", "HEAD"),
                ("git", "--no-optional-locks", "-C", str(REPO), "status", "--short"),
                self._object_command(checkout, "rev-parse", "--verify", "HEAD^{commit}"),
                self._object_command(
                    checkout, "ls-tree", "-rz", "--full-tree", "a" * 40
                ),
            )
            for argv in accepted:
                with self.subTest(argv=argv):
                    probe._assert_host_git_command(argv)

    def test_rejects_mismatched_paths_moving_refs_and_other_git_reads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            checkout = base / "checkout"
            checkout.joinpath(".git").mkdir(parents=True)
            other = base / "other"
            other.joinpath(".git").mkdir(parents=True)
            rejected = (
                self._object_command(checkout, "rev-parse", "HEAD"),
                self._object_command(checkout, "ls-tree", "-rz", "--full-tree", "HEAD"),
                self._object_command(checkout, "ls-tree", "-rz", "--full-tree", "main"),
                self._object_command(checkout, "cat-file", "-p", "HEAD"),
                (
                    "git",
                    "--no-optional-locks",
                    "--no-replace-objects",
                    f"--git-dir={other / '.git'}",
                    f"--work-tree={checkout}",
                    "rev-parse",
                    "--verify",
                    "HEAD^{commit}",
                ),
            )
            for argv in rejected:
                with self.subTest(argv=argv):
                    with self.assertRaisesRegex(ValueError, "read-only allowlist"):
                        probe._assert_host_git_command(argv)

    def test_runner_scrubs_git_environment_before_object_reads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            checkout = Path(temporary) / "checkout"
            checkout.joinpath(".git").mkdir(parents=True)
            command = self._object_command(
                checkout, "rev-parse", "--verify", "HEAD^{commit}"
            )
            captured: dict[str, object] = {}

            def run(argv: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
                captured["argv"] = argv
                captured["env"] = kwargs["env"]
                return subprocess.CompletedProcess(argv, 0, "a" * 40 + "\n", "")

            with mock.patch.dict(
                os.environ,
                {
                    "GIT_DIR": "untrusted",
                    "GIT_OBJECT_DIRECTORY": "untrusted",
                    "GIT_CONFIG_PARAMETERS": "untrusted",
                },
                clear=False,
            ), mock.patch.object(probe.subprocess, "run", side_effect=run):
                result = probe._run_host_git(command)

            self.assertEqual(0, result.returncode)
            environment = captured["env"]
            self.assertIsInstance(environment, dict)
            self.assertNotIn("GIT_DIR", environment)
            self.assertNotIn("GIT_OBJECT_DIRECTORY", environment)
            self.assertNotIn("GIT_CONFIG_PARAMETERS", environment)
            self.assertEqual(os.devnull, environment["GIT_CONFIG_GLOBAL"])
            self.assertEqual("1", environment["GIT_CONFIG_NOSYSTEM"])
            self.assertEqual("1", environment["GIT_NO_REPLACE_OBJECTS"])


class ImmutableGitTreeProvenanceTests(unittest.TestCase):
    _HOST_TREES = (
        ("claude", "", ".claude-plugin/plugin.json"),
        ("codex", "plugins/save-toolkit", ".codex-plugin/plugin.json"),
    )

    def _fixture_tree(
        self, source_prefix: str, *, object_id_length: int = 40
    ) -> dict[str, str]:
        prefix = f"{source_prefix.strip('/')}/" if source_prefix else ""
        return {
            repository_path[len(prefix) :]: _git_blob_oid(
                content, object_id_length=object_id_length
            )
            for repository_path, content in _RELEASE_FIXTURE_FILES.items()
            if not prefix or repository_path.startswith(prefix)
        }

    def test_sha256_repository_and_blob_oids_match_checkout_bytes(self) -> None:
        revision = "a" * 64
        for host, source_prefix, required_manifest in self._HOST_TREES:
            with self.subTest(host=host), tempfile.TemporaryDirectory() as temporary:
                target = Path(temporary) / "target"
                target.mkdir()
                target = target.resolve(strict=True)
                checkout = target / "checkout"
                _write_release_checkout(checkout, host=host)
                calls: list[tuple[str, ...]] = []
                base_git = git_with_tree_variant("exact", object_id_length=64)

                def git_run(argv: tuple[str, ...]) -> probe.CommandResult:
                    calls.append(argv)
                    return base_git(argv)

                observed, revision_matches, checkout_matches, resolved, expected = (
                    probe._marketplace_checkout_provenance(
                        checkout,
                        target=target,
                        expected_revision=revision,
                        git_run=git_run,
                        source_prefix=source_prefix,
                        required_manifest=required_manifest,
                    )
                )

                self.assertEqual(revision, observed)
                self.assertIs(True, revision_matches)
                self.assertIs(True, checkout_matches)
                self.assertEqual(checkout.resolve(), resolved)
                self.assertEqual(
                    self._fixture_tree(source_prefix, object_id_length=64), expected
                )
                self.assertTrue(expected)
                self.assertTrue(all(len(object_id) == 64 for object_id in expected.values()))
                tree_reads = [
                    argv
                    for argv in calls
                    if tuple(argv[-4:-1]) == ("ls-tree", "-rz", "--full-tree")
                ]
                self.assertEqual(1, len(tree_reads))
                self.assertEqual(revision, tree_reads[0][-1])

    def test_100755_blob_mode_preserves_byte_and_path_identity_across_hosts(self) -> None:
        ordinary_output = _git_tree_output("exact")
        executable_output = _git_tree_output("executable")
        self.assertIn("100755 blob ", executable_output)

        for host, source_prefix, required_manifest in self._HOST_TREES:
            with self.subTest(host=host):
                parse = lambda output: probe._expected_git_tree(  # noqa: E731
                    output,
                    source_prefix=source_prefix,
                    required_manifest=required_manifest,
                    object_id_length=40,
                )
                ordinary = parse(ordinary_output)
                executable = parse(executable_output)

                self.assertEqual(self._fixture_tree(source_prefix), executable)
                self.assertEqual(ordinary, executable)
                self.assertIs(
                    True,
                    probe._tree_matches_expected(
                        {
                            path: _RELEASE_FIXTURE_FILES[
                                f"{source_prefix}/{path}" if source_prefix else path
                            ]
                            for path in executable
                        },
                        executable,
                    ),
                )

    def test_non_blob_type_is_rejected_with_ordinary_file_mode(self) -> None:
        output = _git_tree_output("non-blob-type")
        records = output[:-1].split("\0")
        non_blob_records = [record for record in records if record.startswith("100644 tree ")]
        self.assertEqual(2, len(non_blob_records))
        self.assertNotIn("120000", output)
        self.assertNotIn("160000", output)

        for host, source_prefix, required_manifest in self._HOST_TREES:
            with self.subTest(host=host):
                self.assertIsNone(
                    probe._expected_git_tree(
                        output,
                        source_prefix=source_prefix,
                        required_manifest=required_manifest,
                        object_id_length=40,
                    )
                )

    def test_casefold_colliding_paths_are_rejected_as_windows_ambiguous(self) -> None:
        output = _git_tree_output("casefold-collision")
        repository_paths = {
            record.partition("\t")[2] for record in output[:-1].split("\0")
        }
        for path in (
            "skills/fixture/SKILL.md",
            "plugins/save-toolkit/skills/fixture/SKILL.md",
        ):
            self.assertNotEqual(path, path.casefold())
            self.assertIn(path, repository_paths)
            self.assertIn(path.casefold(), repository_paths)

        for host, source_prefix, required_manifest in self._HOST_TREES:
            with self.subTest(host=host):
                self.assertIsNone(
                    probe._expected_git_tree(
                        output,
                        source_prefix=source_prefix,
                        required_manifest=required_manifest,
                        object_id_length=40,
                    )
                )


class ChildEnvironmentTests(unittest.TestCase):
    def test_windows_app_data_pointers_land_in_the_disposable_home(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            home = Path(raw) / "home"
            environment = probe._child_env(home, {})
            for key in ("APPDATA", "LOCALAPPDATA"):
                self.assertIn(key, environment)
                self.assertEqual(home.resolve(), Path(environment[key]).resolve().parents[1])

    def test_child_commands_cannot_consume_the_probe_stdin(self) -> None:
        seen: dict[str, object] = {}

        def fake_run(argv, **kwargs):
            seen.update(kwargs)
            return subprocess.CompletedProcess(list(argv), 0, "", "")

        with mock.patch.object(probe.subprocess, "run", fake_run):
            probe._run_probe(("claude", "--version"), None, root=REPO)
        self.assertEqual(subprocess.DEVNULL, seen.get("stdin"))


class AbsentHostTests(unittest.TestCase):
    def test_all_hosts_skip_when_no_cli_exists(self) -> None:
        calls: list[tuple[str, ...]] = []

        def run(argv: tuple[str, ...], env: object) -> probe.CommandResult:
            calls.append(argv)
            raise AssertionError("no CLI command may run when every host is absent")

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            report = probe.collect_report(
                REPO,
                target=base / "target",
                home=base / "home",
                run=run,
                git_run=fake_git,
                which=absent_which,
                now=NOW,
            )
        self.assertEqual({"pass": 0, "fail": 0, "skip": 16, "inconclusive": 0}, report["summary"])
        self.assertEqual([], calls)
        fleet_doctor.validate_report(report)
        for item in report["evidence"]:
            evidence_envelope.validate_envelope(item)

    def test_copilot_present_drives_a_real_install_cycle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            state = {"add_rc": 0, "install_rc": 0, "uninstall_rc": 0, "installed": False, "residue": False}
            envs: list[object] = []
            report = probe.collect_report(
                REPO,
                target=base / "target",
                hosts=("copilot",),
                home=base / "home",
                run=copilot_run(state, envs),
                git_run=fake_git,
                which=make_which(copilot="copilot.exe"),
                now=NOW,
            )
            target = (base / "target").resolve()
            for env in envs:
                if env is None:
                    continue
                self.assertTrue(Path(env["HOME"]).resolve().is_relative_to(target))  # type: ignore[arg-type]
        items = checks_by_id(report)
        for criterion in probe.CRITERIA:
            self.assertEqual("pass", items[f"host.copilot.probe-{criterion}"]["status"], criterion)
        fleet_doctor.validate_report(report)

    def test_copilot_verb_failure_is_inconclusive_and_downstream_skips(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            state = {"add_rc": 1, "install_rc": 0, "uninstall_rc": 0, "installed": False, "residue": False}
            report = probe.collect_report(
                REPO,
                target=base / "target",
                hosts=("copilot",),
                home=base / "home",
                run=copilot_run(state, []),
                git_run=fake_git,
                which=make_which(copilot="copilot.exe"),
                now=NOW,
            )
        items = checks_by_id(report)
        self.assertEqual("inconclusive", items["host.copilot.probe-install"]["status"])
        self.assertEqual("skip", items["host.copilot.probe-inventory"]["status"])
        self.assertEqual("skip", items["host.copilot.probe-uninstall"]["status"])
        self.assertEqual("pass", items["host.copilot.probe-authority"]["status"])

    def test_copilot_uninstall_residue_is_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            state = {"add_rc": 0, "install_rc": 0, "uninstall_rc": 0, "installed": False, "residue": True}
            report = probe.collect_report(
                REPO,
                target=base / "target",
                hosts=("copilot",),
                home=base / "home",
                run=copilot_run(state, []),
                git_run=fake_git,
                which=make_which(copilot="copilot.exe"),
                now=NOW,
            )
        self.assertEqual("fail", checks_by_id(report)["host.copilot.probe-uninstall"]["status"])

    def test_copilot_user_state_write_is_authority_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            watched = base / "home" / ".copilot"
            state = {"add_rc": 0, "install_rc": 0, "uninstall_rc": 0, "installed": False, "residue": False}
            base_run = copilot_run(state, [])

            def run(argv: tuple[str, ...], env: object) -> probe.CommandResult:
                if tuple(argv[1:]) == ("plugin", "install", probe.COPILOT_PLUGIN_ID):
                    watched.mkdir(parents=True, exist_ok=True)
                    watched.joinpath("config.json").write_text("{}", encoding="utf-8")
                return base_run(argv, env)

            report = probe.collect_report(
                REPO,
                target=base / "target",
                hosts=("copilot",),
                home=base / "home",
                run=run,
                git_run=fake_git,
                which=make_which(copilot="copilot.exe"),
                now=NOW,
            )
        authority = checks_by_id(report)["host.copilot.probe-authority"]
        self.assertEqual("fail", authority["status"])
        self.assertNotIn("config.json", repr(authority))


class CensusTests(unittest.TestCase):
    def test_missing_then_created_empty_root_is_a_change(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            watched = Path(temporary) / "user-config"
            before = probe._stat_census(watched)
            watched.mkdir()
            after = probe._stat_census(watched)

        self.assertEqual(1, probe._census_change(before, after))

    def test_linked_root_or_child_is_indeterminate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            watched = Path(temporary) / "user-config"
            child = watched / "child"
            child.mkdir(parents=True)
            original = probe.verification_sandbox._is_indirection

            for indirect in (watched, child):
                with self.subTest(indirect=indirect.name), mock.patch.object(
                    probe.verification_sandbox,
                    "_is_indirection",
                    side_effect=lambda path, indirect=indirect: path == indirect or original(path),
                ):
                    self.assertIsNone(probe._stat_census(watched))

    def test_special_entry_is_indeterminate(self) -> None:
        special = mock.Mock(
            st_mode=probe.stat.S_IFIFO | 0o600,
            st_size=0,
            st_mtime_ns=0,
        )
        with mock.patch.object(Path, "lstat", return_value=special), mock.patch.object(
            probe.verification_sandbox,
            "_is_indirection",
            return_value=False,
        ):
            self.assertIsNone(probe._census_entry(Path("special")))

    def test_indirection_inspection_failure_is_indeterminate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            watched = Path(temporary) / "user-config"
            watched.mkdir()
            with mock.patch.object(
                probe.verification_sandbox,
                "_is_indirection",
                side_effect=probe.verification_sandbox.SandboxError("metadata race"),
            ):
                self.assertIsNone(probe._stat_census(watched))

    def test_unreadable_walk_is_indeterminate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            watched = Path(temporary) / "user-config"
            watched.mkdir()

            def inaccessible_walk(path, *, followlinks, onerror=None):
                del path
                self.assertFalse(followlinks)
                if onerror is not None:
                    onerror(PermissionError("denied"))
                return iter(())

            with mock.patch.object(probe.os, "walk", side_effect=inaccessible_walk):
                self.assertIsNone(probe._stat_census(watched))

    def test_either_indeterminate_snapshot_keeps_change_indeterminate(self) -> None:
        self.assertIsNone(probe._census_change(None, {}))
        self.assertIsNone(probe._census_change({}, None))

    def test_unchanged_census_is_labeled_residual_evidence_not_no_write_proof(self) -> None:
        authority = probe._authority_check("claude", [("Claude-config-root", {}, {})])

        self.assertEqual("pass", authority.status)
        self.assertIn("residual metadata-visible change", authority.summary)
        self.assertNotIn("all probe writes", repr(authority).lower())
        self.assertTrue(any("transient" in item for item in authority.limitations))


class ClaudeProbeTests(unittest.TestCase):
    def _claude_run(self, state: dict[str, object], calls: list[tuple[str, ...]], envs: list[object]):
        def run(argv: tuple[str, ...], env: object) -> probe.CommandResult:
            calls.append(argv)
            envs.append(env)
            tail = tuple(argv[1:])
            if tail == ("--version",):
                return probe.CommandResult(0, "claude 2.0\n", "")
            if tail[:3] == ("plugin", "marketplace", "add"):
                if state["add_rc"] == 0:
                    state["marketplace"] = True
                    if tail[-1] == RELEASE_SOURCE:
                        checkout = (
                            Path(env["CLAUDE_CONFIG_DIR"])  # type: ignore[index]
                            / "plugins"
                            / "marketplaces"
                            / probe.MARKETPLACE_NAME
                        )
                        state["checkout_path"] = checkout
                        state["plugin_source_path"] = _write_release_checkout(
                            checkout, host="claude"
                        )
                        source_variant = state.get("source_variant")
                        if isinstance(source_variant, str):
                            _mutate_source_fixture(
                                state["plugin_source_path"], source_variant  # type: ignore[arg-type]
                            )
                return probe.CommandResult(state["add_rc"], "", "")
            if tail == ("plugin", "install", probe.CLAUDE_PLUGIN_ID):
                state["installed"] = state["add_rc"] == 0
                source = state.get("plugin_source_path")
                if state["install_rc"] == 0 and isinstance(source, Path):
                    installed = (
                        Path(env["CLAUDE_CONFIG_DIR"])  # type: ignore[index]
                        / "plugins"
                        / "cache"
                        / "latent-sre"
                        / "save-toolkit"
                        / "1.2.3"
                    )
                    state["installed_cache_path"] = installed
                    _write_installed_fixture(
                        source, installed, str(state.get("tree_variant", "exact"))
                    )
                return probe.CommandResult(state["install_rc"], "", "")
            if tail in (("plugin", "list"), ("plugin", "list", "--json")):
                state["list_count"] = int(state.get("list_count", 0)) + 1
                list_rc = (
                    state.get("post_list_rc", 0)
                    if state["list_count"] > 1
                    else state.get("list_rc", 0)
                )
                version = str(state.get("version", REPOSITORY_VERSION))
                if tail[-1] == "--json":
                    install_path: object = state.get(
                        "install_path", state.get("installed_cache_path", "disposable")
                    )
                    if isinstance(install_path, Path):
                        install_path = str(install_path)
                    row = json.dumps(
                        [
                            {
                                "id": probe.CLAUDE_PLUGIN_ID,
                                "version": version,
                                "scope": "user",
                                "enabled": True,
                                "installPath": install_path,
                            }
                        ]
                        if state["installed"]
                        else []
                    )
                else:
                    row = (
                        f"Installed plugins:\n\n  ❯ save-toolkit@latent-sre\n    Version: {version}\n"
                        "    Scope: user\n    Status: ✔ enabled\n"
                        if state["installed"]
                        else ""
                    )
                return probe.CommandResult(list_rc, row, "")  # type: ignore[arg-type]
            if tail == ("plugin", "uninstall", probe.CLAUDE_PLUGIN_ID):
                if state["uninstall_rc"] == 0 and not state["residue"]:
                    state["installed"] = False
                return probe.CommandResult(state["uninstall_rc"], "", "")
            if tail == ("plugin", "marketplace", "remove", "latent-sre"):
                returncode = state.get("marketplace_remove_rc", 0)
                if returncode == 0 and not state.get("marketplace_residue"):
                    state["marketplace"] = False
                return probe.CommandResult(returncode, "", "")  # type: ignore[arg-type]
            if tail == ("plugin", "marketplace", "list", "--json"):
                rows = [{"name": "latent-sre"}] if state.get("marketplace") else []
                return probe.CommandResult(0, json.dumps(rows), "")
            raise AssertionError(f"unexpected argv: {argv!r}")

        return run

    def _collect(self, run, base: Path, hosts=("claude",)):
        return probe.collect_report(
            REPO,
            target=base / "target",
            hosts=hosts,
            home=base / "home",
            run=run,
            git_run=fake_git,
            which=make_which(claude="claude.exe"),
            now=NOW,
        )

    def test_full_cycle_passes_and_env_is_scrubbed(self) -> None:
        state = {"add_rc": 0, "install_rc": 0, "uninstall_rc": 0, "installed": False, "residue": False}
        calls: list[tuple[str, ...]] = []
        envs: list[object] = []
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "probe-must-not-inherit"}):
                report = self._collect(self._claude_run(state, calls, envs), Path(temporary))
            target = (Path(temporary) / "target").resolve()
            items = checks_by_id(report)
            for criterion in probe.CRITERIA:
                self.assertEqual("pass", items[f"host.claude.probe-{criterion}"]["status"], criterion)
            self.assertNotIn(
                "clean source tree",
                items["host.claude.probe-install"]["source"]["summary"],
            )
            claude_envs = [env for argv, env in zip(calls, envs) if argv[0] == "claude.exe" and argv[1] != "--version"]
            self.assertTrue(claude_envs)
            for env in claude_envs:
                self.assertIsNotNone(env)
                allowed = {
                    "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR",
                    "HOME", "USERPROFILE", "TEMP", "TMP", "TMPDIR", "CLAUDE_CONFIG_DIR",
                    "APPDATA", "LOCALAPPDATA",
                }
                self.assertLessEqual(set(env), allowed)  # type: ignore[arg-type]
                self.assertNotIn("ANTHROPIC_API_KEY", env)  # type: ignore[operator]
                for key in ("APPDATA", "LOCALAPPDATA"):
                    self.assertTrue(
                        Path(env[key]).resolve().is_relative_to(target)  # type: ignore[arg-type]
                    )
                self.assertTrue(
                    Path(env["CLAUDE_CONFIG_DIR"]).resolve().is_relative_to(target)  # type: ignore[arg-type]
                )
        fleet_doctor.validate_report(report)
        self.assertIn(("claude.exe", "plugin", "marketplace", "remove", "latent-sre"), calls)
        self.assertIn(("claude.exe", "plugin", "marketplace", "list", "--json"), calls)

    def test_release_source_is_used_and_reported(self) -> None:
        state = {"add_rc": 0, "install_rc": 0, "uninstall_rc": 0, "installed": False, "residue": False, "version": "1.2.3"}
        calls: list[tuple[str, ...]] = []
        with tempfile.TemporaryDirectory() as temporary:
            report = probe.collect_report(
                REPO,
                target=Path(temporary) / "target",
                hosts=("claude",),
                home=Path(temporary) / "home",
                marketplace_source=RELEASE_SOURCE,
                run=self._claude_run(state, calls, []),
                git_run=fake_git,
                which=make_which(claude="claude.exe"),
                now=NOW,
            )
        self.assertIn(
            ("claude.exe", "plugin", "marketplace", "add", RELEASE_SOURCE), calls
        )
        checks = checks_by_id(report)
        for criterion in ("install", "inventory"):
            item = checks[f"host.claude.probe-{criterion}"]
            self.assertEqual("pass", item["status"])
            details = item["source"]["details"]
            self.assertIs(True, details["marketplace_revision_matches"])
            self.assertIs(True, details["marketplace_checkout_clean"])
            self.assertIs(True, details["source_tree_matches"])
            self.assertIs(True, details["installed_tree_matches"])
            self.assertEqual(
                "ordinary-file-paths-and-git-blob-bytes",
                details["tree_identity_contract"],
            )
            self.assertEqual(details["expected_file_count"], details["source_file_count"])
            self.assertEqual(details["source_file_count"], details["installed_file_count"])
            self.assertGreater(details["source_file_count"], 0)
        for item in report["evidence"]:
            self.assertEqual(RELEASE_SOURCE, item["environment"]["marketplace_source"])
            self.assertEqual("pinned-version-tag", item["environment"]["marketplace_source_kind"])

    def test_release_source_dirty_marketplace_checkout_fails_install_and_inventory(self) -> None:
        state = {"add_rc": 0, "install_rc": 0, "uninstall_rc": 0, "installed": False, "residue": False, "version": "1.2.3"}
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            report = probe.collect_report(
                REPO,
                target=base / "target",
                hosts=("claude",),
                home=base / "home",
                marketplace_source=RELEASE_SOURCE,
                run=self._claude_run(state, [], []),
                git_run=git_with_dirty_marketplace,
                which=make_which(claude="claude.exe"),
                now=NOW,
            )
        checks = checks_by_id(report)
        for criterion in ("install", "inventory"):
            item = checks[f"host.claude.probe-{criterion}"]
            self.assertEqual("fail", item["status"])
            self.assertIs(False, item["source"]["details"]["marketplace_checkout_clean"])

    def test_release_source_rejects_matching_non_head_source_and_installed_trees(self) -> None:
        for variant in ("extra", "changed", "missing", "empty"):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as temporary:
                state = {
                    "add_rc": 0,
                    "install_rc": 0,
                    "uninstall_rc": 0,
                    "installed": False,
                    "residue": False,
                    "version": "1.2.3",
                    "source_variant": variant,
                }
                base = Path(temporary)
                report = probe.collect_report(
                    REPO,
                    target=base / "target",
                    hosts=("claude",),
                    home=base / "home",
                    marketplace_source=RELEASE_SOURCE,
                    run=self._claude_run(state, [], []),
                    git_run=fake_git,
                    which=make_which(claude="claude.exe"),
                    now=NOW,
                )
            checks = checks_by_id(report)
            for criterion in ("install", "inventory"):
                item = checks[f"host.claude.probe-{criterion}"]
                self.assertEqual("fail", item["status"])
                self.assertIs(False, item["source"]["details"]["installed_tree_matches"])

    def test_release_source_binds_tree_read_to_the_observed_commit(self) -> None:
        state = {
            "add_rc": 0,
            "install_rc": 0,
            "uninstall_rc": 0,
            "installed": False,
            "residue": False,
            "version": "1.2.3",
            "source_variant": "changed",
        }
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            report = probe.collect_report(
                REPO,
                target=base / "target",
                hosts=("claude",),
                home=base / "home",
                marketplace_source=RELEASE_SOURCE,
                run=self._claude_run(state, [], []),
                git_run=git_with_switched_head,
                which=make_which(claude="claude.exe"),
                now=NOW,
            )
        checks = checks_by_id(report)
        self.assertEqual("fail", checks["host.claude.probe-install"]["status"])
        self.assertEqual("fail", checks["host.claude.probe-inventory"]["status"])

    def test_release_source_rejects_unsafe_or_ambiguous_git_trees(self) -> None:
        variants = (
            "symlink",
            "gitlink",
            "special",
            "duplicate",
            "unsafe",
            "empty",
            "missing-manifest",
            "malformed",
            "replacement-character",
        )
        for variant in variants:
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as temporary:
                state = {
                    "add_rc": 0,
                    "install_rc": 0,
                    "uninstall_rc": 0,
                    "installed": False,
                    "residue": False,
                    "version": "1.2.3",
                }
                base = Path(temporary)
                report = probe.collect_report(
                    REPO,
                    target=base / "target",
                    hosts=("claude",),
                    home=base / "home",
                    marketplace_source=RELEASE_SOURCE,
                    run=self._claude_run(state, [], []),
                    git_run=git_with_tree_variant(variant),
                    which=make_which(claude="claude.exe"),
                    now=NOW,
                )
            checks = checks_by_id(report)
            self.assertEqual("fail", checks["host.claude.probe-install"]["status"])
            self.assertEqual("fail", checks["host.claude.probe-inventory"]["status"])

    def test_release_source_missing_extra_and_changed_installed_bytes_fail(self) -> None:
        for variant in ("missing", "extra", "changed", "missing-root"):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as temporary:
                state = {
                    "add_rc": 0,
                    "install_rc": 0,
                    "uninstall_rc": 0,
                    "installed": False,
                    "residue": False,
                    "version": "1.2.3",
                    "tree_variant": variant,
                }
                base = Path(temporary)
                report = probe.collect_report(
                    REPO,
                    target=base / "target",
                    hosts=("claude",),
                    home=base / "home",
                    marketplace_source=RELEASE_SOURCE,
                    run=self._claude_run(state, [], []),
                    git_run=fake_git,
                    which=make_which(claude="claude.exe"),
                    now=NOW,
                )
            checks = checks_by_id(report)
            for criterion in ("install", "inventory"):
                item = checks[f"host.claude.probe-{criterion}"]
                self.assertEqual("fail", item["status"])
                self.assertIs(False, item["source"]["details"]["installed_tree_matches"])

    def test_release_source_indirect_checkout_root_install_root_or_entry_fails(self) -> None:
        original = probe.verification_sandbox._is_indirection

        for indirect_part in (
            "marketplace-root",
            "git-metadata",
            "installed-root",
            "tree-entry",
        ):
            with self.subTest(indirect_part=indirect_part), tempfile.TemporaryDirectory() as temporary:
                state = {
                    "add_rc": 0,
                    "install_rc": 0,
                    "uninstall_rc": 0,
                    "installed": False,
                    "residue": False,
                    "version": "1.2.3",
                    "tree_variant": "indirect",
                }

                def mark_fixture_indirect(path: Path) -> bool:
                    if indirect_part == "marketplace-root" and path.name == "latent-sre":
                        return path.parent.name == "marketplaces"
                    if indirect_part == "git-metadata" and path.name == ".git":
                        return True
                    if indirect_part == "installed-root" and path.name == "1.2.3":
                        return path.parent.name == "save-toolkit"
                    if indirect_part == "tree-entry" and path.name == "indirect.txt":
                        return True
                    return original(path)

                with mock.patch.object(
                    probe.verification_sandbox,
                    "_is_indirection",
                    side_effect=mark_fixture_indirect,
                ):
                    base = Path(temporary)
                    report = probe.collect_report(
                        REPO,
                        target=base / "target",
                        hosts=("claude",),
                        home=base / "home",
                        marketplace_source=RELEASE_SOURCE,
                        run=self._claude_run(state, [], []),
                        git_run=fake_git,
                        which=make_which(claude="claude.exe"),
                        now=NOW,
                    )
            checks = checks_by_id(report)
            for criterion in ("install", "inventory"):
                self.assertEqual("fail", checks[f"host.claude.probe-{criterion}"]["status"])

    def test_release_source_malformed_or_out_of_target_install_path_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            cases: tuple[object, ...] = ({"not": "a path"}, str(base / "outside-cache"))
            for index, install_path in enumerate(cases):
                with self.subTest(install_path=install_path):
                    state = {
                        "add_rc": 0,
                        "install_rc": 0,
                        "uninstall_rc": 0,
                        "installed": False,
                        "residue": False,
                        "version": "1.2.3",
                        "install_path": install_path,
                    }
                    report = probe.collect_report(
                        REPO,
                        target=base / f"target-{index}",
                        hosts=("claude",),
                        home=base / "home",
                        marketplace_source=RELEASE_SOURCE,
                        run=self._claude_run(state, [], []),
                        git_run=fake_git,
                        which=make_which(claude="claude.exe"),
                        now=NOW,
                    )
                    checks = checks_by_id(report)
                    for criterion in ("install", "inventory"):
                        item = checks[f"host.claude.probe-{criterion}"]
                        self.assertEqual("fail", item["status"])
                        self.assertIs(
                            False, item["source"]["details"]["installed_tree_matches"]
                        )

    def test_release_source_wrong_inventory_version_is_fail(self) -> None:
        state = {"add_rc": 0, "install_rc": 0, "uninstall_rc": 0, "installed": False, "residue": False, "version": "9.9.9"}
        with tempfile.TemporaryDirectory() as temporary:
            report = probe.collect_report(
                REPO,
                target=Path(temporary) / "target",
                hosts=("claude",),
                home=Path(temporary) / "home",
                marketplace_source=RELEASE_SOURCE,
                run=self._claude_run(state, [], []),
                git_run=fake_git,
                which=make_which(claude="claude.exe"),
                now=NOW,
            )
        self.assertEqual("fail", checks_by_id(report)["host.claude.probe-inventory"]["status"])

    def test_release_source_checkout_revision_mismatch_is_fail(self) -> None:
        state = {"add_rc": 0, "install_rc": 0, "uninstall_rc": 0, "installed": False, "residue": False, "version": "1.2.3"}

        def mismatched_git(argv: tuple[str, ...]) -> probe.CommandResult:
            if tuple(argv[-3:]) == ("rev-parse", "--verify", "HEAD^{commit}"):
                return probe.CommandResult(0, "b" * 40, "")
            if tuple(argv[-4:-1]) == ("ls-tree", "-rz", "--full-tree"):
                return probe.CommandResult(0, _git_tree_output(), "")
            if tuple(argv[-2:]) == ("status", "--short"):
                return probe.CommandResult(0, "", "")
            if tuple(argv[-2:]) == ("rev-parse", "HEAD"):
                return probe.CommandResult(0, "a" * 40, "")
            raise AssertionError(f"unexpected git argv: {argv!r}")

        with tempfile.TemporaryDirectory() as temporary:
            report = probe.collect_report(
                REPO,
                target=Path(temporary) / "target",
                hosts=("claude",),
                home=Path(temporary) / "home",
                marketplace_source=RELEASE_SOURCE,
                run=self._claude_run(state, [], []),
                git_run=mismatched_git,
                which=make_which(claude="claude.exe"),
                now=NOW,
            )
        self.assertEqual("fail", checks_by_id(report)["host.claude.probe-install"]["status"])

    def test_marketplace_residue_fails_uninstall(self) -> None:
        state = {"add_rc": 0, "install_rc": 0, "uninstall_rc": 0, "installed": False, "residue": False, "marketplace_residue": True}
        with tempfile.TemporaryDirectory() as temporary:
            report = self._collect(self._claude_run(state, [], []), Path(temporary))
        self.assertEqual("fail", checks_by_id(report)["host.claude.probe-uninstall"]["status"])

    def test_cli_verb_failure_is_inconclusive_and_downstream_skips(self) -> None:
        state = {"add_rc": 0, "install_rc": 1, "uninstall_rc": 0, "installed": False, "residue": False}
        with tempfile.TemporaryDirectory() as temporary:
            report = self._collect(self._claude_run(state, [], []), Path(temporary))
        items = checks_by_id(report)
        self.assertEqual("inconclusive", items["host.claude.probe-install"]["status"])
        self.assertEqual(
            ["claude.exe", "plugin", "install", probe.CLAUDE_PLUGIN_ID],
            items["host.claude.probe-install"]["command"]["argv"],
        )
        self.assertEqual(1, items["host.claude.probe-install"]["command"]["exit_code"])
        self.assertEqual("skip", items["host.claude.probe-inventory"]["status"])
        self.assertEqual("skip", items["host.claude.probe-uninstall"]["status"])
        self.assertEqual("pass", items["host.claude.probe-authority"]["status"])

    def test_install_without_inventory_row_is_fail(self) -> None:
        state = {"add_rc": 0, "install_rc": 0, "uninstall_rc": 0, "installed": False, "residue": True}
        calls: list[tuple[str, ...]] = []

        def run(argv: tuple[str, ...], env: object) -> probe.CommandResult:
            tail = tuple(argv[1:])
            if tail == ("plugin", "install", probe.CLAUDE_PLUGIN_ID):
                return probe.CommandResult(0, "", "")
            if tail == ("plugin", "list", "--json"):
                return probe.CommandResult(0, "[]", "")
            if tail == ("plugin", "uninstall", probe.CLAUDE_PLUGIN_ID):
                return probe.CommandResult(0, "", "")
            if tail[:3] == ("plugin", "marketplace", "add"):
                return probe.CommandResult(0, "", "")
            if tail == ("plugin", "marketplace", "remove", "latent-sre"):
                return probe.CommandResult(0, "", "")
            if tail == ("plugin", "marketplace", "list", "--json"):
                return probe.CommandResult(0, "[]", "")
            return probe.CommandResult(0, "claude 2.0\n", "")

        with tempfile.TemporaryDirectory() as temporary:
            report = self._collect(run, Path(temporary))
        self.assertEqual("fail", checks_by_id(report)["host.claude.probe-inventory"]["status"])

    def test_uninstall_residue_is_fail(self) -> None:
        state = {"add_rc": 0, "install_rc": 0, "uninstall_rc": 0, "installed": False, "residue": True}
        with tempfile.TemporaryDirectory() as temporary:
            report = self._collect(self._claude_run(state, [], []), Path(temporary))
        self.assertEqual("fail", checks_by_id(report)["host.claude.probe-uninstall"]["status"])

    def test_post_uninstall_inventory_verb_failure_is_inconclusive(self) -> None:
        state = {
            "add_rc": 0,
            "install_rc": 0,
            "uninstall_rc": 0,
            "post_list_rc": 1,
            "installed": False,
            "residue": False,
        }
        with tempfile.TemporaryDirectory() as temporary:
            report = self._collect(self._claude_run(state, [], []), Path(temporary))
        self.assertEqual(
            "inconclusive", checks_by_id(report)["host.claude.probe-uninstall"]["status"]
        )

    def test_user_config_write_during_probe_is_authority_fail(self) -> None:
        state = {"add_rc": 0, "install_rc": 0, "uninstall_rc": 0, "installed": False, "residue": False}
        base_run = self._claude_run(state, [], [])

        def run(argv: tuple[str, ...], env: object) -> probe.CommandResult:
            if tuple(argv[1:]) == ("plugin", "install", probe.CLAUDE_PLUGIN_ID):
                leak = watched / "settings.json"
                leak.parent.mkdir(parents=True, exist_ok=True)
                leak.write_text("{}", encoding="utf-8")
            return base_run(argv, env)

        with tempfile.TemporaryDirectory() as temporary:
            watched = Path(temporary) / "home" / ".claude"
            report = self._collect(run, Path(temporary))
        authority = checks_by_id(report)["host.claude.probe-authority"]
        self.assertEqual("fail", authority["status"])
        self.assertEqual(2, authority["source"]["details"]["changed_user_path_count"])
        self.assertNotIn("settings.json", repr(authority))

    def test_sibling_user_config_write_during_probe_is_authority_fail(self) -> None:
        state = {"add_rc": 0, "install_rc": 0, "uninstall_rc": 0, "installed": False, "residue": False}
        base_run = self._claude_run(state, [], [])

        def run(argv: tuple[str, ...], env: object) -> probe.CommandResult:
            if tuple(argv[1:]) == ("plugin", "install", probe.CLAUDE_PLUGIN_ID):
                leak = watched / "history.jsonl"
                leak.parent.mkdir(parents=True, exist_ok=True)
                leak.write_text("{}\n", encoding="utf-8")
            return base_run(argv, env)

        with tempfile.TemporaryDirectory() as temporary:
            watched = Path(temporary) / "home" / ".claude"
            report = self._collect(run, Path(temporary))
        authority = checks_by_id(report)["host.claude.probe-authority"]
        self.assertEqual("fail", authority["status"])
        self.assertEqual(2, authority["source"]["details"]["changed_user_path_count"])
        self.assertNotIn("history.jsonl", repr(authority))

    def test_indirection_inspection_failure_is_sanitized_inconclusive(self) -> None:
        state = {"add_rc": 0, "install_rc": 0, "uninstall_rc": 0, "installed": False, "residue": False}
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            watched = base / "home" / ".claude"
            watched.mkdir(parents=True)
            with mock.patch.object(
                probe.verification_sandbox,
                "_is_indirection",
                side_effect=probe.verification_sandbox.SandboxError(f"cannot inspect {watched}"),
            ):
                report = self._collect(self._claude_run(state, [], []), base)

        authority = checks_by_id(report)["host.claude.probe-authority"]
        self.assertEqual("inconclusive", authority["status"])
        self.assertNotIn(str(watched), repr(authority))


class CodexProbeTests(unittest.TestCase):
    def _collect(
        self,
        base: Path,
        *,
        state: dict[str, object] | None = None,
        calls: list[tuple[str, ...]] | None = None,
        envs: list[object] | None = None,
        marketplace_source: str | None = None,
    ) -> dict[str, object]:
        if state is None:
            state = {}
        if marketplace_source == RELEASE_SOURCE and "version" not in state:
            state["version"] = "1.2.3"
        return probe.collect_report(
            REPO,
            target=base / "target",
            hosts=("codex",),
            home=base / "home",
            marketplace_source=marketplace_source,
            run=codex_run(state, calls if calls is not None else [], envs if envs is not None else []),
            git_run=fake_git,
            which=make_which(codex="codex.exe"),
            now=NOW,
        )

    def test_full_cycle_passes_on_real_generated_bytes(self) -> None:
        calls: list[tuple[str, ...]] = []
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            report = self._collect(base, calls=calls)
            items = checks_by_id(report)
            for criterion in probe.CRITERIA:
                self.assertEqual("pass", items[f"host.codex.probe-{criterion}"]["status"], criterion)
            agents = base / "target" / "codex" / "home" / "agents"
            self.assertFalse(list(agents.glob("*.toml")))
        inventory = items["host.codex.probe-inventory"]
        self.assertEqual(8, inventory["source"]["details"]["role_count"])
        self.assertTrue(inventory["source"]["details"]["plugin_installed"])
        fleet_doctor.validate_report(report)
        self.assertIn(("codex.exe", "plugin", "marketplace", "remove", "latent-sre"), calls)
        self.assertIn(("codex.exe", "plugin", "marketplace", "list", "--json"), calls)

    def test_release_source_runs_plugin_and_standalone_agent_lifecycles(self) -> None:
        calls: list[tuple[str, ...]] = []
        envs: list[object] = []
        state: dict[str, object] = {}
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            report = self._collect(
                base,
                state=state,
                calls=calls,
                envs=envs,
                marketplace_source=RELEASE_SOURCE,
            )
            codex_home = (base / "target" / "codex" / "home").resolve()
            expected_cache = (
                codex_home
                / "plugins"
                / "cache"
                / "latent-sre"
                / "save-toolkit"
                / "1.2.3"
            )
            self.assertEqual(expected_cache, state["installed_cache_path"])
            for argv, environment in zip(calls, envs):
                if argv[1:] == ("--version",):
                    continue
                self.assertEqual(codex_home, Path(environment["CODEX_HOME"]).resolve())
        self.assertIn(("codex.exe", "plugin", "marketplace", "add", RELEASE_SOURCE), calls)
        self.assertIn(("codex.exe", "plugin", "add", probe.CODEX_PLUGIN_ID), calls)
        self.assertIn(("codex.exe", "plugin", "list", "--json"), calls)
        self.assertIn(("codex.exe", "plugin", "remove", probe.CODEX_PLUGIN_ID), calls)
        for criterion in probe.CRITERIA:
            self.assertEqual(
                "pass", checks_by_id(report)[f"host.codex.probe-{criterion}"]["status"]
            )
        for criterion in ("install", "inventory"):
            details = checks_by_id(report)[f"host.codex.probe-{criterion}"]["source"][
                "details"
            ]
            self.assertIs(True, details["marketplace_revision_matches"])
            self.assertIs(True, details["marketplace_checkout_clean"])
            self.assertIs(True, details["source_tree_matches"])
            self.assertIs(True, details["installed_tree_matches"])
            self.assertEqual(
                "ordinary-file-paths-and-git-blob-bytes",
                details["tree_identity_contract"],
            )
            self.assertEqual(details["expected_file_count"], details["source_file_count"])
            self.assertEqual(details["source_file_count"], details["installed_file_count"])
            self.assertGreater(details["source_file_count"], 0)
            self.assertEqual(str(expected_cache), details["installed_tree_path"])

    def test_release_source_rejects_matching_non_head_source_and_installed_trees(self) -> None:
        for variant in ("extra", "changed", "missing", "empty"):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as temporary:
                report = self._collect(
                    Path(temporary),
                    state={"version": "1.2.3", "source_variant": variant},
                    marketplace_source=RELEASE_SOURCE,
                )
            checks = checks_by_id(report)
            for criterion in ("install", "inventory"):
                item = checks[f"host.codex.probe-{criterion}"]
                self.assertEqual("fail", item["status"])
                self.assertIs(False, item["source"]["details"]["installed_tree_matches"])

    def test_release_source_rejects_missing_extra_and_changed_installed_bytes(self) -> None:
        for variant in ("missing", "extra", "changed", "missing-root"):
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as temporary:
                report = self._collect(
                    Path(temporary),
                    state={"version": "1.2.3", "tree_variant": variant},
                    marketplace_source=RELEASE_SOURCE,
                )
            checks = checks_by_id(report)
            for criterion in ("install", "inventory"):
                item = checks[f"host.codex.probe-{criterion}"]
                self.assertEqual("fail", item["status"])
                self.assertIs(False, item["source"]["details"]["installed_tree_matches"])

    def test_release_source_rejects_unsafe_or_ambiguous_git_trees(self) -> None:
        variants = (
            "symlink",
            "gitlink",
            "special",
            "duplicate",
            "unsafe",
            "empty",
            "missing-manifest",
            "malformed",
            "replacement-character",
        )
        for variant in variants:
            with self.subTest(variant=variant), tempfile.TemporaryDirectory() as temporary:
                base = Path(temporary)
                report = probe.collect_report(
                    REPO,
                    target=base / "target-adversarial",
                    hosts=("codex",),
                    home=base / "home",
                    marketplace_source=RELEASE_SOURCE,
                    run=codex_run({"version": "1.2.3"}, [], []),
                    git_run=git_with_tree_variant(variant),
                    which=make_which(codex="codex.exe"),
                    now=NOW,
                )
            checks = checks_by_id(report)
            self.assertEqual("fail", checks["host.codex.probe-install"]["status"])
            self.assertEqual("fail", checks["host.codex.probe-inventory"]["status"])

    def test_release_source_wrong_inventory_version_is_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = self._collect(
                Path(temporary),
                state={"version": "9.9.9"},
                marketplace_source=RELEASE_SOURCE,
            )
        self.assertEqual("fail", checks_by_id(report)["host.codex.probe-inventory"]["status"])

    def test_release_source_checkout_revision_mismatch_is_fail(self) -> None:
        state: dict[str, object] = {"version": "1.2.3"}

        def mismatched_git(argv: tuple[str, ...]) -> probe.CommandResult:
            if tuple(argv[-3:]) == ("rev-parse", "--verify", "HEAD^{commit}"):
                return probe.CommandResult(0, "b" * 40, "")
            if tuple(argv[-4:-1]) == ("ls-tree", "-rz", "--full-tree"):
                return probe.CommandResult(0, _git_tree_output(), "")
            if tuple(argv[-2:]) == ("status", "--short"):
                return probe.CommandResult(0, "", "")
            if tuple(argv[-2:]) == ("rev-parse", "HEAD"):
                return probe.CommandResult(0, "a" * 40, "")
            raise AssertionError(f"unexpected git argv: {argv!r}")

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            report = probe.collect_report(
                REPO,
                target=base / "target",
                hosts=("codex",),
                home=base / "home",
                marketplace_source=RELEASE_SOURCE,
                run=codex_run(state, [], []),
                git_run=mismatched_git,
                which=make_which(codex="codex.exe"),
                now=NOW,
            )
        self.assertEqual("fail", checks_by_id(report)["host.codex.probe-install"]["status"])

    def test_marketplace_residue_fails_uninstall(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = self._collect(
                Path(temporary),
                state={"marketplace_residue": True},
            )
        self.assertEqual("fail", checks_by_id(report)["host.codex.probe-uninstall"]["status"])

    def test_installed_plugin_missing_from_json_inventory_is_fail(self) -> None:
        state = {"installed": False}

        def missing_inventory_run(argv: tuple[str, ...], env: object) -> probe.CommandResult:
            result = codex_run(state, [], [])(argv, env)
            if tuple(argv[1:]) == ("plugin", "list", "--json") and state.get("installed"):
                return probe.CommandResult(0, '{"installed":[],"available":[]}', "")
            return result

        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            report = probe.collect_report(
                REPO,
                target=base / "target",
                hosts=("codex",),
                home=base / "home",
                run=missing_inventory_run,
                git_run=fake_git,
                which=make_which(codex="codex.exe"),
                now=NOW,
            )
        self.assertEqual("fail", checks_by_id(report)["host.codex.probe-inventory"]["status"])

    def test_inventory_requires_one_exact_identity_row(self) -> None:
        cases = (
            {"inventory_plugin_id": "other@latent-sre"},
            {"inventory_name": "other"},
            {"inventory_marketplace": "other"},
            {"version": "9.9.9"},
            {"inventory_installed": False},
            {"inventory_enabled": False},
            {"inventory_row_count": 2},
        )
        for state in cases:
            with self.subTest(state=state), tempfile.TemporaryDirectory() as temporary:
                report = self._collect(Path(temporary), state=dict(state))
            self.assertEqual(
                "fail", checks_by_id(report)["host.codex.probe-inventory"]["status"]
            )

    def test_codex_cli_verb_failure_is_inconclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = self._collect(Path(temporary), state={"install_rc": 1})
        items = checks_by_id(report)
        self.assertEqual("inconclusive", items["host.codex.probe-install"]["status"])
        self.assertEqual("skip", items["host.codex.probe-inventory"]["status"])

    def test_plugin_success_cannot_mask_missing_standalone_agent_install(self) -> None:
        empty_plan = install_codex_agents.SyncPlan((), (), ())
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.object(
                probe.install_codex_agents, "build_sync_plan", return_value=empty_plan
            ):
                report = self._collect(Path(temporary))
        items = checks_by_id(report)
        self.assertEqual("fail", items["host.codex.probe-install"]["status"])
        self.assertEqual("fail", items["host.codex.probe-inventory"]["status"])

    def test_codex_inventory_verb_failure_is_inconclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = self._collect(Path(temporary), state={"list_rc": 1})
        self.assertEqual(
            "inconclusive", checks_by_id(report)["host.codex.probe-inventory"]["status"]
        )

    def test_codex_malformed_successful_inventory_is_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = self._collect(Path(temporary), state={"malformed_json": True})
        items = checks_by_id(report)
        self.assertEqual("fail", items["host.codex.probe-inventory"]["status"])
        self.assertEqual("fail", items["host.codex.probe-uninstall"]["status"])

    def test_codex_remove_verb_failure_is_inconclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = self._collect(Path(temporary), state={"uninstall_rc": 1})
        self.assertEqual(
            "inconclusive", checks_by_id(report)["host.codex.probe-uninstall"]["status"]
        )

    def test_codex_uninstall_residue_is_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = self._collect(Path(temporary), state={"residue": True})
        self.assertEqual("fail", checks_by_id(report)["host.codex.probe-uninstall"]["status"])

    def test_user_codex_home_write_during_install_is_authority_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            watched = base / "home" / ".codex" / "plugins"
            original = probe.install_codex_agents.apply_sync_plan

            def leaking_apply(plan: object) -> None:
                original(plan)
                watched.mkdir(parents=True, exist_ok=True)
                watched.joinpath("state.json").write_text("{}\n", encoding="utf-8")

            with mock.patch.object(probe.install_codex_agents, "apply_sync_plan", leaking_apply):
                report = self._collect(base)
        authority = checks_by_id(report)["host.codex.probe-authority"]
        self.assertEqual("fail", authority["status"])
        self.assertNotIn("state.json", repr(authority))

    def test_user_agent_write_during_install_is_authority_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            watched = base / "home" / ".codex" / "agents"
            original = probe.install_codex_agents.apply_sync_plan

            def leaking_apply(plan: object) -> None:
                original(plan)
                watched.mkdir(parents=True, exist_ok=True)
                watched.joinpath("snoop.toml").write_text("x = 1\n", encoding="utf-8")

            with mock.patch.object(probe.install_codex_agents, "apply_sync_plan", leaking_apply):
                report = self._collect(base)
        authority = checks_by_id(report)["host.codex.probe-authority"]
        self.assertEqual("fail", authority["status"])
        self.assertNotIn("snoop.toml", repr(authority))


class VSCodeProbeTests(unittest.TestCase):
    def _collect(self, base: Path) -> dict[str, object]:
        settings = base / "home" / "Code" / "User" / "settings.json"
        with mock.patch.object(probe, "_vscode_user_settings", return_value=settings):
            return probe.collect_report(
                REPO,
                target=base / "target",
                hosts=("vscode",),
                home=base / "home",
                run=version_only_run,
                git_run=fake_git,
                which=make_which(code="code.exe"),
                now=NOW,
            )

    def test_full_cycle_passes_with_untouched_user_settings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            settings = base / "home" / "Code" / "User" / "settings.json"
            settings.parent.mkdir(parents=True)
            settings.write_text('{"editor.fontSize": 13}\n', encoding="utf-8")
            before = settings.read_bytes()
            report = self._collect(base)
            items = checks_by_id(report)
            for criterion in probe.CRITERIA:
                self.assertEqual("pass", items[f"host.vscode.probe-{criterion}"]["status"], criterion)
            self.assertEqual(before, settings.read_bytes())
            workspace = base / "target" / "vscode" / "workspace"
            self.assertEqual([], [p for p in workspace.rglob("*") if p.is_file()])
        inventory = items["host.vscode.probe-inventory"]
        self.assertTrue(inventory["source"]["details"]["skills_location_registered"])
        fleet_doctor.validate_report(report)

    def test_foreign_file_in_workspace_is_uninstall_residue_fail(self) -> None:
        original = probe._copy_generated_tree

        def dirty_copy(source: Path, destination: Path) -> int:
            copied = original(source, destination)
            destination.joinpath("foreign.txt").write_text("not ours\n", encoding="utf-8")
            return copied

        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.object(probe, "_copy_generated_tree", dirty_copy):
                report = self._collect(Path(temporary))
        items = checks_by_id(report)
        self.assertEqual("fail", items["host.vscode.probe-uninstall"]["status"])
        self.assertEqual("pass", items["host.vscode.probe-authority"]["status"])

    def test_absent_cli_skips_by_default_but_explicit_file_probe_passes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            skipped = probe.collect_report(
                REPO,
                target=base / "skip-target",
                hosts=("vscode",),
                home=base / "home",
                run=version_only_run,
                git_run=fake_git,
                which=absent_which,
                now=NOW,
            )
            passed = probe.collect_report(
                REPO,
                target=base / "pass-target",
                hosts=("vscode",),
                home=base / "home",
                run=version_only_run,
                git_run=fake_git,
                which=absent_which,
                now=NOW,
                allow_vscode_file_probe_without_cli=True,
            )
        self.assertEqual({"pass": 0, "fail": 0, "skip": 4, "inconclusive": 0}, skipped["summary"])
        self.assertEqual({"pass": 4, "fail": 0, "skip": 0, "inconclusive": 0}, passed["summary"])
        for item in passed["evidence"]:
            self.assertEqual("unavailable:file-level-opt-in", item["environment"]["host_cli"])


class ReportContractTests(unittest.TestCase):
    def test_strict_exit_blocks_skip_and_inconclusive_while_default_does_not(self) -> None:
        for status in ("skip", "inconclusive"):
            report = {"summary": {"pass": 3, "fail": 0, "skip": 0, "inconclusive": 0}}
            report["summary"][status] = 1
            self.assertEqual(0, probe._exit_code(report, require_pass=False))
            self.assertEqual(
                1, probe._exit_code(report, require_pass=True, expected_passes=4)
            )
        all_pass = {
            "evidence": [{"environment": {"source_worktree_clean": True}}],
            "summary": {"pass": 4, "fail": 0, "skip": 0, "inconclusive": 0},
        }
        self.assertEqual(
            0, probe._exit_code(all_pass, require_pass=True, expected_passes=4)
        )
        incomplete = {"summary": {"pass": 3, "fail": 0, "skip": 0, "inconclusive": 0}}
        self.assertEqual(
            1, probe._exit_code(incomplete, require_pass=True, expected_passes=4)
        )

    def test_strict_exit_rejects_evidence_from_a_dirty_source_tree(self) -> None:
        report = {
            "evidence": [{"environment": {"source_worktree_clean": False}}],
            "summary": {"pass": 4, "fail": 0, "skip": 0, "inconclusive": 0},
        }
        self.assertEqual(0, probe._exit_code(report, require_pass=False))
        self.assertEqual(
            1,
            probe._exit_code(report, require_pass=True, expected_passes=4),
        )

    def test_unknown_revision_aborts_before_probing(self) -> None:
        def bad_git(argv: tuple[str, ...]) -> probe.CommandResult:
            return probe.CommandResult(1, "", "")

        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "target"
            with self.assertRaisesRegex(ValueError, "unknown revision"):
                probe.collect_report(
                    REPO,
                    target=target,
                    hosts=("codex",),
                    home=Path(temporary) / "home",
                    run=version_only_run,
                    git_run=bad_git,
                    which=make_which(codex="codex.exe"),
                    now=NOW,
                )
            self.assertFalse(target.exists())

    def test_main_removes_target_unless_kept(self) -> None:
        report = {
            "schema_version": 1,
            "run_id": "probe-1",
            "generated_at": "2026-08-04T00:00:00Z",
            "root": str(REPO),
            "revision": "d" * 40,
            "summary": {"pass": 4, "fail": 0, "skip": 0, "inconclusive": 0},
            "evidence": [],
        }
        report["evidence"] = [{"environment": {"source_worktree_clean": True}}]

        forwarded: list[tuple[object, object]] = []

        def fake_collect(
            root: Path,
            *,
            target: Path,
            hosts: object,
            marketplace_source: object,
            allow_vscode_file_probe_without_cli: object,
            require_clean: object,
        ) -> dict[str, object]:
            forwarded.append(
                (marketplace_source, allow_vscode_file_probe_without_cli, require_clean)
            )
            Path(target).mkdir(parents=True)
            return report

        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "target"
            with mock.patch.object(probe, "collect_report", fake_collect):
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(0, probe.main(["--target", str(target), "--json"]))
            self.assertFalse(target.exists())
            with mock.patch.object(probe, "collect_report", fake_collect):
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(0, probe.main(["--target", str(target), "--keep", "--json"]))
            self.assertTrue(target.is_dir())
            target.rmdir()
            with mock.patch.object(probe, "collect_report", fake_collect):
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(
                        0,
                        probe.main(
                            [
                                "--target",
                                str(target),
                                "--marketplace-source",
                                RELEASE_SOURCE,
                                "--allow-vscode-file-probe-without-cli",
                                "--hosts",
                                "vscode",
                                "--require-pass",
                                "--json",
                            ]
                        ),
                    )
        self.assertEqual((None, False, False), forwarded[0])
        self.assertEqual((None, False, False), forwarded[1])
        self.assertEqual((RELEASE_SOURCE, True, True), forwarded[2])


if __name__ == "__main__":
    unittest.main()
