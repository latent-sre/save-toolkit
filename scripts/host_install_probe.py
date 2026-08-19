#!/usr/bin/env python3
"""Prove disposable fleet install, inventory, authority boundary, and uninstall per host.

For each requested host the probe installs the fleet into an explicit, initially empty disposable
target, checks host-visible inventory, checks watched user configuration for residual metadata
changes, then uninstalls and confirms no residue. It redirects writable configuration pointers away
from user-owned plugin, agent, and settings locations, never provisions credentials, and never starts
a model session. The before/after census is defense in depth, not structural proof that no transient
or metadata-restored write occurred. An unavailable host is ``skip``; a CLI that cannot complete a
verb is ``inconclusive``; only an observed boundary violation or uninstall residue is ``fail``.
Diagnostic mode preserves those four states; ``--require-pass`` is the release-gate mode and returns
nonzero unless every selected criterion is ``pass`` and the source worktree is clean.

Claude and Codex can register either the exact checkout root or this repository's version-tag source
(``latent-sre/save-toolkit@save-toolkit--v<SemVer>``). No arbitrary repository, URL, branch, or moving
ref is accepted. The release workflow separately proves that the tag is protected and resolves to
this checkout revision. Codex proves both its skills-plugin lifecycle and the marker-managed custom
agents from the same checkout.

The Copilot CLI mirrors the Claude flow: a local-path marketplace registration, an explicit
plugin id install, an exact-row inventory check, and an uninstall verb, all against a
credential-free disposable HOME.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence

# Importing repository helpers must not create scripts/__pycache__ in a clean checkout.
sys.dont_write_bytecode = True

try:
    from scripts import (
        evidence_envelope,
        fleet_doctor,
        generate_platform_adapters,
        install_codex_agents,
        verification_sandbox,
    )
except ModuleNotFoundError:
    import evidence_envelope  # type: ignore[no-redef]
    import fleet_doctor  # type: ignore[no-redef]
    import generate_platform_adapters  # type: ignore[no-redef]
    import install_codex_agents  # type: ignore[no-redef]
    import verification_sandbox  # type: ignore[no-redef]


REPO_ROOT = Path(__file__).resolve().parents[1]
HOSTS = ("claude", "codex", "vscode", "copilot")
CLI_COMMANDS = {"claude": "claude", "codex": "codex", "vscode": "code", "copilot": "copilot"}
CRITERIA = ("install", "inventory", "authority", "uninstall")
CLAUDE_PLUGIN_ID = "save-toolkit@latent-sre"
CODEX_PLUGIN_ID = "save-toolkit@latent-sre"
COPILOT_PLUGIN_ID = "save-toolkit@latent-sre"
MARKETPLACE_NAME = "latent-sre"
RELEASE_MARKETPLACE_PREFIX = "latent-sre/save-toolkit@save-toolkit--v"
_SEMVER_IDENTIFIER = r"(?:0|[1-9]\d*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)"
_SEMVER_RE = (
    r"(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)"
    rf"(?:-{_SEMVER_IDENTIFIER}(?:\.{_SEMVER_IDENTIFIER})*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)
RELEASE_MARKETPLACE_SOURCE_RE = re.compile(
    rf"latent-sre/save-toolkit@(?P<tag>save-toolkit--v(?P<version>{_SEMVER_RE}))\Z"
)
MODEL_LIMITATION = (
    "No model session was started; requested/observed model fields are absent by design "
    "(model behavior is an EVAL-001 concern)."
)
CREDENTIAL_LIMITATION = (
    "No credentials were provisioned; a CLI verb requiring authentication reports inconclusive."
)

Check = fleet_doctor.Check
CommandResult = fleet_doctor.CommandResult
Runner = Callable[[Sequence[str], Mapping[str, str] | None], CommandResult]
GitRunner = Callable[[Sequence[str]], CommandResult]
Which = Callable[[str], str | None]
ExpectedGitTree = dict[str, str]


def _command_name(executable: str) -> str:
    return Path(executable).stem.lower()


def _normalize_marketplace_source(
    source: str | os.PathLike[str] | None, *, root: Path
) -> str:
    """Accept only this checkout or this repository's pinned release-version tag shape."""

    root = root.resolve()
    if source is None:
        return str(root)
    candidate = os.fspath(source).strip()
    if not candidate:
        raise ValueError("marketplace source must not be empty")
    if RELEASE_MARKETPLACE_SOURCE_RE.fullmatch(candidate):
        return candidate
    try:
        candidate_path = Path(candidate).expanduser().resolve()
    except OSError as exc:
        raise ValueError(f"marketplace source is not a valid path: {candidate!r}") from exc
    if candidate_path == root:
        return str(root)
    raise ValueError(
        "marketplace source must be the exact checkout root or "
        f"{RELEASE_MARKETPLACE_PREFIX}<semver>: {candidate!r}"
    )


def _marketplace_source_identity(source: str, *, root: Path) -> dict[str, str]:
    matched = RELEASE_MARKETPLACE_SOURCE_RE.fullmatch(source)
    if matched:
        return {
            "marketplace_source": source,
            "marketplace_source_kind": "pinned-version-tag",
            "marketplace_tag": matched.group("tag"),
            "marketplace_version": matched.group("version"),
        }
    if Path(source).resolve() != root.resolve():
        raise ValueError("normalized local marketplace source no longer matches the checkout root")
    return {
        "marketplace_source": source,
        "marketplace_source_kind": "local-checkout",
    }


def _marketplace_source_limitations(source: str) -> tuple[str, ...]:
    if RELEASE_MARKETPLACE_SOURCE_RE.fullmatch(source):
        return (
            "The probe proves the CLI marketplace checkout and installed ordinary-file paths and "
            "Git blob bytes match the source revision; the release workflow separately proves "
            "that the remote tag is protected and immutable.",
        )
    return ()


def _expected_marketplace_version(source: str, *, root: Path) -> str:
    matched = RELEASE_MARKETPLACE_SOURCE_RE.fullmatch(source)
    if matched:
        return matched.group("version")
    manifest = root / "plugin.json"
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise ValueError("could not read the local marketplace version") from exc
    version = payload.get("version") if isinstance(payload, dict) else None
    if not isinstance(version, str) or not version:
        raise ValueError("local marketplace manifest has no version")
    return version


def _ordinary_contained_directory(path: Path, *, container: Path) -> Path | None:
    """Return a direct ordinary directory below ``container`` or fail closed with ``None``."""

    container = Path(os.path.abspath(container))
    try:
        container_info = container.lstat()
        if verification_sandbox._is_indirection(container) or not stat.S_ISDIR(
            container_info.st_mode
        ):
            return None
        container = container.resolve(strict=True)
    except (OSError, verification_sandbox.SandboxError):
        return None
    candidate = Path(os.path.abspath(path))
    try:
        relative = candidate.relative_to(container)
    except ValueError:
        return None
    if not relative.parts:
        return None
    current = container
    try:
        for component in relative.parts:
            current /= component
            if not os.path.lexists(current):
                return None
            if verification_sandbox._is_indirection(current):
                return None
        resolved = candidate.resolve(strict=True)
        info = candidate.lstat()
    except (OSError, verification_sandbox.SandboxError):
        return None
    if not resolved.is_relative_to(container) or not stat.S_ISDIR(info.st_mode):
        return None
    return resolved


def _assert_host_git_command(argv: Sequence[str]) -> None:
    """Allow only the repository checks and immutable marketplace object reads."""

    if not argv or _command_name(argv[0]) != "git":
        raise ValueError("host install probe refused a non-Git provenance command")
    tail = tuple(argv[1:])
    repository_read = (
        len(tail) >= 5
        and tail[:2] == ("--no-optional-locks", "-C")
        and tuple(tail[3:]) in {("rev-parse", "HEAD"), ("status", "--short")}
    )
    object_read = False
    if (
        len(tail) >= 7
        and tail[:2] == ("--no-optional-locks", "--no-replace-objects")
        and tail[2].startswith("--git-dir=")
        and tail[3].startswith("--work-tree=")
    ):
        git_dir = Path(tail[2].partition("=")[2])
        work_tree = Path(tail[3].partition("=")[2])
        try:
            paths_match = (
                git_dir.is_absolute()
                and work_tree.is_absolute()
                and git_dir.resolve(strict=True) == (work_tree / ".git").resolve(strict=True)
            )
        except OSError:
            paths_match = False
        object_tail = tuple(tail[4:])
        object_read = paths_match and (
            object_tail == ("rev-parse", "--verify", "HEAD^{commit}")
            or (
                len(object_tail) == 4
                and object_tail[:3] == ("ls-tree", "-rz", "--full-tree")
                and re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", object_tail[3])
                is not None
            )
        )
    if not repository_read and not object_read:
        raise ValueError(
            "host install probe refused a Git command outside its read-only allowlist: "
            + repr(list(argv))
        )


def _run_host_git(argv: Sequence[str]) -> CommandResult:
    """Run the narrow Git read set without inheriting caller-controlled Git configuration."""

    _assert_host_git_command(argv)
    inherited = ("PATH", "PATHEXT", "SYSTEMROOT", "WINDIR")
    env = {name: os.environ[name] for name in inherited if name in os.environ}
    env.update(
        {
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    try:
        result = subprocess.run(
            list(argv),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=30,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CommandResult(127, "", type(exc).__name__)
    return CommandResult(result.returncode, result.stdout, result.stderr)


def _safe_git_tree_path(path: str) -> bool:
    if (
        not path
        or path.startswith("/")
        or "\\" in path
        or ":" in path
        or "\ufffd" in path
        or any(ord(character) < 32 for character in path)
    ):
        return False
    parts = path.split("/")
    return all(part not in {"", ".", ".."} for part in parts)


def _expected_git_tree(
    output: str,
    *,
    source_prefix: str,
    required_manifest: str,
    object_id_length: int,
) -> ExpectedGitTree | None:
    """Parse one NUL-delimited Git tree into the host-selected immutable blob map."""

    if object_id_length not in {40, 64} or not output or not output.endswith("\0"):
        return None
    if "\ufffd" in output:
        return None
    prefix = source_prefix.strip("/")
    prefix_with_separator = f"{prefix}/" if prefix else ""
    expected: ExpectedGitTree = {}
    normalized_paths: set[str] = set()
    for record in output[:-1].split("\0"):
        if not record:
            return None
        header, separator, repository_path = record.partition("\t")
        fields = header.split(" ")
        if not separator or len(fields) != 3:
            return None
        mode, object_type, object_id = fields
        if prefix_with_separator:
            if not repository_path.startswith(prefix_with_separator):
                continue
            relative = repository_path[len(prefix_with_separator) :]
        else:
            relative = repository_path
        if not _safe_git_tree_path(relative):
            return None
        if mode not in {"100644", "100755"} or object_type != "blob":
            return None
        if re.fullmatch(rf"[0-9a-f]{{{object_id_length}}}", object_id) is None:
            return None
        normalized = relative.casefold()
        if relative in expected or normalized in normalized_paths:
            return None
        expected[relative] = object_id
        normalized_paths.add(normalized)
    if not expected or required_manifest not in expected:
        return None
    return expected


def _git_blob_object_id(content: bytes, *, object_id_length: int) -> str | None:
    payload = b"blob " + str(len(content)).encode("ascii") + b"\0" + content
    if object_id_length == 40:
        # This reproduces Git's existing object format; it does not select SHA-1 for new security.
        return hashlib.sha1(payload, usedforsecurity=False).hexdigest()
    if object_id_length == 64:
        return hashlib.sha256(payload).hexdigest()
    return None


def _tree_matches_expected(
    files: dict[str, bytes] | None, expected: ExpectedGitTree | None
) -> bool:
    if files is None or not expected or set(files) != set(expected):
        return False
    object_id_length = len(next(iter(expected.values())))
    return all(
        _git_blob_object_id(files[path], object_id_length=object_id_length)
        == expected[path]
        for path in expected
    )


def _marketplace_checkout_provenance(
    checkout: Path,
    *,
    target: Path,
    expected_revision: str,
    git_run: GitRunner,
    source_prefix: str,
    required_manifest: str,
) -> tuple[str | None, bool, bool, Path | None, ExpectedGitTree | None]:
    checkout = _ordinary_contained_directory(checkout, container=target)
    if checkout is None:
        return None, False, False, None, None
    git_metadata = checkout / ".git"
    try:
        git_info = git_metadata.lstat()
        if verification_sandbox._is_indirection(git_metadata) or not stat.S_ISDIR(
            git_info.st_mode
        ):
            return None, False, False, checkout, None
    except (OSError, verification_sandbox.SandboxError):
        return None, False, False, checkout, None
    base_argv = (
        "git",
        "--no-optional-locks",
        "--no-replace-objects",
        f"--git-dir={git_metadata}",
        f"--work-tree={checkout}",
    )
    argv = (*base_argv, "rev-parse", "--verify", "HEAD^{commit}")
    result = git_run(argv)
    observed = result.stdout.strip().lower()
    expected_revision = expected_revision.lower()
    if (
        result.returncode
        or re.fullmatch(r"[0-9a-f]{40,64}", observed) is None
        or len(observed) != len(expected_revision)
    ):
        observed_revision: str | None = None
        revision_matches = False
    else:
        observed_revision = observed
        revision_matches = observed == expected_revision
    if observed_revision is None:
        return observed_revision, revision_matches, False, checkout, None
    tree_result = git_run(
        (*base_argv, "ls-tree", "-rz", "--full-tree", observed_revision)
    )
    expected_tree = (
        _expected_git_tree(
            tree_result.stdout,
            source_prefix=source_prefix,
            required_manifest=required_manifest,
            object_id_length=len(observed_revision),
        )
        if tree_result.returncode == 0
        else None
    )
    source_root = (
        checkout
        if not source_prefix
        else checkout.joinpath(*source_prefix.strip("/").split("/"))
    )
    first_files, first_root = _ordinary_tree_files(
        source_root,
        target=target,
        omit_root_git_metadata=not source_prefix,
    )
    second_files, second_root = _ordinary_tree_files(
        source_root,
        target=target,
        omit_root_git_metadata=not source_prefix,
    )
    checkout_matches = (
        first_root is not None
        and first_root == second_root
        and first_files == second_files
        and _tree_matches_expected(first_files, expected_tree)
    )
    return observed_revision, revision_matches, checkout_matches, checkout, expected_tree


def _read_stable_file(path: Path) -> bytes | None:
    """Read one ordinary file without accepting a link swap or changing bytes."""

    try:
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or verification_sandbox._is_indirection(path):
            return None
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
    except (OSError, verification_sandbox.SandboxError):
        return None
    try:
        opened = os.fstat(descriptor)
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            content = stream.read()
        after = os.fstat(descriptor)
    except OSError:
        return None
    finally:
        os.close(descriptor)
    try:
        final = path.lstat()
        indirect = verification_sandbox._is_indirection(path)
    except (OSError, verification_sandbox.SandboxError):
        return None
    def identity(info: os.stat_result) -> tuple[int, int, int, int, int]:
        return (
            info.st_dev,
            info.st_ino,
            info.st_mode,
            info.st_size,
            info.st_mtime_ns,
        )
    if indirect or identity(before) != identity(opened) or identity(opened) != identity(after):
        return None
    if identity(after) != identity(final) or len(content) != final.st_size:
        return None
    return content


def _ordinary_tree_files(
    root: Path,
    *,
    target: Path,
    omit_root_git_metadata: bool = False,
) -> tuple[dict[str, bytes] | None, Path | None]:
    """Snapshot an ordinary contained tree; no link, reparse point, or special file is accepted."""

    safe_root = _ordinary_contained_directory(root, container=target)
    if safe_root is None:
        return None, None
    files: dict[str, bytes] = {}

    def visit(directory: Path) -> bool:
        try:
            entries = sorted(directory.iterdir(), key=lambda item: item.name)
        except OSError:
            return False
        for entry in entries:
            try:
                indirect = verification_sandbox._is_indirection(entry)
                info = entry.lstat()
            except (OSError, verification_sandbox.SandboxError):
                return False
            if indirect:
                return False
            if entry.name == ".git":
                if directory != safe_root or not omit_root_git_metadata:
                    return False
                if not stat.S_ISDIR(info.st_mode):
                    return False
                continue
            relative = entry.relative_to(safe_root).as_posix()
            if stat.S_ISDIR(info.st_mode):
                if not visit(entry):
                    return False
                continue
            if not stat.S_ISREG(info.st_mode):
                return False
            content = _read_stable_file(entry)
            if content is None:
                return False
            files[relative] = content
        return True

    if not visit(safe_root):
        return None, safe_root
    return files, safe_root


def _installed_tree_provenance(
    source: Path,
    installed: Path | None,
    *,
    target: Path,
    omit_source_git_metadata: bool,
    expected_tree: ExpectedGitTree | None,
) -> dict[str, object]:
    details: dict[str, object] = {
        "installed_tree_matches": False,
        "source_tree_matches": False,
        "expected_file_count": None if expected_tree is None else len(expected_tree),
        "source_file_count": None,
        "installed_file_count": None,
        "installed_tree_path": None if installed is None else str(installed),
    }
    if installed is None:
        return details
    source_files, safe_source = _ordinary_tree_files(
        source,
        target=target,
        omit_root_git_metadata=omit_source_git_metadata,
    )
    installed_files, safe_installed = _ordinary_tree_files(installed, target=target)
    if source_files is not None:
        details["source_file_count"] = len(source_files)
    if installed_files is not None:
        details["installed_file_count"] = len(installed_files)
    if safe_source is None or safe_installed is None:
        return details
    if (
        safe_source == safe_installed
        or safe_source in safe_installed.parents
        or safe_installed in safe_source.parents
    ):
        return details
    details["installed_tree_path"] = str(safe_installed)
    source_matches = _tree_matches_expected(source_files, expected_tree)
    installed_matches = _tree_matches_expected(installed_files, expected_tree)
    details["source_tree_matches"] = source_matches
    details["installed_tree_matches"] = source_matches and installed_matches
    return details


def _absolute_install_path(value: object) -> Path | None:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        return None
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts:
        return None
    return path


def _source_worktree_clean(checks: Sequence[Check]) -> bool | None:
    for check in checks:
        if check.check_id != "repository.worktree-state" or check.status != "pass":
            continue
        value = check.details.get("clean")
        return value if isinstance(value, bool) else None
    return None


def _assert_probe_command(
    argv: Sequence[str], *, root: Path, marketplace_source: str | os.PathLike[str] | None = None
) -> None:
    """Reject command drift before subprocess execution can acquire install authority."""

    if not argv:
        raise ValueError("empty command")
    source = _normalize_marketplace_source(marketplace_source, root=root)
    name = _command_name(argv[0])
    tail = tuple(argv[1:])
    allowed = name in set(CLI_COMMANDS.values()) and tail == ("--version",)
    if name == "claude":
        allowed = allowed or tail in {
            ("plugin", "list", "--json"),
            ("plugin", "marketplace", "add", source),
            ("plugin", "marketplace", "list", "--json"),
            ("plugin", "marketplace", "remove", MARKETPLACE_NAME),
            ("plugin", "install", CLAUDE_PLUGIN_ID),
            ("plugin", "uninstall", CLAUDE_PLUGIN_ID),
        }
    if name == "codex":
        allowed = allowed or tail in {
            ("plugin", "marketplace", "add", source),
            ("plugin", "add", CODEX_PLUGIN_ID),
            ("plugin", "list", "--json"),
            ("plugin", "marketplace", "list", "--json"),
            ("plugin", "marketplace", "remove", MARKETPLACE_NAME),
            ("plugin", "remove", CODEX_PLUGIN_ID),
        }
    if name == "copilot":
        allowed = allowed or tail in {
            ("plugin", "list"),
            ("plugin", "marketplace", "add", str(root)),
            ("plugin", "install", COPILOT_PLUGIN_ID),
            ("plugin", "uninstall", COPILOT_PLUGIN_ID),
        }
    if not allowed:
        raise ValueError(
            "host install probe refused a command outside its scoped allowlist: " + repr(list(argv))
        )


def _run_probe(
    argv: Sequence[str],
    env: Mapping[str, str] | None,
    *,
    root: Path,
    marketplace_source: str | os.PathLike[str] | None = None,
) -> CommandResult:
    _assert_probe_command(argv, root=root, marketplace_source=marketplace_source)
    try:
        result = subprocess.run(
            list(argv),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=60,
            stdin=subprocess.DEVNULL,
            env=dict(env) if env is not None else None,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CommandResult(127, "", type(exc).__name__)
    return CommandResult(result.returncode, result.stdout, result.stderr)


def _vscode_user_settings(home: Path) -> Path:
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else home / "AppData" / "Roaming"
        return base / "Code" / "User" / "settings.json"
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "Code" / "User" / "settings.json"
    return home / ".config" / "Code" / "User" / "settings.json"


def _validate_target(target: Path, *, root: Path, home: Path) -> Path:
    """Resolve the disposable target and prove it cannot alias user- or repo-owned state.

    Unlike verification_sandbox's source mounts -- where a swapped ancestor silently changes
    digest-bound bytes, so every ancestor link must be rejected -- this target is created fresh
    by the probe and removed afterwards, so OS-resolved ancestor links (macOS /var -> /private/var)
    are safe. Only the final component must never be a link or reparse point itself.
    """

    expanded = Path(target).expanduser()
    if os.path.lexists(expanded) and verification_sandbox._is_indirection(expanded):
        raise ValueError(f"disposable target must not itself be a link or reparse point: {expanded}")
    target = Path(os.path.abspath(expanded)).resolve()
    user_locations = {
        (home / ".claude").resolve(),
        (home / ".codex").resolve(),
        (home / ".copilot").resolve(),
        Path(os.environ.get("CLAUDE_CONFIG_DIR", home / ".claude")).expanduser().resolve(),
        Path(os.environ.get("CODEX_HOME", home / ".codex")).expanduser().resolve(),
        _vscode_user_settings(home).parent.resolve(),
    }
    if target in user_locations or any(
        location in target.parents or target in location.parents for location in user_locations
    ):
        raise ValueError(f"disposable target must not live inside user-owned configuration: {target}")
    if target == home or home in target.parents or target in home.parents:
        raise ValueError(f"disposable target must not be or contain the user home: {target}")
    if target == root or root in target.parents or target in root.parents:
        raise ValueError(
            f"disposable target must not be, contain, or live inside the fleet repository: {target}"
        )
    if target == Path(target.anchor):
        raise ValueError(f"disposable target must not be a filesystem root: {target}")
    if target.exists():
        if not target.is_dir() or any(target.iterdir()):
            raise ValueError(f"disposable target must be absent or an empty directory: {target}")
    target.mkdir(parents=True, exist_ok=True)
    return target


def _census_entry(path: Path) -> tuple[str, int, int] | None:
    try:
        info = path.lstat()
    except OSError:
        return None
    try:
        if verification_sandbox._is_indirection(path):
            return None
    except verification_sandbox.SandboxError:
        return None
    if stat.S_ISDIR(info.st_mode):
        return ("dir", 0, 0)
    if stat.S_ISREG(info.st_mode):
        return ("file", info.st_size, info.st_mtime_ns)
    return None


def _stat_census(location: Path) -> dict[str, tuple[str, int, int]] | None:
    """Map a watched user location to path metadata; ``None`` means it could not be enumerated.

    Metadata only: sizes and mtimes detect writes without reading user-owned bytes. A missing
    location is an empty census, not an error. Indirection, special files, and traversal errors
    make the census indeterminate rather than silently narrowing it.
    """

    try:
        location.lstat()
    except FileNotFoundError:
        return {}
    except OSError:
        return None
    root_entry = _census_entry(location)
    if root_entry is None:
        return None
    if root_entry[0] == "file":
        return {".": root_entry}
    if root_entry[0] != "dir":
        return None

    census: dict[str, tuple[str, int, int]] = {".": root_entry}

    def raise_walk_error(error: OSError) -> None:
        raise error

    try:
        for current, dirnames, filenames in os.walk(
            location,
            followlinks=False,
            onerror=raise_walk_error,
        ):
            current_path = Path(current)
            for name in dirnames:
                child = current_path / name
                entry = _census_entry(child)
                if entry is None or entry[0] != "dir":
                    return None
                census[child.relative_to(location).as_posix()] = entry
            for name in filenames:
                child = current_path / name
                entry = _census_entry(child)
                if entry is None or entry[0] != "file":
                    return None
                census[child.relative_to(location).as_posix()] = entry
    except OSError:
        return None
    return census


def _census_change(before: dict | None, after: dict | None) -> int | None:
    if before is None or after is None:
        return None
    changed = {key for key in before.keys() | after.keys() if before.get(key) != after.get(key)}
    return len(changed)


def _child_env(disposable_home: Path, extra: Mapping[str, str]) -> dict[str, str]:
    """Minimal credential-free child environment; every writable pointer lands in the target."""

    environment = {
        key: os.environ[key]
        for key in ("PATH", "PATHEXT", "SYSTEMROOT", "WINDIR")
        if key in os.environ
    }
    home = disposable_home.resolve()
    home.mkdir(parents=True, exist_ok=True)
    temporary = home / "tmp"
    temporary.mkdir(exist_ok=True)
    # Unset APPDATA/LOCALAPPDATA leave Windows tooling resolving `${APPDATA}`-style defaults
    # relative to the cwd, which lands installs inside the repository.
    roaming = home / "AppData" / "Roaming"
    local = home / "AppData" / "Local"
    roaming.mkdir(parents=True, exist_ok=True)
    local.mkdir(parents=True, exist_ok=True)
    environment.update(
        {
            "HOME": str(home),
            "USERPROFILE": str(home),
            "APPDATA": str(roaming),
            "LOCALAPPDATA": str(local),
            "TEMP": str(temporary),
            "TMP": str(temporary),
            "TMPDIR": str(temporary),
        }
    )
    environment.update(extra)
    return environment


def _availability(host: str, which: Which, run: Runner) -> tuple[str | None, str]:
    executable = which(CLI_COMMANDS[host])
    if not executable:
        return None, "unavailable"
    version = run((executable, "--version"), None)
    if version.returncode:
        return executable, "unreadable"
    safe_version, _ = fleet_doctor._safe_version(version.stdout)
    return executable, safe_version


def _unavailable_checks(host: str) -> list[Check]:
    return [
        Check(
            f"host.{host}.probe-{criterion}",
            "skip",
            f"{host} CLI is not installed or not on PATH.",
            limitations=(
                "Availability was not treated as a passing runtime check.",
                MODEL_LIMITATION,
            ),
        )
        for criterion in CRITERIA
    ]


def _authority_check(host: str, watched: Sequence[tuple[str, dict | None, dict | None]]) -> Check:
    """Compare residual censuses of user locations; only counts and labels are reported."""

    changes = 0
    labels = []
    for label, before, after in watched:
        changed = _census_change(before, after)
        if changed is None:
            return Check(
                f"host.{host}.probe-authority",
                "inconclusive",
                f"The {label} user location could not be enumerated, so the write boundary is unproven.",
            )
        if changed:
            changes += changed
            labels.append(label)
    if changes:
        return Check(
            f"host.{host}.probe-authority",
            "fail",
            f"{changes} path(s) changed under user-owned location(s) during the disposable probe.",
            {"changed_user_path_count": changes, "changed_location_count": len(labels)},
        )
    return Check(
        f"host.{host}.probe-authority",
        "pass",
        "No residual metadata-visible change was observed in watched user locations.",
        limitations=(
            "Before/after metadata cannot prove that no transient or metadata-restored write occurred.",
        ),
    )


def _claude_plugin_inventory(
    stdout: str,
    *,
    expected_version: str,
) -> tuple[bool | None, bool | None, Path | None]:
    """Return (exact installed row, any exact-id residue, exact row installPath)."""

    try:
        payload = json.loads(stdout)
    except (TypeError, ValueError):
        return None, None, None
    if not isinstance(payload, list):
        return None, None, None
    exact_id_rows = [
        row for row in payload if isinstance(row, dict) and row.get("id") == CLAUDE_PLUGIN_ID
    ]
    exact_installed = [
        row
        for row in exact_id_rows
        if row.get("version") == expected_version and row.get("enabled") is True
    ]
    exact = len(exact_id_rows) == 1 and len(exact_installed) == 1
    install_path = (
        _absolute_install_path(exact_installed[0].get("installPath")) if exact else None
    )
    return exact, bool(exact_id_rows), install_path


def _claude_marketplace_residue(stdout: str) -> bool | None:
    try:
        payload = json.loads(stdout)
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, list):
        return None
    return any(isinstance(row, dict) and row.get("name") == MARKETPLACE_NAME for row in payload)


def _codex_marketplace_residue(stdout: str) -> bool | None:
    try:
        payload = json.loads(stdout)
    except (TypeError, ValueError):
        return None
    if not isinstance(payload, dict) or not isinstance(payload.get("marketplaces"), list):
        return None
    return any(
        isinstance(row, dict) and row.get("name") == MARKETPLACE_NAME
        for row in payload["marketplaces"]
    )


def _probe_claude(
    root: Path,
    target: Path,
    home: Path,
    run: Runner,
    *,
    executable: str,
    marketplace_source: str,
    expected_revision: str,
    git_run: GitRunner,
) -> list[Check]:
    checks: list[Check] = []
    config = target / "claude" / "config"
    env = _child_env(target / "claude" / "home", {"CLAUDE_CONFIG_DIR": str(config)})
    user_config = Path(
        os.environ.get("CLAUDE_CONFIG_DIR", home / ".claude")
    ).expanduser().absolute()
    watched_locations = (("Claude-config-root", user_config),)
    census_before = [_stat_census(location) for _, location in watched_locations]

    def authority() -> Check:
        watched = [
            (label, before, _stat_census(location))
            for (label, location), before in zip(watched_locations, census_before)
        ]
        return _authority_check("claude", watched)

    def cli(*tail: str) -> CommandResult:
        return run((executable, *tail), env)

    source_details = _marketplace_source_identity(marketplace_source, root=root)
    expected_version = _expected_marketplace_version(marketplace_source, root=root)
    source_details["expected_plugin_version"] = expected_version
    source_limitations = _marketplace_source_limitations(marketplace_source)
    release_source = RELEASE_MARKETPLACE_SOURCE_RE.fullmatch(marketplace_source) is not None
    if release_source:
        source_details.update(
            {
                "marketplace_checkout_clean": False,
                "marketplace_revision_matches": False,
                "tree_identity_contract": "ordinary-file-paths-and-git-blob-bytes",
                "installed_tree_matches": False,
                "source_tree_matches": False,
                "expected_file_count": None,
                "source_file_count": None,
                "installed_file_count": None,
                "installed_tree_path": None,
            }
        )
    add = cli("plugin", "marketplace", "add", marketplace_source)
    source_revision: str | None = expected_revision
    source_revision_matches = add.returncode == 0
    marketplace_checkout_clean: bool | None = None
    marketplace_checkout: Path | None = None
    expected_tree: ExpectedGitTree | None = None
    if add.returncode == 0 and release_source:
        (
            source_revision,
            source_revision_matches,
            marketplace_checkout_clean,
            marketplace_checkout,
            expected_tree,
        ) = _marketplace_checkout_provenance(
            config / "plugins" / "marketplaces" / MARKETPLACE_NAME,
            target=target,
            expected_revision=expected_revision,
            git_run=git_run,
            source_prefix="",
            required_manifest=".claude-plugin/plugin.json",
        )
    install = cli("plugin", "install", CLAUDE_PLUGIN_ID) if add.returncode == 0 else None
    source_details.update(
        {
            "marketplace_revision": source_revision,
            "marketplace_revision_matches": source_revision_matches,
        }
    )
    if release_source:
        source_details["marketplace_checkout_clean"] = marketplace_checkout_clean is True
    if install is None or install.returncode != 0:
        failed_command = (
            (executable, "plugin", "marketplace", "add", marketplace_source)
            if install is None
            else (executable, "plugin", "install", CLAUDE_PLUGIN_ID)
        )
        failed_rc = add.returncode if install is None else install.returncode
        checks.append(
            Check(
                "host.claude.probe-install",
                "inconclusive",
                "The Claude CLI could not complete the disposable plugin install verbs.",
                {
                    "marketplace_add_rc": add.returncode,
                    "install_rc": None if install is None else install.returncode,
                    **source_details,
                },
                failed_command,
                str(target),
                failed_rc,
                (CREDENTIAL_LIMITATION, *source_limitations),
            )
        )
        checks.extend(
            Check(
                f"host.claude.probe-{criterion}",
                "skip",
                "Install did not complete, so there is nothing to inventory or uninstall.",
                source_details,
                limitations=(MODEL_LIMITATION,),
            )
            for criterion in ("inventory", "uninstall")
        )
        checks.append(authority())
        return checks
    listing = cli("plugin", "list", "--json")
    found, _, installed_path = (
        _claude_plugin_inventory(listing.stdout, expected_version=expected_version)
        if listing.returncode == 0
        else (None, None, None)
    )
    if release_source:
        (
            source_revision,
            source_revision_matches,
            marketplace_checkout_clean,
            marketplace_checkout,
            expected_tree,
        ) = _marketplace_checkout_provenance(
            config / "plugins" / "marketplaces" / MARKETPLACE_NAME,
            target=target,
            expected_revision=expected_revision,
            git_run=git_run,
            source_prefix="",
            required_manifest=".claude-plugin/plugin.json",
        )
        source_details.update(
            {
                "marketplace_revision": source_revision,
                "marketplace_revision_matches": source_revision_matches,
                "marketplace_checkout_clean": marketplace_checkout_clean,
            }
        )
        source_details.update(
            _installed_tree_provenance(
                marketplace_checkout
                or config / "plugins" / "marketplaces" / MARKETPLACE_NAME,
                installed_path,
                target=target,
                omit_source_git_metadata=True,
                expected_tree=expected_tree,
            )
        )
    release_provenance_matches = (
        source_details.get("marketplace_revision_matches") is True
        and source_details.get("marketplace_checkout_clean") is True
        and source_details.get("installed_tree_matches") is True
    )
    install_status = (
        "pass"
        if source_revision_matches and (not release_source or release_provenance_matches)
        else "fail"
    )
    checks.append(
        Check(
            "host.claude.probe-install",
            install_status,
            (
                "Fleet plugin installed from the exact Git-object-bound release source into a disposable Claude configuration."
                if install_status == "pass" and release_source
                else "Fleet plugin installed from the local checkout into a disposable Claude configuration."
                if install_status == "pass"
                else "The Claude install did not match the exact clean marketplace source tree."
            ),
            {
                "marketplace_add_rc": add.returncode,
                "install_rc": install.returncode,
                **source_details,
            },
            (executable, "plugin", "install", CLAUDE_PLUGIN_ID),
            str(target),
            install.returncode,
            (CREDENTIAL_LIMITATION, *source_limitations),
        )
    )
    inventory_status = (
        "fail"
        if release_source and not release_provenance_matches
        else (
            "inconclusive"
            if found is None
            else ("pass" if found and source_revision_matches else "fail")
        )
    )
    checks.append(
        Check(
            "host.claude.probe-inventory",
            inventory_status,
            (
                "Disposable Claude inventory lists the exact enabled fleet plugin version."
                if inventory_status == "pass"
                else "Disposable Claude inventory could not confirm the exact enabled fleet plugin version."
            ),
            {"installed": found, **source_details},
            (executable, "plugin", "list", "--json"),
            str(target),
            listing.returncode,
            (MODEL_LIMITATION, *source_limitations),
        )
    )

    remove = cli("plugin", "uninstall", CLAUDE_PLUGIN_ID)
    after = cli("plugin", "list", "--json")
    marketplace_remove = cli("plugin", "marketplace", "remove", MARKETPLACE_NAME)
    marketplaces_after = cli("plugin", "marketplace", "list", "--json")
    _, plugin_residue, _ = (
        _claude_plugin_inventory(after.stdout, expected_version=expected_version)
        if after.returncode == 0
        else (None, None, None)
    )
    marketplace_residue = (
        _claude_marketplace_residue(marketplaces_after.stdout)
        if marketplaces_after.returncode == 0
        else None
    )
    if plugin_residue is True or marketplace_residue is True:
        uninstall_status = "fail"
    elif (
        remove.returncode
        or after.returncode
        or marketplace_remove.returncode
        or marketplaces_after.returncode
        or plugin_residue is None
        or marketplace_residue is None
    ):
        uninstall_status = "inconclusive"
    else:
        uninstall_status = "pass"
    checks.append(
        Check(
            "host.claude.probe-uninstall",
            uninstall_status,
            (
                "Fleet plugin and marketplace are absent after disposable rollback."
                if uninstall_status == "pass"
                else "Disposable Claude rollback could not prove both plugin and marketplace removal."
            ),
            {
                "uninstall_rc": remove.returncode,
                "post_uninstall_list_rc": after.returncode,
                "marketplace_remove_rc": marketplace_remove.returncode,
                "post_remove_marketplace_list_rc": marketplaces_after.returncode,
                "plugin_residue": plugin_residue,
                "marketplace_residue": marketplace_residue,
                **source_details,
            },
            (executable, "plugin", "uninstall", CLAUDE_PLUGIN_ID),
            str(target),
            remove.returncode,
        )
    )
    checks.append(authority())
    return checks


def _codex_plugin_inventory(
    stdout: str,
    *,
    expected_version: str,
) -> tuple[bool | None, bool | None]:
    """Return (installed-and-enabled, any exact-id residue); ``None`` means invalid JSON."""

    try:
        payload = json.loads(stdout)
    except (TypeError, ValueError):
        return None, None
    if not isinstance(payload, dict) or not isinstance(payload.get("installed"), list):
        return None, None
    rows = payload["installed"]
    exact_id_rows = [
        row for row in rows if isinstance(row, dict) and row.get("pluginId") == CODEX_PLUGIN_ID
    ]
    exact_installed = [
        row
        for row in exact_id_rows
        if row.get("name") == "save-toolkit"
        and row.get("marketplaceName") == "latent-sre"
        and row.get("version") == expected_version
        and row.get("installed") is True
        and row.get("enabled") is True
    ]
    return len(exact_id_rows) == 1 and len(exact_installed) == 1, bool(exact_id_rows)


def _probe_codex(
    root: Path,
    target: Path,
    home: Path,
    run: Runner,
    *,
    executable: str,
    marketplace_source: str,
    expected_revision: str,
    git_run: GitRunner,
) -> list[Check]:
    checks: list[Check] = []
    codex_home = target / "codex" / "home"
    agents = codex_home / "agents"
    env = _child_env(codex_home, {"CODEX_HOME": str(codex_home.resolve())})
    user_codex_home = Path(os.environ.get("CODEX_HOME", home / ".codex")).expanduser().resolve()
    watched_locations = (
        ("Codex-agents", user_codex_home / "agents"),
        ("Codex-plugins", user_codex_home / "plugins"),
        ("Codex-marketplaces", user_codex_home / ".tmp" / "marketplaces"),
        ("Codex-config", user_codex_home / "config.toml"),
    )
    census_before = [_stat_census(location) for _, location in watched_locations]
    source_details = _marketplace_source_identity(marketplace_source, root=root)
    expected_version = _expected_marketplace_version(marketplace_source, root=root)
    source_details["expected_plugin_version"] = expected_version
    source_limitations = _marketplace_source_limitations(marketplace_source)
    release_source = RELEASE_MARKETPLACE_SOURCE_RE.fullmatch(marketplace_source) is not None
    if release_source:
        source_details.update(
            {
                "marketplace_checkout_clean": False,
                "marketplace_revision_matches": False,
                "tree_identity_contract": "ordinary-file-paths-and-git-blob-bytes",
                "installed_tree_matches": False,
                "source_tree_matches": False,
                "expected_file_count": None,
                "source_file_count": None,
                "installed_file_count": None,
                "installed_tree_path": None,
            }
        )

    def authority() -> Check:
        watched = [
            (label, before, _stat_census(location))
            for (label, location), before in zip(watched_locations, census_before)
        ]
        return _authority_check("codex", watched)

    def cli(*tail: str) -> CommandResult:
        return run((executable, *tail), env)

    adapter_failures = generate_platform_adapters.validate_generated_outputs(root)
    if adapter_failures:
        checks.append(
            Check(
                "host.codex.probe-install",
                "inconclusive",
                f"Generated adapters have {len(adapter_failures)} issue(s); known-good bytes cannot be installed.",
                source_details,
                limitations=(
                    "Issue text is omitted; rerun generate_platform_adapters.py locally.",
                    *source_limitations,
                ),
            )
        )
        checks.extend(
            Check(
                f"host.codex.probe-{criterion}",
                "skip",
                "Install did not complete, so there is nothing to inventory or uninstall.",
                source_details,
                limitations=(MODEL_LIMITATION, *source_limitations),
            )
            for criterion in ("inventory", "uninstall")
        )
        checks.append(authority())
        return checks

    sources = sorted((root / ".codex" / "agents").glob("*.toml"))
    plan = install_codex_agents.build_sync_plan(root / ".codex" / "agents", agents)
    for planned in (*plan.writes, *plan.removals, *plan.conflicts):
        path = planned if isinstance(planned, Path) else planned.path
        if target not in path.resolve().parents:
            raise ValueError(f"probe planned a write outside the disposable target: {path}")
    install_codex_agents.apply_sync_plan(plan)
    agent_install_complete = (
        bool(sources) and not plan.conflicts and len(plan.writes) == len(sources)
    )

    marketplace_add = cli("plugin", "marketplace", "add", marketplace_source)
    source_revision: str | None = expected_revision
    source_revision_matches = marketplace_add.returncode == 0
    marketplace_checkout_clean: bool | None = None
    marketplace_checkout: Path | None = None
    expected_tree: ExpectedGitTree | None = None
    if marketplace_add.returncode == 0 and release_source:
        (
            source_revision,
            source_revision_matches,
            marketplace_checkout_clean,
            marketplace_checkout,
            expected_tree,
        ) = _marketplace_checkout_provenance(
            codex_home / ".tmp" / "marketplaces" / MARKETPLACE_NAME,
            target=target,
            expected_revision=expected_revision,
            git_run=git_run,
            source_prefix="plugins/save-toolkit",
            required_manifest=".codex-plugin/plugin.json",
        )
    source_details.update(
        {
            "marketplace_revision": source_revision,
            "marketplace_revision_matches": source_revision_matches,
        }
    )
    if release_source:
        source_details["marketplace_checkout_clean"] = marketplace_checkout_clean is True
    plugin_add = (
        cli("plugin", "add", CODEX_PLUGIN_ID) if marketplace_add.returncode == 0 else None
    )
    plugin_install_complete = plugin_add is not None and plugin_add.returncode == 0
    if release_source:
        (
            source_revision,
            source_revision_matches,
            marketplace_checkout_clean,
            marketplace_checkout,
            expected_tree,
        ) = _marketplace_checkout_provenance(
            codex_home / ".tmp" / "marketplaces" / MARKETPLACE_NAME,
            target=target,
            expected_revision=expected_revision,
            git_run=git_run,
            source_prefix="plugins/save-toolkit",
            required_manifest=".codex-plugin/plugin.json",
        )
        source_details.update(
            {
                "marketplace_revision": source_revision,
                "marketplace_revision_matches": source_revision_matches,
                "marketplace_checkout_clean": marketplace_checkout_clean,
            }
        )
        installed_cache = (
            codex_home
            / "plugins"
            / "cache"
            / "latent-sre"
            / "save-toolkit"
            / expected_version
        )
        source_details.update(
            _installed_tree_provenance(
                (marketplace_checkout or codex_home / ".tmp" / "marketplaces" / MARKETPLACE_NAME)
                / "plugins"
                / "save-toolkit",
                installed_cache,
                target=target,
                omit_source_git_metadata=False,
                expected_tree=expected_tree,
            )
        )
    release_checkout_matches = (
        source_details.get("marketplace_revision_matches") is True
        and source_details.get("marketplace_checkout_clean") is True
    )
    release_tree_matches = source_details.get("installed_tree_matches") is True
    if (
        not agent_install_complete
        or not source_revision_matches
        or (release_source and not release_checkout_matches)
    ):
        install_status = "fail"
    elif not plugin_install_complete:
        install_status = "inconclusive"
    elif release_source and not release_tree_matches:
        install_status = "fail"
    else:
        install_status = "pass"
    checks.append(
        Check(
            "host.codex.probe-install",
            install_status,
            (
                "Codex skills plugin and generated custom agents installed into a disposable CODEX_HOME."
                if install_status == "pass"
                else "The disposable install could not prove both the Codex skills plugin and generated custom agents."
            ),
            {
                "marketplace_add_rc": marketplace_add.returncode,
                "plugin_add_rc": None if plugin_add is None else plugin_add.returncode,
                "agent_written_count": len(plan.writes),
                "agent_expected_count": len(sources),
                "agent_conflict_count": len(plan.conflicts),
                **source_details,
            },
            (
                (executable, "plugin", "add", CODEX_PLUGIN_ID)
                if marketplace_add.returncode == 0
                else (executable, "plugin", "marketplace", "add", marketplace_source)
            ),
            str(target),
            marketplace_add.returncode if plugin_add is None else plugin_add.returncode,
            (
                "Standalone-agent installation used the fleet's conflict-safe installer in-process.",
                CREDENTIAL_LIMITATION,
                *source_limitations,
            ),
        )
    )

    mismatches = sum(
        1
        for source in sources
        if not (agents / source.name).is_file()
        or (agents / source.name).read_bytes()
        != install_codex_agents._installed_bytes(source.read_bytes())
    )
    listing = cli("plugin", "list", "--json") if plugin_install_complete else None
    plugin_installed, _ = (
        _codex_plugin_inventory(listing.stdout, expected_version=expected_version)
        if listing is not None and listing.returncode == 0
        else (None, None)
    )
    if (
        mismatches
        or not source_revision_matches
        or (release_source and not release_checkout_matches)
        or (
            listing is not None
            and listing.returncode == 0
            and plugin_installed is not True
        )
    ):
        inventory_status = "fail"
    elif not plugin_install_complete:
        inventory_status = "skip"
    elif release_source and not release_tree_matches:
        inventory_status = "fail"
    elif listing is None or listing.returncode != 0:
        inventory_status = "inconclusive"
    else:
        inventory_status = "pass"
    checks.append(
        Check(
            "host.codex.probe-inventory",
            inventory_status,
            (
                f"Disposable inventory holds the enabled Codex skills plugin and {len(sources)} marker-managed fleet role(s)."
                if inventory_status == "pass"
                else "Disposable Codex inventory could not prove both the skills plugin and standalone agents."
            ),
            {
                "role_count": len(sources),
                "mismatch_count": mismatches,
                "plugin_installed": plugin_installed,
                "plugin_list_rc": None if listing is None else listing.returncode,
                **source_details,
            },
            None if listing is None else (executable, "plugin", "list", "--json"),
            None if listing is None else str(target),
            None if listing is None else listing.returncode,
            (
                "Custom-agent inventory is file-level; headless Codex agent discovery is a measured platform limitation.",
                MODEL_LIMITATION,
                *source_limitations,
            ),
        )
    )

    plugin_remove = cli("plugin", "remove", CODEX_PLUGIN_ID) if plugin_install_complete else None
    after = (
        cli("plugin", "list", "--json")
        if plugin_remove is not None and plugin_remove.returncode == 0
        else None
    )
    _, plugin_residue = (
        _codex_plugin_inventory(after.stdout, expected_version=expected_version)
        if after is not None and after.returncode == 0
        else (None, None)
    )
    uninstall = install_codex_agents.build_uninstall_plan(agents)
    install_codex_agents.apply_sync_plan(uninstall)
    remaining = [
        item.name
        for item in agents.glob("*.toml")
        if item.is_file() and install_codex_agents._is_managed(item.read_bytes())
    ]
    marketplace_remove = (
        cli("plugin", "marketplace", "remove", MARKETPLACE_NAME)
        if marketplace_add.returncode == 0
        else None
    )
    marketplaces_after = (
        cli("plugin", "marketplace", "list", "--json")
        if marketplace_remove is not None and marketplace_remove.returncode == 0
        else None
    )
    marketplace_residue = (
        _codex_marketplace_residue(marketplaces_after.stdout)
        if marketplaces_after is not None and marketplaces_after.returncode == 0
        else None
    )
    if remaining or (after is not None and after.returncode == 0 and plugin_residue is not False) or marketplace_residue is True:
        uninstall_status = "fail"
    elif not plugin_install_complete:
        uninstall_status = "skip"
    elif plugin_remove is None or plugin_remove.returncode != 0:
        uninstall_status = "inconclusive"
    elif after is None or after.returncode != 0:
        uninstall_status = "inconclusive"
    elif marketplace_remove is None or marketplace_remove.returncode != 0:
        uninstall_status = "inconclusive"
    elif marketplaces_after is None or marketplaces_after.returncode != 0 or marketplace_residue is None:
        uninstall_status = "inconclusive"
    else:
        uninstall_status = "pass"
    checks.append(
        Check(
            "host.codex.probe-uninstall",
            uninstall_status,
            (
                "Codex skills plugin, marketplace, and all marker-managed role files are absent after rollback."
                if uninstall_status == "pass"
                else "Disposable Codex uninstall could not prove both plugin and standalone-agent cleanup."
            ),
            {
                "plugin_remove_rc": None if plugin_remove is None else plugin_remove.returncode,
                "post_remove_list_rc": None if after is None else after.returncode,
                "plugin_residue": plugin_residue,
                "marketplace_remove_rc": None if marketplace_remove is None else marketplace_remove.returncode,
                "post_remove_marketplace_list_rc": None if marketplaces_after is None else marketplaces_after.returncode,
                "marketplace_residue": marketplace_residue,
                "agent_removed_count": len(uninstall.removals),
                "agent_residue_count": len(remaining),
                **source_details,
            },
            None if plugin_remove is None else (executable, "plugin", "remove", CODEX_PLUGIN_ID),
            None if plugin_remove is None else str(target),
            None if plugin_remove is None else plugin_remove.returncode,
            (
                "Standalone-agent uninstall removes only marker-managed files.",
                *source_limitations,
            ),
        )
    )
    checks.append(authority())
    return checks


def _link_free_tree(root: Path) -> bool:
    for current, dirnames, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        for name in (*dirnames, *filenames):
            if verification_sandbox._is_indirection(current_path / name):
                return False
    return True


def _copy_generated_tree(source: Path, destination: Path) -> int:
    copied = 0
    for current, _, filenames in os.walk(source, followlinks=False):
        current_path = Path(current)
        for name in filenames:
            origin = current_path / name
            placed = destination / origin.relative_to(source)
            placed.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(origin, placed)
            copied += 1
    return copied


def _probe_vscode(root: Path, target: Path, home: Path) -> list[Check]:
    checks: list[Check] = []
    workspace = target / "vscode" / "workspace"
    watched = _vscode_user_settings(home)
    census_before = _stat_census(watched)

    adapter_failures = generate_platform_adapters.validate_generated_outputs(root)
    agent_source = root / ".github" / "agents"
    skill_source = root / "platforms" / "copilot" / "skills"
    if adapter_failures or not agent_source.is_dir() or not skill_source.is_dir():
        checks.append(
            Check(
                "host.vscode.probe-install",
                "inconclusive",
                "Generated VS Code projections are incomplete; known-good bytes cannot be installed.",
                limitations=("Issue text is omitted; rerun generate_platform_adapters.py locally.",),
            )
        )
        checks.extend(
            Check(
                f"host.vscode.probe-{criterion}",
                "skip",
                "Install did not complete, so there is nothing to inventory or uninstall.",
                limitations=(MODEL_LIMITATION,),
            )
            for criterion in ("inventory", "uninstall")
        )
        checks.append(
            _authority_check("vscode", [("VS-Code-user-settings", census_before, _stat_census(watched))])
        )
        return checks

    if not (_link_free_tree(agent_source) and _link_free_tree(skill_source)):
        raise ValueError("generated VS Code projection contains links or reparse points; refusing to copy")

    agents_dest = workspace / ".github" / "agents"
    skills_dest = workspace / "platforms" / "copilot" / "skills"
    settings_dest = workspace / ".vscode" / "settings.json"
    written_agents = _copy_generated_tree(agent_source, agents_dest)
    written_skills = _copy_generated_tree(skill_source, skills_dest)
    settings_dest.parent.mkdir(parents=True, exist_ok=True)
    settings_dest.write_text(
        json.dumps({"chat.agentSkillsLocations": {"platforms/copilot/skills": True}}, indent=2) + "\n",
        encoding="utf-8",
    )
    checks.append(
        Check(
            "host.vscode.probe-install",
            "pass",
            "Generated agents, skills, and skills-location setting placed into a disposable workspace.",
            {"agent_file_count": written_agents, "skill_file_count": written_skills},
            limitations=("VS Code install is workspace file placement; discovery is a folder scan.",),
        )
    )

    mismatches = 0
    for source_root, destination_root in ((agent_source, agents_dest), (skill_source, skills_dest)):
        for origin in sorted(source_root.rglob("*")):
            if not origin.is_file():
                continue
            placed = destination_root / origin.relative_to(source_root)
            if not placed.is_file() or placed.read_bytes() != origin.read_bytes():
                mismatches += 1
    try:
        settings = json.loads(settings_dest.read_text(encoding="utf-8"))
        locations = settings.get("chat.agentSkillsLocations")
        skills_registered = isinstance(locations, dict) and locations.get("platforms/copilot/skills") is True
    except (OSError, ValueError):
        skills_registered = False
    checks.append(
        Check(
            "host.vscode.probe-inventory",
            "pass" if not mismatches and skills_registered else "fail",
            (
                "Disposable workspace inventory matches the generated projections byte for byte."
                if not mismatches and skills_registered
                else "Disposable workspace inventory diverges from the generated projections."
            ),
            {"mismatch_count": mismatches, "skills_location_registered": skills_registered},
            limitations=(
                "File-level inventory only; VS Code runtime discovery is UI-bound and was not exercised.",
                MODEL_LIMITATION,
            ),
        )
    )

    for source_root, destination_root in ((agent_source, agents_dest), (skill_source, skills_dest)):
        for origin in sorted(source_root.rglob("*")):
            if origin.is_file():
                (destination_root / origin.relative_to(source_root)).unlink(missing_ok=True)
    settings_dest.unlink(missing_ok=True)
    residue = 0
    for current, dirnames, filenames in os.walk(workspace, followlinks=False):
        residue += len(filenames)
        residue += sum(
            1
            for name in dirnames
            if verification_sandbox._is_indirection(Path(current) / name)
        )
    checks.append(
        Check(
            "host.vscode.probe-uninstall",
            "fail" if residue else "pass",
            (
                f"{residue} unexpected file(s) remain in the disposable workspace after uninstall."
                if residue
                else "Exactly the placed files were removed; the disposable workspace holds no residue."
            ),
            {"residue_count": residue},
            limitations=(
                "Uninstall removes exactly the paths the probe placed; foreign content is reported "
                "as residue, never deleted.",
            ),
        )
    )
    checks.append(
        _authority_check("vscode", [("VS-Code-user-settings", census_before, _stat_census(watched))])
    )
    return checks


def _probe_copilot(root: Path, target: Path, home: Path, run: Runner, *, executable: str) -> list[Check]:
    checks: list[Check] = []
    env = _child_env(target / "copilot" / "home", {})
    watched_locations = (home / ".copilot", home / ".cache" / "copilot")
    census_before = [_stat_census(location) for location in watched_locations]

    def authority() -> Check:
        watched = [
            (label, before, _stat_census(location))
            for label, before, location in zip(
                ("Copilot-config", "Copilot-cache"), census_before, watched_locations
            )
        ]
        return _authority_check("copilot", watched)

    def cli(*tail: str) -> CommandResult:
        return run((executable, *tail), env)

    add = cli("plugin", "marketplace", "add", str(root))
    install = cli("plugin", "install", COPILOT_PLUGIN_ID) if add.returncode == 0 else None
    if install is None or install.returncode != 0:
        checks.append(
            Check(
                "host.copilot.probe-install",
                "inconclusive",
                "The Copilot CLI could not complete the disposable plugin install verbs.",
                {
                    "marketplace_add_rc": add.returncode,
                    "install_rc": None if install is None else install.returncode,
                },
                (executable, "plugin", "marketplace", "add", str(root)),
                str(target),
                add.returncode,
                (CREDENTIAL_LIMITATION,),
            )
        )
        checks.extend(
            Check(
                f"host.copilot.probe-{criterion}",
                "skip",
                "Install did not complete, so there is nothing to inventory or uninstall.",
                limitations=(MODEL_LIMITATION,),
            )
            for criterion in ("inventory", "uninstall")
        )
        checks.append(authority())
        return checks
    checks.append(
        Check(
            "host.copilot.probe-install",
            "pass",
            "Fleet plugin installed into a disposable Copilot home.",
            {"marketplace_add_rc": add.returncode, "install_rc": install.returncode},
            (executable, "plugin", "install", COPILOT_PLUGIN_ID),
            str(target),
            install.returncode,
            (CREDENTIAL_LIMITATION,),
        )
    )

    listing = cli("plugin", "list")
    found = (
        fleet_doctor._inventory_contains_plugin("copilot", listing.stdout, "save-toolkit")
        if listing.returncode == 0
        else None
    )
    checks.append(
        Check(
            "host.copilot.probe-inventory",
            "inconclusive" if found is None else ("pass" if found else "fail"),
            (
                "Disposable Copilot inventory lists the fleet plugin."
                if found
                else "Disposable Copilot inventory could not confirm the fleet plugin."
            ),
            {"installed": found},
            (executable, "plugin", "list"),
            str(target),
            listing.returncode,
            (MODEL_LIMITATION,),
        )
    )

    remove = cli("plugin", "uninstall", COPILOT_PLUGIN_ID)
    if remove.returncode:
        checks.append(
            Check(
                "host.copilot.probe-uninstall",
                "inconclusive",
                "The Copilot CLI could not complete the disposable plugin uninstall verb.",
                {"uninstall_rc": remove.returncode},
                (executable, "plugin", "uninstall", COPILOT_PLUGIN_ID),
                str(target),
                remove.returncode,
            )
        )
    else:
        after = cli("plugin", "list")
        residue = after.returncode == 0 and fleet_doctor._inventory_contains_plugin(
            "copilot", after.stdout, "save-toolkit"
        )
        checks.append(
            Check(
                "host.copilot.probe-uninstall",
                "fail" if residue else "pass",
                (
                    "Fleet plugin remains in the disposable inventory after uninstall."
                    if residue
                    else "Fleet plugin is absent from the disposable inventory after uninstall."
                ),
                {"residue": residue},
                (executable, "plugin", "uninstall", COPILOT_PLUGIN_ID),
                str(target),
                remove.returncode,
            )
        )
    checks.append(authority())
    return checks


def _to_envelope(
    check: Check,
    *,
    host: str,
    cli_version: str,
    root: Path,
    revision: str,
    run_id: str,
    started_at: datetime,
    ended_at: datetime,
    marketplace_identity: Mapping[str, str],
    source_worktree_clean: bool | None,
) -> dict[str, object]:
    remote_source = (
        host in {"claude", "codex"}
        and marketplace_identity["marketplace_source_kind"] == "pinned-version-tag"
    )
    return evidence_envelope.new_envelope(
        producer="host_install_probe",
        role="disposable-host-proof",
        target_root=str(root),
        target_revision=revision,
        criterion=check.check_id,
        status=check.status,
        started_at=started_at,
        ended_at=ended_at,
        command_argv=check.command_argv,
        command_cwd=check.command_cwd,
        exit_code=check.exit_code,
        source={"summary": check.summary, "details": check.details},
        run_id=run_id,
        task_id=check.check_id,
        attempt_id="attempt-1",
        environment={
            "probe": "disposable-host-install",
            "host": host,
            "host_cli": cli_version,
            "source_worktree_clean": source_worktree_clean,
            **(marketplace_identity if host in {"claude", "codex"} else {}),
        },
        isolation={
            "writes": "disposable-target-only",
            "auth_material": "not-provisioned",
            "model_sessions": "none",
            "network": "required-for-pinned-release-source" if remote_source else "not-required",
        },
        limitations=check.limitations,
    )


def collect_report(
    root: Path = REPO_ROOT,
    *,
    target: Path,
    hosts: Sequence[str] = HOSTS,
    home: Path | None = None,
    run: Runner | None = None,
    git_run: GitRunner = _run_host_git,
    which: Which = shutil.which,
    now: datetime | None = None,
    marketplace_source: str | os.PathLike[str] | None = None,
    allow_vscode_file_probe_without_cli: bool = False,
    require_clean: bool = False,
) -> dict[str, object]:
    root = root.resolve()
    home = (home or Path.home()).resolve()
    marketplace_source = _normalize_marketplace_source(marketplace_source, root=root)
    marketplace_identity = _marketplace_source_identity(marketplace_source, root=root)
    unknown = [host for host in hosts if host not in HOSTS]
    if unknown or not hosts:
        raise ValueError(f"unknown or empty host selection: {sorted(unknown) or 'none selected'}")
    started = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    run_id = "probe-" + started.strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    revision, git_checks = fleet_doctor._git_checks(root, git_run)
    if revision == "unknown":
        detail = git_checks[0].summary if git_checks else "no revision evidence"
        raise ValueError(f"cannot prove a disposable install against an unknown revision: {detail}")
    source_worktree_clean = _source_worktree_clean(git_checks)
    if require_clean and source_worktree_clean is not True:
        raise ValueError("strict host evidence requires a clean, inspectable source worktree")
    target = _validate_target(target, root=root, home=home)
    if run is None:
        run = lambda argv, env: _run_probe(  # noqa: E731
            argv, env, root=root, marketplace_source=marketplace_source
        )

    checks_by_host: dict[str, tuple[str, list[Check]]] = {}
    for host in hosts:
        executable, version = _availability(host, which, run)
        if executable is None:
            if host == "vscode" and allow_vscode_file_probe_without_cli:
                checks_by_host[host] = (
                    "unavailable:file-level-opt-in",
                    _probe_vscode(root, target, home),
                )
            else:
                checks_by_host[host] = (version, _unavailable_checks(host))
        elif host == "claude":
            checks_by_host[host] = (
                version,
                _probe_claude(
                    root,
                    target,
                    home,
                    run,
                    executable=executable,
                    marketplace_source=marketplace_source,
                    expected_revision=revision,
                    git_run=git_run,
                ),
            )
        elif host == "codex":
            checks_by_host[host] = (
                version,
                _probe_codex(
                    root,
                    target,
                    home,
                    run,
                    executable=executable,
                    marketplace_source=marketplace_source,
                    expected_revision=revision,
                    git_run=git_run,
                ),
            )
        elif host == "vscode":
            checks_by_host[host] = (version, _probe_vscode(root, target, home))
        else:
            checks_by_host[host] = (
                version,
                _probe_copilot(root, target, home, run, executable=executable),
            )

    ended = started if now is not None else datetime.now(timezone.utc)
    envelopes = [
        _to_envelope(
            check,
            host=host,
            cli_version=version,
            root=root,
            revision=revision,
            run_id=run_id,
            started_at=started,
            ended_at=ended,
            marketplace_identity=marketplace_identity,
            source_worktree_clean=source_worktree_clean,
        )
        for host, (version, checks) in checks_by_host.items()
        for check in checks
    ]
    counts = Counter(item["status"] for item in envelopes)
    report: dict[str, object] = {
        "schema_version": 1,
        "run_id": run_id,
        "generated_at": evidence_envelope.format_timestamp(ended),
        "root": str(root),
        "revision": revision,
        "summary": {status: counts.get(status, 0) for status in fleet_doctor.STATUSES},
        "evidence": envelopes,
    }
    fleet_doctor.validate_report(report)
    return report


def render_human(report: Mapping[str, object]) -> str:
    return "Host install probe" + fleet_doctor.render_human(report)[len("Fleet doctor"):]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="fleet repository root")
    parser.add_argument(
        "--target",
        type=Path,
        required=True,
        help=(
            "explicit disposable target: absent or empty, outside user-owned configuration and the "
            "repository; removed afterwards unless --keep"
        ),
    )
    parser.add_argument(
        "--hosts",
        type=lambda value: tuple(item.strip() for item in value.split(",") if item.strip()),
        default=HOSTS,
        help="comma-separated subset of: " + ", ".join(HOSTS),
    )
    parser.add_argument("--json", action="store_true", help="emit the versioned JSON report")
    parser.add_argument(
        "--marketplace-source",
        help=(
            "marketplace source for Claude and Codex: defaults to the exact checkout root; "
            f"release probes accept only {RELEASE_MARKETPLACE_PREFIX}<semver>"
        ),
    )
    parser.add_argument(
        "--allow-vscode-file-probe-without-cli",
        action="store_true",
        help=(
            "run the accepted VS Code workspace file placement/inventory/uninstall proof when "
            "the code CLI is absent; runtime discovery remains explicitly unproven"
        ),
    )
    parser.add_argument(
        "--require-pass",
        action="store_true",
        help="return nonzero unless every selected host criterion passes",
    )
    parser.add_argument(
        "--keep",
        action="store_true",
        help="keep the disposable target for inspection instead of removing it",
    )
    return parser


def _exit_code(
    report: Mapping[str, object], *, require_pass: bool, expected_passes: int | None = None
) -> int:
    summary = report["summary"]
    if not isinstance(summary, Mapping):
        raise ValueError("host install probe report summary is invalid")
    if require_pass:
        no_blocking_status = all(
            summary.get(status) == 0 for status in ("fail", "skip", "inconclusive")
        )
        complete = expected_passes is None or summary.get("pass") == expected_passes
        evidence = report.get("evidence")
        clean = (
            isinstance(evidence, list)
            and bool(evidence)
            and all(
                isinstance(item, Mapping)
                and isinstance(item.get("environment"), Mapping)
                and item["environment"].get("source_worktree_clean") is True
                for item in evidence
            )
        )
        return 0 if no_blocking_status and complete and clean else 1
    return 1 if summary.get("fail") else 0


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    target = args.target.expanduser()
    try:
        report = collect_report(
            args.root,
            target=target,
            hosts=args.hosts,
            marketplace_source=args.marketplace_source,
            allow_vscode_file_probe_without_cli=args.allow_vscode_file_probe_without_cli,
            require_clean=args.require_pass,
        )
    except (OSError, ValueError, evidence_envelope.EnvelopeValidationError) as exc:
        print(f"host install probe could not produce a report: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_human(report))
    resolved = Path(os.path.abspath(target))
    if resolved.exists():
        if args.keep:
            print(f"Disposable target kept for inspection: {resolved}", file=sys.stderr)
        else:
            shutil.rmtree(resolved)
            print(f"Disposable target removed: {resolved}", file=sys.stderr)
    return _exit_code(
        report,
        require_pass=args.require_pass,
        expected_passes=len(args.hosts) * len(CRITERIA),
    )


if __name__ == "__main__":
    raise SystemExit(main())
