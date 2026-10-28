"""Independent verifier contracts with fakes only at SWE-bench and Docker boundaries."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest
from swebench_adapter import verifier

IMAGE = "sha256:" + "a" * 64
ENGINE = "offline-engine"
ENDPOINT = "unix:///var/run/docker.sock"
INSTANCE = "org__project-123"
RUN_ID = "wp08-unique-run"
CONTAINER = f"sweb.eval.{INSTANCE}.{RUN_ID}"
PATCH = "diff --git a/a.py b/a.py\n--- a/a.py\n+++ b/a.py\n@@ -1 +1 @@\n-bad\n+good\n"


def task():
    return {
        "instance_id": INSTANCE,
        "base_commit": "b" * 40,
        "repo": "org/project",
        "version": "1.0",
        "image": "registry.example/project@sha256:" + "c" * 64,
        "eval_script": "echo verifier tests",
        "log_parser": "pytest",
        "eval_type": "pass_and_fail",
        "FAIL_TO_PASS": ["tests/test_bug.py::test_bug"],
        "PASS_TO_PASS": ["tests/test_existing.py::test_existing"],
        "patch": "PRIVATE GOLD PATCH",
        "test_patch": "PRIVATE TEST PATCH",
        "hints_text": "PRIVATE HINTS",
    }


def report():
    return {
        INSTANCE: {
            "patch_is_None": False,
            "patch_exists": True,
            "patch_successfully_applied": True,
            "resolved": True,
            "infra_failure": False,
            "tests_status": {
                field: {"success": list(task()[field]), "failure": []} for field in ("FAIL_TO_PASS", "PASS_TO_PASS")
            },
        }
    }


class NotFound(Exception):
    pass


class FakeContainer:
    id = "1" * 64
    name = CONTAINER

    def __init__(self, client):
        self.client = client

    def start(self):
        self.client.started = True

    def kill(self):
        self.client.killed = True

    def remove(self, **options):
        self.client.removals.append(options)
        if self.client.remove_error:
            raise RuntimeError("Docker removal failed")
        self.client.present = False


class FakeClient:
    def __init__(self):
        self.present = False
        self.remove_error = False
        self.lookup_error = False
        self.create_error = False
        self.options = []
        self.removals = []
        self.image_lookups = []
        self.image_id = IMAGE
        self.closed = False
        self.started = False
        self.engine_id = ENGINE
        self.head = "b" * 40
        self.tracked_clean = True
        self.index_clean = True
        self.base_probes = []
        self.candidate_executed = False
        self.killed = False
        self.size = 0
        self.executions = {}
        self.api = SimpleNamespace(
            containers=self.list_containers,
            exec_create=self.exec_create,
            exec_start=self.exec_start,
            exec_inspect=self.exec_inspect,
        )
        self.containers = SimpleNamespace(get=self.get, create=self.create)
        self.images = SimpleNamespace(get=self.image)

    def get(self, name):
        assert name == CONTAINER
        if self.lookup_error:
            raise RuntimeError("Docker unavailable")
        if not self.present:
            raise NotFound
        return FakeContainer(self)

    def image(self, value):
        self.image_lookups.append(value)
        return SimpleNamespace(id=self.image_id)

    def create(self, **options):
        self.options.append(options)
        self.present = True
        if self.create_error:
            raise RuntimeError("create failed after resource allocation")
        return FakeContainer(self)

    def close(self):
        self.closed = True

    def info(self):
        return {"ID": self.engine_id}

    def list_containers(self, **kwargs):
        assert kwargs == {"all": True, "filters": {"id": FakeContainer.id}, "size": True}
        return [{"Id": FakeContainer.id, "SizeRw": self.size}]

    def exec_create(self, container_id, cmd, **options):
        self.base_probes.append((cmd, options))
        if "rev-parse" in cmd:
            output, code = (self.head + "\n").encode(), 0
        else:
            clean = self.index_clean if "--cached" in cmd else self.tracked_clean
            output, code = b"", 0 if clean else 1
        key = str(len(self.executions))
        self.executions[key] = (output, code)
        return {"Id": key}

    def exec_start(self, exec_id, **options):
        return iter([self.executions[exec_id][0]])

    def exec_inspect(self, exec_id):
        return {"Running": False, "ExitCode": self.executions[exec_id][1]}


class FakeHarness:
    """The external run_instance API writes the same files as the pinned wheel."""

    def __init__(self, client):
        self.client = client
        self.calls = []
        self.raw_report = report()
        self.error = None
        self.no_result = False
        self.no_report = False
        self.marker = ""
        self.expected_patch = PATCH
        self.CONTAINER_USER = "root"
        self.APPLY_PATCH_FAIL = ">>>>> Patch Apply Failed"
        self.LOG_REPORT = "report.json"
        self.LOG_INSTANCE = "run_instance.log"
        self.RUN_EVALUATION_LOG_DIR = Path("unused-original-logs")
        self.docker = SimpleNamespace(errors=SimpleNamespace(NotFound=NotFound))
        self.create_container = mock.Mock(side_effect=AssertionError("unrestricted upstream factory called"))
        self.exec_run_with_timeout = mock.Mock()

    def _docker_client(self):
        return self.client

    def make_test_spec(self, row):
        assert row["version"] == "1.0"
        return SimpleNamespace(**row)

    def run_instance(self, spec, prediction, client, run_id, **kwargs):
        self.calls.append((spec, prediction, run_id, kwargs))
        assert prediction == {"model_name_or_path": "wp08", "model_patch": self.expected_patch, "instance_id": INSTANCE}
        container = self.create_container(spec, client, run_id, SimpleNamespace(info=lambda _: None))
        container.start()
        client.candidate_executed = True
        log = self.RUN_EVALUATION_LOG_DIR / run_id / "wp08" / INSTANCE
        log.mkdir(parents=True, exist_ok=True)
        (log / self.LOG_INSTANCE).write_bytes(self.marker.encode("utf-8"))
        if self.error:
            raise self.error
        if self.no_result:
            return None
        if not self.no_report:
            (log / self.LOG_REPORT).write_text(json.dumps(self.raw_report), encoding="utf-8")
        return INSTANCE, copy.deepcopy(self.raw_report)


@pytest.fixture
def boundary(tmp_path, monkeypatch):
    task_path = tmp_path / "task.json"
    task_path.write_text(json.dumps(task()), encoding="utf-8")
    patch_path = tmp_path / "candidate.patch"
    patch_path.write_text(PATCH, encoding="utf-8", newline="\n")
    output = tmp_path / "output"
    client = FakeClient()
    harness = FakeHarness(client)
    monkeypatch.setattr(verifier.metadata, "version", lambda name: "5.0.2")
    monkeypatch.setattr(verifier.importlib, "import_module", lambda name: harness)
    monkeypatch.setenv("DOCKER_HOST", ENDPOINT)
    return SimpleNamespace(task_path=task_path, patch_path=patch_path, output=output, client=client, harness=harness)


def run(boundary):
    return verifier.verify(
        boundary.task_path, boundary.patch_path, boundary.output, RUN_ID, IMAGE, engine_id=ENGINE, docker_host=ENDPOINT
    )


def test_command_launches_this_adapter_with_project_interpreter(tmp_path):
    command = verifier.verifier_command(tmp_path / "task", tmp_path / "patch", tmp_path / "output", RUN_ID, IMAGE)
    assert command == [
        sys.executable,
        str(Path(verifier.__file__).resolve()),
        "--task",
        str(tmp_path / "task"),
        "--patch",
        str(tmp_path / "patch"),
        "--output",
        str(tmp_path / "output"),
        "--run-id",
        RUN_ID,
        "--image-digest",
        IMAGE,
        "--storage-quota",
    ]


def test_pass_receipt_binds_identity_and_factory_removes_privileges(boundary):
    original_factory = boundary.harness.create_container
    receipt = run(boundary)
    assert receipt == json.loads((boundary.output / "verifier-receipt.json").read_text())
    assert json.loads((boundary.output / "verifier-report.json").read_text()) == report()
    assert receipt["instance_id"] == INSTANCE
    assert receipt["base_commit"] == task()["base_commit"]
    assert receipt["patch_sha256"] == hashlib.sha256(PATCH.encode()).hexdigest()
    assert receipt["swebench_version"] == "5.0.2"
    assert receipt["verifier_image_digest"] == IMAGE
    assert receipt["command"] == verifier.verifier_command(
        boundary.task_path, boundary.patch_path, boundary.output, RUN_ID, IMAGE, engine_id=ENGINE, docker_host=ENDPOINT
    )
    assert receipt["report_path"] == "verifier-report.json"
    assert receipt["evaluated_at"].endswith("+00:00")
    assert (receipt["outcome"], receipt["exit_status"], receipt["reason"]) == ("PASS", 0, None)
    assert receipt["cleanup"] == [{"name": CONTAINER, "present": False, "removed": True}]
    assert boundary.client.closed
    assert boundary.harness.create_container is original_factory
    assert Path("unused-original-logs") == boundary.harness.RUN_EVALUATION_LOG_DIR
    assert boundary.client.image_lookups == [IMAGE]
    assert boundary.client.options == [
        {
            "image": IMAGE,
            "name": CONTAINER,
            "user": "root",
            "detach": True,
            "command": "tail -f /dev/null",
            "cap_drop": ["ALL"],
            "security_opt": ["no-new-privileges:true"],
            "nano_cpus": 2_000_000_000,
            "mem_limit": "2g",
            "memswap_limit": "2g",
            "pids_limit": 256,
            "network_disabled": True,
            "privileged": False,
            "storage_opt": {"size": "10G"},
        }
    ]
    spec, _, _, options = boundary.harness.calls[0]
    assert spec.image == IMAGE
    assert options == {"timeout": 2700, "rewrite_reports": False, "skip_patch": False, "task_repo": None}


@pytest.mark.parametrize("field", ["FAIL_TO_PASS", "PASS_TO_PASS"])
def test_complete_failed_expected_tests_are_fail(boundary, field):
    result = boundary.harness.raw_report[INSTANCE]
    result["resolved"] = False
    result["tests_status"][field] = {"success": [], "failure": task()[field]}
    receipt = run(boundary)
    assert (receipt["outcome"], receipt["exit_status"]) == ("FAIL", 1)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda row: row.pop("tests_status"),
        lambda row: row["tests_status"].pop("PASS_TO_PASS"),
        lambda row: row["tests_status"]["FAIL_TO_PASS"].update(success=[]),
        lambda row: row["tests_status"]["PASS_TO_PASS"].update(success=["unexpected"]),
        lambda row: row["tests_status"]["FAIL_TO_PASS"].update(success=task()["FAIL_TO_PASS"] * 2),
        lambda row: row["tests_status"]["FAIL_TO_PASS"].update(failure=task()["FAIL_TO_PASS"]),
        lambda row: row["tests_status"]["FAIL_TO_PASS"].update(success="not a list"),
        lambda row: row.update(resolved=False),
        lambda row: row.update(resolved=1),
        lambda row: row.update(infra_failure="false"),
        lambda row: row.pop("infra_failure"),
        lambda row: row.update(patch_is_None=True),
        lambda row: row.update(patch_exists=False),
        lambda row: row.update(patch_successfully_applied=False),
        lambda row: row.update(infra_failure=True, infra_failure_reason="environment unavailable"),
    ],
)
def test_missing_inconsistent_or_infrastructure_report_is_inconclusive(boundary, mutation):
    mutation(boundary.harness.raw_report[INSTANCE])
    receipt = run(boundary)
    assert (receipt["outcome"], receipt["exit_status"]) == ("INCONCLUSIVE", 2)
    assert receipt["reason"]


def test_report_for_another_instance_is_inconclusive(boundary):
    boundary.harness.raw_report = {"other-instance": report()[INSTANCE]}
    assert run(boundary)["outcome"] == "INCONCLUSIVE"


def test_empty_pass_to_pass_list_is_valid_and_still_recorded(boundary):
    row = task()
    row["PASS_TO_PASS"] = []
    boundary.task_path.write_text(json.dumps(row))
    boundary.harness.raw_report[INSTANCE]["tests_status"]["PASS_TO_PASS"] = {"success": [], "failure": []}
    assert run(boundary)["outcome"] == "PASS"


@pytest.mark.parametrize("text", ["", " \n\t"])
def test_empty_patch_fails_without_evaluation(boundary, text):
    boundary.patch_path.write_text(text)
    receipt = run(boundary)
    assert (receipt["outcome"], receipt["exit_status"]) == ("FAIL", 1)
    assert not boundary.harness.calls
    assert json.loads((boundary.output / "verifier-report.json").read_text()) == {}


@pytest.mark.parametrize(
    "marker,outcome",
    [
        (">>>>> Patch Apply Failed:\nexplicit upstream marker", "FAIL"),
        ("2026-10-24 12:00:00,100 - INFO - >>>>> Patch Apply Failed:\nupstream output", "FAIL"),
        ("Failed to apply patch to container: git apply", "INCONCLUSIVE"),
        ("Docker API Error; patch apply failed", "INCONCLUSIVE"),
        ("arbitrary exception mentions >>>>> Patch Apply Failed: inside its message", "INCONCLUSIVE"),
        ("", "INCONCLUSIVE"),
    ],
)
@pytest.mark.parametrize("line_ending", ["\n", "\r\n"])
def test_no_result_requires_explicit_patch_failure_marker(boundary, marker, outcome, line_ending):
    boundary.harness.no_result = True
    boundary.harness.marker = marker.replace("\n", line_ending)
    receipt = run(boundary)
    assert receipt["outcome"] == outcome
    assert receipt["cleanup"] == [{"name": CONTAINER, "present": False, "removed": True}]


@pytest.mark.parametrize("error", [RuntimeError("harness infrastructure failed"), KeyboardInterrupt()])
def test_cleanup_and_receipt_written_on_harness_exception(boundary, error):
    boundary.harness.error = error
    receipt = run(boundary)
    assert receipt["outcome"] == "INCONCLUSIVE"
    assert receipt["cleanup"] == [{"name": CONTAINER, "present": False, "removed": True}]
    assert not boundary.client.present
    assert (boundary.output / "verifier-receipt.json").is_file()


def test_cleanup_removes_container_when_creation_raises_after_allocation(boundary):
    boundary.client.create_error = True
    receipt = run(boundary)
    assert receipt["outcome"] == "INCONCLUSIVE"
    assert receipt["cleanup"] == [{"name": CONTAINER, "present": False, "removed": True}]


@pytest.mark.parametrize("outcome", ["PASS", "FAIL"])
def test_cleanup_failure_preserves_supported_assessment(boundary, outcome):
    if outcome == "FAIL":
        row = boundary.harness.raw_report[INSTANCE]
        row["resolved"] = False
        row["tests_status"]["FAIL_TO_PASS"] = {"success": [], "failure": task()["FAIL_TO_PASS"]}
    boundary.client.remove_error = True
    receipt = run(boundary)
    assert receipt["outcome"] == outcome
    assert receipt["after_assessment"] == "verifier container cleanup is unresolved"
    assert receipt["cleanup"] == [{"name": CONTAINER, "present": True, "removed": False}]


def test_unknown_cleanup_state_preserves_supported_pass(boundary):
    original = boundary.harness.run_instance

    def lose_docker(*args, **kwargs):
        result = original(*args, **kwargs)
        boundary.client.lookup_error = True
        return result

    boundary.harness.run_instance = lose_docker
    receipt = run(boundary)
    assert receipt["outcome"] == "PASS"
    assert receipt["after_assessment"] == "verifier container cleanup is unresolved"
    assert receipt["cleanup"] == [{"name": CONTAINER, "present": None, "removed": False}]


def test_preexisting_named_container_is_never_removed_or_reused(boundary):
    boundary.client.present = True
    receipt = run(boundary)
    assert receipt["outcome"] == "INCONCLUSIVE"
    assert not boundary.harness.calls
    assert not boundary.client.removals
    assert receipt["cleanup"] == [{"name": CONTAINER, "present": True, "removed": False}]


def test_missing_fresh_report_is_inconclusive(boundary):
    boundary.harness.no_report = True
    assert run(boundary)["outcome"] == "INCONCLUSIVE"


def test_stale_harness_run_is_never_reused(boundary):
    stale = boundary.output / "harness-logs" / RUN_ID / "wp08" / INSTANCE / "report.json"
    stale.parent.mkdir(parents=True)
    stale.write_text(json.dumps(report()))
    receipt = run(boundary)
    assert receipt["outcome"] == "INCONCLUSIVE"
    assert not boundary.harness.calls
    assert json.loads((boundary.output / "verifier-report.json").read_text()) == {}


def test_existing_adapter_output_is_refused(boundary):
    run(boundary)
    before = (boundary.output / "verifier-receipt.json").read_bytes()
    with pytest.raises(ValueError, match="already contains verifier evidence"):
        run(boundary)
    assert len(boundary.harness.calls) == 1
    assert (boundary.output / "verifier-receipt.json").read_bytes() == before


@pytest.mark.parametrize("version", ["5.0.1", "5.0.2.dev1", "6.0.0"])
def test_version_is_enforced_before_package_import_or_evaluation(boundary, monkeypatch, version):
    monkeypatch.setattr(verifier.metadata, "version", lambda name: version)
    with mock.patch.object(verifier.importlib, "import_module") as load:
        receipt = run(boundary)
    assert receipt["outcome"] == "INCONCLUSIVE"
    assert receipt["swebench_version"] == version
    load.assert_not_called()
    assert not boundary.harness.calls


def test_missing_dependency_writes_inconclusive_receipt(boundary, monkeypatch):
    def absent(name):
        raise verifier.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(verifier.metadata, "version", absent)
    receipt = run(boundary)
    assert receipt["outcome"] == "INCONCLUSIVE"
    assert receipt["swebench_version"] is None
    assert not boundary.harness.calls


def test_actual_image_id_must_match_pinned_digest(boundary):
    boundary.client.image_id = "sha256:" + "d" * 64
    receipt = run(boundary)
    assert receipt["outcome"] == "INCONCLUSIVE"
    assert not boundary.client.options


@pytest.mark.parametrize(
    "field,value",
    [
        ("base_commit", "main"),
        ("instance_id", "../escape"),
        ("version", ""),
        ("FAIL_TO_PASS", []),
        ("FAIL_TO_PASS", ["duplicate", "duplicate"]),
        ("PASS_TO_PASS", "[]"),
        ("image_assets", {"patch": [{"url": "https://example.com/unpinned"}]}),
    ],
)
def test_invalid_task_or_network_asset_refused_before_harness(boundary, field, value):
    row = task()
    row[field] = value
    boundary.task_path.write_text(json.dumps(row))
    assert run(boundary)["outcome"] == "INCONCLUSIVE"
    assert not boundary.harness.calls


def test_cli_exit_matches_written_receipt(boundary):
    command = verifier.verifier_command(
        boundary.task_path, boundary.patch_path, boundary.output, RUN_ID, IMAGE, engine_id=ENGINE, docker_host=ENDPOINT
    )
    assert verifier.main(command[2:]) == 0
    assert json.loads((boundary.output / "verifier-receipt.json").read_text())["exit_status"] == 0


@pytest.mark.parametrize("outcome", ["PASS", "FAIL", "INCONCLUSIVE"])
def test_baseline_executes_independent_tests_instead_of_empty_shortcut(boundary, outcome):
    boundary.patch_path.write_text("")
    boundary.harness.expected_patch = ""
    result = boundary.harness.raw_report[INSTANCE]
    if outcome == "FAIL":
        result["resolved"] = False
        result["tests_status"]["FAIL_TO_PASS"] = {"success": [], "failure": task()["FAIL_TO_PASS"]}
    elif outcome == "INCONCLUSIVE":
        result["infra_failure"] = True
    receipt = verifier.verify(
        boundary.task_path,
        boundary.patch_path,
        boundary.output,
        RUN_ID,
        IMAGE,
        baseline=True,
        engine_id=ENGINE,
        docker_host=ENDPOINT,
    )
    assert receipt["outcome"] == outcome
    assert boundary.harness.calls[0][3]["skip_patch"] is True
    assert receipt["command"][-1] == "--baseline"
    assert receipt["baseline"] is True


def test_verifier_engine_is_attested_before_container_lookup_or_creation(boundary):
    boundary.client.engine_id = "wrong-engine"
    receipt = run(boundary)
    assert receipt["outcome"] == "INCONCLUSIVE"
    assert not boundary.client.options and not boundary.client.candidate_executed


@pytest.mark.parametrize("field,value", [("head", "f" * 40), ("tracked_clean", False), ("index_clean", False)])
def test_wrong_or_dirty_image_baseline_is_refused_before_candidate(boundary, field, value):
    setattr(boundary.client, field, value)
    receipt = run(boundary)
    assert receipt["outcome"] == "INCONCLUSIVE"
    assert not boundary.client.candidate_executed
    assert receipt["cleanup"][0]["present"] is False


def test_base_receipt_records_observed_head_and_clean_source_state(boundary):
    receipt = run(boundary)
    assert receipt["observed_base_commit"] == "b" * 40
    assert receipt["initial_state"] == {
        "head": "b" * 40,
        "tracked_clean": True,
        "index_clean": True,
        "replace_objects_disabled": True,
        "untracked_policy": "preserved",
    }
    assert boundary.client.base_probes
    assert all(options["environment"]["GIT_NO_REPLACE_OBJECTS"] == "1" for _, options in boundary.client.base_probes)


def test_verifier_interrupt_is_retained_after_cleanup(boundary):
    boundary.harness.error = KeyboardInterrupt()
    receipt = run(boundary)
    assert receipt["outcome"] == "INCONCLUSIVE" and receipt["interrupted"] is True
    assert receipt["cleanup"][0]["present"] is False


def test_verifier_storage_quota_option_reaches_factory(boundary):
    receipt = verifier.verify(
        boundary.task_path,
        boundary.patch_path,
        boundary.output,
        RUN_ID,
        IMAGE,
        engine_id=ENGINE,
        docker_host=ENDPOINT,
        storage_quota=True,
    )
    assert receipt["outcome"] == "PASS"
    assert boundary.client.options[0]["storage_opt"] == {"size": "10G"}


@pytest.mark.parametrize("size", [None, 10_737_418_241])
def test_verifier_storage_or_monitor_limit_is_inconclusive_before_candidate(boundary, size):
    boundary.client.size = size
    receipt = run(boundary)
    assert receipt["outcome"] == "INCONCLUSIVE"
    assert boundary.client.killed and not boundary.client.candidate_executed
    assert receipt["cleanup"][0]["present"] is False


@pytest.mark.parametrize("quota", [False, None, 1, "true"])
def test_verifier_rejects_missing_hard_quota_before_execution(boundary, quota):
    with pytest.raises(ValueError, match="hard storage quota"):
        verifier.verify(
            boundary.task_path,
            boundary.patch_path,
            boundary.output,
            RUN_ID,
            IMAGE,
            storage_quota=quota,
            engine_id=ENGINE,
            docker_host=ENDPOINT,
        )
    assert boundary.client.options == []
    assert not boundary.client.candidate_executed
    assert not boundary.output.exists()


@pytest.mark.parametrize("quota", [False, None, 1, "true"])
def test_factory_cannot_bypass_hard_quota(boundary, quota):
    with pytest.raises(ValueError, match="hard storage quota"):
        verifier._container_factory(IMAGE, "root", task()["base_commit"], {}, storage_quota=quota)
    assert boundary.client.options == []


def test_cli_requires_hard_quota_flag_before_execution(boundary):
    command = verifier.verifier_command(boundary.task_path, boundary.patch_path, boundary.output, RUN_ID, IMAGE)
    command.remove("--storage-quota")
    with pytest.raises(SystemExit) as error:
        verifier.main(command[2:])
    assert error.value.code == 2
    assert not boundary.client.options
    assert not boundary.output.exists()
