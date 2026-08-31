#!/usr/bin/env python3
"""Component tests for the fleet knowledge atlas (GRAPH-004)."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import fleet_atlas  # noqa: E402
import fleet_atlas_views  # noqa: E402


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


class QueryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.document = fleet_atlas.snapshot(ROOT, fleet_atlas.build_graph(ROOT))

    def test_each_operator_query_has_a_grounded_answer(self) -> None:
        queries = (
            ("governs", ["eval runner"], "governed_by"),
            ("owner-of", ["EVAL-003"], "owns"),
            ("loads-for", ["backend-craft", "authenticating"], "loads_when"),
            (
                "supersedes",
                ["2026-08-22-agent-discovery-calibration"],
                "supersedes",
            ),
            ("depends-on", ["EVAL-003"], "depends_on"),
            ("blocks", ["HOST-003"], "depends_on"),
            ("verified-by", ["obs-dashboards/http-api.md"], "verified_by"),
            ("evidence-for", ["SWEEP-001"], "evidenced_by"),
            (
                "generated-from",
                ["platforms/copilot/skills/stack-profile/references/copilot-models.md"],
                "generated_from",
            ),
        )
        for verb, terms, expected_kind in queries:
            with self.subTest(verb=verb):
                results, truncated = fleet_atlas.query_document(
                    self.document, verb, terms
                )
                self.assertIsInstance(truncated, bool)
                edges = [item for item in results if item["resultType"] == "edge"]
                self.assertTrue(edges, f"{verb} returned no cited edge")
                self.assertTrue(any(edge["kind"] == expected_kind for edge in edges))
                self.assertTrue(
                    all(edge["sourceNode"] and edge["targetNode"] for edge in edges)
                )

        states, truncated = fleet_atlas.query_document(
            self.document, "state", ["EVAL-003"]
        )
        self.assertFalse(truncated)
        self.assertEqual(
            [(item["id"], item["state"]) for item in states],
            [("roadmap-item:EVAL-003", "live")],
        )

    def test_query_results_are_bounded(self) -> None:
        document = {
            "nodes": [
                {
                    "id": f"rule:{index}", "type": "rule", "name": "bounded demo",
                    "authority": "live-contract", "path": "docs/rules.md", "state": "live",
                    "attrs": {}, "evidence": [],
                }
                for index in range(fleet_atlas.QUERY_LIMIT + 2)
            ],
            "edges": [],
        }
        results, truncated = fleet_atlas.query_document(document, "governs", ["demo"])
        self.assertTrue(truncated)
        self.assertEqual(len(results), fleet_atlas.QUERY_LIMIT)


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
        self.assertTrue(inferred, "a dependency stated outside Prerequisites must still be recorded")
        self.assertTrue(all(e.attrs.get("field") != "Prerequisites" for e in inferred),
                        "a Prerequisites dependency is CONTRACT_RESOLVED, never inferred")

    def test_a_dependency_on_a_closed_item_is_kept_not_dropped(self) -> None:
        """A live item depending on a CLOSED item is a real relationship, and the one an operator
        asks about: 'it was waiting on that — is it unblocked now?'

        extract_roadmap once resolved dependencies against live item ids only, so when GRAPH-002
        closed the GRAPH-003 -> GRAPH-002 edge vanished silently. Dropping an edge answers the
        question wrongly and without saying so, which is worse than naming a historical target.
        """
        closed_ids = {
            n.id for n in self.graph.nodes.values()
            if n.type == "roadmap-item" and n.state == "historical"
        }
        to_closed = [
            e for e in self.graph.edges.values()
            if e.kind == "depends_on" and e.target in closed_ids
        ]
        self.assertTrue(to_closed, "no live item depends on a closed one; this test proves nothing")
        for edge in self.graph.edges.values():
            if edge.kind == "depends_on":
                self.assertIn(edge.target, self.graph.nodes, f"{edge.id} points at a missing node")

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
        self.assertNotIn("decision:2026-08-01-local-sol-conformance", self.graph.nodes)
        self.assertFalse(any(
            u.path == "docs/decisions/2026-08-01-local-sol-conformance.md"
            for u in self.graph.unknowns
        ))


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
        self.assertEqual(self.graph.nodes["owner:software-engineer"].attrs["kind"], "agent")
        caps = [e for e in self.graph.edges.values() if e.kind == "owns" and e.source == "agent:sre"]
        self.assertTrue(caps and all(e.cls == "STATIC_INFERRED" for e in caps))

    def test_a_component_named_in_an_owner_field_is_not_a_person(self) -> None:
        """An Owner field mentions components in passing; typing one 'human' invents a person.

        `runbook` and `stack-profile` are real skills that appear backticked inside Owner fields,
        and both were classified as human owners until extract_owners filtered components out.
        """
        components = {n.name for n in self.graph.nodes.values() if n.type in ("skill", "command")}
        humans = {
            n.name for n in self.graph.nodes.values()
            if n.type == "owner" and n.attrs["kind"] == "human"
        }
        self.assertEqual(humans & components, set(), f"components typed as human owners: {humans & components}")
        self.assertNotIn("fleet-atlas", humans, "a not-yet-created skill is still not a human")

    def test_no_unknown_reports_a_synthetic_fixture_path_as_stale(self) -> None:
        """Test files build temp repositories; their paths are not stale repository pins.

        Reporting them produced 143 findings with no true positive, which would bury the real
        contradictions in the stale-evidence view.
        """
        stale = [u for u in self.graph.unknowns if u.code == "extract.test-literal-stale"]
        self.assertEqual(stale, [], f"{len(stale)} unresolvable test literals reported as stale")


import fleet_atlas_detect  # noqa: E402


def _write_minimal_fixture(root: Path) -> None:
    """Build a small, real, git-committed repository copy for a detector mutation proof.

    Copies enough of the real tree (agents/, skills/, commands/, the live root docs, decisions,
    hooks, catalog) for fleet_atlas.build_graph() to run end to end, then commits it so cite()'s
    git plumbing has something to read. schemas/catalog-v1.json names validators outside every
    directory this fixture copies wholesale (scripts/evidence_envelope.py, scripts/fleet_atlas.py,
    evals/execution_profiles.py, evals/engine_contract.py); extract_schemas() cites each one by
    reading it, so without a stand-in file build_graph() raises FileNotFoundError -- proven by
    running this fixture without them.
    """
    import shutil
    import subprocess

    shutil.copytree(ROOT / "agents", root / "agents")
    shutil.copytree(ROOT / "skills", root / "skills")
    shutil.copytree(ROOT / "commands", root / "commands")
    for name in ("AGENTS.md", "CONTRIBUTING.md", "README.md"):
        shutil.copy(ROOT / name, root / name)
    (root / "docs").mkdir()
    shutil.copy(ROOT / "docs/rules.md", root / "docs/rules.md")
    shutil.copytree(ROOT / "docs/decisions", root / "docs/decisions")
    (root / "docs/reviews").mkdir(); (root / "hooks").mkdir(); (root / "schemas").mkdir()
    shutil.copy(ROOT / "hooks/hooks.json", root / "hooks/hooks.json")
    shutil.copy(ROOT / "schemas/catalog-v1.json", root / "schemas/catalog-v1.json")
    (root / "docs/fleet-roadmap.md").write_text("# Fleet roadmap\n", encoding="utf-8", newline="\n")
    (root / "docs/README.md").write_text("# map\n", encoding="utf-8", newline="\n")
    (root / "evals/scenarios").mkdir(parents=True); (root / "scripts").mkdir()
    (root / "scripts/evidence_envelope.py").write_text("# fixture stand-in\n", encoding="utf-8", newline="\n")
    (root / "scripts/fleet_atlas.py").write_text("# fixture stand-in\n", encoding="utf-8", newline="\n")
    (root / "evals/execution_profiles.py").write_text("# fixture stand-in\n", encoding="utf-8", newline="\n")
    (root / "evals/engine_contract.py").write_text("# fixture stand-in\n", encoding="utf-8", newline="\n")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A"], cwd=root, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-q", "-m", "fixture"], cwd=root, check=True)


class DetectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.graph = fleet_atlas.build_graph(ROOT)

    def test_detectors_never_emit_a_fact_class(self) -> None:
        findings = [e for e in self.graph.edges.values() if e.kind == "contradicts"]
        self.assertTrue(all(e.cls == "STATIC_INFERRED" for e in findings))
        self.assertTrue(all("detector" in e.attrs and "message" in e.attrs for e in findings))

    def test_uncited_review_detector_discriminates_cited_from_uncited(self) -> None:
        """Pins the DISCRIMINATION, not one filename.

        This test used to assert a specific orphan (2026-08-19-obs-skill-hardening-round.md). The
        live-doc cleanup then deleted that file — which is what docs/README.md prescribes for an
        uncited review, i.e. the detector's own finding was acted on — and the test failed for
        being right. A fixture that a correct downstream action invalidates is the wrong fixture.
        """
        uncited = {u.path for u in self.graph.unknowns if u.code == "stale.review-uncited"}
        reviews = {n.path for n in self.graph.nodes.values() if n.type == "review"}
        self.assertTrue(uncited, "the detector must still find at least one uncited review")
        self.assertTrue(uncited <= reviews, "every finding names a real review node")

        cited = {
            self.graph.nodes[e.target].path
            for e in self.graph.edges.values()
            if e.kind in ("evidenced_by", "cites")
            and e.target in self.graph.nodes
            and self.graph.nodes[e.target].type == "review"
        }
        self.assertTrue(cited, "some reviews are cited; otherwise this proves nothing")
        self.assertEqual(cited & uncited, set(), "a cited review must never be reported uncited")

    def test_uncited_review_detector_also_scans_live_doc_citations(self) -> None:
        """docs/README.md cites retained audit evidence outside roadmap and decision records.

        link_evidence() and extract_reviews() only walk roadmap-item/decision/review sources for
        citations, not a live root/docs guide's own body. Without also scanning that guide,
        the retained full-skill audit packets would be wrongly reported uncited.
        """
        uncited = {u.path for u in self.graph.unknowns if u.code == "stale.review-uncited"}
        self.assertNotIn("docs/reviews/2026-08-24-full-skill-audit-batch-1.md", uncited)

    def test_retired_name_detector_fires_on_prose_but_respects_the_filename_carve_out(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_minimal_fixture(root)
            agent_path = root / "agents" / "sre.md"
            original = agent_path.read_text(encoding="utf-8")

            # A prose mention of a retired unit name is a real hit.
            agent_path.write_text(original + "\nSee prompt-engineer for legacy context.\n",
                                  encoding="utf-8", newline="\n")
            prose_graph = fleet_atlas.build_graph(root)
            prose_hits = [u for u in prose_graph.unknowns if u.code == "stale.retired-name"]
            self.assertTrue(prose_hits, "a prose mention of a retired unit name must be reported")
            self.assertNotIn("F:", prose_hits[0].message, "the message must not embed an absolute path")
            self.assertTrue(prose_hits[0].message.startswith("agents/sre.md:"), prose_hits[0].message)

            # A link to a file that still legitimately carries a retired name (api-design.md
            # survives as skills/backend-craft/references/api-design.md) must NOT be reported.
            agent_path.write_text(
                original + "\nSee [api design](../skills/backend-craft/references/api-design.md).\n",
                encoding="utf-8", newline="\n",
            )
            exempt_graph = fleet_atlas.build_graph(root)
            exempt_hits = [u for u in exempt_graph.unknowns if u.code == "stale.retired-name"]
            self.assertEqual(exempt_hits, [], "a link to a surviving retired-name filename is not a stale mention")

    def test_delegation_mismatch_detector_fires_when_the_roster_disagrees_with_the_enforced_graph(self) -> None:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_minimal_fixture(root)
            agents_md = root / "AGENTS.md"
            text = agents_md.read_text(encoding="utf-8")
            before = fleet_atlas.build_graph(root)
            before_findings = [e for e in before.edges.values()
                               if e.kind == "contradicts" and e.attrs["detector"] == "delegation_mismatch"]
            needle = "| `sre` |"
            self.assertEqual(text.count(needle), 1, "fixture AGENTS.md must carry exactly one sre roster row")
            row_start = text.index(needle)
            row_end = text.index("\n", row_start)
            row = text[row_start:row_end]
            self.assertTrue(row.endswith("`researcher` |"), row)
            mutated_row = row[: -len("`researcher` |")] + "`researcher`, `scribe` |"
            agents_md.write_text(text[:row_start] + mutated_row + text[row_end:], encoding="utf-8", newline="\n")
            after = fleet_atlas.build_graph(root)
            after_findings = [e for e in after.edges.values()
                              if e.kind == "contradicts" and e.attrs["detector"] == "delegation_mismatch"]
            self.assertEqual(before_findings, [])
            self.assertGreater(len(after_findings), 0)


class ViewAndDriftTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._temporary = tempfile.TemporaryDirectory()
        cls.root = Path(cls._temporary.name) / "repository"
        shutil.copytree(
            ROOT,
            cls.root,
            ignore=shutil.ignore_patterns(".git", ".worktrees", "__pycache__"),
        )
        subprocess.run(["git", "init", "-q"], cwd=cls.root, check=True)
        subprocess.run(
            ["git", "config", "core.autocrlf", "false"], cwd=cls.root, check=True
        )
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", "add", "-A"],
            cwd=cls.root,
            check=True,
        )
        subprocess.run(
            [
                "git", "-c", "user.email=t@t", "-c", "user.name=t",
                "commit", "-q", "-m", "fixture",
            ],
            cwd=cls.root,
            check=True,
        )
        cls._original_fleet_root = fleet_atlas.ROOT
        fleet_atlas.ROOT = cls.root
        # unittest's default test-method ordering is alphabetical, which runs
        # test_a_renamed_reference_... before test_build_is_deterministic_..., yet the former calls
        # `check` and expects a baseline docs/fleet-atlas/generated/ to already exist and match HEAD.
        # Building once here (independent of method order) gives every test in this class that
        # baseline without weakening any individual assertion.
        result = fleet_atlas.main(["build"])
        if result != 0:
            raise RuntimeError(f"fleet_atlas build failed with exit code {result}")

    @classmethod
    def tearDownClass(cls) -> None:
        fleet_atlas.ROOT = cls._original_fleet_root
        cls._temporary.cleanup()

    def test_build_is_deterministic_and_check_passes_after_build(self) -> None:
        self.assertEqual(fleet_atlas.main(["build"]), 0)
        first = {
            p.name: p.read_bytes()
            for p in (self.root / "docs/fleet-atlas/generated").iterdir()
        }
        self.assertEqual(fleet_atlas.main(["build"]), 0)
        second = {
            p.name: p.read_bytes()
            for p in (self.root / "docs/fleet-atlas/generated").iterdir()
        }
        self.assertEqual(first, second)
        self.assertEqual(fleet_atlas.main(["check"]), 0)

    def test_every_generated_markdown_has_the_banner_and_respects_caps(self) -> None:
        for path in (self.root / "docs/fleet-atlas/generated").glob("*.md"):
            text = path.read_bytes()
            self.assertTrue(text.startswith(fleet_atlas_views.BANNER.encode()), path.name)
            self.assertNotIn(b"\r\n", text, path.name)
            cap = fleet_atlas_views.INDEX_CAP if path.name == "INDEX.md" else fleet_atlas_views.VIEW_CAP
            self.assertLessEqual(len(text), cap + len(fleet_atlas_views.TRUNCATED) + 2, path.name)

    def test_no_timestamps_or_absolute_paths_in_generated_output(self) -> None:
        import re
        for path in (self.root / "docs/fleet-atlas/generated").iterdir():
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", text), path.name)
            self.assertNotIn(str(self.root), text, path.name)
            self.assertNotIn("F:\\", text, path.name)
            self.assertTrue(all(line == line.rstrip() for line in text.splitlines()), path.name)

    def test_check_detects_a_drifted_view_and_a_timestamp(self) -> None:
        view = self.root / "docs/fleet-atlas/generated/INDEX.md"
        original = view.read_bytes()
        try:
            view.write_bytes(original + b"\nextra line\n")
            self.assertEqual(fleet_atlas.main(["check"]), 1)
        finally:
            view.write_bytes(original)
        self.assertEqual(fleet_atlas.main(["check"]), 0)

    def test_manifest_hashes_every_generated_file(self) -> None:
        generated = self.root / "docs/fleet-atlas/generated"
        manifest = json.loads((generated / "manifest.json").read_text(encoding="utf-8"))
        names = {p.name for p in generated.iterdir()} - {"manifest.json"}
        self.assertEqual(set(manifest["files"]), names)
        for name, digest in manifest["files"].items():
            actual = hashlib.sha256((generated / name).read_bytes()).hexdigest()
            self.assertEqual(digest, f"sha256:{actual}")

    def test_a_renamed_reference_turns_its_edge_unknown_and_reds_check(self) -> None:
        ref = self.root / "skills/stack-profile/references/copilot-models.md"
        moved = ref.with_name("copilot-models.renamed.md")
        try:
            ref.rename(moved)
            self.assertEqual(fleet_atlas.main(["check"]), 1)
            graph = fleet_atlas.build_graph(self.root)
            self.assertTrue(any(u.code == "extract.skill-link-unresolved" and "copilot-models.md" in u.message for u in graph.unknowns))
        finally:
            moved.rename(ref)
        self.assertEqual(fleet_atlas.main(["check"]), 0)


if __name__ == "__main__":
    unittest.main()
