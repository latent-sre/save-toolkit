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

    def test_guarded_copilot_agents_do_not_receive_execute(self) -> None:
        for name in sorted(adapters.GUARDED_AGENTS):
            self.assertNotIn("execute", self._copilot_tools(name), name)

    def test_builder_copilot_agent_keeps_edit_and_execute(self) -> None:
        tools = self._copilot_tools("sde")
        self.assertIn("edit", tools)
        self.assertIn("execute", tools)

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
        self.assertEqual("read-only", reviewer["sandbox_mode"])
        self.assertEqual("workspace-write", builder["sandbox_mode"])

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
            self.assertNotIn("sre-agents:", description, source.name)
            self.assertNotIn("sre-agents:", codex["description"], source.name)
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
