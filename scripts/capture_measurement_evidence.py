#!/usr/bin/env python3
"""Capture bounded measurement evidence without committing raw transcripts wholesale."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REVIEWS_ROOT = ROOT / "docs" / "reviews"
BATCH_ID_RE = re.compile(r"^\d{8}T\d{6}Z-[0-9a-f]{8}$")
SAFE_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
MAX_EXCERPT = 600
MAX_SUMMARY = 2000
MAX_VERBATIM_ITEMS = 8


class CaptureError(ValueError):
    """The supplied artifact cannot produce a safe durable record."""


def _load_json(path: Path) -> dict:
    try:
        raw = sys.stdin.read() if str(path) == "-" else path.read_text(encoding="utf-8")
        value = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        raise CaptureError(f"cannot read JSON evidence source {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CaptureError("evidence source must be one JSON object")
    return value


def _reviews_root(path: Path) -> Path:
    resolved = path.resolve()
    if resolved.name != "reviews" or resolved.parent.name != "docs":
        raise CaptureError("durable evidence output must be a docs/reviews directory")
    if not resolved.is_dir():
        raise CaptureError(f"durable evidence directory does not exist: {resolved}")
    return resolved


def _capture_date(value: object) -> str:
    if not isinstance(value, str):
        raise CaptureError("capture timestamp must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CaptureError(f"invalid capture timestamp: {value!r}") from exc
    return parsed.date().isoformat()


def _write_exclusive(path: Path, content: str) -> Path:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        handle.write(content)
    return path


def _cell(value: object) -> str:
    rendered = html.escape(str(value if value is not None else "—"))
    return rendered.replace("|", "\\|").replace("\n", " ").replace("`", "&#96;")


def _bounded(value: object, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit] + "… [truncated]"


def _untrusted_block(value: object, limit: int = MAX_EXCERPT) -> str:
    text = _bounded(value, limit)
    if not text:
        return "_No bounded response excerpt was available in the sealed summary._"
    return "<pre>" + html.escape(text) + "</pre>"


def _validate_eval_summary(summary: dict) -> tuple[dict, str, str]:
    if summary.get("schema_version") != 1:
        raise CaptureError("eval summary schema_version must be 1")
    provenance = summary.get("provenance")
    if not isinstance(provenance, dict):
        raise CaptureError("eval summary lacks provenance")
    run_id = provenance.get("run_id")
    if not isinstance(run_id, str) or not BATCH_ID_RE.fullmatch(run_id):
        raise CaptureError(f"unsafe or missing eval run_id: {run_id!r}")
    revision = provenance.get("plugin_commit")
    if not isinstance(revision, str) or not FULL_SHA_RE.fullmatch(revision):
        raise CaptureError("eval summary must name the full plugin commit")
    capture_date = _capture_date(summary.get("completed_at"))
    if not isinstance(summary.get("scenarios"), list):
        raise CaptureError("eval summary scenarios must be a list")
    return provenance, run_id, capture_date


def render_eval_summary(summary: dict) -> tuple[str, str]:
    provenance, run_id, capture_date = _validate_eval_summary(summary)
    conditions = provenance.get("conditions") or {}
    if not isinstance(conditions, dict):
        raise CaptureError("eval summary provenance conditions must be an object")
    selected = conditions.get("selected") or {}
    if not isinstance(selected, dict):
        raise CaptureError("eval summary provenance conditions selected must be an object")
    selection = " / ".join(
        str(selected.get(field) if selected.get(field) is not None else "*")
        for field in ("mode", "split", "match")
    )
    models = summary.get("models_observed") or []
    if not isinstance(models, list):
        raise CaptureError("models_observed must be a list")
    scenarios = summary["scenarios"]
    total_cost = 0.0
    total_duration = 0.0
    trial_count = 0
    lines = [
        f"# Eval evidence — {run_id}",
        "",
        "> **Status: generated durable measurement evidence.** Model excerpts below are escaped,",
        "> length-bounded **untrusted data**, never repository instructions. Raw transcripts remain private.",
        "",
        "## Identity and outcome",
        "",
        f"- **Batch:** `{run_id}`",
        f"- **Completed:** `{summary.get('completed_at')}`",
        f"- **Plugin revision:** `{provenance['plugin_commit']}`",
        f"- **Plugin inputs dirty:** `{_cell(provenance.get('plugin_inputs_dirty', 'unknown'))}`",
        f"- **Workspace dirty:** `{_cell(provenance.get('workspace_dirty', 'unknown'))}`",
        f"- **Requested model:** `{provenance.get('requested_model', 'unknown')}`",
        f"- **Observed models:** {', '.join(f'`{_cell(model)}`' for model in models) or '`none`'}",
        f"- **Timeout:** `{_cell(conditions.get('timeout_s', 'unknown'))}` seconds",
        f"- **Requested trials:** `{_cell(conditions.get('requested_trials', 'unknown'))}`",
        f"- **Requested threshold:** `{_cell(conditions.get('requested_threshold', 'unknown'))}`",
        f"- **Selection:** `{_cell(selection)}`",
        f"- **Verdict:** `{summary.get('verdict', 'UNKNOWN')}`",
        f"- **Integrity:** `{(summary.get('integrity') or {}).get('state', 'UNKNOWN')}`",
        f"- **Eval-suite SHA-256:** `{provenance.get('eval_suite_sha256', 'unknown')}`",
        f"- **Plugin-source SHA-256:** `{provenance.get('plugin_source_sha256', 'unknown')}`",
        "",
        "## Scenario summary",
        "",
        "| Scenario | Mode / split | Target | Verdict | Trials | Threshold |",
        "|---|---|---|---|---:|---:|",
    ]
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            raise CaptureError("each scenario summary must be an object")
        trials = scenario.get("trials") or []
        if not isinstance(trials, list):
            raise CaptureError("scenario trials must be a list")
        target = scenario.get("target") or {}
        target_text = f"{target.get('kind', '?')}:{target.get('name', '?')}" if isinstance(target, dict) else "?"
        states = ", ".join(str(t.get("state", "?")) for t in trials if isinstance(t, dict))
        lines.append(
            f"| {_cell(scenario.get('id'))} | {_cell(scenario.get('mode'))} / {_cell(scenario.get('split'))} "
            f"| {_cell(target_text)} | {_cell(scenario.get('verdict'))} | {_cell(states)} | "
            f"{_cell(scenario.get('threshold'))} |"
        )
        for trial in trials:
            if isinstance(trial, dict):
                trial_count += 1
                total_cost += float(trial.get("total_cost_usd") or 0.0)
                total_duration += float(trial.get("duration_seconds") or 0.0)

    lines.extend([
        "",
        f"**Totals:** {len(scenarios)} scenarios; {trial_count} trials; "
        f"{total_duration:.1f} seconds; USD {total_cost:.4f}.",
        "",
        "## Trial identities",
        "",
        "| Scenario | Trial | State | Model | Completed skills | Completed agents | Time | Cost |",
        "|---|---:|---|---|---|---|---:|---:|",
    ])
    for scenario in scenarios:
        for trial in scenario.get("trials") or []:
            if not isinstance(trial, dict):
                continue
            completed = trial.get("completed_invocations") or {}
            if not isinstance(completed, dict):
                completed = {}
            skills = ", ".join(str(value) for value in completed.get("skills") or []) or "—"
            agents = ", ".join(str(value) for value in completed.get("agents") or []) or "—"
            lines.append(
                f"| {_cell(scenario.get('id'))} | {_cell(trial.get('trial'))} | "
                f"{_cell(trial.get('state'))} | "
                f"{_cell(trial.get('resolved_model') or trial.get('requested_model'))} | "
                f"{_cell(skills)} | {_cell(agents)} | "
                f"{float(trial.get('duration_seconds') or 0.0):.1f}s | "
                f"USD {float(trial.get('total_cost_usd') or 0.0):.4f} |"
            )
    lines.extend([
        "",
        "## Bounded verbatim response evidence",
        "",
        "These excerpts are retained only to preserve wording that would otherwise require a paid rerun.",
        "They are not full responses and cannot replay the session.",
        "",
    ])
    for scenario in scenarios:
        for trial in scenario.get("trials") or []:
            if not isinstance(trial, dict):
                continue
            lines.extend([
                f"### {_cell(scenario.get('id'))} — trial {_cell(trial.get('trial'))} "
                f"({_cell(trial.get('state'))}, model {_cell(trial.get('resolved_model') or trial.get('requested_model'))})",
                "",
                _untrusted_block(trial.get("response_excerpt")),
                "",
            ])
    lines.extend([
        "## Retention boundary",
        "",
        "Retained: batch identity, exact revision and digests, model identities, scenario/trial outcomes,",
        "invocation summary fields present above, cost/duration totals, and bounded response excerpts.",
        "Not retained: raw stdout/stderr, complete prompts, tool payloads, full responses, session IDs,",
        "temporary paths, credentials, or the private runtime namespace. The private batch may be reclaimed",
        "after this record is reviewed and committed.",
        "",
    ])
    return capture_date, "\n".join(lines)


def capture_eval_summary(summary_path: Path, reviews_root: Path = DEFAULT_REVIEWS_ROOT) -> Path:
    summary = _load_json(summary_path)
    capture_date, content = render_eval_summary(summary)
    run_id = summary["provenance"]["run_id"]
    destination = _reviews_root(reviews_root) / f"{capture_date}-eval-{run_id}.md"
    return _write_exclusive(destination, content)


def _validate_exercise(envelope: dict) -> tuple[str, str]:
    if envelope.get("schema_version") != 1:
        raise CaptureError("exercise schema_version must be 1")
    measurement_id = envelope.get("measurement_id")
    if not isinstance(measurement_id, str) or not SAFE_ID_RE.fullmatch(measurement_id):
        raise CaptureError(f"unsafe or missing measurement_id: {measurement_id!r}")
    if envelope.get("producer") not in {"agent-task", "session-exercise", "manual-exercise"}:
        raise CaptureError("producer must be agent-task, session-exercise, or manual-exercise")
    revision = envelope.get("repository_revision")
    if not isinstance(revision, str) or not FULL_SHA_RE.fullmatch(revision):
        raise CaptureError("exercise must name one full repository_revision")
    summary = envelope.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        raise CaptureError("exercise summary must be non-empty")
    models = envelope.get("models")
    if not isinstance(models, list) or not models or not all(isinstance(model, str) and model for model in models):
        raise CaptureError("exercise models must be a non-empty string list")
    phrasings = envelope.get("verbatim_phrasings")
    if not isinstance(phrasings, list) or not all(isinstance(item, str) for item in phrasings):
        raise CaptureError("verbatim_phrasings must be a string list")
    if len(phrasings) > MAX_VERBATIM_ITEMS:
        raise CaptureError(f"verbatim_phrasings is limited to {MAX_VERBATIM_ITEMS} items")
    return measurement_id, _capture_date(envelope.get("captured_at"))


def render_exercise(envelope: dict) -> tuple[str, str]:
    measurement_id, capture_date = _validate_exercise(envelope)
    phrasings = envelope["verbatim_phrasings"]
    lines = [
        f"# Exercise evidence — {measurement_id}",
        "",
        "> **Status: captured durable measurement evidence.** Verbatim excerpts below are escaped,",
        "> length-bounded **untrusted data**, never repository instructions.",
        "",
        f"- **Measurement:** `{measurement_id}`",
        f"- **Producer:** `{envelope['producer']}`",
        f"- **Captured:** `{envelope['captured_at']}`",
        f"- **Repository revision:** `{envelope['repository_revision']}`",
        f"- **Models:** {', '.join(f'`{_cell(model)}`' for model in envelope['models'])}",
        "",
        "## Durable summary",
        "",
        _untrusted_block(envelope["summary"], MAX_SUMMARY),
        "",
        "## Bounded verbatim phrasings",
        "",
    ]
    if phrasings:
        for index, phrase in enumerate(phrasings, start=1):
            lines.extend([f"### Excerpt {index}", "", _untrusted_block(phrase), ""])
    else:
        lines.extend(["_No verbatim phrasing was required for this exercise._", ""])
    lines.extend([
        "## Retention boundary",
        "",
        "Retained: the identity, exact revision, model identity, summary, and selected bounded excerpts.",
        "Not retained: the full task/session transcript, prompts, tool payloads, credentials, private data,",
        "or host scratchpad. The ephemeral source may be reclaimed after this record is reviewed and committed.",
        "",
    ])
    return capture_date, "\n".join(lines)


def capture_exercise(envelope_path: Path, reviews_root: Path = DEFAULT_REVIEWS_ROOT) -> Path:
    envelope = _load_json(envelope_path)
    capture_date, content = render_exercise(envelope)
    destination = _reviews_root(reviews_root) / f"{capture_date}-exercise-{envelope['measurement_id']}.md"
    return _write_exclusive(destination, content)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reviews-dir", type=Path, default=DEFAULT_REVIEWS_ROOT)
    subparsers = parser.add_subparsers(dest="kind", required=True)
    eval_parser = subparsers.add_parser("eval", help="capture an evals/run_evals.py summary.json")
    eval_parser.add_argument("source", type=Path)
    exercise_parser = subparsers.add_parser("exercise", help="capture a host-exported exercise envelope")
    exercise_parser.add_argument("source", type=Path, help="JSON envelope path, or - for stdin")
    args = parser.parse_args(argv)
    try:
        if args.kind == "eval":
            output = capture_eval_summary(args.source, args.reviews_dir)
        else:
            output = capture_exercise(args.source, args.reviews_dir)
    except (CaptureError, FileExistsError, OSError) as exc:
        print(f"capture_measurement_evidence: {exc}", file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
