"""Structural tests for the Claude plugin's session-wide guard hook."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def available_shell() -> str | None:
    discovered = shutil.which("sh")
    if discovered:
        return discovered
    for candidate in (r"C:\Program Files\Git\bin\sh.exe", r"C:\Program Files\Git\usr\bin\sh.exe"):
        if Path(candidate).is_file():
            return candidate
    return None


def rebuild_inline_command(script_lines: list[str]) -> str:
    """Join the standalone launcher's stripped lines back into one inlined hook command."""
    rebuilt: list[str] = []
    for line in script_lines:
        if rebuilt and rebuilt[-1].endswith(" do"):
            rebuilt[-1] = f"{rebuilt[-1]} {line}"
        elif rebuilt:
            rebuilt[-1] = f"{rebuilt[-1]}; {line}"
        else:
            rebuilt.append(line)
    if len(rebuilt) != 1:
        raise AssertionError(
            "scripts/readonly-guard-hook.sh must rebuild into exactly one command, "
            f"got {len(rebuilt)}; the launcher is empty or was split into separate statements"
        )
    return rebuilt[0]


class RebuildInlineCommandTests(unittest.TestCase):
    def test_an_empty_launcher_is_reported_not_indexed(self) -> None:
        """A launcher that strips to nothing must name the problem, not raise IndexError.

        The drift check exists to print a specific remedy. Indexing rebuilt[0] on an empty
        list replaces that remedy with a bare traceback at the moment it is needed most.
        """
        with self.assertRaisesRegex(AssertionError, "exactly one command"):
            rebuild_inline_command([])


class HookWiringTests(unittest.TestCase):
    def test_hook_is_session_wide_and_fail_closed_for_guarded_agents(self) -> None:
        document = json.loads((ROOT / "hooks/hooks.json").read_text(encoding="utf-8"))
        entry = document["hooks"]["PreToolUse"][0]
        self.assertEqual("Bash", entry["matcher"])
        command = entry["hooks"][0]["command"]
        for token in (
            "${CLAUDE_PLUGIN_ROOT}/scripts/readonly-guard.py",
            '"permissionDecision":"deny"',
            "python3 python py",
        ):
            self.assertIn(token, command)
        self.assertNotIn('case "$IN"', command)

    def test_standalone_launcher_matches_inlined_hook_command(self) -> None:
        """scripts/readonly-guard-hook.sh and the hooks.json command are the same program.

        The launcher exists twice: inlined as the live hook command and as the standalone
        shell file (a hash input for eval provenance). Without this check the two copies can
        drift silently — and the drifting copy would be the enforced one.
        """
        document = json.loads((ROOT / "hooks/hooks.json").read_text(encoding="utf-8"))
        inlined = document["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        script_lines = [
            line.strip()
            for line in (ROOT / "scripts/readonly-guard-hook.sh")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertEqual(
            rebuild_inline_command(script_lines),
            inlined,
            "hooks.json inline command and scripts/readonly-guard-hook.sh have drifted; "
            "edit both together (strip comments, join with '; ', keep loop bodies on ' ')",
        )

    def test_plugin_agents_do_not_claim_inert_hooks(self) -> None:
        for path in sorted((ROOT / "agents").glob("*.md")):
            frontmatter = path.read_text(encoding="utf-8").split("---", 2)[1]
            self.assertNotIn("\nhooks:", frontmatter, path.name)

    def test_copilot_hook_is_explicitly_empty(self) -> None:
        document = json.loads((ROOT / "hooks/copilot-hooks.json").read_text(encoding="utf-8"))
        self.assertEqual({}, document.get("hooks"))

    @unittest.skipUnless(available_shell(), "POSIX shell not available")
    def test_exact_hook_command_allows_safe_denies_write_and_ignores_main(self) -> None:
        document = json.loads((ROOT / "hooks/hooks.json").read_text(encoding="utf-8"))
        command = document["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        environment = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(ROOT))

        def invoke_raw(payload: str, *, env: dict[str, str] = environment) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [available_shell(), "-c", command],
                input=payload,
                text=True,
                capture_output=True,
                cwd=ROOT,
                env=env,
                timeout=30,
                check=False,
            )

        def invoke(payload: dict, *, env: dict[str, str] = environment) -> subprocess.CompletedProcess[str]:
            return invoke_raw(json.dumps(payload), env=env)

        safe = invoke({"tool_name": "Bash", "agent_type": "save-toolkit:sre", "tool_input": {"command": "git status --short"}})
        denied = invoke({"tool_name": "Bash", "agent_type": "save-toolkit:sre", "tool_input": {"command": "git push origin main"}})
        main = invoke({"tool_name": "Bash", "tool_input": {"command": "git push origin main"}})
        whitespace = invoke_raw('{\n "tool_name" : "Bash", "agent_type"\t:\t"save-toolkit:sre", "tool_input" : {"command" : "git push origin main"}}')
        renamed = invoke({"tool_name": "Bash", "subagent_type": "save-toolkit:sre", "tool_input": {"command": "git push origin main"}})
        unavailable = invoke(
            {"tool_name": "Bash", "tool_input": {"command": "git status"}},
            env=dict(environment, PATH=""),
        )
        self.assertEqual((0, ""), (safe.returncode, safe.stdout))
        self.assertEqual(0, denied.returncode)
        self.assertEqual("deny", json.loads(denied.stdout)["hookSpecificOutput"]["permissionDecision"])
        self.assertEqual((0, ""), (main.returncode, main.stdout))
        self.assertEqual("deny", json.loads(whitespace.stdout)["hookSpecificOutput"]["permissionDecision"])
        self.assertEqual("deny", json.loads(renamed.stdout)["hookSpecificOutput"]["permissionDecision"])
        self.assertEqual("deny", json.loads(unavailable.stdout)["hookSpecificOutput"]["permissionDecision"])


if __name__ == "__main__":
    unittest.main()
