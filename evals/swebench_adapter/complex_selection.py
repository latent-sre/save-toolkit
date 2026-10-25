"""A separate, explicitly proposed hard-case campaign; never an implicit easy-draw change."""

from __future__ import annotations

import copy
from collections.abc import Iterable, Mapping
from typing import Any

from . import selection

REVISION = "78f471bf655a3137b2e8a75af1501690ec009ec3"
CASES = {
    "astropy__astropy-13398": "Coordinate-frame transforms must preserve terrestrial reference and observer geometry.",
    "django__django-13344": "Mixed synchronous/asynchronous middleware must preserve response and await boundaries.",
    "django__django-16631": "Session validation must handle key rotation, fallback secrets and migration to the new key.",
    "pydata__xarray-6992": "Index transitions must preserve coordinate, variable and representation invariants.",
    "pylint-dev__pylint-4551": "Type annotations must flow through inference into UML attributes despite None defaults.",
    "pytest-dev__pytest-5787": "Nested exception causes and contexts must survive serialization and remote reporting.",
    "pytest-dev__pytest-10356": "Marker inheritance must respect multiple-inheritance order without losing base markers.",
    "scikit-learn__scikit-learn-25102": "Transformer output must preserve pandas extension dtypes and feature selection semantics.",
    "sphinx-doc__sphinx-7590": "The Python C++ parser must recognize user-defined literal forms without breaking expressions.",
    "sympy__sympy-13878": "Distribution-specific CDFs must preserve domains, parameters and limiting behavior.",
}
_DIFFICULTIES = ("1-4 hours", ">4 hours")
_KEYS = {"schema_version", "dataset", "revision", "profile", "admission", "recipe", "tasks"}
_TASK_KEYS = {"instance_id", "repo", "difficulty", "complexity", "licence", "field_hashes", "row_sha256"}


def propose(rows: Iterable[Mapping[str, Any]], licences: Mapping[str, Any]) -> dict[str, Any]:
    """Freeze ten predeclared cases with per-base licence evidence and full-row hashes."""
    if not isinstance(licences, Mapping):
        raise ValueError("licences must map case IDs to pinned evidence")
    population = {row["instance_id"]: row for row in selection._validated_rows(rows)}
    tasks = []
    for instance_id, rationale in CASES.items():
        if instance_id not in population:
            raise ValueError("complex campaign is missing a predeclared case")
        row = population[instance_id]
        if row["difficulty"] not in _DIFFICULTIES:
            raise ValueError("complex campaign requires upstream difficulty of at least one hour")
        licence = licences.get(instance_id)
        if not isinstance(licence, dict) or set(licence) != {"url", "sha256"}:
            raise ValueError("each case requires pinned licence URL and content digest")
        selection._hex(licence["sha256"], "licence digest", 64)
        prefix = f"https://raw.githubusercontent.com/{row['repo']}/{row['base_commit']}/"
        if not isinstance(licence["url"], str) or not licence["url"].startswith(prefix):
            raise ValueError("licence source must name the selected repository and exact base")
        tasks.append(
            {
                "instance_id": instance_id,
                "repo": row["repo"],
                "difficulty": row["difficulty"],
                "complexity": rationale,
                "licence": copy.deepcopy(licence),
                "field_hashes": {field: selection._digest(row[field]) for field in selection._FIELD_NAMES},
                "row_sha256": selection._digest(row),
            }
        )
    return {
        "schema_version": 2,
        "dataset": selection.DATASET,
        "revision": REVISION,
        "profile": "complex-v1",
        "admission": "pending-human-acceptance",
        "recipe": {
            "eligible_difficulties": list(_DIFFICULTIES),
            "selection": "predeclared ten cases across eight repositories; no model-outcome selection",
            "balance": "complexity and subsystem diversity; replaces the easy-profile crash-marker quota",
        },
        "tasks": tasks,
    }


def resolve(
    manifest: Mapping[str, Any],
    rows: Iterable[Mapping[str, Any]],
    instance_id: str,
    *,
    allow_proposed: bool = False,
) -> dict[str, Any]:
    """Recompute every hash; an unaccepted proposal is usable only for offline inspection.

    The owner records acceptance by changing admission to ``accepted`` after reviewing
    the exact proposal and run-plan amendment. This is a cooperative human gate, not
    cryptographic proof of authorization. The resulting selection must be committed
    unchanged before the ordinary execution entrypoint will use it.
    """
    if not isinstance(manifest, Mapping) or set(manifest) != _KEYS:
        raise ValueError("invalid complex selection fields")
    if manifest["admission"] not in ("pending-human-acceptance", "accepted"):
        raise ValueError("invalid complex selection admission")
    tasks = manifest["tasks"]
    if not isinstance(tasks, list) or len(tasks) != len(CASES):
        raise ValueError("complex selection requires ten cases")
    licences = {}
    for task in tasks:
        if (
            not isinstance(task, dict)
            or set(task) != _TASK_KEYS
            or not isinstance(task["instance_id"], str)
            or task["instance_id"] not in CASES
        ):
            raise ValueError("invalid complex selection task")
        licences[task["instance_id"]] = task["licence"]
    population = selection._validated_rows(rows)
    expected = propose(population, licences)
    expected["admission"] = manifest["admission"]
    if selection._canonical(manifest) != selection._canonical(expected):
        raise ValueError("complex selection differs from the frozen cases, recipe or dataset hashes")
    if instance_id not in CASES:
        raise ValueError("instance_id is not selected")
    if manifest["admission"] != "accepted" and not allow_proposed:
        raise ValueError("complex selection requires human acceptance before execution")
    return next(row for row in population if row["instance_id"] == instance_id)
