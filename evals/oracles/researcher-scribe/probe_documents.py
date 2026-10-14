"""Bounded artifact checks for fictional scribe fixtures, not a document-quality grader."""

from pathlib import Path
import re
import sys

import yaml


def labeled_record(text, marker, evidence):
    """These fixtures request one-line claim records, with their source/gap and retained labels."""
    lines = [line for line in text.splitlines() if re.search(marker, line, re.I)]
    assert lines, f"missing claim record: {marker}"
    label = rf"\[UNTRUSTED\]\s*\[{evidence}(?:\]|\s*:[^\]]+\])"
    assert all(re.search(label, line, re.I) for line in lines), f"claim record lost its labels: {marker}"
    return lines


def no_new_verified(text):
    assert not re.search(r"\[verified(?:\s*:|\])", text, re.I), "fixture supplies no verified claims"


def frontmatter(text):
    match = re.match(r"\A---\n(.*?)\n---(?:\n|\Z)", text, re.S)
    assert match, "missing YAML frontmatter"
    fields = yaml.safe_load(match[1])
    assert isinstance(fields, dict), "frontmatter must be a mapping"
    return fields


def _fixture_record(text, name, value):
    """Check an explicitly requested fixture record, not arbitrary prose semantics."""
    records = [line.strip() for line in text.splitlines() if line.startswith(name + ":")]
    expected = f"{name}: {value}"
    assert len(records) == 1 and " ".join(records[0].split()) == expected, f"wrong or missing {name} record"


def _check_postmortem(root, *, full):
    number = "74" if full else "72"
    text = (root / f"docs/postmortems/INC-{number}.md").read_text(encoding="utf-8")
    no_new_verified(text)
    fields = frontmatter(text)
    for key, value in {"incident_id": f"INC-{number}", "status": "draft", "severity": None if full else "P3",
                       "last_reviewed": None}.items():
        assert key in fields and fields[key] == value, f"wrong or missing {key}"
    for key, value in {"started_at": "2026-09-22T10:00:00Z",
                       "resolved_at": None if full else "2026-09-22T10:12:00Z",
                       "resolution_confirmed_at": "2026-09-22T10:20:00Z"}.items():
        assert key in fields and fields[key] == value, f"{key} must retain the supplied UTC time or null"
    for heading in ("Summary", "Timeline", "Assessment", "Follow-ups"):
        assert re.search(rf"^## {heading}\b", text, re.M), f"missing {heading}"
    if full:
        assert re.search(r"^## Full analysis\b", text, re.M), "full form required"
        for heading in ("Impact", "Causal analysis", "Detection and response", "Where we got lucky", "Lessons"):
            assert re.search(rf"^### {heading}\b", text, re.M), f"missing full-form {heading}"
        _fixture_record(text, "Form choice", f"[UNTRUSTED][sourced] EVENT-{number}: "
                        "full; customer-visible impact; owner confirmation pending")
    else:
        assert not re.search(r"^## Full analysis", text, re.M), "abbreviated form requested"
    rows = [line for line in text.splitlines()
            if line.startswith("|") and re.search(rf"\bFUP-{number}\b", line)]
    assert len(rows) == 1, f"retain one existing FUP-{number} follow-up row"
    cells = [cell.strip() for cell in rows[0].split("|")[1:-1]]
    assert len(cells) == 6, "follow-up must use the six template columns"
    assert re.fullmatch(rf"(?:FUP-{number}|\[FUP-{number}\]\([^)]+\))", cells[0]), "wrong follow-up ID"
    expected = ("Investigate causal mechanism from retained profiles", "Casey / 2026-09-30", "open",
                "Reviewed causal finding or explicit evidence limit linked")
    assert tuple(cells[1:5]) == expected, "lost follow-up question, owner/date, open status, or proof"
    for source in (f"EVENT-{number}", f"RES-{number}"):
        labeled_record(text, rf"\b{source}\b", "sourced")
    duration = "[UNTRUSTED][unverified] unknown" if full else f"[UNTRUSTED][sourced] EVENT-{number}: 12 minutes"
    _fixture_record(text, "Impact duration", duration)
    _fixture_record(text, "Resolution confirmation",
                    f"[UNTRUSTED][sourced] RES-{number}: Morgan at 2026-09-22T10:20:00Z")
    _fixture_record(text, "Causal status", "[UNTRUSTED][unverified] unknown")
    _fixture_record(text, "Data integrity", "[UNTRUSTED][unverified] not assessed")


def check_postmortem(root):
    _check_postmortem(root, full=False)


def check_postmortem_full(root):
    _check_postmortem(root, full=True)


def check_closeout(root):
    card = (root / "docs/operations/services/checkout.md").read_text(encoding="utf-8")
    index = (root / "docs/operations/index.md").read_text(encoding="utf-8")
    fields = frontmatter(card)
    assert fields.get("owner") == "Checkout Operations", "service owner was not corrected"
    assert fields.get("lifecycle") == "active", "contact correction changed lifecycle"
    assert str(fields.get("last_reviewed")) == "2026-09-01", "contact correction changed review evidence"
    assert fields.get("source_revision") == "reviewed-release-R1", "contact correction rewrote source history"
    for text in (card, index):
        no_new_verified(text)
        assert "#checkout-operations" in text, "new contact absent from owning artifact"
        assert "#checkout-platform" not in text, "stale contact retained"
        assert "Checkout Operations" in text and "Checkout Platform" not in text, "stale owning team retained"
    assert "services/checkout.md" in index, "index lost existing service-card target"
    assert "../../runbooks/checkout.md" in card, "card lost existing procedure target"
    records = labeled_record(card, r"\bAUDIT-73\b", "sourced")
    assert any(re.search(r"\bCheckout Operations\b", line)
               and re.search(r"(?<![\w#-])#checkout-operations(?![\w-])", line) for line in records), (
        "AUDIT-73 must label the corrected owner and contact on the same line"
    )


def check_alert_closeout(root):
    index = (root / "docs/operations/index.md").read_text(encoding="utf-8")
    no_new_verified(index)
    # Supplied fixture facts, not a schema for arbitrary alert cards or live Grafana state.
    cases = (
        ("queue-lag", "QueueLag", "API-owned", "RULE-81", None,
         "https://grafana.example.invalid/alerting/grafana/queue-lag/view?orgId=7"),
        ("queue-depth", "QueueDepth", "source-managed", "SOURCE-82", "b" * 40,
         "alert-definitions/config/queue-depth.yaml@" + "b" * 40),
    )
    for slug, name, kind, receipt, version, locator in cases:
        card = (root / f"docs/operations/alerts/{slug}.md").read_text(encoding="utf-8")
        no_new_verified(card)
        fields = frontmatter(card)
        expected = {"alert_id": slug, "service_id": "checkout", "status": "active",
                    "source_definition": locator, "definition_version": version,
                    "source_receipt": receipt, "runbook": "../../runbooks/checkout.md",
                    "last_reviewed": None}
        for key, value in expected.items():
            assert key in fields and fields[key] == value, f"{name}: wrong or missing {key}"
        provenance = labeled_record(card, r"^Definition provenance:", "sourced")
        assert len(provenance) == 1 and all(value in provenance[0] for value in (kind, receipt, locator)), (
            f"{name}: provenance must bind the owning definition and supplied receipt"
        )
        evidence = "unverified" if version is None else "sourced"
        version_records = labeled_record(card, r"^Version evidence:", evidence)
        assert len(version_records) == 1 and (version or "unknown") in version_records[0], (
            f"{name}: version evidence does not match the supplied record"
        )
        assert "../services/checkout.md" in card, f"{name}: lost service-card link"
        rows = [line.split("|")[1:-1] for line in index.splitlines() if line.startswith("|")]
        rows = [[cell.strip() for cell in row] for row in rows if row and row[0].strip() == name]
        assert len(rows) == 1 and len(rows[0]) == 6, f"{name}: missing or duplicate index row"
        assert rows[0][1:3] == ["active", "checkout"], f"{name}: index lifecycle or service changed"
        for value, cell in ((f"alerts/{slug}.md", rows[0][3]),
                            ("../runbooks/checkout.md", rows[0][4]), (locator, rows[0][5])):
            assert cell == value or re.fullmatch(r"\[[^\]\n]+\]\(" + re.escape(value) + r"\)", cell), (
                f"{name}: index link does not identify the owning artifact"
            )


def main():
    try:
        {"postmortem": check_postmortem, "postmortem-full": check_postmortem_full, "closeout": check_closeout,
         "alert-closeout": check_alert_closeout}[sys.argv[1]](Path.cwd())
    except (AssertionError, OSError, yaml.YAMLError) as exc:
        print(f"FAIL: {exc}")
        return 10
    print("PASS: bounded artifact fields; free-form quality and live behavior remain unverified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
