"""Offline package integrity and compatibility checks use real package bytes."""

import base64
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / 'skills/grafana/scripts'
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGP4//8/AAX+Av4N70a4AAAAAElFTkSuQmCC')


@pytest.fixture
def modules():
    loaded = []
    for name in ('grafana_evidence', 'grafana_capture'):
        spec = importlib.util.spec_from_file_location(name, ROOT / (name + '.py'))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        loaded.append(module)
    return loaded


def report():
    return {'schema_version': 1, 'operation': 'investigate', 'dashboard': {'uid': 'demo', 'title': 'Demo'},
            'provenance': {'grafana_url': 'https://grafana.example', 'organization_id': 1},
            'from_ms': 1000, 'to_ms': 2000, 'variables': {}, 'coverage': 'raw_queries_only',
            'panels': [{'id': 1, 'targets': [{'ref_id': 'A', 'mode': 'range', 'status': 'values_returned',
                                           'result': {'datasource': 'metrics', 'kind': 'prometheus', 'from': '1000', 'to': '2000',
                                                      'mode': 'range', 'expression': {'resolved': 'up'}, 'limits': {'intervalMs': 1000},
                                                      'results': {'A': {'frames': [{'data': {'values': [[1000], [1]]}}]}}}}]}]}


def manifest_update(path, change):
    value = json.loads((path / 'manifest.json').read_text())
    change(value)
    (path / 'manifest.json').write_text(json.dumps(value))


def test_verify_load_and_roundtrip(modules, tmp_path):
    evidence, capture = modules
    evidence.write_package(report(), tmp_path / 'out')
    receipt = capture.verify_package(tmp_path / 'out')
    assert receipt['status'] == 'verified' and receipt['files_verified'] == 2
    assert receipt['authenticity'] == 'not_established'
    assert capture.load_capture(tmp_path / 'out') == report()


def test_verified_image_names_come_only_from_manifest(modules, tmp_path):
    evidence, capture = modules
    value = report()
    value['panels'][0]['render'] = {'image_path': '/untrusted/outside.png', 'image_file': 'panel-999.png'}
    evidence.write_package(value, tmp_path / 'out', images={'panel-9.png': PNG, 'panel-1.png': PNG})
    assert capture.verify_package(tmp_path / 'out')['images'] == ['panel-1.png', 'panel-9.png']
    assert capture.load_capture(tmp_path / 'out') == value


def test_matching_manifest_does_not_make_corrupt_image_valid(modules, tmp_path):
    evidence, capture = modules
    output = tmp_path / 'out'
    evidence.write_package(report(), output, images={'panel-1.png': PNG})
    corrupt = bytearray(PNG)
    corrupt[45] ^= 1
    (output / 'panel-1.png').write_bytes(corrupt)
    manifest_update(output, lambda value: value['files']['panel-1.png'].update(sha256=hashlib.sha256(corrupt).hexdigest()))
    with pytest.raises(ValueError, match='PNG integrity or pixel decoding failed'):
        capture.verify_package(output)


def test_json_only_verification_needs_no_optional_dependencies(modules, tmp_path):
    evidence, _ = modules
    output = tmp_path / 'out'
    evidence.write_package(report(), output)
    script = """
import importlib.util
import sys
spec = importlib.util.spec_from_file_location('capture', sys.argv[1])
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)
assert capture.verify_package(sys.argv[2])['status'] == 'verified'
assert not {'deepdiff', 'PIL'} & sys.modules.keys()
"""
    result = subprocess.run([sys.executable, '-I', '-S', '-c', script, str(ROOT / 'grafana_capture.py'), str(output)],
                            capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('mutation,error', [
    ('tamper', 'mismatch'), ('incomplete', 'incomplete'), ('extra', 'unexpected'),
    ('schema', 'schema'), ('size', 'size'), ('missing', 'missing'),
])
def test_invalid_packages_refused(modules, tmp_path, mutation, error):
    evidence, capture = modules
    output = tmp_path / 'out'
    evidence.write_package(report(), output)
    if mutation == 'tamper':
        raw = (output / 'report.json').read_bytes().replace(b'Demo', b'Fake')
        (output / 'report.json').write_bytes(raw)
    elif mutation == 'incomplete':
        (output / '.incomplete').write_text('interrupted')
    elif mutation == 'extra':
        (output / 'unknown.json').write_text('{}')
    elif mutation == 'schema':
        manifest_update(output, lambda value: value.update(schema_version=2))
    elif mutation == 'size':
        manifest_update(output, lambda value: value['files']['report.json'].update(size_bytes=100000000))
    else:
        (output / 'report.html').unlink()
    with pytest.raises(ValueError, match=error):
        capture.load_capture(output)


def test_path_traversal_refused_before_file_read(modules, tmp_path):
    evidence, capture = modules
    output = tmp_path / 'out'
    evidence.write_package(report(), output)
    manifest_update(output, lambda value: value['files'].update({'../secret': {'size_bytes': 1, 'sha256': '0' * 64}}))
    with pytest.raises(ValueError):
        capture.verify_package(output)


def test_symlink_file_refused(modules, tmp_path):
    evidence, capture = modules
    output = tmp_path / 'out'
    evidence.write_package(report(), output)
    target = tmp_path / 'elsewhere'
    target.write_bytes((output / 'report.html').read_bytes())
    (output / 'report.html').unlink()
    try:
        (output / 'report.html').symlink_to(target)
    except OSError:
        pytest.skip('Host cannot create symlinks')
    with pytest.raises(ValueError, match='symlink'):
        capture.verify_package(output)


@pytest.mark.parametrize('raw', [b'{"schema_version":2}', b'{"schema_version":true}', b'{"schema_version":1,"schema_version":1}', b'{"value":NaN}', b'{"value":1e999}', b'{"panels":{}}'])
def test_invalid_report_schema_with_matching_hash_refused(modules, tmp_path, raw):
    evidence, capture = modules
    output = tmp_path / 'out'
    evidence.write_package({}, output)
    (output / 'report.json').write_bytes(raw)
    manifest_update(output, lambda value: value['files']['report.json'].update(size_bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
    with pytest.raises(ValueError):
        capture.load_capture(output)


def test_load_parses_verified_bytes_without_second_report_read(modules, tmp_path, monkeypatch):
    evidence, capture = modules
    output = tmp_path / 'out'
    evidence.write_package(report(), output)
    original = capture._read
    count = 0
    def read(path, limit):
        nonlocal count
        if path.name == 'report.json':
            count += 1
        return original(path, limit)
    monkeypatch.setattr(capture, '_read', read)
    assert capture.load_capture(output) == report()
    assert count == 1


def test_compatible_values_and_configuration_compared(modules):
    _, capture = modules
    before, after = report(), report()
    after['dashboard']['title'] = 'Renamed'
    after['panels'][0]['targets'][0]['result']['results']['A']['frames'][0]['data']['values'][1] = [2]
    result = capture.compare_captures(before, after)
    assert result['configuration']['changed'] is True
    assert result['values'][0]['status'] == 'compared'
    assert result['values'][0]['values_changed'] is True
    assert result['configuration']['differences']['changes'][0]['path'] == ['title']


@pytest.mark.parametrize('field', [
    'grafana_url', 'organization_id', 'from_ms', 'to_ms', 'variables', 'dashboard_uid', 'templating',
    'datasource', 'kind', 'from', 'to', 'mode', 'expression', 'limits', 'missing_full_results', 'partial',
])
def test_incompatible_values_explicitly_unsupported(modules, field):
    _, capture = modules
    before, after = report(), report()
    if field in ('grafana_url', 'organization_id'):
        after['provenance'][field] = 'different'
    elif field in ('from_ms', 'to_ms', 'variables'):
        after[field] = 'different'
    elif field == 'dashboard_uid':
        after['dashboard']['uid'] = 'different'
    elif field == 'templating':
        after['dashboard']['templating'] = {'different': True}
    elif field == 'partial':
        after['evidence'] = {'status': 'partial'}
    elif field == 'missing_full_results':
        del after['panels'][0]['targets'][0]['result']['results']
    else:
        after['panels'][0]['targets'][0]['result'][field] = {'different': True}
    result = capture.compare_captures(before, after)
    assert result['values'][0]['status'] == 'unsupported'
    assert result['values'][0]['reasons']
    assert 'values_changed' not in result['values'][0]
    assert 'differences' not in result['values'][0]


def test_coverage_diff_and_duplicate_identity(modules):
    _, capture = modules
    before, after = report(), report()
    after['panels'][0]['targets'][0]['status'] = 'query_failed'
    result = capture.compare_captures(before, after)
    assert result['coverage']['target_changes'][0]['after'] == 'query_failed'
    after['panels'][0]['targets'].append(copy.deepcopy(after['panels'][0]['targets'][0]))
    with pytest.raises(ValueError, match='ambiguous'):
        capture.compare_captures(before, after)


def compare_results(capture, before_value, after_value):
    before, after = report(), report()
    before['panels'][0]['targets'][0]['result']['results'] = before_value
    after['panels'][0]['targets'][0]['result']['results'] = after_value
    return capture.compare_captures(before, after)


@pytest.mark.parametrize('before,after,changed,kind', [
    ({'a': 1, 'b': 2}, {'b': 2, 'a': 1}, False, None),
    ([1, 2], [2, 1], True, 'values_changed'),
    ({'value': 1}, {'value': 1.0}, True, 'type_changes'),
    ({'value': False}, {'value': 0}, True, 'type_changes'),
    ({'value': [0.0]}, {'value': [-0.0]}, True, 'values_changed'),
    ({'__private': 1}, {'__private': 2}, True, 'values_changed'),
    ({'value': 'first\nsecond'}, {'value': 'first\nthird'}, True, 'values_changed'),
    ({'value': [1.25]}, {'value': [1.25]}, False, None),
])
def test_exact_content_semantics_and_structural_explanations(modules, before, after, changed, kind):
    _, capture = modules
    item = compare_results(capture, before, after)['values'][0]
    assert item['values_changed'] is changed
    assert item['differences']['status'] == 'complete'
    assert {value['kind'] for value in item['differences']['changes']} == ({kind} if kind else set())


def test_nested_changes_reference_values_without_copying_them(modules):
    _, capture = modules
    before = {'nested': {'removed': 'old-private-value', 'items': [1, 2], 'changed': 'before-private-value'}}
    after = {'nested': {'added': 'new-private-value', 'items': [1], 'changed': 'after-private-value'}}
    result = compare_results(capture, before, after)
    changes = {tuple(value['path']): value for value in result['values'][0]['differences']['changes']}
    assert {path: value['kind'] for path, value in changes.items()} == {
        ('nested', 'removed'): 'dictionary_item_removed',
        ('nested', 'added'): 'dictionary_item_added',
        ('nested', 'items', 1): 'iterable_item_removed',
        ('nested', 'changed'): 'values_changed',
    }
    assert changes['nested', 'added']['before_ref'] is None
    assert changes['nested', 'removed']['after_ref'] is None
    prefix = ['panels', 0, 'targets', 0, 'result', 'results']
    for path, change in changes.items():
        for side, source in (('before', before), ('after', after)):
            reference = change[side + '_ref']
            if reference is None:
                continue
            assert reference == {'capture': side, 'report_path': prefix + list(path), 'scope': 'value'}
            for part in path:
                source = source[part]
            assert source is not None
    assert 'private-value' not in json.dumps(result)


def test_array_additions_and_panel_reordering_keep_correct_source_paths(modules, tmp_path):
    evidence, capture = modules
    before, after = report(), report()
    before['panels'].append({'id': 2, 'targets': []})
    after['panels'].insert(0, {'id': 2, 'targets': []})
    after['panels'][1]['targets'][0]['result']['results']['A']['frames'].append({'data': {'values': [[2000], [2]]}})
    for name, value in (('before', before), ('after', after)):
        evidence.write_package(value, tmp_path / name)
    result = capture.compare_captures(capture.load_capture(tmp_path / 'before'), capture.load_capture(tmp_path / 'after'))
    change, = result['values'][0]['differences']['changes']
    assert change['kind'] == 'iterable_item_added'
    assert change['before_ref'] is None
    assert change['after_ref']['report_path'] == ['panels', 1, 'targets', 0, 'result', 'results', 'A', 'frames', 1]


@pytest.mark.parametrize('key', ['secret-' * 100, 'control\nkey', '\U0001f4ca' * 200])
def test_unbounded_or_control_character_paths_are_omitted(modules, key):
    _, capture = modules
    result = compare_results(capture, {'nested': {key: 1}}, {'nested': {key: 2}})
    change, = result['values'][0]['differences']['changes']
    assert change['path'] is None and change['path_omitted'] is True
    assert change['before_ref']['scope'] == 'subtree'
    assert change['before_ref']['report_path'] == ['panels', 0, 'targets', 0, 'result', 'results']
    assert key not in json.dumps(result, ensure_ascii=False)


def test_report_wide_change_budget_retains_exact_value_change_flag(modules):
    _, capture = modules
    before, after = report(), report()
    before['dashboard']['settings'] = list(range(150))
    after['dashboard']['settings'] = list(range(150, 300))
    before['panels'][0]['targets'][0]['result']['results'] = list(range(100))
    after['panels'][0]['targets'][0]['result']['results'] = list(range(100, 200))
    result = capture.compare_captures(before, after)
    assert result['truncated'] is True
    assert len(result['configuration']['differences']['changes']) == 150
    value = result['values'][0]
    assert value['values_changed'] is True
    assert len(value['differences']['changes']) == 50
    assert value['differences']['reasons'] == ['detail_output_limit']


@pytest.mark.parametrize('limit', ['bytes', 'nodes', 'depth', 'work'])
def test_detail_limits_do_not_claim_unchanged_values(modules, limit):
    _, capture = modules
    if limit == 'bytes':
        before, after = 'a' * capture.MAX_DETAIL_BYTES, 'b' * capture.MAX_DETAIL_BYTES
        reason = 'detail_input_size_limit'
    elif limit == 'nodes':
        before, after = [0] * capture.MAX_DETAIL_NODES, [1] * capture.MAX_DETAIL_NODES
        reason = 'detail_input_node_limit'
    elif limit == 'depth':
        before, after = 0, 1
        for _ in range(capture.MAX_DETAIL_DEPTH + 1):
            before, after = [before], [after]
        reason = 'detail_input_depth_limit'
    else:
        before, after = list(range(6000)), list(range(6000, 12000))
        reason = 'detail_work_limit'
    result = compare_results(capture, before, after)
    assert result['values'][0]['values_changed'] is True
    details = result['values'][0]['differences']
    assert details['status'] == 'truncated'
    assert reason in details['reasons']
    assert result['truncated'] is True


def test_target_limit_reports_omitted_target_count(modules):
    _, capture = modules
    before, after = report(), report()
    target = before['panels'][0]['targets'][0]
    before['panels'][0]['targets'] = [{**target, 'ref_id': str(index)} for index in range(capture.MAX_DIFF_ITEMS + 1)]
    after['panels'][0]['targets'] = copy.deepcopy(before['panels'][0]['targets'])
    result = capture.compare_captures(before, after)
    assert len(result['values']) == capture.MAX_DIFF_ITEMS
    assert result['value_target_count'] == capture.MAX_DIFF_ITEMS + 1
    assert result['truncated'] is True
