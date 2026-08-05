"""Contract tests for the generated host adapters."""

from __future__ import annotations

import json
import shutil
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

import generate_platform_adapters as adapters


ROOT = Path(__file__).resolve().parents[1]


class PlatformAdapterTests(unittest.TestCase):
    @staticmethod
    def _copilot_tools(name: str) -> list[str]:
        rendered = adapters.render_copilot_agent(ROOT / "agents" / f"{name}.md")
        frontmatter = rendered.split("---", 2)[1]
        return json.loads(
            next(line for line in frontmatter.splitlines() if line.startswith("tools: "))[7:]
        )

    def test_committed_outputs_match_canonical_sources(self) -> None:
        self.assertEqual([], adapters.validate_generated_outputs(ROOT))

    def test_codex_agent_identity_is_namespaced_but_skills_stay_bare(self) -> None:
        """Codex resolves a custom agent by its `name` field, not its filename.

        Documented at https://learn.chatgpt.com/docs/agent-configuration/subagents:
        "Codex identifies the custom agent by its `name` field. Matching the filename to the
        agent name is the simplest convention, but the `name` field is the source of truth."

        So a prefixed FILENAME alone stops an install from overwriting another suite's file
        but leaves the invocable identity colliding. Sibling-agent references must move with
        the identity, or a body saying "hand off to researcher" resolves to the OTHER fleet's
        researcher -- silently crossing this fleet's local/external trust split. Skills are not
        renamed and must stay bare.
        """
        codex = tomllib.loads(adapters.render_codex_agent(ROOT / "agents/sde.md"))
        body = codex["developer_instructions"]
        self.assertEqual("save-toolkit-sde", codex["name"])
        # Namespaced reference in the canonical description.
        self.assertIn("save-toolkit-reviewer", codex["description"])
        # Bare backticked sibling in the body must move with the identity, or it spawns
        # whichever `reviewer` another installed suite happens to own.
        self.assertIn("`save-toolkit-reviewer`", body)
        self.assertNotIn("`reviewer`", body)
        # Skills are not renamed, and prose must not be rewritten.
        self.assertIn("eng-ladder", body)
        self.assertNotIn("save-toolkit-eng-ladder", body)
        self.assertNotIn("save-toolkit:", body)
        self.assertIn("SRE lens", body)

    def test_codex_skill_projection_namespaces_agent_references(self) -> None:
        """Skills carry sibling references too, and Codex resolves them by bare name.

        The agent-profile rewrite alone left 125 bare backticked references in the Codex
        skills projection, so a skill saying "route it to `sre`" spawned whichever `sre`
        another installed suite owned. This asserts over EVERY Codex skill output rather
        than one file, because a single-file assertion is what let that gap survive.
        """
        agent_names = {path.stem for path in (ROOT / "agents").glob("*.md")}
        offenders = []
        for path, blob in adapters.expected_outputs(ROOT).items():
            if path.parts[:3] != ("plugins", "save-toolkit", "skills"):
                continue
            if path.suffix.lower() not in {".md", ".txt"}:
                continue
            text = blob.decode("utf-8")
            offenders.extend(
                f"{path.as_posix()}: `{name}`" for name in agent_names if f"`{name}`" in text
            )
        self.assertEqual([], sorted(offenders))

    def test_codex_agent_filenames_carry_a_fleet_prefix(self) -> None:
        """Codex custom agents share ONE flat global directory with no namespace.

        Claude loads these as `save-toolkit:<name>` and cannot collide. Codex installs bare
        filenames into `$CODEX_HOME/agents`, where `prompt-engineer.toml`,
        `repository-investigator.toml` and `researcher.toml` are names other agent suites
        also use — so an unprefixed projection overwrites user-owned files from another fleet.
        """
        emitted = [
            path
            for path in adapters.expected_outputs(ROOT)
            if path.parent == adapters.CODEX_AGENTS
        ]
        self.assertTrue(emitted, "no Codex agent adapters were emitted")
        unprefixed = sorted(
            path.name for path in emitted if not path.name.startswith("save-toolkit-")
        )
        self.assertEqual([], unprefixed, "Codex agent filenames must be fleet-prefixed")
        # `save-toolkit-` mirrors the Claude namespace. A bare `sre-` prefix would produce
        # sre-sre.toml and sre-observability-engineer.toml for the two roles already starting with `sre`.
        self.assertIn(adapters.CODEX_AGENTS / "save-toolkit-sre.toml", emitted)
        self.assertIn(adapters.CODEX_AGENTS / "save-toolkit-observability-engineer.toml", emitted)

    def test_guarded_copilot_agents_do_not_receive_execute(self) -> None:
        for name in sorted(adapters.GUARDED_AGENTS):
            self.assertNotIn("execute", self._copilot_tools(name), name)

    def test_builder_copilot_agent_keeps_edit_and_execute(self) -> None:
        tools = self._copilot_tools("sde")
        self.assertIn("edit", tools)
        self.assertIn("execute", tools)

    def test_scribe_copilot_agent_can_edit_but_cannot_execute_or_delegate(self) -> None:
        self.assertEqual(["read", "search", "edit"], self._copilot_tools("scribe"))

    def test_copilot_research_boundaries_are_mutually_exclusive(self) -> None:
        self.assertEqual(["read", "search"], self._copilot_tools("repository-investigator"))
        self.assertEqual(["web"], self._copilot_tools("researcher"))
        for name in sorted(
            path.stem for path in (ROOT / "agents").glob("*.md") if path.stem != "researcher"
        ):
            self.assertNotIn("web", self._copilot_tools(name), name)

    def test_codex_sandbox_follows_write_authority(self) -> None:
        reviewer = tomllib.loads(adapters.render_codex_agent(ROOT / "agents/reviewer.md"))
        builder = tomllib.loads(adapters.render_codex_agent(ROOT / "agents/sde.md"))
        scribe = tomllib.loads(adapters.render_codex_agent(ROOT / "agents/scribe.md"))
        self.assertEqual("read-only", reviewer["sandbox_mode"])
        self.assertEqual("workspace-write", builder["sandbox_mode"])
        self.assertEqual("workspace-write", scribe["sandbox_mode"])
        self.assertIn("Do not execute anything", scribe["developer_instructions"])
        self.assertIn("Codex custom-agent TOML cannot deny inherited tools", scribe["developer_instructions"])
        self.assertIn("disable network egress and external MCP tools", scribe["developer_instructions"])

    def test_codex_reviewer_does_not_self_disable_on_inherited_capability_visibility(self) -> None:
        reviewer = tomllib.loads(adapters.render_codex_agent(ROOT / "agents/reviewer.md"))
        instructions = reviewer["developer_instructions"]
        self.assertIn("capability visibility alone is therefore not a fleet failure", instructions)
        self.assertIn("if this reviewer actually", instructions)
        self.assertIn("executes or delegates", instructions)
        self.assertNotIn("if you ever find yourself able to run a shell command", instructions)

    def test_codex_research_boundaries_require_outer_isolation(self) -> None:
        local = tomllib.loads(
            adapters.render_codex_agent(ROOT / "agents/repository-investigator.md")
        )
        external = tomllib.loads(adapters.render_codex_agent(ROOT / "agents/researcher.md"))
        self.assertIn("disable network egress", local["developer_instructions"])
        self.assertIn("do not mount the private repository", external["developer_instructions"])

    def test_generated_agent_descriptions_use_host_native_names(self) -> None:
        for source in sorted((ROOT / "agents").glob("*.md")):
            copilot = adapters.render_copilot_agent(source)
            frontmatter = copilot.split("---", 2)[1]
            description = json.loads(
                next(line for line in frontmatter.splitlines() if line.startswith("description: "))[13:]
            )
            codex = tomllib.loads(adapters.render_codex_agent(source))
            self.assertNotIn("save-toolkit:", description, source.name)
            self.assertNotIn("save-toolkit:", codex["description"], source.name)
        self.assertIn("eng-ladder", adapters.render_copilot_agent(ROOT / "agents/sde.md"))
        self.assertIn("reviewer", tomllib.loads(adapters.render_codex_agent(ROOT / "agents/sde.md"))["description"])

    def test_codex_rewrite_does_not_corrupt_api_paths(self) -> None:
        value = adapters.adapt_text("GET /healthz; run `/pcf-deploy`; ref #/components/schemas/X", "codex")
        self.assertIn("/healthz", value)
        self.assertIn("#/components/schemas/X", value)
        self.assertIn("`$pcf-deploy`", value)

    def test_manual_skills_get_host_native_invocation_controls(self) -> None:
        for name in sorted(adapters.MANUAL_ONLY):
            copilot = (ROOT / adapters.COPILOT_SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
            codex = (ROOT / adapters.CODEX_SKILLS / name / "SKILL.md").read_text(encoding="utf-8")
            policy = ROOT / adapters.CODEX_SKILLS / name / "agents/openai.yaml"
            self.assertIn("disable-model-invocation: true", copilot)
            self.assertNotIn("disable-model-invocation:", codex)
            self.assertIn("allow_implicit_invocation: false", policy.read_text(encoding="utf-8"))

    def test_platform_manifests_agree(self) -> None:
        self.assertEqual([], adapters.validate_platform_contracts(ROOT))

    def test_byte_drift_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            shutil.copytree(ROOT / "agents", root / "agents")
            shutil.copytree(ROOT / "skills", root / "skills")
            for relative in adapters.GENERATED_ROOTS:
                shutil.copytree(ROOT / relative, root / relative)
            target = root / adapters.COPILOT_AGENTS / "sde.agent.md"
            target.write_text(target.read_text(encoding="utf-8") + "\nmanual edit\n", encoding="utf-8")
            failures = adapters.validate_generated_outputs(root)
        self.assertTrue(any("generated output drift" in failure for failure in failures))

    def test_retired_generated_root_present_on_disk_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self.assertEqual([], adapters._retired_generated_root_failures(root))
            retired = root / adapters.RETIRED_GENERATED_ROOTS[0]
            retired.mkdir(parents=True)
            (retired / "leftover.md").write_text("stale mirror\n", encoding="utf-8")
            failures = adapters._retired_generated_root_failures(root)
        self.assertTrue(any("retired generated root" in f for f in failures), failures)

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

    def test_crlf_code_asset_is_normalized_in_projection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            shutil.copytree(ROOT / "agents", root / "agents")
            shutil.copytree(ROOT / "skills", root / "skills")
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
                and (adapters.COPILOT_SKILLS in path.parents or adapters.CODEX_SKILLS in path.parents)
            ]
            self.assertTrue(projected, "code asset was not projected")
            for blob in projected:
                self.assertNotIn(b"\r", blob, "CRLF source leaked into a generated code asset")

    def test_directory_swap_failure_restores_every_existing_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            shutil.copytree(ROOT / "agents", root / "agents")
            shutil.copytree(ROOT / "skills", root / "skills")
            for relative in adapters.GENERATED_ROOTS:
                destination = root / relative
                destination.mkdir(parents=True)
                (destination / "sentinel.txt").write_text(relative.as_posix(), encoding="utf-8")

            real_replace = adapters.os.replace

            def fail_second_stage(source: str | Path, destination: str | Path) -> None:
                source_path = Path(source)
                destination_path = Path(destination)
                if destination_path == root / adapters.CODEX_AGENTS and "new" in source_path.parts:
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
            shutil.copytree(ROOT / "agents", root / "agents")
            shutil.copytree(ROOT / "skills", root / "skills")
            (root / ".github").mkdir()
            real_check = adapters._is_link_or_reparse

            def mark_github_as_indirection(path: Path) -> bool:
                return path == root / ".github" or real_check(path)

            with mock.patch.object(adapters, "_is_link_or_reparse", side_effect=mark_github_as_indirection):
                with self.assertRaisesRegex(ValueError, "must not traverse"):
                    adapters.write_generated_outputs(root)


if __name__ == "__main__":
    unittest.main()
