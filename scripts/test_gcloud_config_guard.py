"""Exercise configuration-read policy without running gcloud or reading credentials."""
import pytest
from testkit import guard_decision, guard_payload, run_guard

CONTEXTS = [
    ("Bash", "save-toolkit:sre-assistant", False),
    ("PowerShell", "save-toolkit:sre-assistant", False),
    ("execute/runInTerminal", None, True),
    ("Bash", "save-toolkit:software-engineer", False),
    ("PowerShell", "save-toolkit:software-engineer", False),
]


def decision(command, context):
    tool, agent, copilot = context
    return guard_decision(run_guard(guard_payload(command, tool_name=tool, agent_type=agent), copilot=copilot))


@pytest.mark.parametrize("context", CONTEXTS)
@pytest.mark.parametrize("command", [
    "gcloud config list proxy/password",
    "gcloud config get-value proxy/password",
    "gcloud config get proxy/password",
    "gcloud config list proxy/username --format=json",
    "gcloud config list",
    "gcloud config list --all",
    "gcloud config list proxy/",
    "gcloud config list core/",
    "gcloud config get-value account",
    "gcloud config get-value unreviewed/property",
    "gcloud alpha config list proxy/password",
    "gcloud beta config get-value proxy/password",
    "gcloud config list project proxy/password",
])
def test_credential_or_unrestricted_configuration_reads_denied(command, context):
    assert decision(command, context) == "deny"


@pytest.mark.parametrize("context", CONTEXTS)
@pytest.mark.parametrize("command", [
    "gcloud config list project",
    "gcloud config get-value core/project",
    "gcloud config get-value run/region",
    "gcloud config list compute/region",
    "gcloud config get-value compute/zone",
])
def test_required_noncredential_target_reads_remain_available(command, context):
    assert decision(command, context) == "allow"


@pytest.mark.parametrize("context", CONTEXTS[:3])
@pytest.mark.parametrize("suffix", ["--all", "--configuration other", "--format=json", "--log-http"])
def test_sre_config_reads_do_not_accept_extra_flags(suffix, context):
    assert decision("gcloud config list project " + suffix, context) == "deny"


@pytest.mark.parametrize("command", [
    'rg "gcloud config list proxy/password" docs/',
    "gcloud config set project example",
    "gcloud config unset proxy/password",
])
def test_build_lane_data_and_configuration_changes_are_not_read_tripwires(command):
    assert decision(command, CONTEXTS[3]) == "allow"
