#!/usr/bin/env python3
"""Offline tests for check_query_catalog.py. Stdlib only, no network, no model.

Fixture-first: each rule is exercised against a purpose-built tree so a mutation to the validator
has something that fails, and only then is the live repository asserted clean. A suite that only
asserted "the real tree passes" would still pass if the validator were mutated into a no-op.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import check_query_catalog


GOOD_ENTRY = """# Catalog

## Splunk (SPL)

### Which errors started at the same time as the impact?

- **Applies to:** any service
- **Reads as:** one row per error class
- **Healthy looks like:** flat background rate
- **Owner:** `<service on-call>`
- **Verified:** [unverified]

```spl
index=<app_index> earliest=-60m | stats count by error_type
```
"""


def _tree(root: Path, body: str) -> Path:
    path = root / "skills/obs-logs/references/query-catalog.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return root


class CheckQueryCatalogTest(unittest.TestCase):
    def test_a_complete_entry_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual([], check_query_catalog.check(_tree(Path(tmp), GOOD_ENTRY)))

    def test_a_missing_field_is_a_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            body = GOOD_ENTRY.replace("- **Healthy looks like:** flat background rate\n", "")
            failures = check_query_catalog.check(_tree(Path(tmp), body))
            self.assertTrue(any("Healthy looks like:" in f for f in failures), failures)

    def test_an_entry_without_a_query_block_is_a_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            body = GOOD_ENTRY[: GOOD_ENTRY.index("```spl")]
            failures = check_query_catalog.check(_tree(Path(tmp), body))
            self.assertTrue(any("carries no query block" in f for f in failures), failures)

    def test_an_unlabelled_fence_is_a_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            body = GOOD_ENTRY.replace("```spl", "```")
            failures = check_query_catalog.check(_tree(Path(tmp), body))
            self.assertTrue(any("unlabelled query fence" in f for f in failures), failures)

    def test_a_credential_assignment_is_a_failure(self) -> None:
        for literal in (
            ("index=app token=s3cr3tvalue earliest=-1h", "credential"),
            ("index=app | where session_id=9f3c2a11b4", "session or user identifier"),
            ('index=app Authorization="Bearer abc123def456"', "credential"),
        ):
            literal, expected = literal
            with self.subTest(literal=literal), tempfile.TemporaryDirectory() as tmp:
                body = GOOD_ENTRY.replace("index=<app_index> earliest=-60m | stats count by error_type", literal)
                failures = check_query_catalog.check(_tree(Path(tmp), body))
                self.assertTrue(any(expected in f for f in failures), failures)

    def test_a_user_or_customer_identifier_is_a_failure(self) -> None:
        """The catalog rule names user identifiers, so the gate must reject real ones."""

        for literal in (
            "index=app user_id=alice@example.com",
            "index=app | search customer_id=12345",
            "index=app username=jsmith",
            "index=app email=alice@example.com",
        ):
            with self.subTest(literal=literal), tempfile.TemporaryDirectory() as tmp:
                body = GOOD_ENTRY.replace("index=<app_index> earliest=-60m | stats count by error_type", literal)
                failures = check_query_catalog.check(_tree(Path(tmp), body))
                self.assertTrue(any("session or user identifier" in f for f in failures), failures)

    def test_a_raw_payload_is_a_failure(self) -> None:
        for literal in ('index=app payload={"card":"4111"}', "index=app request_body=abc"):
            with self.subTest(literal=literal), tempfile.TemporaryDirectory() as tmp:
                body = GOOD_ENTRY.replace("index=<app_index> earliest=-60m | stats count by error_type", literal)
                failures = check_query_catalog.check(_tree(Path(tmp), body))
                self.assertTrue(any("raw payload" in f for f in failures), failures)

    def test_an_assignment_split_across_lines_is_a_failure(self) -> None:
        """A per-line scan would miss this; Markdown wraps by hand all the time."""

        with tempfile.TemporaryDirectory() as tmp:
            body = GOOD_ENTRY.replace(
                "index=<app_index> earliest=-60m | stats count by error_type",
                "index=app token=\n  s3cr3tvalue",
            )
            failures = check_query_catalog.check(_tree(Path(tmp), body))
            self.assertTrue(any("credential" in f for f in failures), failures)

    def test_an_empty_required_value_is_a_failure(self) -> None:
        """A label with no value is operationally identical to a missing field."""

        with tempfile.TemporaryDirectory() as tmp:
            body = GOOD_ENTRY.replace(
                "- **Healthy looks like:** flat background rate", "- **Healthy looks like:**"
            )
            failures = check_query_catalog.check(_tree(Path(tmp), body))
            self.assertTrue(any("has an empty Healthy looks like:" in f for f in failures), failures)

    def test_a_high_entropy_credential_literal_is_a_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            body = GOOD_ENTRY.replace(
                "index=<app_index> earliest=-60m",
                "index=app ghp_abcdefghijklmnopqrstuvwxyz01",
            )
            failures = check_query_catalog.check(_tree(Path(tmp), body))
            self.assertTrue(any("possible credential" in f for f in failures), failures)

    def test_placeholders_are_not_mistaken_for_secrets(self) -> None:
        """The forms an author must be able to write stay legal, or the catalog is unfillable."""

        with tempfile.TemporaryDirectory() as tmp:
            body = GOOD_ENTRY.replace(
                "index=<app_index> earliest=-60m | stats count by error_type",
                'index=<app_index> session_id=<session_field> user_id=<user_field> '
                'payload=<payload_field> token="<token_placeholder>"',
            )
            self.assertEqual([], check_query_catalog.check(_tree(Path(tmp), body)))

    def test_the_template_example_is_not_graded_as_an_entry(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            body = "# Catalog\n\n### <the question, phrased as a responder would ask it>\n\n- **Applies to:** x\n"
            self.assertEqual([], check_query_catalog.check(_tree(Path(tmp), body)))

    def test_a_missing_catalog_is_a_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            failures = check_query_catalog.check(Path(tmp))
            self.assertTrue(any("catalog file is missing" in f for f in failures), failures)

    def test_the_live_repository_passes(self) -> None:
        self.assertEqual([], check_query_catalog.check())


if __name__ == "__main__":
    unittest.main()
