"""The review's managed hygiene command stays within the existing narrow guard."""

from pathlib import Path

import pytest

from testkit import guard_decision, guard_payload, run_guard

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("tool", ["Bash", "PowerShell"])
def test_review_documents_guarded_named_capture_hygiene(tool: str) -> None:
    reference = (ROOT / "skills/grafana/references/read-only-review.md").read_text(encoding="utf-8")
    command = 'python -I "<absolute-installed-path>/grafana_workflow.py" analyze --source-id capture-one --analysis hygiene --agent-json'
    assert command in reference
    installed = command.replace("<absolute-installed-path>", (ROOT / "skills/grafana/scripts").as_posix())
    assert guard_decision(run_guard(guard_payload(installed, tool_name=tool))) == "allow"
    arbitrary = f'python -I "{ROOT.as_posix()}/skills/grafana/scripts/dashboard_hygiene.py" dashboard.json --format json'
    assert guard_decision(run_guard(guard_payload(arbitrary, tool_name=tool))) == "deny"
