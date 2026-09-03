"""Structural tests for the Claude plugin's session-wide guard hook."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
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
        self.assertIn("TRACE=", command)
        self.assertIn("exit-${RC}", command)

    def test_session_start_preflights_the_guard_interpreter_protocol(self) -> None:
        document = json.loads((ROOT / "hooks/hooks.json").read_text(encoding="utf-8"))
        entry = document["hooks"]["SessionStart"][0]
        self.assertEqual("startup|resume|clear|compact", entry["matcher"])
        command = entry["hooks"][0]["command"]
        for token in (
            "guard-session-preflight.py",
            "python3 python py",
            "candidate failures",
        ):
            self.assertIn(token, command)

        script_lines = [
            line.strip()
            for line in (ROOT / "scripts/guard-session-preflight-hook.sh")
            .read_text(encoding="utf-8")
            .splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertEqual(rebuild_inline_command(script_lines), command)

    def test_session_preflight_accepts_the_current_interpreter(self) -> None:
        result = subprocess.run(
            [sys.executable, "-I", "-S", str(ROOT / "scripts/guard-session-preflight.py")],
            text=True,
            capture_output=True,
            cwd=ROOT,
            timeout=30,
            check=False,
        )
        self.assertEqual(42, result.returncode, result.stderr)
        self.assertEqual("", result.stdout)

    @unittest.skipUnless(available_shell(), "POSIX shell not available")
    def test_exact_session_start_command_accepts_the_lane_path(self) -> None:
        document = json.loads((ROOT / "hooks/hooks.json").read_text(encoding="utf-8"))
        command = document["hooks"]["SessionStart"][0]["hooks"][0]["command"]
        result = subprocess.run(
            [available_shell(), "-c", command],
            input='{"hook_event_name":"SessionStart","source":"startup"}',
            text=True,
            capture_output=True,
            cwd=ROOT,
            env=dict(os.environ, CLAUDE_PLUGIN_ROOT=str(ROOT)),
            timeout=30,
            check=False,
        )
        self.assertEqual((0, ""), (result.returncode, result.stdout), result.stderr)

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
        """The ONLY test that runs the real inlined hooks.json command string.

        Every other guard test invokes `[sys.executable, GUARD]` directly, which is a different
        invocation: it never exercises `"$C" -I -S "$G"` (isolated mode, no site) or the
        `python3 python py` interpreter walk that the live hook depends on.

        The skip below is a local-developer convenience. A focused run that reports this test
        skipped did not exercise the real hook command and is incomplete evidence; rerun it on a
        machine with `sh`. Gate A does not run this component suite.
        """
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

        safe = invoke({"tool_name": "Bash", "agent_type": "save-toolkit:sre-assistant", "tool_input": {"command": "git status --short"}})
        denied = invoke({"tool_name": "Bash", "agent_type": "save-toolkit:sre-assistant", "tool_input": {"command": "git push origin main"}})
        main = invoke({"tool_name": "Bash", "tool_input": {"command": "git push origin main"}})
        whitespace = invoke_raw('{\n "tool_name" : "Bash", "agent_type"\t:\t"save-toolkit:sre-assistant", "tool_input" : {"command" : "git push origin main"}}')
        renamed = invoke({"tool_name": "Bash", "subagent_type": "save-toolkit:sre-assistant", "tool_input": {"command": "git push origin main"}})
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

    @unittest.skipUnless(available_shell(), "POSIX shell not available")
    def test_a_stub_interpreter_first_on_path_does_not_disarm_the_guard(self) -> None:
        """The incident validate.yml cites, reproduced: a non-interpreter named `python3` answers first.

        The Microsoft Store stub is on PATH as `python3` on a stock Windows box. The guard's earlier
        inline form ran it, took exit 0 as "allowed", and every guarded Bash call sailed through. The
        current loop only trusts the guard's own exit codes (42 allow / 43 deny), so a stub that exits
        0 with no output must be skipped, the next interpreter must answer, and a machine with ONLY
        stubs must fail closed. The marker file proves the stub was actually consulted -- without it
        this test could pass while `command -v` never found the stub at all.
        """
        document = json.loads((ROOT / "hooks/hooks.json").read_text(encoding="utf-8"))
        command = document["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
        cat = shutil.which("cat")
        if cat is None:
            self.skipTest("`cat` not on PATH; the hook reads stdin through it")
        guarded_write = json.dumps({"tool_name": "Bash", "agent_type": "save-toolkit:sre-assistant", "tool_input": {"command": "git push origin main"}})
        main_thread = json.dumps({"tool_name": "Bash", "tool_input": {"command": "git push origin main"}})

        def run(path: str, payload: str) -> subprocess.CompletedProcess[str]:
            env = dict(os.environ, CLAUDE_PLUGIN_ROOT=str(ROOT), PATH=path)
            return subprocess.run([available_shell(), "-c", command], input=payload, text=True,
                                  capture_output=True, cwd=ROOT, env=env, timeout=30, check=False)

        with tempfile.TemporaryDirectory() as tmp:
            stub_dir = Path(tmp) / "stub"
            real_dir = Path(tmp) / "real"
            stub_dir.mkdir()
            real_dir.mkdir()
            marker = Path(tmp) / "stub-was-consulted"
            stub = stub_dir / "python3"
            stub.write_text(f"#!/bin/sh\necho hit >> '{marker.as_posix()}'\nexit 0\n", encoding="utf-8")
            stub.chmod(0o755)
            # A `python` wrapper to the real interpreter, so the walk has something honest to reach
            # after the stub regardless of what the host calls its interpreter.
            wrapper = real_dir / "python"
            wrapper.write_text(f'#!/bin/sh\nexec "{Path(sys.executable).as_posix()}" "$@"\n', encoding="utf-8")
            wrapper.chmod(0o755)
            tools = os.path.dirname(cat)
            # The tools dir is wherever `cat` lives -- /usr/bin on Linux, which also holds the real
            # python3. So the stubs-only case stubs EVERY name the hook walks, ahead of it.
            all_stubs = Path(tmp) / "all-stubs"
            all_stubs.mkdir()
            for name in ("python3", "python", "py"):
                shutil.copy(stub, all_stubs / name)
                (all_stubs / name).chmod(0o755)
            stub_then_real = os.pathsep.join([str(stub_dir), str(real_dir), tools])
            stubs_only = os.pathsep.join([str(all_stubs), tools])

            denied = run(stub_then_real, guarded_write)
            self.assertTrue(marker.exists(), "the stub was never consulted, so this proves nothing")
            self.assertTrue(denied.stdout, "the guarded write was ALLOWED: the stub's exit 0 was taken as the guard's answer -- the original disarm")
            decision = json.loads(denied.stdout)["hookSpecificOutput"]
            self.assertEqual("deny", decision["permissionDecision"])
            self.assertIn("allowlist", decision["permissionDecisionReason"], "the GUARD must have answered, not the fail-closed fallback")

            allowed = run(stub_then_real, main_thread)
            self.assertEqual((0, ""), (allowed.returncode, allowed.stdout), "a stub first on PATH must not turn into a false deny either")

            closed = run(stubs_only, guarded_write)
            decision = json.loads(closed.stdout)["hookSpecificOutput"]
            self.assertEqual("deny", decision["permissionDecision"])
            self.assertIn("unavailable", decision["permissionDecisionReason"], "with only stubs, the hook must fail closed by name")

    def test_explicit_ci_run_must_not_skip_the_real_hook_invocation(self) -> None:
        """When this suite is explicitly run in CI, an absent shell is a failure.

        The structural workflow does not invoke component suites. This assertion applies whenever
        a caller explicitly adds this focused suite to a CI job: the job must not turn a missing
        shell into green evidence for the hook boundary.
        """
        if not os.environ.get("CI"):
            self.skipTest("local run; the shell requirement is enforced on CI")
        self.assertIsNotNone(
            available_shell(),
            "CI has no POSIX shell, so the only test of the real hooks.json command string would "
            "be skipped and this job would report green over an unexercised guard. Install a "
            "shell on this runner (Git for Windows provides one) rather than accepting the skip.",
        )


if __name__ == "__main__":
    unittest.main()
