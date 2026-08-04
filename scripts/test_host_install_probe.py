"""Safety and schema tests for the disposable host install probe."""

from __future__ import annotations

import io
import os
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


def fake_git(argv: tuple[str, ...]) -> probe.CommandResult:
    if tuple(argv[-2:]) == ("rev-parse", "HEAD"):
        return probe.CommandResult(0, "a" * 40 + "\n", "")
    if tuple(argv[-2:]) == ("status", "--short"):
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
            ("claude", "plugin", "list"),
            ("claude", "plugin", "marketplace", "add", str(REPO)),
            ("claude", "plugin", "install", "save-toolkit@latent-sre"),
            ("claude", "plugin", "uninstall", "save-toolkit@latent-sre"),
            ("copilot", "plugin", "list"),
            ("copilot", "plugin", "marketplace", "add", str(REPO)),
            ("copilot", "plugin", "install", "save-toolkit@latent-sre"),
            ("copilot", "plugin", "uninstall", "save-toolkit@latent-sre"),
        ):
            with self.subTest(argv=argv):
                probe._assert_probe_command(argv, root=REPO)

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


class ClaudeProbeTests(unittest.TestCase):
    def _claude_run(self, state: dict[str, bool], calls: list[tuple[str, ...]], envs: list[object]):
        def run(argv: tuple[str, ...], env: object) -> probe.CommandResult:
            calls.append(argv)
            envs.append(env)
            tail = tuple(argv[1:])
            if tail == ("--version",):
                return probe.CommandResult(0, "claude 2.0\n", "")
            if tail[:3] == ("plugin", "marketplace", "add"):
                return probe.CommandResult(state["add_rc"], "", "")
            if tail == ("plugin", "install", probe.CLAUDE_PLUGIN_ID):
                state["installed"] = state["add_rc"] == 0
                return probe.CommandResult(state["install_rc"], "", "")
            if tail == ("plugin", "list"):
                row = (
                    "Installed plugins:\n\n  ❯ save-toolkit@latent-sre\n    Version: 1.0.0\n"
                    "    Scope: user\n    Status: ✔ enabled\n"
                    if state["installed"]
                    else ""
                )
                return probe.CommandResult(0, row, "")
            if tail == ("plugin", "uninstall", probe.CLAUDE_PLUGIN_ID):
                if state["uninstall_rc"] == 0 and not state["residue"]:
                    state["installed"] = False
                return probe.CommandResult(state["uninstall_rc"], "", "")
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
            claude_envs = [env for argv, env in zip(calls, envs) if argv[0] == "claude.exe" and argv[1] != "--version"]
            self.assertTrue(claude_envs)
            for env in claude_envs:
                self.assertIsNotNone(env)
                allowed = {
                    "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR",
                    "HOME", "USERPROFILE", "TEMP", "TMP", "TMPDIR", "CLAUDE_CONFIG_DIR",
                }
                self.assertLessEqual(set(env), allowed)  # type: ignore[arg-type]
                self.assertNotIn("ANTHROPIC_API_KEY", env)  # type: ignore[operator]
                self.assertTrue(
                    Path(env["CLAUDE_CONFIG_DIR"]).resolve().is_relative_to(target)  # type: ignore[arg-type]
                )
        fleet_doctor.validate_report(report)

    def test_cli_verb_failure_is_inconclusive_and_downstream_skips(self) -> None:
        state = {"add_rc": 1, "install_rc": 0, "uninstall_rc": 0, "installed": False, "residue": False}
        with tempfile.TemporaryDirectory() as temporary:
            report = self._collect(self._claude_run(state, [], []), Path(temporary))
        items = checks_by_id(report)
        self.assertEqual("inconclusive", items["host.claude.probe-install"]["status"])
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
            if tail == ("plugin", "list"):
                return probe.CommandResult(0, "", "")
            if tail == ("plugin", "uninstall", probe.CLAUDE_PLUGIN_ID):
                return probe.CommandResult(0, "", "")
            if tail[:3] == ("plugin", "marketplace", "add"):
                return probe.CommandResult(0, "", "")
            return probe.CommandResult(0, "claude 2.0\n", "")

        with tempfile.TemporaryDirectory() as temporary:
            report = self._collect(run, Path(temporary))
        self.assertEqual("fail", checks_by_id(report)["host.claude.probe-inventory"]["status"])

    def test_uninstall_residue_is_fail(self) -> None:
        state = {"add_rc": 0, "install_rc": 0, "uninstall_rc": 0, "installed": False, "residue": True}
        with tempfile.TemporaryDirectory() as temporary:
            report = self._collect(self._claude_run(state, [], []), Path(temporary))
        self.assertEqual("fail", checks_by_id(report)["host.claude.probe-uninstall"]["status"])

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
        self.assertEqual(1, authority["source"]["details"]["changed_user_path_count"])
        self.assertNotIn("settings.json", repr(authority))


class CodexProbeTests(unittest.TestCase):
    def _collect(self, base: Path) -> dict[str, object]:
        return probe.collect_report(
            REPO,
            target=base / "target",
            hosts=("codex",),
            home=base / "home",
            run=version_only_run,
            git_run=fake_git,
            which=make_which(codex="codex.exe"),
            now=NOW,
        )

    def test_full_cycle_passes_on_real_generated_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            report = self._collect(base)
            items = checks_by_id(report)
            for criterion in probe.CRITERIA:
                self.assertEqual("pass", items[f"host.codex.probe-{criterion}"]["status"], criterion)
            agents = base / "target" / "codex" / "home" / "agents"
            self.assertFalse(list(agents.glob("*.toml")))
        inventory = items["host.codex.probe-inventory"]
        self.assertEqual(8, inventory["source"]["details"]["role_count"])
        fleet_doctor.validate_report(report)

    def test_user_agents_write_during_install_is_authority_fail(self) -> None:
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
        self.assertNotIn("snoop", repr(authority))


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


class ReportContractTests(unittest.TestCase):
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
            "summary": {"pass": 1, "fail": 0, "skip": 0, "inconclusive": 0},
            "evidence": [],
        }

        def fake_collect(root: Path, *, target: Path, hosts: object) -> dict[str, object]:
            Path(target).mkdir(parents=True)
            return report

        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "target"
            with mock.patch.object(probe, "collect_report", fake_collect):
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(0, probe.main(["--target", str(target)]))
            self.assertFalse(target.exists())
            with mock.patch.object(probe, "collect_report", fake_collect):
                with redirect_stdout(io.StringIO()):
                    self.assertEqual(0, probe.main(["--target", str(target), "--keep"]))
            self.assertTrue(target.is_dir())


if __name__ == "__main__":
    unittest.main()
