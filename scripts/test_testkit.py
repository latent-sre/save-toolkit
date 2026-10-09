"""The shared test helpers must fail loudly; a helper that quietly matches nothing hides a test."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import testkit


class MarkdownHelperTests(unittest.TestCase):
    TEXT = "# T\n\n## Evidence base\nwrong\n## Evidence\nright\n### Detail\nkept\n## Next\nout\n"

    def test_section_matches_the_exact_heading_and_keeps_deeper_headings(self) -> None:
        self.assertEqual("\nright\n### Detail\nkept\n", testkit.markdown_section(self.TEXT, "## Evidence"))
        self.assertEqual("\nkept\n", testkit.markdown_section(self.TEXT, "### Detail"))

    def test_a_missing_heading_or_a_non_heading_is_an_error(self) -> None:
        with self.assertRaises(AssertionError):
            testkit.markdown_section(self.TEXT, "### Evidence")
        with self.assertRaises(ValueError):
            testkit.markdown_section(self.TEXT, "Evidence")

    def test_frontmatter_block_requires_a_closed_opening_fence(self) -> None:
        self.assertEqual("name: x\n", testkit.frontmatter_block("---\nname: x\n---\nbody --- here\n"))
        for text in ("name: x\n---\n", "---\nname: x\n", "\n---\nname: x\n---\n"):
            with self.subTest(text=text), self.assertRaises(AssertionError):
                testkit.frontmatter_block(text)

    def test_normalized_ignores_case_and_wrapping(self) -> None:
        self.assertEqual(testkit.normalized("One  Two\nthree"), testkit.normalized("one two three "))


class MutationAndLoadingTests(unittest.TestCase):
    def test_must_replace_refuses_a_mutation_that_matches_nothing(self) -> None:
        self.assertEqual("a-b a", testkit.must_replace("a a a", " a", "-b"))
        self.assertEqual("a-b-b", testkit.must_replace("a a a", " a", "-b", count=-1))
        with self.assertRaises(AssertionError):
            testkit.must_replace("text", "absent", "x")

    def test_load_path_registers_the_module_and_unregisters_a_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            good, bad = Path(tmp, "good.py"), Path(tmp, "bad.py")
            good.write_text("from dataclasses import dataclass\n@dataclass\nclass Row:\n    value: int\n",
                            encoding="utf-8")
            bad.write_text("raise RuntimeError('boom')\n", encoding="utf-8")
            try:
                module = testkit.load_path(good, "testkit_probe_good")
                self.assertIs(sys.modules["testkit_probe_good"], module)
                self.assertEqual(1, module.Row(1).value)
                with self.assertRaises(RuntimeError):
                    testkit.load_path(bad, "testkit_probe_bad")
                self.assertNotIn("testkit_probe_bad", sys.modules)
            finally:
                sys.modules.pop("testkit_probe_good", None)


if __name__ == "__main__":
    unittest.main()
