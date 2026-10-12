"""Bounded, offline evidence verification and comparisons for agent consumers.

Manifest hashes detect damage relative to the manifest; they do not authenticate a
package author. No paths or URLs inside report content are fetched or executed.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
from functools import cache
from pathlib import Path
from runpy import run_path

MAX_PACKAGE_BYTES = 96 * 1024 * 1024
MAX_REPORT_BYTES = 32 * 1024 * 1024
MAX_MANIFEST_BYTES = 65536
MAX_FILES = 52
MAX_DIFF_ITEMS = 200
MAX_DETAIL_BYTES = 1024 * 1024
MAX_DETAIL_NODES = 20000
MAX_DETAIL_DEPTH = 32
MAX_DEEP_DIFFS = 10000
MAX_DEEP_PASSES = 1
MAX_PATH_CHARS = 1024
FILE_NAME = re.compile(r'(?:report\.json|report\.html|panel-[0-9]+\.png)\Z')
_module = run_path(str(Path(__file__).with_name('grafana_modules.py')))['load_module']


def _json(raw: bytes):
    def pairs(items):
        value = {}
        for key, child in items:
            if key in value:
                raise ValueError('duplicate_json_key')
            value[key] = child
        return value
    def invalid(value):
        raise ValueError('nonfinite_json_number')
    try:
        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
        pending = [(value, 0)]
        while pending:
            item, depth = pending.pop()
            if depth > 64:
                raise ValueError('json_depth_exceeded')
            if isinstance(item, float) and not math.isfinite(item):
                raise ValueError('nonfinite_json_number')
            if isinstance(item, dict):
                pending.extend((child, depth + 1) for child in item.values())
            elif isinstance(item, list):
                pending.extend((child, depth + 1) for child in item)
        return value
    except (UnicodeError, RecursionError, json.JSONDecodeError) as error:
        raise ValueError('invalid_capture_json') from error


def _identity(info):
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns


def _plain(path: Path, *, directory=False):
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise ValueError('symlink_or_reparse_point_refused')
    if not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)):
        raise ValueError('unexpected_file_type')
    return info


def _read(path: Path, limit: int) -> bytes:
    before = _plain(path)
    if before.st_size > limit:
        raise ValueError('capture_size_limit')
    descriptor = os.open(path, os.O_RDONLY | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(descriptor, 'rb') as stream:
        if _identity(os.fstat(stream.fileno())) != _identity(before):
            raise ValueError('capture_changed_during_read')
        raw = stream.read(limit + 1)
        after = os.fstat(stream.fileno())
    if len(raw) > limit or _identity(after) != _identity(before) or _identity(_plain(path)) != _identity(before):
        raise ValueError('capture_changed_during_read')
    return raw


def _manifest_files(manifest_raw: bytes, names: set[str]) -> dict:
    """Validate the manifest's schema and inventory before reading its files."""
    manifest = _json(manifest_raw)
    if not isinstance(manifest, dict) or type(manifest.get('schema_version')) is not int or manifest['schema_version'] != 1:
        raise ValueError('unsupported_manifest_schema')
    files = manifest.get('files')
    if not isinstance(files, dict) or not {'report.json', 'report.html'} <= set(files) or len(files) > MAX_FILES:
        raise ValueError('invalid_manifest_files')
    if names != set(files) | {'manifest.json'}:
        raise ValueError('unexpected_or_missing_package_file')
    return files


def _parse_report(report_raw: bytes) -> dict:
    """Validate the already-verified report bytes without reopening the file."""
    report = _json(report_raw)
    if not isinstance(report, dict) or type(report.get('schema_version', 1)) is not int or report.get('schema_version', 1) != 1:
        raise ValueError('unsupported_report_schema')
    for name, expected in (('panels', list), ('dashboard', dict), ('provenance', dict), ('variables', dict), ('evidence', dict)):
        if name in report and not isinstance(report[name], expected):
            raise ValueError('invalid_report_shape')
    return report


def _verified(directory) -> tuple[dict, dict]:
    root = Path(os.path.abspath(directory))
    # Refuse redirection in the supplied path, including Windows junctions.
    for ancestor in (root, *root.parents):
        _plain(ancestor, directory=True)
    before = _identity(root.stat())
    names = {entry.name for entry in root.iterdir()}
    if '.incomplete' in names:
        raise ValueError('incomplete_capture')
    if len(names) > MAX_FILES + 1:
        raise ValueError('capture_file_limit')
    manifest_raw = _read(root / 'manifest.json', MAX_MANIFEST_BYTES)
    files = _manifest_files(manifest_raw, names)
    total = len(manifest_raw)
    report_raw = None
    for name, entry in files.items():
        if not FILE_NAME.fullmatch(name) or not isinstance(entry, dict):
            raise ValueError('invalid_manifest_path')
        size, digest = entry.get('size_bytes'), entry.get('sha256')
        if type(size) is not int or size < 0 or not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise ValueError('invalid_manifest_entry')
        total += size
        limit = MAX_REPORT_BYTES if name == 'report.json' else 8 * 1024 * 1024 if name.endswith('.png') else MAX_PACKAGE_BYTES
        if size > limit or total > MAX_PACKAGE_BYTES:
            raise ValueError('capture_size_limit')
        raw = _read(root / name, size)
        if len(raw) != size or hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError('capture_hash_or_size_mismatch')
        if name.endswith('.png'):
            _module('grafana_evidence').validate_image(name, raw)
        if name == 'report.json':
            report_raw = raw
    if before != _identity(root.stat()) or names != {entry.name for entry in root.iterdir()} or manifest_raw != _read(root / 'manifest.json', MAX_MANIFEST_BYTES):
        raise ValueError('capture_changed_during_read')
    report = _parse_report(report_raw)
    receipt = {'schema_version': 1, 'operation': 'verify_package', 'status': 'verified',
               'capture_status': report.get('evidence', {}).get('status', 'complete'),
               'files_verified': len(files), 'bytes_verified': total,
               'images': sorted(name for name in files if name.endswith('.png')),
               'manifest_sha256': hashlib.sha256(manifest_raw).hexdigest(),
               'report_sha256': hashlib.sha256(report_raw).hexdigest(),
               'integrity': 'matches_manifest', 'authenticity': 'not_established'}
    return report, receipt


def verify_package(directory) -> dict:
    """Return a bounded receipt, or raise ValueError/OSError for invalid evidence."""
    return _verified(directory)[1]


def load_capture(directory) -> dict:
    """Parse exactly the bytes verified in this call, not a second report read."""
    return _verified(directory)[0]


@cache
def _comparison_engine():
    """Keep optional dependencies outside verification and ordinary capture reads."""
    from deepdiff import DeepDiff  # noqa: PLC0415 - optional comparison dependency
    from deepdiff.operator import BaseOperator  # noqa: PLC0415 - optional comparison dependency

    class ExactScalar(BaseOperator):
        def give_up_diffing(self, level, diff_instance):
            # Preserve JSON signed zero and avoid generating unused multiline
            # text diffs, whose work is not limited by DeepDiff's node budget.
            before = level.t1.hex() if isinstance(level.t1, float) else level.t1
            after = level.t2.hex() if isinstance(level.t2, float) else level.t2
            if before != after:
                diff_instance.custom_report_result('values_changed', level)
            return True

    return DeepDiff, ExactScalar(types=[float, str])


def _detail_limit(before, after, before_json, after_json):
    """Bound the objects entering DeepDiff, not only the number of returned paths."""
    if len(before_json) + len(after_json) > MAX_DETAIL_BYTES:
        return 'detail_input_size_limit'
    pending = [(before, 0), (after, 0)]
    visited = 0
    while pending:
        value, depth = pending.pop()
        visited += 1
        if depth > MAX_DETAIL_DEPTH:
            return 'detail_input_depth_limit'
        if visited + len(pending) > MAX_DETAIL_NODES:
            return 'detail_input_node_limit'
        if isinstance(value, (dict, list)):
            children = value.values() if isinstance(value, dict) else value
            if visited + len(pending) + len(value) > MAX_DETAIL_NODES:
                return 'detail_input_node_limit'
            pending.extend((child, depth + 1) for child in children)
    return None


def _difference(kind, path, before_path, after_path):
    """Expose references, never changed values or unbounded, misleading paths."""
    omitted = any(isinstance(part, str) and (len(part) > 256 or any(ord(char) < 32 for char in part)) for part in path)
    if not omitted:
        omitted = len(json.dumps(path, ensure_ascii=True)) > MAX_PATH_CHARS
    relative_path = [] if omitted else path
    result = {'kind': kind, 'path': None if omitted else path,
              'before_ref': {'capture': 'before', 'report_path': before_path + relative_path,
                             'scope': 'subtree' if omitted else 'value'},
              'after_ref': {'capture': 'after', 'report_path': after_path + relative_path,
                            'scope': 'subtree' if omitted else 'value'}}
    if kind.endswith('_added'):
        result['before_ref'] = None
    elif kind.endswith('_removed'):
        result['after_ref'] = None
    if omitted:
        result['path_omitted'] = True
    return result


def _compare_content(before, after, before_path, after_path, remaining):
    # Preserve the established exact JSON comparison, including 1 versus 1.0 and
    # signed zero. DeepDiff explains the difference; an exhausted detail budget
    # must never turn an incomplete traversal into a false "unchanged" result.
    before_json = json.dumps(before, sort_keys=True, separators=(',', ':'), allow_nan=False)
    after_json = json.dumps(after, sort_keys=True, separators=(',', ':'), allow_nan=False)
    changed = before_json != after_json
    details = {'engine': 'deepdiff', 'status': 'complete', 'changes': [], 'reasons': []}
    if not changed:
        return changed, details
    reason = 'detail_output_limit' if remaining == 0 else _detail_limit(before, after, before_json, after_json)
    if reason:
        details.update(status='truncated', reasons=[reason])
        return changed, details
    DeepDiff, scalar_operator = _comparison_engine()
    diff = DeepDiff(before, after, view='tree', verbose_level=0, ignore_order=False,
                    ignore_numeric_type_changes=False, ignore_private_variables=False,
                    zip_ordered_iterables=True, threshold_to_diff_deeper=0,
                    max_diffs=MAX_DEEP_DIFFS, max_passes=MAX_DEEP_PASSES,
                    custom_operators=[scalar_operator])
    for kind in sorted(diff):
        for node in diff[kind]:
            if len(details['changes']) == remaining:
                details['reasons'].append('detail_output_limit')
                break
            details['changes'].append(_difference(kind, node.path(output_format='list'), before_path, after_path))
        if details['reasons']:
            break
    stats = diff.get_stats()
    for name, reason in (('MAX DIFF LIMIT REACHED', 'detail_work_limit'), ('MAX PASS LIMIT REACHED', 'detail_pass_limit')):
        if stats[name]:
            details['reasons'].append(reason)
    if details['reasons']:
        details['status'] = 'truncated'
    return changed, details


def _label(value):
    return value[:256] if isinstance(value, str) else 'unknown'


def _targets(report):
    result = {}
    for panel_index, panel in enumerate(report.get('panels', [])):
        if not isinstance(panel, dict) or not isinstance(panel.get('targets', []), list):
            raise ValueError('invalid_panel_shape')
        for target_index, target in enumerate(panel.get('targets', [])):
            if not isinstance(target, dict):
                raise ValueError('invalid_target_shape')
            if (type(panel.get('id')) is not int or
                    not isinstance(target.get('ref_id'), (str, type(None))) or
                    len(target.get('ref_id') or '') > 128 or
                    target.get('mode') not in (None, 'range', 'instant') or
                    not isinstance(target.get('result', {}), dict)):
                raise ValueError('invalid_target_identity_or_result')
            key = json.dumps([panel.get('id'), target.get('ref_id'), target.get('mode')])
            if key in result:
                raise ValueError('ambiguous_target_identity')
            result[key] = (target, ['panels', panel_index, 'targets', target_index, 'result', 'results'])
            if len(result) > 10000:
                raise ValueError('comparison_target_limit')
    return result


def compare_captures(before: dict, after: dict) -> dict:
    """Compare loaded investigations; values require explicit identical query context."""
    if before.get('operation') != 'investigate' or after.get('operation') != 'investigate':
        raise ValueError('comparison_requires_investigation_captures')
    left, right = _targets(before), _targets(after)
    reasons = []
    for field in ('grafana_url', 'organization_id'):
        a, b = before.get('provenance', {}).get(field), after.get('provenance', {}).get(field)
        if a is None or b is None or a != b:
            reasons.append(field + '_missing_or_different')
    for field in ('from_ms', 'to_ms', 'variables'):
        if field not in before or field not in after or before[field] != after[field]:
            reasons.append(field + '_missing_or_different')
    if not before.get('dashboard', {}).get('uid') or before.get('dashboard', {}).get('uid') != after.get('dashboard', {}).get('uid'):
        reasons.append('dashboard_identity_missing_or_different')
    if any(report.get('evidence', {}).get('status') == 'partial' for report in (before, after)):
        reasons.append('partial_capture')
    if before.get('dashboard', {}).get('templating') != after.get('dashboard', {}).get('templating'):
        reasons.append('dashboard_variables_or_filters_different')
    changed, details = _compare_content(before.get('dashboard'), after.get('dashboard'), ['dashboard'], ['dashboard'], MAX_DIFF_ITEMS)
    configuration = {'status': 'compared' if 'dashboard' in before and 'dashboard' in after else 'unsupported',
                     'changed': changed,
                     'changed_fields': [key[:256] for key in sorted(set(before.get('dashboard', {})) | set(after.get('dashboard', {})))
                                        if before.get('dashboard', {}).get(key) != after.get('dashboard', {}).get(key)][:MAX_DIFF_ITEMS],
                     'differences': details}
    remaining = MAX_DIFF_ITEMS - len(details['changes'])
    truncated = details['status'] == 'truncated'
    changes, values = [], []
    value_count = 0
    for key in sorted(set(left) | set(right)):
        a, before_path = left.get(key, (None, None))
        b, after_path = right.get(key, (None, None))
        if a is None or b is None or (a.get('status'), a.get('error'), a.get('evidence_status')) != (b.get('status'), b.get('error'), b.get('evidence_status')):
            changes.append({'target': json.loads(key), 'before': _label(a.get('status')) if a else 'absent', 'after': _label(b.get('status')) if b else 'absent'})
        if a is None or b is None:
            continue
        value_count += 1
        if len(values) == MAX_DIFF_ITEMS:
            continue
        ar, br = a.get('result', {}), b.get('result', {})
        context = ('datasource', 'kind', 'from', 'to', 'mode', 'expression', 'limits')
        unsupported = list(reasons)
        if any(field not in ar or field not in br or ar[field] != br[field] for field in context):
            unsupported.append('query_context_missing_or_different')
        if 'results' not in ar or 'results' not in br:
            unsupported.append('full_results_unavailable')
        item = {'target': json.loads(key), 'status': 'unsupported' if unsupported else 'compared'}
        if unsupported:
            item['reasons'] = unsupported
        else:
            changed, details = _compare_content(ar['results'], br['results'], before_path, after_path, remaining)
            remaining -= len(details['changes'])
            truncated |= details['status'] == 'truncated'
            item.update(values_changed=changed, differences=details,
                        comparison='exact_returned_frame_content', health='not_assessed')
        values.append(item)
    return {'schema_version': 1, 'operation': 'compare_captures', 'status': 'complete',
            'configuration': configuration,
            'coverage': {'before': _label(before.get('coverage')), 'after': _label(after.get('coverage')),
                         'target_changes': changes[:MAX_DIFF_ITEMS], 'target_change_count': len(changes)},
            'values': values, 'value_target_count': value_count,
            'truncated': truncated or value_count > MAX_DIFF_ITEMS or len(changes) > MAX_DIFF_ITEMS,
            'comparison_limits': {'reported_changes': MAX_DIFF_ITEMS, 'detail_input_bytes': MAX_DETAIL_BYTES,
                                  'detail_input_nodes': MAX_DETAIL_NODES, 'detail_input_depth': MAX_DETAIL_DEPTH,
                                  'deepdiff_max_diffs': MAX_DEEP_DIFFS, 'deepdiff_max_passes': MAX_DEEP_PASSES},
            'limitations': ['No health conclusion; frame differences do not reproduce panel transformations.',
                            'Inputs must be supplied by load_capture to establish manifest verification.']}
