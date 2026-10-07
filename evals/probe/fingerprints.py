"""What a result is bound to: the runner's source, the measured plugin, the CLI and host, and the case.

Every scenario identity binds the runner's own source digest, so a verdict names the code that graded
it; the case digest leaves the runner out, so two runners grading the same case share it (DEC-22).
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shlex
import stat
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import clean_room
import graders as fleet_graders
import judge as rubric_judge
import yaml

from .constants import EVALS_DIR, ORACLE_DIR, PACKAGE_DIR, ROOT

# Every file whose code grades a trial. The package is globbed, so a module added to it is bound the
# moment it exists; a hand-kept list could leave one out of the identity without anyone noticing.
HARNESS_FILES = tuple(
    Path(path).resolve()
    for path in (
        EVALS_DIR / "build_probe.py",
        *sorted(PACKAGE_DIR.glob("*.py")),
        fleet_graders.__file__,
        rubric_judge.__file__,
        clean_room.__file__,
        fleet_graders.INCIDENT_BOARD_ORACLE,
    )
)


def harness_source_digest() -> str:
    digest = hashlib.sha256()
    for path in HARNESS_FILES:
        digest.update(path.relative_to(EVALS_DIR).as_posix().encode("utf-8") + b"\0")
        digest.update(path.read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return digest.hexdigest()


# Loaded code is stable for this process. Changed disk bytes require a restart, never a new
# identity assigned to functions that Python imported earlier. Dependencies are pinned by CI.
HARNESS_SOURCE_SHA256 = harness_source_digest()


HARNESS_IDENTITY = {
    "source_sha256": HARNESS_SOURCE_SHA256,
    "python": sys.version,
    "python_implementation": sys.implementation.name,
    "pyyaml": yaml.__version__,
}


def required_rubrics(spec: Mapping[str, Any]) -> set[str]:
    return {g["name"] for g in spec.get("graders", []) if g.get("type") == "rubric"} | {
        g["rubric_name"]
        for g in spec.get("checks", [])
        if g.get("check") == "fleet_grader" and g.get("name") == "rubric"
    }


def scenario_digest(
    spec: Mapping[str, Any], judge_binding: dict[str, Any] | None = None, *, case_only: bool = False
) -> str:
    """Bind the scenario, the judge's cached rubric definitions, and current oracle file bytes.

    The judge loads rubrics once per process. A disk edit takes effect in a new process, so hash
    the same cached definitions it consumes rather than attributing a verdict to unconsumed bytes.
    """
    if harness_source_digest() != HARNESS_SOURCE_SHA256:
        raise RuntimeError("evaluator source changed after import; start a new process")
    rubrics, oracles = {}, {}
    available = None
    for definition in [*spec.get("graders", []), *spec.get("checks", [])]:
        name = (
            definition.get("name")
            if definition.get("type") == "rubric"
            else definition.get("rubric_name")
            if definition.get("check") == "fleet_grader" and definition.get("name") == "rubric"
            else None
        )
        if name:
            if available is None:
                available = rubric_judge.load_rubrics()
            rubrics[name] = available.get(name)
        for relative in (definition.get("writes_from") or {}).values():
            path = (ROOT / relative).resolve()
            oracles[relative] = (
                hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
                if path.is_relative_to(ORACLE_DIR) and path.is_file()
                else None
            )
    payload: dict[str, Any] = {"scenario": spec, "rubrics": rubrics, "oracles": oracles}
    if case_only:
        return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")).hexdigest()
    payload = {
        "scenario": spec,
        "rubrics": rubrics,
        "oracles": oracles,
        "implementation": HARNESS_IDENTITY,
    }
    if required_rubrics(spec):
        payload["judge_binding"] = judge_binding
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")).hexdigest()


def case_digest(spec: Mapping[str, Any]) -> str:
    """The case alone: scenario, oracle bytes and rubric definitions, without the runner, Python,
    library versions or judge binding. Two runners grading the same case share it (DEC-22)."""
    return scenario_digest(spec, case_only=True)


def stamp_assertions(identity: str, expectations: list[dict[str, Any]]) -> str:
    """Positions distinguish repeated grader types; the digest binds each position's configuration."""
    for index, expectation in enumerate(expectations):
        expectation["id"] = f"{identity}:{index}"
    return identity


# Canonical plugin inputs whose bytes are hashed for every trial.
PLUGIN_INPUT_PATHS = (
    "agents",
    "skills",
    "commands",
    "hooks",
    ".claude-plugin/plugin.json",
    "scripts/fleet_frontmatter.py",
    "scripts/readonly-guard.py",
    "scripts/readonly-guard-hook.sh",
)


# Runtime files introduced after the baseline revision remain measured when present, while their
# absence is itself a valid property of an older plugin image in a fixed incumbent/candidate run.
OPTIONAL_PLUGIN_INPUT_PATHS = (
    "scripts/guard-session-preflight.py",
    "scripts/guard-session-preflight-hook.sh",
    "scripts/readonly-guard-hook.ps1",  # hooks.json runs it for PowerShell; measured since 2026-10-06
)


class MeasuredInputRefused(RuntimeError):
    """A measured plugin input is missing, linked or unreadable, or the plugin root has no commit to
    bind it to, so the candidate cannot be identified."""


def _is_reparse_point(path: Path) -> bool:
    """True for links/junctions, so a measured input cannot be redirected outside the checkout."""
    try:
        info = path.lstat()
    except OSError as exc:
        raise MeasuredInputRefused(f"could not inspect path {path}: {exc}") from exc
    attributes = getattr(info, "st_file_attributes", 0)
    return path.is_symlink() or bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def _files_under(*relative_roots: str, root: Path) -> list[Path]:
    files: list[Path] = []
    for relative in relative_roots:
        path = root / relative
        if not os.path.lexists(path):
            raise MeasuredInputRefused(f"required measured input is missing: {path}")
        if _is_reparse_point(path):  # a link is refused even when its target is gone
            raise MeasuredInputRefused(f"refusing linked/reparse measured input: {path}")
        if path.is_file():
            files.append(path)
        elif path.is_dir():
            for child in path.rglob("*"):
                if _is_reparse_point(child):
                    raise MeasuredInputRefused(f"refusing linked/reparse measured input: {child}")
                if child.is_file():
                    files.append(child)
    return files


def plugin_digest(root: Path = ROOT) -> str:
    """One digest over every measured plugin input, path-bound so a rename is not invisible.

    Line endings are normalized to LF before hashing: the repository stores LF, a Windows checkout
    with autocrlf holds CRLF for whatever git wrote and LF for whatever a tool rewrote, and a raw
    digest therefore named the host, not the bytes (2026-09-03: three values for one commit).
    """
    # A present optional input is measured as a required one is, so a link there is refused, never
    # read as absent; one that is absent is a property of an older plugin image.
    files = _files_under(
        *PLUGIN_INPUT_PATHS,
        *(relative for relative in OPTIONAL_PLUGIN_INPUT_PATHS if os.path.lexists(root / relative)),
        root=root,
    )
    digest = hashlib.sha256()
    for path in sorted((p for p in files if p.is_file()), key=lambda p: p.as_posix()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes().replace(b"\r\n", b"\n"))
        digest.update(b"\0")
    return digest.hexdigest()


def _git_text(cwd: Path, *args: str) -> str | None:
    """A git command's trimmed output, or None when it failed: an unknown answer, never an empty one."""
    proc = subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    return proc.stdout.strip() if proc.returncode == 0 else None


def plugin_provenance(plugin_root: Path) -> dict[str, Any]:
    """Bind a run to the bytes it measured: the plugin root's HEAD, whether its plugin inputs are
    dirty (None when git could not say), and the plugin-source digest.
    A label such as `new_skill` is operator-chosen; this is what proves which revision was graded."""
    commit = _git_text(plugin_root, "rev-parse", "HEAD")
    if commit is None:
        raise MeasuredInputRefused(f"plugin root {plugin_root} is not a git checkout; provenance cannot be recorded")
    dirty = _git_text(
        plugin_root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--",
        *PLUGIN_INPUT_PATHS,
        *OPTIONAL_PLUGIN_INPUT_PATHS,
    )
    return {
        "plugin_root": str(plugin_root.resolve()),
        "plugin_commit": commit,
        "plugin_inputs_dirty": None if dirty is None else bool(dirty),
        "plugin_source_sha256": plugin_digest(plugin_root),
    }


_RUNNER_PROVENANCE: dict[str, Any] | None = None


def runner_provenance() -> dict[str, Any]:
    """The runner that graded a run: its checkout's HEAD, whether its source files are dirty, and the
    source digest that every scenario identity binds. With `--plugin-root` on another checkout,
    `plugin_commit` names the candidate; this names the runner."""
    global _RUNNER_PROVENANCE
    if _RUNNER_PROVENANCE is None:
        root = ROOT.resolve()
        files = [path.relative_to(root).as_posix() for path in HARNESS_FILES if path.is_relative_to(root)]
        dirty = _git_text(ROOT, "status", "--porcelain=v1", "--untracked-files=all", "--", *files)
        _RUNNER_PROVENANCE = {
            "runner_commit": _git_text(ROOT, "rev-parse", "HEAD"),
            "runner_source_dirty": None if dirty is None else bool(dirty),
            "runner_source_sha256": HARNESS_SOURCE_SHA256,
        }
    return dict(_RUNNER_PROVENANCE)


def executable_argv(executable: str) -> list[str]:
    """The argv `--executable` launches: a bare binary, or a command such as "python stub.py" split into
    words (tests use a stub that emits stream-json). Trials and the version probe launch this argv from
    a fresh directory, so a command must name its script by absolute path."""
    return [t.strip('"') for t in shlex.split(executable, posix=False)] if " " in executable else [executable]


def runtime_identity(executable: str) -> dict[str, Any]:
    """The CLI version and host platform a batch measured; a version the CLI cannot report is null."""
    try:
        # From an empty directory, as a trial runs from its fresh workspace: a script path relative to
        # the runner's directory finds nothing here, as it would find nothing in a trial.
        with tempfile.TemporaryDirectory(prefix="cli-version-", ignore_cleanup_errors=True) as neutral:
            proc = subprocess.run(
                [*executable_argv(executable), "--version"],
                cwd=neutral,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
        lines = proc.stdout.strip().splitlines() if proc.returncode == 0 else []
        version = lines[0].strip() if lines else None
    except (OSError, ValueError, subprocess.TimeoutExpired):  # ValueError: a command with an unclosed quote
        version = None
    return {
        "cli_version": version,
        "host_platform": {"system": platform.system(), "release": platform.release(), "machine": platform.machine()},
    }


def plugin_drift_problem(plugin_root: Path, expected: str) -> str | None:
    try:
        if plugin_digest(plugin_root) != expected:
            return "plugin inputs changed during the trial; re-run with one candidate"
    except (OSError, RuntimeError) as exc:
        return f"plugin inputs could not be verified after the trial: {exc}"
    return None
