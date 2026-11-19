"""The review's offline hygiene check grants no guarded execution path."""

from pathlib import Path

import pytest

from testkit import guard_decision, guard_payload, run_guard

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("tool", ["Bash", "PowerShell"])
def test_review_hygiene_check_stays_outside_the_guard(tool: str) -> None:
    reference = (ROOT / "skills/grafana/references/dashboard-reading.md").read_text(encoding="utf-8")
    assert "grafana_workflow.py" not in reference
    arbitrary = f'python -I "{ROOT.as_posix()}/skills/grafana/scripts/dashboard_hygiene.py" dashboard.json --format json'
    assert guard_decision(run_guard(guard_payload(arbitrary, tool_name=tool))) == "deny"
