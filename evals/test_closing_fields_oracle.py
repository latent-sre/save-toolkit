"""No-model regressions for the incident advisor's reply-closing contract.

Two things are held here: the oracle discriminates the four closing shapes, including the
heading-style checkpoint that a colon-anchored detector misses; and the skill still carries the
contract the oracle grades, so the suite fails if the rule is removed again rather than passing an
empty promise.
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ORACLE = ROOT / "evals/oracles/incident-closing-fields/probe_closing_fields.py"
SKILL = ROOT / "skills/incident-investigation/SKILL.md"


@pytest.fixture(scope="module")
def oracle():
    spec = importlib.util.spec_from_file_location("probe_closing_fields", ORACLE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CLOSING = """Check the pool counts next.

Applied: none — nothing executed yet
Open:    (a) downstream latency (owner: DB on-call)  (b) consumer-side backlog — unowned
Next:    ledger-db p95 over 15:00-15:50; elevated strengthens downstream
"""

CHECKPOINT_COLON = """Handing over.

- **Assessment:** downstream latency versus consumer backlog
- **Checked:** queue depth 1,800 at 15:45 [sourced]
- **Actions:** scale 2 to 4 at 15:12, confirmed applied
- **Next:** Lee checks database p95 for the incident window
- **Follow-ups:** reconcile the 15:30 attempt with Omar
"""

# The shape that a colon-anchored detector reads as an absence.
CHECKPOINT_HEADINGS = """Handing over to Lee.

### Assessment
Downstream latency versus consumer-side backlog; neither ruled out.

### Checked
Queue depth 1,800 at 15:45 [sourced: Wavefront].

### Actions
Scale 2 to 4 at 15:12 by Omar, confirmed applied.

### Next
Lee checks database p95 for the incident window.

### Follow-ups
Owner Dana: reconcile the 15:30 retry-flag attempt.
"""

NONE = """"Waiting for a connection" means a thread is waiting to acquire a connection from the
pool. That is an acquisition wait; it does not by itself establish a full pool or name the cause.
The counts that would discriminate are active, maximum, and waiting.
"""


@pytest.mark.parametrize(
    "text,expected",
    [
        (CLOSING, "fields"),
        (CHECKPOINT_COLON, "checkpoint"),
        (CHECKPOINT_HEADINGS, "checkpoint"),
        (CLOSING + CHECKPOINT_COLON, "both"),
        (NONE, "none"),
    ],
)
def test_classifies_each_closing_shape(oracle, text, expected):
    assert oracle.classify(text) == expected


def test_heading_style_checkpoint_is_not_read_as_absence(oracle):
    """The regression that made a sound handover score as nothing."""
    assert oracle.classify(CHECKPOINT_HEADINGS) != "none"


def test_prose_mention_of_a_field_word_is_not_the_closing_fields(oracle):
    """One field name in a sentence must not satisfy the contract."""
    assert oracle.classify("Next, open the Events view and see what is applied.") == "none"


def test_removing_the_fields_flips_the_verdict(oracle):
    """Mutate the thing the oracle names and watch it fail, so a pass means something."""
    ok, _ = oracle.check(CLOSING, "fields")
    assert ok
    removed = CLOSING.replace("Applied:", "").replace("Open:", "").replace("Next:", "")
    ok, reason = oracle.check(removed, "fields")
    assert not ok and "expected 'fields'" in reason


def test_alternation_accepts_either_allowed_shape(oracle):
    assert oracle.check(CHECKPOINT_HEADINGS, "checkpoint-or-both")[0]
    assert oracle.check(CLOSING + CHECKPOINT_COLON, "checkpoint-or-both")[0]
    assert not oracle.check(CLOSING, "checkpoint-or-both")[0]


def test_unknown_expected_class_is_refused(oracle):
    ok, reason = oracle.check(CLOSING, "nonsense")
    assert not ok and "unknown expected class" in reason


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Open the console.\nNext, inspect the request.", "fields"),
        ("Applied: none\nNext: inspect the request", "fields"),
        ("### Assessment\n\n### Checked\n", "checkpoint"),
        ("Assessment: latency\nChecked: queue depth", "checkpoint"),
        (CLOSING + "\n## Actual answer\nInspect the request.", "fields"),
        (CLOSING + "\nInspect the request.", "fields"),
        ("> " + CLOSING.replace("\n", "\n> "), "fields"),
        ("```text\n" + CLOSING + "```\n\nInspect the request.", "fields"),
        ("Example:\n```text\n" + CLOSING + "```\n", "fields"),
        ("### Sample response\n```text\n" + CLOSING + "```\n", "fields"),
        ("Applied: none\nOpen: unknown\n### Next — the next useful check", "fields"),
    ],
)
def test_rejects_incomplete_or_nonclosing_blocks(oracle, text, expected):
    assert not oracle.check(text, expected)[0]


def test_presence_is_not_completeness(oracle):
    text = "Assessment: latency\nChecked: queue depth"
    assert oracle.classify(text) == "checkpoint"
    assert not oracle.check(text, "checkpoint-or-both")[0]
    assert oracle.classify("Open the console.\nNext, inspect the request.") == "none"


@pytest.mark.parametrize("expected,names", [
    ("fields", ("Applied", "Open", "Next")),
    ("checkpoint", ("Assessment", "Checked", "Actions", "Next", "Follow-ups")),
])
def test_every_required_field_needs_a_value(oracle, expected, names):
    complete = "\n".join(f"{name}: unknown" for name in names)
    assert oracle.check(complete, expected)[0]
    for name in names:
        for replacement in ("", f"{name}:", f"{name}: **—**"):
            incomplete = complete.replace(f"{name}: unknown", replacement)
            assert not oracle.check(incomplete, expected)[0], (name, replacement)


@pytest.mark.parametrize("text", [
    "Applied: none\nOpen: unknown\nNext: inspect the request",
    "### Applied\nnone\n\n### Open\nunknown\n\n### Next\ninspect the request",
    "~~~markdown\n### Applied ###\nnone\n### Open ###\nunknown\n### Next ###\ninspect the request\n~~~",
    "### Applied — changes made\nnone\n### Open — unresolved candidates\nunknown\n### Next — the next useful check\ninspect the request",
    "1. **Applied:** none\n2. **Open:** unknown\n3. **Next:** inspect the request",
    "| Field | Value |\n| --- | --- |\n| Applied | none |\n| Open | unknown |\n| Next | inspect the request |",
    "```text\nApplied: none\nOpen: unknown\nNext: inspect the request\n```",
])
def test_complete_blocks_keep_supported_markdown_formats(oracle, text):
    assert oracle.check(text, "fields")[0]


@pytest.mark.parametrize("text", [
    "Based on this sample, inspect the pool.\n\n" + CLOSING.split("\n\n", 1)[1],
    "Use the supplied sample to compare.\n\n```text\n" + CLOSING + "```",
])
def test_narrative_sample_mentions_do_not_exclude_actual_closure(oracle, text):
    assert oracle.check(text, "fields")[0]


def test_both_requires_both_complete_forms(oracle):
    both = CLOSING + CHECKPOINT_COLON.split("\n\n", 1)[1]
    assert oracle.check(both, "both")[0]
    assert oracle.check(both, "fields-or-both")[0]
    assert not oracle.check(both.replace("Open:", "Missing:"), "both")[0]


def test_shipped_helper_replies_are_complete(oracle):
    reference = ROOT / "skills/incident-investigation/references/helper-exchange.md"
    replies = re.findall(r"```text\n(.*?)\n```", reference.read_text(encoding="utf-8"), re.S)
    assert len(replies) == 2
    for reply in replies:
        assert oracle.check(reply, "fields")[0]


def test_shipped_handover_reply_is_complete(oracle):
    text = SKILL.read_text(encoding="utf-8").split("Handover example:", 1)[1]
    reply = re.search(r"```text\n(.*?)\n```", text, re.S)
    assert reply is not None
    assert oracle.check(reply[1], "checkpoint")[0]


# --- the skill still carries the contract the oracle grades -------------------------------------

def test_skill_defines_the_three_closing_fields():
    text = SKILL.read_bytes().decode("utf-8")
    for field in ("Applied:", "Open:", "Next:"):
        assert field in text, f"the skill no longer defines the {field!r} field"


def _handoff_sentence() -> str:
    """The clause that sends the closing fields to the checkpoint, alone.

    Scoped deliberately: every trigger word also appears elsewhere in the skill, so a whole-file
    substring search would pass with this clause deleted.
    """
    text = SKILL.read_bytes().decode("utf-8")
    marker = "checkpoint trigger fires:"
    assert marker in text, "the closing fields no longer hand off to the checkpoint at all"
    tail = text.split(marker, 1)[1]
    return tail.split(".", 1)[0].lower()


def test_skill_names_every_checkpoint_trigger():
    """The closing fields must hand off on all of the checkpoint's triggers, not just a handover."""
    clause = _handoff_sentence()
    for trigger in ("transition", "handover", "recap", "direction", "mitigation", "branches"):
        assert trigger in clause, f"checkpoint trigger {trigger!r} missing from the handoff clause"


def test_handoff_clause_scope_excludes_the_rest_of_the_skill():
    """Proves the scoping above: the clause is a fragment, not the document."""
    clause = _handoff_sentence()
    assert len(clause) < 400, "handoff clause captured too much to discriminate"
    assert "postmortem" not in clause, "clause bled into surrounding prose"


def test_skill_keeps_the_live_versus_standalone_boundary():
    text = SKILL.read_bytes().decode("utf-8").lower()
    assert "no live incident" in text, "the standalone-question exemption is gone"
    assert "being worked" in text, "the live-incident trigger is gone"


def test_skill_requires_an_owner_on_every_standing_candidate():
    text = SKILL.read_bytes().decode("utf-8").lower()
    assert "unowned" in text, "standing candidates no longer have to name an owner"
