"""Golden operator workflows through real extraction, persisted artifacts, and queries."""
from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from atlas_test_support import copy_runtime, git, init_repository
from fleet_atlas_v2 import query
from fleet_atlas_v2_artifacts import build, verify
from fleet_atlas_v2_format import DETAIL_BUDGET


FILES = {
    "agents/investigation-reader.md": """---
name: investigation-reader
description: Read scoped investigation guidance.
tools: Read, Skill
---
# Investigation reader
Load the method relevant to the question:

| Need | Method |
|---|---|
| Scoped investigation advice | `incident-investigation` |
""",
    "AGENTS.md": """# Fleet guide

| Agent | Lane | Tools | Delegates to |
|---|---|---|---|
| `agent-engineer` | Fleet methods | Read | — |

Canonical sources remain authoritative. Evidence describes recorded source relationships.
""",
    "agents/agent-engineer.md": """---
name: agent-engineer
description: Own fleet methods.
tools: Read
---
# Agent engineer
Own the methods; execution needs its existing authorization.
""",
    "agents/software-engineer.md": """---
name: software-engineer
description: Implement team code.
tools: Read
---
# Software engineer
Implement accepted code work.
""",
    "skills/fleet-atlas/SKILL.md": """---
name: fleet-atlas
description: Find fleet guidance and recorded change impact.
---
# Fleet atlas
**Owner:** `agent-engineer` owns the fleet-atlas capability; `software-engineer` owns its runtime implementation.
""",
    "skills/incident-investigation/SKILL.md": """---
name: incident-investigation
description: Advise a responder during an incident.
---
# Incident investigation

| When | Read |
|---|---|
| A dependency is slow | [Slow calls](references/slow-calls.md) |

This is guidance, never authorization to change a service.
""",
    "skills/incident-investigation/references/slow-calls.md": """# Slow calls

When ledger calls delay account reads, compare the caller deadline with cancellation and slot release.
An old aggregate cannot establish current recovery. Keep the observation time and target revision.
""",
    "docs/fleet-roadmap.md": """# Fleet roadmap

### GRAPH-004 — useful guidance navigation

**Status:** `active` (2026-09-30).
**Owner:** `agent-engineer` owns the `fleet-atlas` skill.
**Outcome:** Find relevant guidance with source citations.
**Next action:** Verify the selected source relationships.
**Evidence:** [Atlas decision](decisions/atlas.md).
**SRE task:** Locate an operational check.
""",
    "docs/decisions/atlas.md": """# Atlas decision

- **Status:** accepted
- **Date:** 2026-09-30

The atlas locates canonical guidance; it is not live service evidence.
""",
    "evals/scenarios/incident-reader-not-fire.yaml": """id: incident-reader-not-fire
target: {kind: skill, name: incident-investigation}
mode: direct
routing:
  expect: not_fire
  expected_alternative: {kind: agent, name: investigation-reader}
prompt: |
  Discuss weekend hobbies with no operational question.
""",
}


class WorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        copy_runtime(cls.root)
        for path, content in FILES.items():
            destination = cls.root / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content, encoding="utf-8", newline="\n")
        init_repository(cls.root, "Atlas fixture")
        git(cls.root, "add", ".")
        git(cls.root, "commit", "-qm", "synthetic operator workflow")
        cls.document = build(cls.root)

    def result(self, verb, *terms):
        encoded = query(verify(self.root), verb, list(terms))
        result = json.loads(encoded)
        self.assertLessEqual(len(encoded), DETAIL_BUDGET)
        self.assertEqual(len(encoded), result["encodedBytes"])
        return result

    def test_find_body_only_symptom_guidance_with_loading_condition(self):
        result = self.result("guidance", "caller", "deadline")
        self.assertEqual("results", result["outcome"])
        text = [item for item in result["results"] if item["predicate"] == "guidance"]
        self.assertTrue(text, "body-only words must find the actual reference text")
        self.assertTrue(any("slot release" in item["object"] for item in text))
        self.assertTrue(any(item["predicate"] == "loads_when" for item in result["results"]),
                        "a reference hit must preserve its conditional loading edge")
        for item in text:
            self.assertTrue(item["label"])
            self.assertTrue(item["citations"])
            self.assertTrue(any(cite["path"].endswith("slow-calls.md") and cite["start"] > 1
                                for cite in item["citations"]))

    def test_change_impact_explains_reference_to_skill_relationship(self):
        result = self.result("impact", "skills/incident-investigation/references/slow-calls.md")
        edges = [item for item in result["results"] if item["predicate"] in {"loads_when", "cites"}]
        self.assertTrue(any(item["subject"] == "skill:incident-investigation" for item in edges))
        self.assertTrue(any(item["subject"] == "agent:investigation-reader"
                            and item["object"] == "skill:incident-investigation"
                            for item in result["results"]),
                        "reference changes must reach an agent that explicitly selects its owning skill")
        self.assertTrue(all(item["citations"] for item in edges))

    def test_impact_includes_recorded_negative_routing_regression(self):
        result = self.result("impact", "incident-investigation")
        near_miss = [item for item in result["results"] if item["predicate"] == "near_miss_for"]
        self.assertTrue(near_miss, "a routing description change must surface recorded not_fire regressions")
        self.assertEqual(["scenario:incident-reader-not-fire"],
                         sorted(item["subject"] for item in near_miss))

    def test_recorded_owner_and_roadmap_evidence_are_resolvable(self):
        owner = self.result("owner-of", "fleet-atlas")
        self.assertTrue(any(item["subject"] == "agent:agent-engineer" for item in owner["results"]))
        evidence = self.result("evidence-for", "GRAPH-004")
        self.assertTrue(any(item["object"] == "decision:atlas" for item in evidence["results"]))

    def test_unknown_symptom_is_verified_empty_not_an_operational_claim(self):
        result = self.result("guidance", "no-such-symptom-fb0c13")
        self.assertEqual("empty", result["outcome"])
        self.assertEqual([], result["results"])
        self.assertIn("not proof", result["scope"])


if __name__ == "__main__":
    unittest.main()
