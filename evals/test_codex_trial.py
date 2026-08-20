#!/usr/bin/env python3
"""Contract tests for the isolated one-trial Codex/Terra executor."""
from __future__ import annotations

import dataclasses
import json
import hashlib
import contextlib
import io
import os
import runpy
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import codex_harness  # noqa: E402
import codex_model_catalog  # noqa: E402
import codex_routing_grade  # noqa: E402
import codex_snapshot  # noqa: E402
import codex_trial  # noqa: E402
import run_codex_routing  # noqa: E402


def _scenario() -> dict[str, object]:
    return {
        "schema_version": 1,
        "id": "discovery-gcp-ops-cloud-run-startup",
        "mode": "discovery",
        "split": "regression",
        "target": {"kind": "skill", "name": "gcp-ops"},
        "prompt": "Diagnose the startup failure without making changes.",
        "success_criteria": ["A bounded read-only diagnosis."],
        "graders": [{"type": "contains_all", "of": ["READY"]}],
        "routing": {"expect": "fire"},
        "_file": "discovery-gcp-ops-cloud-run-startup.yaml",
        "_source_sha256": "a" * 64,
    }


def _spec() -> run_codex_routing.TrialSpec:
    return run_codex_routing.TrialSpec(
        scenario_id="discovery-gcp-ops-cloud-run-startup",
        cohort="current_only",
        revision=run_codex_routing.CURRENT_REVISION,
        trial=1,
        scenario_sha256="a" * 64,
    )


def _manifest_sha256() -> str:
    return hashlib.sha256(run_codex_routing.MANIFEST_PATH.read_bytes()).hexdigest()


def _trace(response: str = "READY") -> str:
    usage = {
        "input_tokens": 1,
        "cached_input_tokens": 0,
        "cache_write_input_tokens": 0,
        "output_tokens": 1,
        "reasoning_output_tokens": 0,
    }
    events = [
        {"type": "thread.started", "thread_id": "private-thread"},
        {"type": "turn.started"},
        {
            "type": "item.completed",
            "item": {"id": "message-1", "type": "agent_message", "text": response},
        },
        {"type": "turn.completed", "usage": usage},
    ]
    return "\n".join(json.dumps(event, separators=(",", ":")) for event in events)


def _hooks() -> codex_harness.ParsedHookReceipts:
    payload = {
        "session_id": "private-session",
        "transcript_path": "private-transcript",
        "cwd": "private-workspace",
        "hook_event_name": "SessionStart",
        "model": codex_harness.MODEL,
        "permission_mode": codex_harness.HOOK_PERMISSION_MODE,
        "source": "startup",
    }
    return codex_harness.parse_hook_receipts(json.dumps(payload, separators=(",", ":")))


class EnvironmentBoundaryTests(unittest.TestCase):
    def test_posix_private_mode_preserves_only_the_owner_execute_intent(self) -> None:
        self.assertEqual(0o700, codex_trial._posix_private_mode(0o755, directory=False))
        self.assertEqual(0o700, codex_trial._posix_private_mode(0o111, directory=False))
        self.assertEqual(0o600, codex_trial._posix_private_mode(0o644, directory=False))
        self.assertEqual(0o700, codex_trial._posix_private_mode(0o777, directory=True))

    @unittest.skipUnless(os.name == "nt", "Windows ACL ownership is host-specific")
    def test_private_path_setter_assigns_the_current_owner_and_exact_dacl(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            target = root / "private.txt"
            target.write_bytes(b"private")

            codex_trial._set_windows_private_path(target, directory=False)

            self.assertTrue(
                codex_trial._windows_path_acl_is_private(target, directory=False)
            )

    def test_private_acl_shape_rejects_each_security_weakening(self) -> None:
        baseline = {
            "dacl_present": True,
            "protected": True,
            "owner_matches": True,
            "ace_count": 1,
            "ace_type": codex_trial._ACCESS_ALLOWED_ACE_TYPE,
            "ace_flags": 0,
            "access_mask": codex_trial._FILE_ALL_ACCESS,
            "trustee_matches": True,
            "ace_size_matches": True,
            "directory": False,
        }
        self.assertTrue(codex_trial._windows_acl_shape_is_private(**baseline))
        inherited = dict(
            baseline, ace_flags=codex_trial._INHERITED_ACE
        )
        self.assertTrue(codex_trial._windows_acl_shape_is_private(**inherited))
        directory = dict(
            baseline,
            ace_flags=(
                codex_trial._OBJECT_INHERIT_ACE
                | codex_trial._CONTAINER_INHERIT_ACE
            ),
            directory=True,
        )
        self.assertTrue(codex_trial._windows_acl_shape_is_private(**directory))
        inherited_directory = dict(
            directory,
            ace_flags=directory["ace_flags"] | codex_trial._INHERITED_ACE,
        )
        self.assertTrue(
            codex_trial._windows_acl_shape_is_private(**inherited_directory)
        )
        self.assertFalse(
            codex_trial._windows_acl_shape_is_private(
                **dict(directory, ace_flags=codex_trial._OBJECT_INHERIT_ACE)
            )
        )
        self.assertFalse(
            codex_trial._windows_acl_shape_is_private(
                **dict(directory, ace_flags=codex_trial._CONTAINER_INHERIT_ACE)
            )
        )
        mutations = {
            "missing-dacl": {"dacl_present": False},
            "unprotected": {"protected": False},
            "wrong-owner": {"owner_matches": False},
            "zero-ace": {"ace_count": 0},
            "extra-ace": {"ace_count": 2},
            "deny-ace": {"ace_type": 1},
            "file-inheritance": {"ace_flags": codex_trial._OBJECT_INHERIT_ACE},
            "no-propagate": {"ace_flags": 0x04},
            "inherit-only": {"ace_flags": 0x08},
            "success-audit": {"ace_flags": 0x40},
            "failure-audit": {"ace_flags": 0x80},
            "wrong-rights": {"access_mask": codex_trial._FILE_ALL_ACCESS ^ 1},
            "wrong-trustee": {"trustee_matches": False},
            "trailing-ace-bytes": {"ace_size_matches": False},
        }
        for label, mutation in mutations.items():
            with self.subTest(label=label):
                self.assertFalse(
                    codex_trial._windows_acl_shape_is_private(
                        **dict(baseline, **mutation)
                    )
                )

    def test_trial_directory_never_falls_back_to_ambient_temp(self) -> None:
        repository = Path(__file__).resolve().parents[1]
        with self.assertRaisesRegex(
            codex_trial.InstrumentError,
            "private trial parent is required",
        ):
            with codex_trial._private_trial_directory(
                parent=None,
                repository=repository,
            ):
                self.fail("ambient temporary directory was accepted")

    @staticmethod
    def _windows_volume_facts(
        *,
        drive_type: int = 3,
        filesystem: str = "NTFS",
        dos_device: str = r"\Device\HarddiskVolume3",
    ) -> object:
        return SimpleNamespace(
            drive_type=drive_type,
            filesystem=filesystem,
            dos_device=dos_device,
            volume_root="C:\\",
        )

    def test_windows_private_root_requires_local_fixed_ntfs_storage(self) -> None:
        accepted = mock.Mock(return_value=self._windows_volume_facts())
        codex_trial._validate_windows_private_root_locality(
            r"C:\private", volume_probe=accepted
        )
        accepted.assert_called_once_with(r"C:\private", "C:")

        cases = {
            "remote": (self._windows_volume_facts(drive_type=4), "local fixed storage"),
            "removable": (
                self._windows_volume_facts(drive_type=2),
                "local fixed storage",
            ),
            "subst": (
                self._windows_volume_facts(dos_device=r"\??\C:\operator\private"),
                "substituted or mapped",
            ),
            "mapped": (
                self._windows_volume_facts(
                    dos_device=r"\Device\LanmanRedirector\server\share"
                ),
                "substituted or mapped",
            ),
            "non-ntfs": (
                self._windows_volume_facts(filesystem="ReFS"),
                "must use NTFS",
            ),
        }
        for label, (facts, message) in cases.items():
            with self.subTest(label=label), self.assertRaisesRegex(
                codex_trial.InstrumentError, message
            ):
                codex_trial._validate_windows_private_root_locality(
                    r"C:\private", volume_probe=lambda *_args, value=facts: value
                )

    def test_windows_private_root_rejects_unc_before_volume_queries(self) -> None:
        probe = mock.Mock(side_effect=AssertionError("UNC must fail before Win32 probing"))

        with self.assertRaisesRegex(codex_trial.InstrumentError, "local fixed drive"):
            codex_trial._validate_windows_private_root_locality(
                r"\\server\share\private", volume_probe=probe
            )

        probe.assert_not_called()

    def test_trial_validates_the_same_authoritative_external_parent(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            repository = root / "repository"
            private_root = root / "private"
            repository.mkdir()
            private_root.mkdir()
            with mock.patch.object(
                codex_trial,
                "_validate_private_root_locality",
                side_effect=codex_trial.InstrumentError(
                    "unsafe-temp-boundary", "not local fixed storage"
                ),
                create=True,
            ) as validate, self.assertRaisesRegex(
                codex_trial.InstrumentError, "not local fixed storage"
            ):
                codex_trial._validated_private_parent(private_root, repository)

        validate.assert_called_once_with(private_root)

    @unittest.skipUnless(os.name == "nt", "Windows volume APIs are host-specific")
    def test_current_windows_host_temp_root_is_local_fixed_ntfs(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            codex_trial._validate_private_root_locality(Path(raw).resolve())

    def test_scrubbed_environment_rehomes_state_and_drops_secrets(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            home = root / "home"
            codex_home = root / "codex-home"
            temp = root / "temp"
            for path in (home, codex_home, temp):
                path.mkdir()
            source = {
                "PATH": "C:\\operator\\bin",
                "SYSTEMROOT": "C:\\operator\\windows",
                "COMSPEC": "C:\\operator\\cmd.exe",
                "SSL_CERT_FILE": "C:\\operator\\private-ca.pem",
                "OPENAI_API_KEY": "sk-proj-ABCDEFGHIJKLMNOPQRST",
                "AWS_SECRET_ACCESS_KEY": "not-for-the-child",
                "HOME": "C:\\operator",
                "USERPROFILE": "C:\\operator",
                "APPDATA": "C:\\operator\\AppData\\Roaming",
                "UNRELATED": "drop-me",
            }

            env = codex_trial.scrubbed_environment(
                home=home,
                codex_home=codex_home,
                temp=temp,
                source=source,
            )

            self.assertEqual(env["CODEX_HOME"], str(codex_home))
            self.assertEqual(env["HOME"], str(home))
            self.assertEqual(env["USERPROFILE"], str(home))
            self.assertEqual(env["APPDATA"], str(home / "appdata"))
            self.assertEqual(env["LOCALAPPDATA"], str(home / "localappdata"))
            self.assertEqual(env["TEMP"], str(temp))
            self.assertEqual(env["TMP"], str(temp))
            self.assertNotIn("OPENAI_API_KEY", env)
            self.assertNotIn("AWS_SECRET_ACCESS_KEY", env)
            self.assertNotIn("UNRELATED", env)
            self.assertNotIn("C:\\operator", json.dumps(env))
            self.assertNotIn("SSL_CERT_FILE", env)
            self.assertNotIn("SSL_CERT_DIR", env)
            self.assertTrue(Path(env["COMSPEC"]).is_absolute())

    def test_auth_copy_is_create_only_and_rejects_hardlinks(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            source = root / "source-auth.json"
            destination = root / "dest-auth.json"
            secret = b'{"access_token":"sk-proj-ABCDEFGHIJKLMNOPQRST"}'
            source.write_bytes(secret)

            codex_trial.copy_auth_file(source, destination)
            self.assertEqual(destination.read_bytes(), secret)
            with self.assertRaises(codex_trial.InstrumentError):
                codex_trial.copy_auth_file(source, destination)

            hard_source = root / "hard-source.json"
            hard_peer = root / "hard-peer.json"
            hard_source.write_bytes(secret)
            os.link(hard_source, hard_peer)
            with self.assertRaisesRegex(codex_trial.InstrumentError, "ordinary private file"):
                codex_trial.copy_auth_file(hard_source, root / "hard-dest.json")

    def test_auth_copy_invokes_no_external_acl_helper_after_secret_write(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            source = root / "source-auth.json"
            destination = root / "private" / "auth.json"
            destination.parent.mkdir()
            source.write_bytes(b'{"access_token":"opaque-session-value-1234567890"}')
            with mock.patch(
                "codex_trial.subprocess.run",
                side_effect=AssertionError("external ACL helper was invoked"),
            ) as external_process:
                codex_trial.copy_auth_file(source, destination)

            external_process.assert_not_called()
            self.assertTrue(destination.is_file())

    def test_disposable_auth_removal_rejects_missing_and_linked_targets(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            source = root / "source-auth.json"
            destination = root / "auth.json"
            source.write_bytes(b'{"access_token":"opaque-session-value-1234567890"}')
            codex_trial.copy_auth_file(source, destination)

            codex_trial.remove_auth_file(destination)
            self.assertFalse(destination.exists())
            with self.assertRaises(codex_trial.InstrumentError):
                codex_trial.remove_auth_file(destination)

            linked = root / "linked-auth.json"
            peer = root / "linked-peer.json"
            linked.write_bytes(b"private")
            os.link(linked, peer)
            with self.assertRaisesRegex(codex_trial.InstrumentError, "ordinary private file"):
                codex_trial.remove_auth_file(linked)

    def test_auth_guard_detects_exact_opaque_values_not_covered_by_token_regexes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            source = root / "source-auth.json"
            destination = root / "auth.json"
            opaque = "opaque-session-value-1234567890"
            source.write_text(
                json.dumps({"tokens": {"access_token": opaque}}), encoding="utf-8"
            )

            guard = codex_trial.copy_auth_file(source, destination)

            with self.assertRaises(codex_trial.CredentialEchoError):
                guard.reject_output(f"unexpected echo: {opaque}")

    def test_auth_guard_detects_json_escaped_exact_values_after_decode(self) -> None:
        opaque = 'opaque-"session\\value-1234567890'
        guard = codex_trial.AuthGuard((opaque,))
        encoded = json.dumps({"message": opaque})
        self.assertNotIn(opaque, encoded)

        with self.assertRaises(codex_trial.CredentialEchoError):
            guard.reject_jsonl(encoded)

    def test_hook_bundle_is_an_exact_create_only_copy(self) -> None:
        source = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory() as raw:
            destination = Path(raw).resolve(strict=True) / "hook-bundle"
            destination.mkdir()

            bundle = codex_trial.copy_hook_bundle(source, destination)

            self.assertEqual(bundle.file_count, 2)
            self.assertRegex(bundle.source_tree_sha256, r"^[0-9a-f]{64}$")
            self.assertEqual(bundle.source_tree_sha256, bundle.staged_tree_sha256)
            self.assertEqual(bundle.recorder_path, destination / "codex_hook_recorder.py")
            self.assertEqual(
                (destination / "codex_harness.py").read_bytes(),
                (source / "codex_harness.py").read_bytes(),
            )
            with self.assertRaises(codex_trial.InstrumentError):
                codex_trial.copy_hook_bundle(source, destination)

    def test_hook_bundle_verification_rejects_an_extra_import_shadow_file(self) -> None:
        source = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory() as raw:
            destination = Path(raw).resolve(strict=True) / "hook-bundle"
            destination.mkdir()
            bundle = codex_trial.copy_hook_bundle(source, destination)
            (destination / "json.py").write_text(
                "raise RuntimeError('must never be imported')\n", encoding="utf-8"
            )

            with self.assertRaisesRegex(
                codex_trial.InstrumentError, "hook bundle changed during trial"
            ):
                codex_trial.verify_hook_bundle(source, bundle)


class ProbeTests(unittest.TestCase):
    def test_default_probe_runner_uses_the_kill_on_close_process_boundary(self) -> None:
        capture = codex_trial.ProcessCapture(
            stdout="codex-cli 0.147.0\n",
            stderr="",
            returncode=0,
            duration_ms=1,
            timed_out=False,
            output_limited=False,
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            env = {"TEMP": str(root)}
            with (
                mock.patch("codex_trial.launch_process", return_value=capture) as bounded,
                mock.patch(
                    "codex_trial.subprocess.run",
                    side_effect=AssertionError("probe bypassed the bounded process launcher"),
                ),
            ):
                result = codex_trial._default_command_runner(
                    ("C:/private/codex.exe", "--version"),
                    env=env,
                    timeout_s=10,
                    cwd=root,
                )

        self.assertEqual(b"codex-cli 0.147.0\n", result.stdout)
        self.assertEqual(b"", result.stderr)
        self.assertEqual(1, bounded.call_count)

    def test_python_runtime_requires_exact_platform_version_and_executable_pin(self) -> None:
        python_executable = Path(sys.executable).resolve(strict=True)
        python_digest = hashlib.sha256(python_executable.read_bytes()).hexdigest()
        python_version = ".".join(str(item) for item in sys.version_info[:3])
        runtime_platform = codex_trial._runtime_platform()
        with (
            mock.patch.object(codex_trial.sys, "executable", str(python_executable)),
            mock.patch.object(
                run_codex_routing, "PYTHON_EXECUTABLE_SHA256", python_digest
            ),
            mock.patch.object(run_codex_routing, "PYTHON_VERSION", python_version),
            mock.patch.object(
                run_codex_routing, "RUNTIME_PLATFORM", runtime_platform
            ),
        ):
            resolved, observed_digest = codex_trial.verify_python_runtime()
        self.assertEqual(python_executable, resolved)
        self.assertEqual(python_digest, observed_digest)

        with (
            mock.patch.object(codex_trial.sys, "executable", str(python_executable)),
            mock.patch.object(
                run_codex_routing, "PYTHON_EXECUTABLE_SHA256", "0" * 64
            ),
        ):
            with self.assertRaisesRegex(
                codex_trial.InstrumentError, "Python runtime"
            ):
                codex_trial.verify_python_runtime()

    def test_runtime_copy_rejects_executable_bytes_outside_the_manifest_pin(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            source = root / ("codex.exe" if os.name == "nt" else "codex")
            destination = root / ("trial-codex.exe" if os.name == "nt" else "trial-codex")
            source.write_bytes(b"not the authorized Codex executable")

            with self.assertRaisesRegex(codex_trial.InstrumentError, "authorized digest"):
                codex_trial.copy_authorized_executable(source, destination)

    def test_probe_requires_exact_cli_version(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            executable = Path(raw).resolve(strict=True) / ("codex.exe" if os.name == "nt" else "codex")
            executable.write_bytes(b"fake executable")

            def wrong_version(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[bytes]:
                return subprocess.CompletedProcess([], 0, b"codex-cli 0.147.0\n", b"")

            with self.assertRaisesRegex(codex_trial.InstrumentError, "CLI version"):
                codex_trial.probe_codex(
                    executable,
                    {},
                    cwd=Path(raw).resolve(strict=True),
                    command_runner=wrong_version,
                )

    def test_probe_runs_every_command_from_the_private_neutral_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            executable = root / ("codex.exe" if os.name == "nt" else "codex")
            executable.write_bytes(b"fake executable")
            observed: list[Path] = []

            def runner(
                command: tuple[str, ...],
                *,
                env: dict[str, str],
                timeout_s: int,
                cwd: Path,
            ) -> subprocess.CompletedProcess[bytes]:
                del env, timeout_s
                observed.append(cwd)
                if command[-1] == "--version":
                    return subprocess.CompletedProcess(
                        command, 0, b"codex-cli 0.147.0\n", b""
                    )
                return subprocess.CompletedProcess(command, 0, b"{}", b"")

            codex_trial.probe_codex(
                executable,
                {},
                cwd=root,
                expected_cli_version=run_codex_routing.WINDOWS_CODEX_CLI_VERSION,
                command_runner=runner,
            )

            self.assertEqual([root, root], observed)


@unittest.skipIf(os.name == "nt", "POSIX process-group semantics; Windows uses a Job Object")
class PosixBoundaryClosureTests(unittest.TestCase):
    """The narrow idempotence of the POSIX final close, pinned without any timing dependence.

    Two macOS jobs on PR #106 failed at exact head `a2a046e1` when the post-timeout
    `_close_process_boundary` raised `EPERM` from `os.killpg` — after the tree had already been
    terminated and waited on. The end-to-end timeout test can only reproduce that when the runner
    happens to lose the race, so these drive the exact state directly instead.

    The invariant being pinned is deliberately narrow: EPERM is a no-op ONLY once the group leader
    has been reaped. While the process is still running it means the tree was not signalled, and
    tolerating it there would hide a live descendant — the failure this boundary exists to prevent.
    """

    _EPERM = PermissionError(1, "Operation not permitted")

    @staticmethod
    def _process(poll_result: int | None) -> mock.Mock:
        process = mock.Mock(spec=subprocess.Popen)
        process.pid = 4242
        process.poll.return_value = poll_result
        return process

    def test_eperm_after_the_leader_is_reaped_is_a_no_op(self) -> None:
        """The reported failure. A completed termination must not become a test error."""
        with mock.patch.object(codex_trial.os, "killpg", side_effect=self._EPERM):
            codex_trial._close_process_boundary(
                self._process(poll_result=0), None, terminated=True
            )

    def test_eperm_on_a_first_and_only_close_fails_closed(self) -> None:
        """The normal-completion path, where nothing was terminated first.

        `_terminate_process_tree` is never called when the process exits on its own, so this close
        is the FIRST and ONLY kill of the group — and it is what removes a descendant the leader
        spawned before exiting. The leader being reaped says nothing about whether that kill
        worked, so `poll()` alone is not evidence of a completed termination: accepting EPERM here
        would let the descendant escape the boundary silently.
        """
        with mock.patch.object(codex_trial.os, "killpg", side_effect=self._EPERM):
            with self.assertRaises(codex_trial.InstrumentError) as raised:
                codex_trial._close_process_boundary(
                    self._process(poll_result=0), None, terminated=False
                )
        self.assertEqual("process-tree-boundary-failed", raised.exception.reason_code)

    def test_eperm_while_the_tree_still_runs_fails_closed(self) -> None:
        """The half that must NOT be swallowed: unsignalled tree, possible live descendant."""
        with mock.patch.object(codex_trial.os, "killpg", side_effect=self._EPERM):
            with self.assertRaises(codex_trial.InstrumentError) as raised:
                codex_trial._close_process_boundary(
                    self._process(poll_result=None), None, terminated=True
                )
        self.assertEqual("process-tree-boundary-failed", raised.exception.reason_code)

    def test_initial_termination_never_tolerates_eperm(self) -> None:
        """Idempotence belongs to the final close alone. A first-order failure to terminate stays
        fail-closed even though the leader looks reaped, because that reading is what would let a
        surviving descendant through."""
        with mock.patch.object(codex_trial.os, "killpg", side_effect=self._EPERM):
            with self.assertRaises(codex_trial.InstrumentError) as raised:
                codex_trial._terminate_process_tree(self._process(poll_result=0), None)
        self.assertEqual("process-tree-boundary-failed", raised.exception.reason_code)

    def test_an_already_gone_group_stays_tolerated_in_both_paths(self) -> None:
        """ESRCH was always a no-op; narrowing the EPERM case must not disturb it."""
        with mock.patch.object(codex_trial.os, "killpg", side_effect=ProcessLookupError()):
            codex_trial._close_process_boundary(self._process(poll_result=0), None)
            codex_trial._close_process_boundary(
                self._process(poll_result=None), None, terminated=True
            )
            codex_trial._terminate_process_tree(self._process(poll_result=None), None)

    def test_a_successful_kill_is_still_issued_to_the_process_group(self) -> None:
        """Pins that the close actually signals, so the tolerance above cannot be satisfied by a
        boundary that quietly stopped killing anything."""
        with mock.patch.object(codex_trial.os, "killpg") as killpg:
            codex_trial._close_process_boundary(self._process(poll_result=0), None)
        killpg.assert_called_once_with(4242, signal.SIGKILL)


class ProcessBoundaryTests(unittest.TestCase):
    def test_normal_bounded_binary_parent_cannot_leave_a_descendant(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            marker = root / "git-descendant-survived.txt"
            child_code = (
                "import pathlib,time;time.sleep(1.5);"
                f"pathlib.Path({str(marker)!r}).write_text('survived',encoding='utf-8')"
            )
            parent_code = (
                "import subprocess,sys;"
                f"subprocess.Popen([sys.executable,'-c',{child_code!r}])"
            )
            env = os.environ.copy()
            env["TEMP"] = str(root)

            result = codex_trial._bounded_git_runner(
                (sys.executable, "-c", parent_code),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                cwd=root,
                env=env,
                timeout=10,
                check=False,
            )
            time.sleep(2)

            self.assertEqual(0, result.returncode)
            self.assertFalse(marker.exists(), "normal probe descendant process survived")

    def test_timeout_terminates_the_created_process_tree(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            marker = root / "descendant-survived.txt"
            child_code = (
                "import pathlib,time;time.sleep(1.5);"
                f"pathlib.Path({str(marker)!r}).write_text('survived',encoding='utf-8')"
            )
            parent_code = (
                "import subprocess,sys,time;"
                f"subprocess.Popen([sys.executable,'-c',{child_code!r}]);"
                "time.sleep(10)"
            )
            env = os.environ.copy()
            env["TEMP"] = str(root)

            capture = codex_trial.launch_process(
                (sys.executable, "-c", parent_code),
                prompt="",
                cwd=root,
                env=env,
                timeout_s=1,
                output_limit=1024 * 1024,
            )
            time.sleep(2)

            self.assertTrue(capture.timed_out)
            self.assertFalse(marker.exists(), "timed-out descendant process survived")

    def test_output_limit_returns_no_raw_capture(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            env = os.environ.copy()
            env["TEMP"] = str(root)

            capture = codex_trial.launch_process(
                (sys.executable, "-c", "print('x' * 100000)"),
                prompt="",
                cwd=root,
                env=env,
                timeout_s=10,
                output_limit=1024,
            )

            self.assertTrue(capture.output_limited)
            self.assertEqual("", capture.stdout)
            self.assertEqual("", capture.stderr)

    def test_oversized_capture_is_not_read_into_memory(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            env = os.environ.copy()
            env["TEMP"] = str(root)
            with mock.patch(
                "pathlib.Path.read_bytes",
                side_effect=AssertionError("oversized capture must not be read"),
            ):
                capture = codex_trial.launch_process(
                    (sys.executable, "-c", "print('x' * 100000)"),
                    prompt="",
                    cwd=root,
                    env=env,
                    timeout_s=10,
                    output_limit=1024,
                )

            self.assertTrue(capture.output_limited)
            self.assertEqual("", capture.stdout)
            self.assertEqual("", capture.stderr)


class TrialExecutionTests(unittest.TestCase):
    def _run(
        self,
        root: Path,
        capture: codex_trial.ProcessCapture | BaseException,
        *,
        credential_free_only: bool = False,
        canary_probe_mode: str | None = None,
    ) -> tuple[codex_trial.TrialResult, list[Path]]:
        root = root.resolve(strict=True)
        python_executable = Path(sys.executable).resolve(strict=True)
        python_sha256 = hashlib.sha256(python_executable.read_bytes()).hexdigest()
        codex_trial._secure_directory(root)
        codex_bin = root / ("codex.exe" if os.name == "nt" else "codex")
        fake_codex_bytes = b"fake codex executable"
        codex_bin.write_bytes(fake_codex_bytes)
        fake_codex_sha256 = hashlib.sha256(fake_codex_bytes).hexdigest()
        auth = root / "auth.json"
        if not credential_free_only:
            auth.write_bytes(b'{"access_token":"sk-proj-ABCDEFGHIJKLMNOPQRST"}')
        observed_homes: list[Path] = []

        def command_runner(
            command: tuple[str, ...],
            *,
            env: dict[str, str],
            timeout_s: int,
            cwd: Path,
        ) -> subprocess.CompletedProcess[bytes]:
            del env, timeout_s
            self.assertTrue(cwd.is_dir())
            if command[-1] == "--version":
                return subprocess.CompletedProcess(command, 0, b"codex-cli 0.148.0\n", b"")
            self.assertEqual(command[-3:], ("debug", "models", "--bundled"))
            return subprocess.CompletedProcess(command, 0, b"{}", b"")

        def process_runner(
            command: tuple[str, ...],
            *,
            prompt: str,
            cwd: Path,
            env: dict[str, str],
            timeout_s: int,
            output_limit: int,
        ) -> codex_trial.ProcessCapture:
            del command, prompt, cwd, timeout_s, output_limit
            observed_homes.append(Path(env["CODEX_HOME"]))
            if isinstance(capture, BaseException):
                raise capture
            return capture

        snapshot_receipt = codex_snapshot.SnapshotReceipt(
            commit_sha=run_codex_routing.CURRENT_REVISION,
            file_count=10,
            total_bytes=100,
            tree_sha256="1" * 64,
        )
        stage_receipt = codex_snapshot.StageReceipt(
            skill_file_count=2,
            agent_file_count=1,
            transformed_agent_file_count=1,
            total_bytes=90,
            skill_tree_sha256="2" * 64,
            source_agent_tree_sha256="3" * 64,
            staged_agent_tree_sha256="4" * 64,
            project_tree_sha256="5" * 64,
        )
        fake_catalog_bytes = b'{"models":[]}'
        fake_catalog_sha256 = hashlib.sha256(fake_catalog_bytes).hexdigest()
        catalog_receipt = codex_model_catalog.CatalogReceipt(
            model=codex_harness.MODEL,
            source_entry_sha256=codex_model_catalog.EXPECTED_SOURCE_ENTRY_SHA256,
            transformed_entry_sha256=codex_model_catalog.EXPECTED_TRANSFORMED_ENTRY_SHA256,
            safe_catalog_sha256=fake_catalog_sha256,
            source_field_count=37,
            changed_fields=codex_model_catalog.CHANGED_FIELDS,
        )

        def write_catalog(_raw: bytes, destination: Path) -> codex_model_catalog.CatalogReceipt:
            destination.write_bytes(fake_catalog_bytes)
            return catalog_receipt

        def fast_secure(path: Path, *, recursive: bool = False) -> Path:
            del recursive
            path.mkdir(parents=True, exist_ok=True)
            return path

        def stage_project(_snapshot: Path, project: Path):
            if canary_probe_mode == "body":
                target = project / ".agents" / "skills" / "gcp-ops" / "SKILL.md"
                target.parent.mkdir(parents=True, exist_ok=True)
                source = (
                    Path(__file__).resolve().parents[1]
                    / "plugins"
                    / "save-toolkit"
                    / "skills"
                    / "gcp-ops"
                    / "SKILL.md"
                )
                target.write_bytes(source.read_bytes())
            return stage_receipt

        with (
            mock.patch.object(
                codex_snapshot, "materialize_snapshot", return_value=snapshot_receipt
            ) as materialize,
            mock.patch.object(
                codex_snapshot, "stage_neutral_project", side_effect=stage_project
            ),
            mock.patch.object(codex_snapshot, "verify_staged_project", return_value=None),
            mock.patch.object(codex_model_catalog, "write_safe_catalog", side_effect=write_catalog),
            mock.patch("codex_trial._secure_directory", side_effect=fast_secure),
            mock.patch.object(
                codex_trial,
                "verify_python_runtime",
                return_value=(python_executable, python_sha256),
            ),
            mock.patch.object(
                run_codex_routing,
                "CODEX_EXECUTABLE_SHA256",
                fake_codex_sha256,
            ),
            mock.patch.object(
                codex_model_catalog,
                "EXPECTED_SAFE_CATALOG_SHA256",
                fake_catalog_sha256,
            ),
        ):
            arguments = {
                "repo_root": Path(__file__).resolve().parents[1],
                "codex_bin": codex_bin,
                "scenario": _scenario(),
                "spec": _spec(),
                "manifest_sha256": _manifest_sha256(),
                "exact_revision": False,
                "temp_parent": root,
                "command_runner": command_runner,
                "canary_probe_mode": canary_probe_mode,
            }
            if credential_free_only:
                result = codex_trial.run_preflight(**arguments)
            else:
                result = codex_trial.run_trial(
                    auth_file=auth, process_runner=process_runner, **arguments
                )
            self.assertIs(
                codex_trial._bounded_git_runner,
                materialize.call_args.kwargs["command_runner"],
            )
        return result, observed_homes

    def test_preflight_completes_setup_without_auth_or_a_model_process(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            with (
                mock.patch.object(
                    codex_trial,
                    "_preflight_process_forbidden",
                    side_effect=AssertionError(
                        "credential-free preflight launched the model process"
                    ),
                ) as model_process,
                mock.patch.object(
                    codex_trial,
                    "copy_auth_file",
                    side_effect=AssertionError(
                        "credential-free preflight accessed auth"
                    ),
                ) as auth_copy,
            ):
                result, observed_homes = self._run(
                    root,
                    AssertionError("unexpected injected process runner use"),
                    credential_free_only=True,
                )

        self.assertEqual(
            ("credential-free-preflight-pass",), result.reason_codes
        )
        model_process.assert_not_called()
        auth_copy.assert_not_called()
        self.assertEqual([], observed_homes)
        self.assertIsNotNone(result.runtime_facts)
        serialized = json.dumps(result.as_dict(), sort_keys=True)
        self.assertNotIn(str(root), serialized)
        self.assertNotIn("sk-proj-", serialized)

    def test_body_probe_preflight_records_the_exact_staged_skill_body(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            result, observed_homes = self._run(
                Path(raw).resolve(strict=True),
                AssertionError("preflight must not launch a model"),
                credential_free_only=True,
                canary_probe_mode="body",
            )

        self.assertEqual([], observed_homes)
        self.assertEqual(
            "gcp-ops", result.runtime_facts["selected_skill_name"]
        )
        self.assertEqual(
            run_codex_routing.CANARY_SKILL_BODY_SHA256,
            result.runtime_facts["selected_skill_body_sha256"],
        )

    def test_success_is_graded_and_serialized_without_raw_content(self) -> None:
        capture = codex_trial.ProcessCapture(
            stdout=_trace(),
            stderr="",
            returncode=0,
            duration_ms=123,
            timed_out=False,
            output_limited=False,
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            with mock.patch(
                "codex_trial.codex_hook_recorder.load_receipts", return_value=_hooks()
            ):
                result, observed_homes = self._run(root, capture)
            serialized = json.dumps(result.as_dict(), sort_keys=True)

            self.assertEqual(result.state, codex_routing_grade.VerdictState.PASS)
            self.assertEqual(result.reason_codes, ("observational-behavior-pass",))
            self.assertNotIn("READY", serialized)
            self.assertNotIn("sk-proj-", serialized)
            self.assertNotIn(str(root), serialized)
            self.assertEqual(len(observed_homes), 1)
            self.assertFalse(observed_homes[0].exists())
            self.assertFalse(result.as_dict()["authority"]["baseline_eligible"])
            self.assertFalse(result.as_dict()["authority"]["release_granted"])
            self.assertEqual(
                "no-model-tools-non-root",
                result.as_dict()["configuration"]["tool_policy"],
            )

    def test_invalid_trace_is_distinguished_before_hook_receipts_are_loaded(self) -> None:
        capture = codex_trial.ProcessCapture(
            stdout='{"type":"unsupported-private-event"}\n',
            stderr="",
            returncode=0,
            duration_ms=1,
            timed_out=False,
            output_limited=False,
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            with mock.patch(
                "codex_trial.codex_hook_recorder.load_receipts",
                side_effect=AssertionError("receipts must not be loaded after an invalid trace"),
            ) as load_receipts:
                result, _ = self._run(root, capture)

        self.assertEqual(codex_routing_grade.VerdictState.INCONCLUSIVE, result.state)
        self.assertEqual(("trace-invalid",), result.reason_codes)
        self.assertIsNone(result.trace_facts)
        self.assertIsNone(result.hook_facts)
        load_receipts.assert_not_called()

    def test_invalid_hook_receipts_are_distinguished_without_private_diagnostics(self) -> None:
        capture = codex_trial.ProcessCapture(
            stdout=_trace(),
            stderr="",
            returncode=0,
            duration_ms=1,
            timed_out=False,
            output_limited=False,
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            with mock.patch(
                "codex_trial.codex_hook_recorder.load_receipts",
                side_effect=ValueError("private hook parser detail"),
            ):
                result, _ = self._run(root, capture)

        serialized = json.dumps(result.as_dict(), sort_keys=True)
        self.assertEqual(codex_routing_grade.VerdictState.INCONCLUSIVE, result.state)
        self.assertEqual(("hook-invalid",), result.reason_codes)
        self.assertIsNone(result.trace_facts)
        self.assertIsNone(result.hook_facts)
        self.assertNotIn("private hook parser detail", serialized)

    def test_serialized_root_tool_policy_is_explicitly_unscored(self) -> None:
        contract = codex_trial.TrialContract(
            scenario_id="root-case",
            cohort="current_only",
            revision=run_codex_routing.CURRENT_REVISION,
            trial=1,
            scenario_sha256="a" * 64,
            prompt_sha256="b" * 64,
            manifest_sha256="c" * 64,
            prompt="private",
            enable_multi_agent=True,
        )

        result = codex_trial._base_result(
            contract,
            state=codex_routing_grade.VerdictState.INCONCLUSIVE,
            reason_codes=("root-delegation-unobservable-v2",),
            exact_revision=False,
        )

        self.assertEqual(
            "no-local-effect-tools-root-collaboration-unscored",
            result.as_dict()["configuration"]["tool_policy"],
        )

    def test_disposable_auth_is_absent_before_response_grading(self) -> None:
        capture = codex_trial.ProcessCapture(
            stdout=_trace(),
            stderr="",
            returncode=0,
            duration_ms=123,
            timed_out=False,
            output_limited=False,
        )
        original_grade_trial = codex_routing_grade.grade_trial

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)

            def assert_auth_absent_before_grade(*args, **kwargs):
                disposable_auth = list(
                    root.glob("save-toolkit-terra-trial-*/codex-home/auth.json")
                )
                self.assertEqual([], disposable_auth)
                return original_grade_trial(*args, **kwargs)

            with (
                mock.patch(
                    "codex_trial.codex_hook_recorder.load_receipts",
                    return_value=_hooks(),
                ),
                mock.patch(
                    "codex_trial.codex_routing_grade.grade_trial",
                    side_effect=assert_auth_absent_before_grade,
                ),
            ):
                result, _ = self._run(root, capture)

        self.assertEqual(codex_routing_grade.VerdictState.PASS, result.state)

    def test_interrupt_during_launch_removes_disposable_auth_before_propagating(self) -> None:
        removed = False
        original_remove_auth_file = codex_trial.remove_auth_file

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)

            def observe_removal(path: Path) -> None:
                nonlocal removed
                self.assertTrue(path.is_file())
                original_remove_auth_file(path)
                self.assertFalse(path.exists())
                removed = True

            with mock.patch(
                "codex_trial.remove_auth_file", side_effect=observe_removal
            ):
                with self.assertRaises(KeyboardInterrupt):
                    self._run(root, KeyboardInterrupt())

        self.assertTrue(removed)

    def test_disposable_auth_is_absent_before_decoded_output_scanning(self) -> None:
        capture = codex_trial.ProcessCapture(
            stdout=_trace(),
            stderr="",
            returncode=0,
            duration_ms=123,
            timed_out=False,
            output_limited=False,
        )
        original_reject_jsonl = codex_trial.AuthGuard.reject_jsonl

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)

            def assert_auth_absent_before_decode(guard, text):
                disposable_auth = list(
                    root.glob("save-toolkit-terra-trial-*/codex-home/auth.json")
                )
                self.assertEqual([], disposable_auth)
                return original_reject_jsonl(guard, text)

            with (
                mock.patch(
                    "codex_trial.codex_hook_recorder.load_receipts",
                    return_value=_hooks(),
                ),
                mock.patch.object(
                    codex_trial.AuthGuard,
                    "reject_jsonl",
                    new=assert_auth_absent_before_decode,
                ),
            ):
                result, _ = self._run(root, capture)

        self.assertEqual(codex_routing_grade.VerdictState.PASS, result.state)

    def test_timeout_is_inconclusive_and_never_loads_hook_receipts(self) -> None:
        capture = codex_trial.ProcessCapture(
            stdout="partial raw output",
            stderr="",
            returncode=-1,
            duration_ms=300_000,
            timed_out=True,
            output_limited=False,
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            with mock.patch(
                "codex_trial.codex_hook_recorder.load_receipts",
                side_effect=AssertionError("receipts must not be parsed after a timeout"),
            ):
                result, _ = self._run(root, capture)

            self.assertEqual(result.state, codex_routing_grade.VerdictState.INCONCLUSIVE)
            self.assertEqual(result.reason_codes, ("process-timeout",))
            self.assertIsNone(result.trace_facts)
            self.assertIsNone(result.hook_facts)

    def test_timeout_still_runs_post_trial_integrity_and_drift_wins(self) -> None:
        capture = codex_trial.ProcessCapture(
            stdout="partial raw output",
            stderr="",
            returncode=-1,
            duration_ms=300_000,
            timed_out=True,
            output_limited=False,
        )
        drift = codex_trial.InstrumentError(
            "hook-bundle-drift", "trusted hook bundle changed during trial"
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            with (
                mock.patch(
                    "codex_trial.codex_hook_recorder.load_receipts",
                    side_effect=AssertionError("receipts must not be parsed after a timeout"),
                ),
                mock.patch(
                    "codex_trial.verify_hook_bundle", side_effect=(None, drift)
                ) as verify_hooks,
            ):
                result, _ = self._run(root, capture)

            self.assertEqual(
                codex_routing_grade.VerdictState.INCONCLUSIVE, result.state
            )
            self.assertEqual(("post-trial-input-drift",), result.reason_codes)
            self.assertEqual(2, verify_hooks.call_count)

    def test_original_auth_guard_runs_before_auth_refresh_can_fail(self) -> None:
        capture = codex_trial.ProcessCapture(
            stdout="sk-proj-ABCDEFGHIJKLMNOPQRST",
            stderr="",
            returncode=0,
            duration_ms=1,
            timed_out=False,
            output_limited=False,
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            with mock.patch(
                "codex_trial.load_auth_guard",
                side_effect=codex_trial.InstrumentError(
                    "auth-refresh-failed", "refresh must not mask the original guard"
                ),
            ):
                result, _ = self._run(root, capture)

        self.assertEqual(
            codex_routing_grade.VerdictState.INCONCLUSIVE, result.state
        )
        self.assertEqual(("credential-shaped-output",), result.reason_codes)

    def test_unexpected_auth_refresh_exception_removes_copy_before_propagation(self) -> None:
        capture = codex_trial.ProcessCapture(
            stdout=_trace(),
            stderr="",
            returncode=0,
            duration_ms=1,
            timed_out=False,
            output_limited=False,
        )
        original_remove = codex_trial.remove_auth_file
        observed_existence: list[bool] = []

        def recording_remove(path: Path) -> None:
            observed_existence.append(path.exists())
            original_remove(path)
            observed_existence.append(path.exists())

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            with (
                mock.patch(
                    "codex_trial.load_auth_guard",
                    side_effect=RecursionError("unexpected refresh failure"),
                ),
                mock.patch(
                    "codex_trial.remove_auth_file",
                    side_effect=recording_remove,
                ),
                self.assertRaisesRegex(RecursionError, "unexpected refresh failure"),
            ):
                self._run(root, capture)

        self.assertEqual([True, False], observed_existence)

    def test_auth_refresh_interrupts_remove_copy_before_propagation(self) -> None:
        capture = codex_trial.ProcessCapture(
            stdout=_trace(),
            stderr="",
            returncode=0,
            duration_ms=1,
            timed_out=False,
            output_limited=False,
        )
        original_remove = codex_trial.remove_auth_file
        for pending in (KeyboardInterrupt(), SystemExit(19)):
            observed_existence: list[bool] = []

            def recording_remove(path: Path) -> None:
                observed_existence.append(path.exists())
                original_remove(path)
                observed_existence.append(path.exists())

            with self.subTest(exception=type(pending).__name__), tempfile.TemporaryDirectory() as raw:
                root = Path(raw).resolve(strict=True)
                with (
                    mock.patch("codex_trial.load_auth_guard", side_effect=pending),
                    mock.patch(
                        "codex_trial.remove_auth_file",
                        side_effect=recording_remove,
                    ),
                    self.assertRaises(type(pending)) as raised,
                ):
                    self._run(root, capture)

            self.assertEqual([True, False], observed_existence)
            if isinstance(pending, SystemExit):
                self.assertEqual(19, raised.exception.code)

    def test_auth_refresh_instrument_error_remains_a_sanitized_verdict(self) -> None:
        capture = codex_trial.ProcessCapture(
            stdout=_trace(),
            stderr="",
            returncode=0,
            duration_ms=1,
            timed_out=False,
            output_limited=False,
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            with mock.patch(
                "codex_trial.load_auth_guard",
                side_effect=codex_trial.InstrumentError(
                    "auth-refresh-failed", "private refresh diagnostic"
                ),
            ):
                result, _ = self._run(root, capture)

        self.assertEqual(codex_routing_grade.VerdictState.INCONCLUSIVE, result.state)
        self.assertEqual(("auth-refresh-failed",), result.reason_codes)

    def test_cleanup_failure_overrides_a_tentative_pass_and_warns_transiently(self) -> None:
        capture = codex_trial.ProcessCapture(
            stdout=_trace(),
            stderr="",
            returncode=0,
            duration_ms=123,
            timed_out=False,
            output_limited=False,
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve(strict=True)
            warning = io.StringIO()
            with (
                mock.patch(
                    "codex_trial.codex_hook_recorder.load_receipts", return_value=_hooks()
                ),
                mock.patch("codex_trial.shutil.rmtree", side_effect=OSError("locked")),
                contextlib.redirect_stderr(warning),
            ):
                result, observed_homes = self._run(root, capture)

            residual_root = observed_homes[0].parent
            self.assertEqual(
                codex_routing_grade.VerdictState.INCONCLUSIVE, result.state
            )
            self.assertEqual(("private-cleanup-failed",), result.reason_codes)
            self.assertIn("remove this credential-bearing path manually", warning.getvalue())
            self.assertTrue(residual_root.exists())
            # The failure was synthetic; remove only the exact child created by this test.
            import shutil

            shutil.rmtree(residual_root)

    def test_scenario_and_trial_spec_must_match_before_setup(self) -> None:
        scenario = _scenario()
        scenario["id"] = "different-scenario"
        with self.assertRaisesRegex(codex_trial.TrialContractError, "scenario id"):
            codex_trial.validate_trial_contract(
                scenario,
                _spec(),
                manifest_sha256=_manifest_sha256(),
            )

    def test_scenario_digest_must_match_the_manifest_bound_trial_spec(self) -> None:
        scenario = _scenario()
        scenario["_source_sha256"] = "c" * 64
        with self.assertRaisesRegex(codex_trial.TrialContractError, "scenario digest"):
            codex_trial.validate_trial_contract(
                scenario,
                _spec(),
                manifest_sha256=_manifest_sha256(),
            )

    def test_manifest_digest_must_match_the_evaluator_manifest_bytes(self) -> None:
        with self.assertRaisesRegex(codex_trial.TrialContractError, "evaluator manifest"):
            codex_trial.validate_trial_contract(
                _scenario(),
                _spec(),
                manifest_sha256="0" * 64,
            )

    def test_canary_body_probe_binds_the_explicit_skill_and_effective_prompt_hash(self) -> None:
        scenario = _scenario()

        contract = codex_trial.validate_trial_contract(
            scenario,
            _spec(),
            manifest_sha256=_manifest_sha256(),
            canary_probe_mode="body",
        )

        expected_prompt = f"$gcp-ops\n\n{scenario['prompt']}"
        self.assertEqual(expected_prompt, contract.prompt)
        self.assertEqual(
            hashlib.sha256(expected_prompt.encode("utf-8")).hexdigest(),
            contract.prompt_sha256,
        )
        self.assertEqual("explicit-skill-body-probe", contract.invocation_mode)
        result = codex_trial._base_result(
            contract,
            state=codex_routing_grade.VerdictState.INCONCLUSIVE,
            reason_codes=("credential-free-preflight-pass",),
            exact_revision=False,
        )
        self.assertEqual(
            "explicit-skill-body-probe",
            result.as_dict()["configuration"]["invocation_mode"],
        )

    def test_canary_description_probe_binds_a_target_blind_selection_prompt(self) -> None:
        scenario = _scenario()

        contract = codex_trial.validate_trial_contract(
            scenario,
            _spec(),
            manifest_sha256=_manifest_sha256(),
            canary_probe_mode="description",
        )

        expected_prompt = (
            f"{run_codex_routing.CANARY_DESCRIPTION_PROMPT_PREFIX}"
            f"{scenario['prompt']}"
        )
        self.assertEqual(expected_prompt, contract.prompt)
        self.assertNotIn("gcp-ops", contract.prompt)
        self.assertNotIn("$", contract.prompt)
        self.assertEqual(
            hashlib.sha256(expected_prompt.encode("utf-8")).hexdigest(),
            contract.prompt_sha256,
        )
        self.assertEqual("description-selection-probe", contract.invocation_mode)

    def test_ordinary_campaign_contract_remains_implicit_discovery(self) -> None:
        scenario = _scenario()

        contract = codex_trial.validate_trial_contract(
            scenario,
            _spec(),
            manifest_sha256=_manifest_sha256(),
        )

        self.assertEqual(scenario["prompt"], contract.prompt)
        self.assertEqual("implicit-discovery", contract.invocation_mode)

    def test_explicit_body_probe_rejects_any_non_canary_coordinate(self) -> None:
        scenario = _scenario()
        scenario["id"] = "discovery-obs-logs-cloud-logging"
        spec = run_codex_routing.TrialSpec(
            scenario_id="discovery-obs-logs-cloud-logging",
            cohort="paired",
            revision=run_codex_routing.CURRENT_REVISION,
            trial=1,
            scenario_sha256="a" * 64,
        )

        with self.assertRaisesRegex(
            codex_trial.TrialContractError, "fixed development canary"
        ):
            codex_trial.validate_trial_contract(
                scenario,
                spec,
                manifest_sha256=_manifest_sha256(),
                canary_probe_mode="body",
            )

    def test_explicit_body_probe_rejects_a_second_campaign_trial_coordinate(self) -> None:
        scenario = _scenario()
        spec = dataclasses.replace(_spec(), trial=2)

        with self.assertRaisesRegex(
            codex_trial.TrialContractError, "fixed development canary"
        ):
            codex_trial.validate_trial_contract(
                scenario,
                spec,
                manifest_sha256=_manifest_sha256(),
                canary_probe_mode="body",
            )

    def test_canary_probe_mode_rejects_unknown_or_non_text_values(self) -> None:
        for value in ("other", True, 1):
            with self.subTest(value=value), self.assertRaisesRegex(
                codex_trial.TrialContractError, "probe mode"
            ):
                codex_trial.validate_trial_contract(
                    _scenario(),
                    _spec(),
                    manifest_sha256=_manifest_sha256(),
                    canary_probe_mode=value,
                )

    def test_staged_entrypoint_trial_spec_has_one_shared_runtime_identity(self) -> None:
        staged_namespace = runpy.run_path(
            str(Path(run_codex_routing.__file__).resolve()),
            run_name="_staged_run_codex_routing",
        )
        staged_spec = staged_namespace["TrialSpec"](
            scenario_id=_spec().scenario_id,
            cohort=_spec().cohort,
            revision=_spec().revision,
            trial=_spec().trial,
            scenario_sha256=_spec().scenario_sha256,
        )

        contract = codex_trial.validate_trial_contract(
            _scenario(),
            staged_spec,
            manifest_sha256=_manifest_sha256(),
        )

        self.assertEqual(_spec().scenario_id, contract.scenario_id)


if __name__ == "__main__":
    unittest.main()
