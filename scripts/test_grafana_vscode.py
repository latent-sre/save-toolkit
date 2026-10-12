"""The report opener reuses VS Code without shells or Grafana credentials."""
import json
import os
import stat
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


def test_absolute_workspace_path_launcher_never_reaches_version_probe(tmp_path, monkeypatch):
    opener = load_path(ROOT / 'skills/grafana/scripts/grafana_vscode.py', 'grafana_vscode')
    workspace = tmp_path / 'workspace'
    directory = workspace / 'capture'
    directory.mkdir(parents=True)
    (directory / 'report.html').write_text('report')
    install = workspace / 'contributor' / 'VS Code'
    (install / 'bin').mkdir(parents=True)
    (install / 'Code.exe').write_bytes(b'benign launcher fixture')
    cli = install / 'resources/app/out/cli.js'
    cli.parent.mkdir(parents=True)
    cli.write_text('benign CLI fixture')
    (install / 'bin/code.cmd').write_text('"%~dp0..\\Code.exe" "%~dp0..\\resources\\app\\out\\cli.js" %*')
    launcher = install / 'bin/code'
    launcher.write_text('benign launcher fixture')
    launcher.chmod(0o700)
    monkeypatch.chdir(workspace)
    ready(opener, monkeypatch)
    monkeypatch.setattr(opener, '_session_executable', lambda _env: install / 'Code.exe', raising=False)
    monkeypatch.setattr(opener, '_installation_roots', lambda: [install], raising=False)
    calls = []

    def runner(argv, **_options):
        calls.append(argv)
        return SimpleNamespace(returncode=0, stdout=b'1.141.0\n')

    result = opener.open_report(directory, environ={'PATH': str(install / 'bin')}, runner=runner)
    assert calls == []
    assert result['error'] == 'vscode_cli_unavailable'


def test_cli_environment_excludes_loader_selectors_and_unrelated_secrets(tmp_path, monkeypatch):
    opener = load_path(ROOT / 'skills/grafana/scripts/grafana_vscode.py', 'grafana_vscode')
    (tmp_path / 'report.html').write_text('report')
    ready(opener, monkeypatch)
    monkeypatch.setattr(opener, '_command', lambda _env: (['/trusted/code', '/trusted/cli.js'],
                                                        {'ELECTRON_RUN_AS_NODE': '1', 'VSCODE_DEV': ''}))
    env = {'VSCODE_IPC_HOOK_CLI': '/trusted/session.sock', 'HOME': '/trusted/home',
           'NODE_OPTIONS': '--require contributor.js', 'NODE_PATH': '/contributor/modules',
           'VSCODE_NODE_OPTIONS': '--require contributor.js', 'LD_PRELOAD': '/contributor/module.so',
           'DYLD_INSERT_LIBRARIES': '/contributor/module.dylib', 'ELECTRON_RUN_AS_NODE': '0',
           'PATH': '/contributor', 'GRAFANA_TOKEN': 'grafana-secret', 'OTHER_TOKEN': 'unrelated-secret'}
    calls = []

    def runner(argv, **options):
        calls.append((argv, options))
        return SimpleNamespace(returncode=0, stdout=b'1.141.0\n')

    result = opener.open_report(tmp_path, environ=env, runner=runner)
    assert result['status'] == 'launch_requested'
    for _argv, options in calls:
        assert options['env'] == {'VSCODE_IPC_HOOK_CLI': '/trusted/session.sock', 'HOME': '/trusted/home',
                                  'ELECTRON_RUN_AS_NODE': '1', 'VSCODE_DEV': ''}


def installation(opener, tmp_path, monkeypatch, *, platform='win32', prefix=''):
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    monkeypatch.chdir(workspace)
    root = tmp_path / 'installed VS Code'
    executable = root / {'win32': 'Code.exe', 'linux': 'code', 'darwin': 'Contents/MacOS/Code'}[platform]
    executable.parent.mkdir(parents=True)
    executable.write_bytes(b'benign native executable fixture')
    executable.chmod(0o700)
    cli = root / ('Contents/Resources/app/out/cli.js' if platform == 'darwin'
                  else prefix + 'resources/app/out/cli.js')
    cli.parent.mkdir(parents=True)
    cli.write_text('benign CLI fixture')
    if platform == 'win32':
        (root / 'bin').mkdir()
        (root / 'bin/code.cmd').write_text('"%~dp0..\\Code.exe" "%~dp0..\\'
                                          + prefix.replace('/', '\\') + 'resources\\app\\out\\cli.js" %*')
    monkeypatch.setattr(opener, '_PLATFORM', platform)
    monkeypatch.setattr(opener, '_installation_roots', lambda: [root])
    monkeypatch.setattr(opener, '_session_executable', lambda _env: executable)
    return root, executable, cli


@pytest.mark.parametrize('prefix', ['', '123abc456d/'])
def test_trusted_windows_installation_is_bound_to_pid_and_ignores_path(tmp_path, monkeypatch, prefix):
    opener = load_path(ROOT / 'skills/grafana/scripts/grafana_vscode.py', 'grafana_vscode')
    root, executable, cli = installation(opener, tmp_path, monkeypatch, prefix=prefix)
    directory = Path.cwd() / 'report'
    directory.mkdir()
    (directory / 'report.html').write_text('report')
    ready(opener, monkeypatch)
    calls = []

    def runner(argv, **options):
        calls.append((argv, options))
        return SimpleNamespace(returncode=0, stdout=b'1.141.0\n')

    env = {'PATH': str(Path.cwd() / 'contributor'), 'LOCALAPPDATA': str(Path.cwd()),
           'PROGRAMFILES': str(Path.cwd()), 'VSCODE_PID': '123', 'VSCODE_IPC_HOOK_CLI': 'trusted IPC'}
    result = opener.open_report(directory, environ=env, runner=runner)
    assert result['status'] == 'launch_requested'
    assert calls[0][0] == [str(executable), str(cli), '--version']
    assert calls[1][0] == [str(executable), str(cli), '--reuse-window', str(directory / 'report.html')]
    assert 'PATH' not in calls[0][1]['env']
    assert root != Path.cwd()


@pytest.mark.parametrize('platform', ['linux', 'darwin'])
def test_posix_installation_invokes_electron_and_cli_without_path_scripts(tmp_path, monkeypatch, platform):
    opener = load_path(ROOT / 'skills/grafana/scripts/grafana_vscode.py', 'grafana_vscode')
    _root, executable, cli = installation(opener, tmp_path, monkeypatch, platform=platform)
    if platform == 'linux':
        real_stat = Path.stat

        def immutable_stat(path, **kwargs):
            metadata = list(real_stat(path, **kwargs))
            metadata[0] = stat.S_IFMT(metadata[0]) | 0o555
            metadata[4] = 0
            return os.stat_result(metadata)

        monkeypatch.setattr(Path, 'stat', immutable_stat)
    assert opener._command({'PATH': str(Path.cwd() / 'contributor')}) == (
        [str(executable), str(cli)], {'ELECTRON_RUN_AS_NODE': '1', 'VSCODE_DEV': ''})


def test_running_foreign_process_does_not_authenticate_standard_installation(tmp_path, monkeypatch):
    opener = load_path(ROOT / 'skills/grafana/scripts/grafana_vscode.py', 'grafana_vscode')
    _root, _executable, _cli = installation(opener, tmp_path, monkeypatch)
    foreign = Path.cwd() / 'Code.exe'
    foreign.write_bytes(b'benign foreign process fixture')
    monkeypatch.setattr(opener, '_session_executable', lambda _env: foreign)
    assert opener._command({}) == (None, {})


def test_standard_installation_refuses_workspace_redirected_cli(tmp_path, monkeypatch):
    opener = load_path(ROOT / 'skills/grafana/scripts/grafana_vscode.py', 'grafana_vscode')
    root, executable, _cli = installation(opener, tmp_path, monkeypatch)
    foreign = Path.cwd() / 'cli.js'
    foreign.write_text('benign foreign CLI fixture')
    monkeypatch.setattr(opener, '_windows_command', lambda _launcher: [str(executable), str(foreign)])
    assert not opener._trusted_installation(root, [executable, foreign])
    assert opener._command({}) == (None, {})


@pytest.mark.parametrize('owner,permissions', [(12345, 0o755), (0, 0o777)])
def test_linux_installation_refuses_user_owned_or_writable_files(tmp_path, monkeypatch, owner, permissions):
    opener = load_path(ROOT / 'skills/grafana/scripts/grafana_vscode.py', 'grafana_vscode')
    root, executable, cli = installation(opener, tmp_path, monkeypatch, platform='linux')
    real_stat = Path.stat

    def insecure_stat(path, **kwargs):
        metadata = list(real_stat(path, **kwargs))
        metadata[0] = stat.S_IFMT(metadata[0]) | permissions
        metadata[4] = owner
        return os.stat_result(metadata)

    monkeypatch.setattr(Path, 'stat', insecure_stat)
    assert not opener._trusted_installation(root, [executable, cli])
    assert opener._command({}) == (None, {})


def test_windows_roots_use_os_known_folders_without_ambient_location_variables(tmp_path, monkeypatch):
    opener = load_path(ROOT / 'skills/grafana/scripts/grafana_vscode.py', 'grafana_vscode')
    monkeypatch.setattr(opener, '_PLATFORM', 'win32')
    folders = {identifier: tmp_path / name for identifier, name in (
        ('F1B32785-6FBA-4FCF-9D55-7B8E7F157091', 'Local'),
        ('905E63B6-C1BF-494E-B29C-65B732D3D21A', 'Program Files'),
        ('7C5A40EF-A0FB-4BFC-874A-C0F2E0B9FA8E', 'Program Files x86'))}
    monkeypatch.setattr(opener, '_windows_known_folder', lambda identifier: folders[identifier])
    for key in ('LOCALAPPDATA', 'PROGRAMFILES', 'USERPROFILE', 'PATH'):
        monkeypatch.setenv(key, str(tmp_path / 'contributor'))
    assert opener._installation_roots() == [folders['F1B32785-6FBA-4FCF-9D55-7B8E7F157091'] / 'Programs/Microsoft VS Code',
                                            folders['905E63B6-C1BF-494E-B29C-65B732D3D21A'] / 'Microsoft VS Code',
                                            folders['7C5A40EF-A0FB-4BFC-874A-C0F2E0B9FA8E'] / 'Microsoft VS Code']


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
