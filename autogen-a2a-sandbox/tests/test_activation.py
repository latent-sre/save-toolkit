from __future__ import annotations

import copy
import importlib.util
import json
import os
import platform
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from io import StringIO
from datetime import datetime
from pathlib import Path
from unittest.mock import patch


SANDBOX_ROOT = Path(__file__).resolve().parents[1]
ACTIVATE_PATH = SANDBOX_ROOT / "activate.py"
RUNTIME_PATH = SANDBOX_ROOT / "interop_sandbox" / "runtime_cli.py"


def _load_activate():
    spec = importlib.util.spec_from_file_location("sandbox_activate", ACTIVATE_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("activate.py is not importable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_runtime():
    sys.path.insert(0, str(SANDBOX_ROOT))
    from interop_sandbox import runtime_cli

    return runtime_cli


def _rendered_model(image: str = "sha256:" + "a" * 64) -> dict[str, object]:
    common = {
        "image": image,
        "user": "65532:65532",
        "read_only": True,
        "init": True,
        "cap_drop": ["ALL"],
        "security_opt": ["no-new-privileges:true"],
        "pids_limit": 64,
        "cpus": 0.75,
        "mem_limit": "536870912",
        "tmpfs": ["/tmp:rw,noexec,nosuid,nodev,size=67108864"],
        "networks": {"sandbox": None},
    }
    worker = {
        **common,
        "command": [
            "python",
            "-m",
            "interop_sandbox.runtime_cli",
            "worker",
            "--state-directory",
            "/state",
            "--agent-url",
            "http://worker:8081/a2a/jsonrpc",
            "--host",
            "0.0.0.0",
            "--port",
            "8081",
        ],
        "healthcheck": {
            "test": [
                "CMD",
                "python",
                "-m",
                "interop_sandbox.runtime_cli",
                "healthcheck",
                "--url",
                "http://127.0.0.1:8081/readyz",
            ],
            "interval": "2s",
            "timeout": "2s",
            "retries": 20,
            "start_period": "2s",
        },
        "volumes": [
            {"type": "volume", "source": "state", "target": "/state"}
        ],
    }
    orchestrator = {
        **common,
        "command": [
            "python",
            "-m",
            "interop_sandbox.runtime_cli",
            "orchestrate",
            "--mode",
            "fresh",
            "--source-revision",
            "1" * 40,
            "--run-id",
            "mission-healthy-001",
            "--case",
            "mission-healthy-001",
            "--decision",
            "NONE",
            "--worker-url",
            "http://worker:8081",
            "--state-directory",
            "/state",
            "--evidence-directory",
            "/evidence",
            "--cases-directory",
            "/opt/interop-sandbox/cases",
        ],
        "depends_on": {
            "worker": {"condition": "service_healthy", "required": True}
        },
        "volumes": [
            {"type": "volume", "source": "state", "target": "/state"},
            {"type": "volume", "source": "evidence", "target": "/evidence"},
        ],
    }
    return {
        "name": "a2a-deadbeef",
        "services": {"worker": worker, "orchestrator": orchestrator},
        "networks": {"sandbox": {"name": "a2a-deadbeef-network", "internal": True}},
        "volumes": {
            "state": {"name": "a2a-deadbeef-state"},
            "evidence": {"name": "a2a-deadbeef-evidence"},
        },
    }


class ActivationImportTests(unittest.TestCase):
    def test_host_entrypoint_imports_without_third_party_packages(self) -> None:
        source = ACTIVATE_PATH.read_text(encoding="utf-8")
        forbidden = (
            "agent_framework",
            "autogen_",
            "from a2a",
            "import a2a",
            "import httpx",
            "import yaml",
        )
        for marker in forbidden:
            with self.subTest(marker=marker):
                self.assertNotIn(marker, source)
        module = _load_activate()
        self.assertTrue(callable(module.build_parser))

    def test_parser_exposes_only_build_fresh_and_resume(self) -> None:
        parser = _load_activate().build_parser()
        for command in ("build", "fresh", "resume"):
            with self.subTest(command=command):
                args = parser.parse_args(
                    [
                        command,
                        "--docker-context",
                        "desktop-linux",
                        "--source-revision",
                        "1" * 40,
                        *(
                            []
                            if command == "build"
                            else [
                                "--run-id",
                                "mission-healthy-001",
                                "--evidence-root",
                                os.getcwd(),
                            ]
                        ),
                        *(
                            [
                                "--case",
                                "mission-healthy-001",
                                "--approval-fixture",
                                "PENDING",
                            ]
                            if command == "fresh"
                            else []
                        ),
                        *(
                            ["--decision", "ACCEPT"]
                            if command == "resume"
                            else []
                        ),
                    ]
                )
                self.assertEqual(args.command, command)

    def test_invalid_cli_is_one_json_error_line(self) -> None:
        module = _load_activate()
        diagnostic = StringIO()
        with redirect_stderr(diagnostic):
            exit_code = module.main(["fresh"])
        lines = diagnostic.getvalue().splitlines()
        self.assertEqual(exit_code, module.EXIT_USAGE)
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["error_class"], "invalid_arguments")


class AmbientEnvironmentTests(unittest.TestCase):
    def test_rejects_credential_proxy_model_cloud_and_docker_overrides(self) -> None:
        reject = _load_activate().reject_ambient_environment
        for name in (
            "OPENAI_API_KEY",
            "HTTPS_PROXY",
            "NO_PROXY",
            "AWS_SESSION_TOKEN",
            "GOOGLE_APPLICATION_CREDENTIALS",
            "GITHUB_TOKEN",
            "CF_HOME",
            "SSH_AUTH_SOCK",
            "DOCKER_HOST",
            "COMPOSE_FILE",
            "MODEL_NAME",
        ):
            with self.subTest(name=name):
                with self.assertRaisesRegex(Exception, name):
                    reject({name: "do-not-print-this-value"})

    def test_allows_only_non_sensitive_process_basics(self) -> None:
        _load_activate().reject_ambient_environment(
            {"PATH": "ignored", "SYSTEMROOT": "ignored", "TEMP": "ignored"}
        )

    def test_minimal_environment_keeps_windows_compose_plugin_discovery(self) -> None:
        module = _load_activate()
        with patch.dict(
            os.environ,
            {"PROGRAMFILES": r"C:\Program Files", "PROGRAMDATA": r"C:\ProgramData"},
        ):
            environment = module._minimal_environment()
        self.assertEqual(environment["PROGRAMFILES"], r"C:\Program Files")
        self.assertEqual(environment["PROGRAMDATA"], r"C:\ProgramData")


class ComposeModelValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = _load_activate()
        self.expected = self.module.ComposeExpectation(
            image="sha256:" + "a" * 64,
            project="a2a-deadbeef",
            state_volume="a2a-deadbeef-state",
            evidence_volume="a2a-deadbeef-evidence",
            network="a2a-deadbeef-network",
            mode="fresh",
            source_revision="1" * 40,
            run_id="mission-healthy-001",
            case_id="mission-healthy-001",
            decision="NONE",
        )

    def test_accepts_exact_two_service_hardened_internal_model(self) -> None:
        self.module.validate_compose_model(_rendered_model(), self.expected)

    def test_rejects_each_load_bearing_topology_or_security_mutation(self) -> None:
        mutations = {
            "host port": lambda model: model["services"]["worker"].update(
                {"ports": [{"target": 8081, "published": "8081"}]}
            ),
            "external network": lambda model: model["networks"]["sandbox"].update(
                {"internal": False}
            ),
            "writable root": lambda model: model["services"]["worker"].update(
                {"read_only": False}
            ),
            "root user": lambda model: model["services"]["orchestrator"].update(
                {"user": "0:0"}
            ),
            "capability": lambda model: model["services"]["worker"].update(
                {"cap_add": ["NET_ADMIN"]}
            ),
            "bind mount": lambda model: model["services"]["orchestrator"][
                "volumes"
            ].append({"type": "bind", "source": "/tmp", "target": "/host"}),
            "different image": lambda model: model["services"]["worker"].update(
                {"image": "sha256:" + "b" * 64}
            ),
            "build stanza": lambda model: model["services"]["worker"].update(
                {"build": {"context": "."}}
            ),
            "third service": lambda model: model["services"].update(
                {"helper": copy.deepcopy(model["services"]["worker"])}
            ),
            "unbounded pids": lambda model: model["services"]["worker"].pop(
                "pids_limit"
            ),
            "command substitution": lambda model: model["services"][
                "orchestrator"
            ]["command"].__setitem__(0, "sh"),
            "healthcheck removed": lambda model: model["services"]["worker"].pop(
                "healthcheck"
            ),
            "entrypoint override": lambda model: model["services"]["worker"].update(
                {"entrypoint": ["sh", "-c"]}
            ),
            "volumes_from escape": lambda model: model["services"]["orchestrator"].update(
                {"volumes_from": ["untrusted"]}
            ),
            "volume driver escape": lambda model: model["volumes"]["state"].update(
                {
                    "driver": "local",
                    "driver_opts": {"type": "none", "o": "bind", "device": "/"},
                }
            ),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                model = _rendered_model()
                mutate(model)
                with self.assertRaisesRegex(Exception, label.split()[0]):
                    self.module.validate_compose_model(model, self.expected)


class HandoffValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = _load_activate()
        self.handoff = {
            "handoff_version": "autogen-a2a-resume-handoff/v1",
            "state": "AWAITING_APPROVAL",
            "run_id": "mission-healthy-001",
            "source_revision": "1" * 40,
            "case_id": "mission-healthy-001",
            "case_digest": "2" * 64,
            "candidate_revision": "3" * 40,
            "artifact_digest": "4" * 64,
            "checkpoint_id": "checkpoint-1",
            "image_id": "sha256:" + "a" * 64,
            "project": "a2a-deadbeef",
            "state_volume": "a2a-deadbeef-state",
            "evidence_volume": "a2a-deadbeef-evidence",
        }

    def test_handoff_is_closed_and_bound_to_host_identity(self) -> None:
        self.module.validate_resume_handoff(
            self.handoff,
            source_revision="1" * 40,
            run_id="mission-healthy-001",
            image_id="sha256:" + "a" * 64,
            project="a2a-deadbeef",
            state_volume="a2a-deadbeef-state",
            evidence_volume="a2a-deadbeef-evidence",
        )

    def test_handoff_rejects_unknown_or_stale_identity(self) -> None:
        for field, value in (
            ("unknown", True),
            ("source_revision", "9" * 40),
            ("image_id", "sha256:" + "b" * 64),
            ("state", "COMPLETED"),
        ):
            with self.subTest(field=field):
                mutation = dict(self.handoff)
                mutation[field] = value
                with self.assertRaises(Exception):
                    self.module.validate_resume_handoff(
                        mutation,
                        source_revision="1" * 40,
                        run_id="mission-healthy-001",
                        image_id="sha256:" + "a" * 64,
                        project="a2a-deadbeef",
                        state_volume="a2a-deadbeef-state",
                        evidence_volume="a2a-deadbeef-evidence",
                    )

    def test_atomic_export_never_overwrites_changed_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "handoff.json"
            first = json.dumps(self.handoff, sort_keys=True).encode("utf-8") + b"\n"
            self.module.publish_file_once(target, first)
            self.module.publish_file_once(target, first)
            with self.assertRaisesRegex(Exception, "overwrite"):
                self.module.publish_file_once(target, b"changed\n")


class RuntimeStateValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = _load_runtime()
        self.pending = {
            "pending_version": "autogen-a2a-pending-state/v1",
            "state": "AWAITING_APPROVAL",
            "run_id": "mission-healthy-001",
            "source_revision": "1" * 40,
            "case_id": "mission-healthy-001",
            "case_digest": "2" * 64,
            "candidate_revision": "3" * 40,
            "analysis_invocations": 1,
            "artifact": {
                "artifact_digest": "4" * 64,
                "run_id": "mission-healthy-001",
                "source_revision": "1" * 40,
                "case_id": "mission-healthy-001",
                "case_digest": "2" * 64,
                "candidate_revision": "3" * 40,
            },
            "a2a": {
                "state": "completed",
                "task_id": "task-1",
                "context_id": "context-1",
                "artifact_id": "release-recommendation:mission-healthy-001",
                "authoritative_content": "data",
                "used_streaming_workflow": True,
            },
            "approval": {
                "checkpoint_id": "checkpoint-1",
                "request_id": "request-1",
                "request_info_count": 1,
                "workflow_name": "workflow-1",
            },
        }

    def _completed_retry_fixture(self):
        from interop_sandbox.contracts import canonical_json_bytes, canonical_sha256

        artifact = {
            "artifact_version": "release-recommendation/v1",
            "artifact_id": "release-recommendation:mission-healthy-001",
            "run_id": "mission-healthy-001",
            "case_id": "mission-healthy-001",
            "case_digest": "2" * 64,
            "source_revision": "1" * 40,
            "candidate_revision": "3" * 40,
            "a2a_task_id": "task-1",
            "a2a_context_id": "context-1",
            "recommendation": "ADVANCE_CANARY",
            "basis": ["slo.within_budget"],
            "resolved_contradictions": [],
            "unresolved_contradictions": [],
            "reconciliation_attempts": 0,
            "graph_state_sha256": "5" * 64,
            "packages": {
                "agent-framework-core": "1.16.0",
                "agent-framework-a2a": "1.0.0b260821",
                "autogen-agentchat": "0.7.5",
                "a2a-sdk": "1.1.2",
            },
        }
        artifact["artifact_digest"] = canonical_sha256(artifact)
        pending = copy.deepcopy(self.pending)
        pending["artifact"] = artifact
        decision = {
            "decision_version": "release-decision-state/v1",
            "run_id": artifact["run_id"],
            "source_revision": artifact["source_revision"],
            "case_id": artifact["case_id"],
            "case_digest": artifact["case_digest"],
            "candidate_revision": artifact["candidate_revision"],
            "artifact_digest": artifact["artifact_digest"],
            "decision": "ACCEPT",
            "approver": "human-release-owner",
            "decided_at": "2026-01-01T00:00:00Z",
            "expires_at": "2026-01-01T00:15:00Z",
        }
        runtime_final = {
            "runtime_evidence_version": "autogen-a2a-runtime-evidence/v1",
            "status": "DECISION_RECORDED",
            "run_id": pending["run_id"],
            "source_revision": pending["source_revision"],
            "case_id": pending["case_id"],
            "case_digest": pending["case_digest"],
            "candidate_revision": pending["candidate_revision"],
            "python": platform.python_version(),
            "packages": artifact["packages"],
            "analysis_invocations": 1,
            "a2a": pending["a2a"],
            "graphflow": {
                "state_sha256": artifact["graph_state_sha256"],
                "state_loaded_for_analysis": True,
                "analysis_rerun_on_approval_resume": False,
            },
            "approval": {
                "checkpoint_id": pending["approval"]["checkpoint_id"],
                "restored_checkpoint_id": pending["approval"]["checkpoint_id"],
                "initial_request_info_count": 1,
                "resume_request_info_count": 0,
                "decision_replayed": False,
            },
            "artifact": artifact,
            "decision": decision,
            "release_effect_executed": False,
        }
        return (
            pending,
            decision,
            self.module._canonical_json(runtime_final),
            canonical_json_bytes(decision),
        )

    def test_runtime_module_has_no_import_time_framework_dependency(self) -> None:
        source = RUNTIME_PATH.read_text(encoding="utf-8")
        before_main = source.split("def _run_fresh", 1)[0]
        for marker in ("agent_framework", "from a2a", "import httpx", "import uvicorn"):
            with self.subTest(marker=marker):
                self.assertNotIn(marker, before_main)

    def test_pending_state_is_closed_and_lineage_bound(self) -> None:
        value = self.module.validate_runtime_pending(
            self.pending,
            run_id="mission-healthy-001",
            source_revision="1" * 40,
            case_id="mission-healthy-001",
        )
        self.assertEqual(value["analysis_invocations"], 1)

    def test_pending_state_rejects_second_analysis_and_stale_artifact(self) -> None:
        for path, value in (
            (("analysis_invocations",), 2),
            (("artifact", "source_revision"), "9" * 40),
            (("a2a", "authoritative_content"), "text"),
            (("approval", "request_info_count"), 2),
        ):
            with self.subTest(path=path):
                mutation = copy.deepcopy(self.pending)
                target = mutation
                for part in path[:-1]:
                    target = target[part]
                target[path[-1]] = value
                with self.assertRaises(Exception):
                    self.module.validate_runtime_pending(
                        mutation,
                        run_id="mission-healthy-001",
                        source_revision="1" * 40,
                        case_id="mission-healthy-001",
                    )

    def test_a2a_input_required_request_is_not_misclassified_as_final_approval(self) -> None:
        proof = self.module.validate_noncompleted_terminal(
            a2a_state="input-required",
            artifact_object=None,
            remote_request_info_count=1,
        )
        self.assertEqual(proof["remote_request_info_count"], 1)
        self.assertEqual(proof["approval_request_info_count"], 0)

        with self.assertRaises(Exception):
            self.module.validate_noncompleted_terminal(
                a2a_state="input-required",
                artifact_object={"unauthorized": "artifact"},
                remote_request_info_count=1,
            )

    def test_existing_expired_decision_recovers_exact_final_without_timestamp_replay(self) -> None:
        from interop_sandbox.contracts import (
            validate_decision_replay,
            validate_recommendation_artifact,
            validate_release_decision,
        )

        pending, decision, runtime_bytes, decision_bytes = self._completed_retry_fixture()
        artifact = validate_recommendation_artifact(pending["artifact"])
        decided_at = datetime.fromisoformat(decision["decided_at"].replace("Z", "+00:00"))
        existing = validate_release_decision(decision, artifact=artifact, at_time=decided_at)
        changed = copy.deepcopy(decision)
        changed["decided_at"] = "2026-01-01T00:01:00Z"
        changed["expires_at"] = "2026-01-01T00:16:00Z"
        candidate = validate_release_decision(
            changed,
            artifact=artifact,
            at_time=datetime.fromisoformat("2026-01-01T00:01:00+00:00"),
        )
        with self.assertRaisesRegex(Exception, "different value"):
            validate_decision_replay(existing, candidate)

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            final_path = root / "runtime-final.json"
            decision_path = root / "decision.json"
            final_path.write_bytes(runtime_bytes)
            decision_path.write_bytes(decision_bytes)
            recovered = self.module.recover_existing_final(
                runtime_final_path=final_path,
                decision_path=decision_path,
                pending=pending,
                requested_decision="ACCEPT",
            )

        self.assertEqual(recovered, runtime_bytes)

    def test_existing_final_rejects_different_decision_or_tampering(self) -> None:
        pending, decision, runtime_bytes, decision_bytes = self._completed_retry_fixture()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            final_path = root / "runtime-final.json"
            decision_path = root / "decision.json"
            final_path.write_bytes(runtime_bytes)
            decision_path.write_bytes(decision_bytes)

            with self.assertRaisesRegex(Exception, "requested decision"):
                self.module.recover_existing_final(
                    runtime_final_path=final_path,
                    decision_path=decision_path,
                    pending=pending,
                    requested_decision="REJECT",
                )

            final_object = json.loads(runtime_bytes)
            for field, value in (
                ("analysis_invocations", 2),
                ("release_effect_executed", True),
            ):
                with self.subTest(field=field):
                    mutation = copy.deepcopy(final_object)
                    mutation[field] = value
                    final_path.write_bytes(self.module._canonical_json(mutation))
                    with self.assertRaises(Exception):
                        self.module.recover_existing_final(
                            runtime_final_path=final_path,
                            decision_path=decision_path,
                            pending=pending,
                            requested_decision="ACCEPT",
                        )
            final_path.write_bytes(runtime_bytes)
            changed_decision = copy.deepcopy(decision)
            changed_decision["decided_at"] = "2026-01-01T00:01:00Z"
            changed_decision["expires_at"] = "2026-01-01T00:16:00Z"
            decision_path.write_bytes(
                json.dumps(changed_decision, separators=(",", ":"), sort_keys=True).encode()
            )
            with self.assertRaises(Exception):
                self.module.recover_existing_final(
                    runtime_final_path=final_path,
                    decision_path=decision_path,
                    pending=pending,
                    requested_decision="ACCEPT",
                )


if __name__ == "__main__":
    unittest.main()
