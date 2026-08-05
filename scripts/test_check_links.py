#!/usr/bin/env python3
"""Red-first contracts for the temporary Phase-2 link and stale-name gates."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import check_links
import check_stale_names


CLEAN_FRONTMATTER = """---
name: probe-skill
description: >-
  A clean probe skill. Triggers: "check this probe", "inspect this probe".
argument-hint: "[the probe]"
---
"""


class Fixture(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="phase2-checkers-")
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def write(self, relative: str, text: str) -> Path:
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
        return path

    def skill(self, body: str = "# Probe\n") -> Path:
        return self.write("skills/probe-skill/SKILL.md", CLEAN_FRONTMATTER + "\n" + body)


class LinkCheckerTests(Fixture):
    def test_clean_fixture_is_silent(self):
        self.skill(
            "# Probe\n\nRead [notes](./references/notes.md) and use "
            "[template](./assets/template.txt).\n"
        )
        self.write("skills/probe-skill/references/notes.md", "# Notes\n")
        self.write("skills/probe-skill/assets/template.txt", "template\n")
        self.assertEqual([], check_links.check(self.root))

    def test_top_level_frontmatter_comment_is_allowed(self):
        frontmatter = CLEAN_FRONTMATTER.replace(
            'argument-hint: "[the probe]"',
            '# Human-invoked skill; this comment is model-visible context.\n'
            'argument-hint: "[the probe]"',
        )
        self.write("skills/probe-skill/SKILL.md", frontmatter + "\n# Probe\n")
        self.assertEqual([], check_links.check(self.root))

    def test_frontmatter_contract_rejects_each_silent_load_failure(self):
        cases = {
            "unknown": CLEAN_FRONTMATTER.replace(
                'argument-hint: "[the probe]"',
                'argument-hint: "[the probe]"\nrogue: true',
            ),
            "blank-hint": CLEAN_FRONTMATTER.replace(
                'argument-hint: "[the probe]"', 'argument-hint: ""'
            ),
            "list-hint": CLEAN_FRONTMATTER.replace(
                'argument-hint: "[the probe]"', "argument-hint: [the probe]"
            ),
            "boolean-hint": CLEAN_FRONTMATTER.replace(
                'argument-hint: "[the probe]"', "argument-hint: false"
            ),
            "number-hint": CLEAN_FRONTMATTER.replace(
                'argument-hint: "[the probe]"', "argument-hint: 123"
            ),
            "null-hint": CLEAN_FRONTMATTER.replace(
                'argument-hint: "[the probe]"', "argument-hint: null"
            ),
            "missing-triggers": CLEAN_FRONTMATTER.replace("Triggers:", "Use when"),
            "one-trigger": CLEAN_FRONTMATTER.replace(
                ', "inspect this probe"', ""
            ),
            "over-600": CLEAN_FRONTMATTER.replace(
                "A clean probe skill.", "x" * 590
            ),
        }
        for label, frontmatter in cases.items():
            with self.subTest(label=label):
                self.root = Path(self._tmp.name) / label
                self.write(
                    "skills/probe-skill/SKILL.md", frontmatter + "\n# Probe\n"
                )
                failures = check_links.check(self.root)
                self.assertTrue(failures, label)

    def test_manual_only_control_is_required_inside_frontmatter_and_cannot_widen(self):
        manual_frontmatter = CLEAN_FRONTMATTER.replace(
            "name: probe-skill", "name: service-onboarding"
        ).replace(
            'argument-hint: "[the probe]"',
            'argument-hint: "[the probe]"\ndisable-model-invocation: true',
        )
        self.write(
            "skills/service-onboarding/SKILL.md",
            manual_frontmatter + "\n# Manual probe\n",
        )
        self.assertEqual([], check_links.check(self.root))

        fixture_root = Path(self._tmp.name)
        missing = fixture_root / "missing"
        self.root = missing
        self.write(
            "skills/service-onboarding/SKILL.md",
            manual_frontmatter.replace("disable-model-invocation: true\n", "")
            + "\n# Manual probe\n",
        )
        self.assertTrue(
            any("manual-only skill must contain frontmatter" in item for item in check_links.check(self.root))
        )

        moved = fixture_root / "moved"
        self.root = moved
        self.write(
            "skills/service-onboarding/SKILL.md",
            manual_frontmatter.replace("disable-model-invocation: true\n", "")
            + "\ndisable-model-invocation: true\n# Manual probe\n",
        )
        self.assertTrue(
            any("manual-only skill must contain frontmatter" in item for item in check_links.check(self.root))
        )

        widened = fixture_root / "widened"
        self.root = widened
        self.write(
            "skills/probe-skill/SKILL.md",
            CLEAN_FRONTMATTER.replace(
                'argument-hint: "[the probe]"',
                'argument-hint: "[the probe]"\ndisable-model-invocation: true',
            )
            + "\n# Probe\n",
        )
        self.assertTrue(
            any("only pcf-deploy and service-onboarding" in item for item in check_links.check(self.root))
        )

    def test_code_span_pointer_is_rejected(self):
        self.skill("# Probe\n\nRead `references/notes.md`.\n")
        self.write("skills/probe-skill/references/notes.md", "# Notes\n")
        self.assertTrue(any("code-span pointer" in item for item in check_links.check(self.root)))

    def test_dead_relative_link_is_rejected(self):
        self.skill("# Probe\n\nRead [missing](./references/missing.md).\n")
        self.assertTrue(any("dead link" in item for item in check_links.check(self.root)))

    def test_existing_relative_link_cannot_escape_the_skill_root(self):
        self.skill("# Probe\n\nRead [outside](../../outside.md).\n")
        self.write("outside.md", "untrusted context\n")
        failures = check_links.check(self.root)
        self.assertTrue(any("escapes owned skill root" in item for item in failures))

    def test_chain_only_bundle_link_is_rejected(self):
        self.skill("# Probe\n\nRead [notes](./references/notes.md).\n")
        self.write(
            "skills/probe-skill/references/notes.md",
            "Use [template](../assets/template.txt).\n",
        )
        self.write("skills/probe-skill/assets/template.txt", "template\n")
        failures = check_links.check(self.root)
        self.assertTrue(any("not linked directly" in item for item in failures))

    def test_external_link_label_cannot_spoof_a_direct_bundle_link(self):
        self.skill(
            "# Probe\n\nRead "
            "[references/notes.md](https://attacker.invalid/context).\n"
        )
        self.write("skills/probe-skill/references/notes.md", "# Notes\n")
        failures = check_links.check(self.root)
        self.assertTrue(any("not linked directly" in item for item in failures))

    def test_fenced_code_span_is_not_a_pointer(self):
        self.skill("# Probe\n\n```text\n`references/example.md`\n```\n")
        self.assertEqual([], check_links.check(self.root))


class StaleNameCheckerTests(Fixture):
    def _fleet(self, *, agent_description="clean agent", command_description="clean command"):
        self.write(
            "canonical/fleet.json",
            json.dumps(
                {
                    "agents": [{"name": "probe", "description": agent_description}],
                    "commands": [
                        {
                            "name": "probe",
                            "description": command_description,
                            "argument_usage": "clean argument",
                        }
                    ],
                }
            ),
        )

    def test_guide_clean_fixture_is_silent(self):
        self.write("CLAUDE.md", "# entry\n@AGENTS.md\n")
        self.write("scripts/gate_a.py", "x\n")
        self.write("docs/README.md", "x\n")
        (self.root / "agents").mkdir(exist_ok=True)
        self.write(
            "AGENTS.md",
            "# guide\nRun [gate](scripts/gate_a.py). See the `docs/README.md` map and `references/`\n"
            "generically, plus [`agent-authoring/references/x.md`](docs/README.md) as a label.\n",
        )
        self.assertEqual([], check_links._check_guide(self.root))

    def test_guide_missing_claude_import_is_flagged(self):
        self.write("CLAUDE.md", "# entry with no import\n")
        self.write("AGENTS.md", "# guide\n")
        failures = check_links._check_guide(self.root)
        self.assertTrue(any("@AGENTS.md" in f for f in failures), failures)

    def test_guide_fenced_or_prose_import_mention_does_not_satisfy(self):
        # A fenced example or a prose mention must NOT count as the real import line.
        self.write(
            "CLAUDE.md",
            "# entry\nDo not remove the @AGENTS.md line.\n\n```\n@AGENTS.md\n```\n",
        )
        self.write("AGENTS.md", "# guide\n")
        failures = check_links._check_guide(self.root)
        self.assertTrue(any("@AGENTS.md" in f for f in failures), failures)

    def test_guide_dead_markdown_link_is_flagged(self):
        self.write("CLAUDE.md", "@AGENTS.md\n")
        self.write("AGENTS.md", "# guide\nSee [gone](scripts/renamed_away.py).\n")
        failures = check_links._check_guide(self.root)
        self.assertTrue(any("dead link" in f and "renamed_away" in f for f in failures), failures)

    def test_guide_dead_inline_code_path_is_flagged(self):
        self.write("CLAUDE.md", "@AGENTS.md\n")
        (self.root / "scripts").mkdir(exist_ok=True)
        # first segment `scripts` is a real repo entry, so the full token must resolve
        self.write("AGENTS.md", "# guide\nRun `scripts/does_not_exist.py`.\n")
        failures = check_links._check_guide(self.root)
        self.assertTrue(
            any("inline-code path does not resolve" in f and "does_not_exist" in f for f in failures),
            failures,
        )

    def test_guide_generic_and_skill_relative_tokens_are_not_flagged(self):
        # `references/` (no such root dir) and a skill-relative label whose first segment is not a
        # repo-root entry must not be treated as broken repo-root paths.
        self.write("CLAUDE.md", "@AGENTS.md\n")
        self.write("AGENTS.md", "# guide\nEvery `references/` file; see `agent-authoring/refs/x.md`.\n")
        self.assertEqual([], check_links._check_guide(self.root))

    def test_word_boundary_hit_is_flagged(self):
        self.write("skills/probe/SKILL.md", "Hand this to code-reviewer now.\n")
        self.assertTrue(check_stale_names.check(self.root))

    def test_path_and_md_suffix_are_exempt(self):
        self.write(
            "skills/probe/SKILL.md",
            "[safe](references/safe-refactor.md) and safe-refactor.md remain paths.\n",
        )
        self.assertEqual([], check_stale_names.check(self.root))

    def test_canonical_command_description_is_scanned(self):
        self._fleet(command_description="Ask code-reviewer to approve this")
        failures = check_stale_names.check(self.root)
        self.assertTrue(any("commands[0].description" in item for item in failures))

    def test_canonical_agent_description_is_scanned(self):
        self._fleet(agent_description="The sre-engineer owns this")
        failures = check_stale_names.check(self.root)
        self.assertTrue(any("agents[0].description" in item for item in failures))

    def test_clean_replacement_metadata_is_silent(self):
        self._fleet(agent_description="The sre agent owns this", command_description="Ask reviewer")
        self.assertEqual([], check_stale_names.check(self.root))


if __name__ == "__main__":
    unittest.main()
