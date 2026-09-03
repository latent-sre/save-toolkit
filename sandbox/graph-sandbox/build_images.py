"""Immutable-snapshot image builder used only by :mod:`activate`.

There is deliberately no standalone CLI. ``activate.py build`` is the sole supported entrypoint.
"""

from __future__ import annotations

from io import BytesIO
import json
import os
from pathlib import Path, PurePosixPath
import re
import secrets
import shutil
import tarfile
import tempfile
from typing import Any, Mapping

from preflight import (
    BASE_REFERENCE,
    DockerCLI,
    LOCK_VERSION,
    PLATFORM,
    PreflightError,
    REVISION_RE,
    RepositoryLayout,
    assert_no_ambient_docker_authority,
    build_context_digest,
    dockerfile_base_references,
    file_digest,
    run_process,
    scrub_environment,
    validate_local_context,
)


MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 2048
WINDOWS_RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL", *(f"COM{index}" for index in range(1, 10)), *(f"LPT{index}" for index in range(1, 10))}
)


class SnapshotError(PreflightError):
    """A Git snapshot cannot be proven to represent the requested revision."""


def _text_output(result: Any) -> str:
    output = result.stdout
    if isinstance(output, bytes):
        return output.decode("utf-8", errors="strict").strip()
    return str(output).strip()


def _require_clean_revision(
    repository_root: Path,
    source_revision: str,
    *,
    runner=run_process,
    environment: Mapping[str, str],
    changed_message: str,
) -> None:
    if not REVISION_RE.fullmatch(source_revision):
        raise SnapshotError("source_revision: expected lowercase 40-hex revision")
    head = runner(
        ["git", "-C", str(repository_root), "rev-parse", "HEAD"],
        environment=environment,
        timeout_seconds=30,
        stdin=None,
    )
    if head.returncode != 0 or _text_output(head) != source_revision:
        raise SnapshotError(f"source_revision: {changed_message}")
    status = runner(
        [
            "git",
            "-C",
            str(repository_root),
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
        ],
        environment=environment,
        timeout_seconds=30,
        stdin=None,
    )
    if status.returncode != 0 or _text_output(status):
        raise SnapshotError(f"source_revision: {changed_message}")


def safe_extract_archive(archive_bytes: bytes, destination: Path) -> Path:
    """Extract a bounded regular-file-only ``graph-sandbox`` Git archive."""

    if len(archive_bytes) > MAX_ARCHIVE_BYTES:
        raise SnapshotError("archive: compressed input exceeds size limit")
    try:
        destination.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise SnapshotError("archive: exclusive snapshot destination already exists") from exc

    seen: set[PurePosixPath] = set()
    total_size = 0
    try:
        with tarfile.open(fileobj=BytesIO(archive_bytes), mode="r:") as archive:
            members = archive.getmembers()
            if len(members) > MAX_ARCHIVE_MEMBERS:
                raise SnapshotError("archive: member count exceeds limit")
            for member in members:
                relative = PurePosixPath(member.name)
                if (
                    relative.is_absolute()
                    or not relative.parts
                    or relative.parts[0] != "graph-sandbox"
                    or any(part in {"", ".", ".."} for part in relative.parts)
                    or any("\\" in part or ":" in part for part in relative.parts)
                    or any(
                        part.rstrip(". ").split(".", 1)[0].upper() in WINDOWS_RESERVED_NAMES
                        for part in relative.parts
                    )
                ):
                    raise SnapshotError("archive: path traversal or foreign root rejected")
                if relative in seen:
                    raise SnapshotError("archive: duplicate member rejected")
                seen.add(relative)
                if not (member.isdir() or member.isreg()):
                    raise SnapshotError("archive: links, devices, and special files are rejected")
                total_size += member.size
                if total_size > MAX_ARCHIVE_BYTES:
                    raise SnapshotError("archive: expanded size exceeds limit")

            for member in members:
                relative = PurePosixPath(member.name)
                target = destination.joinpath(*relative.parts)
                try:
                    target.relative_to(destination)
                except ValueError as exc:
                    raise SnapshotError("archive: extracted path escaped destination") from exc
                if member.isdir():
                    target.mkdir(mode=0o700, parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                source = archive.extractfile(member)
                if source is None:
                    raise SnapshotError("archive: regular member has no data")
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
                flags |= getattr(os, "O_NOFOLLOW", 0)
                try:
                    descriptor = os.open(target, flags, 0o600)
                except OSError as exc:
                    raise SnapshotError("archive: exclusive file creation failed") from exc
                with source, os.fdopen(descriptor, "wb") as output:
                    shutil.copyfileobj(source, output, length=1024 * 1024)
                    output.flush()
                    os.fsync(output.fileno())
    except (tarfile.TarError, OSError, UnicodeError) as exc:
        raise SnapshotError("archive: invalid or unsafe tar stream") from exc

    sandbox = destination / "graph-sandbox"
    if not sandbox.is_dir():
        raise SnapshotError("archive: graph-sandbox root is missing")
    return sandbox


def prepare_git_snapshot(
    repository_root: Path,
    source_revision: str,
    destination: Path,
    *,
    archive_root: Path,
    runner=run_process,
    environ: Mapping[str, str] | None = None,
) -> Path:
    ambient = os.environ if environ is None else environ
    assert_no_ambient_docker_authority(ambient)
    environment = scrub_environment(ambient)
    _require_clean_revision(
        repository_root,
        source_revision,
        runner=runner,
        environment=environment,
        changed_message="checkout is not the requested clean revision",
    )
    archived = runner(
        [
            "git",
            "-C",
            str(archive_root),
            "archive",
            "--format=tar",
            source_revision,
            "--",
            "graph-sandbox",
        ],
        environment=environment,
        timeout_seconds=60,
        stdin=None,
        binary=True,
    )
    if archived.returncode != 0 or not isinstance(archived.stdout, bytes):
        raise SnapshotError("archive: git archive failed")
    sandbox = safe_extract_archive(archived.stdout, destination)
    _require_clean_revision(
        repository_root,
        source_revision,
        runner=runner,
        environment=environment,
        changed_message="checkout changed during snapshot",
    )
    return sandbox


def _atomic_replace_lock(lock_path: Path, payload: Mapping[str, Any]) -> None:
    if lock_path.is_symlink() or not lock_path.is_file():
        raise SnapshotError("images.lock: expected existing regular template")
    serialized = (json.dumps(payload, indent=2, sort_keys=False) + "\n").encode("utf-8")
    temporary = lock_path.parent / f".{lock_path.name}.{secrets.token_hex(16)}.tmp"
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(temporary, flags, 0o600)
    except OSError as exc:
        raise SnapshotError("images.lock: exclusive temporary creation failed") from exc
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(serialized)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, lock_path)
    finally:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def build_and_lock(
    *,
    layout: RepositoryLayout,
    source_revision: str,
    docker_context: str,
    runner=run_process,
    environ: Mapping[str, str] | None = None,
) -> None:
    ambient = os.environ if environ is None else environ
    assert_no_ambient_docker_authority(ambient)
    initial_context = validate_local_context(
        docker_context, runner=runner, environ=ambient
    )
    environment = scrub_environment(ambient, extra={"SOURCE_REVISION": source_revision})

    with tempfile.TemporaryDirectory(prefix="graph-sandbox-build-") as temporary:
        snapshot_sandbox = prepare_git_snapshot(
            layout.repository_root,
            source_revision,
            Path(temporary) / "snapshot",
            archive_root=layout.archive_root,
            runner=runner,
            environ=ambient,
        )
        for logical_name in ("runner", "services"):
            references = dockerfile_base_references(
                snapshot_sandbox / logical_name / "Dockerfile"
            )
            if any(reference != BASE_REFERENCE for reference in references):
                raise SnapshotError(
                    f"{logical_name} Dockerfile: unpinned or unexpected base reference"
                )

        docker = DockerCLI(
            docker_context,
            runner=runner,
            environ=ambient,
            timeout_seconds=30,
        )
        status = docker.status()
        if not status.reachable or status.os_type.lower() != "linux" or not status.compose_json:
            raise SnapshotError(
                "docker.daemon: reachable Linux Docker and Compose JSON support required"
            )
        immediate_context = validate_local_context(
            docker_context, runner=runner, environ=ambient
        )
        if immediate_context != initial_context:
            raise SnapshotError("context.endpoint: Docker context changed before build")

        build_source = snapshot_sandbox / "compose.build.yaml"
        guard = b"activation_guard: graph-sandbox/activate.py/v1\n"
        source_bytes = build_source.read_bytes()
        if not source_bytes.startswith(guard) or source_bytes.count(guard) != 1:
            raise SnapshotError("build Compose activation guard is missing or duplicated")
        unguarded_build = snapshot_sandbox / f".activation-build-{secrets.token_hex(16)}.yaml"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        flags |= getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(unguarded_build, flags, 0o600)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(source_bytes[len(guard) :])
                stream.flush()
                os.fsync(stream.fileno())
            built = runner(
                [
                    "docker",
                    "--context",
                    docker_context,
                    "compose",
                    "--file",
                    str(unguarded_build),
                    "--project-name",
                    "graph-sandbox-build-v1",
                    "build",
                    "--pull",
                ],
                environment=environment,
                timeout_seconds=1800,
                stdin=None,
            )
            if built.returncode != 0:
                raise SnapshotError(f"image build failed with exit {built.returncode}")
        finally:
            try:
                unguarded_build.unlink()
            except FileNotFoundError:
                pass

        _require_clean_revision(
            layout.repository_root,
            source_revision,
            runner=runner,
            environment=scrub_environment(ambient),
            changed_message="checkout changed during image build",
        )
        final_context = validate_local_context(
            docker_context, runner=runner, environ=ambient
        )
        if final_context != initial_context:
            raise SnapshotError("context.endpoint: Docker context changed during build")

        tags = {
            "runner": f"graph-sandbox/graph-runner:{source_revision}",
            "services": f"graph-sandbox/synthetic-services:{source_revision}",
        }
        context_digest = build_context_digest(snapshot_sandbox)
        records: dict[str, dict[str, str]] = {}
        for logical_name, tag in tags.items():
            metadata = docker.inspect_image(tag)
            if metadata.platform != PLATFORM:
                raise SnapshotError(
                    f"{logical_name} image: expected {PLATFORM}, got {metadata.platform}"
                )
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", metadata.image_id):
                raise SnapshotError(
                    f"{logical_name} image: Docker returned a mutable or invalid ID"
                )
            if metadata.entrypoint:
                raise SnapshotError(f"{logical_name} image: Config.Entrypoint is forbidden")
            if metadata.declared_volumes:
                raise SnapshotError(f"{logical_name} image: Config.Volumes is forbidden")
            records[logical_name] = {
                "logical_name": logical_name,
                "platform": PLATFORM,
                "source_revision": source_revision,
                "dockerfile_digest": file_digest(
                    snapshot_sandbox / logical_name / "Dockerfile"
                ),
                "build_context_digest": context_digest,
                "base_reference": BASE_REFERENCE,
                "image_id": metadata.image_id,
            }

        _atomic_replace_lock(
            layout.images_lock,
            {"lock_version": LOCK_VERSION, "images": records},
        )
