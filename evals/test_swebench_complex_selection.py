"""Complex proposals are reproducible, isolated from the approved easy draw and gated."""

import copy
import json

import pytest
import swebench_repair as cli
from swebench_adapter import complex_selection, selection


@pytest.fixture
def population():
    rows, licences = [], {}
    for instance in complex_selection.CASES:
        repo = instance.rsplit("-", 1)[0].replace("__", "/")
        rows.append({
            "instance_id": instance, "repo": repo, "base_commit": "a" * 40,
            "difficulty": "1-4 hours", "problem_statement": "PRIVATE PROBLEM",
            "FAIL_TO_PASS": ["test_regression"], "PASS_TO_PASS": ["test_existing"],
            "image": "registry/image:tag", "eval_script": "PRIVATE VERIFIER",
            "log_parser": "pytest", "eval_type": "pass_and_fail", "version": "1.0",
            "patch": "PRIVATE FIX", "test_patch": "PRIVATE TEST", "hints_text": "PRIVATE HINT",
        })
        licences[instance] = {"url": f"https://raw.githubusercontent.com/{repo}/{'a' * 40}/LICENSE",
                              "sha256": "b" * 64}
    return rows, licences


def test_proposal_is_order_independent_hidden_free_and_blocked_by_default(population):
    rows, licences = population
    proposed = complex_selection.propose(rows, licences)
    assert proposed == complex_selection.propose(reversed(rows), licences)
    assert len(proposed["tasks"]) == 10
    assert len({task["repo"] for task in proposed["tasks"]}) == 8
    assert "PRIVATE" not in json.dumps(proposed)
    case = rows[0]["instance_id"]
    assert selection.resolve_task(proposed, rows, case, allow_proposed=True) == rows[0]
    with pytest.raises(ValueError, match="human acceptance"):
        selection.resolve_task(proposed, rows, case)
    accepted = copy.deepcopy(proposed)
    accepted["admission"] = "accepted"
    assert selection.resolve_task(accepted, rows, case) == rows[0]
    assert proposed["admission"] == "pending-human-acceptance"


@pytest.mark.parametrize("field,value", [
    ("difficulty", "<15 min fix"), ("patch", "other"), ("test_patch", "other"),
    ("base_commit", "c" * 40), ("new_metadata", "other"),
])
def test_changed_dataset_cannot_reuse_proposal(population, field, value):
    rows, licences = population
    proposed = complex_selection.propose(rows, licences)
    rows[0][field] = value
    with pytest.raises(ValueError):
        complex_selection.resolve(proposed, rows, rows[0]["instance_id"], allow_proposed=True)


@pytest.mark.parametrize("field,value", [("schema_version", True), ("revision", "c" * 40),
                                        ("profile", "easy"), ("admission", True)])
def test_changed_proposal_cannot_bypass_recipe_or_admission(population, field, value):
    rows, licences = population
    proposed = complex_selection.propose(rows, licences)
    proposed[field] = value
    with pytest.raises(ValueError):
        complex_selection.resolve(proposed, rows, rows[0]["instance_id"], allow_proposed=True)


def test_missing_duplicate_and_easy_cases_are_not_substituted(population):
    rows, licences = population
    for data in (rows[:-1], rows + rows[:1]):
        with pytest.raises(ValueError):
            complex_selection.propose(data, licences)
    rows[0]["difficulty"] = "15 min - 1 hour"
    with pytest.raises(ValueError, match="at least one hour"):
        complex_selection.propose(rows, licences)


def test_licence_from_different_revision_is_rejected(population):
    rows, licences = population
    licences[rows[0]["instance_id"]]["url"] = "https://example.test/LICENSE"
    with pytest.raises(ValueError, match="exact base"):
        complex_selection.propose(rows, licences)


def test_cli_proposes_offline_and_refuses_unaccepted_smoke(population, tmp_path, monkeypatch, capsys):
    rows, licences = population
    data = tmp_path / "dataset.json"
    data.write_text(json.dumps({"dataset": selection.DATASET, "revision": complex_selection.REVISION, "rows": rows}))
    license_file = tmp_path / "licences.json"
    license_file.write_text(json.dumps(licences))
    output = tmp_path / "proposal.json"
    assert cli.main(["propose-complex", "--dataset", str(data), "--licences", str(license_file),
                     "--out", str(output)]) == 0
    assert json.loads(output.read_text()) == complex_selection.propose(rows, licences)
    monkeypatch.setattr(cli, "load_config", lambda _path: {"images": {row["instance_id"]: {} for row in rows}})
    def must_not_preflight():
        pytest.fail("unaccepted smoke reached dependency/daemon preparation")
    monkeypatch.setattr(cli, "dependency_problems", must_not_preflight)
    assert cli.main(["smoke", "--selection", str(output), "--dataset", str(data), "--config", "unused.json",
                     "--out", str(tmp_path / "smoke")]) == 3
    assert "human acceptance" in capsys.readouterr().err
    assert not (tmp_path / "smoke").exists()
