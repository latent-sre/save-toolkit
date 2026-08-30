from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock


SANDBOX_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SANDBOX_ROOT))

from preflight import (  # noqa: E402
    BASE_REFERENCE,
    DockerStatus,
    ImageMetadata,
    CASE_DIGESTS,
    PreflightError,
    build_context_digest,
    file_digest,
    load_sandbox_case,
    project_scope,
    render_compose,
    run_process,
    scrub_environment,
    validate_preflight,
)


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "compose"
SOURCE_REVISION = "a" * 40


class FakeDocker:
    def __init__(
        self,
        *,
        reachable: bool = True,
        os_type: str = "linux",
        compose_json: bool = True,
        unavailable_images: set[str] | None = None,
        resolved_images: dict[str, str] | None = None,
        entrypoints: dict[str, tuple[str, ...]] | None = None,
        declared_volumes: dict[str, tuple[str, ...]] | None = None,
    ) -> None:
        self._status = DockerStatus(reachable, os_type, compose_json, "29.7.2", "5.4.0")
        self._unavailable = unavailable_images or set()
        self._resolved = resolved_images or {}
        self._entrypoints = entrypoints or {}
        self._declared_volumes = declared_volumes or {}

    def status(self) -> DockerStatus:
        return self._status

    def inspect_image(self, image_id: str) -> ImageMetadata:
        if image_id in self._unavailable:
            raise PreflightError(f"image unavailable: {image_id}")
        return ImageMetadata(
            self._resolved.get(image_id, image_id),
            "linux/amd64",
            self._entrypoints.get(image_id, ()),
            self._declared_volumes.get(image_id, ()),
        )


class PreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.evidence_root = self.root / "evidence"
        self.evidence_dir = self.evidence_root / "mission-healthy-001"
        self.evidence_dir.mkdir(parents=True)

        self.sandbox_root = self.root / "sandbox"
        (self.sandbox_root / "runner").mkdir(parents=True)
        (self.sandbox_root / "services").mkdir()
        (self.sandbox_root / "cases").mkdir()
        (self.sandbox_root / "tests" / "contract").mkdir(parents=True)
        (self.sandbox_root / "tests" / "integration").mkdir()
        (self.sandbox_root / "tests" / "recovery").mkdir()
        (self.sandbox_root / ".dockerignore").write_text(
            "**\n!runner/\n!runner/**\n!services/\n!services/**\n"
            "!cases/\n!cases/**\n!tests/\n!tests/contract/\n"
            "!tests/contract/test_services_contract.py\n!tests/integration/\n"
            "!tests/contract/test_runner_contract.py\n"
            "!tests/integration/test_services_integration.py\n"
            "!tests/integration/test_runner_integration.py\n"
            "!tests/recovery/\n!tests/recovery/**\n!.dockerignore\n",
            encoding="utf-8",
        )
        for relative in ("runner/Dockerfile", "services/Dockerfile"):
            (self.sandbox_root / relative).write_text(f"FROM {BASE_REFERENCE}\n", encoding="utf-8")
        (self.sandbox_root / "runner" / "main.py").write_text("VALUE = 1\n", encoding="utf-8")
        (self.sandbox_root / "services" / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
        (self.sandbox_root / "cases" / "mission.json").write_text("{}\n", encoding="utf-8")
        for relative in (
            "tests/contract/test_services_contract.py",
            "tests/contract/test_runner_contract.py",
            "tests/integration/test_services_integration.py",
            "tests/integration/test_runner_integration.py",
            "tests/recovery/test_runner_recovery.py",
        ):
            (self.sandbox_root / relative).write_text("VALUE = 1\n", encoding="utf-8")

        self.model = json.loads((FIXTURE_ROOT / "valid-default.json").read_text(encoding="utf-8"))
        self.case = load_sandbox_case(SANDBOX_ROOT / "cases", "mission-healthy-001")
        self.lock = json.loads((FIXTURE_ROOT / "valid-lock.json").read_text(encoding="utf-8"))
        context_digest = build_context_digest(self.sandbox_root)
        for logical_name in ("runner", "services"):
            record = self.lock["images"][logical_name]
            record["build_context_digest"] = context_digest
            record["dockerfile_digest"] = file_digest(
                self.sandbox_root / logical_name / "Dockerfile"
            )

    def validate(
        self,
        *,
        model: dict[str, object] | None = None,
        lock: dict[str, object] | None = None,
        docker: FakeDocker | None = None,
        profile: str = "default",
    ) -> None:
        validate_preflight(
            model if model is not None else self.model,
            lock if lock is not None else self.lock,
            sandbox_root=self.sandbox_root,
            source_revision=SOURCE_REVISION,
            run_id="mission-healthy-001",
            sandbox_case=self.case,
            profile=profile,
            docker=docker or FakeDocker(),
        )

    def rejected(self, model: dict[str, object], diagnostic: str) -> None:
        with self.assertRaisesRegex(PreflightError, diagnostic):
            self.validate(model=model)

    def test_reviewed_default_model_passes(self) -> None:
        self.validate()

    def test_runner_waits_for_exact_service_health_and_healthchecks_are_closed(self) -> None:
        for dependency in ("checkout", "payments", "inventory"):
            with self.subTest(dependency=dependency):
                broken = copy.deepcopy(self.model)
                broken["services"]["graph-runner"]["depends_on"][dependency]["condition"] = "service_started"
                self.rejected(broken, rf"depends_on\.{dependency}")
        broken = copy.deepcopy(self.model)
        del broken["services"]["payments"]["healthcheck"]
        self.rejected(broken, r"payments\.healthcheck")
        broken = copy.deepcopy(self.model)
        broken["services"]["graph-runner"]["healthcheck"] = {"test": ["NONE"]}
        self.rejected(broken, r"graph-runner\.healthcheck")

    def test_service_fixture_projection_and_five_durable_volumes_are_exact(self) -> None:
        self.assertEqual(
            set(self.model["volumes"]),
            {"runner-state", "runner-evidence", "checkout-data", "payments-data", "inventory-data"},
        )
        for service in ("checkout", "payments", "inventory"):
            with self.subTest(service=service):
                broken = copy.deepcopy(self.model)
                broken["services"][service]["environment"]["EFFECT_FIXTURE"] = "mismatch"
                self.rejected(broken, rf"{service}.*EFFECT_FIXTURE")

    def test_case_catalog_is_exact_closed_and_digest_frozen(self) -> None:
        observed = {path.stem for path in (SANDBOX_ROOT / "cases").glob("*.json")}
        self.assertEqual(observed, set(CASE_DIGESTS))
        for case_id in sorted(observed):
            with self.subTest(case_id=case_id):
                case = load_sandbox_case(SANDBOX_ROOT / "cases", case_id)
                self.assertEqual(case.case_id, case_id)
                self.assertEqual(case.digest, CASE_DIGESTS[case_id])

    def test_unknown_or_changed_case_fails_before_render(self) -> None:
        with self.assertRaisesRegex(PreflightError, "unknown frozen case"):
            load_sandbox_case(SANDBOX_ROOT / "cases", "not-a-case")
        with tempfile.TemporaryDirectory() as temporary:
            cases = Path(temporary) / "cases"
            cases.mkdir()
            for source in (SANDBOX_ROOT / "cases").glob("*.json"):
                (cases / source.name).write_bytes(source.read_bytes())
            target = cases / "mission-healthy-001.json"
            target.write_bytes(target.read_bytes() + b"\n")
            with self.assertRaisesRegex(PreflightError, "frozen digest mismatch"):
                load_sandbox_case(cases, "mission-healthy-001")

    def test_runtime_compose_source_is_guarded_against_direct_invocation(self) -> None:
        for name in ("compose.yaml", "compose.build.yaml"):
            with self.subTest(name=name):
                first_line = (SANDBOX_ROOT / name).read_text(encoding="utf-8").splitlines()[0]
                self.assertEqual(first_line, "activation_guard: graph-sandbox/activate.py/v1")

        project = project_scope("mission-healthy-001")
        direct_environment = scrub_environment(
            os.environ,
            extra={
                "APPROVAL_FIXTURE": "APPROVED",
                "GRAPH_EVIDENCE_DIR": str(self.evidence_dir),
                "GRAPH_PROJECT_NAME": project,
                "GRAPH_RUN_ID": "mission-healthy-001",
                "GRAPH_RUNNER_IMAGE_ID": "sha256:" + "d" * 64,
                "GRAPH_SCOPE_HASH": project.removeprefix("graph-sandbox-v1-"),
                "SANDBOX_CASE_ID": self.case.case_id,
                "SANDBOX_CASE_DIGEST": self.case.digest,
                "CHECKOUT_READINESS_FIXTURE": "ready",
                "CHECKOUT_EFFECT_FIXTURE": "success",
                "PAYMENTS_READINESS_FIXTURE": "ready",
                "PAYMENTS_EFFECT_FIXTURE": "success",
                "INVENTORY_READINESS_FIXTURE": "ready",
                "INVENTORY_EFFECT_FIXTURE": "success",
                "SOURCE_REVISION": SOURCE_REVISION,
                "SYNTHETIC_SERVICES_IMAGE_ID": "sha256:" + "e" * 64,
            },
        )
        direct = run_process(
            [
                "docker",
                "--context",
                "desktop-linux",
                "compose",
                "--file",
                str(SANDBOX_ROOT / "compose.yaml"),
                "--project-name",
                project,
                "config",
                "--format",
                "json",
            ],
            environment=direct_environment,
            timeout_seconds=30,
            stdin=None,
        )
        self.assertNotEqual(direct.returncode, 0)
        self.assertIn("activation_guard", direct.stderr)

    def test_run_process_decodes_malformed_command_output_without_host_locale_failure(self) -> None:
        result = run_process(
            [
                sys.executable,
                "-c",
                "import os; os.write(1, bytes([0x81])); os.write(2, b'ok')",
            ],
            environment=os.environ,
            timeout_seconds=10,
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "\ufffd")
        self.assertEqual(result.stderr, "ok")

    def test_checked_in_compose_renders_to_the_reviewed_model(self) -> None:
        rendered = render_compose(
            SANDBOX_ROOT / "compose.yaml",
            docker_context="desktop-linux",
            image_lock=self.lock,
            source_revision=SOURCE_REVISION,
            run_id="mission-healthy-001",
            sandbox_case=self.case,
            approval_fixture="APPROVED",
            profile="default",
        )
        self.validate(model=rendered)

    def test_negative_fixture_catalog_covers_contract_classes(self) -> None:
        classes = json.loads(
            (FIXTURE_ROOT / "contract-negative-classes.json").read_text(encoding="utf-8")
        )
        self.assertEqual(len(classes), len(set(classes)))
        self.assertGreaterEqual(len(classes), 45)

    def test_daemon_unavailable_is_rejected_before_model_acceptance(self) -> None:
        with self.assertRaisesRegex(PreflightError, "docker.daemon"):
            self.validate(docker=FakeDocker(reachable=False))

    def test_non_linux_daemon_is_rejected(self) -> None:
        with self.assertRaisesRegex(PreflightError, "docker.os"):
            self.validate(docker=FakeDocker(os_type="windows"))

    def test_compose_json_capability_is_required(self) -> None:
        with self.assertRaisesRegex(PreflightError, "docker.compose"):
            self.validate(docker=FakeDocker(compose_json=False))

    def test_service_allowlist_and_saturation_profile_are_exact(self) -> None:
        unexpected = copy.deepcopy(self.model)
        unexpected["services"]["database"] = copy.deepcopy(unexpected["services"]["inventory"])
        self.rejected(unexpected, "services.allowlist")

        loadgen = copy.deepcopy(self.model)
        loadgen["services"]["loadgen"] = copy.deepcopy(loadgen["services"]["inventory"])
        loadgen["services"]["loadgen"]["command"] = ["python", "-m", "sandbox_services.loadgen"]
        loadgen["services"]["loadgen"]["profiles"] = ["saturation"]
        del loadgen["services"]["loadgen"]["healthcheck"]
        del loadgen["services"]["loadgen"]["volumes"]
        loadgen["services"]["loadgen"]["environment"] = {
            "CHECKOUT_URL": "http://checkout:8080",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1",
            "RUN_ID": "mission-healthy-001",
            "RUN_TIMEOUT_SECONDS": "300",
            "CASE_ID": "mission-healthy-001",
        }
        self.rejected(loadgen, "services.allowlist")
        self.validate(model=loadgen, profile="saturation")

    def test_images_must_be_immutable_locked_and_locally_available(self) -> None:
        mutable = copy.deepcopy(self.model)
        mutable["services"]["graph-runner"]["image"] = "graph-sandbox/runner:latest"
        self.rejected(mutable, "services.graph-runner.image")

        build = copy.deepcopy(self.model)
        build["services"]["graph-runner"]["build"] = {"context": "."}
        self.rejected(build, "services.graph-runner.build")

        pull = copy.deepcopy(self.model)
        pull["services"]["graph-runner"]["pull_policy"] = "always"
        self.rejected(pull, "services.graph-runner.pull_policy")

        mismatched_lock = copy.deepcopy(self.lock)
        mismatched_lock["images"]["runner"]["image_id"] = "sha256:" + "f" * 64
        with self.assertRaisesRegex(PreflightError, "images.lock.runner.image_id"):
            self.validate(lock=mismatched_lock)

        runner_image = self.model["services"]["graph-runner"]["image"]
        with self.assertRaisesRegex(PreflightError, "image unavailable"):
            self.validate(docker=FakeDocker(unavailable_images={runner_image}))

    def test_image_config_entrypoint_and_declared_volumes_are_rejected(self) -> None:
        runner_image = self.model["services"]["graph-runner"]["image"]
        with self.assertRaisesRegex(PreflightError, "config.Entrypoint"):
            self.validate(docker=FakeDocker(entrypoints={runner_image: ("/bin/sh",)}))
        with self.assertRaisesRegex(PreflightError, "config.Volumes"):
            self.validate(docker=FakeDocker(declared_volumes={runner_image: ("/state",)}))

    def test_runtime_requires_explicit_empty_entrypoint_override(self) -> None:
        model = copy.deepcopy(self.model)
        model["services"]["checkout"]["entrypoint"] = None
        self.rejected(model, "services.checkout.entrypoint")

    def test_approval_fixture_is_exact_uppercase_contract_value(self) -> None:
        model = copy.deepcopy(self.model)
        model["services"]["graph-runner"]["environment"]["APPROVAL_FIXTURE"] = "approved"
        self.rejected(model, "APPROVAL_FIXTURE")

    def test_identity_and_container_hardening_are_required(self) -> None:
        cases: list[tuple[str, object, str]] = [
            ("user", "0:0", "services.checkout.user"),
            ("user", "app", "services.checkout.user"),
            ("read_only", False, "services.checkout.read_only"),
            ("cap_drop", [], "services.checkout.cap_drop"),
            ("cap_add", ["NET_ADMIN"], "services.checkout.cap_add"),
            ("security_opt", [], "services.checkout.security_opt"),
        ]
        for key, value, diagnostic in cases:
            with self.subTest(key=key, value=value):
                model = copy.deepcopy(self.model)
                model["services"]["checkout"][key] = value
                self.rejected(model, diagnostic)

    def test_resource_limits_and_runner_timeout_are_bounded(self) -> None:
        for key, value in (("cpus", 3), ("mem_limit", 536870913), ("pids_limit", 129)):
            with self.subTest(key=key):
                model = copy.deepcopy(self.model)
                model["services"]["checkout"][key] = value
                self.rejected(model, f"services.checkout.{key}")

                missing = copy.deepcopy(self.model)
                del missing["services"]["checkout"][key]
                self.rejected(missing, f"services.checkout.{key}")

        for value in ("0", "901", "not-an-integer"):
            with self.subTest(timeout=value):
                model = copy.deepcopy(self.model)
                model["services"]["graph-runner"]["environment"]["RUN_TIMEOUT_SECONDS"] = value
                self.rejected(model, "RUN_TIMEOUT_SECONDS")

        missing_timeout = copy.deepcopy(self.model)
        del missing_timeout["services"]["graph-runner"]["environment"]["RUN_TIMEOUT_SECONDS"]
        self.rejected(missing_timeout, "RUN_TIMEOUT_SECONDS")

    def test_host_and_network_authority_keys_are_rejected(self) -> None:
        forbidden = {
            "ports": ["127.0.0.1:8080:8080"],
            "privileged": True,
            "devices": ["/dev/null:/dev/null"],
            "pid": "host",
            "ipc": "host",
            "uts": "host",
            "network_mode": "host",
            "external_links": ["outside"],
            "extra_hosts": ["host.docker.internal:host-gateway"],
            "dns": ["8.8.8.8"],
            "secrets": ["credential"],
        }
        for key, value in forbidden.items():
            with self.subTest(key=key):
                model = copy.deepcopy(self.model)
                model["services"]["checkout"][key] = value
                self.rejected(model, f"services.checkout.{key}")

    def test_environment_and_command_allowlists_are_exact(self) -> None:
        credential = copy.deepcopy(self.model)
        credential["services"]["checkout"]["environment"]["AWS_SECRET_ACCESS_KEY"] = "unsafe"
        self.rejected(credential, "AWS_SECRET_ACCESS_KEY")

        unexpected = copy.deepcopy(self.model)
        unexpected["services"]["checkout"]["environment"]["DEBUG"] = "1"
        self.rejected(unexpected, "services.checkout.environment.DEBUG")

        command = copy.deepcopy(self.model)
        command["services"]["checkout"]["command"] = ["sh", "-c", "python -m sandbox_services.checkout"]
        self.rejected(command, "services.checkout.command")

        unresolved = copy.deepcopy(self.model)
        unresolved["services"]["checkout"]["environment"]["PAYMENTS_URL"] = "${PAYMENTS_URL}"
        self.rejected(unresolved, "unresolved interpolation")

    def test_network_is_the_single_internal_non_external_network(self) -> None:
        not_internal = copy.deepcopy(self.model)
        not_internal["networks"]["sandbox"]["internal"] = False
        self.rejected(not_internal, "networks.sandbox.internal")

        external = copy.deepcopy(self.model)
        external["networks"]["sandbox"]["external"] = True
        self.rejected(external, "networks.sandbox.external")

        unexpected = copy.deepcopy(self.model)
        unexpected["networks"]["internet"] = {"name": "internet", "internal": False}
        self.rejected(unexpected, "networks.allowlist")

    def test_mount_allowlist_rejects_socket_wrong_targets_and_extra_storage(self) -> None:
        socket_mount = copy.deepcopy(self.model)
        socket_mount["services"]["checkout"]["volumes"] = [
            {"type": "bind", "source": "/var/run/docker.sock", "target": "/var/run/docker.sock"}
        ]
        self.rejected(socket_mount, "services.checkout.volumes")

        wrong_target = copy.deepcopy(self.model)
        wrong_target["services"]["graph-runner"]["volumes"][1]["target"] = "/workspace"
        self.rejected(wrong_target, "services.graph-runner.volumes.evidence.target")

        extra_bind = copy.deepcopy(self.model)
        extra_bind["services"]["graph-runner"]["volumes"].append(
            {"type": "bind", "source": str(self.root), "target": "/host"}
        )
        self.rejected(extra_bind, "services.graph-runner.volumes")

        service_volume = copy.deepcopy(self.model)
        service_volume["services"]["payments"]["volumes"] = [
            {"type": "volume", "source": "checkpoint-data", "target": "/state"}
        ]
        self.rejected(service_volume, "services.payments.volumes")

        wrong_tmpfs = copy.deepcopy(self.model)
        wrong_tmpfs["services"]["payments"]["tmpfs"] = ["/run:size=16777216"]
        self.rejected(wrong_tmpfs, "services.payments.tmpfs")

    def test_runner_named_volume_sources_and_copy_semantics_are_exact(self) -> None:
        nocopy = copy.deepcopy(self.model)
        nocopy["services"]["graph-runner"]["volumes"][0]["volume"] = {"nocopy": True}
        self.rejected(nocopy, "services.graph-runner.volumes.state")

        bind = copy.deepcopy(self.model)
        bind["services"]["graph-runner"]["volumes"][1] = {
            "type": "bind",
            "source": str(self.evidence_dir),
            "target": "/evidence",
        }
        self.rejected(bind, "services.graph-runner.volumes")

        wrong_source = copy.deepcopy(self.model)
        wrong_source["services"]["graph-runner"]["volumes"][1]["source"] = "checkpoint-data"
        self.rejected(wrong_source, "services.graph-runner.volumes.evidence")

    def test_unknown_top_level_and_service_keys_fail_closed(self) -> None:
        top = copy.deepcopy(self.model)
        top["configs"] = {"unsafe": {"file": "secret"}}
        self.rejected(top, "top-level keys")

        service = copy.deepcopy(self.model)
        service["services"]["checkout"]["sysctls"] = {"net.ipv4.ip_forward": "1"}
        self.rejected(service, "services.checkout.sysctls")

    def test_lock_binds_revision_base_dockerfiles_and_build_context(self) -> None:
        cases = {
            "source_revision": "f" * 40,
            "base_reference": "python:3.12-slim",
            "dockerfile_digest": "sha256:" + "f" * 64,
            "build_context_digest": "sha256:" + "f" * 64,
        }
        for field, value in cases.items():
            with self.subTest(field=field):
                lock = copy.deepcopy(self.lock)
                lock["images"]["runner"][field] = value
                with self.assertRaisesRegex(PreflightError, f"images.lock.runner.{field}"):
                    self.validate(lock=lock)

    def test_digest_helpers_reject_symlinks_in_build_context(self) -> None:
        link = self.sandbox_root / "runner" / "linked.py"
        link.write_text("VALUE = 1\n", encoding="utf-8")
        real_link_check = __import__("preflight")._is_link_or_junction
        with mock.patch(
            "preflight._is_link_or_junction",
            side_effect=lambda path: Path(path) == link or real_link_check(Path(path)),
        ):
            with self.assertRaisesRegex(PreflightError, "symlink"):
                build_context_digest(self.sandbox_root)


if __name__ == "__main__":
    unittest.main()
