"""Regression contracts for scoped restores and evidence-bound backlog diagnosis."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(path: str) -> str:
    return ' '.join((ROOT / path).read_text(encoding='utf-8').split())


def test_dashboard_restore_requires_operation_written_comparison_before_fresh_token() -> None:
    api = text('skills/grafana/references/http-api.md').split('## Rollback')[1]
    assert 'operation-written state from verified readback' in api
    assert 'Stop on intervening edits or missing comparison evidence' in api
    assert 'restoring query Q0 after writing Q1 must not erase a later title T1' in api
    assert api.index('compare a fresh live read') < api.index('Only after the comparison passes')
    assert 'stop on conflict' in api
    workflow = text('skills/grafana/references/dashboard-operations.md')
    assert 'Rollback first compares a fresh read with that state and stops on intervening edits' in workflow


def test_folder_restore_preserves_intervening_edits_and_parent_authority() -> None:
    api = text('skills/grafana/references/http-api.md').split('## Verify, then record')[0]
    assert 'Save the successful operation-written folder state too' in api
    assert 'including title and parent' in api
    assert 'Stop on intervening edits or missing comparison evidence' in api
    assert 'Only an unchanged state permits restoring' in api
    assert 'A parent move still requires its separately authorized path' in api


def test_pubsub_age_contract_rejects_successful_cohort_as_failure_proof() -> None:
    # FIFO initial cohort remains oldest while every attempted acknowledgement succeeds.
    initial, arrivals_per_second, acknowledgements_per_second = 60_000, 200, 100
    observations = []
    for seconds in (60, 120, 180):
        completed = acknowledgements_per_second * seconds
        assert completed < initial
        observations.append((seconds, completed, initial + arrivals_per_second * seconds - completed))
    assert observations == [(60, 6000, 66000), (120, 12000, 72000), (180, 18000, 78000)]
    skill = text('skills/gcp-ops/SKILL.md')
    assert 'while acknowledgements succeed' in skill
    assert 'Slower age growth alone does not prove completion either' in skill
    assert 'retention expiry' in skill
    assert 'completion rates with ingress and backlog trends' in skill
    assert 'repeated message IDs with failed delivery or acknowledgement evidence' in skill
    assert 'means some messages are never acknowledged' not in skill


def test_reliability_eval_guide_defers_live_status_to_roadmap() -> None:
    guide = text('evals/README.md')
    assert '`RELIABILITY-001` is deferred' not in guide
    assert 'this guide does not duplicate its live status' in guide
    assert '../docs/fleet-roadmap.md#reliability-001--measure-the-timing-repair-on-claude-then-decide-on-the-reliability-lane' in guide
