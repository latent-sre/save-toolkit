#!/usr/bin/env python3
"""Offline tests for check_canary_tokens.py. Stdlib only, no network, no model.

Each rule is exercised against a purpose-built fixture tree so a mutation to the validator has
something that fails, and then the live repository is asserted clean. Fixture-first matters here:
a suite that only asserted "the real tree passes" would still pass if the validator were mutated
into always returning no failures.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import check_canary_tokens


def _tree(root: Path, files: dict[str, str]) -> None:
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


class CheckCanaryTokensTest(unittest.TestCase):
    def test_clean_fixture_tree_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _tree(root, {
                "skills/obs-metrics/references/promql.md": "body\n\nq_ompr_0001\n",
                "skills/obs-logs/references/logql.md": "body\n\nq_ollq_0002\n",
                "skills/akamai-edge/references/edge.md": "body\n\nq_akedge_0003\n",
                "skills/incident-investigation/references/first-response.md": "body\n\nq_iifr_0004\n",
                # a bundle outside REQUIRED_GLOBS may carry no token at all
                "skills/backend-craft/references/api.md": "no token here\n",
            })
            self.assertEqual(check_canary_tokens.check(root), [])

    def test_duplicate_token_across_files_is_a_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _tree(root, {
                "skills/obs-metrics/references/promql.md": "q_dup_0001\n",
                "skills/obs-metrics/references/wql.md": "q_dup_0001\n",
                "skills/akamai-edge/references/edge.md": "q_akedge_0003\n",
                "skills/incident-investigation/references/first-response.md": "q_iifr_0004\n",
            })
            failures = check_canary_tokens.check(root)
            self.assertEqual(len(failures), 1, failures)
            self.assertIn("q_dup_0001", failures[0])
            self.assertIn("promql.md", failures[0])
            self.assertIn("wql.md", failures[0])

    def test_missing_token_in_a_required_bundle_is_a_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _tree(root, {
                "skills/obs-traces/references/traceql.md": "body with no token\n",
                "skills/akamai-edge/references/edge.md": "q_akedge_0003\n",
                "skills/incident-investigation/references/first-response.md": "q_iifr_0004\n",
            })
            failures = check_canary_tokens.check(root)
            self.assertEqual(len(failures), 1, failures)
            self.assertIn("traceql.md", failures[0])
            self.assertIn("carries none", failures[0])

    def test_a_required_glob_matching_nothing_is_a_failure(self) -> None:
        """Guards the instrument: a typo'd glob would make the presence rule vacuous."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _tree(root, {"skills/obs-logs/references/logql.md": "q_ollq_0002\n"})
            failures = check_canary_tokens.check(root)
            self.assertTrue(
                any("matches no files" in f and "akamai" in f for f in failures), failures
            )

    def test_token_grammar_rejects_near_misses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _tree(root, {
                # `q_ab` is too short and `Q_UPPER_0001` is the wrong case: neither is a token, so
                # the required-bundle file counts as carrying none.
                "skills/obs-logs/references/logql.md": "q_ab and Q_UPPER_0001\n",
                "skills/akamai-edge/references/edge.md": "q_akedge_0003\n",
                "skills/incident-investigation/references/first-response.md": "q_iifr_0004\n",
            })
            failures = check_canary_tokens.check(root)
            self.assertTrue(any("logql.md" in f and "carries none" in f for f in failures), failures)

    def test_the_live_repository_satisfies_both_rules(self) -> None:
        self.assertEqual(check_canary_tokens.check(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
