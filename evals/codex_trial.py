#!/usr/bin/env python3
"""Run one isolated, sanitized Codex/Terra ROUTE-001 trial.

Raw prompts, model output, stderr, hook payloads, runtime identifiers, credentials, and temporary
paths exist only inside this function's process and disposable directory.  Callers may persist only
``TrialResult.as_dict()``.  A setup, auth, timeout, output-limit, parser, or evidence failure is an
instrument ``INCONCLUSIVE`` result, never a routing PASS/FAIL.
"""
from __future__ import annotations

import dataclasses
import contextlib
import hashlib
import json
import os
import platform
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import codex_harness
import codex_hook_recorder
import codex_model_catalog
import codex_routing_grade
import codex_runtime
import codex_snapshot
import run_codex_routing


MAX_AUTH_BYTES = 4 * 1024 * 1024
MAX_PROCESS_OUTPUT_BYTES = 16 * 1024 * 1024
PROBE_TIMEOUT_SECONDS = 30
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
HOOK_BUNDLE_FILES = ("codex_harness.py", "codex_hook_recorder.py")


class TrialContractError(ValueError):
    """The requested probe is outside the fixed ROUTE-001 canary contract."""


class InstrumentError(RuntimeError):
    """A trusted executor boundary failed before a measurement could be made."""

    def __init__(self, reason_code: str, message: str) -> None:
        super().__init__(message)
        self.reason_code = reason_code


class CredentialEchoError(RuntimeError):
    """Trial output contains an exact sensitive value from the transient auth copy."""


@dataclass(frozen=True)
class AuthGuard:
    """Transient exact-string guard; sensitive values are excluded from repr and evidence."""

    sensitive_values: tuple[str, ...] = dataclasses.field(repr=False)

    def reject_output(self, text: str) -> None:
        if not isinstance(text, str):
            raise TypeError("auth output scan requires text")
        if any(value in text for value in self.sensitive_values):
            raise CredentialEchoError("trial output echoed an auth value")

    def reject_value(self, value: object) -> None:
        """Scan decoded JSON-compatible values, including keys and escaped strings."""

        pending = [value]
        seen: set[int] = set()
        while pending:
            child = pending.pop()
            if isinstance(child, str):
                self.reject_output(child)
                continue
            if isinstance(child, Mapping):
                identity = id(child)
                if identity in seen:
                    continue
                seen.add(identity)
                pending.extend(child.keys())
                pending.extend(child.values())
                continue
            if isinstance(child, Sequence) and not isinstance(child, (bytes, bytearray)):
                identity = id(child)
                if identity in seen:
                    continue
                seen.add(identity)
                pending.extend(child)

    def reject_jsonl(self, text: str) -> None:
        """Decode each valid JSONL record so JSON escapes cannot hide exact auth values."""

        self.reject_output(text)
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                value = json.loads(line, object_pairs_hook=lambda pairs: pairs)
            except json.JSONDecodeError:
                continue
            self.reject_value(value)

    def merged(self, other: "AuthGuard") -> "AuthGuard":
        if not isinstance(other, AuthGuard):
            raise TypeError("auth guards can only merge with auth guards")
        return AuthGuard(tuple(sorted(set(self.sensitive_values) | set(other.sensitive_values))))


@dataclass(frozen=True)
class TrialContract:
    scenario_id: str
    revision: str
    trial: int
    scenario_sha256: str
    prompt_sha256: str
    manifest_sha256: str
    prompt: str = dataclasses.field(repr=False)
    invocation_mode: str


@dataclass(frozen=True)
class CodexProbe:
    cli_version: str
    executable_sha256: str
    bundled_catalog: bytes = dataclasses.field(repr=False)


@dataclass(frozen=True)
class HookBundleReceipt:
    """Trusted copied-hook facts; the transient recorder path is never serialized."""

    file_count: int
    source_tree_sha256: str
    staged_tree_sha256: str
    recorder_path: Path = dataclasses.field(repr=False)

    def persistable_facts(self) -> dict[str, object]:
        return {
            "file_count": self.file_count,
            "source_tree_sha256": self.source_tree_sha256,
            "staged_tree_sha256": self.staged_tree_sha256,
        }


@dataclass(frozen=True)
class ProcessCapture:
    stdout: str = dataclasses.field(repr=False)
    stderr: str = dataclasses.field(repr=False)
    returncode: int
    duration_ms: int
    timed_out: bool
    output_limited: bool


@dataclass(frozen=True)
class TrialResult:
    scenario_id: str
    revision: str
    trial: int
    state: codex_routing_grade.VerdictState
    reason_codes: tuple[str, ...]
    manifest_sha256: str
    scenario_sha256: str
    prompt_sha256: str
    exact_revision: bool
    tool_policy: str
    invocation_mode: str
    runtime_facts: dict[str, object] | None = None
    trace_facts: dict[str, object] | None = None
    hook_facts: dict[str, object] | None = None
    verdict_facts: dict[str, object] | None = None

    def as_dict(self) -> dict[str, object]:
        """Return the only trial representation suitable for persistence."""

        authority = run_codex_routing.authority_facts(
            {}, exact_revision=self.exact_revision
        )
        codex_cli_version = codex_harness.CODEX_CLI_VERSION
        if self.runtime_facts is not None:
            observed_version = self.runtime_facts.get("codex_cli_version")
            if isinstance(observed_version, str) and observed_version:
                codex_cli_version = observed_version
        return {
            "schema_version": 1,
            "scenario": {
                "id": self.scenario_id,
                "revision": self.revision,
                "trial": self.trial,
                "manifest_sha256": self.manifest_sha256,
                "scenario_sha256": self.scenario_sha256,
                "prompt_sha256": self.prompt_sha256,
            },
            "configuration": {
                "provider": "openai-codex",
                "codex_cli_version": codex_cli_version,
                "model": codex_harness.MODEL,
                "reasoning_effort": codex_harness.REASONING_EFFORT,
                "sandbox": codex_harness.SANDBOX_MODE,
                "approval_policy": codex_harness.APPROVAL_POLICY,
                "timeout_s": codex_harness.TIMEOUT_SECONDS,
                "tool_policy": self.tool_policy,
                "invocation_mode": self.invocation_mode,
            },
            "state": self.state.value,
            "reason_codes": list(self.reason_codes),
            "runtime": self.runtime_facts,
            "trace": self.trace_facts,
            "hooks": self.hook_facts,
            "verdict": self.verdict_facts,
            "authority": authority,
        }


CommandRunner = Callable[..., subprocess.CompletedProcess[bytes]]
ProcessRunner = Callable[..., ProcessCapture]


def _is_symlink(path: Path) -> bool:
    return path.is_symlink()


def _assert_private_path(path: Path) -> None:
    if not path.exists() or _is_symlink(path):
        raise InstrumentError(
            "private-permissions-failed", "private path is missing or redirected"
        )
    if path.stat().st_mode & 0o077:
        raise InstrumentError(
            "private-permissions-failed", "private path grants group or other permissions"
        )


def _posix_private_mode(current_mode: int, *, directory: bool) -> int:
    if directory:
        return stat.S_IRWXU
    execute = stat.S_IXUSR if current_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH) else 0
    return stat.S_IRUSR | stat.S_IWUSR | execute


def _secure_directory(path: Path, *, recursive: bool = False) -> Path:
    """Create and verify a private POSIX tree."""

    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise InstrumentError(
            "private-permissions-failed", "private directory could not be created"
        ) from exc
    targets = [path]
    if recursive:
        targets.extend(sorted(path.rglob("*"), key=lambda item: str(item)))
    for target in targets:
        metadata = target.lstat()
        if (
            _is_symlink(target)
            or not (target.is_dir() or target.is_file())
            or (target.is_file() and getattr(metadata, "st_nlink", 1) != 1)
        ):
            raise InstrumentError(
                "private-permissions-failed", "private tree contains a redirected or special entry"
            )
        try:
            os.chmod(
                target,
                _posix_private_mode(
                    target.stat().st_mode, directory=target.is_dir()
                ),
            )
        except OSError as exc:
            raise InstrumentError(
                "private-permissions-failed", "private path mode could not be set"
            ) from exc
        _assert_private_path(target)
    return path


def _ordinary_file(path: Path, *, label: str, require_single_link: bool = True) -> Path:
    candidate = Path(path)
    try:
        metadata = candidate.lstat()
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise InstrumentError("unsafe-file-boundary", f"{label} is unavailable") from exc
    if (
        _is_symlink(candidate)
        or not candidate.is_file()
        or resolved != candidate.absolute()
        or (require_single_link and getattr(metadata, "st_nlink", 1) != 1)
    ):
        raise InstrumentError(
            "unsafe-file-boundary", f"{label} must be one ordinary private file"
        )
    return resolved


def _sha256_file(path: Path, *, label: str) -> str:
    source = _ordinary_file(path, label=label)
    digest = hashlib.sha256()
    try:
        before = source.stat()
        with source.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        after = source.stat()
    except OSError as exc:
        raise InstrumentError("unsafe-file-boundary", f"{label} could not be hashed") from exc
    if (
        before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or before.st_ino != after.st_ino
        or before.st_dev != after.st_dev
    ):
        raise InstrumentError("file-drift", f"{label} changed while it was hashed")
    return digest.hexdigest()


def _runtime_platform() -> str:
    return f"{sys.platform}-{platform.machine().casefold()}"


def _trusted_process_environment() -> dict[str, str]:
    """Return the fixed executable-resolution inputs for the Linux container."""

    return {
        "PATH": "/usr/bin:/bin",
        "COMSPEC": "/bin/sh",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }


def verify_python_runtime(
    runtime_profile: codex_runtime.RuntimeProfile,
) -> tuple[Path, str]:
    """Bind the evaluator and hook interpreter to the exact Linux runtime."""

    if (
        not isinstance(runtime_profile, codex_runtime.RuntimeProfile)
        or runtime_profile.runtime_kind != "linux-container"
        or runtime_profile.runtime_platform != "linux-x86_64"
    ):
        raise InstrumentError(
            "python-runtime-mismatch", "Linux container runtime profile is required"
        )
    executable = _ordinary_file(Path(sys.executable), label="Python runtime")
    digest = _sha256_file(executable, label="Python runtime")
    version = ".".join(str(item) for item in sys.version_info[:3])
    if (
        _runtime_platform() != runtime_profile.runtime_platform
        or version != runtime_profile.python_version
        or digest != runtime_profile.python_executable_sha256
        or executable != runtime_profile.python_executable_path
    ):
        raise InstrumentError(
            "python-runtime-mismatch",
            "running Python runtime does not match the immutable Linux profile",
        )
    return executable, digest


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _tree_digest(root: Path, names: Sequence[str]) -> str:
    entries: list[tuple[str, str]] = []
    for name in names:
        path = root / name
        entries.append((name, _sha256_file(path, label=f"evaluator {name}")))
    return _canonical_sha256(entries)


def _exact_hook_tree_digest(root: Path) -> str:
    """Hash the hook import directory only when it contains the two authorized files."""

    directory = Path(root)
    try:
        if _is_symlink(directory) or not directory.is_dir():
            raise InstrumentError(
                "hook-bundle-drift", "trusted hook bundle changed during trial"
            )
        entries = list(directory.iterdir())
    except OSError as exc:
        raise InstrumentError(
            "hook-bundle-drift", "trusted hook bundle changed during trial"
        ) from exc
    expected = set(HOOK_BUNDLE_FILES)
    if len(entries) != len(expected) or {entry.name for entry in entries} != expected:
        raise InstrumentError(
            "hook-bundle-drift", "trusted hook bundle changed during trial"
        )
    return _tree_digest(directory, HOOK_BUNDLE_FILES)


def _stable_file_bytes(path: Path, *, label: str, max_bytes: int) -> bytes:
    source = _ordinary_file(path, label=label)
    try:
        before = source.stat()
        if before.st_size <= 0 or before.st_size > max_bytes:
            raise InstrumentError("unsafe-file-boundary", f"{label} size is invalid")
        content = source.read_bytes()
        after = source.stat()
    except OSError as exc:
        raise InstrumentError("unsafe-file-boundary", f"{label} could not be read") from exc
    if (
        len(content) != before.st_size
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or before.st_ino != after.st_ino
        or before.st_dev != after.st_dev
    ):
        raise InstrumentError("file-drift", f"{label} changed while it was read")
    return content


def validate_trial_contract(
    scenario: Mapping[str, object],
    spec: codex_harness.TrialSpec,
    *,
    manifest_sha256: str,
    manifest_path: Path = run_codex_routing.MANIFEST_PATH,
    canary_probe_mode: str,
) -> TrialContract:
    """Bind the fixed canary scenario and coordinate to the evaluator manifest."""

    if not isinstance(spec, codex_harness.TrialSpec):
        raise TrialContractError("trial spec must be a TrialSpec")
    if not isinstance(manifest_sha256, str) or not SHA256_RE.fullmatch(manifest_sha256):
        raise TrialContractError("manifest digest must be one lowercase SHA-256")
    try:
        evaluator_manifest_sha256 = hashlib.sha256(
            _stable_file_bytes(
                manifest_path,
                label="Terra evaluator manifest",
                max_bytes=1024 * 1024,
            )
        ).hexdigest()
    except InstrumentError as exc:
        raise TrialContractError("evaluator manifest bytes could not be verified") from exc
    if manifest_sha256 != evaluator_manifest_sha256:
        raise TrialContractError("manifest digest does not match evaluator manifest bytes")
    scenario_id = scenario.get("id")
    if scenario_id != spec.scenario_id:
        raise TrialContractError("scenario id does not match the trial spec")
    if (
        scenario_id != run_codex_routing.CANARY_SCENARIO_ID
        or spec.revision != run_codex_routing.CURRENT_REVISION
        or spec.trial != run_codex_routing.CANARY_TRIAL
    ):
        raise TrialContractError("probe coordinate does not match the fixed canary")
    if scenario.get("mode") != "discovery" or scenario.get("split") != "regression":
        raise TrialContractError("scenario must be one discovery regression")
    scenario_sha256 = scenario.get("_source_sha256")
    if not isinstance(scenario_sha256, str) or not SHA256_RE.fullmatch(scenario_sha256):
        raise TrialContractError("scenario source digest is invalid")
    if scenario_sha256 != spec.scenario_sha256:
        raise TrialContractError("scenario digest does not match the manifest-bound trial spec")
    prompt = scenario.get("prompt")
    if not isinstance(prompt, str) or not prompt:
        raise TrialContractError("scenario prompt must be non-empty text")
    if canary_probe_mode not in run_codex_routing.CANARY_PROBE_MODES:
        raise TrialContractError("canary probe mode is invalid")
    if scenario.get("target") != {
        "kind": "skill",
        "name": run_codex_routing.CANARY_EXPLICIT_SKILL,
    }:
        raise TrialContractError("canary target does not match the fixed skill")
    if canary_probe_mode == "body":
        prompt = f"${run_codex_routing.CANARY_EXPLICIT_SKILL}\n\n{prompt}"
        invocation_mode = "explicit-skill-body-probe"
    else:
        prompt = f"{run_codex_routing.CANARY_DESCRIPTION_PROMPT_PREFIX}{prompt}"
        invocation_mode = "description-selection-probe"
    try:
        codex_harness.reject_credentials(prompt, location="scenario_prompt")
    except codex_harness.CredentialExposureError as exc:
        raise TrialContractError("scenario prompt contains credential-shaped text") from exc
    routing = scenario.get("routing")
    if not isinstance(routing, Mapping):
        raise TrialContractError("scenario routing contract is missing")
    if routing.get("scope") is not None:
        raise TrialContractError("fixed canary cannot request root routing scope")
    return TrialContract(
        scenario_id=str(scenario_id),
        revision=spec.revision,
        trial=spec.trial,
        scenario_sha256=scenario_sha256,
        prompt_sha256=hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        manifest_sha256=manifest_sha256,
        prompt=prompt,
        invocation_mode=invocation_mode,
    )


def scrubbed_environment(
    *,
    home: Path,
    codex_home: Path,
    temp: Path,
    source: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build an allowlisted environment and relocate every user-state directory."""

    del source
    env = _trusted_process_environment().copy()
    appdata = home / "appdata"
    localappdata = home / "localappdata"
    env.update(
        {
            "CODEX_HOME": str(codex_home),
            "HOME": str(home),
            "USERPROFILE": str(home),
            "APPDATA": str(appdata),
            "LOCALAPPDATA": str(localappdata),
            "TEMP": str(temp),
            "TMP": str(temp),
            "TMPDIR": str(temp),
            "NO_COLOR": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUTF8": "1",
        }
    )
    try:
        codex_harness.reject_credentials(env, location="child_environment")
    except codex_harness.CredentialExposureError as exc:
        raise InstrumentError(
            "credential-shaped-environment", "child environment contains credential-shaped text"
        ) from exc
    return env


def _private_write(path: Path, content: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise InstrumentError("create-only-boundary", "private destination already exists")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(path, flags, stat.S_IRUSR | stat.S_IWUSR)
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
    except OSError as exc:
        raise InstrumentError("create-only-boundary", "private file could not be created") from exc
    finally:
        if "descriptor" in locals() and descriptor >= 0:
            os.close(descriptor)
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError as exc:
        raise InstrumentError("private-permissions-failed", "private file mode could not be set") from exc


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, child in pairs:
        if key in value:
            raise ValueError("duplicate auth JSON key")
        value[key] = child
    return value


def _reject_json_constant(value: str) -> object:
    raise ValueError(f"invalid auth JSON constant {value}")


def _collect_sensitive_strings(value: object) -> tuple[str, ...]:
    found: set[str] = set()

    def visit(child: object) -> None:
        if isinstance(child, str):
            if len(child) >= 8:
                found.add(child)
            return
        if isinstance(child, Mapping):
            for nested in child.values():
                visit(nested)
            return
        if isinstance(child, list):
            for nested in child:
                visit(nested)

    visit(value)
    return tuple(sorted(found))


def _auth_guard_from_bytes(raw: bytes) -> AuthGuard:
    try:
        auth_value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise InstrumentError("auth-boundary-failed", "Codex auth is not strict JSON") from exc
    if not isinstance(auth_value, Mapping):
        raise InstrumentError("auth-boundary-failed", "Codex auth must be one JSON object")
    sensitive_values = _collect_sensitive_strings(auth_value)
    if not sensitive_values:
        raise InstrumentError(
            "auth-boundary-failed", "Codex auth contains no guardable string values"
        )
    return AuthGuard(sensitive_values=sensitive_values)


def load_auth_guard(source: Path) -> AuthGuard:
    """Read a stable auth file only to refresh the transient exact-output guard."""

    raw = _stable_file_bytes(
        Path(source), label="Codex auth", max_bytes=MAX_AUTH_BYTES
    )
    guard = _auth_guard_from_bytes(raw)
    del raw
    return guard


def copy_auth_file(source: Path, destination: Path) -> AuthGuard:
    """Copy one stable regular auth file without retaining its bytes or digest."""

    _secure_directory(destination.parent)
    origin = _ordinary_file(Path(source), label="Codex auth", require_single_link=True)
    try:
        before = origin.stat()
        if before.st_size <= 0 or before.st_size > MAX_AUTH_BYTES:
            raise InstrumentError("auth-boundary-failed", "Codex auth file size is invalid")
        raw = origin.read_bytes()
        after = origin.stat()
    except OSError as exc:
        raise InstrumentError("auth-boundary-failed", "Codex auth file could not be read") from exc
    if (
        len(raw) != before.st_size
        or before.st_size != after.st_size
        or before.st_mtime_ns != after.st_mtime_ns
        or before.st_ino != after.st_ino
        or before.st_dev != after.st_dev
        or getattr(after, "st_nlink", 1) != 1
    ):
        raise InstrumentError("auth-boundary-failed", "Codex auth file changed while copied")
    guard = _auth_guard_from_bytes(raw)
    _private_write(destination, raw)
    _assert_private_path(destination)
    try:
        copied = destination.read_bytes()
    except OSError as exc:
        raise InstrumentError("auth-boundary-failed", "Codex auth copy could not be verified") from exc
    if copied != raw:
        raise InstrumentError("auth-boundary-failed", "Codex auth copy differs from its source")
    del copied
    del raw
    return guard


def remove_auth_file(destination: Path) -> None:
    """Remove and verify absence of the disposable auth copy before parsing output."""

    target = _ordinary_file(
        Path(destination), label="disposable Codex auth", require_single_link=True
    )
    _assert_private_path(target)
    try:
        target.unlink()
    except OSError as exc:
        raise InstrumentError(
            "auth-copy-removal-failed", "disposable Codex auth could not be removed"
        ) from exc
    try:
        target.lstat()
    except FileNotFoundError:
        return
    except OSError as exc:
        raise InstrumentError(
            "auth-copy-removal-failed", "disposable Codex auth absence could not be verified"
        ) from exc
    raise InstrumentError(
        "auth-copy-removal-failed", "disposable Codex auth still exists after removal"
    )


def _hook_tree(files: Mapping[str, bytes]) -> str:
    return _canonical_sha256(
        [(name, hashlib.sha256(files[name]).hexdigest()) for name in sorted(files)]
    )


def copy_hook_bundle(source_root: Path, destination: Path) -> HookBundleReceipt:
    """Copy the exact trusted recorder and parser into one empty private directory."""

    source = Path(source_root).resolve(strict=True)
    target = Path(destination).resolve(strict=True)
    try:
        if _is_symlink(target) or not target.is_dir() or any(target.iterdir()):
            raise InstrumentError(
                "hook-bundle-boundary-failed",
                "hook bundle destination must be one empty ordinary directory",
            )
    except OSError as exc:
        raise InstrumentError(
            "hook-bundle-boundary-failed", "hook bundle destination could not be inspected"
        ) from exc
    source_files = {
        name: _stable_file_bytes(
            source / name, label=f"hook bundle source {name}", max_bytes=2 * 1024 * 1024
        )
        for name in HOOK_BUNDLE_FILES
    }
    source_tree = _hook_tree(source_files)
    for name, content in source_files.items():
        _private_write(target / name, content)
    _secure_directory(target, recursive=True)
    staged_files = {
        name: _stable_file_bytes(
            target / name, label=f"staged hook bundle {name}", max_bytes=2 * 1024 * 1024
        )
        for name in HOOK_BUNDLE_FILES
    }
    staged_tree = _exact_hook_tree_digest(target)
    if staged_files != source_files or staged_tree != source_tree:
        raise InstrumentError(
            "hook-bundle-boundary-failed", "staged hook bundle differs from trusted source"
        )
    return HookBundleReceipt(
        file_count=len(source_files),
        source_tree_sha256=source_tree,
        staged_tree_sha256=staged_tree,
        recorder_path=target / "codex_hook_recorder.py",
    )


def verify_hook_bundle(
    source_root: Path, bundle: HookBundleReceipt
) -> None:
    """Re-read source and staged hook bytes to close the hash-then-use window."""

    source_tree = _tree_digest(Path(source_root), HOOK_BUNDLE_FILES)
    staged_tree = _exact_hook_tree_digest(bundle.recorder_path.parent)
    if (
        source_tree != bundle.source_tree_sha256
        or staged_tree != bundle.staged_tree_sha256
        or source_tree != staged_tree
    ):
        raise InstrumentError("hook-bundle-drift", "trusted hook bundle changed during trial")


def _default_command_runner(
    command: tuple[str, ...],
    *,
    env: dict[str, str],
    timeout_s: int,
    cwd: Path,
) -> subprocess.CompletedProcess[bytes]:
    capture = launch_process(
        command,
        prompt="",
        cwd=cwd,
        env=env,
        timeout_s=timeout_s,
        output_limit=MAX_PROCESS_OUTPUT_BYTES,
    )
    if capture.timed_out or capture.output_limited:
        raise InstrumentError("codex-probe-failed", "Codex probe did not complete")
    return subprocess.CompletedProcess(
        list(command),
        capture.returncode,
        capture.stdout.encode("utf-8"),
        capture.stderr.encode("utf-8"),
    )


def probe_codex(
    executable: Path,
    env: Mapping[str, str],
    *,
    cwd: Path,
    expected_cli_version: str = codex_harness.CODEX_CLI_VERSION,
    command_runner: CommandRunner = _default_command_runner,
) -> CodexProbe:
    """Prove exact CLI bytes/version and return the local bundled catalog transiently."""

    codex_bin = _ordinary_file(Path(executable), label="Codex executable")
    executable_sha256 = _sha256_file(codex_bin, label="Codex executable")
    child_env = dict(env)
    version = command_runner(
        (str(codex_bin), "--version"),
        env=child_env,
        timeout_s=PROBE_TIMEOUT_SECONDS,
        cwd=Path(cwd),
    )
    try:
        version_stdout = version.stdout.decode("utf-8", errors="strict")
        version_stderr = version.stderr.decode("utf-8", errors="strict")
        codex_harness.reject_credentials(
            {"stdout": version_stdout, "stderr": version_stderr}, location="codex_version"
        )
    except (UnicodeDecodeError, codex_harness.CredentialExposureError) as exc:
        raise InstrumentError("codex-cli-version-mismatch", "Codex CLI version output is invalid") from exc
    if not isinstance(expected_cli_version, str) or not expected_cli_version:
        raise InstrumentError("codex-cli-version-mismatch", "Codex CLI version pin is invalid")
    expected = f"codex-cli {expected_cli_version}"
    if version.returncode != 0 or version_stdout.strip() != expected or version_stderr.strip():
        raise InstrumentError(
            "codex-cli-version-mismatch",
            f"Codex CLI version must be exactly {expected_cli_version}",
        )

    catalog = command_runner(
        (str(codex_bin), "debug", "models", "--bundled"),
        env=child_env,
        timeout_s=PROBE_TIMEOUT_SECONDS,
        cwd=Path(cwd),
    )
    try:
        catalog_stderr = catalog.stderr.decode("utf-8", errors="strict")
        codex_harness.reject_credentials(catalog_stderr, location="codex_catalog_stderr")
    except (UnicodeDecodeError, codex_harness.CredentialExposureError) as exc:
        raise InstrumentError("model-catalog-probe-failed", "Codex model catalog output is invalid") from exc
    if (
        catalog.returncode != 0
        or catalog_stderr.strip()
        or not catalog.stdout
        or len(catalog.stdout) > codex_model_catalog.MAX_CATALOG_BYTES
    ):
        raise InstrumentError(
            "model-catalog-probe-failed", "Codex bundled model catalog could not be read"
        )
    return CodexProbe(
        cli_version=expected_cli_version,
        executable_sha256=executable_sha256,
        bundled_catalog=bytes(catalog.stdout),
    )


def _open_private_capture(path: Path):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    flags |= getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, flags, stat.S_IRUSR | stat.S_IWUSR)
    return os.fdopen(descriptor, "wb")


def _spawn_bounded_process(
    command: tuple[str, ...],
    *,
    cwd: Path,
    env: dict[str, str],
    stdin: int,
    stdout: object,
    stderr: object,
) -> subprocess.Popen[bytes]:
    return subprocess.Popen(
        list(command),
        cwd=cwd,
        env=env,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        start_new_session=True,
    )


def _bounded_git_runner(
    command: Sequence[str],
    *,
    stdout: object,
    stderr: object,
    stdin: int,
    cwd: Path,
    env: Mapping[str, str],
    timeout: int,
    check: bool,
) -> subprocess.CompletedProcess[bytes]:
    """Run the pinned Git archive process inside the same kill-on-close boundary as Codex."""

    if (
        stdout is not subprocess.PIPE
        or stderr is not subprocess.PIPE
        or stdin is not subprocess.DEVNULL
        or check
    ):
        raise InstrumentError(
            "process-tree-boundary-failed", "Git runner received an unsupported process contract"
        )
    child_env = dict(env)
    temp = Path(child_env.get("TEMP", ""))
    if not temp.is_absolute():
        raise InstrumentError(
            "process-tree-boundary-failed", "Git runner requires a private absolute TEMP"
        )
    stdout_path = temp / f"git-stdout-{uuid.uuid4().hex}.bin"
    stderr_path = temp / f"git-stderr-{uuid.uuid4().hex}.bin"
    process: subprocess.Popen[bytes] | None = None
    timed_out = False
    terminated = False
    output_limit = codex_snapshot.MAX_ARCHIVE_BYTES + (1024 * 1024)
    try:
        with _open_private_capture(stdout_path) as stdout_stream, _open_private_capture(
            stderr_path
        ) as stderr_stream:
            process = _spawn_bounded_process(
                tuple(command),
                cwd=Path(cwd),
                env=child_env,
                stdin=subprocess.DEVNULL,
                stdout=stdout_stream,
                stderr=stderr_stream,
            )
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                if time.monotonic() >= deadline:
                    timed_out = True
                    _terminate_process_tree(process)
                    terminated = True
                    break
                try:
                    if stdout_path.stat().st_size + stderr_path.stat().st_size > output_limit:
                        _terminate_process_tree(process)
                        terminated = True
                        raise InstrumentError(
                            "process-output-limit",
                            "Git archive output exceeded its fixed bound",
                        )
                except OSError as exc:
                    _terminate_process_tree(process)
                    terminated = True
                    raise InstrumentError(
                        "process-capture-failed", "Git output capture could not be inspected"
                    ) from exc
                time.sleep(0.05)
            try:
                returncode = process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                _terminate_process_tree(process)
                terminated = True
                returncode = process.wait(timeout=10)
                timed_out = True
        if timed_out:
            raise subprocess.TimeoutExpired(tuple(command), timeout)
        if stdout_path.stat().st_size + stderr_path.stat().st_size > output_limit:
            raise InstrumentError(
                "process-output-limit", "Git archive output exceeded its fixed bound"
            )
        stdout_bytes = stdout_path.read_bytes()
        stderr_bytes = stderr_path.read_bytes()
        if len(stdout_bytes) + len(stderr_bytes) > output_limit:
            raise InstrumentError(
                "process-output-limit", "Git archive output exceeded its fixed bound"
            )
        return subprocess.CompletedProcess(
            list(command), returncode, stdout_bytes, stderr_bytes
        )
    except (InstrumentError, subprocess.TimeoutExpired):
        raise
    except (OSError, subprocess.SubprocessError) as exc:
        raise InstrumentError(
            "process-launch-failed", "Git archive process could not run"
        ) from exc
    finally:
        if process is not None:
            _close_process_boundary(process, terminated=terminated)
        for capture_path in (stdout_path, stderr_path):
            try:
                capture_path.unlink(missing_ok=True)
            except OSError:
                pass


def _terminate_process_tree(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except PermissionError as exc:
        raise InstrumentError(
            "process-tree-boundary-failed", "POSIX process tree could not be terminated"
        ) from exc


def _close_process_boundary(
    process: subprocess.Popen[bytes], *, terminated: bool = False
) -> None:
    """Kill remaining descendants when the POSIX process-group boundary closes."""

    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    except PermissionError as exc:
        # Tolerate only an idempotent close after a successful termination and reap. A first
        # close or a still-running leader may leave descendants alive and therefore fails closed.
        if not terminated or process.poll() is None:
            raise InstrumentError(
                "process-tree-boundary-failed",
                "POSIX process tree could not be signalled and may still be running",
            ) from exc


def launch_process(
    command: tuple[str, ...],
    *,
    prompt: str,
    cwd: Path,
    env: dict[str, str],
    timeout_s: int,
    output_limit: int,
) -> ProcessCapture:
    """Launch Codex with private bounded raw captures that are destroyed by the caller."""

    stdout_path = Path(env["TEMP"]) / f"stdout-{uuid.uuid4().hex}.jsonl"
    stderr_path = Path(env["TEMP"]) / f"stderr-{uuid.uuid4().hex}.txt"
    started = time.monotonic()
    timed_out = False
    terminated = False
    output_limited = False
    returncode = -1
    process: subprocess.Popen[bytes] | None = None
    try:
        with _open_private_capture(stdout_path) as stdout_stream, _open_private_capture(
            stderr_path
        ) as stderr_stream:
            process = _spawn_bounded_process(
                command,
                cwd=cwd,
                env=env,
                stdin=subprocess.PIPE,
                stdout=stdout_stream,
                stderr=stderr_stream,
            )
            assert process.stdin is not None
            try:
                process.stdin.write(prompt.encode("utf-8"))
                process.stdin.close()
            except (BrokenPipeError, OSError):
                try:
                    process.stdin.close()
                except OSError:
                    pass
            deadline = started + timeout_s
            while process.poll() is None:
                if time.monotonic() >= deadline:
                    timed_out = True
                    _terminate_process_tree(process)
                    terminated = True
                    break
                try:
                    if stdout_path.stat().st_size + stderr_path.stat().st_size > output_limit:
                        output_limited = True
                        _terminate_process_tree(process)
                        terminated = True
                        break
                except OSError:
                    _terminate_process_tree(process)
                    terminated = True
                    raise InstrumentError(
                        "process-capture-failed", "Codex output capture could not be inspected"
                    )
                time.sleep(0.05)
            try:
                returncode = process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                _terminate_process_tree(process)
                terminated = True
                returncode = process.wait(timeout=10)
                timed_out = True
    except InstrumentError:
        raise
    except (OSError, subprocess.SubprocessError) as exc:
        raise InstrumentError("process-launch-failed", "Codex trial process could not run") from exc
    finally:
        if process is not None:
            _close_process_boundary(process, terminated=terminated)
    duration_ms = max(0, int((time.monotonic() - started) * 1000))
    try:
        captured_bytes = stdout_path.stat().st_size + stderr_path.stat().st_size
    except OSError as exc:
        raise InstrumentError(
            "process-capture-failed", "Codex output capture could not be inspected"
        ) from exc
    if captured_bytes > output_limit:
        output_limited = True
        stdout_raw = b""
        stderr_raw = b""
    else:
        try:
            stdout_raw = stdout_path.read_bytes()
            stderr_raw = stderr_path.read_bytes()
        except OSError as exc:
            raise InstrumentError(
                "process-capture-failed", "Codex output capture could not be read"
            ) from exc
        if len(stdout_raw) + len(stderr_raw) > output_limit:
            output_limited = True
            stdout_raw = b""
            stderr_raw = b""
    try:
        stdout = stdout_raw.decode("utf-8", errors="strict")
        stderr = stderr_raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise InstrumentError("process-output-invalid", "Codex output is not strict UTF-8") from exc
    return ProcessCapture(
        stdout=stdout,
        stderr=stderr,
        returncode=returncode,
        duration_ms=duration_ms,
        timed_out=timed_out,
        output_limited=output_limited,
    )


def _receipt_dict(value: object) -> dict[str, object]:
    result = dataclasses.asdict(value)
    for key, child in list(result.items()):
        if isinstance(child, tuple):
            result[key] = list(child)
    return result


def _sanitized_argv(
    command: tuple[str, ...], codex_bin: Path, workspace: Path
) -> list[str]:
    replacements = {
        str(codex_bin): "<codex-bin>",
        str(workspace): "<workspace>",
    }
    sanitized = [replacements.get(value, value) for value in command]
    if any(str(workspace) in value or str(codex_bin) in value for value in sanitized):
        raise InstrumentError("argv-sanitization-failed", "Codex argv contains an unbound path")
    return sanitized


def _base_result(
    contract: TrialContract,
    *,
    state: codex_routing_grade.VerdictState,
    reason_codes: tuple[str, ...],
    exact_revision: bool,
    runtime_facts: dict[str, object] | None = None,
    trace_facts: dict[str, object] | None = None,
    hook_facts: dict[str, object] | None = None,
    verdict_facts: dict[str, object] | None = None,
) -> TrialResult:
    return TrialResult(
        scenario_id=contract.scenario_id,
        revision=contract.revision,
        trial=contract.trial,
        state=state,
        reason_codes=reason_codes,
        manifest_sha256=contract.manifest_sha256,
        scenario_sha256=contract.scenario_sha256,
        prompt_sha256=contract.prompt_sha256,
        exact_revision=exact_revision,
        tool_policy="no-model-tools-non-root",
        invocation_mode=contract.invocation_mode,
        runtime_facts=runtime_facts,
        trace_facts=trace_facts,
        hook_facts=hook_facts,
        verdict_facts=verdict_facts,
    )


@contextlib.contextmanager
def _private_trial_directory(
    *, parent: Path | None, repository: Path
):
    """Create one exact temp root and fail visibly if private cleanup cannot complete."""

    if parent is None:
        raise InstrumentError(
            "unsafe-temp-boundary", "private trial parent is required"
        )
    _assert_private_path(parent)
    raw = tempfile.mkdtemp(
        prefix="save-toolkit-terra-trial-",
        dir=str(parent),
    )
    root = Path(raw).resolve(strict=True)
    try:
        if root == repository or root.is_relative_to(repository):
            raise InstrumentError(
                "unsafe-temp-boundary", "trial directory must be outside the checkout"
            )
        if root.parent != parent or _is_symlink(root) or any(root.iterdir()):
            raise InstrumentError(
                "unsafe-temp-boundary",
                "fresh trial directory is redirected, misplaced, or nonempty",
            )
        _secure_directory(root)
        _assert_private_path(parent)
        yield root
    finally:
        if _is_symlink(root):
            print(
                f"codex-terra-routing: WARNING private trial path was redirected and was not "
                f"removed: {root}",
                file=sys.stderr,
            )
            raise InstrumentError(
                "private-cleanup-failed", "private trial path was redirected before cleanup"
            )
        try:
            shutil.rmtree(root)
        except OSError as exc:
            print(
                f"codex-terra-routing: WARNING private trial cleanup failed; remove this "
                f"credential-bearing path manually: {root}",
                file=sys.stderr,
            )
            raise InstrumentError(
                "private-cleanup-failed", "private trial directory could not be removed"
            ) from exc


def _validated_private_parent(path: Path, repository: Path) -> Path:
    """Revalidate the externally bound private ancestor without resolving through links."""

    candidate = Path(path)
    if not candidate.is_absolute() or candidate != Path(os.path.abspath(candidate)):
        raise InstrumentError(
            "unsafe-temp-boundary", "private trial parent must be absolute and normalized"
        )
    current = Path(candidate.anchor)
    try:
        for component in candidate.parts[1:]:
            current /= component
            metadata = current.lstat()
            if _is_symlink(current) or (
                current == candidate and not stat.S_ISDIR(metadata.st_mode)
            ):
                raise InstrumentError(
                    "unsafe-temp-boundary",
                    "private trial parent traverses a redirected or non-directory path",
                )
        resolved = candidate.resolve(strict=True)
    except InstrumentError:
        raise
    except OSError as exc:
        raise InstrumentError(
            "unsafe-temp-boundary", "private trial parent is unavailable"
        ) from exc
    if resolved != candidate:
        raise InstrumentError(
            "unsafe-temp-boundary", "private trial parent resolves through indirection"
        )
    if (
        candidate == repository
        or candidate.is_relative_to(repository)
        or repository.is_relative_to(candidate)
    ):
        raise InstrumentError(
            "unsafe-temp-boundary", "private trial parent must be outside the checkout"
        )
    _secure_directory(candidate)
    return candidate


def _preflight_process_forbidden(*_args: object, **_kwargs: object) -> ProcessCapture:
    """Make an accidental authenticated/model-process step fail closed during preflight."""

    raise InstrumentError(
        "preflight-model-process-attempted",
        "credential-free preflight attempted to start the model process",
    )


def run_preflight(
    *,
    repo_root: Path,
    codex_bin: Path,
    scenario: Mapping[str, object],
    spec: codex_harness.TrialSpec,
    manifest_sha256: str,
    exact_revision: bool,
    runtime_profile: codex_runtime.RuntimeProfile,
    canary_probe_mode: str,
    temp_parent: Path | None = None,
    command_runner: CommandRunner = _default_command_runner,
) -> TrialResult:
    """Exercise the real credential-free setup and stop before auth or a model request."""

    return _execute_trial(
        repo_root=repo_root,
        codex_bin=codex_bin,
        auth_file=None,
        scenario=scenario,
        spec=spec,
        manifest_sha256=manifest_sha256,
        exact_revision=exact_revision,
        runtime_profile=runtime_profile,
        canary_probe_mode=canary_probe_mode,
        credential_free_only=True,
        temp_parent=temp_parent,
        command_runner=command_runner,
        process_runner=_preflight_process_forbidden,
    )


def run_trial(
    *,
    repo_root: Path,
    codex_bin: Path,
    auth_file: Path,
    scenario: Mapping[str, object],
    spec: codex_harness.TrialSpec,
    manifest_sha256: str,
    exact_revision: bool,
    runtime_profile: codex_runtime.RuntimeProfile,
    canary_probe_mode: str,
    temp_parent: Path | None = None,
    command_runner: CommandRunner = _default_command_runner,
    process_runner: ProcessRunner = launch_process,
) -> TrialResult:
    """Execute one fixed trial and return only sanitized, authority-bounded evidence."""

    return _execute_trial(
        repo_root=repo_root,
        codex_bin=codex_bin,
        auth_file=auth_file,
        scenario=scenario,
        spec=spec,
        manifest_sha256=manifest_sha256,
        exact_revision=exact_revision,
        runtime_profile=runtime_profile,
        canary_probe_mode=canary_probe_mode,
        credential_free_only=False,
        temp_parent=temp_parent,
        command_runner=command_runner,
        process_runner=process_runner,
    )


def _execute_trial(
    *,
    repo_root: Path,
    codex_bin: Path,
    auth_file: Path | None,
    scenario: Mapping[str, object],
    spec: codex_harness.TrialSpec,
    manifest_sha256: str,
    exact_revision: bool,
    runtime_profile: codex_runtime.RuntimeProfile,
    canary_probe_mode: str | None,
    credential_free_only: bool,
    temp_parent: Path | None,
    command_runner: CommandRunner,
    process_runner: ProcessRunner,
) -> TrialResult:
    """Run the shared setup, optionally continuing into the authenticated model step."""

    contract = validate_trial_contract(
        scenario,
        spec,
        manifest_sha256=manifest_sha256,
        manifest_path=runtime_profile.manifest_path,
        canary_probe_mode=canary_probe_mode,
    )
    if not isinstance(exact_revision, bool):
        raise TrialContractError("exact_revision must be a caller-supplied boolean")
    evaluator_root = Path(__file__).resolve().parent
    expected_codex_cli_version = runtime_profile.codex_cli_version
    runtime_facts: dict[str, object] = {
        "codex_cli_version": expected_codex_cli_version,
    }
    expected_codex_sha256 = runtime_profile.codex_executable_sha256
    expected_python_version = runtime_profile.python_version
    evaluator_files = runtime_profile.evaluator_files
    finish_after_launch: Callable[..., TrialResult] | None = None

    def finish_result(
        *,
        state: codex_routing_grade.VerdictState,
        reason_codes: tuple[str, ...],
        trace_facts: dict[str, object] | None = None,
        hook_facts: dict[str, object] | None = None,
        verdict_facts: dict[str, object] | None = None,
    ) -> TrialResult:
        if finish_after_launch is not None:
            return finish_after_launch(
                state=state,
                reason_codes=reason_codes,
                trace_facts=trace_facts,
                hook_facts=hook_facts,
                verdict_facts=verdict_facts,
            )
        return _base_result(
            contract,
            state=state,
            reason_codes=reason_codes,
            exact_revision=exact_revision,
            runtime_facts=runtime_facts,
            trace_facts=trace_facts,
            hook_facts=hook_facts,
            verdict_facts=verdict_facts,
        )

    try:
        python_executable, python_sha256 = verify_python_runtime(runtime_profile)
        runtime_facts["evaluator_tree_sha256"] = _tree_digest(evaluator_root, evaluator_files)
    except InstrumentError as exc:
        return finish_result(
            state=codex_routing_grade.VerdictState.INCONCLUSIVE,
            reason_codes=(exc.reason_code,),
        )
    repository = Path(repo_root).resolve(strict=True)
    try:
        parent = _validated_private_parent(
            Path(temp_parent) if temp_parent is not None else Path(), repository
        ) if temp_parent is not None else None
        with _private_trial_directory(parent=parent, repository=repository) as root:
            _secure_directory(root)
            paths = {
                name: root / name
                for name in (
                    "probe-home",
                    "codex-home",
                    "home",
                    "temp",
                    "snapshot",
                    "project",
                    "receipts",
                    "hook-bundle",
                )
            }
            for path in paths.values():
                _secure_directory(path)
            for path in (paths["home"] / "appdata", paths["home"] / "localappdata"):
                _secure_directory(path)

            snapshot_receipt = codex_snapshot.materialize_snapshot(
                repository,
                contract.revision,
                paths["snapshot"],
                git_executable=runtime_profile.git_executable_path,
                git_executable_sha256=runtime_profile.git_executable_sha256,
                command_runner=_bounded_git_runner,
            )
            stage_receipt = codex_snapshot.stage_neutral_project(
                paths["snapshot"], paths["project"]
            )
            if contract.invocation_mode == "explicit-skill-body-probe":
                skill_body = _stable_file_bytes(
                    paths["project"]
                    / ".agents"
                    / "skills"
                    / run_codex_routing.CANARY_EXPLICIT_SKILL
                    / "SKILL.md",
                    label="selected canary skill body",
                    max_bytes=1024 * 1024,
                )
                skill_body_sha256 = hashlib.sha256(skill_body).hexdigest()
                if skill_body_sha256 != run_codex_routing.CANARY_SKILL_BODY_SHA256:
                    raise InstrumentError(
                        "skill-body-mismatch",
                        "selected canary skill body differs from the fixed snapshot",
                    )
                runtime_facts.update(
                    {
                        "selected_skill_name": run_codex_routing.CANARY_EXPLICIT_SKILL,
                        "selected_skill_body_sha256": skill_body_sha256,
                    }
                )
            staged_codex = _ordinary_file(Path(codex_bin), label="protected Codex executable")
            if (
                staged_codex != runtime_profile.codex_executable_path
                or _sha256_file(staged_codex, label="protected Codex executable")
                != expected_codex_sha256
            ):
                raise InstrumentError(
                    "codex-executable-mismatch",
                    "protected Codex executable differs from the runtime profile",
                )
            probe_env = scrubbed_environment(
                home=paths["home"],
                codex_home=paths["probe-home"],
                temp=paths["temp"],
            )
            probe = probe_codex(
                staged_codex,
                probe_env,
                cwd=paths["probe-home"],
                expected_cli_version=expected_codex_cli_version,
                command_runner=command_runner,
            )
            if probe.executable_sha256 != expected_codex_sha256:
                raise InstrumentError(
                    "codex-executable-mismatch",
                    "staged Codex executable differs from the manifest pin",
                )
            catalog_path = paths["codex-home"] / "route-models.json"
            catalog_receipt = codex_model_catalog.write_safe_catalog(
                probe.bundled_catalog, catalog_path
            )

            nonce = uuid.uuid4().hex
            hook_bundle = copy_hook_bundle(evaluator_root, paths["hook-bundle"])
            recorder = hook_bundle.recorder_path
            config = run_codex_routing.render_config(
                python_executable,
                recorder,
                paths["receipts"],
                catalog_path,
                nonce,
            )
            config_path = paths["codex-home"] / "config.toml"
            _private_write(config_path, config.encode("utf-8"))
            _secure_directory(root, recursive=True)

            env = scrubbed_environment(
                home=paths["home"],
                codex_home=paths["codex-home"],
                temp=paths["temp"],
            )
            resolved_codex = _ordinary_file(staged_codex, label="staged Codex executable")
            if (
                _sha256_file(resolved_codex, label="staged Codex executable")
                != expected_codex_sha256
            ):
                raise InstrumentError(
                    "codex-executable-drift",
                    "staged Codex executable changed before auth copy",
                )
            command = run_codex_routing.build_command(
                resolved_codex,
                paths["project"],
            )
            argv = _sanitized_argv(command, resolved_codex, paths["project"])
            runtime_facts.update(
                {
                    "codex_cli_version": probe.cli_version,
                    "codex_executable_sha256": probe.executable_sha256,
                    "runtime_platform": _runtime_platform(),
                    "python_version": expected_python_version,
                    "python_executable_sha256": python_sha256,
                    "hook_bundle": hook_bundle.persistable_facts(),
                    "snapshot": _receipt_dict(snapshot_receipt),
                    "stage": _receipt_dict(stage_receipt),
                    "model_catalog": _receipt_dict(catalog_receipt),
                    "config_sha256": hashlib.sha256(config.encode("utf-8")).hexdigest(),
                    "argv": argv,
                    "argv_sha256": _canonical_sha256(argv),
                    "environment_keys": sorted(env),
                    "environment_keys_sha256": _canonical_sha256(sorted(env)),
                }
            )
            codex_snapshot.verify_staged_project(
                paths["snapshot"], paths["project"], stage_receipt
            )
            verify_hook_bundle(evaluator_root, hook_bundle)
            if (
                _sha256_file(config_path, label="Codex config")
                != runtime_facts["config_sha256"]
                or _sha256_file(catalog_path, label="safe model catalog")
                != codex_model_catalog.EXPECTED_SAFE_CATALOG_SHA256
                or _sha256_file(python_executable, label="Python executable")
                != python_sha256
                or _tree_digest(evaluator_root, evaluator_files)
                != runtime_facts["evaluator_tree_sha256"]
            ):
                raise InstrumentError(
                    "credential-free-boundary-drift",
                    "credential-free trial inputs changed before auth copy",
                )

            if credential_free_only:
                return finish_result(
                    state=codex_routing_grade.VerdictState.INCONCLUSIVE,
                    reason_codes=("credential-free-preflight-pass",),
                )
            if auth_file is None:
                raise TrialContractError("authenticated trial requires an auth file")

            # This is deliberately the final preparation step. Its helper applies and verifies the
            # private destination mode and ownership before returning; the next operation launches
            # Codex once.
            auth_destination = paths["codex-home"] / "auth.json"
            auth_guard = copy_auth_file(Path(auth_file), auth_destination)
            try:
                capture = process_runner(
                    command,
                    prompt=contract.prompt,
                    cwd=paths["project"],
                    env=env,
                    timeout_s=codex_harness.TIMEOUT_SECONDS,
                    output_limit=MAX_PROCESS_OUTPUT_BYTES,
                )
            except BaseException:
                remove_auth_file(auth_destination)
                raise
            runtime_facts.update(
                {
                    "returncode": capture.returncode,
                    "duration_ms": capture.duration_ms,
                    "timed_out": capture.timed_out,
                    "output_limited": capture.output_limited,
                }
            )

            def _finish_after_launch(
                *,
                state: codex_routing_grade.VerdictState,
                reason_codes: tuple[str, ...],
                trace_facts: dict[str, object] | None = None,
                hook_facts: dict[str, object] | None = None,
                verdict_facts: dict[str, object] | None = None,
            ) -> TrialResult:
                try:
                    codex_snapshot.verify_staged_project(
                        paths["snapshot"], paths["project"], stage_receipt
                    )
                    verify_hook_bundle(evaluator_root, hook_bundle)
                    drift = (
                        _sha256_file(resolved_codex, label="staged Codex executable")
                        != expected_codex_sha256
                        or _sha256_file(config_path, label="Codex config")
                        != runtime_facts["config_sha256"]
                        or _sha256_file(catalog_path, label="safe model catalog")
                        != codex_model_catalog.EXPECTED_SAFE_CATALOG_SHA256
                        or _sha256_file(python_executable, label="Python executable")
                        != python_sha256
                        or _tree_digest(evaluator_root, evaluator_files)
                        != runtime_facts["evaluator_tree_sha256"]
                    )
                except (
                    InstrumentError,
                    codex_snapshot.SnapshotError,
                    OSError,
                    ValueError,
                ):
                    drift = True
                if drift:
                    state = codex_routing_grade.VerdictState.INCONCLUSIVE
                    reason_codes = ("post-trial-input-drift",)
                    trace_facts = None
                    hook_facts = None
                    verdict_facts = None
                return _base_result(
                    contract,
                    state=state,
                    reason_codes=reason_codes,
                    exact_revision=exact_revision,
                    runtime_facts=runtime_facts,
                    trace_facts=trace_facts,
                    hook_facts=hook_facts,
                    verdict_facts=verdict_facts,
                )

            finish_after_launch = _finish_after_launch
            refreshed_guard = auth_guard
            refresh_problem: str | None = None
            removal_problem: str | None = None
            try:
                try:
                    refreshed_guard = auth_guard.merged(load_auth_guard(auth_destination))
                except InstrumentError as exc:
                    refresh_problem = exc.reason_code
            finally:
                try:
                    remove_auth_file(auth_destination)
                except InstrumentError as exc:
                    removal_problem = exc.reason_code
            if removal_problem is not None:
                return finish_result(
                    state=codex_routing_grade.VerdictState.INCONCLUSIVE,
                    reason_codes=("auth-copy-removal-failed",),
                )
            scan_problem = refresh_problem
            try:
                refreshed_guard.reject_output(capture.stdout)
                refreshed_guard.reject_output(capture.stderr)
                refreshed_guard.reject_jsonl(capture.stdout)
                codex_harness.reject_credentials(
                    {"stdout": capture.stdout, "stderr": capture.stderr},
                    location="trial_output",
                )
            except (CredentialEchoError, codex_harness.CredentialExposureError):
                scan_problem = "credential-shaped-output"
            except InstrumentError as exc:
                if scan_problem is None:
                    scan_problem = exc.reason_code
            if scan_problem is not None:
                return finish_result(
                    state=codex_routing_grade.VerdictState.INCONCLUSIVE,
                    reason_codes=(scan_problem,),
                )
            if capture.timed_out:
                return finish_result(
                    state=codex_routing_grade.VerdictState.INCONCLUSIVE,
                    reason_codes=("process-timeout",),
                )
            if capture.output_limited:
                return finish_result(
                    state=codex_routing_grade.VerdictState.INCONCLUSIVE,
                    reason_codes=("process-output-limit",),
                )
            runtime_facts.update(
                {
                    "stdout_bytes": len(capture.stdout.encode("utf-8")),
                    "stderr_bytes": len(capture.stderr.encode("utf-8")),
                    "stderr_sha256": hashlib.sha256(
                        capture.stderr.encode("utf-8")
                    ).hexdigest(),
                }
            )
            try:
                trace = codex_harness.parse_jsonl(
                    capture.stdout, process_exit_code=capture.returncode
                )
            except CredentialEchoError:
                return finish_result(
                    state=codex_routing_grade.VerdictState.INCONCLUSIVE,
                    reason_codes=("credential-shaped-output",),
                )
            except codex_harness.TraceError:
                return finish_result(
                    state=codex_routing_grade.VerdictState.INCONCLUSIVE,
                    reason_codes=("trace-invalid",),
                )
            try:
                hooks = codex_hook_recorder.load_receipts(
                    paths["receipts"], nonce, payload_validator=refreshed_guard.reject_value
                )
            except CredentialEchoError:
                return finish_result(
                    state=codex_routing_grade.VerdictState.INCONCLUSIVE,
                    reason_codes=("credential-shaped-output",),
                )
            except (OSError, ValueError, codex_harness.TraceError):
                return finish_result(
                    state=codex_routing_grade.VerdictState.INCONCLUSIVE,
                    reason_codes=("hook-invalid",),
                )
            verdict = (
                codex_routing_grade.grade_description_selection(
                    expected_skill=run_codex_routing.CANARY_EXPLICIT_SKILL,
                    trace=trace,
                    hooks=hooks,
                )
                if contract.invocation_mode == "description-selection-probe"
                else codex_routing_grade.grade_trial(scenario, trace, hooks)
            )
            return finish_result(
                state=verdict.state,
                reason_codes=verdict.reason_codes,
                trace_facts=trace.persistable_facts(),
                hook_facts=hooks.persistable_facts(),
                verdict_facts=verdict.as_dict(),
            )
    except InstrumentError as exc:
        return finish_result(
            state=codex_routing_grade.VerdictState.INCONCLUSIVE,
            reason_codes=(exc.reason_code,),
        )
    except codex_snapshot.SnapshotError:
        return finish_result(
            state=codex_routing_grade.VerdictState.INCONCLUSIVE,
            reason_codes=("snapshot-boundary-failed",),
        )
    except codex_model_catalog.CatalogError:
        return finish_result(
            state=codex_routing_grade.VerdictState.INCONCLUSIVE,
            reason_codes=("model-catalog-mismatch",),
        )
    except (OSError, ValueError):
        return finish_result(
            state=codex_routing_grade.VerdictState.INCONCLUSIVE,
            reason_codes=("executor-boundary-failed",),
        )
