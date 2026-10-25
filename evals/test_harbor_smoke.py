"""Derived smoke controls refuse missing evidence without the optional SDK."""
import copy

import pytest
from harbor_adapter.runner import CHECKS
from harbor_adapter.smoke import assess_smoke


@pytest.fixture
def observation():
    return {
        'reference':{'native_result':{'rewards':{'reward':1}},'execution_error':None,'assessment':{'verdict':'PASS'}},
        'empty':{'native_result':{'rewards':{'reward':0}},'execution_error':None,'assessment':{'verdict':'FAIL'}},
        'reference_returncode':0,
        'container':{'HostConfig':{'NanoCpus':2_000_000_000,'CapDrop':['ALL'],'CapAdd':[],
                                   'Privileged':False,'SecurityOpt':['no-new-privileges'],
                                   'Memory':2*1024**3,'PidsLimit':256},
                     'Mounts':[{'Destination':'/opt/claude','RW':False},{'Destination':'/opt/fleet','RW':False}]},
        'cpu':{'wall_seconds':5.0,'cpu_seconds':9.0},
        'network':{'Internal':True,'EnableIPv6':False,'Options':{'com.docker.network.bridge.gateway_mode_ipv4':'isolated'}},
        'egress':{'proxy':True,'internet':False,'host':False,'dns':False,'key_route':False},
        'storage':{'quota_rejected':True},
        'native_cli':True,'native_plugin':True,'hidden_separation':True,'source_inputs':True,'artifact_handoff':True,
        'missing_reward':{'verdict':'INCONCLUSIVE'},
    }


def test_complete_observations_and_unknowns(observation):
    assert set(assess_smoke(observation,[{'present':False}])) == set(CHECKS)
    assert all(assess_smoke(observation,[{'present':False}]).values())
    assert not any(assess_smoke({},[]).values())
    assert assess_smoke(observation,[{'present':None}])['cleanup'] is False


@pytest.mark.parametrize(('key','check'), [('reference','reference_pass'),('empty','empty_fail'),
    ('cpu','cpu_cap'),('network','egress'),('storage','storage_cap'),('native_cli','native_cli'),
    ('native_plugin','native_plugin'),('hidden_separation','hidden_separation'),
    ('artifact_handoff','artifact_handoff'),('missing_reward','missing_reward_inconclusive')])
def test_absent_observation_never_passes(observation,key,check):
    changed = copy.deepcopy(observation)
    del changed[key]
    assert assess_smoke(changed,[{'present':False}])[check] is False
