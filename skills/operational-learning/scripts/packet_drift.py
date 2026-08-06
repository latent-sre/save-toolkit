#!/usr/bin/env python3
"""Report pending knowledge-update packets whose ground has moved since they were written.

WHY THIS EXISTS. A `proposed` or `blocked` disposition names an owner and a next action, but
nothing observes whether that action ever happened. Such a packet can therefore outlive the work
it describes: the runbook it asked for may already exist, or the configuration it was reasoning
about may have changed underneath it. Two cheap, reviewable signals say "look again":

  * DRIFT - a repository evidence locator the packet was built on has been committed to since
    `target.revision`.
  * FRESHNESS - a v3 `review_at` or `expires_at` deadline has passed.

Only packets with at least one pending disposition are watched. A packet whose outcomes are all
prepared, duplicate, or not applicable has already said its last word, and re-reporting it would
train the reader to ignore this tool.

WHY THE BASELINE IS EXACT. `target.revision` is a full Git object ID pinned inside the packet, so
this asks Git for an exact graph range rather than a timestamp window. Reachability is the
contract: a change authored before the packet can still become reachable afterward through a
merge, and a date filter would silently miss it.

DELIBERATELY ADVISORY BY DEFAULT. Drift is evidence a human should look, not proof anything is
wrong - an unrelated commit to a shared file is the common case, and a live gate on a judgement
call trains the shape rather than the work. The default exit code is 0 so this can be wired into
an existing pipeline without turning a prompt into a blocker. `--fail-on-drift` exists for a
caller who wants a hard gate. An unreadable repository or packet is different in kind: it exits 2,
because reporting "clean" for something never inspected is the one failure this must not have.

WHAT IT IS NOT. This finds later activity; it does not decide whether that activity satisfied the
packet. It also never proves an absence: a locator it cannot safely resolve, or that Git has never
tracked, is reported as unwatchable rather than dropped. An empty log for a path Git never knew
about is not evidence of no drift.

Pure standard library; git is the only external call.

    python3 packet_drift.py PACKET.json --root .                  # advisory report
    python3 packet_drift.py PACKET.json --root . --fail-on-drift  # exit 1 on any finding
    python3 packet_drift.py PACKET.json --root . --json           # machine-readable
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

# The validator owns the packet vocabulary and the repository-path safety rule. Keeping a second
# copy of either here would let this watch quietly stop matching the contract it reports against.
import knowledge_update

PENDING_STATUSES = {"proposed", "blocked"}
# Bounds the machine-readable payload without hiding the cut: past this many commits the finding
# sets commits_truncated. The human report shows fewer still and says how many it left out.
MAX_PAYLOAD_COMMITS = 50
MAX_PRINTED_COMMITS = 5
MAX_PRINTED_TEXT = 120
# Packet text reaches an operator console or CI log. `locator` only has to satisfy
# `_string(maximum=2048)` to pass the packet validator — no control-character rejection — so a
# *valid* packet can carry a newline plus this tool's own clean-sweep sentence and forge it into
# the report, or an ESC sequence that rewrites lines already printed (CWE-117/CWE-150).
CONTROL_CHARACTER_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")
# The first knowledge-update version carrying a freshness object; earlier versions have none.
FRESHNESS_SCHEMA_VERSION = 3
# Repository evidence is conventionally cited as `path` or `path:line` / `path:line-line`.
# Strip only that trailing line reference; anything else is left for the safety check to judge.
LINE_REFERENCE_RE = re.compile(r":\d+(?:-\d+)?$")


class PacketDriftError(RuntimeError):
    """The repository or a packet could not be read. Never swallowed: an empty log and a broken
    repository look identical to the caller, and conflating them turns --fail-on-drift into a
    false green."""


def git(root: Path, *args: str) -> str:
    """Run one read-only Git command under the validator's hardened environment.

    `--literal-pathspecs` is load-bearing, not cosmetic: evidence locators are untrusted packet
    text, and `_safe_relative_path` accepts `*`, `[a-z]`, and `:(glob)` because they are legal
    path characters. Without this flag Git treats such a locator as a wildcard pathspec and
    reports commits to files the packet never cited as though they were its own evidence.
    """

    try:
        result = subprocess.run(
            ["git", "-C", str(root), "--literal-pathspecs", *args],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env=knowledge_update._git_environment(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PacketDriftError(f"cannot run git in {root}: {exc}") from exc
    if result.returncode != 0:
        raise PacketDriftError(f"git {' '.join(args)} failed in {root}: {result.stderr.strip()}")
    return result.stdout.strip()


def git_ok(root: Path, *args: str) -> bool:
    """Run a Git predicate whose non-zero exit is an answer rather than a failure."""

    try:
        git(root, *args)
    except PacketDriftError:
        return False
    return True


def display(value: object, limit: int = MAX_PRINTED_TEXT) -> str:
    """Render untrusted packet text safely for a terminal or CI log.

    Control characters become visible escapes rather than terminal behaviour, and the result is
    capped so one locator cannot flood the report. JSON mode needs none of this — `json.dumps`
    escapes control characters already.
    """

    text = CONTROL_CHARACTER_RE.sub(
        lambda match: f"\\x{ord(match.group()):02x}", str(value)
    )
    return text if len(text) <= limit else f"{text[:limit]}..."


def is_known_to_git(root: Path, relative: str) -> bool:
    """Whether Git can report history for this exact literal path.

    A path Git has never tracked produces the same empty log as a path nothing has touched. Left
    undistinguished, the second reads as "checked, clean" — the false green this watch exits 2 to
    avoid everywhere else. A path deleted since the baseline still has history, so removing the
    file the packet reasoned about stays drift rather than becoming unwatchable.

    History is the only authority here. Presence in the working tree is not: an untracked or
    ignored file exists on disk yet yields the same empty log, so trusting the filesystem would
    reopen the hole this function exists to close.
    """

    return bool(git(root, "log", "-1", "--format=%h", "--", relative))


def verify_repository(root: Path) -> None:
    """Fail loudly on a root Git cannot read, so that a later empty log is a real answer."""

    git(root, "rev-parse", "--git-dir")


def evidence_paths(packet: Mapping[str, object]) -> tuple[list[str], list[str]]:
    """Split repository evidence locators into watchable paths and unwatchable ones.

    A locator is free text from an untrusted packet. Only a normalized repository-relative path
    is ever handed to Git; everything else is returned so the caller can report it rather than
    imply it was checked and clean.
    """

    watchable: list[str] = []
    unwatchable: list[str] = []
    records = packet.get("evidence")
    if not isinstance(records, list):
        raise PacketDriftError("packet evidence must be an array")
    for record in records:
        if not isinstance(record, Mapping) or record.get("kind") != "repository":
            continue
        locator = record.get("locator")
        if not isinstance(locator, str) or not locator.strip():
            unwatchable.append(str(locator))
            continue
        candidate = LINE_REFERENCE_RE.sub("", locator)
        try:
            knowledge_update._safe_relative_path(candidate, "locator")
        except knowledge_update.KnowledgeUpdateValidationError:
            unwatchable.append(locator)
            continue
        if candidate not in watchable:
            watchable.append(candidate)
    return watchable, unwatchable


def pending_artifacts(packet: Mapping[str, object]) -> list[str]:
    dispositions = packet.get("dispositions")
    if not isinstance(dispositions, list):
        raise PacketDriftError("packet dispositions must be an array")
    pending = []
    for disposition in dispositions:
        if isinstance(disposition, Mapping) and disposition.get("status") in PENDING_STATUSES:
            pending.append(str(disposition.get("artifact")))
    return pending


def freshness_findings(packet: Mapping[str, object], now: datetime) -> list[str]:
    """Passed deadlines, if this packet version carries any. v1 and v2 have no freshness object."""

    freshness = packet.get("freshness")
    # v1 and v2 carry no freshness object at all; only a version that promises one may be judged
    # against it. Keying on the declared version rather than on shape means a null, mistyped, or
    # absent freshness on a v3 packet is malformed input — reported like an unparseable deadline
    # string, never silently treated as "no deadlines set".
    if packet.get("schema_version") != FRESHNESS_SCHEMA_VERSION:
        return []
    if not isinstance(freshness, Mapping):
        raise PacketDriftError(
            f"packet declares schema_version {FRESHNESS_SCHEMA_VERSION} but its freshness is not "
            "an object"
        )
    findings = []
    for field, label in (("expires_at", "expired"), ("review_at", "review due")):
        deadline = freshness.get(field)
        if deadline is None:
            continue
        if not isinstance(deadline, str):
            raise PacketDriftError(f"packet freshness.{field} must be a string or null")
        try:
            parsed = knowledge_update.parse_utc_timestamp(
                knowledge_update._timestamp(deadline, field)
            )
        except knowledge_update.KnowledgeUpdateValidationError as exc:
            raise PacketDriftError(f"packet freshness.{field} is unreadable: {exc}") from exc
        if parsed <= now:
            findings.append(f"{label} ({field} {deadline})")
    return findings


def inspect_packet(root: Path, path: Path, now: datetime) -> dict[str, object] | None:
    try:
        packet = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PacketDriftError(f"cannot read packet {path}: {exc}") from exc
    if not isinstance(packet, dict):
        raise PacketDriftError(f"packet {path} must be a JSON object")

    pending = pending_artifacts(packet)
    if not pending:
        return None

    target = packet.get("target")
    if not isinstance(target, Mapping):
        raise PacketDriftError(f"packet {path} has no target object")
    revision = target.get("revision")
    if not isinstance(revision, str) or not knowledge_update.GIT_REVISION_RE.fullmatch(revision):
        raise PacketDriftError(f"packet {path} target.revision is not a full Git object ID")
    # A revision this checkout has never seen means the caller pointed at the wrong repository.
    # Skipping it would report a clean result for a packet nobody compared against anything.
    try:
        object_type = git(root, "cat-file", "-t", revision)
    except PacketDriftError as exc:
        raise PacketDriftError(
            f"packet {path} target.revision {revision[:12]} is absent from {root}: {exc}"
        ) from exc
    if object_type != "commit":
        raise PacketDriftError(
            f"packet {path} target.revision {revision[:12]} is a {object_type}, not a commit"
        )
    # A HEAD that predates the baseline cannot show later activity: every `<rev>..HEAD` log is
    # empty for the same reason a clean tree is. The object exists, so `cat-file -t` above cannot
    # tell the two apart — without this, a stale or detached checkout gets a clean bill over a
    # tree that never contained the packet's baseline.
    if not git_ok(root, "merge-base", "--is-ancestor", revision, "HEAD"):
        raise PacketDriftError(
            f"packet {path} target.revision {revision[:12]} is not an ancestor of HEAD in {root}; "
            "this checkout cannot show what changed after it"
        )

    cited, unwatchable = evidence_paths(packet)
    # A locator Git has never heard of cannot be watched, however well-formed it looks.
    watchable = [path for path in cited if is_known_to_git(root, path)]
    unwatchable.extend(path for path in cited if path not in watchable)
    commits: list[dict[str, str]] = []
    drifted: list[str] = []
    revisions: set[str] = set()
    for target_path in watchable:
        # One commit touching several evidence paths is one change, not several: count distinct
        # SHAs so the report cannot imply more independent activity than actually happened.
        log = git(
            root,
            "log",
            f"{revision}..HEAD",
            "--full-history",
            "--format=%h %ad %s",
            "--date=short",
            "--",
            target_path,
        )
        lines = [line for line in log.splitlines() if line.strip()]
        if not lines:
            continue
        drifted.append(target_path)
        for line in lines:
            commits.append({"path": target_path, "commit": line})
            revisions.add(line.split(" ", 1)[0])

    stale = freshness_findings(packet, now)
    if not drifted and not stale and not unwatchable:
        return None
    return {
        "update_id": str(packet.get("update_id")),
        "packet": path.as_posix(),
        "pending_artifacts": pending,
        "baseline_revision": revision,
        "drifted_paths": drifted,
        # commit_count counts distinct SHAs while commits holds (path, commit) pairs, so their
        # lengths differ even when nothing was dropped. A consumer therefore cannot infer
        # truncation by comparing them, and has to be told outright.
        "commits": commits[:MAX_PAYLOAD_COMMITS],
        # Measured before any cap: the withheld count must describe what was actually dropped,
        # not what survived truncation.
        "commits_total": len(commits),
        "commits_truncated": len(commits) > MAX_PAYLOAD_COMMITS,
        "commit_count": len(revisions),
        "freshness": stale,
        "unwatchable_locators": unwatchable,
    }


def _now(value: str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    try:
        return knowledge_update.parse_utc_timestamp(
            knowledge_update._timestamp(value, "--now")
        )
    except knowledge_update.KnowledgeUpdateValidationError as exc:
        raise PacketDriftError(str(exc)) from exc


def _report(findings: Sequence[Mapping[str, object]]) -> None:
    print(
        f"{len(findings)} pending packet(s) whose evidence changed or whose freshness "
        "deadline passed."
    )
    print("Each may need a disposition transition, or a note that the change was unrelated.")
    print("This is a prompt to look, not a defect.\n")
    for finding in findings:
        artifacts = ", ".join(display(item, 40) for item in finding["pending_artifacts"])
        print(
            f"  {display(finding['update_id'], 100)}  pending: {artifacts}"
            f"  ({finding['commit_count']} commit(s) since "
            f"{str(finding['baseline_revision'])[:12]})"
        )
        for entry in finding["commits"][:MAX_PRINTED_COMMITS]:
            print(f"      {display(entry['path'])}: {display(entry['commit'], 96)}")
        withheld = finding["commits_total"] - MAX_PRINTED_COMMITS
        if withheld > 0:
            more = "more (payload also truncated)" if finding["commits_truncated"] else "more"
            print(f"      ... and {withheld} {more}")
        for stale in finding["freshness"]:
            print(f"      freshness: {display(stale)}")
        for locator in finding["unwatchable_locators"]:
            print(f"      unwatchable locator (not inspected): {display(locator)}")
        print()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("packets", type=Path, nargs="+", help="knowledge-update JSON packets")
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root to inspect")
    parser.add_argument(
        "--now",
        help="RFC3339 UTC instant to evaluate freshness against; default is the current time",
    )
    parser.add_argument(
        "--fail-on-drift",
        action="store_true",
        help="exit 1 when any pending packet has drifted or gone stale",
    )
    parser.add_argument("--json", action="store_true", help="emit findings as JSON")
    args = parser.parse_args(argv)

    # A bad clock argument or an unreadable root invalidates every packet, so those stop the run.
    try:
        now = _now(args.now)
        verify_repository(args.root)
    except PacketDriftError as exc:
        print(f"packet_drift: {exc}", file=sys.stderr)
        return 2

    # One unreadable packet, by contrast, says nothing about the others. Burying their findings
    # behind an unrelated corrupt file would lose a genuine review prompt.
    findings: list[Mapping[str, object]] = []
    errors: list[str] = []
    for packet in args.packets:
        try:
            finding = inspect_packet(args.root, packet, now)
        except PacketDriftError as exc:
            errors.append(str(exc))
            continue
        if finding is not None:
            findings.append(finding)

    if args.json:
        print(json.dumps(findings, indent=2))
    elif findings:
        _report(findings)
    elif not errors:
        # Only claim a clean sweep when every packet was actually inspected.
        print("OK - no pending packet has drifted or passed a freshness deadline.")

    for error in errors:
        print(f"packet_drift: {error}", file=sys.stderr)

    if errors:
        return 2
    return 1 if (findings and args.fail_on_drift) else 0


if __name__ == "__main__":
    raise SystemExit(main())
