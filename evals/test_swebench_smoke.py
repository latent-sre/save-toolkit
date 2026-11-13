"""Smoke acceptance requires observed controls, never just requested Docker flags."""

import copy
import errno
import json
import os
import subprocess
import sys
import time

import pytest
from swebench_adapter.limits import STORAGE_LIMIT
from swebench_adapter.smoke import _STORAGE_PROBE, assess_smoke, cpu_probe


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
        'storage': {'stop': None, 'quota_rejected': True},
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


@pytest.mark.parametrize('enforced', [True, False])
def test_storage_probe_reaches_binary_docker_quota_without_allocating_disk(monkeypatch, capsys, enforced):
    class File:
        written = 0

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            pass

        def write(self, block):
            if enforced and self.written + len(block) > 10_737_418_240:
                raise OSError(errno.ENOSPC, 'simulated Docker size=10G quota')
            self.written += len(block)
            return len(block)

    file = File()
    sleeps = []
    monkeypatch.setattr(time, 'sleep', sleeps.append)
    exec(_STORAGE_PROBE, {'open': lambda *_args, **_kwargs: file})
    result = json.loads(capsys.readouterr().out)
    assert result['quota'] is enforced
    if enforced:
        assert result['written'] == 10_737_418_240
        assert sleeps == []
    else:
        assert 10_737_418_240 < result['written'] <= 10_842_275_840
        assert sleeps == [90]


def test_watchdog_detection_does_not_establish_hard_containment():
    observed = evidence()
    observed["storage"] = {"stop": "storage_limit", "quota_rejected": False}
    assert not assess_smoke(observed, [{"present": False}])["storage_cap"]


def monitored_evidence():
    observed = evidence()
    observed["storage"] = {
        "mode": "monitored",
        "target_bytes": STORAGE_LIMIT,
        "hard_enforced": False,
        "quota_rejected": False,
        "samples": 2,
        "observed_peak_bytes": STORAGE_LIMIT + 1,
        "stop": "storage_limit",
    }
    return observed


def test_monitored_smoke_accepts_observed_stop_and_omits_hard_quota_check():
    checks = assess_smoke(monitored_evidence(), [{"present": False}], storage_mode="monitored")
    assert set(checks) == {
        "reference_resolves", "empty_rejected", "guard_allow", "guard_deny", "no_cr",
        "history_pruned", "egress", "cpu_cap", "storage_monitor", "cleanup",
    }
    assert all(checks.values())


def test_explicit_quota_smoke_preserves_the_default_check_contract():
    checks = assess_smoke(evidence(), [{"present": False}], storage_mode="quota")
    assert checks == assess_smoke(evidence(), [{"present": False}])
    assert "storage_cap" in checks and "storage_monitor" not in checks


@pytest.mark.parametrize("storage_mode", [None, False, 1, "", "unknown", [], {}])
def test_smoke_rejects_unknown_or_malformed_storage_mode(storage_mode):
    with pytest.raises(ValueError, match="storage"):
        assess_smoke(evidence(), [{"present": False}], storage_mode=storage_mode)


@pytest.mark.parametrize("field,value", [
    ("mode", "quota"), ("mode", None),
    ("target_bytes", STORAGE_LIMIT - 1), ("target_bytes", STORAGE_LIMIT + 1),
    ("hard_enforced", True), ("hard_enforced", None), ("hard_enforced", 0),
    ("quota_rejected", True), ("quota_rejected", None), ("quota_rejected", 0),
    ("samples", 0), ("samples", -1), ("samples", True), ("samples", 1.0),
    ("observed_peak_bytes", STORAGE_LIMIT), ("observed_peak_bytes", None),
    ("observed_peak_bytes", True), ("observed_peak_bytes", float(STORAGE_LIMIT + 1)),
    ("stop", None), ("stop", "timeout"),
])
def test_monitored_smoke_requires_complete_literal_storage_evidence(field, value):
    observed = monitored_evidence()
    observed["storage"][field] = value
    assert assess_smoke(observed, [{"present": False}], storage_mode="monitored")["storage_monitor"] is False


@pytest.mark.parametrize("cleanup", [[], [{"present": True}], [{"present": None}]])
def test_monitored_storage_proof_requires_observed_cleanup(cleanup):
    assert assess_smoke(monitored_evidence(), cleanup, storage_mode="monitored")["storage_monitor"] is False


def test_quota_rejection_alone_cannot_pass_monitored_storage_smoke():
    assert assess_smoke(evidence(), [{"present": False}], storage_mode="monitored")["storage_monitor"] is False
