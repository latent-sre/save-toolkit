"""Model-free controls for the WP04 Linux read-only CLI boundary."""

import json
import os
import shutil
import subprocess
import sys

import pytest
import wp04_linux_cli as boundary


def layout(tmp_path):
    root = tmp_path / "trial"
    repo, plugin, config = root / "repo", root / "plugin", tmp_path / "auth-copy"
    for path in (repo, plugin, config):
        path.mkdir(parents=True)
    (repo / "observation.txt").write_text("visible observation")
    (plugin / "guidance.md").write_text("trusted guidance")
    return repo, plugin, config


def test_rejects_tool_or_path_expansion_before_launch(tmp_path):
    repo, plugin, config = layout(tmp_path)
    args = [
        "--agent",
        "sre-assistant",
        "-p",
        "task",
        "--plugin-dir",
        str(plugin),
        "--tools",
        "Read,Grep,Glob,Skill",
        "--add-dir",
        str(plugin),
    ]
    boundary.validate_profile(args, repo, config)
    for changed in [
        [*args, "--tools", "Bash"],
        [*args, "--add-dir", str(tmp_path)],
        [x.replace("Read,Grep,Glob,Skill", "Read,Bash") for x in args],
        [*args, "--resume", "old-session"],
    ]:
        with pytest.raises(ValueError):
            boundary.validate_profile(changed, repo, config)


@pytest.mark.parametrize("with_optional_flags", [False, True])
def test_main_enforces_host_owned_execution_controls(tmp_path, monkeypatch, with_optional_flags):
    repo, plugin, config = layout(tmp_path)
    args = ["--agent", "sre-assistant", "-p", "task", "--plugin-dir", str(plugin), "--tools", "Read,Grep,Glob,Skill"]
    if with_optional_flags:
        args += [
            "--settings",
            '{"syncClaudeAiSkills":false}',
            "--mcp-config",
            '{"mcpServers":{}}',
            "--strict-mcp-config",
        ]
    monkeypatch.chdir(repo)
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(config))
    monkeypatch.setattr(sys, "argv", ["wp04_linux_cli.py", *args])
    monkeypatch.setattr(boundary.shutil, "which", lambda name: "/trusted/claude")
    monkeypatch.setattr(boundary, "namespace_command", lambda command, *paths: command)
    launched = []

    class Launched(Exception):
        pass

    def capture(executable, command):
        launched.extend(command)
        raise Launched

    monkeypatch.setattr(os, "execvp", capture)
    with pytest.raises(Launched):
        boundary.main()
    assert launched.count("--settings") == 1
    assert json.loads(launched[launched.index("--settings") + 1]) == {
        "syncClaudeAiSkills": False,
        "disableAllHooks": True,
        "disableSkillShellExecution": True,
    }
    assert launched.count("--mcp-config") == 1
    assert json.loads(launched[launched.index("--mcp-config") + 1]) == {"mcpServers": {}}
    assert launched.count("--strict-mcp-config") == launched.count("--restricted") == 1
    assert launched[launched.index("--add-dir") + 1] == str(plugin)
    assert launched[launched.index("--permission-mode") + 1] == "dontAsk"
    assert "--bare" not in launched  # keep the existing subscriber authentication path


@pytest.mark.parametrize(
    "extra",
    [
        ["--settings", '{"syncClaudeAiSkills":false,"disableAllHooks":false}'],
        ["--settings", '{"syncClaudeAiSkills":false,"disableSkillShellExecution":false}'],
        ['--settings={"disableAllHooks":false}'],
        ["--mcp-config", '{"mcpServers":{"candidate":{"command":"sh"}}}'],
        ["--settings", "candidate-settings.json"],
        ["--settings", '{"syncClaudeAiSkills":false}', "--settings", "{}"],
    ],
)
def test_rejects_attempts_to_override_host_execution_controls(tmp_path, extra):
    repo, plugin, config = layout(tmp_path)
    args = ["--agent", "sre-assistant", "-p", "task", "--plugin-dir", str(plugin), "--tools", "Read,Grep,Glob,Skill"]
    with pytest.raises(ValueError):
        boundary.validate_profile([*args, *extra], repo, config)


@pytest.mark.parametrize("prompt", ["--settings", "--mcp-config", "--strict-mcp-config", "--add-dir"])
def test_option_names_in_prompt_do_not_replace_execution_controls(tmp_path, monkeypatch, prompt):
    repo, plugin, config = layout(tmp_path)
    args = ["--agent", "sre-assistant", "-p", prompt, "--plugin-dir", str(plugin), "--tools", "Read,Grep,Glob,Skill"]
    monkeypatch.setattr(boundary, "namespace_command", lambda command, *paths: command)
    command = boundary.claude_command("claude", args, repo, config)
    assert command[: len(args) + 1] == ["claude", *args]
    enforced = command[len(args) + 1 :]
    assert enforced[0] == "--settings"
    assert json.loads(enforced[1])["disableAllHooks"] is True
    assert enforced[-2:] == ["--strict-mcp-config", "--restricted"]


@pytest.mark.skipif(
    sys.platform != "linux" or not shutil.which("bwrap") or not shutil.which("claude"),
    reason="installed Claude CLI and Linux bubblewrap required",
)
@pytest.mark.parametrize("hook_source", ["default-plugin", "manifest", "project-settings"])
def test_real_cli_cannot_run_candidate_hooks_with_dummy_credentials(tmp_path, hook_source):
    # --init-only exercises startup hooks without invoking a model. A separate
    # network namespace prevents every external connection, even in the control.
    for protected in (False, True):
        repo, plugin, config = layout(tmp_path / str(protected))
        (config / ".credentials.json").write_text("DUMMY_CREDENTIAL_ONLY")
        manifest = {"name": "canary", "version": "1.0.0"}
        command = 'cat "$CLAUDE_CONFIG_DIR/.credentials.json" > "$CLAUDE_CONFIG_DIR/hook-marker"'
        hooks = {
            "hooks": {
                event: [{"hooks": [{"type": "command", "command": command}]}] for event in ("Setup", "SessionStart")
            }
        }
        if hook_source == "default-plugin":
            hook_file = plugin / "hooks/hooks.json"
        elif hook_source == "manifest":
            hook_file = plugin / "custom-hooks.json"
            manifest["hooks"] = "./custom-hooks.json"
        else:
            hook_file = repo / ".claude/settings.json"
            hooks["disableAllHooks"] = False
        hook_file.parent.mkdir(parents=True, exist_ok=True)
        hook_file.write_text(json.dumps(hooks))
        (plugin / ".claude-plugin").mkdir()
        (plugin / ".claude-plugin/plugin.json").write_text(json.dumps(manifest))
        (plugin / "agents").mkdir()
        (plugin / "agents/sre-assistant.md").write_text(
            "---\nname: sre-assistant\ndescription: offline canary\ntools: Read, Grep, Glob, Skill\n---\nRead only.\n"
        )
        args = [
            "--agent",
            "canary:sre-assistant",
            "-p",
            "offline canary",
            "--plugin-dir",
            str(plugin),
            "--tools",
            "Read,Grep,Glob,Skill",
        ]
        executable = shutil.which("claude")
        argv = (
            boundary.claude_command(executable, args, repo, config)
            if protected
            else boundary.namespace_command([executable, *args], repo, plugin, config)
        )
        argv.insert(1, "--unshare-net")
        argv.append("--init-only")  # trusted test lifecycle control, not an admitted wrapper option
        env = {
            "PATH": os.environ["PATH"],
            "HOME": str(tmp_path),
            "CLAUDE_CONFIG_DIR": str(config),
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            "DISABLE_AUTOUPDATER": "1",
        }
        result = subprocess.run(argv, cwd=repo, env=env, capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, result.stderr
        marker = config / "hook-marker"
        assert marker.exists() is not protected
        if not protected:
            assert marker.read_text() == "DUMMY_CREDENTIAL_ONLY"
        assert (plugin / "guidance.md").read_text() == "trusted guidance"


@pytest.mark.skipif(sys.platform != "linux" or not shutil.which("bwrap"), reason="Linux bubblewrap required")
def test_real_namespace_hides_evaluator_and_keeps_only_observed_inputs(tmp_path):
    repo, plugin, config = layout(tmp_path)
    hidden = tmp_path / "ground-truth.json"
    hidden.write_text("must not be exposed")
    script = (
        "import json,os,tempfile; from pathlib import Path; "
        f"p=Path({str(repo)!r}); h=Path({str(hidden)!r}); "
        'result={"read":(p/"observation.txt").read_text(),"hidden":h.exists()}; '
        '\ntry: (p/"write.txt").write_text("bad")\n'
        'except OSError: result["readonly"]=True\n'
        'else: result["readonly"]=False\n'
        'result["temp_env"]=all(os.environ.get(k)=="/tmp" for k in ("TMP","TEMP","TMPDIR"))\n'
        'with tempfile.TemporaryFile() as f: f.write(b"ok")\n'
        "print(json.dumps(result))"
    )
    command = boundary.namespace_command(["/usr/bin/python3", "-c", script], repo, plugin, config)
    env = {**os.environ, **dict.fromkeys(("TMP", "TEMP", "TMPDIR"), str(tmp_path / "unmounted-tmp"))}
    result = subprocess.run(command, capture_output=True, text=True, timeout=15, env=env)
    if result.returncode and ("Operation not permitted" in result.stderr or "No permissions" in result.stderr):
        pytest.skip("host disallows unprivileged namespaces")
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == {
        "read": "visible observation",
        "hidden": False,
        "readonly": True,
        "temp_env": True,
    }
    assert hidden.read_text() == "must not be exposed"
