#!/usr/bin/env python3
"""Probe the exact Python interpreter that a SessionStart hook resolved for the Bash guard."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ALLOW_EXIT = 42
DENY_EXIT = 43
TIMEOUT_SECONDS = 5
ALLOW_PAYLOAD = json.dumps(
    {
        "tool_name": "Bash",
        "agent_type": "save-toolkit:sre",
        "tool_input": {"command": "git status --short"},
    },
    separators=(",", ":"),
)
DENY_PAYLOAD = json.dumps(
    {
        "tool_name": "Bash",
        "agent_type": "save-toolkit:sre",
        "tool_input": {"command": "python -c pass"},
    },
    separators=(",", ":"),
)


def _run(guard: Path, payload: str) -> tuple[int, str]:
    try:
        result = subprocess.run(
            [sys.executable, "-I", "-S", str(guard)],
            input=payload,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return 127, ""
    return result.returncode, result.stdout


def _is_deny(stdout: str) -> bool:
    try:
        output = json.loads(stdout)["hookSpecificOutput"]
    except (json.JSONDecodeError, KeyError, TypeError):
        return False
    return (
        isinstance(output, dict)
        and output.get("hookEventName") == "PreToolUse"
        and output.get("permissionDecision") == "deny"
    )


def main() -> int:
    guard = Path(__file__).with_name("readonly-guard.py")
    allow_code, allow_stdout = _run(guard, ALLOW_PAYLOAD)
    deny_code, deny_stdout = _run(guard, DENY_PAYLOAD)
    if allow_code == ALLOW_EXIT and not allow_stdout.strip() and deny_code == DENY_EXIT and _is_deny(deny_stdout):
        return ALLOW_EXIT

    reason = (
        "save-toolkit guard session preflight failed for resolved interpreter "
        f"{sys.executable!r}: allow_exit={allow_code}, deny_exit={deny_code}. "
        "Guarded Bash remains fail-closed; repair the lane PATH or plugin before relying on it."
    )
    print(
        json.dumps(
            {
                "systemMessage": reason,
                "hookSpecificOutput": {
                    "hookEventName": "SessionStart",
                    "additionalContext": reason,
                },
            },
            separators=(",", ":"),
        )
    )
    return DENY_EXIT


if __name__ == "__main__":
    raise SystemExit(main())
