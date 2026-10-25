"""Admission and published v1 mappings stay useful without optional Harbor."""
import json
from pathlib import Path

import pytest
from harbor_adapter.contracts import load_manifest, sha256
from harbor_adapter.runner import CHECKS, admit, make_record
from probe.records import RecordV1


@pytest.fixture
def case():
    return load_manifest(Path(__file__).parent / 'manifests/wp09-terminal-complex5.json')['cases'][0]


def test_no_unadmitted_execution(case, tmp_path):
    bound = {'candidate': 'exact-digest'}
    with pytest.raises(ValueError, match='admission'):
        admit({}, bound, case)
    smoke = {'format':'wp09-terminal-smoke','schema_version':1,'binding':bound,
             'case_id':case['local_case_id'],'checks':dict.fromkeys(CHECKS, True),
             'cleanup':[{'present':False}], 'error':None,'model_calls':0}
    path = tmp_path / 'smoke.json'
    path.write_text(json.dumps(smoke))
    accepted = {'format': 'wp09-terminal-admission', 'schema_version': 1, 'binding': bound,
                'accepted': True, 'human_owner': 'owner', 'case_smoke': {case['local_case_id']: {'sha256':sha256(path), 'evidence_path': 'smoke.json'}}}
    admit(accepted, bound, case, base=tmp_path)
    for check in CHECKS:
        broken = json.loads(json.dumps(smoke))
        broken['checks'][check] = False
        path.write_text(json.dumps(broken))
        accepted['case_smoke'][case['local_case_id']]['sha256'] = sha256(path)
        with pytest.raises(ValueError, match='smoke'):
            admit(accepted, bound, case, base=tmp_path)
    with pytest.raises(ValueError, match='admission'):
        admit(accepted, {'candidate': 'other'}, case, base=tmp_path)
    path.write_text(json.dumps(smoke))
    with pytest.raises(ValueError, match='digest'):
        admit(accepted, bound, case, base=tmp_path)


@pytest.mark.parametrize('state', ['PASS', 'FAIL', 'INCONCLUSIVE'])
def test_v1_preserves_assessment_after_cleanup_and_billing_failure(case, state):
    record = make_record(
        case=case,
        candidate={'plugin_root':'/fixture','plugin_commit':None,'plugin_inputs_dirty':None,'plugin_source_sha256':None},
        runner={'runner_commit':None,'runner_source_dirty':None,'runner_source_sha256':None},
        runtime={'cli_version':'fixture','host_platform':{},'host_identity':None},
        model='model',label='candidate',started='2026-10-25T00:00:00+00:00',ended='2026-10-25T00:01:00+00:00',
        execution={'observed_models':['model'], 'cost_usd_estimate':None},
        verification={'native_result': {'rewards': {'reward': 1 if state == 'PASS' else 0}},
                      'assessment': {'verdict':state,'reason':'test outcome'}},
        problem='billing unavailable',cleanup_ok=False,
    )
    assert RecordV1.model_validate_json(json.dumps(record)).verdict.status == state
    assert record['checks'][0]['id'] == 'independent-terminal-verification'
    assert record['case']['id'] == case['local_case_id']
    assert '/' not in record['case']['id']
    assert record['cost']['trial_usd'] is None
    assert 'cleanup incomplete' in record['verdict']['after_assessment']
    assert 'billing unavailable' in record['verdict']['after_assessment']
    assert record['conditions']['observed_models'] == ['model']
