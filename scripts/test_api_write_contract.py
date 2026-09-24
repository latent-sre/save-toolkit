"""Offline controls validate acceptance assertions, not any production implementation.

The controlled adapter models outcomes, overlap evidence, and failpoint/exit evidence. It
does not create concurrent database sessions or crash a process; passing these controls
does not establish either property in an application. Projects supply the real adapter.
"""
from __future__ import annotations

from copy import deepcopy
import importlib.util
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest
from httpx import Response


ASSET = Path(__file__).resolve().parents[1] / 'skills/backend-craft/assets/test_api_write_contract.py'
spec = importlib.util.spec_from_file_location('api_write_acceptance_asset', ASSET)
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


def controlled_case(fault=None):
    """Small deterministic control for the assertions, deliberately not idempotency code."""
    persisted = {'owner': [], 'other': []}
    ledger = {}
    case = SimpleNamespace(payload={'amount': 1}, changed_payload={'amount': 2})

    def submit(key, payload, scope='owner'):
        ledger_key = (None if fault == 'cross_scope' else scope, key)
        entry = ledger.get(ledger_key)
        if entry:
            saved_payload, effect_id = entry
            if payload != saved_payload and fault != 'conflict_replayed':
                if fault == 'conflict_corrupts_state':
                    persisted[scope][0]['state']['amount'] = 999
                return {'outcome': 'conflict'}
            if fault == 'duplicate_effects':
                persisted[scope].append({'id': f'{scope}-{len(persisted[scope]) + 1}',
                                         'state': dict(payload)})
        else:
            effect_id = f'{scope}-{len(persisted[scope]) + 1}'
            if fault != 'no_effect':
                persisted[scope].append({'id': effect_id, 'state': dict(payload)})
            ledger[ledger_key] = (dict(payload), effect_id)
        return {'outcome': 'completed', 'result_id': effect_id}

    def race(key, payload):
        # Synthetic evidence is appropriate ONLY for validating the acceptance predicates.
        case.overlap_observed = fault != 'no_overlap'
        results = [submit(key, payload), submit(key, payload)]
        if fault == 'still_pending':
            results[1] = {'outcome': 'pending'}
        return results

    def interrupt(phase, key, payload):
        case.failpoint_observed = None if fault == 'no_failpoint' else phase
        case.worker_terminated = fault != 'no_termination'
        if phase == 'after_commit' or fault == 'precommit_survives':
            submit(key, payload)
        return fault != 'interruption_incomplete'

    def restart():
        if fault == 'lost_replay':
            ledger.clear()
        if fault == 'restart_replaces_effect':
            for ledger_key, (payload, effect_id) in list(ledger.items()):
                replacement = f'{effect_id}-replaced'
                scope = ledger_key[0]
                for record in persisted[scope]:
                    if record['id'] == effect_id:
                        record['id'] = replacement
                ledger[ledger_key] = (payload, replacement)
        if fault == 'restart_mutates_state':
            persisted['owner'][0]['state']['amount'] = 999

    case.submit = submit
    case.effects = lambda scope='owner': deepcopy(persisted[scope])
    case.race = race
    case.interrupt = interrupt
    case.restart = restart
    return case


CHECKS = [
    contract.test_concurrent_duplicates_have_one_effect,
    contract.test_changed_payload_conflicts_without_another_effect,
    contract.test_restart_before_commit_allows_one_retry_effect,
    contract.test_restart_after_commit_replays_the_committed_effect,
    contract.test_authorized_scopes_do_not_share_replay_state,
]


@pytest.mark.parametrize('check', CHECKS, ids=lambda check: check.__name__)
def test_correct_control_passes_acceptance_check(check):
    check(controlled_case())


def test_control_effect_snapshots_are_detached():
    case = controlled_case()
    case.submit('snapshot-key', case.payload)
    snapshot = case.effects()
    snapshot[0]['id'] = 'changed'
    snapshot[0]['state']['amount'] = 999
    assert case.effects() == [{'id': 'owner-1', 'state': {'amount': 1}}]


@pytest.mark.parametrize('first_header', [None, 'false'])
@pytest.mark.parametrize('replay_header', ['true', None, 'false'])
def test_starter_adapter_checks_replay_marker_without_requiring_initial_header(first_header, replay_header):
    case = controlled_case()
    submit = case.submit
    first = None

    def starter_submit(key, payload, scope='owner'):
        nonlocal first
        result = submit(key, payload, scope)
        marker = first_header if first is None else replay_header
        response = Response(201, json={'id': result['result_id'], 'status': 'open', 'title': 'Probe'},
                            headers={} if marker is None else {'Idempotent-Replayed': marker})
        if first is None:
            first = response
        else:
            contract.assert_starter_replay_response(first, response)
        return result

    # The project adapter opts into its native HTTP contract; generic effect checks stay portable.
    case.submit = starter_submit
    case.race = lambda key, payload: [starter_submit(key, payload), starter_submit(key, payload)]
    case.overlap_observed = True
    if replay_header == 'true':
        contract.test_concurrent_duplicates_have_one_effect(case)
    else:
        with pytest.raises(AssertionError, match='Idempotent-Replayed'):
            contract.test_concurrent_duplicates_have_one_effect(case)


@pytest.mark.parametrize('fault,check,message', [
    ('duplicate_effects', CHECKS[0], 'expected exactly one persisted business effect'),
    ('no_effect', CHECKS[0], 'expected exactly one persisted business effect'),
    ('no_overlap', CHECKS[0], 'server overlap was not independently observed'),
    ('still_pending', CHECKS[0], 'write did not complete'),
    ('conflict_replayed', CHECKS[1], 'changed payload must conflict'),
    ('conflict_corrupts_state', CHECKS[1], 'conflict changed persisted business effects'),
    ('precommit_survives', CHECKS[2], 'uncommitted effect survived termination'),
    ('lost_replay', CHECKS[3], 'result does not identify the persisted effect'),
    ('restart_replaces_effect', CHECKS[3], 'restart changed the committed effect'),
    ('restart_mutates_state', CHECKS[3], 'restart changed the committed effect'),
    ('cross_scope', CHECKS[4], 'expected exactly one persisted business effect'),
    ('no_failpoint', CHECKS[2], 'requested failpoint was not acknowledged'),
    ('no_termination', CHECKS[2], 'worker process termination was not confirmed'),
    ('interruption_incomplete', CHECKS[2], 'interruption incomplete'),
])
def test_broken_control_fails_the_named_acceptance_assertion(fault, check, message):
    with pytest.raises(AssertionError, match=message):
        check(controlled_case(fault))


def test_missing_project_adapter_errors_instead_of_skipping(tmp_path):
    target = tmp_path / 'test_project_write.py'
    target.write_bytes(ASSET.read_bytes())
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider',
         '--confcutdir', str(tmp_path), str(target)],
        cwd=tmp_path, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "fixture 'write_case' not found" in result.stdout
    assert '5 errors' in result.stdout
    assert 'skipped' not in result.stdout
