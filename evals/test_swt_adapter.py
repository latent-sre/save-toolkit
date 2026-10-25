"""Offline SWT field, leakage, admission and assessment controls."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from swt_adapter import core


def patch(path="tests/test_behavior.py", body="assert behavior() == 1"):
    return f"diff --git a/{path} b/{path}\n--- a/{path}\n+++ b/{path}\n@@ -0,0 +1 @@\n+{body}\n"


def row():
    return dict(
        instance_id="org__repo-1",
        repo="org/repo",
        base_commit="a" * 40,
        version="1.0",
        difficulty="1-4 hours",
        problem_statement="Behavior must be one.",
        patch=patch("pkg/behavior.py", "return 1"),
        test_patch=patch(),
        hints_text="HIDDEN_HINT",
        FAIL_TO_PASS='["HIDDEN_TEST"]',
        PASS_TO_PASS="[]",
    )


def manifest(r):
    return dict(
        schema_version=1,
        status="proposed",
        upstream_revision=core.UPSTREAM_REVISION,
        dataset=core.DATASET,
        dataset_revision=core.DATASET_REVISION,
        cases=[
            dict(
                instance_id=r["instance_id"],
                row_sha256=core.digest(r),
                test_roots=["tests/"],
                complexity="1-4 hours",
                rationale="Multi-step behavior",
            )
        ],
    )


def test_original_field_roles_and_filter_exclusion():
    r = row()
    m = manifest(r)
    assert core.select(m, [r], set()) == [r]
    with pytest.raises(ValueError, match="excluded"):
        core.select(m, [r], {r["instance_id"]})
    upstream = core.transform(r)
    assert upstream["golden_code_patch"] == r["patch"]
    assert upstream["golden_test_patch"] == r["test_patch"]
    assert "patch" not in upstream
    assert "patch" in r  # no upstream in-place mutation of source identity
    with pytest.raises(ValueError, match="identity"):
        core.select(m, [{**r, "patch": "tampered"}], set())


def test_public_input_is_explicit_allowlist_and_export_is_original_array(tmp_path):
    r = row()
    public = core.author_input(r)
    assert set(public) == {"instance_id", "repo", "base_commit", "problem_statement"}
    assert "HIDDEN" not in json.dumps(public)
    paths = core.stage(manifest(r), [r], set(), tmp_path / "stage")
    assert json.loads(Path(paths["dataset"]).read_text()) == [r]
    assert json.loads(Path(paths["author"]).read_text()) == [public]
    with pytest.raises(ValueError, match="exists"):
        core.stage(manifest(r), [r], set(), tmp_path / "stage")


@pytest.mark.parametrize(
    "bad",
    [
        patch("pkg/behavior.py"),
        patch("../tests/test_x.py"),
        patch("tests/test_x.py", 'assert "golden_code_patch" in open("source.py").read()'),
        patch("tests/test_x.py", 'assert "return 1" in inspect.getsource(behavior)'),
        patch("tests/test_x.py", 'import subprocess; subprocess.run(["git", "show"])'),
    ],
)
def test_non_test_or_patch_text_admission_control(bad):
    assert core.admit_patch(bad, ["tests/"])["state"] == "FAIL"


def test_semantic_review_is_never_inferred_from_differential_execution():
    r = row()
    evidence = {v: {"completed": True, "patch_applied": True, "tests": {"case": "PASSED"}} for v in core.VARIANTS}
    evidence["pred_pre"]["tests"]["case"] = "FAILED"
    evidence["gold_pre"]["tests"]["case"] = "FAILED"
    report = {
        r["instance_id"]: {
            "patch_is_None": False,
            "patch_exists": True,
            "patch_successfully_applied": True,
            "resolved": True,
            "added_f2p": 1,
        }
    }
    result = core.assess(r["instance_id"], report, evidence, core.admit_patch(patch(), ["tests/"]))
    assert result["mechanical"] == "PASS"
    assert result["relevance"] == "UNVERIFIED"
    assert result["verdict"] == "INCONCLUSIVE"
    assert result["upstream_report"] == report
    assert (
        core.assess(
            r["instance_id"],
            report,
            evidence,
            core.admit_patch(patch(), ["tests/"]),
            relevance={
                "state": "PASS",
                "reviewer": "human",
                "patch_sha256": hashlib.sha256(patch().encode()).hexdigest(),
                "reason": "Behavior reproduces issue.",
            },
        )["verdict"]
        == "PASS"
    )


@pytest.mark.parametrize(
    ("pre", "post"), [("FAILED", "FAILED"), ("PASSED", "PASSED"), ("ERROR", "ERROR"), ("ERROR", "PASSED")]
)
def test_always_fail_pass_both_unrelated_import_and_error_to_pass_controls(pre, post):
    r = row()
    evidence = {v: {"completed": True, "patch_applied": True, "tests": {"case": "PASSED"}} for v in core.VARIANTS}
    evidence["gold_pre"]["tests"]["case"] = "FAILED"
    evidence["pred_pre"]["tests"]["case"] = pre
    evidence["pred_post"]["tests"]["case"] = post
    report = {
        r["instance_id"]: {
            "patch_is_None": False,
            "patch_exists": True,
            "patch_successfully_applied": True,
            "resolved": True,
            "added_f2p": 1,
        }
    }
    result = core.assess(r["instance_id"], report, evidence, core.admit_patch(patch(), ["tests/"]))
    assert result["mechanical"] == "FAIL"
    assert result["verdict"] == "FAIL"


def test_incomplete_or_malformed_evidence_cannot_be_success():
    admission = core.admit_patch(patch(), ["tests/"])
    assert core.assess("id", {}, {}, admission)["verdict"] == "INCONCLUSIVE"
    assert admission["state"] == "PASS"
    assert core.admit_patch("", ["tests/"])["state"] == "FAIL"


def test_rendered_output_reads_are_admitted_but_source_introspection_is_not():
    assert (
        core.admit_patch(patch(body='assert "expected" in (outdir / "index.html").read_text()'), ["tests/"])["state"]
        == "PASS"
    )
    assert core.admit_patch(patch(body='assert "fixed" in Path(__file__).read_text()'), ["tests/"])["state"] == "FAIL"


def test_failed_gold_control_is_inconclusive_not_candidate_success():
    r = row()
    variants = {v: {"completed": True, "patch_applied": True, "tests": {"case": "PASSED"}} for v in core.VARIANTS}
    variants["pred_pre"]["tests"]["case"] = "FAILED"
    report = {
        r["instance_id"]: {
            "patch_is_None": False,
            "patch_exists": True,
            "patch_successfully_applied": True,
            "resolved": True,
        }
    }
    assert (
        core.assess(r["instance_id"], report, variants, core.admit_patch(patch(), ["tests/"]))["mechanical"]
        == "INCONCLUSIVE"
    )
