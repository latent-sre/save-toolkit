"""Real Harbor 0.24.0 interfaces, accessible only through owned bounded containers.

Import this optional module inside the dedicated requirements-harbor environment.
The generic Harbor Docker provider is deliberately not an admitted execution path.
"""

from __future__ import annotations

import asyncio
import importlib.metadata
import json
import shlex
import time
from pathlib import Path
from typing import Any

from harbor.agents.base import BaseAgent
from harbor.environments.base import BaseEnvironment, ExecResult
from harbor.environments.capabilities import EnvironmentCapabilities, EnvironmentResourceCapabilities
from harbor.models.agent.context import AgentContext
from harbor.models.task.config import EnvironmentConfig
from harbor.models.task.task import Task
from harbor.models.trial.paths import TrialPaths
from harbor.verifier.verifier import Verifier
from probe import invocation, tracing
from swebench_adapter.artifacts import screen
from swebench_adapter.containers import DockerResources

from .contracts import HARBOR_VERSION, PROFILE, reward_assessment


def require_sdk() -> None:
    if importlib.metadata.version("harbor") != HARBOR_VERSION:
        raise ValueError("Harbor version must match the pinned SDK")


class FleetEnvironment(BaseEnvironment):  # type: ignore[misc]  # optional SDK base
    """Attach to a container already admitted and owned by the host lifecycle.

    Author commands use only ``author``; generic exec and hidden-test uploads are
    verifier-only. All execution uses the shared output/wall/resource controls.
    """

    def __init__(
        self,
        *,
        resources: DockerResources,
        container: str,
        role: str,
        task: Task,
        trial_paths: TrialPaths,
        wall_seconds: float,
        config: dict[str, Any] | None = None,
        sensitive: tuple[str, ...] = (),
    ):
        require_sdk()
        if role not in {"author", "verifier"} or not 0 < wall_seconds <= 2700:
            raise ValueError("invalid actor or wall limit")
        resources._container(container)
        self.resources, self.container, self.role = resources, container, role
        self.wall_seconds, self.config = wall_seconds, config
        self.deadline = time.monotonic() + wall_seconds
        self.sensitive = sensitive
        self.execution: dict[str, Any] | None = None
        super().__init__(
            environment_dir=task.paths.environment_dir,
            environment_name=task.name,
            session_id=container,
            trial_paths=trial_paths,
            task_env_config=EnvironmentConfig(cpus=2, memory_mb=2048, storage_mb=10240),
            enable_environment_dir_upload=False,
        )

    @staticmethod
    def type() -> str:
        return "save-toolkit-owned-bounded-docker"

    @property
    def capabilities(self) -> EnvironmentCapabilities:
        return EnvironmentCapabilities(disable_internet=True)

    @classmethod
    def resource_capabilities(cls) -> EnvironmentResourceCapabilities:
        return EnvironmentResourceCapabilities(cpu_limit=True, memory_limit=True)

    def _validate_definition(self) -> None:
        if not self.environment_dir.is_dir():
            raise ValueError("task environment directory is unavailable")

    async def start(self, force_build: bool = False) -> None:
        raise ValueError("host lifecycle must create and admit the bounded container first")

    async def stop(self, delete: bool = True) -> None:
        raise ValueError("host lifecycle owns cleanup and absence receipts")

    def _verifier(self) -> None:
        if self.role != "verifier":
            raise ValueError("hidden tests and external-code execution require the independent verifier")

    async def upload_file(self, source_path: Path | str, target_path: str) -> None:
        self._verifier()
        source = Path(source_path)
        if source.is_symlink() or not source.is_file() or not target_path.startswith("/tests/"):
            raise ValueError("only regular hidden test files may be uploaded")
        await asyncio.to_thread(self.resources.docker.call, ["cp", str(source), f"{self.container}:{target_path}"])

    async def upload_dir(self, source_dir: Path | str, target_dir: str) -> None:
        self._verifier()
        source = Path(source_dir)
        if target_dir != "/tests" or not source.is_dir():
            raise ValueError("only the task hidden-test directory may be uploaded")
        if any(p.is_symlink() or (not p.is_file() and not p.is_dir()) for p in source.rglob("*")):
            raise ValueError("hidden tests contain unsupported filesystem entries")
        await asyncio.to_thread(self.resources.docker.call, ["cp", str(source) + "/.", f"{self.container}:/tests"])

    async def download_file(self, source_path: str, target_path: Path | str) -> None:
        raise ValueError("use bounded verifier-directory collection")

    async def download_dir(self, source_dir: str, target_dir: Path | str) -> None:
        self._verifier()
        if source_dir != "/logs/verifier" or Path(target_dir) != self.trial_paths.verifier_dir:
            raise ValueError("only verifier evidence may be collected")
        # The producer is untrusted; collect through a bounded stream and validate
        # archive entries before writing regular files on the host.
        from .transfer import collect_tree  # noqa: PLC0415

        await asyncio.to_thread(collect_tree, self.resources.docker, self.container, source_dir, Path(target_dir))

    async def exec(
        self,
        command: str,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout_sec: int | None = None,
        user: str | int | None = None,
    ) -> ExecResult:
        self._verifier()
        if cwd not in (None, "/app") or env or user not in (None, "root"):
            raise ValueError("unsupported verifier execution override")
        execution = await asyncio.to_thread(
            self.resources.execute,
            self.container,
            ["/bin/sh", "-c", "cd /app && " + command],
            wall_seconds=self._remaining(timeout_sec),
            storage_quota=True,
        )
        if execution.stop:
            raise RuntimeError("verifier execution stopped: " + execution.stop)
        return ExecResult(
            stdout=execution.stdout.decode("utf-8", "replace"),
            stderr=execution.stderr.decode("utf-8", "replace"),
            return_code=execution.returncode,
        )

    def _remaining(self, requested: int | None = None) -> float:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("actor wall-clock deadline exhausted")
        return min(remaining, requested or self.wall_seconds)

    async def author(self, instruction: str, logs_dir: Path) -> dict[str, Any]:
        if self.role != "author" or self.config is None:
            raise ValueError("native author requires its admitted container configuration")
        prompt = (
            "Use the static-authoring profile. Inspect inputs and author files under /app without executing "
            "task code or tests, compiling, installing dependencies or starting services. Author Python code; "
            "use shell only as launch glue and protobuf only for the RPC schema. Independent verification "
            "runs separately. If generation or service startup is needed, write /app/submission.sh for the "
            "independent actor to execute. Do not alter policy/settings. Preserve the supplied input data.\n\n"
            + instruction
        )
        argv = invocation.build_command(
            "/opt/claude",
            Path("/opt/fleet"),
            "save-toolkit:software-engineer",
            prompt,
            self.config["model"],
            max_turns=64,
        )
        argv[argv.index("--plugin-dir") + 1] = "/opt/fleet"
        denied = argv.index("--disallowedTools") + 1
        argv[denied] += ",WebFetch,WebSearch"
        if self.config.get("api_key_helper"):
            pos = argv.index("--settings") + 1
            settings = json.loads(argv[pos])
            settings["apiKeyHelper"] = 'printf "%s" "$ANTHROPIC_AUTH_TOKEN"'
            argv[pos] = json.dumps(settings)
        # start_agent's shared /testbed default is overridden explicitly here.
        execution = await asyncio.to_thread(
            self.resources.execute,
            self.container,
            ["/bin/sh", "-c", "cd /app && exec " + shlex.join(argv)],
            wall_seconds=self._remaining(),
            storage_quota=True,
        )
        screen(execution.stdout, self.sensitive)
        screen(execution.stderr, self.sensitive)
        logs_dir.mkdir(parents=True, exist_ok=True)
        trace = logs_dir / "stdout.jsonl"
        trace.write_bytes(execution.stdout)
        (logs_dir / "stderr.txt").write_bytes(execution.stderr)
        (logs_dir / "argv.json").write_text(json.dumps(argv, indent=2) + "\n")
        parsed = tracing.parse_trace(trace)
        self.execution = {
            "returncode": execution.returncode,
            "stop": execution.stop,
            "seconds": execution.seconds,
            "requested_agent": "save-toolkit:software-engineer",
            "requested_model": self.config["model"],
            "observed_models": parsed.models,
            "runtime_plugins": parsed.runtime_plugins,
            "advertised_tools": parsed.advertised_tools,
            "tool_counts": parsed.tool_counts,
            "tool_counts_complete": parsed.tool_counts_complete,
            "session_id": parsed.session_id,
            "has_result": parsed.has_result,
            "result_is_error": parsed.result_is_error,
            "result_subtype": parsed.result_subtype,
            "cost_usd_estimate": parsed.total_cost_usd,
            "policy_review": "unmeasured",
            "trace": "agent/stdout.jsonl",
            "execution_profile": PROFILE,
        }
        return self.execution


class FleetAgent(BaseAgent):  # type: ignore[misc]  # optional SDK base
    """Custom --agent harbor_adapter.sdk:FleetAgent; admitted environment required."""

    @staticmethod
    def name() -> str:
        return "save-toolkit-static-author"

    def version(self) -> str:
        return "wp09-v1"

    async def setup(self, environment: BaseEnvironment) -> None:
        require_sdk()
        if not isinstance(environment, FleetEnvironment) or environment.role != "author":
            raise ValueError("generic Harbor environments are not admitted for fleet authoring")
        if self.mcp_servers or self.skills_dir or self.extra_env:
            raise ValueError("extra tools, skills and inherited environment are not admitted")

    async def run(self, instruction: str, environment: BaseEnvironment, context: AgentContext) -> None:
        await self.setup(environment)
        assert isinstance(environment, FleetEnvironment)
        if environment.config is None or self.model_name != environment.config["model"]:
            raise ValueError("requested model differs from admitted configuration")
        context.metadata = await environment.author(instruction, self.logs_dir)
        context.cost_usd = context.metadata["cost_usd_estimate"]


async def verify_task(
    task: Task, environment: FleetEnvironment, paths: TrialPaths, *, submission_script: bool
) -> dict[str, Any]:
    """Run the actual pinned Harbor verifier, retaining native output and local policy dimensions."""
    environment._verifier()
    receipt: dict[str, Any] = {
        "format": "wp09-harbor-verification",
        "schema_version": 1,
        "task_id": task.name,
        "execution_actor": "independent-verifier",
        "harbor_version": HARBOR_VERSION,
        "native_result": None,
        "execution_error": None,
        "submission_returncode": None,
        "policy_review": "unmeasured",
        "cleanup": "pending",
    }
    try:
        if submission_script:
            prepared = await environment.exec("/bin/sh /app/submission.sh")
            receipt["submission_returncode"] = prepared.return_code
            (paths.trial_dir / "submission.stdout.txt").write_text(prepared.stdout or "")
            (paths.trial_dir / "submission.stderr.txt").write_text(prepared.stderr or "")
            # A failed candidate submission does not prevent independent tests from measuring it.
        native = await Verifier(task=task, trial_paths=paths, environment=environment).verify()
        receipt["native_result"] = native.model_dump(mode="json")
    except Exception as exc:
        receipt["execution_error"] = type(exc).__name__
    receipt["assessment"] = reward_assessment(paths.verifier_dir)
    if receipt["native_result"] is None:
        receipt["assessment"]["verdict"] = "INCONCLUSIVE"
        receipt["assessment"]["reason"] = "Harbor verifier did not complete; raw reward retained"
    (paths.trial_dir / "verification.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt
