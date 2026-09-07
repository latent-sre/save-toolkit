"""Offline tests for skills/runbook/scripts/confluence_to_runbook.py.

The converter turns a human-supplied Confluence export (view/export HTML preferred; storage-format
XHTML best-effort) into a DRAFT runbook in the template shape. The contract under test:

  * the draft's frontmatter carries exactly the runbook template's key set, with the import
    invariants pinned: status draft, version 1, both dates null, empty verification evidence;
  * recognizable source headings land in the matching template slot; unrecognized content lands in
    an explicit "Imported content (unmapped)" section — nothing is silently dropped;
  * every imported fenced command block carries an [unverified] marker;
  * Confluence macro elements (<ac:...>/<ri:...>) are counted and reported as conversion losses in
    the provenance, never silently mangled;
  * provenance (source file, title, optional URL, loss counts) is stamped into the draft.

Written before the converter existed and confirmed failing (fails-without-the-change rule).
Pure stdlib; run directly when the converter or its import contract changes. Gate A does not run
component tests.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONVERTER = ROOT / "skills" / "runbook" / "scripts" / "confluence_to_runbook.py"
# The published `schemas/runbook-frontmatter-v1.schema.json` was removed in the 2026-09-02
# retention pass, so the template is the frontmatter contract now (see test_runbook_schema.py).
# Pinning the converter to the template is the stronger binding anyway: the template is the file a
# human copies, so a converter that agrees with it agrees with what runbooks actually look like.
TEMPLATE_PATH = ROOT / "skills" / "runbook" / "assets" / "runbook-template.md"
IMPORT_REFERENCE = ROOT / "skills" / "runbook" / "references" / "confluence-import.md"

_TEMPLATE_KEY_RE = re.compile(r"^([a-z_][a-z0-9_]*):")


def template_frontmatter_keys() -> list[str]:
    """Top-level keys between the runbook template's first two `---` fences."""
    lines = TEMPLATE_PATH.read_text(encoding="utf-8").splitlines()
    keys: list[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            return keys
        match = _TEMPLATE_KEY_RE.match(line)
        if match:
            keys.append(match.group(1))
    raise AssertionError(f"{TEMPLATE_PATH}: frontmatter fence never closes")

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


def child_env() -> dict[str, str]:
    """Pin the child's stdout encoding so both ends of the pipe agree on every host.

    The report echoes source headings, so it carries whatever Unicode the page had. Without
    this pin the child encodes with an inherited PYTHONIOENCODING while `subprocess` decodes
    with the locale encoding, and any byte the locale lacks makes `proc.stdout` None instead
    of raising -- a decode error surfaces as an unrelated TypeError several assertions later.
    """
    return {**os.environ, "PYTHONIOENCODING": "utf-8"}


def run_converter(html: str, *args: str) -> tuple[subprocess.CompletedProcess, str]:
    """Run the converter on `html`, returning (proc, draft_text)."""
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "page.html"
        out = Path(tmp) / "draft.md"
        src.write_text(html, encoding="utf-8")
        proc = subprocess.run(
            [
                sys.executable,
                str(CONVERTER),
                str(src),
                "-o",
                str(out),
                "--service-id",
                "checkout-worker",
                *args,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=child_env(),
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
    def test_draft_revision_slot_accepts_short_commit_ids(self) -> None:
        self.assertEqual(
            frontmatter_fields(self.draft)["source_revision"],
            "<repository@short-commit or reviewed release identifier>",
        )

    def setUp(self) -> None:
        self.proc, self.draft = run_converter(
            VIEW_HTML, "--source-url", "https://example.atlassian.net/wiki/pages/123"
        )
        self.assertEqual(
            self.proc.returncode, 0,
            f"converter failed: stderr={self.proc.stderr[:500]!r}",
        )

    def test_frontmatter_matches_the_template_key_set(self) -> None:
        fields = frontmatter_fields(self.draft)
        self.assertEqual(sorted(fields), sorted(template_frontmatter_keys()))

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
        self.assertEqual(json.loads(fields["service_id"]), "checkout-worker")

    def test_invalid_service_id_fails_without_writing_a_draft(self) -> None:
        proc, draft = run_converter(
            VIEW_HTML,
            "--service-id",
            "checkout\ninjected: true",
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertEqual(draft, "")
        self.assertIn("service-id", proc.stderr)

    def test_empty_owner_fails_without_writing_a_draft(self) -> None:
        for owner in ("", "   "):
            with self.subTest(owner=owner):
                proc, draft = run_converter(VIEW_HTML, "--owner", owner)
                self.assertNotEqual(proc.returncode, 0)
                self.assertEqual(draft, "")
                self.assertIn("owner", proc.stderr)

    def test_owner_is_serialized_as_one_yaml_scalar(self) -> None:
        proc, draft = run_converter(VIEW_HTML, "--owner", "ops\ninjected: true")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        fields = frontmatter_fields(draft)
        self.assertEqual(sorted(fields), sorted(template_frontmatter_keys()))
        self.assertNotIn("injected", fields)
        self.assertEqual(json.loads(fields["owner"]), "ops\ninjected: true")

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

    def test_incident_history_uses_reviewable_provenance_not_retired_update_ids(self) -> None:
        self.assertIn(
            "Follow-up (disposition / PR or evidence reference)",
            self.draft,
        )
        self.assertNotIn("update id", self.draft.lower())
        self.assertNotIn("ol_ id", self.draft.lower())

    def test_report_survives_a_hostile_inherited_encoding(self) -> None:
        # The bug this pins: the child encoded with an inherited PYTHONIOENCODING while the parent
        # decoded with the locale encoding, so a curly quote the locale lacked killed the reader
        # thread and left proc.stdout as None -- surfacing as a TypeError, not a decode error.
        #
        # Setting a conflicting value here makes the mismatch reachable on every host instead of
        # only on one with a non-UTF-8 locale. Honest limit: this kills the child-env pin on any
        # host, but the parent's explicit decoder is unobservable where the locale is already
        # UTF-8 -- identical behavior -- so the Windows CI leg remains its only coverage.
        previous = os.environ.get("PYTHONIOENCODING")
        os.environ["PYTHONIOENCODING"] = "cp1252"
        try:
            proc, draft = run_converter(VIEW_HTML)
        finally:
            if previous is None:
                os.environ.pop("PYTHONIOENCODING", None)
            else:
                os.environ["PYTHONIOENCODING"] = previous
        self.assertIsNotNone(proc.stdout, "a decode failure silently nulls stdout")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # The exact non-ASCII the locale mismatch chokes on must round-trip, not be replaced.
        self.assertIn("“Restart the checkout worker”", proc.stdout)
        self.assertRegex(proc.stdout, r"[Mm]acro")
        self.assertIn("Restart the checkout worker", draft)

    def test_unreadable_input_fails_loudly(self) -> None:
        # Both paths live in a real temp dir so the case stays cross-platform (Gate A runs on
        # Windows too); the source path simply never gets created.
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "nonexistent" / "page.html"
            out = Path(tmp) / "draft.md"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(CONVERTER),
                    str(missing),
                    "-o",
                    str(out),
                    "--service-id",
                    "checkout-worker",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=child_env(),
                timeout=30,
            )
            self.assertEqual(proc.returncode, 1)
            self.assertIn("cannot read", proc.stderr)
            self.assertFalse(out.exists(), "no draft may be written on failure")


class ConfluenceContentTest(unittest.TestCase):
    def test_image_labels_cannot_create_markdown_headings_or_command_fences(self) -> None:
        for attribute, label in (
            ("diagram&#10;## Verification", r"diagram \#\# Verification"),
            ("diagram&#13;&#10;&#9;&#x2028;## Verification", r"diagram \#\# Verification"),
            ("diagram&#10;```sh&#10;danger-command&#10;```",
             r"diagram \`\`\`sh danger\-command \`\`\`"),
            ("diagram&#10;~~~sh&#10;danger-command&#10;~~~",
             r"diagram \~\~\~sh danger\-command \~\~\~"),
        ):
            with self.subTest(attribute=attribute):
                proc, draft = run_converter(
                    '<p>Before.</p><img src="diagram.png" alt="' + attribute + '">'
                    '<p>Ordinary following content.</p>'
                )
                self.assertEqual(0, proc.returncode, proc.stderr)
                body = draft.split("## Purpose & scope\n\n", 1)[1].split("\n## Trigger", 1)[0]
                self.assertEqual(
                    f"Before.\n\nImage: [{label}](<diagram.png>)\n\nOrdinary following content.\n",
                    body,
                )
                self.assertIn("Image attachments not copied: 1", proc.stdout)

    def test_reference_labels_preserve_text_and_destinations_as_literal_markdown(self) -> None:
        proc, draft = run_converter(
            '<p><a href="https://example.com/console?q=1&amp;b=2">'
            'Ops [primary] *console* _status_ `check` &lt;b&gt;</a> ordinary following text.</p>'
            '<img src="../diagram v1.png" alt="  plain&#9;diagram&#13;&#10;label  ">'
        )
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertIn(
            r'[Ops \[primary\] \*console\* \_status\_ \`check\` \<b\>](<https://example.com/console?q=1&b=2>)'
            ' ordinary following text.',
            draft,
        )
        self.assertIn('[plain diagram label](<../diagram%20v1.png>)', draft)
        self.assertIn("Unusable link or image destinations: 0", proc.stdout)

    def test_unsupported_media_suppresses_descendants_and_resumes_afterward(self) -> None:
        # iframe is raw text: its first </iframe> closes it, so it cannot nest another iframe.
        for tag, child, count in (
            ("svg", "svg", 2), ("video", "video", 2), ("audio", "audio", 2),
            ("iframe", "div", 1), ("object", "object", 2),
        ):
            with self.subTest(tag=tag):
                proc, draft = run_converter(
                    f'<p>Visible before.</p><{tag}><{child}>nested-hidden</{child}>'
                    '<div><br><img src="hidden.png">fallback-hidden '
                    '<a href="https://example.com/hidden">link-hidden</a></div>'
                    '<ac:structured-macro><ac:parameter>macro-hidden</ac:parameter>'
                    f'</ac:structured-macro></{tag}><p>Visible after.</p>'
                )
                self.assertEqual(0, proc.returncode, proc.stderr)
                self.assertIn("Visible before.", draft)
                self.assertIn("Visible after.", draft)
                self.assertNotIn("hidden", draft)
                for output in (draft, proc.stdout):
                    self.assertIn(f"Unsupported media dropped: {count}", output)

    def test_void_and_self_closing_media_do_not_suppress_following_content(self) -> None:
        for media, count in (
            ("<embed>", 1), ("<embed/>", 1), ("<svg/>", 1), ("<video/>", 1),
            ("<svg><g/><text>hidden</text></svg>", 1),
            ("<video><embed><svg/><source>hidden</video>", 3),
        ):
            with self.subTest(media=media):
                proc, draft = run_converter(media + '<p>Retained afterward.</p>')
                self.assertEqual(0, proc.returncode, proc.stderr)
                self.assertIn("Retained afterward.", draft)
                self.assertNotIn("hidden", draft)
                self.assertIn(f"Unsupported media dropped: {count}", proc.stdout)

    def test_anchor_line_breaks_preserve_one_destination_without_link_bleed(self) -> None:
        proc, draft = run_converter(
            '<p>Open <a href="https://example.com/recovery">recovery<br>'
            '<em>console</em><br/>guide</a> outside-first. '
            '<a href="#next">next<br>step</a> outside-second.</p><p>Following paragraph.</p>'
        )
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertIn('[recovery console guide](<https://example.com/recovery>) outside-first.', draft)
        self.assertIn('[next step](<#next>) outside-second.', draft)
        self.assertIn("Following paragraph.", draft)
        self.assertEqual(1, draft.count("https://example.com/recovery"))

    def test_line_breaks_do_not_activate_an_unsafe_anchor_destination(self) -> None:
        proc, draft = run_converter(
            '<p><a href="javascript:alert(1)">unsafe<br>label</a> ordinary text.</p>'
        )
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertIn("unsafe label ordinary text.", draft)
        self.assertNotIn("javascript:", draft)
        self.assertIn("Unusable link or image destinations: 1", proc.stdout)

    def test_rendered_links_and_image_references_survive_with_loss_accounting(self) -> None:
        proc, draft = run_converter(
            '<title>Recovery</title><h2>Procedure</h2><p>Open '
            '<a href="https://example.com/recovery">recovery <em>console</em></a>.</p>'
            '<img src="diagram.png" alt="failure isolation diagram">'
            '<iframe src="https://example.com/embed"></iframe>'
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('[recovery console](<https://example.com/recovery>)', draft)
        self.assertIn('[failure isolation diagram](<diagram.png>)', draft)
        for output in (draft, proc.stdout):
            self.assertIn('Image attachments not copied: 1', output)
            self.assertIn('Unsupported media dropped: 1', output)

    def test_unsafe_link_destinations_are_reported_without_becoming_active_links(self) -> None:
        proc, draft = run_converter(
            '<title>Recovery</title><p><a href="javascript:alert(1)">console</a></p>'
            '<img src="data:text/html,unsafe" alt="diagram">'
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('console', draft)
        self.assertIn('diagram', draft)
        self.assertNotIn('javascript:', draft)
        self.assertNotIn('data:text/html', draft)
        for output in (draft, proc.stdout):
            self.assertIn('Unusable link or image destinations: 2', output)

    def test_h1_supplies_the_title_when_the_export_has_no_title_element(self) -> None:
        proc, draft = run_converter('<h1>Restart payments</h1><p>Read the runbook.</p>')
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('# Runbook: Restart payments', draft)
        self.assertEqual(frontmatter_fields(draft)['runbook_id'], 'restart-payments')


class ConfluenceImportReferenceTest(unittest.TestCase):
    def test_export_example_prompts_for_token_instead_of_putting_it_in_argv(self) -> None:
        reference = IMPORT_REFERENCE.read_text(encoding="utf-8")
        self.assertNotIn("$CONFLUENCE_API_TOKEN", reference)
        self.assertIn('--user "user@example.com"', reference)
        self.assertIn("prompts for the API token", reference)
        self.assertIn("--fail-with-body", reference)
        self.assertIn("--exit-status --raw-output", reference)
        self.assertIn(".body.view.value", reference)
        self.assertIn("> page.html", reference)


if __name__ == "__main__":
    unittest.main()
