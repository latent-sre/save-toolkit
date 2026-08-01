#!/usr/bin/env python3
"""Materialize a bounded, raw Git tree selection without checkout filters or hooks.

The authenticated acquisition step must finish before this program starts. The repository must have
no remotes, partial-clone configuration, credential configuration, or existing worktree files. Blob
bytes are read directly from the local object database with ``git cat-file --batch``; candidate
attributes, filters, hooks, submodules, and symlinks are never executed or materialized.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Sequence


COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")
SAFE_PATH = re.compile(r"^[A-Za-z0-9._/-]+$")
ALLOWED_MODES = {"100644": 0o644, "100755": 0o755}
MAX_TREE_ENTRIES = 5_000
MAX_TREE_BYTES = 64 * 1024 * 1024
MAX_FILE_BYTES = 8 * 1024 * 1024
MARKER_NAME = "sre-agents-materialization-v1.json"
FORBIDDEN_ENVIRONMENT = (
    "GH_TOKEN",
    "GITHUB_TOKEN",
    "OPENAI_API_KEY",
    "CODEX_CONFORMANCE_OPENAI_API_KEY",
)
FORBIDDEN_LOCAL_CONFIG = re.compile(
    r"(?:credential|extraheader|token|promisor|partialclone|proxy|"
    r"^remote\.|\.remote$|^url\.|^http\.|^include(?:if)?\.|^filter\.|^lfs\.|"
    r"^core\.(?:attributesfile|fsmonitor|hookspath|sshcommand)$)",
    re.I,
)
SAFE_ATTRIBUTES = "* -filter -working-tree-encoding -ident -text -eol\n"
MARKER_FIELDS = frozenset(
    {
        "schema_version",
        "repository_commit",
        "repository_tree",
        "paths",
        "entry_count",
        "byte_count",
        "selection_sha256",
        "filters_executed",
        "links_materialized",
    }
)


class MaterializationError(ValueError):
    """The object store or requested output cannot be materialized safely."""


@dataclass(frozen=True)
class TreeEntry:
    mode: str
    object_type: str
    object_id: str
    size: int
    path: str


def _git_environment() -> dict[str, str]:
    environment = dict(os.environ)
    for name in tuple(environment):
        if name.startswith(("GIT_", "SSH_")):
            environment.pop(name)
    environment["GIT_NO_LAZY_FETCH"] = "1"
    environment["GIT_NO_REPLACE_OBJECTS"] = "1"
    environment["GIT_CONFIG_NOSYSTEM"] = "1"
    environment["GIT_CONFIG_GLOBAL"] = os.devnull
    environment["GIT_ATTR_NOSYSTEM"] = "1"
    environment["GIT_TERMINAL_PROMPT"] = "0"
    return environment


def _git(
    repository: Path,
    arguments: Sequence[str],
    *,
    input_bytes: bytes | None = None,
) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        input=input_bytes,
        capture_output=True,
        check=False,
        env=_git_environment(),
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).decode("utf-8", errors="replace").strip()
        raise MaterializationError(
            f"git {' '.join(arguments)} failed: {detail[-500:]}"
        )
    return result.stdout


def _assert_credential_free_environment() -> None:
    present = [name for name in FORBIDDEN_ENVIRONMENT if os.environ.get(name)]
    if present:
        raise MaterializationError(
            "raw materialization requires a credential-free process; found " + ", ".join(present)
        )


def _assert_safe_local_config(repository: Path, allowed_controls: set[str] | None = None) -> None:
    allowed = {key.casefold() for key in (allowed_controls or set())}
    local_keys = _git(repository, ["config", "--local", "--name-only", "--list", "-z"])
    for raw_key in local_keys.split(b"\0"):
        if not raw_key:
            continue
        key = raw_key.decode("utf-8", errors="replace")
        if FORBIDDEN_LOCAL_CONFIG.search(key) and key.casefold() not in allowed:
            raise MaterializationError(f"object-store repository retains unsafe config: {key}")


def _assert_directory(path: Path, label: str) -> Path:
    absolute = path.expanduser().absolute()
    current = Path(absolute.anchor)
    for component in absolute.parts[1:]:
        current /= component
        if _is_link_or_reparse(current):
            raise MaterializationError(f"{label} traverses a linked or reparse path: {current}")
    if not absolute.is_dir() or _is_link_or_reparse(absolute):
        raise MaterializationError(f"{label} must be an existing unlinked directory: {absolute}")
    return absolute


def _is_link_or_reparse(path: Path) -> bool:
    try:
        attributes = path.lstat()
    except OSError:
        return False
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    file_attributes = getattr(attributes, "st_file_attributes", 0)
    return stat.S_ISLNK(attributes.st_mode) or bool(file_attributes & reparse_flag)


def _same_existing_path(left: Path, right: Path) -> bool:
    """Compare filesystem identity instead of path spelling.

    Windows runners can hand Python a short (8.3) temporary path while Git reports the long path.
    Both names identify the same directory, but string normalization cannot prove that. ``samefile``
    compares the underlying file identity and fails closed when either path cannot be inspected.
    """

    try:
        return left.samefile(right)
    except OSError:
        return False


def _assert_repository_layout(repository: Path, git_directory: Path) -> None:
    top_level = Path(_git(repository, ["rev-parse", "--show-toplevel"]).decode().strip())
    actual_git_directory = Path(
        _git(repository, ["rev-parse", "--absolute-git-dir"]).decode().strip()
    )
    if not _same_existing_path(top_level, repository):
        raise MaterializationError("object-store Git worktree resolves outside the repository")
    if not _same_existing_path(actual_git_directory, git_directory):
        raise MaterializationError("object-store Git metadata resolves outside the repository")
    for relative in ("objects/info/alternates", "objects/info/http-alternates"):
        if (git_directory / relative).exists():
            raise MaterializationError("object-store repository uses an alternate object database")
    pack_directory = git_directory / "objects" / "pack"
    if pack_directory.is_dir() and any(pack_directory.glob("*.promisor")):
        raise MaterializationError("object-store repository retains promisor metadata")


def _validate_requested_path(value: str) -> str:
    if not value or not SAFE_PATH.fullmatch(value) or "\\" in value:
        raise MaterializationError(f"unsafe requested path: {value!r}")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise MaterializationError(f"unsafe requested path: {value!r}")
    if any(part.casefold() == ".git" for part in path.parts):
        raise MaterializationError(f"requested path targets Git metadata: {value!r}")
    return path.as_posix().rstrip("/")


def _normalize_requested_paths(requested_paths: Sequence[str]) -> tuple[str, ...]:
    paths = tuple(_validate_requested_path(value) for value in requested_paths)
    if not paths:
        raise MaterializationError("at least one materialization path is required")
    if len(set(paths)) != len(paths):
        raise MaterializationError("materialization paths must not be duplicated")
    for index, path in enumerate(paths):
        for other in paths[index + 1 :]:
            if path.startswith(other + "/") or other.startswith(path + "/"):
                raise MaterializationError("materialization paths must not overlap")
    return paths


def _parse_tree(raw: bytes) -> list[TreeEntry]:
    entries: list[TreeEntry] = []
    seen_paths: set[str] = set()
    seen_casefold: dict[str, str] = {}
    total_bytes = 0
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            fields = metadata.split()
            if len(fields) != 4:
                raise ValueError("unexpected metadata field count")
            mode, object_type, object_id, raw_size = (
                field.decode("ascii", errors="strict") for field in fields
            )
            path = raw_path.decode("utf-8", errors="strict")
        except (UnicodeDecodeError, ValueError) as exc:
            raise MaterializationError("Git tree contains an unparseable entry") from exc
        if mode not in ALLOWED_MODES or object_type != "blob":
            raise MaterializationError(
                f"Git tree contains a linked, submodule, or unsupported entry: {mode} {path!r}"
            )
        try:
            size = int(raw_size)
        except ValueError as exc:
            raise MaterializationError(f"Git tree has an invalid size for {path!r}") from exc
        if not re.fullmatch(r"[0-9a-f]{40}", object_id):
            raise MaterializationError(f"Git tree contains an invalid object ID for {path!r}")
        if size < 0 or size > MAX_FILE_BYTES:
            raise MaterializationError(f"Git tree file exceeds the trusted size limit: {path!r}")
        normalized = _validate_requested_path(path)
        if normalized != path or path in seen_paths:
            raise MaterializationError(
                f"Git tree contains a duplicate or non-canonical path: {path!r}"
            )
        seen_paths.add(path)
        for index in range(1, len(PurePosixPath(path).parts) + 1):
            prefix = "/".join(PurePosixPath(path).parts[:index])
            folded = prefix.casefold()
            previous = seen_casefold.setdefault(folded, prefix)
            if previous != prefix:
                raise MaterializationError(
                    f"Git tree contains a case-colliding path: {previous!r} and {prefix!r}"
                )
        total_bytes += size
        if len(entries) + 1 > MAX_TREE_ENTRIES or total_bytes > MAX_TREE_BYTES:
            raise MaterializationError("Git tree exceeds the trusted entry or byte limit")
        entries.append(TreeEntry(mode, object_type, object_id, size, path))
    if not entries:
        raise MaterializationError("Git tree is empty")
    return entries


def _select_entries(entries: Sequence[TreeEntry], paths: Sequence[str]) -> list[TreeEntry]:
    selected = [
        entry
        for entry in entries
        if any(entry.path == path or entry.path.startswith(path + "/") for path in paths)
    ]
    for path in paths:
        if not any(entry.path == path or entry.path.startswith(path + "/") for entry in selected):
            raise MaterializationError(f"requested path is absent from the commit: {path!r}")
    return selected


def _read_blobs(repository: Path, entries: Sequence[TreeEntry]) -> list[bytes]:
    request = b"".join(entry.object_id.encode("ascii") + b"\n" for entry in entries)
    raw = _git(repository, ["cat-file", "--batch"], input_bytes=request)
    position = 0
    blobs: list[bytes] = []
    for entry in entries:
        line_end = raw.find(b"\n", position)
        if line_end < 0:
            raise MaterializationError("git cat-file returned a truncated object header")
        try:
            object_id, object_type, raw_size = raw[position:line_end].decode("ascii").split()
            size = int(raw_size)
        except (UnicodeDecodeError, ValueError) as exc:
            raise MaterializationError("git cat-file returned an invalid object header") from exc
        position = line_end + 1
        end = position + size
        if (
            object_id != entry.object_id
            or object_type != "blob"
            or size != entry.size
            or end >= len(raw)
            or raw[end : end + 1] != b"\n"
        ):
            raise MaterializationError(f"git cat-file object contract failed for {entry.path!r}")
        blobs.append(raw[position:end])
        position = end + 1
    if position != len(raw):
        raise MaterializationError("git cat-file returned unexpected trailing bytes")
    return blobs


def _write_blob(root: Path, entry: TreeEntry, data: bytes) -> None:
    destination = root.joinpath(*PurePosixPath(entry.path).parts)
    try:
        destination.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
        current = root
        for component in PurePosixPath(entry.path).parts[:-1]:
            current /= component
            attributes = current.lstat()
            if not stat.S_ISDIR(attributes.st_mode) or _is_link_or_reparse(current):
                raise MaterializationError(
                    f"materialized parent is not a real directory: {current}"
                )
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(destination, flags, ALLOWED_MODES[entry.mode])
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
        os.chmod(destination, ALLOWED_MODES[entry.mode])
    except MaterializationError:
        raise
    except OSError as exc:
        raise MaterializationError(f"cannot materialize {entry.path!r}: {exc}") from exc


def _write_exclusive(path: Path, data: bytes, mode: int) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags, mode)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
        os.chmod(path, mode)
    except OSError as exc:
        raise MaterializationError(f"cannot create trusted metadata {path}: {exc}") from exc


def _selection_digest(entries: Sequence[TreeEntry]) -> str:
    digest = hashlib.sha256()
    for entry in entries:
        for value in (entry.path, entry.mode, entry.object_id, str(entry.size)):
            digest.update(value.encode("utf-8"))
            digest.update(b"\0")
    return digest.hexdigest()


def _marker_for(
    commit: str,
    tree_id: str,
    paths: Sequence[str],
    entries: Sequence[TreeEntry],
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "repository_commit": commit,
        "repository_tree": tree_id,
        "paths": list(paths),
        "entry_count": len(entries),
        "byte_count": sum(entry.size for entry in entries),
        "selection_sha256": _selection_digest(entries),
        "filters_executed": False,
        "links_materialized": False,
    }


def _read_regular_file(path: Path, expected_size: int) -> tuple[bytes, os.stat_result]:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
        try:
            attributes = os.fstat(descriptor)
            if not stat.S_ISREG(attributes.st_mode):
                raise MaterializationError(f"materialized path is not a regular file: {path}")
            chunks: list[bytes] = []
            remaining = expected_size + 1
            while remaining:
                chunk = os.read(descriptor, min(remaining, 1024 * 1024))
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
        finally:
            os.close(descriptor)
    except MaterializationError:
        raise
    except OSError as exc:
        raise MaterializationError(f"cannot read materialized file {path}: {exc}") from exc
    data = b"".join(chunks)
    if len(data) != expected_size:
        raise MaterializationError(f"materialized file size differs from its Git object: {path}")
    return data, attributes


def _collect_materialized_files(
    repository: Path,
    paths: Sequence[str],
    entries: Sequence[TreeEntry],
) -> dict[str, Path]:
    exact_entries = {entry.path for entry in entries}
    files: dict[str, Path] = {}
    expected_directories: set[str] = set()
    for entry in entries:
        parts = PurePosixPath(entry.path).parts
        for index in range(1, len(parts)):
            prefix = "/".join(parts[:index])
            if any(prefix == path or prefix.startswith(path + "/") for path in paths):
                expected_directories.add(prefix)
    actual_directories: set[str] = set()
    for requested in paths:
        target = repository.joinpath(*PurePosixPath(requested).parts)
        if requested in exact_entries:
            if _is_link_or_reparse(target) or not target.is_file():
                raise MaterializationError(
                    f"materialized selection is not a regular file: {requested}"
                )
            files[requested] = target
            continue
        if _is_link_or_reparse(target) or not target.is_dir():
            raise MaterializationError(
                f"materialized selection is not a real directory: {requested}"
            )
        actual_directories.add(requested)
        for current, directories, names in os.walk(target, followlinks=False):
            current_path = Path(current)
            if _is_link_or_reparse(current_path):
                raise MaterializationError(
                    f"materialized selection contains a linked directory: {current_path}"
                )
            for name in directories:
                child = current_path / name
                relative = child.relative_to(repository).as_posix()
                if _is_link_or_reparse(child) or not child.is_dir():
                    raise MaterializationError(
                        f"materialized selection contains a linked directory: {relative}"
                    )
                actual_directories.add(relative)
            for name in names:
                child = current_path / name
                relative = child.relative_to(repository).as_posix()
                if _is_link_or_reparse(child) or not child.is_file():
                    raise MaterializationError(
                        f"materialized selection contains a non-regular file: {relative}"
                    )
                if relative in files:
                    raise MaterializationError(
                        f"materialized selection duplicates a path: {relative}"
                    )
                files[relative] = child
    if actual_directories != expected_directories:
        raise MaterializationError("materialized directory set differs from the selected Git tree")
    return files


def _git_blob_id(data: bytes) -> str:
    digest = hashlib.sha1(usedforsecurity=False)
    digest.update(f"blob {len(data)}\0".encode("ascii"))
    digest.update(data)
    return digest.hexdigest()


def materialize(repository: Path, commit: str, requested_paths: Sequence[str]) -> dict[str, object]:
    _assert_credential_free_environment()
    repository = _assert_directory(repository, "repository")
    git_directory = _assert_directory(repository / ".git", "Git metadata")
    _assert_repository_layout(repository, git_directory)
    if not COMMIT_SHA.fullmatch(commit):
        raise MaterializationError("commit must be a full lowercase SHA-1")
    paths = _normalize_requested_paths(requested_paths)
    unexpected = [path.name for path in repository.iterdir() if path.name != ".git"]
    if unexpected:
        raise MaterializationError(
            "object-store worktree must be empty before materialization: " + ", ".join(unexpected)
        )
    if _git(repository, ["remote"]).strip():
        raise MaterializationError("object-store repository must not retain a remote")
    _assert_safe_local_config(repository)
    resolved_commit = _git(repository, ["rev-parse", "--verify", f"{commit}^{{commit}}"])
    if resolved_commit.decode("ascii").strip() != commit:
        raise MaterializationError("object-store repository does not contain the exact commit")
    tree_id = _git(repository, ["rev-parse", f"{commit}^{{tree}}"])
    tree_id_text = tree_id.decode("ascii").strip()
    all_entries = _parse_tree(_git(repository, ["ls-tree", "-rlz", "--full-tree", commit]))
    selected = _select_entries(all_entries, paths)
    blobs = _read_blobs(repository, selected)

    disabled_hooks = git_directory / "sre-agents-disabled-hooks"
    try:
        disabled_hooks.mkdir(mode=0o700)
    except OSError as exc:
        raise MaterializationError(f"cannot create disabled hooks directory: {exc}") from exc
    _git(repository, ["config", "--local", "core.hooksPath", str(disabled_hooks)])
    _git(repository, ["config", "--local", "core.fsmonitor", "false"])
    _git(repository, ["config", "--local", "submodule.recurse", "false"])
    _git(repository, ["config", "--local", "core.autocrlf", "false"])
    info = _assert_directory(git_directory / "info", "Git info directory")
    attributes = info / "attributes"
    _write_exclusive(attributes, SAFE_ATTRIBUTES.encode("utf-8"), 0o600)
    for entry, data in zip(selected, blobs, strict=True):
        _write_blob(repository, entry, data)

    _git(repository, ["read-tree", "--reset", commit])
    _git(repository, ["update-ref", "--no-deref", "HEAD", commit])
    status = _git(repository, ["status", "--porcelain=v1", "--", *paths])
    if status.strip():
        raise MaterializationError("raw materialization differs from the selected Git objects")

    marker = _marker_for(commit, tree_id_text, paths, selected)
    marker_path = git_directory / MARKER_NAME
    _write_exclusive(
        marker_path,
        (json.dumps(marker, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        0o600,
    )
    verify_materialization(repository, paths)
    return marker


def verify_materialization(
    repository: Path,
    requested_paths: Sequence[str],
) -> dict[str, object]:
    """Recompute the marker and prove every selected file is the exact raw Git blob."""

    _assert_credential_free_environment()
    repository = _assert_directory(repository, "repository")
    git_directory = _assert_directory(repository / ".git", "Git metadata")
    _assert_repository_layout(repository, git_directory)
    paths = _normalize_requested_paths(requested_paths)
    if _git(repository, ["remote"]).strip():
        raise MaterializationError("materialized repository must not retain a remote")
    _assert_safe_local_config(repository, {"core.hooksPath", "core.fsmonitor"})

    marker_path = git_directory / MARKER_NAME
    if _is_link_or_reparse(marker_path) or not marker_path.is_file():
        raise MaterializationError("trusted raw-materialization marker is missing or linked")
    try:
        if marker_path.stat().st_size > 16 * 1024:
            raise MaterializationError("trusted raw-materialization marker exceeds its size limit")
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MaterializationError("trusted raw-materialization marker is invalid") from exc
    if not isinstance(marker, dict) or set(marker) != MARKER_FIELDS:
        raise MaterializationError(
            "trusted raw-materialization marker has unknown or missing fields"
        )
    commit = marker.get("repository_commit")
    if not isinstance(commit, str) or not COMMIT_SHA.fullmatch(commit):
        raise MaterializationError("trusted raw-materialization marker has an invalid commit")
    resolved_head = _git(repository, ["rev-parse", "--verify", "HEAD^{commit}"])
    if resolved_head.decode("ascii").strip() != commit:
        raise MaterializationError("materialized repository HEAD differs from the trusted marker")
    tree_id = _git(repository, ["rev-parse", f"{commit}^{{tree}}"])
    tree_id_text = tree_id.decode("ascii").strip()
    all_entries = _parse_tree(_git(repository, ["ls-tree", "-rlz", "--full-tree", commit]))
    selected = _select_entries(all_entries, paths)
    expected_marker = _marker_for(commit, tree_id_text, paths, selected)
    if marker != expected_marker:
        raise MaterializationError("trusted raw-materialization marker differs from Git objects")

    actual_files = _collect_materialized_files(repository, paths, selected)
    expected_files = {entry.path: entry for entry in selected}
    if set(actual_files) != set(expected_files):
        raise MaterializationError("materialized file set differs from the selected Git tree")
    for path, entry in expected_files.items():
        data, attributes = _read_regular_file(actual_files[path], entry.size)
        if _git_blob_id(data) != entry.object_id:
            raise MaterializationError(f"materialized bytes differ from the Git blob: {path!r}")
        if os.name != "nt":
            expected_executable = entry.mode == "100755"
            actual_executable = bool(stat.S_IMODE(attributes.st_mode) & 0o111)
            if actual_executable != expected_executable:
                raise MaterializationError(
                    f"materialized executable mode differs from Git: {path!r}"
                )

    disabled_hooks = _assert_directory(
        git_directory / "sre-agents-disabled-hooks", "disabled hooks directory"
    )
    try:
        if any(disabled_hooks.iterdir()):
            raise MaterializationError("disabled hooks directory must remain empty")
        attributes_path = git_directory / "info" / "attributes"
        if (
            _is_link_or_reparse(attributes_path)
            or attributes_path.read_bytes() != SAFE_ATTRIBUTES.encode()
        ):
            raise MaterializationError("trusted no-filter attributes are missing or changed")
    except MaterializationError:
        raise
    except OSError as exc:
        raise MaterializationError("cannot verify trusted Git controls") from exc
    expected_config = {
        "core.hooksPath": str(disabled_hooks),
        "core.fsmonitor": "false",
        "submodule.recurse": "false",
        "core.autocrlf": "false",
    }
    for key, expected_value in expected_config.items():
        values = _git(repository, ["config", "--local", "--get-all", key]).decode().splitlines()
        if values != [expected_value]:
            raise MaterializationError(f"trusted local Git control differs: {key}")
    status = _git(repository, ["status", "--porcelain=v1", "--", *paths])
    if status.strip():
        raise MaterializationError("materialized selection no longer matches the Git index")
    return marker


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--path", action="append", required=True, dest="paths")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        marker = materialize(args.repository, args.commit, args.paths)
    except MaterializationError as exc:
        print(f"materialize_git_tree: ERROR: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(marker, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
