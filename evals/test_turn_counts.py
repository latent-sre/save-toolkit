"""The turn-count summary reads saved timing records only; no model or CLI call."""

import json
from pathlib import Path

import turn_counts


def write_trial(root, scenario, run, payload, label='baseline'):
    folder = root / 'iter-1' / f'eval-{scenario}' / label / f'run-{run}'
    folder.mkdir(parents=True)
    text = payload if isinstance(payload, str) else json.dumps(payload)
    (folder / 'timing.json').write_text(text, encoding='utf-8')


def test_counts_known_turns_and_keeps_unreadable_or_missing_counts_visible(tmp_path):
    write_trial(tmp_path, 'case-a', 1, {'num_turns': 12, 'trial_duration_seconds': 40.5})
    write_trial(tmp_path, 'case-a', 2, {'num_turns': 30, 'trial_duration_seconds': 95})
    write_trial(tmp_path, 'case-a', 3, {'num_turns': 20}, label='candidate')
    write_trial(tmp_path, 'case-a', 4, {'num_turns': True})
    write_trial(tmp_path, 'case-a', 5, {'num_turns': None})
    write_trial(tmp_path, 'case-a', 6, '{not json')
    write_trial(tmp_path, 'case-b', 1, ['not', 'an', 'object'])
    observed = turn_counts.collect(tmp_path, set())
    assert sorted(observed['case-a'].turns) == [12, 20, 30]
    assert observed['case-a'].unknown == 3
    assert observed['case-a'].longest_seconds == 95
    assert observed['case-b'].turns == [] and observed['case-b'].unknown == 1


def test_named_scenarios_limit_the_report_and_absent_ones_show_zero_trials(tmp_path, capsys):
    write_trial(tmp_path, 'case-a', 1, {'num_turns': 7})
    write_trial(tmp_path, 'case-b', 1, {'num_turns': 9})
    assert turn_counts.main([str(tmp_path), '--scenario', 'case-a', '--scenario', 'never-run']) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].split() == ['scenario', 'trials', 'min', 'median', 'max', 'no', 'count', 'longest', 's']
    assert lines[1].split() == ['case-a', '1', '7', '7', '7', '0', '-']
    assert lines[2].split() == ['never-run', '0', '-', '-', '-', '0', '-']
    assert len(lines) == 3


def test_missing_root_exits_three(tmp_path, capsys):
    assert turn_counts.main([str(tmp_path / 'absent')]) == 3
    assert 'not a directory' in capsys.readouterr().err


def test_reads_a_whole_runs_tree_as_well_as_one_iteration(tmp_path):
    write_trial(tmp_path, 'case-a', 1, {'num_turns': 4})
    whole = turn_counts.collect(tmp_path, set())
    one = turn_counts.collect(Path(tmp_path) / 'iter-1', set())
    assert whole['case-a'].turns == one['case-a'].turns == [4]
