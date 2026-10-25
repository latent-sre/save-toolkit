"""Specification and oracle calibration tests for the `python-engineering` skill."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import yaml
from probe import catalog as probe_catalog

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "skills" / "python-engineering"
SKILL_MD = SKILL_DIR / "SKILL.md"
REFERENCES_DIR = SKILL_DIR / "references"
ORACLE_PATH = ROOT / "evals" / "oracles" / "python-engineering" / "evaluate_cases.py"

EXPECTED_REFERENCES = (
    "starting-code.md",
    "refactoring-playbook.md",
    "refactoring-tools.md",
    "dependencies.md",
    "quality-gates.md",
)

EXPECTED_PLAYBOOK_RECIPES = (
    "Extract and Inline Function",
    "Extract and Inline Variable",
    "Extract and Inline Class",
    "Extract Module and Move Function/Class/Symbol",
    "Rename Symbol and Change Function Declaration",
    "Introduce Parameter Object",
    "Split Phase",
    "Separate Query from Modifier",
    "Decompose and Consolidate Conditionals",
    "Introduce Guard Clauses",
    "Replace Conditional Dispatch with Polymorphism",
    "Parameterize Function and Consolidate Genuine Behavioral Duplication",
    "Encapsulate Mutable State and Make Dependencies Explicit",
    "Remove Middle Man and Simplify Unnecessary Abstractions",
    "Replace Unnecessary Inheritance with Delegation or Composition",
    "Introduce Narrow Testing or Integration Boundaries",
    "Preparatory Refactoring Before Implementing a Feature",
    "Incremental Component or Dependency Replacement",
    "Remove Dead Code After Checking Static and Dynamic Usage",
)


def _load_oracle_module():
    spec = importlib.util.spec_from_file_location("python_engineering_eval_oracle", ORACLE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["python_engineering_eval_oracle"] = module
    spec.loader.exec_module(module)
    return module


def _split_frontmatter(text: str) -> tuple[dict[str, object], str]:
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, flags=re.DOTALL)
    assert match is not None, "SKILL.md must begin with YAML frontmatter"
    meta = yaml.safe_load(match.group(1))
    assert isinstance(meta, dict)
    return meta, match.group(2)


def test_required_file_structure_and_no_extra_files() -> None:
    assert SKILL_MD.is_file()
    assert REFERENCES_DIR.is_dir()
    actual_top = sorted(p.name for p in SKILL_DIR.iterdir())
    assert actual_top == ["SKILL.md", "references"]
    actual_refs = sorted(p.name for p in REFERENCES_DIR.iterdir())
    assert actual_refs == sorted(EXPECTED_REFERENCES)


def test_skill_frontmatter_and_word_budget() -> None:
    raw = SKILL_MD.read_text(encoding="utf-8")
    meta, body = _split_frontmatter(raw)
    assert set(meta.keys()) <= {"name", "description", "argument-hint", "disable-model-invocation", "compatibility"}
    assert meta["name"] == "python-engineering"
    description = str(meta["description"])
    assert len(description) <= 1024
    assert "Triggers:" in description
    quoted_triggers = re.findall(r'"([^"]+)"', description.split("Triggers:", 1)[1])
    assert 2 <= len(quoted_triggers) <= 4
    body_words = len(body.split())
    assert 550 <= body_words <= 950, f"Expected SKILL.md body near 600-900 words, got {body_words}"


def test_skill_sections_routing_and_universal_workflow() -> None:
    _, body = _split_frontmatter(SKILL_MD.read_text(encoding="utf-8"))
    for heading in (
        "## Primary Objectives",
        "## Engineering Posture and Decision Rules",
        "## Mandatory Reference Routing",
        "## Universal Execution Workflow",
        "## Verification Integrity, Authority, and Completion",
    ):
        assert heading in body, f"Missing heading {heading}"

    for ref_name in EXPECTED_REFERENCES:
        link_pattern = f"](references/{ref_name})"
        assert link_pattern in body, f"SKILL.md must link directly to references/{ref_name}"

    for step in (
        "A. **Inspect.**",
        "B. **Classify.**",
        "C. **Define success.**",
        "D. **Consult references.**",
        "E. **Establish evidence.**",
        "F. **Execute.**",
        "G. **Verify.**",
        "H. **Assess improvement.**",
    ):
        assert step in body, f"Missing workflow step {step}"

    assert "Problem | Selected approach | Benefit | Cost/risk | Verification" in body


def test_references_have_contents_toc_and_no_evidence_labels() -> None:
    forbidden_labels = ("[verified]", "[sourced]", "[unverified]")
    for path in [SKILL_MD, *(REFERENCES_DIR / name for name in EXPECTED_REFERENCES)]:
        text = path.read_text(encoding="utf-8")
        for label in forbidden_labels:
            assert label not in text, f"{path.name} must not contain runtime evidence label {label}"
        if path != SKILL_MD and len(text.splitlines()) > 100:
            assert "## Contents" in text, f"{path.name} (>100 lines) must include a ## Contents section"


def test_refactoring_playbook_covers_all_required_recipes_and_fields() -> None:
    playbook = (REFERENCES_DIR / "refactoring-playbook.md").read_text(encoding="utf-8")
    for title in EXPECTED_PLAYBOOK_RECIPES:
        assert title in playbook, f"Missing refactoring recipe: {title}"
    for required_field in (
        "- **Trigger:**",
        "- **Preconditions:**",
        "- **Transformation:**",
        "- **Verification:**",
        "- **Avoid when:**",
    ):
        assert playbook.count(required_field) >= 19, f"Expected >=19 occurrences of {required_field}"
    for hazard in (
        "Decorators and wrappers",
        "Dynamic imports and reflection",
        "Public re-exports and entry points",
        "Import-time behavior and circular imports",
        "Mutation, aliasing, and evaluation order",
        "Generator exhaustion",
        "Exception hierarchy and chaining",
        "Serialization and persisted representations",
        "Async cancellation, concurrency, and resource lifetimes",
    ):
        assert hazard in playbook, f"Missing Python hazard coverage: {hazard}"


def test_refactoring_tools_dependencies_and_quality_gates_substance() -> None:
    tools_text = (REFERENCES_DIR / "refactoring-tools.md").read_text(encoding="utf-8")
    for tool_name in ("LibCST", "Rope", "Ruff", "pytest", "mypy", "pyright", "ast"):
        assert tool_name in tools_text, f"Missing tool in refactoring-tools.md: {tool_name}"

    deps_text = (REFERENCES_DIR / "dependencies.md").read_text(encoding="utf-8")
    for dep_topic in ("pyproject.toml", "[dependency-groups]", "uv", "tomllib", "Pydantic", "Hypothesis"):
        assert dep_topic in deps_text, f"Missing topic in dependencies.md: {dep_topic}"

    gates_text = (REFERENCES_DIR / "quality-gates.md").read_text(encoding="utf-8")
    for gate_topic in (
        "Risk-to-Verification Selection Matrix",
        "Advanced Verification Techniques for High-Risk Changes",
        "Verification Integrity and Final Review Rules",
    ):
        assert gate_topic in gates_text, f"Missing section in quality-gates.md: {gate_topic}"


def test_routing_scenarios_for_python_engineering_validate() -> None:
    scenario_dir = ROOT / "evals" / "scenarios"
    expected_ids = {
        "discovery-python-engineering-modernize": "fire",
        "discovery-python-engineering-new-component": "fire",
        "discovery-python-engineering-defers-go-service": "not_fire",
        "discovery-python-engineering-defers-live-incident": "not_fire",
    }
    for scenario_id, expected_routing in expected_ids.items():
        path = scenario_dir / f"{scenario_id}.yaml"
        assert path.is_file(), f"Missing routing scenario {path}"
        spec = probe_catalog.load_scenario(path)
        assert spec["target"] == {"kind": "skill", "name": "python-engineering"}
        assert spec["routing"]["expect"] == expected_routing


def test_oracle_self_calibration_rejects_unimproved_initial_fixtures() -> None:
    oracle = _load_oracle_module()
    results = oracle.run_self_calibration()
    assert len(results) == 12
    for res in results:
        assert not res.passed, f"Initial unimproved fixture for {res.case_id} should not pass post-improvement grader"
