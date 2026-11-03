"""Opt-in incident conversations: frozen releases outside the candidate workspace.

Only exact authored CHECK lines select telemetry. Advice is never semantically classified here.
Every released input and cumulative judge context is saved independently of the candidate's files.
"""

from __future__ import annotations

import hashlib
import json
import posixpath
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import constants, layout, specs, tracing

PROFILE = constants.INCIDENT_PROFILE


def enabled(spec: Mapping[str, Any]) -> bool:
    value = spec.get("conversation")
    return isinstance(value, dict) and value.get("profile") == PROFILE


def count(spec: Mapping[str, Any]) -> int:
    return 1 + len(spec.get("followups", []))


def folders(run: Path, spec: Mapping[str, Any]) -> list[Path]:
    if enabled(spec):
        return [run, *(run / "invocations" / f"{i:03}" for i in range(2, count(spec) + 1))]
    return [run, run / "followup"] if spec.get("followups") else [run]


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
                or not specs.SLUG.fullmatch(h)
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
                issue += specs.grader_problems({"graders": entries}, where)
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
            elif not specs.SLUG.fullmatch(ident):
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


@dataclass(frozen=True)
class Released:
    """What one incident invocation was released and answered, as a replay reads it: from the run's
    files for a run saved before its evidence carried them, from its evidence after. A field that is
    None was missing or unreadable."""

    invoked: bool  # the invocation ran: its invocation.json was written
    prompt: str | None  # the `-p` argument it ran with
    input_sha256: str | None  # digest of the released input.md text
    release: Mapping[str, Any] | None  # its release.json
    judge_context_sha256: str | None  # canonical digest of its judge-context.json
    response: str | None  # its trace's final text
    response_text_sha256: str | None  # digest of the saved response.md text


def universal_newlines(text: str) -> str:
    """Text as reading it back with universal newlines gives it: CRLF and a lone CR become LF."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def canonical_sha256(value: object) -> str:
    """A JSON value's digest, independent of key order: how a judge context is compared."""
    return digest(json.dumps(value, sort_keys=True, ensure_ascii=False))


def replay_problem(run: Path, spec: Mapping[str, Any], initial: str) -> str | None:
    """Bind saved releases to frozen choices and actual preceding responses, without future context,
    reading a saved run's files."""
    invocation_root = run / "invocations"
    expected_names = {f"{i:03}" for i in range(2, count(spec) + 1)}
    manifest = layout.read_object(run / "conversation.json")
    if (
        manifest == manifest_for(spec)
        and invocation_root.is_dir()
        and any(p.name not in expected_names for p in invocation_root.iterdir())
    ):
        return "incident conversation contains an unexpected invocation"
    return replay_releases(manifest, [released_from(folder) for folder in folders(run, spec)], spec, initial)


def manifest_for(spec: Mapping[str, Any]) -> dict[str, Any]:
    """The conversation index an incident conversation writes."""
    return {"profile": PROFILE, "invocations": count(spec), "guard_scope": "per invocation"}


def released_from(folder: Path) -> Released:
    """One invocation's release facts as its folder keeps them; a missing or unreadable one is None."""
    if not (folder / "invocation.json").is_file():
        return Released(False, None, None, None, None, None, None)

    def attempt(read: Callable[[], Any]) -> Any:
        try:
            return read()
        except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError):
            return None

    def prompt() -> str:
        argv = json.loads((folder / "invocation.json").read_text(encoding="utf-8"))["argv"]
        return str(argv[argv.index("-p") + 1])

    context = layout.read_object(folder / "judge-context.json")
    return Released(
        True,
        attempt(prompt),
        attempt(lambda: digest((folder / "input.md").read_text(encoding="utf-8"))),
        layout.read_object(folder / "release.json"),
        canonical_sha256(context) if context is not None else None,
        attempt(lambda: tracing.parse_trace(folder / "stdout.jsonl").result_text),
        attempt(lambda: digest((folder / "response.md").read_text(encoding="utf-8"))),
    )


def replay_releases(
    manifest: object, released: Sequence[Released], spec: Mapping[str, Any], initial: str
) -> str | None:
    """Bind each invocation's release to the frozen choice the preceding response selects, and its
    then-visible judge context to the conversation so far: the incident replay, over files or evidence."""
    if manifest != manifest_for(spec):
        return "incident conversation index missing or differs from scenario"
    messages: list[dict[str, str]] = []
    previous = ""
    for index, item in enumerate(released):
        if not item.invoked:
            break  # native boundary replay distinguishes budget exhaustion from missing evidence
        selected = (
            {"selected": "initial", "text": initial} if index == 0 else resolve(spec["followups"][index - 1], previous)
        )
        messages.append({"role": "user", "content": selected["text"]})
        if item.prompt is None:
            return "incident released input evidence missing or invalid"
        if item.prompt != selected["text"]:
            return "incident invocation prompt differs from released input"
        if item.input_sha256 is None:
            return "incident released input evidence missing or invalid"
        if item.input_sha256 != digest(selected["text"]):
            return "incident released input missing or changed"
        expected = {
            "invocation": index + 1,
            "selected": selected["selected"],
            "input_sha256": digest(selected["text"]),
            "trigger_response_sha256": digest(previous) if index else None,
        }
        if item.release != expected:
            return "incident branch release differs from frozen evidence"
        if item.judge_context_sha256 != canonical_sha256(judge_context(index, messages, spec["fixture"]["files"])):
            return "incident then-visible judge context missing or changed"
        if item.response is None or item.response_text_sha256 is None:
            return "incident released input evidence missing or invalid"
        previous = item.response
        # response.md is read back with universal newlines, so the trace's text is compared the same way;
        # a runner before the fix wrote it with Windows newline translation, which turned CRLF into CR CR LF.
        saved_forms = {digest(universal_newlines(previous)), digest(universal_newlines(previous.replace("\n", "\r\n")))}
        if item.response_text_sha256 not in saved_forms:
            return "incident saved response differs from its invocation trace"
        messages.append({"role": "assistant", "content": previous})
    return None
