"""Real Git fixture checks through the shared build/check artifact boundary."""

import json
from pathlib import Path
import unittest

from atlas_test_support import ReadmeRepository, fact_rows, fixture_extract, row_extraction, verified
from fleet_atlas_v2_artifacts import (
    OUTPUT, VerifiedDocument, build, checked_facts, mermaid_label, render_files, verify, verify_runtime_sources,
)
from fleet_atlas_v2_model import EvidenceClass, Fact, Node, Predicate, Proof, ProofKind, canonical_bytes, digest
from fleet_atlas_v2_proofs import Derivation
from fleet_atlas_v2_sources import Snapshot, Source


class ArtifactTests(ReadmeRepository, unittest.TestCase):
    def test_build_and_check_share_verifier_and_are_deterministic(self):
        first = build(self.root, fixture_extract)
        initial = {path.name: path.read_bytes() for path in (self.root / OUTPUT).iterdir()}
        self.assertEqual(first, verify(self.root, fixture_extract))
        build(self.root, fixture_extract)
        self.assertEqual(initial, {path.name: path.read_bytes() for path in (self.root / OUTPUT).iterdir()})
        with self.assertRaises(ValueError):
            VerifiedDocument(first.facts, first.revision, object())
        for name in ("delegation.mmd", "roadmap-dependency-map.mmd"):
            content = self.output(name).read_bytes()
            marker = json.loads(content.split(b"\n%% ")[-1])
            self.assertEqual(len(content), marker["encodedBytes"])

    def test_atlas_validates_against_real_draft_2020_12_schema(self):
        from jsonschema import Draft202012Validator

        build(self.root, fixture_extract)
        schema_path = Path(__file__).resolve().parents[1] / "schemas/fleet-atlas-v2.schema.json"
        schema = json.loads(schema_path.read_bytes())
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        document = json.loads(self.output("atlas.json").read_bytes())
        self.assertEqual([], list(validator.iter_errors(document)))
        document["facts"][0]["proof"]["inputs"] = []
        self.assertTrue(list(validator.iter_errors(document)))

    def test_running_implementation_is_bound_to_recorded_source_tree(self):
        directory = Path(__file__).resolve().parent
        # Named here, not via runtime_modules(): a module dropped there must fail this check.
        paths = [*directory.glob("fleet_atlas_v2*.py"), directory / "fleet_frontmatter.py"]
        sources = tuple(Source("scripts/" + path.name, path.read_bytes()) for path in sorted(paths))
        snapshot = Snapshot("fixture", sources)
        verify_runtime_sources(snapshot)
        changed = Source(sources[0].path, sources[0].content + b"\n# changed\n")
        with self.assertRaisesRegex(ValueError, "implementation differs"):
            verify_runtime_sources(Snapshot("fixture", (changed, *sources[1:])))

    def test_mermaid_keeps_readable_entity_labels_and_complete_evidence(self):
        source = Source("docs/fleet-roadmap.md", b"roadmap-item:GRAPH-001 depends_on roadmap-item:GRAPH-002\n")
        proof = Proof(ProofKind.EXTRACTED, (source.span(1, 1),), "diagram-fixture/v1")
        nodes = (Node("roadmap-item:GRAPH-001", "roadmap-item", source.path, "GRAPH-001"),
                 Node("roadmap-item:GRAPH-002", "roadmap-item", source.path, "GRAPH-002"))
        fact = Fact("edge:dependency", nodes[0].id, "depends_on", nodes[1].id, EvidenceClass.EXTRACTED, proof)
        predicate = Predicate("depends_on", frozenset({"roadmap-item"}), frozenset({"roadmap-item"}), (source.path,))

        def target_from_source(fact, snapshot, premises):
            return Derivation(snapshot.source(source.path).lines[0].split()[-1], EvidenceClass.EXTRACTED, proof)

        checked = verified((source,), nodes, (fact,), (predicate,), {"diagram-fixture/v1": target_from_source},
                           revision="1" * 40)
        diagram = render_files(checked)["roadmap-dependency-map.mmd"].decode()
        self.assertIn('["roadmap-item:GRAPH-001"]', diagram)
        self.assertIn('["roadmap-item:GRAPH-002"]', diagram)
        self.assertIn("STATIC_EXTRACTED [verified]", diagram)
        self.assertIn("docs/fleet-roadmap.md:1-1", diagram)
        self.assertEqual("agent:操作 team", mermaid_label("agent:操作 team"))
        self.assertEqual("agent:bad#34;#93; --#62; forged", mermaid_label('agent:bad"] --> forged'))

    def test_named_views_preserve_donor_state_and_negative_routing_facts(self):
        payloads = [
            ("f:decision-state", "decision:choice", "state", "proposed"),
            ("f:decision-date", "decision:choice", "attr.date", "2026-09-30"),
            ("f:decision-authority", "decision:choice", "authority", "historical-evidence"),
            ("f:roadmap-state", "roadmap-item:GRAPH-004", "state", "live"),
            ("f:roadmap-status", "roadmap-item:GRAPH-004", "attr.status", "active"),
            ("f:roadmap-owner", "roadmap-item:GRAPH-004", "attr.owner", "maintainers"),
            ("e:negative", "scenario:negative", "near_miss_for", "skill:demo"),
            ("e:delegate", "agent:a", "delegates_to", "agent:b"),
            ("e:guard", "agent:a", "constrained_by", "hook:guard"),
        ]
        snapshot = Snapshot("1" * 40, (Source("docs/example.md", fact_rows(payloads)),))
        views = render_files(checked_facts(snapshot, lambda current: row_extraction(current, "docs/example.md")))
        expected = {
            "decision-supersession-map.md": ("f:decision-state", "f:decision-date", "f:decision-authority"),
            "roadmap-dependency-map.md": ("f:roadmap-state", "f:roadmap-status", "f:roadmap-owner"),
            "claim-to-eval-map.md": ("e:negative",),
            "capability-owner-map.md": ("e:delegate", "e:guard"),
        }
        for filename, identities in expected.items():
            for identity in identities:
                with self.subTest(view=filename, fact=identity):
                    self.assertIn(identity, views[filename].decode())

    def test_tampered_view_and_forged_manifest_fail_regenerated_projection(self):
        build(self.root, fixture_extract)
        path = self.output("INDEX.md")
        path.write_bytes(path.read_bytes() + b"forged\n")
        manifest_path = self.output("manifest.json")
        manifest = json.loads(manifest_path.read_bytes())
        manifest["files"]["INDEX.md"] = digest(path.read_bytes())
        manifest_path.write_bytes(canonical_bytes(manifest))
        with self.assertRaisesRegex(ValueError, "projection or manifest drift"):
            verify(self.root, fixture_extract)

    def test_tampered_fact_fails_proof_replay_even_with_real_span(self):
        build(self.root, fixture_extract)
        path = self.output("atlas.json")
        data = json.loads(path.read_bytes())
        data["facts"][0]["object"] = "not the source value"
        path.write_bytes(canonical_bytes(data))
        with self.assertRaisesRegex(ValueError, "complete claim"):
            verify(self.root, fixture_extract)

    def test_missing_and_extra_output_members_fail_closed(self):
        build(self.root, fixture_extract)
        extra = self.output("not-in-manifest.txt")
        extra.write_bytes(b"extra")
        with self.assertRaisesRegex(ValueError, "membership"):
            verify(self.root, fixture_extract)
        with self.assertRaisesRegex(ValueError, "unexpected output"):
            build(self.root, fixture_extract)
        extra.unlink()
        self.output("INDEX.md").unlink()
        with self.assertRaisesRegex(ValueError, "membership"):
            verify(self.root, fixture_extract)

    def test_dirty_and_new_committed_sources_make_existing_atlas_unusable(self):
        build(self.root, fixture_extract)
        (self.root / "README.md").write_bytes(b"changed\n")
        with self.assertRaisesRegex(ValueError, "dirty canonical"):
            verify(self.root, fixture_extract)
        self.git("add", "README.md")
        self.git("commit", "-qm", "changed source")
        with self.assertRaisesRegex(ValueError, "stale"):
            verify(self.root, fixture_extract)

    def test_generated_only_commit_retains_valid_recorded_revision(self):
        original = build(self.root, fixture_extract)
        self.git("add", OUTPUT.as_posix())
        self.git("commit", "-qm", "generated output")
        self.assertEqual(original.revision, verify(self.root, fixture_extract).revision)

    def test_duplicate_json_fields_and_wrong_dirty_type_fail_closed(self):
        build(self.root, fixture_extract)
        path = self.output("atlas.json")
        original = path.read_bytes()
        path.write_bytes(original.replace(b'{"apiVersion":', b'{"kind":"other","apiVersion":', 1))
        with self.assertRaisesRegex(ValueError, "duplicate JSON"):
            verify(self.root, fixture_extract)
        data = json.loads(original)
        data["metadata"]["dirty"] = 0
        path.write_bytes(canonical_bytes(data))
        with self.assertRaisesRegex(ValueError, "provenance"):
            verify(self.root, fixture_extract)


if __name__ == "__main__":
    unittest.main()
