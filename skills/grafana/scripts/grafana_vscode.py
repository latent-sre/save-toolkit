"""Open a completed local report in the existing VS Code desktop window.

Python 3.12+, stdlib only. No server, extension installation, settings mutation,
shell command strings, or report-controlled executable arguments.
"""
import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path

_PLATFORM = sys.platform
_CLI_ENVIRONMENT = frozenset({
    'VSCODE_IPC_HOOK_CLI', 'VSCODE_PID', 'SYSTEMROOT', 'WINDIR',
    'HOME', 'USERPROFILE', 'APPDATA', 'LOCALAPPDATA', 'TMP', 'TEMP', 'TMPDIR',
    'LANG', 'LC_ALL', 'LC_CTYPE', 'DISPLAY', 'WAYLAND_DISPLAY', 'XDG_RUNTIME_DIR',
    'DBUS_SESSION_BUS_ADDRESS',
})


def _session_pid(environ):
    value = environ.get('VSCODE_PID', '')
    if not value.isascii() or not value.isdigit() or not 1 <= int(value) <= 2**32 - 1:
        return None
    return int(value)


def _session_running(environ):
    """Read-only liveness check; never invoke a CLI that could cold-start another session."""
    pid = _session_pid(environ)
    if pid is None:
        return False
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


def _session_executable(environ):
    """Ask the OS for the marked process image; its location still needs validation."""
    pid = _session_pid(environ)
    if pid is None:
        return None
    if _PLATFORM == 'linux':
        return Path(os.readlink(f'/proc/{pid}/exe'))
    import ctypes  # noqa: PLC0415
    if _PLATFORM == 'darwin':
        library = ctypes.CDLL('/usr/lib/libproc.dylib')
        library.proc_pidpath.argtypes = (ctypes.c_int, ctypes.c_void_p, ctypes.c_uint32)
        library.proc_pidpath.restype = ctypes.c_int
        buffer = ctypes.create_string_buffer(4096)
        size = library.proc_pidpath(pid, buffer, len(buffer))
        return Path(os.fsdecode(buffer.value)) if 0 < size < len(buffer) else None
    if _PLATFORM != 'win32':
        return None
    from ctypes import wintypes  # noqa: PLC0415
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = (wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR,
                                                 ctypes.POINTER(wintypes.DWORD))
    kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel.OpenProcess(0x1000, False, pid)
    if not handle:
        return None
    try:
        buffer = ctypes.create_unicode_buffer(32768)
        size = wintypes.DWORD(len(buffer))
        return Path(buffer.value) if kernel.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)) else None
    finally:
        kernel.CloseHandle(handle)


def _windows_known_folder(identifier):
    import ctypes  # noqa: PLC0415
    from ctypes import wintypes  # noqa: PLC0415
    from uuid import UUID  # noqa: PLC0415
    shell = ctypes.WinDLL('shell32')
    shell.SHGetKnownFolderPath.argtypes = (ctypes.c_void_p, wintypes.DWORD, wintypes.HANDLE,
                                          ctypes.POINTER(ctypes.c_wchar_p))
    shell.SHGetKnownFolderPath.restype = ctypes.c_long
    ole = ctypes.WinDLL('ole32')
    ole.CoTaskMemFree.argtypes = (ctypes.c_void_p,)
    identifier = (ctypes.c_ubyte * 16).from_buffer_copy(UUID(identifier).bytes_le)
    value = ctypes.c_wchar_p()
    try:
        if shell.SHGetKnownFolderPath(ctypes.byref(identifier), 0, None, ctypes.byref(value)) != 0 or not value.value:
            return None
        return Path(value.value)
    finally:
        ole.CoTaskMemFree(value)


def _installation_roots():
    """Standard installation locations come from the OS, never workspace environment."""
    if _PLATFORM == 'win32':
        locations = (
            ('F1B32785-6FBA-4FCF-9D55-7B8E7F157091', ('Programs', 'Microsoft VS Code')),
            ('905E63B6-C1BF-494E-B29C-65B732D3D21A', ('Microsoft VS Code',)),
            ('7C5A40EF-A0FB-4BFC-874A-C0F2E0B9FA8E', ('Microsoft VS Code',)),
        )
        return [path.joinpath(*suffix) for identifier, suffix in locations
                if (path := _windows_known_folder(identifier)) is not None]
    if _PLATFORM == 'linux':
        return [Path('/usr/share/code'), Path('/snap/code/current/usr/share/code')]
    if _PLATFORM == 'darwin':
        import pwd  # noqa: PLC0415
        home = Path(pwd.getpwuid(os.getuid()).pw_dir)
        return [Path('/Applications/Visual Studio Code.app'), home / 'Applications/Visual Studio Code.app']
    return []


def _trusted_installation(root, paths):
    workspace = Path.cwd().resolve()
    root = root.resolve(strict=True)
    paths = [path.resolve(strict=True) for path in paths]
    if root.is_relative_to(workspace) or workspace.is_relative_to(root):
        return False
    if any(not path.is_relative_to(root) or path.is_relative_to(workspace) for path in paths):
        return False
    if _PLATFORM == 'linux':
        # System package roots and every loaded file must be immutable to ordinary users.
        checked = {root, *root.parents, *paths}
        for path in paths:
            checked.update(parent for parent in path.parents if parent.is_relative_to(root))
        if any((metadata := path.stat()).st_uid != 0 or metadata.st_mode & (stat.S_IWGRP | stat.S_IWOTH)
               for path in checked):
            return False
    return True


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
    running = _session_executable(environ)
    if running is None or not running.is_absolute():
        return None, {}
    running = running.resolve(strict=True)
    for root in _installation_roots():
        try:
            if _PLATFORM == 'win32':
                executable = root / 'Code.exe'
                launcher = root / 'bin/code.cmd'
                if executable.resolve(strict=True) != running:
                    continue
                command = _windows_command(launcher)
                if command is None or not _trusted_installation(root, [launcher, *map(Path, command)]):
                    continue
            else:
                executable = root / ('Contents/MacOS/Code' if _PLATFORM == 'darwin' else 'code')
                cli = root / ('Contents/Resources/app/out/cli.js' if _PLATFORM == 'darwin' else 'resources/app/out/cli.js')
                if executable.resolve(strict=True) != running or not cli.is_file():
                    continue
                if not _trusted_installation(root, [executable, cli]):
                    continue
                command = [str(executable), str(cli)]
            return [str(Path(part).resolve(strict=True)) for part in command], {'ELECTRON_RUN_AS_NODE': '1', 'VSCODE_DEV': ''}
        except OSError:
            continue
    return None, {}


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
        child_env = {key: value for key, value in environ.items() if key.upper() in _CLI_ENVIRONMENT}
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
