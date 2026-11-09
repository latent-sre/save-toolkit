"""Workflow integration tests use the real read client and a fake HTTP boundary."""
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
        self.calls, self.probes, self.stored = [], [], 'v0alpha1'
        self.org, self.rules = org, rules or []
        self.items = [{'uid': 'board', 'folderUid': 'ops'}] if items is None else items
        self.query = query or {'results': {'A': {'frames': [{'schema': {'fields': [
            {'name': 'Time', 'type': 'time'}, {'name': 'Value', 'type': 'number', 'labels': {'host': 'example-host'}}]},
            'data': {'values': [[1000, 31000, 61000], [1, 1, 1]]}}]}}}

    def __call__(self, request, **bounds):
        assert 0 < bounds['timeout'] <= 45
        path = request.full_url.split('example.test')[-1]
        if path.startswith('/apis/dashboard.grafana.app/v0alpha1/'):
            # The stored-version check is recorded apart from the calls the tests count.
            self.probes.append(request)
            uid = path.rsplit('/', 1)[-1]
            return 200, json.dumps({'apiVersion': 'dashboard.grafana.app/v0alpha1', 'kind': 'Dashboard',
                                    'metadata': {'name': uid, 'namespace': 'default'}, 'spec': {},
                                    'status': {'conversion': {'storedVersion': self.stored}}}).encode()
        self.calls.append(request)
        if path == '/api/org':
            result = {'id': self.org}
        elif path == '/api/dashboards/uid/board':
            result = self.board
        elif path.startswith('/api/datasources/uid/'):
            uid = path.split('/uid/')[1]
            result = {'uid': uid, 'type': 'loki' if uid == 'logs' else 'prometheus'}
        elif path == '/api/ds/query':
            result = self.query
        elif path.startswith('/api/annotations'):
            result = []
        elif path.startswith('/api/search'):
            result = self.items
        elif path == '/api/v1/provisioning/alert-rules/export?format=json&folderUid=ops':
            if not self.rules:
                return 404, b''
            result = {'apiVersion': 1, 'groups': self.rules}
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
    {'expr': 'up', 'instant': False, 'range': False}, {'expr': 'rate(up[${__rate_interval:raw}])'}])
def test_unsupported_targets_keep_their_gap_and_do_not_issue_queries(tmp_path, target):
    http = HTTP(sample_panel(targets=[target]))
    code, _, report = run_workflow(tmp_path, http)
    assert code == 0 and report['panels'][0]['targets'][0]['status'] == 'unsupported'
    assert not any(call.method == 'POST' for call in http.calls)


def test_builtin_macros_and_multiline_expressions_run_with_backend_expansion_recorded(tmp_path):
    expressions = ['sum(rate(up[$__rate_interval]))', 'increase(up[$__range])', 'sum by (job) (\n\trate(up[5m])\n)']
    http = HTTP(sample_panel(targets=[{'refId': ref, 'expr': expr} for ref, expr in zip('ABC', expressions, strict=True)]))
    code, _, report = run_workflow(tmp_path, http, ['--render', 'none'])
    assert code == 0
    sent = [json.loads(call.data)['queries'][0] for call in http.calls if call.method == 'POST']
    assert [query['expr'] for query in sent] == expressions and all(query['intervalMs'] == 1000 for query in sent)
    targets = report['panels'][0]['targets']
    assert [target['status'] for target in targets] == ['values_returned'] * 3
    assert [target['result']['expression']['backend_expanded'] for target in targets] == [['$__rate_interval'], ['$__range'], []]
    assert targets[0]['result']['expression']['panel_equivalence'] == 'not_established'


def test_explicit_rate_interval_still_substitutes_locally(tmp_path):
    http = HTTP(sample_panel(targets=[{'refId': 'A', 'expr': 'rate(up[$__rate_interval])'}]))
    code, _, report = run_workflow(tmp_path, http, ['--render', 'none', '--rate-interval-ms', '60000'])
    assert code == 0
    assert [json.loads(call.data)['queries'][0]['expr'] for call in http.calls if call.method == 'POST'] == ['rate(up[60000ms])']
    assert report['panels'][0]['targets'][0]['result']['expression']['backend_expanded'] == []


def test_explicit_variables_and_both_query_modes_are_recorded(tmp_path):
    http = HTTP(sample_panel(targets=[{'refId': 'A', 'expr': 'up{host="$host"}', 'range': True, 'instant': True}]))
    code, _, report = run_workflow(tmp_path, http, ['--var', 'host=example-host'])
    assert code == 0
    queries = [json.loads(call.data)['queries'][0] for call in http.calls if call.method == 'POST']
    assert [(q['range'], q['instant']) for q in queries] == [(True, False), (False, True)]
    assert all(q['expr'] == 'up{host="example-host"}' for q in queries)
    assert report['variables'] == {'host': 'example-host'}


def test_regex_format_variable_and_leading_minus_reach_the_backend(tmp_path):
    http = HTTP(sample_panel(targets=[
        {'refId': 'A', 'expr': 'rate(up{host=~"${host:regex}"}[$__rate_interval])'},
        {'refId': 'B', 'expr': '-rate(up{host=~"${host:regex}"}[$__rate_interval])'}]))
    code, _, report = run_workflow(tmp_path, http, ['--var', 'host=node.a'])
    assert code == 0
    queries = [json.loads(call.data)['queries'][0]['expr'] for call in http.calls if call.method == 'POST']
    assert queries == ['rate(up{host=~"node\\\\.a"}[$__rate_interval])', '-rate(up{host=~"node\\\\.a"}[$__rate_interval])']
    statuses = [target['status'] for panel in report['panels'] for target in panel['targets']]
    assert 'unsupported' not in statuses


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


def test_missing_output_parent_is_a_specific_error_before_connecting(tmp_path):
    workflow = load_path(ROOT / 'skills/grafana/scripts/grafana_workflow.py', 'grafana_workflow')
    http, output = HTTP(), io.StringIO()
    destination = tmp_path / 'absent' / 'capture'
    code = workflow.main(['investigate', '--uid', 'board', '--from', '1000', '--to', '61000', '--render', 'none',
                          '--agent-json', '--output-dir', str(destination)], environ=ENV, transport=http, output=output)
    assert code == 2 and json.loads(output.getvalue()) == {'ok': False, 'error': 'output_parent_missing'}
    assert not http.calls and not (tmp_path / 'absent').exists()


def test_failed_reads_keep_their_http_status(tmp_path):
    http = HTTP()

    def transport(request, **bounds):
        return (503, b'unavailable') if request.full_url.endswith('/api/ds/query') else http(request, **bounds)

    code, _, report = run_workflow(tmp_path, transport, ['--render', 'none'])
    assert code == 0
    assert report['panels'][0]['targets'][0] | {'status': 'query_failed', 'error': 'http_error', 'http_status': 503} == \
        report['panels'][0]['targets'][0]
    workflow = load_path(ROOT / 'skills/grafana/scripts/grafana_workflow.py', 'grafana_workflow')
    output = io.StringIO()
    assert workflow.main(['plan', '--uid', 'board', '--from', '1000', '--to', '61000', '--agent-json'], environ=ENV,
                         transport=lambda request, **bounds: (401, b''), output=output) == 2
    assert json.loads(output.getvalue()) == {'ok': False, 'error': 'http_error', 'http_status': 401}


def test_capture_timestamps_and_doctor_capabilities_match_the_commands(tmp_path):
    workflow = load_path(ROOT / 'skills/grafana/scripts/grafana_workflow.py', 'grafana_workflow')
    code, _, report = run_workflow(tmp_path, HTTP(), ['--render', 'none'])
    assert code == 0 and report['provenance']['retrieved_at_utc'].endswith('Z')
    assert report['panels'][0]['targets'][0]['result']['retrieved_at_utc'].endswith('Z')
    capabilities = workflow.doctor(ENV, lambda *args, **kwargs: pytest.fail('network'))['capabilities']
    commands = set(workflow._argument_parser()._subparsers._group_actions[0].choices) - {'doctor'}
    assert set(capabilities) == commands


V2_ELEMENTS = {
    'panel-1': {'kind': 'Panel', 'spec': {'id': 1, 'title': 'Rate', 'links': [], 'vizConfig': {
        'kind': 'VizConfig', 'group': 'timeseries', 'version': '13.3.0', 'spec': {'options': {}, 'fieldConfig': {
            'defaults': {'unit': 's'}, 'overrides': []}}}, 'data': {'kind': 'QueryGroup', 'spec': {
        'transformations': [], 'queryOptions': {}, 'queries': [{'kind': 'PanelQuery', 'spec': {
            'refId': 'A', 'hidden': False, 'query': {'kind': 'DataQuery', 'group': 'prometheus', 'version': 'v0',
                                                     'datasource': {'name': 'prom'},
                                                     'spec': {'expr': 'rate(up[5m])'}}}}]}}}},
}
V2_TABS = {'kind': 'TabsLayout', 'spec': {'tabs': [{'kind': 'TabsLayoutTab', 'spec': {'title': 'One', 'layout': {
    'kind': 'RowsLayout', 'spec': {'rows': [{'kind': 'RowsLayoutRow', 'spec': {'title': 'Row', 'layout': {
        'kind': 'GridLayout', 'spec': {'items': [{'kind': 'GridLayoutItem', 'spec': {
            'x': 0, 'y': 0, 'width': 24, 'height': 8, 'element': {'kind': 'ElementReference', 'name': 'panel-1'}}}]}}}}]}}}}]}}


class V2HTTP(HTTP):
    """A V2-stored dashboard: the legacy read is a down-conversion and the native object is v2."""

    def __init__(self):
        super().__init__(items=[{'uid': 'board', 'folderUid': 'ops'}])
        self.stored = 'v2'
        self.board['dashboard']['panels'] = [{'id': 99, 'type': 'row', 'panels': []}]

    def __call__(self, request, **bounds):
        if '/apis/dashboard.grafana.app/v2/' in request.full_url:
            self.calls.append(request)
            return 200, json.dumps({'apiVersion': 'dashboard.grafana.app/v2', 'kind': 'Dashboard',
                                    'metadata': {'name': 'board', 'namespace': 'default', 'generation': 4},
                                    'spec': {'title': 'Synthetic', 'elements': V2_ELEMENTS, 'layout': V2_TABS,
                                             'variables': []}}).encode()
        return super().__call__(request, **bounds)


@pytest.mark.parametrize('command', ['investigate', 'plan'])
def test_v2_dashboard_investigation_and_plan_use_the_native_model(tmp_path, command):
    http = V2HTTP()
    code, _, report = run_workflow(tmp_path, http, ['--render', 'none'],
                                   command=[command, '--uid', 'board', '--from', '1000', '--to', '61000'])
    assert code == 0
    plan = report if command == 'plan' else report['query_plan']
    assert [(panel['id'], panel['title']) for panel in plan['panels']] == [(1, 'Rate')]
    assert plan['panels'][0]['targets'][0]['status'] == 'planned'
    if command == 'investigate':
        assert report['dashboard']['version'] == 4 and report['dashboard_capture']['model']['format'] == 'v2'
        assert report['panels'][0]['targets'][0]['status'] == 'values_returned'
        assert 'dashboard_changed_during_capture' not in report['gaps']
        assert report['dashboard_version_at_end'] == 4


def test_v2_dashboard_dependencies_and_hygiene_read_the_mapped_view(tmp_path):
    code, _, report = run_workflow(tmp_path, V2HTTP(), command=['dependencies', '--folder-uid', 'ops'])
    assert code == 0
    assert {node['kind'] for node in report['nodes']} >= {'dashboard', 'panel', 'query', 'datasource', 'metric'}
    assert not any(gap['code'] == 'unsupported_dashboard_model' for gap in report['gaps'])
    workflow = load_path(ROOT / 'skills/grafana/scripts/grafana_workflow.py', 'grafana_workflow')
    output = io.StringIO()
    assert workflow.main(['analyze', '--package-dir', str(tmp_path / 'capture'), '--analysis', 'hygiene', '--agent-json'],
                         environ={}, output=output) == 0, output.getvalue()
    hygiene = json.loads(output.getvalue())['data']['hygiene']['dashboards'][0]
    assert hygiene['ok'] and hygiene['panel_count'] == 1


def test_folder_map_reads_folder_scoped_export_and_never_runs_data_queries(tmp_path):
    http = HTTP(rules=[{'orgId': 1, 'name': 'group', 'folder': 'Ops', 'rules': [
        {'uid': 'rule', 'title': 'Alert', 'condition': 'A', 'dashboardUid': 'board', 'panelId': 1,
         'data': [{'refId': 'A', 'datasourceUid': 'prom', 'model': {'expr': 'up', 'datasource': {'type': 'prometheus'}}}]}]}])
    code, _, report = run_workflow(tmp_path, http, command=['dependencies', '--folder-uid', 'ops'])
    assert code == 0
    assert [call.full_url.split('example.test')[1] for call in http.calls if 'alert-rules' in call.full_url] == [
        '/api/v1/provisioning/alert-rules/export?format=json&folderUid=ops']
    rule = report['alert_captures'][0]['rule']
    assert rule['folderUID'] == 'ops' and rule['annotations'] == {'__dashboardUid__': 'board', '__panelId__': '1'}
    assert {edge['relation'] for edge in report['edges']} >= {'annotates_dashboard', 'annotates_panel', 'evaluates_condition'}
    assert report['discovery']['coverage'] == 'permission_scoped'
    assert all(call.method == 'GET' for call in http.calls)


@pytest.mark.parametrize('rules,gap', [
    ([], {'code': 'alert_definitions_none_visible', 'source': 'folder:ops', 'http_status': 404}),
    ([{'orgId': 2, 'name': 'group', 'rules': []}],
     {'code': 'alert_definitions_organization_mismatch', 'source': 'folder:ops', 'error': 'organization_mismatch'}),
])
def test_folder_map_reports_empty_or_foreign_rule_exports_as_gaps(tmp_path, rules, gap):
    code, _, report = run_workflow(tmp_path, HTTP(rules=rules), command=['dependencies', '--folder-uid', 'ops'])
    assert code == 0 and gap in report['gaps'] and report['alert_captures'] == []


def test_folder_map_refuses_unscoped_search_response(tmp_path):
    http = HTTP(items=[{'uid': 'board', 'folderUid': 'other'}])
    code, response, report = run_workflow(tmp_path, http, command=['dependencies', '--folder-uid', 'ops'])
    assert code == 2 and response['error'] == 'folder_mismatch' and report is None
    assert len(http.calls) == 2


def test_oversized_saved_output_has_executable_section_recovery(tmp_path, monkeypatch):
    section = 'nodes'
    report = {'operation': 'dependencies', 'nodes': [{'id': 'metric:up', 'kind': 'metric', 'key': 'up'}], 'edges': [], 'gaps': []}
    workflow = load_path(ROOT / 'skills/grafana/scripts/grafana_workflow.py', 'grafana_workflow')
    monkeypatch.setattr(workflow, '_capture_path', lambda identifier, **kwargs: tmp_path / identifier)
    # Keep the actual report small while forcing only its first response over budget.
    monkeypatch.setattr(workflow, 'MAX_AGENT_BYTES', 100)
    args = workflow.parse_args(['dependencies', '--folder-uid', 'ops', '--capture-id', 'saved', '--agent-json'])
    response = workflow._prepare_response(args, workflow._Execution(report, {}), tmp_path / 'saved')
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
        if '/api/v1/provisioning/alert-rules/export' in request.full_url:
            return 403, b'Forbidden'
        return http(request, **bounds)

    code, _, report = run_workflow(tmp_path, transport, command=['dependencies', '--folder-uid', 'ops'])
    assert code == 0
    assert {'code': 'alert_definitions_http_error', 'source': 'folder:ops', 'error': 'http_error',
            'http_status': 403} in report['gaps']
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


@pytest.mark.parametrize('destination_kind', ['path', 'capture_id', 'safe_capture_id'])
def test_truncated_authenticated_output_omits_masked_recovery(tmp_path, monkeypatch, destination_kind):
    workflow = load_path(ROOT / 'skills/grafana/scripts/grafana_workflow.py', 'grafana_workflow')
    username = 'synthetic-user'
    http = HTTP(sample_panel(title='x' * 600000))
    monkeypatch.setattr(workflow, '_capture_path', lambda identifier, **kwargs: tmp_path / identifier)
    destination = (['--output-dir', str(tmp_path / username)] if destination_kind == 'path' else
                   ['--capture-id', 'saved' if destination_kind == 'safe_capture_id' else username])
    output = io.StringIO()
    code = workflow.main(['plan', '--uid', 'board', '--from', '1000', '--to', '2000',
                          *destination, '--agent-json'],
                         environ={'GRAFANA_URL': 'https://example.test', 'GRAFANA_ORG_ID': '1',
                                  'GRAFANA_USERNAME': username, 'GRAFANA_PASSWORD': 'synthetic-password'},
                         transport=http, output=output)
    assert code == 0, output.getvalue()
    response = json.loads(output.getvalue())
    assert response['status'] == 'output_truncated'
    assert username not in output.getvalue()
    if destination_kind == 'safe_capture_id':
        recovery = response['recovery']['arguments']
        assert recovery == ['inspect', '--source-id', 'saved', '--agent-json']
        assert workflow.main(recovery, environ={}, output=io.StringIO()) == 0
    else:
        assert 'arguments' not in response['recovery']
        assert response['recovery']['error'] == 'recovery_arguments_masked'
    assert len(http.calls) == 2


def test_symlinked_output_parent_is_rejected_before_collection(tmp_path):
    workflow = load_path(ROOT / 'skills/grafana/scripts/grafana_workflow.py', 'grafana_workflow')
    (tmp_path / 'actual').mkdir()
    try:
        (tmp_path / 'linked').symlink_to(tmp_path / 'actual', target_is_directory=True)
    except OSError:
        pytest.skip('directory symlinks unavailable')
    destination = tmp_path / 'linked' / 'capture'
    http = HTTP()
    output = io.StringIO()
    code = workflow.main(['plan', '--uid', 'board', '--from', '1000', '--to', '2000',
                          '--output-dir', str(destination), '--agent-json'],
                         environ=ENV, transport=http, output=output)
    assert code == 2
    assert json.loads(output.getvalue()) == {'ok': False, 'error': 'output_directory_unavailable'}
    assert not http.calls
    assert not destination.exists()
    assert not list((tmp_path / 'actual').iterdir())
