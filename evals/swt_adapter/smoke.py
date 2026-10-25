"""Executable model-free SWT controls plus the existing bounded isolation smoke.

Run in its own CLI process. Scoped seam adaptation reuses WP08's measured guard,
network, CPU, storage and cleanup probes; no model endpoint is contacted.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path
from typing import Any

from swebench_adapter import runner as repair_runner
from swebench_adapter import smoke as isolation
from swebench_adapter.artifacts import store_json
from swebench_adapter.containers import Docker

from swt_adapter import core, runner, verifier


def control_patch(root: str, body: str) -> str:
    path = root + "test_wp09_control.py"
    lines = [
        "import unittest",
        "",
        "class WP09Control(unittest.TestCase):",
        "    def test_wp09_control(self):",
        "        " + body,
    ]
    return (
        f"diff --git a/{path} b/{path}\nnew file mode 100644\n--- /dev/null\n+++ b/{path}\n"
        f"@@ -0,0 +1,{len(lines)} @@\n" + "\n".join("+" + line for line in lines) + "\n"
    )


def run_smoke(
    config: dict[str, Any],
    manifest: dict[str, Any],
    rows: list[dict[str, Any]],
    excluded: set[str],
    source: Path,
    output: Path,
    instance_id: str,
) -> dict[str, Any]:
    verifier.check_source(source)
    problems = verifier.runtime_problems()
    if problems:
        raise ValueError("; ".join(problems))
    selected = core.select(manifest, rows, excluded)
    row = next(r for r in selected if r["instance_id"] == instance_id)
    roots = next(c["test_roots"] for c in manifest["cases"] if c["instance_id"] == instance_id)
    docker = Docker()
    bound = runner.live_binding(config, manifest, row, docker)
    image = repair_runner.image_identity(docker, config, instance_id)
    endpoint = bound["docker_runtime"]["endpoint"]
    engine = bound["docker_runtime"]["ID"]
    observations = {}
    controls = {}
    if output.exists():
        raise ValueError("smoke destination already exists")
    output.mkdir(parents=True, mode=0o700)

    def verify(name: str, patch: str) -> dict[str, Any]:
        supervised = verifier.supervise(
            source, row, patch, roots, output / name, "wp09-" + uuid.uuid4().hex, image, endpoint, engine
        )
        receipt = (
            json.loads((output / name / "verifier-receipt.json").read_text()) if supervised["receipt_available"] else {}
        )
        observations[name] = {"supervisor": supervised, "verifier": receipt}
        if not supervised["process_cleanup_complete"] or not all(c["removed"] for c in supervised["cleanup"]):
            raise ValueError("SWT control cleanup remains unresolved")
        return receipt

    def bridge(
        task: Any, patch: str, folder: Path, run_id: str, image_id: str, docker_client: Any, **kwargs: Any
    ) -> dict[str, Any]:
        # The shared smoke's two verifier slots become real SWT gold and always-fail controls.
        name = "always-fail" if kwargs.get("baseline") else "gold"
        submitted = control_patch(roots[0], "assert False") if name == "always-fail" else row["test_patch"]
        receipt = verify(name, submitted)
        controls["always_fail_rejected" if name == "always-fail" else "reference_reproduces"] = receipt.get(
            "mechanical"
        ) == ("FAIL" if name == "always-fail" else "PASS")
        return {
            "outcome": receipt.get("mechanical", "INCONCLUSIVE"),
            "baseline": bool(kwargs.get("baseline")),
            "cleanup": [
                {"present": False, "removed": True} for c in observations[name]["supervisor"]["cleanup"] if c["removed"]
            ],
        }

    # A dedicated smoke process owns these adapters; restore them even on failure.
    isolation_module: Any = isolation
    repair_module: Any = repair_runner
    previous = (
        isolation_module.resolve_task,
        isolation_module.dependency_problems,
        repair_module.runtime_binding,
        repair_module.verify_patch,
    )
    try:
        isolation_module.resolve_task = lambda *a: row
        isolation_module.dependency_problems = verifier.runtime_problems
        repair_module.runtime_binding = lambda *a: bound
        repair_module.verify_patch = bridge
        shell = isolation.run_smoke(config, {"tasks": [{"instance_id": instance_id}]}, [row], output / "isolation")
    finally:
        (
            isolation_module.resolve_task,
            isolation_module.dependency_problems,
            repair_module.runtime_binding,
            repair_module.verify_patch,
        ) = previous
    for key in runner.SMOKE_CHECKS:
        if key in shell["checks"]:
            controls[key] = shell["checks"][key]
    error = shell["error"]
    try:
        if error is None and controls.get("cleanup") is True:
            for name, body, key in [
                ("pass-both", "assert True", "pass_both_rejected"),
                ("unrelated-import", "import wp09_missing_unrelated_dependency", "unrelated_import_rejected"),
            ]:
                receipt = verify(name, control_patch(roots[0], body))
                controls[key] = receipt.get("mechanical") == "FAIL"
        controls["patch_text_rejected"] = (
            core.admit_patch(control_patch(roots[0], 'assert "fixed" in inspect.getsource(target)'), roots)["state"]
            == "FAIL"
        )
        controls["code_fix_rejected"] = core.admit_patch(row["patch"], roots)["state"] == "FAIL"
    except (ValueError, OSError):
        error = "SWT negative control execution or cleanup failed"
    checks = {key: controls.get(key, False) for key in runner.SMOKE_CHECKS}
    receipt = {
        "format": "wp09-swt-smoke",
        "schema_version": 1,
        "instance_id": instance_id,
        "cleanup": shell["cleanup"],
        "binding": bound,
        "checks": checks,
        "error": error,
        "observations": observations,
        "human_acceptance": "pending",
        "model_calls": 0,
    }
    smoke_path = store_json(output, "smoke.json", receipt)
    # This is a proposal with actual measured checks, never an automatic acceptance.
    store_json(
        output,
        "pending-admission.json",
        {
            "accepted": False,
            "owner": None,
            "binding": bound,
            "smoke_receipt": "smoke.json",
            "smoke_sha256": hashlib.sha256(smoke_path.read_bytes()).hexdigest(),
        },
    )
    return receipt
