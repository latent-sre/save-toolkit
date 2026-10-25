"""Deterministic SWE-bench selection and immutable case evidence.

Public manifests contain metadata and hashes only. Full dataset rows remain on the
host and must be resolved against the frozen manifest before an attempt starts.
"""

from __future__ import annotations

import copy
import hashlib
import json
import random
import re
from collections.abc import Iterable, Mapping
from typing import Any

DATASET = "SWE-bench/SWE-bench_Verified"
SEED = 20261018
_DIFFICULTIES = ("<15 min fix", "15 min - 1 hour")
_DEFECTS = ("crash", "wrong behavior")
_MARKER = "Traceback (most recent call last)"
_RECIPE = {
    "eligible_difficulties": list(_DIFFICULTIES),
    "repositories": "sort by repo; first 10 eligible",
    "tasks": "sort by instance_id; single seeded Random.choice stream",
    "balance": "last repository backward; majority to minority seeded choice; stop at 3 each or exhaustion",
    "crash_marker": _MARKER,
}
_FIELD_NAMES = (
    "instance_id",
    "repo",
    "difficulty",
    "base_commit",
    "problem_statement",
    "FAIL_TO_PASS",
    "PASS_TO_PASS",
    "image",
    "patch",
    "test_patch",
    "hints_text",
    "eval_script",
    "log_parser",
    "eval_type",
    "version",
)
_MANIFEST_KEYS = {"schema_version", "dataset", "revision", "seed", "difficulty_field", "recipe", "balance", "tasks"}
_TASK_KEYS = {"instance_id", "repo", "defect_type", "licence", "field_hashes", "row_sha256"}
_IDENTITY_KEYS = {
    "dataset",
    "revision",
    "instance_id",
    "base_commit",
    "problem_statement_sha256",
    "fail_to_pass_sha256",
    "pass_to_pass_sha256",
    "image_digest",
}


def _text(value: Any, name: str, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise ValueError(f"{name} must be a {'possibly empty ' if empty else 'nonempty '}string")
    return value


def _hex(value: Any, name: str, length: int, prefix: str = "") -> str:
    if not isinstance(value, str) or re.fullmatch(re.escape(prefix) + f"[0-9a-f]{{{length}}}", value) is None:
        raise ValueError(f"{name} requires {prefix}{length} lowercase hexadecimal characters")
    return value


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode(
            "utf-8"
        )
    except (TypeError, ValueError, UnicodeError) as error:
        raise ValueError("dataset and manifest values must be canonical JSON") from error


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _validate_row(task: Mapping[str, Any]) -> None:
    if not isinstance(task, Mapping) or not set(_FIELD_NAMES) <= task.keys():
        raise ValueError("dataset row is missing required case or verifier fields")
    for field in (
        "instance_id",
        "repo",
        "difficulty",
        "problem_statement",
        "image",
        "eval_script",
        "log_parser",
        "eval_type",
        "version",
    ):
        _text(task[field], field)
    if re.fullmatch(r"[A-Za-z0-9_.-]+", task["instance_id"]) is None:
        raise ValueError("instance_id must be a safe dataset identifier")
    if re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", task["repo"]) is None:
        raise ValueError("repo must be an owner/repository name")
    _hex(task["base_commit"], "base_commit", 40)
    for field in ("patch", "test_patch", "hints_text"):
        _text(task[field], field, empty=True)
    for field in ("FAIL_TO_PASS", "PASS_TO_PASS"):
        tests = task[field]
        if not isinstance(tests, list) or (field == "FAIL_TO_PASS" and not tests):
            raise ValueError(f"{field} must be a list of test names (FAIL_TO_PASS cannot be empty)")
        for test in tests:
            _text(test, field)
        if len(set(tests)) != len(tests):
            raise ValueError(f"{field} contains duplicate test names")
    _canonical(task)


def _validated_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for task in rows:
        _validate_row(task)
        if task["instance_id"] in seen:
            raise ValueError("duplicate dataset instance_id")
        seen.add(task["instance_id"])
        result.append(copy.deepcopy(dict(task)))
    return result


def _defect(task: Mapping[str, Any]) -> str:
    return "crash" if _MARKER in task["problem_statement"] else "wrong behavior"


def select_tasks(
    rows: Iterable[Mapping[str, Any]],
    revision: str,
    licences: Mapping[str, str],
) -> dict[str, Any]:
    """Return the approved ten-task manifest; licences maps repository to public evidence.

    The one PRNG stream is consumed by sorted initial draws, then by eligible
    replacements in reverse repository order. An impossible balance is reported,
    never repaired by selecting an eleventh repository or changing the seed.
    """
    _hex(revision, "revision", 40)
    groups: dict[str, list[dict[str, Any]]] = {}
    for task in _validated_rows(rows):
        if task["difficulty"] in _DIFFICULTIES:
            groups.setdefault(task["repo"], []).append(task)
    repositories = sorted(groups)[:10]
    if len(repositories) != 10:
        raise ValueError("selection requires 10 eligible repositories")
    if not isinstance(licences, Mapping):
        raise ValueError("licences must map every selected repository to public licence evidence")
    for repository in repositories:
        _text(licences.get(repository), f"licence for {repository}")
        groups[repository].sort(key=lambda task: task["instance_id"])
    rng = random.Random(SEED)
    selected = [rng.choice(groups[repository]) for repository in repositories]
    counts = {label: sum(_defect(task) == label for task in selected) for label in _DEFECTS}
    if min(counts.values()) < 3:
        minority = min(counts, key=lambda label: counts[label])
        for index in range(len(selected) - 1, -1, -1):
            if counts[minority] >= 3:
                break
            if _defect(selected[index]) == minority:
                continue
            alternatives = [task for task in groups[repositories[index]] if _defect(task) == minority]
            if alternatives:
                counts[_defect(selected[index])] -= 1
                selected[index] = rng.choice(alternatives)
                counts[minority] += 1
    tasks = [
        {
            "instance_id": task["instance_id"],
            "repo": task["repo"],
            "defect_type": _defect(task),
            "licence": licences[task["repo"]],
            "field_hashes": {field: _digest(task[field]) for field in _FIELD_NAMES},
            "row_sha256": _digest(task),
        }
        for task in selected
    ]
    return {
        "schema_version": 1,
        "dataset": DATASET,
        "revision": revision,
        "seed": SEED,
        "difficulty_field": "difficulty",
        "recipe": copy.deepcopy(_RECIPE),
        "balance": {**counts, "satisfied": min(counts.values()) >= 3},
        "tasks": tasks,
    }


def resolve_task(
    manifest: Mapping[str, Any],
    rows: Iterable[Mapping[str, Any]],
    instance_id: str,
) -> dict[str, Any]:
    """Validate the strict manifest and frozen selection, returning a full row copy.

    Recomputing selection also refuses a changed population that would change the
    approved draw. Licence evidence is supplied by the frozen public manifest.
    """
    if not isinstance(manifest, Mapping) or set(manifest) != _MANIFEST_KEYS:
        raise ValueError("invalid selection manifest fields")
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1:
        raise ValueError("invalid manifest schema_version")
    if type(manifest["seed"]) is not int or manifest["seed"] != SEED:
        raise ValueError("invalid manifest seed")
    tasks = manifest["tasks"]
    if not isinstance(tasks, list) or len(tasks) != 10:
        raise ValueError("manifest must contain 10 selected tasks")
    licences: dict[str, str] = {}
    for task in tasks:
        if not isinstance(task, dict) or set(task) != _TASK_KEYS:
            raise ValueError("invalid manifest task fields")
        repository = _text(task["repo"], "repo")
        licences[repository] = _text(task["licence"], "licence")
    validated = _validated_rows(rows)
    expected = select_tasks(validated, manifest["revision"], licences)
    # Canonical bytes preserve strict JSON types (True must not equal integer 1).
    if _canonical(manifest) != _canonical(expected):
        raise ValueError("manifest does not match the pinned dataset selection or selected row hashes")
    if instance_id not in {task["instance_id"] for task in tasks}:
        raise ValueError("instance_id is not selected in the manifest")
    return next(task for task in validated if task["instance_id"] == instance_id)


def case_identity(task: Mapping[str, Any], revision: str, image_digest: str) -> dict[str, Any]:
    """Bind the approved case components to a resolved immutable instance image."""
    _validate_row(task)
    _hex(revision, "revision", 40)
    _hex(image_digest, "image_digest", 64, "sha256:")
    return {
        "dataset": DATASET,
        "revision": revision,
        "instance_id": task["instance_id"],
        "base_commit": task["base_commit"],
        "problem_statement_sha256": hashlib.sha256(task["problem_statement"].encode("utf-8")).hexdigest(),
        "fail_to_pass_sha256": _digest(task["FAIL_TO_PASS"]),
        "pass_to_pass_sha256": _digest(task["PASS_TO_PASS"]),
        "image_digest": image_digest,
    }


def identity_digest(identity: Mapping[str, Any]) -> str:
    """Hash a complete, strictly validated case identity independent of key order."""
    if not isinstance(identity, Mapping) or set(identity) != _IDENTITY_KEYS or identity["dataset"] != DATASET:
        raise ValueError("invalid case identity fields or dataset")
    _text(identity["instance_id"], "instance_id")
    _hex(identity["revision"], "revision", 40)
    _hex(identity["base_commit"], "base_commit", 40)
    _hex(identity["image_digest"], "image_digest", 64, "sha256:")
    for field in ("problem_statement_sha256", "fail_to_pass_sha256", "pass_to_pass_sha256"):
        _hex(identity[field], field, 64)
    return _digest(identity)
