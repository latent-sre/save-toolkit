"""Configuration, identity and admission checks without executable or daemon calls."""

import copy
import hashlib
import importlib
import json
import subprocess
from pathlib import Path

import pytest


def module():
    return importlib.import_module("swebench_adapter.configuration")


@pytest.fixture
def config_file(tmp_path):
    plugin = tmp_path / "plugin"
    for name in ("agents", "skills", "commands", "hooks"):
        (plugin / name).mkdir(parents=True)
        (plugin / name / "input.txt").write_text("plugin bytes\n")
    for name in (
        ".claude-plugin/plugin.json",
        "scripts/fleet_frontmatter.py",
        "scripts/readonly-guard.py",
        "scripts/readonly-guard-hook.sh",
    ):
        path = plugin / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("measured bytes\n")
    cli = tmp_path / "claude"
    cli.write_bytes(b"\x7fELFsynthetic offline binary fixture")
    cli.chmod(0o700)
    config = {
        "schema_version": 1,
        "plugin_root": "plugin",
        "cli_path": "claude",
        "cli_sha256": hashlib.sha256(cli.read_bytes()).hexdigest(),
        "cli_version": "2.1.99",
        "model": "anthropic/claude-sonnet-5.5",
        "haiku_model": "anthropic/claude-haiku-4.5",
        "images": {
            "org__repo-1": {
                "reference": "registry.test/team/image@sha256:" + "a" * 64,
                "image_id": "sha256:" + "b" * 64,
            }
        },
        "proxy_bind": "172.18.0.1",
        "proxy_target": "host.docker.internal",
        "storage_quota": True,
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(config))
    return path, config


def test_config_resolves_paths_checks_actual_cli_bytes_and_defaults_helper(config_file):
    path, _config = config_file
    config = module().load_config(path)
    assert config["plugin_root"] == str(path.parent / "plugin")
    assert config["cli_path"] == str(path.parent / "claude")
    assert config["api_key_helper"] is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema_version", True),
        ("schema_version", 2),
        ("plugin_root", "missing"),
        ("cli_path", "plugin"),
        ("cli_sha256", "a" * 64),
        ("cli_sha256", "A" * 64),
        ("cli_version", " "),
        ("model", "anthropic/claude-sonnet-latest"),
        ("haiku_model", "anthropic/claude-haiku-latest"),
        ("haiku_model", "anthropic/claude-haiku-"),
        ("proxy_bind", "localhost"),
        ("proxy_bind", "::1"),
        ("proxy_target", "evil.test"),
        ("storage_quota", 1),
        ("storage_quota", False),
        ("api_key_helper", "false"),
        ("images", {}),
        ("images", {"case": {"reference": "image:latest", "image_id": "sha256:" + "b" * 64}}),
        ("images", {"case": {"reference": "image@sha256:" + "a" * 64, "image_id": "bad"}}),
        ("cli_version", "Bearer secret-value-never-print"),
        ("unknown", "secret-value-never-print"),
    ],
)
def test_invalid_config_is_rejected_without_echoing_values(config_file, field, value):
    path, config = config_file
    config[field] = value
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError) as error:
        module().load_config(path)
    assert "secret-value-never-print" not in str(error.value)


@pytest.mark.parametrize(
    "text", ["[]", "null", '{"schema_version":1,"schema_version":1}', '{"schema_version":NaN}', '{"schema_version":1']
)
def test_load_requires_strict_json_object(tmp_path, text):
    path = tmp_path / "bad.json"
    path.write_text(text)
    with pytest.raises(ValueError):
        module().load_config(path)


def test_cli_symlink_resolves_but_script_wrapper_is_rejected(config_file):
    path, config = config_file
    link = path.parent / "cli-link"
    link.symlink_to(path.parent / "claude")
    config["cli_path"] = str(link)
    path.write_text(json.dumps(config))
    assert module().load_config(path)["cli_path"] == str(path.parent / "claude")
    (path.parent / "claude").write_bytes(b"#!/bin/sh\nexec claude\n")
    config["cli_sha256"] = hashlib.sha256((path.parent / "claude").read_bytes()).hexdigest()
    path.write_text(json.dumps(config))
    with pytest.raises(ValueError, match="cli"):
        module().load_config(path)


def test_binding_covers_manifest_plugin_cli_and_runtime_without_aliases(config_file, monkeypatch):
    path, _config = config_file
    configuration = module()
    monkeypatch.setattr(configuration, "adapter_digest", lambda: "c" * 64)
    config = configuration.load_config(path)
    manifest = {"tasks": [{"instance_id": "case"}], "schema_version": 1}
    bound = configuration.binding(config, manifest)
    expected_selection = hashlib.sha256(b'{"schema_version":1,"tasks":[{"instance_id":"case"}]}').hexdigest()
    assert bound["selection_sha256"] == expected_selection
    assert bound["adapter_sha256"] == "c" * 64
    assert bound["cli_sha256"] == config["cli_sha256"]
    assert bound["cli_version"] == "2.1.99"
    assert bound["schema_version"] == 1
    assert bound["api_key_helper"] is False
    old_plugin = bound["plugin_sha256"]
    (Path(config["plugin_root"]) / "agents/input.txt").write_text("changed")
    assert configuration.binding(config, manifest)["plugin_sha256"] != old_plugin
    config["images"]["org__repo-1"]["image_id"] = "sha256:" + "d" * 64
    assert bound["images"]["org__repo-1"]["image_id"] == "sha256:" + "b" * 64


def test_binding_rejects_cli_drift(config_file, monkeypatch):
    path, _config = config_file
    configuration = module()
    monkeypatch.setattr(configuration, "adapter_digest", lambda: "c" * 64)
    config = configuration.load_config(path)
    Path(config["cli_path"]).write_bytes(b"\x7fELFchanged")
    with pytest.raises(ValueError, match="cli"):
        configuration.binding(config, {})


def test_adapter_digest_binds_paths_bytes_requirements_and_normalizes_crlf(tmp_path, monkeypatch):
    configuration = module()
    root = tmp_path
    adapter = root / "evals/swebench_adapter"
    adapter.mkdir(parents=True)
    (adapter / "configuration.py").write_bytes(b"adapter\n")
    entry = root / "evals/swebench_repair.py"
    entry.write_bytes(b"entry\n")
    native = root / "evals/probe/native.py"
    native.parent.mkdir()
    native.write_bytes(b"native\n")
    for name in ("requirements-dev.txt", "requirements-test.txt", "requirements-swebench.txt"):
        (root / name).write_bytes(b"dependency==1\n")
    monkeypatch.setattr(configuration, "_ROOT", root)
    monkeypatch.setattr(configuration, "HARNESS_FILES", (native,))
    initial = configuration.adapter_digest()
    (root / "requirements-swebench.txt").write_bytes(b"dependency==2\n")
    assert configuration.adapter_digest() != initial
    (root / "requirements-swebench.txt").write_bytes(b"dependency==1\n")
    native.write_bytes(b"native\r\n")
    assert configuration.adapter_digest() == initial
    native.write_bytes(b"native changed\n")
    assert configuration.adapter_digest() != initial
    native.write_bytes(b"native\n")
    (adapter / "new.py").write_bytes(b"new module\n")
    assert configuration.adapter_digest() != initial
    (adapter / "new.py").unlink()
    (adapter / "configuration.py").rename(adapter / "renamed.py")
    assert configuration.adapter_digest() != initial
    (adapter / "renamed.py").rename(adapter / "configuration.py")
    (root / "requirements-dev.txt").write_bytes(b"dependency==2\n")
    assert configuration.adapter_digest() != initial
    entry.unlink()
    with pytest.raises(ValueError):
        configuration.adapter_digest()


def test_dependency_checks_use_availability_metadata_without_execution(monkeypatch):
    configuration = module()
    monkeypatch.setattr(configuration.shutil, "which", lambda _name: "/synthetic/docker")
    monkeypatch.setattr(configuration.metadata, "version", lambda _name: "5.0.2")
    monkeypatch.setattr(configuration.sys, "version_info", (3, 12, 0))
    for name in ("DOCKER_HOST", "DOCKER_CONTEXT"):
        monkeypatch.delenv(name, raising=False)
    assert configuration.dependency_problems() == []
    monkeypatch.setenv("DOCKER_HOST", "ssh://remote-host")
    assert any("DOCKER_HOST" in problem for problem in configuration.dependency_problems())
    monkeypatch.delenv("DOCKER_HOST")
    monkeypatch.setenv("DOCKER_CONTEXT", "remote-context")
    assert any("DOCKER_CONTEXT" in problem for problem in configuration.dependency_problems())
    monkeypatch.delenv("DOCKER_CONTEXT")
    monkeypatch.setattr(configuration.shutil, "which", lambda _name: None)
    monkeypatch.setattr(configuration.metadata, "version", lambda _name: "5.0.1")
    monkeypatch.setattr(configuration.sys, "version_info", (3, 11, 0))
    problems = configuration.dependency_problems()
    assert any("Docker" in problem for problem in problems)
    assert any("5.0.2" in problem for problem in problems)
    assert any("3.12" in problem for problem in problems)


@pytest.mark.parametrize(
    "host",
    ["unix:///var/run/docker.sock", "tcp://127.0.0.1:2375", "tcp://localhost:2375", "npipe:////./pipe/docker_engine"],
)
def test_local_docker_host_overrides_are_accepted(monkeypatch, host):
    configuration = module()
    monkeypatch.setattr(configuration.shutil, "which", lambda _name: "/synthetic/docker")
    monkeypatch.setattr(configuration.metadata, "version", lambda _name: "5.0.2")
    monkeypatch.setenv("DOCKER_HOST", host)
    monkeypatch.setenv("DOCKER_CONTEXT", "default")
    assert configuration.dependency_problems() == []


def test_missing_swebench_distribution_is_reported(monkeypatch):
    configuration = module()

    def absent(_name):
        raise configuration.metadata.PackageNotFoundError

    monkeypatch.setattr(configuration.metadata, "version", absent)
    assert any("5.0.2" in problem for problem in configuration.dependency_problems())


def test_selection_committed_requires_tracked_clean_head_bytes(tmp_path):
    def git(*args):
        result = subprocess.run(["git", *args], cwd=tmp_path, capture_output=True, check=True)
        return result.stdout

    git("init", "--quiet")
    git("config", "user.name", "Offline Test")
    git("config", "user.email", "offline@example.invalid")
    path = tmp_path / "selection.json"
    path.write_text('{"selection":1}\n')
    assert not module().selection_committed(path)
    git("add", "selection.json")
    assert not module().selection_committed(path)
    git("commit", "--quiet", "-m", "temporary fixture")
    head = git("rev-parse", "HEAD")
    assert module().selection_committed(path)
    path.write_text('{"selection":2}\n')
    assert not module().selection_committed(path)
    git("add", "selection.json")
    assert not module().selection_committed(path)
    path.write_text('{"selection":1}\n')
    assert not module().selection_committed(path), "staged changes also invalidate a selection"
    git("reset", "--quiet", "HEAD", "--", "selection.json")
    assert module().selection_committed(path)
    path.unlink()
    assert not module().selection_committed(path)
    assert git("rev-parse", "HEAD") == head


CHECKS = (
    "reference_resolves",
    "empty_rejected",
    "guard_allow",
    "guard_deny",
    "no_cr",
    "history_pruned",
    "egress",
    "cpu_cap",
    "storage_cap",
    "cleanup",
)


def smoke_receipt(bound):
    return {
        "format": "wp08-smoke",
        "schema_version": 1,
        "binding": copy.deepcopy(bound),
        "checks": dict.fromkeys(CHECKS, True),
        "cleanup": [{"resource": "agent", "present": False}],
    }


def test_smoke_receipt_requires_exact_binding_and_observed_cleanup():
    bound = {"model": "pinned", "images": {"case": "digest"}}
    receipt = smoke_receipt(bound)
    assert module().smoke_problem(receipt, bound) is None
    receipt["binding"]["images"]["case"] = "changed"
    assert "binding" in module().smoke_problem(receipt, bound)


@pytest.mark.parametrize("error", ["measurement failed", "interrupted", {}, False, 0, ""])
def test_smoke_recorded_error_rejects_otherwise_passing_checks(error):
    receipt = smoke_receipt({})
    receipt["error"] = error
    problem = module().smoke_problem(receipt, {})
    assert problem is not None
    assert "error" in problem


def test_smoke_explicit_null_error_is_accepted():
    receipt = smoke_receipt({})
    receipt["error"] = None
    assert module().smoke_problem(receipt, {}) is None


@pytest.mark.parametrize("check", CHECKS)
def test_each_smoke_check_must_be_literal_true(check):
    bound = {"id": "bound"}
    receipt = smoke_receipt(bound)
    receipt["checks"][check] = 1
    assert check in module().smoke_problem(receipt, bound)


@pytest.mark.parametrize("cleanup", [[], [{"present": True}], [{"present": None}], [{}], [False], "none"])
def test_smoke_cleanup_requires_nonempty_observed_absence(cleanup):
    receipt = smoke_receipt({})
    receipt["cleanup"] = cleanup
    assert "cleanup" in module().smoke_problem(receipt, {})


@pytest.mark.parametrize(
    "field,value", [("format", "other"), ("schema_version", True), ("checks", {}), ("binding", None)]
)
def test_smoke_missing_format_or_evidence_names_the_gap(field, value):
    receipt = smoke_receipt({})
    receipt[field] = value
    assert module().smoke_problem(receipt, {})
