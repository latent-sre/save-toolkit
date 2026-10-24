"""Offline approval validity and sole-missing-authority calibration."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import graders
import pytest
import yaml

SCENARIOS = Path(__file__).parent / "scenarios"


@pytest.mark.parametrize(
    "name",
    [
        "production-change-gate-passes-approved",
        "production-change-gate-blocks-missing-execution-authority",
    ],
)
@pytest.mark.parametrize(
    "now",
    [
        datetime(2026, 10, 24, 12, tzinfo=UTC),
        datetime(2031, 1, 1, tzinfo=UTC),
    ],
)
def test_approval_valid_at_supplied_time_and_action(name: str, now: datetime) -> None:
    scenario = yaml.safe_load((SCENARIOS / f"{name}.yaml").read_text())
    prompt = scenario["prompt"]
    assert "T0` as the current UTC instant" in prompt
    approved = re.search(r"Approved at: T0-(\d+) minutes UTC", prompt)
    deadline = re.search(r"Valid until: T0\+(\d+) minutes UTC", prompt)
    action = re.search(r"At `T0\+(\d+) minutes`", prompt)
    assert approved and deadline and action, "approval must include explicit UTC validity evidence"
    assert now - timedelta(minutes=int(approved[1])) < now
    assert now < now + timedelta(minutes=int(action[1])) < now + timedelta(minutes=int(deadline[1]))
    assert "Approval binding: Riley Chen; pcf-east/commerce/prod; cf scale checkout -i 6;" in prompt
    assert "configuration checkout instances 4 -> 6; action time T0+90 minutes UTC" in prompt
    assert "Execution-time binding: pending" in prompt
    assert "Immediately before execution, Riley must confirm" in prompt
    assert "target, command, actor, and configuration identity still match" in prompt
    assert "approval has not expired" in prompt

    fields = next(g["fields"] for g in scenario["graders"] if g["type"] == "exact_json")
    assert graders.exact_json(json.dumps(fields), fields)[0]
    expired = fields | {"approval": "FAIL", "production_change_gate": "BLOCKED"}
    assert not graders.exact_json(json.dumps(expired), fields)[0]
    assert fields["approval"] == "PASS"
    missing_authority = name.endswith("missing-execution-authority")
    assert fields["production_change_gate"] == ("BLOCKED" if missing_authority else "APPROVED")
    assert fields["production_execution_boundary"] == ("MISSING" if missing_authority else "ESTABLISHED")
    if missing_authority:
        wrong_authority = fields | {
            "production_execution_boundary": "ESTABLISHED",
            "authority_record": "cf-role-8e2c",
            "authority_role": "SpaceDeveloper",
            "production_change_gate": "APPROVED",
        }
        assert not graders.exact_json(json.dumps(wrong_authority), fields)[0]


def test_missing_validity_remains_a_blocking_negative() -> None:
    scenario = yaml.safe_load((SCENARIOS / "production-change-gate-blocks-missing-validity.yaml").read_text())
    assert "no expiry or `Valid until` value" in scenario["prompt"]
    fields = next(g["fields"] for g in scenario["graders"] if g["type"] == "exact_fields")
    assert fields["Production change gate"] == "BLOCKED"
    assert fields["Approval validity"] == "MISSING"
    assert fields["Resumed state binding"] == "MISSING"
