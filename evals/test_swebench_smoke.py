"""Smoke acceptance requires observed controls, never just requested Docker flags."""

import copy
import json
import os
import subprocess
import sys

import pytest
from swebench_adapter.smoke import assess_smoke, cpu_probe


def evidence():
    return {
        'reference': {'outcome': 'PASS', 'cleanup': [{'present': False}]},
        'empty': {'outcome': 'FAIL', 'baseline': True, 'cleanup': [{'present': False}]},
        'guard_allow': {'returncode': 0, 'stdout': ''},
        'guard_deny': {'returncode': 0, 'stdout': json.dumps({'hookSpecificOutput': {
            'permissionDecision': 'deny', 'permissionDecisionReason': 'credential-bearing cf env denied'}})},
        'no_cr': True, 'history_pruned': True,
        'egress': {'proxy': True, 'internet': False, 'host': False, 'dns': False, 'key_route': False},
        'cpu': {'wall_seconds': 5.0, 'cpu_seconds': 9.7},
        'container': {'HostConfig': {'NanoCpus': 2000000000, 'CapDrop': ['ALL'],
            'CapAdd': None, 'Privileged': False, 'SecurityOpt': ['no-new-privileges'],
            'Memory': 2147483648, 'PidsLimit': 256}, 'Mounts': [
                {'Destination': '/opt/claude', 'RW': False}, {'Destination': '/opt/fleet', 'RW': False}]},
        'network': {'Internal': True, 'EnableIPv6': False, 'Options': {
            'com.docker.network.bridge.gateway_mode_ipv4': 'isolated'}},
        'storage': {'stop': 'storage_limit', 'quota_rejected': False},
    }


def test_all_observed_controls_pass():

    assert all(assess_smoke(evidence(), [{'present': False}]).values())


@pytest.mark.parametrize('field, replacement, failed', [
    ('reference', {'outcome': 'INCONCLUSIVE', 'cleanup': [{'present': False}]}, 'reference_resolves'),
    ('empty', {'outcome': 'PASS', 'baseline': True, 'cleanup': [{'present': False}]}, 'empty_rejected'),
    ('empty', {'outcome': 'FAIL', 'cleanup': [{'present': False}]}, 'empty_rejected'),
    ('guard_allow', {'returncode': 0, 'stdout': 'guard failed'}, 'guard_allow'),
    ('guard_deny', {'returncode': 0, 'stdout': '{}'}, 'guard_deny'),
    ('no_cr', 'true', 'no_cr'),
    ('history_pruned', False, 'history_pruned'),
    ('cpu', {'wall_seconds': 5, 'cpu_seconds': 20}, 'cpu_cap'),
    ('cpu', {'wall_seconds': 0, 'cpu_seconds': 0}, 'cpu_cap'),
    ('storage', {'stop': None, 'quota_rejected': False}, 'storage_cap'),
])
def test_missing_or_failed_measurements_never_pass(field, replacement, failed):

    observed = evidence()
    observed[field] = replacement
    assert assess_smoke(observed, [{'present': False}])[failed] is False


@pytest.mark.parametrize('path, value', [
    (('egress', 'internet'), True), (('egress', 'host'), True), (('egress', 'dns'), True),
    (('egress', 'key_route'), True), (('egress', 'proxy'), False),
    (('network', 'Internal'), False), (('network', 'EnableIPv6'), True),
])
def test_unintended_network_access_blocks_smoke(path, value):

    observed = evidence()
    observed[path[0]][path[1]] = value
    assert assess_smoke(observed, [{'present': False}])['egress'] is False


def test_unavailable_guard_is_not_mistaken_for_expected_credential_deny():

    observed = evidence()
    observed['guard_deny']['stdout'] = json.dumps({'hookSpecificOutput': {
        'permissionDecision': 'deny', 'permissionDecisionReason': 'guard unavailable or failed'}})
    assert assess_smoke(observed, [{'present': False}])['guard_deny'] is False


@pytest.mark.parametrize('cleanup', [[], [{'present': True}], [{'present': None}], [{'present': 'false'}]])
def test_cleanup_needs_proven_absence(cleanup):

    assert assess_smoke(evidence(), cleanup)['cleanup'] is False


@pytest.mark.skipif(os.name != 'posix', reason='probe runs in Linux containers')
def test_cpu_probe_measures_actual_child_work():

    # Tiny host-side execution proves the probe observes child CPU, not a hard-coded pass.
    result = subprocess.run([sys.executable, '-c', cpu_probe(0.1)], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0
    measured = json.loads(result.stdout)
    assert measured['wall_seconds'] > 0
    assert measured['cpu_seconds'] > 0


def test_unexpected_capability_or_writable_mount_invalidates_caps():

    for change in ('capability', 'mount'):
        observed = copy.deepcopy(evidence())
        if change == 'capability':
            observed['container']['HostConfig']['CapAdd'] = ['SYS_ADMIN']
        else:
            observed['container']['Mounts'][0]['RW'] = True
        assert assess_smoke(observed, [{'present': False}])['cpu_cap'] is False
