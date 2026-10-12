"""Agent query plans must preserve query scope and expose incomplete coverage."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from testkit import load_path

plan = load_path(Path(__file__).resolve().parents[1] / 'skills/grafana/scripts/grafana_plan.py', 'grafana_plan_test')


def board():
    return {'panels': [{'id': 1, 'type': 'timeseries', 'datasource': {'type': 'prometheus', 'uid': 'metrics'},
                        'targets': [{'refId': 'A', 'expr': 'up'}]}]}


def build(dashboard, variables=None, **kwargs):
    args = SimpleNamespace(from_ms=1000, to_ms=61000, max_panels=50, max_queries=100, render='none')
    args.__dict__.update(kwargs)
    return plan.build_plan(dashboard, args, variables or {}, panel_reader=lambda d: d['panels'],
                           target_builder=lambda p, t, a, v: [
                               ['query', '--expr', plan.substitute(t['expr'], v), '--mode', 'range']])


def test_saved_ad_hoc_filters_fail_closed_only_for_affected_datasource():
    dashboard = board()
    dashboard['templating'] = {'list': [{'type': 'adhoc', 'datasource': {'uid': 'metrics'},
                                       'filters': [{'key': 'namespace', 'operator': '=', 'value': 'production'}]}]}
    result = build(dashboard)
    assert result['panels'][0]['targets'][0]['error'] == 'unsupported_ad_hoc_filters'
    assert result['queries_planned'] == 0
    dashboard['templating']['list'][0]['datasource']['uid'] = 'other'
    assert build(dashboard)['queries_planned'] == 1


def test_unknown_filtered_datasource_and_malformed_templating_fail_closed():
    for templating in ({'list': [{'type': 'adhoc', 'filters': [{'key': 'job'}]}]}, {'list': 'bad'}):
        assert build({**board(), 'templating': templating})['queries_planned'] == 0


def test_empty_ad_hoc_filters_do_not_block():
    assert build({**board(), 'templating': {'list': [{'type': 'adhoc', 'filters': []}]}})['queries_planned'] == 1


def test_quoted_scalar_regex_and_literal_values_preserve_scope():
    assert plan.substitute('up{host="$host"}', {'host': 'node.example/path'}) == 'up{host="node.example/path"}'
    assert plan.substitute('up{host=~"$host"}', {'host': 'node.example/path'}) == 'up{host=~"node\\\\.example/path"}'
    assert plan.substitute('up{host="$host"}', {'host': 'a"} or up'}) == 'up{host="a\\"} or up"}'
    assert plan.substitute('{host="$host"} |~ "$pattern"', {'host': 'a', 'pattern': '(a|b)'}) == '{host="a"} |~ "\\\\(a\\\\|b\\\\)"'
    assert plan.substitute('$source', {'source': 'prod-metrics'}, context='datasource') == 'prod-metrics'


@pytest.mark.parametrize('expression,variables', [
    ('$host', {'host': 'node.example/path'}), ('up{host="${host:regex}"}', {'host': 'a'}),
    ('up{host="$missing"}', {}), ('label_replace(up,"x","a","b","$host")', {'host': '.*'}),
    ('[[host]]', {'host': 'a'}), ('up{host="$host"}', {'host': ['a', 'b']}),
])
def test_unsupported_variable_contexts_are_explicit(expression, variables):
    with pytest.raises(ValueError, match='unsupported_variable_interpolation'):
        plan.substitute(expression, variables)


def test_plan_exposes_missing_inputs_and_query_budget_without_commands_for_skipped_targets():
    dashboard = board()
    dashboard['panels'][0]['targets'] = [{'refId': 'A', 'expr': 'up{host="$host"}'},
                                        {'refId': 'B', 'expr': 'up'}, {'refId': 'C', 'expr': 'up'}]
    result = build(dashboard, max_queries=1)
    targets = result['panels'][0]['targets']
    assert result['missing_inputs'] == ['host']
    assert [target['status'] for target in targets] == ['unsupported', 'planned', 'not_run']
    assert 'command' not in targets[2]
    assert result['request_estimate']['queries'] == 1


def test_panel_context_and_inspection_budgets_are_explicit():
    dashboard = board()
    dashboard['panels'][0]['repeat'] = 'host'
    result = build(dashboard)
    assert result['panels'][0]['blocked']
    assert result['queries_planned'] == 0
    dashboard['panels'][0].pop('repeat')
    dashboard['panels'][0]['targets'] *= 501
    result = build(dashboard)
    assert result['targets_inspected'] == 500
    assert 'target_inspection_limit_reached' in result['gaps']


def test_fallback_request_estimate_includes_blocked_panels():
    dashboard = board()
    dashboard['panels'][0]['libraryPanel'] = {'uid': 'shared'}
    result = build(dashboard, render='fallback')
    assert result['request_estimate']['renders'] == 1
    assert result['request_estimate']['total_upper_bound'] == 7
    assert result['panels'][0]['next_action'] == 'collect_panel_render_with_scope_limitations'
