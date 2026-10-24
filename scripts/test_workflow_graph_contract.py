"""Offline probes of the sandbox's declared effect contract, not a runtime engine."""
import re
from pathlib import Path

import pytest

BUNDLE = Path(__file__).resolve().parents[1] / "sandbox/workflow-graph-engineering"


def document(relative: str) -> str:
    return (BUNDLE / relative).read_text(encoding="utf-8")


def declared_key(request: dict[str, str]) -> tuple[str, ...]:
    """Compare symbolic key inputs; cryptographic hash implementation is out of scope."""
    formula = re.search(r"key = H\(([^)]+)\)", document("references/effects-and-approval.md"))
    assert formula is not None
    return tuple(request[field.strip()] for field in formula[1].split(","))


def test_new_identical_operation_differs_but_retry_keeps_key() -> None:
    first = dict(caller="responder", operation="send", target="reminders", tenant="a")
    first.update({"logical request ID": "reminder-1", "intent digest": "same-payload",
                  "attempt ID": "attempt-1"})
    retry = first | {"attempt ID": "attempt-2"}
    new = first | {"logical request ID": "reminder-2", "attempt ID": "attempt-3"}
    assert declared_key(first) == declared_key(retry)
    assert declared_key(first) != declared_key(new)


def test_changed_payload_cannot_evade_binding_by_changing_key() -> None:
    first = dict(caller="responder", operation="send", target="reminders", tenant="a")
    first.update({"logical request ID": "reminder-1", "intent digest": "payload-a"})
    changed = first | {"intent digest": "payload-b"}
    assert declared_key(first) == declared_key(changed)
    effects = document("references/effects-and-approval.md")
    assert "Compare and reserve this binding atomically" in effects
    assert "Reject reuse with mismatched intent **before dispatch**" in effects


@pytest.mark.parametrize("relative", [
    "SKILL.md", "references/effects-and-approval.md",
    "references/durability-and-lifecycle.md", "assets/design-contract.template.md",
])
def test_recovery_contract_blocks_unresolved_redispatch(relative: str) -> None:
    text = " ".join(document(relative).lower().split())
    assert "no automatic redispatch is allowed while unresolved" in text or (
        "no automatic redispatch while unresolved" in text
    )
    assert "native dedupe" in text or "target-native idempotency" in text


def test_unknown_state_machine_requires_reconciliation() -> None:
    effects = document("references/effects-and-approval.md")
    machine = re.search(r"```\n(.*?)\n```", effects, re.S)
    assert machine is not None
    assert "UNKNOWN -> RECONCILING -> SUCCEEDED | FAILED | STILL_UNKNOWN" in machine[1]
    assert not re.search(r"^(?:UNKNOWN|STILL_UNKNOWN) -> (?:PENDING|DISPATCHED)", machine[1], re.M)
    assert "unless the class is `idempotent-by-key`" not in effects
    # Missing, expired, and even valid dedupe proof cannot resolve an ambiguous commit.
    assert "documented native dedupe with valid retention" in effects
    assert "A missing eventually consistent read is insufficient" in effects
    assert "no in-flight or late commit possible" in effects
    assert "definitive non-application" in document("references/review-checklist.md")


@pytest.mark.parametrize("proof", [
    "Missing", "Same key, expired retention",
    "Exact target, same key, matching digest, valid retention",
])
def test_dedupe_proof_does_not_bypass_unknown_resolution(proof: str) -> None:
    effects = document("references/effects-and-approval.md")
    rows = [line.split("|")[1:-1] for line in effects.splitlines()
            if line.startswith("| Unresolved timeout |")]
    matches = [row for row in rows if row[1].strip() == proof]
    assert len(matches) == 1
    assert matches[0][2].strip() == "Hold; no redispatch"
