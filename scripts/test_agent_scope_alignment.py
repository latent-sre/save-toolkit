"""Check the bounded helper's response contract, not its free-form reasoning."""

from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AgentScopeAlignmentTests(unittest.TestCase):
    def test_default_sre_return_does_not_require_a_diagnosis(self) -> None:
        text = (ROOT / "agents/sre-assistant.md").read_text(encoding="utf-8")
        output = text.split("## Output contract\n", 1)[1]
        output = re.split(r"^## ", output, maxsplit=1, flags=re.MULTILINE)[0]
        templates = re.findall(r"^```[^\n]*\n(.*?)^```", output, re.MULTILINE | re.DOTALL)
        self.assertTrue(templates, "the helper must still provide a default return template")
        fields = set(re.findall(r"^([^:\n]+):", templates[0], re.MULTILINE))
        self.assertTrue(
            {"Returning to", "Assignment", "Observations", "Caller next step"} <= fields,
            "the default return must retain its caller, task, observations, and continuation",
        )
        self.assertFalse(
            fields & {"Hypotheses tested", "Root cause", "Durable fix"},
            "a requested evidence slice must not require a full incident diagnosis",
        )


if __name__ == "__main__":
    unittest.main()
