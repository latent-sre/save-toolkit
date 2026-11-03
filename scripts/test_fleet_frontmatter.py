#!/usr/bin/env python3
"""Contracts for the one shared fleet frontmatter grammar: YAML, as the hosts read it."""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

import yaml

import fleet_frontmatter as frontmatter

PROBE = Path("probe.md")
ROOT = Path(__file__).resolve().parents[1]
FLEET_ROOTS = ("agents", "skills", "commands", ".github/agents", ".github/skills", "com.github.copilot")


class FrontmatterParserTests(unittest.TestCase):
    def raises_or_collects(self, text: str, problem: str) -> frontmatter.ParsedFrontmatter:
        """Strict mode raises `problem`; lenient mode returns its parse with `problem` collected."""
        with self.assertRaisesRegex(frontmatter.FrontmatterError, problem):
            frontmatter.parse(text, PROBE, mode="strict")
        parsed = frontmatter.parse(text, PROBE, mode="lenient")
        self.assertTrue(any(re.search(problem, item) for item in parsed.problems), parsed.problems)
        return parsed

    def test_missing_fences_raise_strictly_and_collect_leniently(self) -> None:
        for text, problem in (("name: probe\n", "missing opening"), ("---\nname: probe\n", "missing closing")):
            with self.subTest(problem=problem):
                collected = self.raises_or_collects(text, problem)
                self.assertEqual({}, collected.fields)
                self.assertEqual(text, collected.body)

    def test_scalars_arrive_typed_the_way_the_hosts_read_them(self) -> None:
        parsed = frontmatter.parse(
            "---\n"
            "my_key: true\n"
            "  # an indented whole-line comment\n"
            "number: 123\n"
            "nullish: null\n"
            "flow: [Read, Grep]\n"
            'quoted: "true"\n'
            "---\n",
            PROBE,
            mode="strict",
        )
        self.assertEqual(
            {"my_key": True, "number": 123, "nullish": None, "flow": ["Read", "Grep"], "quoted": "true"},
            parsed.fields,
        )
        self.assertEqual(
            {"my_key": "plain", "number": "plain", "nullish": "plain", "flow": "list", "quoted": "double-quoted"},
            parsed.styles,
        )

    def test_block_lists_quoted_items_and_empty_values(self) -> None:
        parsed = frontmatter.parse(
            "---\n"
            "tools:\n"
            "  - Read\n"
            "  - 'Web''Fetch'\n"
            '  - "Agent(reviewer, researcher)"\n'
            "empty:\n"
            "next: value\n"
            "---\n",
            PROBE,
            mode="strict",
        )
        self.assertEqual(["Read", "Web'Fetch", "Agent(reviewer, researcher)"], parsed.fields["tools"])
        self.assertIsNone(parsed.fields["empty"])  # an empty value is YAML null, not an empty list
        self.assertEqual("value", parsed.fields["next"])
        self.assertEqual("list", parsed.styles["tools"])

    def test_block_scalars_keep_yaml_folding_and_chomping(self) -> None:
        cases = {
            ">": "first line\nsecond line\n",
            ">-": "first line\nsecond line",
            "|": "first line\n\nsecond line\n",
            "|-": "first line\n\nsecond line",
        }
        for marker, expected in cases.items():
            with self.subTest(marker=marker):
                parsed = frontmatter.parse(
                    f"---\ndescription: {marker}\n  first line\n\n  second line\n---\n", PROBE, mode="strict"
                )
                self.assertEqual(expected, parsed.fields["description"])
                self.assertEqual("block", parsed.styles["description"])

    def test_single_quoted_style_is_recorded(self) -> None:
        parsed = frontmatter.parse("---\nname: 'it''s'\n---\n", PROBE, mode="strict")
        self.assertEqual({"name": "it's"}, parsed.fields)
        self.assertEqual({"name": "single-quoted"}, parsed.styles)

    def test_tool_specs_share_one_nested_argument_aware_splitter(self) -> None:
        self.assertEqual(
            ["Read", "Agent(reviewer, researcher)", "Grep"],
            frontmatter.split_tool_specs("Read, Agent(reviewer, researcher), Grep"),
        )
        self.assertEqual(["Read", "Grep"], frontmatter.split_tool_specs("Read, Grep"))
        self.assertEqual(
            ["Read", "Grep"], frontmatter.split_tool_specs(["Read", "", "Grep"])
        )
        # A missing or empty field grants nothing; it must not become a tool named "None".
        self.assertEqual([], frontmatter.split_tool_specs(None))
        self.assertEqual([], frontmatter.split_tool_specs(""))

    def test_tool_grants_keep_the_base_of_a_malformed_entry(self) -> None:
        """Authority checks reason over every grant's base; only the syntax verdict differs."""
        cases = {
            "Read": ("Read", None, True),
            "Bash(git diff:*)": ("Bash", "git diff:*", True),
            "Bash()": ("Bash", "", True),
            "Agent(a(b))": ("Agent", "a(b)", True),
            "mcp__server__tool": ("mcp__server__tool", None, True),
            "Agent (save-toolkit:reviewer)": ("Agent", None, False),
            "Read)": ("Read)", None, False),
            "Bash(unclosed": ("Bash", None, False),
        }
        for spec, (base, arguments, well_formed) in cases.items():
            with self.subTest(spec=spec):
                self.assertEqual(
                    frontmatter.ToolGrant(spec, base, arguments, well_formed),
                    frontmatter.parse_tool_grant(spec),
                )
        self.assertEqual(
            ["Read", "Agent"],
            [grant.base for grant in frontmatter.tool_grants("Read, Agent(x, y)")],
        )

    def test_delegation_requires_an_exact_plugin_qualified_allowlist(self) -> None:
        def targets(*specs: str) -> list[str]:
            grants = [frontmatter.parse_tool_grant(spec) for spec in specs]
            return frontmatter.delegation_targets(grants, PROBE, plugin="save-toolkit")

        for spec, message in (
            ("Agent", "Agent tool must declare an explicit target allowlist"),
            ("Agent (save-toolkit:reviewer)", "Agent tool must declare an explicit target allowlist"),
            ("Agent(save-toolkit:reviewer(x))", "Agent tool must declare an explicit target allowlist"),
            ("Agent(reviewer)", "invalid Agent target 'reviewer'"),
            ("Agent(other:reviewer)", "invalid Agent target"),
            ("Agent(save-toolkit:*)", "invalid Agent target"),
            ("Agent(save-toolkit:reviewer,)", "invalid Agent target ''"),
            ("Agent(save-toolkit:reviewer:extra)", "invalid Agent target"),
            ("Agent(save-toolkit:reviewer, save-toolkit:reviewer)", "duplicate Agent target 'reviewer'"),
        ):
            with self.subTest(spec=spec), self.assertRaisesRegex(ValueError, f"^probe.md: {message}"):
                targets(spec)
        self.assertEqual(
            ["reviewer", "scribe", "researcher"],
            targets("Read", "Agent(save-toolkit:reviewer, save-toolkit:scribe, save-toolkit:researcher)"),
        )
        self.assertEqual([], targets("Read", "Grep"))

    def test_yaml_syntax_errors_name_their_line_and_end_the_parse(self) -> None:
        """Nothing after a syntax error is defined, so lenient mode reports it alone."""
        for text in (
            '---\nname: probe\nnext: "unterminated\nafter: kept\n---\n',
            "---\nname: probe\ndescription: a plain scalar: with a mapping colon\n---\n",
            "---\nname: probe\n\tindented: with a tab\n---\n",
        ):
            with self.subTest(text=text):
                # YAML reports an unterminated quote where the stream ended, so only the file prefix is pinned.
                parsed = self.raises_or_collects(text, r"probe\.md:[0-9]+: invalid frontmatter YAML")
                self.assertEqual({}, parsed.fields)
                self.assertEqual(1, len(parsed.problems))

    def test_duplicate_keys_fail_and_lenient_mode_keeps_the_first_value(self) -> None:
        parsed = self.raises_or_collects("---\nname: first\nname: second\nafter: kept\n---\n",
                                         "probe.md:3: duplicate frontmatter key 'name'")
        self.assertEqual("first", parsed.fields["name"])
        self.assertEqual("kept", parsed.fields["after"])

    def test_non_mapping_documents_and_non_string_keys_are_rejected(self) -> None:
        parsed = self.raises_or_collects("---\n- Read\n- Grep\n---\n", "probe.md:2: frontmatter must be a YAML mapping")
        self.assertEqual({}, parsed.fields)
        parsed = self.raises_or_collects("---\nname: probe\n1: numeric key\n---\n",
                                         "probe.md:3: frontmatter keys must be strings, not 1")
        self.assertEqual({"name": "probe"}, parsed.fields)

    def test_an_empty_block_between_the_fences_parses_to_no_fields(self) -> None:
        parsed = frontmatter.parse("---\n---\nbody\n", PROBE, mode="strict")
        self.assertEqual({}, parsed.fields)
        self.assertEqual("body\n", parsed.body)

    def test_body_raw_lines_and_terminal_newline_are_preserved(self) -> None:
        text = "---\nname: probe\n---\n\n# Body\n"
        parsed = frontmatter.parse(text, PROBE, mode="strict")
        self.assertEqual(("name: probe",), parsed.raw_lines)
        self.assertEqual("# Body\n", parsed.body)

    def test_file_entrypoint_uses_the_same_parser(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "probe.md"
            path.write_text("---\nname: probe\n---\nbody\n", encoding="utf-8")
            parsed = frontmatter.parse_file(path, mode="strict")
        self.assertEqual("probe", parsed.fields["name"])
        self.assertEqual("body\n", parsed.body)

    def test_every_fleet_file_parses_to_what_a_yaml_host_reads(self) -> None:
        """The shared parser and a plain safe load agree on every canonical and projected file."""
        paths = [path for root in FLEET_ROOTS for path in sorted((ROOT / root).rglob("*.md"))
                 if path.read_text(encoding="utf-8").startswith("---\n")]
        self.assertGreater(len(paths), 50, "the fleet roots moved; update FLEET_ROOTS")
        for path in paths:
            with self.subTest(path=path.relative_to(ROOT).as_posix()):
                parsed = frontmatter.parse_file(path, mode="strict")
                self.assertEqual(yaml.safe_load("\n".join(parsed.raw_lines) + "\n") or {}, parsed.fields)

    def test_frontmatter_key_grammar_is_not_redeclared_by_callers(self) -> None:
        for relative in (
            Path("scripts/check_links.py"),
            Path("scripts/generate_platform_adapters.py"),
        ):
            with self.subTest(path=relative.as_posix()):
                text = (ROOT / relative).read_text(encoding="utf-8")
                self.assertNotIn("KEY_RE =", text)
                self.assertNotIn("yaml.safe_load(", text, "frontmatter is read through fleet_frontmatter only")
        eval_source = "\n".join(path.read_text(encoding="utf-8") for path in (
            ROOT / "evals/build_probe.py", *sorted((ROOT / "evals/probe").glob("*.py"))))
        self.assertNotIn('yaml.safe_load("\\n".join(lines[1:end]))', eval_source)


if __name__ == "__main__":
    unittest.main()
