"""Exercise actual text/Mermaid adapters under oversized multibyte graph input."""

import json
import unittest

from fleet_atlas_v2_artifacts import render_files
from fleet_atlas_v2_model import (
    Bucket, EvidenceClass, Fact, Node, Predicate, Proof, ProofKind, assemble, canonical_bytes,
)
from fleet_atlas_v2_proofs import Derivation, verify_facts
from fleet_atlas_v2_sources import Snapshot, Source


class RenderBudgetTests(unittest.TestCase):
    def test_large_multibyte_details_and_mermaid_account_for_omitted_facts(self):
        rows = []
        for kind, predicate in (("agent", "delegates_to"), ("roadmap-item", "depends_on")):
            for index in range(150):
                rows.append((f"edge:{kind}:{index}", f"{kind}:origin",
                             predicate, f"{kind}:{index}-" + "操作対象" * 24))
        source = Source("docs/budget-fixture.md", b"".join(canonical_bytes(row) for row in rows))
        identities = sorted({identity for row in rows for identity in (row[1], row[3])})
        nodes = tuple(Node(identity, identity.split(":", 1)[0], source.path, identity)
                      for identity in identities)
        proof_by_id = {
            row[0]: Proof(ProofKind.EXTRACTED, (source.span(index, index),), "budget-fixture/v1")
            for index, row in enumerate(rows, 1)
        }
        facts = tuple(Fact(identity, subject, predicate, target, EvidenceClass.EXTRACTED,
                           proof_by_id[identity]) for identity, subject, predicate, target in rows)
        rules = tuple(Predicate(predicate, frozenset({kind}), frozenset({kind}), (source.path,))
                      for kind, predicate in (("agent", "delegates_to"), ("roadmap-item", "depends_on")))
        row_by_id = {row[0]: (index, row) for index, row in enumerate(rows, 1)}

        def replay(fact, snapshot, premises):
            index, expected = row_by_id[fact.id]
            current = snapshot.source(source.path)
            row = json.loads(current.lines[index - 1])
            self.assertEqual(list(expected), row)
            return Derivation(row[3], EvidenceClass.EXTRACTED,
                              Proof(ProofKind.EXTRACTED, (current.span(index, index),), "budget-fixture/v1"))

        checked = verify_facts(assemble((Bucket("large-graph", nodes, facts),), rules),
                               Snapshot("1" * 40, (source,)), rules, {"budget-fixture/v1": replay})
        files = render_files(checked)
        for name, content in files.items():
            if not name.endswith((".md", ".mmd")):
                continue  # Full offline graph and manifest are not compact model views.
            with self.subTest(view=name):
                content.decode("utf-8")  # No split multibyte code point.
                budget = 4_000 if name == "INDEX.md" else 20_000
                self.assertLessEqual(len(content), budget)
                if name.endswith(".mmd"):
                    metadata = json.loads(content.rsplit(b"\n%% ", 1)[1])
                else:
                    metadata = json.loads(content.rsplit(b"<!-- ", 1)[1].removesuffix(b" -->\n"))
                self.assertEqual(budget, metadata["budgetBytes"])
                self.assertEqual(len(content), metadata["encodedBytes"])
                if name.endswith(".mmd"):
                    arrows = sum(b" --> " in line for line in content.splitlines())
                    self.assertGreater(arrows, 0)
                    self.assertTrue(metadata["truncated"])
                    self.assertGreater(metadata["omittedResults"], 0)
                    self.assertEqual(150, arrows + metadata["omittedResults"])
                    self.assertIn("操作対象".encode(), content)
                    self.assertIn(b"[verified]", content)
                elif name in ("capability-owner-map.md", "roadmap-dependency-map.md"):
                    self.assertTrue(metadata["truncated"])
                    self.assertGreater(metadata["omittedResults"], 0)


if __name__ == "__main__":
    unittest.main()
