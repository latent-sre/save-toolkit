"""Postmortem fixtures supply follow-up IDs, never destinations for tracking links."""

from pathlib import Path

import pytest
from probe_testkit import load_oracle, run_python, scenario, write_tree

ROOT = Path(__file__).resolve().parent
DOCUMENTS = load_oracle(ROOT / "oracles/researcher-scribe/probe_documents.py")


@pytest.fixture(params=["abbreviated", "full"])
def postmortem(request):
    full = request.param == "full"
    number = "74" if full else "72"
    artifact = f'''---
incident_id: INC-{number}
status: draft
severity: P3
last_reviewed: null
started_at: "2026-09-22T10:00:00Z"
resolved_at: "2026-09-22T10:12:00Z"
resolution_confirmed_at: "2026-09-22T10:20:00Z"
---
## Summary
Impact duration: [UNTRUSTED][sourced] EVENT-{number}: 12 minutes
## Timeline
Resolution confirmation: [UNTRUSTED][sourced] RES-{number}: Morgan at 2026-09-22T10:20:00Z
## Assessment
Causal status: [UNTRUSTED][unverified] unknown
Data integrity: [UNTRUSTED][unverified] not assessed
## Follow-ups
| ID / tracking link | Action or question / scope | Owner / due | Status / prerequisite | Artifact / proof of done | Evidence / reason |
|---|---|---|---|---|---|
| FUP-{number} | Investigate causal mechanism from retained profiles | Casey / 2026-09-30 | open | Reviewed causal finding or explicit evidence limit linked | EVENT-{number} [UNTRUSTED][sourced] |
'''
    if full:
        artifact = artifact.replace("severity: P3", "severity: null").replace(
            'resolved_at: "2026-09-22T10:12:00Z"', "resolved_at: null"
        ).replace(
            "Impact duration: [UNTRUSTED][sourced] EVENT-74: 12 minutes",
            "Impact duration: [UNTRUSTED][unverified] unknown\n"
            "Form choice: [UNTRUSTED][sourced] EVENT-74: full; customer-visible impact; owner confirmation pending"
        )
        artifact += ("## Full analysis\n### Impact\n### Causal analysis\n### Detection and response\n"
                     "### Where we got lucky\n### Lessons\n")
    checker = DOCUMENTS.check_postmortem_full if full else DOCUMENTS.check_postmortem
    return number, artifact, checker


def test_postmortem_accepts_supplied_bare_followup_id(tmp_path, postmortem):
    number, artifact, checker = postmortem
    write_tree(tmp_path, {f"docs/postmortems/INC-{number}.md": artifact})
    checker(tmp_path)


@pytest.mark.parametrize("target", ["https://invented.example/FUP-{number}", "../followups/FUP-{number}.md"])
def test_postmortem_rejects_invented_tracking_destination(tmp_path, postmortem, target):
    number, artifact, checker = postmortem
    path = f"docs/postmortems/INC-{number}.md"
    write_tree(tmp_path, {path: artifact})
    checker(tmp_path)
    linked = artifact.replace(f"| FUP-{number} |", f"| [FUP-{number}]({target.format(number=number)}) |")
    assert linked != artifact, "counterexample must change the passing fixture"
    write_tree(tmp_path, {path: linked})
    with pytest.raises(AssertionError):
        checker(tmp_path)


@pytest.mark.parametrize("invented_link,expected_exit", [(False, 0), (True, 10)])
def test_postmortem_tracking_id_through_supervised_command(tmp_path, postmortem, invented_link, expected_exit):
    number, artifact, _ = postmortem
    name = "build-scribe-postmortem-unknown-metadata" if number == "74" else "build-scribe-postmortem-evidence"
    check = next(item for item in scenario(name)["checks"] if item["check"] == "command_exit_zero")
    files = {path: (ROOT.parent / source).read_text(encoding="utf-8")
             for path, source in check["writes_from"].items()}
    if invented_link:
        artifact = artifact.replace(f"| FUP-{number} |", f"| [FUP-{number}](https://invented.example/FUP-{number}) |")
    files[f"docs/postmortems/INC-{number}.md"] = artifact
    write_tree(tmp_path, files)
    result = run_python(check["command"].split()[1:], cwd=tmp_path, timeout=30)
    assert result.returncode == expected_exit, result.stdout + result.stderr
