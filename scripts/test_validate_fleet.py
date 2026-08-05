"""Mutation-oriented tests for the canonical fleet validator."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import validate_fleet


ROOT = Path(__file__).resolve().parents[1]


class FleetValidatorTests(unittest.TestCase):
    SCRIBE_LOADED_PATHS = (
        Path("agents/scribe.md"),
        Path("skills/runbook/SKILL.md"),
        Path("skills/postmortem/SKILL.md"),
        Path("skills/operational-learning/SKILL.md"),
        Path("skills/service-onboarding/SKILL.md"),
        Path("skills/incident-command/SKILL.md"),
        Path("skills/runbook/assets/runbook-template.md"),
        Path("skills/postmortem/assets/postmortem-template.md"),
    )

    def _copy_scribe_bundle(self, root: Path) -> None:
        for relative in self.SCRIBE_LOADED_PATHS:
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                (ROOT / relative).read_text(encoding="utf-8"),
                encoding="utf-8",
            )

    def test_current_agents_pass(self) -> None:
        names, failures = validate_fleet.validate_agents(ROOT)
        self.assertEqual(sorted(validate_fleet.EXPECTED_AUTHORITY), sorted(names))
        self.assertEqual([], failures)

    def test_scribe_is_a_non_executing_document_writer(self) -> None:
        path = ROOT / "agents" / "scribe.md"
        fields, body, _ = validate_fleet.adapters.parse_frontmatter(path)
        self.assertEqual(
            {"Read", "Grep", "Glob", "Edit", "Write", "Skill"},
            validate_fleet._tool_bases(fields["tools"]),
        )
        self.assertIn("Do not execute anything", body)
        self.assertIn("## Pick one primary mode", body)
        self.assertIn("**Knowledge closeout mode**", body)

    def test_observability_engineer_no_longer_owns_operational_documentation(self) -> None:
        fields, body, _ = validate_fleet.adapters.parse_frontmatter(
            ROOT / "agents" / "observability-engineer.md"
        )
        description = str(fields["description"]).lower()
        self.assertIn("for runbooks or postmortems use save-toolkit:scribe", description)
        self.assertNotIn("operational documentation", description)
        self.assertNotIn("## Documentation lane", body)
        self.assertNotIn("- `runbook` —", body)
        self.assertNotIn("- `postmortem` —", body)
        self.assertNotIn("documentation output, filled", body)
        self.assertIn("→ `scribe`", body)

    def test_scribe_execute_egress_and_delegation_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "agents").mkdir()
            for source in (ROOT / "agents").glob("*.md"):
                text = source.read_text(encoding="utf-8")
                if source.name == "scribe.md":
                    text = text.replace(
                        "tools: Read, Grep, Glob, Edit, Write, Skill",
                        "tools: Read, Grep, Glob, Edit, Write, Skill, Bash, WebSearch, Agent(researcher)",
                    )
                (root / "agents" / source.name).write_text(text, encoding="utf-8")
            _, failures = validate_fleet.validate_agents(root)
        rendered = "\n".join(failures)
        self.assertIn("forbidden tool(s): Agent, Bash, WebSearch", rendered)
        self.assertIn("delegation mismatch", rendered)

    def test_scribe_loaded_bundle_cannot_execute_or_route_docs_to_observability(self) -> None:
        self.assertEqual([], validate_fleet.validate_scribe_bundle(ROOT))
        bundle_paths = self.SCRIBE_LOADED_PATHS

        execution_directives = (
            (Path("skills/runbook/SKILL.md"), "Run game days / drills under realistic conditions."),
            (
                Path("skills/operational-learning/SKILL.md"),
                "You should execute commands to verify their output.",
            ),
            (
                Path("skills/operational-learning/SKILL.md"),
                "The documentation agent must rehearse the runbook.",
            ),
        )
        for relative, directive in execution_directives:
            with self.subTest(path=relative, directive=directive), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                self._copy_scribe_bundle(root)
                target = root / relative
                source = target.read_text(encoding="utf-8")
                target.write_text(f"{source}\n{directive}\n", encoding="utf-8")
                failures = validate_fleet.validate_scribe_bundle(root)
            self.assertIn("scribe execution directive", "\n".join(failures))

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._copy_scribe_bundle(root)
            for relative in bundle_paths:
                target = root / relative
                text = target.read_text(encoding="utf-8")
                text = text.replace(
                    "never execute from\n  this documentation lane, including a read-only command",
                    "run read-only ones to confirm syntax",
                )
                text = text.replace(
                    "operating documentation → typed `scribe`",
                    "operating documentation → typed `observability-engineer`",
                )
                text = text.replace(
                    "hand the timeline and evidence to the `scribe` agent for retrospective documentation",
                    "hand the timeline and evidence to the `observability-engineer` agent for retrospective documentation",
                )
                text = text.replace("last_verified: null", "last_verified: <bump after incident>")
                text = text.replace(
                    "after resolution typed `scribe` captures the postmortem, operating guidance, and learning dispositions",
                    "typed `observability-engineer` agent captures\ndurable operating guidance",
                )
                target.write_text(text, encoding="utf-8")
            failures = validate_fleet.validate_scribe_bundle(root)
        rendered = "\n".join(failures)
        self.assertIn("run read-only ones to confirm syntax", rendered)
        self.assertIn("scribe execution directive", rendered)
        self.assertIn("operating documentation → typed `observability-engineer`", rendered)
        self.assertIn("timeline and evidence to the `observability-engineer` agent", rendered)
        self.assertIn("last_verified: null", rendered)
        self.assertIn("typed `observability-engineer` agent captures", rendered)

    def test_scribe_bundle_allows_explicit_non_execution_language(self) -> None:
        safe_statements = (
            (Path("agents/scribe.md"), "Do not execute commands."),
            (Path("skills/runbook/SKILL.md"), "Never run commands."),
            (
                Path("skills/runbook/assets/runbook-template.md"),
                "Only a human should execute commands.",
            ),
            (Path("skills/postmortem/SKILL.md"), "`scribe` must not run commands."),
            (
                Path("skills/postmortem/assets/postmortem-template.md"),
                "Do not ask `scribe` to run commands.",
            ),
            (
                Path("skills/postmortem/assets/postmortem-template.md"),
                "Do not ask the `scribe` to run commands.",
            ),
        )
        for relative, statement in safe_statements:
            with self.subTest(path=relative, statement=statement), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                self._copy_scribe_bundle(root)
                target = root / relative
                target.write_text(
                    f"{target.read_text(encoding='utf-8')}\n{statement}\n",
                    encoding="utf-8",
                )
                failures = validate_fleet.validate_scribe_bundle(root)
            self.assertNotIn("scribe execution directive", "\n".join(failures))

    def test_every_scribe_loaded_source_rejects_positive_execution_language(self) -> None:
        self.assertEqual(
            self.SCRIBE_LOADED_PATHS,
            validate_fleet.SCRIBE_LOADED_SOURCES,
        )
        directives = (
            "The documentation agent must execute commands against the target.",
            "Scribe must not browse, but scribe should execute commands.",
            "Scribe must not browse, but should execute commands.",
            'The instruction is: "Scribe should execute commands."',
        )
        for relative in self.SCRIBE_LOADED_PATHS:
            for directive in directives:
                with self.subTest(path=relative, directive=directive), tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary)
                    self._copy_scribe_bundle(root)
                    target = root / relative
                    target.write_text(
                        f"{target.read_text(encoding='utf-8')}\n{directive}\n",
                        encoding="utf-8",
                    )
                    failures = validate_fleet.validate_scribe_bundle(root)
                self.assertIn("scribe execution directive", "\n".join(failures))

    def test_scribe_returns_runbook_link_to_observability_owner(self) -> None:
        _, body, _ = validate_fleet.adapters.parse_frontmatter(ROOT / "agents/scribe.md")
        self.assertNotIn("and link it from the alert", body)
        self.assertIn(
            "Return the exact runbook path or URL and alert name to `observability-engineer`",
            body,
        )

    def test_runbook_template_does_not_upgrade_last_verified_without_evidence(self) -> None:
        template = (ROOT / "skills/runbook/assets/runbook-template.md").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("bump `last_verified`", template)
        self.assertIn(
            "Change `last_verified` only when incoming rehearsal evidence binds this exact runbook version",
            template,
        )
        self.assertIn("otherwise leave it unchanged", template)

    def test_inert_plugin_hook_and_missing_tools_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "agents").mkdir()
            for source in (ROOT / "agents").glob("*.md"):
                text = source.read_text(encoding="utf-8")
                if source.name == "reviewer.md":
                    text = text.replace("tools: Read, Grep, Glob, Skill", "hooks: ignored\ntools: Read")
                (root / "agents" / source.name).write_text(text, encoding="utf-8")
            _, failures = validate_fleet.validate_agents(root)
        rendered = "\n".join(failures)
        self.assertIn("unsupported plugin agent field", rendered)
        self.assertIn("missing required tool", rendered)

    def test_mcp_server_wildcard_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "agents").mkdir()
            for source in (ROOT / "agents").glob("*.md"):
                text = source.read_text(encoding="utf-8")
                if source.name == "researcher.md":
                    text = text.replace("  - mcp__plugin_githits_githits__search\n", "  - mcp__plugin_githits_githits__*\n")
                (root / "agents" / source.name).write_text(text, encoding="utf-8")
            _, failures = validate_fleet.validate_agents(root)
        self.assertIn("MCP authority is not exact-approved", "\n".join(failures))

    def test_unknown_delegation_target_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "agents").mkdir()
            for source in (ROOT / "agents").glob("*.md"):
                text = source.read_text(encoding="utf-8")
                if source.name == "sde.md":
                    text = text.replace(
                        "Agent(reviewer, scribe, researcher)", "Agent(does-not-exist)"
                    )
                (root / "agents" / source.name).write_text(text, encoding="utf-8")
            _, failures = validate_fleet.validate_agents(root)
        self.assertIn("does not exist", "\n".join(failures))

    def test_local_investigator_external_egress_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "agents").mkdir()
            for source in (ROOT / "agents").glob("*.md"):
                text = source.read_text(encoding="utf-8")
                if source.name == "repository-investigator.md":
                    text = text.replace("tools: Read, Grep, Glob", "tools: Read, Grep, Glob, WebSearch")
                (root / "agents" / source.name).write_text(text, encoding="utf-8")
            _, failures = validate_fleet.validate_agents(root)
        self.assertIn("forbidden tool(s): WebSearch", "\n".join(failures))

    def test_external_researcher_local_read_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "agents").mkdir()
            for source in (ROOT / "agents").glob("*.md"):
                text = source.read_text(encoding="utf-8")
                if source.name == "researcher.md":
                    text = text.replace("  - WebSearch\n", "  - Read\n  - WebSearch\n")
                (root / "agents" / source.name).write_text(text, encoding="utf-8")
            _, failures = validate_fleet.validate_agents(root)
        self.assertIn("forbidden tool(s): Read", "\n".join(failures))

    def test_local_agent_direct_web_access_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "agents").mkdir()
            for source in (ROOT / "agents").glob("*.md"):
                text = source.read_text(encoding="utf-8")
                if source.name == "sde.md":
                    text = text.replace("Write, Skill", "Write, WebFetch, Skill")
                (root / "agents" / source.name).write_text(text, encoding="utf-8")
            _, failures = validate_fleet.validate_agents(root)
        self.assertIn("forbidden tool(s): WebFetch", "\n".join(failures))

    def test_delegation_contract_is_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "agents").mkdir()
            for source in (ROOT / "agents").glob("*.md"):
                text = source.read_text(encoding="utf-8")
                if source.name == "sde.md":
                    text = text.replace(
                        "Agent(reviewer, scribe, researcher)", "Agent(reviewer)"
                    )
                (root / "agents" / source.name).write_text(text, encoding="utf-8")
            _, failures = validate_fleet.validate_agents(root)
        self.assertIn("delegation mismatch", "\n".join(failures))

    def _agents_with_mutation(self, filename: str, before: str, after: str) -> list[str]:
        """Copy the agent tree, apply one substitution to one file, return failures."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "agents").mkdir()
            for source in (ROOT / "agents").glob("*.md"):
                text = source.read_text(encoding="utf-8")
                if source.name == filename:
                    text = text.replace(before, after)
                (root / "agents" / source.name).write_text(text, encoding="utf-8")
            _, failures = validate_fleet.validate_agents(root)
        return failures

    def test_scoped_grant_on_non_agent_tool_is_rejected(self) -> None:
        # `Bash(git diff:*)` reads like a narrowed shell and grants an open one — the runtime
        # ignores the scope. Only Agent(...) scoping is real.
        failures = self._agents_with_mutation(
            "sre.md", "Read, Grep, Glob, Bash, Skill", "Read, Grep, Glob, Bash(git diff:*), Skill"
        )
        self.assertIn("scoped tool grant", "\n".join(failures))

    def test_duplicate_tool_grant_is_rejected(self) -> None:
        failures = self._agents_with_mutation(
            "reviewer.md", "tools: Read, Grep, Glob, Skill", "tools: Read, Grep, Glob, Skill, Read"
        )
        self.assertIn("duplicate tool grant", "\n".join(failures))

    def test_incomplete_evidence_triad_is_rejected(self) -> None:
        # Dropping [sourced] while keeping the other two labels loses the ability to distinguish
        # "I ran it" from "the file says so"; the triad is all-or-nothing.
        failures = self._agents_with_mutation("sde.md", "[sourced]", "[srcd]")
        self.assertIn("incomplete evidence-label triad", "\n".join(failures))

    def test_bash_without_write_must_be_on_guard_roster(self) -> None:
        # repository-investigator holds no Bash today; granting it Bash with no write tool makes it
        # read-only-by-intent, whose read-only-ness is only a promise unless the guard scopes it.
        failures = self._agents_with_mutation(
            "repository-investigator.md", "tools: Read, Grep, Glob", "tools: Read, Grep, Glob, Bash"
        )
        self.assertIn("not on the guard roster", "\n".join(failures))

    def _guard_wiring_root(self, temporary: str, guard_mutation=lambda t: t) -> Path:
        """A minimal root carrying a (possibly mutated) guard and the real Claude manifest."""
        root = Path(temporary)
        (root / "scripts").mkdir()
        (root / ".claude-plugin").mkdir()
        guard_text = (ROOT / "scripts" / "readonly-guard.py").read_text(encoding="utf-8")
        (root / "scripts" / "readonly-guard.py").write_text(
            guard_mutation(guard_text), encoding="utf-8"
        )
        (root / ".claude-plugin" / "plugin.json").write_text(
            (ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"), encoding="utf-8"
        )
        return root

    def test_guard_roster_mismatch_with_generator_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._guard_wiring_root(
                temporary,
                lambda t: t.replace(
                    'frozenset({"sre", "observability-engineer"})',
                    'frozenset({"sre", "observability-engineer", "sde"})',
                ),
            )
            failures = validate_fleet.validate_guard_wiring(
                root, sorted(validate_fleet.EXPECTED_AUTHORITY)
            )
        self.assertIn("guard roster mismatch", "\n".join(failures))

    def test_guard_roster_naming_a_non_agent_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._guard_wiring_root(
                temporary,
                lambda t: t.replace(
                    'frozenset({"sre", "observability-engineer"})',
                    'frozenset({"sre", "ghost-agent"})',
                ),
            )
            failures = validate_fleet.validate_guard_wiring(root, ["sre", "observability-engineer"])
        self.assertIn("non-existent agent", "\n".join(failures))

    def test_guard_plugin_name_mismatch_with_manifest_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._guard_wiring_root(
                temporary,
                lambda t: t.replace('PLUGIN_NAME = "save-toolkit"', 'PLUGIN_NAME = "renamed"'),
            )
            failures = validate_fleet.validate_guard_wiring(
                root, sorted(validate_fleet.EXPECTED_AUTHORITY)
            )
        self.assertIn("guard PLUGIN_NAME", "\n".join(failures))


if __name__ == "__main__":
    unittest.main()
