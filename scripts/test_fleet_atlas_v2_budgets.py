"""Exercise actual text/Mermaid adapters under oversized multibyte graph input."""

import json
import unittest

from atlas_test_support import fact_rows, row_extraction
from fleet_atlas_v2_artifacts import checked_facts, render_files
from fleet_atlas_v2_format import DETAIL_BUDGET, INDEX_BUDGET
from fleet_atlas_v2_sources import Snapshot, Source


class RenderBudgetTests(unittest.TestCase):
    def test_large_multibyte_details_and_mermaid_account_for_omitted_facts(self):
        rows = []
        for kind, predicate in (("agent", "delegates_to"), ("roadmap-item", "depends_on")):
            for index in range(150):
                rows.append((f"edge:{kind}:{index}", f"{kind}:origin",
                             predicate, f"{kind}:{index}-" + "操作対象" * 24))
        snapshot = Snapshot("1" * 40, (Source("docs/budget-fixture.md", fact_rows(rows)),))
        checked = checked_facts(snapshot, lambda current: row_extraction(current, "docs/budget-fixture.md"))
        self.assertEqual(len(rows), len(checked.graph.facts))
        files = render_files(checked)
        for name, content in files.items():
            if not name.endswith((".md", ".mmd")):
                continue  # Full offline graph and manifest are not compact model views.
            with self.subTest(view=name):
                content.decode("utf-8")  # No split multibyte code point.
                budget = INDEX_BUDGET if name == "INDEX.md" else DETAIL_BUDGET
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
