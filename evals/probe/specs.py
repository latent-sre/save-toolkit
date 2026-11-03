"""What a scenario's identifiers and grader entries must look like: a leaf both the catalog and the
conversation validator read, so neither imports the other."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

import graders as fleet_graders

Spec = Mapping[str, Any]

SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def grader_problems(spec: Spec, where: str) -> list[str]:
    """Why the `graders` entries of `spec` cannot run, each named with `where`, or an empty list."""
    graders = spec.get("graders")
    if graders is None:
        return []
    if not isinstance(graders, list) or not graders:
        return [f"{where}: graders must be a non-empty list"]
    problems: list[str] = []
    for i, grader in enumerate(graders):
        if not isinstance(grader, dict):
            problems.append(f"{where}: graders[{i}] must be a mapping")
            continue
        kind = grader.get("type")
        if not isinstance(kind, str) or kind not in fleet_graders.REGISTRY:
            problems.append(f"{where}: graders[{i}] names an unknown grader type {kind!r}")
            continue
        try:
            # Empty response: every grader validates its own kwargs before looking at text, so a
            # bad regex or a malformed `fields` map is reported here rather than mid-batch.
            fleet_graders.run_grader(dict(grader), "")
        except Exception as exc:
            problems.append(f"{where}: graders[{i}] ({kind}) has invalid configuration: {exc}")
    return problems
