"""WP-08 artifacts reject credential disclosure and unsupported runtime identities."""

import hashlib
import json
import os

import pytest
from probe.records import RecordV1
from swebench_adapter.artifacts import make_record, runtime_problem, store_bytes


def test_secret_is_rejected_before_any_file_is_created(tmp_path):

    for payload in (b'result sk-or-v1-example-secret', b'result exact-private-value'):
        with pytest.raises(ValueError, match='credential'):
            store_bytes(tmp_path, 'trace.jsonl', payload, secrets=('exact-private-value',))
        assert not (tmp_path / 'trace.jsonl').exists()


@pytest.mark.parametrize('name', ['../outside', '/tmp/outside', '.hidden', 'sub/../outside'])
def test_artifact_paths_cannot_escape_attempt(tmp_path, name):

    with pytest.raises(ValueError, match='path'):
        store_bytes(tmp_path, name, b'content')


def test_artifacts_are_private_and_cannot_overwrite_existing_evidence(tmp_path):

    path = store_bytes(tmp_path, 'trace.jsonl', b'evidence')
    assert path.read_bytes() == b'evidence'
    if os.name == 'posix':
        assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        store_bytes(tmp_path, 'trace.jsonl', b'replacement')
    assert path.read_bytes() == b'evidence'


def test_artifact_symlink_is_never_followed(tmp_path):

    target = tmp_path / 'target'
    target.write_text('untouched')
    (tmp_path / 'trace.jsonl').symlink_to(target)
    with pytest.raises((ValueError, FileExistsError)):
        store_bytes(tmp_path, 'trace.jsonl', b'replacement')
    assert target.read_text() == 'untouched'


def _trace(tmp_path, **changes):
    plugin = tmp_path / 'plugin'
    (plugin / '.claude-plugin').mkdir(parents=True)
    (plugin / '.claude-plugin/plugin.json').write_text('{"name":"save-toolkit"}')
    event = {'type': 'system', 'subtype': 'init', 'session_id': 'one',
             'model': 'anthropic/claude-sonnet-5.5', 'tools': ['Read'], 'mcp_servers': [],
             'plugins': [{'name': 'save-toolkit', 'path': '/opt/fleet'}]}
    event.update(changes)
    path = tmp_path / 'trace.jsonl'
    path.write_text(json.dumps(event) + '\n' + json.dumps(
        {'type': 'result', 'subtype': 'success', 'num_turns': 1, 'result': 'done',
         'total_cost_usd': 0.1, 'modelUsage': {'anthropic/claude-sonnet-5.5': {}}}) + '\n')
    return path, plugin


def test_container_plugin_path_is_verified_without_host_path_confusion(tmp_path):

    trace, plugin = _trace(tmp_path)
    assert runtime_problem(trace, plugin, '/opt/fleet', 'anthropic/claude-sonnet-5.5', ['Read']) is None


@pytest.mark.parametrize('changes, match', [
    ({'model': 'wrong-model'}, 'model'),
    ({'plugins': [{'name': 'save-toolkit', 'path': '/unmeasured'}]}, 'plugin'),
    ({'tools': ['Read', 'WebFetch']}, 'tool'),
    ({'mcp_servers': [{'name': 'unexpected'}]}, 'MCP'),
])
def test_runtime_drift_voids_measurement(tmp_path, changes, match):

    trace, plugin = _trace(tmp_path, **changes)
    assert match in runtime_problem(trace, plugin, '/opt/fleet', 'anthropic/claude-sonnet-5.5', ['Read'])


def test_assistant_model_cannot_substitute_for_missing_init_model(tmp_path):

    trace, plugin = _trace(tmp_path, model=None)
    with trace.open('a') as stream:
        stream.write(json.dumps({'type': 'assistant', 'message': {
            'model': 'anthropic/claude-sonnet-5.5', 'content': []}}) + '\n')
    assert 'model' in runtime_problem(trace, plugin, '/opt/fleet', 'anthropic/claude-sonnet-5.5', ['Read'])


@pytest.mark.parametrize('ending, stop, observed', [('completed', None, ['anthropic/claude-sonnet-5.5']),
                                                 ('cut_short', 'no_result', None)])
def test_record_preserves_profile_verdict_and_separate_estimated_cost(tmp_path, ending, stop, observed):

    case = {'instance_id': 'repo__case-1', 'base_commit': 'a' * 40}
    identity = {**case, 'dataset': 'SWE-bench/SWE-bench_Verified', 'revision': 'b' * 40}
    record = make_record(
        identity=identity, candidate={'plugin_root': '/snapshot', 'plugin_commit': 'a' * 40,
            'plugin_inputs_dirty': False, 'plugin_source_sha256': 'c' * 64},
        runner={'runner_commit': 'd' * 40, 'runner_source_dirty': False, 'runner_source_sha256': 'e' * 64},
        model='anthropic/claude-sonnet-5.5', runtime={'cli_version': '2.1.309', 'host_platform': {'system': 'Linux'}},
        label='claude', started='2026-10-24T00:00:00+00:00', ended='2026-10-24T00:01:00+00:00',
        state='FAIL', reason='patch did not resolve', ending=ending, stop=stop,
        estimated_cost=0.25, evidence={'patch': 'patch.diff'},
    )
    parsed = RecordV1.model_validate_json(json.dumps(record))
    assert parsed.conditions.execution_profile.name == 'static-repair-independently-verified-dec13'
    assert parsed.conditions.execution_profile.authentication == 'openrouter-host-proxy'
    assert parsed.conditions.turn_limit == 64
    assert parsed.conditions.wall_clock_seconds == 2700
    assert parsed.conditions.observed_models == observed
    assert parsed.case.scenario_sha256 is None
    assert parsed.case.case_sha256 == hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    assert parsed.verdict.status == 'FAIL'
    assert parsed.cost.trial_usd == 0.25
    assert parsed.evidence['patch'] == 'patch.diff'
