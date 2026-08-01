#!/usr/bin/env python3
"""Tests for evals/clean_room.py.

The clean room is what makes an eval number a property of the FLEET rather than of the machine it
ran on. These tests hold it to two things: it isolates, and it REFUSES rather than producing a
measurement it cannot stand behind.

Runnable:
    python3 evals/test_clean_room.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clean_room  # noqa: E402

_results: list[tuple[bool, str]] = []


def check(cond: bool, label: str) -> None:
    _results.append((bool(cond), label))
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}")


def _fake_home(tmp: Path) -> Path:
    """A config dir that looks logged-in, plus the junk a real one carries."""
    cfg = tmp / "cfg"
    (cfg / "skills" / "eng-ladder").mkdir(parents=True)
    (cfg / "agents").mkdir(parents=True)
    (cfg / "plugins").mkdir(parents=True)
    (cfg / "CLAUDE.md").write_text("personal instructions\n", encoding="utf-8")
    (cfg / clean_room.CREDENTIALS).write_text('{"token": "secret"}', encoding="utf-8")
    return cfg


def test_clean_env_copies_only_the_credentials() -> None:
    with tempfile.TemporaryDirectory() as td:
        cfg = _fake_home(Path(td))
        os.environ["CLAUDE_CONFIG_DIR"] = str(cfg)
        try:
            with clean_room.clean_env() as env:
                room = Path(env["CLAUDE_CONFIG_DIR"])
                names = sorted(p.name for p in room.iterdir())
                check(names == [clean_room.CREDENTIALS],
                      f"clean room holds ONLY the credentials (got {names})")
                check((room / clean_room.CREDENTIALS).read_text(encoding="utf-8") == '{"token": "secret"}',
                      "credentials were copied, not fabricated")
                check(not (room / "skills").exists(), "personal skills are NOT visible")
                check(not (room / "agents").exists(), "personal agents are NOT visible")
                check(not (room / "plugins").exists(), "installed plugins are NOT visible")
                check(not (room / "CLAUDE.md").exists(), "personal CLAUDE.md is NOT visible")
        finally:
            del os.environ["CLAUDE_CONFIG_DIR"]


def test_clean_env_is_removed_even_when_the_body_raises() -> None:
    with tempfile.TemporaryDirectory() as td:
        cfg = _fake_home(Path(td))
        os.environ["CLAUDE_CONFIG_DIR"] = str(cfg)
        room = None
        try:
            with clean_room.clean_env() as env:
                room = Path(env["CLAUDE_CONFIG_DIR"])
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        finally:
            del os.environ["CLAUDE_CONFIG_DIR"]
        check(room is not None and not room.exists(),
              "the temp dir (which held an auth secret) is removed on exception")


def test_missing_credentials_raises_instead_of_running() -> None:
    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td) / "cfg"
        cfg.mkdir()  # exists, but no credentials
        os.environ["CLAUDE_CONFIG_DIR"] = str(cfg)
        try:
            try:
                with clean_room.clean_env():
                    check(False, "clean_env must NOT yield without credentials")
            except clean_room.AuthUnavailable as e:
                check("no Claude credentials" in str(e), "AuthUnavailable names the problem")
                check("no-route" in str(e),
                      "the error explains WHY this is fatal (else it reads as a fake finding)")
        finally:
            del os.environ["CLAUDE_CONFIG_DIR"]


def test_api_key_auth_bypasses_the_credentials_file_requirement() -> None:
    """[P2] ANTHROPIC_API_KEY (or Bedrock/Vertex) operators have NO ~/.claude/.credentials.json --
    not a missing one, a nonexistent concept -- yet `claude -p` works for them. clean_env() must not
    refuse them; it should skip the credential copy and still yield full isolation (empty temp dir)."""
    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td) / "cfg"
        cfg.mkdir()  # exists, but no credentials -- would normally raise AuthUnavailable
        os.environ["CLAUDE_CONFIG_DIR"] = str(cfg)
        os.environ["ANTHROPIC_API_KEY"] = "sk-test-not-a-real-key"
        os.environ["GITHUB_TOKEN"] = "must-not-reach-model-tools"
        try:
            with clean_room.clean_env() as env:
                room = Path(env["CLAUDE_CONFIG_DIR"])
                check(room.is_dir(), "clean_env yields a temp dir even with no credentials file")
                check(list(room.iterdir()) == [], "the temp dir is empty -- no credentials to copy")
                check(env.get("ANTHROPIC_API_KEY") == "sk-test-not-a-real-key",
                      "the selected Claude authentication variable is retained")
                check("GITHUB_TOKEN" not in env, "unrelated host secrets are scrubbed from the child env")
                check(bool(env.get("PATH")), "the executable PATH is retained")
        except clean_room.AuthUnavailable:
            check(False, "an API-key operator must NOT be refused for lacking a credentials file")
        finally:
            del os.environ["CLAUDE_CONFIG_DIR"]
            del os.environ["ANTHROPIC_API_KEY"]
            del os.environ["GITHUB_TOKEN"]


def test_neutral_workspace_is_empty_outside_the_repository_and_removed() -> None:
    room = None
    with clean_room.neutral_workspace() as workspace:
        room = workspace
        check(workspace.is_dir(), "neutral workspace exists during the trial")
        check(sorted(path.name for path in workspace.iterdir()) == [".git"],
              "neutral workspace contains only its git-root boundary")
        check(not workspace.is_relative_to(Path.cwd()), "neutral workspace is outside the plugin repository")
        import subprocess
        top = subprocess.run(
            ["git", "-C", str(workspace), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True, encoding="utf-8",
        ).stdout.strip()
        check(Path(top).resolve() == workspace.resolve(), "neutral workspace is its own git root")
    check(room is not None and not room.exists(), "neutral workspace is removed after the trial")


def test_is_auth_failure_recognises_a_real_not_logged_in_trace() -> None:
    # Verbatim shapes from a probed credential-less run. Note the trap: the result event says
    # subtype "success" while is_error is true -- anything keying on subtype calls this a good run.
    # A real auth failure exits non-zero (probed: exit=1); pass that through so the returncode gate
    # doesn't mask it.
    assistant = '{"type":"assistant","error":"authentication_failed"}'
    result = '{"type":"result","subtype":"success","is_error":true,"result":"Not logged in \\u00b7 Please run /login"}'
    check(clean_room.is_auth_failure(assistant, returncode=1), "detects error=authentication_failed")
    check(clean_room.is_auth_failure(result, returncode=1), "detects the 'Not logged in' result text")
    check(clean_room.is_auth_failure(assistant + "\n" + result, returncode=1), "detects it in a full trace")


def test_is_auth_failure_does_not_fire_on_a_healthy_trace() -> None:
    healthy = (
        '{"type":"system","subtype":"init","tools":["Skill","Task"]}\n'
        '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Skill",'
        '"input":{"skill":"sde-ladder"}}]}}\n'
        '{"type":"result","subtype":"success","is_error":false,"result":"done"}'
    )
    check(not clean_room.is_auth_failure(healthy, returncode=0), "no false positive on a healthy trace")


def test_is_auth_failure_is_gated_on_exit_code_not_just_text() -> None:
    # This is an SRE fleet: a perfectly healthy response can legitimately quote a log line or an
    # incident narrative containing "Not logged in" (Splunk triage, an auth-incident postmortem).
    # Flagging that as a fatal auth failure would abort the whole suite over normal fleet output --
    # a false fatal, as bad as the fail-open this module exists to close. A healthy run exits 0, no
    # matter what words are in it, so rc=0 must never be treated as an auth failure.
    healthy_but_mentions_the_marker = (
        '{"type":"system","subtype":"init","tools":["Skill","Task"]}\n'
        '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Skill",'
        '"input":{"skill":"sde-ladder"}}]}}\n'
        '{"type":"result","subtype":"success","is_error":false,'
        '"result":"the log shows: Not logged in \\u00b7 Please run /login"}'
    )
    check(
        not clean_room.is_auth_failure(healthy_but_mentions_the_marker, returncode=0),
        "a healthy (rc=0) trace that quotes 'Not logged in' in its own text is NOT flagged",
    )


def test_run_evals_aborts_on_auth_failure_instead_of_grading_the_error_string() -> None:
    import subprocess
    import unittest.mock as mock

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import run_evals  # noqa: E402

    fake = subprocess.CompletedProcess(
        args=[], returncode=1, stdout="Not logged in · Please run /login", stderr="",
    )
    scenario = {"mode": "direct", "target": {"kind": "skill", "name": "root-cause"}, "prompt": "hi"}
    with mock.patch.object(run_evals.subprocess, "run", return_value=fake) as m:
        try:
            run_evals.run_agent(
                scenario, env={"CLAUDE_CONFIG_DIR": "/tmp/room"}, cwd=Path.cwd(),
                timeout=10, model=None, claude_bin="claude",
            )
            check(False, "auth failure must raise, NOT return a string for the graders to score")
        except run_evals.InconclusiveTrial as exc:
            check(True, "run_agent raises an inconclusive trial instead of returning an auth error string")
            check(exc.returncode == 1 and bool(exc.raw_trace),
                  "auth inconclusive retains return code and raw trace")
            check(exc.duration_seconds is not None and bool(exc.command),
                  "auth inconclusive retains duration and exact argv")
    kwargs = m.call_args.kwargs
    check((kwargs.get("env") or {}).get("CLAUDE_CONFIG_DIR") == "/tmp/room",
          "run_agent passes the clean env to subprocess.run")


def test_run_evals_raises_runner_failed_on_a_non_auth_nonzero_exit() -> None:
    """[P0] A broken runner (rate limit, 5xx, bad flag — anything that is NOT an auth failure) must
    raise RunnerFailed, never fall through to `return f"[runner error ...]"` where it would be handed
    to the TEXT graders and scored as a plausible-looking scenario FAILURE."""
    import subprocess
    import unittest.mock as mock

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import run_evals  # noqa: E402

    fake = subprocess.CompletedProcess(
        args=[], returncode=1, stdout="", stderr="upstream 529: overloaded, try again later",
    )
    scenario = {"mode": "direct", "target": {"kind": "skill", "name": "root-cause"}, "prompt": "hi"}
    with mock.patch.object(run_evals.subprocess, "run", return_value=fake):
        try:
            result = run_evals.run_agent(
                scenario, env={"CLAUDE_CONFIG_DIR": "/tmp/room"}, cwd=Path.cwd(),
                timeout=10, model=None, claude_bin="claude",
            )
            check(False, f"non-auth runner failure must raise RunnerFailed, not return {result!r}")
        except clean_room.AuthUnavailable:
            check(False, "a non-auth failure must NOT be misclassified as AuthUnavailable")
        except clean_room.RunnerFailed as e:
            check("529" in str(e) or "overloaded" in str(e), "RunnerFailed carries the runner's own error text")


def main() -> int:
    tests = [
        test_clean_env_copies_only_the_credentials,
        test_clean_env_is_removed_even_when_the_body_raises,
        test_missing_credentials_raises_instead_of_running,
        test_api_key_auth_bypasses_the_credentials_file_requirement,
        test_neutral_workspace_is_empty_outside_the_repository_and_removed,
        test_is_auth_failure_recognises_a_real_not_logged_in_trace,
        test_is_auth_failure_does_not_fire_on_a_healthy_trace,
        test_is_auth_failure_is_gated_on_exit_code_not_just_text,
        test_run_evals_aborts_on_auth_failure_instead_of_grading_the_error_string,
        test_run_evals_raises_runner_failed_on_a_non_auth_nonzero_exit,
    ]
    for t in tests:
        t()
    passed = sum(1 for ok, _ in _results if ok)
    total = len(_results)
    print(f"\ntest_clean_room: {passed}/{total} checks passed.")
    if passed != total:
        print("FAILED")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
