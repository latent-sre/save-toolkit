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
import shutil
import subprocess
from pathlib import Path
from unittest import mock

import clean_room
import pytest

AUTH_SELECTORS = (*clean_room.API_KEY_ENV_VARS, *clean_room.CLOUD_AUTH_SELECTORS)


def claude_env(**values: str):
    """The caller's environment without Claude auth selectors, plus `values`; restored on exit."""
    kept = {name: value for name, value in os.environ.items() if name not in AUTH_SELECTORS}
    return mock.patch.dict(os.environ, {**kept, **values}, clear=True)


def _fake_home(tmp: Path) -> Path:
    """A config dir that looks logged-in, plus the junk a real one carries."""
    cfg = tmp / "cfg"
    (cfg / "skills" / "eng-ladder").mkdir(parents=True)
    (cfg / "agents").mkdir(parents=True)
    (cfg / "plugins").mkdir(parents=True)
    (cfg / "CLAUDE.md").write_text("personal instructions\n", encoding="utf-8")
    (cfg / clean_room.CREDENTIALS).write_text('{"token": "secret"}', encoding="utf-8")
    return cfg


def test_clean_env_copies_only_the_credentials(tmp_path) -> None:
    with claude_env(CLAUDE_CONFIG_DIR=str(_fake_home(tmp_path))), clean_room.clean_env() as env:
        room = Path(env["CLAUDE_CONFIG_DIR"])
        names = sorted(p.name for p in room.iterdir())
        # Personal skills, agents, plugins and CLAUDE.md are therefore NOT visible.
        assert names == [clean_room.CREDENTIALS], f"clean room holds ONLY the credentials (got {names})"
        assert (room / clean_room.CREDENTIALS).read_text(encoding="utf-8") == '{"token": "secret"}', \
            "credentials were copied, not fabricated"


def test_clean_env_is_removed_even_when_the_body_raises(tmp_path) -> None:
    # match: AuthUnavailable is a RuntimeError too, and a refusal must surface as itself.
    with claude_env(CLAUDE_CONFIG_DIR=str(_fake_home(tmp_path))), pytest.raises(RuntimeError, match="boom"), \
            clean_room.clean_env() as env:
        room = Path(env["CLAUDE_CONFIG_DIR"])
        raise RuntimeError("boom")
    assert not room.exists(), "the temp dir (which held an auth secret) is removed on exception"


def test_missing_credentials_raises_instead_of_running(tmp_path) -> None:
    # tmp_path exists, but holds no credentials.
    with claude_env(CLAUDE_CONFIG_DIR=str(tmp_path)), pytest.raises(clean_room.AuthUnavailable) as refused, \
            clean_room.clean_env():
        pytest.fail("clean_env must NOT yield without credentials")
    assert "no Claude credentials" in str(refused.value), "AuthUnavailable names the problem"
    assert "no-route" in str(refused.value), "the error explains WHY this is fatal (else it reads as a fake finding)"


def test_api_key_auth_bypasses_the_credentials_file_requirement(tmp_path) -> None:
    """[P2] ANTHROPIC_API_KEY (or Bedrock/Vertex) operators have NO ~/.claude/.credentials.json --
    not a missing one, a nonexistent concept -- yet `claude -p` works for them. clean_env() must not
    refuse them; it should skip the credential copy and still yield full isolation (empty temp dir)."""
    # tmp_path holds no credentials, which would normally raise AuthUnavailable.
    with claude_env(CLAUDE_CONFIG_DIR=str(tmp_path), ANTHROPIC_API_KEY="sk-test-not-a-real-key",
                    GITHUB_TOKEN="must-not-reach-model-tools"), clean_room.clean_env() as env:
        room = Path(env["CLAUDE_CONFIG_DIR"])
        assert room.is_dir(), "clean_env yields a temp dir even with no credentials file"
        assert list(room.iterdir()) == [], "the temp dir is empty -- no credentials to copy"
        assert env.get("ANTHROPIC_API_KEY") == "sk-test-not-a-real-key", \
            "the selected Claude authentication variable is retained"
        assert "GITHUB_TOKEN" not in env, "unrelated host secrets are scrubbed from the child env"
        assert env.get("PATH"), "the executable PATH is retained"


def test_subscriber_only_clean_env_rejects_api_key_auth(tmp_path) -> None:
    with claude_env(CLAUDE_CONFIG_DIR=str(_fake_home(tmp_path)), ANTHROPIC_API_KEY="must-not-be-used"), \
            pytest.raises(clean_room.AuthUnavailable, match="subscriber"), \
            clean_room.clean_env(subscriber_only=True):
        pytest.fail("subscriber-only clean_env must reject API key auth")


def test_neutral_workspace_is_empty_outside_the_repository_and_removed() -> None:
    with clean_room.neutral_workspace() as workspace:
        assert workspace.is_dir(), "neutral workspace exists during the trial"
        assert sorted(path.name for path in workspace.iterdir()) == [".git"], \
            "neutral workspace contains only its git-root boundary"
        assert not workspace.is_relative_to(Path.cwd()), "neutral workspace is outside the plugin repository"
        top = subprocess.run(
            ["git", "-C", str(workspace), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=True, encoding="utf-8", timeout=60,
        ).stdout.strip()
        assert Path(top).resolve() == workspace.resolve(), "neutral workspace is its own git root"
    assert not workspace.exists(), "neutral workspace is removed after the trial"


def test_instruction_bearing_ancestor_finds_the_nearest_file_above_a_workspace() -> None:
    """The walk that leaked: Claude reads CLAUDE.md from ANY ancestor, not just the cwd.

    The tree is built under workspace_root() rather than the default temp dir, because on Windows
    the default temp dir is exactly what is contaminated -- basing the "clean chain" case there
    fails for the reason this fix exists, as it did on the first run of this test.
    """
    tmp = clean_room.make_workspace("detector-test-")
    try:
        deep = tmp / "a" / "b" / "c"
        deep.mkdir(parents=True)
        assert clean_room.instruction_bearing_ancestor(deep) is None, \
            "a clean chain under workspace_root() reports no instruction ancestor"

        far = tmp / "a" / "CLAUDE.md"
        far.write_text("personal rules\n", encoding="utf-8")
        assert clean_room.instruction_bearing_ancestor(deep) == far, "an ancestor CLAUDE.md two levels up is found"

        near = tmp / "a" / "b" / ".claude"
        near.mkdir()
        (near / "CLAUDE.md").write_text("nearer rules\n", encoding="utf-8")
        assert clean_room.instruction_bearing_ancestor(deep) == near / "CLAUDE.md", \
            "the NEAREST instruction file wins, including the .claude/CLAUDE.md form"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_instruction_bearing_ancestor_finds_hidden_agents_md_and_rules() -> None:
    """Claude Code also loads .claude/AGENTS.md and .claude/rules/**/*.md from every ancestor."""
    for relative in (Path(".claude") / "AGENTS.md", Path(".claude") / "rules" / "team" / "style.md"):
        tmp = clean_room.make_workspace("detector-hidden-test-")
        try:
            deep = tmp / "a" / "b"
            deep.mkdir(parents=True)
            planted = tmp / "a" / relative
            planted.parent.mkdir(parents=True)
            planted.write_text("inherited instructions\n", encoding="utf-8")
            assert clean_room.instruction_bearing_ancestor(deep) == planted, \
                f"an ancestor {relative.as_posix()} is found when it is the only instruction source"
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def test_instruction_bearing_ancestor_finds_an_ancestor_claude_local_md() -> None:
    """Claude Code loads CLAUDE.local.md, not only CLAUDE.md, from every directory above the cwd."""
    tmp = clean_room.make_workspace("detector-local-test-")
    try:
        deep = tmp / "a" / "b"
        deep.mkdir(parents=True)
        local = tmp / "a" / "CLAUDE.local.md"
        local.write_text("personal project notes\n", encoding="utf-8")
        assert clean_room.instruction_bearing_ancestor(deep) == local, \
            "an ancestor CLAUDE.local.md is found when it is the only instruction file"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_workspace_root_refuses_a_contaminated_override(tmp_path) -> None:
    """A refusal, not a silent measurement: the harness's rule applied to its own workspace."""
    tmp = tmp_path.resolve()
    (tmp / "CLAUDE.md").write_text("personal rules\n", encoding="utf-8")
    target = tmp / "workspaces"
    target.mkdir()
    with mock.patch.dict(os.environ, {clean_room.WORKSPACE_ROOT_ENV: str(target)}), \
            pytest.raises(clean_room.RunnerFailed) as refused:
        clean_room.workspace_root()
    # A contaminated workspace root is refused, naming the file and the override.
    assert "CLAUDE.md" in str(refused.value)
    assert clean_room.WORKSPACE_ROOT_ENV in str(refused.value)


def test_make_workspace_has_no_instruction_bearing_ancestor() -> None:
    """The guarantee itself, on whatever root this host resolves to.

    This is the check that was missing: on Windows the default temp root sits under the operator's
    home, so every trial inherited ~/.claude/CLAUDE.md and the number measured the operator, not
    the plugin.
    """
    workspace = clean_room.make_workspace("test-workspace-")
    try:
        offender = clean_room.instruction_bearing_ancestor(workspace)
        assert offender is None, f"{workspace} would inherit {offender}"
    finally:
        workspace.rmdir()


def test_is_auth_failure_recognises_a_real_not_logged_in_trace() -> None:
    # Verbatim shapes from a probed credential-less run. Note the trap: the result event says
    # subtype "success" while is_error is true -- anything keying on subtype calls this a good run.
    # A real auth failure exits non-zero (probed: exit=1); pass that through so the returncode gate
    # doesn't mask it.
    assistant = '{"type":"assistant","error":"authentication_failed"}'
    result = '{"type":"result","subtype":"success","is_error":true,"result":"Not logged in \\u00b7 Please run /login"}'
    assert clean_room.is_auth_failure(assistant, returncode=1), "detects error=authentication_failed"
    assert clean_room.is_auth_failure(result, returncode=1), "detects the 'Not logged in' result text"
    assert clean_room.is_auth_failure(assistant + "\n" + result, returncode=1), "detects it in a full trace"


def test_is_auth_failure_does_not_fire_on_a_healthy_trace() -> None:
    healthy = (
        '{"type":"system","subtype":"init","tools":["Skill","Task"]}\n'
        '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Skill",'
        '"input":{"skill":"sde-ladder"}}]}}\n'
        '{"type":"result","subtype":"success","is_error":false,"result":"done"}'
    )
    assert not clean_room.is_auth_failure(healthy, returncode=0), "no false positive on a healthy trace"


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
    assert not clean_room.is_auth_failure(healthy_but_mentions_the_marker, returncode=0), \
        "a healthy (rc=0) trace that quotes 'Not logged in' in its own text is NOT flagged"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
