"""Opt-in Linux filesystem boundary for WP04's native read-only Claude profile.

Use as build_probe --executable "<python> <absolute path to this file>".
Only the staged fixture, staged plugin, temporary CLI config, system runtime and
resolved CLI binary are mounted. Network remains available for Claude's service.
The host disables candidate hooks, inline skill commands and plugin MCP servers;
restricted mode confines model file tools to the staged inputs.
This is a separate Linux runtime profile, not Windows acceptance evidence.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

TOOLS = {"Read", "Grep", "Glob", "Skill"}
VALUE_FLAGS = {
    "--agent",
    "-p",
    "--output-format",
    "--plugin-dir",
    "--mcp-config",
    "--settings",
    "--tools",
    "--disallowedTools",
    "--add-dir",
    "--allowedTools",
    "--permission-mode",
    "--model",
    "--max-turns",
    "--max-budget-usd",
}
SWITCHES = {"--verbose", "--forward-subagent-text", "--strict-mcp-config", "--no-session-persistence"}


def validate_profile(args: list[str], cwd: Path, config: Path) -> Path:
    values: dict[str, str] = {}
    seen: set[str] = set()
    index = 0
    while index < len(args):
        flag = args[index]
        if flag in seen or flag not in VALUE_FLAGS | SWITCHES:
            raise ValueError("unknown or repeated CLI option")
        seen.add(flag)
        if flag in VALUE_FLAGS:
            index += 1
            if index == len(args):
                raise ValueError("missing CLI option value")
            values[flag] = args[index]
        index += 1
    if values.get("--agent", "").split(":")[-1] != "sre-assistant":
        raise ValueError("only the WP04 sre-assistant profile is admitted")
    if set(values.get("--tools", "").split(",")) != TOOLS:
        raise ValueError("only Read/Grep/Glob/Skill are admitted")
    if "--allowedTools" in values and set(values["--allowedTools"].split(",")) != TOOLS:
        raise ValueError("tool approvals differ from the read-only profile")
    if values.get("--permission-mode", "dontAsk") != "dontAsk":
        raise ValueError("only the noninteractive profile is admitted")
    if "--mcp-config" in values and json.loads(values["--mcp-config"]) != {"mcpServers": {}}:
        raise ValueError("external MCP servers are not admitted")
    if "--settings" in values and json.loads(values["--settings"]) != {"syncClaudeAiSkills": False}:
        raise ValueError("unexpected CLI settings")
    plugin = Path(values.get("--plugin-dir", "")).resolve(strict=True)
    if cwd.resolve() != plugin.parent / "repo" or plugin.name != "plugin":
        raise ValueError("expected sibling staged repo and plugin directories")
    if "--add-dir" in values and Path(values["--add-dir"]).resolve() != plugin:
        raise ValueError("additional host paths are not admitted")
    if not config.is_dir() or config.resolve().is_relative_to(plugin.parent):
        raise ValueError("temporary CLI config must be separate from staged inputs")
    if config.is_symlink() or any(
        p.is_symlink() or p.name != ".credentials.json" or not p.is_file() for p in config.iterdir()
    ):
        raise ValueError("CLI config must contain only the clean-room credential copy")
    return plugin


def namespace_command(command: list[str], cwd: Path, plugin: Path, config: Path) -> list[str]:
    if sys.platform != "linux" or not shutil.which("bwrap"):
        raise ValueError("this profile requires Linux bubblewrap")
    executable = Path(command[0]).resolve(strict=True)
    if not executable.is_file():
        raise ValueError("CLI executable is not a regular file")
    argv = [
        "bwrap",
        "--die-with-parent",
        "--new-session",
        "--unshare-user",
        "--unshare-pid",
        "--unshare-ipc",
        "--unshare-uts",
        "--cap-drop",
        "ALL",
    ]
    for name in ("/usr", "/lib", "/lib64"):
        if Path(name).exists():
            argv += ["--ro-bind", name, name]
    argv += ["--symlink", "usr/bin", "/bin", "--proc", "/proc", "--dev", "/dev", "--tmpfs", "/tmp"]
    for name in ("TMP", "TEMP", "TMPDIR"):
        argv += ["--setenv", name, "/tmp"]
    for name in ("/etc/ssl", "/etc/resolv.conf", "/etc/hosts", "/etc/nsswitch.conf"):
        if Path(name).exists():
            argv += ["--ro-bind", name, name]
    home = str(Path.home())
    argv += ["--dir", home, "--setenv", "HOME", home, "--setenv", "PATH", "/usr/bin:/bin"]
    if not executable.is_relative_to("/usr"):
        argv += ["--ro-bind", str(executable), str(executable)]
    for path in (cwd, plugin):
        resolved = str(path.resolve(strict=True))
        argv += ["--ro-bind", resolved, resolved]
    resolved_config = str(config.resolve(strict=True))
    argv += ["--bind", resolved_config, resolved_config, "--setenv", "CLAUDE_CONFIG_DIR", resolved_config]
    return [*argv, "--chdir", str(cwd.resolve()), "--", str(executable), *command[1:]]


def claude_command(executable: str, args: list[str], cwd: Path, config: Path) -> list[str]:
    """Admit the profile, then enforce host-owned controls before any plugin loads.

    Do not remove or rewrite candidate files: their measured bytes stay intact.
    These launch controls are specific to WP04, whose model has no command tools.
    """
    plugin = validate_profile(args, cwd, config)
    admitted = list(args)
    positions = {}
    index = 0
    while index < len(args):
        flag = args[index]
        positions[flag] = index + 1
        index += 2 if flag in VALUE_FLAGS else 1
    settings = {"syncClaudeAiSkills": False, "disableAllHooks": True, "disableSkillShellExecution": True}
    for flag, value in (
        ("--settings", json.dumps(settings)),
        ("--mcp-config", '{"mcpServers":{}}'),
        ("--add-dir", str(plugin)),
        ("--allowedTools", ",".join(sorted(TOOLS))),
        ("--permission-mode", "dontAsk"),
    ):
        if flag in positions:
            admitted[positions[flag]] = value
        else:
            admitted += [flag, value]
    if "--strict-mcp-config" not in positions:
        admitted.append("--strict-mcp-config")
    admitted.append("--restricted")
    return namespace_command([executable, *admitted], cwd, plugin, config)


def main() -> int:
    executable = shutil.which("claude")
    if executable is None:
        print("WP04 Linux boundary: Claude CLI unavailable", file=sys.stderr)
        return 3
    args = sys.argv[1:]
    if args == ["--version"]:
        version = subprocess.run([executable, "--version"], capture_output=True, text=True, check=False)
        bwrap = shutil.which("bwrap")
        if version.returncode or bwrap is None:
            return 3
        boundary = subprocess.run([bwrap, "--version"], capture_output=True, text=True, check=False)
        if boundary.returncode:
            return 3
        source = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        binary = hashlib.sha256(Path(executable).resolve().read_bytes()).hexdigest()
        print(f"{version.stdout.strip()}; {boundary.stdout.strip()}; wp04-linux={source}; cli-binary={binary}")
        return 0
    try:
        configured = os.environ.get("CLAUDE_CONFIG_DIR")
        if not configured:
            raise ValueError("temporary clean-room CLI config is required")
        cwd, config = Path.cwd(), Path(configured)
        command = claude_command(executable, args, cwd, config)
        # No child credential/content output is inspected or copied here. The
        # runner owns stdout/stderr evidence and process-group cancellation.
        os.execvp(command[0], command)
    except (OSError, ValueError) as exc:
        print(f"WP04 Linux boundary refused: {exc}", file=sys.stderr)
        return 3
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
