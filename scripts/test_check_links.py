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

# The real repository root, for the handful of tests that assert against the live tree rather than
# a synthetic fixture. Taken from check_links so the two can never disagree about where root is.
ROOT = check_links.ROOT


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


class LiveDocLinkTests(unittest.TestCase):
    """Live authority docs must not carry dead relative links."""

    def test_live_tree_is_clean(self) -> None:
        self.assertEqual([], check_links._check_live_doc_links(ROOT))

    def test_a_dead_link_in_a_live_doc_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "docs").mkdir()
            (root / "README.md").write_text(
                "See [gone](docs/no-such-file.md).\n", encoding="utf-8"
            )
            failures = check_links._check_live_doc_links(root)
        self.assertTrue(any("dead link" in f for f in failures), failures)

    def test_a_live_link_is_not_flagged(self) -> None:
        """The complement: without this, a checker that flags everything would pass the test above."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "docs").mkdir()
            (root / "docs/real.md").write_text("# real\n", encoding="utf-8")
            (root / "README.md").write_text("See [real](docs/real.md).\n", encoding="utf-8")
            self.assertEqual([], check_links._check_live_doc_links(root))


class EvidenceBannerTests(unittest.TestCase):
    """The evidence-default banner is duplicated 29 times; pin the copies in step.

    A shared reference is architecturally impossible here — check_links forbids a relative link
    escaping its skill root — so duplication is the design and drift is the risk it carries.
    """

    def test_live_skills_share_one_banner(self) -> None:
        self.assertEqual([], check_links._check_evidence_banner(ROOT))

    def test_one_reworded_copy_is_flagged(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, tail in (("alpha", "never upgrade it."), ("beta", "never upgrade it."),
                               ("gamma", "must never upgrade it.")):
                skill = root / "skills" / name
                skill.mkdir(parents=True)
                (skill / "SKILL.md").write_text(
                    f"---\nname: {name}\n---\n\n"
                    "> **Evidence default — `[unverified]`.** Handoffs "
                    f"{tail}\n\nbody\n",
                    encoding="utf-8",
                )
            failures = check_links._check_evidence_banner(root)
        self.assertTrue(any("gamma" in f and "banner differs" in f for f in failures), failures)

    def test_a_skill_that_drops_the_banner_is_flagged_once_others_carry_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, banner in (("alpha", True), ("beta", True), ("naked", False)):
                skill = root / "skills" / name
                skill.mkdir(parents=True)
                text = f"---\nname: {name}\n---\n\n"
                if banner:
                    text += "> **Evidence default \u2014 `[unverified]`.** Handoffs never upgrade it.\n\n"
                (skill / "SKILL.md").write_text(text + "body\n", encoding="utf-8")
            failures = check_links._check_evidence_banner(root)
        self.assertTrue(any("naked" in f and "missing" in f for f in failures), failures)

    def test_a_tree_with_no_banners_at_all_is_left_alone(self) -> None:
        """A minimal fixture is not a fleet that lost its evidence contract."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            skill = root / "skills" / "alpha"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("---\nname: alpha\n---\n\nbody\n", encoding="utf-8")
            self.assertEqual([], check_links._check_evidence_banner(root))


class EscapingLinkTests(unittest.TestCase):
    """A link that resolves outside the repository is a defect, not a pass.

    `.exists()` on an escaped path answers a question about the HOST: a root README link to
    `../../etc/passwd` resolves to a real file on Unix and to nothing on Windows, so the check
    would be host-dependent and falsely green for a target no consumer can resolve.
    """

    def test_a_link_escaping_the_root_is_flagged_even_when_the_host_has_it(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / "docs").mkdir()
            depth = len(root.parts) + 2
            escape = "/".join([".."] * depth) + "/etc/passwd"
            (root / "README.md").write_text(f"See [x]({escape}).\n", encoding="utf-8")
            failures = check_links._check_live_doc_links(root)
        self.assertTrue(any("escapes the repository" in f for f in failures), failures)


if __name__ == "__main__":
    unittest.main()
