"""The shared test helpers must fail loudly; a helper that quietly matches nothing hides a test."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import testkit


class MarkdownHelperTests(unittest.TestCase):
    TEXT = "# T\n\n## Evidence base\nwrong\n## Evidence\nright\n### Detail\nkept\n## Next\nout\n"

    def test_section_matches_the_exact_heading_and_keeps_deeper_headings(self) -> None:
        self.assertEqual("\nright\n### Detail\nkept\n", testkit.markdown_section(self.TEXT, "## Evidence"))
        self.assertEqual("\nkept\n", testkit.markdown_section(self.TEXT, "### Detail"))

    def test_a_missing_heading_or_a_non_heading_is_an_error(self) -> None:
        with self.assertRaises(AssertionError):
            testkit.markdown_section(self.TEXT, "### Evidence")
        with self.assertRaises(ValueError):
            testkit.markdown_section(self.TEXT, "Evidence")

    def test_frontmatter_block_requires_a_closed_opening_fence(self) -> None:
        self.assertEqual("name: x\n", testkit.frontmatter_block("---\nname: x\n---\nbody --- here\n"))
        for text in ("name: x\n---\n", "---\nname: x\n", "\n---\nname: x\n---\n"):
            with self.subTest(text=text), self.assertRaises(AssertionError):
                testkit.frontmatter_block(text)

    def test_normalized_ignores_case_and_wrapping(self) -> None:
        self.assertEqual(testkit.normalized("One  Two\nthree"), testkit.normalized("one two three "))


class MutationAndLoadingTests(unittest.TestCase):
    def test_must_replace_refuses_a_mutation_that_matches_nothing(self) -> None:
        self.assertEqual("a-b a", testkit.must_replace("a a a", " a", "-b"))
        self.assertEqual("a-b-b", testkit.must_replace("a a a", " a", "-b", count=-1))
        with self.assertRaises(AssertionError):
            testkit.must_replace("text", "absent", "x")

    def test_load_path_registers_the_module_and_unregisters_a_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            good, bad = Path(tmp, "good.py"), Path(tmp, "bad.py")
            good.write_text("from dataclasses import dataclass\n@dataclass\nclass Row:\n    value: int\n",
                            encoding="utf-8")
            bad.write_text("raise RuntimeError('boom')\n", encoding="utf-8")
            try:
                module = testkit.load_path(good, "testkit_probe_good")
                self.assertIs(sys.modules["testkit_probe_good"], module)
                self.assertEqual(1, module.Row(1).value)
                with self.assertRaises(RuntimeError):
                    testkit.load_path(bad, "testkit_probe_bad")
                self.assertNotIn("testkit_probe_bad", sys.modules)
            finally:
                sys.modules.pop("testkit_probe_good", None)


class GuardRunnerTests(unittest.TestCase):
    DENY = b'{"hookSpecificOutput": {"permissionDecision": "deny"}}'

    @staticmethod
    def completed(returncode: int, stdout: bytes = b"") -> subprocess.CompletedProcess[bytes]:
        return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=b"")

    def test_decision_requires_the_exit_code_and_stdout_to_agree(self) -> None:
        self.assertEqual("allow", testkit.guard_decision(self.completed(42)))
        self.assertEqual("deny", testkit.guard_decision(self.completed(43, self.DENY)))
        for proc in (
            self.completed(42, self.DENY),
            self.completed(43, self.DENY.replace(b"deny", b"allow")),
            self.completed(44), self.completed(1), self.completed(0),
        ):
            with self.subTest(returncode=proc.returncode, stdout=proc.stdout), self.assertRaises(AssertionError):
                testkit.guard_decision(proc)

    def test_payload_names_the_guarded_agent_unless_told_otherwise(self) -> None:
        self.assertEqual(
            {"tool_name": "Bash", "tool_input": {"command": "x"}, "agent_type": "save-toolkit:sre-assistant"},
            json.loads(testkit.guard_payload("x")),
        )
        self.assertNotIn("agent_type", json.loads(testkit.guard_payload("x", agent_type=None)))

    def test_the_guard_runs_isolated_as_the_hook_launches_it(self) -> None:
        with mock.patch.object(testkit.subprocess, "run", return_value=self.completed(42)) as run:
            testkit.run_guard("{}", copilot=True)
        self.assertEqual([sys.executable, "-I", "-S", str(testkit.GUARD), "--copilot"], run.call_args.args[0])
        self.assertEqual("deny", testkit.guard_decision(testkit.run_guard(testkit.guard_payload("git push"))))

    def test_decisions_cover_every_tool_agent_and_command(self) -> None:
        sent: list[str] = []

        def fake_batch(payloads: list[str], *, copilot: bool = False) -> list[subprocess.CompletedProcess[bytes]]:
            sent.extend(payloads)
            return [self.completed(42) for _ in payloads]

        tools, agents, commands = ("Bash", "PowerShell"), ("save-toolkit:software-engineer", None), ("a", "b")
        with mock.patch.object(testkit, "run_guard_batch", side_effect=fake_batch):
            testkit.assert_guard_decisions(self, "allow", commands, tool_names=tools, agent_types=agents)
        self.assertCountEqual(
            [testkit.guard_payload(command, tool_name=tool, agent_type=agent)
             for tool in tools for agent in agents for command in commands],
            sent,
        )

    def test_batch_requires_overlapping_invocations(self) -> None:
        barrier = threading.Barrier(2)

        def fake_run_guard(payload: str, *, copilot: bool = False) -> subprocess.CompletedProcess[bytes]:
            try:
                barrier.wait(timeout=1)
            except threading.BrokenBarrierError as exc:
                raise AssertionError("run_guard_batch stopped overlapping guard invocations") from exc
            return self.completed(42)

        # run_guard_batch looks run_guard up in testkit on every call; patching any other module's
        # name for it would leave the real guard running and this test passing without a barrier.
        with mock.patch.object(testkit, "run_guard", side_effect=fake_run_guard) as fake:
            procs = testkit.run_guard_batch(["{}", "{}"])
        self.assertEqual(2, fake.call_count)
        self.assertEqual([42, 42], [proc.returncode for proc in procs])


if __name__ == "__main__":
    unittest.main()
