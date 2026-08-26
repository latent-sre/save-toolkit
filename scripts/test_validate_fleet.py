"""Mutation-oriented tests for the canonical fleet validator."""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

import validate_fleet


ROOT = Path(__file__).resolve().parents[1]


def _normalized(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _markdown_section(relative: Path, heading: str) -> str:
    text = (ROOT / relative).read_text(encoding="utf-8")
    marker = f"{heading}\n"
    if marker not in text:
        raise AssertionError(f"{relative.as_posix()}: missing heading {heading!r}")
    section = text.split(marker, 1)[1]
    level = len(heading) - len(heading.lstrip("#"))
    next_heading = re.search(rf"^#{{1,{level}}}\s+", section, re.MULTILINE)
    if next_heading:
        section = section[: next_heading.start()]
    return _normalized(section)


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

    def test_builder_agent_uses_software_engineer_identity(self) -> None:
        path = ROOT / "agents/software-engineer.md"
        self.assertTrue(path.is_file())
        fields, _, _ = validate_fleet.adapters.parse_frontmatter(path)
        self.assertEqual("software-engineer", fields["name"])
        self.assertIn("software-engineer", validate_fleet.EXPECTED_AUTHORITY)
        old_name = "s" + "de"
        self.assertNotIn(old_name, validate_fleet.EXPECTED_AUTHORITY)
        self.assertFalse((ROOT / "agents" / f"{old_name}.md").exists())

    def test_always_loaded_guide_keeps_conditional_authority_complete(self) -> None:
        guide = _normalized((ROOT / "AGENTS.md").read_text(encoding="utf-8"))
        self.assertIn(
            "load it before recommending or changing supported runtime, tooling, or "
            "infrastructure choices",
            guide,
        )
        self.assertIn(
            "[complete agent-body dashboard-write rule]"
            "(agents/observability-engineer.md#change-authority)",
            guide,
        )
        self.assertIn(
            "if any required step cannot be completed, hand off without applying",
            guide,
        )

    def test_exact_commit_id_independent_review_is_prod_deployment_only(self) -> None:
        """Deleting or moving the review boundary must fail this contract."""
        production_checklist = _markdown_section(
            Path("skills/production-change-gate/SKILL.md"),
            "## Checklist",
        )
        self.assertIn(
            "production deployment of a new artifact requires independent review of the exact "
            "candidate commit id",
            production_checklist,
        )
        self.assertIn(
            "for a new-artifact deployment, attach protected-environment evidence",
            production_checklist,
        )
        self.assertIn(
            "for another planned production action, attach evidence that the named human or "
            "protected automation",
            production_checklist,
        )

        for relative in (
            Path("skills/merge-gate/SKILL.md"),
            Path("skills/release-gate/SKILL.md"),
        ):
            checklist = _markdown_section(relative, "## Checklist")
            with self.subTest(contract=relative.as_posix()):
                self.assertNotIn("requires independent review", checklist)
                self.assertNotIn("reviewed commit id", checklist)

    def test_release_gate_uses_distribution_specific_immutability(self) -> None:
        checklist = _markdown_section(
            Path("skills/release-gate/SKILL.md"), "## Checklist"
        ).replace("*", "")

        self.assertIn("when the artifact is distributed as a github release", checklist)
        self.assertIn("gh api repos/{owner}/{repo}/immutable-releases", checklist)
        self.assertIn('"enabled": true', checklist)
        self.assertIn("gh api repos/{owner}/{repo}/rulesets/{ruleset_id}", checklist)
        self.assertIn("target: tag", checklist)
        self.assertIn("enforcement: active", checklist)
        self.assertIn("ref_name.include", checklist)
        self.assertIn("no matching exclusion", checklist)
        self.assertIn("`update` and `deletion` rules", checklist)
        self.assertIn("for any other distribution path", checklist)
        self.assertIn("do not require github release controls", checklist)

    def test_review_consumers_keep_routine_work_out_of_the_prod_review_gate(self) -> None:
        software_engineer_path = ROOT / "agents/software-engineer.md"
        software_engineer_fields, _, _ = validate_fleet.adapters.parse_frontmatter(
            software_engineer_path
        )
        scenario = (ROOT / "evals/scenarios/release-gate-passes-ready.yaml").read_text(
            encoding="utf-8"
        )
        prompt = _normalized(scenario.split("prompt: |", 1)[1].split("success_criteria:", 1)[0])
        criteria = _normalized(scenario.split("success_criteria:", 1)[1].split("graders:", 1)[0])
        contracts = (
            (
                "agents-learning",
                _markdown_section(Path("AGENTS.md"), "## Hard rules"),
                (
                    "eval results never promote a candidate",
                    "only human acceptance of the exact candidate revision does",
                ),
                ("let pr review promote",),
            ),
            (
                "merge-ci",
                _markdown_section(Path("skills/merge-gate/SKILL.md"), "## Checklist"),
                ("read the trusted ci record directly", "missing reviewer packet alone is not a **no**"),
                ("read the reviewer's packet",),
            ),
            (
                "software-engineer-description",
                _normalized(software_engineer_fields["description"]),
                (),
                ("reviewer",),
            ),
            (
                "software-engineer-boundary",
                _markdown_section(Path("agents/software-engineer.md"), "## Untrusted input boundary"),
                (
                    "routine completion returns the evidence packet to the caller without spawning a review",
                    "caller requests review",
                    "security-sensitive",
                    "production deployment",
                ),
                (),
            ),
            (
                "agent-engineer",
                _markdown_section(Path("agents/agent-engineer.md"), "## Method"),
                ("promotion is the human owner's acceptance of the exact candidate revision",),
                ("approval on the exact candidate revision by someone other than",),
            ),
            (
                "agent-authoring",
                _markdown_section(
                    Path("skills/agent-authoring/references/artifact.md"),
                    "## Learn from an encountered failure",
                ),
                ("human acceptance of the exact candidate revision is promotion",),
                ("pr approval on the exact candidate revision is promotion",),
            ),
            (
                "reviewer-scope",
                _markdown_section(Path("agents/reviewer.md"), "## Scope the review first"),
                ("cannot supply the exact-sha review evidence required for a production deployment",),
                ("re-review before merge",),
            ),
            (
                "reviewer-output",
                _markdown_section(Path("agents/reviewer.md"), "## Output format"),
                ("cannot supply production-change-gate's exact-sha review evidence",),
                ("cannot satisfy merge-gate",),
            ),
            (
                "release-prompt",
                prompt,
                ("production-change-gate has not run", "intentionally later"),
                ("production-change-gate is cleared",),
            ),
            ("release-criteria", criteria, ("without requiring production-change clearance",), ()),
        )
        for name, text, required, forbidden in contracts:
            with self.subTest(contract=name):
                for phrase in required:
                    self.assertIn(phrase, text)
                for phrase in forbidden:
                    self.assertNotIn(phrase, text)

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

    def test_nonexecuting_handoffs_keep_ci_output_untrusted(self) -> None:
        """Authenticated CI has provenance, but candidate-controlled output stays untrusted."""
        for relative in (Path("agents/reviewer.md"), Path("agents/scribe.md")):
            packet = _markdown_section(relative, "## The handoff packet")
            inputs = packet.split("inputs:", 1)[1].split("verified:", 1)[0]
            trusted = inputs.split("[trusted]", 1)[1].split("[untrusted]", 1)[0]
            with self.subTest(agent=relative.stem):
                self.assertNotIn("ci", trusted)
                self.assertIn("[untrusted] ci output", inputs)

    def test_retired_learning_machinery_stays_absent(self) -> None:
        retained = (
            Path("schemas/evidence-envelope-v1.schema.json"),
            Path("skills/operational-learning/SKILL.md"),
            Path("skills/operational-learning/references/disposition-policy.md"),
            Path("skills/operational-learning/assets/service-card-template.md"),
            Path("skills/operational-learning/assets/alert-card-template.md"),
            Path("skills/operational-learning/assets/knowledge-index-template.md"),
        )
        retired = (
            Path("skills/operational-learning/assets/knowledge-update-v1.schema.json"),
            Path("skills/operational-learning/assets/knowledge-update-v2.schema.json"),
            Path("skills/operational-learning/assets/knowledge-update-v3.schema.json"),
            Path("skills/operational-learning/scripts/knowledge_update.py"),
            Path("skills/operational-learning/scripts/migrate_v1_to_v2.py"),
            Path("skills/operational-learning/scripts/migrate_v2_to_v3.py"),
            Path("skills/operational-learning/scripts/packet_drift.py"),
            Path("skills/agent-authoring/assets/fleet-improvement-v1.schema.json"),
            Path("skills/agent-authoring/references/improvement-lifecycle.md"),
            Path("scripts/validate_improvements.py"),
            Path("scripts/test_validate_improvements.py"),
        )
        for relative in retained:
            with self.subTest(retained=relative.as_posix()):
                self.assertTrue((ROOT / relative).is_file())
        for relative in retired:
            with self.subTest(retired=relative.as_posix()):
                self.assertFalse((ROOT / relative).exists())
        examples = ROOT / "skills/operational-learning/assets/examples"
        self.assertEqual([], sorted(examples.glob("*.json")))
        self.assertEqual([], sorted((ROOT / "evals/improvements").glob("*/record.json")))

        skill = (ROOT / "skills/operational-learning/SKILL.md").read_text(encoding="utf-8").lower()
        for obsolete_term in ("knowledge-update", "packet drift", "sha-256"):
            with self.subTest(obsolete_term=obsolete_term):
                self.assertNotIn(obsolete_term, skill)
        active_fleet_contracts = (
            Path("AGENTS.md"),
            Path("agents/agent-engineer.md"),
            Path("agents/reviewer.md"),
            Path("skills/agent-authoring/SKILL.md"),
            Path("skills/agent-authoring/references/artifact.md"),
            Path("skills/agent-authoring/references/roster.md"),
            Path("skills/agent-security/SKILL.md"),
        )
        for relative in active_fleet_contracts:
            text = (ROOT / relative).read_text(encoding="utf-8").lower()
            for obsolete_term in (
                "improvement_id",
                "failure_fingerprint",
                "improvement lifecycle",
                "fleet-improvement-v1",
            ):
                with self.subTest(contract=relative.as_posix(), obsolete_term=obsolete_term):
                    self.assertNotIn(obsolete_term, text)
        for relative in retained[3:]:
            with self.subTest(template=relative.as_posix()):
                self.assertIn("last_reviewed: null", (ROOT / relative).read_text(encoding="utf-8"))

    def test_operational_templates_use_reviewable_provenance_not_retired_ids(self) -> None:
        expected_provenance = {
            Path("skills/operational-learning/assets/service-card-template.md"): (
                "| Date | PR / revision / evidence reference | Change | Reviewer |"
            ),
            Path("skills/operational-learning/assets/alert-card-template.md"): (
                "| Date | PR / revision / evidence reference | Change | Reviewer |"
            ),
            Path("skills/operational-learning/assets/knowledge-index-template.md"): (
                "| PR / revision / evidence reference | Trigger | Summary | Dispositions | Reviewed change |"
            ),
            Path("skills/runbook/assets/runbook-template.md"): (
                "- Provenance: <PR, target revision, and evidence references>"
            ),
        }
        for relative, marker in expected_provenance.items():
            text = (ROOT / relative).read_text(encoding="utf-8")
            with self.subTest(template=relative.as_posix()):
                self.assertNotIn("knowledge update id", text.lower())
                self.assertNotIn("update id", text.lower())
                self.assertNotIn("ol_ id", text.lower())
                self.assertIn(marker, text)

    def test_prepared_requires_verified_checkout_revision_binding(self) -> None:
        contract_paths = (
            Path("agents/scribe.md"),
            Path("skills/operational-learning/SKILL.md"),
            Path("skills/operational-learning/references/disposition-policy.md"),
        )
        for relative in contract_paths:
            text = re.sub(
                r"\s+",
                " ",
                (ROOT / relative).read_text(encoding="utf-8").lower(),
            )
            with self.subTest(contract=relative.as_posix()):
                self.assertIn("mounted checkout's current full sha equals the target revision", text)
                self.assertIn("`[verified]` checkout binding", text)
                self.assertIn("`proposed`", text)
                self.assertIn("`blocked`", text)

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
                    "The caller, not `sre`, separately\ndispatches typed `observability-engineer` for detection changes and typed `scribe` for the\npostmortem, operating guidance, and learning dispositions",
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

    def test_incident_command_rejects_observability_as_recovery_owner(self) -> None:
        stale_contracts = (
            "Resolve only after the typed `observability-engineer` confirm that user impact ended.",
            (
                "Resolve only after the typed `observability-engineer` confirms that golden "
                "signals stayed healthy."
            ),
        )
        for stale_contract in stale_contracts:
            with self.subTest(stale_contract=stale_contract), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                self._copy_scribe_bundle(root)
                target = root / "skills" / "incident-command" / "SKILL.md"
                target.write_text(
                    f"{target.read_text(encoding='utf-8')}\n{stale_contract}\n",
                    encoding="utf-8",
                )
                failures = validate_fleet.validate_scribe_bundle(root)
            self.assertTrue(
                any("stale incident recovery owner" in failure for failure in failures),
                failures,
            )

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._copy_scribe_bundle(root)
            target = root / "skills" / "incident-command" / "SKILL.md"
            target.write_text(
                f"{target.read_text(encoding='utf-8')}\n"
                "Resolution does not depend on the typed `observability-engineer`, which does not "
                "confirm recovery.\n",
                encoding="utf-8",
            )
            failures = validate_fleet.validate_scribe_bundle(root)
        self.assertFalse(
            any("stale incident recovery owner" in failure for failure in failures),
            failures,
        )

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
                    text = text.replace("tools: Read, Grep, Glob", "hooks: ignored\ntools: Read")
                (root / "agents" / source.name).write_text(text, encoding="utf-8")
            _, failures = validate_fleet.validate_agents(root)
        rendered = "\n".join(failures)
        self.assertIn("unsupported plugin agent field", rendered)
        self.assertIn("missing required tool", rendered)
        # The inert-field rule emits a distinct, more educational message than the generic
        # unknown-field one (a `hooks:` guard in plugin frontmatter looks like armor and does
        # nothing). Assert it specifically, so this test fails if that rule is ever deleted —
        # without this line it would pass on the unknown-field message alone.
        self.assertIn("plugin-inert authority field(s) are forbidden", rendered)

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
                if source.name == "software-engineer.md":
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
                if source.name == "software-engineer.md":
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
                if source.name == "software-engineer.md":
                    text = text.replace(
                        "Agent(reviewer, scribe, researcher)", "Agent(reviewer)"
                    )
                (root / "agents" / source.name).write_text(text, encoding="utf-8")
            _, failures = validate_fleet.validate_agents(root)
        self.assertIn("delegation mismatch", "\n".join(failures))

    def test_sre_postincident_delegation_edges_are_rejected(self) -> None:
        failures = self._agents_with_mutation(
            "sre.md",
            "Agent(researcher)",
            "Agent(observability-engineer, scribe, researcher)",
        )
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
            for relative in validate_fleet.CONDITIONAL_HANDOFF_CONTRACTS.values():
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text((ROOT / relative).read_text(encoding="utf-8"), encoding="utf-8")
            _, failures = validate_fleet.validate_agents(root)
        return failures

    def test_sre_conditional_handoff_requires_an_explicit_pointer(self) -> None:
        failures = self._agents_with_mutation(
            "sre.md", "incident-handoff reference", "conditional handoff details"
        )
        self.assertIn("missing handoff contract", "\n".join(failures))

    def test_sre_conditional_handoff_rejects_a_negated_pointer(self) -> None:
        failures = self._agents_with_mutation(
            "sre.md",
            "read `sre-ladder`'s incident-handoff reference before forming the packet",
            "do not read `sre-ladder`'s incident-handoff reference before forming the packet",
        )
        self.assertIn("missing handoff contract", "\n".join(failures))

    def test_model_alias_is_accepted(self) -> None:
        """An alias must produce NO failure at all, not merely avoid one message.

        Asserting only the absence of "model must be one of" left the test green when
        `model` was dropped from KNOWN_AGENT_FIELDS -- the validator then rejects the pin as
        an unknown field, a different message, and the acceptance contract silently stopped
        being tested.
        """
        failures = self._agents_with_mutation(
            "sre.md", "name: sre\n", "name: sre\nmodel: sonnet\n"
        )
        self.assertEqual([], failures)

    def test_full_model_id_is_rejected(self) -> None:
        # The staleness the old blanket ban existed to prevent: a dated ID keeps pointing at
        # a model long after the fleet has moved on, and nothing errors.
        failures = self._agents_with_mutation(
            "sre.md", "name: sre\n", "name: sre\nmodel: claude-opus-4-1-20250805\n"
        )
        self.assertIn("model must be one of", "\n".join(failures))

    def test_scoped_grant_on_non_agent_tool_is_rejected(self) -> None:
        # `Bash(git diff:*)` reads like a narrowed shell and grants an open one — the runtime
        # ignores the scope. Only Agent(...) scoping is real.
        failures = self._agents_with_mutation(
            "sre.md", "Read, Grep, Glob, Bash, Skill", "Read, Grep, Glob, Bash(git diff:*), Skill"
        )
        self.assertIn("scoped tool grant", "\n".join(failures))

    def test_duplicate_tool_grant_is_rejected(self) -> None:
        failures = self._agents_with_mutation(
            "reviewer.md", "tools: Read, Grep, Glob", "tools: Read, Grep, Glob, Read"
        )
        self.assertIn("duplicate tool grant", "\n".join(failures))

    def test_incomplete_evidence_triad_is_rejected(self) -> None:
        # Dropping [sourced] while keeping the other two labels loses the ability to distinguish
        # "I ran it" from "the file says so"; the triad is all-or-nothing.
        failures = self._agents_with_mutation("software-engineer.md", "[sourced]", "[srcd]")
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
                    'frozenset({"sre"})',
                    'frozenset({"sre", "software-engineer"})',
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
                    'frozenset({"sre"})',
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

    def _roster_root(self, temporary: str, mutate) -> Path:
        root = Path(temporary)
        (root / "AGENTS.md").write_text(
            mutate((ROOT / "AGENTS.md").read_text(encoding="utf-8")), encoding="utf-8"
        )
        return root

    def test_current_roster_graph_matches_enforced_graph(self) -> None:
        # Anchor: the shipped roster render already agrees with the enforced graph, or every
        # mutation below proves nothing.
        self.assertEqual([], validate_fleet.validate_roster_graph(ROOT))

    def test_roster_dropping_a_delegation_edge_is_rejected(self) -> None:
        # software-engineer delegates to reviewer, scribe, researcher in frontmatter; drop researcher from the
        # rendered row and the render now describes a graph the fleet does not have.
        with tempfile.TemporaryDirectory() as temporary:
            root = self._roster_root(
                temporary,
                lambda t: t.replace(
                    "| `reviewer`, `scribe`, `researcher` |",
                    "| `reviewer`, `scribe` |",
                    1,
                ),
            )
            failures = validate_fleet.validate_roster_graph(root)
        self.assertTrue(any("'software-engineer'" in f and "researcher" in f for f in failures), failures)

    def test_roster_adding_a_phantom_edge_is_rejected(self) -> None:
        # scribe holds no Agent grant at all; a rendered edge out of it is a phantom the enforced
        # graph forbids.
        with tempfile.TemporaryDirectory() as temporary:
            root = self._roster_root(
                temporary,
                lambda t: t.replace(
                    "no Bash, web, or delegation**; terminal | — |",
                    "no Bash, web, or delegation**; terminal | `researcher` |",
                    1,
                ),
            )
            failures = validate_fleet.validate_roster_graph(root)
        self.assertTrue(any("'scribe'" in f for f in failures), failures)

    def test_roster_with_duplicate_agent_row_is_rejected(self) -> None:
        source = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        software_engineer_row = next(
            line for line in source.splitlines() if line.startswith("| `software-engineer` |")
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = self._roster_root(
                temporary,
                lambda text: text.replace(
                    software_engineer_row,
                    f"{software_engineer_row}\n{software_engineer_row}",
                    1,
                ),
            )
            failures = validate_fleet.validate_roster_graph(root)
        self.assertTrue(
            any("duplicate roster row for agent 'software-engineer'" in failure for failure in failures),
            failures,
        )

    def test_roster_without_the_table_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = self._roster_root(temporary, lambda t: "# no roster here\n")
            failures = validate_fleet.validate_roster_graph(root)
        self.assertTrue(any("could not find the roster" in f for f in failures), failures)


class NonDelegatingHandoffTests(unittest.TestCase):
    """An agent with no `Agent` tool must not carry the delegating handoff imperative.

    The real defect this pins: `reviewer` — read-only by tool absence, and the lane that gates every
    merge — carried the `software-engineer` handoff block verbatim, instructing it to "Hand to exactly one agent"
    and to load `production-change-gate`, a skill it holds no `Skill` tool to load. `scribe`, under
    the identical constraint, had already been adapted correctly, which is what showed the reviewer
    copy was drift and not a decision.
    """

    def _mutate(self, filename: str, before: str, after: str) -> list[str]:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "agents").mkdir()
            replaced = False
            for source in (ROOT / "agents").glob("*.md"):
                text = source.read_text(encoding="utf-8")
                if source.name == filename:
                    mutated = text.replace(before, after)
                    # Without this the whole test silently passes on a needle that moved — the exact
                    # failure AGENTS.md records this repo having already shipped once.
                    self.assertNotEqual(text, mutated, f"{filename}: mutation matched nothing")
                    text, replaced = mutated, True
                (root / "agents" / source.name).write_text(text, encoding="utf-8")
            self.assertTrue(replaced, f"{filename} not found in agents/")
            _, failures = validate_fleet.validate_agents(root)
        return failures

    def test_live_tree_has_no_delegation_contradiction(self) -> None:
        _, failures = validate_fleet.validate_agents(ROOT)
        offenders = [f for f in failures if "Agent tool" in f]
        self.assertEqual([], offenders, offenders)

    def test_delegating_imperative_in_a_toolless_lane_is_flagged(self) -> None:
        failures = self._mutate(
            "reviewer.md",
            "Recommend exactly one next owner. This role cannot invoke that owner",
            "Hand to exactly one agent. If two are needed, sequence them",
        )
        self.assertTrue(
            any("holds no Agent tool" in f and "reviewer" in f for f in failures), failures
        )

    def test_a_lane_that_drops_every_disclaimer_is_flagged(self) -> None:
        """Strip ALL disclaimer phrasings, not one, or the test proves nothing.

        `scribe` states the constraint twice — once in its handoff rules and again as "this agent
        cannot delegate or browse". Removing only the first leaves the second matching and the
        validator correctly silent, so an earlier single-substitution version of this test failed
        for the right reason. Strip every phrase and assert none survive before expecting the flag.
        """
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "agents").mkdir()
            for source in (ROOT / "agents").glob("*.md"):
                text = source.read_text(encoding="utf-8")
                if source.name == "scribe.md":
                    for phrase in validate_fleet.NON_DELEGATION_DISCLAIMERS:
                        text = text.replace(phrase, "proceeds")
                    self.assertFalse(
                        any(
                            phrase in validate_fleet._flatten(text)
                            for phrase in validate_fleet.NON_DELEGATION_DISCLAIMERS
                        ),
                        "fixture still carries a disclaimer; the assertion below would be vacuous",
                    )
                (root / "agents" / source.name).write_text(text, encoding="utf-8")
            _, failures = validate_fleet.validate_agents(root)
        self.assertTrue(
            any("must state that it cannot invoke" in f and "scribe" in f for f in failures),
            failures,
        )


    def test_a_recommendation_alone_is_not_a_disclaimer(self) -> None:
        """Describing what the lane does is not stating what it cannot do.

        "Recommend exactly one next owner" was briefly accepted as a disclaimer. It is not one: an
        agent could keep that sentence, drop every incapability statement, and pass -- reopening
        the misleading-authority drift the contract exists to stop.
        """
        self.assertNotIn(
            "Recommend exactly one next owner", validate_fleet.NON_DELEGATION_DISCLAIMERS
        )
        for phrase in validate_fleet.NON_DELEGATION_DISCLAIMERS:
            with self.subTest(phrase=phrase):
                self.assertTrue(
                    phrase.startswith("cannot ") or "must invoke" in phrase,
                    f"{phrase!r} does not assert incapability",
                )

    def test_disclaimer_is_found_across_a_line_wrap(self) -> None:
        """A hard-wrapped disclaimer must still count.

        `repository-investigator` genuinely wraps "You cannot\\ndelegate or contact the external
        lane yourself". A raw substring test misses that and reports a violation in a file that is
        already correct, so the checker flattens whitespace first. Pin the behavior directly.
        """
        self.assertIn("cannot delegate", validate_fleet._flatten("You cannot\ndelegate or contact"))
        _, failures = validate_fleet.validate_agents(ROOT)
        self.assertFalse(
            any("repository-investigator" in f and "cannot invoke" in f for f in failures), failures
        )


class SharedHandoffBlockTests(unittest.TestCase):
    """The delegating agents' inline or predicate-loaded rules stay byte-identical.

    It was NOT identical: `observability-engineer` carried two straight quotes where `software-engineer` and `sre`
    have curly ones. Harmless in itself, diagnostic in aggregate — something edited one copy of a
    duplicated block and the other copies did not move, which is the same mechanism that produced
    the reviewer contradiction above. The next divergence may not be punctuation.
    """

    DELEGATING = ("software-engineer", "sre", "observability-engineer")

    @staticmethod
    def _rules_block(name: str) -> str:
        relative = validate_fleet.CONDITIONAL_HANDOFF_CONTRACTS.get(
            name, Path("agents") / f"{name}.md"
        )
        text = (ROOT / relative).read_text(encoding="utf-8")
        match = re.search(r"^## Rules\n(.*?)(?=\n## |\Z)", text, re.S | re.M)
        assert match is not None, f"{name}: no '## Rules' section"
        return match.group(1)

    def test_rules_block_is_byte_identical_across_delegating_agents(self) -> None:
        blocks = {name: self._rules_block(name) for name in self.DELEGATING}
        # Guard against the section regex silently matching nothing in every file, which would make
        # the equality assertion below trivially true.
        for name, block in blocks.items():
            self.assertGreater(len(block), 500, f"{name}: '## Rules' block implausibly short")
        distinct = set(blocks.values())
        self.assertEqual(
            1,
            len(distinct),
            "delegating agents' '## Rules' blocks have drifted: "
            + ", ".join(f"{n}={len(b)}B" for n, b in blocks.items()),
        )


if __name__ == "__main__":
    unittest.main()
