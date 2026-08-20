#!/usr/bin/env python3
"""Regression tests for the local Codex authentication guidance."""
from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LocalCodexAuthDocsTests(unittest.TestCase):
    def test_operator_guide_names_chatgpt_login_and_rejects_api_key_prerequisite(self) -> None:
        guide = (ROOT / "evals/README.md").read_text(encoding="utf-8")

        self.assertIn("codex login status", guide)
        self.assertIn("Logged in using ChatGPT", guide)
        self.assertIn("`OPENAI_API_KEY` is not required", guide)
        self.assertIn("Never print, paste, or commit `auth.json`", guide)

    def test_governing_docs_keep_the_same_authentication_contract(self) -> None:
        decision = (
            ROOT / "docs/decisions/2026-08-01-local-sol-conformance.md"
        ).read_text(encoding="utf-8")
        contributing = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")

        for document in (decision, contributing):
            self.assertIn("ChatGPT-authenticated Codex", document)
            self.assertIn("`OPENAI_API_KEY` is not required", document)


if __name__ == "__main__":
    unittest.main()
