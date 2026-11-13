"""Admission for a single immutable WP04 fixture on the Codex subscription path."""

from __future__ import annotations

import gzip
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

import yaml
from probe import catalog

PROFILE = "wp04-readonly-v1"
BROWSE_TOOLS = {"list_files", "search_files", "read_slice"}
MANUAL_CHECK = {
    "check": "command_exit_zero",
    "command": 'python -c "raise SystemExit(2)"',
    "inconclusive_exit_code": 2,
    "failure_exit_code": 10,
    "text": "independent operational semantics require human review",
}


def is_wp04(spec: dict[str, Any]) -> bool:
    return bool(re.fullmatch(r"wp04-itbench-(7|21|24|80|102)-indexed-v[67]", str(spec.get("id", ""))))


def validate_wp04_case(spec: Any) -> dict[str, Any]:
    """External task data may not provide executable fixtures or grading commands."""
    if not isinstance(spec, dict) or set(spec) != {"id", "max_turns", "agent", "tools", "prompt", "fixture", "checks"}:
        raise ValueError("WP04 requires the exact recorded observation fixture shape")
    if not is_wp04(spec) or spec["agent"] != "sre-assistant" or spec["max_turns"] != 36:
        raise ValueError("only the five indexed-v6/v7 WP04 SRE cases are admitted")
    if spec["tools"] != ["Read", "Grep", "Glob", "Skill"]:
        raise ValueError("WP04 must retain its recorded read-only tool declaration")
    fixture = spec["fixture"]
    if not isinstance(fixture, dict) or set(fixture) != {"files"} or not isinstance(fixture["files"], dict):
        raise ValueError("WP04 allows files only, without environment, commands or branches")
    files = fixture["files"]
    if "observations/index.json" not in files:
        raise ValueError("WP04 requires its complete observation index")
    for name, content in files.items():
        if (
            not isinstance(name, str)
            or not isinstance(content, str)
            or "\\" in name
            or ":" in name
            or PurePosixPath(name).is_absolute()
            or any(part in {"", ".", "..", ".git"} for part in name.split("/"))
            or name.split("/")[0] == "guidance"
        ):
            raise ValueError("WP04 fixture path or contents are outside the declared observation scope")
    submission = (
        {
            "check": "wp04_submission_v1",
            "case_id": "wp04-" + spec["id"].split("-")[2],
            "text": "one valid structured diagnosis for the selected case supplied",
        }
        if spec["id"].endswith("-v7")
        else {
            "check": "text_regex",
            "pattern": r"(?m)^```json\s*$",
            "text": "explicit structured diagnosis block supplied",
        }
    )
    expected = [
        {"check": "no_workspace_changes", "text": "recorded evidence was not changed"},
        {"check": "no_new_commits", "text": "no commits were created"},
        submission,
        MANUAL_CHECK,
    ]
    if spec["checks"] != expected:
        raise ValueError("WP04 checks differ from the admitted historical or corrected contract")
    problems = catalog.validate_scenario(spec)
    if problems:
        raise ValueError("; ".join(problems))
    return spec


def load_wp04_case(path: Path) -> dict[str, Any]:
    # Feed one archive directly to libyaml; do not materialize another ~1GB text copy
    # or load the whole catalog alongside it. Each CLI process owns one selected case.
    opener = gzip.open if path.name.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8") as source:
        spec = yaml.load(source, Loader=getattr(yaml, "CSafeLoader", yaml.SafeLoader))
    return validate_wp04_case(spec)


def require_subscription_auth(path: Path) -> None:
    """Verify authentication kind without printing or retaining credential values."""
    auth = json.loads(path.read_text(encoding="utf-8"))
    if (
        not isinstance(auth, dict)
        or auth.get("auth_mode") != "chatgpt"
        or not isinstance(auth.get("tokens"), dict)
        or auth.get("OPENAI_API_KEY")
    ):
        raise ValueError("WP04 requires the approved ChatGPT subscription login, without an API key")
