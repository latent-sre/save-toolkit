"""Contract tests for the generated host adapters."""

from __future__ import annotations

import os
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
            Path("plugins/save-toolkit/.codex-plugin/plugin.json"),
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
        scanned = 0
        for path, blob in adapters.expected_outputs(ROOT).items():
            # Iterate by the generator's own constant, not a hard-coded path tuple: if CODEX_SKILLS
            # ever moves, a literal tuple would silently match nothing and this test would verify
            # nothing while staying green.
            if adapters.CODEX_SKILLS not in path.parents:
                continue
            if path.suffix.lower() not in {".md", ".txt"}:
                continue
            scanned += 1
            text = blob.decode("utf-8")
            offenders.extend(
                f"{path.as_posix()}: `{name}`" for name in agent_names if f"`{name}`" in text
            )
        self.assertTrue(scanned, "no Codex skill files were scanned — the projection path moved")
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

    def test_each_platform_manifest_is_required(self) -> None:
        manifests = (
            Path(".claude-plugin/plugin.json"),
            Path("plugin.json"),
            Path("plugins/save-toolkit/.codex-plugin/plugin.json"),
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

    def test_codex_manifest_rejects_unsupported_component_paths(self) -> None:
        for field in ("agents", "hooks"):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                self._copy_platform_contract_files(root)
                self.assertEqual([], adapters.validate_platform_contracts(root))
                target = root / "plugins/save-toolkit/.codex-plugin/plugin.json"
                manifest = json.loads(target.read_text(encoding="utf-8"))
                manifest[field] = f"./{field}/"
                target.write_text(json.dumps(manifest), encoding="utf-8", newline="\n")
                failures = adapters.validate_platform_contracts(root)
                self.assertIn(
                    f"Codex manifest must not claim unsupported {field!r} component",
                    failures,
                )

    def test_codex_skills_path_cannot_be_deduplicated_to_copilot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self._copy_platform_contract_files(root)
            self.assertEqual([], adapters.validate_platform_contracts(root))
            target = root / "plugins/save-toolkit/.codex-plugin/plugin.json"
            manifest = json.loads(target.read_text(encoding="utf-8"))
            manifest["skills"] = "./platforms/copilot/skills/"
            target.write_text(json.dumps(manifest), encoding="utf-8", newline="\n")
            failures = adapters.validate_platform_contracts(root)
        self.assertIn("Codex manifest skills must be './skills/'", failures)

    def test_byte_drift_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self._copy_canonical_sources(root)
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
                and (adapters.COPILOT_SKILLS in path.parents or adapters.CODEX_SKILLS in path.parents)
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
            generated = root / adapters.GENERATED_ROOTS[2]
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

if __name__ == "__main__":
    unittest.main()
