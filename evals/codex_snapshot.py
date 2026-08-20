#!/usr/bin/env python3
"""Materialize fixed ROUTE-001 Git objects and stage a neutral Codex project.

The evaluator must not read routing inputs from the mutable checkout.  This module asks Git for
only the committed Codex projection needed by the campaign, validates the tar stream without
``extractall()``, and publishes ordinary files create-only into a caller-owned temporary directory.
The neutral project contains only the projected skills and custom agents.  Each custom-agent TOML
has its legacy ``sandbox_mode`` assignment removed so no child can widen the root evaluator's named
permission profile; both the source and transformed trees are bound into the returned receipt.
"""
from __future__ import annotations

import hashlib
import ctypes
import functools
import io
import json
import ntpath
import os
import posixpath
import re
import stat
import subprocess
import tarfile
import tomllib
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_REVISIONS = frozenset(
    {
        "a39a81f33f7ad7325c52d883822bbbdd80c7ed28",
        "b459a5d3a209d384acb2b2b7ca325aa63697113b",
    }
)
ARCHIVE_PATHS = (
    ".agents/plugins/marketplace.json",
    "plugins/save-toolkit",
    ".codex/agents",
    "plugin.json",
)
REQUIRED_MANIFESTS = (
    ".agents/plugins/marketplace.json",
    "plugin.json",
    "plugins/save-toolkit/.codex-plugin/plugin.json",
)

MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_TOTAL_BYTES = 32 * 1024 * 1024
MAX_FILE_BYTES = 8 * 1024 * 1024
MAX_MEMBERS = 4096
GIT_TIMEOUT_SECONDS = 60
MAX_GIT_EXECUTABLE_BYTES = 16 * 1024 * 1024
GIT_EXECUTABLE_PATH = Path(r"C:\Program Files\Git\mingw64\bin\git.exe")
GIT_EXECUTABLE_SHA256 = (
    "c39b1b4f7a57935bbeadf246dc2466316619453a6a9da77c4a9c6bd6d8fb21d3"
)
EXPECTED_SNAPSHOT_TREE_SHA256 = {
    "a39a81f33f7ad7325c52d883822bbbdd80c7ed28": (
        "195e5afad5ccd95f0aa3611b96cd31c8c1e9bc06818009603e2c4181240f62b5"
    ),
    "b459a5d3a209d384acb2b2b7ca325aa63697113b": (
        "867f92cccb6eff6e994f27eff7301722ebb82da24b6f2adcd26be92fe2babf4a"
    ),
}

_EXACT_FILES = frozenset({".agents/plugins/marketplace.json", "plugin.json"})
_FILE_PREFIXES = ("plugins/save-toolkit/", ".codex/agents/")
_EXACT_DIRECTORIES = frozenset(
    {
        ".agents",
        ".agents/plugins",
        ".codex",
        ".codex/agents",
        "plugins",
        "plugins/save-toolkit",
    }
)
_DIRECTORY_PREFIXES = ("plugins/save-toolkit/", ".codex/agents/")
_WINDOWS_RESERVED = frozenset(
    {"CON", "PRN", "AUX", "NUL", *(f"COM{number}" for number in range(1, 10)), *(f"LPT{number}" for number in range(1, 10))}
)
_SANDBOX_LINE = re.compile(
    br'^sandbox_mode = "(?:read-only|workspace-write|danger-full-access)"\n$'
)
_GENERATED_AGENT_FIELDS = frozenset(
    {"name", "description", "sandbox_mode", "developer_instructions"}
)
_DEVELOPER_INSTRUCTIONS_LINE = b"developer_instructions = '''\n"


class SnapshotError(ValueError):
    """The fixed snapshot or neutral staging boundary could not be proven safe."""


@dataclass(frozen=True)
class SnapshotReceipt:
    """Persistable snapshot facts; no filesystem path or manifest value is retained."""

    commit_sha: str
    file_count: int
    total_bytes: int
    tree_sha256: str


@dataclass(frozen=True)
class StageReceipt:
    """Persistable source/transformation facts for one neutral project."""

    skill_file_count: int
    agent_file_count: int
    transformed_agent_file_count: int
    total_bytes: int
    skill_tree_sha256: str
    source_agent_tree_sha256: str
    staged_agent_tree_sha256: str
    project_tree_sha256: str


def _is_link_or_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def _resolved_normal_directory(path: Path, *, label: str) -> Path:
    if _is_link_or_reparse(path):
        raise SnapshotError(f"{label} must not be a link or reparse point")
    try:
        metadata = path.lstat()
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise SnapshotError(f"{label} must be an existing directory") from exc
    if not stat.S_ISDIR(metadata.st_mode):
        raise SnapshotError(f"{label} must be an existing directory")
    return resolved


def _assert_no_indirection_below(root: Path, path: Path, *, label: str) -> None:
    """Reject every existing link/reparse component from ``root`` through ``path``."""

    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise SnapshotError(f"{label} must remain below its trusted root") from exc
    current = root
    for component in relative.parts:
        current /= component
        if (current.exists() or current.is_symlink()) and _is_link_or_reparse(current):
            raise SnapshotError(f"{label} must not traverse a link or reparse point")


def _is_below(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _require_outside_checkout(path: Path, *, label: str) -> None:
    checkout = REPO_ROOT.resolve()
    if path == checkout or _is_below(path, checkout):
        raise SnapshotError(f"{label} must be outside the mutable checkout")


def _sha256_regular_file(path: Path, *, label: str, max_bytes: int) -> str:
    candidate = Path(path)
    try:
        metadata = candidate.lstat()
        resolved = candidate.resolve(strict=True)
    except OSError as exc:
        raise SnapshotError(f"{label} is unavailable") from exc
    if (
        not candidate.is_absolute()
        or _is_link_or_reparse(candidate)
        or not stat.S_ISREG(metadata.st_mode)
        or resolved != candidate.absolute()
        or metadata.st_size <= 0
        or metadata.st_size > max_bytes
    ):
        raise SnapshotError(f"{label} must be one bounded ordinary absolute file")
    digest = hashlib.sha256()
    try:
        with candidate.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
    except OSError as exc:
        raise SnapshotError(f"{label} could not be read") from exc
    return digest.hexdigest()


def _pinned_git_executable(
    path: Path, *, expected_sha256: str = GIT_EXECUTABLE_SHA256
) -> tuple[Path, os.stat_result]:
    candidate = Path(path)
    digest = _sha256_regular_file(
        candidate, label="Git executable", max_bytes=MAX_GIT_EXECUTABLE_BYTES
    )
    resolved = candidate.resolve(strict=True)
    if resolved != path or digest != expected_sha256:
        raise SnapshotError("Git executable does not match the fixed protected-install pin")
    try:
        metadata = resolved.stat()
    except OSError as exc:
        raise SnapshotError("Git executable identity could not be read") from exc
    return resolved, metadata


def _git_environment(neutral_root: Path) -> dict[str, str]:
    env = _trusted_os_environment().copy()
    env.update(
        {
            "HOME": str(neutral_root),
            "USERPROFILE": str(neutral_root),
            "XDG_CONFIG_HOME": str(neutral_root / "xdg"),
            "TEMP": str(neutral_root),
            "TMP": str(neutral_root),
            "TMPDIR": str(neutral_root),
            "LANG": "C",
            "LC_ALL": "C",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_COUNT": "0",
            "GIT_ATTR_NOSYSTEM": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_PROTOCOL_FROM_USER": "0",
        }
    )
    return env


@functools.lru_cache(maxsize=1)
def _trusted_os_environment() -> dict[str, str]:
    if os.name == "nt":
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetWindowsDirectoryW.argtypes = (wintypes.LPWSTR, wintypes.UINT)
        kernel32.GetWindowsDirectoryW.restype = wintypes.UINT
        buffer = ctypes.create_unicode_buffer(32768)
        length = kernel32.GetWindowsDirectoryW(buffer, len(buffer))
        if length == 0 or length >= len(buffer):
            raise SnapshotError("trusted Windows directory could not be resolved")
        windows = Path(buffer.value).resolve(strict=True)
        system32 = windows / "System32"
        command_shell = system32 / "cmd.exe"
        if not command_shell.is_file() or _is_link_or_reparse(command_shell):
            raise SnapshotError("trusted Windows command shell is unavailable")
        return {
            "SYSTEMROOT": str(windows),
            "WINDIR": str(windows),
            "COMSPEC": str(command_shell.resolve(strict=True)),
            "PATH": str(system32),
            "PATHEXT": ".COM;.EXE;.BAT;.CMD",
        }
    return {"PATH": "/usr/bin:/bin", "COMSPEC": "/bin/sh"}


def _validate_member_name(raw_name: str, *, directory: bool) -> str:
    if not isinstance(raw_name, str) or not raw_name:
        raise SnapshotError("archive member has an empty name")
    if "\\" in raw_name:
        raise SnapshotError("archive member names must use POSIX separators")
    if any(ord(character) < 32 or ord(character) == 127 for character in raw_name):
        raise SnapshotError("archive member name contains a control character")
    try:
        raw_name.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise SnapshotError("archive member name is not valid Unicode") from exc
    if raw_name.endswith("/"):
        if not directory:
            raise SnapshotError("ordinary archive file has a directory suffix")
        raw_name = raw_name[:-1]
    if not raw_name:
        raise SnapshotError("archive member has an empty name")
    drive, _tail = ntpath.splitdrive(raw_name)
    if posixpath.isabs(raw_name) or ntpath.isabs(raw_name) or drive:
        raise SnapshotError("archive member path must be relative")
    parts = raw_name.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise SnapshotError("archive member path is not normalized")
    for part in parts:
        if part.endswith((" ", ".")) or ":" in part:
            raise SnapshotError("archive member path is not portable")
        stem = part.split(".", 1)[0].upper()
        if stem in _WINDOWS_RESERVED:
            raise SnapshotError("archive member path uses a reserved Windows name")
    return "/".join(parts)


def _member_is_allowed(name: str, *, directory: bool) -> bool:
    if directory:
        return name in _EXACT_DIRECTORIES or name.startswith(_DIRECTORY_PREFIXES)
    return name in _EXACT_FILES or name.startswith(_FILE_PREFIXES)


def _tree_sha256(files: Mapping[str, bytes]) -> str:
    digest = hashlib.sha256()
    for name in sorted(files):
        name_bytes = name.encode("utf-8")
        content = files[name]
        digest.update(len(name_bytes).to_bytes(4, "big"))
        digest.update(name_bytes)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _parse_archive(archive_bytes: bytes, expected_sha: str) -> dict[str, bytes]:
    if not archive_bytes:
        raise SnapshotError("git archive returned no bytes")
    if len(archive_bytes) > MAX_ARCHIVE_BYTES:
        raise SnapshotError("git archive exceeds the fixed byte limit")
    try:
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:") as archive:
            if archive.pax_headers.get("comment") != expected_sha:
                raise SnapshotError("git archive does not bind the requested commit")
            members = archive.getmembers()
            if not members or len(members) > MAX_MEMBERS:
                raise SnapshotError("git archive member count is empty or oversized")

            seen: set[str] = set()
            folded: dict[str, str] = {}
            files: dict[str, bytes] = {}
            total_bytes = 0
            for member in members:
                is_directory = member.type == tarfile.DIRTYPE
                name = _validate_member_name(member.name, directory=is_directory)
                if name in seen:
                    raise SnapshotError("git archive contains a duplicate member")
                seen.add(name)
                casefolded = name.casefold()
                if casefolded in folded:
                    raise SnapshotError("git archive contains a casefold path collision")
                folded[casefolded] = name
                if not _member_is_allowed(name, directory=is_directory):
                    raise SnapshotError("git archive contains a member outside the fixed allowlist")

                if is_directory:
                    if member.size != 0:
                        raise SnapshotError("git archive directory has a nonzero payload")
                    continue
                if member.type not in {tarfile.REGTYPE, tarfile.AREGTYPE}:
                    raise SnapshotError("git archive contains a nonordinary member")
                if member.size <= 0:
                    raise SnapshotError("git archive contains an empty file")
                if member.size > MAX_FILE_BYTES:
                    raise SnapshotError("git archive file exceeds the fixed byte limit")
                total_bytes += member.size
                if total_bytes > MAX_TOTAL_BYTES:
                    raise SnapshotError("git archive expands beyond the fixed byte limit")
                handle = archive.extractfile(member)
                if handle is None:
                    raise SnapshotError("git archive ordinary file has no payload")
                content = handle.read(member.size + 1)
                if len(content) != member.size:
                    raise SnapshotError("git archive payload size does not match its header")
                files[name] = content
    except SnapshotError:
        raise
    except (EOFError, OSError, OverflowError, ValueError, tarfile.TarError) as exc:
        raise SnapshotError("git archive is malformed") from exc

    if not files:
        raise SnapshotError("git archive contains no ordinary files")
    _verify_manifests(files)
    return files


def _reject_json_constant(value: str) -> object:
    raise SnapshotError(f"manifest contains a non-JSON numeric constant: {value}")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise SnapshotError("manifest contains a duplicate object key")
        result[key] = value
    return result


def _json_manifest(path: str, files: Mapping[str, bytes]) -> dict[str, object]:
    content = files.get(path)
    if content is None:
        raise SnapshotError("git archive is missing a required manifest")
    try:
        parsed = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        )
    except SnapshotError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise SnapshotError("required manifest is not valid UTF-8 JSON") from exc
    if not isinstance(parsed, dict):
        raise SnapshotError("required manifest must be a JSON object")
    return parsed


def _verify_manifests(files: Mapping[str, bytes]) -> None:
    marketplace = _json_manifest(REQUIRED_MANIFESTS[0], files)
    portable = _json_manifest(REQUIRED_MANIFESTS[1], files)
    codex = _json_manifest(REQUIRED_MANIFESTS[2], files)

    version = portable.get("version")
    if portable.get("name") != "save-toolkit" or not isinstance(version, str) or not version:
        raise SnapshotError("portable plugin manifest identity is invalid")
    if (
        codex.get("name") != "save-toolkit"
        or codex.get("version") != version
        or codex.get("skills") != "./skills/"
    ):
        raise SnapshotError("Codex plugin manifest does not match the portable manifest")
    plugins = marketplace.get("plugins")
    if marketplace.get("name") != "latent-sre" or not isinstance(plugins, list):
        raise SnapshotError("marketplace manifest identity is invalid")
    matching = [
        item
        for item in plugins
        if isinstance(item, dict) and item.get("name") == "save-toolkit"
    ]
    if len(matching) != 1 or matching[0].get("source") != {
        "source": "local",
        "path": "./plugins/save-toolkit",
    }:
        raise SnapshotError("marketplace manifest does not bind the local save-toolkit plugin")


def _expected_directories(files: Mapping[str, bytes]) -> set[str]:
    directories: set[str] = set()
    for name in files:
        parent = PurePosixPath(name).parent
        while parent != PurePosixPath("."):
            directories.add(parent.as_posix())
            parent = parent.parent
    return directories


def _scan_regular_tree(root: Path, *, label: str) -> tuple[dict[str, bytes], set[str]]:
    resolved = _resolved_normal_directory(root, label=label)
    files: dict[str, bytes] = {}
    directories: set[str] = set()
    folded_paths: set[str] = set()
    total_bytes = 0
    for current, child_directories, child_files in os.walk(resolved, followlinks=False):
        current_path = Path(current)
        if _is_link_or_reparse(current_path):
            raise SnapshotError(f"{label} must not traverse a link or reparse point")
        relative_current = current_path.relative_to(resolved)
        if relative_current.parts:
            directories.add(relative_current.as_posix())
        child_directories.sort()
        child_files.sort()
        if len(directories) + len(child_directories) + len(files) + len(child_files) > MAX_MEMBERS:
            raise SnapshotError(f"{label} contains too many entries")
        for name in child_directories:
            child = current_path / name
            if _is_link_or_reparse(child):
                raise SnapshotError(f"{label} must not contain a link or reparse point")
            try:
                metadata = child.lstat()
            except OSError as exc:
                raise SnapshotError(f"{label} changed while it was scanned") from exc
            if not stat.S_ISDIR(metadata.st_mode):
                raise SnapshotError(f"{label} contains a non-directory traversal entry")
        for name in child_files:
            child = current_path / name
            if _is_link_or_reparse(child):
                raise SnapshotError(f"{label} must not contain a link or reparse point")
            try:
                metadata = child.lstat()
                content = child.read_bytes()
            except OSError as exc:
                raise SnapshotError(f"{label} changed while it was scanned") from exc
            if not stat.S_ISREG(metadata.st_mode):
                raise SnapshotError(f"{label} contains a nonordinary file")
            if not content:
                raise SnapshotError(f"{label} contains an empty file")
            if len(content) > MAX_FILE_BYTES:
                raise SnapshotError(f"{label} contains an oversized file")
            total_bytes += len(content)
            if total_bytes > MAX_TOTAL_BYTES:
                raise SnapshotError(f"{label} exceeds the fixed byte limit")
            relative = child.relative_to(resolved).as_posix()
            folded = relative.casefold()
            if folded in folded_paths:
                raise SnapshotError(f"{label} contains a casefold path collision")
            folded_paths.add(folded)
            files[relative] = content
    return files, directories


def _write_plan_create_only(root: Path, files: Mapping[str, bytes]) -> None:
    directories = sorted(
        _expected_directories(files),
        key=lambda value: (len(PurePosixPath(value).parts), value),
    )
    try:
        for relative in directories:
            (root / Path(*PurePosixPath(relative).parts)).mkdir()
        for relative in sorted(files):
            target = root / Path(*PurePosixPath(relative).parts)
            _assert_no_indirection_below(
                root, target.parent, label="create-only target parent"
            )
            with target.open("xb") as handle:
                handle.write(files[relative])
                handle.flush()
    except SnapshotError:
        raise
    except OSError as exc:
        raise SnapshotError("create-only publication failed") from exc


def _verify_exact_tree(root: Path, expected: Mapping[str, bytes], *, label: str) -> None:
    actual, directories = _scan_regular_tree(root, label=label)
    if directories != _expected_directories(expected) or actual != dict(expected):
        raise SnapshotError(f"{label} has exact-copy drift")


def materialize_snapshot(
    repo_root: Path | str,
    revision: str,
    destination: Path | str,
    *,
    git_executable: Path | str = GIT_EXECUTABLE_PATH,
    git_executable_sha256: str | None = None,
    command_runner: Callable[..., subprocess.CompletedProcess[bytes]] | None = None,
) -> SnapshotReceipt:
    """Materialize one fixed ROUTE-001 commit into an existing empty temp directory."""

    if revision not in ALLOWED_REVISIONS:
        raise SnapshotError("revision is not a fixed ROUTE-001 full Git SHA")
    repository = _resolved_normal_directory(Path(repo_root), label="repository root")
    git_directory = _resolved_normal_directory(
        repository / ".git", label="repository Git directory"
    )
    target = _resolved_normal_directory(Path(destination), label="snapshot destination")
    _require_outside_checkout(target, label="snapshot destination")
    try:
        if any(target.iterdir()):
            raise SnapshotError("snapshot destination must be empty")
    except OSError as exc:
        raise SnapshotError("snapshot destination could not be inspected") from exc

    expected_git_sha256 = (
        GIT_EXECUTABLE_SHA256
        if git_executable_sha256 is None
        else git_executable_sha256
    )
    git_binary, git_before = _pinned_git_executable(
        Path(git_executable), expected_sha256=expected_git_sha256
    )
    command = [
        str(git_binary),
        "--no-pager",
        "--no-replace-objects",
        f"--git-dir={git_directory}",
        "archive",
        "--format=tar",
        revision,
        "--",
        *ARCHIVE_PATHS,
    ]
    try:
        runner = command_runner if command_runner is not None else subprocess.run
        process = runner(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            cwd=target,
            env=_git_environment(target),
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SnapshotError("git archive could not be executed") from exc
    if process.returncode != 0:
        raise SnapshotError("git archive failed for the fixed revision")
    if not isinstance(process.stdout, bytes):
        raise SnapshotError("git archive did not return a binary tar stream")
    try:
        git_after = git_binary.stat()
    except OSError as exc:
        raise SnapshotError("Git executable changed during snapshot materialization") from exc
    if (
        git_before.st_size != git_after.st_size
        or git_before.st_mtime_ns != git_after.st_mtime_ns
        or git_before.st_ino != git_after.st_ino
        or git_before.st_dev != git_after.st_dev
        or _sha256_regular_file(
            git_binary, label="Git executable", max_bytes=MAX_GIT_EXECUTABLE_BYTES
        )
        != expected_git_sha256
    ):
        raise SnapshotError("Git executable changed during snapshot materialization")

    files = _parse_archive(process.stdout, revision)
    tree_sha256 = _tree_sha256(files)
    if tree_sha256 != EXPECTED_SNAPSHOT_TREE_SHA256[revision]:
        raise SnapshotError("git archive does not match the fixed snapshot tree digest")
    _write_plan_create_only(target, files)
    _verify_exact_tree(target, files, label="materialized snapshot")
    return SnapshotReceipt(
        commit_sha=revision,
        file_count=len(files),
        total_bytes=sum(len(content) for content in files.values()),
        tree_sha256=tree_sha256,
    )


def _parse_agent_toml(content: bytes) -> dict[str, object]:
    try:
        parsed = tomllib.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
        raise SnapshotError("custom-agent profile is not valid UTF-8 TOML") from exc
    if not isinstance(parsed, dict):
        raise SnapshotError("custom-agent profile must be a TOML document")
    return parsed


def _expected_agent_transform(source: bytes) -> bytes:
    lines = source.splitlines(keepends=True)
    try:
        developer_index = lines.index(_DEVELOPER_INSTRUCTIONS_LINE)
    except ValueError as exc:
        raise SnapshotError("custom-agent profile lacks the generated instruction boundary") from exc
    candidates = [
        index
        for index, line in enumerate(lines[:developer_index])
        if line.lstrip().startswith(b"sandbox_mode")
    ]
    if len(candidates) != 1 or not _SANDBOX_LINE.fullmatch(lines[candidates[0]]):
        raise SnapshotError("custom-agent profile must contain one canonical sandbox_mode assignment")

    before = _parse_agent_toml(source)
    if set(before) != _GENERATED_AGENT_FIELDS or any(
        not isinstance(before[field], str) for field in _GENERATED_AGENT_FIELDS
    ):
        raise SnapshotError(
            "custom-agent profile contains unsupported configuration fields"
        )
    if before.get("sandbox_mode") not in {
        "read-only",
        "workspace-write",
        "danger-full-access",
    }:
        raise SnapshotError("custom-agent sandbox_mode is not a supported generated value")
    transformed = b"".join(lines[: candidates[0]] + lines[candidates[0] + 1 :])
    after = _parse_agent_toml(transformed)
    expected_after = dict(before)
    del expected_after["sandbox_mode"]
    if after != expected_after or "sandbox_mode" in after:
        raise SnapshotError("custom-agent transform changed fields beyond sandbox_mode")
    return transformed


def transform_agent_toml(source: bytes) -> bytes:
    """Remove exactly one generated top-level ``sandbox_mode`` assignment."""

    return _expected_agent_transform(source)


def _verify_agent_transform(source: bytes, transformed: bytes) -> None:
    if transformed != _expected_agent_transform(source):
        raise SnapshotError("custom-agent transform changed bytes beyond sandbox_mode")


def _validate_neutral_workspace(workspace: Path) -> None:
    try:
        entries = {entry.name: entry for entry in workspace.iterdir()}
    except OSError as exc:
        raise SnapshotError("neutral workspace could not be inspected") from exc
    if entries:
        raise SnapshotError("neutral workspace contains pre-existing project content")


def _verify_neutral_layout(workspace: Path) -> None:
    expected = {".agents", ".codex"}
    try:
        entries = {entry.name: entry for entry in workspace.iterdir()}
    except OSError as exc:
        raise SnapshotError("neutral workspace changed while it was verified") from exc
    if set(entries) != expected:
        raise SnapshotError("neutral workspace acquired unexpected project content")
    for name in (".agents", ".codex"):
        _resolved_normal_directory(entries[name], label="staged project root")
    if set(entry.name for entry in entries[".agents"].iterdir()) != {"skills"}:
        raise SnapshotError("staged .agents root contains unexpected content")
    if set(entry.name for entry in entries[".codex"].iterdir()) != {"agents"}:
        raise SnapshotError("staged .codex root contains unexpected content")


def _copy_plan_create_only(workspace: Path, files: Mapping[str, bytes]) -> None:
    _write_plan_create_only(workspace, files)


def stage_neutral_project(
    snapshot_root: Path | str,
    project_root: Path | str,
) -> StageReceipt:
    """Stage only committed skills and transformed agents into a neutral Codex project."""

    snapshot = _resolved_normal_directory(Path(snapshot_root), label="snapshot root")
    workspace = _resolved_normal_directory(Path(project_root), label="neutral workspace")
    _require_outside_checkout(snapshot, label="snapshot root")
    _require_outside_checkout(workspace, label="neutral workspace")
    if _is_below(workspace, snapshot) or _is_below(snapshot, workspace):
        raise SnapshotError("snapshot and neutral workspace must not contain one another")
    _validate_neutral_workspace(workspace)

    skill_source = snapshot / "plugins" / "save-toolkit" / "skills"
    agent_source = snapshot / ".codex" / "agents"
    _assert_no_indirection_below(snapshot, skill_source, label="snapshot skills")
    _assert_no_indirection_below(snapshot, agent_source, label="snapshot agents")
    skills, _skill_directories = _scan_regular_tree(skill_source, label="snapshot skills")
    agents, _agent_directories = _scan_regular_tree(agent_source, label="snapshot agents")
    if not skills or not any(PurePosixPath(name).name == "SKILL.md" for name in skills):
        raise SnapshotError("snapshot contains no staged Codex skills")
    if not agents:
        raise SnapshotError("snapshot contains no staged Codex agents")
    for relative in agents:
        path = PurePosixPath(relative)
        if len(path.parts) != 1 or path.suffix.lower() != ".toml":
            raise SnapshotError("snapshot Codex agents must be flat TOML files")

    transformed_agents: dict[str, bytes] = {}
    for relative, source in agents.items():
        transformed = transform_agent_toml(source)
        _verify_agent_transform(source, transformed)
        transformed_agents[relative] = transformed

    plan = {
        **{f".agents/skills/{relative}": content for relative, content in skills.items()},
        **{
            f".codex/agents/{relative}": content
            for relative, content in transformed_agents.items()
        },
    }
    _copy_plan_create_only(workspace, plan)

    # Re-read both sources to catch a mutation between planning and publication, then verify every
    # staged byte independently of the copy operation.
    current_skills, _ = _scan_regular_tree(skill_source, label="snapshot skills")
    current_agents, _ = _scan_regular_tree(agent_source, label="snapshot agents")
    if current_skills != skills or current_agents != agents:
        raise SnapshotError("snapshot changed while the neutral project was staged")
    _verify_exact_tree(
        workspace / ".agents" / "skills",
        skills,
        label="staged skills",
    )
    _verify_exact_tree(
        workspace / ".codex" / "agents",
        transformed_agents,
        label="staged agents",
    )
    _verify_neutral_layout(workspace)

    return StageReceipt(
        skill_file_count=len(skills),
        agent_file_count=len(agents),
        transformed_agent_file_count=len(transformed_agents),
        total_bytes=sum(len(content) for content in plan.values()),
        skill_tree_sha256=_tree_sha256(skills),
        source_agent_tree_sha256=_tree_sha256(agents),
        staged_agent_tree_sha256=_tree_sha256(transformed_agents),
        project_tree_sha256=_tree_sha256(plan),
    )


def verify_staged_project(
    snapshot_root: Path | str,
    project_root: Path | str,
    receipt: StageReceipt,
) -> None:
    """Re-prove source and staged bytes against a prior stage receipt without writing."""

    if not isinstance(receipt, StageReceipt):
        raise SnapshotError("stage receipt has the wrong type")
    snapshot = _resolved_normal_directory(Path(snapshot_root), label="snapshot root")
    workspace = _resolved_normal_directory(Path(project_root), label="neutral workspace")
    _require_outside_checkout(snapshot, label="snapshot root")
    _require_outside_checkout(workspace, label="neutral workspace")
    if _is_below(workspace, snapshot) or _is_below(snapshot, workspace):
        raise SnapshotError("snapshot and neutral workspace must not contain one another")

    skill_source = snapshot / "plugins" / "save-toolkit" / "skills"
    agent_source = snapshot / ".codex" / "agents"
    _assert_no_indirection_below(snapshot, skill_source, label="snapshot skills")
    _assert_no_indirection_below(snapshot, agent_source, label="snapshot agents")
    skills, _ = _scan_regular_tree(skill_source, label="snapshot skills")
    agents, _ = _scan_regular_tree(agent_source, label="snapshot agents")
    transformed_agents = {
        relative: transform_agent_toml(content)
        for relative, content in agents.items()
    }
    plan = {
        **{f".agents/skills/{relative}": content for relative, content in skills.items()},
        **{
            f".codex/agents/{relative}": content
            for relative, content in transformed_agents.items()
        },
    }
    expected = StageReceipt(
        skill_file_count=len(skills),
        agent_file_count=len(agents),
        transformed_agent_file_count=len(transformed_agents),
        total_bytes=sum(len(content) for content in plan.values()),
        skill_tree_sha256=_tree_sha256(skills),
        source_agent_tree_sha256=_tree_sha256(agents),
        staged_agent_tree_sha256=_tree_sha256(transformed_agents),
        project_tree_sha256=_tree_sha256(plan),
    )
    if expected != receipt:
        raise SnapshotError("snapshot source no longer matches the stage receipt")
    _verify_exact_tree(
        workspace / ".agents" / "skills", skills, label="staged skills"
    )
    _verify_exact_tree(
        workspace / ".codex" / "agents",
        transformed_agents,
        label="staged agents",
    )
    _verify_neutral_layout(workspace)
