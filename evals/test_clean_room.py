#!/usr/bin/env python3
"""Tests for evals/clean_room.py.

The clean room is what makes an eval number a property of the FLEET rather than of the machine it
ran on. These tests hold it to two things: it isolates, and it REFUSES rather than producing a
measurement it cannot stand behind.

Runnable:
    python3 evals/test_clean_room.py
"""
from __future__ import annotations

import contextlib
import os
import sys
import tempfile
import unittest.mock as mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import clean_room  # noqa: E402

_results: list[tuple[bool, str]] = []
EVAL_PROFILE_ENV = "SAVE_TOOLKIT_CLAUDE_EVAL_CONFIG_DIR"
EVAL_PROFILE_LOCK = ".save-toolkit-eval.lock"


def check(cond: bool, label: str) -> None:
    _results.append((bool(cond), label))
    print(f"  [{'PASS' if cond else 'FAIL'}] {label}")


@contextlib.contextmanager
def _temporary_environment(**updates: str | None):
    previous = {key: os.environ.get(key) for key in updates}
    try:
        for key, value in updates.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _fake_home(tmp: Path) -> Path:
    """A config dir that looks logged-in, plus the junk a real one carries."""
    cfg = tmp / "cfg"
    (cfg / "skills" / "eng-ladder").mkdir(parents=True)
    (cfg / "agents").mkdir(parents=True)
    (cfg / "plugins").mkdir(parents=True)
    (cfg / "CLAUDE.md").write_text("personal instructions\n", encoding="utf-8")
    (cfg / clean_room.CREDENTIALS).write_text('{"token": "secret"}', encoding="utf-8")
    return cfg


def _fake_eval_profile(tmp: Path) -> Path:
    cfg = tmp / "eval-profile"
    cfg.mkdir()
    (cfg / clean_room.CREDENTIALS).write_text('{"token": "secret"}', encoding="utf-8")
    return cfg


def test_oauth_requires_an_explicit_dedicated_eval_profile() -> None:
    with tempfile.TemporaryDirectory() as td:
        personal = _fake_home(Path(td))
        with _temporary_environment(
            CLAUDE_CONFIG_DIR=str(personal),
            SAVE_TOOLKIT_CLAUDE_EVAL_CONFIG_DIR=None,
            ANTHROPIC_API_KEY=None,
            ANTHROPIC_AUTH_TOKEN=None,
        ):
            try:
                with clean_room.clean_env():
                    check(False, "ambient OAuth credentials must NOT be copied into an eval batch")
            except clean_room.AuthUnavailable as exc:
                check(EVAL_PROFILE_ENV in str(exc), "the refusal names the dedicated-profile setting")
                check("API key" not in str(exc) or "not required" in str(exc),
                      "the refusal does not present an API key as a prerequisite")


def test_oauth_uses_one_persistent_profile_and_serializes_batches() -> None:
    with tempfile.TemporaryDirectory() as td:
        cfg = _fake_eval_profile(Path(td))
        with _temporary_environment(
            CLAUDE_CONFIG_DIR=str(Path(td) / "personal-profile-must-not-be-used"),
            SAVE_TOOLKIT_CLAUDE_EVAL_CONFIG_DIR=str(cfg),
            ANTHROPIC_API_KEY=None,
            ANTHROPIC_AUTH_TOKEN=None,
        ):
            with clean_room.clean_env() as env:
                room = Path(env["CLAUDE_CONFIG_DIR"])
                check(room.resolve() == cfg.resolve(),
                      "OAuth uses the dedicated profile directly so refreshed credentials persist")
                check((cfg / EVAL_PROFILE_LOCK).is_file(), "the profile is locked for the whole batch")
                (room / clean_room.CREDENTIALS).write_text('{"token": "refreshed"}', encoding="utf-8")
                try:
                    with clean_room.clean_env():
                        check(False, "a concurrent batch must NOT reuse the rotating OAuth profile")
                except clean_room.AuthUnavailable as exc:
                    check("already in use" in str(exc), "concurrent reuse fails with an actionable reason")
            check((cfg / clean_room.CREDENTIALS).read_text(encoding="utf-8") == '{"token": "refreshed"}',
                  "a child credential refresh survives the batch")
            check(not (cfg / EVAL_PROFILE_LOCK).exists(), "the batch lock is removed on normal exit")


def test_oauth_profile_lock_is_removed_even_when_the_body_raises() -> None:
    with tempfile.TemporaryDirectory() as td:
        cfg = _fake_eval_profile(Path(td))
        with _temporary_environment(
            SAVE_TOOLKIT_CLAUDE_EVAL_CONFIG_DIR=str(cfg),
            ANTHROPIC_API_KEY=None,
            ANTHROPIC_AUTH_TOKEN=None,
        ):
            try:
                with clean_room.clean_env():
                    raise RuntimeError("boom")
            except RuntimeError:
                pass
            check(cfg.is_dir(), "the persistent eval profile survives an exception")
            check(not (cfg / EVAL_PROFILE_LOCK).exists(), "the batch lock is removed on exception")


def test_oauth_profile_rejects_behavior_bearing_configuration() -> None:
    with tempfile.TemporaryDirectory() as td:
        cfg = _fake_eval_profile(Path(td))
        (cfg / "skills").mkdir()
        with _temporary_environment(
            SAVE_TOOLKIT_CLAUDE_EVAL_CONFIG_DIR=str(cfg),
            ANTHROPIC_API_KEY=None,
            ANTHROPIC_AUTH_TOKEN=None,
        ):
            try:
                with clean_room.clean_env():
                    check(False, "a profile containing personal skills must NOT enter the clean room")
            except clean_room.AuthUnavailable as exc:
                check("behavior-bearing" in str(exc), "the refusal identifies profile contamination")


def test_oauth_profile_rejects_the_personal_default_even_when_explicit() -> None:
    with tempfile.TemporaryDirectory() as td:
        personal = _fake_eval_profile(Path(td))
        with (
            _temporary_environment(
                SAVE_TOOLKIT_CLAUDE_EVAL_CONFIG_DIR=str(personal),
                ANTHROPIC_API_KEY=None,
                ANTHROPIC_AUTH_TOKEN=None,
            ),
            mock.patch.object(clean_room, "default_user_config_dir", return_value=personal),
        ):
            try:
                with clean_room.clean_env():
                    check(False, "the personal default profile must NOT become an eval profile")
            except clean_room.AuthUnavailable as exc:
                check("personal default profile" in str(exc), "explicit ambient-profile reuse fails closed")


def test_oauth_profile_rejects_a_path_inside_the_repository() -> None:
    with tempfile.TemporaryDirectory() as td:
        fake_repo = Path(td) / "repository"
        fake_repo.mkdir()
        cfg = _fake_eval_profile(fake_repo)
        with _temporary_environment(
            FLEET_ROOT=str(fake_repo),
            SAVE_TOOLKIT_CLAUDE_EVAL_CONFIG_DIR=str(cfg),
            ANTHROPIC_API_KEY=None,
            ANTHROPIC_AUTH_TOKEN=None,
        ):
            try:
                with clean_room.clean_env():
                    check(False, "an OAuth credential profile must NOT live inside the repository")
            except clean_room.AuthUnavailable as exc:
                check("outside the repository" in str(exc), "the refusal prevents committing credentials")


def test_missing_credentials_raises_instead_of_running() -> None:
    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td) / "cfg"
        cfg.mkdir()  # exists, but no credentials
        with _temporary_environment(
            SAVE_TOOLKIT_CLAUDE_EVAL_CONFIG_DIR=str(cfg),
            ANTHROPIC_API_KEY=None,
            ANTHROPIC_AUTH_TOKEN=None,
        ):
            try:
                with clean_room.clean_env():
                    check(False, "clean_env must NOT yield without credentials")
            except clean_room.AuthUnavailable as e:
                check("no Claude credentials" in str(e), "AuthUnavailable names the problem")
                check("no-route" in str(e),
                      "the error explains WHY this is fatal (else it reads as a fake finding)")


def test_api_key_auth_bypasses_the_credentials_file_requirement() -> None:
    """[P2] ANTHROPIC_API_KEY (or Bedrock/Vertex) operators have NO ~/.claude/.credentials.json --
    not a missing one, a nonexistent concept -- yet `claude -p` works for them. clean_env() must not
    refuse them; it should skip the credential copy and still yield full isolation (empty temp dir)."""
    with tempfile.TemporaryDirectory() as td:
        cfg = Path(td) / "cfg"
        cfg.mkdir()  # exists, but no credentials -- would normally raise AuthUnavailable
        with _temporary_environment(
            CLAUDE_CONFIG_DIR=str(cfg),
            SAVE_TOOLKIT_CLAUDE_EVAL_CONFIG_DIR=None,
            ANTHROPIC_API_KEY="sk-test-not-a-real-key",
            ANTHROPIC_AUTH_TOKEN=None,
            GITHUB_TOKEN="must-not-reach-model-tools",
        ):
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


def test_current_docs_name_the_refresh_safe_no_key_contract() -> None:
    readme = (Path(__file__).resolve().parent / "README.md").read_text(encoding="utf-8")
    agents = (Path(__file__).resolve().parent.parent / "AGENTS.md").read_text(encoding="utf-8")
    roadmap = (
        Path(__file__).resolve().parent.parent / "docs" / "fleet-roadmap.md"
    ).read_text(encoding="utf-8")
    for document, name in ((readme, "eval guide"), (agents, "fleet guide"), (roadmap, "roadmap")):
        check(EVAL_PROFILE_ENV in document, f"{name} names the dedicated Claude eval profile")
        check("no API key is required" in document, f"{name} says subscription OAuth needs no API key")
    check("claude auth login" in readme, "eval guide gives the subscription login command")
    check("must not run in parallel" in readme, "eval guide explains the rotating-token concurrency rule")


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
    check(
        clean_room.is_auth_failure(
            "Failed to authenticate: OAuth session expired and could not be refreshed",
            returncode=1,
        ),
        "detects the observed OAuth refresh failure even without stream-json metadata",
    )


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
        test_oauth_requires_an_explicit_dedicated_eval_profile,
        test_oauth_uses_one_persistent_profile_and_serializes_batches,
        test_oauth_profile_lock_is_removed_even_when_the_body_raises,
        test_oauth_profile_rejects_behavior_bearing_configuration,
        test_oauth_profile_rejects_the_personal_default_even_when_explicit,
        test_oauth_profile_rejects_a_path_inside_the_repository,
        test_missing_credentials_raises_instead_of_running,
        test_api_key_auth_bypasses_the_credentials_file_requirement,
        test_current_docs_name_the_refresh_safe_no_key_contract,
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
