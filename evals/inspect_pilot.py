"""Inspect SWE pilot: reuse a build fixture and grade its artifacts, not native fleet behavior."""

import hashlib
import json
import re
from importlib.metadata import version
from pathlib import Path

import anthropic
import yaml
from inspect_ai import Task, task
from inspect_ai.dataset import Sample
from inspect_ai.scorer import Score, Target, accuracy, scorer
from inspect_ai.solver import TaskState
from inspect_ai.util import sandbox
from inspect_swe import claude_code


ROOT = Path(__file__).resolve().parents[1]
SCENARIO = ROOT / "evals/build-scenarios/build-software-engineer-cli-with-tests.yaml"
COMPOSE = Path(__file__).with_name("inspect-compose.yaml")
ARTIFACT_CHECKS = {"file_exists", "glob_exists", "command_exit_zero", "command_output_regex"}


def pilot_spec() -> tuple[dict, list[dict], list[str]]:
    spec = yaml.safe_load(SCENARIO.read_text(encoding="utf-8"))
    checks = [check for check in spec["checks"] if check["check"] in ARTIFACT_CHECKS]
    omitted = [check["text"] for check in spec["checks"] if check["check"] not in ARTIFACT_CHECKS]
    if not checks:
        raise ValueError("pilot fixture has no artifact checks")
    return spec, checks, omitted


@scorer(metrics=[accuracy()])
def artifact_checks(checks: list[dict]):
    async def score(state: TaskState, target: Target) -> Score:
        results = []
        for check in checks:
            # Probe-owned inputs are restored after the agent finishes.
            for path, content in check.get("writes", {}).items():
                await sandbox().write_file(path, content)
            kind = check["check"]
            if kind == "file_exists":
                command = ["/usr/bin/test", "-f", check["path"]]
            elif kind == "glob_exists":
                command = ["/usr/local/bin/python", "-c", "import glob,sys; sys.exit(not glob.glob(sys.argv[1]))", check["pattern"]]
            elif kind in {"command_exit_zero", "command_output_regex"}:
                command = ["/bin/bash", "-c", check["command"]]
            else:
                raise ValueError(f"unsupported artifact check: {kind}")
            # Sandbox/timeout exceptions become Inspect sample errors, not agent failures.
            result = await sandbox().exec(command, timeout=check.get("timeout", 60), env={
                "PATH": "/usr/local/bin:/usr/bin:/bin", "BASH_ENV": "/dev/null",
                "PYTHONPATH": "", "PYTHONSAFEPATH": "1", "PYTHONNOUSERSITE": "1",
            })
            passed = result.success
            if kind == "command_output_regex":
                passed = passed and re.search(check["pattern"], result.stdout, re.MULTILINE) is not None
            results.append({"check": check["text"], "passed": passed,
                            "returncode": result.returncode, "stdout": result.stdout,
                            "stderr": result.stderr})
        return Score(value=int(all(item["passed"] for item in results)),
                     explanation="Artifact checks only; native fleet behavior is unverified.",
                     metadata={"checks": results, "assessment_scope": "artifact_only"})

    return score


@task
def wordfreq(claude_version: str = "latest") -> Task:
    """One sandboxed coding task; no implicit retries or model/provider selection."""
    spec, checks, omitted = pilot_spec()
    files = spec["fixture"]["files"]
    # Sample.setup runs inside Docker; JSON preserves empty files and literal newlines.
    setup = "python - <<'PY'\nimport json\nfrom pathlib import Path\n"
    setup += f"files = json.loads({json.dumps(files)!r})\n"
    setup += "for name, content in files.items():\n p = Path(name)\n p.parent.mkdir(parents=True, exist_ok=True)\n p.write_text(content, encoding='utf-8')\nPY\n"
    return Task(
        dataset=[Sample(id=spec["id"], input=spec["prompt"], setup=setup)],
        solver=claude_code(version=claude_version, attempts=1,
                           retry_refusals=0, retry_uncaught_errors=0,
                           disallowed_tools=["WebSearch", "WebFetch"], cwd="/workspace"),
        scorer=artifact_checks(checks), sandbox=("docker", str(COMPOSE)),
        epochs=1, token_limit=20000, time_limit=300, cost_limit=1.0,
        fail_on_error=True, score_on_error=False,
        metadata={"assessment_scope": "artifact_only", "native_fleet_parity": False,
                  "scenario_sha256": hashlib.sha256(SCENARIO.read_bytes()).hexdigest(),
                  "omitted_checks": omitted, "claude_version_requested": claude_version,
                  "inspect_ai": version("inspect-ai"), "inspect_swe": version("inspect-swe"),
                  "anthropic": anthropic.__version__},
    )
