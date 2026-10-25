"""The WP-08 entrypoint explains prerequisites without starting paid work."""

import subprocess
import sys
from pathlib import Path

import pytest
import swebench_repair as cli
from swebench_adapter import smoke

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'evals/swebench_repair.py'


def test_help_names_separate_owner_started_steps():
    result = subprocess.run([sys.executable, str(CLI), '--help'], capture_output=True, text=True)
    assert result.returncode == 0
    for step in ('select', 'preflight', 'smoke', 'trial', 'batch'):
        assert step in result.stdout


@pytest.mark.parametrize('command', ['preflight', 'smoke', 'trial', 'batch'])
def test_missing_inputs_fail_before_any_resources_are_started(command):
    result = subprocess.run([sys.executable, str(CLI), command], capture_output=True, text=True)
    assert result.returncode == 2
    assert '--selection' in result.stderr
    assert 'Traceback' not in result.stderr


def test_missing_selection_produces_a_bounded_error(tmp_path):
    result = subprocess.run([sys.executable, str(CLI), 'preflight', '--selection', str(tmp_path/'missing.json'),
                             '--dataset', str(tmp_path/'dataset.json'), '--config', str(tmp_path/'config.json')],
                            capture_output=True, text=True)
    assert result.returncode == 3
    assert 'Traceback' not in result.stderr
    assert 'missing' in result.stderr.lower()


def test_smoke_error_is_not_a_successful_cli_exit(monkeypatch, tmp_path):
    manifest = {'revision': 'a' * 40, 'tasks': [{'instance_id': 'one'}]}
    monkeypatch.setattr(cli, 'read_object', lambda path: manifest)
    monkeypatch.setattr(cli, '_dataset', lambda *args: [])
    monkeypatch.setattr(cli, 'load_config', lambda path: {'images': {'one': {}}})
    monkeypatch.setattr(cli, 'resolve_task', lambda *args, **kwargs: {})
    monkeypatch.setattr(cli, 'dependency_problems', lambda: [])
    monkeypatch.setattr(cli, 'selection_committed', lambda path: True)
    monkeypatch.setattr(smoke, 'run_smoke', lambda *args: {
        'format': 'wp08-smoke', 'schema_version': 1, 'binding': {},
        'checks': dict.fromkeys(('reference_resolves', 'empty_rejected', 'guard_allow', 'guard_deny',
                                'no_cr', 'history_pruned', 'egress', 'cpu_cap', 'storage_cap', 'cleanup'), True),
        'cleanup': [{'present': False}], 'error': 'late cleanup bookkeeping failed'})
    assert cli.main(['smoke', '--selection', 'selection.json', '--dataset', 'dataset.json',
                     '--config', 'config.json', '--out', str(tmp_path/'out')]) == 3
