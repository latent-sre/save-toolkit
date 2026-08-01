#!/usr/bin/env python3
"""Run isolated Codex plugin conformance lanes on an explicitly pinned Sol model.

The existing Claude evaluation runner remains authoritative for Claude routing and direct-agent
contracts. This runner is deliberately separate: it installs the Codex plugin into a temporary
CODEX_HOME, runs from an empty git-root fixture, and records Codex/Sol evidence without relabeling
or blending the historical Claude/Opus results.

Raw JSONL is held in memory and reduced to hashes and deterministic facts. It is not persisted.
The isolated CODEX_HOME contains a temporary copy of ``auth.json`` because the CLI cannot run an
authenticated model call without it. Codex's read-only shell can read that config tree, so live
lanes are restricted to clean, reviewed plugin bytes and fixed prompts from this manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Callable, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import evidence_envelope  # noqa: E402

DEFAULT_MANIFEST = REPO_ROOT / "evals" / "conformance" / "codex-sol.json"
MARKETPLACE_MANIFEST = Path(".agents/plugins/marketplace.json")
PLUGIN_DIRECTORY = Path("plugins/sre-agents")
AUTH_FILE = "auth.json"
SOL_MODEL = "gpt-5.6-sol"
VERDICTS = {"pass", "fail", "inconclusive"}

SAFE_ENV_KEYS = (
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "WINDIR",
    "COMSPEC",
    "TEMP",
    "TMP",
    "TMPDIR",
    "HOME",
    "USERPROFILE",
    "APPDATA",
    "LOCALAPPDATA",
    "LANG",
    "LC_ALL",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "NO_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "no_proxy",
    "all_proxy",
)


class ConformanceError(ValueError):
    """The suite or local runtime cannot produce a trustworthy measurement."""


@dataclass(frozen=True)
class CommandResult:
    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool = False


@dataclass(frozen=True)
class Score:
    verdict: str
    reason: str
    response: dict[str, object] | None
    skill_read_verified: bool
    skill_read_diagnostics: dict[str, object]

    def __post_init__(self) -> None:
        if self.verdict not in VERDICTS:
            raise ValueError(f"unknown verdict: {self.verdict}")


Runner = Callable[[Sequence[str], Path, int, Mapping[str, str]], CommandResult]


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def load_manifest(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConformanceError(f"cannot load Codex conformance manifest {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ConformanceError("Codex conformance manifest must be a JSON object")
    validate_manifest(value)
    return value


def validate_manifest(manifest: Mapping[str, object]) -> None:
    if set(manifest) != {"schema_version", "description", "plugin", "lanes"}:
        raise ConformanceError("manifest has missing or unknown top-level fields")
    if manifest["schema_version"] != 1:
        raise ConformanceError("unsupported Codex conformance schema version")
    if not isinstance(manifest["description"], str) or not manifest["description"].strip():
        raise ConformanceError("manifest description must be non-empty")

    plugin = manifest["plugin"]
    if not isinstance(plugin, dict) or set(plugin) != {
        "marketplace",
        "plugin_id",
        "name",
        "version",
    }:
        raise ConformanceError("plugin contract has missing or unknown fields")
    if any(not isinstance(plugin[field], str) or not plugin[field].strip() for field in plugin):
        raise ConformanceError("plugin contract fields must be non-empty strings")
    if plugin["plugin_id"] != f'{plugin["name"]}@{plugin["marketplace"]}':
        raise ConformanceError("plugin_id must be <name>@<marketplace>")

    lanes = manifest["lanes"]
    if not isinstance(lanes, list) or not lanes:
        raise ConformanceError("manifest must contain at least one lane")
    ids: set[str] = set()
    base_fields = {
        "id",
        "kind",
        "model",
        "reasoning_effort",
        "sandbox",
        "approval_policy",
        "skill",
        "prompt",
        "expected",
        "timeout_seconds",
        "required",
    }
    for lane in lanes:
        if not isinstance(lane, dict):
            raise ConformanceError("each lane must be an object")
        lane_fields = set(lane)
        if lane.get("kind") == "skill-direct":
            expected_fields = base_fields
        elif lane.get("kind") == "reference-direct":
            expected_fields = base_fields | {"references"}
        else:
            raise ConformanceError(f"lane {lane.get('id')!r}: unsupported lane kind")
        if lane_fields != expected_fields:
            raise ConformanceError("each lane has missing or unknown fields")
        lane_id = lane["id"]
        if not isinstance(lane_id, str) or not lane_id or lane_id in ids:
            raise ConformanceError("lane IDs must be unique non-empty strings")
        ids.add(lane_id)
        if lane["model"] != SOL_MODEL:
            raise ConformanceError(f"lane {lane_id!r}: model must be {SOL_MODEL}")
        if lane["reasoning_effort"] != "high":
            raise ConformanceError(f"lane {lane_id!r}: reasoning effort must be high")
        if lane["sandbox"] != "read-only":
            raise ConformanceError(f"lane {lane_id!r}: sandbox must be read-only")
        if lane["approval_policy"] != "never":
            raise ConformanceError(f"lane {lane_id!r}: approval policy must be never")
        if not isinstance(lane["skill"], str) or not lane["skill"].strip():
            raise ConformanceError(f"lane {lane_id!r}: skill must be non-empty")
        if not isinstance(lane["prompt"], str) or not lane["prompt"].strip():
            raise ConformanceError(f"lane {lane_id!r}: prompt must be non-empty")
        if f'${lane["skill"]}' not in lane["prompt"]:
            raise ConformanceError(f"lane {lane_id!r}: prompt must explicitly select its skill")
        if lane["kind"] == "skill-direct":
            read_directive = f'First read only the installed skill file for ${lane["skill"]}.'
            if read_directive not in lane["prompt"]:
                raise ConformanceError(
                    f"lane {lane_id!r}: skill-direct prompt must require the exact installed-skill read"
                )
            if "do not run a command" in lane["prompt"].lower():
                raise ConformanceError(
                    f"lane {lane_id!r}: prompt must not forbid its required installed-skill read"
                )
        if not isinstance(lane["expected"], dict) or not lane["expected"]:
            raise ConformanceError(f"lane {lane_id!r}: expected must be a non-empty object")
        if not isinstance(lane["timeout_seconds"], int) or not 1 <= lane["timeout_seconds"] <= 900:
            raise ConformanceError(f"lane {lane_id!r}: timeout must be between 1 and 900 seconds")
        if not isinstance(lane["required"], bool):
            raise ConformanceError(f"lane {lane_id!r}: required must be boolean")
        if lane["kind"] == "reference-direct":
            references = lane["references"]
            if not isinstance(references, list) or not 1 <= len(references) <= 3:
                raise ConformanceError(
                    f"lane {lane_id!r}: references must contain one to three paths"
                )
            if not all(isinstance(reference, str) for reference in references):
                raise ConformanceError(f"lane {lane_id!r}: reference path must be a string")
            if len(set(references)) != len(references):
                raise ConformanceError(f"lane {lane_id!r}: reference paths must be unique")
            for reference in references:
                parsed = PurePosixPath(reference)
                if (
                    parsed.is_absolute()
                    or parsed.as_posix() != reference
                    or not parsed.parts
                    or parsed.parts[0] != "references"
                    or any(part in {".", ".."} for part in parsed.parts)
                    or parsed.suffix != ".md"
                ):
                    raise ConformanceError(f"lane {lane_id!r}: invalid reference path {reference!r}")
    if not any(lane["required"] for lane in lanes):
        raise ConformanceError("manifest must contain at least one required lane")


def validate_local_plugin_contract(root: Path, manifest: Mapping[str, object]) -> None:
    plugin_contract = manifest["plugin"]
    marketplace_path = root / MARKETPLACE_MANIFEST
    plugin_manifest_path = root / PLUGIN_DIRECTORY / ".codex-plugin" / "plugin.json"
    _assert_no_indirection(root, marketplace_path, "Codex marketplace manifest")
    _assert_no_indirection(root, plugin_manifest_path, "Codex plugin manifest")
    try:
        marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
        plugin_manifest = json.loads(plugin_manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConformanceError(f"cannot read local Codex plugin contract: {exc}") from exc
    if not isinstance(marketplace, dict) or marketplace.get("name") != plugin_contract["marketplace"]:
        raise ConformanceError("local Codex marketplace name differs from the conformance manifest")
    entries = marketplace.get("plugins")
    if not isinstance(entries, list) or len(entries) != 1 or not isinstance(entries[0], dict):
        raise ConformanceError("local Codex marketplace must contain exactly one plugin")
    entry = entries[0]
    if entry.get("name") != plugin_contract["name"]:
        raise ConformanceError("local Codex marketplace plugin name differs from the manifest")
    source = entry.get("source")
    if not isinstance(source, dict) or source.get("source") != "local" or source.get("path") != "./plugins/sre-agents":
        raise ConformanceError("local Codex marketplace source contract is invalid")
    if not isinstance(plugin_manifest, dict):
        raise ConformanceError("local Codex plugin manifest must be an object")
    if plugin_manifest.get("name") != plugin_contract["name"]:
        raise ConformanceError("local Codex plugin name differs from the conformance manifest")
    if plugin_manifest.get("version") != plugin_contract["version"]:
        raise ConformanceError("local Codex plugin version differs from the conformance manifest")
    if plugin_manifest.get("skills") != "./skills/":
        raise ConformanceError("local Codex plugin skills path must be './skills/'")
    for lane in manifest["lanes"]:
        skill = root / PLUGIN_DIRECTORY / "skills" / lane["skill"] / "SKILL.md"
        _assert_no_indirection(root, skill, f"lane {lane['id']!r} skill")
        if not skill.is_file() or _is_link_or_reparse(skill):
            raise ConformanceError(f"lane {lane['id']!r} targets a missing or linked skill")
        for reference in lane.get("references", []):
            reference_path = root / PLUGIN_DIRECTORY / "skills" / lane["skill"] / reference
            _assert_no_indirection(
                root, reference_path, f"lane {lane['id']!r} reference {reference!r}"
            )
            if not reference_path.is_file() or _is_link_or_reparse(reference_path):
                raise ConformanceError(
                    f"lane {lane['id']!r} targets a missing or linked reference {reference!r}"
                )


def build_exec_command(executable: str, workspace: Path, lane: Mapping[str, object]) -> list[str]:
    """Build argv with global options before ``exec`` and one prompt after ``--``."""

    return [
        executable,
        "--ask-for-approval",
        lane["approval_policy"],
        "exec",
        "--json",
        "--ephemeral",
        "--ignore-rules",
        "--color",
        "never",
        "--model",
        lane["model"],
        "--sandbox",
        lane["sandbox"],
        "-c",
        f'model_reasoning_effort="{lane["reasoning_effort"]}"',
        "--cd",
        str(workspace),
        "--",
        lane["prompt"],
    ]


def _run(argv: Sequence[str], cwd: Path, timeout: int, env: Mapping[str, str]) -> CommandResult:
    try:
        result = subprocess.run(
            list(argv),
            cwd=cwd,
            env=dict(env),
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            returncode=None,
            stdout=str(exc.stdout or ""),
            stderr=str(exc.stderr or ""),
            timed_out=True,
        )
    except OSError as exc:
        return CommandResult(returncode=127, stdout="", stderr=str(exc))
    return CommandResult(result.returncode, result.stdout, result.stderr)


def _is_link_or_reparse(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        attributes = path.stat(follow_symlinks=False).st_file_attributes
    except (AttributeError, OSError):
        return False
    return bool(attributes & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def _assert_no_indirection(root: Path, target: Path, label: str) -> None:
    """Reject links/reparse points in every existing component from root through target."""

    root_absolute = root.absolute()
    target_absolute = target.absolute()
    try:
        relative = target_absolute.relative_to(root_absolute)
    except ValueError as exc:
        raise ConformanceError(f"{label} escapes its repository root: {target}") from exc
    current = root_absolute
    if _is_link_or_reparse(current):
        raise ConformanceError(f"{label} traverses a linked or reparse root: {current}")
    for part in relative.parts:
        current /= part
        if (current.exists() or current.is_symlink()) and _is_link_or_reparse(current):
            raise ConformanceError(f"{label} traverses a linked or reparse path: {current}")


def _checked_files(base: Path) -> list[Path]:
    if not base.is_dir() or _is_link_or_reparse(base):
        raise ConformanceError(f"refusing missing, linked, or reparse directory: {base}")
    files: list[Path] = []
    for current, directories, names in os.walk(base, followlinks=False):
        current_path = Path(current)
        if _is_link_or_reparse(current_path):
            raise ConformanceError(f"refusing linked or reparse path: {current_path}")
        for name in directories:
            child = current_path / name
            if _is_link_or_reparse(child):
                raise ConformanceError(f"refusing linked or reparse path: {child}")
        for name in names:
            child = current_path / name
            if _is_link_or_reparse(child) or not child.is_file():
                raise ConformanceError(f"refusing non-regular plugin input: {child}")
            files.append(child)
    return sorted(files, key=lambda path: path.relative_to(base).as_posix())


def _digest_files(base: Path, files: Sequence[Path]) -> str:
    digest = hashlib.sha256()
    for path in files:
        digest.update(path.relative_to(base).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def directory_digest(base: Path) -> str:
    return _digest_files(base, _checked_files(base))


def codex_plugin_digest(root: Path = REPO_ROOT) -> str:
    manifest = root / MARKETPLACE_MANIFEST
    plugin = root / PLUGIN_DIRECTORY
    _assert_no_indirection(root, manifest, "Codex marketplace manifest")
    _assert_no_indirection(root, plugin, "Codex plugin directory")
    if not manifest.is_file() or _is_link_or_reparse(manifest):
        raise ConformanceError(f"refusing missing, linked, or reparse marketplace manifest: {manifest}")
    files = [manifest, *_checked_files(plugin)]
    return _digest_files(root, files)


def copy_codex_marketplace_snapshot(source_root: Path, destination_root: Path) -> None:
    """Copy only the Codex marketplace manifest and plugin bundle into an empty root."""

    if destination_root.exists():
        raise ConformanceError(f"snapshot destination already exists: {destination_root}")
    before = codex_plugin_digest(source_root)
    (destination_root / MARKETPLACE_MANIFEST.parent).mkdir(parents=True)
    shutil.copy2(source_root / MARKETPLACE_MANIFEST, destination_root / MARKETPLACE_MANIFEST)
    shutil.copytree(source_root / PLUGIN_DIRECTORY, destination_root / PLUGIN_DIRECTORY)
    after = codex_plugin_digest(source_root)
    snapshot = codex_plugin_digest(destination_root)
    if before != after or before != snapshot:
        raise ConformanceError("Codex plugin inputs changed while the snapshot was being copied")


def source_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex")).expanduser().resolve()


def require_auth_file() -> Path:
    auth = source_codex_home() / AUTH_FILE
    if not auth.is_file() or _is_link_or_reparse(auth):
        raise ConformanceError(
            f"no regular Codex credential file at {auth}; run `codex login` before live conformance"
        )
    return auth


def scrubbed_child_env(codex_home: Path, neutral_profile: Path | None = None) -> dict[str, str]:
    env = {key: os.environ[key] for key in SAFE_ENV_KEYS if os.environ.get(key)}
    env["CODEX_HOME"] = str(codex_home)
    if neutral_profile is not None:
        neutral_profile.mkdir(parents=True, exist_ok=True)
        roaming = neutral_profile / "AppData" / "Roaming"
        local = neutral_profile / "AppData" / "Local"
        roaming.mkdir(parents=True)
        local.mkdir(parents=True)
        env.update(
            {
                "HOME": str(neutral_profile),
                "USERPROFILE": str(neutral_profile),
                "APPDATA": str(roaming),
                "LOCALAPPDATA": str(local),
            }
        )
    return env


def parse_codex_jsonl(text: str) -> dict[str, object]:
    events: list[dict[str, object]] = []
    malformed_line_count = 0
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            malformed_line_count += 1
            continue
        if isinstance(value, dict):
            events.append(value)
        else:
            malformed_line_count += 1

    commands: list[dict[str, object]] = []
    messages: list[str] = []
    usages: list[dict[str, object]] = []
    observed_models: set[str] = set()
    thread_id: str | None = None
    command_started_ids: set[str] = set()
    command_completed_ids: set[str] = set()
    anonymous_command_starts = 0
    turn_completed_count = 0

    def walk(value: object):
        yield value
        if isinstance(value, dict):
            for child in value.values():
                yield from walk(child)
        elif isinstance(value, list):
            for child in value:
                yield from walk(child)

    for event in events:
        if event.get("type") == "thread.started" and isinstance(event.get("thread_id"), str):
            thread_id = event["thread_id"]
        for value in walk(event):
            if isinstance(value, dict):
                model = value.get("model")
                if isinstance(model, str) and model.startswith("gpt-"):
                    observed_models.add(model)
        if event.get("type") == "item.started" and isinstance(event.get("item"), dict):
            item = event["item"]
            if item.get("type") == "command_execution":
                if isinstance(item.get("id"), str):
                    command_started_ids.add(item["id"])
                else:
                    anonymous_command_starts += 1
        if event.get("type") == "item.completed" and isinstance(event.get("item"), dict):
            item = event["item"]
            if item.get("type") == "command_execution":
                commands.append(dict(item))
                if isinstance(item.get("id"), str):
                    command_completed_ids.add(item["id"])
            elif item.get("type") == "agent_message" and isinstance(item.get("text"), str):
                messages.append(item["text"])
        if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
            usages.append(dict(event["usage"]))
            turn_completed_count += 1
    return {
        "event_count": len(events),
        "commands": commands,
        "last_message": messages[-1] if messages else None,
        "usage": usages[-1] if usages else None,
        "observed_models": sorted(observed_models),
        "thread_id": thread_id,
        "malformed_line_count": malformed_line_count,
        "turn_completed_count": turn_completed_count,
        "unfinished_command_count": len(command_started_ids - command_completed_ids)
        + anonymous_command_starts,
    }


def _extract_object(text: str | None) -> dict[str, object] | None:
    if not text:
        return None
    candidate = text.strip()
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def _normalized_text(value: str) -> str:
    return value.replace("\r\n", "\n")


_DOTNET_WINDOWS_1252_TRANSLATION = str.maketrans(
    {
        0x80: 0x20AC,
        0x82: 0x201A,
        0x83: 0x0192,
        0x84: 0x201E,
        0x85: 0x2026,
        0x86: 0x2020,
        0x87: 0x2021,
        0x88: 0x02C6,
        0x89: 0x2030,
        0x8A: 0x0160,
        0x8B: 0x2039,
        0x8C: 0x0152,
        0x8E: 0x017D,
        0x91: 0x2018,
        0x92: 0x2019,
        0x93: 0x201C,
        0x94: 0x201D,
        0x95: 0x2022,
        0x96: 0x2013,
        0x97: 0x2014,
        0x98: 0x02DC,
        0x99: 0x2122,
        0x9A: 0x0161,
        0x9B: 0x203A,
        0x9C: 0x0153,
        0x9E: 0x017E,
        0x9F: 0x0178,
    }
)


def _dotnet_windows_1252_decode(raw: bytes) -> str:
    """Match .NET Windows-1252, including preserved undefined C1 bytes."""

    return raw.decode("latin-1").translate(_DOTNET_WINDOWS_1252_TRANSLATION)


def _command_output_matches(actual: str, expected: str) -> bool:
    """Accept exact UTF-8 or PowerShell 5.1 CP-1252 rendering plus one shell newline."""

    normalized_actual = _normalized_text(actual)
    normalized_expected = _normalized_text(expected)
    renderings = {normalized_expected}
    renderings.add(
        _normalized_text(_dotnet_windows_1252_decode(expected.encode("utf-8")))
    )
    return any(normalized_actual in {rendering, rendering + "\n"} for rendering in renderings)


def _normalized_windows_pathish(value: str) -> str:
    normalized = value.replace("/", "\\").lower()
    while "\\\\" in normalized:
        normalized = normalized.replace("\\\\", "\\")
    return normalized.replace("\\?\\", "")


def _is_simple_skill_read_command(rendered: str) -> bool:
    suspicious = ("auth.json", "env:", ";", "&&", "||", "|", ">", "<", "$(", "`", "\n", "\r")
    if any(token in rendered for token in suspicious):
        return False
    powershell_read = rendered.count("get-content -raw") == 1
    posix_read = rendered.count(" cat ") == 1 or rendered.lstrip().startswith("cat ")
    return powershell_read or posix_read


def _verify_artifact_command(
    command: Mapping[str, object],
    *,
    relative_path: str,
    expected_text: str,
    allowed_paths: Mapping[str, Path],
    isolated_root: Path | None,
) -> tuple[bool, dict[str, object]]:
    rendered = _normalized_windows_pathish(str(command.get("command") or ""))
    output = str(command.get("aggregated_output") or "")
    normalized_output = _normalized_text(output)
    normalized_expected = _normalized_text(expected_text)
    normalized_paths = {
        scope: _normalized_windows_pathish(str(path)) for scope, path in allowed_paths.items()
    }
    matched_scope: str | None = next(
        (scope for scope, expected_path in normalized_paths.items() if expected_path in rendered),
        None,
    )
    normalized_isolated_root = (
        _normalized_windows_pathish(str(isolated_root)) if isolated_root is not None else None
    )
    artifact_suffix = _normalized_windows_pathish(relative_path)
    isolated_root_matched = bool(
        normalized_isolated_root and normalized_isolated_root in rendered
    )
    artifact_suffix_matched = artifact_suffix in rendered
    if matched_scope is None and isolated_root_matched and artifact_suffix_matched:
        matched_scope = "host-staged-isolated"
    simple_read_command = _is_simple_skill_read_command(rendered)
    output_matched = _command_output_matches(output, expected_text)
    diagnostics = {
        "relative_path": relative_path,
        "status": command.get("status"),
        "exit_code": command.get("exit_code"),
        "path_matched": matched_scope is not None,
        "matched_scope": matched_scope,
        "isolated_root_matched": isolated_root_matched,
        "artifact_suffix_matched": artifact_suffix_matched,
        "simple_read_command": simple_read_command,
        "command_sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
        "output_chars": len(normalized_output),
        "expected_chars": len(normalized_expected),
        "output_sha256": hashlib.sha256(normalized_output.encode("utf-8")).hexdigest(),
        "expected_sha256": hashlib.sha256(normalized_expected.encode("utf-8")).hexdigest(),
        "full_output_matched": output_matched,
    }
    verified = (
        command.get("status") == "completed"
        and command.get("exit_code") == 0
        and matched_scope is not None
        and simple_read_command
        and output_matched
    )
    return verified, diagnostics


def _trace_instrument_failure(
    parsed: Mapping[str, object],
    *,
    returncode: int | None,
    stderr: str,
    timed_out: bool,
    diagnostics: dict[str, object],
) -> Score | None:
    if timed_out:
        return Score("inconclusive", "Codex timed out", None, False, diagnostics)
    if returncode != 0:
        detail = "authentication or model access failed" if any(
            marker in stderr.lower()
            for marker in ("auth", "not logged in", "not available", "rate limit", "access")
        ) else "Codex exited non-zero"
        return Score("inconclusive", detail, None, False, diagnostics)
    if (
        parsed.get("malformed_line_count")
        or parsed.get("turn_completed_count") != 1
        or parsed.get("unfinished_command_count")
    ):
        diagnostics.update(
            {
                "malformed_line_count": parsed.get("malformed_line_count"),
                "turn_completed_count": parsed.get("turn_completed_count"),
                "unfinished_command_count": parsed.get("unfinished_command_count"),
            }
        )
        return Score(
            "inconclusive", "Codex trace was malformed or incomplete", None, False, diagnostics
        )
    if not parsed.get("last_message"):
        return Score(
            "inconclusive", "Codex emitted no final agent message", None, False, diagnostics
        )
    return None


def score_trace(
    parsed: Mapping[str, object],
    *,
    lane: Mapping[str, object],
    expected_skill_text: str,
    returncode: int | None,
    stderr: str,
    timed_out: bool,
    installed_skill: Path | None = None,
    allowed_skill_paths: Mapping[str, Path] | None = None,
    isolated_root: Path | None = None,
) -> Score:
    diagnostics: dict[str, object] = {"command_count": 0}
    if timed_out:
        return Score("inconclusive", "Codex timed out", None, False, diagnostics)
    if returncode != 0:
        detail = "authentication or model access failed" if any(
            marker in stderr.lower()
            for marker in ("auth", "not logged in", "not available", "rate limit", "access")
        ) else "Codex exited non-zero"
        return Score("inconclusive", detail, None, False, diagnostics)
    if (
        parsed.get("malformed_line_count")
        or parsed.get("turn_completed_count") != 1
        or parsed.get("unfinished_command_count")
    ):
        diagnostics.update(
            {
                "malformed_line_count": parsed.get("malformed_line_count"),
                "turn_completed_count": parsed.get("turn_completed_count"),
                "unfinished_command_count": parsed.get("unfinished_command_count"),
            }
        )
        return Score("inconclusive", "Codex trace was malformed or incomplete", None, False, diagnostics)
    if not parsed.get("last_message"):
        return Score(
            "inconclusive", "Codex emitted no final agent message", None, False, diagnostics
        )

    response = _extract_object(parsed["last_message"])
    commands = parsed.get("commands") if isinstance(parsed.get("commands"), list) else []
    diagnostics["command_count"] = len(commands)
    if allowed_skill_paths is None:
        if installed_skill is None:
            raise ValueError("score_trace requires installed_skill or allowed_skill_paths")
        allowed_skill_paths = {"installed-cache": installed_skill}
    normalized_paths = {
        scope: _normalized_windows_pathish(str(path))
        for scope, path in allowed_skill_paths.items()
    }
    skill_read_verified = False
    if len(commands) == 1 and isinstance(commands[0], dict):
        command = commands[0]
        rendered = _normalized_windows_pathish(str(command.get("command") or ""))
        output = str(command.get("aggregated_output") or "")
        normalized_output = _normalized_text(output)
        normalized_expected = _normalized_text(expected_skill_text)
        matched_scope: str | None = next(
            (scope for scope, expected_path in normalized_paths.items() if expected_path in rendered),
            None,
        )
        normalized_isolated_root = (
            _normalized_windows_pathish(str(isolated_root)) if isolated_root is not None else None
        )
        skill_suffix = _normalized_windows_pathish(
            str(Path("skills") / str(lane["skill"]) / "SKILL.md")
        )
        isolated_root_matched = bool(
            normalized_isolated_root and normalized_isolated_root in rendered
        )
        skill_suffix_matched = skill_suffix in rendered
        simple_read_command = _is_simple_skill_read_command(rendered)
        if matched_scope is None and isolated_root_matched and skill_suffix_matched:
            matched_scope = "host-staged-isolated"
        diagnostics.update(
            {
                "status": command.get("status"),
                "exit_code": command.get("exit_code"),
                "path_matched": matched_scope is not None,
                "matched_scope": matched_scope,
                "isolated_root_matched": isolated_root_matched,
                "skill_suffix_matched": skill_suffix_matched,
                "simple_read_command": simple_read_command,
                "command_sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
                "output_chars": len(normalized_output),
                "expected_chars": len(normalized_expected),
                "output_sha256": hashlib.sha256(normalized_output.encode("utf-8")).hexdigest(),
                "expected_sha256": hashlib.sha256(normalized_expected.encode("utf-8")).hexdigest(),
                "full_output_matched": _command_output_matches(output, expected_skill_text),
                "output_contains_canary": str(lane["expected"].get("canary", ""))
                in normalized_output,
            }
        )
        skill_read_verified = (
            command.get("status") == "completed"
            and command.get("exit_code") == 0
            and matched_scope is not None
            and simple_read_command
            and _command_output_matches(output, expected_skill_text)
        )

    observed = parsed.get("observed_models")
    if isinstance(observed, list) and observed and lane["model"] not in observed:
        return Score(
            "fail",
            "observed model differs from requested model",
            response,
            skill_read_verified,
            diagnostics,
        )
    if response != lane["expected"]:
        return Score(
            "fail",
            "final response did not match the deterministic oracle",
            response,
            skill_read_verified,
            diagnostics,
        )
    if not skill_read_verified:
        return Score(
            "fail",
            "oracle matched without a verified installed-skill read",
            response,
            False,
            diagnostics,
        )
    return Score(
        "pass",
        "deterministic oracle and installed-skill read passed",
        response,
        True,
        diagnostics,
    )


def score_reference_trace(
    parsed: Mapping[str, object],
    *,
    lane: Mapping[str, object],
    artifact_texts: Mapping[str, str],
    artifact_paths: Mapping[str, Mapping[str, Path]],
    isolated_root: Path,
    returncode: int | None,
    stderr: str,
    timed_out: bool,
) -> Score:
    commands = parsed.get("commands") if isinstance(parsed.get("commands"), list) else []
    diagnostics: dict[str, object] = {
        "command_count": len(commands),
        "expected_artifact_count": len(artifact_texts),
        "verified_artifact_count": 0,
        "artifacts": [],
    }
    instrument_failure = _trace_instrument_failure(
        parsed,
        returncode=returncode,
        stderr=stderr,
        timed_out=timed_out,
        diagnostics=diagnostics,
    )
    if instrument_failure is not None:
        return instrument_failure

    response = _extract_object(parsed["last_message"])
    observed = parsed.get("observed_models")
    if isinstance(observed, list) and observed and lane["model"] not in observed:
        return Score(
            "fail", "observed model differs from requested model", response, False, diagnostics
        )
    if response != lane["expected"]:
        return Score(
            "fail",
            "final response did not match the deterministic oracle",
            response,
            False,
            diagnostics,
        )

    used_commands: set[int] = set()
    artifact_diagnostics: list[dict[str, object]] = []
    all_verified = len(commands) == len(artifact_texts)
    for relative_path, expected_text in artifact_texts.items():
        candidates: list[tuple[int, bool, dict[str, object]]] = []
        for index, command in enumerate(commands):
            if not isinstance(command, dict):
                continue
            verified, command_diagnostics = _verify_artifact_command(
                command,
                relative_path=relative_path,
                expected_text=expected_text,
                allowed_paths=artifact_paths[relative_path],
                isolated_root=isolated_root,
            )
            if command_diagnostics["path_matched"]:
                candidates.append((index, verified, command_diagnostics))
        if len(candidates) != 1:
            artifact_diagnostics.append(
                {
                    "relative_path": relative_path,
                    "verified": False,
                    "candidate_command_count": len(candidates),
                }
            )
            all_verified = False
            continue
        index, verified, command_diagnostics = candidates[0]
        if index in used_commands:
            verified = False
            command_diagnostics["reused_command"] = True
        used_commands.add(index)
        command_diagnostics["verified"] = verified
        artifact_diagnostics.append(command_diagnostics)
        all_verified = all_verified and verified

    verified_count = sum(bool(item.get("verified")) for item in artifact_diagnostics)
    diagnostics["verified_artifact_count"] = verified_count
    diagnostics["artifacts"] = artifact_diagnostics
    if not all_verified or len(used_commands) != len(commands):
        return Score(
            "fail",
            "oracle matched without every required artifact read",
            response,
            False,
            diagnostics,
        )
    return Score(
        "pass",
        "deterministic oracle and every required artifact read passed",
        response,
        True,
        diagnostics,
    )


def _git_value(root: Path, argv: Sequence[str]) -> str:
    result = subprocess.run(
        ["git", *argv],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise ConformanceError(
            f"git {' '.join(argv)} failed: {(result.stderr or result.stdout).strip()[-300:]}"
        )
    value = result.stdout.strip()
    if not value:
        raise ConformanceError(f"git {' '.join(argv)} returned an empty result")
    return value


def _git_status(root: Path, paths: Sequence[str]) -> str:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--", *paths],
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise ConformanceError(
            f"git status failed: {(result.stderr or result.stdout).strip()[-300:]}"
        )
    return result.stdout.strip()


def _plugin_git_status(root: Path) -> str:
    return _git_status(
        root, [str(MARKETPLACE_MANIFEST), str(PLUGIN_DIRECTORY)]
    ) or ""


def _harness_git_status(root: Path) -> str:
    return _git_status(
        root,
        [
            "evals/run_codex_conformance.py",
            "evals/conformance/codex-sol.json",
            "scripts/evidence_envelope.py",
            "schemas/evidence-envelope-v1.schema.json",
        ],
    ) or ""


def build_conformance_evidence(
    report: Mapping[str, object],
    *,
    producer: str,
    role: str,
    target_root: Path,
    tree_digest: str,
    criterion: str,
    source_extra: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Reduce a multi-lane report to the fleet's portable verdict envelope."""

    summary = report["summary"]
    if not isinstance(summary, Mapping):
        raise ConformanceError("conformance summary must be an object")
    inputs_dirty = bool(
        report.get("plugin_inputs_dirty")
        or report.get("agent_inputs_dirty")
        or report.get("harness_inputs_dirty")
    )
    if inputs_dirty:
        status = "inconclusive"
    elif summary.get("fail", 0):
        status = "fail"
    elif summary.get("inconclusive", 0):
        status = "inconclusive"
    else:
        status = "pass"
    results = report["results"]
    if not isinstance(results, list) or not results:
        raise ConformanceError("conformance evidence requires at least one lane result")
    requested_models = sorted(
        {item["requested_model"] for item in results if isinstance(item, dict)}
    )
    limitations = ["Raw model transcripts were reduced to hashes and were not persisted."]
    missing_model_evidence = sum(
        isinstance(item, dict) and not item.get("observed_model_exposed") for item in results
    )
    if missing_model_evidence:
        limitations.append(
            f"The runtime did not expose the resolved model for {missing_model_evidence} lane(s)."
        )
    if inputs_dirty:
        limitations.append(
            "Inputs differed from HEAD, so this result is not exact-revision evidence."
        )
    source: dict[str, object] = {
        "kind": "codex-sol-conformance",
        "lane_count": len(results),
        "required_lane_count": sum(
            bool(item.get("required")) for item in results if isinstance(item, dict)
        ),
        "summary": dict(summary),
        "manifest_sha256": report["manifest_sha256"],
        "runner_sha256": report["runner_sha256"],
        "plugin_source_sha256": report["plugin_source_sha256"],
    }
    source.update(dict(source_extra or {}))
    started = evidence_envelope.parse_timestamp(report["started_at"], "started_at")
    ended = evidence_envelope.parse_timestamp(report["generated_at"], "generated_at")
    run_id = producer.replace("_", "-") + "-" + started.strftime("%Y%m%dT%H%M%SZ")
    return evidence_envelope.new_envelope(
        producer=producer,
        role=role,
        target_root=str(target_root),
        target_revision=str(report["repository_commit"]),
        tree_digest=tree_digest,
        criterion=criterion,
        status=status,
        started_at=started,
        ended_at=ended,
        source=source,
        run_id=run_id,
        task_id="required-lanes",
        attempt_id="attempt-1",
        environment={
            "cli_version": results[0]["cli_version"],
            "requested_models": requested_models,
            "reasoning_effort": sorted(
                {item["reasoning_effort"] for item in results if isinstance(item, dict)}
            ),
            "sandbox": sorted({item["sandbox"] for item in results if isinstance(item, dict)}),
            "approval_policy": sorted(
                {item["approval_policy"] for item in results if isinstance(item, dict)}
            ),
        },
        isolation={
            "disposable_home": True,
            "read_only_sandbox_requested": True,
            "raw_transcript_persisted": False,
        },
        limitations=limitations,
    )


def _parse_json_object(text: str, label: str) -> dict[str, object]:
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConformanceError(f"{label} did not return one JSON object") from exc
    if not isinstance(value, dict):
        raise ConformanceError(f"{label} did not return one JSON object")
    return value


def _bootstrap_plugin(
    executable: str,
    marketplace_root: Path,
    plugin: Mapping[str, object],
    workspace: Path,
    env: Mapping[str, str],
    runner: Runner,
) -> tuple[str, Path, str]:
    version_result = runner((executable, "--version"), workspace, 30, env)
    if version_result.returncode != 0 or not version_result.stdout.strip():
        raise ConformanceError("Codex CLI version command failed")
    version = version_result.stdout.strip().splitlines()[0]

    add_marketplace = runner(
        (executable, "plugin", "marketplace", "add", str(marketplace_root), "--json"),
        workspace,
        60,
        env,
    )
    if add_marketplace.returncode != 0:
        raise ConformanceError(f"Codex marketplace registration failed: {add_marketplace.stderr[-300:]}")

    add_plugin = runner(
        (executable, "plugin", "add", str(plugin["plugin_id"]), "--json"),
        workspace,
        60,
        env,
    )
    if add_plugin.returncode != 0:
        raise ConformanceError(f"Codex plugin installation failed: {add_plugin.stderr[-300:]}")
    installed = _parse_json_object(add_plugin.stdout, "Codex plugin installation")
    if installed.get("pluginId") != plugin["plugin_id"]:
        raise ConformanceError("Codex installed plugin ID differs from the manifest")
    if installed.get("name") != plugin["name"] or installed.get("version") != plugin["version"]:
        raise ConformanceError("Codex installed plugin name or version differs from the manifest")
    raw_installed_path = installed.get("installedPath")
    if not isinstance(raw_installed_path, str):
        raise ConformanceError("Codex plugin installation did not report installedPath")
    installed_path = Path(raw_installed_path).resolve()
    codex_home = Path(env["CODEX_HOME"]).resolve()
    if not installed_path.is_relative_to(codex_home) or not installed_path.is_dir():
        raise ConformanceError("Codex installed plugin outside the isolated CODEX_HOME")

    listing_result = runner((executable, "plugin", "list", "--json"), workspace, 60, env)
    if listing_result.returncode != 0:
        raise ConformanceError("Codex plugin inventory command failed")
    listing = _parse_json_object(listing_result.stdout, "Codex plugin inventory")
    installed_items = listing.get("installed")
    if not isinstance(installed_items, list) or len(installed_items) != 1:
        raise ConformanceError("isolated Codex inventory must contain exactly one installed plugin")
    item = installed_items[0]
    if not isinstance(item, dict) or item.get("pluginId") != plugin["plugin_id"]:
        raise ConformanceError("isolated Codex inventory does not contain the expected plugin")
    expected_inventory = {
        "name": plugin["name"],
        "version": plugin["version"],
        "marketplaceName": plugin["marketplace"],
        "installed": True,
        "enabled": True,
    }
    for field, expected in expected_inventory.items():
        if item.get(field) != expected:
            raise ConformanceError(
                f"isolated Codex inventory field {field!r} differs from {expected!r}"
            )
    inventory_digest = hashlib.sha256(_canonical_json(listing)).hexdigest()
    return version, installed_path, inventory_digest


def run_live(
    root: Path,
    manifest: Mapping[str, object],
    *,
    executable: str,
    require_clean_plugin: bool,
    require_clean_harness: bool,
    runner: Runner = _run,
) -> dict[str, object]:
    source_digest_before = codex_plugin_digest(root)
    plugin_status = _plugin_git_status(root)
    harness_status = _harness_git_status(root)
    runner_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    if require_clean_plugin and plugin_status:
        raise ConformanceError("Codex plugin inputs differ from HEAD; refusing publishable baseline")
    if require_clean_harness and harness_status:
        raise ConformanceError("Codex conformance harness differs from HEAD; refusing publishable baseline")
    auth = require_auth_file()
    started_at = _timestamp()
    start = time.monotonic()
    results: list[dict[str, object]] = []

    with tempfile.TemporaryDirectory(prefix="sre-agents-codex-sol-") as temporary:
        temporary_root = Path(temporary)
        if temporary_root.resolve().is_relative_to(root.resolve()):
            raise ConformanceError("isolated Codex workspace resolved inside the plugin repository")
        if _is_link_or_reparse(temporary_root):
            raise ConformanceError("isolated Codex root must not be a link or reparse point")
        codex_home = temporary_root / "codex-home"
        workspace = temporary_root / "workspace"
        marketplace = temporary_root / "marketplace"
        codex_home.mkdir()
        workspace.mkdir()
        os.chmod(codex_home, stat.S_IRWXU)
        shutil.copyfile(auth, codex_home / AUTH_FILE)
        os.chmod(codex_home / AUTH_FILE, stat.S_IRUSR | stat.S_IWUSR)
        copy_codex_marketplace_snapshot(root, marketplace)
        snapshot_digest = codex_plugin_digest(marketplace)
        if snapshot_digest != source_digest_before:
            raise ConformanceError("Codex marketplace snapshot digest differs from source")

        init = subprocess.run(
            ["git", "init", "--quiet", str(workspace)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if init.returncode != 0:
            raise ConformanceError(f"cannot initialize neutral Codex workspace: {init.stderr[-300:]}")
        if {path.name for path in workspace.iterdir()} != {".git"}:
            raise ConformanceError("neutral Codex workspace contains unexpected template content")
        top = subprocess.run(
            ["git", "-C", str(workspace), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if top.returncode != 0 or Path(top.stdout.strip()).resolve() != workspace.resolve():
            raise ConformanceError("neutral Codex workspace is not its own git-root boundary")
        env = scrubbed_child_env(codex_home, temporary_root / "user-profile")
        version, installed_path, inventory_digest = _bootstrap_plugin(
            executable,
            marketplace,
            manifest["plugin"],
            workspace,
            env,
            runner,
        )
        snapshot_plugin_digest = directory_digest(marketplace / PLUGIN_DIRECTORY)
        installed_plugin_digest = directory_digest(installed_path)
        if snapshot_plugin_digest != installed_plugin_digest:
            raise ConformanceError("installed Codex plugin bytes differ from the frozen snapshot")
        source_skill_count = len(list((marketplace / PLUGIN_DIRECTORY / "skills").glob("*/SKILL.md")))
        installed_skill_count = len(list((installed_path / "skills").glob("*/SKILL.md")))
        if source_skill_count == 0 or installed_skill_count != source_skill_count:
            raise ConformanceError("installed Codex skill inventory differs from the frozen snapshot")

        for lane in manifest["lanes"]:
            lane_started = _timestamp()
            lane_start = time.monotonic()
            relative_paths = [f'skills/{lane["skill"]}/SKILL.md']
            relative_paths.extend(
                f'skills/{lane["skill"]}/{reference}'
                for reference in lane.get("references", [])
            )
            artifact_texts: dict[str, str] = {}
            artifact_paths: dict[str, dict[str, Path]] = {}
            artifact_sha256: dict[str, str] = {}
            for relative_path in relative_paths:
                parts = PurePosixPath(relative_path).parts
                installed_artifact = installed_path.joinpath(*parts)
                frozen_artifact = (marketplace / PLUGIN_DIRECTORY).joinpath(*parts)
                if not installed_artifact.is_file() or _is_link_or_reparse(installed_artifact):
                    raise ConformanceError(
                        f"installed artifact is missing or linked: {installed_artifact}"
                    )
                if not frozen_artifact.is_file() or _is_link_or_reparse(frozen_artifact):
                    raise ConformanceError(
                        f"frozen artifact is missing or linked: {frozen_artifact}"
                    )
                if installed_artifact.read_bytes() != frozen_artifact.read_bytes():
                    raise ConformanceError(
                        f"installed artifact differs from frozen source: {relative_path}"
                    )
                artifact_texts[relative_path] = installed_artifact.read_text(encoding="utf-8")
                artifact_paths[relative_path] = {
                    "installed-cache": installed_artifact,
                    "frozen-marketplace": frozen_artifact,
                }
                artifact_sha256[relative_path] = hashlib.sha256(
                    installed_artifact.read_bytes()
                ).hexdigest()
            skill_relative_path = relative_paths[0]
            skill_path = artifact_paths[skill_relative_path]["installed-cache"]
            command = build_exec_command(executable, workspace, lane)
            execution = runner(command, workspace, lane["timeout_seconds"], env)
            parsed = parse_codex_jsonl(execution.stdout)
            if lane["kind"] == "reference-direct":
                score = score_reference_trace(
                    parsed,
                    lane=lane,
                    artifact_texts=artifact_texts,
                    artifact_paths=artifact_paths,
                    isolated_root=temporary_root,
                    returncode=execution.returncode,
                    stderr=execution.stderr,
                    timed_out=execution.timed_out,
                )
            else:
                score = score_trace(
                    parsed,
                    lane=lane,
                    allowed_skill_paths=artifact_paths[skill_relative_path],
                    isolated_root=temporary_root,
                    expected_skill_text=artifact_texts[skill_relative_path],
                    returncode=execution.returncode,
                    stderr=execution.stderr,
                    timed_out=execution.timed_out,
                )
            transcript = execution.stdout + execution.stderr
            results.append(
                {
                    "lane_id": lane["id"],
                    "kind": lane["kind"],
                    "verdict": score.verdict,
                    "reason": score.reason,
                    "required": lane["required"],
                    "started_at": lane_started,
                    "ended_at": _timestamp(),
                    "duration_ms": round((time.monotonic() - lane_start) * 1000),
                    "cli_version": version,
                    "requested_model": lane["model"],
                    "observed_models": parsed["observed_models"],
                    "observed_model_exposed": bool(parsed["observed_models"]),
                    "reasoning_effort": lane["reasoning_effort"],
                    "sandbox": lane["sandbox"],
                    "approval_policy": lane["approval_policy"],
                    "prompt_digest": hashlib.sha256(lane["prompt"].encode("utf-8")).hexdigest(),
                    "expected": lane["expected"],
                    "response": score.response,
                    "skill": lane["skill"],
                    "references": lane.get("references", []),
                    "skill_sha256": hashlib.sha256(skill_path.read_bytes()).hexdigest(),
                    "artifact_sha256": artifact_sha256,
                    "artifact_reads_verified": score.skill_read_verified,
                    "skill_read_verified": (
                        score.skill_read_verified if lane["kind"] == "skill-direct" else None
                    ),
                    "skill_read_diagnostics": score.skill_read_diagnostics,
                    "event_count": parsed["event_count"],
                    "command_count": len(parsed["commands"]),
                    "usage": parsed["usage"],
                    "exit_code": execution.returncode,
                    "timed_out": execution.timed_out,
                    "transcript_digest": hashlib.sha256(transcript.encode("utf-8")).hexdigest(),
                }
            )

    source_digest_after = codex_plugin_digest(root)
    if source_digest_after != source_digest_before:
        raise ConformanceError("Codex plugin inputs changed during the live run")
    summary = {verdict: sum(item["verdict"] == verdict for item in results) for verdict in sorted(VERDICTS)}
    report: dict[str, object] = {
        "schema_version": 1,
        "generated_at": _timestamp(),
        "started_at": started_at,
        "duration_ms": round((time.monotonic() - start) * 1000),
        "repository_commit": _git_value(root, ["rev-parse", "HEAD"]),
        "plugin_inputs_dirty": bool(plugin_status),
        "harness_inputs_dirty": bool(harness_status),
        "runner_sha256": runner_sha256,
        "plugin_source_sha256": source_digest_before,
        "manifest_sha256": hashlib.sha256(_canonical_json(manifest)).hexdigest(),
        "plugin_inventory_sha256": inventory_digest,
        "installed_skill_count": installed_skill_count,
        "raw_transcript_persisted": False,
        "auth_boundary": (
            "The isolated CODEX_HOME contains auth.json during the run and is deleted afterward; "
            "run only fixed prompts against reviewed plugin bytes."
        ),
        "summary": summary,
        "results": results,
    }
    report["evidence"] = build_conformance_evidence(
        report,
        producer="codex_skill_conformance",
        role="codex-skill-conformance",
        target_root=root,
        tree_digest=source_digest_before,
        criterion="all required Codex/Sol skill and reference lanes pass",
    )
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--validate", action="store_true", help="validate manifest and plugin bytes; no model")
    action.add_argument("--run", action="store_true", help="run live Codex/Sol conformance")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument(
        "--allow-dirty-plugin",
        action="store_true",
        help="development only: permit plugin inputs that differ from HEAD",
    )
    parser.add_argument(
        "--allow-dirty-harness",
        action="store_true",
        help="development only: permit runner/manifest inputs that differ from HEAD",
    )
    parser.add_argument("--output", type=Path, help="write the sanitized report JSON")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        manifest = load_manifest(args.manifest)
        validate_local_plugin_contract(REPO_ROOT, manifest)
        plugin_digest = codex_plugin_digest(REPO_ROOT)
        if args.validate:
            report: dict[str, object] = {
                "schema_version": 1,
                "manifest": str(args.manifest),
                "manifest_sha256": hashlib.sha256(_canonical_json(manifest)).hexdigest(),
                "plugin_source_sha256": plugin_digest,
                "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "lanes": len(manifest["lanes"]),
                "models": sorted({lane["model"] for lane in manifest["lanes"]}),
                "status": "valid",
            }
            exit_code = 0
        else:
            if args.manifest.resolve() != DEFAULT_MANIFEST.resolve():
                raise ConformanceError(
                    "live runs require the repository's fixed codex-sol.json manifest; "
                    "custom manifests are validation-only"
                )
            executable = shutil.which(args.codex_bin)
            if executable is None:
                raise ConformanceError(f"Codex executable is not on PATH: {args.codex_bin}")
            report = run_live(
                REPO_ROOT,
                manifest,
                executable=executable,
                require_clean_plugin=not args.allow_dirty_plugin,
                require_clean_harness=not args.allow_dirty_harness,
            )
            required = [item for item in report["results"] if item["required"]]
            if any(item["verdict"] == "fail" for item in required):
                exit_code = 1
            elif any(item["verdict"] == "inconclusive" for item in required):
                exit_code = 2
            else:
                exit_code = 0
        rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered, encoding="utf-8", newline="\n")
        print(rendered, end="")
        return exit_code
    except (ConformanceError, OSError, ValueError) as exc:
        print(f"Codex conformance error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
