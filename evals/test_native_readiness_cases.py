"""WP-02 native-readiness case controls, proven offline; no model or CLI call."""

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


def test_canary_grades_runtime_effects_only():
    spec = canary()
    kinds = {item['check'] for item in spec['checks']}
    assert kinds == {'no_workspace_changes', 'no_task_dispatch', 'no_new_commits'}
    assert all(checking.CHECKS[kind].polarity is checking.Polarity.FORBIDS for kind in kinds)
