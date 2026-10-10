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


def check_postmortem(root):
    text = (root / "docs/postmortems/INC-72.md").read_text(encoding="utf-8")
    no_new_verified(text)
    fields = frontmatter(text)
    for key, value in {"incident_id": "INC-72", "status": "draft", "severity": "P3",
                       "last_reviewed": None}.items():
        assert key in fields and fields[key] == value, f"wrong or missing {key}"
    for key, value in {"started_at": "2026-09-22T10:00:00Z",
                       "resolved_at": "2026-09-22T10:12:00Z",
                       "resolution_confirmed_at": "2026-09-22T10:20:00Z"}.items():
        assert fields.get(key) == value, f"{key} must retain the supplied quoted UTC time"
    for heading in ("Summary", "Timeline", "Assessment", "Follow-ups"):
        assert re.search(rf"^## {heading}\b", text, re.M), f"missing {heading}"
    assert not re.search(r"^## Full analysis", text, re.M), "abbreviated form requested"
    rows = [line for line in text.splitlines() if line.startswith("|") and "FUP-72" in line]
    assert len(rows) == 1, "retain one existing FUP-72 follow-up row"
    assert all(value in rows[0] for value in ("Casey", "2026-09-30")), "lost follow-up owner/date"
    for source in ("EVENT-72", "RES-72"):
        labeled_record(text, rf"\b{source}\b", "sourced")
    for gap in ("Causal status", "Data integrity"):
        labeled_record(text, rf"\b{gap}\b", "unverified")


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
        {"postmortem": check_postmortem, "closeout": check_closeout,
         "alert-closeout": check_alert_closeout}[sys.argv[1]](Path.cwd())
    except (AssertionError, OSError, yaml.YAMLError) as exc:
        print(f"FAIL: {exc}")
        return 10
    print("PASS: bounded artifact fields; free-form quality and live behavior remain unverified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
