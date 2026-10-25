"""Bounded Docker archive collection without extracting untrusted archive paths."""

from __future__ import annotations

import io
import re
import subprocess
import tarfile
import threading
from pathlib import Path, PurePosixPath

from swebench_adapter.containers import Docker

LIMIT = 64 * 1024 * 1024


def unpack_regular(data: bytes, destination: Path) -> dict[str, bytes]:
    """Validate the whole archive before writing; no links, devices, traversal or duplicates."""
    if len(data) > LIMIT:
        raise ValueError("archive exceeds bounded artifact limit")
    files: dict[str, bytes] = {}
    total = 0
    folded: dict[str, str] = {}
    modes: dict[str, int] = {}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as archive:
        for member in archive:
            path = PurePosixPath(member.name)
            if (
                path.is_absolute()
                or ".." in path.parts
                or "\\" in member.name
                or any(
                    ":" in part
                    or part.endswith((".", " "))
                    or any(ord(char) < 32 for char in part)
                    or re.fullmatch(r"(?i)(CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])(?:\..*)?", part)
                    for part in path.parts
                )
            ):
                raise ValueError("unsafe artifact path")
            for index in range(1, len(path.parts) + 1):
                prefix = "/".join(path.parts[:index])
                old = folded.setdefault(prefix.casefold(), prefix)
                if old != prefix:
                    raise ValueError("case-insensitive artifact path collision")
            if member.isdir():
                continue
            name = path.as_posix()
            if name == "." or not path.parts:
                raise ValueError("empty artifact file path")
            if not member.isfile() or name in files or member.size < 0:
                raise ValueError("unsupported artifact entry")
            total += member.size
            if total > LIMIT or len(files) >= 10000:
                raise ValueError("artifact tree exceeds bounded limit")
            source = archive.extractfile(member)
            if source is None:
                raise ValueError("artifact file has no contents")
            files[name] = source.read(LIMIT + 1)
            modes[name] = 0o755 if member.mode & 0o111 else 0o644
            if len(files[name]) != member.size:
                raise ValueError("artifact size mismatch")
    for name in files:
        if any(parent.as_posix() in files for parent in PurePosixPath(name).parents):
            raise ValueError("artifact file conflicts with directory")
    # Docker cp /path/. emits paths relative to '.', not the parent directory.
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("artifact destination must be empty")
    if destination.is_symlink() or any(parent.is_symlink() for parent in destination.parents):
        raise ValueError("artifact destination crosses a symlink")
    destination.mkdir(parents=True, exist_ok=True)
    for relative, contents in files.items():
        output = destination / relative
        if output.is_symlink() or any(p.is_symlink() for p in output.parents):
            raise ValueError("artifact destination crosses a symlink")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(contents)
        output.chmod(modes[relative])
    return files


def collect_tree(
    docker: Docker, container: str, source: str, destination: Path, *, timeout_seconds: float = 60
) -> None:
    """Drain Docker cp to a capped buffer; kill on overflow/time, then validate/write."""
    if not 0 < timeout_seconds <= 60:
        raise ValueError("collection timeout must be positive and at most 60 seconds")
    if source not in {"/app", "/logs/verifier"}:
        raise ValueError("unadmitted artifact source")
    process = subprocess.Popen(
        [*docker.argv, "cp", f"{container}:{source}/.", "-"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    data, error = bytearray(), bytearray()
    overflow = threading.Event()

    def drain(stream: object, output: bytearray, limit: int) -> None:
        assert stream is not None
        try:
            while chunk := stream.read(65536):  # type: ignore[attr-defined]
                remaining = max(0, limit - len(output))
                output.extend(chunk[:remaining])
                if len(chunk) > remaining:
                    overflow.set()
                    process.kill()
                    break
        finally:
            stream.close()  # type: ignore[attr-defined]

    threads = [
        threading.Thread(target=drain, args=(stream, output, limit), daemon=True)
        for stream, output, limit in ((process.stdout, data, LIMIT), (process.stderr, error, 65536))
    ]
    for thread in threads:
        thread.start()
    try:
        process.wait(timeout=timeout_seconds)
    except BaseException:
        process.kill()
        process.wait(timeout=5)
        raise
    finally:
        for thread in threads:
            thread.join(timeout=2)
    if overflow.is_set() or process.returncode or any(t.is_alive() for t in threads):
        raise RuntimeError("bounded artifact collection failed")
    unpack_regular(bytes(data), destination)
