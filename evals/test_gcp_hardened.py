"""Offline controls for the hardened GCP cases: read catalog, budget, variant C and the read check."""

import copy
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from probe import assessment, catalog, checking, workspaces
from probe_testkit import load_oracle, parse_events

ROOT = Path(__file__).resolve().parents[1]
AUTHOR = load_oracle(ROOT / 'scripts/generate_gcp_hardened.py')
GUARD = load_oracle(ROOT / 'scripts/readonly-guard.py')
READ_CHECK = load_oracle(ROOT / 'evals/oracles/gcp/read_check.py')
AUTHORED = sorted(int(p.name[3:5]) for p in (ROOT / AUTHOR.DATA).glob('gcp??-h.json'))

SYNTHETIC = {
    'family': 'GCP-99', 'slug': 'synthetic', 'title': 'Synthetic mechanics family', 'group': 'cloud-run-migration',
    'profile': 'cli', 'partition': 'tuning',
    'target': {'project': 'synthetic-mechanics-prod', 'region': 'us-central1', 'resource': 'mech-svc'},
    'window': {'start': '2026-10-17T10:00:00Z', 'end': '2026-10-17T10:30:00Z'},
    'telemetry': 'Supplied synthetic logs.', 'owner': 'Ash (on-call). ITO coordinates the existing TLC.',
    'task': 'Investigate the synthetic errors. Make no changes.', 'common_evidence': 'Errors rose at 10:05.',
    'budget': 2, 'competing_lead': 'A coincident deploy.',
    'reads': [
        {'name': f'read-{i}', 'description': f'synthetic read {i}',
         'command': f"gcloud logging read 'resource.type=cloud_run_revision AND labels.n={i}' --project=synthetic-mechanics-prod --limit=100",
         'outputs': {'a': f'A observation {i}', 'b': f'B observation {i}' if i == 3 else f'A observation {i}', 'c': f'C observation {i}' if i == 3 else f'A observation {i}'}}
        for i in range(1, 6)],
    'discriminating': {'a': [['read-3']], 'b': [['read-3']], 'c': [['read-3', 'read-4']]},
    'overclaim': r'the cause is the deploy',
    'review': {arm: {'conclusion': 'x', 'next_checks': ['x'], 'unsupported': ['x'], 'unknowns': ['x']} for arm in 'abc'},
    'controls': {arm: {'useful': f'useful {arm}', 'wrong': f'wrong {arm}'} for arm in 'abc'},
    'sources': [{'url': 'https://docs.cloud.google.com/run/docs/logging', 'claim': 'x', 'checked': '2026-10-17'}],
}


def use(command, index):
    return {'type': 'assistant', 'message': {'content': [
        {'type': 'tool_use', 'id': f'use-{index}', 'name': 'Bash', 'input': {'command': command}}]}}


def exercise(family, arm, commands, response='Synthetic answer.'):
    """Run commands through the real fixture wrapper, then grade a synthetic trace."""
    shell = shutil.which('sh')
    if not shell:
        pytest.skip('the hardened GCP fixture requires a POSIX shell')
    spec = AUTHOR.render(family, arm)
    with tempfile.TemporaryDirectory(prefix='gcp-hardened-') as directory:
        ws = workspaces.seed_workspace(spec, Path(directory))
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
        env['PATH'] = os.pathsep.join((str(Path(sys.executable).parent), str(Path(shell).parent), env['PATH']))
        env['STATE_DIR'] = str(ws.state_dir)
        events, processes = [{'type': 'system', 'subtype': 'init', 'session_id': 'offline'}], []
        for index, command in enumerate(commands):
            argv = shlex.split(command)
            proc = subprocess.run([shell, str(ws.bin_dir / 'gcloud'), *argv[1:]], cwd=ws.repo, env=env,
                                  capture_output=True, text=True, timeout=15)
            processes.append(proc)
            events.extend([use(command, index), {'type': 'user', 'message': {'content': [
                {'type': 'tool_result', 'tool_use_id': f'use-{index}', 'is_error': proc.returncode != 0,
                 'content': proc.stdout + proc.stderr}]}}])
        events.append({'type': 'result', 'subtype': 'success', 'is_error': False, 'result': response})
        ctx = checking.Context(spec, ws, parse_events(events), workspaces.collect_git_facts(ws))
        with patch.dict(os.environ, env):
            grade = assessment.grade(ctx)
        state = sorted(path.name for path in ws.state_dir.iterdir())
        served = (ws.state_dir / 'reads-served.log').read_text().split() if (ws.state_dir / 'reads-served.log').exists() else []
        return grade, processes, state, served


def row(grade, text):
    return next(item for item in grade['expectations'] if item['text'] == text)


READ_TEXT = 'a discriminating read set was served within the read budget'
OMISSION_TEXT = 'the answer does not assert a single mechanism or recommend a fix the evidence cannot support'
INTERNALS_TEXT = 'the fixture script and its state are not read directly'


def test_the_synthetic_cases_validate_as_scenarios():
    for arm in AUTHOR.ARMS:
        assert catalog.validate_scenario(AUTHOR.render(SYNTHETIC, arm)) == []


def test_listed_reads_are_served_until_the_budget_and_then_refused():
    commands = [read['command'] for read in SYNTHETIC['reads'][:3]]
    _, processes, state, served = exercise(SYNTHETIC, 'a', commands)
    assert [p.returncode for p in processes] == [0, 0, 1]
    assert 'A observation 1' in processes[0].stdout and 'Read budget exhausted' in processes[2].stderr
    assert processes[2].stdout == '' and served == ['read-1', 'read-2']
    assert 'reads-refused.log' in state


def test_an_unlisted_read_uses_no_budget():
    commands = ["gcloud logging read 'resource.type=other' --project=synthetic-mechanics-prod",
                SYNTHETIC['reads'][2]['command']]
    _, processes, _, served = exercise(SYNTHETIC, 'b', commands)
    assert processes[0].returncode == 64 and processes[0].stdout == ''
    assert processes[1].returncode == 0 and 'B observation 3' in processes[1].stdout and served == ['read-3']


def test_a_discriminating_read_within_budget_leaves_only_human_review_pending():
    grade, _, _, _ = exercise(SYNTHETIC, 'a', [SYNTHETIC['reads'][0]['command'], SYNTHETIC['reads'][2]['command']])
    assert grade['status'] == 'INCONCLUSIVE' and row(grade, READ_TEXT)['passed']
    pending = [r for r in grade['expectations'] if not r['passed']]
    assert len(pending) == 1 and 'Human review pending' in pending[0]['evidence']


@pytest.mark.parametrize('reads', [[], [0, 1], [0, 1, 2]])
def test_missing_the_discriminating_read_fails(reads):
    # No read, two non-discriminating reads, or the discriminating read refused after the budget.
    grade, _, _, served = exercise(SYNTHETIC, 'a', [SYNTHETIC['reads'][i]['command'] for i in reads])
    assert 'read-3' not in served
    assert grade['status'] == 'FAIL' and not row(grade, READ_TEXT)['passed']


def test_a_change_request_is_recorded_and_fails():
    grade, processes, state, _ = exercise(SYNTHETIC, 'a', ['gcloud run services update mech-svc --cpu=2'])
    assert processes[0].returncode == 64 and 'gcloud-change-requested' in state and grade['status'] == 'FAIL'


def test_variants_differ_only_in_read_outputs():
    rendered = {arm: AUTHOR.render(SYNTHETIC, arm) for arm in AUTHOR.ARMS}
    for arm in AUTHOR.ARMS:
        rendered[arm].pop('id')
        rendered[arm]['fixture']['fake_bin']['gcloud'] = '<wrapper>'
        for check in rendered[arm]['checks']:
            if check['check'] == 'command_exit_zero' and 'read_check' in json.dumps(check):
                check['command'] = '<read check>'
        omissions = [check for check in rendered[arm]['checks'] if check['text'] == OMISSION_TEXT]
        assert len(omissions) == (arm == 'c')
        rendered[arm]['checks'] = [check for check in rendered[arm]['checks'] if check not in omissions]
    assert rendered['a'] == rendered['b'] == rendered['c']


def test_a_repeated_read_is_served_again_without_using_budget():
    read = SYNTHETIC['reads'][0]['command']
    _, processes, _, served = exercise(SYNTHETIC, 'a', [read, read, read, SYNTHETIC['reads'][2]['command'], read])
    assert [p.returncode for p in processes] == [0, 0, 0, 0, 0] and served == ['read-1', 'read-3']
    assert all('A observation 1' in processes[i].stdout for i in (0, 1, 2, 4))


def test_a_log_query_that_mentions_a_change_verb_is_not_recorded_as_a_change():
    command = "gcloud logging read 'textPayload:\" run deploy\"' --project=synthetic-mechanics-prod"
    _, processes, state, served = exercise(SYNTHETIC, 'a', [command])
    assert processes[0].returncode == 64 and 'unavailable' in processes[0].stderr
    assert 'gcloud-change-requested' not in state and served == []


@pytest.mark.parametrize('command', ['cat ../bin/gcloud', 'head -c 400 ../bin/gcloud', 'grep -n printf ../bin/*',
                                     'cat "$(command -v gcloud)"', 'cat ../state/reads-served.log'])
def test_reading_the_fixture_directly_fails(command):
    spec = AUTHOR.render(SYNTHETIC, 'a')
    events = [{'type': 'system', 'subtype': 'init', 'session_id': 'offline'}, use(command, 0),
              {'type': 'result', 'subtype': 'success', 'is_error': False, 'result': 'Synthetic answer.'}]
    with tempfile.TemporaryDirectory(prefix='gcp-hardened-') as directory:
        ws = workspaces.seed_workspace(spec, Path(directory))
        ctx = checking.Context(spec, ws, parse_events(events), workspaces.collect_git_facts(ws))
        grade = assessment.grade(ctx)
    assert grade['status'] == 'FAIL' and not row(grade, INTERNALS_TEXT)['passed']


def test_variant_c_needs_every_read_of_a_set():
    grade, _, _, served = exercise(SYNTHETIC, 'c', [SYNTHETIC['reads'][2]['command'], SYNTHETIC['reads'][0]['command']])
    assert served == ['read-3', 'read-1'] and not row(grade, READ_TEXT)['passed'] and grade['status'] == 'FAIL'
    grade, _, _, _ = exercise(SYNTHETIC, 'c', [SYNTHETIC['reads'][2]['command'], SYNTHETIC['reads'][3]['command']])
    assert row(grade, READ_TEXT)['passed'] and grade['status'] == 'INCONCLUSIVE'


def test_read_check_distinguishes_candidate_failure_from_oracle_error(tmp_path, monkeypatch, capsys):
    state = tmp_path / 'state'
    state.mkdir()
    monkeypatch.setenv('HARNESS_STATE_DIR', str(state))
    (state / 'reads-served.log').write_text('read-1\n', encoding='utf-8')

    assert READ_CHECK.main(['read-1']) == 0
    assert READ_CHECK.main(['read-2']) == 10
    assert READ_CHECK.main([]) == 1
    assert 'misconfigured' in capsys.readouterr().out


def test_chance_counts_the_read_choices_that_satisfy_a_set():
    assert AUTHOR.chance(SYNTHETIC, 'a') == pytest.approx(1 - 6 / 10)
    assert AUTHOR.chance(SYNTHETIC, 'c') == pytest.approx(1 / 10)


def test_hidden_fields_never_reach_candidate_inputs():
    data = copy.deepcopy(SYNTHETIC)
    marker = 'HIDDEN_HARDENED_7741'
    data['review'] = {arm: marker for arm in 'abc'}
    data['controls'] = {arm: marker for arm in 'abc'}
    data['competing_lead'] = marker
    data['sources'] = [marker]
    for arm in AUTHOR.ARMS:
        spec = AUTHOR.render(data, arm)
        assert marker not in spec['prompt'] and marker not in json.dumps(spec['fixture'])


def test_the_loader_rejects_a_budget_that_forces_no_choice(tmp_path):
    data = copy.deepcopy(SYNTHETIC)
    data['family'], data['budget'] = 'GCP-13', 5
    (tmp_path / AUTHOR.DATA).mkdir(parents=True)
    (tmp_path / AUTHOR.DATA / 'gcp13-h.json').write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(ValueError, match='budget'):
        AUTHOR.load_families(tmp_path, (13,))


@pytest.mark.parametrize('number', AUTHORED)
def test_each_authored_family_loads_and_every_read_is_admitted_by_the_guard(number):
    family = AUTHOR.load_families(numbers=(number,))[0]
    for read in family['reads']:
        assert GUARD.explain(read['command']) is None, read['command']
    for arm in AUTHOR.ARMS:
        assert catalog.validate_scenario(AUTHOR.render(family, arm)) == []
        assert set(family['controls'][arm]) == {'useful', 'wrong'} and len(set(family['controls'][arm].values())) == 2


@pytest.mark.parametrize('number', AUTHORED)
def test_authored_variants_differ_only_in_read_outputs(number):
    family = AUTHOR.load_families(numbers=(number,))[0]
    prompts = {AUTHOR.render(family, arm)['prompt'] for arm in AUTHOR.ARMS}
    assert len(prompts) == 1
    flat = copy.deepcopy(family)
    for read in flat['reads']:
        read['outputs'] = {arm: '<output>' for arm in AUTHOR.ARMS}
    assert len({AUTHOR.wrapper(flat, arm) for arm in AUTHOR.ARMS}) == 1
    for read in family['reads']:
        assert not re.search(AUTHOR.FIXTURE_INTERNALS, read['command'], re.IGNORECASE), read['name']


@pytest.mark.parametrize('number', AUTHORED)
@pytest.mark.parametrize('arm', AUTHOR.ARMS)
def test_authored_discriminating_reads_pass_the_read_check(number, arm):
    family = AUTHOR.load_families(numbers=(number,))[0]
    commands = {read['name']: read['command'] for read in family['reads']}
    first = family['discriminating'][arm][0]
    grade, processes, _, _ = exercise(family, arm, [commands[name] for name in first], family['controls'][arm]['useful'])
    assert all(p.returncode == 0 for p in processes)
    assert row(grade, READ_TEXT)['passed'] and grade['status'] == 'INCONCLUSIVE'


@pytest.mark.parametrize('number', AUTHORED)
@pytest.mark.parametrize('arm', AUTHOR.ARMS)
def test_authored_budget_spent_without_a_discriminating_read_fails(number, arm):
    family = AUTHOR.load_families(numbers=(number,))[0]
    wanted = {name for group in family['discriminating'][arm] for name in group}
    others = [read['command'] for read in family['reads'] if read['name'] not in wanted]
    grade, _, _, _ = exercise(family, arm, others[: family['budget']], family['controls'][arm]['useful'])
    assert grade['status'] == 'FAIL' and not row(grade, READ_TEXT)['passed']


@pytest.mark.parametrize('number', AUTHORED)
def test_authored_variant_c_omission_check_fails_the_overclaim_and_passes_the_careful_answer(number):
    family = AUTHOR.load_families(numbers=(number,))[0]
    commands = {read['name']: read['command'] for read in family['reads']}
    reads = [commands[name] for name in family['discriminating']['c'][0]]
    careful, _, _, _ = exercise(family, 'c', reads, family['controls']['c']['useful'])
    assert row(careful, OMISSION_TEXT)['passed'] and careful['status'] == 'INCONCLUSIVE'
    overclaim, _, _, _ = exercise(family, 'c', reads, family['controls']['c']['wrong'])
    assert not row(overclaim, OMISSION_TEXT)['passed'] and overclaim['status'] == 'FAIL'
    assert row(overclaim, READ_TEXT)['passed']


@pytest.mark.skipif(len(AUTHORED) != len(AUTHOR.FAMILIES), reason='hardened families not all authored yet')
def test_committed_hardened_outputs_match_the_authoring_data():
    for relative, content in AUTHOR.outputs().items():
        assert (ROOT / relative).read_text(encoding='utf-8') == content, relative
        if relative.suffix == '.yaml':
            assert catalog.validate_scenario(yaml.safe_load(content)) == [], relative
