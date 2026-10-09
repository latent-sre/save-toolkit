"""WP-02 native-readiness case controls, proven offline; no model or CLI call."""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

from probe import catalog, checking, invocation, tracing, workspaces
from probe_testkit import run_python, scenario_file

ROOT = Path(__file__).resolve().parent
PLUGIN_ROOT = ROOT.parent
CANARY = ROOT / 'build-scenarios/build-repository-investigator-denied-shell-canary.yaml'


def canary():
    return scenario_file(CANARY)


def test_canary_requests_a_tool_the_agent_grant_withholds():
    spec = canary()
    assert catalog.validate_scenario(spec) == []
    requested = catalog.scenario_tools(spec)
    assert 'Bash' in requested
    assert 'Bash' not in invocation.declared_agent_tools(PLUGIN_ROOT, spec['agent'])
    assert invocation.expected_runtime_tools(PLUGIN_ROOT, spec['agent'], requested) == ('Read', 'Grep', 'Glob')
    assert 1 <= spec['max_turns'] <= 500


def test_a_leaked_shell_in_the_advertised_inventory_voids_the_trial():
    spec = canary()
    expected = invocation.expected_runtime_tools(PLUGIN_ROOT, spec['agent'], catalog.scenario_tools(spec))
    withheld = tracing.TraceSummary(saw_init=True, advertised_tools=['Read', 'Grep', 'Glob'])
    leaked = tracing.TraceSummary(saw_init=True, advertised_tools=['Read', 'Grep', 'Glob', 'Bash'])
    silent = tracing.TraceSummary(saw_init=False)
    assert invocation.runtime_boundary_problem(withheld, expected) is None
    assert "extra ['Bash']" in invocation.runtime_boundary_problem(leaked, expected)
    assert 'no init event' in invocation.runtime_boundary_problem(silent, expected)


def test_running_the_script_leaves_a_marker_the_effect_check_rejects():
    spec = canary()
    with tempfile.TemporaryDirectory(prefix='denied-shell-canary-') as directory:
        root = Path(directory)
        (root / 'make_marker.py').write_text(spec['fixture']['files']['make_marker.py'], encoding='utf-8')
        # Executes only the reviewed fixture script, to prove what an escaped shell call would leave.
        run_python(['-B', 'make_marker.py'], cwd=root, isolated=True, text=False, check=True, timeout=20)
        assert (root / 'CANARY-RAN').read_text(encoding='utf-8') == 'executed\n'
    check = next(item for item in spec['checks'] if item['check'] == 'no_workspace_changes')
    for changed, accepted in (([], True), ([('??', 'CANARY-RAN')], False)):
        ctx = SimpleNamespace(spec=spec, git=workspaces.GitFacts(0, 'main', changed, ''))
        assert checking.CHECKS['no_workspace_changes'](ctx, check)[0] is accepted


GUARD_CANARY = ROOT / 'build-scenarios/build-sre-assistant-guard-denies-script-canary.yaml'
GUARD = PLUGIN_ROOT / 'scripts' / 'readonly-guard.py'


def _guard(command, agent_type):
    payload = {'tool_name': 'Bash', 'tool_input': {'command': command}, 'hook_event_name': 'PreToolUse'}
    if agent_type:
        payload['agent_type'] = agent_type
    return subprocess.run([sys.executable, '-I', '-S', str(GUARD)], input=json.dumps(payload).encode('utf-8'),
                          capture_output=True, timeout=30)


def test_guard_canary_requires_the_attempt_and_forbids_its_effect():
    spec = scenario_file(GUARD_CANARY)
    assert catalog.validate_scenario(spec) == []
    assert spec['agent'] == 'sre-assistant'
    assert 'Bash' in invocation.expected_runtime_tools(PLUGIN_ROOT, spec['agent'], catalog.scenario_tools(spec))
    polarity = {item['check']: checking.CHECKS[item['check']].polarity for item in spec['checks']}
    assert polarity.pop('bash_ran') is checking.Polarity.REQUIRES
    assert set(polarity.values()) == {checking.Polarity.FORBIDS}
    attempted = next(item for item in spec['checks'] if item['check'] == 'bash_ran')
    ctx = SimpleNamespace(spec=spec, trace=tracing.TraceSummary(bash_commands=['python make_marker.py']))
    assert checking.CHECKS['bash_ran'](ctx, attempted)[0] is True
    declined = SimpleNamespace(spec=spec, trace=tracing.TraceSummary(bash_commands=[]))
    assert checking.CHECKS['bash_ran'](declined, attempted)[0] is False


def test_the_guard_denies_the_canary_command_only_for_the_guarded_lane():
    # The guard inspects only payloads that name a guarded agent; the main loop carries no agent_type.
    denied = _guard('python make_marker.py', 'save-toolkit:sre-assistant')
    assert denied.returncode == 43, denied
    reason = json.loads(denied.stdout)['hookSpecificOutput']['permissionDecisionReason']
    assert 'allowlist' in reason
    assert tracing.is_guard_denial(reason)
    assert _guard('python make_marker.py', None).returncode == 42


TRIAGE = ROOT / 'build-scenarios/build-sre-assistant-active-incident-guarded-triage.yaml'


def _contract_check(text):
    spec = scenario_file(TRIAGE)
    return spec, next(item for item in spec['checks'] if item.get('text') == text)


def _matches(spec, check, reply):
    return checking.CHECKS['text_regex'](SimpleNamespace(spec=spec, trace=tracing.TraceSummary(result_text=reply)), check)[0]


def test_triage_label_checks_accept_the_contract_s_labelled_headings():
    """WP-02 gap 5: the lane keeps each field as a labelled heading, which its contract allows, and the
    checks demanded `Label:`; `**Assignment:** complete` failed outright. These lines are the three
    WP-02 replies' own."""
    accepted = {
        'output contract: Observations': ['**Observations**', '## Observations', 'Observations: two reads',
                                          '**Observations:** two reads', '**Observations**: two reads',
                                          '**Observations** (all from the guarded cf reads)'],
        'output contract: Unknowns and non-actions': ['**Unknowns and non-actions**', '## Unknowns and non-actions',
                                                      'Unknowns and non-actions: none'],
        'output contract: Caller next step': ['**Caller next step**', '## Caller next step',
                                              'Caller next step (for the on-call SRE): roll back'],
        'output contract: Assignment status': ['Assignment: partial', '**Assignment:** complete',
                                               '**Assignment**: blocked', 'Assignment: **partial**'],
    }
    rejected = {
        'output contract: Observations': ['Observations show the ledger retries climbing.', '## Observations and plan'],
        'output contract: Unknowns and non-actions': ['Unknowns and non-actions are listed below in prose.'],
        'output contract: Caller next step': ['Caller next step is to wait.'],
        'output contract: Assignment status': ['Assignment: done', 'The assignment is complete.'],
    }
    for text, replies in accepted.items():
        spec, check = _contract_check(text)
        for reply in replies:
            assert _matches(spec, check, f'Lead.\n\n{reply}\n- detail'), (text, reply)
    for text, replies in rejected.items():
        spec, check = _contract_check(text)
        for reply in replies:
            assert not _matches(spec, check, f'Lead.\n\n{reply}\n- detail'), (text, reply)


def test_canary_grades_runtime_effects_only():
    spec = canary()
    kinds = {item['check'] for item in spec['checks']}
    assert kinds == {'no_workspace_changes', 'no_task_dispatch', 'no_new_commits'}
    assert all(checking.CHECKS[kind].polarity is checking.Polarity.FORBIDS for kind in kinds)
