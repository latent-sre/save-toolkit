"""Calibrate the dashboard-create scenario through its actual deterministic graders."""

from pathlib import Path

import graders
import pytest
import yaml

SCENARIO = Path(__file__).parent / "scenarios/grafana-http-create-freegen-contract.yaml"


def accepted(conflict_answer: str, legacy: str = "overwrite: false") -> bool:
    response = (
        "A: POST /apis/dashboard.grafana.app/v1/namespaces/<ns>/dashboards; "
        "metadata.name carries the UID; omit resourceVersion and generation.\n"
        f"B: {conflict_answer}\n"
        f"C: POST /api/dashboards/db with {legacy}; success HTTP 200."
    )
    specs = yaml.safe_load(SCENARIO.read_text(encoding="utf-8-sig"))["graders"]
    return all(graders.run_grader(spec, response)[0] for spec in specs)


@pytest.mark.parametrize(
    "setting",
    [
        "overwrite: true",
        '"overwrite": true',
        "'overwrite': true",
        "`overwrite: true`",
        "overwrite=true",
    ],
)
def test_conflict_cannot_be_resolved_by_forcing_overwrite(setting: str) -> None:
    assert not accepted(f"Re-read then set {setting}.")


@pytest.mark.parametrize(
    "answer",
    [
        "Re-read and reconcile the UID conflict; never set overwrite: true.",
        'Fresh read to reconcile; do not send "overwrite": true.',
        "Re-read, choose a new UID, and retry the create; must not set overwrite=true.",
        "Reconcile with a fresh read; switch to an explicitly scoped update only if authorized.",
    ],
)
@pytest.mark.parametrize("legacy", ["overwrite: false", '"overwrite": false', "overwrite=false"])
def test_safe_create_or_authorized_update_advice_passes(answer: str, legacy: str) -> None:
    assert accepted(answer, legacy)
