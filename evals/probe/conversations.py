"""Opt-in incident conversations: frozen releases outside the candidate workspace.

Only exact authored CHECK lines select telemetry. Advice is never semantically classified here.
Every released input and cumulative judge context is saved independently of the candidate's files.
"""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from . import constants, layout

PROFILE = "incident-v1"


def enabled(spec: Mapping[str, Any]) -> bool:
    value = spec.get("conversation")
    return isinstance(value, dict) and value.get("profile") == PROFILE


def count(spec: Mapping[str, Any]) -> int:
    return 1 + len(spec.get("followups", []))


def folders(run: Path, spec: Mapping[str, Any]) -> list[Path]:
    if enabled(spec):
        return [run, *(run / "invocations" / f"{i:03}" for i in range(2, count(spec) + 1))]
    return [run, run / "followup"] if spec.get("followups") else [run]


def saved_folders(run: Path) -> list[Path]:
    """Read only a canonical index; never follow arbitrary evidence paths from disk."""
    manifest = layout.read_object(run / "conversation.json")
    if manifest is not None:
        n = manifest.get("invocations")
        if manifest.get("profile") != PROFILE or type(n) is not int or not 2 <= n <= 32:
            raise ValueError("invalid incident conversation index")
        return [run, *(run / "invocations" / f"{i:03}" for i in range(2, n + 1))]
    return [run, run / "followup"] if (run / "followup").is_dir() else [run]


def turn_spec(spec: Mapping[str, Any], index: int) -> Mapping[str, Any]:
    return {**spec, "_conversation_turn": index} if enabled(spec) else spec


def expected_helper(spec: Mapping[str, Any], index: int) -> str | None:
    return spec["conversation"]["helpers"][index] if enabled(spec) else spec.get("helper")


def normalize(request: str) -> str:
    return " ".join(request.casefold().split())


def resolve(update: str | Mapping[str, Any], response: str) -> dict[str, str]:
    if isinstance(update, str):
        return {"selected": "fixed", "text": update}
    requests = re.findall(r"^CHECK:[ \t]*(.*?)[ \t]*$", response, re.MULTILINE | re.IGNORECASE)
    if len(requests) != 1 or not requests[0]:
        return {"selected": "ambiguous", "text": update["ambiguous"]}
    request = normalize(requests[0])
    for option in update["request_map"]:
        if request in {normalize(form) for form in option["requests"]}:
            return {"selected": option["id"], "text": option["text"]}
    return {"selected": "unavailable", "text": update["unavailable"]}


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def release(
    folder: Path,
    index: int,
    selected: Mapping[str, str],
    messages: Sequence[Mapping[str, str]],
    response: str,
    files: Mapping[str, str],
) -> None:
    text = selected["text"]
    (folder / "input.md").write_text(text, encoding="utf-8", newline="\n")
    layout.write_json(
        folder / "release.json",
        {
            "invocation": index + 1,
            "selected": selected["selected"],
            "input_sha256": digest(text),
            "trigger_response_sha256": digest(response) if index else None,
        },
    )
    layout.write_json(folder / "judge-context.json", judge_context(index, messages, files))


def judge_context(index: int, messages: Sequence[Mapping[str, str]], files: Mapping[str, str]) -> dict[str, Any]:
    current = "." if index == 0 else f"invocations/{index + 1:03}"
    traces = ["stdout.jsonl", *(f"invocations/{i:03}/stdout.jsonl" for i in range(2, index + 2))]
    return {
        "profile": PROFILE,
        "invocation": index + 1,
        "messages": list(messages),
        "available_files": dict(files),
        "visible_traces": [posixpath.relpath(path, current) for path in traces],
        "response": "response.md",
        "assessment_scope": "then-visible evidence only; semantic review pending",
    }


def problems(spec: Mapping[str, Any], where: str) -> list[str]:
    """Shape-check all opt-in values before a trial can start."""
    from . import catalog  # noqa: PLC0415 -- catalog calls this validator

    issue: list[str] = []
    config = spec.get("conversation")
    if not isinstance(config, dict) or config.get("profile") != PROFILE:
        return [f"{where}: conversation.profile must be {PROFILE}"]
    if set(config) - {"profile", "helpers", "turn_graders", "partition", "manual_review"}:
        issue.append(f"{where}: unknown incident conversation configuration")
    followups = spec.get("followups")
    if not isinstance(followups, list) or not 1 <= len(followups) <= 31:
        return [*issue, f"{where}: incident conversation needs 1..31 followups"]
    helpers = config.get("helpers")
    if (
        not isinstance(helpers, list)
        or len(helpers) != count(spec)
        or any(
            h is not None
            and (
                not isinstance(h, str)
                or not catalog.SLUG.fullmatch(h)
                or not (constants.ROOT / "agents" / f"{h}.md").is_file()
            )
            for h in helpers
        )
    ):
        issue.append(f"{where}: helpers must declare null or a canonical helper for every invocation")
    if config.get("partition") not in ("development", "held-out") or config.get("manual_review") != "pending":
        issue.append(f"{where}: partition must be development or held-out; manual_review remains pending")
    graders = config.get("turn_graders", [[] for _ in range(count(spec))])
    if not isinstance(graders, list) or len(graders) != count(spec) or not all(isinstance(g, list) for g in graders):
        issue.append(f"{where}: turn_graders must have one list per invocation")
    else:
        for entries in graders:
            if any(isinstance(g, dict) and g.get("type") == "rubric" for g in entries):
                issue.append(
                    f"{where}: incident semantic rubric requires a calibrated then-visible judge; use manual review"
                )
            elif entries:
                issue += catalog._grader_problems({"graders": entries}, where)
    if spec.get("graders") or spec.get("helper"):
        issue.append(f"{where}: declare incident graders and helpers per invocation")
    for update in followups:
        if isinstance(update, str) and update.strip():
            continue
        if not isinstance(update, dict) or set(update) != {"request_map", "ambiguous", "unavailable"}:
            issue.append(f"{where}: followup must be non-empty text or a frozen request_map")
            continue
        if not all(isinstance(update[k], str) and update[k].strip() for k in ("ambiguous", "unavailable")):
            issue.append(f"{where}: branch ambiguous/unavailable text must be non-empty")
        options = update["request_map"]
        if not isinstance(options, list) or len(options) < 2:
            issue.append(f"{where}: branch must have at least two useful checks")
            continue
        ids: set[str] = set()
        forms: set[str] = set()
        for option in options:
            if not isinstance(option, dict) or set(option) != {"id", "requests", "text"}:
                issue.append(f"{where}: malformed request-map option")
                continue
            ident, requests, text = option["id"], option["requests"], option["text"]
            if not isinstance(ident, str) or ident in ids or ident in {"fixed", "ambiguous", "unavailable"}:
                issue.append(f"{where}: branch ids must be unique, non-reserved strings")
            elif not catalog.SLUG.fullmatch(ident):
                issue.append(f"{where}: branch id must be a slug")
            else:
                ids.add(ident)
            if not isinstance(text, str) or not text.strip():
                issue.append(f"{where}: branch observation must be non-empty")
            if not isinstance(requests, list) or not requests:
                issue.append(f"{where}: branch requests must be a non-empty list")
                continue
            for form in requests:
                if not isinstance(form, str) or not form.strip() or "\n" in form or normalize(form) in forms:
                    issue.append(f"{where}: branch aliases must be unique non-empty single lines")
                else:
                    forms.add(normalize(form))
    return issue


def replay_problem(run: Path, spec: Mapping[str, Any], initial: str) -> str | None:
    """Bind saved releases to frozen choices and actual preceding responses, without future context."""
    manifest = layout.read_object(run / "conversation.json")
    if manifest != {"profile": PROFILE, "invocations": count(spec), "guard_scope": "per invocation"}:
        return "incident conversation index missing or differs from scenario"
    invocation_root = run / "invocations"
    expected_names = {f"{i:03}" for i in range(2, count(spec) + 1)}
    if invocation_root.is_dir() and any(p.name not in expected_names for p in invocation_root.iterdir()):
        return "incident conversation contains an unexpected invocation"
    messages: list[dict[str, str]] = []
    previous = ""
    from . import tracing  # noqa: PLC0415 -- tracing imports this module

    for index, folder in enumerate(folders(run, spec)):
        if not (folder / "invocation.json").is_file():
            break  # native boundary replay distinguishes budget exhaustion from missing evidence
        selected = (
            {"selected": "initial", "text": initial} if index == 0 else resolve(spec["followups"][index - 1], previous)
        )
        messages.append({"role": "user", "content": selected["text"]})
        try:
            metadata = json.loads((folder / "invocation.json").read_text(encoding="utf-8"))
            argv = metadata["argv"]
            if argv[argv.index("-p") + 1] != selected["text"]:
                return "incident invocation prompt differs from released input"
            if (folder / "input.md").read_text(encoding="utf-8") != selected["text"]:
                return "incident released input missing or changed"
            expected = {
                "invocation": index + 1,
                "selected": selected["selected"],
                "input_sha256": digest(selected["text"]),
                "trigger_response_sha256": digest(previous) if index else None,
            }
            if layout.read_object(folder / "release.json") != expected:
                return "incident branch release differs from frozen evidence"
            context = layout.read_object(folder / "judge-context.json")
            if context != judge_context(index, messages, spec["fixture"]["files"]):
                return "incident then-visible judge context missing or changed"
            previous = tracing.parse_trace(folder / "stdout.jsonl").result_text
            if (folder / "response.md").read_text(encoding="utf-8") != previous:
                return "incident saved response differs from its invocation trace"
        except (OSError, ValueError, KeyError, TypeError):
            return "incident released input evidence missing or invalid"
        messages.append({"role": "assistant", "content": previous})
    return None
