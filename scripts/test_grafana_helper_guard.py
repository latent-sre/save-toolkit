"""The narrow helper grant must not become a general Python or shell grant."""
import base64
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "skills/grafana/scripts/grafana_read.py"
GUARD = ROOT / "scripts/readonly-guard.py"
PREFIX = f'python -I -S "{HELPER.as_posix()}"'
WRAPPER = f"& '{HELPER.with_suffix('.ps1').as_posix()}'"
PS_QUERY = "-Datasource logs -Kind loki -From 1758400000000 -To 1758403600000 -Expr '{service=\"edge\"} |= \"error\"'"


def decision(command, tool, *, copilot=False):
    payload = {"tool_name": tool, "tool_input": {"command": command}}
    if not copilot:
        payload["agent_type"] = "save-toolkit:sre-assistant"
    result = subprocess.run(
        [sys.executable, "-I", "-S", str(GUARD), *(["--copilot"] if copilot else [])],
        input=json.dumps(payload),
        text=True, capture_output=True, timeout=10,
    )
    assert result.returncode in (42, 43), result.stderr
    return result.returncode


def test_documented_copilot_query_passes_shell_independent_guard():
    reference = (ROOT / "skills/grafana/references/command-access.md").read_text(encoding="utf-8")
    assert "### Copilot command-preview queries\n" in reference, "Missing shell-independent Copilot query guidance"
    section = reference.split("### Copilot command-preview queries\n", 1)[1]
    command = section.split("```text\n", 1)[1].split("\n```", 1)[0]
    command = command.replace("<absolute-installed-path>/grafana_read.py", HELPER.as_posix())
    assert decision(command, "execute/runInTerminal", copilot=True) == 42


@pytest.mark.parametrize("arguments,expected", [
    ("--expr 'up'", 43),
    ('--expr \'{service="edge"} |= "error"\'', 43),
    ("--expr-base64 dXA=", 42),
    ("--expr-base64 " + base64.b64encode(b'{service="edge"} |= "error"').decode(), 42),
    ("--expr-base64 !", 43),
    ("--expr-base64 " + base64.b64encode(b"$__interval").decode(), 43),
    ("--expr-base64 dXA=; cf restart edge", 43),
])
def test_copilot_query_transport_keeps_shell_and_expression_checks(arguments, expected):
    command = f"{PREFIX} query --datasource logs --kind loki --from 1000 --to 61000 {arguments}"
    assert decision(command, "execute/runInTerminal", copilot=True) == expected


@pytest.mark.parametrize("tool", ["Bash", "PowerShell"])
@pytest.mark.parametrize("arguments", [
    "dashboard --uid bsg-edge",
    "query --datasource metrics --kind prometheus --from 1758400000000 --to 1758403600000 --expr 'up'",
    'query --datasource logs --kind loki --from 1758400000000 --to 1758403600000 --expr \'{service="edge"} |= "error"\'',
])
def test_only_installed_helper_reads_are_admitted(tool, arguments):
    assert decision(f"{PREFIX} {arguments}", tool) == (43 if tool == "PowerShell" and "--expr " in arguments else 42)


@pytest.mark.parametrize("tool", ["Bash", "PowerShell"])
def test_strict_base64_expression_transport_is_available(tool):
    encoded = base64.b64encode(b'{service="edge"} |= "error"').decode()
    assert decision(f"{PREFIX} query --datasource logs --kind loki --from 1000 --to 61000 --expr-base64 {encoded}", tool) == 42


def test_only_fixed_powershell_wrapper_preserves_readable_expressions():
    assert decision(f"{WRAPPER} {PS_QUERY}", "PowerShell") == 42
    assert decision(f"{WRAPPER} {PS_QUERY}", "Bash") == 43


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
    assert decision(command, "PowerShell") == 43


@pytest.mark.parametrize("tool", ["Bash", "PowerShell"])
@pytest.mark.parametrize("command", [
    f"{PREFIX} dashboard --uid ../other",
    f"{PREFIX} dashboard --uid edge --url https://other.invalid",
    f"{PREFIX} dashboard --uid edge --token secret",
    f"{PREFIX} dashboard --uid edge > result.json",
    f"{PREFIX} dashboard --uid edge; cf restart edge",
    f"{PREFIX} dashboard --uid edge | python -c pass",
    f"{PREFIX} dashboard --uid edge\ncf restart edge",
    f"{PREFIX} query --datasource metrics --kind sql --from 1758400000000 --to 1758403600000 --expr 'DROP TABLE example'",
    f"{PREFIX} query --datasource metrics --kind prometheus --from 1 --to 9999999999999 --expr 'up'",
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
    assert decision(command, tool) == 43


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
    assert decision(command, "PowerShell") == 43
