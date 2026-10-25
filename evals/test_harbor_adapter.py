"""Offline Terminal-Bench admission, provenance and reward controls."""
import json
from pathlib import Path

import pytest
from harbor_adapter import contracts
from harbor_adapter.contracts import load_manifest, reward_assessment, stage_task

ROOT = Path(__file__).resolve().parents[1]


def test_frozen_five():
    manifest = load_manifest(ROOT / 'evals/manifests/wp09-terminal-complex5.json')
    assert len(manifest['cases']) == 5
    assert sum(c['upstream_difficulty'] == 'hard' for c in manifest['cases']) == 3
    assert all(c['image_digest'] is None for c in manifest['cases'])
    assert all(c['local_case_id'] != c['task_id'] for c in manifest['cases'])


@pytest.mark.parametrize(('value', 'verdict'), [(b'1', 'PASS'), (b'0', 'FAIL'), (b'NaN', 'INCONCLUSIVE'), (b'Infinity', 'INCONCLUSIVE'), (b'', 'INCONCLUSIVE'), (b'0.5', 'INCONCLUSIVE')])
def test_text_controls(tmp_path, value, verdict):
    (tmp_path / 'reward.txt').write_bytes(value)
    result = reward_assessment(tmp_path)
    assert result['verdict'] == verdict
    assert result['upstream_reward_text'] == value.decode()


@pytest.mark.parametrize('value', ['{}', '[]', '{"reward": true}', '{"reward": "1"}', '{"reward": NaN}', '{"reward": 1e309}', '{"reward":1,"reward":0}', '{"reward":1,"other":0}'])
def test_invalid_json_is_not_failure(tmp_path, value):
    (tmp_path / 'reward.json').write_text(value)
    assert reward_assessment(tmp_path)['verdict'] == 'INCONCLUSIVE'


def test_reward_precedence_missing_and_cleanup(tmp_path):
    assert reward_assessment(tmp_path)['verdict'] == 'INCONCLUSIVE'
    (tmp_path / 'reward.txt').write_text('0')
    (tmp_path / 'reward.json').write_text('{"reward":1}')
    result = reward_assessment(tmp_path)
    assert result['verdict'] == 'PASS'
    assert result['upstream_reward_text'] == '0'


def test_reward_symlink_refused(tmp_path):
    other = tmp_path / 'other'
    other.write_text('1')
    (tmp_path / 'reward.txt').symlink_to(other)
    assert reward_assessment(tmp_path)['verdict'] == 'INCONCLUSIVE'


def test_stage_refuses_unpinned_source(tmp_path):
    manifest = load_manifest(ROOT / 'evals/manifests/wp09-terminal-complex5.json')
    with pytest.raises(ValueError):
        stage_task(tmp_path, manifest['cases'][0], tmp_path / 'output')


def test_manifest_rejects_mutated_case(tmp_path):
    source = ROOT / 'evals/manifests/wp09-terminal-complex5.json'
    manifest = json.loads(source.read_text())
    manifest['cases'][0]['task_id'] = 'terminal-bench/not-selected'
    target = tmp_path / 'manifest.json'
    target.write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        load_manifest(target)


def test_reference_encoder_is_not_candidate_visible(tmp_path, monkeypatch):
    source = tmp_path / 'source'
    source.mkdir()
    (source / 'environment').mkdir()
    (source / 'tests').mkdir()
    (source / 'solution').mkdir()
    names = ['instruction.md', 'environment/Dockerfile', 'environment/decomp.c', 'environment/data.txt',
             'environment/main.rs', 'tests/test.sh', 'solution/solve.sh']
    for name in names:
        (source / name).write_text('hidden-reference' if name.endswith(('main.rs','solve.sh')) else name)
    case = {'source_path':'write-compressor','task_id':'terminal-bench/write-compressor',
            'local_case_id':'wp09-terminal-static-v1-write-compressor','content_sha256':'fixture',
            'files':dict.fromkeys(names,'fixture'),
            'candidate_source_files':['instruction.md','environment/decomp.c','environment/data.txt']}
    monkeypatch.setattr(contracts, 'verify_source', lambda *a: source)
    output = tmp_path / 'stage'
    contracts.stage_task(source, case, output)
    assert not (output/'author-input/environment/main.rs').exists()
    assert not (output/'author-input/tests').exists()
    assert not (output/'author-input/solution').exists()
    assert (output/'author-input/environment/decomp.c').is_file()
    assert (output/'verifier-task/environment/main.rs').is_file()
    case['candidate_source_files'].append('environment/main.rs')
    with pytest.raises(ValueError, match='COPY'):
        contracts.stage_task(source, case, tmp_path/'leaked')
