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

    def test_explicit_recovery_headings_win_over_generic_step_words(self) -> None:
        proc, draft = run_converter(
            "<h1>Recovery</h1>"
            "<h2>Rollback steps</h2><p>Restore the previous artifact.</p>"
            "<h2>Verification steps</h2><p>Confirm healthy traffic.</p>"
        )
        self.assertEqual(0, proc.returncode, proc.stderr)
        rollback = draft.split("## Rollback / cleanup\n\n", 1)[1].split("\n## Escalation", 1)[0]
        verification = draft.split("## Verification\n\n", 1)[1].split("\n## Rollback", 1)[0]
        procedure = draft.split("## Procedure\n\n", 1)[1].split("\n## Verification", 1)[0]
        self.assertIn("Restore the previous artifact.", rollback)
        self.assertIn("Confirm healthy traffic.", verification)
        self.assertNotIn("Restore the previous artifact.", procedure)
        self.assertNotIn("Confirm healthy traffic.", procedure)

    def test_unrecognized_content_is_kept_not_dropped(self) -> None:
        self.assertIn("Imported content (unmapped)", self.draft)
        unmapped = self.draft.split("Imported content (unmapped)", 1)[1]
        self.assertIn("architecture space", unmapped)

    def test_imported_commands_are_marked_unverified(self) -> None:
        self.assertIn("cf app checkout-worker", self.draft)
        block_and_after = self.draft.split("cf app checkout-worker", 1)[1]
        self.assertIn("[unverified]", block_and_after[:300])

    def test_code_fence_is_longer_than_backticks_inside_the_command(self) -> None:
        command = "cat <<'EOF'\n```\nliteral document sample\n```\nEOF"
        proc, draft = run_converter(
            "<h1>Recovery</h1><h2>Procedure</h2><pre>" + command + "</pre>"
        )
        self.assertEqual(0, proc.returncode, proc.stderr)
        procedure = draft.split("## Procedure\n\n", 1)[1].split("\n## Verification", 1)[0]
        self.assertIn("````\n" + command + "\n````", procedure)
        self.assertEqual(1, procedure.count("*Imported command — [unverified] until rehearsed on the target.*"))

    def test_ordered_list_numbers_survive_and_flattened_tables_are_reported(self) -> None:
        proc, draft = run_converter(
            '<h1>Recovery</h1><h2>Procedure</h2><ol start="3">'
            '<li>Inspect.</li><li>If unsafe, return to step 3.</li></ol>'
            '<table><tr><th>State</th><th>Action</th></tr>'
            '<tr><td>Running</td><td>Wait</td></tr></table>'
        )
        self.assertEqual(0, proc.returncode, proc.stderr)
        procedure = draft.split("## Procedure\n\n", 1)[1].split("\n## Verification", 1)[0]
        self.assertIn("3. Inspect.", procedure)
        self.assertIn("4. If unsafe, return to step 3.", procedure)
        for output in (draft, proc.stdout):
            self.assertIn("HTML tables flattened: 1", output)

    def test_ordered_numbers_attach_to_paragraph_wrapped_items_with_a_nested_list(self) -> None:
        proc, draft = run_converter(
            '<h1>Recovery</h1><h2>Procedure</h2><ol start="3">'
            '<li><p>Inspect.</p><ul><li>Check the dependency.</li></ul></li>'
            '<li><p>Continue.</p></li></ol>'
        )
        self.assertEqual(0, proc.returncode, proc.stderr)
        procedure = draft.split("## Procedure\n\n", 1)[1].split("\n## Verification", 1)[0]
        self.assertIn("3. Inspect.", procedure)
        self.assertIn("\n   - Check the dependency.\n", procedure)
        self.assertIn("4. Continue.", procedure)

    def test_list_continuations_and_nested_commands_stay_with_their_step(self) -> None:
        proc, draft = run_converter(
            '<h1>Recovery</h1><h2>Procedure</h2><ol start="10">'
            '<li><p>Inspect.</p><ul><li><p>Check.</p><pre>cf app worker</pre></li></ul>'
            '<p>Only then continue.</p></li><li>Finish.</li></ol><p>Outside.</p>'
        )
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertIn("10. Inspect.\n\n    - Check.", draft)
        self.assertIn("\n      ```\n      cf app worker\n      ```", draft)
        self.assertIn("\n    Only then continue.\n\n11. Finish.\n\nOutside.", draft)

    def test_explicit_and_reversed_step_labels_survive_markdown(self) -> None:
        cases = [
            ('<ol><li value="5">Five.</li><li>Six.</li></ol>', '5. Five.\n\n6. Six.'),
            ('<ol reversed start="5"><li>Five.</li><li>Four.</li></ol>', '- **5.** Five.\n\n- **4.** Four.'),
            ('<ol reversed><li>Two.</li><li>One.</li></ol>', '- **2.** Two.\n\n- **1.** One.'),
            ('<ol><li>One.</li><li value="5">Five.</li><li>Six.</li></ol>',
             '- **1.** One.\n\n- **5.** Five.\n\n- **6.** Six.'),
            ('<ol reversed><li>Three.<ul><li>Child.</li></ul></li>'
             '<li value="7">Seven.</li><li>Six.</li></ol>',
             '- **3.** Three.\n\n  - Child.\n\n- **7.** Seven.\n\n- **6.** Six.'),
        ]
        for html, expected in cases:
            with self.subTest(html=html):
                proc, draft = run_converter('<h1>Recovery</h1><h2>Procedure</h2>' + html)
                self.assertEqual(0, proc.returncode, proc.stderr)
                self.assertIn(expected, draft)

    def test_missing_output_parent_is_created_for_first_import(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "page.html"
            output = root / "docs" / "runbooks" / "draft.md"
            source.write_text(VIEW_HTML, encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(CONVERTER),
                    str(source),
                    "-o",
                    str(output),
                    "--service-id",
                    "checkout-worker",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=child_env(),
                timeout=30,
            )
            self.assertEqual(0, proc.returncode, proc.stderr)
            self.assertTrue(output.is_file())

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
    def test_titles_remain_one_literal_heading_before_the_import_warning(self) -> None:
        cases = (
            ("Restart payments", "Restart payments", "Restart payments", "restart-payments"),
            ("Recovery&#13;&#10;&#9;## Verification", "Recovery ## Verification",
             r"Recovery \#\# Verification", "recovery-verification"),
            ("Recovery&#10;```sh&#10;danger-command&#10;```", "Recovery ```sh danger-command ```",
             r"Recovery \`\`\`sh danger\-command \`\`\`", "recovery-sh-danger-command"),
            ("Recovery&#x2028;~~~sh&#10;danger-command&#10;~~~", "Recovery ~~~sh danger-command ~~~",
             r"Recovery \~\~\~sh danger\-command \~\~\~", "recovery-sh-danger-command"),
        )
        for tag in ("h1", "title"):
            for encoded, semantic, rendered, runbook_id in cases:
                with self.subTest(tag=tag, encoded=encoded):
                    proc, draft = run_converter(f'<{tag}>{encoded}</{tag}><p>Ordinary body.</p>')
                    self.assertEqual(0, proc.returncode, proc.stderr)
                    prefix, warning, remainder = draft.partition("> **Imported draft.**")
                    self.assertTrue(warning)
                    self.assertEqual(
                        f"\n# Runbook: {rendered}\n\n", prefix.split("\n---\n", 1)[1],
                    )
                    fields = frontmatter_fields(draft)
                    self.assertEqual(sorted(template_frontmatter_keys()), sorted(fields))
                    self.assertEqual(runbook_id, fields["runbook_id"])
                    self.assertIn(f"“{semantic}”", proc.stdout.splitlines()[0])
                    self.assertIn(f"- Source page title: “{rendered}”", draft)
                    self.assertIn("Ordinary body.", remainder)

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


def run_on(name: str, content: str, *args: str, env: dict[str, str] | None = None,
           existing: str | None = None) -> tuple[subprocess.CompletedProcess, str]:
    """Run the converter on a source file called `name`; its suffix selects page JSON or HTML."""
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / name
        out = Path(tmp) / "draft.md"
        src.write_text(content, encoding="utf-8")
        if existing is not None:
            out.write_text(existing, encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(CONVERTER), str(src), "-o", str(out), "--service-id", "order-router", *args],
            capture_output=True, text=True, encoding="utf-8", env=env or child_env(), timeout=30,
        )
        draft = out.read_text(encoding="utf-8") if out.exists() else ""
    return proc, draft


def slot_text(draft: str, slot: str) -> str:
    return draft.split(f"## {slot}\n\n", 1)[1].split("\n## ", 1)[0]


class ConfluenceImportPathTest(unittest.TestCase):
    """The documented import path: page JSON in, provenance kept, nothing silently lost or replaced."""

    PAGE_JSON = json.dumps({
        "id": "123",
        "title": "Restart the order router",
        "version": {"number": 7, "createdAt": "2026-09-01T10:00:00.000Z"},
        "body": {"view": {"value": "<h1>Symptoms</h1><p>Order queue depth keeps growing.</p>"
                                    "<h1>Steps</h1><ol><li>Check the router state.</li></ol>"}},
    })

    def test_page_json_supplies_title_version_and_keeps_every_h1_section(self) -> None:
        proc, draft = run_on("page.json", self.PAGE_JSON)
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertEqual("restart-the-order-router", frontmatter_fields(draft)["runbook_id"])
        self.assertIn("Order queue depth keeps growing.", slot_text(draft, "Trigger"))
        self.assertIn("Check the router state.", slot_text(draft, "Procedure"))
        self.assertIn("- Source page version: 7", draft)
        self.assertIn("- Source page last modified: 2026-09-01T10:00:00.000Z", draft)
        self.assertNotIn("warning", proc.stdout)

    def test_data_center_page_json_supplies_its_modified_date(self) -> None:
        page = json.loads(self.PAGE_JSON)
        page["version"] = {"number": 3, "when": "2025-11-02T08:30:00.000Z"}
        proc, draft = run_on("page.json", json.dumps(page))
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertIn("- Source page version: 3", draft)
        self.assertIn("- Source page last modified: 2025-11-02T08:30:00.000Z", draft)

    def test_page_json_without_a_view_body_fails_without_a_draft(self) -> None:
        storage_only = json.dumps({"title": "Restart", "body": {"storage": {"value": "<p>x</p>"}}})
        proc, draft = run_on("page.json", storage_only)
        self.assertEqual(1, proc.returncode)
        self.assertIn("body-format=view", proc.stderr)
        self.assertEqual("", draft)

    def test_html_without_version_leaves_visible_fill_in_lines(self) -> None:
        proc, draft = run_on("page.html", VIEW_HTML)
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertIn("- Source page version: <fill in — page history>", draft)
        self.assertIn("- Source page last modified: <fill in — page history>", draft)

    def test_title_flag_keeps_a_bare_fragments_first_h1_as_a_section(self) -> None:
        fragment = "<h1>Symptoms</h1><p>Order queue depth keeps growing.</p>"
        proc, draft = run_on("page.html", fragment, "--title", "Restart the order router")
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertEqual("restart-the-order-router", frontmatter_fields(draft)["runbook_id"])
        self.assertIn("Order queue depth keeps growing.", slot_text(draft, "Trigger"))

    def test_an_untitled_fragment_warns_instead_of_silently_naming_it_after_the_file(self) -> None:
        proc, _ = run_on("page.html", "<h2>Steps</h2><p>Check the router state.</p>")
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertIn("no page title found", proc.stdout)
        self.assertIn("--title", proc.stdout)

    def test_existing_output_is_refused_unless_forced(self) -> None:
        history = "| 2026-02-18 | INC-8841 | 3 | steps 1-2 | — | PR #412 |\n"
        proc, draft = run_on("page.json", self.PAGE_JSON, existing=history)
        self.assertEqual(1, proc.returncode)
        self.assertIn("--force", proc.stderr)
        self.assertEqual(history, draft, "an existing runbook and its history must survive")
        proc, draft = run_on("page.json", self.PAGE_JSON, "--force", existing=history)
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertIn("restart-the-order-router", draft)

    def test_report_prints_non_ascii_headings_on_a_legacy_stdout(self) -> None:
        # Captured stdout (an agent's Bash, CI, `> log`) can default to a legacy code page; the draft
        # is written before the report prints, so an encode error there left a draft and exit 1.
        env = {**os.environ, "PYTHONIOENCODING": "ascii"}
        html = "<h1>Recovery</h1><h2>⚠️ Rollback → safe path</h2><p>Undo the change.</p>"
        proc, _ = run_on("page.html", html, env=env)
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertIn("⚠️ Rollback → safe path", proc.stdout)

    def test_headings_match_word_starts_and_contacts_outrank_alerts(self) -> None:
        proc, draft = run_on(
            "page.html",
            "<h1>Recovery</h1>"
            "<h2>Escalation process</h2><p>Page the trading lead.</p>"
            "<h2>Alert contacts</h2><p>Trading on-call rota.</p>"
            "<h2>Prefix conventions</h2><p>Queue names use the desk prefix.</p>",
        )
        self.assertEqual(0, proc.returncode, proc.stderr)
        escalation = slot_text(draft, "Escalation")
        self.assertIn("Page the trading lead.", escalation)
        self.assertIn("Trading on-call rota.", escalation)
        self.assertNotIn("desk prefix", slot_text(draft, "Procedure"))
        self.assertIn("desk prefix", draft.split("Imported content (unmapped)", 1)[1])


class ConfluenceImportReferenceTest(unittest.TestCase):
    def test_export_example_prompts_for_token_instead_of_putting_it_in_argv(self) -> None:
        reference = IMPORT_REFERENCE.read_text(encoding="utf-8")
        self.assertNotIn("$CONFLUENCE_API_TOKEN", reference)
        self.assertIn('--user "user@example.com"', reference)
        self.assertIn("prompts for the API token", reference)
        self.assertIn("--fail-with-body", reference)
        # The page JSON goes to the converter whole, so the title, version, and modified date
        # survive and a missing view body fails in the converter (tested above), not in a jq step.
        self.assertIn("?body-format=view", reference)
        self.assertIn('"<resolved converter path>" page.json', reference)
        self.assertIn("refuses a JSON without a view body", reference)


if __name__ == "__main__":
    unittest.main()
