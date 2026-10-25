"""Portable bounded untrusted artifact transfer controls; no optional SDK required."""
import base64
import io
import subprocess
import sys
import tarfile
from pathlib import PureWindowsPath

import pytest
from harbor_adapter import transfer
from harbor_adapter.transfer import unpack_regular
from swebench_adapter.containers import Docker


def archive(entries):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode='w') as stream:
        for name, kind, value in entries:
            info = tarfile.TarInfo(name)
            info.type = kind
            info.size = len(value) if kind == tarfile.REGTYPE else 0
            if kind == tarfile.SYMTYPE:
                info.linkname = '/etc/passwd'
            stream.addfile(info, io.BytesIO(value) if kind == tarfile.REGTYPE else None)
    return output.getvalue()


@pytest.mark.parametrize('entries', [
    [('../escape',tarfile.REGTYPE,b'x')], [('C:/outside',tarfile.REGTYPE,b'x')],
    [('NUL',tarfile.REGTYPE,b'x')], [('dir/CON.txt',tarfile.REGTYPE,b'x')],
    [('dir/trailing.',tarfile.REGTYPE,b'x')], [('dir/trailing ',tarfile.REGTYPE,b'x')],
    [('name:stream',tarfile.REGTYPE,b'x')],
    [('same.py',tarfile.REGTYPE,b'x'),('SAME.py',tarfile.REGTYPE,b'y')],
    [('file',tarfile.REGTYPE,b'x'),('file/child',tarfile.REGTYPE,b'y')], [('/absolute',tarfile.REGTYPE,b'x')],
    [('link',tarfile.SYMTYPE,b'')], [('fifo',tarfile.FIFOTYPE,b'')],
    [('same',tarfile.REGTYPE,b'x'),('same',tarfile.REGTYPE,b'y')],
])
def test_untrusted_artifact_archive_refused(tmp_path, entries):
    with pytest.raises(ValueError):
        unpack_regular(archive(entries), tmp_path / 'out')
    assert not (tmp_path / 'out').exists()


def test_regular_archive_transfer(tmp_path):
    files = unpack_regular(archive([('./source.py',tarfile.REGTYPE,b'pass\n')]), tmp_path / 'out')
    assert files == {'source.py': b'pass\n'}
    assert (tmp_path / 'out/source.py').read_bytes() == b'pass\n'




def test_windows_drive_join_regression(tmp_path):
    # The same archive entry escapes an apparently safe staging join on Windows.
    assert not (PureWindowsPath('D:/staging') / 'C:/outside').is_relative_to(PureWindowsPath('D:/staging'))
    with pytest.raises(ValueError, match='unsafe'):
        unpack_regular(archive([('C:/outside',tarfile.REGTYPE,b'x')]), tmp_path/'out')


@pytest.mark.parametrize('mode', ['valid','overflow','timeout'])
def test_real_bounded_collection_process(tmp_path, monkeypatch, mode):

    original = subprocess.Popen
    data = base64.b64encode(archive([('source.py',tarfile.REGTYPE,b'pass\n')])).decode()
    script = f'import base64,sys;sys.stdout.buffer.write(base64.b64decode({data!r}))'
    if mode == 'overflow':
        monkeypatch.setattr(transfer, 'LIMIT', 8192)
        script = 'import sys;sys.stdout.buffer.write(b"x"*65536)'
    elif mode == 'timeout':
        script = 'import time;time.sleep(10)'
    processes = []
    def launch(argv, **kwargs):
        process = original([sys.executable, '-c', script], **kwargs)
        processes.append(process)
        return process
    monkeypatch.setattr(transfer.subprocess, 'Popen', launch)
    if mode == 'valid':
        transfer.collect_tree(Docker(), 'fixture', '/app', tmp_path/'out')
        assert (tmp_path/'out/source.py').read_bytes() == b'pass\n'
    else:
        with pytest.raises((RuntimeError, subprocess.TimeoutExpired)):
            transfer.collect_tree(Docker(), 'fixture', '/app', tmp_path/'out', timeout_seconds=.05 if mode == 'timeout' else 2)
        assert not (tmp_path/'out').exists()
    assert all(process.poll() is not None for process in processes)


def test_empty_submission_is_collected_for_independent_failure(tmp_path):
    output = tmp_path/'empty'
    assert unpack_regular(archive([]), output) == {}
    assert output.is_dir()
