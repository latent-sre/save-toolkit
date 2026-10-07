"""The disposable fixture repository a trial works in, the environment it sees, and what changed.

The workspace sits outside the repository under a neutral root, with an empty home for the child, so
no operator dotfile or `cf` session is reachable through the home lookup. It is not a sandbox: the
agent's shell still runs on the host.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import stat
import subprocess
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .backing import Service

DEFAULT_GITIGNORE = "__pycache__/\n*.pyc\n.pytest_cache/\n"


GIT_IDENTITY = ("-c", "user.name=fixture", "-c", "user.email=fixture@example.invalid")


@dataclass
class Workspace:
    root: Path
    repo: Path
    bin_dir: Path
    state_dir: Path
    baseline_commits: int
    baseline_branch: str
    baseline_sha: str = ""
    # The repository path the trial's commands name. Only a regrade sets it: its checkout is gone, so
    # `repo` is a placeholder there, but a `cd "<repo>" && <suite>` receipt still names the real path.
    command_repo: Path | None = None


def _git(
    repo: Path, *args: str, check: bool = True, env: Mapping[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *GIT_IDENTITY, *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=check,
        env=env,
    )


def _write_files(base: Path, files: dict[str, str]) -> None:
    for name, content in files.items():
        target = base / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="\n")


def agent_path(path: Path) -> str:
    """A path as the agent's shell sees it: POSIX, drive-letter style on Windows (`/c/Users/…`)."""
    p = path.resolve()
    if os.name == "nt" and p.drive:
        return "/" + p.drive[0].lower() + p.as_posix()[len(p.drive) :]
    return p.as_posix()


def declared_env(spec: Mapping[str, Any]) -> dict[str, Any]:
    """The env vars this scenario's fixture points at harness paths.

    Routing and contract scenarios carry no `fixture` at all -- the runner seeds them a synthetic
    one to get an empty git root -- so every fixture read on the trial path goes through here.
    """
    return (spec.get("fixture") or {}).get("env") or {}


def seed_workspace(spec: Mapping[str, Any], root: Path) -> Workspace:
    """Materialise the fixture under *root* (which must be outside the repository)."""
    repo, bin_dir, state_dir = root / "repo", root / "bin", root / "state"
    for d in (repo, bin_dir, state_dir, root / "home", root / "tmp"):
        d.mkdir(parents=True, exist_ok=True)
    fixture = spec.get("fixture") or {"files": {}}  # a routing/contract trial gets an empty repo
    files = dict(fixture.get("files") or {})
    files.setdefault(".gitignore", DEFAULT_GITIGNORE)
    _write_files(repo, files)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "core.autocrlf", "false")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "fixture baseline")
    for branch, body in (fixture.get("branches") or {}).items():
        _git(repo, "checkout", "-q", "-b", branch)
        _write_files(repo, body["files"])
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", body.get("message", f"{branch} changes"))
        _git(repo, "checkout", "-q", "main")
    for name, script in (fixture.get("fake_bin") or {}).items():
        target = bin_dir / name
        # Bake the state path in; the script never names a harness variable the agent could read.
        script = script.replace("${STATE_DIR}", state_dir.as_posix())
        target.write_text(script, encoding="utf-8", newline="\n")
        target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    # Uncommitted work (an agent's unfinished change) sits on top of the checked-out branch.
    branch = fixture.get("checkout") or "main"
    _git(repo, "checkout", "-q", branch)
    _write_files(repo, fixture.get("uncommitted") or {})
    count = int(_git(repo, "rev-list", "--count", "--all").stdout.strip())
    sha = _git(repo, "rev-parse", "HEAD").stdout.strip()
    return Workspace(root, repo, bin_dir, state_dir, count, branch, sha)


ISOLATED_HOME_KEYS = (
    "HOME",
    "USERPROFILE",
    "CF_HOME",
    "CF_PLUGIN_HOME",
    "XDG_CONFIG_HOME",
    "XDG_CACHE_HOME",
    "XDG_DATA_HOME",
)


def fixture_value(value: str, ws: Workspace) -> str:
    """${STATE_DIR} / ${REPO} let a fixture point an innocuous env var at harness paths."""
    return value.replace("${STATE_DIR}", str(ws.state_dir)).replace("${REPO}", str(ws.repo))


def child_env(
    base: dict[str, str], ws: Workspace, spec: Mapping[str, Any], services: Sequence[Service] | None = None
) -> dict[str, str]:
    env = dict(base)
    env["PATH"] = str(ws.bin_dir) + os.pathsep + env.get("PATH", "")
    # The child gets an empty home: a real `cf` found by absolute path cannot find the operator's
    # session (~/.cf, CF_HOME) and no dotfile of the operator's is readable through the home lookup.
    # The Claude credential copy stays where clean_env put it (CLAUDE_CONFIG_DIR), which is the one
    # path the probe still has to expose and scans outputs for.
    home = ws.root / "home"
    home.mkdir(exist_ok=True)
    for key in ISOLATED_HOME_KEYS:
        env[key] = str(home)
    if os.name == "nt":
        env["HOMEDRIVE"] = home.drive
        env["HOMEPATH"] = str(home)[len(home.drive) :]
    # No harness-named variable reaches the agent; fixtures point innocuous names at ${STATE_DIR}.
    for key, value in declared_env(spec).items():
        env[str(key)] = service_value(fixture_value(str(value), ws), services, for_agent=True)
    return env


def service_value(value: str, services: Sequence[Service] | None, *, for_agent: bool = False) -> str:
    """Resolve a service placeholder to its audited agent URL or direct grading URL."""
    for service in services or []:
        url = service.agent_url if for_agent and service.agent_url else service.base_url
        value = value.replace("${SERVICE_URL:" + service.name + "}", url)
    return value


@dataclass
class GitFacts:
    commit_count: int
    branch: str
    changed: list[tuple[str, str]]  # (status, posix path)
    patch: str
    # Why the changed paths could not be listed: a git command failed, so they are unknown, not none.
    problem: str | None = None


def collect_git_facts(ws: Workspace) -> GitFacts:
    count = int(_git(ws.repo, "rev-list", "--count", "--all").stdout.strip())
    branch = _git(ws.repo, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    # Diff against the fixture baseline, not the current HEAD: changes the agent committed must
    # stay visible to the surgical-change and content checks.
    base = ws.baseline_sha or "HEAD"
    # Stage into a private copy of the agent's index: a lock the agent left on its own index cannot
    # hide a change, and grading never rewrites the agent's index.
    with tempfile.TemporaryDirectory(dir=ws.root) as private:
        index = Path(private) / "index"
        if (ws.repo / ".git" / "index").is_file():
            shutil.copyfile(ws.repo / ".git" / "index", index)
        env = {**os.environ, "GIT_INDEX_FILE": str(index)}
        outputs = []
        for args in (
            ("add", "-A"),
            # --no-renames: a file moved out of the allowed set must show as a deletion, not vanish
            # into an R line whose only reported path is the destination.
            ("diff", "--cached", "--no-renames", "--name-status", base),
            ("diff", "--cached", base),
        ):
            proc = _git(ws.repo, *args, check=False, env=env)
            if proc.returncode != 0:
                return GitFacts(
                    count, branch, [], "", f"git {args[0]} exited {proc.returncode}: {proc.stderr.strip()[:200]}"
                )
            outputs.append(proc.stdout)
    changed = []
    for line in outputs[1].splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            changed.append((parts[0][:1], parts[-1].replace("\\", "/")))
    return GitFacts(count, branch, changed, outputs[2])


def remove_tree(root: Path) -> None:
    """Delete a workspace, clearing the read-only bit git sets on object files (Windows refuses otherwise)."""

    def _clear_and_retry(func: Callable[..., Any], path: str, _exc: BaseException) -> None:
        with contextlib.suppress(OSError):
            os.chmod(path, stat.S_IWRITE)
            func(path)

    for attempt in range(3):
        shutil.rmtree(root, onexc=_clear_and_retry)
        if not root.exists():
            return
        time.sleep(0.5 * (attempt + 1))
    raise OSError(f"could not remove workspace {root} after 3 attempts")
