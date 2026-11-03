"""The shadow period of the runner rewrite (RUNNER-001, stage 3): every live grade and every regrade
also grades its evidence with the evidence engine, and `shadow.json` beside the authoritative grade
records whether the two agree. A disagreement is a test failure on the goldens and a reported row in
the owner's runs; the `shadow` command counts them across an iteration against the gate the owner set.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from . import engine, evidence, layout
from .outcomes import EVIDENCE_LIMIT

FILE = "shadow.json"
ENGINE = "evidence-v1 engine"
# The owner's gate for stage 4 (decision of 2026-11-02): this many private attempts with zero
# disagreements, among them at least one of each kind below.
GATE_COUNT = 30
GATE_COVERAGE = ("native", "cut_short", "machinery_failure")
_KEPT = re.compile(r"^\[kept: [\w-]+\] ")
# The longest kept marker a regrade prepends before bounding evidence to EVIDENCE_LIMIT; what both
# engines surely hold of a kept outcome's evidence is the bound less this.
_COMMON_EVIDENCE = EVIDENCE_LIMIT - len("[kept: workspace-dependent] ")


def comparable(grading: Mapping[str, Any]) -> dict[str, Any]:
    """The whole grade minus what is volatile or beside the verdict: identities and digests, the
    judge binding, timestamps and revision marks, the after-assessment record (rule 6: beside the
    verdict, the live attempt's alone), and a regrade's kept markers on probe evidence. Evidence is
    compared on the prefix both engines surely hold: a regrade bounds marker and evidence together,
    and a probe's recorded evidence is already bounded, so the truncation flag is not compared."""
    return {
        "status": grading.get("status"),
        "inconclusive": grading.get("inconclusive"),
        "unmeasured": grading.get("unmeasured"),
        "void": grading.get("void"),
        "run_end": grading.get("run_end"),
        "run_stop": grading.get("run_stop"),
        "grader_error": grading.get("grader_error"),
        "expectations": [
            {
                "text": e.get("text"),
                "kind": e.get("kind"),
                "state": e.get("state"),
                "passed": e.get("passed"),
                "evidence": _KEPT.sub("", str(e.get("evidence") or ""))[:_COMMON_EVIDENCE],
            }
            for e in grading.get("expectations") or []
        ],
        "summary": {key: (grading.get("summary") or {}).get(key) for key in ("passed", "failed", "total")},
    }


def differences(authoritative: Mapping[str, Any], shadowed: Mapping[str, Any]) -> list[str]:
    """Each place the two comparable grades differ, as `path: authoritative != shadow`."""
    found: list[str] = []
    _walk(comparable(authoritative), comparable(shadowed), "", found)
    return found


def _walk(left: Any, right: Any, path: str, found: list[str]) -> None:
    if isinstance(left, dict) and isinstance(right, dict):
        for key in sorted(set(left) | set(right)):
            _walk(left.get(key), right.get(key), f"{path}.{key}" if path else str(key), found)
    elif isinstance(left, list) and isinstance(right, list) and len(left) == len(right):
        for index, (a, b) in enumerate(zip(left, right, strict=True)):
            _walk(a, b, f"{path}[{index}]", found)
    elif left != right:
        found.append(f"{path}: {left!r} != {right!r}")


def compare(
    spec: Mapping[str, Any],
    found: evidence.EvidenceV1,
    authoritative: Mapping[str, Any],
    *,
    source: str,
    plugin_root: Path | None = None,
    stale_judge: str | None = None,
    run_level: str | None = None,
) -> dict[str, Any]:
    """Grade `found` with the evidence engine and compare with the authoritative grade. The engine
    is advisory here: a failure inside it is recorded, never raised into the grade it shadows.
    `run_level` is a reason the caller found that voids the run, which the engine then applies too."""
    try:
        verdict = engine.grade(
            spec, found, engine.kept_from(found, stale_judge=stale_judge), plugin_root=plugin_root, run_level=run_level
        )
        rendered = engine.render(verdict, spec)
        diffs = differences(authoritative, rendered)
        return {"engine": ENGINE, "source": source, "agrees": not diffs, "differences": diffs, "verdict": rendered}
    except Exception as exc:  # the old engine stays authoritative; the shadow reports its own failure
        return {"engine": ENGINE, "source": source, "agrees": False, "error": f"{type(exc).__name__}: {exc}"[:500]}


def write(folder: Path, result: Mapping[str, Any]) -> None:
    layout.write_json(folder / FILE, result)


def row_fields(result: Mapping[str, Any] | None) -> dict[str, Any]:
    """What a summary or regrade row carries of a shadow result: nothing when the engines agree."""
    if result is None or result.get("agrees"):
        return {}
    if result.get("error"):
        return {"shadow_error": result["error"]}
    return {"shadow_disagreements": list(result.get("differences") or [])}


def print_report(result: Mapping[str, Any]) -> None:
    for r in result["runs"]:
        if r["agrees"]:
            continue
        name = layout.run_name(*layout.run_key(r))
        detail = r.get("shadow_error") or "; ".join(r.get("shadow_disagreements") or [])
        print(f"{name} ({r['source']}): disagrees: {detail}")
    coverage = ", ".join(f"{kind} {count}" for kind, count in result["coverage"].items())
    print(
        f"shadow: {result['attempts']} attempt(s), {result['agreeing']} grade(s) agree, "
        f"{result['disagreeing']} disagree; coverage: {coverage}; "
        f"gate of {result['gate']['count']} {'met' if result['gate']['met'] else 'not met'}"
    )
    if result["skipped"]["scenarios"]:
        print(f"skipped scenario(s) not in this checkout: {', '.join(result['skipped']['scenarios'])}", file=sys.stderr)
