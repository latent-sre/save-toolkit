#!/usr/bin/env python3
"""Run one command in a digest-bound, networkless Docker or Podman verification sandbox."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence

try:
    from scripts import evidence_envelope
except ModuleNotFoundError:
    import evidence_envelope  # type: ignore[no-redef]


IMAGE_RE = re.compile(r"^[^\s]+@sha256:[0-9a-f]{64}$")
REVISION_RE = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
USER_RE = re.compile(r"^[1-9][0-9]*:[1-9][0-9]*$")
MEMORY_RE = re.compile(r"^[1-9][0-9]*(?:[bkmg])?$", re.IGNORECASE)
IMAGE_ID_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
CONTAINER_ID_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_CAPTURE_BYTES = 1024 * 1024
CAPTURE_CHUNK_BYTES = 64 * 1024
SCRATCH_MIN_BYTES = 1024 * 1024
SCRATCH_MAX_BYTES = 4 * 1024 * 1024 * 1024
MAX_TREE_FILES = 100_000
MAX_TREE_BYTES = 10 * 1024 * 1024 * 1024
FILE_ATTRIBUTE_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)


class SandboxError(ValueError):
    """Raised before execution when the requested isolation contract is unsafe."""


def _default_container_user() -> str:
    if os.name != "nt" and hasattr(os, "geteuid") and hasattr(os, "getegid"):
        uid = os.geteuid()
        gid = os.getegid()
        if uid > 0 and gid > 0:
            return f"{uid}:{gid}"
    return "65532:65532"


@dataclass(frozen=True)
class ProcessResult:
    returncode: int | None
    stdout: bytes
    stderr: bytes
    timed_out: bool = False
    spawn_error: bool = False
    output_limit_exceeded: bool = False


@dataclass(frozen=True)
class SandboxConfig:
    engine: str
    image: str
    source: Path
    expected_tree_digest: str
    command: tuple[str, ...]
    scratch_size: str = "256m"
    timeout_seconds: int = 600
    cpus: float = 1.0
    memory: str = "1g"
    pids_limit: int = 256
    user: str = _default_container_user()


Runner = Callable[[Sequence[str], int, Mapping[str, str]], ProcessResult]


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    """Stop a client process promptly without waiting forever on a hostile stream."""

    if process.poll() is not None:
        return
    try:
        process.terminate()
    except OSError:
        return
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        process.kill()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass


def _capture_pipe(
    pipe: object,
    output: bytearray,
    overflow: threading.Event,
) -> None:
    """Drain one pipe while retaining at most MAX_CAPTURE_BYTES."""

    read = getattr(pipe, "read")
    try:
        while True:
            chunk = read(CAPTURE_CHUNK_BYTES)
            if not chunk:
                return
            remaining = MAX_CAPTURE_BYTES - len(output)
            if remaining > 0:
                output.extend(chunk[:remaining])
            if len(chunk) > remaining:
                overflow.set()
    except (OSError, ValueError):
        overflow.set()


def _run_process(argv: Sequence[str], timeout: int, environment: Mapping[str, str]) -> ProcessResult:
    try:
        process = subprocess.Popen(
            list(argv),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=dict(environment),
        )
    except OSError as exc:
        return ProcessResult(
            127,
            b"",
            type(exc).__name__.encode("ascii", errors="replace"),
            spawn_error=True,
        )

    assert process.stdout is not None and process.stderr is not None
    stdout = bytearray()
    stderr = bytearray()
    overflow = threading.Event()
    readers = [
        threading.Thread(target=_capture_pipe, args=(process.stdout, stdout, overflow), daemon=True),
        threading.Thread(target=_capture_pipe, args=(process.stderr, stderr, overflow), daemon=True),
    ]
    for reader in readers:
        reader.start()

    deadline = time.monotonic() + timeout
    timed_out = False
    output_limit_exceeded = False
    while process.poll() is None:
        if overflow.wait(timeout=0.05):
            output_limit_exceeded = True
            _stop_process(process)
            break
        if time.monotonic() >= deadline:
            timed_out = True
            _stop_process(process)
            break

    for reader in readers:
        reader.join(timeout=2)
    output_limit_exceeded = output_limit_exceeded or overflow.is_set()
    if any(reader.is_alive() for reader in readers):
        process.stdout.close()
        process.stderr.close()
        for reader in readers:
            reader.join(timeout=1)
        output_limit_exceeded = True
    else:
        process.stdout.close()
        process.stderr.close()

    return ProcessResult(
        process.poll(),
        bytes(stdout),
        bytes(stderr),
        timed_out=timed_out,
        output_limit_exceeded=output_limit_exceeded,
    )


def _is_indirection(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError as exc:
        raise SandboxError(f"cannot inspect path metadata: {path}") from exc
    return path.is_symlink() or bool(
        getattr(info, "st_file_attributes", 0) & FILE_ATTRIBUTE_REPARSE_POINT
    )


def _absolute_without_indirection(path: Path, label: str) -> Path:
    """Resolve an absolute path only after rejecting linked/reparsed existing ancestors."""

    absolute = Path(os.path.abspath(path.expanduser()))
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        if not current.exists() and not current.is_symlink():
            break
        if _is_indirection(current):
            raise SandboxError(f"{label} must not traverse a link or reparse point: {current}")
    return absolute.resolve()


def tree_digest(root: Path) -> str:
    """Hash a bounded ordinary-file tree without following links or executing target code."""

    root = _absolute_without_indirection(root, "source")
    if not root.is_dir() or _is_indirection(root):
        raise SandboxError("source must be an ordinary directory, not a link or reparse point")
    if root.name.casefold() == ".git":
        raise SandboxError("source snapshots must not expose .git metadata")
    digest = hashlib.sha256(b"save-toolkit-verification-tree-v1\0")
    file_count = 0
    byte_count = 0

    def visit(directory: Path) -> None:
        nonlocal file_count, byte_count
        try:
            entries = sorted(directory.iterdir(), key=lambda item: item.name)
        except OSError as exc:
            raise SandboxError(f"cannot enumerate source tree: {directory}") from exc
        for entry in entries:
            relative = entry.relative_to(root).as_posix()
            if entry.name.casefold() == ".git":
                raise SandboxError("source snapshots must not expose .git metadata")
            if _is_indirection(entry):
                raise SandboxError(f"source snapshots must not contain links or reparse points: {relative}")
            try:
                info = entry.stat(follow_symlinks=False)
            except OSError as exc:
                raise SandboxError(f"cannot stat source entry: {relative}") from exc
            encoded = relative.encode("utf-8", errors="surrogatepass")
            if stat.S_ISDIR(info.st_mode):
                digest.update(b"D\0" + encoded + b"\0")
                visit(entry)
                continue
            if not stat.S_ISREG(info.st_mode):
                raise SandboxError(f"source snapshots may contain only files and directories: {relative}")
            file_count += 1
            byte_count += info.st_size
            if file_count > MAX_TREE_FILES or byte_count > MAX_TREE_BYTES:
                raise SandboxError("source snapshot exceeds the verification tree limit")
            content_digest = evidence_envelope.sha256_file(entry)
            after = entry.stat(follow_symlinks=False)
            if (info.st_size, info.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise SandboxError(f"source changed while it was being hashed: {relative}")
            digest.update(
                b"F\0"
                + encoded
                + b"\0"
                + str(info.st_size).encode("ascii")
                + b"\0"
                + bytes.fromhex(content_digest)
            )

    visit(root)
    return digest.hexdigest()


def _engine_environment(client_home: Path, engine_name: str) -> dict[str, str]:
    """Use an isolated client home and an explicit local engine endpoint."""

    environment = {
        key: os.environ[key]
        for key in ("PATH", "PATHEXT", "SYSTEMROOT", "WINDIR")
        if key in os.environ
    }
    home = client_home.resolve()
    home.mkdir(parents=True, exist_ok=True)
    temporary = home / "tmp"
    temporary.mkdir()
    environment.update(
        {
            "HOME": str(home),
            "USERPROFILE": str(home),
            "TEMP": str(temporary),
            "TMP": str(temporary),
        }
    )
    if engine_name == "docker":
        docker_config = home / "docker-config"
        docker_config.mkdir()
        environment["DOCKER_CONFIG"] = str(docker_config)
        environment["DOCKER_HOST"] = (
            "npipe:////./pipe/docker_engine"
            if os.name == "nt"
            else "unix:///var/run/docker.sock"
        )
    return environment


def _size_bytes(value: str, label: str) -> int:
    match = re.fullmatch(r"([1-9][0-9]*)([bkmg]?)", value, re.IGNORECASE)
    if not match:
        raise SandboxError(f"{label} must be a positive Docker/Podman size such as 256m")
    scale = {"": 1, "b": 1, "k": 1024, "m": 1024**2, "g": 1024**3}
    return int(match.group(1)) * scale[match.group(2).lower()]


def _validate_config(config: SandboxConfig) -> SandboxConfig:
    engine_name = Path(config.engine).stem.lower()
    if engine_name not in {"docker", "podman"}:
        raise SandboxError("engine must resolve to docker or podman")
    if not IMAGE_RE.fullmatch(config.image) or config.image.startswith("-"):
        raise SandboxError("image must be an explicit name@sha256:<64 lowercase hex> reference")
    if not evidence_envelope.SHA256_RE.fullmatch(config.expected_tree_digest):
        raise SandboxError("expected_tree_digest must be a lowercase SHA-256 digest")
    source = _absolute_without_indirection(config.source, "source")
    if not source.is_dir():
        raise SandboxError(f"source is not a directory: {source}")
    if "," in str(source):
        raise SandboxError("source path cannot contain commas in --mount syntax")
    if not config.command or not all(
        isinstance(item, str) and item and "\0" not in item for item in config.command
    ):
        raise SandboxError("command must be a non-empty argv sequence without NUL bytes")
    evidence_envelope._reject_sensitive_argv(config.command)
    if not 1 <= config.timeout_seconds <= 86400:
        raise SandboxError("timeout_seconds must be between 1 and 86400")
    if not 0 < config.cpus <= 64:
        raise SandboxError("cpus must be greater than zero and at most 64")
    if not MEMORY_RE.fullmatch(config.memory):
        raise SandboxError("memory must be a positive Docker/Podman value such as 1g")
    scratch_bytes = _size_bytes(config.scratch_size, "scratch_size")
    if not SCRATCH_MIN_BYTES <= scratch_bytes <= SCRATCH_MAX_BYTES:
        raise SandboxError("scratch_size must be between 1m and 4g")
    if not 1 <= config.pids_limit <= 4096:
        raise SandboxError("pids_limit must be between 1 and 4096")
    if not USER_RE.fullmatch(config.user):
        raise SandboxError("user must be a non-root numeric uid:gid pair")
    return SandboxConfig(
        engine=config.engine,
        image=config.image,
        source=source,
        expected_tree_digest=config.expected_tree_digest,
        command=config.command,
        scratch_size=config.scratch_size,
        timeout_seconds=config.timeout_seconds,
        cpus=config.cpus,
        memory=config.memory,
        pids_limit=config.pids_limit,
        user=config.user,
    )


def build_command(config: SandboxConfig, *, container_name: str) -> list[str]:
    config = _validate_config(config)
    if not re.fullmatch(r"sre-verify-[0-9a-f]{16}", container_name):
        raise SandboxError("container name is not a fleet-generated verification name")
    return [
        config.engine,
        "run",
        "--name",
        container_name,
        "--label",
        f"save-toolkit.verification={container_name}",
        "--rm",
        "--pull",
        "never",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        str(config.pids_limit),
        "--memory",
        config.memory,
        "--cpus",
        str(config.cpus),
        "--user",
        config.user,
        "--mount",
        f"type=bind,src={config.source},dst=/workspace,readonly",
        "--tmpfs",
        f"/scratch:rw,nosuid,nodev,size={config.scratch_size}",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,nodev,size=64m",
        "--workdir",
        "/workspace",
        "--env",
        "HOME=/scratch/home",
        "--env",
        "TMPDIR=/tmp",
        config.image,
        *config.command,
    ]


def _captured_artifact(name: str, content: bytes) -> dict[str, object]:
    return {
        "path": name,
        "sha256": hashlib.sha256(content).hexdigest(),
        "size": len(content),
    }


def _truncate(content: bytes) -> tuple[bytes, bool]:
    if len(content) <= MAX_CAPTURE_BYTES:
        return content, False
    return content[:MAX_CAPTURE_BYTES], True


def _no_such_container(result: ProcessResult) -> bool:
    message = (result.stdout + result.stderr).decode("utf-8", errors="replace").lower()
    return "no such container" in message or "no such object" in message


def _image_inspect_command(config: SandboxConfig) -> tuple[str, ...]:
    return (config.engine, "image", "inspect", "--format", "{{.Id}}", config.image)


def _ownership_inspect_command(config: SandboxConfig, container_name: str) -> tuple[str, ...]:
    return (
        config.engine,
        "container",
        "inspect",
        "--format",
        '{{.Id}}|{{ index .Config.Labels "save-toolkit.verification" }}',
        container_name,
    )


def _owned_container_id(result: ProcessResult, container_name: str) -> tuple[str | None, str]:
    if _no_such_container(result):
        return None, "automatic --rm removal confirmed"
    if result.returncode != 0:
        return None, "engine could not inspect verification-container ownership"
    value = result.stdout.decode("utf-8", errors="replace").strip()
    parts = value.split("|", 1)
    if len(parts) != 2 or not CONTAINER_ID_RE.fullmatch(parts[0]):
        return None, "engine returned malformed verification-container identity"
    if parts[1] != container_name:
        return None, "container name is occupied by a foreign or unlabelled container"
    return parts[0], "verification-container ownership confirmed"


def execute(
    config: SandboxConfig,
    *,
    target_revision: str,
    criterion: str,
    run_id: str | None = None,
    task_id: str | None = None,
    attempt_id: str | None = None,
    runner: Runner = _run_process,
    now: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
) -> dict[str, object]:
    config = _validate_config(config)
    if not REVISION_RE.fullmatch(target_revision):
        raise SandboxError("target_revision must be a full lowercase 40- or 64-hex revision")
    observed_before = tree_digest(config.source)
    if observed_before != config.expected_tree_digest:
        raise SandboxError("source tree digest does not match the preapproved digest")

    container_name = f"sre-verify-{secrets.token_hex(8)}"
    argv = build_command(config, container_name=container_name)
    started = now()
    with tempfile.TemporaryDirectory(prefix="sre-engine-client-") as client_directory:
        environment = _engine_environment(Path(client_directory), Path(config.engine).stem.lower())
        preflight_argv = _image_inspect_command(config)
        preflight = runner(preflight_argv, 30, environment)
        image_id = preflight.stdout.decode("utf-8", errors="replace").strip()
        if preflight.returncode != 0 or preflight.spawn_error or not IMAGE_ID_RE.fullmatch(image_id):
            ended = now()
            limitations = [
                "the pinned image was not proven locally present; verification command was not run"
            ]
            return evidence_envelope.new_envelope(
                producer="verification_sandbox",
                role="isolated-verification",
                target_root=str(config.source),
                target_revision=target_revision,
                tree_digest=observed_before,
                criterion=criterion,
                status="inconclusive",
                started_at=started,
                ended_at=ended,
                command_argv=preflight_argv,
                command_cwd=str(config.source),
                exit_code=preflight.returncode,
                source={"kind": "container-image-preflight", "verification_executed": False},
                run_id=run_id,
                task_id=task_id,
                attempt_id=attempt_id,
                environment={"engine": Path(config.engine).stem.lower(), "image": config.image},
                isolation={"network": "not-created", "source_mount": "not-created"},
                artifacts=(),
                limitations=limitations,
            )

        result = runner(argv, config.timeout_seconds, environment)
        ownership = runner(_ownership_inspect_command(config, container_name), 30, environment)
        owned_id, ownership_check = _owned_container_id(ownership, container_name)
        cleanup_attempted = owned_id is not None
        if owned_id is None:
            cleanup = ProcessResult(0, b"", b"")
            residue = False if "--rm removal confirmed" in ownership_check else None
            residue_check = (
                "no container residue found"
                if residue is False
                else ownership_check
            )
        else:
            cleanup = runner((config.engine, "rm", "--force", owned_id), 30, environment)
            inspect = runner((config.engine, "container", "inspect", owned_id), 30, environment)
            if inspect.returncode == 0:
                residue = True
                residue_check = "owned container still exists after forced cleanup"
            elif _no_such_container(inspect):
                residue = False
                residue_check = "no container residue found"
            else:
                residue = None
                residue_check = "engine could not prove whether owned container residue remains"

    stdout, stdout_truncated = _truncate(result.stdout)
    stderr, stderr_truncated = _truncate(result.stderr)
    limitations: list[str] = []
    if stdout_truncated:
        limitations.append(f"stdout truncated to {MAX_CAPTURE_BYTES} bytes before hashing")
    if stderr_truncated:
        limitations.append(f"stderr truncated to {MAX_CAPTURE_BYTES} bytes before hashing")
    if result.output_limit_exceeded:
        status = "inconclusive"
        limitations.append(
            f"verification output exceeded the {MAX_CAPTURE_BYTES}-byte per-stream capture limit"
        )
    elif result.timed_out:
        status = "inconclusive"
        limitations.append("verification timed out before a verdict")
    elif result.spawn_error:
        status = "inconclusive"
        limitations.append("container engine could not be started")
    elif result.returncode == 0:
        status = "pass"
    else:
        status = "fail"
    if cleanup_attempted and cleanup.returncode != 0:
        status = "inconclusive"
        limitations.append(f"forced cleanup returned {cleanup.returncode}")
    if residue is not False:
        status = "inconclusive"
        limitations.append(residue_check)

    try:
        observed_after = tree_digest(config.source)
    except SandboxError as exc:
        observed_after = None
        status = "inconclusive"
        limitations.append(f"source residue check failed: {exc}")
    if observed_after is not None and observed_after != observed_before:
        status = "inconclusive"
        limitations.append("source tree changed during verification")

    ended = now()
    return evidence_envelope.new_envelope(
        producer="verification_sandbox",
        role="isolated-verification",
        target_root=str(config.source),
        target_revision=target_revision,
        tree_digest=observed_before,
        criterion=criterion,
        status=status,
        started_at=started,
        ended_at=ended,
        command_argv=argv,
        command_cwd=str(config.source),
        exit_code=result.returncode,
        source={
            "kind": "container-verification",
            "container_name": container_name,
            "container_argv": list(config.command),
            "image_id": image_id,
            "ownership_check": ownership_check,
            "cleanup_attempted": cleanup_attempted,
            "cleanup_returncode": cleanup.returncode,
            "residue": residue,
            "residue_check": residue_check,
            "source_digest_after": observed_after,
        },
        run_id=run_id,
        task_id=task_id,
        attempt_id=attempt_id,
        environment={"engine": Path(config.engine).stem.lower(), "image": config.image},
        isolation={
            "network": "none",
            "root_filesystem": "read-only",
            "source_mount": "read-only",
            "scratch_mount": "size-limited-empty-tmpfs",
            "scratch_size": config.scratch_size,
            "capabilities": "dropped-all",
            "no_new_privileges": True,
            "user": config.user,
            "cpus": config.cpus,
            "memory": config.memory,
            "pids_limit": config.pids_limit,
            "pull": "never",
            "client_home": "isolated-temporary",
        },
        artifacts=(
            _captured_artifact("captured-stdout.bin", stdout),
            _captured_artifact("captured-stderr.bin", stderr),
        ),
        limitations=limitations,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)
    digest = subparsers.add_parser("tree-digest", help="hash a link-free source snapshot")
    digest.add_argument("source", type=Path)

    run = subparsers.add_parser("run", help="run one direct argv command in the sandbox")
    run.add_argument("--engine", choices=("docker", "podman"), default="docker")
    run.add_argument("--image", required=True)
    run.add_argument("--source", type=Path, required=True)
    run.add_argument("--scratch-size", default="256m")
    run.add_argument("--expected-tree-digest", required=True)
    run.add_argument("--target-revision", required=True)
    run.add_argument("--criterion", required=True)
    run.add_argument("--timeout", type=int, default=600)
    run.add_argument("--cpus", type=float, default=1.0)
    run.add_argument("--memory", default="1g")
    run.add_argument("--pids-limit", type=int, default=256)
    run.add_argument("--user", default=_default_container_user())
    run.add_argument("--run-id")
    run.add_argument("--task-id")
    run.add_argument("--attempt-id")
    run.add_argument("command", nargs=argparse.REMAINDER)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.action == "tree-digest":
        try:
            print(tree_digest(args.source))
        except (OSError, SandboxError) as exc:
            print(f"verification sandbox error: {exc}", file=sys.stderr)
            return 2
        return 0

    command = list(args.command)
    if command and command[0] == "--":
        command = command[1:]
    executable = shutil.which(args.engine)
    if executable is None:
        print(f"verification sandbox error: {args.engine} is not on PATH", file=sys.stderr)
        return 2
    try:
        config = SandboxConfig(
            executable,
            args.image,
            args.source,
            args.expected_tree_digest,
            tuple(command),
            args.scratch_size,
            args.timeout,
            args.cpus,
            args.memory,
            args.pids_limit,
            args.user,
        )
        envelope = execute(
            config,
            target_revision=args.target_revision,
            criterion=args.criterion,
            run_id=args.run_id,
            task_id=args.task_id,
            attempt_id=args.attempt_id,
        )
    except (OSError, SandboxError, evidence_envelope.EnvelopeValidationError) as exc:
        print(f"verification sandbox error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(envelope, indent=2, sort_keys=True))
    return 0 if envelope["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
