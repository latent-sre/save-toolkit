"""Offline tests for skills/runbook/scripts/confluence_to_runbook.py.

The converter turns a human-supplied Confluence export (view/export HTML preferred; storage-format
XHTML best-effort) into a DRAFT runbook in the template shape. The contract under test:

  * the draft's frontmatter carries exactly the runbook-frontmatter-v1 key set, with the import
    invariants pinned: status draft, version 1, both dates null, empty verification evidence;
  * recognizable source headings land in the matching template slot; unrecognized content lands in
    an explicit "Imported content (unmapped)" section — nothing is silently dropped;
  * every imported fenced command block carries an [unverified] marker;
  * Confluence macro elements (<ac:...>/<ri:...>) are counted and reported as conversion losses in
    the provenance, never silently mangled;
  * provenance (source file, title, optional URL, loss counts) is stamped into the draft.

Written before the converter existed and confirmed failing (fails-without-the-change rule).
Pure stdlib; runs offline in CI via gate_a.py.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONVERTER = ROOT / "skills" / "runbook" / "scripts" / "confluence_to_runbook.py"
SCHEMA_PATH = ROOT / "schemas" / "runbook-frontmatter-v1.schema.json"

VIEW_HTML = """<html><head><title>Restart the checkout worker</title></head><body>
<h1>Restart the checkout worker</h1>
<h2>When to use this</h2>
<p>The checkout-worker-stalled alert fired, or queue depth keeps growing.</p>
<h2>Before you start</h2>
<ul><li>VPN connected</li><li>cf CLI v8 logged in to pcf-east</li></ul>
<h2>Steps</h2>
<ol><li>Check the worker state.</li></ol>
<pre>cf app checkout-worker</pre>
<h2>Rollback</h2>
<p>No rollback needed; the restart is the reset.</p>
<h2>Escalation</h2>
<p>Page the payments team after two failed restarts.</p>
<h2>Background reading</h2>
<p>Original design doc lives in the architecture space.</p>
<ac:structured-macro ac:name="jira"><ac:parameter ac:name="key">PAY-123</ac:parameter></ac:structured-macro>
</body></html>"""


def run_converter(html: str, *args: str) -> tuple[subprocess.CompletedProcess, str]:
    """Run the converter on `html`, returning (proc, draft_text)."""
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "page.html"
        out = Path(tmp) / "draft.md"
        src.write_text(html, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(CONVERTER), str(src), "-o", str(out), *args],
            capture_output=True,
            text=True,
            timeout=30,
        )
        draft = out.read_text(encoding="utf-8") if out.exists() else ""
    return proc, draft


def frontmatter_fields(draft: str) -> dict[str, str]:
    """Parse the draft's flat YAML frontmatter into raw string values."""
    lines = draft.splitlines()
    if not lines or lines[0] != "---":
        raise AssertionError("draft must open with a frontmatter fence")
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        match = re.match(r"^([a-z_][a-z0-9_]*):\s*(.*)$", line)
        if match:
            fields[match.group(1)] = match.group(2)
    raise AssertionError("frontmatter fence never closes")


class ConfluenceImportTest(unittest.TestCase):
    def setUp(self) -> None:
        self.proc, self.draft = run_converter(
            VIEW_HTML, "--source-url", "https://example.atlassian.net/wiki/pages/123"
        )
        self.assertEqual(
            self.proc.returncode, 0,
            f"converter failed: stderr={self.proc.stderr[:500]!r}",
        )

    def test_frontmatter_matches_the_published_schema_keys(self) -> None:
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        fields = frontmatter_fields(self.draft)
        self.assertEqual(sorted(fields), sorted(schema["properties"]))

    def test_import_invariants_are_pinned(self) -> None:
        # An import is never a review or a rehearsal: draft status, first version, null dates.
        fields = frontmatter_fields(self.draft)
        self.assertEqual(fields["schema_version"], "1")
        self.assertEqual(fields["status"], "draft")
        self.assertEqual(fields["version"], "1")
        self.assertEqual(fields["last_reviewed"], "null")
        self.assertEqual(fields["last_verified"], "null")
        self.assertEqual(fields["verification_evidence"], "[]")
        self.assertEqual(fields["runbook_id"], "restart-the-checkout-worker")

    def test_recognized_headings_land_in_template_slots(self) -> None:
        # "When to use this" → Trigger; "Before you start" → Prerequisites; "Steps" → Procedure;
        # Rollback and Escalation map by name. Each mapped section must carry its source content.
        for slot, content in [
            ("## Trigger", "checkout-worker-stalled"),
            ("## Prerequisites", "VPN connected"),
            ("## Procedure", "Check the worker state"),
            ("## Rollback / cleanup", "the restart is the reset"),
            ("## Escalation", "payments team"),
        ]:
            with self.subTest(slot=slot):
                section = self.draft.split(slot, 1)
                self.assertEqual(len(section), 2, f"missing slot {slot!r}")
                self.assertIn(content, section[1].split("\n## ", 1)[0])

    def test_unrecognized_content_is_kept_not_dropped(self) -> None:
        self.assertIn("Imported content (unmapped)", self.draft)
        unmapped = self.draft.split("Imported content (unmapped)", 1)[1]
        self.assertIn("architecture space", unmapped)

    def test_imported_commands_are_marked_unverified(self) -> None:
        self.assertIn("cf app checkout-worker", self.draft)
        block_and_after = self.draft.split("cf app checkout-worker", 1)[1]
        self.assertIn("[unverified]", block_and_after[:300])

    def test_macro_loss_is_reported_in_provenance_and_stdout(self) -> None:
        # The <ac:structured-macro> cannot convert; it must be COUNTED, in the draft's provenance
        # and on stdout — a silent loss reads as "the page never had it".
        self.assertRegex(self.draft, r"[Mm]acro")
        self.assertRegex(self.proc.stdout, r"[Mm]acro")
        self.assertIn("https://example.atlassian.net/wiki/pages/123", self.draft)
        self.assertIn("page.html", self.draft)

    def test_unreadable_input_fails_loudly(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(CONVERTER), "/nonexistent/page.html", "-o", "/tmp/x.md"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertNotEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
