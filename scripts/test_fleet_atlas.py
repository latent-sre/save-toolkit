#!/usr/bin/env python3
"""Component tests for the fleet knowledge atlas (GRAPH-004)."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import fleet_atlas  # noqa: E402


class ModelTests(unittest.TestCase):
    def test_provenance_and_authority_vocabularies_are_closed(self) -> None:
        self.assertEqual(
            fleet_atlas.PROVENANCE,
            ("CONTRACT_RESOLVED", "STATIC_EXTRACTED", "STATIC_INFERRED", "OPERATOR_CONFIRMED", "UNKNOWN"),
        )
        self.assertEqual(
            fleet_atlas.AUTHORITY,
            ("canonical", "live-contract", "generated", "historical-evidence", "external"),
        )

    def test_stable_id_is_deterministic_and_prefixed(self) -> None:
        first = fleet_atlas.stable_id("rule", "docs/rules.md", "Gate A must pass")
        second = fleet_atlas.stable_id("rule", "docs/rules.md", "Gate A must pass")
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("rule:"))
        self.assertEqual(len(first), len("rule:") + 16)
        self.assertNotEqual(first, fleet_atlas.stable_id("rule", "docs/rules.md", "Gate B must pass"))

    def test_cite_hashes_the_exact_lines(self) -> None:
        evidence = fleet_atlas.cite(ROOT, "AGENTS.md", 1, 1, "test.cite", "STATIC_EXTRACTED")
        first_line = (ROOT / "AGENTS.md").read_text(encoding="utf-8").splitlines()[0]
        self.assertEqual(evidence.excerpt_hash, fleet_atlas.excerpt_hash([first_line]))
        self.assertEqual(evidence.lines, (1, 1))
        with self.assertRaises(ValueError):
            fleet_atlas.cite(ROOT, "AGENTS.md", 1, 1, "test.cite", "HIGH")

    def test_graph_rejects_duplicate_ids_and_unknown_classes(self) -> None:
        graph = fleet_atlas.Graph()
        node = fleet_atlas.Node("agent:sre", "agent", "sre", "canonical", "agents/sre.md", "live", {}, [])
        graph.add_node(node)
        with self.assertRaises(ValueError):
            graph.add_node(node)
        with self.assertRaises(ValueError):
            graph.add_edge(fleet_atlas.Edge("e:1", "agent:sre", "agent:x", "delegates_to", "MAYBE", {}, []))

    def test_snapshot_binds_revision_and_validates_against_schema(self) -> None:
        graph = fleet_atlas.Graph()
        document = fleet_atlas.snapshot(ROOT, graph)
        self.assertEqual(document["apiVersion"], "save-toolkit/fleet-atlas/v1")
        self.assertRegex(document["metadata"]["revision"], r"^[0-9a-f]{40}$")
        self.assertIn(document["metadata"]["dirty"], (True, False))
        self.assertRegex(document["metadata"]["treeDigest"], r"^sha256:[0-9a-f]{64}$")
        schema = json.loads((ROOT / "schemas/fleet-atlas-v1.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["required"], ["apiVersion", "kind", "metadata", "nodes", "edges", "unknowns"])
        for key in schema["required"]:
            self.assertIn(key, document)

    def test_catalog_lists_the_atlas_schema(self) -> None:
        catalog = json.loads((ROOT / "schemas/catalog-v1.json").read_text(encoding="utf-8"))
        entry = [item for item in catalog["schemas"] if item["id"] == "fleet-atlas-v1"]
        self.assertEqual(len(entry), 1)
        self.assertEqual(entry[0]["canonical_path"], "schemas/fleet-atlas-v1.schema.json")
        self.assertEqual(entry[0]["validator"], "scripts/fleet_atlas.py")
        self.assertEqual(entry[0]["status"], "active")


if __name__ == "__main__":
    unittest.main()
