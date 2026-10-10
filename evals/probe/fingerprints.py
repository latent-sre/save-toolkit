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
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import clean_room
import graders as fleet_graders
import judge as rubric_judge
import yaml

from . import constants
from .constants import EVALS_DIR, PACKAGE_DIR, ROOT

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


def _files_digest(paths: Iterable[Path], base: Path) -> str:
    """One digest over files, each bound to its path under `base` and read with LF line endings, as
    `plugin_digest` explains."""
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(base).as_posix().encode("utf-8") + b"\0")
        digest.update(path.read_bytes().replace(b"\r\n", b"\n") + b"\0")
    return digest.hexdigest()


def harness_source_digest() -> str:
    return _files_digest(HARNESS_FILES, EVALS_DIR)


# Loaded code is stable for this process. Changed disk bytes require a restart, never a new
# identity assigned to functions that Python imported earlier. Dependencies are pinned by CI.
HARNESS_SOURCE_SHA256 = harness_source_digest()


HARNESS_IDENTITY = {
    "source_sha256": HARNESS_SOURCE_SHA256,
    "python": sys.version,
    "python_implementation": sys.implementation.name,
    "pyyaml": yaml.__version__,
}


def _rubric_name(definition: Mapping[str, Any]) -> str | None:
    """The rubric a grader or `fleet_grader` check asks the judge for, when it is a rubric."""
    if definition.get("type") == "rubric":
        return definition.get("name")
    if definition.get("check") == "fleet_grader" and definition.get("name") == "rubric":
        return definition.get("rubric_name")
    return None


def required_rubrics(spec: Mapping[str, Any]) -> set[str]:
    definitions = [*spec.get("graders", []), *spec.get("checks", [])]
    return {name for definition in definitions if (name := _rubric_name(definition))}


def binding_for(spec: Mapping[str, Any], judge_binding: rubric_judge.JudgeBinding | None) -> dict[str, Any] | None:
    """The judge binding a scenario's identity binds and its grade records: only a scenario that grades
    a rubric has one."""
    return judge_binding.metadata if judge_binding and required_rubrics(spec) else None


def _case_payload(spec: Mapping[str, Any]) -> dict[str, Any]:
    """The case a verdict is about: the scenario, the judge's cached rubric definitions, and current
    oracle file bytes.

    The judge loads rubrics once per process (`load_rubrics` is cached). A disk edit takes effect in a
    new process, so hash the same cached definitions it consumes rather than attributing a verdict to
    unconsumed bytes.
    """
    if harness_source_digest() != HARNESS_SOURCE_SHA256:
        raise RuntimeError("evaluator source changed after import; start a new process")
    rubrics, oracles = {}, {}
    for definition in [*spec.get("graders", []), *spec.get("checks", [])]:
        name = _rubric_name(definition)
        if name:
            rubrics[name] = rubric_judge.load_rubrics().get(name)
        for relative in (definition.get("writes_from") or {}).values():
            source = constants.oracle_source(relative)
            oracles[relative] = (
                hashlib.sha256(source.read_bytes().replace(b"\r\n", b"\n")).hexdigest() if source else None
            )
    return {"scenario": spec, "rubrics": rubrics, "oracles": oracles}


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=True).encode("utf-8")).hexdigest()


def scenario_digest(spec: Mapping[str, Any], judge_binding: dict[str, Any] | None = None) -> str:
    """The case bound to the runner, Python and libraries that grade it, and to the judge binding
    when a rubric is graded."""
    payload = {**_case_payload(spec), "implementation": HARNESS_IDENTITY}
    if required_rubrics(spec):
        payload["judge_binding"] = judge_binding
    return _digest(payload)


def case_digest(spec: Mapping[str, Any]) -> str:
    """The case alone: scenario, oracle bytes and rubric definitions, without the runner, Python,
    library versions or judge binding. Two runners grading the same case share it (DEC-22)."""
    return _digest(_case_payload(spec))


def assertion_id(identity: str, index: int) -> str:
    """An expectation's id: its scenario identity and position. Positions distinguish repeated grader
    types; the digest binds each position's configuration."""
    return f"{identity}:{index}"


def stamp_assertions(identity: str, expectations: list[dict[str, Any]]) -> str:
    for index, expectation in enumerate(expectations):
        expectation["id"] = assertion_id(identity, index)
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


def _measured_inputs(root: Path) -> list[str]:
    """The plugin inputs measured under `root`: every required one, and each optional one present. A
    present optional input is measured as a required one is, so a link there is refused, never read
    as absent; one that is absent is a property of an older plugin image."""
    return [
        *PLUGIN_INPUT_PATHS,
        *(relative for relative in OPTIONAL_PLUGIN_INPUT_PATHS if os.path.lexists(root / relative)),
    ]


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
        for parent in path.parents:
            if parent == root:
                break
            if _is_reparse_point(parent):
                raise MeasuredInputRefused(f"refusing linked/reparse measured input: {parent}")
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


def _plugin_files(root: Path) -> list[Path]:
    """Tracked and non-ignored candidate files; a served image has no Git filtering.

    Validate the entire measured tree before filtering, so ignore rules cannot hide a link. Git's
    inventory keeps force-tracked ignored files and ordinary untracked candidate edits, while local
    ignored bytecode and private files enter neither the digest nor the served image. A corrupt
    inventory fails closed. Named runtime inputs may not disappear merely because they are ignored.
    """
    inputs = _measured_inputs(root)
    files = _files_under(*inputs, root=root)
    if not os.path.lexists(root / ".git"):
        return files
    inventory = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", *inputs],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="surrogateescape",
    )
    if inventory.returncode:
        raise MeasuredInputRefused(f"could not enumerate plugin Git inventory at {root}")
    included = {root / relative for relative in inventory.stdout.split("\0") if relative}
    for relative in inputs:
        path = root / relative
        if path.is_file() and path not in included:
            raise MeasuredInputRefused(f"named plugin input is ignored and untracked; add it to Git: {path}")
    return [path for path in files if path in included]


def plugin_digest(root: Path = ROOT) -> str:
    """One digest over every measured plugin input, path-bound so a rename is not invisible.

    Line endings are normalized to LF before hashing: the repository stores LF, a Windows checkout
    with autocrlf holds CRLF for whatever git wrote and LF for whatever a tool rewrote, and a raw
    digest therefore named the host, not the bytes (2026-09-03: three values for one commit).
    """
    files = _plugin_files(root)
    return _files_digest(sorted((p for p in files if p.is_file()), key=lambda p: p.as_posix()), root)


def stage_plugin(source: Path, target: Path) -> Path:
    """Copy the measured plugin inputs, and only those, to *target*: the image a trial is served.

    A trial served the checkout as its plugin root could read the rest of it, this repository's
    evals, docs and history, which teach a routing answer (EVAL-014). The image holds nothing else,
    so nothing else is granted. A copy that does not hash as its source is refused.
    """
    if os.path.lexists(target):
        raise MeasuredInputRefused(f"plugin image target already exists: {target}")
    inputs = _measured_inputs(source)
    files = _plugin_files(source)
    for relative in inputs:
        if (source / relative).is_dir():  # a directory input with no files is still a measured input
            (target / relative).mkdir(parents=True, exist_ok=True)
    for path in files:
        destination = target / path.relative_to(source)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
    if plugin_digest(target) != plugin_digest(source):
        raise MeasuredInputRefused(f"plugin image at {target} does not match the measured inputs of {source}")
    return target


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
    top = _git_text(plugin_root, "rev-parse", "--show-toplevel")
    if top is None or Path(top).resolve() != plugin_root.resolve():
        raise MeasuredInputRefused(f"plugin root must be its own Git checkout root: {plugin_root}")
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


def _windows_host_account() -> tuple[str, bool]:
    """The process token's SID and TokenElevation, independent of username/environment claims.

    TokenElevation reports the token used by children, rather than membership in Administrators
    (which a normal UAC-limited process may still hold). Query only; never request elevation.
    """
    if sys.platform != "win32":
        raise OSError("Windows process tokens are unavailable on this host")
    import ctypes  # noqa: PLC0415 -- this binding is used only on Windows
    from ctypes import wintypes  # noqa: PLC0415

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    security = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel.GetCurrentProcess.argtypes = []
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    kernel.LocalFree.argtypes = [wintypes.HLOCAL]
    kernel.LocalFree.restype = wintypes.HLOCAL
    security.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    security.OpenProcessToken.restype = wintypes.BOOL
    security.GetTokenInformation.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        wintypes.LPVOID,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    security.GetTokenInformation.restype = wintypes.BOOL
    security.ConvertSidToStringSidW.argtypes = [wintypes.LPVOID, ctypes.POINTER(wintypes.LPWSTR)]
    security.ConvertSidToStringSidW.restype = wintypes.BOOL
    token = wintypes.HANDLE()
    if not security.OpenProcessToken(kernel.GetCurrentProcess(), 0x0008, ctypes.byref(token)):  # TOKEN_QUERY
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        size = wintypes.DWORD()
        security.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))  # TokenUser: variable size
        if not size.value:
            raise ctypes.WinError(ctypes.get_last_error())
        user = ctypes.create_string_buffer(size.value)
        if not security.GetTokenInformation(token, 1, user, size, ctypes.byref(size)):
            raise ctypes.WinError(ctypes.get_last_error())
        # TOKEN_USER starts with SID_AND_ATTRIBUTES, whose first member is the SID pointer.
        sid = ctypes.cast(user, ctypes.POINTER(wintypes.LPVOID)).contents.value
        text = wintypes.LPWSTR()
        if not security.ConvertSidToStringSidW(sid, ctypes.byref(text)):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            account_id = text.value
        finally:
            kernel.LocalFree(text)
        if not account_id:
            raise OSError("process token returned no account SID")
        elevation = wintypes.DWORD()
        if not security.GetTokenInformation(
            token,
            20,
            ctypes.byref(elevation),
            ctypes.sizeof(elevation),
            ctypes.byref(size),  # TokenElevation
        ):
            raise ctypes.WinError(ctypes.get_last_error())
        return account_id, bool(elevation.value)
    finally:
        kernel.CloseHandle(token)


def host_identity() -> dict[str, Any]:
    """Observed host/account/privilege identity; missing evidence stays unknown.

    On POSIX, `elevated` records effective UID 0, not ambient capabilities or sudo eligibility.
    A SID or effective UID identifies the account without trusting USERNAME, USER or HOME.
    """
    identity: dict[str, Any] = {
        "hostname": None,
        "account_id": None,
        "elevated": None,
        "identity_source": "windows_process_token" if os.name == "nt" else "posix_effective_uid",
    }
    try:
        identity["hostname"] = socket.gethostname() or None
        if sys.platform == "win32":
            identity["account_id"], identity["elevated"] = _windows_host_account()
        else:
            uid = os.geteuid()
            identity.update(account_id=f"uid:{uid}", elevated=uid == 0)
    except (OSError, AttributeError) as exc:
        identity["problem"] = f"host identity could not be fully observed: {exc}"
    return identity


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
        "host_identity": host_identity(),
    }


def runtime_evidence_problem(runtime: object, *, require_unelevated: bool = False) -> str | None:
    """Why a runtime cannot establish one measurement, or cannot admit a new unelevated trial.

    Old records stay readable, but matching unknown account fields does not establish matching
    hosts. Historical known elevation remains observable evidence; only new admission requires
    the ordinary unelevated account mandated by the native execution contract.
    """
    if not isinstance(runtime, Mapping):
        return "CLI version and host/account/elevation evidence is missing"
    version = runtime.get("cli_version")
    if not isinstance(version, str) or not version.strip():
        return "the CLI did not report its version, so no result would identify it; fix --executable first"
    platform_evidence = runtime.get("host_platform")
    if not isinstance(platform_evidence, Mapping) or not platform_evidence:
        return "host platform evidence is missing"
    identity = runtime.get("host_identity")
    if not isinstance(identity, Mapping):
        return "host/account/elevation evidence is missing; legacy platform metadata does not identify the account"
    for field in ("hostname", "account_id"):
        value = identity.get(field)
        if not isinstance(value, str) or not value.strip():
            return f"host/account/elevation evidence is incomplete: {field} is unknown"
    if type(identity.get("elevated")) is not bool:
        return "host/account/elevation evidence is incomplete: elevated is unknown"
    if identity.get("identity_source") not in ("windows_process_token", "posix_effective_uid"):
        return "host/account/elevation evidence has no supported OS identity source"
    if identity.get("problem"):
        return "host/account/elevation observation reported a problem; inspect the recorded identity evidence"
    if require_unelevated and identity["elevated"]:
        return "native trials require an unelevated account; this process is elevated"
    return None


def plugin_drift_problem(plugin_root: Path, expected: str) -> str | None:
    try:
        if plugin_digest(plugin_root) != expected:
            return "plugin inputs changed during the trial; re-run with one candidate"
    except (OSError, RuntimeError) as exc:
        return f"plugin inputs could not be verified after the trial: {exc}"
    return None
