#!/usr/bin/env python3
"""Contracts for the one shared fleet frontmatter grammar."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import fleet_frontmatter as frontmatter


class FrontmatterParserTests(unittest.TestCase):
    def test_missing_fences_raise_strictly_and_collect_leniently(self) -> None:
        missing_open = "name: probe\n"
        with self.assertRaisesRegex(frontmatter.FrontmatterError, "missing opening"):
            frontmatter.parse(missing_open, Path("probe.md"), mode="strict")
        collected = frontmatter.parse(missing_open, Path("probe.md"), mode="lenient")
        self.assertEqual({}, collected.fields)
        self.assertEqual(missing_open, collected.body)
        self.assertTrue(any("missing opening" in problem for problem in collected.problems))

        missing_close = "---\nname: probe\n"
        with self.assertRaisesRegex(frontmatter.FrontmatterError, "missing closing"):
            frontmatter.parse(missing_close, Path("probe.md"), mode="strict")
        collected = frontmatter.parse(missing_close, Path("probe.md"), mode="lenient")
        self.assertEqual({}, collected.fields)
        self.assertEqual(missing_close, collected.body)
        self.assertTrue(any("missing closing" in problem for problem in collected.problems))

    def test_keys_comments_and_plain_scalars_use_the_small_shared_grammar(self) -> None:
        parsed = frontmatter.parse(
            "---\n"
            "my_key: true\n"
            "  # an indented whole-line comment\n"
            "number: 123\n"
            "nullish: null\n"
            "flow: [Read, Grep]\n"
            "---\n",
            Path("probe.md"),
            mode="strict",
        )
        self.assertEqual(
            {"my_key": "true", "number": "123", "nullish": "null", "flow": "[Read, Grep]"},
            parsed.fields,
        )

    def test_scalar_lists_and_empty_values_match_the_adapter_grammar(self) -> None:
        parsed = frontmatter.parse(
            "---\n"
            "tools:\n"
            "  - Read\n"
            "  - 'Web''Fetch'\n"
            '  - "Agent(reviewer, researcher)"\n'
            "empty:\n"
            "next: value\n"
            "---\n",
            Path("probe.md"),
            mode="strict",
        )
        self.assertEqual(
            ["Read", "Web'Fetch", "Agent(reviewer, researcher)"], parsed.fields["tools"]
        )
        self.assertEqual([], parsed.fields["empty"])
        self.assertEqual("value", parsed.fields["next"])

    def test_all_current_block_markers_preserve_space_folding(self) -> None:
        for marker in (">", ">-", "|", "|-"):
            with self.subTest(marker=marker):
                parsed = frontmatter.parse(
                    f"---\ndescription: {marker}\n  first line\n\n  second line\n---\n",
                    Path("probe.md"),
                    mode="strict",
                )
                self.assertEqual("first line second line", parsed.fields["description"])

    def test_quote_decoding_preserves_the_pinned_adapter_behavior(self) -> None:
        self.assertEqual("quoted", frontmatter.decode_scalar('"quoted"'))
        self.assertEqual("abc'", frontmatter.decode_scalar("abc'"))
        self.assertEqual("'abc", frontmatter.decode_scalar("'abc"))
        self.assertEqual("abc", frontmatter.decode_scalar("'abc'"))
        self.assertEqual("it's", frontmatter.decode_scalar("'it''s'"))
        self.assertEqual("plain", frontmatter.decode_scalar("plain"))

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
            return frontmatter.delegation_targets(grants, Path("probe.md"), plugin="save-toolkit")

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

    def test_invalid_double_quote_raises_or_is_collected(self) -> None:
        text = '---\nname: "unterminated\nnext: kept\n---\n'
        with self.assertRaisesRegex(frontmatter.FrontmatterError, "invalid quoted scalar"):
            frontmatter.parse(text, Path("probe.md"), mode="strict")
        parsed = frontmatter.parse(text, Path("probe.md"), mode="lenient")
        self.assertEqual('"unterminated', parsed.fields["name"])
        self.assertEqual("kept", parsed.fields["next"])
        self.assertTrue(any("invalid quoted scalar" in problem for problem in parsed.problems))

    def test_duplicate_keys_fail_and_lenient_mode_keeps_the_first_value(self) -> None:
        text = "---\nname: first\nname: second\nafter: kept\n---\n"
        with self.assertRaisesRegex(frontmatter.FrontmatterError, "duplicate frontmatter key"):
            frontmatter.parse(text, Path("probe.md"), mode="strict")
        parsed = frontmatter.parse(text, Path("probe.md"), mode="lenient")
        self.assertEqual("first", parsed.fields["name"])
        self.assertEqual("kept", parsed.fields["after"])
        self.assertTrue(any("duplicate frontmatter key" in problem for problem in parsed.problems))

    def test_malformed_lines_fail_or_collect_without_stopping_later_diagnostics(self) -> None:
        text = "---\nname: probe\n  malformed\nafter: kept\n---\n"
        with self.assertRaisesRegex(frontmatter.FrontmatterError, "unsupported frontmatter syntax"):
            frontmatter.parse(text, Path("probe.md"), mode="strict")
        parsed = frontmatter.parse(text, Path("probe.md"), mode="lenient")
        self.assertEqual({"name": "probe", "after": "kept"}, parsed.fields)
        self.assertEqual(1, len(parsed.problems))

    def test_body_raw_lines_and_terminal_newline_are_preserved(self) -> None:
        text = "---\nname: probe\n---\n\n# Body\n"
        parsed = frontmatter.parse(text, Path("probe.md"), mode="strict")
        self.assertEqual(("name: probe",), parsed.raw_lines)
        self.assertEqual("# Body\n", parsed.body)

    def test_file_entrypoint_uses_the_same_parser(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "probe.md"
            path.write_text("---\nname: probe\n---\nbody\n", encoding="utf-8")
            parsed = frontmatter.parse_file(path, mode="strict")
        self.assertEqual("probe", parsed.fields["name"])
        self.assertEqual("body\n", parsed.body)

    def test_frontmatter_key_grammar_is_not_redeclared_by_callers(self) -> None:
        root = Path(__file__).resolve().parents[1]
        for relative in (
            Path("scripts/check_links.py"),
            Path("scripts/generate_platform_adapters.py"),
        ):
            with self.subTest(path=relative.as_posix()):
                text = (root / relative).read_text(encoding="utf-8")
                self.assertNotIn("KEY_RE =", text)
        eval_source = "\n".join(path.read_text(encoding="utf-8") for path in (
            root / "evals/build_probe.py", *sorted((root / "evals/probe").glob("*.py"))))
        self.assertNotIn('yaml.safe_load("\\n".join(lines[1:end]))', eval_source)


if __name__ == "__main__":
    unittest.main()
