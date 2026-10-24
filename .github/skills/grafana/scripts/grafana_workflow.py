#!/usr/bin/env python3
"""Bounded Grafana investigations and local evidence reports. Python 3.12+.

Agent-oriented structured investigations reuse grafana_read authentication and fixed endpoints.
Optional evidence packages and local viewing; no arbitrary URLs or Grafana writes.
"""
import base64
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from runpy import run_path

_module = run_path(str(Path(__file__).with_name('grafana_modules.py')))['load_module']
reader = _module('grafana_read')
MAX_REQUESTS, MAX_BYTES, MAX_SECONDS = 300, 64 * 1024 * 1024, 600
MAX_AGENT_BYTES = 512 * 1024
CAPTURE_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z')
LIBRARIES = {'polars': 'polars', 'promql-parser': 'promql_parser', 'deepdiff': 'deepdiff', 'pillow': 'PIL'}


def _check_dependencies(args):
    """Fail before collection when the requested path cannot use its managed dependencies."""
    required = set()
    if args.command == 'investigate':
        if args.agent_json:
            required.update(('polars', 'promql-parser'))
        if args.render != 'none':
            required.add('pillow')
    elif args.command == 'dependencies' or args.command == 'impact':
        required.add('promql-parser')
    elif args.command == 'compare':
        required.add('deepdiff')
    elif args.command == 'inspect' and args.panel is not None and (args.ref_id is None or args.view == 'summary'):
        required.add('polars')
    elif args.command == 'analyze':
        if args.analysis in ('summary', 'all'):
            required.add('polars')
        if args.analysis in ('dependencies', 'all'):
            required.add('promql-parser')
    for name in sorted(required):
        try:
            importlib.import_module(LIBRARIES[name])
        except (ImportError, OSError):
            raise reader.SafeError('dependency_unavailable_' + name.replace('-', '_')) from None


def _capture_path(identifier, *, create=False):
    """Fixed per-user evidence store; identifiers never supply filesystem paths."""
    if not CAPTURE_ID.fullmatch(identifier):
        raise reader.SafeError('invalid_capture_id')
    root = Path.home() / '.cache' / 'save-toolkit' / 'grafana-captures'
    if not root.is_absolute() or any(p.is_symlink() or (p.exists() and getattr(p.stat(), 'st_file_attributes', 0) & 0x400)
                                    for p in (root, *root.parents)):
        raise reader.SafeError('capture_directory_unavailable')
    if create:
        root.mkdir(mode=0o700, parents=True, exist_ok=True)
    path = root / identifier
    if path.is_symlink() or (path.exists() and getattr(path.stat(), 'st_file_attributes', 0) & 0x400):
        raise reader.SafeError('capture_directory_unavailable')
    return path


class Client:
    """Single verified identity with a total request, response-byte and elapsed-time budget."""

    def __init__(self, environ, transport):
        self.requests = self.bytes = 0
        self.started = time.monotonic()
        self.transport = transport
        self.connection, self.secrets = reader._connect(reader._settings(environ, reader._settings_file()), self._transport)
        org = self.connection.read('/api/org')
        if type(org.get('id')) is not int or org['id'] != self.connection.organization:
            raise reader.SafeError('organization_mismatch')

    def _transport(self, request, **bounds):
        remaining = MAX_SECONDS - (time.monotonic() - self.started)
        if self.requests >= MAX_REQUESTS or self.bytes >= MAX_BYTES or remaining <= 0:
            raise reader.SafeError('workflow_budget_exhausted')
        bounds['timeout'] = min(bounds.get('timeout', reader.TIMEOUT), remaining)
        bounds['limit'] = min(bounds.get('limit', reader.MAX_RESPONSE), MAX_BYTES - self.bytes)
        self.requests += 1
        status, raw = self.transport(request, **bounds)
        self.bytes += len(raw)
        if self.bytes > MAX_BYTES:
            raise reader.SafeError('workflow_budget_exhausted')
        return status, raw

    def mask(self, value):
        return reader._mask(value, self.secrets)

    def call(self, argv):
        # Keep values intact inside the workflow: a Basic username can also be a valid metric
        # label, datasource UID or panel ID. Mask once at the export boundary, never before use.
        args = reader.parse_args(argv)
        result = reader._OPERATIONS[args.command](self.connection, args)
        result.update({'grafana_url': self.connection.base, 'organization_id': self.connection.organization,
                       'retrieved_at_utc': datetime.now(UTC).isoformat()})
        return result


def panels(dashboard):
    # Reuse validation of the entire Classic tree, including duplicate IDs and model detection.
    reader._panel(dashboard, 1)
    pending, found = [(panel, []) for panel in reversed(dashboard['panels'])], []
    while pending:
        panel, inherited = pending.pop()
        if panel['type'] == 'row':
            context = inherited + [key for key in ('repeat', 'scopedVars') if panel.get(key)]
            pending.extend((child, context) for child in reversed(panel.get('panels', [])))
        else:
            found.append({**panel, '_parent_context': inherited})
    return found


def _variables(values):
    result = {}
    if len(values) > reader.MAX_VARIABLES:
        raise reader.SafeError('invalid_arguments')
    for item in values:
        if not isinstance(item, str) or '=' not in item:
            raise reader.SafeError('invalid_arguments')
        name, value = item.split('=', 1)
        if (name in result or name.startswith('__') or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,63}', name)
                or not 1 <= len(value) <= 100 or not all(character.isprintable() for character in value)):
            raise reader.SafeError('invalid_arguments')
        result[name] = value
    return result


def _substitute(expression, variables, *, context='query'):
    try:
        return _module('grafana_plan').substitute(expression, variables, context=context)
    except ValueError as error:
        raise reader.SafeError(str(error)) from None


def _target_argv(panel, target, args, variables):
    if not isinstance(target, dict):
        raise reader.SafeError('unsupported_target')
    datasource = target.get('datasource') or panel.get('datasource')
    if not isinstance(datasource, dict) or datasource.get('type') not in ('prometheus', 'loki'):
        raise reader.SafeError('unsupported_datasource')
    uid = datasource.get('uid')
    if not isinstance(uid, str):
        raise reader.SafeError('unsupported_datasource')
    uid = _substitute(uid, variables, context='datasource')
    expr = target.get('expr')
    if not isinstance(expr, str) or not expr.strip():
        raise reader.SafeError('unsupported_expression')
    if target.get('format') not in (None, 'time_series'):
        raise reader.SafeError('unsupported_query_format')
    if target.get('interval') or target.get('intervalFactor') not in (None, 1):
        raise reader.SafeError('unsupported_target_interval')
    kind = datasource['type']
    if kind == 'prometheus':
        if any(key in target and type(target[key]) is not bool for key in ('instant', 'range')):
            raise reader.SafeError('unsupported_query_mode')
        instant, ranged = target.get('instant', False), target.get('range', not target.get('instant', False))
        modes = (['range'] if ranged else []) + (['instant'] if instant else [])
    else:
        mode = target.get('queryType', 'range')
        modes = [mode] if mode in ('range', 'instant') else []
    if not modes:
        raise reader.SafeError('unsupported_query_mode')
    common = ['query', '--datasource', uid, '--kind', kind, '--from', str(args.from_ms),
              '--to', str(args.to_ms), '--expr', _substitute(expr, variables)]
    for flag, value in (('--interval-ms', args.interval_ms), ('--rate-interval-ms', args.rate_interval_ms if kind == 'prometheus' else None)):
        if value is not None:
            common.extend([flag, str(value)])
    commands = [[*common, '--mode', mode] for mode in modes]
    for command in commands:
        reader.parse_args(command)
    return commands


def query_plan(capture, args):
    plan = _module('grafana_plan').build_plan(capture['dashboard'], args, _variables(args.variables),
                                             panel_reader=panels, target_builder=_target_argv,
                                             errors=(reader.SafeError, ValueError))
    plan['provenance'] = {key: capture[key] for key in ('grafana_url', 'organization_id', 'retrieved_at_utc')}
    return plan


def _status(result):
    summary = result['summary']
    if summary['status'] != 'complete':
        return 'unsupported_result'
    if summary['row_count'] == 0:
        return 'no_data'
    if summary['numeric_series_count'] and all(s['state'] == 'all_null' for s in summary['series']):
        return 'all_null' if not summary['series_truncated'] else 'values_returned'
    return 'values_returned'


def investigate(client, args):
    variables = _variables(args.variables)
    capture = client.call(['dashboard', '--uid', args.uid])
    dashboard, meta = capture['dashboard'], capture['meta']
    report = {'schema_version': 1, 'operation': 'investigate', 'dashboard': dashboard,
              'dashboard_capture': capture, 'from_ms': args.from_ms, 'to_ms': args.to_ms,
              'variables': variables, 'panels': [], 'context': {}, 'gaps': ['reads_are_not_an_atomic_snapshot'],
              'coverage': 'raw_queries_only', 'health': 'not_assessed',
              'limits': {'max_panels': args.max_panels, 'max_queries': args.max_queries,
                         'max_requests': MAX_REQUESTS, 'max_response_bytes_total': MAX_BYTES,
                         'max_seconds': MAX_SECONDS}, 'provenance': {
                             key: capture[key] for key in ('grafana_url', 'organization_id', 'retrieved_at_utc')}}
    images, query_count = {}, 0
    plan = query_plan(capture, args)
    report['query_plan'] = plan
    report['gaps'].extend(plan.get('gaps', []))
    report['panel_count'] = plan.get('panel_count', len(plan['panels']))
    for panel in plan['panels']:
        item = {'id': panel['id'], 'title': panel.get('title'), 'type': panel['type'], 'targets': [],
                'status': 'unsupported', 'coverage': 'raw_queries_only', 'gaps': [],
                'render': {'status': 'not_requested'}}
        report['panels'].append(item)
        item['gaps'].extend(panel.get('gaps', []))
        for target in panel['targets']:
            entry = {key: value for key, value in target.items() if key != 'command'}
            command = target.get('command')
            if not command:
                item['targets'].append(entry)
                continue
            if query_count >= args.max_queries:
                item['targets'].append({**entry, 'status': 'not_run', 'error': 'query_limit_reached'})
                continue
            query_count += 1
            try:
                result = client.call(command)
                item['targets'].append({**entry, 'status': _status(result), 'result': result})
            except reader.SafeError as error:
                status = 'unsupported' if str(error) in ('invalid_arguments', 'unresolved_or_invalid_expression') else 'query_failed'
                item['targets'].append({**entry, 'status': status, 'error': str(error)})
        statuses = {target['status'] for target in item['targets'] if target['status'] != 'hidden'}
        item['status'] = next(iter(statuses)) if len(statuses) == 1 else 'mixed' if statuses else 'unsupported'
        fallback = item['status'] != 'values_returned' or bool(item['gaps'])
        if args.render == 'all' or (args.render == 'fallback' and fallback):
            reason = 'explicit_render_request' if args.render == 'all' else 'query_evidence_incomplete'
            try:
                argv = ['render', '--uid', args.uid, '--panel', str(panel['id']), '--from', str(args.from_ms),
                        '--to', str(args.to_ms), '--width', str(args.width), '--height', str(args.height)]
                for name, value in variables.items():
                    variable = name + '=' + value
                    argv.extend(['--var', variable] if reader.VARIABLE.fullmatch(variable) else
                                ['--var-base64', base64.b64encode(variable.encode()).decode()])
                receipt = client.call(argv)
                path = Path(receipt.pop('image_path'))
                # Only an internally generated, owner-private helper capture can supply image bytes.
                if path.parent != reader._render_dir() or not path.name.startswith('grafana-render-'):
                    raise reader.SafeError('invalid_image_path')
                with path.open('rb') as handle:
                    raw = handle.read(reader.MAX_IMAGE + 1)
                if len(raw) != receipt['image_bytes'] or hashlib.sha256(raw).hexdigest() != receipt['image_sha256']:
                    raise reader.SafeError('image_receipt_mismatch')
                name = f"panel-{panel['id']}.png"
                try:
                    _module('grafana_evidence').validate_image(name, raw)
                except ValueError:
                    raise reader.SafeError('invalid_render_image') from None
                images[name] = raw
                item['render'] = {'status': 'image_uninspected', 'image_file': name, 'image_path': str(path),
                                  'fallback_reason': reason, 'next_action': 'inspect_render', 'receipt': receipt}
                if receipt.get('dashboard_version') != dashboard.get('version'):
                    item['gaps'].append('dashboard_changed_during_render')
            except (reader.SafeError, OSError) as error:
                item['render'] = {'status': 'failed', 'fallback_reason': reason,
                                  'error': str(error) if isinstance(error, reader.SafeError) else 'image_unavailable'}
    operations = {'annotations': ['annotations', '--from', str(args.from_ms), '--to', str(args.to_ms), '--dashboard-uid', args.uid]}
    if isinstance(meta.get('folderUid'), str) and reader.UID.fullmatch(meta['folderUid']):
        operations['alerts'] = ['alerts', '--folder-uid', meta['folderUid']]
    else:
        report['gaps'].append('alert_folder_unavailable')
    for name, command in operations.items():
        try:
            report['context'][name] = client.call(command)
        except reader.SafeError as error:
            report['context'][name] = {'ok': False, 'error': str(error)}
            report['gaps'].append(name + '_unavailable')
    try:
        latest = client.call(['dashboard', '--uid', args.uid])
        report['dashboard_version_at_end'] = latest['dashboard'].get('version')
        if latest['dashboard'] != dashboard:
            report['gaps'].append('dashboard_changed_during_capture')
    except reader.SafeError:
        report['gaps'].append('dashboard_readback_unavailable')
    report['queries_attempted'] = query_count
    report['requests_made'] = client.requests
    report['response_bytes'] = client.bytes
    for item in report['panels']:
        render = item['render']
        path = render.get('image_path')
        if path and client.mask(path) != path:
            render.pop('image_path')
            render['path_status'] = 'unavailable'
            render['next_action'] = 'use_verified_package_artifact'
            item['gaps'].append('image_path_masked')
    return client.mask(report), images


def dependencies(client, args):
    """Discover one explicitly selected folder; limits and permission scope stay in the report."""
    gaps, captures, alerts = [], [], []
    folder_source = 'folder:' + args.folder_uid
    items = client.connection.items('/api/search?type=dash-db&limit=100&page=1&folderUIDs=' + args.folder_uid)
    if len(items) > 100 or any(item.get('folderUid') != args.folder_uid for item in items):
        raise reader.SafeError('folder_mismatch')
    if len(items) >= 100 or len(items) > args.max_dashboards:
        gaps.append({'code': 'dashboard_discovery_truncated', 'source': folder_source})
    seen = set()
    for item in items[:args.max_dashboards]:
        uid = item.get('uid')
        if not isinstance(uid, str) or not reader.UID.fullmatch(uid) or uid in seen:
            gaps.append({'code': 'invalid_or_duplicate_dashboard_uid', 'source': folder_source})
            continue
        seen.add(uid)
        try:
            capture = client.call(['dashboard', '--uid', uid])
            if capture['meta'].get('folderUid') != args.folder_uid:
                gaps.append({'code': 'dashboard_folder_changed', 'source': uid})
                continue
            captures.append(capture)
        except reader.SafeError as error:
            gaps.append({'code': 'dashboard_read_' + str(error), 'source': uid})
    try:
        # The legacy API has no folder filter. Fetch once within the normal response-byte cap,
        # validate the organization and retain only definitions in the requested folder.
        rules = client.connection.items('/api/v1/provisioning/alert-rules')
        if any('orgID' in rule and (type(rule['orgID']) is not int or rule['orgID'] != client.connection.organization) for rule in rules):
            raise reader.SafeError('organization_mismatch')
        if any(not isinstance(rule.get('folderUID'), str) for rule in rules):
            gaps.append({'code': 'alert_definitions_missing_folder', 'source': folder_source})
        selected = [rule for rule in rules if rule.get('folderUID') == args.folder_uid]
        if len(selected) > 100:
            gaps.append({'code': 'alert_definition_limit_reached', 'source': folder_source})
        alerts = [{'rule': rule, 'grafana_url': client.connection.base,
                   'organization_id': client.connection.organization} for rule in selected[:100]]
    except reader.SafeError as error:
        gaps.append({'code': 'alert_definitions_' + str(error), 'source': folder_source})
    report = _module('grafana_dependencies').build_map(captures, alerts)
    # Put collection failures before per-expression gaps so the HTML display cap cannot hide them.
    report['gaps'] = gaps + report['gaps']
    report.update({'folder_uid': args.folder_uid, 'dashboard_captures': captures, 'alert_captures': alerts,
                   'discovery': {'items_observed': len(items), 'dashboards_read': len(captures),
                                 'max_dashboards': args.max_dashboards, 'coverage': 'permission_scoped',
                                 'truncated': len(items) >= 100 or len(items) > args.max_dashboards},
                   'provenance': {'grafana_url': client.connection.base, 'organization_id': client.connection.organization,
                                  'retrieved_at_utc': datetime.now(UTC).isoformat()},
                   'requests_made': client.requests, 'response_bytes': client.bytes})
    return client.mask(report), {}


def alert_preview(args):
    packaged = bool(args.package_dir or args.source_id)
    if packaged:
        source, receipt = _load_verified_source(args)
        source_sha256 = receipt['report_sha256']
    else:
        path = args.query_file or args.report_file
        with path.open('rb') as handle:
            raw = handle.read(32 * 1024 * 1024 + 1)
        if len(raw) > 32 * 1024 * 1024:
            raise reader.SafeError('input_too_large')
        try:
            source = json.loads(raw, parse_constant=reader._reject_constant)
        except (ValueError, UnicodeError, RecursionError):
            raise reader.SafeError('invalid_input') from None
        source_sha256 = hashlib.sha256(raw).hexdigest()
    query = source
    if args.report_file or packaged:
        if not isinstance(source, dict) or source.get('operation') != 'investigate' or not isinstance(source.get('panels'), list):
            raise reader.SafeError('invalid_input')
        candidates = [target.get('result') for panel in source['panels'] if isinstance(panel, dict) and panel.get('id') == args.panel
                      for target in panel.get('targets', []) if isinstance(target, dict) and target.get('ref_id') == args.ref_id
                      and target.get('mode') == 'range' and isinstance(target.get('result'), dict)]
        if len(candidates) != 1:
            raise reader.SafeError('query_selection_not_unique')
        query = candidates[0]
    try:
        report = _module('grafana_alert_preview').preview(query, operator=args.operator, threshold=args.threshold,
                                                         pending_ms=args.pending_ms, step_ms=args.step_ms,
                                                         alignment=args.alignment, grid_origin_ms=args.grid_origin_ms)
    except ValueError:
        raise reader.SafeError('unsupported_preview_input') from None
    report['source_sha256'] = source_sha256
    report['source_integrity'] = 'manifest_verified' if packaged else 'unverified_standalone_json'
    report['source_query'] = query
    return report, {}


def _source_path(args):
    return _capture_path(args.source_id) if args.source_id else args.package_dir


def _load_source(args):
    return _load_verified_source(args)[0]


def _load_verified_source(args):
    try:
        return _module('grafana_capture').load_verified_capture(_source_path(args))
    except (OSError, ValueError, RecursionError):
        raise reader.SafeError('invalid_evidence_package') from None


def offline(args):
    capture = _module('grafana_capture')
    if args.command == 'verify-package':
        return capture.verify_package(_source_path(args))
    if args.command == 'compare':
        before = _capture_path(args.before_id) if args.before_id else args.before
        after = _capture_path(args.after_id) if args.after_id else args.after
        return capture.compare_captures(capture.load_capture(before), capture.load_capture(after))
    report = _load_source(args)
    if args.command == 'analyze':
        return _module('grafana_analyze').analyze_capture(report, analysis=args.analysis)
    if args.command == 'impact':
        graph = report if report.get('operation') == 'dependencies' else _module('grafana_analyze').analyze_capture(report, analysis='dependencies')['dependencies']
        return _module('grafana_dependencies').reverse_impact(graph, node_id=args.node_id, kind=args.kind, key=args.key)
    if args.command == 'inspect':
        return _inspect_capture(report, args)
    raise reader.SafeError('invalid_arguments')


def _inspect_capture(report, args):
    """Select stored evidence without loading files or contacting Grafana."""
    if args.panel is None:
        return _inspect_section(report, args.pointer or '', offset=args.offset, limit=args.limit)
    selected = [(index, panel) for index, panel in enumerate(report.get('panels', [])) if panel.get('id') == args.panel]
    if len(selected) != 1:
        raise reader.SafeError('panel_selection_not_unique')
    index, panel = selected[0]
    if args.ref_id is None:
        summary = _module('grafana_analyze').analyze_capture(report, analysis='summary')['summary']
        return {'operation': 'inspect', 'evidence_ref': f'/panels/{index}',
                'panel': next(item for item in summary['panels'] if item.get('id') == args.panel)}
    targets = [(i, target) for i, target in enumerate(panel.get('targets', []))
               if target.get('ref_id') == args.ref_id and (args.mode is None or target.get('mode') == args.mode)]
    if len(targets) != 1:
        raise reader.SafeError('query_selection_not_unique')
    target_index, target = targets[0]
    pointer = f'/panels/{index}/targets/{target_index}'
    if args.view == 'summary':
        digest = {key: value for key, value in target.items() if key != 'result'}
        if isinstance(target.get('result'), dict):
            digest['result'] = {key: value for key, value in target['result'].items() if key != 'results'}
            digest['series_statistics'] = _module('grafana_frames').FrameStatistics().summarize(
                target['result'], pointer + '/result')
        return {'operation': 'inspect', 'evidence_ref': pointer, 'target': digest}
    return _inspect_rows(target, pointer, frame_index=args.frame_index, offset=args.offset, limit=args.limit)


def _inspect_section(report, pointer, *, offset, limit):
    """Page any retained report; containers expose references rather than nested payloads."""
    value = report
    try:
        for encoded in pointer.split('/')[1:] if pointer else []:
            key = encoded.replace('~1', '/').replace('~0', '~')
            if isinstance(value, list):
                if not re.fullmatch(r'0|[1-9][0-9]*', key):
                    raise ValueError
                value = value[int(key)]
            elif isinstance(value, dict):
                value = value[key]
            else:
                raise ValueError
    except (KeyError, IndexError, ValueError):
        raise reader.SafeError('evidence_pointer_unavailable') from None
    result = {'operation': 'inspect', 'evidence_ref': pointer, 'offset': offset}
    if isinstance(value, str):
        end = min(offset + limit, len(value))
        return {**result, 'type': 'string', 'text': value[offset:end], 'total': len(value),
                'next_offset': end if end < len(value) else None}
    if not isinstance(value, (list, dict)):
        return {**result, 'type': 'scalar', 'value': value}
    keys = list(value) if isinstance(value, dict) else range(len(value))
    items = []
    for key in keys[offset:offset + limit]:
        child = value[key]
        ref = pointer + '/' + str(key).replace('~', '~0').replace('/', '~1')
        item = {'key': key, 'evidence_ref': ref}
        if isinstance(child, (dict, list, str)):
            item.update(type='object' if isinstance(child, dict) else 'array' if isinstance(child, list) else 'string',
                        size=len(child))
        else:
            item.update(type='scalar', value=child)
        items.append(item)
    result.update(type='object' if isinstance(value, dict) else 'array', items=items, total=len(value))
    while items and len(json.dumps(result, ensure_ascii=True).encode()) > MAX_AGENT_BYTES // 2:
        items.pop()
    if offset < len(value) and not items:
        raise reader.SafeError('evidence_item_too_large')
    end = min(offset + len(items), len(value))
    result['next_offset'] = end if end < len(value) else None
    return result


def _inspect_rows(target, pointer, *, frame_index, offset, limit):
    """Build one bounded page while retaining its position in the source frame."""
    frames = target.get('result', {}).get('results', {}).get('A', {}).get('frames', [])
    if frame_index >= len(frames):
        raise reader.SafeError('frame_unavailable')
    parsed, _reason = reader.frame_columns(frames[frame_index])
    if parsed is None:
        raise reader.SafeError('unsupported_frame_encoding')
    fields, columns = parsed
    row_count = len(columns[0]) if columns else 0
    selected_rows = list(zip(*(column[offset:offset + limit] for column in columns), strict=True))
    result = {'operation': 'inspect', 'view': 'rows', 'evidence_ref': pointer + f'/result/results/A/frames/{frame_index}',
              'fields': fields, 'row_count': row_count, 'offset': offset, 'rows': selected_rows,
              'health': 'not_assessed'}
    while selected_rows and len(json.dumps(result, ensure_ascii=True).encode()) > MAX_AGENT_BYTES // 2:
        selected_rows.pop()
    result.update(rows_returned=len(selected_rows), next_offset=offset + len(selected_rows)
                  if selected_rows and offset + len(selected_rows) < row_count else None)
    if not selected_rows and offset < row_count:
        result['gaps'] = ['single_row_exceeds_output_budget']
    return result


def doctor(environ, transport, probe=False):
    """Inspect configuration through the protected helper; never return credential values."""
    result = {'schema_version': 1, 'operation': 'doctor', 'configuration': 'unavailable',
              'connection': 'not_checked', 'capture_store': 'not_checked',
              'capabilities': ['plan', 'investigate', 'dependencies', 'verify-package', 'analyze', 'compare', 'impact', 'inspect', 'alert-preview'],
              'health': 'not_assessed', 'gaps': []}
    result['runtime'] = {'python': '.'.join(map(str, sys.version_info[:3])),
                         'isolated': bool(sys.flags.isolated), 'site_enabled': not bool(sys.flags.no_site),
                         'dependencies': {}, 'dependency_imports': 'not_tested'}
    for name, module in LIBRARIES.items():
        try:
            version = importlib.metadata.version(name)
            available = importlib.util.find_spec(module) is not None
        except (ImportError, ValueError):
            version, available = None, False
        result['runtime']['dependencies'][name] = {'version': version, 'available': available}
        if not available:
            result['gaps'].append('dependency_unavailable_' + name.replace('-', '_'))
    try:
        reader._connect(reader._settings(environ, reader._settings_file()), transport)
        result['configuration'] = 'valid'
        if probe:
            Client(environ, transport)
            result['connection'] = 'organization_verified'
    except reader.SafeError as error:
        result['gaps'].append(str(error))
    try:
        _capture_path('diagnostic')
        result['capture_store'] = 'path_validated_write_not_tested'
    except (reader.SafeError, RuntimeError):
        result['gaps'].append('capture_directory_unavailable')
    return result


def _argument_parser():
    parser = reader._Parser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest='command', required=True)
    investigate_parser = sub.add_parser('investigate', aliases=['plan'], allow_abbrev=False)
    investigate_parser.add_argument('--uid', required=True)
    investigate_parser.add_argument('--from', dest='from_ms', type=int, required=True)
    investigate_parser.add_argument('--to', dest='to_ms', type=int, required=True)
    investigate_parser.add_argument('--var', dest='variables', action='append', default=[])
    investigate_parser.add_argument('--interval-ms', type=int)
    investigate_parser.add_argument('--rate-interval-ms', type=int)
    investigate_parser.add_argument('--max-panels', type=int, default=50)
    investigate_parser.add_argument('--max-queries', type=int, default=100)
    investigate_parser.add_argument('--render', choices=('none', 'fallback', 'all'), default='fallback')
    investigate_parser.add_argument('--width', type=int, default=1200)
    investigate_parser.add_argument('--height', type=int, default=600)
    dependency_parser = sub.add_parser('dependencies', allow_abbrev=False)
    dependency_parser.add_argument('--folder-uid', required=True)
    dependency_parser.add_argument('--max-dashboards', type=int, default=50)
    preview_parser = sub.add_parser('alert-preview', allow_abbrev=False)
    source = preview_parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--query-file', type=Path)
    source.add_argument('--report-file', type=Path)
    source.add_argument('--package-dir', type=Path)
    source.add_argument('--source-id')
    preview_parser.add_argument('--panel', type=int)
    preview_parser.add_argument('--ref-id')
    preview_parser.add_argument('--operator', choices=('gt', 'ge', 'lt', 'le', 'eq', 'ne'), required=True)
    preview_parser.add_argument('--threshold', type=float, required=True)
    preview_parser.add_argument('--pending-ms', type=int, required=True)
    preview_parser.add_argument('--step-ms', type=int, required=True)
    preview_parser.add_argument('--alignment', choices=('window', 'observed', 'explicit'), default='observed')
    preview_parser.add_argument('--grid-origin-ms', type=int)
    offline_parsers = []
    for name in ('verify-package', 'analyze', 'impact', 'inspect', 'open-report'):
        item = sub.add_parser(name, allow_abbrev=False)
        inputs = item.add_mutually_exclusive_group(required=True)
        inputs.add_argument('--package-dir', type=Path)
        inputs.add_argument('--source-id')
        if name == 'analyze':
            item.add_argument('--analysis', choices=('all', 'summary', 'hygiene', 'dependencies'), default='all')
        elif name == 'impact':
            item.add_argument('--node-id')
            item.add_argument('--kind')
            item.add_argument('--key')
        elif name == 'inspect':
            selection = item.add_mutually_exclusive_group()
            selection.add_argument('--panel', type=int)
            selection.add_argument('--pointer', help='JSON Pointer into any saved report; omitted selection pages its root.')
            item.add_argument('--ref-id')
            item.add_argument('--mode', choices=('range', 'instant'))
            item.add_argument('--view', choices=('summary', 'rows'), default='summary')
            item.add_argument('--frame-index', type=int, default=0)
            item.add_argument('--offset', type=int, default=0)
            item.add_argument('--limit', type=int, default=100)
        offline_parsers.append(item)
    compare_parser = sub.add_parser('compare', allow_abbrev=False)
    for name in ('before', 'after'):
        group = compare_parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--' + name, type=Path)
        group.add_argument('--' + name + '-id')
    diagnostics = sub.add_parser('doctor', allow_abbrev=False)
    diagnostics.add_argument('--probe', action='store_true')
    for command_parser in (investigate_parser, dependency_parser, preview_parser, compare_parser, diagnostics, *offline_parsers):
        destinations = command_parser.add_mutually_exclusive_group()
        destinations.add_argument('--output-dir', type=Path)
        destinations.add_argument('--capture-id')
        command_parser.add_argument('--agent-json', action='store_true', help='Emit bounded structured evidence for agents.')
        command_parser.add_argument('--open-vscode', action='store_true',
                                    help='Open the completed report in the existing local VS Code window using its Integrated Browser.')
    return parser


def _validate_argument_spelling(argv):
    # A single literal spelling per option keeps guard and CLI semantics identical.
    seen, index = set(), 1
    booleans = {'--agent-json', '--open-vscode', '--probe'}
    while index < len(argv):
        flag = argv[index]
        if not flag.startswith('--') or '=' in flag or (flag in seen and flag != '--var'):
            raise reader.SafeError('invalid_arguments')
        seen.add(flag)
        index += 1 if flag in booleans else 2


def _validate_command_args(args):
    for name in ('capture_id', 'source_id', 'before_id', 'after_id'):
        value = getattr(args, name, None)
        if value is not None and not CAPTURE_ID.fullmatch(value):
            raise reader.SafeError('invalid_capture_id')
    if args.command in ('investigate', 'plan'):
        reader.parse_args(['render', '--uid', args.uid, '--panel', '1', '--from', str(args.from_ms), '--to', str(args.to_ms),
                           '--width', str(args.width), '--height', str(args.height)])
        if args.to_ms - args.from_ms > reader.MAX_RANGE_MS or not 1 <= args.max_panels <= 50 or not 1 <= args.max_queries <= 100:
            raise reader.SafeError('invalid_arguments')
        for interval in (args.interval_ms, args.rate_interval_ms):
            if interval is not None and not 1000 <= interval <= reader.MAX_RANGE_MS:
                raise reader.SafeError('invalid_arguments')
        _variables(args.variables)
    elif args.command == 'dependencies':
        if not reader.UID.fullmatch(args.folder_uid) or not 1 <= args.max_dashboards <= 50:
            raise reader.SafeError('invalid_arguments')
    elif args.command == 'alert-preview':
        if (not args.query_file and (args.panel is None or not args.ref_id)) or (args.query_file and (args.panel is not None or args.ref_id is not None)):
            raise reader.SafeError('invalid_arguments')
        if (args.alignment == 'explicit') != (args.grid_origin_ms is not None):
            raise reader.SafeError('invalid_arguments')
    elif ((args.command == 'impact' and ((args.node_id is None) == (args.kind is None or args.key is None)))
          or (args.command == 'inspect' and (not 0 <= args.offset <= (1000000 if args.panel is not None else 32 * 1024 * 1024) or not 1 <= args.limit <= 500
              or not 0 <= args.frame_index <= 1000 or (args.view == 'rows' and args.ref_id is None)))):
        raise reader.SafeError('invalid_arguments')
    if args.command == 'inspect':
        if args.panel is None and (args.ref_id is not None or args.mode is not None or args.view != 'summary' or args.frame_index != 0):
            raise reader.SafeError('invalid_arguments')
        if args.pointer is not None and (len(args.pointer) > 4096 or (args.pointer and not args.pointer.startswith('/'))
                                         or re.search(r'~(?![01])|[\x00-\x1f\x7f]', args.pointer)):
            raise reader.SafeError('invalid_arguments')


def parse_args(argv):
    """Share the CLI's exact grammar and command constraints with the guard."""
    args = _argument_parser().parse_args(argv)
    _validate_argument_spelling(argv)
    _validate_command_args(args)
    if not args.agent_json and not (args.output_dir or args.capture_id) and args.command != 'open-report':
        raise reader.SafeError('output_required')
    if args.open_vscode and not (args.output_dir or args.capture_id):
        raise reader.SafeError('output_required')
    if args.command == 'open-report' and args.open_vscode:
        raise reader.SafeError('invalid_arguments')
    if args.output_dir:
        if args.output_dir.exists() or args.output_dir.is_symlink():
            raise reader.SafeError('output_directory_exists')
        # Match capture readback's no-indirection policy before collection or creation.
        for parent in args.output_dir.absolute().parents:
            if parent.is_symlink() or (parent.exists() and (
                    not parent.is_dir() or getattr(parent.lstat(), 'st_file_attributes', 0) & 0x400)):
                raise reader.SafeError('output_directory_unavailable')
    return args


@dataclass
class _Execution:
    """Keep captured evidence paired with the client that must sanitize its output."""

    report: dict
    images: dict[str, bytes]
    client: Client | None = None


def _execute_command(args, environ, transport):
    client = None
    images = {}
    if args.command == 'alert-preview':
        report, images = alert_preview(args)
    elif args.command == 'doctor':
        report = doctor(environ, transport, args.probe)
    elif args.command == 'open-report':
        _module('grafana_capture').verify_package(_source_path(args))
        report = {'operation': 'open-report', 'viewer': _module('grafana_vscode').open_report(_source_path(args), environ=environ)}
    elif args.command in ('plan', 'investigate', 'dependencies'):
        client = Client(environ, transport)
        if args.command == 'plan':
            report = client.mask(query_plan(client.call(['dashboard', '--uid', args.uid]), args))
        else:
            report, images = (investigate if args.command == 'investigate' else dependencies)(client, args)
    else:
        report = offline(args)
    return _Execution(report, images, client)


def _prepare_response(args, execution, destination, environ):
    """Publish retained evidence before optional viewing, masking, and output bounds."""
    report, images, client = execution.report, execution.images, execution.client
    report.setdefault('schema_version', 1)
    report['tool_files'] = {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                            for path in sorted(Path(__file__).parent.glob('*.py'))}
    result = {'ok': True, 'operation': args.command, 'trust': 'untrusted_telemetry'}
    if args.command == 'open-report':
        result['viewer'] = report['viewer']
    if destination:
        result['package'] = _module('grafana_evidence').write_package(report, destination, images=images)
        # Analyze the bytes actually retained, including explicit budget omissions.
        report = _module('grafana_capture').load_capture(destination)
    evidence_path = destination or (_source_path(args) if hasattr(args, 'source_id') and (args.source_id or args.package_dir) else None)
    if args.agent_json:
        result['data'] = (_module('grafana_analyze').analyze_capture(report, analysis='all')
                          if args.command == 'investigate' else report)
        if args.capture_id:
            result['capture_id'] = args.capture_id
        if evidence_path:
            verified = _module('grafana_capture').verify_package(evidence_path)
            result['artifacts'] = [{'image_file': name, 'image_path': str((evidence_path / name).absolute()),
                                    'verification': 'manifest_verified', 'appearance': 'not_assessed'}
                                   for name in verified.get('images', [])]
    if args.open_vscode:
        try:
            result['viewer'] = _module('grafana_vscode').open_report(destination, environ=environ)
        except Exception:
            result['viewer'] = {'status': 'unavailable', 'error': 'vscode_launch_unavailable',
                                'visual_verification': 'not_performed'}
    if client is not None:
        for artifact in result.get('artifacts', []):
            if client.mask(artifact['image_path']) != artifact['image_path']:
                artifact.pop('image_path')
                artifact['error'] = 'image_path_masked'
        result = client.mask(result)
    if len(json.dumps(result, ensure_ascii=True, allow_nan=False).encode()) > MAX_AGENT_BYTES:
        result.pop('data', None)
        result.update(status='output_truncated', gaps=['agent_output_limit_reached'],
                      next_action='inspect_saved_report' if evidence_path else 'repeat_with_capture_id')
        if evidence_path:
            source = (['--source-id', args.capture_id] if destination and args.capture_id else
                      ['--source-id', args.source_id] if not destination and getattr(args, 'source_id', None) else
                      ['--package-dir', str(evidence_path)])
            result['recovery'] = {'arguments': ['inspect', *source, '--agent-json'],
                                  'selection': 'Follow evidence_ref with --pointer; page with --offset and --limit.'}
    if client is not None:
        recovery = result.get('recovery')
        if recovery and client.mask(recovery['arguments']) != recovery['arguments']:
            recovery.pop('arguments')
            recovery['error'] = 'recovery_arguments_masked'
        # Recovery metadata is part of the same model-facing credential boundary.
        result = client.mask(result)
    return result


def main(argv=None, *, environ=None, transport=None, output=None):
    output = sys.stdout if output is None else output
    try:
        args = parse_args(sys.argv[1:] if argv is None else argv)
        _check_dependencies(args)
        env = os.environ if environ is None else environ
        transport = reader.http_transport if transport is None else transport
        destination = _capture_path(args.capture_id, create=True) if args.capture_id else args.output_dir
        if destination and destination.exists():
            raise reader.SafeError('output_directory_exists')
        execution = _execute_command(args, env, transport)
        result = _prepare_response(args, execution, destination, environ)
        code = 0
    except reader.SafeError as error:
        result, code = {'ok': False, 'error': str(error)}, 2
    except ImportError:
        result, code = {'ok': False, 'error': 'dependency_unavailable'}, 2
    except (ValueError, OSError, RecursionError):
        result, code = {'ok': False, 'error': 'invalid_or_unavailable_evidence'}, 2
    except Exception:
        result, code = {'ok': False, 'error': 'workflow_failed'}, 2
    output.write(json.dumps(result, ensure_ascii=True, allow_nan=False) + '\n')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
