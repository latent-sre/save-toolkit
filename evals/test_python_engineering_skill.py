"""Specification and oracle calibration tests for the `python-engineering` skill."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from types import ModuleType

import pytest
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


@pytest.fixture
def oracle():
    return _load_oracle_module()


@pytest.mark.parametrize("body", [
    '"""Not implemented."""\n',
    "def clamp_bps(value: int, ceiling: int = 500) -> int:\n    return value\n",
    "def clamp_bps(value: int, ceiling: int = 500) -> int:\n    return min(value, ceiling)\n",
    "def clamp_bps(value: int, ceiling: int = 500) -> int:\n"
    "    if value < 0:\n        raise ValueError\n    return min(value, ceiling)\n",
    "def clamp_bps(value: int, ceiling: int = 500) -> int:\n"
    "    if ceiling <= 0:\n        raise ValueError\n    return min(value, ceiling)\n",
    "def clamp_bps(value: int, ceiling: int = 1000) -> int:\n"
    "    if value < 0 or ceiling <= 0:\n        raise ValueError\n    return min(value, ceiling)\n",
    "def clamp_bps(value: int, ceiling: int = 500) -> float:\n"
    "    if value < 0 or ceiling <= 0:\n        raise ValueError\n    return float(min(value, ceiling))\n",
])
def test_h1_rejects_missing_or_broken_helper_despite_green_candidate_tests(oracle, tmp_path, body):
    name = "H1_existing_tooling_adequate"
    workspace = oracle.seed_case_workspace(name, tmp_path)
    (workspace / "bps.py").write_text(body, encoding="utf-8")
    (workspace / "tests/test_bps.py").write_text("def test_placeholder() -> None:\n    assert True\n", encoding="utf-8")
    result = oracle.grade_case_h1(workspace, "", oracle.CASE_SPECS[name].expected_references)
    assert result.checks["pytest_passes"] and result.checks["ruff_passes"] and result.checks["mypy_passes"]
    assert not result.passed, "Candidate-owned passing checks cannot establish the requested helper's behavior"


def test_h1_accepts_correct_helper_using_independent_contract_checks(oracle, tmp_path):
    name = "H1_existing_tooling_adequate"
    workspace = oracle.seed_case_workspace(name, tmp_path)
    (workspace / "bps.py").write_text(
        "def clamp_bps(value: int, ceiling: int = 500) -> int:\n"
        "    if value < 0 or ceiling <= 0:\n        raise ValueError\n    return min(value, ceiling)\n",
        encoding="utf-8")
    (workspace / "tests/test_bps.py").write_text("def test_placeholder() -> None:\n    assert True\n", encoding="utf-8")
    result = oracle.grade_case_h1(workspace, "", oracle.CASE_SPECS[name].expected_references)
    assert result.passed, result.checks
    assert result.checks["clamp_bps_contract"]


@pytest.mark.parametrize("include_default", [False, True])
def test_f_requires_default_correlation_even_when_candidate_tests_accept_omission(oracle, tmp_path, include_default):
    name = "F_remove_unnecessary_abstraction"
    workspace = oracle.seed_case_workspace(name, tmp_path)
    fallback = "'NONE'" if include_default else "''"
    (workspace / "audit_formatter.py").write_text(
        "def format_audit_event(event):\n"
        "    base = '|'.join(event[key].strip() for key in ('actor', 'action', 'target'))\n"
        f"    correlation = event.get('correlation_id', {fallback}).strip()\n"
        "    return base + ('|' + correlation if correlation else '')\n", encoding="utf-8")
    (workspace / "tests/test_audit_formatter.py").write_text(
        "from audit_formatter import format_audit_event\n"
        "def test_explicit_correlation():\n"
        "    event = dict(actor='alice', action='ACK', target='inc-1', correlation_id='req-9')\n"
        "    assert format_audit_event(event) == 'alice|ACK|inc-1|req-9'\n", encoding="utf-8")
    result = oracle.grade_case_f(workspace, "", oracle.CASE_SPECS[name].expected_references)
    assert result.checks["pytest_passes"]
    assert result.passed is include_default, result.checks
    assert result.checks["correlation_id_and_contract_work"] is include_default


def extracted_fee_workspace(oracle, path: Path, *, lazy: bool = False, package: bool = False) -> Path:
    name = "C_legacy_characterization_before_decompose"
    workspace = oracle.seed_case_workspace(name, path)
    source = oracle.CASE_SPECS[name].files["fee_engine.py"]
    source = source.replace("(qty * px).quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)",
                            "calculate_notional(qty, px)")
    source = source.replace("(notional * bps / Decimal('10000')).quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)",
                            "_fee(notional, bps)")
    source += ("\ndef _fee(notional, bps):\n"
               "    return (notional * bps / Decimal('10000')).quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)\n")
    statement = "from fee_math import calculate_notional\n"
    if lazy:
        source = source.replace("    total_fee =", "    " + statement + "    total_fee =", 1)
    else:
        source = statement + source
    (workspace / "fee_engine.py").write_text(source, encoding="utf-8")
    helper = workspace / ("fee_math/__init__.py" if package else "fee_math.py")
    helper.parent.mkdir(exist_ok=True)
    helper.write_text("from decimal import Decimal, ROUND_HALF_EVEN\n"
                      "def calculate_notional(qty, px):\n"
                      "    return (qty * px).quantize(Decimal('0.01'), rounding=ROUND_HALF_EVEN)\n", encoding="utf-8")
    test = workspace / "tests/test_fee_engine.py"
    test.write_text(test.read_text() +
                    "\ndef test_void():\n    log = []\n"
                    "    assert process_fills([dict(status='VOID', id='v')], log)['processed'] == 0\n"
                    "    assert log == ['SKIP:v']\n"
                    "\ndef test_maker():\n    log = []\n"
                    "    fills = iter([dict(id='m', qty=100, price='10', tier='VIP', liquidity='MAKER')])\n"
                    "    assert process_fills(fills, log, rebate_bps=Decimal('5'))['total_fee'] == Decimal('0.00')\n",
                    encoding="utf-8")
    return workspace


@pytest.mark.parametrize("lazy, package", [(False, False), (True, False), (False, True)])
def test_c_accepts_sibling_imports_and_restores_the_graders_context(oracle, tmp_path, monkeypatch, lazy, package):
    workspace = extracted_fee_workspace(oracle, tmp_path, lazy=lazy, package=package)
    cached = ModuleType("fee_math")
    monkeypatch.setitem(sys.modules, "fee_math", cached)
    old_path, old_cwd = list(sys.path), Path.cwd()
    name = "C_legacy_characterization_before_decompose"
    result = oracle.grade_case_c(workspace, "", oracle.CASE_SPECS[name].expected_references)
    assert result.checks["pytest_passes"]
    assert result.checks["contract_and_generator_preserved"], result.checks
    assert result.passed, result.checks
    assert sys.path == old_path and Path.cwd() == old_cwd
    assert sys.modules["fee_math"] is cached


def test_c_does_not_reuse_helpers_between_candidates_or_leak_failed_imports(oracle, tmp_path):
    name = "C_legacy_characterization_before_decompose"
    good = extracted_fee_workspace(oracle, tmp_path / "good")
    bad = extracted_fee_workspace(oracle, tmp_path / "bad")
    (bad / "fee_math.py").write_text("raise RuntimeError('broken helper')\n", encoding="utf-8")
    old_path, old_cwd, cached = list(sys.path), Path.cwd(), sys.modules.get("fee_math")
    good_result = oracle.grade_case_c(good, "", oracle.CASE_SPECS[name].expected_references)
    bad_result = oracle.grade_case_c(bad, "", oracle.CASE_SPECS[name].expected_references)
    assert good_result.passed, good_result.checks
    assert not bad_result.checks["contract_and_generator_preserved"]
    assert sys.path == old_path and Path.cwd() == old_cwd
    assert sys.modules.get("fee_math") is cached
