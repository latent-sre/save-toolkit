"""Offline package integrity and compatibility checks use real package bytes."""

import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1] / 'skills/grafana/scripts'


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
    png = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aPioAAAAASUVORK5CYII=')
    value = report()
    value['panels'][0]['render'] = {'image_path': '/untrusted/outside.png', 'image_file': 'panel-999.png'}
    evidence.write_package(value, tmp_path / 'out', images={'panel-9.png': png, 'panel-1.png': png})
    assert capture.verify_package(tmp_path / 'out')['images'] == ['panel-1.png', 'panel-9.png']
    assert capture.load_capture(tmp_path / 'out') == value


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


@pytest.mark.parametrize('field', ['grafana_url', 'organization_id', 'from_ms', 'variables', 'expression', 'limits', 'partial'])
def test_incompatible_values_explicitly_unsupported(modules, field):
    _, capture = modules
    before, after = report(), report()
    if field in ('grafana_url', 'organization_id'):
        after['provenance'][field] = 'different'
    elif field in ('from_ms', 'variables'):
        after[field] = 'different'
    elif field == 'partial':
        after['evidence'] = {'status': 'partial'}
    else:
        after['panels'][0]['targets'][0]['result'][field] = {'different': True}
    result = capture.compare_captures(before, after)
    assert result['values'][0]['status'] == 'unsupported'
    assert result['values'][0]['reasons']
    assert 'values_changed' not in result['values'][0]


def test_coverage_diff_and_duplicate_identity(modules):
    _, capture = modules
    before, after = report(), report()
    after['panels'][0]['targets'][0]['status'] = 'query_failed'
    result = capture.compare_captures(before, after)
    assert result['coverage']['target_changes'][0]['after'] == 'query_failed'
    after['panels'][0]['targets'].append(copy.deepcopy(after['panels'][0]['targets'][0]))
    with pytest.raises(ValueError, match='ambiguous'):
        capture.compare_captures(before, after)
