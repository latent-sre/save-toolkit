"""Dashboard export exercises the real artifact boundary and HTML trust boundary."""
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

from fleet_atlas_dashboard import export, payload, render
from fleet_atlas_v2_artifacts import OUTPUT, build
from test_fleet_atlas_v2_artifacts import fixture_extract


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for args in (("init", "-q"), ("config", "user.name", "Atlas test"),
                     ("config", "user.email", "atlas@example.invalid")):
            self.git(*args)
        (self.root / "README.md").write_text("live\n", encoding="utf-8")
        self.git("add", "README.md")
        self.git("commit", "-qm", "fixture")
        self.output = self.root / ".eval-runs/dashboard.html"

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True).stdout

    def test_real_verified_export_preserves_complete_citations_and_sources(self):
        doc = build(self.root, fixture_extract)
        export(self.root, self.output, loader=fixture_extract)
        html = self.output.read_text(encoding="utf-8")
        encoded = re.search(r'<script id="atlas-data" type="application/json">(.*?)</script>', html, re.S)[1]
        data = json.loads(encoded)
        self.assertEqual(doc.revision, data["revision"])
        self.assertEqual("live\n", data["sources"]["README.md"])
        self.assertEqual("verified", data["facts"][0]["label"])
        self.assertEqual(1, data["facts"][0]["citations"][0]["start"])
        self.assertIn("blobHash", data["facts"][0]["citations"][0])
        self.assertIn("connect-src 'none'", html)

    def test_missing_stale_and_tampered_artifacts_never_emit_dashboard(self):
        with self.assertRaises(ValueError):
            export(self.root, self.output, loader=fixture_extract)
        build(self.root, fixture_extract)
        (self.root / OUTPUT / "INDEX.md").write_text("tampered", encoding="utf-8")
        with self.assertRaises(ValueError):
            export(self.root, self.output, loader=fixture_extract)
        build(self.root, fixture_extract)
        (self.root / "README.md").write_text("changed\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            export(self.root, self.output, loader=fixture_extract)
        self.git("add", "README.md")
        self.git("commit", "-qm", "changed canonical source without rebuilding")
        with self.assertRaises(ValueError):
            export(self.root, self.output, loader=fixture_extract)
        self.assertFalse(self.output.exists())

    def test_script_breakout_is_data_and_csp_does_not_allow_injected_script(self):
        value = '</script><script>globalThis.pwned=1</script><!--&>\u2028\u2029__ATLAS_CSP____ATLAS_DATA__'
        template = '<meta content="__ATLAS_CSP__"><script id="atlas-data" type="application/json">__ATLAS_DATA__</script><script>const safe = true;</script>'
        html = render({"value": value}, template)
        self.assertEqual(2, len(re.findall(r"<script\b", html)))
        encoded = re.search(r'application/json">(.*?)</script>', html, re.S)[1]
        self.assertEqual(value, json.loads(encoded)["value"])
        self.assertNotIn("<script>globalThis.pwned", html)
        self.assertEqual(1, html.count("'sha256-"))

    def test_cannot_overwrite_sources_or_existing_output(self):
        build(self.root, fixture_extract)
        for path in (self.root / "docs/dashboard.html", self.root / OUTPUT / "dashboard.html"):
            with self.assertRaises(ValueError):
                export(self.root, path, loader=fixture_extract)
        self.output.parent.mkdir()
        self.output.write_text("keep", encoding="utf-8")
        with self.assertRaises(ValueError):
            export(self.root, self.output, loader=fixture_extract)
        self.assertEqual("keep", self.output.read_text())

    def test_plain_data_cannot_claim_verification(self):
        with self.assertRaises(TypeError):
            payload({"verified": True})

    def test_browser_line_numbers_use_verifier_line_boundaries(self):
        (self.root / "README.md").write_bytes("live\rsecond\u2028third\u2029fourth\x85fifth\n".encode())
        self.git("add", "README.md")
        self.git("commit", "-qm", "source with mixed line separators")
        data = payload(build(self.root, fixture_extract))
        self.assertEqual(["live", "second", "third", "fourth", "fifth"], data["sourceLines"]["README.md"])


if __name__ == "__main__":
    unittest.main()
