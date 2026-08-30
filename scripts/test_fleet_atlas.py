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


import fleet_atlas_extract  # noqa: E402


class ExtractCanonicalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.graph = fleet_atlas.Graph()
        fleet_atlas_extract.extract_agents(ROOT, cls.graph)
        fleet_atlas_extract.extract_skills(ROOT, cls.graph)
        fleet_atlas_extract.extract_commands(ROOT, cls.graph)

    def test_every_agent_skill_and_command_file_becomes_one_node(self) -> None:
        agents = {p.stem for p in (ROOT / "agents").glob("*.md")}
        skills = {p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md")}
        commands = {p.stem for p in (ROOT / "commands").glob("*.md")}
        self.assertEqual({n.name for n in self.graph.nodes.values() if n.type == "agent"}, agents)
        self.assertEqual({n.name for n in self.graph.nodes.values() if n.type == "skill"}, skills)
        self.assertEqual({n.name for n in self.graph.nodes.values() if n.type == "command"}, commands)

    def test_every_reference_file_is_a_node_with_a_loads_when_edge(self) -> None:
        references = {
            f"{p.parents[1].name}/{p.name}" for p in (ROOT / "skills").glob("*/references/*.md")
        }
        nodes = {n.name for n in self.graph.nodes.values() if n.type == "reference"}
        self.assertEqual(nodes, references)
        targets = {e.target for e in self.graph.edges.values() if e.kind == "loads_when"}
        self.assertEqual(targets, {f"reference:{name}" for name in references})

    def test_routing_table_rows_carry_their_predicate(self) -> None:
        stack = [
            e for e in self.graph.edges.values()
            if e.kind == "loads_when" and e.source == "skill:stack-profile"
            and e.target == "reference:stack-profile/observability-stack.md"
        ]
        self.assertTrue(stack, "stack-profile must load observability-stack.md")
        predicates = {e.attrs["predicate"] for e in stack}
        self.assertTrue(any("observability backend" in p for p in predicates), predicates)
        self.assertTrue(all(e.cls == "STATIC_EXTRACTED" for e in stack))
        self.assertTrue(all(ev.path == "skills/stack-profile/SKILL.md" for e in stack for ev in e.evidence))

    def test_manual_only_skills_are_flagged(self) -> None:
        manual = {n.name for n in self.graph.nodes.values() if n.type == "skill" and n.attrs["manual_only"]}
        self.assertEqual(manual, {"incident-drill", "pcf-deploy", "service-lifecycle"})

    def test_agent_grants_are_recorded_but_not_yet_edges(self) -> None:
        engineer = self.graph.nodes["agent:software-engineer"]
        self.assertEqual(sorted(engineer.attrs["grants"]), ["researcher", "reviewer", "scribe"])
        self.assertFalse([e for e in self.graph.edges.values() if e.kind == "delegates_to"])

    def test_a_missing_link_target_becomes_an_unknown_not_an_edge(self) -> None:
        import tempfile, shutil
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            skill = root / "skills" / "demo"
            (skill / "references").mkdir(parents=True)
            (skill / "SKILL.md").write_text(
                "---\nname: demo\ndescription: \"Demo. Triggers: 'a', 'b'.\"\n---\n"
                "See [gone](./references/gone.md) and [here](./references/here.md).\n",
                encoding="utf-8", newline="\n",
            )
            (skill / "references" / "here.md").write_text("# here\n", encoding="utf-8", newline="\n")
            (root / "agents").mkdir(); (root / "commands").mkdir()
            graph = fleet_atlas.Graph()
            fleet_atlas_extract.extract_skills(root, graph)
            codes = [u.code for u in graph.unknowns]
            self.assertIn("extract.skill-link-unresolved", codes)
            self.assertEqual(
                [e.target for e in graph.edges.values() if e.kind == "loads_when"],
                ["reference:demo/here.md"],
            )


if __name__ == "__main__":
    unittest.main()
