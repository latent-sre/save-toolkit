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


def _rendered_model(
    image: str = "sha256:" + "a" * 64, *, mode: str = "fresh"
) -> dict[str, object]:
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
        "volumes": [{
            "type": "volume", "source": "state", "target": "/state",
            **({"read_only": True} if mode == "resume" else {}),
        }],
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


def _final_runtime_fixture(module):
    _load_runtime()
    from interop_sandbox.contracts import canonical_sha256

    case_object = json.loads(
        (SANDBOX_ROOT / "cases" / "mission-healthy-001.json").read_bytes()
    )
    case = module._validation_modules()[0].validate_case(case_object)
    terminal = {
        "state_version": "canary-analysis-state/v1",
        "run_id": "host-validator-run",
        "source_revision": "1" * 40,
        "case_id": case.case_id,
        "case_digest": canonical_sha256(case),
        "candidate_revision": case.candidate.candidate_revision,
        "a2a_task_id": "task-host-validator",
        "a2a_context_id": "context-host-validator",
        "initial_checkpoint_sha256": "6" * 64,
        "final_team_state": {"agents": []},
        "status": "COMPLETED",
        "recommendation": case.expected.recommendation,
        "basis": ["slo.within_budget"],
        "resolved_contradictions": [],
        "unresolved_contradictions": [],
        "reconciliation_attempts": 0,
        "route_evidence": ["join.synthesize", "synthesize.exit"],
        "node_evidence": [
            {"node_id": node_id, "call_count": count, "observed_input_fields": [[] for _ in range(count)]}
            for node_id, count in (
                ("ingest", 1), ("slo_analyzer", 1), ("deployment_analyzer", 1),
                ("dependency_analyzer", 1), ("join", 1), ("reconcile", 0),
                ("synthesize", 1), ("input_required", 0),
            )
        ],
        "terminal_reason": "synthesis complete",
    }
    artifact = {
        "artifact_version": "release-recommendation/v1",
        "artifact_id": "release-recommendation:host-validator-run",
        "run_id": terminal["run_id"],
        "case_id": case.case_id,
        "case_digest": terminal["case_digest"],
        "source_revision": terminal["source_revision"],
        "candidate_revision": terminal["candidate_revision"],
        "a2a_task_id": terminal["a2a_task_id"],
        "a2a_context_id": terminal["a2a_context_id"],
        "recommendation": case.expected.recommendation,
        "basis": terminal["basis"],
        "resolved_contradictions": [],
        "unresolved_contradictions": [],
        "reconciliation_attempts": 0,
        "graph_state_sha256": canonical_sha256(terminal),
        "packages": copy.deepcopy(module._PINNED_PACKAGES),
    }
    artifact["artifact_digest"] = canonical_sha256(artifact)
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
        "decided_at": "2026-08-30T00:00:00Z",
        "expires_at": "2026-08-30T00:15:00Z",
    }
    timeline = {
        "timeline_version": "a2a-event-timeline/v1",
        "events": [
            {"sequence": 0, "event_kind": "workflow_working", "task_id": None, "context_id": None, "a2a_state": None, "artifact_id": None},
            {"sequence": 1, "event_kind": "data_artifact", "task_id": artifact["a2a_task_id"], "context_id": artifact["a2a_context_id"], "a2a_state": None, "artifact_id": artifact["artifact_id"]},
            {"sequence": 2, "event_kind": "session", "task_id": artifact["a2a_task_id"], "context_id": artifact["a2a_context_id"], "a2a_state": "completed", "artifact_id": None},
        ],
    }
    root = {
        "runtime_evidence_version": "autogen-a2a-runtime-evidence/v1",
        "status": "DECISION_RECORDED",
        "run_id": artifact["run_id"],
        "source_revision": artifact["source_revision"],
        "case_id": artifact["case_id"],
        "case_digest": artifact["case_digest"],
        "candidate_revision": artifact["candidate_revision"],
        "python": "3.12.10",
        "packages": copy.deepcopy(module._PINNED_PACKAGES),
        "analysis_invocations": 1,
        "a2a": {"state": "completed", "task_id": artifact["a2a_task_id"], "context_id": artifact["a2a_context_id"], "artifact_id": artifact["artifact_id"], "authoritative_content": "data", "transport_mode": "maf-workflow", "used_streaming_workflow": True, "event_timeline": timeline},
        "graphflow": {"state_sha256": artifact["graph_state_sha256"], "initial_checkpoint_sha256": terminal["initial_checkpoint_sha256"], "terminal_state": terminal, "state_loaded_for_analysis": True, "analysis_rerun_on_approval_resume": False},
        "approval": {"checkpoint_id": "checkpoint-host", "restored_checkpoint_id": "checkpoint-host", "initial_request_info_count": 1, "resume_request_info_count": 0, "decision_replayed": False},
        "artifact": artifact,
        "decision": decision,
        "release_effect_executed": False,
    }
    return case_object, root


def _rebind_final_fixture(module, root):
    _load_runtime()
    from interop_sandbox.contracts import canonical_sha256

    terminal = root["graphflow"]["terminal_state"]
    root["graphflow"]["state_sha256"] = canonical_sha256(terminal)
    artifact = root["artifact"]
    artifact["graph_state_sha256"] = root["graphflow"]["state_sha256"]
    artifact["packages"] = copy.deepcopy(root["packages"])
    artifact["artifact_digest"] = canonical_sha256(
        {key: value for key, value in artifact.items() if key != "artifact_digest"}
    )
    root["decision"]["artifact_digest"] = artifact["artifact_digest"]


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

    def test_only_desktop_linux_local_endpoint_is_accepted(self) -> None:
        module = _load_activate()
        local = [
            {
                "Name": "desktop-linux",
                "Endpoints": {
                    "docker": {
                        "Host": "npipe:////./pipe/dockerDesktopLinuxEngine",
                        "SkipTLSVerify": False,
                    }
                },
            }
        ]
        module.validate_docker_context_record(local, "desktop-linux")
        for context, endpoint in (
            ("default", "npipe:////./pipe/dockerDesktopLinuxEngine"),
            ("desktop-linux", "tcp://127.0.0.1:2375"),
            ("desktop-linux", "ssh://builder@example.test"),
            ("desktop-linux", "http://127.0.0.1:2375"),
            ("desktop-linux", "unix://relative.sock"),
        ):
            with self.subTest(context=context, endpoint=endpoint):
                mutation = copy.deepcopy(local)
                mutation[0]["Name"] = context
                mutation[0]["Endpoints"]["docker"]["Host"] = endpoint
                with self.assertRaises(Exception):
                    module.validate_docker_context_record(mutation, context)

    def test_daemon_id_is_closed_without_exposing_endpoint(self) -> None:
        module = _load_activate()
        self.assertEqual(
            module.validate_daemon_id('"78e193b6-71a1-4a60-9ec0-16e94dd22f62"'),
            "78e193b6-71a1-4a60-9ec0-16e94dd22f62",
        )
        for value in ('""', '"bad id"', "null", '{"endpoint":"tcp://host"}'):
            with self.subTest(value=value):
                with self.assertRaises(Exception):
                    module.validate_daemon_id(value)


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

    def test_worker_state_is_writable_only_during_fresh(self) -> None:
        resume = self.module.ComposeExpectation(
            image=self.expected.image,
            project=self.expected.project,
            state_volume=self.expected.state_volume,
            evidence_volume=self.expected.evidence_volume,
            network=self.expected.network,
            mode="resume",
            source_revision=self.expected.source_revision,
            run_id=self.expected.run_id,
            case_id=self.expected.case_id,
            decision="ACCEPT",
        )
        model = _rendered_model(mode="resume")
        command = model["services"]["orchestrator"]["command"]
        command[command.index("--mode") + 1] = "resume"
        command[command.index("--decision") + 1] = "ACCEPT"
        self.module.validate_compose_model(model, resume)
        model["services"]["worker"]["volumes"][0]["read_only"] = False
        with self.assertRaisesRegex(Exception, "read-only"):
            self.module.validate_compose_model(model, resume)

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
            "daemon_id": "78e193b6-71a1-4a60-9ec0-16e94dd22f62",
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
            daemon_id="78e193b6-71a1-4a60-9ec0-16e94dd22f62",
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
                        daemon_id="78e193b6-71a1-4a60-9ec0-16e94dd22f62",
                    )

    def test_atomic_export_never_overwrites_changed_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "handoff.json"
            first = json.dumps(self.handoff, sort_keys=True).encode("utf-8") + b"\n"
            self.module.publish_file_once(target, first)
            self.module.publish_file_once(target, first)
            with self.assertRaisesRegex(Exception, "overwrite"):
                self.module.publish_file_once(target, b"changed\n")

    def test_private_receipt_rejects_changed_handoff_missing_and_link_substitution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary, patch.object(
            self.module, "_private_receipt_root", return_value=Path(temporary) / "receipts"
        ):
            receipt = self.module._create_or_load_receipt(self.handoff)
            self.module._load_trusted_receipt(self.handoff)
            changed = copy.deepcopy(self.handoff)
            changed["artifact_digest"] = "9" * 64
            with self.assertRaisesRegex(Exception, "receipt"):
                self.module._load_trusted_receipt(changed)

            receipt_path = self.module._receipt_path(self.handoff)
            twin = receipt_path.with_suffix(".hardlink")
            os.link(receipt_path, twin)
            with self.assertRaisesRegex(Exception, "link"):
                self.module._load_trusted_receipt(self.handoff)
            twin.unlink()
            receipt_path.unlink()
            with self.assertRaisesRegex(Exception, "receipt"):
                self.module._load_trusted_receipt(self.handoff)


class HostEvidenceValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = _load_activate()
        self.case_object, self.runtime = _final_runtime_fixture(self.module)

    def _validate(self, root):
        handoff = {
            "artifact_digest": root["artifact"]["artifact_digest"],
            "checkpoint_id": root["approval"]["checkpoint_id"],
        }
        return self.module._validate_runtime_final(
            self.module._canonical_json(root),
            run_id="host-validator-run",
            source_revision="1" * 40,
            case_id="mission-healthy-001",
            case_object=self.case_object,
            requested_decision="ACCEPT",
            handoff=handoff,
        )

    def test_full_host_validator_accepts_exact_nested_proofs(self) -> None:
        validated = self._validate(copy.deepcopy(self.runtime))
        self.assertEqual(validated["status"], "DECISION_RECORDED")

    def test_initial_graphflow_checkpoint_preimage_is_required_and_digest_bound(self) -> None:
        contracts, _runtime = self.module._validation_modules()
        runtime = copy.deepcopy(self.runtime)
        checkpoint = {
            "checkpoint_version": "canary-analysis-checkpoint/v1",
            "run_id": runtime["run_id"],
            "source_revision": runtime["source_revision"],
            "case_id": runtime["case_id"],
            "case_digest": runtime["case_digest"],
            "candidate_revision": runtime["candidate_revision"],
            "team_state": {"agents": {}},
        }
        digest = contracts.canonical_sha256(checkpoint)
        runtime["graphflow"]["terminal_state"]["initial_checkpoint_sha256"] = digest
        runtime["graphflow"]["initial_checkpoint_sha256"] = digest
        _rebind_final_fixture(self.module, runtime)
        handoff = {
            "artifact_digest": runtime["artifact"]["artifact_digest"],
            "checkpoint_id": runtime["approval"]["checkpoint_id"],
        }
        checkpoint_bytes = contracts.canonical_json_bytes(checkpoint)
        self.module._validate_graphflow_checkpoint(
            checkpoint_bytes, runtime_object=runtime, handoff=handoff
        )
        tampered = copy.deepcopy(checkpoint)
        tampered["team_state"] = {"agents": {"forged": True}}
        with self.assertRaisesRegex(Exception, "checkpoint"):
            self.module._validate_graphflow_checkpoint(
                contracts.canonical_json_bytes(tampered),
                runtime_object=runtime,
                handoff=handoff,
            )

    def test_full_host_validator_rejects_closed_contract_mutations(self) -> None:
        mutations = {
            "unknown field": lambda root: root.update({"unknown": True}),
            "missing field": lambda root: root.pop("approval"),
            "artifact digest": lambda root: root["artifact"].update({"artifact_digest": "0" * 64}),
            "expired decision": lambda root: root["decision"].update({"expires_at": root["decision"]["decided_at"]}),
            "forged packages": lambda root: root["packages"].update({"a2a-sdk": "9.9.9"}),
            "missing timeline": lambda root: root["a2a"].pop("event_timeline"),
            "forged call count": lambda root: root["graphflow"]["terminal_state"]["node_evidence"][0].update({"call_count": 2}),
            "malformed terminal": lambda root: root["graphflow"]["terminal_state"].pop("terminal_reason"),
        }
        for label, mutate in mutations.items():
            with self.subTest(label=label):
                root = copy.deepcopy(self.runtime)
                mutate(root)
                if label in {"forged packages", "forged call count", "malformed terminal"}:
                    _rebind_final_fixture(self.module, root)
                with self.assertRaises(Exception):
                    self._validate(root)

    def test_exit2_validator_binds_input_required_timeline_and_terminal(self) -> None:
        _load_runtime()
        from interop_sandbox.contracts import canonical_sha256, validate_case

        case_object = json.loads(
            (SANDBOX_ROOT / "cases" / "unresolved-contradiction-001.json").read_bytes()
        )
        case = validate_case(case_object)
        terminal = copy.deepcopy(self.runtime["graphflow"]["terminal_state"])
        terminal.update({
            "run_id": "terminal-validator-run",
            "case_id": case.case_id,
            "case_digest": canonical_sha256(case),
            "candidate_revision": case.candidate.candidate_revision,
            "a2a_task_id": "task-terminal-validator",
            "a2a_context_id": "context-terminal-validator",
            "status": "INPUT_REQUIRED",
            "recommendation": None,
            "reconciliation_attempts": 1,
            "unresolved_contradictions": ["dependency.canary_only_impact"],
            "route_evidence": ["join.reconcile", "reconcile.join", "join.input_required"],
            "node_evidence": [
                {"node_id": node_id, "call_count": count, "observed_input_fields": [[] for _ in range(count)]}
                for node_id, count in (
                    ("ingest", 1), ("slo_analyzer", 1), ("deployment_analyzer", 1),
                    ("dependency_analyzer", 1), ("join", 2), ("reconcile", 1),
                    ("synthesize", 0), ("input_required", 1),
                )
            ],
        })
        timeline = {
            "timeline_version": "a2a-event-timeline/v1",
            "events": [
                {"sequence": 0, "event_kind": "workflow_working", "task_id": None, "context_id": None, "a2a_state": None, "artifact_id": None},
                {"sequence": 1, "event_kind": "session", "task_id": terminal["a2a_task_id"], "context_id": terminal["a2a_context_id"], "a2a_state": "input-required", "artifact_id": None},
            ],
        }
        root = {
            "runtime_evidence_version": "autogen-a2a-runtime-evidence/v1",
            "status": "input-required", "run_id": terminal["run_id"],
            "source_revision": terminal["source_revision"], "case_id": case.case_id,
            "case_digest": terminal["case_digest"], "candidate_revision": terminal["candidate_revision"],
            "python": "3.12.10", "packages": copy.deepcopy(self.module._PINNED_PACKAGES),
            "analysis_invocations": 1, "remote_request_info_count": 1,
            "approval_request_info_count": 0, "artifact": None,
            "a2a": {"state": "input-required", "task_id": terminal["a2a_task_id"], "context_id": terminal["a2a_context_id"], "artifact_id": None, "transport_mode": "maf-workflow", "used_streaming_workflow": True, "event_timeline": timeline, "recovery": {"same_task": True}},
            "graphflow": {"state_sha256": canonical_sha256(terminal), "initial_checkpoint_sha256": terminal["initial_checkpoint_sha256"], "terminal_state": terminal},
            "release_effect_executed": False,
        }
        self.module._validate_runtime_terminal(
            self.module._canonical_json(root), run_id=root["run_id"],
            source_revision=root["source_revision"], case_id=case.case_id,
            case_object=case_object,
        )
        for label, mutate in (
            ("timeline", lambda value: value["a2a"]["event_timeline"]["events"].pop(0)),
            ("call count", lambda value: value["graphflow"]["terminal_state"]["node_evidence"][4].update({"call_count": 1})),
            ("terminal", lambda value: value["graphflow"]["terminal_state"].pop("terminal_reason")),
        ):
            with self.subTest(label=label):
                mutation = copy.deepcopy(root)
                mutate(mutation)
                if label != "timeline":
                    mutation["graphflow"]["state_sha256"] = canonical_sha256(
                        mutation["graphflow"]["terminal_state"]
                    )
                with self.assertRaises(Exception):
                    self.module._validate_runtime_terminal(
                        self.module._canonical_json(mutation), run_id=root["run_id"],
                        source_revision=root["source_revision"], case_id=case.case_id,
                        case_object=case_object,
                    )

    def test_exit2_validator_accepts_raw_same_task_cancellation_transport(self) -> None:
        _load_runtime()
        from interop_sandbox.contracts import canonical_sha256, validate_case

        case_object = json.loads(
            (SANDBOX_ROOT / "cases" / "slow-analysis-cancel-001.json").read_bytes()
        )
        case = validate_case(case_object)
        task_id = "task-cancel-validator"
        context_id = "context-cancel-validator"
        root = {
            "runtime_evidence_version": "autogen-a2a-runtime-evidence/v1",
            "status": "canceled", "run_id": "cancel-validator-run",
            "source_revision": "1" * 40, "case_id": case.case_id,
            "case_digest": canonical_sha256(case),
            "candidate_revision": case.candidate.candidate_revision,
            "python": "3.12.10", "packages": copy.deepcopy(self.module._PINNED_PACKAGES),
            "analysis_invocations": 1, "remote_request_info_count": 0,
            "approval_request_info_count": 0, "artifact": None,
            "a2a": {
                "state": "canceled", "task_id": task_id, "context_id": context_id,
                "artifact_id": None, "transport_mode": "raw-a2a-cancel",
                "used_streaming_workflow": False,
                "event_timeline": {
                    "timeline_version": "a2a-event-timeline/v1",
                    "events": [
                        {"sequence": 0, "event_kind": "task", "task_id": task_id, "context_id": context_id, "a2a_state": "working", "artifact_id": None},
                        {"sequence": 1, "event_kind": "task", "task_id": task_id, "context_id": context_id, "a2a_state": "canceled", "artifact_id": None},
                    ],
                },
                "recovery": {"same_task": True, "cancel_sent_task_id": task_id, "initial_task_id": task_id, "observed_task_ids": [task_id, task_id, task_id]},
            },
            "graphflow": {"state_sha256": None, "initial_checkpoint_sha256": None, "terminal_state": None},
            "release_effect_executed": False,
        }
        validated = self.module._validate_runtime_terminal(
            self.module._canonical_json(root), run_id=root["run_id"],
            source_revision=root["source_revision"], case_id=case.case_id,
            case_object=case_object,
        )
        self.assertEqual(validated["a2a"]["transport_mode"], "raw-a2a-cancel")

    def _create_stage(self, root: Path):
        contracts, _runtime = self.module._validation_modules()
        runtime = copy.deepcopy(self.runtime)
        image_id = "sha256:" + "a" * 64
        daemon_id = "78e193b6-71a1-4a60-9ec0-16e94dd22f62"
        identity = self.module._run_identity("host-validator-run", "1" * 40)
        model = _rendered_model(image_id, mode="resume")
        model["name"] = identity.project
        model["networks"]["sandbox"]["name"] = identity.network
        model["volumes"]["state"]["name"] = identity.state_volume
        model["volumes"]["evidence"]["name"] = identity.evidence_volume
        for service in model["services"].values():
            service["image"] = image_id
        command = model["services"]["orchestrator"]["command"]
        for flag, value in (
            ("--mode", "resume"), ("--source-revision", "1" * 40),
            ("--run-id", "host-validator-run"), ("--case", "mission-healthy-001"),
            ("--decision", "ACCEPT"),
        ):
            command[command.index(flag) + 1] = value
        case_bytes = (SANDBOX_ROOT / "cases" / "mission-healthy-001.json").read_bytes()
        checkpoint = {
            "checkpoint_version": "canary-analysis-checkpoint/v1",
            "run_id": runtime["run_id"], "source_revision": runtime["source_revision"],
            "case_id": runtime["case_id"], "case_digest": runtime["case_digest"],
            "candidate_revision": runtime["candidate_revision"], "team_state": {"agents": {}},
        }
        checkpoint_bytes = contracts.canonical_json_bytes(checkpoint)
        checkpoint_digest = contracts.canonical_sha256(checkpoint)
        runtime["graphflow"]["initial_checkpoint_sha256"] = checkpoint_digest
        runtime["graphflow"]["terminal_state"]["initial_checkpoint_sha256"] = checkpoint_digest
        _rebind_final_fixture(self.module, runtime)
        handoff = {
            "handoff_version": "autogen-a2a-resume-handoff/v1", "state": "AWAITING_APPROVAL",
            "run_id": runtime["run_id"], "source_revision": runtime["source_revision"],
            "case_id": runtime["case_id"], "case_digest": runtime["case_digest"],
            "candidate_revision": runtime["candidate_revision"],
            "artifact_digest": runtime["artifact"]["artifact_digest"],
            "checkpoint_id": runtime["approval"]["checkpoint_id"], "image_id": image_id,
            "project": identity.project, "state_volume": identity.state_volume,
            "evidence_volume": identity.evidence_volume, "daemon_id": daemon_id,
        }
        receipt = {
            "receipt_version": self.module._RECEIPT_VERSION, "receipt_nonce": "7" * 64,
            "handoff_sha256": __import__("hashlib").sha256(self.module._canonical_json(handoff)).hexdigest(),
            **{field: handoff[field] for field in (
                "run_id", "source_revision", "case_id", "artifact_digest", "checkpoint_id",
                "daemon_id", "image_id", "project", "state_volume", "evidence_volume",
            )},
        }
        values = {
            "case.json": case_bytes,
            "case-manifest.json": (SANDBOX_ROOT / "cases" / "manifest.json").read_bytes(),
            "compose-model.json": self.module._canonical_json(model),
            "runtime-final.json": self.module._canonical_json(runtime),
            "graphflow-state.json": contracts.canonical_json_bytes(runtime["graphflow"]["terminal_state"]),
            "graphflow-checkpoint.json": checkpoint_bytes,
            "artifact.json": self.module._canonical_json(runtime["artifact"]),
            "decision.json": self.module._canonical_json(runtime["decision"]),
            "environment.json": self.module._canonical_json({
                "evidence_version": "autogen-a2a-environment/v1", "source_revision": "1" * 40,
                "run_id": "host-validator-run", "case_id": "mission-healthy-001",
                "image_id": image_id, "daemon_id": daemon_id, "docker_context": "desktop-linux",
                "docker_server": {"Version": "29.7.0", "ApiVersion": "1.53", "Os": "linux", "Arch": "amd64"},
                "docker_compose": "5.0.0", "host_python": platform.python_version(),
                "runtime_python": "3.12.10", "packages": copy.deepcopy(self.module._PINNED_PACKAGES),
            }),
        }
        stage = root / ".final-bundle.pending"
        stage.mkdir()
        for name, data in values.items():
            (stage / name).write_bytes(data)
        manifest = {
            "stage_version": self.module._STAGE_MANIFEST_VERSION,
            "run_id": "host-validator-run", "source_revision": "1" * 40,
            "case_id": "mission-healthy-001", "image_id": image_id,
            "daemon_id": daemon_id,
            "artifact_digest": handoff["artifact_digest"], "checkpoint_id": handoff["checkpoint_id"],
            "handoff_sha256": __import__("hashlib").sha256(self.module._canonical_json(handoff)).hexdigest(),
            "receipt_sha256": __import__("hashlib").sha256(self.module._canonical_json(receipt)).hexdigest(),
            "files": {name: __import__("hashlib").sha256(data).hexdigest() for name, data in sorted(values.items())},
        }
        (stage / "stage-manifest.json").write_bytes(self.module._canonical_json(manifest))
        return stage, image_id, daemon_id, handoff, receipt

    def test_durable_stage_is_nested_validated_and_survives_target_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stage, image_id, daemon_id, handoff, receipt = self._create_stage(root)
            self.module.validate_staged_bundle(
                stage, run_id="host-validator-run", source_revision="1" * 40,
                case_id="mission-healthy-001", image_id=image_id,
                daemon_id=daemon_id, requested_decision="ACCEPT",
                handoff=handoff, receipt=receipt,
            )
            target = root / "final-bundle"
            target.mkdir()
            with self.assertRaisesRegex(Exception, "overwrite"):
                self.module._finalize_bundle(
                    stage, target, run_id="host-validator-run", revision="1" * 40,
                    case_id="mission-healthy-001", image_id=image_id,
                    daemon_id=daemon_id, requested_decision="ACCEPT",
                    handoff=handoff, receipt=receipt,
                )
            self.assertTrue(stage.is_dir())
            with self.assertRaises(Exception):
                self.module.validate_staged_bundle(
                    stage, run_id="host-validator-run", source_revision="1" * 40,
                    case_id="mission-healthy-001", image_id=image_id,
                    daemon_id=daemon_id, requested_decision="REJECT",
                    handoff=handoff, receipt=receipt,
                )
            (stage / "graphflow-checkpoint.json").unlink()
            with self.assertRaisesRegex(Exception, "missing|checkpoint|safely"):
                self.module.validate_staged_bundle(
                    stage, run_id="host-validator-run", source_revision="1" * 40,
                    case_id="mission-healthy-001", image_id=image_id,
                    daemon_id=daemon_id, requested_decision="ACCEPT",
                    handoff=handoff, receipt=receipt,
                )

    def test_trusted_receipt_rejects_a_self_consistent_forged_stage_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            stage, image_id, daemon_id, handoff, receipt = self._create_stage(
                Path(temporary)
            )
            forged_handoff = copy.deepcopy(handoff)
            forged_handoff["artifact_digest"] = "f" * 64
            forged_handoff["checkpoint_id"] = "forged-checkpoint"
            manifest_path = stage / "stage-manifest.json"
            manifest = json.loads(manifest_path.read_bytes())
            manifest["artifact_digest"] = forged_handoff["artifact_digest"]
            manifest["checkpoint_id"] = forged_handoff["checkpoint_id"]
            manifest["handoff_sha256"] = __import__("hashlib").sha256(
                self.module._canonical_json(forged_handoff)
            ).hexdigest()
            manifest_path.write_bytes(self.module._canonical_json(manifest))

            with self.assertRaisesRegex(Exception, "receipt"):
                self.module.validate_staged_bundle(
                    stage, run_id="host-validator-run", source_revision="1" * 40,
                    case_id="mission-healthy-001", image_id=image_id,
                    daemon_id=daemon_id, requested_decision="ACCEPT",
                    handoff=forged_handoff, receipt=receipt,
                )

    def test_stage_rejects_hardlink_and_symlink_substitution(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stage, image_id, daemon_id, handoff, receipt = self._create_stage(root)
            artifact_path = stage / "artifact.json"
            hardlink = root / "artifact-hardlink.json"
            os.link(artifact_path, hardlink)
            with self.assertRaisesRegex(Exception, "link"):
                self.module.validate_staged_bundle(
                    stage, run_id="host-validator-run", source_revision="1" * 40,
                    case_id="mission-healthy-001", image_id=image_id,
                    daemon_id=daemon_id, requested_decision="ACCEPT",
                    handoff=handoff, receipt=receipt,
                )
            hardlink.unlink()

            original = artifact_path.read_bytes()
            artifact_path.unlink()
            target = root / "artifact-target.json"
            target.write_bytes(original)
            try:
                artifact_path.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"host cannot create a test symlink: {exc}")
            with self.assertRaisesRegex(Exception, "link"):
                self.module.validate_staged_bundle(
                    stage, run_id="host-validator-run", source_revision="1" * 40,
                    case_id="mission-healthy-001", image_id=image_id,
                    daemon_id=daemon_id, requested_decision="ACCEPT",
                    handoff=handoff, receipt=receipt,
                )

    def test_windows_reparse_attribute_is_rejected_as_a_link(self) -> None:
        directory_mode = __import__("stat").S_IFDIR | 0o700
        details = type(
            "ReparseDirectory",
            (),
            {"st_mode": directory_mode, "st_file_attributes": 0x400},
        )()
        with patch.object(self.module.os, "lstat", return_value=details):
            with self.assertRaisesRegex(Exception, "reparse"):
                self.module._require_safe_directory(Path("unused"))

    def test_final_bundle_exact_replay_and_post_rename_crash_are_recoverable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stage, image_id, daemon_id, handoff, receipt = self._create_stage(root)
            target = root / "final-bundle"

            def rename_then_fail(source: Path, destination: Path) -> None:
                os.rename(source, destination)
                raise OSError("fault injected after final rename")

            with patch.object(
                self.module, "_durable_publish_directory", side_effect=rename_then_fail
            ):
                with self.assertRaisesRegex(OSError, "after final rename"):
                    self.module._finalize_bundle(
                        stage, target, run_id="host-validator-run", revision="1" * 40,
                        case_id="mission-healthy-001", image_id=image_id,
                        daemon_id=daemon_id, requested_decision="ACCEPT",
                        handoff=handoff, receipt=receipt,
                    )
            self.assertFalse(stage.exists())
            self.module._validate_final_bundle(
                target, run_id="host-validator-run", source_revision="1" * 40,
                case_id="mission-healthy-001", image_id=image_id,
                daemon_id=daemon_id, requested_decision="ACCEPT",
                handoff=handoff, receipt=receipt,
            )
            with self.assertRaises(Exception):
                self.module._validate_final_bundle(
                    target, run_id="host-validator-run", source_revision="1" * 40,
                    case_id="mission-healthy-001", image_id=image_id,
                    daemon_id=daemon_id, requested_decision="REJECT",
                    handoff=handoff, receipt=receipt,
                )
            (target / "decision.json").write_bytes(b"{}")
            with self.assertRaisesRegex(Exception, "digest"):
                self.module._validate_final_bundle(
                    target, run_id="host-validator-run", source_revision="1" * 40,
                    case_id="mission-healthy-001", image_id=image_id,
                    daemon_id=daemon_id, requested_decision="ACCEPT",
                    handoff=handoff, receipt=receipt,
                )

    def test_final_replay_refuses_any_surviving_run_resource(self) -> None:
        identity = self.module._run_identity("host-validator-run", "1" * 40)
        with patch.object(self.module, "_container_ids", return_value=("container",)):
            with self.assertRaisesRegex(Exception, "remain"):
                self.module._verify_full_cleanup("desktop-linux", identity)
        with patch.object(self.module, "_container_ids", return_value=()), patch.object(
            self.module, "_resource_exists", side_effect=lambda _context, kind, _name: kind == "volume"
        ):
            with self.assertRaisesRegex(Exception, "remain"):
                self.module._verify_full_cleanup("desktop-linux", identity)

    def test_resume_returns_success_from_only_an_exact_closed_final_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence_root = Path(temporary)
            run_root = evidence_root / "host-validator-run"
            run_root.mkdir()
            stage, image_id, daemon_id, handoff, receipt = self._create_stage(run_root)
            target = run_root / "final-bundle"
            self.module._finalize_bundle(
                stage, target, run_id="host-validator-run", revision="1" * 40,
                case_id="mission-healthy-001", image_id=image_id,
                daemon_id=daemon_id, requested_decision="ACCEPT",
                handoff=handoff, receipt=receipt,
            )
            with patch.object(self.module, "_resolve_image", return_value=image_id), patch.object(
                self.module, "_load_json_file", return_value=handoff
            ), patch.object(
                self.module, "validate_resume_handoff", return_value=handoff
            ), patch.object(
                self.module, "_load_trusted_receipt", return_value=receipt
            ), patch.object(
                self.module, "_render_compose", return_value=b"{}"
            ), patch.object(
                self.module, "_verify_full_cleanup"
            ) as cleanup:
                result = self.module._resume(
                    SANDBOX_ROOT, "desktop-linux", "1" * 40,
                    "host-validator-run", evidence_root, "ACCEPT", daemon_id,
                )
            self.assertEqual(result, 0)
            cleanup.assert_called_once()

            with patch.object(self.module, "_resolve_image", return_value=image_id), patch.object(
                self.module, "_load_json_file", return_value=handoff
            ), patch.object(
                self.module, "validate_resume_handoff", return_value=handoff
            ), patch.object(
                self.module, "_load_trusted_receipt", return_value=receipt
            ), patch.object(
                self.module, "_render_compose", return_value=b"{}"
            ), self.assertRaises(Exception):
                self.module._resume(
                    SANDBOX_ROOT, "desktop-linux", "1" * 40,
                    "host-validator-run", evidence_root, "REJECT", daemon_id,
                )


class RuntimeStateValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = _load_runtime()
        from interop_sandbox.contracts import canonical_sha256
        terminal_state = {
            "state_version": "canary-analysis-state/v1",
            "run_id": "mission-healthy-001",
            "source_revision": "1" * 40,
            "case_id": "mission-healthy-001",
            "case_digest": "2" * 64,
            "candidate_revision": "3" * 40,
            "a2a_task_id": "task-1",
            "a2a_context_id": "context-1",
            "initial_checkpoint_sha256": "6" * 64,
            "final_team_state": {"agents": []},
            "status": "COMPLETED",
            "recommendation": "ADVANCE_CANARY",
            "basis": ["slo.within_budget"],
            "resolved_contradictions": [],
            "unresolved_contradictions": [],
            "reconciliation_attempts": 0,
            "route_evidence": ["join.synthesize", "synthesize.exit"],
            "node_evidence": [
                {
                    "node_id": node_id,
                    "call_count": call_count,
                    "observed_input_fields": [[] for _ in range(call_count)],
                }
                for node_id, call_count in (
                    ("ingest", 1),
                    ("slo_analyzer", 1),
                    ("deployment_analyzer", 1),
                    ("dependency_analyzer", 1),
                    ("join", 1),
                    ("reconcile", 0),
                    ("synthesize", 1),
                    ("input_required", 0),
                )
            ],
            "terminal_reason": "synthesis complete",
        }
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
            "graph_state_sha256": canonical_sha256(terminal_state),
            "packages": {
                "agent-framework-core": "1.16.0",
                "agent-framework-a2a": "1.0.0b260821",
                "autogen-agentchat": "0.7.5",
                "a2a-sdk": "1.1.2",
            },
        }
        artifact["artifact_digest"] = canonical_sha256(artifact)
        timeline = {
            "timeline_version": "a2a-event-timeline/v1",
            "events": [
                {"sequence": 0, "event_kind": "workflow_working", "task_id": None, "context_id": None, "a2a_state": None, "artifact_id": None},
                {"sequence": 1, "event_kind": "data_artifact", "task_id": "task-1", "context_id": "context-1", "a2a_state": None, "artifact_id": artifact["artifact_id"]},
                {"sequence": 2, "event_kind": "session", "task_id": "task-1", "context_id": "context-1", "a2a_state": "completed", "artifact_id": None},
            ],
        }
        self.pending = {
            "pending_version": "autogen-a2a-pending-state/v1",
            "state": "AWAITING_APPROVAL",
            "run_id": "mission-healthy-001",
            "source_revision": "1" * 40,
            "case_id": "mission-healthy-001",
            "case_digest": "2" * 64,
            "candidate_revision": "3" * 40,
            "analysis_invocations": 1,
            "artifact": artifact,
            "a2a": {
                "state": "completed",
                "task_id": "task-1",
                "context_id": "context-1",
                "artifact_id": "release-recommendation:mission-healthy-001",
                "authoritative_content": "data",
                "transport_mode": "maf-workflow",
                "used_streaming_workflow": True,
                "event_timeline": timeline,
            },
            "graphflow": {
                "state_sha256": artifact["graph_state_sha256"],
                "initial_checkpoint_sha256": terminal_state["initial_checkpoint_sha256"],
                "terminal_state": terminal_state,
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

        pending = copy.deepcopy(self.pending)
        artifact = pending["artifact"]
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
                "initial_checkpoint_sha256": pending["graphflow"]["initial_checkpoint_sha256"],
                "terminal_state": pending["graphflow"]["terminal_state"],
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

    def test_host_direct_runtime_invocations_refuse_before_any_effect(self) -> None:
        if (
            Path("/.dockerenv").is_file()
            and hasattr(os, "getuid")
            and os.getuid() == 65532
            and os.environ.get("AUTOGEN_A2A_RUNTIME_MARKER")
            == "autogen-a2a-sandbox-container/v1"
        ):
            self.skipTest("host-direct refusal is verified only outside the valid image boundary")
        commands = (
            [
                "worker",
                "--state-directory",
                os.getcwd(),
                "--agent-url",
                "http://worker:8081/a2a/jsonrpc",
                "--host",
                "0.0.0.0",
                "--port",
                "8081",
            ],
            ["healthcheck", "--url", "http://127.0.0.1:8081/readyz"],
            [
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
                os.getcwd(),
                "--evidence-directory",
                os.getcwd(),
                "--cases-directory",
                str(SANDBOX_ROOT / "cases"),
            ],
        )
        for command in commands:
            with self.subTest(command=command[0]):
                diagnostic = StringIO()
                with redirect_stderr(diagnostic):
                    exit_code = self.module.main(command)
                self.assertEqual(exit_code, 70)
                self.assertIn("container runtime", diagnostic.getvalue())

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

    def test_decision_only_reconstructs_exact_runtime_final(self) -> None:
        pending, _decision_object, runtime_bytes, decision_bytes = (
            self._completed_retry_fixture()
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            decision_path = root / "decision.json"
            decision_path.write_bytes(decision_bytes)
            artifact, decision = self.module._validated_persisted_decision(
                decision_path=decision_path,
                pending=pending,
                requested_decision="ACCEPT",
            )
            reconstructed = self.module._canonical_json(
                self.module._build_runtime_final(
                    pending=pending,
                    artifact=artifact,
                    decision=decision,
                    decision_replayed=False,
                )
            )
            final_path = root / "runtime-final.json"
            final_path.write_bytes(runtime_bytes)
            decision_path.unlink()
            with self.assertRaisesRegex(Exception, "without its exact decision"):
                self.module.recover_existing_final(
                    runtime_final_path=final_path,
                    decision_path=decision_path,
                    pending=pending,
                    requested_decision="ACCEPT",
                )

        self.assertEqual(reconstructed, runtime_bytes)


if __name__ == "__main__":
    unittest.main()
