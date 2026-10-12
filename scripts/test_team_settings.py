"""Portable settings shape and packaging contracts; these do not prove agent behavior."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

import generate_platform_adapters as adapters

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "skills/stack-profile/assets"
CHILD_KEYS = ("runbooks", "service_cards", "alert_cards", "postmortems", "index")


@pytest.fixture(scope="module")
def validator() -> Draft202012Validator:
    schema = json.loads((ASSETS / "save-toolkit.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def test_example_preserves_existing_defaults(validator: Draft202012Validator) -> None:
    example = yaml.safe_load((ASSETS / "save-toolkit.example.yaml").read_text(encoding="utf-8"))
    assert example == {
        "schema_version": 1,
        "knowledge": {
            "root": "knowledge library",
            "runbooks": "runbooks",
            "service_cards": "operations/services",
            "alert_cards": "operations/alerts",
            "postmortems": "postmortems",
            "index": "operations/index.md",
        },
        "incident": {"display_timezone": "America/New_York"},
    }
    validator.validate(example)


@pytest.mark.parametrize("settings", [
    {"schema_version": 1},
    {"schema_version": 1, "knowledge": {}, "incident": {}},
    {"schema_version": 1, "knowledge": {"root": "."}},
    {"schema_version": 1, "knowledge": {"root": "team docs", "runbooks": "docs/Service Procedures"}},
    {"schema_version": 1, "knowledge": {"root": "équipe", "index": "operations/index.md"}},
    {"schema_version": 1, "incident": {"display_timezone": "UTC"}},
    {"schema_version": 1, "incident": {"display_timezone": "America/Argentina/Buenos_Aires"}},
    {"schema_version": 1, "incident": {"display_timezone": "Etc/GMT+6"}},
])
def test_valid_partial_settings(validator: Draft202012Validator, settings: object) -> None:
    validator.validate(settings)


@pytest.mark.parametrize("settings", [
    {}, [], None,
    {"schema_version": True}, {"schema_version": "1"}, {"schema_version": 2},
    {"schema_version": 1, "runbook": "docs"},
    {"schema_version": 1, "knowledge": None},
    {"schema_version": 1, "knowledge": []},
    {"schema_version": 1, "knowledge": {"runbook": "docs"}},
    {"schema_version": 1, "incident": None},
    {"schema_version": 1, "incident": {"timezone": "UTC"}},
])
def test_invalid_shapes(validator: Draft202012Validator, settings: object) -> None:
    assert not validator.is_valid(settings)


@pytest.mark.parametrize("key", ("root", *CHILD_KEYS))
@pytest.mark.parametrize("value", [
    "", " ", 3, False, None, [], {},
    "/runbooks", "C:/runbooks", "C:runbooks", "//server/share", "\\\\server\\share",
    "docs\\runbooks", "../runbooks", "docs/../runbooks", "docs/..", "./docs", "docs/./runbooks",
    "docs/.", "docs//runbooks", "docs/", "docs/ /runbooks",
    "docs\nrunbooks", "docs\trunbooks", "docs\u0000runbooks", "docs\u007frunbooks", "docs\u0085runbooks",
    "docs\n", "docs/<runbooks>", "docs/ru*nbooks", "docs/ru?nbooks", 'docs/ru"nbooks', "docs/ru|nbooks",
    "$HOME/runbooks", "docs/${RUNBOOKS}", "`runbooks`", "~/runbooks", "docs/~user",
    "https://example.com/runbooks",
])
def test_invalid_paths(validator: Draft202012Validator, key: str, value: object) -> None:
    assert not validator.is_valid({"schema_version": 1, "knowledge": {key: value}})


@pytest.mark.parametrize("key", CHILD_KEYS)
def test_child_path_cannot_be_root(validator: Draft202012Validator, key: str) -> None:
    assert not validator.is_valid({"schema_version": 1, "knowledge": {key: "."}})


@pytest.mark.parametrize("value", [
    "", " ", 3, False, None, "EST", "-05:00", "UTC-5", "America", "America/",
    "/New_York", "America//New_York", "America/New York", "America/New_York\n",
])
def test_invalid_timezone_shape(validator: Draft202012Validator, value: object) -> None:
    assert not validator.is_valid({"schema_version": 1, "incident": {"display_timezone": value}})


def test_timezone_shape_does_not_claim_database_validation(validator: Draft202012Validator) -> None:
    # A plausible but invented zone passes shape validation; the consumer must check existence.
    validator.validate({"schema_version": 1, "incident": {"display_timezone": "Example/Unknown_Zone"}})


@pytest.mark.parametrize("skill", [
    "stack-profile", "incident-investigation", "operational-learning", "runbook",
])
def test_consumers_link_shared_contract(skill: str) -> None:
    source = ROOT / "skills" / skill / "SKILL.md"
    text = source.read_text(encoding="utf-8")
    reference = ROOT / "skills/stack-profile/references/team-settings.md"
    assert reference.is_file()
    if skill == "stack-profile":
        links = re.findall(r"\]\(([^)]+team-settings\.md)\)", text)
        assert links, "the owning skill must link its shared settings contract"
        for link in links:
            assert (source.parent / link).resolve() == reference
    else:
        # Cross-skill Markdown links escape the owned bundle and fail check_links.
        # Other consumers use the existing installed-resource addressing contract.
        assert "`${CLAUDE_PLUGIN_ROOT}/skills/stack-profile/references/team-settings.md`" in text
        assert not re.findall(r"\]\(([^)]+team-settings\.md)\)", text)


def test_assets_are_carried_into_workspace_adapter() -> None:
    outputs = adapters.expected_outputs(ROOT)
    for filename in ("save-toolkit.example.yaml", "save-toolkit.schema.json"):
        generated = Path(".github/skills/stack-profile/assets") / filename
        assert outputs[generated] == (ASSETS / filename).read_bytes()
    reference = Path(".github/skills/stack-profile/references/team-settings.md")
    assert reference in outputs
    for skill in ("stack-profile", "incident-investigation", "operational-learning", "runbook"):
        source = Path(".github/skills") / skill / "SKILL.md"
        text = outputs[source].decode("utf-8")
        assert "${CLAUDE_PLUGIN_ROOT}" not in text
        if skill == "stack-profile":
            links = re.findall(r"\]\(([^)]+team-settings\.md)\)", text)
            assert links
            for link in links:
                assert (ROOT / source.parent / link).resolve() == (ROOT / reference).resolve()
        else:
            assert "the installed `stack-profile` skill's `references/team-settings.md` resource" in text
