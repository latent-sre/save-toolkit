#!/usr/bin/env python3
"""Report fleet repository and host health without changing either.

The doctor validates in memory and invokes only an exact read-only command allowlist. It never
generates, installs, fetches, prunes, or starts a model session. Every check is emitted as a validated
evidence envelope; an unavailable or unprobed host is ``skip`` or ``inconclusive``, never ``pass``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence

# Importing repository helpers must not create scripts/__pycache__ in a clean checkout.
sys.dont_write_bytecode = True

try:
    from scripts import (
        check_plan_status,
        evidence_envelope,
        validate_fleet,
    )
except ModuleNotFoundError:
    import check_plan_status  # type: ignore[no-redef]
    import evidence_envelope  # type: ignore[no-redef]
    import validate_fleet  # type: ignore[no-redef]


REPO_ROOT = Path(__file__).resolve().parents[1]
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

    def __post_init__(self) -> None:
        if self.status not in STATUSES:
            raise ValueError(f"unknown fleet-doctor status: {self.status}")


CommandRunner = Callable[[Sequence[str]], CommandResult]
Which = Callable[[str], str | None]


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


def _repository_checks(root: Path) -> list[Check]:
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
    home: Path | None = None,
    run: CommandRunner = _run_read_only,
    which: Which = shutil.which,
    now: datetime | None = None,
) -> dict[str, object]:
    root = root.resolve()
    home = (home or Path.home()).resolve()
    started = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    run_id = "doctor-" + started.strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    revision, checks = _git_checks(root, run)
    checks.extend(_repository_checks(root))
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
