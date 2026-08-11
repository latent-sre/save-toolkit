#!/usr/bin/env python3
"""Validate and emit an effect-bound request for one immutable Save Toolkit release.

This script is a read-only preflight. It proves that the requested candidate is the clean, exact
``main`` revision, that every version-bearing manifest agrees, and that the changelog carries notes
for that version. It does not create tags, releases, environments, rulesets, or credentials.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Mapping, Sequence


REPOSITORY = "latent-sre/save-toolkit"
WORKFLOW_REF = f"{REPOSITORY}/.github/workflows/release.yml@refs/heads/main"
TAG_PREFIX = "save-toolkit--v"
MAX_APPROVAL_LIFETIME = timedelta(hours=24)
SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
RUN_ID_PATTERN = re.compile(r"[1-9][0-9]{0,19}")
ACTOR_PATTERN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9_.\-\[\]]{0,98}[A-Za-z0-9\]])?")
UTC_TIMESTAMP_PATTERN = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z"
)
VERSION_PATTERN = re.compile(
    r"(?:0|[1-9][0-9]*)"
    r"\.(?:0|[1-9][0-9]*)"
    r"\.(?:0|[1-9][0-9]*)"
)
REVIEW_PATTERN = re.compile(
    rf"https://github\.com/{re.escape(REPOSITORY)}/pull/[1-9][0-9]*"
)
VERSION_SOURCES = (
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    "plugin.json",
    "plugins/save-toolkit/.codex-plugin/plugin.json",
)


class ReleaseContractError(ValueError):
    """The requested release is not safe to promote."""


def _canonical_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        raise ReleaseContractError("timestamps must carry an explicit UTC offset")
    if value.utcoffset() != timedelta(0):
        raise ReleaseContractError("timestamps must use UTC")
    if value.microsecond:
        raise ReleaseContractError("timestamps must be whole-second values without a fraction")
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_timestamp(value: str) -> datetime:
    if UTC_TIMESTAMP_PATTERN.fullmatch(value) is None:
        raise argparse.ArgumentTypeError("expected an RFC3339 UTC timestamp ending in Z")
    candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected an ISO-8601 timestamp with a UTC offset") from exc
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("timestamp must carry a UTC offset")
    if parsed.utcoffset() != timedelta(0):
        raise argparse.ArgumentTypeError("timestamp must use the UTC offset (Z or +00:00)")
    return parsed.astimezone(timezone.utc)


def _read_json(root: Path, relative: str) -> Mapping[str, object]:
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise ReleaseContractError(f"required release manifest is missing or indirect: {relative}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ReleaseContractError(f"could not read release manifest {relative}: {type(exc).__name__}") from exc
    if not isinstance(value, dict):
        raise ReleaseContractError(f"release manifest must be a JSON object: {relative}")
    return value


def _manifest_versions(root: Path) -> dict[str, str]:
    versions: dict[str, str] = {}
    for relative in VERSION_SOURCES:
        document = _read_json(root, relative)
        if relative == ".claude-plugin/marketplace.json":
            plugins = document.get("plugins")
            matches = [
                item
                for item in plugins
                if isinstance(item, dict) and item.get("name") == "save-toolkit"
            ] if isinstance(plugins, list) else []
            if len(matches) != 1 or not isinstance(matches[0].get("version"), str):
                raise ReleaseContractError(
                    "Claude marketplace must contain exactly one versioned save-toolkit entry"
                )
            versions[relative] = matches[0]["version"]
            continue
        if document.get("name") != "save-toolkit" or not isinstance(document.get("version"), str):
            raise ReleaseContractError(f"release manifest has no save-toolkit version: {relative}")
        versions[relative] = document["version"]  # type: ignore[assignment]
    return versions


def _release_notes(root: Path, version: str, *, now: datetime) -> tuple[str, str]:
    path = root / "CHANGELOG.md"
    if path.is_symlink() or not path.is_file():
        raise ReleaseContractError("changelog is missing or indirect: CHANGELOG.md")
    try:
        changelog = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ReleaseContractError(f"could not read changelog: {type(exc).__name__}") from exc
    heading = re.compile(
        rf"^## \[{re.escape(version)}\] - (?P<date>[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}})[ \t]*$",
        re.MULTILINE,
    )
    matches = list(heading.finditer(changelog))
    if not matches:
        raise ReleaseContractError(
            f"changelog has no exact dated section for version {version}: "
            f"expected '## [{version}] - YYYY-MM-DD'"
        )
    if len(matches) != 1:
        raise ReleaseContractError(
            f"changelog must contain exactly one dated section for version {version}"
        )
    match = matches[0]
    try:
        release_date = datetime.strptime(match.group("date"), "%Y-%m-%d").date()
    except ValueError as exc:
        raise ReleaseContractError(f"changelog date is invalid for version {version}") from exc
    if release_date > now.astimezone(timezone.utc).date():
        raise ReleaseContractError(f"changelog date is in the future for version {version}")
    next_heading = re.search(r"^## ", changelog[match.end() :], re.MULTILINE)
    end = match.end() + next_heading.start() if next_heading else len(changelog)
    body = changelog[match.end() : end].strip()
    if not body:
        raise ReleaseContractError(f"changelog section for version {version} has no release notes")
    notes = f"{match.group(0)}\n\n{body}"
    return match.group(0), notes + "\n"


def _validate_version(version: str) -> str:
    if VERSION_PATTERN.fullmatch(version) is None:
        raise ReleaseContractError(f"version is not a supported SemVer value: {version!r}")
    return version


def tag_for_version(version: str) -> str:
    return TAG_PREFIX + _validate_version(version)


def _validate_sha(label: str, value: str) -> str:
    if SHA_PATTERN.fullmatch(value) is None:
        raise ReleaseContractError(f"{label} must be a lowercase full 40-character Git SHA")
    return value


def _version_tuple_from_tag(tag: str) -> tuple[int, int, int]:
    version = tag[len(TAG_PREFIX) :]
    _validate_version(version)
    major, minor, patch = version.split(".")
    return int(major), int(minor), int(patch)


def _validate_recovery(
    recovery_tag: str,
    release_tag: str,
    recovery_sha: str,
) -> dict[str, object]:
    if recovery_tag == "uninstall":
        if recovery_sha:
            raise ReleaseContractError("uninstall recovery must not carry a recovery SHA")
        return {
            "mode": "uninstall",
            "tag": None,
            "candidate_sha": None,
            "rule": "Remove the failed first release; do not move or reuse its tag.",
        }
    expected_prefix = TAG_PREFIX
    if not recovery_tag.startswith(expected_prefix):
        raise ReleaseContractError("recovery target must be 'uninstall' or a Save Toolkit release tag")
    tag_for_version(recovery_tag[len(expected_prefix) :])
    if _version_tuple_from_tag(recovery_tag) >= _version_tuple_from_tag(release_tag):
        raise ReleaseContractError("recovery target must be strictly older than the release tag")
    recovery_commit = _validate_sha("recovery SHA", recovery_sha)
    return {
        "mode": "prior_release",
        "tag": recovery_tag,
        "candidate_sha": recovery_commit,
        "rule": "Remove the failed release locally and reinstall this prior immutable tag.",
    }


def build_release_packet(
    *,
    root: Path,
    candidate_sha: str,
    version: str,
    run_id: str,
    actor: str,
    triggering_actor: str,
    review_evidence: str,
    workflow_ref: str,
    workflow_sha: str,
    issued_at: datetime,
    expires_at: datetime,
    recovery_tag: str,
    recovery_sha: str,
    head_sha: str,
    main_sha: str,
    clean: bool,
    now: datetime | None = None,
) -> dict[str, object]:
    """Build a release packet only after every local and effect-binding invariant passes."""

    root = root.resolve()
    if not root.is_dir():
        raise ReleaseContractError(f"release root is not a directory: {root}")
    evaluated_at = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if issued_at.tzinfo is None or issued_at.utcoffset() != timedelta(0):
        raise ReleaseContractError("promotion issuance must use UTC")
    issued_at = issued_at.astimezone(timezone.utc)
    _canonical_timestamp(issued_at)
    candidate = _validate_sha("candidate SHA", candidate_sha)
    head = _validate_sha("checkout HEAD", head_sha)
    main = _validate_sha("origin/main SHA", main_sha)
    workflow = _validate_sha("workflow SHA", workflow_sha)
    if candidate != head or candidate != main:
        raise ReleaseContractError(
            "candidate SHA must equal both the checked-out HEAD and the current origin/main SHA"
        )
    if workflow != candidate:
        raise ReleaseContractError("workflow SHA must equal the exact reviewed candidate SHA")
    if not clean:
        raise ReleaseContractError("release checkout must be clean, including untracked files")
    if RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise ReleaseContractError("promotion run id must be the immutable numeric GitHub run id")
    if ACTOR_PATTERN.fullmatch(actor) is None:
        raise ReleaseContractError("release request actor is empty or malformed")
    if triggering_actor != actor:
        raise ReleaseContractError("release request actor and triggering actor must be the same identity")
    if REVIEW_PATTERN.fullmatch(review_evidence) is None:
        raise ReleaseContractError("review evidence must be this repository's exact pull-request URL")
    if workflow_ref != WORKFLOW_REF:
        raise ReleaseContractError(
            "promotion workflow must be the trusted main-branch release workflow: " + WORKFLOW_REF
        )
    if expires_at.tzinfo is None or expires_at.utcoffset() != timedelta(0):
        raise ReleaseContractError("promotion approval expiry must use UTC")
    expiry = expires_at.astimezone(timezone.utc)
    _canonical_timestamp(expiry)
    if issued_at > evaluated_at:
        raise ReleaseContractError("promotion issuance cannot be in the future")
    if expiry <= evaluated_at:
        raise ReleaseContractError("promotion approval is expired and must be in the future")
    if expiry <= issued_at:
        raise ReleaseContractError("promotion approval expiry must be in the future")
    if expiry - issued_at > MAX_APPROVAL_LIFETIME:
        raise ReleaseContractError("promotion approval lifetime must not exceed 24 hours")

    version = _validate_version(version)
    release_tag = tag_for_version(version)
    versions = _manifest_versions(root)
    if set(versions.values()) != {version}:
        rendered = ", ".join(f"{path}={value}" for path, value in sorted(versions.items()))
        raise ReleaseContractError(f"version parity failed for requested {version}: {rendered}")
    changelog_heading, notes = _release_notes(root, version, now=issued_at)
    rollback = _validate_recovery(recovery_tag, release_tag, recovery_sha)

    return {
        "schema_version": 1,
        "repository": REPOSITORY,
        "effect": {
            "action": "publish-immutable-release",
            "candidate_sha": candidate,
            "tag": release_tag,
            "release": f"https://github.com/{REPOSITORY}/releases/tag/{release_tag}",
        },
        "approval": {
            "run_id": run_id,
            "actor": actor,
            "triggering_actor": triggering_actor,
            "review_evidence": review_evidence,
            "workflow_ref": workflow_ref,
            "workflow_sha": workflow,
            "issued_at": _canonical_timestamp(issued_at),
            "expires_at": _canonical_timestamp(expiry),
        },
        "rollback": rollback,
        "distribution": {
            "marketplace_source": f"{REPOSITORY}@{release_tag}",
            "checkout_ref": release_tag,
        },
        "evidence": {
            "clean_checkout": True,
            "head_sha": head,
            "main_sha": main,
            "manifest_versions": versions,
            "changelog_heading": changelog_heading,
        },
        "release_notes": notes,
    }


def _run_git(root: Path, argv: Sequence[str]) -> str:
    try:
        result = subprocess.run(
            ("git", "-C", str(root), *argv),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=30,
            stdin=subprocess.DEVNULL,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ReleaseContractError(f"could not inspect Git state: {type(exc).__name__}") from exc
    if result.returncode:
        raise ReleaseContractError(f"Git inspection failed for {' '.join(argv)}")
    return result.stdout.strip()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--triggering-actor", required=True)
    parser.add_argument("--review-evidence", required=True)
    parser.add_argument("--workflow-ref", required=True)
    parser.add_argument("--workflow-sha", required=True)
    parser.add_argument("--issued-at", required=True, type=_parse_timestamp)
    parser.add_argument("--expires-at", required=True, type=_parse_timestamp)
    parser.add_argument("--recovery-tag", required=True)
    parser.add_argument("--recovery-sha", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    root = args.root.resolve()
    try:
        head = _run_git(root, ("rev-parse", "HEAD"))
        main_sha = _run_git(root, ("rev-parse", "refs/remotes/origin/main"))
        dirty = _run_git(root, ("status", "--porcelain=v1", "--untracked-files=all"))
        packet = build_release_packet(
            root=root,
            candidate_sha=args.candidate_sha,
            version=args.version,
            run_id=args.run_id,
            actor=args.actor,
            triggering_actor=args.triggering_actor,
            review_evidence=args.review_evidence,
            workflow_ref=args.workflow_ref,
            workflow_sha=args.workflow_sha,
            issued_at=args.issued_at,
            expires_at=args.expires_at,
            recovery_tag=args.recovery_tag,
            recovery_sha=args.recovery_sha,
            head_sha=head,
            main_sha=main_sha,
            clean=not dirty,
        )
    except ReleaseContractError as exc:
        print(f"release contract blocked: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(packet, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
