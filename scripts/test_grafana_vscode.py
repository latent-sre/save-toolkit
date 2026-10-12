"""The report opener reuses VS Code without shells or Grafana credentials."""
import json
import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from testkit import load_path

ROOT = Path(__file__).resolve().parents[1]


def test_report_does_not_create_a_replacement_workspace(tmp_path):
    evidence = load_path(ROOT / 'skills/grafana/scripts/grafana_evidence.py', 'grafana_evidence')
    directory = tmp_path / 'report'
    evidence.write_package({'operation': 'test'}, directory)
    assert not (directory / 'report.code-workspace').exists()
    manifest = json.loads((directory / 'manifest.json').read_text())
    assert 'report.code-workspace' not in manifest['files']


def ready(opener, monkeypatch):
    monkeypatch.setattr(opener, '_session_running', lambda _env: True)
    monkeypatch.setattr(opener, '_association_available', lambda _directory: True)


def test_open_reuses_window_without_replacing_workspace_and_strips_credentials(tmp_path, monkeypatch):
    opener = load_path(ROOT / 'skills/grafana/scripts/grafana_vscode.py', 'grafana_vscode')
    directory = tmp_path / 'report & spaces'
    directory.mkdir()
    (directory / 'report.html').write_text('report')
    ready(opener, monkeypatch)
    calls = []
    monkeypatch.setattr(opener, '_command', lambda _env: (['/trusted/code'], {}))

    def runner(argv, **options):
        calls.append((argv, options))
        return SimpleNamespace(returncode=0, stdout=b'1.141.0\ncommit\nx64\n')

    result = opener.open_report(directory, environ={'PATH': '/trusted', 'GRAFANA_SA_TOKEN': 'secret',
                                                   'GRAFANA_PASSWORD': 'password'}, runner=runner)
    assert result['status'] == 'launch_requested' and result['visual_verification'] == 'not_performed'
    assert calls[1][0] == ['/trusted/code', '--reuse-window', str(directory / 'report.html')]
    assert all(not any(key.startswith('GRAFANA_') for key in call[1]['env']) for call in calls)
    assert all(call[1].get('shell', False) is False for call in calls)


@pytest.mark.parametrize('version,error', [(b'1.133.0', 'vscode_version_unsupported'),
                                         (b'not a version', 'vscode_version_unknown')])
def test_unsupported_version_does_not_launch(tmp_path, monkeypatch, version, error):
    opener = load_path(ROOT / 'skills/grafana/scripts/grafana_vscode.py', 'grafana_vscode')
    (tmp_path / 'report.html').write_text('report')
    ready(opener, monkeypatch)
    monkeypatch.setattr(opener, '_command', lambda _env: (['/trusted/code'], {}))
    calls = []

    def runner(argv, **_options):
        calls.append(argv)
        return SimpleNamespace(returncode=0, stdout=version)

    result = opener.open_report(tmp_path, environ={}, runner=runner)
    assert result['error'] == error and len(calls) == 1


@pytest.mark.parametrize('error', [FileNotFoundError('secret'), subprocess.TimeoutExpired('secret', 15)])
def test_failure_is_static_and_report_remains_available(tmp_path, monkeypatch, error):
    opener = load_path(ROOT / 'skills/grafana/scripts/grafana_vscode.py', 'grafana_vscode')
    (tmp_path / 'report.html').write_text('report')
    ready(opener, monkeypatch)
    monkeypatch.setattr(opener, '_command', lambda _env: (['/trusted/code'], {}))

    def runner(*_args, **_options):
        raise error

    result = opener.open_report(tmp_path, environ={}, runner=runner)
    assert result['status'] == 'unavailable' and 'secret' not in json.dumps(result)
    assert (tmp_path / 'report.html').read_text() == 'report'


@pytest.mark.parametrize('prefix', ['', '123abc456d\\'])
def test_windows_shim_is_resolved_without_executing_batch_file(tmp_path, prefix):
    opener = load_path(ROOT / 'skills/grafana/scripts/grafana_vscode.py', 'grafana_vscode')
    root = tmp_path / 'VS Code & spaces'
    (root / 'bin').mkdir(parents=True)
    (root / 'Code.exe').write_bytes(b'fixture')
    cli = root.joinpath(*prefix.split('\\'), 'resources', 'app', 'out', 'cli.js')
    cli.parent.mkdir(parents=True)
    cli.write_text('fixture')
    shim = root / 'bin' / 'code.cmd'
    shim.write_text('"%~dp0..\\Code.exe" "%~dp0..\\' + prefix + 'resources\\app\\out\\cli.js" %*')
    assert opener._windows_command(shim) == [str(root / 'Code.exe'), str(cli)]


def test_windows_shim_refuses_interpolated_or_traversing_cli_path(tmp_path):
    opener = load_path(ROOT / 'skills/grafana/scripts/grafana_vscode.py', 'grafana_vscode')
    shim = tmp_path / 'code.cmd'
    for content in ('"%~dp0..\\..\\resources\\app\\out\\cli.js"', '"%SOMEWHERE%\\cli.js"'):
        shim.write_text(content)
        assert opener._windows_command(shim) is None


def test_path_lookup_does_not_pick_up_cwd_launcher(tmp_path, monkeypatch):
    opener = load_path(ROOT / 'skills/grafana/scripts/grafana_vscode.py', 'grafana_vscode')
    monkeypatch.chdir(tmp_path)
    for name in ('code', 'code.cmd'):
        path = tmp_path / name
        path.write_text('must not execute')
        path.chmod(0o700)
    assert opener._command({'PATH': os.pathsep.join(['.', str(tmp_path)])})[0] is None


def test_launch_timeout_is_unknown_and_not_retried(tmp_path, monkeypatch):
    opener = load_path(ROOT / 'skills/grafana/scripts/grafana_vscode.py', 'grafana_vscode')
    (tmp_path / 'report.html').write_text('report')
    ready(opener, monkeypatch)
    monkeypatch.setattr(opener, '_command', lambda _env: (['/trusted/code'], {}))
    calls = []

    def runner(argv, **_options):
        calls.append(argv)
        if len(calls) == 1:
            return SimpleNamespace(returncode=0, stdout=b'1.141.0')
        raise subprocess.TimeoutExpired('secret', 15)

    result = opener.open_report(tmp_path, environ={}, runner=runner)
    assert result['status'] == 'unknown' and len(calls) == 2


@pytest.mark.parametrize('fails', [False, True])
def test_cli_opens_only_after_package_completion_and_keeps_success_on_viewer_failure(tmp_path, monkeypatch, fails):
    workflow = load_path(ROOT / 'skills/grafana/scripts/grafana_workflow.py', 'grafana_workflow')
    original_module = workflow._module
    query_file = tmp_path / 'query.json'
    query_file.write_text(json.dumps({'ok': True, 'operation': 'query', 'kind': 'prometheus', 'mode': 'range',
                                     'from': '1000', 'to': '61000', 'results': {'A': {'frames': []}}}))
    calls = []

    def open_report(directory, **_kwargs):
        calls.append(directory)
        assert (directory / 'manifest.json').is_file()
        assert not (directory / 'report.code-workspace').exists()
        assert not (directory / '.incomplete').exists()
        if fails:
            raise RuntimeError('not safe to print')
        return {'status': 'launch_requested'}

    monkeypatch.setattr(workflow, '_module', lambda name: SimpleNamespace(open_report=open_report)
                        if name == 'grafana_vscode' else original_module(name))
    import io  # noqa: PLC0415
    output = io.StringIO()
    code = workflow.main(['alert-preview', '--query-file', str(query_file), '--operator', 'gt', '--threshold', '4',
                          '--pending-ms', '0', '--step-ms', '2000', '--output-dir', str(tmp_path / 'report'), '--open-vscode'],
                         environ={}, output=output)
    assert code == 0 and len(calls) == 1
    response = json.loads(output.getvalue())
    assert response['viewer']['status'] == ('unavailable' if fails else 'launch_requested')
    assert response['package']['status'] == 'complete' and 'not safe to print' not in output.getvalue()


def test_missing_existing_session_never_runs_cli(tmp_path):
    opener = load_path(ROOT / 'skills/grafana/scripts/grafana_vscode.py', 'grafana_vscode')
    (tmp_path / 'report.html').write_text('report')
    result = opener.open_report(tmp_path, environ={}, runner=lambda *_a, **_kw: pytest.fail('Must not cold-start VS Code'))
    assert result['error'] == 'existing_vscode_session_required'


def test_association_is_scoped_to_current_workspace_and_not_created_implicitly(tmp_path, monkeypatch):
    opener = load_path(ROOT / 'skills/grafana/scripts/grafana_vscode.py', 'grafana_vscode')
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    monkeypatch.chdir(workspace)
    assert not opener._association_available(workspace / 'capture')
    assert not (workspace / '.vscode').exists()
    (workspace / '.vscode').mkdir()
    settings = workspace / '.vscode/settings.json'
    settings.write_text(json.dumps({'workbench.editorAssociations': {'**/report.html': 'workbench.editor.browser'}}))
    assert opener._association_available(workspace / 'capture')
    assert not opener._association_available(tmp_path / 'elsewhere')
