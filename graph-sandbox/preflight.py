#!/usr/bin/env python
"""Fail-closed host preflight for the GRAPH-002 runtime Compose model.

This module is intentionally standard-library-only. It may render and inspect Docker metadata, but
it never builds, pulls, creates, starts, runs, or removes a container.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tempfile
import shutil
from typing import Any, Callable, Mapping, Protocol, Sequence


BASE_REFERENCE = (
    "python:3.12.10-slim-bookworm@"
    "sha256:97983fa8cc88343512862c62307159a82261c3528dc025f79e5a3f7af43e50b4"
)
LOCK_VERSION = "graph-sandbox-images/v1"
PLATFORM = "linux/amd64"
DEFAULT_SERVICES = frozenset({"graph-runner", "checkout", "payments", "inventory"})
SATURATION_SERVICES = DEFAULT_SERVICES | {"loadgen"}
CASE_VERSION = "graph-sandbox-case/v2"
CASE_DIGESTS: Mapping[str, str] = {
    "checkout-readiness-failure-001": "2d8ba52bd5c263d2e654749787474e7ec9a382a4eebea03911d8bd7a708b7bc1",
    "duplicate-effect-001": "87a70054eae9e23f98ad92391da4ec4ab5a97e1f923ce4e2e4e9a16d10c77f62",
    "inventory-http-error-after-payment-001": "8ff20a5daf5bf37f450e7aabff469a9884fcb80588690461a0dca46d69b39798",
    "mission-healthy-001": "74266b9c39a7733128e25f7279bb18820664bfbd6c11d8b0a6a3fa5e53a685d1",
    "payments-ambiguous-after-commit-001": "5e19af92d88d35c0a9b093fb2a644770e97d46b6a77e1b37f1462e24f1b94882",
    "payments-http-error-001": "f7cb97df5d4773602b50ebd15e27a85036a1d2462b0ec4d8a34787e6216475c1",
    "payments-latency-001": "046b8e99f4897b1f953295a6b1f3707b84be931cd67d27a0bad456c437f879b0",
}
IMAGE_ID_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
REVISION_RE = re.compile(r"^[0-9a-f]{40}$")
IDENTITY_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
NUMERIC_USER_RE = re.compile(r"^(?P<uid>[0-9]+)(?::(?P<gid>[0-9]+))?$")
INTERPOLATION_RE = re.compile(r"\$\{[^}]+\}")
MAX_CPUS = 2.0
MAX_MEMORY_BYTES = 512 * 1024 * 1024
MAX_PIDS = 128
MAX_RUN_SECONDS = 900
OWNER_LABEL_PREFIX = "com.latent-sre.graph-sandbox"
ALLOWED_ENVIRONMENT_NAMES = frozenset(
    {
        "APPDATA",
        "HOME",
        "HOMEDRIVE",
        "HOMEPATH",
        "LANG",
        "LC_ALL",
        "LOCALAPPDATA",
        "PATH",
        "PATHEXT",
        "PROGRAMFILES",
        "PROGRAMFILES(X86)",
        "PROGRAMW6432",
        "SYSTEMDRIVE",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "TMPDIR",
        "USERPROFILE",
        "WINDIR",
    }
)
FORBIDDEN_DOCKER_ENV_RE = re.compile(r"^(?:DOCKER|COMPOSE)_", re.IGNORECASE)

TOP_LEVEL_KEYS = frozenset({"name", "services", "networks", "volumes"})
SERVICE_KEYS = frozenset(
    {
        "image",
        "command",
        "entrypoint",
        "labels",
        "working_dir",
        "user",
        "read_only",
        "cap_drop",
        "security_opt",
        "pids_limit",
        "cpus",
        "mem_limit",
        "restart",
        "stop_grace_period",
        "environment",
        "healthcheck",
        "depends_on",
        "networks",
        "tmpfs",
        "volumes",
        "profiles",
    }
)
FORBIDDEN_SERVICE_KEYS = frozenset(
    {
        "build",
        "pull_policy",
        "ports",
        "privileged",
        "cap_add",
        "devices",
        "device_cgroup_rules",
        "pid",
        "ipc",
        "uts",
        "network_mode",
        "external_links",
        "links",
        "extra_hosts",
        "dns",
        "dns_opt",
        "dns_search",
        "secrets",
        "configs",
        "container_name",
        "group_add",
        "sysctls",
        "ulimits",
        "userns_mode",
        "cgroup",
        "cgroup_parent",
        "volumes_from",
        "extends",
        "credential_spec",
        "runtime",
        "isolation",
    }
)
COMMANDS: Mapping[str, tuple[str, ...]] = {
    "graph-runner": ("python", "-m", "runner.main"),
    "checkout": ("python", "-m", "sandbox_services.checkout"),
    "payments": ("python", "-m", "sandbox_services.payments"),
    "inventory": ("python", "-m", "sandbox_services.inventory"),
    "loadgen": ("python", "-m", "sandbox_services.loadgen"),
}
ENVIRONMENT_KEYS: Mapping[str, frozenset[str]] = {
    "graph-runner": frozenset(
        {
            "APPROVAL_FIXTURE",
            "CASE_DIGEST",
            "CASE_ID",
            "CHECKOUT_URL",
            "CHECKPOINT_DB",
            "EFFECT_LEDGER_DB",
            "EVIDENCE_DIR",
            "INVENTORY_URL",
            "PAYMENTS_URL",
            "PYTHONDONTWRITEBYTECODE",
            "PYTHONUNBUFFERED",
            "RUN_ID",
            "RUN_TIMEOUT_SECONDS",
            "SOURCE_REVISION",
        }
    ),
    "checkout": frozenset(
        {
            "DATA_DB",
            "DEPENDENCY_TIMEOUT_SECONDS",
            "EFFECT_FIXTURE",
            "INVENTORY_URL",
            "PAYMENTS_URL",
            "PYTHONDONTWRITEBYTECODE",
            "PYTHONUNBUFFERED",
            "READINESS_FIXTURE",
            "SANDBOX_CASE_ID",
            "SERVICE_PORT",
        }
    ),
    "payments": frozenset({"DATA_DB", "EFFECT_FIXTURE", "PYTHONDONTWRITEBYTECODE", "PYTHONUNBUFFERED", "READINESS_FIXTURE", "SANDBOX_CASE_ID", "SERVICE_PORT"}),
    "inventory": frozenset({"DATA_DB", "EFFECT_FIXTURE", "PYTHONDONTWRITEBYTECODE", "PYTHONUNBUFFERED", "READINESS_FIXTURE", "SANDBOX_CASE_ID", "SERVICE_PORT"}),
    "loadgen": frozenset(
        {
            "CHECKOUT_URL",
            "PYTHONDONTWRITEBYTECODE",
            "PYTHONUNBUFFERED",
            "RUN_ID",
            "RUN_TIMEOUT_SECONDS",
            "CASE_ID",
        }
    ),
}
CREDENTIAL_NAME_RE = re.compile(
    r"(?:^|_)(?:AUTH|AUTHORIZATION|CREDENTIAL|KEY|PASSWORD|PASSWD|PRIVATE|SECRET|SSH|TOKEN)(?:_|$)",
    re.IGNORECASE,
)
EXPECTED_INTERNAL_VALUES: Mapping[str, Mapping[str, str]] = {
    "graph-runner": {
        "CHECKOUT_URL": "http://checkout:8080",
        "CHECKPOINT_DB": "/state/checkpoints.sqlite3",
        "EFFECT_LEDGER_DB": "/state/effects.sqlite3",
        "EVIDENCE_DIR": "/evidence",
        "INVENTORY_URL": "http://inventory:8082",
        "PAYMENTS_URL": "http://payments:8081",
    },
    "checkout": {
        "DATA_DB": "/data/checkout.sqlite3",
        "INVENTORY_URL": "http://inventory:8082",
        "PAYMENTS_URL": "http://payments:8081",
        "SERVICE_PORT": "8080",
    },
    "payments": {"DATA_DB": "/data/payments.sqlite3", "SERVICE_PORT": "8081"},
    "inventory": {"DATA_DB": "/data/inventory.sqlite3", "SERVICE_PORT": "8082"},
    "loadgen": {"CHECKOUT_URL": "http://checkout:8080"},
}


class PreflightError(ValueError):
    """A bounded, operator-actionable preflight rejection."""


class CommandTimeoutError(PreflightError):
    """A bounded command exceeded its deadline and may require safe preservation."""


@dataclass(frozen=True)
class DockerStatus:
    reachable: bool
    os_type: str
    compose_json: bool
    engine_version: str
    compose_version: str


@dataclass(frozen=True)
class ContextIdentity:
    name: str
    endpoint: str
    fingerprint: str


@dataclass(frozen=True)
class ImageMetadata:
    image_id: str
    platform: str
    entrypoint: tuple[str, ...]
    declared_volumes: tuple[str, ...]


@dataclass(frozen=True)
class ResourceRecord:
    kind: str
    name: str
    labels: Mapping[str, str]


@dataclass(frozen=True)
class ResourceState:
    records: tuple[ResourceRecord, ...]


@dataclass(frozen=True)
class ResourceValidation:
    runner_existed: bool
    resource_keys: tuple[str, ...]


@dataclass(frozen=True)
class RepositoryLayout:
    repository_root: Path
    sandbox_root: Path
    compose_file: Path
    build_compose_file: Path
    images_lock: Path


@dataclass(frozen=True)
class SandboxCase:
    case_id: str
    digest: str
    document: Mapping[str, Any]

    @property
    def service_fixtures(self) -> Mapping[str, Mapping[str, str]]:
        return self.document["service_fixtures"]  # type: ignore[return-value]


CommandRunner = Callable[..., subprocess.CompletedProcess[Any]]


class DockerBoundary(Protocol):
    def status(self) -> DockerStatus: ...

    def inspect_image(self, image_id: str) -> ImageMetadata: ...

    def resource_state(self, run_id: str, source_revision: str) -> ResourceState: ...


def run_process(
    arguments: Sequence[str],
    *,
    environment: Mapping[str, str],
    timeout_seconds: int,
    stdin: bytes | None = None,
    binary: bool = False,
) -> subprocess.CompletedProcess[Any]:
    text_options: dict[str, str] = {}
    if not binary:
        text_options = {"encoding": "utf-8", "errors": "replace"}
    try:
        return subprocess.run(
            list(arguments),
            check=False,
            capture_output=True,
            text=not binary,
            input=stdin,
            timeout=timeout_seconds,
            env=dict(environment),
            shell=False,
            **text_options,
        )
    except subprocess.TimeoutExpired as exc:
        raise CommandTimeoutError(f"command timed out: {arguments[0]}") from exc
    except FileNotFoundError as exc:
        raise PreflightError(f"command unavailable: {arguments[0]}") from exc


def assert_no_ambient_docker_authority(environ: Mapping[str, str]) -> None:
    forbidden = sorted(name for name in environ if FORBIDDEN_DOCKER_ENV_RE.match(name))
    if forbidden:
        raise PreflightError(f"{forbidden[0]}: ambient Docker/Compose authority is forbidden")


def scrub_environment(
    environ: Mapping[str, str], *, extra: Mapping[str, str] | None = None
) -> dict[str, str]:
    scrubbed = {
        name: value
        for name, value in environ.items()
        if name.upper() in ALLOWED_ENVIRONMENT_NAMES and not FORBIDDEN_DOCKER_ENV_RE.match(name)
    }
    if extra:
        if any(FORBIDDEN_DOCKER_ENV_RE.match(name) for name in extra):
            raise PreflightError("environment: Docker/Compose selector override rejected")
        scrubbed.update(extra)
    return scrubbed


def validate_local_context(
    context_name: str,
    *,
    runner: CommandRunner = run_process,
    environ: Mapping[str, str] | None = None,
    platform_name: str | None = None,
) -> ContextIdentity:
    ambient = os.environ if environ is None else environ
    assert_no_ambient_docker_authority(ambient)
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}", context_name):
        raise PreflightError("context.name: invalid named Docker context")
    if context_name == "default":
        raise PreflightError("context.name: default context is not an accepted named boundary")
    command = [
        "docker",
        "--context",
        context_name,
        "context",
        "inspect",
        context_name,
        "--format",
        "{{json .}}",
    ]
    result = runner(
        command,
        environment=scrub_environment(ambient),
        timeout_seconds=30,
        stdin=None,
    )
    if result.returncode != 0:
        raise PreflightError("context.inspect: named Docker context is unavailable")
    try:
        payload = json.loads(result.stdout)
    except (TypeError, json.JSONDecodeError) as exc:
        raise PreflightError("context.inspect: invalid JSON") from exc
    if not isinstance(payload, Mapping) or payload.get("Name") != context_name:
        raise PreflightError("context.name: inspected context identity mismatch")
    endpoints = _mapping(payload.get("Endpoints"), "context.Endpoints")
    docker_endpoint = _mapping(endpoints.get("docker"), "context.Endpoints.docker")
    endpoint = docker_endpoint.get("Host")
    if not isinstance(endpoint, str):
        raise PreflightError("context.endpoint: Docker endpoint is missing")
    selected_platform = os.name if platform_name is None else platform_name
    if selected_platform == "nt":
        if not re.fullmatch(r"npipe:////\./pipe/[A-Za-z0-9_.-]{1,128}", endpoint):
            raise PreflightError("context.endpoint: Windows requires a local named pipe")
    else:
        if not endpoint.startswith("unix://"):
            raise PreflightError("context.endpoint: POSIX requires a local Unix socket")
        socket_text = endpoint.removeprefix("unix://")
        if not PurePosixPath(socket_text).is_absolute():
            raise PreflightError("context.endpoint: Unix socket path must be absolute")
        socket_path = Path(socket_text)
        if selected_platform != "nt" and socket_path.exists():
            _reject_path_indirection(socket_path)
    fingerprint = hashlib.sha256(f"{context_name}\n{endpoint}\n".encode("utf-8")).hexdigest()
    return ContextIdentity(context_name, endpoint, fingerprint)


def trusted_layout(script_path: Path) -> RepositoryLayout:
    script = Path(os.path.abspath(script_path))
    _reject_path_indirection(script)
    if not script.is_file():
        raise PreflightError("layout.script: trusted entrypoint is not a regular file")
    sandbox_root = script.parent
    repository_root = sandbox_root.parent
    required = {
        "compose_file": sandbox_root / "compose.yaml",
        "build_compose_file": sandbox_root / "compose.build.yaml",
        "images_lock": sandbox_root / "images.lock.json",
    }
    if not (repository_root / ".git").exists() or not (repository_root / "AGENTS.md").is_file():
        raise PreflightError("layout.repository: script is outside the expected checkout")
    for label, path in required.items():
        _reject_path_indirection(path)
        if not path.is_file():
            raise PreflightError(f"layout.{label}: required file is missing")
    return RepositoryLayout(repository_root, sandbox_root, **required)


class DockerCLI:
    """Read-only Docker metadata boundary used by the production CLI."""

    def __init__(
        self,
        context_name: str,
        *,
        timeout_seconds: int = 30,
        runner: CommandRunner = run_process,
        environ: Mapping[str, str] | None = None,
    ) -> None:
        ambient = os.environ if environ is None else environ
        assert_no_ambient_docker_authority(ambient)
        self.context_name = context_name
        self.timeout_seconds = timeout_seconds
        self.runner = runner
        self.environment = scrub_environment(ambient)

    def _run(self, arguments: Sequence[str]) -> subprocess.CompletedProcess[str]:
        return self.runner(
            ["docker", "--context", self.context_name, *arguments],
            environment=self.environment,
            timeout_seconds=self.timeout_seconds,
            stdin=None,
        )

    def status(self) -> DockerStatus:
        info = self._run(("info", "--format", "{{json .}}"))
        if info.returncode != 0:
            return DockerStatus(False, "", False, "", "")
        try:
            info_payload = json.loads(info.stdout)
        except json.JSONDecodeError as exc:
            raise PreflightError("docker.daemon: docker info did not return JSON") from exc

        compose = self._run(("compose", "version", "--format", "json"))
        compose_json = False
        compose_version = ""
        if compose.returncode == 0:
            try:
                compose_payload = json.loads(compose.stdout)
                compose_version = str(
                    compose_payload.get("version") or compose_payload.get("Version") or ""
                )
                compose_json = bool(compose_version)
            except json.JSONDecodeError:
                compose_json = False
        return DockerStatus(
            True,
            str(info_payload.get("OSType", "")),
            compose_json,
            str(info_payload.get("ServerVersion", "")),
            compose_version,
        )

    def inspect_image(self, image_id: str) -> ImageMetadata:
        inspect = self._run(("image", "inspect", "--format", "{{json .}}", image_id))
        if inspect.returncode != 0:
            raise PreflightError(f"image unavailable: {image_id}")
        try:
            payload = json.loads(inspect.stdout)
        except json.JSONDecodeError as exc:
            raise PreflightError(f"image unavailable: invalid inspect result for {image_id}") from exc
        resolved_id = str(payload.get("Id", ""))
        platform = f"{payload.get('Os', '')}/{payload.get('Architecture', '')}"
        config = payload.get("Config")
        if not isinstance(config, Mapping):
            raise PreflightError(f"image unavailable: missing Config for {image_id}")
        raw_entrypoint = config.get("Entrypoint")
        if raw_entrypoint is None:
            entrypoint: tuple[str, ...] = ()
        elif isinstance(raw_entrypoint, list) and all(isinstance(item, str) for item in raw_entrypoint):
            entrypoint = tuple(raw_entrypoint)
        else:
            raise PreflightError(f"image config: invalid Entrypoint for {image_id}")
        raw_volumes = config.get("Volumes")
        if raw_volumes is None:
            volumes: tuple[str, ...] = ()
        elif isinstance(raw_volumes, Mapping) and all(isinstance(item, str) for item in raw_volumes):
            volumes = tuple(sorted(raw_volumes))
        else:
            raise PreflightError(f"image config: invalid Volumes for {image_id}")
        return ImageMetadata(resolved_id, platform, entrypoint, volumes)

    def resource_state(self, run_id: str, source_revision: str) -> ResourceState:
        expected = expected_resource_records(run_id, source_revision)
        records: dict[tuple[str, str], ResourceRecord] = {}
        for expected_record in expected:
            noun = {"container": "container", "network": "network", "volume": "volume"}[
                expected_record.kind
            ]
            result = self._run((noun, "inspect", "--format", "{{json .}}", expected_record.name))
            if result.returncode != 0:
                continue
            try:
                payload = json.loads(result.stdout)
            except json.JSONDecodeError as exc:
                raise PreflightError(
                    f"resources.inspect: invalid {expected_record.kind} JSON"
                ) from exc
            if expected_record.kind == "container":
                labels = _mapping(_mapping(payload.get("Config"), "container.Config").get("Labels"), "container.Labels")
            else:
                labels = _mapping(payload.get("Labels") or {}, f"{expected_record.kind}.Labels")
            records[(expected_record.kind, expected_record.name)] = ResourceRecord(
                expected_record.kind,
                expected_record.name,
                {str(name): str(value) for name, value in labels.items()},
            )

        project = project_scope(run_id)
        enumerations = (
            ("container", ("container", "ls", "--all"), "Names"),
            ("network", ("network", "ls"), "Name"),
            ("volume", ("volume", "ls"), "Name"),
        )
        for kind, base_command, name_field in enumerations:
            listed = self._run(
                (
                    *base_command,
                    "--filter",
                    f"label=com.docker.compose.project={project}",
                    "--format",
                    "{{json .}}",
                )
            )
            if listed.returncode != 0:
                raise PreflightError(f"resources.inspect: {kind} enumeration failed")
            for line in listed.stdout.splitlines():
                if not line.strip():
                    continue
                try:
                    summary = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise PreflightError(
                        f"resources.inspect: invalid {kind} enumeration JSON"
                    ) from exc
                name = summary.get(name_field)
                if not isinstance(name, str):
                    raise PreflightError(f"resources.inspect: {kind} name missing")
                key = (kind, name)
                if key not in records:
                    records[key] = ResourceRecord(kind, name, {})
        return ResourceState(tuple(sorted(records.values(), key=lambda item: (item.kind, item.name))))


def project_scope(run_id: str) -> str:
    if not IDENTITY_RE.fullmatch(run_id):
        raise PreflightError("run_id: invalid atomic identity")
    suffix = hashlib.sha256(run_id.encode("ascii")).hexdigest()[:12]
    return f"graph-sandbox-v1-{suffix}"


def ownership_labels(run_id: str, source_revision: str) -> dict[str, str]:
    if not REVISION_RE.fullmatch(source_revision):
        raise PreflightError("source_revision: expected lowercase 40-hex revision")
    scope = project_scope(run_id)
    return {
        f"{OWNER_LABEL_PREFIX}.version": "graph-sandbox/v1",
        f"{OWNER_LABEL_PREFIX}.run-id": run_id,
        f"{OWNER_LABEL_PREFIX}.source-revision": source_revision,
        f"{OWNER_LABEL_PREFIX}.scope": scope.removeprefix("graph-sandbox-v1-"),
    }


def expected_resource_records(
    run_id: str, source_revision: str
) -> tuple[ResourceRecord, ...]:
    project = project_scope(run_id)
    owner = ownership_labels(run_id, source_revision)
    records: list[ResourceRecord] = []
    for service in sorted(DEFAULT_SERVICES):
        labels = {
            **owner,
            "com.docker.compose.project": project,
            "com.docker.compose.service": service,
        }
        records.append(ResourceRecord("container", f"{project}-{service}-1", labels))
    records.append(
        ResourceRecord(
            "network",
            f"{project}_sandbox",
            {
                **owner,
                "com.docker.compose.project": project,
                "com.docker.compose.network": "sandbox",
            },
        )
    )
    for logical_name in (
        "runner-state",
        "runner-evidence",
        "checkout-data",
        "payments-data",
        "inventory-data",
    ):
        records.append(
            ResourceRecord(
                "volume",
                f"{project}_{logical_name}",
                {
                    **owner,
                    "com.docker.compose.project": project,
                    "com.docker.compose.volume": logical_name,
                },
            )
        )
    return tuple(sorted(records, key=lambda item: (item.kind, item.name)))


def validate_resource_mode(
    mode: str,
    state: ResourceState,
    *,
    run_id: str,
    source_revision: str,
    claim_phase: str | None = None,
    runner_existed: bool = False,
) -> ResourceValidation:
    if mode not in {"fresh", "resume"}:
        raise PreflightError("resources.mode: expected fresh or resume")
    if mode == "fresh" and claim_phase in {None, "PRELAUNCH"}:
        if state.records:
            first = sorted(state.records, key=lambda item: (item.kind, item.name))[0]
            raise PreflightError(
                f"resources.fresh: existing {first.kind} collision {first.name}"
            )
        return ResourceValidation(False, ())

    expected = expected_resource_records(run_id, source_revision)
    expected_by_key = {(record.kind, record.name): record for record in expected}
    actual_by_key = {(record.kind, record.name): record for record in state.records}
    if len(actual_by_key) != len(state.records) or not set(actual_by_key) <= set(expected_by_key):
        raise PreflightError("resources.resume: resource subset contains a collision")
    for key, actual in actual_by_key.items():
        expected_record = expected_by_key[key]
        for label, expected_value in expected_record.labels.items():
            if actual.labels.get(label) != expected_value:
                raise PreflightError(
                    f"resources.resume: ownership mismatch for {actual.kind} {actual.name}"
                )
    resource_keys = tuple(
        f"{kind}:{name}" for kind, name in sorted(actual_by_key)
    )
    if claim_phase is None:
        if set(actual_by_key) != set(expected_by_key):
            raise PreflightError("resources.resume: resource set is missing or contains a collision")
        return ResourceValidation(True, resource_keys)
    if claim_phase not in {"RUNNING", "PRESERVED", "PUBLISHED"}:
        raise PreflightError("resources.lifecycle: unsupported claim phase")
    project = project_scope(run_id)
    runner_key = ("container", f"{project}-graph-runner-1")
    observed_runner = runner_existed or runner_key in actual_by_key
    if claim_phase in {"RUNNING", "PRESERVED"} and observed_runner:
        required_volumes = {
            ("volume", f"{project}_{logical_name}")
            for logical_name in (
                "runner-state",
                "runner-evidence",
                "checkout-data",
                "payments-data",
                "inventory-data",
            )
        }
        if not required_volumes <= set(actual_by_key):
            raise PreflightError(
                "resources.resume: runner history requires all five durable volumes"
            )
    return ResourceValidation(observed_runner, resource_keys)


def file_digest(path: Path) -> str:
    """Return a SHA-256 content digest while rejecting indirection."""

    if _is_link_or_junction(path):
        raise PreflightError(f"build input symlink or junction rejected: {path.name}")
    try:
        payload = path.read_bytes()
    except (FileNotFoundError, IsADirectoryError, OSError) as exc:
        raise PreflightError(f"build input unavailable: {path.name}") from exc
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def load_sandbox_case(cases_root: Path, case_id: str) -> SandboxCase:
    """Load one frozen case document and reject drift before Compose rendering."""

    if case_id not in CASE_DIGESTS or not IDENTITY_RE.fullmatch(case_id):
        raise PreflightError("case_id: unknown frozen case")
    _reject_path_indirection(cases_root)
    root = cases_root.resolve(strict=True)
    if not root.is_dir():
        raise PreflightError("cases: expected directory")
    observed_names = {
        path.name
        for path in root.iterdir()
        if path.is_file() and not _is_link_or_junction(path)
    }
    expected_names = {f"{name}.json" for name in CASE_DIGESTS}
    if observed_names != expected_names or any(
        _is_link_or_junction(path) for path in root.iterdir()
    ):
        raise PreflightError("cases: exact frozen case set required")
    path = root / f"{case_id}.json"
    if _is_link_or_junction(path) or not path.is_file():
        raise PreflightError("case document: regular frozen file required")
    try:
        payload = path.read_bytes()
        document = json.loads(payload.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PreflightError("case document: invalid JSON") from exc
    digest = hashlib.sha256(payload).hexdigest()
    if digest != CASE_DIGESTS[case_id]:
        raise PreflightError("case document: frozen digest mismatch")
    case = _mapping(document, "case document")
    if set(case) != {
        "case_version",
        "case_id",
        "service_fixtures",
        "checkout",
        "model_fixture",
        "budgets",
    }:
        raise PreflightError("case document: closed top-level schema required")
    if case.get("case_version") != CASE_VERSION or case.get("case_id") != case_id:
        raise PreflightError("case document: identity or version mismatch")
    fixtures = _mapping(case.get("service_fixtures"), "case service_fixtures")
    if set(fixtures) != {"checkout", "payments", "inventory"}:
        raise PreflightError("case service_fixtures: exact service set required")
    allowed_effects = {
        "checkout": {"success"},
        "payments": {"success", "latency", "http_error", "ambiguous_after_commit", "duplicate"},
        "inventory": {"success", "http_error", "duplicate"},
    }
    for service in ("checkout", "payments", "inventory"):
        fixture = _mapping(fixtures[service], f"case service_fixtures.{service}")
        if set(fixture) != {"readiness", "effect"}:
            raise PreflightError(f"case service_fixtures.{service}: closed schema required")
        if fixture["readiness"] not in {"ready", "unavailable"}:
            raise PreflightError(f"case service_fixtures.{service}.readiness: unknown fixture")
        if fixture["effect"] not in allowed_effects[service]:
            raise PreflightError(f"case service_fixtures.{service}.effect: unknown fixture")
    checkout = _mapping(case.get("checkout"), "case checkout")
    if set(checkout) != {"order_id", "amount_cents", "currency", "items"}:
        raise PreflightError("case checkout: closed schema required")
    if (
        not isinstance(checkout["order_id"], str)
        or not IDENTITY_RE.fullmatch(checkout["order_id"])
        or isinstance(checkout["amount_cents"], bool)
        or not isinstance(checkout["amount_cents"], int)
        or checkout["amount_cents"] <= 0
        or checkout["currency"] != "USD"
        or not isinstance(checkout["items"], list)
        or not checkout["items"]
        or len(checkout["items"]) > 16
    ):
        raise PreflightError("case checkout: invalid bounded request")
    for item in checkout["items"]:
        closed_item = _mapping(item, "case checkout item")
        if (
            set(closed_item) != {"sku", "quantity"}
            or not isinstance(closed_item["sku"], str)
            or not IDENTITY_RE.fullmatch(closed_item["sku"])
            or isinstance(closed_item["quantity"], bool)
            or not isinstance(closed_item["quantity"], int)
            or not 0 < closed_item["quantity"] <= 100
        ):
            raise PreflightError("case checkout item: invalid closed item")
    model_fixture = _mapping(case.get("model_fixture"), "case model_fixture")
    if set(model_fixture) != {"plan_class", "token_count"} or model_fixture != {
        "plan_class": "checkout",
        "token_count": 64,
    }:
        raise PreflightError("case model_fixture: exact deterministic fixture required")
    budgets = _mapping(case.get("budgets"), "case budgets")
    limits = {
        "attempts": 8,
        "wall_time_ms": 120000,
        "model_calls": 1,
        "tokens": 64,
        "spend_micro_usd": 0,
    }
    if set(budgets) != set(limits):
        raise PreflightError("case budgets: exact budget set required")
    for name, limit in limits.items():
        counter = _mapping(budgets[name], f"case budgets.{name}")
        if set(counter) != {"limit", "consumed"} or counter != {
            "limit": limit,
            "consumed": 0,
        }:
            raise PreflightError(f"case budgets.{name}: exact initial counter required")
    return SandboxCase(case_id=case_id, digest=digest, document=case)


def build_context_digest(sandbox_root: Path) -> str:
    """Digest the deliberately tiny Docker context declared by ``.dockerignore``."""

    root = sandbox_root.resolve(strict=True)
    candidates = [root / ".dockerignore"]
    for component in ("runner", "services", "cases"):
        component_root = root / component
        if not component_root.is_dir():
            raise PreflightError(f"build context missing directory: {component}")
        if _is_link_or_junction(component_root):
            raise PreflightError(f"build context symlink or junction rejected: {component}")
        for path in component_root.rglob("*"):
            if _is_link_or_junction(path):
                raise PreflightError(
                    "build context symlink or junction rejected: "
                    f"{path.relative_to(root).as_posix()}"
                )
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                candidates.append(path)
    for relative in (
        "tests/contract/test_services_contract.py",
        "tests/contract/test_runner_contract.py",
        "tests/integration/test_services_integration.py",
        "tests/integration/test_runner_integration.py",
    ):
        test_input = root / relative
        if not test_input.is_file():
            raise PreflightError(f"build context missing required file: {relative}")
        candidates.append(test_input)
    recovery_root = root / "tests" / "recovery"
    if not recovery_root.is_dir():
        raise PreflightError("build context missing required directory: tests/recovery")
    recovery_files = []
    for path in recovery_root.rglob("*"):
        if _is_link_or_junction(path):
            raise PreflightError(
                "build context symlink or junction rejected: "
                f"{path.relative_to(root).as_posix()}"
            )
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
            recovery_files.append(path)
    if not recovery_files:
        raise PreflightError("build context missing runner recovery tests")
    candidates.extend(recovery_files)

    digest = hashlib.sha256()
    for path in sorted(candidates, key=lambda candidate: candidate.relative_to(root).as_posix()):
        if _is_link_or_junction(path):
            raise PreflightError(
                f"build context symlink or junction rejected: {path.relative_to(root).as_posix()}"
            )
        relative = path.relative_to(root).as_posix().encode("utf-8")
        payload = path.read_bytes()
        digest.update(relative)
        digest.update(b"\0")
        digest.update(str(len(payload)).encode("ascii"))
        digest.update(b"\0")
        digest.update(payload)
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def dockerfile_base_references(path: Path) -> tuple[str, ...]:
    if _is_link_or_junction(path):
        raise PreflightError(f"Dockerfile symlink or junction rejected: {path}")
    references: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        tokens = line.split()
        if tokens[0].upper() == "FROM" and len(tokens) >= 2:
            references.append(tokens[1])
    if not references:
        raise PreflightError(f"Dockerfile has no FROM instruction: {path.name}")
    return tuple(references)


def validate_preflight(
    model: Mapping[str, Any],
    image_lock: Mapping[str, Any],
    *,
    sandbox_root: Path,
    source_revision: str,
    run_id: str,
    sandbox_case: SandboxCase,
    profile: str,
    docker: DockerBoundary,
) -> None:
    """Validate the rendered runtime model without causing a Docker effect."""

    status = docker.status()
    if not status.reachable:
        raise PreflightError("docker.daemon: Linux Docker daemon is unavailable")
    if status.os_type.lower() != "linux":
        raise PreflightError(f"docker.os: expected linux, got {status.os_type or 'unknown'}")
    if not status.compose_json:
        raise PreflightError("docker.compose: JSON Compose rendering is unavailable")
    if not REVISION_RE.fullmatch(source_revision):
        raise PreflightError("source_revision: expected lowercase 40-hex revision")
    if profile not in {"default", "saturation"}:
        raise PreflightError(f"profile: unsupported profile {profile!r}")
    if not isinstance(model, Mapping):
        raise PreflightError("compose model: expected JSON object")
    _reject_unresolved(model)

    top_keys = set(model)
    if top_keys != TOP_LEVEL_KEYS:
        raise PreflightError(
            f"top-level keys: expected {sorted(TOP_LEVEL_KEYS)}, got {sorted(top_keys)}"
        )
    project = project_scope(run_id)
    if model.get("name") != project:
        raise PreflightError(f"name: expected run-scoped project {project}")

    services = _mapping(model.get("services"), "services")
    expected_services = SATURATION_SERVICES if profile == "saturation" else DEFAULT_SERVICES
    if set(services) != expected_services:
        raise PreflightError(
            f"services.allowlist: expected {sorted(expected_services)}, got {sorted(services)}"
        )
    _validate_networks(
        model.get("networks"), run_id=run_id, source_revision=source_revision
    )
    _validate_volumes(
        model.get("volumes"), run_id=run_id, source_revision=source_revision
    )
    locked_images = _validate_image_lock(
        image_lock,
        sandbox_root=sandbox_root,
        source_revision=source_revision,
    )

    observed_images: dict[str, str] = {}
    for service_name in sorted(services):
        service = _mapping(services[service_name], f"services.{service_name}")
        logical_image = "runner" if service_name == "graph-runner" else "services"
        _validate_service(
            service_name,
            service,
            source_revision=source_revision,
            run_id=run_id,
            sandbox_case=sandbox_case,
            profile=profile,
        )
        image_id = service.get("image")
        if not isinstance(image_id, str) or not IMAGE_ID_RE.fullmatch(image_id):
            raise PreflightError(
                f"services.{service_name}.image: expected lowercase local sha256 image ID"
            )
        if image_id != locked_images[logical_image]:
            raise PreflightError(f"images.lock.{logical_image}.image_id: runtime model mismatch")
        observed_images[logical_image] = image_id

    if set(observed_images) != {"runner", "services"}:
        raise PreflightError("images.lock: both runner and services images are required")
    if observed_images["runner"] == observed_images["services"]:
        raise PreflightError("images.lock: runner and services images must be separate")
    for logical_name, image_id in sorted(observed_images.items()):
        metadata = docker.inspect_image(image_id)
        if metadata.image_id != image_id:
            raise PreflightError(f"images.lock.{logical_name}.image_id: local image ID mismatch")
        if metadata.platform != PLATFORM:
            raise PreflightError(
                f"images.lock.{logical_name}.platform: expected {PLATFORM}, got {metadata.platform}"
            )
        if metadata.entrypoint:
            raise PreflightError(f"images.lock.{logical_name}.config.Entrypoint: forbidden")
        if metadata.declared_volumes:
            raise PreflightError(f"images.lock.{logical_name}.config.Volumes: forbidden")


def _validate_image_lock(
    image_lock: Mapping[str, Any], *, sandbox_root: Path, source_revision: str
) -> dict[str, str]:
    if not isinstance(image_lock, Mapping):
        raise PreflightError("images.lock: expected JSON object")
    if set(image_lock) != {"lock_version", "images"}:
        raise PreflightError("images.lock: unexpected or missing top-level field")
    if image_lock.get("lock_version") != LOCK_VERSION:
        raise PreflightError(f"images.lock.lock_version: expected {LOCK_VERSION}")
    images = _mapping(image_lock.get("images"), "images.lock.images")
    if set(images) != {"runner", "services"}:
        raise PreflightError("images.lock.images: expected runner and services records")

    context_digest = build_context_digest(sandbox_root)
    locked_images: dict[str, str] = {}
    expected_fields = {
        "logical_name",
        "platform",
        "source_revision",
        "dockerfile_digest",
        "build_context_digest",
        "base_reference",
        "image_id",
    }
    for logical_name in ("runner", "services"):
        record = _mapping(images[logical_name], f"images.lock.{logical_name}")
        if set(record) != expected_fields:
            raise PreflightError(f"images.lock.{logical_name}: unexpected or missing field")
        expected_values = {
            "logical_name": logical_name,
            "platform": PLATFORM,
            "source_revision": source_revision,
            "base_reference": BASE_REFERENCE,
            "build_context_digest": context_digest,
            "dockerfile_digest": file_digest(sandbox_root / logical_name / "Dockerfile"),
        }
        for field, expected in expected_values.items():
            if record.get(field) != expected:
                raise PreflightError(f"images.lock.{logical_name}.{field}: lock mismatch")
        dockerfile = sandbox_root / logical_name / "Dockerfile"
        if any(reference != BASE_REFERENCE for reference in dockerfile_base_references(dockerfile)):
            raise PreflightError(f"images.lock.{logical_name}.base_reference: Dockerfile mismatch")
        image_id = record.get("image_id")
        if not isinstance(image_id, str) or not IMAGE_ID_RE.fullmatch(image_id):
            raise PreflightError(f"images.lock.{logical_name}.image_id: expected lowercase sha256 ID")
        locked_images[logical_name] = image_id
    return locked_images


def _validate_service(
    service_name: str,
    service: Mapping[str, Any],
    *,
    source_revision: str,
    run_id: str,
    sandbox_case: SandboxCase,
    profile: str,
) -> None:
    for forbidden in sorted(FORBIDDEN_SERVICE_KEYS):
        if forbidden in service:
            raise PreflightError(f"services.{service_name}.{forbidden}: forbidden runtime field")
    unexpected = set(service) - SERVICE_KEYS
    if unexpected:
        key = sorted(unexpected)[0]
        raise PreflightError(f"services.{service_name}.{key}: unexpected runtime field")

    expected_keys = set(SERVICE_KEYS) - {"profiles", "volumes", "depends_on", "healthcheck"}
    if service_name == "graph-runner":
        expected_keys |= {"volumes", "depends_on"}
    elif service_name in {"checkout", "payments", "inventory"}:
        expected_keys |= {"volumes", "healthcheck"}
    if service_name == "loadgen":
        expected_keys.add("profiles")
    actual_keys = set(service)
    if actual_keys != expected_keys:
        missing = sorted(expected_keys - actual_keys)
        extra = sorted(actual_keys - expected_keys)
        rejected_field = extra[0] if extra else missing[0]
        disposition = "unexpected" if extra else "missing"
        raise PreflightError(f"services.{service_name}.{rejected_field}: {disposition} runtime field")

    if service.get("command") != list(COMMANDS[service_name]):
        raise PreflightError(f"services.{service_name}.command: expected exec-form reviewed command")
    if service.get("entrypoint") != []:
        raise PreflightError(f"services.{service_name}.entrypoint: explicit empty override required")
    expected_labels = ownership_labels(run_id, source_revision)
    if service.get("labels") != expected_labels:
        raise PreflightError(f"services.{service_name}.labels: exact ownership labels required")
    if service.get("working_dir") != "/app":
        raise PreflightError(f"services.{service_name}.working_dir: expected /app")
    if service.get("restart") != "no":
        raise PreflightError(f"services.{service_name}.restart: expected no")
    if service.get("stop_grace_period") != "10s":
        raise PreflightError(f"services.{service_name}.stop_grace_period: expected 10s")
    if service.get("read_only") is not True:
        raise PreflightError(f"services.{service_name}.read_only: required true")
    if service.get("cap_drop") != ["ALL"]:
        raise PreflightError(f"services.{service_name}.cap_drop: expected [ALL]")
    if service.get("security_opt") != ["no-new-privileges:true"]:
        raise PreflightError(
            f"services.{service_name}.security_opt: no-new-privileges:true required"
        )
    _validate_user(service_name, service.get("user"))
    _bounded_number(service_name, "cpus", service.get("cpus"), maximum=MAX_CPUS)
    _bounded_memory(service_name, service.get("mem_limit"))
    _bounded_integer(service_name, "pids_limit", service.get("pids_limit"), maximum=MAX_PIDS)
    _validate_environment(
        service_name,
        service.get("environment"),
        source_revision,
        sandbox_case=sandbox_case,
    )
    _validate_service_network(service_name, service.get("networks"))
    _validate_tmpfs(service_name, service.get("tmpfs"))

    if service_name == "graph-runner":
        _validate_dependencies(service.get("depends_on"))
        _validate_runner_mounts(service.get("volumes"))
    elif service_name in {"checkout", "payments", "inventory"}:
        _validate_healthcheck(service_name, service.get("healthcheck"))
        _validate_service_data_mount(service_name, service.get("volumes"))
    if service_name == "loadgen":
        if profile != "saturation" or service.get("profiles") != ["saturation"]:
            raise PreflightError("services.loadgen.profiles: saturation only")


def _validate_user(service_name: str, value: Any) -> None:
    if not isinstance(value, str):
        raise PreflightError(f"services.{service_name}.user: numeric non-root user required")
    match = NUMERIC_USER_RE.fullmatch(value)
    if not match or int(match.group("uid")) == 0:
        raise PreflightError(f"services.{service_name}.user: numeric non-root user required")
    if match.group("gid") is not None and int(match.group("gid")) == 0:
        raise PreflightError(f"services.{service_name}.user: numeric non-root group required")
    expected = "65532:65532" if service_name == "graph-runner" else "10001:10001"
    if service_name in DEFAULT_SERVICES and value != expected:
        raise PreflightError(f"services.{service_name}.user: expected {expected}")


def _bounded_number(service: str, field: str, value: Any, *, maximum: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PreflightError(f"services.{service}.{field}: positive numeric limit required")
    if not 0 < float(value) <= maximum:
        raise PreflightError(f"services.{service}.{field}: limit exceeds 0..{maximum:g}")


def _bounded_integer(service: str, field: str, value: Any, *, maximum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 < value <= maximum:
        raise PreflightError(f"services.{service}.{field}: integer limit exceeds 0..{maximum}")


def _bounded_memory(service: str, value: Any) -> None:
    if not isinstance(value, str) or not value.isascii() or not value.isdigit():
        raise PreflightError(f"services.{service}.mem_limit: rendered integer string required")
    parsed = int(value)
    if str(parsed) != value or not 0 < parsed <= MAX_MEMORY_BYTES:
        raise PreflightError(
            f"services.{service}.mem_limit: integer limit exceeds 0..{MAX_MEMORY_BYTES}"
        )


def _validate_environment(
    service_name: str,
    value: Any,
    source_revision: str,
    *,
    sandbox_case: SandboxCase,
) -> None:
    environment = _mapping(value, f"services.{service_name}.environment")
    for name in sorted(environment):
        if CREDENTIAL_NAME_RE.search(name):
            raise PreflightError(f"services.{service_name}.environment.{name}: credential-like name")
    expected_names = ENVIRONMENT_KEYS[service_name]
    if set(environment) != expected_names:
        unexpected = sorted(set(environment) - expected_names)
        missing = sorted(expected_names - set(environment))
        field = unexpected[0] if unexpected else missing[0]
        raise PreflightError(
            f"services.{service_name}.environment.{field}: unexpected or missing variable"
        )
    for name, raw_value in environment.items():
        if not isinstance(raw_value, str):
            raise PreflightError(f"services.{service_name}.environment.{name}: string required")
        if INTERPOLATION_RE.search(raw_value):
            raise PreflightError(
                f"unresolved interpolation: services.{service_name}.environment.{name}"
            )
    for name, expected in EXPECTED_INTERNAL_VALUES[service_name].items():
        if environment[name] != expected:
            raise PreflightError(
                f"services.{service_name}.environment.{name}: expected internal sandbox value"
            )
    if environment["PYTHONDONTWRITEBYTECODE"] != "1" or environment["PYTHONUNBUFFERED"] != "1":
        raise PreflightError(f"services.{service_name}.environment: Python runtime controls required")

    if service_name == "graph-runner":
        if environment["SOURCE_REVISION"] != source_revision:
            raise PreflightError("services.graph-runner.environment.SOURCE_REVISION: revision mismatch")
        if not IDENTITY_RE.fullmatch(environment["RUN_ID"]):
            raise PreflightError("services.graph-runner.environment.RUN_ID: invalid identity")
        if environment["CASE_ID"] != sandbox_case.case_id:
            raise PreflightError("services.graph-runner.environment.CASE_ID: case mismatch")
        if environment["CASE_DIGEST"] != sandbox_case.digest:
            raise PreflightError("services.graph-runner.environment.CASE_DIGEST: digest mismatch")
        if environment["APPROVAL_FIXTURE"] not in {"APPROVED", "REJECTED", "TIMEOUT"}:
            raise PreflightError("services.graph-runner.environment.APPROVAL_FIXTURE: invalid fixture")
        _bounded_environment_integer(
            environment, "RUN_TIMEOUT_SECONDS", maximum=MAX_RUN_SECONDS, service=service_name
        )
    elif service_name in {"checkout", "payments", "inventory"}:
        projected = sandbox_case.service_fixtures[service_name]
        if environment["SANDBOX_CASE_ID"] != sandbox_case.case_id:
            raise PreflightError(
                f"services.{service_name}.environment.SANDBOX_CASE_ID: case mismatch"
            )
        if environment["READINESS_FIXTURE"] != projected["readiness"]:
            raise PreflightError(
                f"services.{service_name}.environment.READINESS_FIXTURE: projection mismatch"
            )
        if environment["EFFECT_FIXTURE"] != projected["effect"]:
            raise PreflightError(
                f"services.{service_name}.environment.EFFECT_FIXTURE: projection mismatch"
            )
    if service_name == "checkout":
        _bounded_environment_integer(
            environment, "DEPENDENCY_TIMEOUT_SECONDS", maximum=5, service=service_name
        )
    elif service_name == "loadgen":
        if not IDENTITY_RE.fullmatch(environment["RUN_ID"]):
            raise PreflightError("services.loadgen.environment.RUN_ID: invalid identity")
        _bounded_environment_integer(
            environment, "RUN_TIMEOUT_SECONDS", maximum=MAX_RUN_SECONDS, service=service_name
        )


def _bounded_environment_integer(
    environment: Mapping[str, Any], name: str, *, maximum: int, service: str
) -> None:
    raw_value = environment[name]
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise PreflightError(f"services.{service}.environment.{name}: integer required") from exc
    if str(value) != raw_value or not 0 < value <= maximum:
        raise PreflightError(f"services.{service}.environment.{name}: limit exceeds 0..{maximum}")


def _validate_service_network(service_name: str, value: Any) -> None:
    networks = _mapping(value, f"services.{service_name}.networks")
    if set(networks) != {"sandbox"} or networks["sandbox"] is not None:
        raise PreflightError(f"services.{service_name}.networks: sandbox only, without aliases")


def _validate_tmpfs(service_name: str, value: Any) -> None:
    if value != ["/tmp:size=16777216,mode=1777"]:
        raise PreflightError(f"services.{service_name}.tmpfs: expected bounded /tmp tmpfs")


def _validate_dependencies(value: Any) -> None:
    dependencies = _mapping(value, "services.graph-runner.depends_on")
    if set(dependencies) != {"checkout", "payments", "inventory"}:
        raise PreflightError("services.graph-runner.depends_on: exact service set required")
    expected = {"condition": "service_healthy", "required": True}
    for name, declaration in dependencies.items():
        if declaration != expected:
            raise PreflightError(f"services.graph-runner.depends_on.{name}: unexpected declaration")


def _validate_runner_mounts(value: Any) -> None:
    if not isinstance(value, list) or len(value) != 2:
        raise PreflightError("services.graph-runner.volumes: exactly state and evidence required")
    volume_mounts = [mount for mount in value if isinstance(mount, Mapping) and mount.get("type") == "volume"]
    if len(volume_mounts) != 2:
        raise PreflightError("services.graph-runner.volumes: unexpected mount type or count")

    mounts_by_source = {mount.get("source"): mount for mount in volume_mounts}
    if set(mounts_by_source) != {"runner-state", "runner-evidence"}:
        if "runner-evidence" not in mounts_by_source:
            raise PreflightError(
                "services.graph-runner.volumes.evidence.source: expected runner-evidence"
            )
        raise PreflightError("services.graph-runner.volumes: exact sources required")
    state = mounts_by_source["runner-state"]
    expected_state = {
        "type": "volume",
        "source": "runner-state",
        "target": "/state",
    }
    if state != expected_state:
        raise PreflightError("services.graph-runner.volumes.state: unexpected volume")
    evidence = mounts_by_source["runner-evidence"]
    if evidence.get("target") != "/evidence":
        raise PreflightError("services.graph-runner.volumes.evidence.target: expected /evidence")
    expected_evidence = {
        "type": "volume",
        "source": "runner-evidence",
        "target": "/evidence",
    }
    if evidence != expected_evidence:
        raise PreflightError("services.graph-runner.volumes.evidence: unexpected volume")


def _validate_healthcheck(service_name: str, value: Any) -> None:
    healthcheck = _mapping(value, f"services.{service_name}.healthcheck")
    port = {"checkout": 8080, "payments": 8081, "inventory": 8082}[service_name]
    expected = {
        "test": [
            "CMD",
            "python",
            "-c",
            "import urllib.request; "
            f"r=urllib.request.urlopen('http://127.0.0.1:{port}/livez',timeout=0.5); "
            "raise SystemExit(0 if r.status == 200 else 1)",
        ],
        "interval": "2s",
        "timeout": "1s",
        "retries": 30,
        "start_period": "2s",
    }
    if healthcheck != expected:
        raise PreflightError(f"services.{service_name}.healthcheck: exact /livez probe required")


def _validate_service_data_mount(service_name: str, value: Any) -> None:
    expected = [
        {
            "type": "volume",
            "source": f"{service_name}-data",
            "target": "/data",
        }
    ]
    if value != expected:
        raise PreflightError(
            f"services.{service_name}.volumes: exact durable data mount required"
        )


def _validate_evidence_path(evidence_root: Path, evidence_source: Path) -> None:
    root_absolute = Path(os.path.abspath(evidence_root))
    source_absolute = Path(os.path.abspath(evidence_source))
    try:
        root_resolved = root_absolute.resolve(strict=True)
        source_resolved = source_absolute.resolve(strict=True)
    except (FileNotFoundError, OSError) as exc:
        raise PreflightError("evidence path: root and run directory must already exist") from exc
    if not root_resolved.is_dir() or not source_resolved.is_dir():
        raise PreflightError("evidence path: root and run directory must be directories")
    if _is_link_or_junction(root_absolute):
        raise PreflightError("evidence path: root symlink or junction rejected")
    try:
        lexical_relative = source_absolute.relative_to(root_absolute)
        resolved_relative = source_resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise PreflightError("evidence path: source is outside evidence root") from exc
    if not lexical_relative.parts or not resolved_relative.parts:
        raise PreflightError("evidence path: source must be a strict descendant of evidence root")
    current = root_absolute
    for part in lexical_relative.parts:
        current = current / part
        if _is_link_or_junction(current):
            raise PreflightError("evidence path: symlink or junction rejected")


def _validate_networks(value: Any, *, run_id: str, source_revision: str) -> None:
    networks = _mapping(value, "networks")
    if set(networks) != {"sandbox"}:
        raise PreflightError("networks.allowlist: expected only sandbox")
    sandbox = _mapping(networks["sandbox"], "networks.sandbox")
    if "external" in sandbox:
        raise PreflightError("networks.sandbox.external: external attachment forbidden")
    if set(sandbox) != {"name", "ipam", "internal", "labels"}:
        raise PreflightError("networks.sandbox: unexpected or missing field")
    project = project_scope(run_id)
    if sandbox.get("name") != f"{project}_sandbox":
        raise PreflightError("networks.sandbox.name: expected project-scoped network")
    if sandbox.get("internal") is not True:
        raise PreflightError("networks.sandbox.internal: required true")
    if sandbox.get("ipam") != {}:
        raise PreflightError("networks.sandbox.ipam: custom addressing forbidden")
    if sandbox.get("labels") != ownership_labels(run_id, source_revision):
        raise PreflightError("networks.sandbox.labels: exact ownership labels required")


def _validate_volumes(value: Any, *, run_id: str, source_revision: str) -> None:
    volumes = _mapping(value, "volumes")
    expected_names = {
        "runner-state",
        "runner-evidence",
        "checkout-data",
        "payments-data",
        "inventory-data",
    }
    if set(volumes) != expected_names:
        raise PreflightError("volumes.allowlist: expected exact five-volume durable set")
    project = project_scope(run_id)
    for logical_name in sorted(expected_names):
        declaration = _mapping(volumes[logical_name], f"volumes.{logical_name}")
        if set(declaration) != {"name", "labels"}:
            raise PreflightError(f"volumes.{logical_name}: external or unexpected field")
        if declaration.get("name") != f"{project}_{logical_name}":
            raise PreflightError(f"volumes.{logical_name}.name: expected project-scoped volume")
        if declaration.get("labels") != ownership_labels(run_id, source_revision):
            raise PreflightError(f"volumes.{logical_name}.labels: exact ownership labels required")


def _reject_unresolved(value: Any, path: str = "compose") -> None:
    if isinstance(value, str) and INTERPOLATION_RE.search(value):
        raise PreflightError(f"unresolved interpolation: {path}")
    if isinstance(value, Mapping):
        for key, nested in value.items():
            _reject_unresolved(nested, f"{path}.{key}")
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            _reject_unresolved(nested, f"{path}[{index}]")


def _mapping(value: Any, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PreflightError(f"{path}: expected object")
    if not all(isinstance(key, str) for key in value):
        raise PreflightError(f"{path}: string keys required")
    return value


def _is_link_or_junction(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(os.path, "isjunction", None)
    if is_junction and is_junction(path):
        return True
    try:
        attributes = os.lstat(path).st_file_attributes
    except (AttributeError, FileNotFoundError, OSError):
        return False
    return bool(attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def _reject_path_indirection(path: Path) -> None:
    candidate = Path(os.path.abspath(path))
    if not candidate.exists():
        raise PreflightError(f"path unavailable: {candidate.name}")
    current = candidate
    while True:
        if _is_link_or_junction(current):
            raise PreflightError(f"path symlink, junction, or reparse point rejected: {current}")
        if current.parent == current:
            break
        current = current.parent


def _load_json(path: Path, label: str) -> Mapping[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, json.JSONDecodeError) as exc:
        raise PreflightError(f"{label}: unreadable JSON") from exc
    return _mapping(payload, label)


def render_compose(
    compose_file: Path,
    *,
    docker_context: str,
    image_lock: Mapping[str, Any],
    source_revision: str,
    run_id: str,
    sandbox_case: SandboxCase,
    approval_fixture: str,
    profile: str,
    timeout_seconds: int = 30,
    command_runner: CommandRunner = run_process,
    environ: Mapping[str, str] | None = None,
) -> Mapping[str, Any]:
    guard = b"activation_guard: graph-sandbox/activate.py/v1\n"
    try:
        source_bytes = compose_file.read_bytes()
    except OSError as exc:
        raise PreflightError("compose.render: guarded source is unavailable") from exc
    if not source_bytes.startswith(guard) or source_bytes.count(guard) != 1:
        raise PreflightError("compose.render: activation guard is missing or duplicated")
    guarded_body = source_bytes[len(guard) :]
    images = _mapping(image_lock.get("images"), "images.lock.images")
    runner = _mapping(images.get("runner"), "images.lock.runner")
    services = _mapping(images.get("services"), "images.lock.services")
    ambient = os.environ if environ is None else environ
    assert_no_ambient_docker_authority(ambient)
    project = project_scope(run_id)
    environment = scrub_environment(
        ambient,
        extra={
            "GRAPH_RUNNER_IMAGE_ID": str(runner.get("image_id", "")),
            "SYNTHETIC_SERVICES_IMAGE_ID": str(services.get("image_id", "")),
            "GRAPH_RUN_ID": run_id,
            "GRAPH_PROJECT_NAME": project,
            "GRAPH_SCOPE_HASH": project.removeprefix("graph-sandbox-v1-"),
            "SOURCE_REVISION": source_revision,
            "SANDBOX_CASE_ID": sandbox_case.case_id,
            "SANDBOX_CASE_DIGEST": sandbox_case.digest,
            "CHECKOUT_READINESS_FIXTURE": sandbox_case.service_fixtures["checkout"]["readiness"],
            "CHECKOUT_EFFECT_FIXTURE": sandbox_case.service_fixtures["checkout"]["effect"],
            "PAYMENTS_READINESS_FIXTURE": sandbox_case.service_fixtures["payments"]["readiness"],
            "PAYMENTS_EFFECT_FIXTURE": sandbox_case.service_fixtures["payments"]["effect"],
            "INVENTORY_READINESS_FIXTURE": sandbox_case.service_fixtures["inventory"]["readiness"],
            "INVENTORY_EFFECT_FIXTURE": sandbox_case.service_fixtures["inventory"]["effect"],
            "APPROVAL_FIXTURE": approval_fixture,
        },
    )
    temporary_root = Path(tempfile.mkdtemp(prefix="graph-sandbox-render-"))
    os.chmod(temporary_root, 0o700)
    unguarded_source = temporary_root / "runtime-template.yaml"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(unguarded_source, flags, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(guarded_body)
            stream.flush()
            os.fsync(stream.fileno())
        command = [
            "docker",
            "--context",
            docker_context,
            "compose",
            "--file",
            str(unguarded_source),
            "--project-name",
            project,
        ]
        if profile == "saturation":
            command.extend(("--profile", "saturation"))
        command.extend(("config", "--format", "json"))
        rendered = command_runner(
            command,
            environment=environment,
            timeout_seconds=timeout_seconds,
            stdin=None,
        )
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)
    if rendered.returncode != 0:
        raise PreflightError("compose.render: rendering failed")
    try:
        return _mapping(json.loads(rendered.stdout), "compose")
    except (TypeError, json.JSONDecodeError) as exc:
        raise PreflightError("compose.render: invalid JSON") from exc
