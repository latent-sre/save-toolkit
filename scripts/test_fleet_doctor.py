"""Safety and schema tests for the read-only fleet doctor."""

from __future__ import annotations

import hashlib
import io
import json
import os
import subprocess
import sys
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
    def _write_guard_fixture(self, root: Path) -> None:
        hooks = root / "hooks"
        scripts = root / "scripts"
        hooks.mkdir(parents=True)
        scripts.mkdir(parents=True)
        (hooks / "hooks.json").write_bytes((REPO / "hooks" / "hooks.json").read_bytes())
        (scripts / "readonly-guard-hook.sh").write_bytes(
            (REPO / "scripts" / "readonly-guard-hook.sh").read_bytes()
        )
        (scripts / "guard-session-preflight-hook.sh").write_bytes(
            (REPO / "scripts" / "guard-session-preflight-hook.sh").read_bytes()
        )
        (scripts / "guard-session-preflight.py").write_bytes(
            (REPO / "scripts" / "guard-session-preflight.py").read_bytes()
        )
        (scripts / "readonly-guard.py").write_text("# fixture guard\n", encoding="utf-8")

    def test_import_preserves_bytecode_setting(self) -> None:
        for initial in (False, True):
            with self.subTest(initial=initial):
                result = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        (
                            "import sys; "
                            f"sys.dont_write_bytecode = {initial!r}; "
                            "import fleet_doctor; "
                            "print(sys.dont_write_bytecode)"
                        ),
                    ],
                    cwd=REPO / "scripts",
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    check=False,
                    timeout=30,
                )

                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(str(initial), result.stdout.strip())

    def test_guard_interpreter_requires_exact_allow_and_deny_protocol(self) -> None:
        deny_output = (
            '{"hookSpecificOutput":{"hookEventName":"PreToolUse",'
            '"permissionDecision":"deny","permissionDecisionReason":"fixture"}}\n'
        )

        for label, available, responses, expected_status, expected_calls in (
            (
                "guard protocol",
                {"python3": "C:/tools/python3.exe"},
                [
                    fleet_doctor.CommandResult(42, "", ""),
                    fleet_doctor.CommandResult(43, deny_output, ""),
                ],
                "pass",
                2,
            ),
            (
                "later candidate answers",
                {
                    "python3": "C:/tools/python3.exe",
                    "python": "C:/tools/python.exe",
                },
                [
                    fleet_doctor.CommandResult(0, "", ""),
                    fleet_doctor.CommandResult(0, "", ""),
                    fleet_doctor.CommandResult(42, "", ""),
                    fleet_doctor.CommandResult(43, deny_output, ""),
                ],
                "pass",
                4,
            ),
            (
                "stand-in exits zero",
                {"python3": "C:/tools/python3.exe"},
                [
                    fleet_doctor.CommandResult(0, "", ""),
                    fleet_doctor.CommandResult(0, "", ""),
                ],
                "fail",
                2,
            ),
            ("no candidate", {}, [], "fail", 0),
        ):
            observed_payloads: list[str] = []

            def which(command: str) -> str | None:
                return available.get(command)

            remaining = iter(responses)

            def run(argv: tuple[str, ...], payload: str) -> fleet_doctor.CommandResult:
                observed_payloads.append(payload)
                return next(remaining)

            with self.subTest(label=label):
                check = fleet_doctor._guard_interpreter_check(
                    REPO / "scripts" / "readonly-guard.py",
                    which,
                    run,
                )

                self.assertEqual(expected_status, check.status)
                self.assertEqual(expected_calls, len(observed_payloads))
                if available:
                    first = check.details["observations"][0]
                    self.assertEqual(next(iter(available.values())), first["resolved"])
                if expected_status == "pass":
                    self.assertNotEqual(observed_payloads[0], observed_payloads[1])

    def test_guard_allow_probe_reaches_the_guarded_allowlist(self) -> None:
        deny_output = (
            '{"hookSpecificOutput":{"hookEventName":"PreToolUse",'
            '"permissionDecision":"deny","permissionDecisionReason":"blanket deny"}}\n'
        )

        def run(argv: tuple[str, ...], payload: str) -> fleet_doctor.CommandResult:
            del argv
            if json.loads(payload).get("agent_type") == "save-toolkit:sre":
                return fleet_doctor.CommandResult(43, deny_output, "")
            return fleet_doctor.CommandResult(42, "", "")

        check = fleet_doctor._guard_interpreter_check(
            REPO / "scripts" / "readonly-guard.py",
            lambda candidate: sys.executable if candidate == "python3" else None,
            run,
        )

        self.assertEqual("save-toolkit:sre", json.loads(fleet_doctor.GUARD_ALLOW_PAYLOAD)["agent_type"])
        self.assertEqual("fail", check.status)

    def test_guard_interpreter_stops_each_payload_at_its_first_authenticated_answer(self) -> None:
        deny_output = (
            '{"hookSpecificOutput":{"hookEventName":"PreToolUse",'
            '"permissionDecision":"deny","permissionDecisionReason":"fixture"}}\n'
        )
        available = {
            "python3": "C:/tools/python3.exe",
            "python": "C:/tools/python.exe",
        }

        for label, responses, expected_calls in (
            (
                "early interpreter denies the safe probe",
                [
                    fleet_doctor.CommandResult(43, deny_output, ""),
                    fleet_doctor.CommandResult(43, deny_output, ""),
                    fleet_doctor.CommandResult(42, "", ""),
                    fleet_doctor.CommandResult(43, deny_output, ""),
                ],
                2,
            ),
            (
                "early interpreter allows the deny probe",
                [
                    fleet_doctor.CommandResult(0, "", ""),
                    fleet_doctor.CommandResult(42, "", ""),
                    fleet_doctor.CommandResult(42, "", ""),
                    fleet_doctor.CommandResult(43, deny_output, ""),
                ],
                3,
            ),
        ):
            remaining = iter(responses)
            observed_payloads: list[str] = []

            def run(argv: tuple[str, ...], payload: str) -> fleet_doctor.CommandResult:
                del argv
                observed_payloads.append(payload)
                return next(remaining)

            with self.subTest(label=label):
                check = fleet_doctor._guard_interpreter_check(
                    REPO / "scripts" / "readonly-guard.py",
                    available.get,
                    run,
                )

                self.assertEqual("fail", check.status)
                self.assertEqual(expected_calls, len(observed_payloads))

    def test_hook_registration_reports_registered_and_absent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            plugin_root = Path(temporary) / "plugin"
            self._write_guard_fixture(plugin_root)

            registered = fleet_doctor._guard_hook_check(plugin_root)
            (plugin_root / "hooks" / "hooks.json").write_text(
                json.dumps(
                    {
                        "hooks": {
                            "PreToolUse": [
                                {
                                    "matcher": "Bash",
                                    "hooks": [
                                        {
                                            "type": "command",
                                            "command": (
                                                "echo ${CLAUDE_PLUGIN_ROOT}/scripts/"
                                                "readonly-guard.py"
                                            ),
                                        }
                                    ],
                                }
                            ]
                        }
                    }
                ),
                encoding="utf-8",
            )
            unrelated = fleet_doctor._guard_hook_check(plugin_root)
            (plugin_root / "hooks" / "hooks.json").unlink()
            absent = fleet_doctor._guard_hook_check(plugin_root)

        self.assertEqual("pass", registered.status)
        self.assertEqual("fail", unrelated.status)
        self.assertEqual("fail", absent.status)

    def test_hook_registration_rejects_a_commented_out_launcher(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            plugin_root = Path(temporary) / "plugin"
            self._write_guard_fixture(plugin_root)
            hook_path = plugin_root / "hooks" / "hooks.json"
            document = json.loads(hook_path.read_text(encoding="utf-8"))
            command_hook = document["hooks"]["PreToolUse"][0]["hooks"][0]
            command_hook["command"] = "exit 0; # " + command_hook["command"]
            hook_path.write_text(json.dumps(document), encoding="utf-8")

            observed = fleet_doctor._guard_hook_check(plugin_root)

        self.assertEqual("fail", observed.status)

    def test_hook_registration_rejects_synchronized_inert_launcher_copies(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            plugin_root = Path(temporary) / "plugin"
            self._write_guard_fixture(plugin_root)
            hook_path = plugin_root / "hooks" / "hooks.json"
            document = json.loads(hook_path.read_text(encoding="utf-8"))
            document["hooks"]["PreToolUse"][0]["hooks"][0]["command"] = "exit 0"
            hook_path.write_text(json.dumps(document), encoding="utf-8")
            (plugin_root / "scripts" / "readonly-guard-hook.sh").write_text(
                "#!/bin/sh\nexit 0\n",
                encoding="utf-8",
            )

            observed = fleet_doctor._guard_hook_check(plugin_root)

        self.assertEqual("fail", observed.status)

    def test_guard_file_reports_present_and_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            plugin_root = Path(temporary) / "plugin"
            self._write_guard_fixture(plugin_root)

            present = fleet_doctor._guard_file_check(plugin_root)
            (plugin_root / "scripts" / "readonly-guard.py").unlink()
            missing = fleet_doctor._guard_file_check(plugin_root)

        self.assertEqual("pass", present.status)
        self.assertEqual("fail", missing.status)

    def test_no_checkout_skips_repository_checks_but_reports_guard_health(self) -> None:
        deny_output = (
            '{"hookSpecificOutput":{"hookEventName":"PreToolUse",'
            '"permissionDecision":"deny","permissionDecisionReason":"fixture"}}\n'
        )

        def which(command: str) -> str | None:
            if command == "python3":
                return "C:/tools/python3.exe"
            return None

        def run_guard(argv: tuple[str, ...], payload: str) -> fleet_doctor.CommandResult:
            if payload == fleet_doctor.GUARD_ALLOW_PAYLOAD:
                return fleet_doctor.CommandResult(42, "", "")
            return fleet_doctor.CommandResult(43, deny_output, "")

        def unexpected_command(argv: tuple[str, ...]) -> fleet_doctor.CommandResult:
            self.fail(f"outside-checkout report unexpectedly ran {argv!r}")

        with tempfile.TemporaryDirectory() as temporary:
            plugin_root = Path(temporary) / "installed-plugin"
            self._write_guard_fixture(plugin_root)
            with mock.patch.object(
                fleet_doctor,
                "_repository_checks",
                side_effect=AssertionError("repository validators must not run"),
            ):
                report = fleet_doctor.collect_report(
                    plugin_root,
                    plugin_root=plugin_root,
                    environment={},
                    home=Path(temporary) / "home",
                    run=unexpected_command,
                    guard_run=run_guard,
                    which=which,
                    now=datetime(2026, 8, 23, tzinfo=timezone.utc),
                )

        statuses = {item["criterion"]: item["status"] for item in report["evidence"]}
        self.assertEqual("unknown", report["revision"])
        self.assertEqual("skip", statuses["repository.git-revision"])
        self.assertEqual("skip", statuses["repository.worktree-state"])
        self.assertEqual("skip", statuses["repository.fleet-contracts"])
        self.assertEqual("skip", statuses["repository.plan-status"])
        self.assertEqual("pass", statuses["guard.hook-registration"])
        self.assertEqual("pass", statuses["guard.file"])
        self.assertEqual("pass", statuses["guard.interpreter-protocol"])
        self.assertIn("guard.interpreter-protocol", fleet_doctor.render_human(report))

    def test_minimal_installed_plugin_does_not_import_repository_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            plugin_root = Path(temporary) / "installed-plugin"
            self._write_guard_fixture(plugin_root)
            for name in ("fleet_doctor.py", "evidence_envelope.py", "readonly-guard.py"):
                (plugin_root / "scripts" / name).write_bytes((REPO / "scripts" / name).read_bytes())

            environment = dict(os.environ)
            environment.pop("PYTHONPATH", None)
            environment["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
            result = subprocess.run(
                [sys.executable, str(plugin_root / "scripts" / "fleet_doctor.py"), "--json"],
                cwd=plugin_root,
                env=environment,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
                timeout=30,
            )

        self.assertEqual(0, result.returncode, result.stderr)
        report = json.loads(result.stdout)
        statuses = {item["criterion"]: item["status"] for item in report["evidence"]}
        self.assertEqual("unknown", report["revision"])
        self.assertEqual("skip", statuses["repository.fleet-contracts"])
        self.assertEqual("pass", statuses["guard.plugin-root"])
        self.assertEqual("pass", statuses["guard.interpreter-protocol"])

    def test_runtime_plugin_root_mismatch_does_not_fall_back_to_checkout_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            missing_root = Path(temporary) / "missing-installed-plugin"
            report = fleet_doctor.collect_report(
                missing_root,
                environment={"CLAUDE_PLUGIN_ROOT": str(missing_root)},
                run=lambda argv: self.fail(f"unexpected command: {argv!r}"),
                which=lambda _: None,
                now=datetime(2026, 8, 23, tzinfo=timezone.utc),
            )

        statuses = {item["criterion"]: item["status"] for item in report["evidence"]}
        self.assertEqual("fail", statuses["guard.plugin-root"])
        self.assertEqual("fail", statuses["guard.file"])
        self.assertEqual("skip", statuses["guard.interpreter-protocol"])

    def test_source_checkout_is_not_installed_plugin_proof(self) -> None:
        observed = fleet_doctor._plugin_root_check(REPO, "CLAUDE_PLUGIN_ROOT")

        self.assertEqual("inconclusive", observed.status)
        self.assertIn("source checkout", observed.summary)

    def test_guard_evidence_targets_installed_plugin_bytes_not_checkout_revision(self) -> None:
        def run(argv: tuple[str, ...]) -> fleet_doctor.CommandResult:
            if tuple(argv[-2:]) == ("rev-parse", "HEAD"):
                return fleet_doctor.CommandResult(0, "a" * 40 + "\n", "")
            if tuple(argv[-2:]) == ("status", "--short"):
                return fleet_doctor.CommandResult(0, "", "")
            self.fail(f"unexpected command: {argv!r}")

        with tempfile.TemporaryDirectory() as temporary:
            plugin_root = Path(temporary) / "installed-plugin"
            with mock.patch.object(
                fleet_doctor,
                "_repository_checks",
                return_value=[fleet_doctor.Check("repository.fixture", "pass", "fixture")],
            ):
                report = fleet_doctor.collect_report(
                    REPO,
                    plugin_root=plugin_root,
                    environment={},
                    run=run,
                    which=lambda _: None,
                    now=datetime(2026, 8, 23, tzinfo=timezone.utc),
                )

        evidence = {item["criterion"]: item for item in report["evidence"]}
        self.assertEqual(str(REPO), evidence["repository.git-revision"]["target"]["root"])
        self.assertEqual("a" * 40, evidence["repository.git-revision"]["target"]["revision"])
        self.assertEqual(
            str(plugin_root.resolve()),
            evidence["guard.file"]["target"]["root"],
        )
        self.assertEqual("unknown", evidence["guard.file"]["target"]["revision"])
        self.assertRegex(evidence["guard.file"]["target"]["tree_digest"], r"^[0-9a-f]{64}$")

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

        fleet_doctor._assert_guard_probe_command(
            ("python3", "-I", "-S", str(REPO / "scripts" / "readonly-guard.py"))
        )
        for command in (
            ("python3", "-S", str(REPO / "scripts" / "readonly-guard.py")),
            ("node", "-I", "-S", str(REPO / "scripts" / "readonly-guard.py")),
            ("python3", "-I", "-S", str(REPO / "scripts" / "other.py")),
            ("python3", "-I", "-S", str(REPO / "other" / "readonly-guard.py")),
        ):
            with self.subTest(guard_probe=command):
                with self.assertRaisesRegex(ValueError, "guard|interpreter"):
                    fleet_doctor._assert_guard_probe_command(command)

    def test_guard_probe_protocol_matches_hook_launcher(self) -> None:
        launcher = (REPO / "scripts" / "readonly-guard-hook.sh").read_text(encoding="utf-8")
        candidates = " ".join(fleet_doctor.GUARD_INTERPRETER_CANDIDATES)

        self.assertIn(f"for C in {candidates}; do", launcher)
        self.assertIn(f'"$RC" -eq {fleet_doctor.GUARD_ALLOW_EXIT}', launcher)
        self.assertIn(f'"$RC" -eq {fleet_doctor.GUARD_DENY_EXIT}', launcher)

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

        def run_guard(argv: tuple[str, ...], payload: str) -> fleet_doctor.CommandResult:
            if payload == fleet_doctor.GUARD_ALLOW_PAYLOAD:
                return fleet_doctor.CommandResult(42, "", "")
            return fleet_doctor.CommandResult(
                43,
                '{"hookSpecificOutput":{"hookEventName":"PreToolUse",'
                '"permissionDecision":"deny"}}\n',
                "",
            )

        def which(command: str) -> str:
            return str(Path("C:/tools") / f"{command}.exe")

        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary) / "home"
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
                    environment={},
                    home=home,
                    run=run,
                    guard_run=run_guard,
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
        for host in ("claude",):
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

    def test_trusted_hook_digests_pin_the_shipped_hook_configuration(self) -> None:
        """A pin that no longer describes hooks.json silently downgrades every guard verdict.

        ``_guard_hook_check`` requires both that the registered command equals the standalone
        launcher and that its digest equals the pin here. The launcher half already has a
        verifier (``test_hook_wiring.test_standalone_launcher_matches_inlined_hook_command``);
        the digest half had none, so ``f80c569`` changed the PreToolUse command without
        updating the constant and the doctor reported ``fail`` for every later revision. That
        surfaced only as three ``'pass' != 'fail'`` assertions that named nothing. This binds
        the constants to the bytes they claim to describe, so the next legitimate command
        change fails here, by name, in the same commit.
        """

        document = json.loads((REPO / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        for event, matcher, pin, label in (
            ("PreToolUse", "Bash", fleet_doctor.TRUSTED_GUARD_HOOK_SHA256, "TRUSTED_GUARD_HOOK_SHA256"),
            (
                "SessionStart",
                "startup|resume|clear|compact",
                fleet_doctor.TRUSTED_SESSION_HOOK_SHA256,
                "TRUSTED_SESSION_HOOK_SHA256",
            ),
        ):
            with self.subTest(event=event):
                registrations = [
                    registration
                    for registration in document["hooks"][event]
                    if registration.get("matcher") == matcher
                ]
                self.assertEqual(1, len(registrations), f"expected one {event} {matcher} registration")
                commands = [
                    hook["command"]
                    for hook in registrations[0]["hooks"]
                    if hook.get("type") == "command"
                ]
                self.assertEqual(1, len(commands), f"expected one {event} command hook")
                digest = hashlib.sha256(commands[0].encode("utf-8")).hexdigest()
                self.assertEqual(
                    pin,
                    digest,
                    f"{label} does not describe the shipped {event} command; "
                    f"review the new command and repin it to {digest}",
                )


if __name__ == "__main__":
    unittest.main()
