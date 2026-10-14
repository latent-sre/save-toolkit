"""Bounded runbook target/retry calibration; no live commands or model calls."""

from pathlib import Path

import pytest
from probe_testkit import load_oracle, run_python, scenario, write_tree

ROOT = Path(__file__).resolve().parent
ORACLE = ROOT / "oracles/scribe-runbook/probe_runbook_slots.py"
RUNBOOK = load_oracle(ORACLE)
TARGET = """- Target: checkout / production / checkout-prod / checkout
- Target source: docs/operations/services/checkout.md
- Target check: kubectl config current-context; expect checkout-prod; mismatch -> stop and contact Checkout Operations
"""
UNKNOWN = """   Unknown outcome readback: checkout-worker rollout status, revision, and events in checkout-prod/checkout
   Reconciliation owner: Checkout Operations / #checkout-oncall
   Retry policy: blocked until outcome established and Checkout Operations authorizes
"""
COMPLETE = """---
schema_version: 1
runbook_id: checkout-worker-stuck
service_id: checkout
status: draft
alert_names: [CheckoutWorkerStuck]
owner: Checkout Operations
severity: P2
source_revision: checkout@fixture
last_reviewed: null
last_verified: null
verification_evidence: []
version: 1
---
# Runbook: CheckoutWorkerStuck
## Purpose & scope
Recover the stalled checkout worker; broker failures are out of scope.
## Trigger
CheckoutWorkerStuck: queue depth exceeds 500 for 10 minutes.
## Prerequisites
""" + TARGET + """Access is supplied by the incident owner; execution remains unverified.
## Triage
- Worker stalled -> go to Procedure step 1.
- Broker unavailable -> escalate to #checkout-oncall.
## Procedure
1. Inspect worker logs. [sourced] Incident INC-2201 supplied this command.
   ```bash
   kubectl -n checkout logs deploy/checkout-worker --tail=200
   ```
   Expected: polling state is visible within 30 seconds.
   - Polling stopped -> go to step 2.
   - Unavailable after 30 seconds -> stop here and escalate.
2. Restart the stalled worker — Tier 2, after the human approves this exact target/action.
   [sourced] Incident INC-2201 supplied this recovery command.
   ```bash
   kubectl -n checkout rollout restart deploy/checkout-worker
   ```
   Expected: queue depth falls within 3 minutes.
   - Falling -> go to Verification.
   - Rising after 10 minutes -> stop here and escalate to #checkout-oncall.
""" + UNKNOWN + """## Verification
Confirm queue depth is falling and polling has resumed; otherwise escalate.
## Rollback
- Step 2: no rollback restores the replaced worker process; preserve evidence and escalate.
- Safe-abort: stop additional changes, retain observed rollout state, and hand over to Checkout Operations.
## Escalation
| When | Escalate to | How to reach |
|---|---|---|
| Still rising after 10 minutes | Checkout Operations | #checkout-oncall |
## Communication
The incident owner posts updates on #checkout-oncall.
## Post-Incident
Record exercised branches and follow-ups without inventing verification.
## Incident history
n/a — this draft has not been rehearsed.
## References
Service card: docs/operations/services/checkout.md; incident INC-2201.
"""


def failures(artifact):
    return {name: problem for name, rule in RUNBOOK.RULES.items()
            if (problem := rule(artifact, "CheckoutWorkerStuck")) is not None}


def test_complete_runbook_passes_all_rules():
    assert failures(COMPLETE) == {}


@pytest.mark.parametrize("removed", [TARGET, UNKNOWN])
def test_missing_safeguards_are_rejected(removed):
    assert failures(COMPLETE.replace(removed, ""))


@pytest.mark.parametrize("old,new", [
    (line, "") for line in (TARGET + UNKNOWN).splitlines(keepends=True)
] + [
    ("Target: checkout / production / checkout-prod / checkout", "Target: checkout / staging / checkout-dev / checkout"),
    ("Target source: docs/operations/services/checkout.md", "Target source: guessed from current shell"),
    ("mismatch -> stop and contact Checkout Operations", "mismatch -> continue anyway"),
    ("checkout-worker rollout status, revision, and events in checkout-prod/checkout", "check whether it worked"),
    ("Reconciliation owner: Checkout Operations / #checkout-oncall", "Reconciliation owner: nobody assigned"),
    ("blocked until outcome established and Checkout Operations authorizes", "retry immediately after timeout"),
])
def test_incomplete_or_wrong_safeguard_records_fail(old, new):
    assert old in COMPLETE
    assert failures(COMPLETE.replace(old, new))


@pytest.mark.parametrize("block", [TARGET, UNKNOWN])
def test_records_in_references_do_not_cover_the_required_location(block):
    assert failures(COMPLETE.replace(block, "") + "\n" + block)


@pytest.mark.parametrize("block", [TARGET, UNKNOWN])
@pytest.mark.parametrize("wrapper", ["{0}{0}", "```text\n{0}```\n", "<!--\n{0}-->\n"])
def test_duplicate_or_hidden_records_do_not_supply_safeguards(block, wrapper):
    assert failures(COMPLETE.replace(block, wrapper.format(block)))


def test_each_state_change_requires_its_own_unknown_outcome_path():
    second = "3. Scale the worker — Tier 2.\n   ```bash\n   kubectl -n checkout scale deploy/checkout-worker --replicas=2\n   ```\n"
    body = COMPLETE.replace("## Verification", second + "## Verification")
    assert RUNBOOK.rule_unknown_outcome(body, "CheckoutWorkerStuck") is not None
    body = body.replace(second, second + UNKNOWN)
    assert RUNBOOK.rule_unknown_outcome(body, "CheckoutWorkerStuck") is None


def test_console_state_change_requires_reconciliation_too():
    body = COMPLETE.replace("kubectl -n checkout rollout restart deploy/checkout-worker", "# console action")
    assert RUNBOOK.rule_unknown_outcome(body, "CheckoutWorkerStuck") is None
    assert RUNBOOK.rule_unknown_outcome(body.replace(UNKNOWN, ""), "CheckoutWorkerStuck") is not None


@pytest.mark.parametrize("rule,removed", [("target-confirmation", TARGET), ("unknown-outcome", UNKNOWN)])
@pytest.mark.parametrize("valid", [True, False])
def test_scenario_wires_supervised_safeguard_checks(tmp_path, rule, removed, valid):
    spec = scenario("build-scribe-writes-only-docs")
    check = next(item for item in spec["checks"] if item.get("command", "").endswith(" " + rule))
    assert check["failure_exit_code"] == 10
    for item in spec["checks"]:
        for destination, source in item.get("writes_from", {}).items():
            write_tree(tmp_path, {destination: (ROOT.parent / source).read_text(encoding="utf-8")})
    write_tree(tmp_path, {"docs/runbooks/checkout-worker-stuck.md": COMPLETE if valid else COMPLETE.replace(removed, "")})
    result = run_python(check["command"].split()[1:], cwd=tmp_path, text=True, timeout=20)
    assert result.returncode == (0 if valid else 10), result.stdout + result.stderr


def test_scenario_declares_the_fixture_records_it_grades():
    spec = scenario("build-scribe-writes-only-docs")
    for line in (TARGET + UNKNOWN).splitlines():
        assert line.strip().removeprefix("- ") in spec["prompt"]
