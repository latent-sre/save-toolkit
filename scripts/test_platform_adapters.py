"""Contract tests for the generated host adapters."""

from __future__ import annotations

import os
import re
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import generate_platform_adapters as adapters


ROOT = Path(__file__).resolve().parents[1]


class PlatformAdapterTests(unittest.TestCase):
    @staticmethod
    def _copy_canonical_sources(root: Path) -> None:
        """Copy the authored agents/ and skills/ into a temp root — the generator's inputs."""
        shutil.copytree(ROOT / "agents", root / "agents")
        shutil.copytree(ROOT / "skills", root / "skills")

    @staticmethod
    def _copy_platform_contract_files(root: Path) -> None:
        """Create a complete valid manifest/hook fixture before applying one mutation."""
        for relative in (
            Path(".claude-plugin/plugin.json"),
            Path("plugin.json"),
            Path("hooks/hooks.json"),
        ):
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)

    @staticmethod
    def _copilot_tools(name: str) -> list[str]:
        rendered = adapters.render_copilot_agent(ROOT / "agents" / f"{name}.md")
        frontmatter = rendered.split("---", 2)[1]
        return json.loads(
            next(line for line in frontmatter.splitlines() if line.startswith("tools: "))[7:]
        )

    @staticmethod
    def _copilot_agents(name: str) -> list[str] | None:
        rendered = adapters.render_copilot_agent(ROOT / "agents" / f"{name}.md")
        frontmatter = rendered.split("---", 2)[1]
        value = next(
            (line[8:] for line in frontmatter.splitlines() if line.startswith("agents: ")),
            None,
        )
        return None if value is None else json.loads(value)

    @staticmethod
    def _copilot_handoffs(name: str) -> list[dict[str, object]] | None:
        rendered = adapters.render_copilot_agent(ROOT / "agents" / f"{name}.md")
        frontmatter = rendered.split("---", 2)[1]
        value = next(
            (line[10:] for line in frontmatter.splitlines() if line.startswith("handoffs: ")),
            None,
        )
        return None if value is None else json.loads(value)

    def test_committed_outputs_match_canonical_sources(self) -> None:
        self.assertEqual([], adapters.validate_generated_outputs(ROOT))

    def test_guarded_copilot_agents_do_not_receive_execute(self) -> None:
        for name in sorted(adapters.GUARDED_AGENTS):
            self.assertNotIn("execute", self._copilot_tools(name), name)

    def test_builder_copilot_agent_keeps_edit_and_execute(self) -> None:
        tools = self._copilot_tools("software-engineer")
        self.assertIn("edit", tools)
        self.assertIn("execute", tools)

    def test_scribe_copilot_agent_can_edit_but_cannot_execute_or_delegate(self) -> None:
        self.assertEqual(["read", "search", "edit"], self._copilot_tools("scribe"))

    def test_copilot_agents_preserve_every_canonical_delegation_allowlist(self) -> None:
        expected = {
            "agent-engineer": ["researcher"],
            "observability-engineer": ["scribe", "researcher"],
            "repository-investigator": None,
            "researcher": None,
            "reviewer": None,
            "scribe": None,
            "software-engineer": ["reviewer", "scribe", "researcher"],
            "sre": ["researcher"],
        }
        self.assertEqual(
            set(expected),
            {path.stem for path in (ROOT / "agents").glob("*.md")},
            "every canonical agent must have an explicit Copilot delegation expectation",
        )
        for name, allowed_agents in expected.items():
            with self.subTest(agent=name):
                self.assertEqual(allowed_agents, self._copilot_agents(name))
                self.assertEqual(allowed_agents is not None, "agent" in self._copilot_tools(name))

    def test_copilot_agent_rejects_an_unscoped_agent_tool(self) -> None:
        agent = (
            "---\n"
            "name: probe-agent\n"
            "description: Probe fail-closed Copilot delegation generation.\n"
            "tools: Read, Agent\n"
            "---\n\n# Probe\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "probe-agent.md"
            source.write_text(agent, encoding="utf-8", newline="\n")
            with self.assertRaisesRegex(ValueError, "explicit target allowlist"):
                adapters.render_copilot_agent(source)

    def test_copilot_agents_offer_the_current_roster_handoff_graph(self) -> None:
        expected_targets = {
            "agent-engineer": [],
            "observability-engineer": ["sre", "scribe"],
            "repository-investigator": [],
            "researcher": [],
            "reviewer": ["software-engineer"],
            "scribe": ["software-engineer"],
            "software-engineer": ["reviewer", "scribe"],
            "sre": ["scribe", "software-engineer"],
        }
        for name, targets in expected_targets.items():
            with self.subTest(agent=name):
                handoffs = self._copilot_handoffs(name) or []
                self.assertEqual(targets, [item.get("agent") for item in handoffs])
                self.assertEqual(len(targets), len({item.get("agent") for item in handoffs}))
                for handoff in handoffs:
                    self.assertIs(handoff.get("send"), True)
                    self.assertTrue(str(handoff.get("label", "")).strip())
                    self.assertTrue(str(handoff.get("prompt", "")).strip())
                    self.assertNotEqual("researcher", handoff["agent"])
                    if handoff["agent"] == "reviewer":
                        self.assertIn("[UNTRUSTED]", handoff["prompt"])
                        self.assertIn("Re-derive the diff", handoff["prompt"])
                        self.assertIn("Do not modify files", handoff["prompt"])
                    if handoff["agent"] == "scribe":
                        self.assertIn("explicitly approved", handoff["prompt"])
                        self.assertIn("without writing", handoff["prompt"])
                    if handoff["agent"] == "software-engineer":
                        self.assertIn("explicitly approved", handoff["prompt"])
                        self.assertIn("[UNTRUSTED]", handoff["prompt"])
                        self.assertIn("without editing", handoff["prompt"])
                    if handoff["agent"] == "sre":
                        self.assertIn("[UNTRUSTED]", handoff["prompt"])
                        self.assertIn("without applying production changes", handoff["prompt"])

    def test_copilot_handoffs_are_independent_of_model_called_subagents(self) -> None:
        self.assertNotIn("sre", self._copilot_agents("observability-engineer") or [])
        self.assertEqual(["software-engineer"], [
            handoff["agent"] for handoff in self._copilot_handoffs("reviewer") or []
        ])
        self.assertNotIn("agent", self._copilot_tools("reviewer"))
        self.assertEqual(["software-engineer"], [
            handoff["agent"] for handoff in self._copilot_handoffs("scribe") or []
        ])
        self.assertNotIn("agent", self._copilot_tools("scribe"))

    def test_copilot_research_boundaries_are_mutually_exclusive(self) -> None:
        self.assertEqual(["read", "search"], self._copilot_tools("repository-investigator"))
        self.assertEqual(["web"], self._copilot_tools("researcher"))
        for name in sorted(
            path.stem for path in (ROOT / "agents").glob("*.md") if path.stem != "researcher"
        ):
            self.assertNotIn("web", self._copilot_tools(name), name)

    def test_generated_agent_descriptions_use_host_native_names(self) -> None:
        for source in sorted((ROOT / "agents").glob("*.md")):
            copilot = adapters.render_copilot_agent(source)
            frontmatter = copilot.split("---", 2)[1]
            description = json.loads(
                next(line for line in frontmatter.splitlines() if line.startswith("description: "))[13:]
            )
            self.assertNotIn("save-toolkit:", description, source.name)
        self.assertIn("eng-ladder", adapters.render_copilot_agent(ROOT / "agents/software-engineer.md"))

    def test_copilot_agent_prompt_over_30000_characters_is_rejected(self) -> None:
        agent = (
            "---\n"
            "name: probe-agent\n"
            "description: Probe the generated Copilot prompt-size boundary.\n"
            "tools: Read, Grep, Glob\n"
            "---\n\n"
            + ("x" * 30_001)
            + "\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "probe-agent.md"
            source.write_text(agent, encoding="utf-8", newline="\n")
            with self.assertRaisesRegex(ValueError, "30,000-character maximum"):
                adapters.render_copilot_agent(source)

    def test_manual_skills_get_host_native_invocation_controls(self) -> None:
        for name in sorted(adapters.MANUAL_ONLY):
            copilot = (ROOT / adapters.COPILOT_SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
            self.assertIn("disable-model-invocation: true", copilot)
            self.assertIn("explicit-only through Copilot's frontmatter switch", copilot)

    def test_platform_manifests_agree(self) -> None:
        self.assertEqual([], adapters.validate_platform_contracts(ROOT))

    def test_each_platform_manifest_is_required(self) -> None:
        manifests = (
            Path(".claude-plugin/plugin.json"),
            Path("plugin.json"),
        )
        for relative in manifests:
            with self.subTest(path=relative.as_posix()), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                self._copy_platform_contract_files(root)
                self.assertEqual([], adapters.validate_platform_contracts(root))
                target = root / relative
                target.unlink()
                failures = adapters.validate_platform_contracts(root)
                self.assertTrue(failures, "deleting a required manifest must fail validation")

    def test_shared_manifest_identity_is_mutation_guarded(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self._copy_platform_contract_files(root)
            self.assertEqual([], adapters.validate_platform_contracts(root))
            target = root / "plugin.json"
            manifest = json.loads(target.read_text(encoding="utf-8"))
            manifest["name"] = "different-plugin"
            target.write_text(json.dumps(manifest), encoding="utf-8", newline="\n")
            failures = adapters.validate_platform_contracts(root)
        self.assertTrue(
            any("identity field 'name' differs from Claude manifest" in failure for failure in failures),
            failures,
        )

    def test_copilot_component_paths_cannot_be_deduplicated_to_claude(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self._copy_platform_contract_files(root)
            self.assertEqual([], adapters.validate_platform_contracts(root))
            shutil.copy2(root / ".claude-plugin/plugin.json", root / "plugin.json")
            failures = adapters.validate_platform_contracts(root)
        for field in ("agents", "skills", "hooks"):
            with self.subTest(field=field):
                self.assertTrue(
                    any(f"plugin.json: {field} must be" in failure for failure in failures),
                    failures,
                )

    def test_byte_drift_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self._copy_canonical_sources(root)
            for relative in adapters.GENERATED_ROOTS:
                shutil.copytree(ROOT / relative, root / relative)
            target = root / adapters.COPILOT_AGENTS / "software-engineer.agent.md"
            target.write_text(target.read_text(encoding="utf-8") + "\nmanual edit\n", encoding="utf-8")
            failures = adapters.validate_generated_outputs(root)
        self.assertTrue(any("generated output drift" in failure for failure in failures))

    def test_retired_generated_root_present_on_disk_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self.assertEqual([], adapters._retired_generated_root_failures(root))
            for retired_root in adapters.RETIRED_GENERATED_ROOTS:
                retired = root / retired_root
                retired.mkdir(parents=True)
                (retired / "leftover.md").write_text("stale mirror\n", encoding="utf-8")
                failures = adapters._retired_generated_root_failures(root)
                with self.subTest(retired_root=retired_root.as_posix()):
                    self.assertTrue(
                        any(f.startswith(f"{retired_root.as_posix()}:") for f in failures),
                        failures,
                    )

    def test_gitattributes_missing_eol_rule_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            text = (ROOT / ".gitattributes").read_text(encoding="utf-8")
            # drop the *.py rule specifically
            broken = "\n".join(
                line for line in text.splitlines() if not line.startswith("*.py")
            ) + "\n"
            (root / ".gitattributes").write_text(broken, encoding="utf-8", newline="\n")
            failures = adapters._gitattributes_failures(root)
        self.assertTrue(any("eol=lf' rule for *.py" in f for f in failures), failures)

    def test_gitattributes_must_govern_its_own_line_endings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            text = (ROOT / ".gitattributes").read_text(encoding="utf-8")
            broken = "\n".join(
                line for line in text.splitlines() if not line.startswith(".gitattributes ")
            ) + "\n"
            (root / ".gitattributes").write_text(broken, encoding="utf-8", newline="\n")
            failures = adapters._gitattributes_failures(root)
        self.assertTrue(any("rule for .gitattributes" in f for f in failures), failures)

    def test_recovery_patches_are_governed_by_the_lf_policy(self) -> None:
        # Recovery patches under docs/reviews/ diff sources that are themselves eol=lf. Without
        # the rule, core.autocrlf hands a fresh Windows clone CRLF patches that no longer apply,
        # so a preserved snapshot silently stops being recoverable.
        #
        # `*.patch` is named literally rather than iterated from GITATTRIBUTES_REQUIRED_EOL on
        # purpose: deriving it would let a co-revert of the tuple entry and the .gitattributes
        # rule shrink the loop and pass. Reverting either half alone, or both, must fail here.
        self.assertIn("*.patch", adapters.GITATTRIBUTES_REQUIRED_EOL)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            text = (ROOT / ".gitattributes").read_text(encoding="utf-8")
            broken = "\n".join(
                line for line in text.splitlines() if not line.startswith("*.patch")
            ) + "\n"
            (root / ".gitattributes").write_text(broken, encoding="utf-8", newline="\n")
            failures = adapters._gitattributes_failures(root)
        self.assertTrue(any("eol=lf' rule for *.patch" in f for f in failures), failures)

    def test_generated_cr_byte_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / ".gitattributes").write_bytes(
                (ROOT / ".gitattributes").read_bytes()
            )
            target = root / adapters.COPILOT_AGENTS / "probe.agent.md"
            target.parent.mkdir(parents=True)
            target.write_bytes(b"line one\r\nline two\r\n")
            failures = adapters._gitattributes_failures(root)
        self.assertTrue(any("carries a CR byte" in f for f in failures), failures)

    def test_binary_asset_with_cr_byte_is_not_flagged(self) -> None:
        # A binary passthrough asset (PNG, etc.) routinely contains 0x0D and must not read as a
        # line-ending regression — the CR check is scoped to LF-governed text suffixes.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / ".gitattributes").write_bytes((ROOT / ".gitattributes").read_bytes())
            asset = root / adapters.COPILOT_SKILLS / "probe" / "assets" / "logo.png"
            asset.parent.mkdir(parents=True)
            asset.write_bytes(b"\x89PNG\r\n\x1a\n\x00\r\x00binary\r\n")
            self.assertEqual([], adapters._gitattributes_failures(root))

    def test_crlf_code_asset_is_normalized_in_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self._copy_canonical_sources(root)
            # find a real projected code asset and give the source CRLF line endings
            script = next(
                p for p in (root / "skills").rglob("*.py")
                if "scripts" in p.parts and "__pycache__" not in p.parts
            )
            lf = script.read_text(encoding="utf-8")
            script.write_bytes(lf.replace("\n", "\r\n").encode("utf-8"))
            outputs = adapters.expected_outputs(root)
            relative = script.relative_to(root / "skills")
            projected = [
                blob for path, blob in outputs.items()
                if path.parts[-len(relative.parts):] == relative.parts
                and adapters.COPILOT_SKILLS in path.parents
            ]
            self.assertTrue(projected, "code asset was not projected")
            for blob in projected:
                self.assertNotIn(b"\r", blob, "CRLF source leaked into a generated code asset")

    def test_directory_swap_failure_restores_every_existing_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self._copy_canonical_sources(root)
            for relative in adapters.GENERATED_ROOTS:
                destination = root / relative
                destination.mkdir(parents=True)
                (destination / "sentinel.txt").write_text(relative.as_posix(), encoding="utf-8")

            real_replace = adapters.os.replace

            def fail_second_stage(source: str | Path, destination: str | Path) -> None:
                source_path = Path(source)
                destination_path = Path(destination)
                if destination_path == root / adapters.COPILOT_SKILLS and "new" in source_path.parts:
                    raise OSError("injected stage swap failure")
                real_replace(source, destination)

            with mock.patch.object(adapters.os, "replace", side_effect=fail_second_stage):
                with self.assertRaisesRegex(OSError, "injected"):
                    adapters.write_generated_outputs(root)

            for relative in adapters.GENERATED_ROOTS:
                sentinel = root / relative / "sentinel.txt"
                self.assertEqual(relative.as_posix(), sentinel.read_text(encoding="utf-8"), relative)

    def test_generated_root_ancestor_indirection_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self._copy_canonical_sources(root)
            (root / ".github").mkdir()
            real_check = adapters._is_link_or_reparse

            def mark_github_as_indirection(path: Path) -> bool:
                return path == root / ".github" or real_check(path)

            with mock.patch.object(adapters, "_is_link_or_reparse", side_effect=mark_github_as_indirection):
                with self.assertRaisesRegex(ValueError, "must not traverse"):
                    adapters.write_generated_outputs(root)


    def test_a_real_symlinked_directory_in_canonical_sources_is_refused(self) -> None:
        """The link-rejection control, exercised with a real symlink rather than a mock.

        The generator refuses to walk links so a projection cannot silently absorb content from
        outside the repository, and `os.walk(..., followlinks=False)` backs that up. The only
        existing coverage patched `_is_link_or_reparse` and tested the ancestor path, so the
        in-walk rejection -- the branch that actually fires on a link INSIDE skills/ -- ran in no
        test. A mutation sweep flagged both `followlinks=False` constants as unnoticed, which is
        what surfaced it: with no link anywhere in any fixture, the flag genuinely cannot matter.
        """
        if not hasattr(os, "symlink"):  # pragma: no cover - platform without symlinks
            self.skipTest("symlinks unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self._copy_canonical_sources(root)
            outside = root / "outside"
            (outside / "references").mkdir(parents=True)
            (outside / "references" / "smuggled.md").write_text("# smuggled\n", encoding="utf-8")
            planted = root / "skills" / "stack-profile" / "borrowed"
            try:
                os.symlink(outside, planted, target_is_directory=True)
            except (OSError, NotImplementedError):  # pragma: no cover - unprivileged Windows
                self.skipTest("cannot create a directory symlink here")
            self.assertTrue(planted.is_symlink(), "fixture did not plant a real link")
            with self.assertRaisesRegex(ValueError, "must not be a link/reparse point"):
                adapters._canonical_skill_files(root)

    def test_a_real_symlinked_directory_in_a_generated_root_is_refused(self) -> None:
        """Same control on the output side, where a link would make the byte gate read the wrong
        bytes -- it would compare against a file the repository does not actually contain."""
        if not hasattr(os, "symlink"):  # pragma: no cover - platform without symlinks
            self.skipTest("symlinks unavailable")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self._copy_canonical_sources(root)
            adapters.write_generated_outputs(root)
            generated = root / adapters.GENERATED_ROOTS[-1]
            outside = root / "elsewhere"
            outside.mkdir()
            (outside / "extra.md").write_text("# extra\n", encoding="utf-8")
            planted = generated / "borrowed"
            try:
                os.symlink(outside, planted, target_is_directory=True)
            except (OSError, NotImplementedError):  # pragma: no cover - unprivileged Windows
                self.skipTest("cannot create a directory symlink here")
            self.assertTrue(planted.is_symlink(), "fixture did not plant a real link")
            with self.assertRaisesRegex(ValueError, "must not be a link/reparse point"):
                adapters._actual_generated_files(root)

    # --- non-ASCII must survive projection unescaped -------------------------------------------
    # `json.dumps(..., ensure_ascii=False)` appears at four points that render a description or
    # name into a projection. A mutation sweep flagged every one as unnoticed, correctly: no test
    # asserted anything about non-ASCII. Flipping the flag turns the fleet's em-dashes and arrows
    # into literal `\u2014` / `\u2192` in Copilot frontmatter, where a
    # host renders the escape rather than the character. The byte gate does catch it, but only
    # after a full regenerate; these pin it at the source.

    NON_ASCII_SAMPLE = "em—dash and arrow→here"

    def test_copilot_agent_keeps_non_ascii_unescaped(self) -> None:
        agent = (
            "---\n"
            "name: probe-agent\n"
            f'description: "{self.NON_ASCII_SAMPLE}"\n'
            "tools: Read, Grep, Glob\n"
            "---\n\n# Probe\n\nBody.\n"
        )
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "probe-agent.md"
            source.write_text(agent, encoding="utf-8")
            rendered = adapters.render_copilot_agent(source)
        # Prove the sample actually reached the output before asserting the escape is absent;
        # otherwise a renderer that dropped the description entirely would pass.
        self.assertIn("em—dash", rendered)
        self.assertIn("arrow→here", rendered)
        self.assertNotIn("\\u2014", rendered)
        self.assertNotIn("\\u2192", rendered)

    def test_the_live_projections_contain_no_unicode_escapes(self) -> None:
        """The end-to-end statement: real em-dashes and arrows are in the committed projections.

        Guards against the assertion being vacuous by first proving the canonical sources actually
        carry non-ASCII -- if they ever stopped, the escape check below would pass for free.
        """
        canonical_non_ascii = sum(
            1
            for path in sorted((ROOT / "agents").glob("*.md"))
            if any(ord(char) > 127 for char in str(adapters.parse_frontmatter(path)[0].get("description", "")))
        )
        self.assertGreater(canonical_non_ascii, 0, "no canonical description carries non-ASCII")
        for relative in (Path(".github/agents"),):
            for path in sorted((ROOT / relative).glob("*")):
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("\\u2014", text, path.name)
                self.assertNotIn("\\u2192", text, path.name)

    # --- narrow parse paths in the frontmatter reader -------------------------------------------
    # Operand drops here survived a mutation sweep. Low blast radius on their own -- a malformed
    # value fails the frontmatter contract in check_links before it could reach a projection --
    # but this reader is one of three in the repository that disagree about the same grammar, and
    # consolidating them later is only safe if the behaviour each one has today is written down.

    def test_a_quoted_scalar_needs_BOTH_quotes_to_be_unwrapped(self) -> None:
        """Either half of the `startswith and endswith` guard alone mis-parses real values.

        With only `endswith`, `abc'` loses its first and last character and becomes `bc`; with only
        `startswith`, `'abc` becomes `ab`. Both spellings occur in ordinary prose (a trailing
        apostrophe, a quoted fragment), and silently truncating a description is exactly the kind
        of corruption that reaches a host without erroring.
        """
        self.assertEqual("abc'", adapters._yaml_scalar("abc'"))
        self.assertEqual("'abc", adapters._yaml_scalar("'abc"))
        self.assertEqual("abc", adapters._yaml_scalar("'abc'"))
        self.assertEqual("it's", adapters._yaml_scalar("'it''s'"))
        self.assertEqual("plain", adapters._yaml_scalar("plain"))

    def test_tool_specs_from_a_missing_field_are_empty_not_the_string_None(self) -> None:
        """`str(raw or "")` collapses None to empty. Dropping the `or ""` yields the literal
        string "None", which would parse as a tool named None and silently grant nothing while
        looking like a grant."""
        self.assertEqual([], adapters._split_tool_specs(None))
        self.assertEqual([], adapters._split_tool_specs(""))
        self.assertEqual(["Read", "Grep"], adapters._split_tool_specs("Read, Grep"))
        self.assertEqual(["Read", "Grep"], adapters._split_tool_specs(["Read", "Grep"]))

    def test_an_installed_skill_reference_covers_both_bare_and_SKILL_md_tails(self) -> None:
        """`not tail or tail == "/SKILL.md"` treats both spellings as the skill itself. Dropping
        either operand sends one of them down the resource branch, producing a pointer to a
        `SKILL.md` "resource" inside the skill -- a plausible-looking path that does not exist."""
        pattern = re.compile(
            r"(?P<kind>agents|skills)/(?P<name>[a-z0-9-]+)(?P<tail>/[A-Za-z0-9._/-]*)?"
        )
        def describe(reference: str) -> str:
            # A crash is not a passing grade for the guard: dropping `not tail` makes the bare
            # spelling reach `tail.lstrip()` on None, and an AttributeError would "catch" the
            # mutant only by accident. Convert it into a comparable value so the assertions below
            # judge the BEHAVIOUR either way.
            try:
                return adapters._installed_resource(pattern.match(reference))
            except AttributeError as exc:
                return f"<crashed: {exc}>"

        bare = describe("skills/runbook")
        explicit = describe("skills/runbook/SKILL.md")
        nested = describe("skills/runbook/references/x.md")
        self.assertEqual(bare, explicit, "the two spellings of the skill itself must agree")
        self.assertIn("`runbook` skill", bare)
        self.assertIn("references/x.md", nested)
        self.assertNotEqual(bare, nested)

if __name__ == "__main__":
    unittest.main()
