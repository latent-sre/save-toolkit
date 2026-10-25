"""Real optional Harbor SDK contracts; only Docker/model boundaries are doubled."""
# ruff: noqa: E402
import asyncio
import json
import subprocess
from pathlib import Path

import pytest
from campaign_report import build_report
from harbor_adapter import runner, transfer
from harbor_adapter.contracts import load_manifest
from probe import fingerprints
from swebench_adapter import artifacts, configuration

harbor = pytest.importorskip('harbor', reason='optional pinned Harbor environment required')

from harbor.agents.factory import AgentFactory
from harbor.models.agent.context import AgentContext
from harbor.models.task.task import Task
from harbor.models.trial.config import AgentConfig
from harbor.models.trial.paths import TrialPaths
from harbor_adapter.sdk import FleetAgent, FleetEnvironment, verify_task
from swebench_adapter.containers import Docker, DockerResources, Execution


class BoundaryDocker(Docker):
    def __init__(self):
        super().__init__()
        self.calls = []

    def call(self, args, **kwargs):
        self.calls.append(args)
        if args[:2] == ['container', 'inspect']:
            return subprocess.CompletedProcess(args, 1, b'', b'No such container: test')
        return subprocess.CompletedProcess(args, 0, b'[]', b'')


@pytest.fixture
def task(tmp_path):
    root = tmp_path / 'task'
    for name in ('environment', 'tests', 'solution'):
        (root / name).mkdir(parents=True)
    (root / 'instruction.md').write_text('Author /app/run.py without running it.')
    (root / 'task.toml').write_text('version = "1.0"\n[metadata]\n[agent]\ntimeout_sec=30\n[verifier]\ntimeout_sec=30\n[environment]\ncpus=1\nmemory_mb=128\nstorage_mb=10\n')
    (root / 'environment/Dockerfile').write_text('FROM scratch\n')
    (root / 'tests/test.sh').write_text('#!/bin/sh\necho 1 > /logs/verifier/reward.txt\n')
    return Task(root)


@pytest.fixture
def environment(task, tmp_path):
    resources = DockerResources(BoundaryDocker(), 'test')
    name = resources._own('verifier')
    paths = TrialPaths(tmp_path / 'trial')
    paths.trial_dir.mkdir()
    return FleetEnvironment(resources=resources, container=name, role='verifier', task=task,
                            trial_paths=paths, wall_seconds=30)


def test_real_custom_agent_contract():
    assert FleetAgent.__abstractmethods__ == frozenset()
    assert FleetEnvironment.__abstractmethods__ == frozenset()
    agent = FleetAgent(logs_dir=Path('/unused'), model_name='anthropic/model')
    assert agent.to_agent_info().model_info.name == 'model'
    assert FleetAgent.import_path() == 'harbor_adapter.sdk:FleetAgent'
    # Real factory import path resolution, without constructing providers or models.
    assert AgentFactory.get_agent_class_from_config(AgentConfig(import_path='harbor_adapter.sdk:FleetAgent')) is FleetAgent


@pytest.mark.parametrize(('reward', 'verdict'), [('1', 'PASS'), ('0', 'FAIL'), ('nan', 'INCONCLUSIVE'), (None, 'INCONCLUSIVE')])
def test_actual_verifier_method(task, environment, monkeypatch, reward, verdict):
    events = []
    def execute(container, argv, **kwargs):
        events.append(('exec', argv))
        return Execution(b'verifier output', b'', 0, None, 0.01)
    monkeypatch.setattr(environment.resources, 'execute', execute)
    async def download(source_dir, target_dir):
        events.append(('download', source_dir))
        target_dir.mkdir(parents=True, exist_ok=True)
        if reward is not None:
            (target_dir / 'reward.txt').write_text(reward)
    monkeypatch.setattr(environment, 'download_dir', download)
    receipt = asyncio.run(verify_task(task, environment, environment.trial_paths, submission_script=False))
    assert receipt['assessment']['verdict'] == verdict
    assert receipt['execution_actor'] == 'independent-verifier'
    assert any(args[0] == 'cp' and args[-1].endswith(':/tests') for args in environment.resources.docker.calls)
    assert any('/tests/test.sh' in event[1][-1] for event in events if event[0] == 'exec')
    if verdict != 'INCONCLUSIVE':
        assert receipt['native_result']['rewards']['reward'] == int(reward)
        receipt['cleanup'] = 'failed'
        assert receipt['assessment']['verdict'] == verdict
    else:
        assert receipt['native_result'] is None


def test_hidden_upload_and_generic_exec_block_author(environment):
    environment.role = 'author'
    with pytest.raises(ValueError, match='independent verifier'):
        asyncio.run(environment.exec('python /app/run.py'))
    with pytest.raises(ValueError, match='independent verifier'):
        asyncio.run(environment.upload_dir(environment.environment_dir, '/tests'))


def test_default_harbor_environment_not_admitted(tmp_path):
    agent = FleetAgent(logs_dir=tmp_path)
    with pytest.raises(ValueError, match='not admitted'):
        asyncio.run(agent.setup(object()))


def test_native_invocation_and_trace(environment, monkeypatch, tmp_path):
    environment.role = 'author'
    environment.config = {'model': 'anthropic/model'}
    commands = []
    trace = '\n'.join(json.dumps(x) for x in [
        {'type':'system','subtype':'init','session_id':'native-1','model':'model','tools':['Read','Write'], 'plugins':[{'name':'save-toolkit','path':'/opt/fleet'}]},
        {'type':'result','subtype':'success','is_error':False,'result':'authored','session_id':'native-1','num_turns':2, 'total_cost_usd':0.1},
    ])
    def execute(container, argv, **kwargs):
        commands.append((argv, kwargs))
        return Execution(trace.encode(), b'', 0, None, .1)
    monkeypatch.setattr(environment.resources, 'execute', execute)
    agent = FleetAgent(logs_dir=tmp_path / 'agent', model_name='anthropic/model')
    context = AgentContext()
    asyncio.run(agent.run('task', environment, context))
    assert '--agent save-toolkit:software-engineer' in commands[0][0][-1]
    assert '--plugin-dir /opt/fleet' in commands[0][0][-1]
    assert '--max-turns 64' in commands[0][0][-1]
    assert commands[0][1]['storage_quota'] is True
    assert context.metadata['session_id'] == 'native-1'
    assert context.metadata['policy_review'] == 'unmeasured'


def test_cumulative_actor_deadline(environment, monkeypatch):
    environment.deadline = 0
    with pytest.raises(TimeoutError, match='deadline'):
        asyncio.run(environment.exec('true'))


def test_native_output_secret_rejected_before_persistence(environment, monkeypatch, tmp_path):
    environment.role = 'author'
    environment.config = {'model': 'anthropic/model'}
    environment.sensitive = ('private-token-fixture',)
    monkeypatch.setattr(environment.resources, 'execute', lambda *a, **kw: Execution(b'private-token-fixture', b'', 0, None, .1))
    with pytest.raises(ValueError, match='credential'):
        asyncio.run(environment.author('task', tmp_path / 'secret-output'))
    assert not (tmp_path / 'secret-output').exists()


@pytest.mark.parametrize('late_failure', [None, 'billing', 'cleanup', 'incomplete', 'author_error', 'process_error', 'auth'])
def test_owned_lifecycle_uses_real_sdk_and_preserves_results(task, tmp_path, monkeypatch, late_failure):

    manifest = load_manifest(Path(__file__).parent / 'manifests/wp09-terminal-complex5.json')
    case = manifest['cases'][0]
    plugin = tmp_path / 'plugin'
    plugin.mkdir()
    cli = tmp_path / 'cli'
    cli.write_bytes(b'fixture-cli')
    config = {'plugin_root':str(plugin),'cli_path':str(cli),'cli_version':'fixture-cli-v1',
              'model':'anthropic/model','haiku_model':'anthropic/helper', 'proxy_bind':'127.0.0.1',
              'proxy_target':'host.docker.internal','storage_quota':True}
    bound = {'plugin_sha256':None,'cli_sha256':runner.sha256(cli),
             'selection_sha256':runner.canonical_digest(manifest), 'cli_version':config['cli_version'], 'model':config['model'],
             'images':{case['local_case_id']:{'image_id':'sha256:'+'a'*64}},
             'harbor_adapter_sha256':'a'*64, 'adapter_sha256':'b'*64,
             'host_runtime':{'platform':{'system':'Linux'},'identity':{
                 'hostname':'host','account_id':'1000','elevated':False,'identity_source':'posix_effective_uid'}}}
    monkeypatch.setattr(configuration, 'load_config', lambda p: config)
    monkeypatch.setattr(runner, 'binding', lambda *a: bound)
    monkeypatch.setattr(runner, 'admit', lambda *a, **kw: None)
    monkeypatch.setattr(runner, 'read_json', lambda p: {})
    monkeypatch.setattr(runner, 'verify_source', lambda *a: task.paths.task_dir)
    monkeypatch.setattr(runner, 'image_identity', lambda *a: 'sha256:'+'a'*64)
    monkeypatch.setattr(fingerprints, 'plugin_digest', lambda p: None)
    def stage_plugin(src, dst):
        dst.mkdir()
        return dst
    monkeypatch.setattr(fingerprints, 'stage_plugin', stage_plugin)
    monkeypatch.setattr(fingerprints, 'plugin_provenance', lambda p: {'plugin_root':str(p), 'plugin_commit':None,
                                                                   'plugin_inputs_dirty':None, 'plugin_source_sha256':None})
    monkeypatch.setattr(fingerprints, 'runner_provenance', lambda: {'runner_commit':None,'runner_source_dirty':None,'runner_source_sha256':None})
    monkeypatch.setattr(runner, 'read_key', lambda p: 'fake-secret')
    monkeypatch.setattr(artifacts, 'runtime_problem', lambda *a: None)
    monkeypatch.setattr(runner.invocation, 'expected_runtime_tools', lambda *a: ('Read',))
    class Proxy:
        port = 12345
        auth_failed = late_failure == 'auth'
        def __init__(self, *a, **kw): self.count = 0
        def start(self): pass
        def close(self): pass
        def usage(self):
            self.count += 1
            if self.count > 1 and late_failure == 'billing':
                raise ValueError('unavailable')
            return {'usage': float(self.count), 'limit':30.0, 'limit_remaining':28.0}
    monkeypatch.setattr(runner, 'ModelProxy', Proxy)
    class LifecycleDocker(Docker):
        def __init__(self):
            super().__init__()
            self.events = []
            self.present = set()
        def call(self, args, **kwargs):
            self.events.append(args)
            if args[:2] in (['container','inspect'], ['network','inspect']):
                name = args[-1]
                return subprocess.CompletedProcess(args, 0 if name in self.present else 1,
                                                   b'[{}]' if name in self.present else b'',
                                                   b'' if name in self.present else ('No such object: '+name).encode())
            if args[:2] == ['network','create']:
                self.present.add(args[-1])
            if args[0] == 'run':
                self.present.add(args[args.index('--name')+1])
            if (args[0] == 'rm' or args[:2] == ['network','rm']) and late_failure != 'cleanup':
                self.present.discard(args[-1])
            if args[0] == 'inspect':
                return subprocess.CompletedProcess(args, 0, b'"172.30.0.2"', b'')
            if args[-1] == 'uname -s; uname -r; uname -m; id -u; hostname':
                return subprocess.CompletedProcess(args, 0, b'Linux\nfixture-kernel\nx86_64\n0\nfixture-container', b'')
            if args[-1] == '--version':
                return subprocess.CompletedProcess(args, 0, b'fixture-cli-v1', b'')
            return subprocess.CompletedProcess(args, 0, b'', b'')
    docker = LifecycleDocker()
    def execute(resources, container, argv, **kwargs):
        docker.events.append(['bounded-exec', container, *argv])
        trace = '\n'.join(json.dumps(x) for x in [
            {'type':'system','subtype':'init','session_id':'trial','model':'anthropic/model','tools':['Read']},
            {'type':'result','subtype':'success','is_error':False,'result':'done','session_id':'trial'},
        ])
        if late_failure == 'incomplete':
            trace = trace.splitlines()[0]
        if late_failure == 'author_error':
            trace = trace.replace('\"is_error\": false', '\"is_error\": true')
        return Execution(trace.encode() if '/opt/claude' in argv[-1] else b'', b'', 1 if late_failure == 'process_error' else 0, None, .01)
    monkeypatch.setattr(DockerResources, 'execute', execute)
    def collect(docker, container, source, destination):
        destination.mkdir(parents=True, exist_ok=True)
        (destination / ('run.py' if source == '/app' else 'reward.txt')).write_text('pass\n' if source == '/app' else '1')
        docker.events.append(['collect', container, source])
    monkeypatch.setattr(runner, 'collect_tree', collect)
    monkeypatch.setattr(transfer, 'collect_tree', collect)
    output = tmp_path / 'output'
    record = runner.run_trial(config_path=tmp_path/'config', manifest=manifest, case=case, source=tmp_path,
                              admission_path=tmp_path/'admission', key_file=tmp_path/'key', output=output,
                              label='candidate', docker=docker)
    if late_failure in {'incomplete','author_error','process_error','auth'}:
        assert record['verdict']['status'] == 'INCONCLUSIVE'
        assert not any(e[0] == 'collect' for e in docker.events)
        assert not (output/'harbor-pending.json').exists()
        return
    assert record['verdict']['status'] == 'PASS'
    run = output / ('eval-'+case['local_case_id']) / 'candidate/run-1'
    receipt = json.loads((run/'verification.json').read_text())
    assert receipt['native_result'] == {'rewards':{'reward':1.0}}
    assert json.loads((run/'verifier/verifier-receipt.json').read_text())['outcome'] == 'PASS'
    author_stop = next(i for i,e in enumerate(docker.events) if e[0] == 'stop')
    export = next(i for i,e in enumerate(docker.events) if e[0] == 'collect' and e[-1] == '/app')
    hidden_upload = next(i for i,e in enumerate(docker.events) if e[0] == 'cp' and e[-1].endswith(':/tests'))
    assert author_stop < export < hidden_upload
    verifier_run = next(e for e in docker.events if e[0] == 'run' and e[e.index('--name')+1].endswith('-verifier'))
    assert verifier_run[verifier_run.index('--network')+1] == 'none'
    assert '--storage-opt' in verifier_run
    assert bool((output/'harbor-pending.json').exists()) == (late_failure == 'cleanup')
    if late_failure:
        assert record['verdict']['after_assessment']
    report = build_report(output, manifest, 'candidate')
    attempt = report['cases'][case['local_case_id']]['slots'][0]['attempts'][0]
    assert attempt['valid'], attempt['problems']
    assert attempt['verdict']['status'] == 'PASS'
