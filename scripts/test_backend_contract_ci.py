"""Execute the API starter's comparison step against real root and nested Git histories."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml

from testkit import require_shell

ASSETS = Path(__file__).resolve().parents[1] / "skills/backend-craft/assets/ci"


@pytest.mark.parametrize("workflow", ["api-contract-fastapi.yml", "api-contract-go.yml"])
@pytest.mark.parametrize("service_dir, base_document, base_ref, diff_exit", [
    (".", True, "main", 0),
    ("services/orders", True, "main", 0),
    ("services/orders", True, "main", 23),
    ("services/orders", False, "main", 0),
    ("services/orders", True, "unfetched", 0),
])
def test_contract_comparison_uses_the_service_history(
    tmp_path, workflow, service_dir, base_document, base_ref, diff_exit,
):
    repo = tmp_path / "repo"
    service = repo / service_dir
    service.mkdir(parents=True)
    (repo / "README.md").write_text("fixture\n", encoding="utf-8")
    before = {"openapi": "3.1.0", "info": {"version": "before"}}
    after = {"openapi": "3.1.0", "info": {"version": "after"}}
    if base_document:
        (service / "openapi.json").write_text(json.dumps(before), encoding="utf-8")

    def git(*args):
        return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, timeout=30)

    git("init", "-q", "-b", "main")
    git("add", ".")
    git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
        "-c", "commit.gpgsign=false", "-c", "core.hooksPath=/dev/null", "commit", "-qm", "base")
    git("update-ref", "refs/remotes/origin/main", "HEAD")
    (service / "openapi.json").write_text(json.dumps(after), encoding="utf-8")

    # Replace only the external comparator; the workflow's Git lookup and failure handling run unchanged.
    binaries = tmp_path / "bin"
    binaries.mkdir()
    fake_go = binaries / "go"
    fake_go.write_text(
        '#!/usr/bin/env bash\nset -eu\n'
        'cp "$8" "$RUNNER_TEMP/seen-base.json"\n'
        'cp "$9" "$RUNNER_TEMP/seen-current.json"\n'
        'exit "$DIFF_EXIT"\n', encoding="utf-8", newline="\n",
    )
    fake_go.chmod(0o755)
    bash = require_shell("bash")
    shell_dir = Path(bash).parent
    env = {**os.environ, "BASE_REF": base_ref, "SERVICE_DIR": service_dir,
           "RUNNER_TEMP": tmp_path.as_posix(), "DIFF_EXIT": str(diff_exit)}
    env["PATH"] = os.pathsep.join([
        str(binaries), str(shell_dir), str(shell_dir.parent / "usr/bin"), env.get("PATH", ""),
    ])
    definition = yaml.safe_load((ASSETS / workflow).read_text(encoding="utf-8"))
    step = next(s for s in definition["jobs"]["contract"]["steps"]
                if s.get("name") == "Breaking changes against the base branch")
    directory = step.get("working-directory", ".").replace("${{ env.SERVICE_DIR }}", service_dir)
    script = tmp_path / "compare.sh"
    script.write_text(step["run"], encoding="utf-8", newline="\n")
    result = subprocess.run([bash, "--noprofile", "--norc", "-e", "-o", "pipefail", str(script)],
                            cwd=repo / directory, env=env, capture_output=True, text=True, timeout=30)
    if base_ref == "unfetched":
        assert result.returncode != 0, "an unavailable base must not pass as a first contract"
        assert not (tmp_path / "seen-base.json").exists()
    elif not base_document:
        assert result.returncode == 0, result.stdout + result.stderr
        assert "first contract" in result.stdout
        assert not (tmp_path / "seen-base.json").exists()
    else:
        assert result.returncode == diff_exit, result.stdout + result.stderr
        seen = tmp_path / "seen-base.json"
        assert seen.exists(), "comparison skipped an existing service contract"
        assert json.loads(seen.read_text()) == before
        assert json.loads((tmp_path / "seen-current.json").read_text()) == after
