"""Safety and schema tests for the read-only fleet doctor."""

from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import evidence_envelope
import fleet_doctor


REPO = Path(__file__).resolve().parents[1]


class FleetDoctorTests(unittest.TestCase):
    def test_command_allowlist_rejects_mutating_or_model_commands(self) -> None:
        fleet_doctor._assert_read_only_command(
            ("git", "--no-optional-locks", "-C", str(REPO), "status", "--short")
        )
        fleet_doctor._assert_read_only_command(("claude", "plugin", "list"))
        for command in (
            ("git", "--no-optional-locks", "-C", str(REPO), "fetch"),
            ("git", "-C", str(REPO), "status", "--short"),
            ("claude", "plugin", "install", "save-toolkit"),
            ("codex", "exec", "inspect this repo"),
            ("python", "scripts/generate_platform_adapters.py", "--write"),
        ):
            with self.subTest(command=command):
                with self.assertRaisesRegex(ValueError, "read-only allowlist"):
                    fleet_doctor._assert_read_only_command(command)

    def test_report_uses_valid_envelopes_and_does_not_touch_home(self) -> None:
        calls: list[tuple[str, ...]] = []

        def run(argv: tuple[str, ...]) -> fleet_doctor.CommandResult:
            calls.append(tuple(argv))
            fleet_doctor._assert_read_only_command(argv)
            if tuple(argv[-2:]) == ("rev-parse", "HEAD"):
                return fleet_doctor.CommandResult(0, "a" * 40 + "\n", "")
            if tuple(argv[-2:]) == ("status", "--short"):
                return fleet_doctor.CommandResult(0, "", "")
            if tuple(argv[-2:]) == ("plugin", "list"):
                return fleet_doctor.CommandResult(0, "save-toolkit 1.0.0\n", "")
            return fleet_doctor.CommandResult(0, "test-cli 1.0\n", "")

        def which(command: str) -> str:
            return str(Path("C:/tools") / f"{command}.exe")

        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
            codex_home = Path(temporary) / "codex"
            home.mkdir()
            sentinel = home / "sentinel.txt"
            sentinel.write_text("unchanged\n", encoding="utf-8")
            before = {p.relative_to(home): p.read_bytes() for p in home.rglob("*") if p.is_file()}
            with mock.patch.object(
                fleet_doctor,
                "_repository_checks",
                return_value=[fleet_doctor.Check("repository.fixture", "pass", "fixture current")],
            ):
                report = fleet_doctor.collect_report(
                    REPO,
                    home=home,
                    codex_home=codex_home,
                    run=run,
                    which=which,
                    now=datetime(2026, 7, 31, tzinfo=timezone.utc),
                )
            after = {p.relative_to(home): p.read_bytes() for p in home.rglob("*") if p.is_file()}

        self.assertEqual(before, after)
        self.assertTrue(calls)
        fleet_doctor.validate_report(report)
        for item in report["evidence"]:
            evidence_envelope.validate_envelope(item)
        self.assertEqual("2026-07-31T00:00:00Z", report["generated_at"])
        self.assertGreaterEqual(report["summary"]["pass"], 1)

    def test_missing_hosts_are_skip_never_pass(self) -> None:
        checks, executables = fleet_doctor._cli_checks(lambda _: None, lambda _: None)  # type: ignore[arg-type]
        self.assertEqual({}, executables)
        self.assertTrue(checks)
        self.assertTrue(all(check.status == "skip" for check in checks))

    def test_plugin_inventory_requires_an_exact_installed_row(self) -> None:
        false_positives = (
            "old-save-toolkit-test  installed, enabled  1.0.0  C:/plugins/lookalike\n",
            "save-toolkit@latent-sre  not installed  C:/marketplace/save-toolkit\n",
            "No plugin named save-toolkit is installed.\n",
        )
        for host in ("claude", "codex"):
            for output in false_positives:
                with self.subTest(host=host, output=output):
                    self.assertFalse(
                        fleet_doctor._inventory_contains_plugin(host, output, "save-toolkit")
                    )
        self.assertTrue(
            fleet_doctor._inventory_contains_plugin(
                "claude", "  > save-toolkit@latent-sre\n    Version: 1.0.0\n", "save-toolkit"
            )
        )
        self.assertTrue(
            fleet_doctor._inventory_contains_plugin(
                "claude",
                "Installed plugins:\n\n  ❯ save-toolkit@latent-sre\n    Version: 1.0.0\n    Scope: user\n    Status: ✔ enabled\n",
                "save-toolkit",
            )
        )
        self.assertFalse(
            fleet_doctor._inventory_contains_plugin(
                "claude", "  ❯ old-save-toolkit-test\n    Version: 9.9.9\n", "save-toolkit"
            )
        )
        self.assertTrue(
            fleet_doctor._inventory_contains_plugin(
                "copilot", "Installed plugins:\n  • save-toolkit@latent-sre (v1.0.0)\n", "save-toolkit"
            )
        )
        for output in (
            "No plugins installed.\n",
            "  • old-save-toolkit@latent-sre (v1.0.0)\n",
            "  • save-toolkit-test@latent-sre (v2.0.0)\n",
        ):
            with self.subTest(host="copilot", output=output):
                self.assertFalse(
                    fleet_doctor._inventory_contains_plugin("copilot", output, "save-toolkit")
                )
        self.assertTrue(
            fleet_doctor._inventory_contains_plugin(
                "codex",
                "save-toolkit@latent-sre  installed, enabled  1.0.0  C:/plugins/save-toolkit\n",
                "save-toolkit",
            )
        )

    def test_dirty_worktree_is_recorded_as_a_limitation_without_paths(self) -> None:
        def run(argv: tuple[str, ...]) -> fleet_doctor.CommandResult:
            if tuple(argv[-2:]) == ("rev-parse", "HEAD"):
                return fleet_doctor.CommandResult(0, "b" * 40 + "\n", "")
            return fleet_doctor.CommandResult(0, " M private/customer-name.py\n?? secret-plan.md\n", "")

        revision, checks = fleet_doctor._git_checks(REPO, run)
        self.assertEqual("b" * 40, revision)
        state = next(check for check in checks if check.check_id == "repository.worktree-state")
        self.assertEqual("pass", state.status)
        self.assertEqual(2, state.details["changed_entry_count"])
        self.assertNotIn("customer-name", repr(state.details))
        self.assertTrue(state.limitations)

    def test_report_rejects_secret_bearing_check_details(self) -> None:
        check = fleet_doctor.Check(
            "fixture.secret",
            "pass",
            "bad fixture",
            {"api_token": "must-not-land"},
        )
        with self.assertRaisesRegex(evidence_envelope.EnvelopeValidationError, "secret-bearing"):
            fleet_doctor._to_envelope(
                check,
                root=REPO,
                revision="c" * 40,
                run_id="doctor-1",
                started_at=datetime(2026, 7, 31, tzinfo=timezone.utc),
                ended_at=datetime(2026, 7, 31, tzinfo=timezone.utc),
            )

    def _codex_fixture(self, temporary: str) -> tuple[Path, Path]:
        base = Path(temporary)
        root = base / "repo"
        source = root / ".codex" / "agents"
        source.mkdir(parents=True)
        source.joinpath("save-toolkit-sre.toml").write_text('name = "sre"\n', encoding="utf-8")
        codex_home = base / "codex"
        (codex_home / "agents").mkdir(parents=True)
        return root, codex_home

    def _no_fleet_plugin_list(self, argv: tuple[str, ...]) -> fleet_doctor.CommandResult:
        return fleet_doctor.CommandResult(0, "other-plugin  installed  1.0.0\n", "")

    def test_absent_fleet_on_available_codex_host_is_skip_not_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, codex_home = self._codex_fixture(temporary)
            checks = fleet_doctor._installation_checks(
                root,
                codex_home.parent,
                {"codex": "codex.exe"},
                self._no_fleet_plugin_list,
                codex_home=codex_home,
            )
        custom = next(check for check in checks if check.check_id == "host.codex.custom-agents")
        self.assertEqual("skip", custom.status)
        self.assertIn("no save-toolkit custom agents are installed", custom.summary)
        self.assertTrue(custom.limitations)

    def test_drifted_codex_install_is_still_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root, codex_home = self._codex_fixture(temporary)
            stale = codex_home / "agents" / "save-toolkit-retired.toml"
            stale.write_text(
                "# Managed by save-toolkit scripts/install_codex_agents.py; do not edit.\n",
                encoding="utf-8",
            )
            checks = fleet_doctor._installation_checks(
                root,
                codex_home.parent,
                {"codex": "codex.exe"},
                self._no_fleet_plugin_list,
                codex_home=codex_home,
            )
        custom = next(check for check in checks if check.check_id == "host.codex.custom-agents")
        self.assertEqual("fail", custom.status)
        self.assertIn("differ from generated fleet roles", custom.summary)

    def test_main_exits_one_only_for_failing_checks(self) -> None:
        report = {
            "schema_version": 1,
            "run_id": "doctor-1",
            "generated_at": "2026-07-31T00:00:00Z",
            "root": str(REPO),
            "revision": "d" * 40,
            "summary": {"pass": 0, "fail": 1, "skip": 0, "inconclusive": 0},
            "evidence": [],
        }
        output = io.StringIO()
        with mock.patch.object(fleet_doctor, "collect_report", return_value=report):
            with redirect_stdout(output):
                exit_code = fleet_doctor.main(["--json"])
        self.assertEqual(1, exit_code)
        self.assertIn('"fail": 1', output.getvalue())


if __name__ == "__main__":
    unittest.main()
