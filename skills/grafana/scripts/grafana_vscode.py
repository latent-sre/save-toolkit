"""Open a completed local report in the existing VS Code desktop window.

Python 3.12+, stdlib only. No server, extension installation, settings mutation,
shell command strings, or report-controlled executable arguments.
"""
import json
import os
import re
import subprocess
from pathlib import Path


def _session_running(environ):
    """Read-only liveness check; never invoke a CLI that could cold-start another session."""
    value = environ.get('VSCODE_PID', '')
    if not value.isascii() or not value.isdigit() or not 1 <= int(value) <= 2**32 - 1:
        return False
    pid = int(value)
    if os.name != 'nt':
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    import ctypes  # noqa: PLC0415
    from ctypes import wintypes  # noqa: PLC0415
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return False
    try:
        exit_code = wintypes.DWORD()
        return bool(kernel.GetExitCodeProcess(handle, ctypes.byref(exit_code))) and exit_code.value == 259
    finally:
        kernel.CloseHandle(handle)


def _association_available(directory):
    # Use the invoking workspace, not report-controlled settings or a replacement workspace.
    workspace = Path.cwd().resolve()
    if not directory.is_relative_to(workspace):
        return False
    settings = workspace / '.vscode' / 'settings.json'
    try:
        with settings.open(encoding='utf-8-sig') as stream:
            raw = stream.read(65537)
        if len(raw) > 65536:
            return False
        parsed = json.loads(raw)
        return parsed.get('workbench.editorAssociations', {}).get('**/report.html') == 'workbench.editor.browser'
    except (OSError, ValueError, AttributeError):
        return False


def _windows_command(launcher):
    # Do not execute a .cmd with report paths: Windows batch parsing can interpret metacharacters.
    # Match only the installed Code shim's fixed cli.js path, including versioned install layouts.
    root = launcher.parent.parent
    with launcher.open('r', encoding='utf-8-sig') as stream:
        shim = stream.read(16385)
    if len(shim) > 16384:
        return None
    paths = re.findall(r'"%~dp0\.\.\\((?:[A-Za-z0-9_-]+\\)?resources\\app\\out\\cli\.js)"', shim)
    if len(paths) != 1:
        return None
    executable, cli = root / 'Code.exe', root.joinpath(*paths[0].split('\\'))
    if not executable.is_file() or not cli.is_file():
        return None
    return [str(executable), str(cli)]


def _command(environ):
    # Search the operator's absolute PATH directories, not the output directory or the CWD.
    candidates = (Path(part) / ('code.cmd' if os.name == 'nt' else 'code')
                  for part in environ.get('PATH', '').split(os.pathsep)
                  if part and Path(part).is_absolute() and Path(part).resolve() != Path.cwd().resolve())
    located = next((path for path in candidates if path.is_file() and (os.name == 'nt' or os.access(path, os.X_OK))), None)
    if not located:
        return None, {}
    launcher = Path(located).absolute()
    if os.name == 'nt':
        return _windows_command(launcher), {'ELECTRON_RUN_AS_NODE': '1', 'VSCODE_DEV': ''}
    return [str(launcher)], {}


def open_report(directory, *, environ=None, runner=None):
    """Dispatch once after packaging. Launch failure never invalidates the saved evidence.

    A zero CLI exit proves dispatch only; the user or browser tools verify the visible report.
    Timeout is unknown dispatch, never retried automatically.
    """
    environ = dict(os.environ if environ is None else environ)
    runner = subprocess.run if runner is None else runner
    result = {'status': 'unavailable', 'target': 'vscode_integrated_browser', 'visual_verification': 'not_performed'}
    try:
        directory = Path(directory).resolve()
        if any(environ.get(name) for name in ('VSCODE_REMOTE_NAME', 'WSL_DISTRO_NAME', 'SSH_CONNECTION', 'CODESPACES')):
            return {**result, 'error': 'local_vscode_desktop_required'}
        if not (directory / 'report.html').is_file():
            return {**result, 'error': 'report_files_unavailable'}
        if not _session_running(environ):
            return {**result, 'error': 'existing_vscode_session_required'}
        if not _association_available(directory):
            return {**result, 'error': 'vscode_browser_association_required'}
        command, additions = _command(environ)
        if not command:
            return {**result, 'error': 'vscode_cli_unavailable'}
        child_env = {key: value for key, value in environ.items() if not key.upper().startswith('GRAFANA_')}
        child_env.update(additions)
        options = {'env': child_env, 'stdin': subprocess.DEVNULL, 'stdout': subprocess.PIPE,
                   'stderr': subprocess.DEVNULL, 'timeout': 15, 'check': False, 'shell': False}
        if os.name == 'nt':
            options['creationflags'] = subprocess.CREATE_NO_WINDOW
        version = runner([*command, '--version'], **options)
        match = re.search(rb'(?m)^(\d+)\.(\d+)\.(\d+)', version.stdout or b'')
        if version.returncode != 0 or match is None:
            return {**result, 'error': 'vscode_version_unknown'}
        if (int(match[1]), int(match[2])) < (1, 134):
            return {**result, 'error': 'vscode_version_unsupported'}
        try:
            launched = runner([*command, '--reuse-window', str(directory / 'report.html')], **options)
        except subprocess.TimeoutExpired:
            return {**result, 'status': 'unknown', 'error': 'vscode_launch_timeout'}
        if launched.returncode != 0:
            return {**result, 'error': 'vscode_launch_failed'}
        return {**result, 'status': 'launch_requested'}
    except (OSError, ValueError, subprocess.SubprocessError):
        return {**result, 'error': 'vscode_launch_unavailable'}
