"""Bundled imports remain isolated, reusable and recoverable under Python -I."""

import runpy
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/grafana/scripts'


def loader(directory=SCRIPTS):
    return runpy.run_path(str(directory / 'grafana_modules.py'))['load_module']


def bundle(tmp_path, name):
    directory = tmp_path / name
    directory.mkdir()
    shutil.copyfile(SCRIPTS / 'grafana_modules.py', directory / 'grafana_modules.py')
    return directory


@pytest.mark.parametrize('name', ['../grafana_read', 'grafana_read.py', '/grafana_read', 'os', '', None])
def test_only_fixed_sibling_names_can_select_code(name):
    with pytest.raises(ValueError, match=r'^unsupported_grafana_module$'):
        loader()(name)


def test_repeated_bootstrap_reuses_modules_without_public_name_or_path_changes(monkeypatch):
    sentinel = object()
    monkeypatch.setitem(sys.modules, 'grafana_read', sentinel)
    search_path = list(sys.path)
    first = loader()('grafana_read')
    second = loader()('grafana_read')
    assert first is second
    assert sys.modules[first.__name__] is first
    assert sys.modules['grafana_read'] is sentinel
    assert sys.path == search_path


def test_different_bundles_never_reuse_each_others_modules(tmp_path):
    first, second = (bundle(tmp_path, name) for name in ('canonical', 'projection'))
    for directory in (first, second):
        (directory / 'grafana_plan.py').write_text(f'IDENTITY = {directory.name!r}\n', encoding='utf-8')
    assert loader(first)('grafana_plan').IDENTITY == 'canonical'
    assert loader(second)('grafana_plan').IDENTITY == 'projection'
    assert loader(first)('grafana_plan') is not loader(second)('grafana_plan')


@pytest.mark.parametrize('failure', ['RuntimeError', 'SystemExit'])
def test_failed_import_does_not_leave_a_partially_initialized_module(tmp_path, failure):
    directory = bundle(tmp_path, 'failed')
    path = directory / 'grafana_plan.py'
    path.write_text(f'PARTIAL = True\nraise {failure}("failure")\n', encoding='utf-8')
    load = loader(directory)
    with pytest.raises((RuntimeError, SystemExit), match='failure'):
        load('grafana_plan')
    path.write_text('READY = True\n', encoding='utf-8')
    module = load('grafana_plan')
    assert module.READY is True
    assert not hasattr(module, 'PARTIAL')


def test_a_foreign_cached_module_is_refused(monkeypatch):
    load = loader()
    module = load('grafana_read')
    monkeypatch.setattr(module, '__file__', 'unrelated/grafana_read.py')
    with pytest.raises(ValueError, match=r'^unexpected_grafana_module$'):
        load('grafana_read')


@pytest.mark.parametrize('first', ['grafana_analyze', 'grafana_frames', 'grafana_alert_preview', 'grafana_capture'])
def test_fresh_process_import_orders_share_reader_and_keep_optional_libraries_lazy(tmp_path, first):
    # A working-directory sibling must never win even if its name matches the bundle.
    for name in ('grafana_modules', 'grafana_read', 'grafana_frames', 'promql_parser'):
        (tmp_path / (name + '.py')).write_text('raise AssertionError("cwd code executed")\n', encoding='utf-8')
    code = """
import runpy, sys
from pathlib import Path
root = Path(sys.argv[1])
load = runpy.run_path(str(root / 'grafana_modules.py'))['load_module']
search_path = list(sys.path)
load(sys.argv[2])
workflow = runpy.run_path(str(root / 'grafana_workflow.py'))
reader = workflow['reader']
assert load('grafana_frames').reader is reader
assert load('grafana_alert_preview').reader is reader
assert load('grafana_analyze').frames is load('grafana_frames')
assert load('grafana_capture')._module('grafana_evidence') is load('grafana_evidence')
assert workflow['parse_args'](['doctor', '--agent-json']).command == 'doctor'
assert reader.parse_args(['dashboard', '--uid', 'board']).uid == 'board'
assert sys.path == search_path
assert not {'polars', 'promql_parser', 'deepdiff', 'PIL'} & sys.modules.keys()
"""
    result = subprocess.run([sys.executable, '-I', '-S', '-c', code, str(SCRIPTS), first],
                            cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr


def test_reader_can_still_run_as_a_single_stdlib_file(tmp_path):
    path = tmp_path / 'grafana_read.py'
    shutil.copyfile(SCRIPTS / path.name, path)
    code = """
import runpy, sys
reader = runpy.run_path(sys.argv[1])
assert reader['parse_args'](['dashboard', '--uid', 'board']).uid == 'board'
assert reader['frame_columns']({'schema': {'fields': []}, 'data': {'values': []}}) == (([], []), None)
"""
    result = subprocess.run([sys.executable, '-I', '-S', '-c', code, str(path)],
                            cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
