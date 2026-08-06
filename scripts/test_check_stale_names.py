"""Contract tests for scripts/check_stale_names.py.

This checker had no test. It runs in Gate A only against the real tree, where it currently matches
nothing — so if STALE_RE, the word-boundary logic, or the path/`.md` carve-outs silently broke, the
checker would still print PASS and Gate A would stay green. That is this repo's own documented
failure mode ("a rule that asserts nothing"). These tests feed it known-bad and known-good input so
a future refactor that neuters it fails loudly instead.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_stale_names


class StaleNamesTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="stale-names-")
        self.root = Path(self._tmp.name)
        (self.root / "skills").mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write(self, relative: str, text: str) -> None:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")

    def _a_stale_name(self) -> str:
        # Pick a retired name that is NOT an ordinary English word, so the assertion is about the
        # guard firing, not about a carve-out. `sre-tool` is a retired unit name in STALE.
        assert "sre-tool" in check_stale_names.STALE
        return "sre-tool"

    def test_the_real_repo_is_clean(self) -> None:
        # Anchors the suite: if the live tree ever trips the checker, every test below is suspect.
        self.assertEqual([], check_stale_names.check(check_stale_names.ROOT))

    def test_a_seeded_retired_name_in_prose_is_caught(self) -> None:
        self._write("skills/probe/SKILL.md", f"Route it to the {self._a_stale_name()} skill.\n")
        failures = check_stale_names.check(self.root)
        self.assertTrue(
            any("stale fleet-unit name" in f and self._a_stale_name() in f for f in failures),
            failures,
        )

    def test_clean_prose_is_silent(self) -> None:
        self._write("skills/probe/SKILL.md", "Route it to the reviewer agent.\n")
        self.assertEqual([], check_stale_names.check(self.root))

    def test_a_path_or_md_reference_is_exempt(self) -> None:
        # The carve-out that keeps a reintroduced name usable as a real filename: a match adjacent to
        # `/` or immediately followed by `.md` is skipped. `api-design` is a retired unit name that
        # now also ships as api-design.md; the link form must NOT trip the guard.
        stale_file_token = "api-design"
        self.assertIn(stale_file_token, check_stale_names.STALE)
        self._write(
            "skills/probe/SKILL.md",
            f"See [API surface design](references/{stale_file_token}.md) and "
            f"`references/{stale_file_token}.md`.\n",
        )
        self.assertEqual([], check_stale_names.check(self.root))

    def test_the_same_reintroduced_name_in_prose_is_still_caught(self) -> None:
        # The other half of the carve-out: the filename is exempt, but a bareword prose reference to
        # the retired UNIT is still a finding — the guard is narrowed, not disabled.
        self._write("skills/probe/SKILL.md", "load the api-design skill first\n")
        failures = check_stale_names.check(self.root)
        self.assertTrue(any("api-design" in f for f in failures), failures)

    def test_word_boundary_prevents_substring_false_positive(self) -> None:
        # A retired name embedded in a longer token must not match (the boundary logic is load-
        # bearing: `sre` is a strict prefix of `sre-tool`, `observer`, etc.).
        self._write("skills/probe/SKILL.md", "the observerpattern helper and researcherxyz\n")
        self.assertEqual([], check_stale_names.check(self.root))

    def test_only_skills_agents_commands_are_scanned(self) -> None:
        # A stale name in docs/ or scripts/ is out of scope by design.
        self._write("docs/note.md", f"mentions {self._a_stale_name()} freely\n")
        self.assertEqual([], check_stale_names.check(self.root))


if __name__ == "__main__":
    unittest.main()
