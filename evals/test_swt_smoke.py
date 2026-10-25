"""SWT smoke composition controls; Docker/model-free isolation probes belong to WP08 tests."""

from __future__ import annotations

import ast
import json
import re
import types
import unittest
from pathlib import Path

import pytest
from swt_adapter import core, runner, smoke


def test_smoke_runs_gold_and_three_negative_verifiers_then_keeps_acceptance_pending(tmp_path, monkeypatch):
    path = "tests/test_original.py"
    gold = f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@ -0,0 +1 @@\n+assert behavior() == 42\n"
    code = gold.replace(path, "pkg/behavior.py")
    row = dict(
        instance_id="org__repo-1",
        repo="org/repo",
        base_commit="a" * 40,
        version="1",
        difficulty="1-4 hours",
        patch=code,
        test_patch=gold,
    )
    manifest = dict(
        schema_version=1,
        upstream_revision=core.UPSTREAM_REVISION,
        dataset=core.DATASET,
        dataset_revision=core.DATASET_REVISION,
        cases=[dict(instance_id=row["instance_id"], row_sha256=core.digest(row), test_roots=["tests/"])],
    )
    monkeypatch.setattr(smoke.verifier, "check_source", lambda p: None)
    monkeypatch.setattr(smoke.verifier, "runtime_problems", lambda: [])
    monkeypatch.setattr(
        smoke.runner,
        "live_binding",
        lambda *a: {
            "docker_runtime": {"endpoint": "unix:///offline", "ID": "fake"},
            "instance_id": row["instance_id"],
            "task_sha256": core.digest(row),
        },
    )
    monkeypatch.setattr(smoke.repair_runner, "image_identity", lambda *a: "sha256:" + "b" * 64)
    calls = []

    def supervise(source, task, patch, roots, output, *args):
        calls.append(patch)
        output.mkdir()
        result = {
            "mechanical": "PASS" if patch == gold else "FAIL",
            "instance_id": row["instance_id"],
            "row_sha256": core.digest(row),
        }
        (output / "verifier-receipt.json").write_text(json.dumps(result))
        return {
            "process_cleanup_complete": True,
            "cleanup": [{"name": name, "removed": True} for name in smoke.verifier.container_names(args[0])],
            "run_id": args[0],
            "exit_code": 0,
            "stop": None,
            "receipt_available": True,
        }

    monkeypatch.setattr(smoke.verifier, "supervise", supervise)
    original = smoke.repair_runner.verify_patch

    def isolation(config, manifest, rows, output):
        output.mkdir()
        smoke.repair_runner.verify_patch(row, "", output, "name", "image", None)
        smoke.repair_runner.verify_patch(row, "", output, "name", "image", None, baseline=True)
        return {
            "checks": dict.fromkeys(
                ("guard_allow", "guard_deny", "no_cr", "history_pruned", "egress", "cpu_cap", "storage_cap", "cleanup"),
                True,
            ),
            "error": None,
            "cleanup": [{"present": False, "removed": True}],
        }

    monkeypatch.setattr(smoke.isolation, "run_smoke", isolation)
    result = smoke.run_smoke({}, manifest, [row], set(), Path("pinned"), tmp_path / "smoke", row["instance_id"])
    assert len(calls) == 4 and calls[0] == gold
    assert "assert False" in calls[1]
    assert "assert True" in calls[2]
    assert "wp09_missing_unrelated_dependency" in calls[3]
    assert set(result["checks"]) == set(runner.SMOKE_CHECKS)
    assert all(result["checks"].values())
    assert result["model_calls"] == 0
    assert smoke.repair_runner.verify_patch is original
    assert json.loads((tmp_path / "smoke/pending-admission.json").read_text())["accepted"] is False
    admission_path = tmp_path / "smoke/pending-admission.json"
    accepted = json.loads(admission_path.read_text())
    assert "smoke" not in accepted
    accepted.update(accepted=True, owner="human")
    admission_path.write_text(json.dumps(accepted))
    runner.require_admission(admission_path, result["binding"])


@pytest.mark.parametrize(
    ("body", "success", "errors"),
    [("assert False", False, 0), ("assert True", True, 0), ("import wp09_missing_unrelated_dependency", False, 1)],
)
def test_controls_are_actually_collected_by_unittest(tmp_path, body, success, errors):
    patch = smoke.control_patch("tests/prefetch_related/", body)
    source = (
        "\n".join(line[1:] for line in patch.splitlines() if line.startswith("+") and not line.startswith("+++")) + "\n"
    )
    module = types.ModuleType("prefetch_related.test_wp09_control")
    exec(compile(source, "test_wp09_control.py", "exec"), module.__dict__)
    suite = unittest.defaultTestLoader.loadTestsFromModule(module)
    result = unittest.TestResult()
    suite.run(result)
    assert result.testsRun == 1
    assert result.wasSuccessful() is success
    assert len(result.errors) == errors


def test_pinned_django_test_directive_matches_collectable_module(tmp_path, monkeypatch):
    source = Path(__file__).parents[1] / ".eval-runs/complex-campaigns/wp09-swt-source/src/utils.py"
    if not source.exists():
        pytest.skip("pinned public source required")
    tree = ast.parse(source.read_text())
    method = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "get_test_directives"
    )
    scope = {"re": re, "NON_TEST_EXTS": []}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), "exec"), scope)
    patch = smoke.control_patch("tests/prefetch_related/", "assert True")
    targets = scope["get_test_directives"](patch, "django/django")
    assert targets == ["prefetch_related.test_wp09_control"]
    package = tmp_path / "prefetch_related"
    package.mkdir()
    (package / "__init__.py").write_text("")
    source = (
        "\n".join(line[1:] for line in patch.splitlines() if line.startswith("+") and not line.startswith("+++")) + "\n"
    )
    (package / "test_wp09_control.py").write_text(source)
    monkeypatch.syspath_prepend(str(tmp_path))
    suite = unittest.defaultTestLoader.loadTestsFromNames(targets)
    result = unittest.TestResult()
    suite.run(result)
    assert result.testsRun == 1 and result.wasSuccessful()
