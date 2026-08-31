#!/usr/bin/env python3
"""Focused contracts for roadmap measurement-evidence resolution."""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

import check_evidence_refs


BATCH = "20260826T120000Z-1234abcd"
FOLDED_BATCH = "20260827T013128Z-41e49e29"
FULL_CANDIDATE = "0" * 40
INPUT_SHA256 = "1" * 64
FOLDED_HEADER = (
    "| Batch | Verdict | Model | Candidate | Input state | Workspace dirty | Input SHA-256 | "
    "Scenario count | Scenarios |\n"
    "|---|---|---|---|---|---|---|---:|---|\n"
)
FOLDED_ROW_RE = re.compile(
    r"^\| `(?P<batch>\d{8}T\d{6}Z-[0-9a-f]{8})` \| [^|]+ \| [^|]+ \| "
    r"`(?P<candidate>[0-9a-f]{40})` \| "
    r"(?P<input_state>(?:plugin dirty|candidate clean): (?:true|false)) \| "
    r"(?P<workspace_dirty>true|false|n/a) \| `(?P<input_sha256>[0-9a-f]{64})` \| "
    r"(?P<count>\d+) \| (?P<scenarios>.+) \|$"
)
FOLDED_BATCH_SCENARIOS = {
    "agent-direct-sre-human-owns-incident",
    "discovery-akamai-edge-defers-active-incident",
    "discovery-external-researcher-defers-live-incident",
    "discovery-gcp-ops-defers-active-incident",
    "discovery-incident-command-declare",
    "discovery-incident-investigation-defers-engineering-altitude",
    "discovery-incident-investigation-first-response",
    "discovery-incident-investigation-systemic-failure",
    "discovery-resolved-incident-postmortem",
    "discovery-runbook-incident-update",
    "discovery-scribe-defers-live-incident",
    "discovery-staging-incident-triage",
    "incident-investigation-mode-selection-contract",
}


class EvidenceReferenceTests(unittest.TestCase):
    def make_root(self) -> Path:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        (root / "docs" / "reviews").mkdir(parents=True)
        return root

    def test_roadmap_batch_must_resolve_to_review_record(self) -> None:
        root = self.make_root()
        (root / "docs" / "fleet-roadmap.md").write_text(
            f"# Roadmap\n\nBatch `{BATCH}` is load-bearing.\n", encoding="utf-8"
        )

        failures = check_evidence_refs.check(root)

        self.assertEqual(1, len(failures))
        self.assertIn(BATCH, failures[0])

    def test_review_record_resolves_roadmap_batch(self) -> None:
        root = self.make_root()
        (root / "docs" / "fleet-roadmap.md").write_text(
            f"# Roadmap\n\nBatch `{BATCH}` is load-bearing.\n", encoding="utf-8"
        )
        (root / "docs" / "reviews" / "batch.md").write_text(
            f"# Evidence\n\nBatch `{BATCH}`.\n", encoding="utf-8"
        )

        self.assertEqual([], check_evidence_refs.check(root))

    def test_non_batch_numbers_are_ignored(self) -> None:
        root = self.make_root()
        (root / "docs" / "fleet-roadmap.md").write_text(
            "# Roadmap\n\nCommit 12345678 and date 2026-08-26.\n", encoding="utf-8"
        )

        self.assertEqual([], check_evidence_refs.check(root))

    def _write_folded_index(self, body: str) -> Path:
        root = self.make_root()
        (root / "docs" / "fleet-roadmap.md").write_text("# Roadmap\n", encoding="utf-8")
        (root / check_evidence_refs.FOLDED_INDEX).write_text(body, encoding="utf-8")
        return root

    def test_folded_index_rejects_an_abbreviated_candidate(self) -> None:
        root = self._write_folded_index(
            "1 sealed packets folded.\n\n"
            + FOLDED_HEADER
            + f"| `{BATCH}` | PASS | sonnet | `0123456789ab` | plugin dirty: false | false | "
            f"`{INPUT_SHA256}` | 1 | case-one |\n"
        )

        failures = check_evidence_refs.check(root)

        self.assertTrue(
            any("full 40-character Git object ID" in failure for failure in failures),
            failures,
        )

    def test_folded_index_rejects_an_incomplete_scenario_list(self) -> None:
        root = self._write_folded_index(
            "1 sealed packets folded.\n\n"
            + FOLDED_HEADER
            + f"| `{BATCH}` | PASS | sonnet | `{FULL_CANDIDATE}` | plugin dirty: false | false | "
            f"`{INPUT_SHA256}` | 2 | case-one |\n"
        )

        failures = check_evidence_refs._check_folded_index(root)

        self.assertTrue(
            any("declares 2 scenarios but lists 1" in failure for failure in failures),
            failures,
        )

    def test_folded_index_rejects_an_abbreviated_input_digest(self) -> None:
        root = self._write_folded_index(
            "1 sealed packets folded.\n\n"
            + FOLDED_HEADER
            + f"| `{BATCH}` | PASS | sonnet | `{FULL_CANDIDATE}` | plugin dirty: false | false | "
            "`123456789abc` | 1 | case-one |\n"
        )

        failures = check_evidence_refs._check_folded_index(root)

        self.assertTrue(
            any("full 64-character SHA-256" in failure for failure in failures),
            failures,
        )

    def test_folded_index_rejects_input_state_workspace_mismatches(self) -> None:
        rows = {
            "classic without workspace state": (
                f"| `{BATCH}` | PASS | sonnet | `{FULL_CANDIDATE}` | plugin dirty: false | n/a | "
                f"`{INPUT_SHA256}` | 1 | case-one |\n"
            ),
            "envelope with invented workspace state": (
                f"| `{BATCH}` | PASS | sonnet | `{FULL_CANDIDATE}` | candidate clean: true | false | "
                f"`{INPUT_SHA256}` | 1 | case-one |\n"
            ),
        }
        for label, row in rows.items():
            with self.subTest(label=label):
                root = self._write_folded_index("1 sealed packets folded.\n\n" + FOLDED_HEADER + row)

                failures = check_evidence_refs._check_folded_index(root)

                self.assertTrue(any("Workspace dirty" in failure for failure in failures), failures)

    def test_folded_index_accepts_both_exact_identity_formats(self) -> None:
        root = self._write_folded_index(
            "2 sealed packets folded.\n\n"
            + FOLDED_HEADER
            + f"| `{BATCH}` | PASS | sonnet | `{FULL_CANDIDATE}` | plugin dirty: false | true | "
            f"`{INPUT_SHA256}` | 2 | case-one, case-two |\n"
            + "| `20260826T120001Z-1234abce` | PASS | sonnet | "
            f"`{'2' * 40}` | candidate clean: true | n/a | `{'3' * 64}` | 1 | case-three |\n"
        )

        self.assertEqual([], check_evidence_refs._check_folded_index(root))

    def test_live_folded_index_retains_exact_candidates_and_complete_scenarios(self) -> None:
        index = (
            check_evidence_refs.ROOT
            / "docs"
            / "reviews"
            / "2026-08-30-folded-eval-index.md"
        ).read_text(encoding="utf-8")
        rows = {}
        for line in index.splitlines():
            match = FOLDED_ROW_RE.match(line)
            if match:
                rows[match.group("batch")] = match

        self.assertEqual(
            69,
            len(rows),
            "every folded row must retain exact candidate and input identity",
        )
        self.assertEqual(
            32,
            sum(match.group("input_state") == "plugin dirty: true" for match in rows.values()),
        )
        self.assertEqual(
            6,
            sum(match.group("input_state").startswith("candidate clean:") for match in rows.values()),
        )
        match = rows[FOLDED_BATCH]
        scenarios = {item.strip() for item in match.group("scenarios").split(",")}
        self.assertEqual(int(match.group("count")), len(scenarios))
        self.assertEqual(FOLDED_BATCH_SCENARIOS, scenarios)


if __name__ == "__main__":
    unittest.main()
