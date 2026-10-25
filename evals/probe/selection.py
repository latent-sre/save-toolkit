"""Admit a frozen native case selection; retain exact input bytes before scheduling trials."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import fingerprints

SHA256 = re.compile(r"[0-9a-f]{64}\Z")
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


@dataclass(frozen=True)
class Selection:
    raw: bytes
    trials: int
    scenarios: list[dict[str, Any]]

    @property
    def file_sha256(self) -> str:
        return hashlib.sha256(self.raw).hexdigest()


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate selection key: {key}")
        result[key] = value
    return result


def _safe(path: Path) -> Path:
    if ".." in path.parts:
        raise ValueError("selection path cannot traverse '..'")
    absolute = path.absolute()
    if any(part.is_symlink() for part in (absolute, *absolute.parents)):
        raise ValueError("selection path cannot traverse symlinks")
    return absolute


def _matches(pattern: re.Pattern[str], value: Any) -> bool:
    return isinstance(value, str) and pattern.fullmatch(value) is not None


def _source(value: Any) -> None:
    if not isinstance(value, dict) or set(value) != {"git_revision", "dirty", "suites"}:
        raise ValueError("invalid selection source")
    revision = value["git_revision"]
    if revision is not None and (not isinstance(revision, str) or not re.fullmatch(r"[0-9a-f]{40,64}", revision)):
        raise ValueError("invalid source revision")
    if value["dirty"] is not None and type(value["dirty"]) is not bool:
        raise ValueError("invalid source dirty state")
    if not isinstance(value["suites"], list):
        raise ValueError("invalid source suites")
    seen: set[str] = set()
    for suite in value["suites"]:
        if (
            not isinstance(suite, dict)
            or set(suite) != {"id", "sha256"}
            or not _matches(SLUG, suite["id"])
            or not _matches(SHA256, suite["sha256"])
            or suite["id"] in seen
        ):
            raise ValueError("invalid or duplicate source suite")
        seen.add(suite["id"])


def load(path: Path, scenarios: list[dict[str, Any]]) -> Selection:
    path = _safe(path)
    if not path.is_file() or path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("selection must be a JSON file no larger than 8 MiB")
    raw = path.read_bytes()
    data = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs)
    if (
        not isinstance(data, dict)
        or set(data) != {"schema_version", "profile", "trials", "tasks", "source"}
        or type(data["schema_version"]) is not int
        or data["schema_version"] != 1
        or data["profile"] != "native-selection-v1"
    ):
        raise ValueError("unsupported native selection schema/profile")
    total = data["trials"]
    if type(total) is not int or not 1 <= total <= 10000:
        raise ValueError("selection trials must be 1..10000")
    _source(data["source"])
    if not isinstance(data["tasks"], list) or not data["tasks"]:
        raise ValueError("selection tasks must be nonempty")
    specs = {spec["id"]: spec for spec in scenarios}
    selected: dict[str, dict[str, Any]] = {}
    for task in data["tasks"]:
        if (
            not isinstance(task, dict)
            or set(task) != {"instance_id", "case_sha256"}
            or not _matches(SLUG, task["instance_id"])
            or not _matches(SHA256, task["case_sha256"])
        ):
            raise ValueError("invalid selected task")
        name = task["instance_id"]
        if name in selected or name not in specs:
            raise ValueError(f"duplicate or missing selected case: {name}")
        spec = specs[name]
        if fingerprints.case_digest(spec) != task["case_sha256"]:
            raise ValueError(f"selected case changed: {name}; export a new selection after finalizing definitions")
        selected[name] = spec
    return Selection(raw, total, [selected[name] for name in sorted(selected)])


def trial_count(selection: Selection, offset: int, count: int | None) -> int:
    count = selection.trials - offset if count is None else count
    if (
        type(offset) is not int
        or type(count) is not int
        or offset < 0
        or count < 1
        or offset + count > selection.trials
    ):
        raise ValueError(f"trial window must stay within frozen slots 1..{selection.trials}")
    return count


def retain(out: Path, selection: Selection) -> Path:
    destination = _safe(out / "selections" / f"{selection.file_sha256}.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with destination.open("xb") as handle:
            handle.write(selection.raw)
    except FileExistsError:
        if destination.read_bytes() != selection.raw:
            raise ValueError("retained selection does not match its file digest") from None
    return destination
