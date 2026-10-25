"""Deterministic, offline selection and immutable case identity contracts."""

import copy
import hashlib
import json

import pytest
from swebench_adapter.selection import case_identity, identity_digest, resolve_task, select_tasks

REVISION = "a" * 40
IMAGE_DIGEST = "sha256:" + "b" * 64


def row(repo, suffix="a", crash=False, difficulty="<15 min fix"):
    return {
        "instance_id": f"{repo.replace('/', '__')}-{suffix}",
        "repo": repo,
        "base_commit": "c" * 40,
        "difficulty": difficulty,
        "problem_statement": "PRIVATE PROBLEM " + ("Traceback (most recent call last)" if crash else "bad value"),
        "FAIL_TO_PASS": ["tests/test_bug.py::test_bug"],
        "PASS_TO_PASS": ["tests/test_existing.py::test_existing"],
        "image": f"registry.example/{repo}:{suffix}",
        "eval_script": "PRIVATE VERIFIER SCRIPT",
        "log_parser": "pytest",
        "eval_type": "pytest",
        "version": "1.0",
        "patch": "PRIVATE GOLD PATCH",
        "test_patch": "PRIVATE TEST PATCH",
        "hints_text": "PRIVATE HINTS",
    }


def population():
    return [row(f"org/repo{i:02}", suffix, crash=suffix == "c" and i >= 7)
            for i in range(11) for suffix in ("a", "b", "c")]


def licences():
    return {f"org/repo{i:02}": "BSD-3-Clause; upstream LICENSE at pinned base commit" for i in range(11)}


def test_seed_sorted_repositories_and_backward_balance_are_frozen():
    rows = population()
    manifest = select_tasks(list(reversed(rows)), REVISION, licences())
    assert manifest == select_tasks(rows, REVISION, licences())
    assert manifest["seed"] == 20261018
    assert manifest["dataset"] == "SWE-bench/SWE-bench_Verified"
    assert manifest["revision"] == REVISION
    assert [task["instance_id"] for task in manifest["tasks"]] == [
        "org__repo00-a", "org__repo01-b", "org__repo02-a", "org__repo03-b", "org__repo04-c",
        "org__repo05-c", "org__repo06-a", "org__repo07-c", "org__repo08-c", "org__repo09-c",
    ]
    assert manifest["balance"] == {"crash": 3, "wrong behavior": 7, "satisfied": True}


def test_manifest_contains_only_public_metadata_and_hashes():
    manifest = select_tasks(population(), REVISION, licences())
    assert set(manifest) == {"schema_version", "dataset", "revision", "seed", "difficulty_field", "recipe", "balance", "tasks"}
    assert set(manifest["tasks"][0]) == {"instance_id", "repo", "defect_type", "licence", "field_hashes", "row_sha256"}
    serialized = json.dumps(manifest)
    for secret in ("PRIVATE PROBLEM", "PRIVATE VERIFIER SCRIPT", "PRIVATE GOLD PATCH", "PRIVATE TEST PATCH", "PRIVATE HINTS"):
        assert secret not in serialized
    selected = resolve_task(manifest, population(), manifest["tasks"][0]["instance_id"])
    assert selected["image"] == "registry.example/org/repo00:a"
    assert selected["eval_script"] == "PRIVATE VERIFIER SCRIPT"
    selected["FAIL_TO_PASS"].clear()
    assert resolve_task(manifest, population(), manifest["tasks"][0]["instance_id"])["FAIL_TO_PASS"]


def test_difficulty_filter_does_not_substitute_later_repository():
    rows = population()
    rows += [row("aaa/ineligible", difficulty="1-4 hours")]
    assert select_tasks(rows, REVISION, licences())["tasks"][0]["repo"] == "org/repo00"
    with pytest.raises(ValueError, match="10"):
        select_tasks([r for r in rows if r["repo"] > "org/repo01"], REVISION, licences())


def test_exhausted_minority_is_reported_without_task_substitution():
    rows = population()
    for task in rows:
        if task["repo"] == "org/repo07":
            task["problem_statement"] = "Wrong result"
    manifest = select_tasks(rows, REVISION, licences())
    assert len(manifest["tasks"]) == 10
    assert manifest["balance"] == {"crash": 2, "wrong behavior": 8, "satisfied": False}
    assert manifest["tasks"][-1]["repo"] == "org/repo09"


@pytest.mark.parametrize("field,value", [
    ("difficulty", "15 min - 1 hour"), ("base_commit", "d" * 40),
    ("problem_statement", "changed"), ("FAIL_TO_PASS", ["other"]), ("PASS_TO_PASS", ["other"]),
    ("image", "different:image"), ("eval_script", "changed"), ("log_parser", "changed"),
    ("eval_type", "changed"), ("version", "2.0"), ("patch", "changed"), ("test_patch", "changed"),
    ("hints_text", "changed"), ("new_metadata", "changed"),
])
def test_changed_selected_full_row_is_rejected(field, value):
    rows = population()
    manifest = select_tasks(rows, REVISION, licences())
    rows[0][field] = value
    with pytest.raises(ValueError):
        resolve_task(manifest, rows, manifest["tasks"][0]["instance_id"])


@pytest.mark.parametrize("revision", ["main", "latest", "", "abc123", "A" * 40, None])
def test_revision_must_be_an_immutable_commit(revision):
    with pytest.raises(ValueError, match="revision"):
        select_tasks(population(), revision, licences())


@pytest.mark.parametrize("field,value", [
    ("base_commit", "main"), ("problem_statement", ""), ("image", ""),
    ("FAIL_TO_PASS", '["test"]'), ("PASS_TO_PASS", [1]), ("FAIL_TO_PASS", []),
    ("eval_script", None), ("log_parser", ""), ("eval_type", ""), ("patch", None),
])
def test_invalid_full_row_fields_are_rejected(field, value):
    rows = population()
    rows[0][field] = value
    with pytest.raises(ValueError):
        select_tasks(rows, REVISION, licences())


def test_duplicate_ids_and_missing_licence_evidence_are_rejected():
    rows = population()
    with pytest.raises(ValueError, match="duplicate"):
        select_tasks([*rows, copy.deepcopy(rows[0])], REVISION, licences())
    evidence = licences()
    del evidence["org/repo00"]
    with pytest.raises(ValueError, match="licence"):
        select_tasks(rows, REVISION, evidence)
    evidence["org/repo00"] = ""
    with pytest.raises(ValueError, match="licence"):
        select_tasks(rows, REVISION, evidence)


@pytest.mark.parametrize("mutation", ["extra", "seed", "recipe", "balance", "task", "hash", "version"])
def test_modified_manifest_is_rejected(mutation):
    rows = population()
    manifest = select_tasks(rows, REVISION, licences())
    if mutation == "extra":
        manifest["problem_statement"] = "injection"
    elif mutation == "seed":
        manifest["seed"] = 1
    elif mutation == "recipe":
        manifest["recipe"] = "different"
    elif mutation == "balance":
        manifest["balance"]["satisfied"] = False
    elif mutation == "task":
        manifest["tasks"][0]["unexpected"] = "field"
    elif mutation == "version":
        manifest["schema_version"] = True
    else:
        manifest["tasks"][0]["field_hashes"]["patch"] = "0" * 64
    with pytest.raises(ValueError):
        resolve_task(manifest, rows, rows[0]["instance_id"])


def test_resolve_refuses_unselected_and_duplicate_ids():
    rows = population()
    manifest = select_tasks(rows, REVISION, licences())
    with pytest.raises(ValueError, match="selected"):
        resolve_task(manifest, rows, "org__repo10-a")
    with pytest.raises(ValueError, match="duplicate"):
        resolve_task(manifest, [*rows, rows[0]], rows[0]["instance_id"])


def test_identity_binds_approved_components_without_private_fields():
    task = row("org/repo")
    identity = case_identity(task, REVISION, IMAGE_DIGEST)
    assert identity == {
        "dataset": "SWE-bench/SWE-bench_Verified", "revision": REVISION,
        "instance_id": "org__repo-a", "base_commit": "c" * 40,
        "problem_statement_sha256": hashlib.sha256(task["problem_statement"].encode()).hexdigest(),
        "fail_to_pass_sha256": hashlib.sha256(b'["tests/test_bug.py::test_bug"]').hexdigest(),
        "pass_to_pass_sha256": hashlib.sha256(b'["tests/test_existing.py::test_existing"]').hexdigest(),
        "image_digest": IMAGE_DIGEST,
    }
    assert identity_digest(identity) == identity_digest(dict(reversed(list(identity.items()))))
    for field in identity:
        changed = copy.deepcopy(identity)
        if field == "dataset":
            changed[field] = "other/dataset"
            with pytest.raises(ValueError):
                identity_digest(changed)
        else:
            changed[field] = ({"revision": "d" * 40, "base_commit": "d" * 40,
                               "image_digest": "sha256:" + "d" * 64,
                               "instance_id": "org__repo-b"}.get(field, "d" * 64))
            assert identity_digest(changed) != identity_digest(identity)


@pytest.mark.parametrize("digest", ["image:latest", "b" * 64, "sha256:abc", "sha256:" + "B" * 64, None])
def test_identity_requires_pinned_image_digest(digest):
    with pytest.raises(ValueError, match="image_digest"):
        case_identity(row("org/repo"), REVISION, digest)


def test_identity_rejects_missing_components_and_extra_data():
    identity = case_identity(row("org/repo"), REVISION, IMAGE_DIGEST)
    for field in identity:
        incomplete = dict(identity)
        del incomplete[field]
        with pytest.raises(ValueError):
            identity_digest(incomplete)
    with pytest.raises(ValueError):
        identity_digest({**identity, "patch": "private"})


def test_balancing_can_replace_crashes_with_wrong_behavior():
    rows = population()
    for task in rows:
        task["problem_statement"] = "wrong value" if "Traceback" in task["problem_statement"] else "Traceback (most recent call last)"
    manifest = select_tasks(rows, REVISION, licences())
    assert manifest["balance"] == {"crash": 7, "wrong behavior": 3, "satisfied": True}
    assert [task["instance_id"] for task in manifest["tasks"]][-3:] == [
        "org__repo07-c", "org__repo08-c", "org__repo09-c",
    ]


def test_case_identity_changes_for_each_task_component_and_preserves_test_order():
    task = row("org/repo")
    original = identity_digest(case_identity(task, REVISION, IMAGE_DIGEST))
    for field, value in [
        ("instance_id", "org__repo-b"), ("base_commit", "d" * 40),
        ("problem_statement", "other issue"), ("FAIL_TO_PASS", ["other_test"]),
        ("PASS_TO_PASS", ["other_existing_test"]),
    ]:
        changed = {**task, field: value}
        assert identity_digest(case_identity(changed, REVISION, IMAGE_DIGEST)) != original
    ordered = {**task, "PASS_TO_PASS": ["test_a", "test_b"]}
    reversed_tests = {**task, "PASS_TO_PASS": ["test_b", "test_a"]}
    assert case_identity(ordered, REVISION, IMAGE_DIGEST) != case_identity(reversed_tests, REVISION, IMAGE_DIGEST)
    with pytest.raises(ValueError, match="revision"):
        case_identity(task, "main", IMAGE_DIGEST)


def test_empty_preservation_list_and_empty_hints_are_valid():
    rows = population()
    rows[0]["PASS_TO_PASS"] = []
    rows[0]["hints_text"] = ""
    manifest = select_tasks(rows, REVISION, licences())
    assert resolve_task(manifest, rows, rows[0]["instance_id"])["PASS_TO_PASS"] == []


def test_missing_required_verifier_field_is_rejected_before_selection():
    rows = population()
    del rows[0]["eval_script"]
    with pytest.raises(ValueError, match="missing"):
        select_tasks(rows, REVISION, licences())


@pytest.mark.parametrize("version", [None, "", 1])
def test_version_required_by_pinned_verifier_is_validated(version):
    rows = population()
    rows[0]["version"] = version
    with pytest.raises(ValueError):
        select_tasks(rows, REVISION, licences())


def test_missing_verifier_version_is_rejected():
    rows = population()
    del rows[0]["version"]
    with pytest.raises(ValueError, match="missing"):
        select_tasks(rows, REVISION, licences())
