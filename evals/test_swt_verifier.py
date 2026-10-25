"""Independent SWT execution contracts, with Docker represented only at its boundary."""

from __future__ import annotations

import ast
import importlib
import json
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from swebench_adapter.limits import ProcessResult
from swt_adapter import core, verifier


def test_six_variant_contract_preserves_roles_and_fresh_execution():
    calls = []

    def execute(spec, submitted, log_dir=None, build_mode="api"):
        calls.append((spec.patch_id, list(spec.patch_list), list(spec.test_directives)))
        return spec.instance_id, Path("output")

    # Exercise the exact pinned upstream function body when source is locally available.
    source = Path(__file__).parents[1] / ".eval-runs/complex-campaigns/wp09-swt-source/src/run_evaluation.py"
    if not source.exists():
        pytest.skip("pinned public checkout required for upstream-source integration control")
    tree = ast.parse(source.read_text())
    method = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "run_instance")
    method.returns = None
    for arg in method.args.args:
        arg.annotation = None
    scope = dict(
        remove_binary_diffs=lambda x: x,
        get_test_directives=lambda p, r: [p],
        run_eval_exec_spec=execute,
        get_log_dir=lambda *a: Path("cache"),
        test_directive_id=lambda x: "id",
    )
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), "exec"), scope)
    spec = SimpleNamespace(
        exec_spec=SimpleNamespace(repo="org/repo"), instance_id="id", golden_code_patch="CODE", golden_test_patch="GOLD"
    )
    spec.exec_spec.instance_id = "id"
    scope["run_instance"](
        spec, {"model_patch": "SUBMITTED", "model_name_or_path": "wp09"}, False, False, False, "run", ["vanilla"], 60
    )
    assert [p for _, p, _ in calls] == [
        ["SUBMITTED"],
        ["CODE", "SUBMITTED"],
        ["GOLD"],
        ["CODE", "GOLD"],
        [None],
        ["CODE", None],
    ]
    assert [c[0].split("__")[0] for c in calls] == list(core.VARIANTS)


def test_container_contract_requires_hard_quota_and_pinned_image():
    calls = []
    raw = SimpleNamespace(id="a" * 64)
    client = SimpleNamespace(
        images=SimpleNamespace(get=lambda i: SimpleNamespace(id=i)),
        containers=SimpleNamespace(create=lambda **kw: calls.append(kw) or raw),
    )
    wrapped = verifier.create_container(client, "sha256:" + "b" * 64, "swt-control", "a" * 40, {})
    assert wrapped.container.storage_quota is True
    options = calls[0]
    assert options["storage_opt"] == {"size": "10G"}
    assert options["network_disabled"] is True
    assert options["cap_drop"] == ["ALL"]
    assert options["mem_limit"] == "2g"
    assert options["nano_cpus"] == 2_000_000_000
    assert "volumes" not in options


def test_process_command_uses_credential_free_env_and_six_cleanup_names(tmp_path):
    env = verifier.worker_environment(tmp_path, "unix:///var/run/docker.sock")
    assert set(env) <= {
        "PATH",
        "SYSTEMROOT",
        "WINDIR",
        "TEMP",
        "TMP",
        "HOME",
        "DOCKER_HOST",
        "PYTHON_DOTENV_DISABLED",
        "PYTHONNOUSERSITE",
    }
    assert env["PYTHON_DOTENV_DISABLED"] == "1"
    names = verifier.container_names("wp09-abc")
    assert len(names) == len(set(names)) == 6
    with pytest.raises(ValueError):
        verifier.container_names("../escape")


def test_upstream_exec_timeout_tuple_is_not_forwarded_as_bytes(monkeypatch):
    monkeypatch.setattr(verifier, "bounded_exec", lambda *a, **k: ("captured", False, 0.1))
    assert verifier.swt_exec(None, "cmd", 1) == b"captured"
    monkeypatch.setattr(verifier, "bounded_exec", lambda *a, **k: ("", True, 1))
    with pytest.raises(TimeoutError):
        verifier.swt_exec(None, "cmd", 1)


@pytest.mark.parametrize(
    "mode,expected", [("valid", "PASS"), ("always-fail", "FAIL"), ("pass-both", "FAIL"), ("unrelated-import", "FAIL")]
)
def test_real_upstream_loader_scripts_parser_and_grader(tmp_path, monkeypatch, mode, expected):
    """Optional pinned-source integration; only Docker's boundary is substituted."""

    pytest.importorskip("datasets", reason="optional SWT environment is separate from project dependencies")
    root = Path(__file__).parents[1]
    source = root / ".eval-runs/complex-campaigns/wp09-swt-source"
    dataset_path = root / ".eval-runs/complex-campaigns/wp09-swt-prepared/verifier-only/dataset.json"
    if not source.is_dir() or not dataset_path.is_file():
        pytest.skip("pinned-source preparation required")
    monkeypatch.syspath_prepend(str(source / "src"))
    monkeypatch.syspath_prepend(str(source))
    monkeypatch.setenv("PYTHON_DOTENV_DISABLED", "1")
    monkeypatch.setenv("DOCKER_HOST", "unix:///offline-control")
    for name in ("fcntl", "resource"):
        monkeypatch.setitem(sys.modules, name, None)
    verifier.install_windows_import_guards()
    upstream_dataset = importlib.import_module("src.dataset")
    utils = importlib.import_module("src.utils")
    monkeypatch.setattr(utils, "fcntl", sys.modules["fcntl"])
    with pytest.raises(RuntimeError, match="unavailable"), utils.Locker(str(tmp_path / "forbidden-lock")):
        raise AssertionError("Unix lock unexpectedly succeeded")
    with pytest.raises(RuntimeError, match="unavailable"):
        sys.modules["resource"].setrlimit(0, (1, 1))

    rows = json.loads(dataset_path.read_text())
    loaded = upstream_dataset.load_swebench_dataset(str(dataset_path), is_swt=False)
    assert loaded[0]["golden_code_patch"] == rows[0]["patch"]
    assert loaded[0]["golden_test_patch"] == rows[0]["test_patch"]
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(importlib.import_module("docker"), "from_env", lambda: SimpleNamespace())
    build = importlib.import_module("src.docker_build")
    with pytest.raises(RuntimeError, match="unavailable"):
        build.build_base_image_from_exec_spec(
            SimpleNamespace(base_image_key="offline", base_dockerfile="none", platform="linux")
        )
    row = rows[0]
    containers = []
    scripts = {}

    class Container:
        def __init__(self, name):
            self.name = name
            self.id = "a" * 64

        def start(self):
            pass

        def remove(self, force):
            containers.remove(self)

        def exec_run(self, *a, **kw):
            return SimpleNamespace(output=b"", exit_code=0)

        def put_archive(self, path, data):
            with tarfile.open(fileobj=data, mode="r") as tar:
                scripts[self.name] = tar.extractfile(tar.getmembers()[0]).read().decode()
            return True

    class Client:
        def info(self):
            return dict(ID="offline-engine", OSType="linux")

        def close(self):
            pass

        @property
        def containers(self):
            return SimpleNamespace(list=lambda **kw: [c for c in containers if c.name == kw["filters"]["name"][2:-1]])

    def create(client, image, name, base, receipt):
        container = Container(name)
        containers.append(container)
        return container

    def execute(container, command, timeout):
        failure = "pred-pre" in container.name or "gold-pre" in container.name
        if mode == "always-fail" and "pred-" in container.name:
            failure = True
        if mode == "pass-both" and "pred-" in container.name:
            failure = False
        status = "FAILED" if failure else "PASSED"
        if mode == "unrelated-import" and "pred-" in container.name:
            status = "ERROR"
        name = (
            "tests/test_control.py::test_behavior"
            if "base-" not in container.name
            else "tests/test_control.py::test_existing"
        )
        return ("Applied patch cleanly.\n" + name + " " + status + "\n").encode()

    monkeypatch.setattr(importlib.import_module("docker"), "DockerClient", lambda **kw: Client())
    monkeypatch.setattr(verifier, "create_container", create)
    monkeypatch.setattr(verifier, "swt_exec", execute)
    path = "astropy/wcs/wcsapi/wrappers/tests/test_control.py"
    submitted = f"diff --git a/{path} b/{path}\n--- /dev/null\n+++ b/{path}\n@@ -0,0 +1 @@\n+assert observable() == 1\n"
    result = verifier.run_upstream(
        source,
        row,
        submitted,
        ["astropy/wcs/wcsapi/wrappers/tests/"],
        tmp_path,
        "wp09-offline-" + mode,
        "sha256:" + "b" * 64,
        "offline-engine",
    )
    assert result["agent_executed_tests"] is None
    assert result["mechanical"] == expected
    assert result["verdict"] == ("INCONCLUSIVE" if mode == "valid" else "FAIL")
    assert result["cleanup_complete"] and not containers
    assert len(scripts) == 6
    assert row["patch"] not in scripts["wp09-offline-" + mode + "-pred-pre"]
    assert row["patch"] in scripts["wp09-offline-" + mode + "-pred-post"]
    assert submitted in scripts["wp09-offline-" + mode + "-pred-pre"]
    assert result["upstream_report"][row["instance_id"]]["resolved"] == (mode == "valid")


def test_windows_import_guards_fail_closed(monkeypatch):

    for name in ("fcntl", "resource"):
        monkeypatch.setitem(sys.modules, name, None)
    verifier.install_windows_import_guards()
    with pytest.raises(RuntimeError, match="unavailable"):
        sys.modules["fcntl"].flock(1, sys.modules["fcntl"].LOCK_EX)
    with pytest.raises(RuntimeError, match="unavailable"):
        sys.modules["resource"].setrlimit(1, (1, 1))


def test_supervisor_cleans_exact_owned_names_before_output_screening(tmp_path, monkeypatch):

    calls = []

    class DockerBoundary:
        def pin(self, endpoint):
            pass

        def call(self, args):
            calls.append(args)
            return SimpleNamespace(stdout=b'{"ID":"engine","OSType":"linux"}' if args[0] == "info" else b"")

    monkeypatch.setattr(verifier, "Docker", DockerBoundary)
    monkeypatch.setattr(verifier, "check_source", lambda path: None)
    monkeypatch.setattr(
        verifier, "run_bounded", lambda *a, **kw: ProcessResult(b"sk-or-not-real-secret", b"", 0, None, 0)
    )
    with pytest.raises(ValueError, match="credential-shaped"):
        verifier.supervise(
            tmp_path,
            {"instance_id": "id"},
            "patch",
            ["tests/"],
            tmp_path / "run",
            "wp09-control",
            "sha256:" + "a" * 64,
            "unix:///offline",
            "engine",
        )
    # Initial absence and final absence are both observed for all six exact names.
    assert len([a for a in calls if a[:3] == ["container", "ls", "-aq"]]) == 18
    assert (tmp_path / "run/supervisor-receipt.json").is_file()
