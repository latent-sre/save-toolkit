"""Negative and success-path contracts for isolated verification."""

from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import evidence_envelope
import verification_sandbox


IMAGE = "example.test/verifier@sha256:" + "a" * 64
REVISION = "b" * 40


class VerificationSandboxTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.base = Path(self.temporary.name)
        self.source = self.base / "source"
        self.source.mkdir()
        (self.source / "fixture.txt").write_text("fixed input\n", encoding="utf-8")
        self.digest = verification_sandbox.tree_digest(self.source)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _config(
        self,
        command: tuple[str, ...] = ("python", "-m", "unittest"),
    ) -> verification_sandbox.SandboxConfig:
        return verification_sandbox.SandboxConfig(
            engine="docker",
            image=IMAGE,
            source=self.source,
            expected_tree_digest=self.digest,
            command=command,
            timeout_seconds=60,
        )

    @staticmethod
    def _runner(run_result: verification_sandbox.ProcessResult):
        def runner(argv, timeout, environment):
            if tuple(argv[1:3]) == ("image", "inspect"):
                return verification_sandbox.ProcessResult(0, b"sha256:" + b"c" * 64, b"")
            if tuple(argv[1:3]) == ("container", "inspect"):
                return verification_sandbox.ProcessResult(1, b"", b"Error: No such container")
            if argv[1] == "rm":
                return verification_sandbox.ProcessResult(1, b"", b"No such container")
            return run_result

        return runner

    def test_command_has_fail_closed_isolation_before_image(self) -> None:
        command = verification_sandbox.build_command(
            self._config(("--privileged", "not-an-engine-option")),
            container_name="sre-verify-0123456789abcdef",
        )
        image_index = command.index(IMAGE)
        for required in (
            "--rm",
            "--pull",
            "never",
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
        ):
            self.assertIn(required, command[:image_index])
        self.assertEqual(["--privileged", "not-an-engine-option"], command[image_index + 1 :])
        source_mount = command[command.index("--mount") + 1]
        self.assertIn("dst=/workspace", source_mount)
        self.assertIn("readonly", source_mount)
        self.assertIn("/scratch:rw,nosuid,nodev,size=256m", command)
        self.assertNotIn(str(self.base / "scratch"), command)
        self.assertIn("sre-agents.verification=sre-verify-0123456789abcdef", command)

    def test_unpinned_image_oversized_scratch_and_root_user_are_rejected(self) -> None:
        with self.assertRaisesRegex(verification_sandbox.SandboxError, "docker or podman"):
            verification_sandbox.build_command(
                verification_sandbox.SandboxConfig(
                    "curl", IMAGE, self.source, self.digest, ("true",),
                ),
                container_name="sre-verify-0123456789abcdef",
            )
        with self.assertRaisesRegex(verification_sandbox.SandboxError, "name@sha256"):
            verification_sandbox.build_command(
                verification_sandbox.SandboxConfig(
                    "docker", "example.test/verifier:latest", self.source, self.digest, ("true",),
                ),
                container_name="sre-verify-0123456789abcdef",
            )
        with self.assertRaisesRegex(verification_sandbox.SandboxError, "SHA-256"):
            verification_sandbox.build_command(
                verification_sandbox.SandboxConfig(
                    "docker", IMAGE, self.source, "d" * 40, ("true",),
                ),
                container_name="sre-verify-0123456789abcdef",
            )
        with self.assertRaisesRegex(verification_sandbox.SandboxError, "between 1m and 4g"):
            verification_sandbox.build_command(
                verification_sandbox.SandboxConfig(
                    "docker", IMAGE, self.source, self.digest, ("true",), scratch_size="5g",
                ),
                container_name="sre-verify-0123456789abcdef",
            )
        with self.assertRaisesRegex(verification_sandbox.SandboxError, "non-root"):
            verification_sandbox.build_command(
                verification_sandbox.SandboxConfig(
                    "docker", IMAGE, self.source, self.digest, ("true",), user="0:0",
                ),
                container_name="sre-verify-0123456789abcdef",
            )

    def test_source_links_git_metadata_and_digest_drift_are_rejected(self) -> None:
        (self.source / ".git").mkdir()
        with self.assertRaisesRegex(verification_sandbox.SandboxError, "git metadata"):
            verification_sandbox.tree_digest(self.source)
        (self.source / ".git").rmdir()
        (self.source / "fixture.txt").write_text("changed\n", encoding="utf-8")
        with self.assertRaisesRegex(verification_sandbox.SandboxError, "preapproved digest"):
            verification_sandbox.execute(
                self._config(),
                target_revision=REVISION,
                criterion="fixture",
                runner=self._runner(verification_sandbox.ProcessResult(0, b"", b"")),
            )

    def test_source_change_during_execution_makes_result_inconclusive(self) -> None:
        def runner(argv, timeout, environment):
            if tuple(argv[1:3]) == ("image", "inspect"):
                return verification_sandbox.ProcessResult(0, b"sha256:" + b"c" * 64, b"")
            if argv[1] == "run":
                (self.source / "fixture.txt").write_text("host raced\n", encoding="utf-8")
                return verification_sandbox.ProcessResult(0, b"passed\n", b"")
            if tuple(argv[1:3]) == ("container", "inspect"):
                return verification_sandbox.ProcessResult(1, b"", b"No such container")
            return verification_sandbox.ProcessResult(0, b"", b"")

        envelope = verification_sandbox.execute(
            self._config(),
            target_revision=REVISION,
            criterion="source stability",
            runner=runner,
        )
        self.assertEqual("inconclusive", envelope["status"])
        self.assertTrue(any("source tree changed" in item for item in envelope["limitations"]))

    def test_success_emits_valid_typed_evidence_and_checks_residue(self) -> None:
        calls: list[tuple[str, ...]] = []
        base_runner = self._runner(verification_sandbox.ProcessResult(0, b"tests passed\n", b""))

        def runner(argv, timeout, environment):
            calls.append(tuple(argv))
            return base_runner(argv, timeout, environment)

        fixed = datetime(2026, 7, 31, 12, 0, tzinfo=timezone.utc)
        envelope = verification_sandbox.execute(
            self._config(),
            target_revision=REVISION,
            criterion="unit tests pass",
            run_id="run-1",
            task_id="task-1",
            attempt_id="attempt-1",
            runner=runner,
            now=lambda: fixed,
        )
        evidence_envelope.validate_envelope(envelope)
        self.assertEqual("pass", envelope["status"])
        self.assertEqual(self.digest, envelope["target"]["tree_digest"])
        self.assertEqual("none", envelope["isolation"]["network"])
        self.assertEqual(False, envelope["source"]["residue"])
        self.assertFalse(envelope["source"]["cleanup_attempted"])
        self.assertEqual(3, len(calls))

    def test_timeout_cleanup_failure_and_residue_are_inconclusive(self) -> None:
        timeout = verification_sandbox.execute(
            self._config(),
            target_revision=REVISION,
            criterion="timeout",
            runner=self._runner(
                verification_sandbox.ProcessResult(None, b"partial", b"", timed_out=True)
            ),
        )
        self.assertEqual("inconclusive", timeout["status"])

        inspection_count = 0

        def cleanup_failure(argv, timeout, environment):
            nonlocal inspection_count
            if tuple(argv[1:3]) == ("image", "inspect"):
                return verification_sandbox.ProcessResult(0, b"sha256:" + b"c" * 64, b"")
            if argv[1] == "rm":
                return verification_sandbox.ProcessResult(9, b"", b"failed")
            if tuple(argv[1:3]) == ("container", "inspect"):
                inspection_count += 1
                if inspection_count == 1:
                    name = argv[-1].encode("ascii")
                    return verification_sandbox.ProcessResult(
                        0, b"d" * 64 + b"|" + name, b""
                    )
                return verification_sandbox.ProcessResult(0, b"container", b"")
            return verification_sandbox.ProcessResult(0, b"", b"")

        residue = verification_sandbox.execute(
            self._config(),
            target_revision=REVISION,
            criterion="cleanup",
            runner=cleanup_failure,
        )
        self.assertEqual("inconclusive", residue["status"])
        self.assertTrue(any("cleanup" in item or "exists" in item for item in residue["limitations"]))

    def test_foreign_name_collision_is_never_removed(self) -> None:
        calls: list[tuple[str, ...]] = []

        def runner(argv, timeout, environment):
            calls.append(tuple(argv))
            if tuple(argv[1:3]) == ("image", "inspect"):
                return verification_sandbox.ProcessResult(0, b"sha256:" + b"c" * 64, b"")
            if argv[1] == "run":
                return verification_sandbox.ProcessResult(125, b"", b"name already in use")
            if tuple(argv[1:3]) == ("container", "inspect"):
                return verification_sandbox.ProcessResult(
                    0, b"d" * 64 + b"|someone-elses-container", b""
                )
            self.fail(f"unexpected command: {argv}")

        envelope = verification_sandbox.execute(
            self._config(),
            target_revision=REVISION,
            criterion="collision safety",
            runner=runner,
        )
        self.assertEqual("inconclusive", envelope["status"])
        self.assertFalse(envelope["source"]["cleanup_attempted"])
        self.assertFalse(any(argv[1] == "rm" for argv in calls))

    def test_missing_local_image_is_inconclusive_and_does_not_run_command(self) -> None:
        calls: list[tuple[str, ...]] = []

        def runner(argv, timeout, environment):
            calls.append(tuple(argv))
            return verification_sandbox.ProcessResult(1, b"", b"not present")

        envelope = verification_sandbox.execute(
            self._config(),
            target_revision=REVISION,
            criterion="image preflight",
            runner=runner,
        )
        self.assertEqual("inconclusive", envelope["status"])
        self.assertEqual(1, len(calls))
        self.assertFalse(envelope["source"]["verification_executed"])

    def test_process_output_limit_terminates_a_long_lived_producer(self) -> None:
        started = time.monotonic()
        result = verification_sandbox._run_process(
            (
                sys.executable,
                "-c",
                "import sys,time; sys.stdout.buffer.write(b'x' * "
                f"{verification_sandbox.MAX_CAPTURE_BYTES + 65536}); "
                "sys.stdout.buffer.flush(); time.sleep(30)",
            ),
            10,
            os.environ,
        )
        elapsed = time.monotonic() - started
        self.assertTrue(result.output_limit_exceeded)
        self.assertFalse(result.timed_out)
        self.assertIsNotNone(result.returncode)
        self.assertLessEqual(len(result.stdout), verification_sandbox.MAX_CAPTURE_BYTES)
        self.assertLess(elapsed, 5)

    def test_output_limit_forces_an_inconclusive_verdict(self) -> None:
        limited = verification_sandbox.execute(
            self._config(),
            target_revision=REVISION,
            criterion="bounded output",
            runner=self._runner(
                verification_sandbox.ProcessResult(
                    -15,
                    b"x" * verification_sandbox.MAX_CAPTURE_BYTES,
                    b"",
                    output_limit_exceeded=True,
                )
            ),
        )
        self.assertEqual("inconclusive", limited["status"])
        self.assertTrue(any("capture limit" in item for item in limited["limitations"]))

    def test_output_limit_inspects_ownership_force_removes_and_checks_residue(self) -> None:
        calls: list[tuple[str, ...]] = []
        inspect_count = 0
        owned_id = "d" * 64

        def runner(argv, timeout, environment):
            nonlocal inspect_count
            calls.append(tuple(argv))
            if tuple(argv[1:3]) == ("image", "inspect"):
                return verification_sandbox.ProcessResult(0, b"sha256:" + b"c" * 64, b"")
            if argv[1] == "run":
                return verification_sandbox.ProcessResult(
                    -15,
                    b"x" * verification_sandbox.MAX_CAPTURE_BYTES,
                    b"",
                    output_limit_exceeded=True,
                )
            if tuple(argv[1:3]) == ("container", "inspect"):
                inspect_count += 1
                if inspect_count == 1:
                    return verification_sandbox.ProcessResult(
                        0, owned_id.encode("ascii") + b"|" + argv[-1].encode("ascii"), b""
                    )
                return verification_sandbox.ProcessResult(1, b"", b"No such container")
            if argv[1] == "rm":
                self.assertEqual(owned_id, argv[-1])
                return verification_sandbox.ProcessResult(0, b"", b"")
            self.fail(f"unexpected command: {argv}")

        envelope = verification_sandbox.execute(
            self._config(),
            target_revision=REVISION,
            criterion="bounded output cleanup",
            runner=runner,
        )
        self.assertEqual("inconclusive", envelope["status"])
        self.assertTrue(envelope["source"]["cleanup_attempted"])
        self.assertFalse(envelope["source"]["residue"])
        self.assertTrue(any(argv[1] == "rm" for argv in calls))

    def test_engine_environment_drops_remote_and_secret_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch.dict(
                os.environ,
                {
                    "PATH": "C:/tools",
                    "DOCKER_HOST": "tcp://remote.example:2375",
                    "DOCKER_CONTEXT": "remote",
                    "DOCKER_CONFIG": "C:/secret-config",
                    "OPENAI_API_KEY": "secret",
                },
                clear=True,
            ):
                environment = verification_sandbox._engine_environment(
                    Path(temporary) / "client", "docker"
                )
        self.assertEqual("C:/tools", environment["PATH"])
        self.assertNotEqual("tcp://remote.example:2375", environment["DOCKER_HOST"])
        self.assertNotIn("DOCKER_CONTEXT", environment)
        self.assertNotIn("OPENAI_API_KEY", environment)


if __name__ == "__main__":
    unittest.main()
