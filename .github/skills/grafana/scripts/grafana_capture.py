"""Bounded, offline evidence verification for agent consumers.

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
from pathlib import Path
from runpy import run_path

MAX_PACKAGE_BYTES = 96 * 1024 * 1024
MAX_REPORT_BYTES = 32 * 1024 * 1024
MAX_MANIFEST_BYTES = 65536
MAX_FILES = 52
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
    return load_verified_capture(directory)[0]


def load_verified_capture(directory) -> tuple[dict, dict]:
    """Return parsed evidence and the receipt for those same verified bytes."""
    return _verified(directory)
