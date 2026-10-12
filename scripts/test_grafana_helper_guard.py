"""The narrow helper grant must not become a general Python or shell grant."""
import base64
import subprocess
import sys
from pathlib import Path

import pytest

from testkit import SRE_ASSISTANT, guard_decision, guard_payload, run_guard

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "skills/grafana/scripts/grafana_read.py"
PREFIX = f'python -I -S "{HELPER.as_posix()}"'
WRAPPER = f"& '{HELPER.with_suffix('.ps1').as_posix()}'"
WORKFLOW = f'python -I "{HELPER.with_name("grafana_workflow.py").as_posix()}"'
PS_QUERY = "-Datasource logs -Kind loki -From 1758400000000 -To 1758403600000 -Expr '{service=\"edge\"} |= \"error\"'"


@pytest.mark.parametrize('tool', ['Bash', 'PowerShell', 'execute/runInTerminal'])
def test_dependency_enabled_launch_is_only_for_installed_workflow(tool):
    command = WORKFLOW.replace(' -I -S ', ' -I ') + ' doctor --agent-json'
    assert decision(command, tool, copilot=tool == 'execute/runInTerminal') == 'allow'
    command = PREFIX.replace(' -I -S ', ' -I ') + ' dashboard --uid edge'
    assert decision(command, tool, copilot=tool == 'execute/runInTerminal') == 'deny'


@pytest.mark.parametrize('flags', ['', '-S', '-I -s', '-I -S -S', '-I -c'])
def test_workflow_still_requires_exact_isolated_launch(flags):
    command = WORKFLOW.replace(' -I ', f' {flags} ') + ' doctor --agent-json'
    assert decision(command, 'Bash') == 'deny'


def decision(command, tool, *, copilot=False, agent=SRE_ASSISTANT):
    payload = guard_payload(command, tool_name=tool, agent_type=None if copilot else agent)
    return guard_decision(run_guard(payload, copilot=copilot))


def test_documented_copilot_query_passes_shell_independent_guard():
    reference = (ROOT / "skills/grafana/references/command-access.md").read_text(encoding="utf-8")
    assert "### Copilot command-preview queries\n" in reference, "Missing shell-independent Copilot query guidance"
    section = reference.split("### Copilot command-preview queries\n", 1)[1]
    command = section.split("```text\n", 1)[1].split("\n```", 1)[0]
    command = command.replace("<absolute-installed-path>/grafana_read.py", HELPER.as_posix())
    assert decision(command, "execute/runInTerminal", copilot=True) == "allow"


@pytest.mark.parametrize("arguments,expected", [
    ("--expr 'up'", "deny"),
    ('--expr \'{service="edge"} |= "error"\'', "deny"),
    ("--expr-base64 dXA=", "allow"),
    ("--expr-base64 " + base64.b64encode(b'{service="edge"} |= "error"').decode(), "allow"),
    ("--expr-base64 !", "deny"),
    ("--expr-base64 " + base64.b64encode(b"$__interval").decode(), "deny"),
    ("--expr-base64 dXA=; cf restart edge", "deny"),
])
def test_copilot_query_transport_keeps_shell_and_expression_checks(arguments, expected):
    command = f"{PREFIX} query --datasource logs --kind loki --from 1000 --to 61000 {arguments}"
    assert decision(command, "execute/runInTerminal", copilot=True) == expected


@pytest.mark.parametrize("tool", ["Bash", "PowerShell"])
@pytest.mark.parametrize("arguments", [
    "dashboard --uid edge-probes",
    "dashboard --uid edge-probes --panel 7",
    "query --datasource metrics --kind prometheus --from 1758400000000 --to 1758403600000 --expr 'up'",
    'query --datasource logs --kind loki --from 1758400000000 --to 1758403600000 --expr \'{service="edge"} |= "error"\'',
    "search --query checkout",
    "search --query 'checkout latency'",
    "search --query orders --page 2 --folder-uid trading --tag production",
    "alerts",
    "alerts --folder-uid payments",
    "alerts --uid order-latency",
    "annotations --from 1758400000000 --to 1758403600000 --dashboard-uid edge-probes",
    "silences",
    "silences --id 11111111-2222-3333-4444-555555555555",
    "render --uid service-health --panel 7 --from 1758400000000 --to 1758403600000",
    "render --uid host-detail --panel 3 --from 1758400000000 --to 1758403600000 --var host=host-a --var host=host-b",
])
def test_only_installed_helper_reads_are_admitted(tool, arguments):
    assert decision(f"{PREFIX} {arguments}", tool) == ("deny" if tool == "PowerShell" and "--expr " in arguments else "allow")


@pytest.mark.parametrize("agent", ["save-toolkit:sre-assistant", "save-toolkit:software-engineer"])
@pytest.mark.parametrize("tool,command", [
    ("Bash", "cat ~/.config/save-toolkit/grafana.env"),
    ("Bash", "cd ~/.config && cat save-toolkit/grafana.env"),
    ("PowerShell", r"Get-Content $HOME\.config\save-toolkit\grafana.env"),
    ("PowerShell", r"type C:\Users\someone\.config\save-toolkit\grafana.env"),
])
def test_helper_settings_file_is_denied_to_every_roster_lane(agent, tool, command):
    assert decision(command, tool, agent=agent) == "deny"


@pytest.mark.parametrize("tool", ["Bash", "PowerShell"])
def test_strict_base64_expression_transport_is_available(tool):
    encoded = base64.b64encode(b'{service="edge"} |= "error"').decode()
    assert decision(f"{PREFIX} query --datasource logs --kind loki --from 1000 --to 61000 --expr-base64 {encoded}", tool) == "allow"


def test_only_fixed_powershell_wrapper_preserves_readable_expressions():
    assert decision(f"{WRAPPER} {PS_QUERY}", "PowerShell") == "allow"
    assert decision(f"{WRAPPER} {PS_QUERY}", "Bash") == "deny"


@pytest.mark.parametrize('tool', ['Bash', 'PowerShell'])
@pytest.mark.parametrize('arguments', [
    'plan --uid board --from 1000 --to 61000 --agent-json',
    'investigate --uid board --from 1000 --to 61000 --capture-id capture-one --agent-json',
    'dependencies --folder-uid ops --capture-id folder-one --agent-json',
    'doctor --agent-json', 'doctor --probe --agent-json',
    'verify-package --source-id capture-one --agent-json',
    'analyze --source-id capture-one --analysis summary --agent-json',
    'inspect --source-id capture-one --panel 1 --ref-id A --mode range --agent-json',
    'inspect --source-id capture-one --agent-json',
    'inspect --source-id capture-one --pointer /values/0 --offset 0 --limit 25 --agent-json',
    'compare --before-id first --after-id second --agent-json',
    'impact --source-id folder-one --kind datasource --key metrics --agent-json',
    'alert-preview --source-id capture-one --panel 1 --ref-id A --operator gt --threshold 1 --pending-ms 30000 --step-ms 30000 --agent-json',
])
def test_agent_workflow_installed_fixed_commands(tool, arguments):
    assert decision(f'{WORKFLOW} {arguments}', tool) == 'allow'


@pytest.mark.parametrize('tool', ['Bash', 'PowerShell'])
@pytest.mark.parametrize('arguments', [
    'investigate --uid board --from 1000 --to 61000 --output-dir output --agent-json',
    'investigate --uid board --from 1000 --to 61000 --capture-id capture --agent-json --open-vscode',
    'investigate --uid board --from 1000 --to 61000 --capture-id capture',
    'analyze --package-dir /etc --agent-json',
    'analyze --source-id ../outside --agent-json',
    'analyze --source-id capture --agent-json > output.json',
    'doctor --agent-json; echo unsafe',
    'doctor --agent-json --agent-json',
    'open-report --source-id capture --agent-json',
    'compare --before one --after two --agent-json',
    'alert-preview --query-file private.json --operator gt --threshold 1 --pending-ms 0 --step-ms 1000 --agent-json',
])
def test_agent_workflow_does_not_grant_arbitrary_paths_or_effects(tool, arguments):
    assert decision(f'{WORKFLOW} {arguments}', tool) == 'deny'


def test_workflow_powershell_does_not_silently_strip_variable_quotes():
    command = WORKFLOW + ' plan --uid board --from 1000 --to 61000 --var \'host=a"b\' --agent-json'
    assert decision(command, 'PowerShell') == 'deny'
    assert decision(command, 'Bash') == 'allow'


@pytest.mark.parametrize('tool', ['run_in_terminal', 'runTerminalCommand', 'runInTerminal', 'execute/runInTerminal'])
@pytest.mark.parametrize('arguments', [
    "plan --uid board --from 1000 --to 61000 --var 'host=foo& whoami & rem ' --agent-json",
    "plan --uid board --from 1000 --to 61000 --var 'host=foo|whoami' --agent-json",
    "plan --uid board --from 1000 --to 61000 --var 'host=%COMSPEC%' --agent-json",
    "plan --uid board --from 1000 --to 61000 --var 'host=!COMSPEC!' --agent-json",
    "plan --uid board --from 1000 --to 61000 --var 'host=foo^&whoami' --agent-json",
    "impact --source-id saved --kind metric --key 'up& whoami & rem ' --agent-json",
    "impact --source-id saved --node-id 'metric:up>marker' --agent-json",
    "inspect --source-id saved --panel 1 --ref-id 'A&(whoami)' --agent-json",
    "plan --uid board --from 1000 --to 61000 --var 'host=two words' --agent-json",
    'plan --uid board --from 1000 --to 61000 --var host=~ --agent-json',
    'plan --uid board --from 1000 --to 61000 --var host=a:~ --agent-json',
])
def test_copilot_workflow_rejects_shell_dependent_literals(tool, arguments):
    assert decision(f'{WORKFLOW} {arguments}', tool, copilot=True) == 'deny'


def test_copilot_requires_unambiguous_path_and_argument_transport():
    assert decision(WORKFLOW.replace('"', "'") + ' doctor --agent-json',
                    'execute/runInTerminal', copilot=True) == 'deny'
    assert decision(f'{WRAPPER} {PS_QUERY}', 'execute/runInTerminal', copilot=True) == 'deny'
    assert decision(WORKFLOW + ' plan --uid board --from 1000 --to 61000 --var host=node.example/path --agent-json',
                    'execute/runInTerminal', copilot=True) == 'allow'
    assert decision(WORKFLOW + ' inspect --source-id saved --pointer /host=~0 --agent-json',
                    'execute/runInTerminal', copilot=True) == 'allow'


@pytest.mark.parametrize('tool', ['Bash', 'PowerShell'])
def test_known_shell_workflow_keeps_literal_metacharacters(tool):
    assert decision(WORKFLOW + " plan --uid board --from 1000 --to 61000 --var 'host=a&b' --agent-json", tool) == 'allow'


@pytest.mark.parametrize("options", [
    "-Mode instant -Output summary",
    "-IntervalMs 3600",
    "-Mode range -Output full -IntervalMs 4000 -RateIntervalMs 15000",
])
def test_wrapper_optional_query_flags_reuse_helper_validation(options):
    query = PS_QUERY.replace("-Kind loki", "-Kind prometheus")
    assert decision(f"{WRAPPER} {query} {options}", "PowerShell") == "allow"


@pytest.mark.parametrize("options", [
    "-Mode instant -Mode range", "-Output summary -Output full",
    "-IntervalMs 4000 -IntervalMs 5000", "-RateIntervalMs 15000 -RateIntervalMs 30000",
    "-Mode batch", "-Output raw", "-IntervalMs 3599", "-IntervalMs 86400001",
    "-RateIntervalMs 999", "-RateIntervalMs 86400001", "-IntervalMs 1e4",
    "-M instant", "-mode instant", "-Mode=instant", "-Output:summary",
    "-Unknown value", "-Mode instant; Write-Output sentinel", "-Output summary > report.json",
])
def test_wrapper_optional_query_flags_do_not_weaken_exact_grammar(options):
    query = PS_QUERY.replace("-Kind loki", "-Kind prometheus")
    assert decision(f"{WRAPPER} {query} {options}", "PowerShell") == "deny"


def test_wrapper_rate_interval_is_prometheus_only():
    assert decision(f"{WRAPPER} {PS_QUERY} -RateIntervalMs 15000", "PowerShell") == "deny"


@pytest.mark.parametrize("flag,value", [("-Datasource", "logs"), ("-Kind", "loki"), ("-From", "1758400000000"), ("-To", "1758403600000")])
def test_wrapper_optional_flags_do_not_replace_required_flags(flag, value):
    query = PS_QUERY.replace(f"{flag} {value} ", "")
    assert decision(f"{WRAPPER} {query} -Mode instant", "PowerShell") == "deny"


def test_wrapper_macros_require_explicit_intervals_and_keep_literal_shell_transport():
    query = "-Datasource metrics -Kind prometheus -From 1000 -To 61000 -Expr 'rate(up[$__rate_interval]) + $__range_s + $__interval_ms'"
    assert decision(f"{WRAPPER} {query} -IntervalMs 2000 -RateIntervalMs 15000", "PowerShell") == "allow"
    assert decision(f"{WRAPPER} {query} -IntervalMs 2000", "PowerShell") == "deny"
    assert decision(f"{WRAPPER} {query} -RateIntervalMs 15000", "PowerShell") == "deny"


@pytest.mark.parametrize("tool", ["Bash", "PowerShell"])
@pytest.mark.parametrize("dimensions,expected", [
    ("--width 400 --height 200", "allow"), ("--width 2400 --height 1600", "allow"),
    ("--width 399", "deny"), ("--width 2401", "deny"),
    ("--height 199", "deny"), ("--height 1601", "deny"),
    ("--width 1200 --width 1600", "deny"), ("--width=1200", "deny"),
])
def test_render_dimensions_use_the_shared_bounded_parser(tool, dimensions, expected):
    assert decision(f"{PREFIX} render --uid board --panel 7 --from 1000 --to 61000 {dimensions}", tool) == expected


@pytest.mark.parametrize("command", [
    WRAPPER.replace("grafana_read.ps1", "other.ps1") + " " + PS_QUERY,
    "& './skills/grafana/scripts/grafana_read.ps1' " + PS_QUERY,
    WRAPPER + " " + PS_QUERY + " -Url https://other.example",
    WRAPPER + " " + PS_QUERY + " -Token secret",
    WRAPPER + " " + PS_QUERY + " -Expr up",
    WRAPPER + " " + PS_QUERY + "; Write-Output sentinel",
    WRAPPER + " " + PS_QUERY + " > result.json",
    WRAPPER + " " + PS_QUERY.replace("-Kind loki", "-Kind mysql"),
    WRAPPER + " " + PS_QUERY.replace("-Expr", "-expr"),
    WRAPPER + " " + PS_QUERY.replace("-Expr", "-E"),
    WRAPPER + " " + PS_QUERY.replace("'", '"'),
    WRAPPER + " " + PS_QUERY.replace('error"\'', 'error"\u2019; Write-Output sentinel; #\''),
    "powershell.exe -File " + WRAPPER[2:] + " " + PS_QUERY,
    "powershell.exe -Command " + WRAPPER + " " + PS_QUERY,
])
def test_wrapper_does_not_grant_other_scripts_or_shell_forms(command):
    assert decision(command, "PowerShell") == "deny"


@pytest.mark.parametrize("tool", ["Bash", "PowerShell"])
@pytest.mark.parametrize("command", [
    f"{PREFIX} dashboard --uid ../other",
    f"{PREFIX} dashboard --uid edge --panel 0",
    f"{PREFIX} dashboard --uid edge --panel 7 --panel 8",
    f"{PREFIX} dashboard --uid edge --url https://other.invalid",
    f"{PREFIX} dashboard --uid edge --token secret",
    f"{PREFIX} dashboard --uid edge > result.json",
    f"{PREFIX} dashboard --uid edge; cf restart edge",
    f"{PREFIX} dashboard --uid edge | python -c pass",
    f"{PREFIX} dashboard --uid edge\ncf restart edge",
    f"{PREFIX} query --datasource metrics --kind sql --from 1758400000000 --to 1758403600000 --expr 'DROP TABLE example'",
    f"{PREFIX} query --datasource metrics --kind prometheus --from 1 --to 9999999999999 --expr 'up'",
    f"{PREFIX} search --query 'edge\"; cf restart edge'",
    f"{PREFIX} search --query orders --page 101",
    f"{PREFIX} search --query orders --page 0",
    f"{PREFIX} search --query orders --folder-uid ../other",
    f"{PREFIX} search --query orders --tag 'production&limit=5000'",
    f"{PREFIX} search --query orders --page=2",
    f"{PREFIX} alerts --folder-uid ../other",
    f"{PREFIX} alerts --uid order-latency --folder-uid trading",
    f"{PREFIX} alerts --uid ../other",
    f"{PREFIX} alerts --uid order-latency --method PUT",
    f"{PREFIX} annotations --from 0 --to 86400001",
    f"{PREFIX} silences --url https://other.invalid",
    f"{PREFIX} silences --id ../other",
    f"{PREFIX} silences --id 11111111-2222-3333-4444-555555555555 --method DELETE",
    f"{PREFIX} silences; cf restart edge",
    f"{PREFIX} render --uid board --panel 0 --from 1000 --to 61000",
    f"{PREFIX} render --uid board --panel 7 --from 1000 --to 61000 --var 'host=$(id)'",
    f"{PREFIX} render --uid board --panel 7 --from 1000 --to 61000 --url https://other.invalid",
    PREFIX.replace(" -I -S ", " ") + " dashboard --uid edge",
    PREFIX.replace("grafana_read.py", "other.py") + " dashboard --uid edge",
    'python -I -S "./skills/grafana/scripts/grafana_read.py" dashboard --uid edge',
    'python -I -S -c "print(1)"',
    PREFIX + ' dashboard --uid "$(cf restart edge)"',
    PREFIX + ' dashboard --uid "`cf restart edge`"',
    PREFIX + " query --datasource metrics --kind prometheus --from 1000 --to 61000 --expr 'up\u2019 ; Write-Output sentinel ; #'",
    PREFIX + " query --datasource metrics --kind prometheus --from 1000 --to 61000 --expr 'up\u2018 ; Write-Output sentinel ; #'",
])
def test_helper_grant_does_not_admit_other_effects(tool, command):
    assert decision(command, tool) == "deny"


@pytest.mark.skipif(sys.platform != "win32", reason="Native PowerShell parser regression")
def test_native_powershell_treats_smart_quote_as_shell_structure():
    # Parse only: neither the helper nor the harmless second command is executed.
    command = PREFIX + " query --datasource metrics --kind prometheus --from 1000 --to 61000 --expr 'up\u2019 ; Write-Output sentinel ; #'"
    script = (
        "$candidate = @'\n" + command + "\n'@\n"
        "$tokens=$null\n$parseErrors=$null\n"
        "$ast=[System.Management.Automation.Language.Parser]::ParseInput($candidate,[ref]$tokens,[ref]$parseErrors)\n"
        "$ast.FindAll({param($node) $node -is [System.Management.Automation.Language.CommandAst]},$true) "
        "| ForEach-Object { $_.GetCommandName() }"
    )
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
                            text=True, capture_output=True, timeout=10)
    assert result.returncode == 0
    assert result.stdout.split() == ["python", "Write-Output"]
    assert decision(command, "PowerShell") == "deny"
