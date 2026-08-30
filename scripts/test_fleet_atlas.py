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


import fleet_atlas_cite  # noqa: E402
import validate_fleet  # noqa: E402
import generate_platform_adapters as adapters  # noqa: E402


class CitedContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.graph = fleet_atlas.build_graph(ROOT)
        cls.document = fleet_atlas.snapshot(ROOT, cls.graph)

    def test_delegation_edges_equal_the_enforced_literal(self) -> None:
        pairs = {
            (e.source.removeprefix("agent:"), e.target.removeprefix("agent:"))
            for e in self.graph.edges.values() if e.kind == "delegates_to"
        }
        expected = {(a, b) for a, targets in validate_fleet.EXPECTED_DELEGATION.items() for b in targets}
        self.assertEqual(pairs, expected)
        self.assertTrue(all(e.cls == "CONTRACT_RESOLVED" for e in self.graph.edges.values() if e.kind == "delegates_to"))

    def test_guarded_agents_are_constrained_by_the_hook(self) -> None:
        guarded = {
            e.source.removeprefix("agent:") for e in self.graph.edges.values()
            if e.kind == "constrained_by" and e.target == "hook:readonly-guard"
        }
        self.assertEqual(guarded, set(adapters.GUARDED_AGENTS))

    def test_every_generated_output_has_exactly_one_generated_from_edge(self) -> None:
        expected = {p.as_posix() for p in adapters.expected_outputs(ROOT)}
        projections = {n.path for n in self.graph.nodes.values() if n.type == "generated-projection"}
        self.assertEqual(projections, expected)
        sources = {}
        for e in self.graph.edges.values():
            if e.kind == "generated_from":
                sources.setdefault(e.source, []).append(e.target)
        self.assertEqual(set(sources), {f"generated-projection:{p}" for p in expected})
        self.assertTrue(all(len(v) == 1 for v in sources.values()))
        self.assertFalse([u for u in self.graph.unknowns if u.code == "cite.generated-source-missing"])

    def test_parity_check_is_a_real_detector(self) -> None:
        self.assertEqual(fleet_atlas_cite.parity_failures(ROOT, self.document), [])
        import copy
        broken = copy.deepcopy(self.document)
        broken["edges"] = [e for e in broken["edges"] if not (e["kind"] == "delegates_to" and e["source"] == "agent:sre")]
        self.assertTrue(any("delegates_to" in f and "sre" in f for f in fleet_atlas_cite.parity_failures(ROOT, broken)))
        broken = copy.deepcopy(self.document)
        broken["edges"].append({
            "id": "edge:forged", "source": "agent:scribe", "target": "agent:researcher",
            "kind": "delegates_to", "class": "CONTRACT_RESOLVED", "attrs": {}, "evidence": [],
        })
        self.assertTrue(any("scribe" in f for f in fleet_atlas_cite.parity_failures(ROOT, broken)))
        broken = copy.deepcopy(self.document)
        broken["nodes"] = [n for n in broken["nodes"] if n["type"] != "generated-projection"][:-1]
        self.assertTrue(any("generated" in f for f in fleet_atlas_cite.parity_failures(ROOT, broken)))


import check_plan_status  # noqa: E402


class ExtractGovernanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.graph = fleet_atlas.build_graph(ROOT)

    def test_every_rules_row_is_a_rule_node_with_a_governed_by_edge_or_an_unknown(self) -> None:
        rows = [
            line for line in (ROOT / "docs/rules.md").read_text(encoding="utf-8").splitlines()
            if line.startswith("| ") and not line.startswith("| Rule") and not line.startswith("|---")
        ]
        rules = [n for n in self.graph.nodes.values() if n.type == "rule"]
        self.assertEqual(len(rules), len(rows))
        governed = {e.source for e in self.graph.edges.values() if e.kind == "governed_by"}
        unlinked = {u.path for u in self.graph.unknowns if u.code == "extract.rule-source-unlinked"}
        for rule in rules:
            self.assertTrue(rule.id in governed or rule.attrs["statement"][:40] in " ".join(unlinked) or unlinked, rule.attrs["statement"])
        self.assertTrue(all(n.authority == "live-contract" for n in rules))

    def test_live_roadmap_items_match_the_checker_and_prerequisites_become_contract_edges(self) -> None:
        text = (ROOT / "docs/fleet-roadmap.md").read_text(encoding="utf-8")
        expected_ids = {item["id"] for item in check_plan_status._roadmap_items(text)}
        live = {n.name for n in self.graph.nodes.values() if n.type == "roadmap-item" and n.state == "live"}
        self.assertEqual(live, expected_ids)
        contract = {
            (e.source, e.target) for e in self.graph.edges.values()
            if e.kind == "depends_on" and e.cls == "CONTRACT_RESOLVED"
        }
        for item in check_plan_status._roadmap_items(text):
            for dep in check_plan_status.ROADMAP_ITEM_ID_RE.findall(str(item["fields"].get("Prerequisites", ""))):
                if dep != item["id"] and dep in expected_ids:
                    self.assertIn((f"roadmap-item:{item['id']}", f"roadmap-item:{dep}"), contract)
        inferred = [e for e in self.graph.edges.values() if e.kind == "depends_on" and e.cls == "STATIC_INFERRED"]
        self.assertTrue(any(e.source == "roadmap-item:GRAPH-003" and e.target == "roadmap-item:GRAPH-002" for e in inferred))

    def test_closed_register_rows_are_historical_items(self) -> None:
        closed = {n.name for n in self.graph.nodes.values() if n.type == "roadmap-item" and n.state == "historical"}
        for expected in ("SAFE-001", "EVAL-002", "NAV-001", "SWEEP-001", "MUTATION-001"):
            self.assertIn(expected, closed)
        self.assertEqual(self.graph.nodes["roadmap-item:EVAL-002"].authority, "historical-evidence")

    def test_decisions_declare_state_and_disposals_resolve(self) -> None:
        decisions = [n for n in self.graph.nodes.values() if n.type == "decision"]
        self.assertEqual(len(decisions), len(list((ROOT / "docs/decisions").glob("*.md"))))
        self.assertTrue(all(n.state in ("live", "proposed", "historical", "rejected", "deprecated") for n in decisions))
        calibration = self.graph.nodes["decision:2026-08-22-agent-discovery-calibration"]
        self.assertEqual(calibration.authority, "live-contract")
        disposals = [
            e for e in self.graph.edges.values()
            if e.kind == "supersedes" and e.attrs.get("relation") == "disposes" and e.source == calibration.id
        ]
        self.assertEqual([e.target for e in disposals], ["roadmap-item:EVAL-002"])
        conformance = self.graph.nodes["decision:2026-08-01-local-sol-conformance"]
        self.assertEqual(conformance.state, "historical")
        self.assertTrue(any(u.code == "extract.supersedes-unresolved" for u in self.graph.unknowns))


import check_evidence_refs  # noqa: E402


class ExtractEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.graph = fleet_atlas.build_graph(ROOT)

    def test_reviews_are_classified_and_batches_recorded(self) -> None:
        reviews = [n for n in self.graph.nodes.values() if n.type == "review"]
        self.assertEqual(len(reviews), len(list((ROOT / "docs/reviews").glob("*.md"))))
        generated = [n for n in reviews if n.authority == "generated"]
        self.assertTrue(all("-eval-" in n.name for n in generated))
        self.assertTrue(all(check_evidence_refs.BATCH_ID_RE.fullmatch(n.attrs["batch"]) for n in generated))

    def test_scenarios_bind_targets_and_near_misses(self) -> None:
        scenarios = [n for n in self.graph.nodes.values() if n.type == "scenario"]
        self.assertGreaterEqual(len(scenarios), 130)
        fire = self.graph.nodes["scenario:discovery-gcp-ops-cloud-run-startup"]
        self.assertTrue(any(e.kind == "verified_by" and e.source == "skill:gcp-ops" and e.target == fire.id
                            for e in self.graph.edges.values()))
        near = [e for e in self.graph.edges.values()
                if e.kind == "near_miss_for" and e.source == "scenario:discovery-workflow-graph-engineering-defers-code-graph"]
        self.assertEqual([e.target for e in near], ["skill:workflow-graph-engineering"])
        self.assertEqual(near[0].attrs["expected_alternative"], "inline")
        self.assertFalse([u for u in self.graph.unknowns if u.code == "extract.scenario-target-missing"])

    def test_tests_that_read_a_skill_verify_it(self) -> None:
        pins = [e for e in self.graph.edges.values()
                if e.kind == "verified_by" and e.source == "skill:gcp-ops"
                and e.target == "test:scripts/test_platform_skill_contracts.py"]
        self.assertEqual(len(pins), 1, "test_platform_skill_contracts reads skills/gcp-ops/SKILL.md")

    def test_schemas_come_from_the_catalog(self) -> None:
        self.assertIn("schema:evidence-envelope-v1", self.graph.nodes)
        self.assertTrue(any(e.kind == "constrained_by" and e.source == "schema:evidence-envelope-v1"
                            and e.target == "validator:scripts/evidence_envelope.py" for e in self.graph.edges.values()))

    def test_roadmap_evidence_links_and_batches_resolve(self) -> None:
        edges = [e for e in self.graph.edges.values() if e.kind == "evidenced_by" and e.source == "roadmap-item:SKILL-001"]
        self.assertTrue(any(e.target == "review:2026-08-29-skill-001-gcp-ops" for e in edges))
        self.assertFalse([u for u in self.graph.unknowns if u.code == "extract.batch-unresolved"],
                         "check_evidence_refs is green, so every cited batch must resolve")

    def test_owners_and_capabilities(self) -> None:
        self.assertEqual(self.graph.nodes["owner:latent-sre"].attrs["kind"], "human")
        self.assertEqual(self.graph.nodes["owner:software-engineer"].attrs["kind"], "agent")
        caps = [e for e in self.graph.edges.values() if e.kind == "owns" and e.source == "agent:sre"]
        self.assertTrue(caps and all(e.cls == "STATIC_INFERRED" for e in caps))


if __name__ == "__main__":
    unittest.main()
