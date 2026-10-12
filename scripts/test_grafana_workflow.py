"""Workflow integration tests use the real read client and a fake HTTP boundary."""
import hashlib
import io
import json
import os
import struct
import subprocess
import sys
import zlib
from pathlib import Path

import pytest

from testkit import load_path

ROOT = Path(__file__).resolve().parents[1]


def test_missing_dependencies_fail_before_collection_under_no_site():
    result = subprocess.run([
        sys.executable, '-I', '-S', str(ROOT / 'skills/grafana/scripts/grafana_workflow.py'),
        'investigate', '--uid', 'board', '--from', '1000', '--to', '61000', '--render', 'none', '--agent-json',
    ], capture_output=True, text=True, timeout=15, check=False)
    assert result.returncode == 2
    assert json.loads(result.stdout) == {'ok': False, 'error': 'dependency_unavailable_polars'}
    assert not result.stderr


def test_doctor_reports_dependency_runtime_without_importing_telemetry():
    workflow = load_path(ROOT / 'skills/grafana/scripts/grafana_workflow.py', 'grafana_workflow')
    def no_network(*_args, **_kwargs):
        pytest.fail('doctor contacted Grafana without --probe')
    result = workflow.doctor(ENV, no_network)
    assert result['connection'] == 'not_checked'
    assert result['runtime']['site_enabled']
    assert all(item['available'] and item['version'] for item in result['runtime']['dependencies'].values())


def test_native_offline_analysis_uses_venv_packages_not_working_directory(tmp_path):
    code, _, _ = run_workflow(tmp_path, HTTP(), extra=['--render', 'none'])
    assert code == 0
    (tmp_path / 'polars.py').write_text("raise RuntimeError('untrusted cwd module')")
    result = subprocess.run([
        sys.executable, '-I', str(ROOT / 'skills/grafana/scripts/grafana_workflow.py'),
        'analyze', '--package-dir', str(tmp_path / 'capture'), '--analysis', 'summary', '--agent-json',
    ], cwd=tmp_path, env={**os.environ, 'PYTHONPATH': str(tmp_path)},
        capture_output=True, text=True, timeout=30, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(result.stdout)['data']
    assert 'series_statistics' in data['summary']['panels'][0]['targets'][0]


def test_dashboard_investigation_writes_package_and_keeps_empty_distinct(tmp_path):
    workflow = load_path(ROOT / 'skills/grafana/scripts/grafana_workflow.py', 'grafana_workflow')
    calls = []
    panel = {'id': 1, 'type': 'timeseries', 'title': '<GPU>',
             'datasource': {'uid': 'prom', 'type': 'prometheus'},
             'targets': [{'refId': 'A', 'expr': 'up'}, {'refId': 'B', 'expr': 'missing'}]}
    board = {'dashboard': {'uid': 'board', 'version': 1, 'title': 'Ops', 'panels': [panel]},
             'meta': {'folderUid': 'ops'}}

    def transport(request, **_bounds):
        calls.append(request)
        path = request.full_url.split('example.test')[-1]
        if path == '/api/org':
            value = {'id': 1}
        elif path == '/api/dashboards/uid/board':
            value = board
        elif path.startswith('/api/datasources/uid/prom'):
            value = {'uid': 'prom', 'type': 'prometheus'}
        elif path == '/api/ds/query':
            query = json.loads(request.data)['queries'][0]
            frames = [] if query['expr'] == 'missing' else [{'schema': {'fields': [
                {'name': 'Time', 'type': 'time'}, {'name': 'Value', 'type': 'number'}]},
                'data': {'values': [[1000, 61000], [0, 1]]}}]
            value = {'results': {'A': {'frames': frames}}}
        elif path.startswith('/api/annotations'):
            value = []
        else:
            value = {'status': 'success', 'data': {'groups': []}}
        return 200, json.dumps(value).encode()

    output = io.StringIO()
    destination = tmp_path / 'capture'
    code = workflow.main(['investigate', '--uid', 'board', '--from', '1000', '--to', '61000',
                          '--output-dir', str(destination)],
                         environ={'GRAFANA_URL': 'https://example.test', 'GRAFANA_ORG_ID': '1',
                                  'GRAFANA_SA_TOKEN': 'private-token'}, transport=transport, output=output)
    assert code == 0, output.getvalue()
    report = json.loads((destination / 'report.json').read_text())
    assert [target['status'] for target in report['panels'][0]['targets']] == ['values_returned', 'no_data']
    assert report['panels'][0]['coverage'] == 'raw_queries_only'
    assert (destination / 'report.html').is_file() and (destination / 'manifest.json').is_file()
    assert all(call.method == 'GET' or call.full_url.endswith('/api/ds/query') for call in calls)
    assert 'private-token' not in (destination / 'report.json').read_text()


ENV = {'GRAFANA_URL': 'https://example.test', 'GRAFANA_ORG_ID': '1', 'GRAFANA_SA_TOKEN': 'private-token'}


def sample_panel(**updates):
    return {'id': 1, 'type': 'timeseries', 'title': 'GPU', 'datasource': {'uid': 'prom', 'type': 'prometheus'},
            'targets': [{'refId': 'A', 'expr': 'up'}], **updates}


class HTTP:
    def __init__(self, panel=None, *, query=None, org=1, rules=None, items=None):
        self.board = {'dashboard': {'uid': 'board', 'version': 1, 'title': 'private-token',
                                    'panels': [sample_panel() if panel is None else panel]}, 'meta': {'folderUid': 'ops'}}
        self.calls = []
        self.org, self.rules = org, rules or []
        self.items = [{'uid': 'board', 'folderUid': 'ops'}] if items is None else items
        self.query = query or {'results': {'A': {'frames': [{'schema': {'fields': [
            {'name': 'Time', 'type': 'time'}, {'name': 'Value', 'type': 'number', 'labels': {'host': 'example-host'}}]},
            'data': {'values': [[1000, 31000, 61000], [1, 1, 1]]}}]}}}

    def __call__(self, request, **bounds):
        self.calls.append(request)
        assert 0 < bounds['timeout'] <= 45
        path = request.full_url.split('example.test')[-1]
        if path == '/api/org':
            result = {'id': self.org}
        elif path == '/api/dashboards/uid/board':
            result = self.board
        elif path.startswith('/api/datasources/uid/'):
            uid = path.split('/uid/')[1].split('?')[0]
            result = {'uid': uid, 'type': path.split('ds_type=')[1]}
        elif path == '/api/ds/query':
            result = self.query
        elif path.startswith('/api/annotations'):
            result = []
        elif path.startswith('/api/search'):
            result = self.items
        elif path == '/api/v1/provisioning/alert-rules':
            result = self.rules
        elif path.startswith('/api/prometheus/grafana/api/v1/rules'):
            result = {'status': 'success', 'data': {'groups': []}}
        elif path.startswith('/render/d-solo/'):
            return 503, b'renderer unavailable'
        else:
            raise AssertionError(path)
        return 200, json.dumps(result).encode()


def run_workflow(tmp_path, http, extra=(), *, command=None):
    workflow = load_path(ROOT / 'skills/grafana/scripts/grafana_workflow.py', 'grafana_workflow')
    args = ['investigate', '--uid', 'board', '--from', '1000', '--to', '61000'] if command is None else command
    output = io.StringIO()
    destination = tmp_path / 'capture'
    code = workflow.main([*args, *extra, '--output-dir', str(destination)], environ=ENV, transport=http, output=output)
    response = json.loads(output.getvalue())
    report = json.loads((destination / 'report.json').read_text()) if (destination / 'report.json').is_file() else None
    return code, response, report


@pytest.mark.parametrize('panel', [sample_panel(libraryPanel={'uid': 'library'}), sample_panel(timeShift='1d'),
    sample_panel(repeat='host'), sample_panel(scopedVars={'host': {'value': 'x'}}),
    {'id': 8, 'type': 'row', 'repeat': 'host', 'panels': [sample_panel()]}])
def test_context_dependent_panels_are_not_replayed_with_wrong_scope(tmp_path, panel):
    http = HTTP(panel)
    code, _, report = run_workflow(tmp_path, http)
    assert code == 0 and report['panels'][0]['status'] == 'unsupported'
    assert report['panels'][0]['gaps']
    assert not any(call.method == 'POST' for call in http.calls)


@pytest.mark.parametrize('target', [{'expr': 'up', 'datasource': {'uid': 'db', 'type': 'mysql'}},
    {'expr': 'up{host="$host"}'}, {'expr': 'up', 'format': 'table'}, {'expr': 'up', 'interval': '30s'},
    {'expr': 'up', 'instant': False, 'range': False}, {'expr': '$__rate_interval'}])
def test_unsupported_targets_keep_their_gap_and_do_not_issue_queries(tmp_path, target):
    http = HTTP(sample_panel(targets=[target]))
    code, _, report = run_workflow(tmp_path, http)
    assert code == 0 and report['panels'][0]['targets'][0]['status'] == 'unsupported'
    assert not any(call.method == 'POST' for call in http.calls)


def test_explicit_variables_and_both_query_modes_are_recorded(tmp_path):
    http = HTTP(sample_panel(targets=[{'refId': 'A', 'expr': 'up{host="$host"}', 'range': True, 'instant': True}]))
    code, _, report = run_workflow(tmp_path, http, ['--var', 'host=example-host'])
    assert code == 0
    queries = [json.loads(call.data)['queries'][0] for call in http.calls if call.method == 'POST']
    assert [(q['range'], q['instant']) for q in queries] == [(True, False), (False, True)]
    assert all(q['expr'] == 'up{host="example-host"}' for q in queries)
    assert report['variables'] == {'host': 'example-host'}


def test_query_failure_is_not_empty_data(tmp_path):
    http = HTTP(query={'results': {'A': {'error': 'private-token rejected', 'frames': []}}})
    code, _, report = run_workflow(tmp_path, http)
    assert code == 0 and report['panels'][0]['targets'][0]['status'] == 'query_failed'
    assert 'private-token' not in (tmp_path / 'capture' / 'report.json').read_text()
    assert 'private-token' not in (tmp_path / 'capture' / 'report.html').read_text()


def test_query_budget_and_transformation_gap_are_explicit(tmp_path):
    http = HTTP(sample_panel(targets=[{'refId': 'A', 'expr': 'up'}, {'refId': 'B', 'expr': 'other'}],
                             transformations=[{'id': 'reduce'}]))
    code, _, report = run_workflow(tmp_path, http, ['--max-queries', '1'])
    assert code == 0
    assert report['queries_attempted'] == 1
    assert report['panels'][0]['targets'][1]['error'] == 'query_limit_reached'
    assert 'transformations_not_applied' in report['panels'][0]['gaps']


def test_wrong_organization_stops_before_dashboard_and_artifacts(tmp_path):
    http = HTTP(org=99)
    code, response, report = run_workflow(tmp_path, http)
    assert code == 2 and response['error'] == 'organization_mismatch' and report is None
    assert len(http.calls) == 1 and not (tmp_path / 'capture').exists()


def test_existing_output_is_refused_before_connecting(tmp_path):
    (tmp_path / 'capture').mkdir()
    http = HTTP()
    code, response, _ = run_workflow(tmp_path, http)
    assert code == 2 and response['error'] == 'output_directory_exists' and not http.calls


def test_folder_map_filters_alerts_and_never_runs_data_queries(tmp_path):
    http = HTTP(rules=[{'uid': 'rule', 'folderUID': 'ops', 'orgID': 1, 'title': 'Alert', 'data': []},
                       {'uid': 'elsewhere', 'folderUID': 'elsewhere', 'orgID': 1, 'title': 'Unrelated'}])
    code, _, report = run_workflow(tmp_path, http, command=['dependencies', '--folder-uid', 'ops'])
    assert code == 0
    assert [capture['rule']['uid'] for capture in report['alert_captures']] == ['rule']
    assert 'Unrelated' not in json.dumps(report)
    assert report['discovery']['coverage'] == 'permission_scoped'
    assert all(call.method == 'GET' for call in http.calls)


def test_folder_map_refuses_unscoped_search_response(tmp_path):
    http = HTTP(items=[{'uid': 'board', 'folderUid': 'other'}])
    code, response, report = run_workflow(tmp_path, http, command=['dependencies', '--folder-uid', 'ops'])
    assert code == 2 and response['error'] == 'folder_mismatch' and report is None
    assert len(http.calls) == 2


def test_preview_uses_report_query_without_credentials_or_network(tmp_path):
    http = HTTP()
    code, _, investigation = run_workflow(tmp_path, http)
    assert code == 0
    source = tmp_path / 'source.json'
    source.write_text(json.dumps(investigation))
    preview_dir = tmp_path / 'offline'
    preview_dir.mkdir()

    def no_network(*_args, **_kwargs):
        pytest.fail('Offline preview attempted network access')

    code, _, report = run_workflow(preview_dir, no_network, command=[
        'alert-preview', '--report-file', str(source), '--panel', '1', '--ref-id', 'A',
        '--operator', 'gt', '--threshold', '0', '--pending-ms', '30000', '--step-ms', '30000'])
    assert code == 0 and report['coverage'] == 'sampled_threshold_preview'
    assert report['series'][0]['intervals'][0]['start_ms'] == 31000
    assert report['notification_delivery'] == 'not_evaluated'


@pytest.mark.parametrize('source_flag', ['--source-id', '--package-dir'])
def test_packaged_preview_identifies_exact_verified_report_bytes(tmp_path, monkeypatch, source_flag):
    workflow = load_path(ROOT / 'skills/grafana/scripts/grafana_workflow.py', 'grafana_workflow')
    code, _, _ = run_workflow(tmp_path, HTTP())
    assert code == 0
    package = tmp_path / 'capture'
    raw = (package / 'report.json').read_bytes()
    canonical = json.dumps(json.loads(raw), sort_keys=True, allow_nan=False).encode()
    assert raw != canonical, 'Fixture must distinguish source bytes from reserialization'
    monkeypatch.setattr(workflow, '_capture_path', lambda *_args, **_kwargs: package)
    output = io.StringIO()
    assert workflow.main(['alert-preview', source_flag, 'sample' if source_flag == '--source-id' else str(package),
                          '--panel', '1', '--ref-id', 'A', '--operator', 'gt', '--threshold', '0',
                          '--pending-ms', '0', '--step-ms', '30000', '--agent-json'],
                         environ={}, output=output) == 0, output.getvalue()
    preview = json.loads(output.getvalue())['data']
    assert preview['source_integrity'] == 'manifest_verified'
    assert preview['source_sha256'] == hashlib.sha256(raw).hexdigest()


@pytest.mark.parametrize('operation,section,report', [
    ('dependencies', 'nodes', {'operation': 'dependencies', 'nodes': [{'id': 'metric:up', 'kind': 'metric', 'key': 'up'}],
                               'edges': [], 'gaps': []}),
    ('compare', 'values', {'operation': 'compare_captures', 'values': [{'target': [1, 'A', 'range'], 'status': 'compared'}]}),
])
def test_oversized_saved_output_has_executable_section_recovery(tmp_path, monkeypatch, operation, section, report):
    workflow = load_path(ROOT / 'skills/grafana/scripts/grafana_workflow.py', 'grafana_workflow')
    monkeypatch.setattr(workflow, '_capture_path', lambda identifier, **kwargs: tmp_path / identifier)
    # Keep the actual report small while forcing only its first response over budget.
    monkeypatch.setattr(workflow, 'MAX_AGENT_BYTES', 100)
    argv = (['dependencies', '--folder-uid', 'ops'] if operation == 'dependencies' else
            ['compare', '--before-id', 'first', '--after-id', 'second'])
    args = workflow.parse_args([*argv, '--capture-id', 'saved', '--agent-json'])
    response = workflow._prepare_response(args, workflow._Execution(report, {}), tmp_path / 'saved', {})
    assert response['status'] == 'output_truncated'
    recovery = response['recovery']
    assert recovery['arguments'] == ['inspect', '--source-id', 'saved', '--agent-json']
    monkeypatch.setattr(workflow, 'MAX_AGENT_BYTES', 512 * 1024)
    output = io.StringIO()
    assert workflow.main(recovery['arguments'], environ={}, output=output) == 0, output.getvalue()
    assert section in {item['key'] for item in json.loads(output.getvalue())['data']['items']}
    output = io.StringIO()
    assert workflow.main([*recovery['arguments'], '--pointer', '/' + section, '--limit', '1'],
                         environ={}, output=output) == 0, output.getvalue()
    item = json.loads(output.getvalue())['data']['items'][0]
    assert item['evidence_ref'] == '/' + section + '/0'
    output = io.StringIO()
    assert workflow.main([*recovery['arguments'], '--pointer', item['evidence_ref']],
                         environ={}, output=output) == 0, output.getvalue()
    assert json.loads(output.getvalue())['data']['items']


def test_section_inspection_pages_and_preserves_json_pointer_keys(tmp_path):
    workflow = load_path(ROOT / 'skills/grafana/scripts/grafana_workflow.py', 'grafana_workflow')
    args = workflow.parse_args(['inspect', '--source-id', 'saved', '--pointer', '/a~1b~0c',
                               '--offset', '1', '--limit', '1', '--agent-json'])
    inspected = workflow._inspect_capture({'a/b~c': [1, {'nested': 'value'}, 3]}, args)
    assert inspected['total'] == 3 and inspected['next_offset'] == 2
    assert inspected['items'] == [{'key': 1, 'evidence_ref': '/a~1b~0c/1', 'type': 'object', 'size': 1}]
    args.pointer = '/absent'
    with pytest.raises(workflow.reader.SafeError, match='evidence_pointer_unavailable'):
        workflow._inspect_capture({}, args)


def test_section_inspection_can_finish_long_scalar_text():
    workflow = load_path(ROOT / 'skills/grafana/scripts/grafana_workflow.py', 'grafana_workflow')
    args = workflow.parse_args(['inspect', '--source-id', 'saved', '--pointer', '/text',
                               '--offset', '1000001', '--limit', '2', '--agent-json'])
    result = workflow._inspect_capture({'text': 'x' * 1000001 + 'end'}, args)
    assert result['text'] == 'en' and result['next_offset'] == 1000003
    args.offset = result['next_offset']
    result = workflow._inspect_capture({'text': 'x' * 1000001 + 'end'}, args)
    assert result['text'] == 'd' and result['next_offset'] is None


@pytest.mark.parametrize('options', [
    ['--pointer', 'nodes'], ['--pointer', '/a~2b'], ['--pointer', '/nodes', '--panel', '1'],
    ['--pointer', '/nodes', '--ref-id', 'A'], ['--view', 'rows'],
    ['--offset', '33554433'], ['--panel', '1', '--offset', '1000001'],
])
def test_section_inspection_rejects_ambiguous_or_out_of_bounds_selection(options):
    workflow = load_path(ROOT / 'skills/grafana/scripts/grafana_workflow.py', 'grafana_workflow')
    with pytest.raises(workflow.reader.SafeError, match='invalid_arguments'):
        workflow.parse_args(['inspect', '--source-id', 'saved', '--agent-json', *options])


def test_open_report_cannot_dispatch_twice():
    workflow = load_path(ROOT / 'skills/grafana/scripts/grafana_workflow.py', 'grafana_workflow')
    with pytest.raises(workflow.reader.SafeError, match='invalid_arguments'):
        workflow.parse_args(['open-report', '--source-id', 'saved', '--capture-id', 'copy', '--open-vscode'])


def test_basic_auth_redaction_does_not_rewrite_the_query_before_execution(tmp_path):
    workflow = load_path(ROOT / 'skills/grafana/scripts/grafana_workflow.py', 'grafana_workflow')
    http = HTTP(sample_panel(targets=[{'refId': 'A', 'expr': 'up{host="example-host"}'}]))
    output = io.StringIO()
    code = workflow.main(['investigate', '--uid', 'board', '--from', '1000', '--to', '61000',
                          '--output-dir', str(tmp_path / 'capture')],
                         environ={'GRAFANA_URL': 'https://example.test', 'GRAFANA_ORG_ID': '1',
                                  'GRAFANA_USERNAME': 'example-host', 'GRAFANA_PASSWORD': 'protected-password'},
                         transport=http, output=output)
    assert code == 0
    queries = [json.loads(call.data)['queries'][0] for call in http.calls if call.method == 'POST']
    assert queries[0]['expr'] == 'up{host="example-host"}'
    assert 'example-host' not in output.getvalue()
    assert 'example-host' not in (tmp_path / 'capture' / 'report.json').read_text()
    assert 'example-host' not in (tmp_path / 'capture' / 'report.html').read_text()


def test_repeated_workflows_keep_authentication_and_masking_per_invocation():
    workflow = load_path(ROOT / 'skills/grafana/scripts/grafana_workflow.py', 'grafana_workflow')
    expression = 'up{first="first-host",second="second-host"}'
    for username, visible in (('first-host', 'second-host'), ('second-host', 'first-host')):
        http = HTTP(sample_panel(targets=[{'refId': 'A', 'expr': expression}]))
        output = io.StringIO()
        code = workflow.main(['investigate', '--uid', 'board', '--from', '1000', '--to', '61000', '--agent-json'],
                             environ={'GRAFANA_URL': 'https://example.test', 'GRAFANA_ORG_ID': '1',
                                      'GRAFANA_USERNAME': username, 'GRAFANA_PASSWORD': 'fixture-password'},
                             transport=http, output=output)
        assert code == 0, output.getvalue()
        assert username not in output.getvalue() and visible in output.getvalue()
        queries = [json.loads(request.data)['queries'][0] for request in http.calls if request.method == 'POST']
        assert queries[0]['expr'] == expression


def test_dependency_collection_failures_are_visible_outside_raw_json(tmp_path):
    http = HTTP()
    http.board['dashboard']['panels'] = [sample_panel(id=index, targets=[
        {'refId': str(target), 'expr': 'sum(up)'} for target in range(100)]) for index in range(1, 4)]

    def transport(request, **bounds):
        if request.full_url.endswith('/api/v1/provisioning/alert-rules'):
            return 403, b'Forbidden'
        return http(request, **bounds)

    code, _, report = run_workflow(tmp_path, transport, command=['dependencies', '--folder-uid', 'ops'])
    assert code == 0
    assert {'code': 'alert_definitions_http_error', 'source': 'folder:ops'} in report['gaps']
    html = (tmp_path / 'capture' / 'report.html').read_text()
    assert 'alert_definitions_http_error' in html.split('<details>')[0]


def test_dependency_discovery_truncation_is_visible_outside_raw_json(tmp_path):
    http = HTTP(items=[{'uid': 'board', 'folderUid': 'ops'}, {'uid': 'second', 'folderUid': 'ops'}])
    code, _, report = run_workflow(tmp_path, http, command=['dependencies', '--folder-uid', 'ops', '--max-dashboards', '1'])
    assert code == 0 and report['discovery']['truncated']
    html = (tmp_path / 'capture' / 'report.html').read_text()
    assert 'dashboard_discovery_truncated' in html.split('<details>')[0]


def test_rendered_image_is_packaged_with_receipt_and_query_evidence(tmp_path, monkeypatch):
    workflow = load_path(ROOT / 'skills/grafana/scripts/grafana_workflow.py', 'grafana_workflow')
    http = HTTP()

    def chunk(kind, content):
        return struct.pack('>I', len(content)) + kind + content + struct.pack('>I', zlib.crc32(kind + content))

    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>2I5B', 400, 200, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress((b'\0' + b'\x80\x80\x80' * 400) * 200)) + chunk(b'IEND', b''))
    renders = tmp_path / 'renders'
    renders.mkdir()
    monkeypatch.setattr(workflow.reader, '_render_dir', lambda: renders)

    def transport(request, **bounds):
        if '/render/d-solo/' in request.full_url:
            assert 'width=400' in request.full_url and 'height=200' in request.full_url
            return 200, png
        return http(request, **bounds)

    output = io.StringIO()
    destination = tmp_path / 'capture'
    code = workflow.main(['investigate', '--uid', 'board', '--from', '1000', '--to', '61000',
                          '--render', 'all', '--width', '400', '--height', '200', '--output-dir', str(destination)],
                         environ=ENV, transport=transport, output=output)
    assert code == 0, output.getvalue()
    report = json.loads((destination / 'report.json').read_text())
    assert report['panels'][0]['render']['status'] == 'image_uninspected'
    assert (destination / 'panel-1.png').read_bytes() == png
    manifest = json.loads((destination / 'manifest.json').read_text())
    assert manifest['files']['panel-1.png']['sha256'] == report['panels'][0]['render']['receipt']['image_sha256']
    assert report['panels'][0]['targets'][0]['status'] == 'values_returned'


def test_adhoc_filter_prevents_silent_unfiltered_query(tmp_path):
    http = HTTP()
    http.board['dashboard']['templating'] = {'list': [{'type': 'adhoc', 'datasource': {'uid': 'prom'},
                                                    'filters': [{'key': 'namespace', 'operator': '=', 'value': 'production'}]}]}
    code, _, report = run_workflow(tmp_path, http)
    assert code == 0
    assert report['panels'][0]['targets'][0]['error'] == 'unsupported_ad_hoc_filters'
    assert not any(request.method == 'POST' for request in http.calls)
    assert report['panels'][0]['render']['fallback_reason'] == 'query_evidence_incomplete'


def test_truncated_render_preserves_successful_query(tmp_path, monkeypatch):
    workflow = load_path(ROOT / 'skills/grafana/scripts/grafana_workflow.py', 'grafana_workflow')
    renders = tmp_path / 'renders'
    renders.mkdir()
    monkeypatch.setattr(workflow.reader, '_render_dir', lambda: renders)
    http = HTTP()
    png = b'\x89PNG\r\n\x1a\n' + struct.pack('>I', 13) + b'IHDR' + struct.pack('>II', 400, 200)
    def transport(request, **bounds):
        return (200, png) if '/render/d-solo/' in request.full_url else http(request, **bounds)
    output = io.StringIO()
    destination = tmp_path / 'capture'
    code = workflow.main(['investigate', '--uid', 'board', '--from', '1000', '--to', '61000',
                          '--render', 'all', '--width', '400', '--height', '200', '--output-dir', str(destination)],
                         environ=ENV, transport=transport, output=output)
    assert code == 0, output.getvalue()
    report = json.loads((destination / 'report.json').read_text())
    assert report['panels'][0]['targets'][0]['status'] == 'values_returned'
    assert report['panels'][0]['render']['error'] == 'invalid_render_image'


def test_agent_plan_does_not_execute_queries_or_render():
    workflow = load_path(ROOT / 'skills/grafana/scripts/grafana_workflow.py', 'grafana_workflow')
    http, output = HTTP(), io.StringIO()
    code = workflow.main(['plan', '--uid', 'board', '--from', '1000', '--to', '61000', '--agent-json'],
                         environ=ENV, transport=http, output=output)
    assert code == 0, output.getvalue()
    response = json.loads(output.getvalue())
    assert response['data']['queries_planned'] == 1
    assert len(http.calls) == 2 and all(request.method == 'GET' for request in http.calls)


def test_agent_data_first_does_not_render_usable_query():
    workflow = load_path(ROOT / 'skills/grafana/scripts/grafana_workflow.py', 'grafana_workflow')
    http, output = HTTP(), io.StringIO()
    code = workflow.main(['investigate', '--uid', 'board', '--from', '1000', '--to', '61000', '--agent-json'],
                         environ=ENV, transport=http, output=output)
    assert code == 0, output.getvalue()
    response = json.loads(output.getvalue())
    panel = response['data']['summary']['panels'][0]
    assert panel['targets'][0]['status'] == 'values_returned'
    assert panel['targets'][0]['evidence_ref'] == '/panels/0/targets/0'
    assert panel['render']['status'] == 'not_requested'
    assert not any('/render/' in request.full_url for request in http.calls)
    assert response['data']['hygiene']['dashboards'][0]['ok']


def test_agent_capture_offline_analysis_and_inspection(tmp_path, monkeypatch):
    workflow = load_path(ROOT / 'skills/grafana/scripts/grafana_workflow.py', 'grafana_workflow')
    monkeypatch.setattr(workflow, '_capture_path', lambda identifier, **kwargs: tmp_path / identifier)
    output = io.StringIO()
    assert workflow.main(['investigate', '--uid', 'board', '--from', '1000', '--to', '61000',
                          '--capture-id', 'sample', '--agent-json'], environ=ENV, transport=HTTP(), output=output) == 0
    def no_network(*args, **kwargs):
        pytest.fail('offline analysis tried network')
    for arguments in (['verify-package'], ['analyze', '--analysis', 'hygiene'],
                      ['inspect', '--panel', '1', '--ref-id', 'A', '--mode', 'range']):
        output = io.StringIO()
        assert workflow.main([*arguments, '--source-id', 'sample', '--agent-json'],
                             environ={}, transport=no_network, output=output) == 0, output.getvalue()
        data = json.loads(output.getvalue())['data']
        assert data
        if arguments[0] == 'inspect':
            statistics = data['target']['series_statistics']['series'][0]
            assert statistics['statistics']['mean'] == 1.0
            assert statistics['evidence_ref'] == '/panels/0/targets/0/result/results/A/frames/0/data/values/1'
    output = io.StringIO()
    assert workflow.main(['compare', '--before-id', 'sample', '--after-id', 'sample', '--agent-json'],
                         environ={}, transport=no_network, output=output) == 0, output.getvalue()
    assert not json.loads(output.getvalue())['data']['configuration']['changed']
    output = io.StringIO()
    assert workflow.main(['inspect', '--source-id', 'sample', '--panel', '1', '--ref-id', 'A',
                          '--mode', 'range', '--view', 'rows', '--offset', '1', '--limit', '1', '--agent-json'],
                         environ={}, transport=no_network, output=output) == 0, output.getvalue()
    rows = json.loads(output.getvalue())['data']
    assert rows['rows'] == [[31000, 1]] and rows['next_offset'] == 2


def test_render_fallback_yields_image_for_agent_without_changing_query_status(tmp_path, monkeypatch):
    workflow = load_path(ROOT / 'skills/grafana/scripts/grafana_workflow.py', 'grafana_workflow')
    renders = tmp_path / 'renders'
    renders.mkdir()
    monkeypatch.setattr(workflow.reader, '_render_dir', lambda: renders)
    http = HTTP(sample_panel(targets=[{'refId': 'A', 'expr': 'up{host="$host"}', 'format': 'table'}]))
    def chunk(kind, content):
        return struct.pack('>I', len(content)) + kind + content + struct.pack('>I', zlib.crc32(kind + content))
    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>2I5B', 400, 200, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress((b'\0' + b'\x80\x80\x80' * 400) * 200)) + chunk(b'IEND', b''))
    render_calls = []
    def transport(request, **bounds):
        if '/render/d-solo/' in request.full_url:
            assert 'var-host=node.example%2Fpath' in request.full_url
            render_calls.append(request.full_url)
            return 200, png
        return http(request, **bounds)
    output = io.StringIO()
    assert workflow.main(['investigate', '--uid', 'board', '--from', '1000', '--to', '61000',
                          '--width', '400', '--height', '200', '--var', 'host=node.example/path', '--agent-json'],
                         environ=ENV, transport=transport, output=output) == 0, output.getvalue()
    panel = json.loads(output.getvalue())['data']['summary']['panels'][0]
    assert panel['targets'][0]['status'] == 'unsupported' and len(render_calls) == 1
    assert panel['next_action'] == 'inspect_render' and panel['appearance'] == 'not_assessed'
    assert Path(panel['render']['image_path']).read_bytes() == png


@pytest.mark.parametrize('arguments', [
    ['investigate', '--uid', 'board', '--uid', 'other', '--from', '1000', '--to', '61000', '--agent-json'],
    ['analyze', '--source-id', '../escape', '--agent-json'],
    ['analyze', '--source-id', 'sample', '--agent-json', '--agent-json'],
])
def test_agent_grammar_rejects_ambiguous_flags_and_capture_paths(arguments):
    workflow = load_path(ROOT / 'skills/grafana/scripts/grafana_workflow.py', 'grafana_workflow')
    output = io.StringIO()
    assert workflow.main(arguments, environ={}, transport=HTTP(), output=output) == 2
