#!/usr/bin/env python3
"""Red-first contracts for the temporary Phase-2 link and stale-name gates."""

from __future__ import annotations

import json
import os
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

    def test_a_reference_naming_its_own_skill_by_repo_rooted_path_is_flagged(self):
        """The pointer that reads correct and resolves nowhere.

        `skills/<name>/SKILL.md` inside that skill's own references/ resolves neither from the
        reference's directory nor in platforms/copilot/skills/, where the bundle sits under a
        different prefix. Eight of backend-craft's nine references carried it through every green
        gate because CODE_PATH_RE only covers bundle-internal prefixes.
        """
        self.skill("# Probe\n\nRead [notes](./references/notes.md).\n")
        self.write(
            "skills/probe-skill/references/notes.md",
            "# Notes\n\nThe universal rules live in `skills/probe-skill/SKILL.md`.\n",
        )
        failures = check_links.check(self.root)
        self.assertTrue(
            any("points at its own skill by repo-rooted path" in f for f in failures),
            failures,
        )

    def test_the_relative_self_pointer_and_a_sibling_reference_are_both_allowed(self):
        """`../SKILL.md` is the fix, and naming a *different* skill is not this defect."""
        self.skill("# Probe\n\nRead [notes](./references/notes.md).\n")
        self.write(
            "skills/probe-skill/references/notes.md",
            "# Notes\n\nRules live in `../SKILL.md`; ownership sits with "
            "`skills/other-skill/SKILL.md`.\n",
        )
        self.assertEqual([], check_links.check(self.root))

    def test_top_level_frontmatter_comment_is_allowed(self):
        frontmatter = CLEAN_FRONTMATTER.replace(
            'argument-hint: "[the probe]"',
            '# Human-invoked skill; this comment is model-visible context.\n'
            'argument-hint: "[the probe]"',
        )
        self.write("skills/probe-skill/SKILL.md", frontmatter + "\n# Probe\n")
        self.assertEqual([], check_links.check(self.root))

    def test_list_value_uses_shared_syntax_then_fails_skill_field_policy(self):
        frontmatter = CLEAN_FRONTMATTER.replace(
            'argument-hint: "[the probe]"',
            "argument-hint:\n  - one\n  - two",
        )
        self.write("skills/probe-skill/SKILL.md", frontmatter + "\n# Probe\n")
        failures = check_links.check(self.root)
        self.assertTrue(any("value must be one nonblank YAML string" in item for item in failures))
        self.assertFalse(any("malformed top-level frontmatter" in item for item in failures))

    def test_quoted_implicit_scalars_and_collection_text_remain_strings(self):
        for value in ('"false"', '"123"', '"null"', '"[the probe]"'):
            with self.subTest(value=value):
                root = Path(self._tmp.name) / value.strip('"').replace(" ", "-")
                self.root = root
                frontmatter = CLEAN_FRONTMATTER.replace('"[the probe]"', value)
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
            "unmatched-single-hint": CLEAN_FRONTMATTER.replace(
                'argument-hint: "[the probe]"', "argument-hint: 'the probe"
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
            "name: probe-skill", "name: service-lifecycle"
        ).replace(
            'argument-hint: "[the probe]"',
            'argument-hint: "[the probe]"\ndisable-model-invocation: true',
        )
        self.write(
            "skills/service-lifecycle/SKILL.md",
            manual_frontmatter + "\n# Manual probe\n",
        )
        self.assertEqual([], check_links.check(self.root))

        fixture_root = Path(self._tmp.name)
        missing = fixture_root / "missing"
        self.root = missing
        self.write(
            "skills/service-lifecycle/SKILL.md",
            manual_frontmatter.replace("disable-model-invocation: true\n", "")
            + "\n# Manual probe\n",
        )
        self.assertTrue(
            any("manual-only skill must contain frontmatter" in item for item in check_links.check(self.root))
        )

        moved = fixture_root / "moved"
        self.root = moved
        self.write(
            "skills/service-lifecycle/SKILL.md",
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
            any("may disable model invocation" in item for item in check_links.check(self.root))
        )
        # The message must name the current roster, not a stale pair: a reader who trips this needs
        # to know which skills the exception actually covers.
        self.assertTrue(
            any(
                all(name in item for name in check_links.MANUAL_ONLY)
                for item in check_links.check(self.root)
            )
        )

    def test_incident_drill_is_manual_only(self):
        """`incident-drill` spawns paid model sessions; it must never be model-invocable.

        Pinned as its own case because the cost of a regression here is a drill that starts because
        a conversation mentioned an outage.
        """
        self.assertIn("incident-drill", check_links.MANUAL_ONLY)
        frontmatter = CLEAN_FRONTMATTER.replace(
            "name: probe-skill", "name: incident-drill"
        ).replace(
            'argument-hint: "[the probe]"',
            'argument-hint: "[the probe]"\ndisable-model-invocation: true',
        )
        self.write("skills/incident-drill/SKILL.md", frontmatter + "\n# Drill probe\n")
        self.assertEqual([], check_links.check(self.root))

        without = Path(self._tmp.name) / "drill-without"
        self.root = without
        self.write(
            "skills/incident-drill/SKILL.md",
            frontmatter.replace("disable-model-invocation: true\n", "") + "\n# Drill probe\n",
        )
        self.assertTrue(
            any("manual-only skill must contain frontmatter" in item for item in check_links.check(self.root))
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

    def test_root_sidecar_must_be_directly_linked(self):
        self.skill()
        self.write(
            "skills/probe-skill/context-requirements.yaml",
            "apiVersion: example/v1\nkind: ContextRequirements\n",
        )

        failures = check_links.check(self.root)

        self.assertTrue(
            any(
                item.endswith(
                    "skills/probe-skill/SKILL.md: bundled file not linked directly from "
                    "SKILL.md body: context-requirements.yaml"
                )
                for item in failures
            ),
            failures,
        )

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

    def test_path_and_md_suffix_are_exempt_when_the_file_is_really_there(self):
        # The exemption is earned by the file existing, not by the name being retired -- otherwise
        # `agents/prompt-engineer.md` would be exempt too. See
        # test_check_stale_names.test_a_retired_name_with_no_live_file_is_caught_in_path_and_md_form.
        self.write("skills/probe/references/safe-refactor.md", "# Safe refactor\n")
        self.write(
            "skills/probe/SKILL.md",
            "[safe](references/safe-refactor.md) and safe-refactor.md remain paths.\n",
        )
        self.assertEqual([], check_stale_names.check(self.root))

    def test_a_retired_name_with_no_such_file_is_not_exempt_as_a_path(self):
        self.write("skills/probe/SKILL.md", "[lane](../agents/prompt-engineer.md) owns this.\n")
        self.assertTrue(check_stale_names.check(self.root))

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

    def test_a_symlinked_root_does_not_make_every_link_escape(self) -> None:
        """The containment test must canonicalize the root before comparing against it.

        `.resolve()` on the left side and a raw root on the right describe the same directory
        differently, so every legitimate link reads as escaping. macOS temp dirs are
        `/var/folders/...` resolving to `/private/var/...` and Windows hands out 8.3 short paths --
        this passed on Linux and failed both other CI legs. Simulated here with an explicit
        symlink so the Linux leg covers it too.
        """
        if not hasattr(os, "symlink"):  # pragma: no cover - platform without symlinks
            self.skipTest("symlinks unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            real = Path(temporary) / "real"
            (real / "docs").mkdir(parents=True)
            (real / "docs/target.md").write_text("# t\n", encoding="utf-8")
            (real / "README.md").write_text("See [t](docs/target.md).\n", encoding="utf-8")
            link = Path(temporary) / "link"
            try:
                os.symlink(real, link, target_is_directory=True)
            except (OSError, NotImplementedError):  # pragma: no cover - unprivileged Windows
                self.skipTest("cannot create a directory symlink here")
            self.assertNotEqual(link.resolve(), link, "fixture did not produce an aliased root")
            self.assertEqual([], check_links._check_live_doc_links(link))


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
