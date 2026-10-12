#!/usr/bin/env python3
"""Pure, bounded Classic dashboard query planning for agent consumers.

Callbacks provide the installed reader's model validation and query command
contract. No network, filesystem, query evaluation, or telemetry health inference.
"""
import json
import re

MACRO = re.compile(r'\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]*)')
MAX_TARGETS = 500


def _quote_context(expression, end):
    quote, opening, escaped = None, None, False
    for index, char in enumerate(expression[:end]):
        if escaped:
            escaped = False
        elif quote and char == '\\' and quote != '`':
            escaped = True
        elif quote and char == quote:
            quote, opening = None, None
        elif not quote and char in ('"', "'", '`'):
            quote, opening = char, index
    return quote, opening, escaped


def substitute(expression, variables, *, context='query'):
    """Interpolate explicit scalar literals, never multi/all/raw formatting.

    Quoted matcher regexes escape regex metacharacters before query-string
    escaping. Unquoted substitutions retain a conservative token contract.
    Built-in macros are left to the reader's versioned query validation.
    """
    def replace(match):
        name = match.group(1) or match.group(2)
        if name.startswith('__'):
            return match.group(0)
        value = variables.get(name)
        if (not isinstance(value, str) or not 1 <= len(value) <= 100 or
                any(ord(char) < 32 or ord(char) == 127 for char in value)):
            raise ValueError('unsupported_variable_interpolation')
        quote, opening, escaped = _quote_context(expression, match.start())
        if escaped:
            raise ValueError('unsupported_variable_interpolation')
        if not quote:
            pattern = r'[A-Za-z0-9_.:-]+' if context == 'datasource' else r'[A-Za-z0-9_:]+'
            if not re.fullmatch(pattern, value):
                raise ValueError('unsupported_variable_interpolation')
            return value
        prefix = expression[:opening].rstrip()
        if not prefix.endswith(('=', '!=', '=~', '!~', '|~')):
            raise ValueError('unsupported_variable_interpolation')
        if prefix.endswith(('=~', '!~', '|~')):
            value = re.sub(r'([\\.^$*+?{}\[\]()|])', r'\\\1', value)
        if quote == '`':
            if '`' in value:
                raise ValueError('unsupported_variable_interpolation')
            return value
        if quote == '"':
            return json.dumps(value, ensure_ascii=False)[1:-1]
        return value.replace('\\', '\\\\').replace("'", "\\'")
    result = MACRO.sub(replace, expression)
    # Legacy bracket formatting and malformed variable syntax are not literals.
    if '[[' in result:
        raise ValueError('unsupported_variable_interpolation')
    return result


def _filtered_datasources(dashboard):
    templating = dashboard.get('templating', {})
    if not isinstance(templating, dict) or not isinstance(templating.get('list', []), list):
        return {None}
    filtered = set()
    for variable in templating.get('list', []):
        if not isinstance(variable, dict):
            filtered.add(None)
        elif variable.get('type') in ('adhoc', 'filters') and variable.get('filters'):
            source = variable.get('datasource')
            uid = source.get('uid') if isinstance(source, dict) else None
            filtered.add(uid if isinstance(uid, str) and '$' not in uid else None)
    return filtered


def build_plan(dashboard, args, variables, *, panel_reader, target_builder, errors=(ValueError,)):
    """Plan commands once; execution consumes only targets marked ``planned``.

    ``target_builder(panel,target,args,variables)`` returns already validated
    reader argv lists. ``errors`` names its static safe exception types.
    Library/repeat/time contexts remain explicit gaps, never guessed semantics.
    """
    plan = {'schema_version': 1, 'operation': 'query_plan', 'coverage': 'raw_queries_only',
            'health': 'not_assessed', 'panels': [], 'gaps': [], 'missing_inputs': [],
            'from_ms': args.from_ms, 'to_ms': args.to_ms,
            'limits': {'max_panels': args.max_panels, 'max_queries': args.max_queries,
                       'max_targets_inspected': MAX_TARGETS}}
    try:
        all_panels = panel_reader(dashboard)
    except errors as error:
        plan.update(status='unsupported', panel_count=0, queries_planned=0,
                    request_estimate={'queries': 0, 'total_upper_bound': 0})
        plan['gaps'].append(str(error))
        return plan
    plan['panel_count'] = len(all_panels)
    if len(all_panels) > args.max_panels:
        plan['gaps'].append('panel_limit_reached')
    filtered = _filtered_datasources(dashboard)
    queries = inspected = renders = 0
    missing = set()
    for panel in all_panels[:args.max_panels]:
        blocked = panel.get('_parent_context', []) + [key for key in (
            'libraryPanel', 'repeat', 'scopedVars', 'timeFrom', 'timeShift') if panel.get(key)]
        item = {'id': panel['id'], 'title': panel.get('title'), 'type': panel['type'],
                'blocked': bool(blocked), 'targets': [],
                'gaps': ['unsupported_panel_' + key for key in blocked]}
        plan['panels'].append(item)
        render_policy = getattr(args, 'render', 'fallback')
        item['render_policy'] = render_policy
        if render_policy in ('all', 'fallback'):
            # Fallback can be needed after any query outcome, including blocked
            # contexts. Preflight budgets the maximum, not a success prediction.
            renders += 1
        if panel.get('transformations'):
            item['gaps'].append('transformations_not_applied')
        if panel.get('interval') or panel.get('maxDataPoints'):
            item['gaps'].append('panel_sampling_options_not_reproduced')
        targets = panel.get('targets', [])
        if not isinstance(targets, list):
            item['gaps'].append('unsupported_targets')
            targets = []
        if not targets:
            item['gaps'].append('no_query_targets')
        if blocked:
            item['next_action'] = 'collect_panel_render_with_scope_limitations' if render_policy != 'none' else 'resolve_panel_context'
            continue
        for target in targets:
            if inspected >= MAX_TARGETS:
                if 'target_inspection_limit_reached' not in plan['gaps']:
                    plan['gaps'].append('target_inspection_limit_reached')
                break
            inspected += 1
            entry = {'ref_id': target.get('refId') if isinstance(target, dict) else None}
            if isinstance(target, dict) and target.get('hide') is True:
                item['targets'].append({**entry, 'status': 'hidden'})
                continue
            try:
                if not isinstance(target, dict):
                    raise ValueError('unsupported_target')
                source = target.get('datasource') or panel.get('datasource')
                uid = source.get('uid') if isinstance(source, dict) else None
                for expression in (target.get('expr'), uid):
                    if isinstance(expression, str):
                        missing.update(name for match in MACRO.finditer(expression)
                                       if (name := match.group(1) or match.group(2)) not in variables
                                       and not name.startswith('__'))
                if isinstance(uid, str):
                    uid = substitute(uid, variables, context='datasource')
                if None in filtered or uid in filtered:
                    raise ValueError('unsupported_ad_hoc_filters')
                commands = target_builder(panel, target, args, variables)
                for command in commands:
                    planned = {**entry, 'mode': command[-1], 'original_expression': target.get('expr')}
                    if queries >= args.max_queries:
                        item['targets'].append({**planned, 'status': 'not_run', 'error': 'query_limit_reached'})
                    else:
                        queries += 1
                        item['targets'].append({**planned, 'status': 'planned', 'command': command})
            except (ValueError, *errors) as error:
                item['targets'].append({**entry, 'status': 'unsupported', 'error': str(error),
                                        'next_action': 'collect_panel_render_with_scope_limitations'
                                        if render_policy != 'none' else 'resolve_query_context'})
    plan.update(queries_planned=queries, targets_inspected=inspected, missing_inputs=sorted(missing),
                request_estimate={'queries': queries, 'renders': renders,
                                  'total_upper_bound': 5 + queries * 2 + renders * 2})
    plan['status'] = 'partial' if plan['gaps'] or any(
        panel['gaps'] or any(target['status'] in ('unsupported', 'not_run') for target in panel['targets'])
        for panel in plan['panels']) else 'planned'
    return plan
