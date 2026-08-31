from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import copy
from io import BytesIO, StringIO
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
from unittest import mock


SANDBOX_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SANDBOX_ROOT))

from activate import (  # noqa: E402
    ActivationError,
    RunClaim,
    _command_payload,
    _requires_reconciliation_timeline,
    _validate_published_run,
    _validate_reconciliation_pair,
    activate_runtime,
    cleanup_published_resources,
    execute_validated_compose,
    parse_args,
    verify_and_publish_evidence,
)
from build_images import (  # noqa: E402
    SnapshotError,
    _atomic_replace_lock,
    build_and_lock,
    prepare_git_snapshot,
    safe_extract_archive,
)
from preflight import (  # noqa: E402
    ContextIdentity,
    DockerCLI,
    PreflightError,
    RepositoryLayout,
    ResourceRecord,
    ResourceState,
    assert_no_ambient_docker_authority,
    expected_resource_records,
    project_scope,
    run_process,
    scrub_environment,
    trusted_layout,
    validate_local_context,
    validate_resource_mode,
)


SOURCE_REVISION = "a" * 40
CASE_ID = "mission-healthy-001"
CASE_DIGEST = "74266b9c39a7733128e25f7279bb18820664bfbd6c11d8b0a6a3fa5e53a685d1"


def completed(arguments: list[str], stdout: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(arguments, 0, stdout=stdout, stderr="")


class ContextBoundaryTests(unittest.TestCase):
    def test_ambient_remote_and_selector_environment_is_rejected(self) -> None:
        for name in (
            "DOCKER_HOST",
            "DOCKER_CONTEXT",
            "DOCKER_TLS_VERIFY",
            "DOCKER_CERT_PATH",
            "DOCKER_CONFIG",
            "COMPOSE_FILE",
            "COMPOSE_PROFILES",
        ):
            with self.subTest(name=name):
                with self.assertRaisesRegex(PreflightError, name):
                    assert_no_ambient_docker_authority({name: "attacker-controlled"})

    def test_scrubbed_environment_contains_no_docker_or_compose_selector(self) -> None:
        scrubbed = scrub_environment(
            {
                "PATH": "safe-path",
                "SYSTEMROOT": "safe-root",
                "DOCKER_HOST": "tcp://remote:2375",
                "COMPOSE_FILE": "attacker.yaml",
                "UNRELATED_SECRET": "do-not-forward",
            }
        )
        self.assertEqual(scrubbed, {"PATH": "safe-path", "SYSTEMROOT": "safe-root"})

    def test_remote_context_endpoints_are_rejected(self) -> None:
        for endpoint in ("tcp://127.0.0.1:2375", "tcp://remote:2376", "ssh://host", "https://host"):
            with self.subTest(endpoint=endpoint):
                def runner(arguments, *, environment, timeout_seconds, stdin=None):
                    payload = {"Name": "sandbox-local", "Endpoints": {"docker": {"Host": endpoint}}}
                    return completed(list(arguments), json.dumps(payload))

                with self.assertRaisesRegex(PreflightError, "context.endpoint"):
                    validate_local_context(
                        "sandbox-local", runner=runner, environ={}, platform_name="nt"
                    )

    def test_local_context_is_explicit_on_context_inspection(self) -> None:
        calls: list[list[str]] = []

        def runner(arguments, *, environment, timeout_seconds, stdin=None):
            calls.append(list(arguments))
            payload = {
                "Name": "desktop-linux",
                "Endpoints": {"docker": {"Host": "npipe:////./pipe/dockerDesktopLinuxEngine"}},
            }
            return completed(list(arguments), json.dumps(payload))

        identity = validate_local_context(
            "desktop-linux", runner=runner, environ={}, platform_name="nt"
        )
        self.assertEqual(identity.endpoint, "npipe:////./pipe/dockerDesktopLinuxEngine")
        self.assertEqual(
            calls,
            [[
                "docker",
                "--context",
                "desktop-linux",
                "context",
                "inspect",
                "desktop-linux",
                "--format",
                "{{json .}}",
            ]],
        )

    def test_posix_context_requires_local_unix_socket(self) -> None:
        def runner(arguments, *, environment, timeout_seconds, stdin=None):
            payload = {
                "Name": "sandbox-local",
                "Endpoints": {"docker": {"Host": "unix:///var/run/nonexistent-test.sock"}},
            }
            return completed(list(arguments), json.dumps(payload))

        identity = validate_local_context(
            "sandbox-local", runner=runner, environ={}, platform_name="posix"
        )
        self.assertEqual(identity.endpoint, "unix:///var/run/nonexistent-test.sock")

    def test_docker_metadata_calls_always_repeat_explicit_context(self) -> None:
        calls: list[list[str]] = []

        def runner(arguments, *, environment, timeout_seconds, stdin=None):
            arguments = list(arguments)
            calls.append(arguments)
            if arguments[3] == "info":
                return completed(arguments, json.dumps({"OSType": "linux", "ServerVersion": "29"}))
            if arguments[3:5] == ["compose", "version"]:
                return completed(arguments, json.dumps({"version": "5.4.0"}))
            return completed(
                arguments,
                json.dumps(
                    {
                        "Id": "sha256:" + "a" * 64,
                        "Os": "linux",
                        "Architecture": "amd64",
                        "Config": {"Entrypoint": None, "Volumes": None}
                    }
                ),
            )

        docker = DockerCLI("sandbox-local", runner=runner, environ={})
        docker.status()
        docker.inspect_image("sha256:" + "a" * 64)
        self.assertTrue(calls)
        self.assertTrue(all(call[:3] == ["docker", "--context", "sandbox-local"] for call in calls))


class TrustedLayoutTests(unittest.TestCase):
    def test_repository_layout_is_derived_and_reparse_ancestors_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repository = Path(temporary) / "repo"
            sandbox = repository / "graph-sandbox"
            sandbox.mkdir(parents=True)
            (repository / ".git").mkdir()
            (repository / "AGENTS.md").write_text("# test\n", encoding="utf-8")
            script = sandbox / "activate.py"
            for path in (
                script,
                sandbox / "compose.yaml",
                sandbox / "compose.build.yaml",
                sandbox / "images.lock.json",
            ):
                path.write_text("{}\n", encoding="utf-8")
            layout = trusted_layout(script)
            self.assertEqual(layout.repository_root, repository)
            real_check = __import__("preflight")._is_link_or_junction
            with mock.patch(
                "preflight._is_link_or_junction",
                side_effect=lambda path: Path(path) == sandbox or real_check(Path(path)),
            ):
                with self.assertRaisesRegex(PreflightError, "reparse point"):
                    trusted_layout(script)


class ResourceScopeTests(unittest.TestCase):
    def test_run_id_derives_bounded_distinct_project_scope(self) -> None:
        first = project_scope("mission-healthy-001")
        second = project_scope("mission-healthy-002")
        self.assertRegex(first, r"^graph-sandbox-v1-[0-9a-f]{12}$")
        self.assertNotEqual(first, second)

    def test_owned_resource_graph_contains_separate_state_and_evidence_volumes(self) -> None:
        records = expected_resource_records("mission-healthy-001", SOURCE_REVISION)
        volumes = {record.name for record in records if record.kind == "volume"}
        project = project_scope("mission-healthy-001")
        self.assertEqual(
            volumes,
            {
                f"{project}_runner-state",
                f"{project}_runner-evidence",
                f"{project}_checkout-data",
                f"{project}_payments-data",
                f"{project}_inventory-data",
            },
        )

    def test_fresh_rejects_any_exact_name_or_owned_resource(self) -> None:
        record = expected_resource_records("mission-healthy-001", SOURCE_REVISION)[0]
        state = ResourceState((record,))
        with self.assertRaisesRegex(PreflightError, "resources.fresh"):
            validate_resource_mode(
                "fresh", state, run_id="mission-healthy-001", source_revision=SOURCE_REVISION
            )

    def test_resume_requires_the_exact_owned_resource_graph(self) -> None:
        expected = expected_resource_records("mission-healthy-001", SOURCE_REVISION)
        validate_resource_mode(
            "resume",
            ResourceState(expected),
            run_id="mission-healthy-001",
            source_revision=SOURCE_REVISION,
        )

        missing = ResourceState(expected[:-1])
        with self.assertRaisesRegex(PreflightError, "resources.resume"):
            validate_resource_mode(
                "resume", missing, run_id="mission-healthy-001", source_revision=SOURCE_REVISION
            )

        labels = dict(expected[0].labels)
        labels["com.latent-sre.graph-sandbox.source-revision"] = "f" * 40
        collision = ResourceRecord(expected[0].kind, expected[0].name, labels)
        with self.assertRaisesRegex(PreflightError, "resources.resume"):
            validate_resource_mode(
                "resume",
                ResourceState((collision, *expected[1:])),
                run_id="mission-healthy-001",
                source_revision=SOURCE_REVISION,
            )

    def test_claim_phase_accepts_only_safe_partial_resource_graphs(self) -> None:
        expected = expected_resource_records(CASE_ID, SOURCE_REVISION)
        by_key = {(record.kind, record.name): record for record in expected}
        project = project_scope(CASE_ID)
        volumes = tuple(
            by_key[("volume", f"{project}_{name}")]
            for name in (
                "runner-state",
                "runner-evidence",
                "checkout-data",
                "payments-data",
                "inventory-data",
            )
        )
        partial_before_runner = ResourceState(
            (
                by_key[("network", f"{project}_sandbox")],
                by_key[("container", f"{project}-checkout-1")],
                by_key[("volume", f"{project}_checkout-data")],
            )
        )
        facts = validate_resource_mode(
            "resume",
            partial_before_runner,
            run_id=CASE_ID,
            source_revision=SOURCE_REVISION,
            claim_phase="PRESERVED",
            runner_existed=False,
        )
        self.assertFalse(facts.runner_existed)

        runner = by_key[("container", f"{project}-graph-runner-1")]
        facts = validate_resource_mode(
            "resume",
            ResourceState((runner, *volumes)),
            run_id=CASE_ID,
            source_revision=SOURCE_REVISION,
            claim_phase="RUNNING",
            runner_existed=False,
        )
        self.assertTrue(facts.runner_existed)
        with self.assertRaisesRegex(PreflightError, "five durable volumes"):
            validate_resource_mode(
                "resume",
                ResourceState((runner, *volumes[:-1])),
                run_id=CASE_ID,
                source_revision=SOURCE_REVISION,
                claim_phase="PRESERVED",
                runner_existed=False,
            )

        published = validate_resource_mode(
            "resume",
            ResourceState(()),
            run_id=CASE_ID,
            source_revision=SOURCE_REVISION,
            claim_phase="PUBLISHED",
            runner_existed=True,
        )
        self.assertTrue(published.runner_existed)
        bad_labels = dict(partial_before_runner.records[0].labels)
        bad_labels["com.latent-sre.graph-sandbox.source-revision"] = "f" * 40
        poisoned = ResourceRecord(
            partial_before_runner.records[0].kind,
            partial_before_runner.records[0].name,
            bad_labels,
        )
        with self.assertRaisesRegex(PreflightError, "ownership mismatch"):
            validate_resource_mode(
                "resume",
                ResourceState((poisoned,)),
                run_id=CASE_ID,
                source_revision=SOURCE_REVISION,
                claim_phase="PUBLISHED",
                runner_existed=True,
            )


class SnapshotTests(unittest.TestCase):
    def test_build_inputs_force_lf_in_git_attributes(self) -> None:
        repository_root = SANDBOX_ROOT.parent
        expected = {
            "graph-sandbox/runner/Dockerfile": ("set", "lf"),
            "graph-sandbox/runner/requirements.txt": ("set", "lf"),
            "graph-sandbox/services/Dockerfile": ("set", "lf"),
            "graph-sandbox/services/requirements.txt": ("set", "lf"),
            "graph-sandbox/.dockerignore": ("set", "lf"),
        }
        for relative, (text_value, eol_value) in expected.items():
            with self.subTest(relative=relative):
                observed: dict[str, str] = {}
                for attribute in ("text", "eol"):
                    result = run_process(
                        [
                            "git",
                            "-C",
                            str(repository_root),
                            "check-attr",
                            attribute,
                            "--",
                            relative,
                        ],
                        environment=os.environ,
                        timeout_seconds=30,
                    )
                    self.assertEqual(result.returncode, 0)
                    observed[attribute] = result.stdout.strip().rsplit(": ", 1)[-1]
                self.assertEqual(observed, {"text": text_value, "eol": eol_value})

    @staticmethod
    def archive_bytes(name: str, payload: bytes, *, member_type: bytes | None = None) -> bytes:
        stream = BytesIO()
        with tarfile.open(fileobj=stream, mode="w") as archive:
            member = tarfile.TarInfo(name)
            member.size = len(payload)
            if member_type is not None:
                member.type = member_type
            archive.addfile(member, BytesIO(payload))
        return stream.getvalue()

    @staticmethod
    def archive_files(files: dict[str, bytes]) -> bytes:
        stream = BytesIO()
        with tarfile.open(fileobj=stream, mode="w") as archive:
            for name, payload in files.items():
                member = tarfile.TarInfo(name)
                member.size = len(payload)
                archive.addfile(member, BytesIO(payload))
        return stream.getvalue()

    def test_archive_rejects_traversal_and_indirection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary)
            for name, member_type in (
                ("../escape", None),
                ("graph-sandbox/link", tarfile.SYMTYPE),
                ("graph-sandbox/hardlink", tarfile.LNKTYPE),
                ("graph-sandbox/..\\escape", None),
                ("graph-sandbox/CON", None),
            ):
                with self.subTest(name=name):
                    with self.assertRaisesRegex(SnapshotError, "archive"):
                        safe_extract_archive(
                            self.archive_bytes(name, b"unsafe", member_type=member_type), destination
                        )

    def test_builder_rejects_ambient_remote_daemon_before_any_command(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            layout = RepositoryLayout(
                root,
                root,
                root / "compose.yaml",
                root / "compose.build.yaml",
                root / "images.lock.json",
            )
            def runner(*_args, **_kwargs):
                self.fail("runner must not be reached with ambient DOCKER_HOST")
            with self.assertRaisesRegex(PreflightError, "DOCKER_HOST"):
                build_and_lock(
                    layout=layout,
                    source_revision=SOURCE_REVISION,
                    docker_context="sandbox-local",
                    runner=runner,
                    environ={"DOCKER_HOST": "tcp://remote:2375"},
                )

    def test_image_lock_temporary_is_exclusive_and_does_not_follow_precreated_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            lock = Path(temporary) / "images.lock.json"
            lock.write_text('{"template":true}\n', encoding="utf-8")
            attacker_path = Path(temporary) / f".{lock.name}.{'a' * 32}.tmp"
            attacker_path.write_text("attacker-controlled\n", encoding="utf-8")
            with mock.patch("build_images.secrets.token_hex", return_value="a" * 32):
                with self.assertRaisesRegex(SnapshotError, "exclusive temporary"):
                    _atomic_replace_lock(lock, {"lock_version": "test"})
            self.assertEqual(lock.read_text(encoding="utf-8"), '{"template":true}\n')

    def test_builder_uses_snapshot_for_build_and_repeats_explicit_local_context(self) -> None:
        base = (
            b"FROM python:3.12.10-slim-bookworm@"
            b"sha256:97983fa8cc88343512862c62307159a82261c3528dc025f79e5a3f7af43e50b4\n"
        )
        archive = self.archive_files(
            {
                "graph-sandbox/.dockerignore": b"**\n!runner/**\n!services/**\n!cases/**\n",
                "graph-sandbox/compose.build.yaml": (
                    b"activation_guard: graph-sandbox/activate.py/v1\n"
                    b"name: graph-sandbox-build-v1\nservices: {}\n"
                ),
                "graph-sandbox/runner/Dockerfile": base,
                "graph-sandbox/runner/main.py": b"VALUE = 1\n",
                "graph-sandbox/services/Dockerfile": base,
                "graph-sandbox/services/app.py": b"VALUE = 1\n",
                "graph-sandbox/cases/mission.json": b"{}\n",
                "graph-sandbox/tests/contract/test_services_contract.py": b"VALUE = 1\n",
                "graph-sandbox/tests/contract/test_runner_contract.py": b"VALUE = 1\n",
                "graph-sandbox/tests/integration/test_services_integration.py": b"VALUE = 1\n",
                "graph-sandbox/tests/integration/test_runner_integration.py": b"VALUE = 1\n",
                "graph-sandbox/tests/recovery/test_runner_recovery.py": b"VALUE = 1\n",
            }
        )
        calls: list[list[str]] = []

        def runner(arguments, *, environment, timeout_seconds, stdin=None, binary=False):
            arguments = list(arguments)
            calls.append(arguments)
            if arguments[:4] == ["git", "-C", arguments[2], "rev-parse"]:
                return completed(arguments, SOURCE_REVISION)
            if "status" in arguments:
                return completed(arguments, "")
            if "archive" in arguments:
                return subprocess.CompletedProcess(arguments, 0, stdout=archive, stderr=b"")
            if arguments[3:5] == ["context", "inspect"]:
                endpoint = (
                    "npipe:////./pipe/dockerDesktopLinuxEngine"
                    if os.name == "nt"
                    else "unix:///var/run/docker.sock"
                )
                payload = {
                    "Name": "desktop-linux",
                    "Endpoints": {"docker": {"Host": endpoint}},
                }
                return completed(arguments, json.dumps(payload))
            if arguments[3] == "info":
                return completed(
                    arguments, json.dumps({"OSType": "linux", "ServerVersion": "29.7.2"})
                )
            if arguments[3:5] == ["compose", "version"]:
                return completed(arguments, json.dumps({"version": "5.4.0"}))
            if arguments[3:5] == ["compose", "--file"]:
                self.assertIn("snapshot", arguments[5])
                return completed(arguments)
            if arguments[3:5] == ["image", "inspect"]:
                tag = arguments[-1]
                image_hex = "d" * 64 if "graph-runner" in tag else "e" * 64
                return completed(
                    arguments,
                    json.dumps(
                        {
                            "Id": "sha256:" + image_hex,
                            "Os": "linux",
                            "Architecture": "amd64",
                            "Config": {"Entrypoint": None, "Volumes": None},
                        }
                    ),
                )
            self.fail(f"unexpected command: {arguments}")

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            lock = root / "images.lock.json"
            lock.write_text("{}\n", encoding="utf-8")
            layout = RepositoryLayout(
                root,
                root,
                root / "compose.yaml",
                root / "compose.build.yaml",
                lock,
            )
            build_and_lock(
                layout=layout,
                source_revision=SOURCE_REVISION,
                docker_context="desktop-linux",
                runner=runner,
                environ={},
            )
            locked = json.loads(lock.read_text(encoding="utf-8"))
            self.assertRegex(locked["images"]["runner"]["image_id"], r"^sha256:d{64}$")
        docker_calls = [call for call in calls if call and call[0] == "docker"]
        self.assertTrue(docker_calls)
        self.assertTrue(all(call[:3] == ["docker", "--context", "desktop-linux"] for call in docker_calls))

    def test_snapshot_rejects_worktree_mutation_after_archive(self) -> None:
        archive = self.archive_bytes("graph-sandbox/runner/main.py", b"VALUE = 1\n")
        responses = iter(
            (
                completed([], SOURCE_REVISION),
                completed([], ""),
                subprocess.CompletedProcess([], 0, stdout=archive, stderr=b""),
                completed([], SOURCE_REVISION),
                completed([], " M graph-sandbox/runner/main.py"),
            )
        )

        def runner(arguments, *, environment, timeout_seconds, stdin=None, binary=False):
            return next(responses)

        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(SnapshotError, "changed during snapshot"):
                prepare_git_snapshot(
                    Path(temporary), SOURCE_REVISION, Path(temporary) / "snapshot", runner=runner
                )


class ActivationTests(unittest.TestCase):
    def test_reconciliation_timeline_requires_approved_checkout_fixture(self) -> None:
        sandbox_case = type(
            "Case",
            (),
            {
                "service_fixtures": {
                    "checkout": {"effect": "ambiguous_after_commit"}
                }
            },
        )()

        self.assertTrue(_requires_reconciliation_timeline(sandbox_case, "APPROVED"))
        self.assertFalse(_requires_reconciliation_timeline(sandbox_case, "REJECTED"))
        self.assertFalse(_requires_reconciliation_timeline(sandbox_case, "TIMEOUT"))

    def test_reconciliation_pair_rejects_divergent_runtime_histories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            unknown = root / "unknown"
            reconciled = root / "reconciled"
            unknown.mkdir()
            reconciled.mkdir()
            immutable = {
                "run_id": "reconcile-001",
                "case_id": "checkout-ambiguous-after-commit-001",
                "case_digest": "a" * 64,
                "source_revision": "b" * 40,
                "thread_id": "checkout-payments-timeout-drill-v1:reconcile-001",
                "started_at": "2026-08-30T12:00:00.000Z",
            }
            unknown_manifest = {
                **immutable,
                "outcome": "UNKNOWN",
                "ended_at": "2026-08-30T12:00:01.000Z",
            }
            reconciled_manifest = {
                **immutable,
                "outcome": "SUCCEEDED",
                "ended_at": "2026-08-30T12:00:02.000Z",
            }
            event_prefix = {"sequence": 1, "event_type": "effect.unknown"}
            (unknown / "events.jsonl").write_text(
                json.dumps(event_prefix) + "\n" + json.dumps({"sequence": 2, "event_type": "run.terminal"}) + "\n",
                encoding="utf-8",
            )
            (reconciled / "events.jsonl").write_text(
                json.dumps(event_prefix) + "\n" + json.dumps({"sequence": 2, "event_type": "effect.reconciled"}) + "\n" + json.dumps({"sequence": 3, "event_type": "run.terminal"}) + "\n",
                encoding="utf-8",
            )
            unknown_effects = [
                {"sequence": 1, "effect_id": "reconcile-001:effect", "effect_state": "UNKNOWN"}
            ]
            reconciled_effects = [
                *unknown_effects,
                {"sequence": 2, "effect_id": "reconcile-001:effect", "effect_state": "RECONCILED"},
            ]
            (unknown / "effects.jsonl").write_text(
                "".join(json.dumps(record) + "\n" for record in unknown_effects),
                encoding="utf-8",
            )
            (reconciled / "effects.jsonl").write_text(
                "".join(json.dumps(record) + "\n" for record in reconciled_effects),
                encoding="utf-8",
            )

            _validate_reconciliation_pair(
                unknown,
                reconciled,
                unknown_manifest,
                reconciled_manifest,
            )
            divergent = {"sequence": 1, "event_type": "effect.dispatched"}
            (reconciled / "events.jsonl").write_text(
                json.dumps(divergent) + "\n" + json.dumps({"sequence": 2, "event_type": "effect.reconciled"}) + "\n" + json.dumps({"sequence": 3, "event_type": "run.terminal"}) + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ActivationError, "event history"):
                _validate_reconciliation_pair(
                    unknown,
                    reconciled,
                    unknown_manifest,
                    reconciled_manifest,
                )

    @staticmethod
    def host_verification() -> dict[str, object]:
        return {
            "docker_context": "desktop-linux",
            "docker_context_fingerprint": "f" * 64,
            "docker_engine_version": "29.7.2",
            "docker_compose_version": "5.4.0",
            "docker_platform": "linux",
            "project": "graph-sandbox-v1-27c42c93d2da",
            "base_image_digest": "sha256:" + "9" * 64,
            "runner_image_id": "sha256:" + "d" * 64,
            "services_image_id": "sha256:" + "e" * 64,
        }

    @staticmethod
    def command_journal() -> list[dict[str, object]]:
        context = "desktop-linux"
        time_utc = "2026-08-29T12:00:03.000Z"
        return [
            {
                "command_version": "graph-sandbox-command/v1",
                "phase": phase,
                "command": command,
                "time_utc": time_utc,
                "exit_status": 0,
            }
            for phase, command in (
                ("activation", ["python", "graph-sandbox/activate.py", "fresh"]),
                ("preflight", ["docker", "--context", context, "compose", "config"]),
                ("up", ["docker", "--context", context, "compose", "up"]),
                ("export", ["docker", "--context", context, "container", "cp"]),
                ("teardown", ["docker", "--context", context, "compose", "down", "--volumes"]),
            )
        ]

    @staticmethod
    def write_runner_evidence(root: Path, *, outcome: str = "SUCCEEDED") -> Path:
        run_dir = root / "mission-healthy-001"
        (run_dir / "receipts").mkdir(parents=True)
        contract = "checkout-payments-timeout-drill/v1"
        effect_id = "mission-healthy-001:checkout_effect:0:effect-checkout"
        parent_key = hashlib.sha256(f"{contract}\n{effect_id}".encode("ascii")).hexdigest()
        receipts = {}
        checkout_receipt = None
        if outcome == "SUCCEEDED":
            targets = {}
            for effect_class, receipt_id in (
                ("payment", "payment-receipt-001"),
                ("inventory", "inventory-receipt-001"),
            ):
                child_key = hashlib.sha256(
                    f"{contract}\n{parent_key}\n{effect_class}".encode("ascii")
                ).hexdigest()
                targets[effect_class] = {
                    "receipt_version": "synthetic-receipt/v1",
                    "effect_class": effect_class,
                    "receipt_id": receipt_id,
                    "idempotency_key": child_key,
                    "request_digest": ("b" if effect_class == "payment" else "c") * 64,
                    "status": "committed",
                    "replayed": False,
                }
            checkout_receipt = {
                "authoritative_result_id": "result-001",
                "order_id": "synthetic-order-healthy-001",
                "completion_class": "COMPLETE",
                "payment_receipt": targets["payment"],
                "inventory_receipt": targets["inventory"],
                "replayed": False,
            }
            receipts[effect_id] = checkout_receipt
        final_state = {
            "contract_version": contract,
            "state_schema": "graph-state/v2",
            "run_id": "mission-healthy-001",
            "thread_id": "checkout-payments-timeout-drill-v1:mission-healthy-001",
            "source_revision": SOURCE_REVISION,
            "case_id": "mission-healthy-001",
            "case_digest": "74266b9c39a7733128e25f7279bb18820664bfbd6c11d8b0a6a3fa5e53a685d1",
            "replay_number": 0,
            "phase": "TERMINAL",
            "outcome": outcome,
            "checkout": {"order_id": "synthetic-order-healthy-001"},
            "checkout_status": "COMPLETE" if outcome == "SUCCEEDED" else "FAILED",
            "approval": {
                "request_id": "approval-mission-healthy-001",
                "status": "APPROVED",
                "actor_class": "fixture-operator",
                "decision_time": "2026-08-29T12:00:00.500Z",
            },
            "tasks": {
                "mission-healthy-001:readiness:0": {"status": "completed", "attempt": 1},
                "mission-healthy-001:readiness:1": {"status": "completed", "attempt": 1},
                "mission-healthy-001:readiness:2": {"status": "completed", "attempt": 1},
                "mission-healthy-001:checkout_effect:0": {"status": "completed", "attempt": 1},
            },
            "receipts": receipts,
            "pending_effects": [],
            "readiness": {
                service: {"status": "ok", "service": service}
                for service in ("checkout", "payments", "inventory")
            },
            "budgets": {
                "attempts": {"limit": 8, "consumed": 1},
                "wall_time_ms": {"limit": 120000, "consumed": 20},
                "model_calls": {"limit": 1, "consumed": 1},
                "tokens": {"limit": 64, "consumed": 64},
                "spend_micro_usd": {"limit": 0, "consumed": 0},
            },
            "cancellation": {
                "state": "NONE",
                "request_id": None,
                "acknowledgement_ms": None,
            },
            "failure": None if outcome == "SUCCEEDED" else {"error_class": "synthetic_failure"},
        }
        effect_record = {
            "sequence": 0,
            "effect_id": effect_id,
            "task_id": "mission-healthy-001:checkout_effect:0",
            "attempt_id": "mission-healthy-001:checkout_effect:0:attempt-1",
            "replay_id": "mission-healthy-001:replay-0",
            "idempotency_key": parent_key,
            "payload_hash": "d" * 64,
            "target": "checkout",
            "reason_class": None,
            "receipt": None,
        }
        effect_records = []
        for sequence, state in enumerate(
            (
                "PREPARED",
                "DISPATCHED",
                "RECEIPT_RECORDED" if outcome == "SUCCEEDED" else "UNKNOWN",
            ),
            start=1,
        ):
            record = copy.deepcopy(effect_record)
            record.update(
                {
                    "sequence": sequence,
                    "effect_state": state,
                    "time_utc": f"2026-08-29T12:00:01.{sequence:03d}Z",
                    "reason_class": "synthetic_failure" if state == "UNKNOWN" else None,
                    "receipt": checkout_receipt if state == "RECEIPT_RECORDED" else None,
                }
            )
            effect_records.append(record)
        events = []
        thread_id = "checkout-payments-timeout-drill-v1:mission-healthy-001"
        event_specs = [
            ("run.accepted", {"result": "accepted"}, None, None),
            ("run.started", {"result": "started"}, None, None),
            ("edge.fanout_emitted", {"targets": ["checkout", "payments", "inventory"]}, None, None),
            ("task.started", {"status": "started"}, None, None),
            ("task.completed", {"status": "completed"}, None, None),
            ("task.started", {"status": "started"}, None, None),
            ("task.completed", {"status": "completed"}, None, None),
            ("task.started", {"status": "started"}, None, None),
            ("task.completed", {"status": "completed"}, None, None),
            ("edge.join_satisfied", {"branches": ["checkout", "payments", "inventory"]}, None, None),
            ("approval.requested", {"request_id": "approval-mission-healthy-001", "approval_status": "PENDING"}, None, None),
            ("approval.approved", {"request_id": "approval-mission-healthy-001", "approval_status": "APPROVED", "actor_class": "fixture-operator"}, None, None),
            ("checkpoint.write_started", {"operation": "write"}, "checkpoint-001", None),
            ("checkpoint.write_completed", {"operation": "write", "result": "recorded"}, "checkpoint-001", None),
            ("task.started", {"status": "started"}, None, effect_id),
            ("effect.prepared", {"effect_class": "checkout", "effect_state": "PREPARED"}, None, effect_id),
            ("effect.dispatched", {"effect_class": "checkout", "effect_state": "DISPATCHED"}, None, effect_id),
            (
                "effect.receipt_recorded" if outcome == "SUCCEEDED" else "effect.unknown",
                {"effect_class": "checkout", "effect_state": "RECEIPT_RECORDED", "authoritative_result_id": "result-001"}
                if outcome == "SUCCEEDED"
                else {"effect_class": "checkout", "effect_state": "UNKNOWN", "reason_class": "synthetic_failure"},
                None,
                effect_id,
            ),
            (
                "task.completed" if outcome == "SUCCEEDED" else "task.failed",
                {"status": "completed"}
                if outcome == "SUCCEEDED"
                else {"status": "failed", "disposition": "stop"},
                None,
                effect_id,
            ),
            (
                "run.terminal",
                {"result": "terminal", "outcome": outcome, **({"authoritative_result_id": "result-001"} if outcome == "SUCCEEDED" else {})},
                None,
                None,
            ),
        ]
        readiness_task_event = 0
        for sequence, (event_type, data, checkpoint_id, event_effect_id) in enumerate(event_specs, start=1):
            task_id = None
            attempt_id = None
            if event_type in {"task.started", "task.completed"} and event_effect_id is None:
                ordinal = readiness_task_event // 2
                task_id = f"mission-healthy-001:readiness:{ordinal}"
                attempt_id = f"{task_id}:attempt-1"
                readiness_task_event += 1
            elif event_effect_id is not None:
                task_id = "mission-healthy-001:checkout_effect:0"
                attempt_id = f"{task_id}:attempt-1"
            events.append(
                {
                    "event_version": "graph-boundary-event/v2",
                    "event_type": event_type,
                    "event_id": f"mission-healthy-001:{sequence:08d}",
                    "sequence": sequence,
                    "time_utc": f"2026-08-29T12:00:01.{sequence:03d}Z",
                    "contract_version": contract,
                    "sandbox_version": "graph-sandbox/v1",
                    "source_revision": SOURCE_REVISION,
                    "run_id": "mission-healthy-001",
                    "case_id": "mission-healthy-001",
                    "case_digest": CASE_DIGEST,
                    "thread_id": thread_id,
                    "node_id": None,
                    "task_id": task_id,
                    "attempt_id": attempt_id,
                    "replay_id": "mission-healthy-001:replay-0",
                    "checkpoint_id": checkpoint_id,
                    "effect_id": event_effect_id,
                    "failure_plane": None,
                    "error_class": None,
                    "data": data,
                }
            )
        artifacts = {
            "events.jsonl": "".join(json.dumps(event) + "\n" for event in events),
            "effects.jsonl": "".join(json.dumps(record) + "\n" for record in effect_records),
            "final-state.json": json.dumps(final_state) + "\n",
            "checkpoint-lineage.json": json.dumps(
                {
                    "lineage_version": "graph-checkpoint-lineage/v2",
                    "contract_version": contract,
                    "state_schema": "graph-state/v2",
                    "source_revision": SOURCE_REVISION,
                    "thread_id": thread_id,
                    "langgraph_version": "1.0.10",
                    "sqlite_saver_version": "3.1.1",
                    "resume_source_checkpoint_id": None,
                    "checkpoints": [
                        {"checkpoint_id": "checkpoint-001", "operation": "write", "result": "recorded"}
                    ],
                    "saver_checkpoint_ids": ["checkpoint-001"],
                }
            ) + "\n",
            "runtime.json": json.dumps(
                {
                    "runtime_version": "graph-runner-runtime/v1",
                    "python_version": "3.12.10",
                    "packages": {
                        "httpx": "0.28.1",
                        "langgraph": "1.0.10",
                        "langgraph-checkpoint-sqlite": "3.1.1",
                    },
                }
            )
            + "\n",
            "manifest.json": json.dumps(
                {
                    "evidence_version": "graph-evidence/v2",
                    "contract_version": contract,
                    "sandbox_version": "graph-sandbox/v1",
                    "source_revision": SOURCE_REVISION,
                    "run_id": "mission-healthy-001",
                    "case_id": "mission-healthy-001",
                    "case_digest": "74266b9c39a7733128e25f7279bb18820664bfbd6c11d8b0a6a3fa5e53a685d1",
                    "thread_id": "checkout-payments-timeout-drill-v1:mission-healthy-001",
                    "outcome": outcome,
                    "authoritative_result_id": "result-001" if outcome == "SUCCEEDED" else None,
                    "started_at": "2026-08-29T12:00:00.000Z",
                    "ended_at": "2026-08-29T12:00:02.000Z",
                    "artifacts": sorted(
                        [
                            "checkpoint-lineage.json",
                            "effects.jsonl",
                            "events.jsonl",
                            "final-state.json",
                            "runtime.json",
                        ]
                        + (
                            ["receipts/inventory.json", "receipts/payment.json"]
                            if outcome == "SUCCEEDED"
                            else []
                        )
                    ),
                }
            )
            + "\n",
        }
        if outcome == "SUCCEEDED":
            artifacts["receipts/payment.json"] = json.dumps(checkout_receipt["payment_receipt"]) + "\n"
            artifacts["receipts/inventory.json"] = json.dumps(checkout_receipt["inventory_receipt"]) + "\n"
        for relative, content in artifacts.items():
            target = run_dir / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        checksum_lines = []
        for path in sorted(run_dir.rglob("*")):
            if path.is_file():
                relative = path.relative_to(run_dir).as_posix()
                checksum_lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {relative}\n")
        (run_dir / "checksums.sha256").write_text("".join(checksum_lines), encoding="ascii")
        return run_dir

    def write_reconciled_retry_evidence(
        self,
        root: Path,
        *,
        final_reconciliation_attempt: int = 2,
    ) -> Path:
        """Shape runner output for bounded failed lookups followed by success."""

        run_dir = self.write_runner_evidence(root)
        state_path = run_dir / "final-state.json"
        events_path = run_dir / "events.jsonl"
        effects_path = run_dir / "effects.jsonl"
        state = json.loads(state_path.read_text(encoding="utf-8"))
        events = [
            json.loads(line)
            for line in events_path.read_text(encoding="utf-8").splitlines()
        ]
        effects = [
            json.loads(line)
            for line in effects_path.read_text(encoding="utf-8").splitlines()
        ]
        checkout_task_id = "mission-healthy-001:checkout_effect:0"
        reconcile_task_id = "mission-healthy-001:reconcile_if_ambiguous:0"
        effect_id = f"{checkout_task_id}:effect-checkout"
        checkout_receipt = state["receipts"][effect_id]
        state["tasks"][checkout_task_id] = {"status": "failed", "attempt": 1}
        state["tasks"][reconcile_task_id] = {
            "status": "completed",
            "attempt": final_reconciliation_attempt,
        }

        unknown_record = copy.deepcopy(effects[-1])
        unknown_record.update(
            {
                "effect_state": "UNKNOWN",
                "reason_class": "ambiguous_after_commit",
                "receipt": None,
            }
        )
        reconciled_record = copy.deepcopy(unknown_record)
        reconciled_record.update(
            {
                "sequence": 4,
                "effect_state": "RECONCILED",
                "time_utc": "2026-08-29T12:00:01.004Z",
                "reason_class": None,
                "receipt": checkout_receipt,
            }
        )
        effects = [*effects[:2], unknown_record, reconciled_record]

        checkout_started = next(
            event
            for event in events
            if event["event_type"] == "task.started"
            and event["task_id"] == checkout_task_id
        )
        checkout_completed = next(
            event
            for event in events
            if event["event_type"] == "task.completed"
            and event["task_id"] == checkout_task_id
        )
        prepared = next(event for event in events if event["event_type"] == "effect.prepared")
        dispatched = next(
            event for event in events if event["event_type"] == "effect.dispatched"
        )
        receipt_recorded = next(
            event
            for event in events
            if event["event_type"] == "effect.receipt_recorded"
        )
        terminal = copy.deepcopy(events[-1])
        prefix = events[: events.index(checkout_started) + 1]

        effect_unknown = copy.deepcopy(receipt_recorded)
        effect_unknown.update(
            {
                "event_type": "effect.unknown",
                "failure_plane": "checkout",
                "error_class": "ambiguous_after_commit",
                "data": {
                    "effect_class": "checkout",
                    "effect_state": "UNKNOWN",
                    "reason_class": "ambiguous_after_commit",
                },
            }
        )
        checkout_failed = copy.deepcopy(checkout_completed)
        checkout_failed.update(
            {
                "event_type": "task.failed",
                "failure_plane": "checkout",
                "error_class": "ambiguous_after_commit",
                "data": {"status": "failed", "disposition": "reconcile"},
            }
        )
        snapshot_replay_refused = copy.deepcopy(effect_unknown)
        snapshot_replay_refused.update(
            {
                "event_type": "effect.replay_refused",
                "node_id": "checkout_effect",
                "failure_plane": "graph-control",
                "error_class": "automatic_replay_forbidden",
                "data": {
                    "effect_class": "checkout",
                    "effect_state": "UNKNOWN",
                    "reason_class": "reconciliation_snapshot_required",
                },
            }
        )

        def reconciliation_task_event(
            event_type: str,
            attempt: int,
        ) -> dict[str, object]:
            event = copy.deepcopy(
                checkout_started if event_type == "task.started" else checkout_completed
            )
            event.update(
                {
                    "event_type": event_type,
                    "node_id": "reconcile_if_ambiguous",
                    "task_id": reconcile_task_id,
                    "attempt_id": f"{reconcile_task_id}:attempt-{attempt}",
                    "effect_id": effect_id,
                    "failure_plane": "checkout" if event_type == "task.failed" else None,
                    "error_class": "gateway_unavailable"
                    if event_type == "task.failed"
                    else None,
                    "data": (
                        {"status": "failed", "disposition": "stop"}
                        if event_type == "task.failed"
                        else {"status": event_type.removeprefix("task.")}
                    ),
                }
            )
            return event

        retry_replay_refused = copy.deepcopy(effect_unknown)
        retry_replay_refused.update(
            {
                "event_type": "effect.replay_refused",
                "node_id": "reconcile_if_ambiguous",
                "task_id": None,
                "attempt_id": None,
                "failure_plane": "checkout",
                "error_class": "gateway_unavailable",
                "data": {
                    "effect_class": "checkout",
                    "effect_state": "UNKNOWN",
                    "reason_class": "reconciliation_unavailable",
                },
            }
        )
        effect_reconciled = copy.deepcopy(receipt_recorded)
        effect_reconciled.update(
            {
                "event_type": "effect.reconciled",
                "data": {
                    "effect_class": "checkout",
                    "effect_state": "RECONCILED",
                    "authoritative_result_id": checkout_receipt[
                        "authoritative_result_id"
                    ],
                },
            }
        )
        reconciliation_history: list[dict[str, object]] = []
        for attempt in range(1, final_reconciliation_attempt):
            reconciliation_history.extend(
                [
                    reconciliation_task_event("task.started", attempt),
                    copy.deepcopy(retry_replay_refused),
                    reconciliation_task_event("task.failed", attempt),
                ]
            )
        reconciliation_history.extend(
            [
                reconciliation_task_event(
                    "task.started",
                    final_reconciliation_attempt,
                ),
                effect_reconciled,
                reconciliation_task_event(
                    "task.completed",
                    final_reconciliation_attempt,
                ),
            ]
        )
        events = [
            *prefix,
            prepared,
            dispatched,
            effect_unknown,
            checkout_failed,
            snapshot_replay_refused,
            *reconciliation_history,
            terminal,
        ]
        for sequence, event in enumerate(events, start=1):
            event["sequence"] = sequence
            event["event_id"] = f"mission-healthy-001:{sequence:08d}"

        state_path.write_text(json.dumps(state) + "\n", encoding="utf-8")
        events_path.write_text(
            "".join(json.dumps(event) + "\n" for event in events),
            encoding="utf-8",
        )
        effects_path.write_text(
            "".join(json.dumps(record) + "\n" for record in effects),
            encoding="utf-8",
        )
        self._rewrite_checksums(run_dir)
        return run_dir

    def test_reconciled_success_accepts_bounded_failed_lookup_then_success(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence_root = Path(temporary)
            staging = evidence_root / ".mission-healthy-001.export"
            staging.mkdir()
            self.write_reconciled_retry_evidence(staging)

            final = verify_and_publish_evidence(
                staging,
                evidence_root=evidence_root,
                run_id=CASE_ID,
                case_id=CASE_ID,
                case_digest=CASE_DIGEST,
                source_revision=SOURCE_REVISION,
                exit_code=0,
                validated_compose=b"{}\n",
                verification=self.host_verification(),
                commands=self.command_journal(),
                runner_state={"Status": "exited", "ExitCode": 0, "OOMKilled": False},
            )

            state = json.loads(
                (final / "final-state.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                state["tasks"][f"{CASE_ID}:reconcile_if_ambiguous:0"],
                {"status": "completed", "attempt": 2},
            )

    def test_reconciled_success_accepts_recovered_open_reconciliation_attempt(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence_root = Path(temporary)
            staging = evidence_root / ".mission-healthy-001.export"
            staging.mkdir()
            self.write_reconciled_retry_evidence(
                staging,
                final_reconciliation_attempt=1,
            )

            final = verify_and_publish_evidence(
                staging,
                evidence_root=evidence_root,
                run_id=CASE_ID,
                case_id=CASE_ID,
                case_digest=CASE_DIGEST,
                source_revision=SOURCE_REVISION,
                exit_code=0,
                validated_compose=b"{}\n",
                verification=self.host_verification(),
                commands=self.command_journal(),
                runner_state={"Status": "exited", "ExitCode": 0, "OOMKilled": False},
            )

            events = [
                json.loads(line)
                for line in (final / "events.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            reconciliation_task_id = f"{CASE_ID}:reconcile_if_ambiguous:0"
            self.assertEqual(
                [
                    event["event_type"]
                    for event in events
                    if event["task_id"] == reconciliation_task_id
                ],
                ["task.started", "task.completed"],
            )

    def test_reconciled_success_accepts_attempt_limit_and_rejects_attempt_nine(
        self,
    ) -> None:
        for final_attempt, should_publish in ((8, True), (9, False)):
            with self.subTest(final_attempt=final_attempt), tempfile.TemporaryDirectory() as temporary:
                evidence_root = Path(temporary)
                staging = evidence_root / ".mission-healthy-001.export"
                staging.mkdir()
                self.write_reconciled_retry_evidence(
                    staging,
                    final_reconciliation_attempt=final_attempt,
                )

                def publish() -> Path:
                    return verify_and_publish_evidence(
                        staging,
                        evidence_root=evidence_root,
                        run_id=CASE_ID,
                        case_id=CASE_ID,
                        case_digest=CASE_DIGEST,
                        source_revision=SOURCE_REVISION,
                        exit_code=0,
                        validated_compose=b"{}\n",
                        verification=self.host_verification(),
                        commands=self.command_journal(),
                        runner_state={
                            "Status": "exited",
                            "ExitCode": 0,
                            "OOMKilled": False,
                        },
                    )

                if should_publish:
                    final = publish()
                    state = json.loads(
                        (final / "final-state.json").read_text(encoding="utf-8")
                    )
                    self.assertEqual(
                        state["tasks"][f"{CASE_ID}:reconcile_if_ambiguous:0"][
                            "attempt"
                        ],
                        8,
                    )
                else:
                    with self.assertRaisesRegex(ActivationError, "runtime limit"):
                        publish()

    def test_success_oracle_rejects_out_of_contract_task_retries(self) -> None:
        reconciliation_task_id = f"{CASE_ID}:reconcile_if_ambiguous:0"
        checkout_task_id = f"{CASE_ID}:checkout_effect:0"

        def noncontiguous(run_dir: Path) -> None:
            state_path = run_dir / "final-state.json"
            events_path = run_dir / "events.jsonl"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["tasks"][reconciliation_task_id]["attempt"] = 3
            events = [
                json.loads(line)
                for line in events_path.read_text(encoding="utf-8").splitlines()
            ]
            for event in events:
                if event["attempt_id"] == f"{reconciliation_task_id}:attempt-2":
                    event["attempt_id"] = f"{reconciliation_task_id}:attempt-3"
            state_path.write_text(json.dumps(state) + "\n", encoding="utf-8")
            events_path.write_text(
                "".join(json.dumps(event) + "\n" for event in events),
                encoding="utf-8",
            )

        def unrelated_retry(run_dir: Path) -> None:
            events_path = run_dir / "events.jsonl"
            events = [
                json.loads(line)
                for line in events_path.read_text(encoding="utf-8").splitlines()
            ]
            unrelated = copy.deepcopy(
                next(
                    event
                    for event in events
                    if event["task_id"] == reconciliation_task_id
                    and event["event_type"] == "task.started"
                )
            )
            unrelated_task_id = f"{CASE_ID}:unrelated:0"
            unrelated.update(
                {
                    "task_id": unrelated_task_id,
                    "attempt_id": f"{unrelated_task_id}:attempt-2",
                }
            )
            events.insert(-1, unrelated)
            for sequence, event in enumerate(events, start=1):
                event["sequence"] = sequence
                event["event_id"] = f"{CASE_ID}:{sequence:08d}"
            events_path.write_text(
                "".join(json.dumps(event) + "\n" for event in events),
                encoding="utf-8",
            )

        def retried_checkout_dispatch(run_dir: Path) -> None:
            state_path = run_dir / "final-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["tasks"][checkout_task_id]["attempt"] = 2
            state_path.write_text(json.dumps(state) + "\n", encoding="utf-8")

        def retried_effect_ledger(run_dir: Path) -> None:
            effects_path = run_dir / "effects.jsonl"
            effects = [
                json.loads(line)
                for line in effects_path.read_text(encoding="utf-8").splitlines()
            ]
            effects[0]["attempt_id"] = f"{checkout_task_id}:attempt-2"
            effects_path.write_text(
                "".join(json.dumps(record) + "\n" for record in effects),
                encoding="utf-8",
            )

        def consumed_reconciliation_attempt(run_dir: Path) -> None:
            state_path = run_dir / "final-state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["budgets"]["attempts"]["consumed"] = 2
            state_path.write_text(json.dumps(state) + "\n", encoding="utf-8")

        def invented_recovery_ordinal(run_dir: Path) -> None:
            events_path = run_dir / "events.jsonl"
            events = [
                json.loads(line)
                for line in events_path.read_text(encoding="utf-8").splitlines()
            ]
            reconciled = next(
                event for event in events if event["event_type"] == "effect.reconciled"
            )
            started_first = next(
                event
                for event in events
                if event["event_type"] == "task.started"
                and event["attempt_id"] == f"{reconciliation_task_id}:attempt-1"
            )
            events = [
                event
                for event in events
                if event is not reconciled
                and not (
                    event["event_type"] == "task.failed"
                    and event["attempt_id"]
                    == f"{reconciliation_task_id}:attempt-1"
                )
                and not (
                    event["event_type"] == "effect.replay_refused"
                    and event["node_id"] == "reconcile_if_ambiguous"
                )
            ]
            events.insert(events.index(started_first) + 1, reconciled)
            for sequence, event in enumerate(events, start=1):
                event["sequence"] = sequence
                event["event_id"] = f"{CASE_ID}:{sequence:08d}"
            events_path.write_text(
                "".join(json.dumps(event) + "\n" for event in events),
                encoding="utf-8",
            )

        def duplicate_reconciliation_completion(run_dir: Path) -> None:
            events_path = run_dir / "events.jsonl"
            events = [
                json.loads(line)
                for line in events_path.read_text(encoding="utf-8").splitlines()
            ]
            first_result = next(
                event
                for event in events
                if event["event_type"] == "task.failed"
                and event["attempt_id"] == f"{reconciliation_task_id}:attempt-1"
            )
            first_result.update(
                {
                    "event_type": "task.completed",
                    "failure_plane": None,
                    "error_class": None,
                    "data": {"status": "completed"},
                }
            )
            events_path.write_text(
                "".join(json.dumps(event) + "\n" for event in events),
                encoding="utf-8",
            )

        def omitted_retry_refusal(run_dir: Path) -> None:
            events_path = run_dir / "events.jsonl"
            events = [
                json.loads(line)
                for line in events_path.read_text(encoding="utf-8").splitlines()
            ]
            events = [
                event
                for event in events
                if not (
                    event["event_type"] == "effect.replay_refused"
                    and event["node_id"] == "reconcile_if_ambiguous"
                )
            ]
            for sequence, event in enumerate(events, start=1):
                event["sequence"] = sequence
                event["event_id"] = f"{CASE_ID}:{sequence:08d}"
            events_path.write_text(
                "".join(json.dumps(event) + "\n" for event in events),
                encoding="utf-8",
            )

        def duplicated_retry_refusal(run_dir: Path) -> None:
            events_path = run_dir / "events.jsonl"
            events = [
                json.loads(line)
                for line in events_path.read_text(encoding="utf-8").splitlines()
            ]
            refusal = next(
                event
                for event in events
                if event["event_type"] == "effect.replay_refused"
                and event["node_id"] == "reconcile_if_ambiguous"
            )
            events.insert(events.index(refusal) + 1, copy.deepcopy(refusal))
            for sequence, event in enumerate(events, start=1):
                event["sequence"] = sequence
                event["event_id"] = f"{CASE_ID}:{sequence:08d}"
            events_path.write_text(
                "".join(json.dumps(event) + "\n" for event in events),
                encoding="utf-8",
            )

        def out_of_order_retry_refusal(run_dir: Path) -> None:
            events_path = run_dir / "events.jsonl"
            events = [
                json.loads(line)
                for line in events_path.read_text(encoding="utf-8").splitlines()
            ]
            refusal = next(
                event
                for event in events
                if event["event_type"] == "effect.replay_refused"
                and event["node_id"] == "reconcile_if_ambiguous"
            )
            started = next(
                event
                for event in events
                if event["event_type"] == "task.started"
                and event["attempt_id"] == f"{reconciliation_task_id}:attempt-1"
            )
            events.remove(refusal)
            events.insert(events.index(started), refusal)
            for sequence, event in enumerate(events, start=1):
                event["sequence"] = sequence
                event["event_id"] = f"{CASE_ID}:{sequence:08d}"
            events_path.write_text(
                "".join(json.dumps(event) + "\n" for event in events),
                encoding="utf-8",
            )

        def mismatched_retry_refusal(run_dir: Path) -> None:
            events_path = run_dir / "events.jsonl"
            events = [
                json.loads(line)
                for line in events_path.read_text(encoding="utf-8").splitlines()
            ]
            refusal = next(
                event
                for event in events
                if event["event_type"] == "effect.replay_refused"
                and event["node_id"] == "reconcile_if_ambiguous"
            )
            refusal["error_class"] = "different_gateway_failure"
            events_path.write_text(
                "".join(json.dumps(event) + "\n" for event in events),
                encoding="utf-8",
            )

        def checkout_failure_before_unknown(run_dir: Path) -> None:
            events_path = run_dir / "events.jsonl"
            events = [
                json.loads(line)
                for line in events_path.read_text(encoding="utf-8").splitlines()
            ]
            unknown = next(
                event for event in events if event["event_type"] == "effect.unknown"
            )
            checkout_failed = next(
                event
                for event in events
                if event["event_type"] == "task.failed"
                and event["task_id"] == checkout_task_id
            )
            events.remove(checkout_failed)
            events.insert(events.index(unknown), checkout_failed)
            for sequence, event in enumerate(events, start=1):
                event["sequence"] = sequence
                event["event_id"] = f"{CASE_ID}:{sequence:08d}"
            events_path.write_text(
                "".join(json.dumps(event) + "\n" for event in events),
                encoding="utf-8",
            )

        def snapshot_refusal_before_checkout_failure(run_dir: Path) -> None:
            events_path = run_dir / "events.jsonl"
            events = [
                json.loads(line)
                for line in events_path.read_text(encoding="utf-8").splitlines()
            ]
            snapshot_refusal = next(
                event
                for event in events
                if event["event_type"] == "effect.replay_refused"
                and event["data"].get("reason_class")
                == "reconciliation_snapshot_required"
            )
            checkout_failed = next(
                event
                for event in events
                if event["event_type"] == "task.failed"
                and event["task_id"] == checkout_task_id
            )
            events.remove(snapshot_refusal)
            events.insert(events.index(checkout_failed), snapshot_refusal)
            for sequence, event in enumerate(events, start=1):
                event["sequence"] = sequence
                event["event_id"] = f"{CASE_ID}:{sequence:08d}"
            events_path.write_text(
                "".join(json.dumps(event) + "\n" for event in events),
                encoding="utf-8",
            )

        def reconciliation_before_snapshot_refusal(run_dir: Path) -> None:
            events_path = run_dir / "events.jsonl"
            events = [
                json.loads(line)
                for line in events_path.read_text(encoding="utf-8").splitlines()
            ]
            snapshot_refusal = next(
                event
                for event in events
                if event["event_type"] == "effect.replay_refused"
                and event["data"].get("reason_class")
                == "reconciliation_snapshot_required"
            )
            started = next(
                event
                for event in events
                if event["event_type"] == "task.started"
                and event["attempt_id"] == f"{reconciliation_task_id}:attempt-1"
            )
            events.remove(started)
            events.insert(events.index(snapshot_refusal), started)
            for sequence, event in enumerate(events, start=1):
                event["sequence"] = sequence
                event["event_id"] = f"{CASE_ID}:{sequence:08d}"
            events_path.write_text(
                "".join(json.dumps(event) + "\n" for event in events),
                encoding="utf-8",
            )

        cases = (
            (noncontiguous, "bounded and contiguous"),
            (unrelated_retry, "unrelated task event"),
            (retried_checkout_dispatch, "retried unexpectedly"),
            (retried_effect_ledger, "effect ledger identity"),
            (consumed_reconciliation_attempt, "healthy fixture consumption"),
            (invented_recovery_ordinal, "attempt sequence"),
            (duplicate_reconciliation_completion, "attempt sequence"),
            (omitted_retry_refusal, "retry refusal"),
            (duplicated_retry_refusal, "retry refusal"),
            (out_of_order_retry_refusal, "retry refusal"),
            (mismatched_retry_refusal, "retry refusal"),
            (checkout_failure_before_unknown, "entry sequence"),
            (snapshot_refusal_before_checkout_failure, "entry sequence"),
            (reconciliation_before_snapshot_refusal, "entry sequence"),
        )
        for mutate, message in cases:
            with self.subTest(mutate=mutate.__name__), tempfile.TemporaryDirectory() as temporary:
                evidence_root = Path(temporary)
                staging = evidence_root / ".mission-healthy-001.export"
                staging.mkdir()
                run_dir = self.write_reconciled_retry_evidence(staging)
                mutate(run_dir)
                self._rewrite_checksums(run_dir)

                with self.assertRaisesRegex(ActivationError, message):
                    verify_and_publish_evidence(
                        staging,
                        evidence_root=evidence_root,
                        run_id=CASE_ID,
                        case_id=CASE_ID,
                        case_digest=CASE_DIGEST,
                        source_revision=SOURCE_REVISION,
                        exit_code=0,
                        validated_compose=b"{}\n",
                        verification=self.host_verification(),
                        commands=self.command_journal(),
                        runner_state={
                            "Status": "exited",
                            "ExitCode": 0,
                            "OOMKilled": False,
                        },
                    )

    def test_host_verifies_adds_metadata_rechecksums_and_atomically_publishes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence_root = Path(temporary)
            staging = evidence_root / ".mission-healthy-001.export"
            staging.mkdir()
            self.write_runner_evidence(staging)
            final = verify_and_publish_evidence(
                staging,
                evidence_root=evidence_root,
                run_id="mission-healthy-001",
                source_revision=SOURCE_REVISION,
                exit_code=0,
                validated_compose=b'{"name":"validated"}\n',
                verification=self.host_verification(),
                commands=self.command_journal(),
            )
            self.assertEqual(final, evidence_root / "mission-healthy-001")
            self.assertTrue((final / "verification.json").is_file())
            self.assertTrue((final / "compose-config.json").is_file())
            checksums = (final / "checksums.sha256").read_text(encoding="ascii")
            self.assertIn("verification.json", checksums)
            self.assertIn("compose-config.json", checksums)
            command_records = [
                json.loads(line)
                for line in (final / "commands.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(
                [record["phase"] for record in command_records],
                ["activation", "preflight", "up", "export", "teardown"],
            )
            for record in command_records:
                self.assertEqual(
                    set(record),
                    {"command_version", "phase", "command", "time_utc", "exit_status"},
                )
                self.assertRegex(record["time_utc"], r"^\d{4}-\d{2}-\d{2}T.*Z$")
                self.assertIsInstance(record["exit_status"], int)
            self.assertNotIn(str(staging), json.dumps(command_records))
            environment = json.loads(
                (final / "environment.json").read_text(encoding="utf-8")
            )
            self.assertEqual(environment["python_runtime_posture"], "observed:3.12.10")
            self.assertEqual(
                environment["package_posture"],
                {
                    "httpx": "observed:0.28.1",
                    "langgraph": "observed:1.0.10",
                    "langgraph-checkpoint-sqlite": "observed:3.1.1",
                },
            )
            self.assertFalse(staging.exists())

    def test_command_journal_rejects_raw_path_arguments(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ActivationError, "command record schema"):
                _command_payload(
                    [
                        {
                            "command_version": "graph-sandbox-command/v1",
                            "phase": "export",
                            "command": [
                                "docker",
                                "--context",
                                "desktop-linux",
                                "container",
                                "cp",
                                str(Path(temporary)),
                            ],
                            "time_utc": "2026-08-29T12:00:00.000Z",
                            "exit_status": 0,
                        }
                    ]
                )

    def test_runtime_evidence_must_match_checkpoint_package_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence_root = Path(temporary)
            staging = evidence_root / ".mission-healthy-001.export"
            staging.mkdir()
            run_dir = self.write_runner_evidence(staging)
            runtime_path = run_dir / "runtime.json"
            runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
            runtime["packages"]["langgraph"] = "1.0.9"
            runtime_path.write_text(json.dumps(runtime) + "\n", encoding="utf-8")
            self._rewrite_checksums(run_dir)

            with self.assertRaisesRegex(ActivationError, "runtime.*langgraph"):
                verify_and_publish_evidence(
                    staging,
                    evidence_root=evidence_root,
                    run_id="mission-healthy-001",
                    case_id="mission-healthy-001",
                    case_digest="74266b9c39a7733128e25f7279bb18820664bfbd6c11d8b0a6a3fa5e53a685d1",
                    source_revision=SOURCE_REVISION,
                    exit_code=0,
                    validated_compose=b"{}\n",
                    verification=self.host_verification(),
                    runner_state={"Status": "exited", "ExitCode": 0, "OOMKilled": False},
                )

    def test_event_and_checkpoint_oracles_reject_closed_contract_drift(self) -> None:
        def renumber(events: list[dict[str, object]]) -> None:
            for sequence, event in enumerate(events, start=1):
                event["sequence"] = sequence
                event["event_id"] = f"mission-healthy-001:{sequence:08d}"

        def unknown_type(events, lineage):
            events[0]["event_type"] = "run.unreviewed"

        def extra_data(events, lineage):
            events[0]["data"]["extra"] = "rejected"

        def sequence_gap(events, lineage):
            events[1]["sequence"] = 9

        def changed_lineage(events, lineage):
            events[2]["case_id"] = "payments-latency-001"

        def duplicate_terminal(events, lineage):
            events.append(copy.deepcopy(events[-1]))
            renumber(events)

        def nonfinal_terminal(events, lineage):
            events.append(copy.deepcopy(events[1]))
            renumber(events)

        def effect_before_approval(events, lineage):
            index = next(
                index
                for index, event in enumerate(events)
                if str(event["event_type"]).startswith("effect.")
            )
            effect = events.pop(index)
            events.insert(2, effect)
            renumber(events)

        def effect_before_readiness_join(events, lineage):
            join_index = next(
                index
                for index, event in enumerate(events)
                if event["event_type"] == "edge.join_satisfied"
            )
            join = events.pop(join_index)
            effect_index = next(
                index
                for index, event in enumerate(events)
                if str(event["event_type"]).startswith("effect.")
            )
            events.insert(effect_index + 1, join)
            renumber(events)

        def unpaired_write(events, lineage):
            events[:] = [event for event in events if event["event_type"] != "checkpoint.write_completed"]
            renumber(events)

        def missing_write_pair(events, lineage):
            events[:] = [
                event
                for event in events
                if event["event_type"]
                not in {"checkpoint.write_started", "checkpoint.write_completed"}
            ]
            renumber(events)

        def missing_lineage_record(events, lineage):
            lineage["checkpoints"] = []

        def failed_write_present_in_saver(events, lineage):
            completed = next(
                event
                for event in events
                if event["event_type"] == "checkpoint.write_completed"
            )
            completed.update(
                {
                    "event_type": "checkpoint.write_failed",
                    "data": {"operation": "write", "result": "failed"},
                    "failure_plane": "checkpoint-store",
                    "error_class": "checkpoint-write-failed",
                }
            )

        def wrong_resume(events, lineage):
            lineage["resume_source_checkpoint_id"] = "checkpoint-missing"

        def resume_without_descendant(events, lineage):
            started = copy.deepcopy(
                next(
                    event
                    for event in events
                    if event["event_type"] == "checkpoint.write_started"
                )
            )
            started.update(
                {
                    "event_type": "checkpoint.resume_started",
                    "checkpoint_id": "checkpoint-001",
                    "task_id": None,
                    "attempt_id": None,
                    "data": {"operation": "resume"},
                }
            )
            completed = copy.deepcopy(
                next(
                    event
                    for event in events
                    if event["event_type"] == "checkpoint.write_completed"
                )
            )
            completed.update(
                {
                    "event_type": "checkpoint.resume_completed",
                    "checkpoint_id": "checkpoint-001",
                    "task_id": None,
                    "attempt_id": None,
                    "data": {"operation": "resume", "result": "completed"},
                }
            )
            events[-1:-1] = [started, completed]
            renumber(events)
            lineage["resume_source_checkpoint_id"] = "checkpoint-001"

        def absent_from_saver(events, lineage):
            lineage["saver_checkpoint_ids"] = ["another-checkpoint"]

        mutations = (
            (unknown_type, "unknown boundary event"),
            (extra_data, "event data schema"),
            (sequence_gap, "sequence or lineage"),
            (changed_lineage, "sequence or lineage"),
            (duplicate_terminal, "one final run terminal"),
            (nonfinal_terminal, "one final run terminal"),
            (effect_before_approval, "before approval"),
            (effect_before_readiness_join, "before readiness join"),
            (unpaired_write, "unpaired checkpoint write"),
            (missing_write_pair, "checkpoint write events do not equal saver IDs"),
            (missing_lineage_record, "checkpoint lineage mismatch|lineage does not equal saver IDs"),
            (failed_write_present_in_saver, "checkpoint write events do not equal saver IDs"),
            (wrong_resume, "wrong checkpoint resume source"),
            (resume_without_descendant, "wrong checkpoint resume source"),
            (absent_from_saver, "absent from saver"),
        )
        for mutate, diagnostic in mutations:
            with self.subTest(mutation=mutate.__name__), tempfile.TemporaryDirectory() as temporary:
                evidence_root = Path(temporary)
                staging = evidence_root / ".mission-healthy-001.export"
                staging.mkdir()
                run_dir = self.write_runner_evidence(staging)
                events_path = run_dir / "events.jsonl"
                lineage_path = run_dir / "checkpoint-lineage.json"
                events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
                lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
                mutate(events, lineage)
                events_path.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
                lineage_path.write_text(json.dumps(lineage) + "\n", encoding="utf-8")
                self._rewrite_checksums(run_dir)
                with self.assertRaisesRegex(ActivationError, diagnostic):
                    verify_and_publish_evidence(
                        staging,
                        evidence_root=evidence_root,
                        run_id=CASE_ID,
                        case_id=CASE_ID,
                        case_digest=CASE_DIGEST,
                        source_revision=SOURCE_REVISION,
                        exit_code=0,
                        validated_compose=b"{}\n",
                        verification=self.host_verification(),
                        runner_state={"Status": "exited", "ExitCode": 0, "OOMKilled": False},
                    )

    def test_checkpoint_oracle_accepts_failed_resume_followed_by_recorded_descendant(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence_root = Path(temporary)
            staging = evidence_root / ".mission-healthy-001.export"
            staging.mkdir()
            run_dir = self.write_runner_evidence(staging)
            events_path = run_dir / "events.jsonl"
            lineage_path = run_dir / "checkpoint-lineage.json"
            events = [
                json.loads(line)
                for line in events_path.read_text(encoding="utf-8").splitlines()
            ]
            template = next(
                event
                for event in events
                if event["event_type"] == "checkpoint.write_started"
            )
            additions = []
            for event_type, checkpoint_id, data in (
                ("checkpoint.resume_started", "checkpoint-001", {"operation": "resume"}),
                (
                    "checkpoint.resume_failed",
                    "checkpoint-001",
                    {"operation": "resume", "result": "failed"},
                ),
                ("checkpoint.resume_started", "checkpoint-001", {"operation": "resume"}),
                ("checkpoint.write_started", "checkpoint-002", {"operation": "write"}),
                (
                    "checkpoint.write_completed",
                    "checkpoint-002",
                    {"operation": "write", "result": "recorded"},
                ),
                (
                    "checkpoint.resume_completed",
                    "checkpoint-002",
                    {"operation": "resume", "result": "completed"},
                ),
            ):
                event = copy.deepcopy(template)
                event.update(
                    {
                        "event_type": event_type,
                        "checkpoint_id": checkpoint_id,
                        "task_id": None,
                        "attempt_id": None,
                        "data": data,
                    }
                )
                additions.append(event)
            insert_at = next(
                index
                for index, event in enumerate(events)
                if str(event["event_type"]).startswith("effect.")
            )
            events[insert_at:insert_at] = additions
            for sequence, event in enumerate(events, start=1):
                event["sequence"] = sequence
                event["event_id"] = f"mission-healthy-001:{sequence:08d}"
            lineage = json.loads(lineage_path.read_text(encoding="utf-8"))
            lineage["resume_source_checkpoint_id"] = "checkpoint-001"
            lineage["checkpoints"].append(
                {"checkpoint_id": "checkpoint-002", "operation": "write", "result": "recorded"}
            )
            lineage["saver_checkpoint_ids"].append("checkpoint-002")
            events_path.write_text(
                "".join(json.dumps(event) + "\n" for event in events),
                encoding="utf-8",
            )
            lineage_path.write_text(json.dumps(lineage) + "\n", encoding="utf-8")
            self._rewrite_checksums(run_dir)

            final = verify_and_publish_evidence(
                staging,
                evidence_root=evidence_root,
                run_id=CASE_ID,
                case_id=CASE_ID,
                case_digest=CASE_DIGEST,
                source_revision=SOURCE_REVISION,
                exit_code=0,
                validated_compose=b"{}\n",
                verification=self.host_verification(),
                commands=self.command_journal(),
                runner_state={"Status": "exited", "ExitCode": 0, "OOMKilled": False},
            )

            self.assertTrue((final / "checkpoint-lineage.json").is_file())

    def test_effect_ledger_oracle_rejects_incomplete_or_changed_transition_chain(self) -> None:
        def missing_prepared(records):
            records.pop(0)
            for sequence, record in enumerate(records, start=1):
                record["sequence"] = sequence

        def missing_dispatched(records):
            records.pop(1)
            for sequence, record in enumerate(records, start=1):
                record["sequence"] = sequence

        def sequence_gap(records):
            records[-1]["sequence"] = 9

        def changed_payload(records):
            records[-1]["payload_hash"] = "e" * 64

        for mutate in (
            missing_prepared,
            missing_dispatched,
            sequence_gap,
            changed_payload,
        ):
            with self.subTest(mutation=mutate.__name__), tempfile.TemporaryDirectory() as temporary:
                evidence_root = Path(temporary)
                staging = evidence_root / ".mission-healthy-001.export"
                staging.mkdir()
                run_dir = self.write_runner_evidence(staging)
                effects_path = run_dir / "effects.jsonl"
                effects = [
                    json.loads(line)
                    for line in effects_path.read_text(encoding="utf-8").splitlines()
                ]
                mutate(effects)
                effects_path.write_text(
                    "".join(json.dumps(record) + "\n" for record in effects),
                    encoding="utf-8",
                )
                self._rewrite_checksums(run_dir)

                with self.assertRaisesRegex(ActivationError, "effect ledger|payload identity"):
                    verify_and_publish_evidence(
                        staging,
                        evidence_root=evidence_root,
                        run_id=CASE_ID,
                        case_id=CASE_ID,
                        case_digest=CASE_DIGEST,
                        source_revision=SOURCE_REVISION,
                        exit_code=0,
                        validated_compose=b"{}\n",
                        verification=self.host_verification(),
                        runner_state={"Status": "exited", "ExitCode": 0, "OOMKilled": False},
                    )

    def test_completed_effect_with_wall_budget_failure_publishes_truthful_receipts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence_root = Path(temporary)
            staging = evidence_root / ".mission-healthy-001.export"
            staging.mkdir()
            run_dir = self.write_runner_evidence(staging)
            state_path = run_dir / "final-state.json"
            manifest_path = run_dir / "manifest.json"
            events_path = run_dir / "events.jsonl"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state.update(
                {
                    "outcome": "FAILED",
                    "checkout_status": "COMPLETE",
                    "failure": {
                        "plane": "graph-control",
                        "error_class": "budget_exhausted",
                        "retryable": False,
                        "disposition": "effect-completed-budget-exceeded",
                    },
                }
            )
            state["budgets"]["wall_time_ms"]["consumed"] = 120000
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["outcome"] = "FAILED"
            events = [
                json.loads(line)
                for line in events_path.read_text(encoding="utf-8").splitlines()
            ]
            budget = copy.deepcopy(events[-2])
            budget.update(
                {
                    "event_type": "budget.exhausted",
                    "effect_id": None,
                    "task_id": None,
                    "attempt_id": None,
                    "failure_plane": None,
                    "error_class": None,
                    "data": {
                        "kind": "wall_time_ms",
                        "limit": 120000,
                        "consumed": 120000,
                        "remaining": 0,
                    },
                }
            )
            events.insert(-1, budget)
            events[-1]["data"] = {"result": "terminal", "outcome": "FAILED"}
            for sequence, event in enumerate(events, start=1):
                event["sequence"] = sequence
                event["event_id"] = f"mission-healthy-001:{sequence:08d}"
            state_path.write_text(json.dumps(state) + "\n", encoding="utf-8")
            manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
            events_path.write_text(
                "".join(json.dumps(event) + "\n" for event in events),
                encoding="utf-8",
            )
            self._rewrite_checksums(run_dir)

            final = verify_and_publish_evidence(
                staging,
                evidence_root=evidence_root,
                run_id=CASE_ID,
                case_id=CASE_ID,
                case_digest=CASE_DIGEST,
                source_revision=SOURCE_REVISION,
                exit_code=2,
                validated_compose=b"{}\n",
                verification=self.host_verification(),
                commands=self.command_journal(),
                runner_state={"Status": "exited", "ExitCode": 2, "OOMKilled": False},
            )

            self.assertEqual(
                json.loads((final / "manifest.json").read_text(encoding="utf-8"))["outcome"],
                "FAILED",
            )
            self.assertTrue((final / "receipts/payment.json").is_file())

    def test_no_effect_terminal_branches_publish_only_not_started_and_empty_ledger(self) -> None:
        branches = (
            ("approval_rejected", "REJECTED"),
            ("approval_timed_out", "REJECTED"),
            ("readiness_failed", "FAILED"),
            ("cancelled", "CANCELLED"),
            ("budget_exhausted", "FAILED"),
        )
        for branch, outcome in branches:
            with self.subTest(branch=branch), tempfile.TemporaryDirectory() as temporary:
                evidence_root = Path(temporary)
                staging = evidence_root / ".mission-healthy-001.export"
                staging.mkdir()
                run_dir = self.write_runner_evidence(staging)
                state_path = run_dir / "final-state.json"
                manifest_path = run_dir / "manifest.json"
                events_path = run_dir / "events.jsonl"
                state = json.loads(state_path.read_text(encoding="utf-8"))
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                original_events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
                state.update(
                    {
                        "outcome": outcome,
                        "checkout_status": "NOT_STARTED",
                        "tasks": {},
                        "receipts": {},
                        "pending_effects": [],
                        "failure": None,
                    }
                )
                event_type = "run.terminal"
                checkpoint_events = [
                    copy.deepcopy(event)
                    for event in original_events
                    if event["event_type"]
                    in {"checkpoint.write_started", "checkpoint.write_completed"}
                ]
                healthy_path = [
                    copy.deepcopy(event)
                    for event in original_events
                    if event["event_type"]
                    in {
                        "edge.fanout_emitted",
                        "task.started",
                        "task.completed",
                        "edge.join_satisfied",
                    }
                    and (
                        event["task_id"] is None
                        or ":readiness:" in str(event["task_id"])
                    )
                ]
                readiness_tasks = {
                    task_id: copy.deepcopy(task)
                    for task_id, task in state["tasks"].items()
                    if ":readiness:" in task_id
                }
                approval_request = copy.deepcopy(
                    next(
                        event
                        for event in original_events
                        if event["event_type"] == "approval.requested"
                    )
                )
                decision = copy.deepcopy(
                    next(
                        event
                        for event in original_events
                        if event["event_type"] == "approval.approved"
                    )
                )
                if branch == "approval_rejected":
                    state["tasks"] = readiness_tasks
                    decision.update({"event_type": "approval.rejected", "data": {"request_id": "approval-mission-healthy-001", "approval_status": "REJECTED", "actor_class": "fixture-operator"}})
                    state["approval"].update({"status": "REJECTED", "decision_time": decision["time_utc"]})
                    branch_events = [*healthy_path, approval_request, decision]
                elif branch == "approval_timed_out":
                    state["tasks"] = readiness_tasks
                    decision.update({"event_type": "approval.timed_out", "data": {"request_id": "approval-mission-healthy-001", "approval_status": "TIMED_OUT"}})
                    state["approval"].update({"status": "TIMED_OUT", "actor_class": "fixture-operator", "decision_time": decision["time_utc"]})
                    branch_events = [*healthy_path, approval_request, decision]
                elif branch == "readiness_failed":
                    state["approval"].update({"status": "PENDING", "decision_time": None})
                    state["readiness"]["checkout"] = {"status": "failed", "service": "checkout", "error_class": "health_http_failure"}
                    state["failure"] = {"plane": "application", "error_class": "readiness_failed", "retryable": False, "disposition": "not-started"}
                    state["tasks"] = readiness_tasks
                    state["tasks"]["mission-healthy-001:readiness:0"] = {"status": "failed", "attempt": 1}
                    failed_path = copy.deepcopy(healthy_path)
                    failed_result = next(
                        event
                        for event in failed_path
                        if event["event_type"] == "task.completed"
                        and event["task_id"] == "mission-healthy-001:readiness:0"
                    )
                    failed_result.update({"event_type": "task.failed", "failure_plane": "checkout", "error_class": "health_http_failure", "data": {"status": "failed", "disposition": "stop"}})
                    join = next(event for event in failed_path if event["event_type"] == "edge.join_satisfied")
                    join.update({"event_type": "edge.join_starved", "failure_plane": "checkout", "error_class": "readiness_join_incomplete", "data": {"missing_branches": ["checkout"]}})
                    branch_events = failed_path
                elif branch == "cancelled":
                    state["cancellation"] = {"state": "ACKNOWLEDGED", "request_id": "cancel-001", "acknowledgement_ms": 10}
                    state["readiness"] = {}
                    state["tasks"] = {}
                    state["approval"].update({"status": "PENDING", "decision_time": None})
                    branch_events = []
                    for cancellation_type, data in (
                        ("cancellation.requested", {"state": "REQUESTED", "request_id": "cancel-001"}),
                        ("cancellation.propagated", {"state": "PROPAGATED", "request_id": "cancel-001"}),
                        ("cancellation.acknowledged", {"state": "ACKNOWLEDGED", "request_id": "cancel-001", "acknowledgement_ms": 10}),
                    ):
                        event = copy.deepcopy(original_events[0])
                        event.update({"event_type": cancellation_type, "node_id": "admit_run", "data": data})
                        branch_events.append(event)
                    event_type = "run.cancelled"
                else:
                    state["approval"].update({"status": "PENDING", "decision_time": None})
                    state["tasks"] = readiness_tasks
                    state["budgets"]["model_calls"] = {"limit": 0, "consumed": 0}
                    state["failure"] = {"plane": "graph-control", "error_class": "budget_exhausted", "retryable": False, "disposition": "not-started"}
                    budget = copy.deepcopy(original_events[0])
                    budget.update({"event_type": "budget.exhausted", "node_id": "fixture_plan", "failure_plane": "model-fixture", "error_class": "budget_exhausted", "data": {"kind": "model_calls", "limit": 0, "consumed": 0, "remaining": 0}})
                    branch_events = [*healthy_path, budget]
                terminal = copy.deepcopy(original_events[-1])
                terminal.update({"event_type": event_type, "data": {"result": "terminal", "outcome": outcome}})
                events = [
                    copy.deepcopy(original_events[0]),
                    copy.deepcopy(original_events[1]),
                    *checkpoint_events,
                    *branch_events,
                    terminal,
                ]
                for sequence, event in enumerate(events, start=1):
                    event["sequence"] = sequence
                    event["event_id"] = f"mission-healthy-001:{sequence:08d}"
                manifest.update({"outcome": outcome, "authoritative_result_id": None})
                for relative in ("receipts/payment.json", "receipts/inventory.json"):
                    (run_dir / relative).unlink()
                (run_dir / "effects.jsonl").write_text("", encoding="utf-8")
                state_path.write_text(json.dumps(state) + "\n", encoding="utf-8")
                events_path.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
                manifest["artifacts"] = sorted(
                    path.relative_to(run_dir).as_posix()
                    for path in run_dir.rglob("*")
                    if path.is_file() and path.name not in {"manifest.json", "checksums.sha256"}
                )
                manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
                self._rewrite_checksums(run_dir)
                invalid_events = copy.deepcopy(events)
                if branch == "approval_rejected":
                    invalid_events = [
                        event
                        for event in invalid_events
                        if event["event_type"] != "approval.requested"
                    ]
                elif branch == "approval_timed_out":
                    request_index = next(
                        index
                        for index, event in enumerate(invalid_events)
                        if event["event_type"] == "approval.requested"
                    )
                    decision_index = next(
                        index
                        for index, event in enumerate(invalid_events)
                        if event["event_type"] == "approval.timed_out"
                    )
                    invalid_events[request_index], invalid_events[decision_index] = (
                        invalid_events[decision_index],
                        invalid_events[request_index],
                    )
                elif branch == "readiness_failed":
                    invalid_events = [
                        event
                        for event in invalid_events
                        if event["event_type"] != "edge.join_starved"
                    ]
                elif branch == "cancelled":
                    request_index = next(
                        index
                        for index, event in enumerate(invalid_events)
                        if event["event_type"] == "cancellation.requested"
                    )
                    propagated_index = next(
                        index
                        for index, event in enumerate(invalid_events)
                        if event["event_type"] == "cancellation.propagated"
                    )
                    invalid_events[request_index], invalid_events[propagated_index] = (
                        invalid_events[propagated_index],
                        invalid_events[request_index],
                    )
                else:
                    invalid_events = [
                        event
                        for event in invalid_events
                        if event["event_type"] != "budget.exhausted"
                    ]
                for sequence, event in enumerate(invalid_events, start=1):
                    event["sequence"] = sequence
                    event["event_id"] = f"mission-healthy-001:{sequence:08d}"
                events_path.write_text(
                    "".join(json.dumps(event) + "\n" for event in invalid_events),
                    encoding="utf-8",
                )
                self._rewrite_checksums(run_dir)
                with self.assertRaises(ActivationError):
                    verify_and_publish_evidence(
                        staging,
                        evidence_root=evidence_root,
                        run_id=CASE_ID,
                        case_id=CASE_ID,
                        case_digest=CASE_DIGEST,
                        source_revision=SOURCE_REVISION,
                        exit_code=2,
                        validated_compose=b"{}\n",
                        verification=self.host_verification(),
                        commands=self.command_journal(),
                        runner_state={"Status": "exited", "ExitCode": 2, "OOMKilled": False},
                    )
                events_path.write_text(
                    "".join(json.dumps(event) + "\n" for event in events),
                    encoding="utf-8",
                )
                self._rewrite_checksums(run_dir)
                contradictory_events = copy.deepcopy(events)
                if branch == "approval_rejected":
                    forbidden = copy.deepcopy(contradictory_events[0])
                    forbidden.update(
                        {
                            "event_type": "task.started",
                            "node_id": "checkout_effect",
                            "task_id": "mission-healthy-001:checkout_effect:0",
                            "attempt_id": "mission-healthy-001:checkout_effect:0:attempt-1",
                            "data": {"status": "started"},
                        }
                    )
                    contradictory_events.insert(-1, forbidden)
                elif branch == "cancelled":
                    acknowledged = next(
                        event
                        for event in contradictory_events
                        if event["event_type"] == "cancellation.acknowledged"
                    )
                    acknowledged["data"]["state"] = "REQUESTED"
                elif branch == "budget_exhausted":
                    exhausted_event = next(
                        event
                        for event in contradictory_events
                        if event["event_type"] == "budget.exhausted"
                    )
                    exhausted_event["data"]["remaining"] = 1
                else:
                    contradictory_events = []
                if contradictory_events:
                    for sequence, event in enumerate(contradictory_events, start=1):
                        event["sequence"] = sequence
                        event["event_id"] = f"mission-healthy-001:{sequence:08d}"
                    events_path.write_text(
                        "".join(json.dumps(event) + "\n" for event in contradictory_events),
                        encoding="utf-8",
                    )
                    self._rewrite_checksums(run_dir)
                    with self.assertRaises(ActivationError):
                        verify_and_publish_evidence(
                            staging,
                            evidence_root=evidence_root,
                            run_id=CASE_ID,
                            case_id=CASE_ID,
                            case_digest=CASE_DIGEST,
                            source_revision=SOURCE_REVISION,
                            exit_code=2,
                            validated_compose=b"{}\n",
                            verification=self.host_verification(),
                            commands=self.command_journal(),
                            runner_state={"Status": "exited", "ExitCode": 2, "OOMKilled": False},
                        )
                    events_path.write_text(
                        "".join(json.dumps(event) + "\n" for event in events),
                        encoding="utf-8",
                    )
                    self._rewrite_checksums(run_dir)
                final = verify_and_publish_evidence(
                    staging,
                    evidence_root=evidence_root,
                    run_id=CASE_ID,
                    case_id=CASE_ID,
                    case_digest=CASE_DIGEST,
                    source_revision=SOURCE_REVISION,
                    exit_code=2,
                    validated_compose=b"{}\n",
                    verification=self.host_verification(),
                    commands=self.command_journal(),
                    runner_state={"Status": "exited", "ExitCode": 2, "OOMKilled": False},
                )
                self.assertEqual(json.loads((final / "final-state.json").read_text())["checkout_status"], "NOT_STARTED")
                self.assertEqual((final / "effects.jsonl").read_text(encoding="utf-8"), "")

    def test_unknown_rejects_nonterminal_effect_state_or_completed_checkout_receipt(self) -> None:
        for mutation in ("PREPARED", "DISPATCHED", "completed_receipt"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                evidence_root = Path(temporary)
                staging = evidence_root / ".mission-healthy-001.export"
                staging.mkdir()
                run_dir = self.write_runner_evidence(staging, outcome="FAILED")
                state_path = run_dir / "final-state.json"
                manifest_path = run_dir / "manifest.json"
                events_path = run_dir / "events.jsonl"
                state = json.loads(state_path.read_text(encoding="utf-8"))
                state.update({"outcome": "UNKNOWN", "checkout_status": "UNKNOWN"})
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                manifest["outcome"] = "UNKNOWN"
                events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
                events[-1]["data"]["outcome"] = "UNKNOWN"
                effects_path = run_dir / "effects.jsonl"
                effects = [json.loads(line) for line in effects_path.read_text(encoding="utf-8").splitlines()]
                if mutation in {"PREPARED", "DISPATCHED"}:
                    effects[-1]["effect_state"] = mutation
                else:
                    state["receipts"]["mission-healthy-001:checkout_effect:0:effect-checkout"] = {"completion_class": "COMPLETE"}
                state_path.write_text(json.dumps(state) + "\n", encoding="utf-8")
                manifest_path.write_text(json.dumps(manifest) + "\n", encoding="utf-8")
                events_path.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
                effects_path.write_text("".join(json.dumps(effect) + "\n" for effect in effects), encoding="utf-8")
                self._rewrite_checksums(run_dir)
                with self.assertRaisesRegex(
                    ActivationError,
                    "UNKNOWN effect evidence|false-success|effect ledger",
                ):
                    verify_and_publish_evidence(
                        staging,
                        evidence_root=evidence_root,
                        run_id=CASE_ID,
                        case_id=CASE_ID,
                        case_digest=CASE_DIGEST,
                        source_revision=SOURCE_REVISION,
                        exit_code=2,
                        validated_compose=b"{}\n",
                        verification=self.host_verification(),
                        runner_state={"Status": "exited", "ExitCode": 2, "OOMKilled": False},
                    )

    def test_success_evidence_rejects_empty_receipt_presence_oracle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence_root = Path(temporary)
            staging = evidence_root / ".mission-healthy-001.export"
            staging.mkdir()
            run_dir = self.write_runner_evidence(staging)
            (run_dir / "receipts/payment.json").write_text("{}\n", encoding="utf-8")
            checksum_lines = []
            for path in sorted(run_dir.rglob("*")):
                if path.is_file() and path.name != "checksums.sha256":
                    relative = path.relative_to(run_dir).as_posix()
                    checksum_lines.append(
                        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {relative}\n"
                    )
            (run_dir / "checksums.sha256").write_text(
                "".join(checksum_lines), encoding="ascii"
            )
            with self.assertRaisesRegex(ActivationError, "payment receipt schema"):
                verify_and_publish_evidence(
                    staging,
                    evidence_root=evidence_root,
                    run_id="mission-healthy-001",
                    case_id="mission-healthy-001",
                    case_digest="74266b9c39a7733128e25f7279bb18820664bfbd6c11d8b0a6a3fa5e53a685d1",
                    source_revision=SOURCE_REVISION,
                    exit_code=0,
                    validated_compose=b"{}\n",
                    verification={},
                )

    def test_success_evidence_rejects_invalid_control_state(self) -> None:
        invalid_values = {
            "approval": {},
            "tasks": {},
            "readiness": {},
            "budgets": {},
            "cancellation": {},
            "failure": {"plane": "graph-control"},
        }
        for field, invalid in invalid_values.items():
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                evidence_root = Path(temporary)
                staging = evidence_root / ".mission-healthy-001.export"
                staging.mkdir()
                run_dir = self.write_runner_evidence(staging)
                state_path = run_dir / "final-state.json"
                state = json.loads(state_path.read_text(encoding="utf-8"))
                state[field] = invalid
                state_path.write_text(json.dumps(state) + "\n", encoding="utf-8")
                self._rewrite_checksums(run_dir)
                with self.assertRaisesRegex(ActivationError, field):
                    verify_and_publish_evidence(
                        staging,
                        evidence_root=evidence_root,
                        run_id="mission-healthy-001",
                        case_id="mission-healthy-001",
                        case_digest="74266b9c39a7733128e25f7279bb18820664bfbd6c11d8b0a6a3fa5e53a685d1",
                        source_revision=SOURCE_REVISION,
                        exit_code=0,
                        validated_compose=b"{}\n",
                        verification=self.host_verification(),
                        runner_state={"Status": "exited", "ExitCode": 0, "OOMKilled": False},
                    )

    @staticmethod
    def _rewrite_checksums(run_dir: Path) -> None:
        checksum_lines = []
        for path in sorted(run_dir.rglob("*")):
            if path.is_file() and path.name != "checksums.sha256":
                relative = path.relative_to(run_dir).as_posix()
                checksum_lines.append(
                    f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {relative}\n"
                )
        (run_dir / "checksums.sha256").write_text(
            "".join(checksum_lines), encoding="ascii"
        )

    def test_failed_exit_rejects_false_success_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence_root = Path(temporary)
            staging = evidence_root / ".mission-healthy-001.export"
            staging.mkdir()
            self.write_runner_evidence(staging, outcome="SUCCEEDED")
            with self.assertRaisesRegex(ActivationError, "false-success"):
                verify_and_publish_evidence(
                    staging,
                    evidence_root=evidence_root,
                    run_id="mission-healthy-001",
                    case_id="mission-healthy-001",
                    case_digest="74266b9c39a7733128e25f7279bb18820664bfbd6c11d8b0a6a3fa5e53a685d1",
                    source_revision=SOURCE_REVISION,
                    exit_code=2,
                    validated_compose=b"{}\n",
                    verification=self.host_verification(),
                    runner_state={"Status": "exited", "ExitCode": 2, "OOMKilled": False},
                )

    def test_container_exit_or_oom_mismatch_rejects_before_publication(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            for state in (
                {"Status": "exited", "ExitCode": 2, "OOMKilled": False},
                {"Status": "exited", "ExitCode": 0, "OOMKilled": True},
            ):
                with self.subTest(state=state):
                    evidence_root = Path(temporary)
                    staging = evidence_root / f".{state['ExitCode']}.{state['OOMKilled']}.export"
                    staging.mkdir()
                    self.write_runner_evidence(staging)
                    with self.assertRaisesRegex(ActivationError, "runner container exit mismatch"):
                        verify_and_publish_evidence(
                            staging,
                            evidence_root=evidence_root,
                            run_id="mission-healthy-001",
                            case_id="mission-healthy-001",
                            case_digest="74266b9c39a7733128e25f7279bb18820664bfbd6c11d8b0a6a3fa5e53a685d1",
                            source_revision=SOURCE_REVISION,
                            exit_code=0,
                            validated_compose=b"{}\n",
                            verification=self.host_verification(),
                            runner_state=state,
                        )

    def test_fresh_run_claim_is_exclusive_and_resume_is_identity_bound(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            claim = RunClaim.acquire(
                "fresh", root, CASE_ID, SOURCE_REVISION, "context-a", CASE_ID, CASE_DIGEST,
                "APPROVED", "d" * 64,
            )
            with self.assertRaisesRegex(ActivationError, "already claimed"):
                RunClaim.acquire(
                    "fresh", root, CASE_ID, SOURCE_REVISION, "context-a", CASE_ID, CASE_DIGEST,
                    "APPROVED", "d" * 64,
                )
            claim.transition("RUNNING")
            claim.transition("PRESERVED")
            resumed = RunClaim.acquire(
                "resume", root, CASE_ID, SOURCE_REVISION, "context-a", CASE_ID, CASE_DIGEST,
                "APPROVED", "d" * 64,
            )
            self.assertEqual(resumed.path, claim.path)
            with self.assertRaisesRegex(ActivationError, "claim identity mismatch"):
                RunClaim.acquire(
                    "resume", root, CASE_ID, "b" * 40, "context-a", CASE_ID, CASE_DIGEST,
                    "APPROVED", "d" * 64,
                )
            resumed.release()
            self.assertFalse(claim.path.exists())

    def test_run_claim_binds_approval_and_validated_compose_digest(self) -> None:
        compose_digest = "d" * 64
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            claim = RunClaim.acquire(
                "fresh",
                root,
                CASE_ID,
                SOURCE_REVISION,
                "context-a",
                CASE_ID,
                CASE_DIGEST,
                "APPROVED",
                compose_digest,
            )
            claim.transition("RUNNING")
            claim.transition("PRESERVED")
            for approval_fixture, digest in (
                ("REJECTED", compose_digest),
                ("APPROVED", "e" * 64),
            ):
                with self.subTest(approval_fixture=approval_fixture, digest=digest):
                    with self.assertRaisesRegex(ActivationError, "claim identity mismatch"):
                        RunClaim.acquire(
                            "resume",
                            root,
                            CASE_ID,
                            SOURCE_REVISION,
                            "context-a",
                            CASE_ID,
                            CASE_DIGEST,
                            approval_fixture,
                            digest,
                        )
            resumed = RunClaim.acquire(
                "resume",
                root,
                CASE_ID,
                SOURCE_REVISION,
                "context-a",
                CASE_ID,
                CASE_DIGEST,
                "APPROVED",
                compose_digest,
            )
            resumed.release()

    def test_resume_requires_an_exclusive_active_lease(self) -> None:
        from activate import ActivationLease

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            first = ActivationLease.acquire(root, "mission-healthy-001")
            with self.assertRaisesRegex(ActivationError, "activation already in progress"):
                ActivationLease.acquire(root, "mission-healthy-001")
            first.release()
            second = ActivationLease.acquire(root, "mission-healthy-001")
            second.release()

    def test_activation_lease_is_kernel_held_and_crash_releases_it(self) -> None:
        holder_code = (
            "import sys; from pathlib import Path; from activate import ActivationLease; "
            "lease=ActivationLease.acquire(Path(sys.argv[1]),sys.argv[2]); "
            "print('LOCKED',flush=True); sys.stdin.read()"
        )
        probe_code = (
            "import sys; from pathlib import Path; from activate import ActivationLease,ActivationError; "
            "\ntry:\n lease=ActivationLease.acquire(Path(sys.argv[1]),sys.argv[2])"
            "\nexcept ActivationError:\n raise SystemExit(7)"
            "\nelse:\n lease.release(); raise SystemExit(0)"
        )
        with tempfile.TemporaryDirectory() as temporary:
            arguments = [sys.executable, "-c", holder_code, temporary, CASE_ID]
            holder = subprocess.Popen(
                arguments,
                cwd=SANDBOX_ROOT,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                self.assertEqual(holder.stdout.readline().strip(), "LOCKED")
                blocked = subprocess.run(
                    [sys.executable, "-c", probe_code, temporary, CASE_ID],
                    cwd=SANDBOX_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                self.assertEqual(blocked.returncode, 7, blocked.stderr)
                holder.terminate()
                holder.wait(timeout=10)
                recovered = subprocess.run(
                    [sys.executable, "-c", probe_code, temporary, CASE_ID],
                    cwd=SANDBOX_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    check=False,
                )
                self.assertEqual(recovered.returncode, 0, recovered.stderr)
            finally:
                if holder.poll() is None:
                    holder.kill()
                    holder.wait(timeout=10)
                for stream in (holder.stdin, holder.stdout, holder.stderr):
                    if stream is not None:
                        stream.close()

    def test_fresh_prelaunch_rejection_releases_claim_and_lease(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = type(
                "Args",
                (),
                {
                    "operation": "fresh",
                    "docker_context": "desktop-linux",
                    "source_revision": SOURCE_REVISION,
                    "run_id": "mission-healthy-001",
                    "evidence_root": root,
                    "case_id": CASE_ID,
                    "approval_fixture": "APPROVED",
                },
            )()
            context = ContextIdentity("desktop-linux", "npipe:////./pipe/docker", "f" * 64)
            layout = RepositoryLayout(root, root, root / "compose.yaml", root / "build.yaml", root / "lock.json")
            with (
                mock.patch("activate.trusted_layout", return_value=layout),
                mock.patch("activate.validate_local_context", return_value=context),
                mock.patch("activate._runtime_revision_is_exact"),
                mock.patch(
                    "activate.load_sandbox_case",
                    return_value=type("Case", (), {"case_id": CASE_ID, "digest": CASE_DIGEST})(),
                ),
                mock.patch("activate._prepare_evidence_directory"),
                mock.patch("activate._load_json", return_value={}),
                mock.patch("activate.render_compose", side_effect=ActivationError("prelaunch")),
                self.assertRaisesRegex(ActivationError, "prelaunch"),
            ):
                activate_runtime(args, runner=lambda *a, **k: completed([]), environ={"PATH": "safe"})
            self.assertEqual(list(root.glob(".*claim.json")), [])
            self.assertEqual(list(root.glob(".*lease")), [])

    def run_activation_with_mocked_preflight(
        self,
        args: object,
        *,
        docker: mock.Mock,
        sandbox_case: object,
        runner,
    ) -> tuple[int, str]:
        root = args.evidence_root
        context = ContextIdentity(
            "desktop-linux",
            "npipe:////./pipe/docker",
            "f" * 64,
        )
        layout = RepositoryLayout(
            root,
            root,
            root / "compose.yaml",
            root / "build.yaml",
            root / "lock.json",
        )
        output = StringIO()
        with (
            mock.patch("activate.trusted_layout", return_value=layout),
            mock.patch("activate.validate_local_context", return_value=context),
            mock.patch("activate._runtime_revision_is_exact"),
            mock.patch("activate.load_sandbox_case", return_value=sandbox_case),
            mock.patch(
                "activate._load_json",
                return_value={
                    "images": {
                        "runner": {
                            "base_reference": "python@sha256:" + "a" * 64,
                            "image_id": "sha256:" + "b" * 64,
                        },
                        "services": {"image_id": "sha256:" + "c" * 64},
                    }
                },
            ),
            mock.patch("activate.render_compose", return_value={}),
            mock.patch("activate.DockerCLI", return_value=docker),
            mock.patch("activate.validate_preflight"),
            redirect_stdout(output),
        ):
            exit_code = activate_runtime(
                args,
                runner=runner,
                environ={"PATH": "safe"},
            )
        return exit_code, output.getvalue()

    def test_runner_error_boundary_preserves_post_effect_and_cleans_pre_effect(
        self,
    ) -> None:
        cases = (
            ("post-effect-value-error", 1, 126, "PRESERVED"),
            ("pre-effect-configuration-error", 64, 64, None),
        )
        for error_class, runner_exit, expected_exit, expected_phase in cases:
            with self.subTest(error_class=error_class), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                run_id = f"round2-{error_class}"
                args = type(
                    "Args",
                    (),
                    {
                        "operation": "fresh",
                        "docker_context": "desktop-linux",
                        "source_revision": SOURCE_REVISION,
                        "run_id": run_id,
                        "evidence_root": root,
                        "case_id": CASE_ID,
                        "approval_fixture": "APPROVED",
                    },
                )()
                sandbox_case = type(
                    "Case",
                    (),
                    {"case_id": CASE_ID, "digest": CASE_DIGEST},
                )()
                expected_resources = expected_resource_records(run_id, SOURCE_REVISION)
                resources_exist = False
                calls: list[list[str]] = []
                docker = mock.Mock()
                docker.status.return_value = type(
                    "Status",
                    (),
                    {
                        "engine_version": "29",
                        "compose_version": "5",
                        "os_type": "linux",
                    },
                )()

                def resource_state(*_arguments) -> ResourceState:
                    return ResourceState(expected_resources if resources_exist else ())

                docker.resource_state.side_effect = resource_state

                def runner(arguments, *, environment, timeout_seconds, stdin=None):
                    nonlocal resources_exist
                    arguments = list(arguments)
                    calls.append(arguments)
                    if "up" in arguments:
                        resources_exist = True
                        return subprocess.CompletedProcess(
                            arguments,
                            runner_exit,
                            stdout="",
                            stderr=error_class,
                        )
                    if "stop" in arguments:
                        return completed(arguments)
                    if "down" in arguments:
                        resources_exist = False
                        return completed(arguments)
                    self.fail(f"unexpected activation command: {arguments}")

                exit_code, output = self.run_activation_with_mocked_preflight(
                    args,
                    docker=docker,
                    sandbox_case=sandbox_case,
                    runner=runner,
                )

                self.assertEqual(exit_code, expected_exit)
                claim_path = root / f".{run_id}.claim.json"
                if expected_phase is None:
                    self.assertFalse(claim_path.exists())
                    self.assertFalse(resources_exist)
                    self.assertIn("activation_terminal_rejection", output)
                    teardown = next(call for call in calls if "down" in call)
                    self.assertIn("--volumes", teardown)
                    self.assertFalse(any("stop" in call for call in calls))
                else:
                    claim = json.loads(claim_path.read_text(encoding="utf-8"))
                    self.assertEqual(claim["phase"], expected_phase)
                    self.assertTrue(claim["runner_existed"])
                    self.assertEqual(
                        claim["observed_resources"],
                        sorted(
                            f"{record.kind}:{record.name}"
                            for record in expected_resources
                        ),
                    )
                    self.assertTrue(resources_exist)
                    self.assertIn("activation_resume_required", output)
                    self.assertTrue(any("stop" in call for call in calls))
                    self.assertFalse(any("down" in call for call in calls))
                self.assertFalse(
                    any(
                        "ps" in call or "inspect" in call or "cp" in call
                        for call in calls
                    )
                )
                self.assertFalse((root / run_id).exists())

    def test_reconciliation_exhaustion_preserves_across_repeated_resume(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_id = "round2-reconciliation-exhausted"
            args = type(
                "Args",
                (),
                {
                    "operation": "resume",
                    "docker_context": "desktop-linux",
                    "source_revision": SOURCE_REVISION,
                    "run_id": run_id,
                    "evidence_root": root,
                    "case_id": CASE_ID,
                    "approval_fixture": "APPROVED",
                },
            )()
            context = ContextIdentity(
                "desktop-linux",
                "npipe:////./pipe/docker",
                "f" * 64,
            )
            compose_digest = hashlib.sha256(b"{}\n").hexdigest()
            expected_resources = expected_resource_records(run_id, SOURCE_REVISION)
            resource_keys = tuple(
                sorted(f"{record.kind}:{record.name}" for record in expected_resources)
            )
            claim = RunClaim.acquire(
                "fresh",
                root,
                run_id,
                SOURCE_REVISION,
                context.fingerprint,
                CASE_ID,
                CASE_DIGEST,
                "APPROVED",
                compose_digest,
            )
            claim.transition("RUNNING")
            claim.record_resources(resource_keys, runner_existed=True)
            claim.transition("PRESERVED")
            sandbox_case = type(
                "Case",
                (),
                {
                    "case_id": CASE_ID,
                    "digest": CASE_DIGEST,
                    "service_fixtures": {
                        "checkout": {"effect": "ambiguous_after_commit"}
                    },
                },
            )()
            docker = mock.Mock()
            docker.status.return_value = type(
                "Status",
                (),
                {
                    "engine_version": "29",
                    "compose_version": "5",
                    "os_type": "linux",
                },
            )()
            docker.resource_state.return_value = ResourceState(expected_resources)
            calls: list[list[str]] = []

            def runner(arguments, *, environment, timeout_seconds, stdin=None):
                arguments = list(arguments)
                calls.append(arguments)
                if "up" in arguments:
                    return subprocess.CompletedProcess(
                        arguments,
                        1,
                        stdout="",
                        stderr="reconciliation_attempts_exhausted",
                    )
                if "stop" in arguments:
                    return completed(arguments)
                self.fail(f"exhausted reconciliation must preserve: {arguments}")

            outputs = []
            for _resume in range(2):
                exit_code, output = self.run_activation_with_mocked_preflight(
                    args,
                    docker=docker,
                    sandbox_case=sandbox_case,
                    runner=runner,
                )
                self.assertEqual(exit_code, 126)
                outputs.append(json.loads(output))
                persisted = json.loads(claim.path.read_text(encoding="utf-8"))
                self.assertEqual(persisted["phase"], "PRESERVED")
                self.assertTrue(persisted["runner_existed"])
                self.assertEqual(persisted["observed_resources"], list(resource_keys))

            self.assertEqual(
                [event["event"] for event in outputs],
                ["activation_resume_required", "activation_resume_required"],
            )
            self.assertEqual(sum("up" in call for call in calls), 2)
            self.assertEqual(sum("stop" in call for call in calls), 2)
            self.assertFalse(
                any(
                    "down" in call
                    or "ps" in call
                    or "inspect" in call
                    or "cp" in call
                    for call in calls
                )
            )
            self.assertFalse((root / run_id).exists())

    def test_preserved_activation_retains_claim_and_prints_exact_resume_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = type(
                "Args",
                (),
                {
                    "operation": "fresh",
                    "docker_context": "desktop-linux",
                    "source_revision": SOURCE_REVISION,
                    "run_id": "run-independent-001",
                    "evidence_root": root,
                    "case_id": CASE_ID,
                    "approval_fixture": "APPROVED",
                },
            )()
            context = ContextIdentity("desktop-linux", "npipe:////./pipe/docker", "f" * 64)
            layout = RepositoryLayout(root, root, root / "compose.yaml", root / "build.yaml", root / "lock.json")
            sandbox_case = type("Case", (), {"case_id": CASE_ID, "digest": CASE_DIGEST})()
            docker = mock.Mock()
            docker.status.return_value = type(
                "Status", (), {"engine_version": "29", "compose_version": "5", "os_type": "linux"}
            )()
            expected = expected_resource_records("run-independent-001", SOURCE_REVISION)
            by_key = {(record.kind, record.name): record for record in expected}
            project = project_scope("run-independent-001")
            partial = ResourceState(
                (
                    by_key[("network", f"{project}_sandbox")],
                    by_key[("container", f"{project}-checkout-1")],
                    by_key[("volume", f"{project}_checkout-data")],
                )
            )
            docker.resource_state.side_effect = [ResourceState(()), partial]

            def preserved(*arguments, **kwargs):
                kwargs["on_launch"]()
                kwargs["on_preserve"]()
                return subprocess.CompletedProcess([], 126, stdout="", stderr="preserved")

            output = StringIO()
            with (
                mock.patch("activate.trusted_layout", return_value=layout),
                mock.patch("activate.validate_local_context", return_value=context),
                mock.patch("activate._runtime_revision_is_exact"),
                mock.patch("activate.load_sandbox_case", return_value=sandbox_case),
                mock.patch("activate._prepare_evidence_directory"),
                mock.patch(
                    "activate._load_json",
                    return_value={
                        "images": {
                            "runner": {"base_reference": "python@sha256:" + "a" * 64, "image_id": "sha256:" + "b" * 64},
                            "services": {"image_id": "sha256:" + "c" * 64},
                        }
                    },
                ),
                mock.patch("activate.render_compose", return_value={}),
                mock.patch("activate.DockerCLI", return_value=docker),
                mock.patch("activate.validate_preflight"),
                mock.patch("activate.execute_validated_compose", side_effect=preserved),
                redirect_stdout(output),
            ):
                exit_code = activate_runtime(args, runner=lambda *a, **k: completed([]), environ={"PATH": "safe"})
            self.assertEqual(exit_code, 126)
            handoff = json.loads(output.getvalue())
            self.assertEqual(handoff["event"], "activation_resume_required")
            self.assertEqual(handoff["resume_command"], __import__("activate")._resume_command(args))
            claim_path = root / ".run-independent-001.claim.json"
            claim_document = json.loads(claim_path.read_text(encoding="utf-8"))
            self.assertEqual(claim_document["phase"], "PRESERVED")
            self.assertEqual(claim_document["approval_fixture"], "APPROVED")
            self.assertEqual(
                claim_document["compose_digest"], hashlib.sha256(b"{}\n").hexdigest()
            )
            self.assertFalse(claim_document["runner_existed"])
            self.assertEqual(
                claim_document["observed_resources"],
                sorted(f"{record.kind}:{record.name}" for record in partial.records),
            )
            lease = __import__("activate").ActivationLease.acquire(root, "run-independent-001")
            lease.release()
            claim = RunClaim.acquire(
                "resume",
                root,
                "run-independent-001",
                SOURCE_REVISION,
                context.fingerprint,
                CASE_ID,
                CASE_DIGEST,
                "APPROVED",
                hashlib.sha256(b"{}\n").hexdigest(),
            )
            claim.release()

    def test_resume_continues_an_interrupted_running_claim_without_self_transition(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = type(
                "Args",
                (),
                {
                    "operation": "resume",
                    "docker_context": "desktop-linux",
                    "source_revision": SOURCE_REVISION,
                    "run_id": CASE_ID,
                    "evidence_root": root,
                    "case_id": CASE_ID,
                    "approval_fixture": "APPROVED",
                },
            )()
            context = ContextIdentity("desktop-linux", "npipe:////./pipe/docker", "f" * 64)
            layout = RepositoryLayout(
                root,
                root,
                root / "compose.yaml",
                root / "build.yaml",
                root / "lock.json",
            )
            sandbox_case = type("Case", (), {"case_id": CASE_ID, "digest": CASE_DIGEST})()
            compose_digest = hashlib.sha256(b"{}\n").hexdigest()
            claim = RunClaim.acquire(
                "fresh",
                root,
                CASE_ID,
                SOURCE_REVISION,
                context.fingerprint,
                CASE_ID,
                CASE_DIGEST,
                "APPROVED",
                compose_digest,
            )
            claim.transition("RUNNING")
            docker = mock.Mock()
            docker.status.return_value = type(
                "Status",
                (),
                {"engine_version": "29", "compose_version": "5", "os_type": "linux"},
            )()
            docker.resource_state.return_value = ResourceState(())

            def interrupted(*arguments, **kwargs):
                kwargs["on_launch"]()
                return subprocess.CompletedProcess([], 126, stdout="", stderr="preserved")

            with (
                mock.patch("activate.trusted_layout", return_value=layout),
                mock.patch("activate.validate_local_context", return_value=context),
                mock.patch("activate._runtime_revision_is_exact"),
                mock.patch("activate.load_sandbox_case", return_value=sandbox_case),
                mock.patch("activate._load_json", return_value={
                    "images": {
                        "runner": {
                            "base_reference": "python@sha256:" + "a" * 64,
                            "image_id": "sha256:" + "b" * 64,
                        },
                        "services": {"image_id": "sha256:" + "c" * 64},
                    }
                }),
                mock.patch("activate.render_compose", return_value={}),
                mock.patch("activate.DockerCLI", return_value=docker),
                mock.patch("activate.validate_preflight"),
                mock.patch("activate.execute_validated_compose", side_effect=interrupted),
                redirect_stdout(StringIO()),
            ):
                exit_code = activate_runtime(
                    args,
                    runner=lambda *a, **k: completed([]),
                    environ={"PATH": "safe"},
                )

            self.assertEqual(exit_code, 126)
            persisted = json.loads((root / f".{CASE_ID}.claim.json").read_text(encoding="utf-8"))
            self.assertEqual(persisted["phase"], "PRESERVED")

    def test_resume_recovers_a_published_directory_after_claim_transition_crash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            staging = root / ".published-before-claim.export"
            staging.mkdir()
            self.write_runner_evidence(staging)
            verify_and_publish_evidence(
                staging,
                evidence_root=root,
                run_id=CASE_ID,
                source_revision=SOURCE_REVISION,
                exit_code=0,
                validated_compose=b"{}\n",
                verification=self.host_verification(),
                commands=self.command_journal(),
            )

            args = type(
                "Args",
                (),
                {
                    "operation": "resume",
                    "docker_context": "desktop-linux",
                    "source_revision": SOURCE_REVISION,
                    "run_id": CASE_ID,
                    "evidence_root": root,
                    "case_id": CASE_ID,
                    "approval_fixture": "APPROVED",
                },
            )()
            context = ContextIdentity("desktop-linux", "npipe:////./pipe/docker", "f" * 64)
            layout = RepositoryLayout(
                root,
                root,
                root / "compose.yaml",
                root / "build.yaml",
                root / "lock.json",
            )
            sandbox_case = type("Case", (), {"case_id": CASE_ID, "digest": CASE_DIGEST})()
            claim = RunClaim.acquire(
                "fresh",
                root,
                CASE_ID,
                SOURCE_REVISION,
                context.fingerprint,
                CASE_ID,
                CASE_DIGEST,
                "APPROVED",
                hashlib.sha256(b"{}\n").hexdigest(),
            )
            claim.transition("RUNNING")
            docker = mock.Mock()
            docker.status.return_value = type(
                "Status",
                (),
                {"engine_version": "29", "compose_version": "5", "os_type": "linux"},
            )()
            docker.resource_state.return_value = ResourceState(())

            with (
                mock.patch("activate.trusted_layout", return_value=layout),
                mock.patch("activate.validate_local_context", return_value=context),
                mock.patch("activate._runtime_revision_is_exact"),
                mock.patch("activate.load_sandbox_case", return_value=sandbox_case),
                mock.patch("activate._load_json", return_value={
                    "images": {
                        "runner": {
                            "base_reference": "python@sha256:" + "a" * 64,
                            "image_id": "sha256:" + "b" * 64,
                        },
                        "services": {"image_id": "sha256:" + "c" * 64},
                    }
                }),
                mock.patch("activate.render_compose", return_value={}),
                mock.patch("activate.DockerCLI", return_value=docker),
                mock.patch("activate.validate_preflight"),
                mock.patch(
                    "activate.cleanup_published_resources",
                    return_value=completed([]),
                ) as cleanup,
                mock.patch("activate.execute_validated_compose") as execute,
            ):
                exit_code = activate_runtime(
                    args,
                    runner=lambda *a, **k: completed([]),
                    environ={"PATH": "safe"},
                )

            self.assertEqual(exit_code, 0)
            cleanup.assert_called_once()
            execute.assert_not_called()
            self.assertFalse((root / f".{CASE_ID}.claim.json").exists())

    def test_resume_revalidates_a_published_reconciliation_pair(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            final = root / CASE_ID
            unknown = final / "unknown"
            reconciled = final / "reconciled"
            unknown.mkdir(parents=True)
            reconciled.mkdir()
            immutable = {
                "run_id": CASE_ID,
                "case_id": CASE_ID,
                "case_digest": CASE_DIGEST,
                "source_revision": SOURCE_REVISION,
                "thread_id": f"checkout-payments-timeout-drill-v1:{CASE_ID}",
                "started_at": "2026-08-30T12:00:00.000Z",
            }
            unknown_manifest = {
                **immutable,
                "outcome": "UNKNOWN",
                "ended_at": "2026-08-30T12:00:01.000Z",
            }
            reconciled_manifest = {
                **immutable,
                "outcome": "SUCCEEDED",
                "ended_at": "2026-08-30T12:00:02.000Z",
            }
            for directory, manifest in (
                (unknown, unknown_manifest),
                (reconciled, reconciled_manifest),
            ):
                (directory / "manifest.json").write_text(
                    json.dumps(manifest) + "\n",
                    encoding="utf-8",
                )
            (unknown / "events.jsonl").write_text(
                json.dumps({"sequence": 1, "event_type": "effect.unknown"})
                + "\n"
                + json.dumps({"sequence": 2, "event_type": "run.terminal"})
                + "\n",
                encoding="utf-8",
            )
            (reconciled / "events.jsonl").write_text(
                json.dumps({"sequence": 1, "event_type": "effect.dispatched"})
                + "\n"
                + json.dumps({"sequence": 2, "event_type": "effect.reconciled"})
                + "\n"
                + json.dumps({"sequence": 3, "event_type": "run.terminal"})
                + "\n",
                encoding="utf-8",
            )

            # Each child passes its independent bundle check; only the pair check can
            # detect that the reconciled history does not extend the UNKNOWN history.
            with (
                mock.patch("activate._validate_published_bundle") as validate_bundle,
                mock.patch(
                    "activate._validate_reconciliation_pair",
                    wraps=_validate_reconciliation_pair,
                ) as validate_pair,
                self.assertRaisesRegex(ActivationError, "event history"),
            ):
                _validate_published_run(
                    final,
                    evidence_root=root,
                    run_id=CASE_ID,
                    case_id=CASE_ID,
                    case_digest=CASE_DIGEST,
                    source_revision=SOURCE_REVISION,
                    compose_digest=hashlib.sha256(b"{}\n").hexdigest(),
                    context_fingerprint="f" * 64,
                    reconciliation_timeline=True,
                )

            self.assertEqual(
                [
                    (call.args[0], call.kwargs["snapshot_role"])
                    for call in validate_bundle.call_args_list
                ],
                [(unknown, "UNKNOWN"), (reconciled, "RECONCILED")],
            )
            validate_pair.assert_called_once_with(
                unknown,
                reconciled,
                unknown_manifest,
                reconciled_manifest,
            )

    def test_timeout_stops_without_volumes_and_returns_resume_exit(self) -> None:
        calls: list[list[str]] = []

        def runner(arguments, *, environment, timeout_seconds, stdin=None):
            arguments = list(arguments)
            calls.append(arguments)
            if "up" in arguments:
                raise subprocess.TimeoutExpired(arguments, timeout_seconds)
            if "stop" in arguments:
                return completed(arguments)
            self.fail(f"unexpected timeout command: {arguments}")

        with tempfile.TemporaryDirectory() as temporary:
            result = execute_validated_compose(
                b'{"name":"validated"}\n',
                docker_context="desktop-linux",
                project_name=project_scope("mission-healthy-001"),
                evidence_root=Path(temporary),
                run_id="mission-healthy-001",
                source_revision=SOURCE_REVISION,
                verification={},
                runner=runner,
                environment={"PATH": "safe"},
                revalidate=lambda: None,
            )
        self.assertEqual(result.returncode, 124)
        stop = calls[-1]
        self.assertIn("stop", stop)
        self.assertNotIn("--volumes", stop)

    def test_production_wrapper_timeout_reaches_preservation_branch(self) -> None:
        timeout = subprocess.TimeoutExpired(["docker", "compose", "up"], 960)
        stop = completed(["docker", "compose", "stop"])
        with tempfile.TemporaryDirectory() as temporary, mock.patch(
            "preflight.subprocess.run", side_effect=[timeout, stop]
        ):
            result = execute_validated_compose(
                b'{"name":"validated"}\n',
                docker_context="desktop-linux",
                project_name=project_scope("mission-healthy-001"),
                evidence_root=Path(temporary),
                run_id="mission-healthy-001",
                source_revision=SOURCE_REVISION,
                verification={},
                runner=run_process,
                environment={"PATH": "safe"},
                revalidate=lambda: None,
            )
        self.assertEqual(result.returncode, 124)

    def test_production_wrapper_stop_failure_returns_preservation_failure(self) -> None:
        timeout = subprocess.TimeoutExpired(["docker", "compose", "up"], 960)
        failed_stop = subprocess.CompletedProcess(
            ["docker", "compose", "stop"], 1, stdout="", stderr="failed"
        )
        with tempfile.TemporaryDirectory() as temporary, mock.patch(
            "preflight.subprocess.run", side_effect=[timeout, failed_stop]
        ) as process:
            result = execute_validated_compose(
                b'{"name":"validated"}\n',
                docker_context="desktop-linux",
                project_name=project_scope("mission-healthy-001"),
                evidence_root=Path(temporary),
                run_id="mission-healthy-001",
                source_revision=SOURCE_REVISION,
                verification={},
                runner=run_process,
                environment={"PATH": "safe"},
                revalidate=lambda: None,
            )
        self.assertEqual(result.returncode, 125)
        self.assertFalse(
            any("--volumes" in list(call.args[0]) for call in process.call_args_list)
        )

    def test_keyboard_interrupt_stops_without_volumes_and_returns_resume_exit(self) -> None:
        calls: list[list[str]] = []

        def runner(arguments, *, environment, timeout_seconds, stdin=None):
            arguments = list(arguments)
            calls.append(arguments)
            if "up" in arguments:
                raise KeyboardInterrupt
            if "stop" in arguments:
                return completed(arguments)
            self.fail(f"unexpected interrupt command: {arguments}")

        with tempfile.TemporaryDirectory() as temporary:
            result = execute_validated_compose(
                b'{"name":"validated"}\n',
                docker_context="desktop-linux",
                project_name=project_scope("mission-healthy-001"),
                evidence_root=Path(temporary),
                run_id="mission-healthy-001",
                source_revision=SOURCE_REVISION,
                verification={},
                runner=runner,
                environment={"PATH": "safe"},
                revalidate=lambda: None,
            )
        self.assertEqual(result.returncode, 130)
        self.assertIn("stop", calls[-1])
        self.assertNotIn("--volumes", calls[-1])

    def test_stop_failure_returns_preservation_failure_without_volume_removal(self) -> None:
        calls: list[list[str]] = []

        def runner(arguments, *, environment, timeout_seconds, stdin=None):
            arguments = list(arguments)
            calls.append(arguments)
            if "up" in arguments:
                raise subprocess.TimeoutExpired(arguments, timeout_seconds)
            if "stop" in arguments:
                return subprocess.CompletedProcess(arguments, 1, stdout="", stderr="failed")
            self.fail(f"unexpected stop-failure command: {arguments}")

        with tempfile.TemporaryDirectory() as temporary:
            result = execute_validated_compose(
                b'{"name":"validated"}\n',
                docker_context="desktop-linux",
                project_name=project_scope("mission-healthy-001"),
                evidence_root=Path(temporary),
                run_id="mission-healthy-001",
                source_revision=SOURCE_REVISION,
                verification={},
                runner=runner,
                environment={"PATH": "safe"},
                revalidate=lambda: None,
            )
        self.assertEqual(result.returncode, 125)
        self.assertFalse(any("--volumes" in command for command in calls))

    def test_host_export_rejects_unexpected_paths_and_size_overflow(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence_root = Path(temporary)
            for case in ("unexpected", "oversized", "symlink"):
                with self.subTest(case=case):
                    staging = evidence_root / f".{case}.export"
                    staging.mkdir()
                    run_dir = self.write_runner_evidence(staging)
                    if case == "unexpected":
                        (run_dir / "checkpoint.sqlite3").write_bytes(b"unsafe")
                        diagnostic = "unexpected evidence path"
                        maximum = 32 * 1024 * 1024
                    elif case == "oversized":
                        diagnostic = "size limit"
                        maximum = 10
                    else:
                        diagnostic = "symlink or reparse"
                        maximum = 32 * 1024 * 1024
                    target_link = run_dir / "events.jsonl"
                    real_link_check = __import__("activate")._is_link_or_junction
                    link_patch = mock.patch(
                        "activate._is_link_or_junction",
                        side_effect=lambda path: Path(path) == target_link or real_link_check(Path(path)),
                    ) if case == "symlink" else mock.patch(
                        "activate._is_link_or_junction",
                        side_effect=real_link_check,
                    )
                    with link_patch:
                        with self.assertRaisesRegex(ActivationError, diagnostic):
                            verify_and_publish_evidence(
                                staging,
                                evidence_root=evidence_root,
                                run_id="mission-healthy-001",
                                case_id="mission-healthy-001",
                                case_digest="74266b9c39a7733128e25f7279bb18820664bfbd6c11d8b0a6a3fa5e53a685d1",
                                source_revision=SOURCE_REVISION,
                                exit_code=0,
                                validated_compose=b"{}\n",
                                verification={},
                                max_bytes=maximum,
                            )
    def test_only_frozen_subcommands_and_no_path_overrides_are_accepted(self) -> None:
        build = parse_args(
            ["build", "--docker-context", "desktop-linux", "--source-revision", SOURCE_REVISION]
        )
        self.assertEqual(build.operation, "build")
        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit):
                parse_args(
                    [
                        "fresh",
                        "--docker-context",
                        "desktop-linux",
                        "--source-revision",
                        SOURCE_REVISION,
                        "--run-id",
                        "mission-healthy-001",
                        "--evidence-root",
                        "evidence",
                        "--compose-file",
                        "attacker.yaml",
                    ]
                )

    def test_mutation_between_validation_and_launch_is_rejected(self) -> None:
        calls: list[list[str]] = []
        payload = b'{"name":"validated"}\n'

        def runner(arguments, *, environment, timeout_seconds, stdin=None):
            calls.append(list(arguments))
            return completed(list(arguments))

        def mutate(path: Path) -> None:
            path.write_bytes(b'{"name":"mutated"}\n')

        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ActivationError, "validated Compose bytes changed"):
                execute_validated_compose(
                    payload,
                    docker_context="desktop-linux",
                    project_name=project_scope("mission-healthy-001"),
                    evidence_root=Path(temporary),
                    run_id="mission-healthy-001",
                    source_revision=SOURCE_REVISION,
                    verification={},
                    runner=runner,
                    environment={"PATH": "safe"},
                    revalidate=lambda: None,
                    temp_parent=Path(temporary),
                    before_launch=mutate,
                )
        self.assertEqual(calls, [])

    def test_terminal_launch_exports_verifies_publishes_then_tears_down_exact_model(self) -> None:
        observed: dict[str, object] = {"commands": []}
        revalidations: list[str] = []
        payload = b'{"name":"validated"}\n'

        def runner(arguments, *, environment, timeout_seconds, stdin=None):
            arguments = list(arguments)
            observed["commands"].append(arguments)
            observed["environment"] = dict(environment)
            if "--file" in arguments:
                compose_path = Path(arguments[arguments.index("--file") + 1])
                self.assertEqual(compose_path.read_bytes(), payload)
            if "up" in arguments:
                return completed(arguments)
            if "ps" in arguments:
                return completed(arguments, "a" * 64 + "\n")
            if arguments[3:5] == ["container", "inspect"]:
                return completed(
                    arguments,
                    json.dumps({"Status": "exited", "ExitCode": 0, "OOMKilled": False}),
                )
            if arguments[3:5] == ["container", "cp"]:
                staging = Path(arguments[-1])
                self.write_runner_evidence(staging)
                return completed(arguments)
            if "down" in arguments:
                return completed(arguments)
            self.fail(f"unexpected lifecycle command: {arguments}")

        with tempfile.TemporaryDirectory() as temporary:
            evidence_root = Path(temporary)
            result = execute_validated_compose(
                payload,
                docker_context="desktop-linux",
                project_name=project_scope("mission-healthy-001"),
                evidence_root=evidence_root,
                run_id="mission-healthy-001",
                source_revision=SOURCE_REVISION,
                verification=self.host_verification(),
                runner=runner,
                environment={"PATH": "safe", "DOCKER_HOST": "tcp://remote"},
                revalidate=lambda: revalidations.append("validated"),
            )
            self.assertTrue((evidence_root / "mission-healthy-001" / "verification.json").is_file())
        self.assertEqual(result.returncode, 0)
        self.assertNotIn("DOCKER_HOST", observed["environment"])
        commands = observed["commands"]
        self.assertTrue(all(command[:3] == ["docker", "--context", "desktop-linux"] for command in commands))
        self.assertIn("--no-build", commands[0])
        self.assertEqual(commands[0][commands[0].index("--pull") + 1], "never")
        self.assertTrue(any("down" in command and "--volumes" in command for command in commands))
        self.assertEqual(len(revalidations), 5)

    def test_reconciliation_timeline_validates_and_publishes_both_snapshots(self) -> None:
        calls: list[list[str]] = []
        payload = b'{"name":"validated"}\n'

        def runner(arguments, *, environment, timeout_seconds, stdin=None):
            arguments = list(arguments)
            calls.append(arguments)
            if "up" in arguments:
                return completed(arguments)
            if "ps" in arguments:
                return completed(arguments, "a" * 64 + "\n")
            if arguments[3:5] == ["container", "inspect"]:
                return completed(
                    arguments,
                    json.dumps({"Status": "exited", "ExitCode": 0, "OOMKilled": False}),
                )
            if arguments[3:5] == ["container", "cp"]:
                staging = Path(arguments[-1])
                (staging / f"{CASE_ID}-unknown").mkdir()
                (staging / f"{CASE_ID}-reconciled").mkdir()
                return completed(arguments)
            if "down" in arguments:
                return completed(arguments)
            self.fail(f"unexpected lifecycle command: {arguments}")

        with tempfile.TemporaryDirectory() as temporary:
            evidence_root = Path(temporary)

            def validated(staging, **kwargs):
                directory_name = kwargs["directory_name"]
                return evidence_root, Path(staging), Path(staging) / directory_name, {
                    "outcome": kwargs["snapshot_role"]
                }

            final_parent = evidence_root / CASE_ID
            final_unknown = final_parent / "unknown"
            final_reconciled = final_parent / "reconciled"
            with (
                mock.patch("activate._validated_staged_run", side_effect=validated) as validate,
                mock.patch("activate._validate_reconciliation_pair") as validate_pair,
                mock.patch(
                    "activate._publish_staged_timeline",
                    return_value=(final_unknown, final_reconciled),
                ) as publish,
                mock.patch("activate._refresh_published_commands") as refresh,
            ):
                result = execute_validated_compose(
                    payload,
                    docker_context="desktop-linux",
                    project_name=project_scope(CASE_ID),
                    evidence_root=evidence_root,
                    run_id=CASE_ID,
                    source_revision=SOURCE_REVISION,
                    verification=self.host_verification(),
                    runner=runner,
                    environment={"PATH": "safe"},
                    revalidate=lambda: None,
                    reconciliation_timeline=True,
                )

            self.assertEqual(result.returncode, 0)
            self.assertEqual(
                [(call.kwargs["snapshot_role"], call.kwargs["exit_code"]) for call in validate.call_args_list],
                [("UNKNOWN", 2), ("RECONCILED", 0)],
            )
            publish.assert_called_once()
            validate_pair.assert_called_once()
            self.assertEqual(
                [call.args[0] for call in refresh.call_args_list],
                [final_unknown, final_reconciled],
            )
            self.assertTrue(any("down" in command and "--volumes" in command for command in calls))

    def test_context_change_after_up_blocks_every_later_docker_effect(self) -> None:
        calls: list[list[str]] = []
        validation_count = 0

        def runner(arguments, *, environment, timeout_seconds, stdin=None):
            arguments = list(arguments)
            calls.append(arguments)
            if "up" in arguments:
                return completed(arguments)
            return completed(arguments)

        def revalidate() -> None:
            nonlocal validation_count
            validation_count += 1
            if validation_count > 1:
                raise ActivationError("context.endpoint: Docker context changed during lifecycle")

        with tempfile.TemporaryDirectory() as temporary:
            result = execute_validated_compose(
                b'{"name":"validated"}\n',
                docker_context="desktop-linux",
                project_name=project_scope(CASE_ID),
                evidence_root=Path(temporary),
                run_id=CASE_ID,
                source_revision=SOURCE_REVISION,
                verification=self.host_verification(),
                runner=runner,
                environment={"PATH": "safe"},
                revalidate=revalidate,
            )

        self.assertEqual(result.returncode, 125)
        self.assertEqual(validation_count, 3)
        self.assertEqual(len(calls), 1)
        self.assertIn("up", calls[0])

    def test_nonterminal_exit_preserves_resources_without_export_or_teardown(self) -> None:
        calls: list[list[str]] = []
        preserved_resource_checks: list[str] = []

        def runner(arguments, *, environment, timeout_seconds, stdin=None):
            calls.append(list(arguments))
            if "stop" in arguments:
                return completed(list(arguments))
            return subprocess.CompletedProcess(arguments, 137, stdout="", stderr="")

        with tempfile.TemporaryDirectory() as temporary:
            evidence_root = Path(temporary)
            result = execute_validated_compose(
                b'{"name":"validated"}\n',
                docker_context="desktop-linux",
                project_name=project_scope("mission-healthy-001"),
                evidence_root=evidence_root,
                run_id="mission-healthy-001",
                source_revision=SOURCE_REVISION,
                verification=self.host_verification(),
                runner=runner,
                environment={"PATH": "safe"},
                revalidate=lambda: None,
                on_preserve=lambda: preserved_resource_checks.append("validated-subset"),
            )
            self.assertFalse((evidence_root / "mission-healthy-001").exists())
        self.assertEqual(result.returncode, 126)
        self.assertEqual(len(calls), 2)
        self.assertIn("stop", calls[-1])
        self.assertNotIn("--volumes", calls[-1])
        self.assertEqual(preserved_resource_checks, ["validated-subset"])

    def test_published_cleanup_accepts_an_empty_owned_subset_without_rerunning(self) -> None:
        calls: list[list[str]] = []
        validations: list[object] = []

        def runner(arguments, *, environment, timeout_seconds, stdin=None):
            arguments = list(arguments)
            calls.append(arguments)
            self.assertIn("down", arguments)
            self.assertNotIn("up", arguments)
            return completed(arguments)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            final = root / CASE_ID
            final.mkdir()
            (final / "commands.jsonl").write_bytes(
                _command_payload(
                    [
                        {
                            "command_version": "graph-sandbox-command/v1",
                            "phase": "activation",
                            "command": ["python", "graph-sandbox/activate.py", "resume"],
                            "time_utc": "2026-08-29T12:00:00.000Z",
                            "exit_status": 0,
                        }
                    ]
                )
            )

            def revalidate() -> None:
                validations.append(
                    validate_resource_mode(
                        "resume",
                        ResourceState(()),
                        run_id=CASE_ID,
                        source_revision=SOURCE_REVISION,
                        claim_phase="PUBLISHED",
                        runner_existed=True,
                    )
                )

            result = cleanup_published_resources(
                b'{"name":"validated"}\n',
                docker_context="desktop-linux",
                project_name=project_scope(CASE_ID),
                evidence_root=root,
                run_id=CASE_ID,
                runner=runner,
                environment={"PATH": "safe"},
                revalidate=revalidate,
                on_preserve=lambda: self.fail("successful cleanup must not preserve"),
            )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(validations), 1)
        self.assertEqual(len(calls), 1)

    def test_every_post_launch_fault_uses_the_single_preservation_funnel(self) -> None:
        cases = (
            ("up_result", 126),
            ("stop", 125),
            ("locate", 126),
            ("inspect", 126),
            ("copy", 126),
            ("staged_validation", 126),
            ("publish", 126),
            ("cleanup", 126),
        )
        for fault, expected_exit in cases:
            with self.subTest(fault=fault), tempfile.TemporaryDirectory() as temporary:
                evidence_root = Path(temporary)
                calls: list[list[str]] = []

                def runner(arguments, *, environment, timeout_seconds, stdin=None):
                    arguments = list(arguments)
                    calls.append(arguments)
                    if "up" in arguments:
                        return subprocess.CompletedProcess(arguments, 13 if fault in {"up_result", "stop"} else 0, stdout="", stderr="")
                    if "stop" in arguments:
                        return subprocess.CompletedProcess(arguments, 1 if fault == "stop" else 0, stdout="", stderr="")
                    if "ps" in arguments:
                        return subprocess.CompletedProcess(arguments, 1 if fault == "locate" else 0, stdout="" if fault == "locate" else "a" * 64, stderr="")
                    if "inspect" in arguments:
                        payload = "not-json" if fault == "inspect" else json.dumps({"Status": "exited", "ExitCode": 0, "OOMKilled": False})
                        return subprocess.CompletedProcess(arguments, 1 if fault == "inspect" else 0, stdout=payload, stderr="")
                    if "cp" in arguments:
                        return subprocess.CompletedProcess(arguments, 1 if fault == "copy" else 0, stdout="", stderr="")
                    if "down" in arguments:
                        return subprocess.CompletedProcess(arguments, 1 if fault == "cleanup" else 0, stdout="", stderr="")
                    return completed(arguments)

                validation_patch = mock.patch("activate._validated_staged_run", side_effect=ActivationError("staged")) if fault == "staged_validation" else mock.patch("activate._validated_staged_run")
                publish_patch = mock.patch("activate._publish_staged_run", side_effect=ActivationError("publish")) if fault == "publish" else mock.patch("activate._publish_staged_run")
                with validation_patch as validate_mock, publish_patch as publish_mock:
                    if fault in {"publish", "cleanup"}:
                        staging = evidence_root / ".export"
                        run_dir = staging / CASE_ID
                        validate_mock.return_value = (evidence_root, staging, run_dir, {})
                        final = evidence_root / CASE_ID
                        final.mkdir()
                        publish_mock.return_value = final
                    result = execute_validated_compose(
                        b'{"name":"validated"}\n',
                        docker_context="desktop-linux",
                        project_name=project_scope(CASE_ID),
                        evidence_root=evidence_root,
                        run_id=CASE_ID,
                        case_id=CASE_ID,
                        case_digest=CASE_DIGEST,
                        source_revision=SOURCE_REVISION,
                        verification=self.host_verification(),
                        runner=runner,
                        environment={"PATH": "safe"},
                        revalidate=lambda: None,
                    )
                self.assertEqual(result.returncode, expected_exit)
                self.assertTrue(any("stop" in call for call in calls))
                self.assertNotIn("--volumes", next(call for call in reversed(calls) if "stop" in call))

    def test_terminal_failed_graph_exports_partial_evidence_before_teardown(self) -> None:
        calls: list[list[str]] = []

        def runner(arguments, *, environment, timeout_seconds, stdin=None):
            arguments = list(arguments)
            calls.append(arguments)
            if "up" in arguments:
                return subprocess.CompletedProcess(arguments, 2, stdout="", stderr="")
            if "ps" in arguments:
                return completed(arguments, "b" * 64 + "\n")
            if arguments[3:5] == ["container", "inspect"]:
                return completed(
                    arguments,
                    json.dumps({"Status": "exited", "ExitCode": 2, "OOMKilled": False}),
                )
            if arguments[3:5] == ["container", "cp"]:
                self.write_runner_evidence(Path(arguments[-1]), outcome="FAILED")
                return completed(arguments)
            if "down" in arguments:
                return completed(arguments)
            self.fail(f"unexpected failed-run command: {arguments}")

        with tempfile.TemporaryDirectory() as temporary:
            evidence_root = Path(temporary)
            result = execute_validated_compose(
                b'{"name":"validated"}\n',
                docker_context="desktop-linux",
                project_name=project_scope("mission-healthy-001"),
                evidence_root=evidence_root,
                run_id="mission-healthy-001",
                source_revision=SOURCE_REVISION,
                verification=self.host_verification(),
                runner=runner,
                environment={"PATH": "safe"},
                revalidate=lambda: None,
            )
            manifest = json.loads(
                (evidence_root / "mission-healthy-001" / "manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            commands = [
                json.loads(line)
                for line in (
                    evidence_root / "mission-healthy-001" / "commands.jsonl"
                ).read_text(encoding="utf-8").splitlines()
            ]
        self.assertEqual(result.returncode, 2)
        self.assertEqual(manifest["outcome"], "FAILED")
        self.assertEqual(
            next(record["exit_status"] for record in commands if record["phase"] == "up"),
            2,
        )
        self.assertTrue(any("down" in command for command in calls))

    def test_terminal_rejection_tears_down_without_publishing_evidence(self) -> None:
        calls: list[list[str]] = []

        def runner(arguments, *, environment, timeout_seconds, stdin=None):
            arguments = list(arguments)
            calls.append(arguments)
            if "up" in arguments:
                return subprocess.CompletedProcess(arguments, 64, stdout="", stderr="bounded")
            if "down" in arguments:
                return completed(arguments)
            self.fail(f"unexpected rejection command: {arguments}")

        with tempfile.TemporaryDirectory() as temporary:
            evidence_root = Path(temporary)
            result = execute_validated_compose(
                b'{"name":"validated"}\n',
                docker_context="desktop-linux",
                project_name=project_scope("mission-healthy-001"),
                evidence_root=evidence_root,
                run_id="mission-healthy-001",
                source_revision=SOURCE_REVISION,
                verification={},
                runner=runner,
                environment={"PATH": "safe"},
                revalidate=lambda: None,
            )
            self.assertFalse((evidence_root / "mission-healthy-001").exists())
        self.assertEqual(result.returncode, 64)
        self.assertTrue(any("down" in command for command in calls))


if __name__ == "__main__":
    unittest.main()
