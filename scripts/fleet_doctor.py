#!/usr/bin/env python3
"""Report fleet repository, guard, and host health without changing them.

The doctor validates in memory and invokes only an exact read-only command allowlist. It never
generates, installs, fetches, prunes, or starts a model session. Every check is emitted as a validated
evidence envelope; an unavailable or unprobed host is ``skip`` or ``inconclusive``, never ``pass``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from collections import Counter
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence

# Importing repository helpers must not create scripts/__pycache__ in a clean checkout.
_previous_dont_write_bytecode = sys.dont_write_bytecode
sys.dont_write_bytecode = True
try:
    try:
        from scripts import evidence_envelope
    except ModuleNotFoundError:
        import evidence_envelope  # type: ignore[no-redef]
finally:
    sys.dont_write_bytecode = _previous_dont_write_bytecode
del _previous_dont_write_bytecode


PLUGIN_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PLUGIN_ROOT
STATUSES = ("pass", "fail", "skip", "inconclusive")
REPORT_FIELDS = {
    "schema_version",
    "run_id",
    "generated_at",
    "root",
    "revision",
    "summary",
    "evidence",
}
SENSITIVE_OUTPUT_RE = re.compile(
    r"(?i)(api[-_ ]?key|authorization|bearer|cookie|credential|password|secret|token)"
)


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class Check:
    check_id: str
    status: str
    summary: str
    details: dict[str, object] = field(default_factory=dict)
    command_argv: tuple[str, ...] | None = None
    command_cwd: str | None = None
    exit_code: int | None = None
    limitations: tuple[str, ...] = ()
    target_root: str | None = None
    target_revision: str | None = None
    tree_digest: str | None = None

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise ValueError(f"unknown fleet-doctor status: {self.status}")


CommandRunner = Callable[[Sequence[str]], CommandResult]
GuardRunner = Callable[[Sequence[str], str], CommandResult]
Which = Callable[[str], str | None]

GUARD_INTERPRETER_CANDIDATES = ("python3", "python", "py")
GUARD_ALLOW_EXIT = 42
GUARD_DENY_EXIT = 43
GUARD_PROBE_TIMEOUT_SECONDS = 5
TRUSTED_GUARD_HOOK_SHA256 = "d605b157942c8db893c7c06882824bcdaef33748bdbaf57dc2bacde8b19ab0cc"
GUARD_ALLOW_PAYLOAD = json.dumps(
    {
        "tool_name": "Bash",
        "agent_type": "save-toolkit:sre",
        "tool_input": {"command": "git status --short"},
    },
    separators=(",", ":"),
)
GUARD_DENY_PAYLOAD = json.dumps(
    {
        "tool_name": "Bash",
        "agent_type": "save-toolkit:sre",
        "tool_input": {"command": "python -c pass"},
    },
    separators=(",", ":"),
)


def _command_name(executable: str) -> str:
    return Path(executable).stem.lower()


def _assert_read_only_command(argv: Sequence[str]) -> None:
    """Reject command drift before subprocess execution can acquire mutation authority."""

    if not argv:
        raise ValueError("empty command")
    name = _command_name(argv[0])
    tail = tuple(argv[1:])
    allowed = (
        name == "git"
        and len(tail) >= 5
        and tail[:2] == ("--no-optional-locks", "-C")
        and tuple(tail[3:]) in {("rev-parse", "HEAD"), ("status", "--short")}
    ) or (name == "claude" and tail in {("--version",), ("plugin", "list")})
    allowed = allowed or (name in {"copilot", "code"} and tail == ("--version",))
    if not allowed:
        raise ValueError(
            "fleet doctor refused a command outside its read-only allowlist: " + repr(list(argv))
        )


def _run_read_only(argv: Sequence[str]) -> CommandResult:
    _assert_read_only_command(argv)
    try:
        result = subprocess.run(
            list(argv),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CommandResult(127, "", type(exc).__name__)
    return CommandResult(result.returncode, result.stdout, result.stderr)


def _assert_guard_probe_command(argv: Sequence[str]) -> None:
    """Allow only the hook's isolated interpreter shape against the bundled guard."""

    expected_guard = (PLUGIN_ROOT / "scripts" / "readonly-guard.py").resolve()
    if len(argv) != 4:
        raise ValueError("fleet doctor refused a malformed guard probe")
    if _command_name(argv[0]) not in GUARD_INTERPRETER_CANDIDATES:
        raise ValueError("fleet doctor refused a non-hook interpreter")
    if tuple(argv[1:3]) != ("-I", "-S") or Path(argv[3]).resolve() != expected_guard:
        raise ValueError("fleet doctor refused a command outside the guard probe contract")


def _run_guard_probe(argv: Sequence[str], payload: str) -> CommandResult:
    _assert_guard_probe_command(argv)
    try:
        result = subprocess.run(
            list(argv),
            input=payload,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=GUARD_PROBE_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CommandResult(127, "", type(exc).__name__)
    return CommandResult(result.returncode, result.stdout, result.stderr)


def _is_guard_deny_output(stdout: str) -> bool:
    try:
        payload = json.loads(stdout)
        output = payload["hookSpecificOutput"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return False
    return (
        isinstance(output, dict)
        and output.get("hookEventName") == "PreToolUse"
        and output.get("permissionDecision") == "deny"
    )


def _guard_interpreter_check(
    guard_path: Path,
    which: Which,
    run: GuardRunner = _run_guard_probe,
) -> Check:
    """Model the launcher's first authenticated answer independently for each payload."""

    observations: list[dict[str, object]] = []
    available = False
    allow_answer: tuple[str, CommandResult] | None = None
    deny_answer: tuple[str, CommandResult] | None = None
    for candidate in GUARD_INTERPRETER_CANDIDATES:
        executable = which(candidate)
        if not executable:
            continue
        available = True
        argv = (executable, "-I", "-S", str(guard_path))
        observation: dict[str, object] = {"candidate": candidate}
        if allow_answer is None:
            allow = run(argv, GUARD_ALLOW_PAYLOAD)
            observation["allow_exit_code"] = allow.returncode
            if allow.returncode in {GUARD_ALLOW_EXIT, GUARD_DENY_EXIT}:
                allow_answer = (candidate, allow)
        if deny_answer is None:
            deny = run(argv, GUARD_DENY_PAYLOAD)
            observation["deny_exit_code"] = deny.returncode
            if deny.returncode in {GUARD_ALLOW_EXIT, GUARD_DENY_EXIT}:
                deny_answer = (candidate, deny)
        observations.append(observation)
        if allow_answer is not None and deny_answer is not None:
            break

    if not available:
        return Check(
            "guard.interpreter-protocol",
            "fail",
            "No hook-candidate Python interpreter is available.",
            {
                "candidates": list(GUARD_INTERPRETER_CANDIDATES),
                "plugin_root": str(guard_path.parent.parent),
            },
            limitations=("The hook denies all Bash when no candidate can run the guard.",),
        )

    allow_ok = (
        allow_answer is not None
        and allow_answer[1].returncode == GUARD_ALLOW_EXIT
        and not allow_answer[1].stdout.strip()
    )
    deny_ok = (
        deny_answer is not None
        and deny_answer[1].returncode == GUARD_DENY_EXIT
        and _is_guard_deny_output(deny_answer[1].stdout)
    )
    details: dict[str, object] = {
        "allow_answer": (
            None
            if allow_answer is None
            else {"candidate": allow_answer[0], "exit_code": allow_answer[1].returncode}
        ),
        "deny_answer": (
            None
            if deny_answer is None
            else {"candidate": deny_answer[0], "exit_code": deny_answer[1].returncode}
        ),
        "observations": observations,
        "plugin_root": str(guard_path.parent.parent),
    }
    if allow_ok and deny_ok:
        return Check(
            "guard.interpreter-protocol",
            "pass",
            "The launcher candidate walk returned the guard's exact allow and deny protocol.",
            details,
        )

    return Check(
        "guard.interpreter-protocol",
        "fail",
        "The launcher candidate walk did not return the guard's exact allow and deny protocol.",
        details,
        limitations=(
            "Each payload stops at its first 42 or 43; other exit codes continue the candidate walk.",
        ),
    )


def _expected_guard_hook_command(plugin_root: Path) -> str | None:
    """Rebuild the installed standalone launcher into its exact inlined command."""

    launcher_path = plugin_root / "scripts" / "readonly-guard-hook.sh"
    if not launcher_path.is_file() or launcher_path.is_symlink():
        return None
    try:
        script_lines = [
            line.strip()
            for line in launcher_path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
    except (OSError, UnicodeError):
        return None
    if not script_lines:
        return None

    command = script_lines[0]
    for line in script_lines[1:]:
        separator = " " if command.endswith(" do") else "; "
        command = f"{command}{separator}{line}"
    return command


def _guard_bundle_tree_digest(plugin_root: Path) -> str:
    """Bind guard evidence to the exact installed files without following links."""

    digest = hashlib.sha256()
    for relative in (
        Path("hooks/hooks.json"),
        Path("scripts/readonly-guard-hook.sh"),
        Path("scripts/readonly-guard.py"),
    ):
        digest.update(relative.as_posix().encode("utf-8") + b"\0")
        path = plugin_root / relative
        if not path.is_file() or path.is_symlink():
            digest.update(b"missing\0")
            continue
        try:
            payload = path.read_bytes()
        except OSError:
            digest.update(b"unreadable\0")
            continue
        digest.update(len(payload).to_bytes(8, "big"))
        digest.update(payload)
    return digest.hexdigest()


def _guard_hook_check(plugin_root: Path) -> Check:
    """Inspect the current plugin root's PreToolUse registration without firing a hook."""

    hook_path = plugin_root / "hooks" / "hooks.json"
    if not hook_path.is_file() or hook_path.is_symlink():
        return Check(
            "guard.hook-registration",
            "fail",
            "The current plugin root has no regular hooks/hooks.json file.",
            {
                "registered": False,
                "configuration": "missing",
                "plugin_root": str(plugin_root),
            },
        )
    try:
        document = json.loads(hook_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return Check(
            "guard.hook-registration",
            "fail",
            "The current plugin hook configuration could not be read as JSON.",
            {
                "registered": False,
                "configuration": "invalid",
                "plugin_root": str(plugin_root),
            },
        )

    expected_command = _expected_guard_hook_command(plugin_root)
    if expected_command is None:
        return Check(
            "guard.hook-registration",
            "fail",
            "The current plugin root has no readable regular standalone guard launcher.",
            {
                "registered": False,
                "configuration": "launcher-missing-or-invalid",
                "plugin_root": str(plugin_root),
            },
        )

    hooks = document.get("hooks") if isinstance(document, dict) else None
    pre_tool_use = hooks.get("PreToolUse") if isinstance(hooks, dict) else None
    registered = False
    copies_synchronized = False
    trusted_contract = False
    if isinstance(pre_tool_use, list):
        for registration in pre_tool_use:
            if not isinstance(registration, dict) or registration.get("matcher") != "Bash":
                continue
            commands = registration.get("hooks")
            if not isinstance(commands, list):
                continue
            for command_hook in commands:
                if not isinstance(command_hook, dict) or command_hook.get("type") != "command":
                    continue
                command = command_hook.get("command")
                if not isinstance(command, str):
                    continue
                command_digest = hashlib.sha256(command.encode("utf-8")).hexdigest()
                synchronized = command == expected_command
                trusted = command_digest == TRUSTED_GUARD_HOOK_SHA256
                copies_synchronized = copies_synchronized or synchronized
                trusted_contract = trusted_contract or trusted
                if synchronized and trusted:
                    registered = True
                    break
            if registered:
                break

    return Check(
        "guard.hook-registration",
        "pass" if registered else "fail",
        (
            "The current plugin root registers the read-only guard for Bash PreToolUse events."
            if registered
            else (
                "The current plugin root does not register the read-only guard for Bash "
                "PreToolUse events."
            )
        ),
        {
            "registered": registered,
            "configuration": "present",
            "copies_synchronized": copies_synchronized,
            "trusted_contract": trusted_contract,
            "plugin_root": str(plugin_root),
        },
        limitations=(
            "Static registration was inspected; no live Claude hook event was fired.",
        ),
    )


def _guard_file_check(plugin_root: Path) -> Check:
    guard_path = plugin_root / "scripts" / "readonly-guard.py"
    present = guard_path.is_file() and not guard_path.is_symlink()
    return Check(
        "guard.file",
        "pass" if present else "fail",
        (
            "The guard resolves to a regular file under the current plugin root."
            if present
            else "The guard does not resolve to a regular file under the current plugin root."
        ),
        {
            "present": present,
            "relative_path": "scripts/readonly-guard.py",
            "plugin_root": str(plugin_root),
        },
    )


def _select_plugin_root(
    explicit_root: Path | None,
    environment: Mapping[str, str],
) -> tuple[Path, str]:
    if explicit_root is not None:
        return explicit_root.resolve(), "explicit"
    configured = environment.get("CLAUDE_PLUGIN_ROOT", "").strip()
    if configured:
        return Path(configured).resolve(), "CLAUDE_PLUGIN_ROOT"
    return PLUGIN_ROOT.resolve(), "script"


def _plugin_root_check(plugin_root: Path, source: str) -> Check:
    script_root = PLUGIN_ROOT.resolve()
    if source == "CLAUDE_PLUGIN_ROOT":
        matches_script = plugin_root == script_root
        checkout = (plugin_root / ".git").exists()
        status = "fail" if not matches_script else ("inconclusive" if checkout else "pass")
        if not matches_script:
            summary = "CLAUDE_PLUGIN_ROOT does not resolve to the current doctor's plugin root."
            limitations = (
                "The interpreter protocol was not executed from a mismatched plugin root.",
            )
        elif checkout:
            summary = (
                "CLAUDE_PLUGIN_ROOT resolves to the current source checkout; installed-plugin "
                "provenance was not established."
            )
            limitations = (
                "Runtime root resolution was observed, but these are source-checkout bytes.",
            )
        else:
            summary = "CLAUDE_PLUGIN_ROOT resolves to the current doctor's installed-style root."
            limitations = ()
        return Check(
            "guard.plugin-root",
            status,
            summary,
            {
                "source": source,
                "plugin_root": str(plugin_root),
                "script_root": str(script_root),
                "matches_script_root": matches_script,
                "checkout": checkout,
            },
            limitations=limitations,
        )

    checkout = (plugin_root / ".git").exists()
    if source == "explicit":
        summary = (
            "An explicit plugin root was selected; Claude hook runtime resolution was not observed."
        )
    elif checkout:
        summary = (
            "CLAUDE_PLUGIN_ROOT is unset; guard checks describe source-checkout bytes, not "
            "installed-plugin health."
        )
    else:
        summary = (
            "CLAUDE_PLUGIN_ROOT is unset; the doctor is running from an installed-style layout, "
            "but hook runtime resolution was not observed."
        )
    return Check(
        "guard.plugin-root",
        "inconclusive",
        summary,
        {
            "source": source,
            "plugin_root": str(plugin_root),
            "script_root": str(script_root),
            "checkout": checkout,
        },
        limitations=("Run the doctor where Claude supplies CLAUDE_PLUGIN_ROOT for runtime proof.",),
    )


def _guard_checks(
    plugin_root: Path,
    plugin_root_source: str,
    which: Which,
    run: GuardRunner,
) -> list[Check]:
    root_check = _plugin_root_check(plugin_root, plugin_root_source)
    hook = _guard_hook_check(plugin_root)
    guard_file = _guard_file_check(plugin_root)
    checks = [root_check, hook, guard_file]
    trusted_probe_root = plugin_root == PLUGIN_ROOT.resolve() or run is not _run_guard_probe
    if guard_file.status == "pass" and trusted_probe_root:
        checks.append(
            _guard_interpreter_check(
                plugin_root / "scripts" / "readonly-guard.py",
                which,
                run,
            )
        )
    elif guard_file.status == "pass":
        checks.append(
            Check(
                "guard.interpreter-protocol",
                "skip",
                "The interpreter protocol was not probed from a plugin root that differs from "
                "the current doctor.",
                {
                    "plugin_root": str(plugin_root),
                    "script_root": str(PLUGIN_ROOT.resolve()),
                },
                limitations=("An untrusted external Python file was not executed.",),
            )
        )
    else:
        checks.append(
            Check(
                "guard.interpreter-protocol",
                "skip",
                "The interpreter protocol could not be probed because the guard file is missing.",
                limitations=("An unrun probe was not treated as healthy.",),
            )
        )
    tree_digest = _guard_bundle_tree_digest(plugin_root)
    return [
        replace(
            check,
            target_root=str(plugin_root),
            target_revision="unknown",
            tree_digest=tree_digest,
        )
        for check in checks
    ]


def _safe_version(stdout: str) -> tuple[str, tuple[str, ...]]:
    first = stdout.strip().splitlines()[0] if stdout.strip() else "unknown"
    first = " ".join(first.split())[:200]
    if SENSITIVE_OUTPUT_RE.search(first):
        return "redacted", ("CLI version output matched a credential-like marker and was omitted.",)
    return first, ()


def _inventory_contains_plugin(host: str, stdout: str, plugin_name: str) -> bool:
    """Match a real inventory row, never an explanatory substring or lookalike name."""

    plugin_id = re.compile(
        r"(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)(?:@[A-Za-z0-9][A-Za-z0-9._-]*)?"
    )
    for line in stdout.splitlines():
        stripped = line.strip()
        if host == "claude":
            # The installed-row marker is ❯ (U+276F) in observed Claude CLI output; accept the
            # legacy > as well. The plugin id must still fullmatch, so annotated lookalike rows
            # and explanatory text never count.
            match = re.fullmatch(r"[❯>]\s+" + plugin_id.pattern, stripped)
            if match and match.group("name") == plugin_name:
                return True
            continue
        if host == "copilot":
            # Observed Copilot CLI row: "• save-toolkit@latent-sre (v1.0.0)". The bullet and the
            # version annotation are part of the row; the plugin id must still fullmatch.
            match = re.fullmatch(r"•\s+" + plugin_id.pattern + r"(?:\s+\(v[^)]*\))?", stripped)
            if match and match.group("name") == plugin_name:
                return True
    return False


def _git_checks(root: Path, run: CommandRunner) -> tuple[str, list[Check]]:
    head_argv = ("git", "--no-optional-locks", "-C", str(root), "rev-parse", "HEAD")
    head = run(head_argv)
    if head.returncode or not re.fullmatch(r"[0-9a-fA-F]{40,64}", head.stdout.strip()):
        return "unknown", [
            Check(
                "repository.git-revision",
                "inconclusive",
                "Git could not identify an immutable repository revision.",
                {"returncode": head.returncode},
                head_argv,
                str(root),
                head.returncode,
            )
        ]

    revision = head.stdout.strip().lower()
    checks = [
        Check(
            "repository.git-revision",
            "pass",
            "Git repository revision identified.",
            {"revision": revision},
            head_argv,
            str(root),
            head.returncode,
        )
    ]
    status_argv = ("git", "--no-optional-locks", "-C", str(root), "status", "--short")
    status = run(status_argv)
    if status.returncode:
        checks.append(
            Check(
                "repository.worktree-state",
                "inconclusive",
                "Git could not inspect worktree state.",
                {"returncode": status.returncode},
                status_argv,
                str(root),
                status.returncode,
            )
        )
    else:
        changed = len([line for line in status.stdout.splitlines() if line.strip()])
        limitations = (
            ("The worktree contains local changes; evidence describes these exact uncommitted bytes.",)
            if changed
            else ()
        )
        checks.append(
            Check(
                "repository.worktree-state",
                "pass",
                "Git worktree state inspected.",
                {"clean": changed == 0, "changed_entry_count": changed},
                status_argv,
                str(root),
                status.returncode,
                limitations,
            )
        )
    return revision, checks


def _outside_checkout_checks() -> list[Check]:
    limitation = ("Repository-only validation was not treated as a passing check.",)
    return [
        Check(
            "repository.git-revision",
            "skip",
            "No repository checkout is present; Git revision was not inspected.",
            {"checkout": False},
            limitations=limitation,
        ),
        Check(
            "repository.worktree-state",
            "skip",
            "No repository checkout is present; worktree state was not inspected.",
            {"checkout": False},
            limitations=limitation,
        ),
        Check(
            "repository.fleet-contracts",
            "skip",
            "No repository checkout is present; source-tree fleet contracts were not inspected.",
            {"checkout": False},
            limitations=limitation,
        ),
        Check(
            "repository.plan-status",
            "skip",
            "No repository checkout is present; planning governance was not inspected.",
            {"checkout": False},
            limitations=limitation,
        ),
    ]


def _repository_checks(root: Path) -> list[Check]:
    try:
        from scripts import check_plan_status, validate_fleet
    except ModuleNotFoundError:
        import check_plan_status  # type: ignore[no-redef]
        import validate_fleet  # type: ignore[no-redef]

    names, fleet_issues = validate_fleet.validate_repo(root)
    checks = [
        Check(
            "repository.fleet-contracts",
            "fail" if fleet_issues else "pass",
            (
                f"Fleet and generated adapter contracts have {len(fleet_issues)} issue(s)."
                if fleet_issues
                else "Fleet and generated adapter contracts are aligned."
            ),
            {
                "agent_count": len(names),
                "issue_count": len(fleet_issues),
            },
            limitations=(
                ("Issue text is omitted from the portable envelope; rerun validate_fleet.py locally.",)
                if fleet_issues
                else ()
            ),
        )
    ]
    plan_issues = check_plan_status.check(root)
    checks.append(
        Check(
            "repository.plan-status",
            "fail" if plan_issues else "pass",
            (
                f"Planning governance has {len(plan_issues)} issue(s)."
                if plan_issues
                else "The live roadmap and historical plan statuses are consistent."
            ),
            {"issue_count": len(plan_issues)},
            limitations=(
                ("Issue text is omitted from the portable envelope; rerun check_plan_status.py locally.",)
                if plan_issues
                else ()
            ),
        )
    )
    return checks


def _cli_checks(which: Which, run: CommandRunner) -> tuple[list[Check], dict[str, str]]:
    checks: list[Check] = []
    executables: dict[str, str] = {}
    for host, command in (
        ("claude", "claude"),
        ("copilot", "copilot"),
        ("vscode", "code"),
    ):
        executable = which(command)
        if not executable:
            checks.append(
                Check(
                    f"host.{host}.cli",
                    "skip",
                    f"{host} CLI is not installed or not on PATH.",
                    limitations=("Availability was not treated as a passing runtime check.",),
                )
            )
            continue
        executables[host] = executable
        argv = (executable, "--version")
        version = run(argv)
        if version.returncode:
            checks.append(
                Check(
                    f"host.{host}.cli",
                    "inconclusive",
                    f"{host} CLI was found but its version could not be read.",
                    {"returncode": version.returncode},
                    argv,
                    str(REPO_ROOT),
                    version.returncode,
                )
            )
        else:
            safe_version, limitations = _safe_version(version.stdout)
            checks.append(
                Check(
                    f"host.{host}.cli",
                    "pass",
                    f"{host} CLI availability and version were observed.",
                    {"version": safe_version},
                    argv,
                    str(REPO_ROOT),
                    version.returncode,
                    limitations,
                )
            )
    return checks, executables


def _plugin_listing_check(host: str, executable: str, run: CommandRunner) -> Check:
    argv = (executable, "plugin", "list")
    listing = run(argv)
    if listing.returncode:
        return Check(
            f"host.{host}.plugin-inventory",
            "inconclusive",
            f"{host} plugin inventory could not be read.",
            {"returncode": listing.returncode},
            argv,
            str(REPO_ROOT),
            listing.returncode,
        )
    installed = _inventory_contains_plugin(host, listing.stdout, "save-toolkit")
    return Check(
        f"host.{host}.plugin-inventory",
        "pass" if installed else "skip",
        (
            "save-toolkit is present in the host plugin inventory."
            if installed
            else "save-toolkit is absent from the host plugin inventory."
        ),
        {"installed": installed},
        argv,
        str(REPO_ROOT),
        listing.returncode,
        () if installed else ("Absence is not a runtime failure; no plugin behavior was exercised.",),
    )


def _installation_checks(
    root: Path,
    home: Path,
    executables: Mapping[str, str],
    run: CommandRunner,
) -> list[Check]:
    checks: list[Check] = []
    if "claude" in executables:
        checks.append(_plugin_listing_check("claude", executables["claude"], run))
    return checks


def _to_envelope(
    check: Check,
    *,
    root: Path,
    revision: str,
    run_id: str,
    started_at: datetime,
    ended_at: datetime,
) -> dict[str, object]:
    return evidence_envelope.new_envelope(
        producer="fleet_doctor",
        role="fleet-health",
        target_root=check.target_root if check.target_root is not None else str(root),
        target_revision=(
            check.target_revision if check.target_revision is not None else revision
        ),
        tree_digest=check.tree_digest,
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
        environment={"probe": "local-read-only"},
        isolation={"writes": "none", "model_sessions": "none"},
        limitations=check.limitations,
    )


def validate_report(report: Mapping[str, object]) -> None:
    if set(report) != REPORT_FIELDS:
        raise ValueError("fleet-doctor report fields do not match schema version 1")
    if report["schema_version"] != 1:
        raise ValueError("unsupported fleet-doctor schema version")
    run_id = report["run_id"]
    if not isinstance(run_id, str) or not evidence_envelope.CONTEXT_ID_RE.fullmatch(run_id):
        raise ValueError("fleet-doctor run_id is invalid")
    evidence = report["evidence"]
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("fleet-doctor evidence must be a non-empty list")
    counts = Counter()
    for item in evidence:
        if not isinstance(item, dict):
            raise ValueError("fleet-doctor evidence entries must be objects")
        evidence_envelope.validate_envelope(item)
        if item["context"]["run_id"] != run_id:  # type: ignore[index]
            raise ValueError("fleet-doctor evidence run_id mismatch")
        counts[item["status"]] += 1
    summary = report["summary"]
    if not isinstance(summary, dict) or set(summary) != set(STATUSES):
        raise ValueError("fleet-doctor summary must contain exact status counts")
    expected = {status: counts.get(status, 0) for status in STATUSES}
    if summary != expected:
        raise ValueError("fleet-doctor summary does not match evidence")


def collect_report(
    root: Path = REPO_ROOT,
    *,
    plugin_root: Path | None = None,
    environment: Mapping[str, str] | None = None,
    home: Path | None = None,
    run: CommandRunner = _run_read_only,
    guard_run: GuardRunner = _run_guard_probe,
    which: Which = shutil.which,
    now: datetime | None = None,
) -> dict[str, object]:
    root = root.resolve()
    environment = os.environ if environment is None else environment
    plugin_root, plugin_root_source = _select_plugin_root(plugin_root, environment)
    home = (home or Path.home()).resolve()
    started = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    run_id = "doctor-" + started.strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    if (root / ".git").exists():
        revision, checks = _git_checks(root, run)
        checks.extend(_repository_checks(root))
    else:
        revision = "unknown"
        checks = _outside_checkout_checks()
    checks.extend(_guard_checks(plugin_root, plugin_root_source, which, guard_run))
    cli_checks, executables = _cli_checks(which, run)
    checks.extend(cli_checks)
    checks.extend(_installation_checks(root, home, executables, run))
    ended = started if now is not None else datetime.now(timezone.utc)
    envelopes = [
        _to_envelope(
            check,
            root=root,
            revision=revision,
            run_id=run_id,
            started_at=started,
            ended_at=ended,
        )
        for check in checks
    ]
    counts = Counter(item["status"] for item in envelopes)
    report: dict[str, object] = {
        "schema_version": 1,
        "run_id": run_id,
        "generated_at": evidence_envelope.format_timestamp(ended),
        "root": str(root),
        "revision": revision,
        "summary": {status: counts.get(status, 0) for status in STATUSES},
        "evidence": envelopes,
    }
    validate_report(report)
    return report


def render_human(report: Mapping[str, object]) -> str:
    lines = [f"Fleet doctor: {report['root']}@{report['revision']}"]
    for item in report["evidence"]:  # type: ignore[index]
        source = item["source"]
        lines.append(
            f"[{item['status'].upper():12}] {item['criterion']}: {source['summary']}"
        )
        for limitation in item["limitations"]:
            lines.append(f"  limitation: {limitation}")
    summary = report["summary"]
    lines.append("Summary: " + ", ".join(f"{s}={summary[s]}" for s in STATUSES))
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="fleet repository root")
    parser.add_argument("--json", action="store_true", help="emit the versioned JSON report")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = collect_report(args.root)
    except (OSError, ValueError, evidence_envelope.EnvelopeValidationError) as exc:
        print(f"fleet doctor could not produce a report: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_human(report))
    return 1 if report["summary"]["fail"] else 0  # type: ignore[index]


if __name__ == "__main__":
    raise SystemExit(main())
