#!/usr/bin/env python3
"""Prove disposable fleet install, inventory, authority boundary, and uninstall per host.

For each requested host the probe installs the fleet into an explicit, initially empty disposable
target, checks host-visible inventory, proves every write stayed inside the target and out of
user-owned configuration, then uninstalls and confirms no residue. It never writes to user-owned
plugin, agent, or settings locations, never provisions credentials, and never starts a model
session. An unavailable host is ``skip``; a CLI that cannot complete a verb is ``inconclusive``;
only a proven boundary violation or uninstall residue is ``fail``.

The Copilot CLI mirrors the Claude flow: a local-path marketplace registration, an explicit
plugin id install, an exact-row inventory check, and an uninstall verb, all against a
credential-free disposable HOME.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence

# Importing repository helpers must not create scripts/__pycache__ in a clean checkout.
sys.dont_write_bytecode = True

try:
    from scripts import (
        evidence_envelope,
        fleet_doctor,
        generate_platform_adapters,
        install_codex_agents,
        verification_sandbox,
    )
except ModuleNotFoundError:
    import evidence_envelope  # type: ignore[no-redef]
    import fleet_doctor  # type: ignore[no-redef]
    import generate_platform_adapters  # type: ignore[no-redef]
    import install_codex_agents  # type: ignore[no-redef]
    import verification_sandbox  # type: ignore[no-redef]


REPO_ROOT = Path(__file__).resolve().parents[1]
HOSTS = ("claude", "codex", "vscode", "copilot")
CLI_COMMANDS = {"claude": "claude", "codex": "codex", "vscode": "code", "copilot": "copilot"}
CRITERIA = ("install", "inventory", "authority", "uninstall")
CLAUDE_PLUGIN_ID = "sre-agents@latent-sre"
COPILOT_PLUGIN_ID = "sre-agents@latent-sre"
MODEL_LIMITATION = (
    "No model session was started; requested/observed model fields are absent by design "
    "(model behavior is an EVAL-001 concern)."
)
CREDENTIAL_LIMITATION = (
    "No credentials were provisioned; a CLI verb requiring authentication reports inconclusive."
)

Check = fleet_doctor.Check
CommandResult = fleet_doctor.CommandResult
Runner = Callable[[Sequence[str], Mapping[str, str] | None], CommandResult]
GitRunner = Callable[[Sequence[str]], CommandResult]
Which = Callable[[str], str | None]


def _command_name(executable: str) -> str:
    return Path(executable).stem.lower()


def _assert_probe_command(argv: Sequence[str], *, root: Path) -> None:
    """Reject command drift before subprocess execution can acquire install authority."""

    if not argv:
        raise ValueError("empty command")
    name = _command_name(argv[0])
    tail = tuple(argv[1:])
    allowed = name in set(CLI_COMMANDS.values()) and tail == ("--version",)
    if name == "claude":
        allowed = allowed or tail in {
            ("plugin", "list"),
            ("plugin", "marketplace", "add", str(root)),
            ("plugin", "install", CLAUDE_PLUGIN_ID),
            ("plugin", "uninstall", CLAUDE_PLUGIN_ID),
        }
    if name == "copilot":
        allowed = allowed or tail in {
            ("plugin", "list"),
            ("plugin", "marketplace", "add", str(root)),
            ("plugin", "install", COPILOT_PLUGIN_ID),
            ("plugin", "uninstall", COPILOT_PLUGIN_ID),
        }
    if not allowed:
        raise ValueError(
            "host install probe refused a command outside its scoped allowlist: " + repr(list(argv))
        )


def _run_probe(
    argv: Sequence[str],
    env: Mapping[str, str] | None,
    *,
    root: Path,
) -> CommandResult:
    _assert_probe_command(argv, root=root)
    try:
        result = subprocess.run(
            list(argv),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=60,
            env=dict(env) if env is not None else None,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CommandResult(127, "", type(exc).__name__)
    return CommandResult(result.returncode, result.stdout, result.stderr)


def _vscode_user_settings(home: Path) -> Path:
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) if appdata else home / "AppData" / "Roaming"
        return base / "Code" / "User" / "settings.json"
    if sys.platform == "darwin":
        return home / "Library" / "Application Support" / "Code" / "User" / "settings.json"
    return home / ".config" / "Code" / "User" / "settings.json"


def _validate_target(target: Path, *, root: Path, home: Path) -> Path:
    """Resolve the disposable target and prove it cannot alias user- or repo-owned state.

    Unlike verification_sandbox's source mounts -- where a swapped ancestor silently changes
    digest-bound bytes, so every ancestor link must be rejected -- this target is created fresh
    by the probe and removed afterwards, so OS-resolved ancestor links (macOS /var -> /private/var)
    are safe. Only the final component must never be a link or reparse point itself.
    """

    expanded = Path(target).expanduser()
    if os.path.lexists(expanded) and verification_sandbox._is_indirection(expanded):
        raise ValueError(f"disposable target must not itself be a link or reparse point: {expanded}")
    target = Path(os.path.abspath(expanded)).resolve()
    user_locations = {
        (home / ".claude").resolve(),
        (home / ".codex").resolve(),
        (home / ".copilot").resolve(),
        Path(os.environ.get("CLAUDE_CONFIG_DIR", home / ".claude")).expanduser().resolve(),
        Path(os.environ.get("CODEX_HOME", home / ".codex")).expanduser().resolve(),
        _vscode_user_settings(home).parent.resolve(),
    }
    if target in user_locations or any(
        location in target.parents or target in location.parents for location in user_locations
    ):
        raise ValueError(f"disposable target must not live inside user-owned configuration: {target}")
    if target == home or target in home.parents:
        raise ValueError(f"disposable target must not be or contain the user home: {target}")
    if target == root or root in target.parents or target in root.parents:
        raise ValueError(
            f"disposable target must not be, contain, or live inside the fleet repository: {target}"
        )
    if target == Path(target.anchor):
        raise ValueError(f"disposable target must not be a filesystem root: {target}")
    if target.exists():
        if not target.is_dir() or any(target.iterdir()):
            raise ValueError(f"disposable target must be absent or an empty directory: {target}")
    target.mkdir(parents=True, exist_ok=True)
    return target


def _census_entry(path: Path) -> tuple[str, int, int] | None:
    try:
        info = path.lstat()
    except OSError:
        return None
    if verification_sandbox._is_indirection(path):
        return ("link", 0, 0)
    if info.st_mode & 0o170000 == 0o040000:
        return ("dir", 0, 0)
    return ("file", info.st_size, info.st_mtime_ns)


def _stat_census(location: Path) -> dict[str, tuple[str, int, int]] | None:
    """Map a watched user location to path metadata; ``None`` means it could not be enumerated.

    Metadata only: sizes and mtimes detect writes without reading user-owned bytes. A missing
    location is an empty census, not an error.
    """

    if not location.exists():
        return {}
    if location.is_file() or location.is_symlink():
        entry = _census_entry(location)
        return {".": entry} if entry is not None else None
    census: dict[str, tuple[str, int, int]] = {}
    try:
        for current, dirnames, filenames in os.walk(location, followlinks=False):
            current_path = Path(current)
            kept = []
            for name in dirnames:
                child = current_path / name
                entry = _census_entry(child)
                if entry is None:
                    return None
                census[child.relative_to(location).as_posix()] = entry
                if entry[0] == "dir":
                    kept.append(name)
            dirnames[:] = kept
            for name in filenames:
                child = current_path / name
                entry = _census_entry(child)
                if entry is None:
                    return None
                census[child.relative_to(location).as_posix()] = entry
    except OSError:
        return None
    return census


def _census_change(before: dict | None, after: dict | None) -> int | None:
    if before is None or after is None:
        return None
    changed = {key for key in before.keys() | after.keys() if before.get(key) != after.get(key)}
    return len(changed)


def _child_env(disposable_home: Path, extra: Mapping[str, str]) -> dict[str, str]:
    """Minimal credential-free child environment; every writable pointer lands in the target."""

    environment = {
        key: os.environ[key]
        for key in ("PATH", "PATHEXT", "SYSTEMROOT", "WINDIR")
        if key in os.environ
    }
    home = disposable_home.resolve()
    home.mkdir(parents=True, exist_ok=True)
    temporary = home / "tmp"
    temporary.mkdir(exist_ok=True)
    environment.update(
        {
            "HOME": str(home),
            "USERPROFILE": str(home),
            "TEMP": str(temporary),
            "TMP": str(temporary),
            "TMPDIR": str(temporary),
        }
    )
    environment.update(extra)
    return environment


def _availability(host: str, which: Which, run: Runner) -> tuple[str | None, str]:
    executable = which(CLI_COMMANDS[host])
    if not executable:
        return None, "unavailable"
    version = run((executable, "--version"), None)
    if version.returncode:
        return executable, "unreadable"
    safe_version, _ = fleet_doctor._safe_version(version.stdout)
    return executable, safe_version


def _unavailable_checks(host: str) -> list[Check]:
    return [
        Check(
            f"host.{host}.probe-{criterion}",
            "skip",
            f"{host} CLI is not installed or not on PATH.",
            limitations=(
                "Availability was not treated as a passing runtime check.",
                MODEL_LIMITATION,
            ),
        )
        for criterion in CRITERIA
    ]


def _authority_check(host: str, watched: Sequence[tuple[str, dict | None, dict | None]]) -> Check:
    """Compare censuses of user-owned locations; only counts and category labels are reported."""

    changes = 0
    labels = []
    for label, before, after in watched:
        changed = _census_change(before, after)
        if changed is None:
            return Check(
                f"host.{host}.probe-authority",
                "inconclusive",
                f"The {label} user location could not be enumerated, so the write boundary is unproven.",
            )
        if changed:
            changes += changed
            labels.append(label)
    if changes:
        return Check(
            f"host.{host}.probe-authority",
            "fail",
            f"{changes} path(s) changed under user-owned location(s) during the disposable probe.",
            {"changed_user_path_count": changes, "changed_location_count": len(labels)},
        )
    return Check(
        f"host.{host}.probe-authority",
        "pass",
        "All probe writes stayed inside the disposable target; watched user locations are unchanged.",
    )


def _probe_claude(root: Path, target: Path, home: Path, run: Runner, *, executable: str) -> list[Check]:
    checks: list[Check] = []
    config = target / "claude" / "config"
    env = _child_env(target / "claude" / "home", {"CLAUDE_CONFIG_DIR": str(config)})
    watched = Path(os.environ.get("CLAUDE_CONFIG_DIR", home / ".claude")).expanduser().resolve()
    census_before = _stat_census(watched)

    def cli(*tail: str) -> CommandResult:
        return run((executable, *tail), env)

    add = cli("plugin", "marketplace", "add", str(root))
    install = cli("plugin", "install", CLAUDE_PLUGIN_ID) if add.returncode == 0 else None
    if install is None or install.returncode != 0:
        checks.append(
            Check(
                "host.claude.probe-install",
                "inconclusive",
                "The Claude CLI could not complete the disposable plugin install verbs.",
                {
                    "marketplace_add_rc": add.returncode,
                    "install_rc": None if install is None else install.returncode,
                },
                (executable, "plugin", "marketplace", "add", str(root)),
                str(target),
                add.returncode,
                (CREDENTIAL_LIMITATION,),
            )
        )
        checks.extend(
            Check(
                f"host.claude.probe-{criterion}",
                "skip",
                "Install did not complete, so there is nothing to inventory or uninstall.",
                limitations=(MODEL_LIMITATION,),
            )
            for criterion in ("inventory", "uninstall")
        )
        checks.append(_authority_check("claude", [("Claude-config", census_before, _stat_census(watched))]))
        return checks
    checks.append(
        Check(
            "host.claude.probe-install",
            "pass",
            "Fleet plugin installed into a disposable Claude configuration.",
            {"marketplace_add_rc": add.returncode, "install_rc": install.returncode},
            (executable, "plugin", "install", CLAUDE_PLUGIN_ID),
            str(target),
            install.returncode,
            (CREDENTIAL_LIMITATION,),
        )
    )

    listing = cli("plugin", "list")
    found = (
        fleet_doctor._inventory_contains_plugin("claude", listing.stdout, "sre-agents")
        if listing.returncode == 0
        else None
    )
    checks.append(
        Check(
            "host.claude.probe-inventory",
            "inconclusive" if found is None else ("pass" if found else "fail"),
            (
                "Disposable Claude inventory lists the fleet plugin."
                if found
                else "Disposable Claude inventory could not confirm the fleet plugin."
            ),
            {"installed": found},
            (executable, "plugin", "list"),
            str(target),
            listing.returncode,
            (MODEL_LIMITATION,),
        )
    )

    remove = cli("plugin", "uninstall", CLAUDE_PLUGIN_ID)
    if remove.returncode:
        checks.append(
            Check(
                "host.claude.probe-uninstall",
                "inconclusive",
                "The Claude CLI could not complete the disposable plugin uninstall verb.",
                {"uninstall_rc": remove.returncode},
                (executable, "plugin", "uninstall", CLAUDE_PLUGIN_ID),
                str(target),
                remove.returncode,
            )
        )
    else:
        after = cli("plugin", "list")
        residue = after.returncode == 0 and fleet_doctor._inventory_contains_plugin(
            "claude", after.stdout, "sre-agents"
        )
        checks.append(
            Check(
                "host.claude.probe-uninstall",
                "fail" if residue else "pass",
                (
                    "Fleet plugin remains in the disposable inventory after uninstall."
                    if residue
                    else "Fleet plugin is absent from the disposable inventory after uninstall."
                ),
                {"residue": residue},
                (executable, "plugin", "uninstall", CLAUDE_PLUGIN_ID),
                str(target),
                remove.returncode,
            )
        )
    checks.append(_authority_check("claude", [("Claude-config", census_before, _stat_census(watched))]))
    return checks


def _probe_codex(root: Path, target: Path, home: Path) -> list[Check]:
    checks: list[Check] = []
    agents = target / "codex" / "home" / "agents"
    watched = Path(os.environ.get("CODEX_HOME", home / ".codex")).expanduser().resolve() / "agents"
    census_before = _stat_census(watched)

    adapter_failures = generate_platform_adapters.validate_generated_outputs(root)
    if adapter_failures:
        checks.append(
            Check(
                "host.codex.probe-install",
                "inconclusive",
                f"Generated adapters have {len(adapter_failures)} issue(s); known-good bytes cannot be installed.",
                limitations=("Issue text is omitted; rerun generate_platform_adapters.py locally.",),
            )
        )
        checks.extend(
            Check(
                f"host.codex.probe-{criterion}",
                "skip",
                "Install did not complete, so there is nothing to inventory or uninstall.",
                limitations=(MODEL_LIMITATION,),
            )
            for criterion in ("inventory", "uninstall")
        )
        checks.append(_authority_check("codex", [("Codex-agents", census_before, _stat_census(watched))]))
        return checks

    plan = install_codex_agents.build_sync_plan(root / ".codex" / "agents", agents)
    for planned in (*plan.writes, *plan.removals, *plan.conflicts):
        path = planned if isinstance(planned, Path) else planned.path
        if target not in path.resolve().parents:
            raise ValueError(f"probe planned a write outside the disposable target: {path}")
    install_codex_agents.apply_sync_plan(plan)
    checks.append(
        Check(
            "host.codex.probe-install",
            "pass",
            "Generated Codex custom agents installed into a disposable CODEX_HOME.",
            {"written_count": len(plan.writes)},
            limitations=("Installation used the fleet's conflict-safe installer in-process.",),
        )
    )

    sources = sorted((root / ".codex" / "agents").glob("*.toml"))
    mismatches = sum(
        1
        for source in sources
        if not (agents / source.name).is_file()
        or (agents / source.name).read_bytes()
        != install_codex_agents._installed_bytes(source.read_bytes())
    )
    checks.append(
        Check(
            "host.codex.probe-inventory",
            "pass" if not mismatches else "fail",
            (
                f"Disposable inventory holds {len(sources)} marker-managed fleet role(s)."
                if not mismatches
                else f"{mismatches} disposable role file(s) are missing or differ from generated bytes."
            ),
            {"role_count": len(sources), "mismatch_count": mismatches},
            limitations=(
                "File-level inventory only; headless Codex agent discovery is a measured platform limitation.",
                MODEL_LIMITATION,
            ),
        )
    )

    uninstall = install_codex_agents.build_uninstall_plan(agents)
    install_codex_agents.apply_sync_plan(uninstall)
    remaining = [
        item.name
        for item in agents.glob("*.toml")
        if item.is_file() and install_codex_agents._is_managed(item.read_bytes())
    ]
    checks.append(
        Check(
            "host.codex.probe-uninstall",
            "fail" if remaining else "pass",
            (
                f"{len(remaining)} managed role file(s) remain after uninstall."
                if remaining
                else "No marker-managed role files remain after uninstall."
            ),
            {"removed_count": len(uninstall.removals), "residue_count": len(remaining)},
            limitations=("Uninstall removes only marker-managed files.",),
        )
    )
    checks.append(_authority_check("codex", [("Codex-agents", census_before, _stat_census(watched))]))
    return checks


def _link_free_tree(root: Path) -> bool:
    for current, dirnames, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        for name in (*dirnames, *filenames):
            if verification_sandbox._is_indirection(current_path / name):
                return False
    return True


def _copy_generated_tree(source: Path, destination: Path) -> int:
    copied = 0
    for current, _, filenames in os.walk(source, followlinks=False):
        current_path = Path(current)
        for name in filenames:
            origin = current_path / name
            placed = destination / origin.relative_to(source)
            placed.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(origin, placed)
            copied += 1
    return copied


def _probe_vscode(root: Path, target: Path, home: Path) -> list[Check]:
    checks: list[Check] = []
    workspace = target / "vscode" / "workspace"
    watched = _vscode_user_settings(home)
    census_before = _stat_census(watched)

    adapter_failures = generate_platform_adapters.validate_generated_outputs(root)
    agent_source = root / ".github" / "agents"
    skill_source = root / "platforms" / "copilot" / "skills"
    if adapter_failures or not agent_source.is_dir() or not skill_source.is_dir():
        checks.append(
            Check(
                "host.vscode.probe-install",
                "inconclusive",
                "Generated VS Code projections are incomplete; known-good bytes cannot be installed.",
                limitations=("Issue text is omitted; rerun generate_platform_adapters.py locally.",),
            )
        )
        checks.extend(
            Check(
                f"host.vscode.probe-{criterion}",
                "skip",
                "Install did not complete, so there is nothing to inventory or uninstall.",
                limitations=(MODEL_LIMITATION,),
            )
            for criterion in ("inventory", "uninstall")
        )
        checks.append(
            _authority_check("vscode", [("VS-Code-user-settings", census_before, _stat_census(watched))])
        )
        return checks

    if not (_link_free_tree(agent_source) and _link_free_tree(skill_source)):
        raise ValueError("generated VS Code projection contains links or reparse points; refusing to copy")

    agents_dest = workspace / ".github" / "agents"
    skills_dest = workspace / "platforms" / "copilot" / "skills"
    settings_dest = workspace / ".vscode" / "settings.json"
    written_agents = _copy_generated_tree(agent_source, agents_dest)
    written_skills = _copy_generated_tree(skill_source, skills_dest)
    settings_dest.parent.mkdir(parents=True, exist_ok=True)
    settings_dest.write_text(
        json.dumps({"chat.agentSkillsLocations": {"platforms/copilot/skills": True}}, indent=2) + "\n",
        encoding="utf-8",
    )
    checks.append(
        Check(
            "host.vscode.probe-install",
            "pass",
            "Generated agents, skills, and skills-location setting placed into a disposable workspace.",
            {"agent_file_count": written_agents, "skill_file_count": written_skills},
            limitations=("VS Code install is workspace file placement; discovery is a folder scan.",),
        )
    )

    mismatches = 0
    for source_root, destination_root in ((agent_source, agents_dest), (skill_source, skills_dest)):
        for origin in sorted(source_root.rglob("*")):
            if not origin.is_file():
                continue
            placed = destination_root / origin.relative_to(source_root)
            if not placed.is_file() or placed.read_bytes() != origin.read_bytes():
                mismatches += 1
    try:
        settings = json.loads(settings_dest.read_text(encoding="utf-8"))
        locations = settings.get("chat.agentSkillsLocations")
        skills_registered = isinstance(locations, dict) and locations.get("platforms/copilot/skills") is True
    except (OSError, ValueError):
        skills_registered = False
    checks.append(
        Check(
            "host.vscode.probe-inventory",
            "pass" if not mismatches and skills_registered else "fail",
            (
                "Disposable workspace inventory matches the generated projections byte for byte."
                if not mismatches and skills_registered
                else "Disposable workspace inventory diverges from the generated projections."
            ),
            {"mismatch_count": mismatches, "skills_location_registered": skills_registered},
            limitations=(
                "File-level inventory only; VS Code runtime discovery is UI-bound and was not exercised.",
                MODEL_LIMITATION,
            ),
        )
    )

    for source_root, destination_root in ((agent_source, agents_dest), (skill_source, skills_dest)):
        for origin in sorted(source_root.rglob("*")):
            if origin.is_file():
                (destination_root / origin.relative_to(source_root)).unlink(missing_ok=True)
    settings_dest.unlink(missing_ok=True)
    residue = 0
    for current, dirnames, filenames in os.walk(workspace, followlinks=False):
        residue += len(filenames)
        residue += sum(
            1
            for name in dirnames
            if verification_sandbox._is_indirection(Path(current) / name)
        )
    checks.append(
        Check(
            "host.vscode.probe-uninstall",
            "fail" if residue else "pass",
            (
                f"{residue} unexpected file(s) remain in the disposable workspace after uninstall."
                if residue
                else "Exactly the placed files were removed; the disposable workspace holds no residue."
            ),
            {"residue_count": residue},
            limitations=(
                "Uninstall removes exactly the paths the probe placed; foreign content is reported "
                "as residue, never deleted.",
            ),
        )
    )
    checks.append(
        _authority_check("vscode", [("VS-Code-user-settings", census_before, _stat_census(watched))])
    )
    return checks


def _probe_copilot(root: Path, target: Path, home: Path, run: Runner, *, executable: str) -> list[Check]:
    checks: list[Check] = []
    env = _child_env(target / "copilot" / "home", {})
    watched_locations = (home / ".copilot", home / ".cache" / "copilot")
    census_before = [_stat_census(location) for location in watched_locations]

    def authority() -> Check:
        watched = [
            (label, before, _stat_census(location))
            for label, before, location in zip(
                ("Copilot-config", "Copilot-cache"), census_before, watched_locations
            )
        ]
        return _authority_check("copilot", watched)

    def cli(*tail: str) -> CommandResult:
        return run((executable, *tail), env)

    add = cli("plugin", "marketplace", "add", str(root))
    install = cli("plugin", "install", COPILOT_PLUGIN_ID) if add.returncode == 0 else None
    if install is None or install.returncode != 0:
        checks.append(
            Check(
                "host.copilot.probe-install",
                "inconclusive",
                "The Copilot CLI could not complete the disposable plugin install verbs.",
                {
                    "marketplace_add_rc": add.returncode,
                    "install_rc": None if install is None else install.returncode,
                },
                (executable, "plugin", "marketplace", "add", str(root)),
                str(target),
                add.returncode,
                (CREDENTIAL_LIMITATION,),
            )
        )
        checks.extend(
            Check(
                f"host.copilot.probe-{criterion}",
                "skip",
                "Install did not complete, so there is nothing to inventory or uninstall.",
                limitations=(MODEL_LIMITATION,),
            )
            for criterion in ("inventory", "uninstall")
        )
        checks.append(authority())
        return checks
    checks.append(
        Check(
            "host.copilot.probe-install",
            "pass",
            "Fleet plugin installed into a disposable Copilot home.",
            {"marketplace_add_rc": add.returncode, "install_rc": install.returncode},
            (executable, "plugin", "install", COPILOT_PLUGIN_ID),
            str(target),
            install.returncode,
            (CREDENTIAL_LIMITATION,),
        )
    )

    listing = cli("plugin", "list")
    found = (
        fleet_doctor._inventory_contains_plugin("copilot", listing.stdout, "sre-agents")
        if listing.returncode == 0
        else None
    )
    checks.append(
        Check(
            "host.copilot.probe-inventory",
            "inconclusive" if found is None else ("pass" if found else "fail"),
            (
                "Disposable Copilot inventory lists the fleet plugin."
                if found
                else "Disposable Copilot inventory could not confirm the fleet plugin."
            ),
            {"installed": found},
            (executable, "plugin", "list"),
            str(target),
            listing.returncode,
            (MODEL_LIMITATION,),
        )
    )

    remove = cli("plugin", "uninstall", COPILOT_PLUGIN_ID)
    if remove.returncode:
        checks.append(
            Check(
                "host.copilot.probe-uninstall",
                "inconclusive",
                "The Copilot CLI could not complete the disposable plugin uninstall verb.",
                {"uninstall_rc": remove.returncode},
                (executable, "plugin", "uninstall", COPILOT_PLUGIN_ID),
                str(target),
                remove.returncode,
            )
        )
    else:
        after = cli("plugin", "list")
        residue = after.returncode == 0 and fleet_doctor._inventory_contains_plugin(
            "copilot", after.stdout, "sre-agents"
        )
        checks.append(
            Check(
                "host.copilot.probe-uninstall",
                "fail" if residue else "pass",
                (
                    "Fleet plugin remains in the disposable inventory after uninstall."
                    if residue
                    else "Fleet plugin is absent from the disposable inventory after uninstall."
                ),
                {"residue": residue},
                (executable, "plugin", "uninstall", COPILOT_PLUGIN_ID),
                str(target),
                remove.returncode,
            )
        )
    checks.append(authority())
    return checks


def _to_envelope(
    check: Check,
    *,
    host: str,
    cli_version: str,
    root: Path,
    revision: str,
    run_id: str,
    started_at: datetime,
    ended_at: datetime,
) -> dict[str, object]:
    return evidence_envelope.new_envelope(
        producer="host_install_probe",
        role="disposable-host-proof",
        target_root=str(root),
        target_revision=revision,
        criterion=check.check_id,
        status=check.status,
        started_at=started_at,
        ended_at=ended_at,
        command_argv=check.command_argv,
        command_cwd=check.command_cwd,
        exit_code=check.exit_code,
        source={"summary": check.summary, "details": check.details},
        run_id=run_id,
        task_id=check.check_id,
        attempt_id="attempt-1",
        environment={"probe": "disposable-host-install", "host": host, "host_cli": cli_version},
        isolation={
            "writes": "disposable-target-only",
            "auth_material": "not-provisioned",
            "model_sessions": "none",
            "network": "not-required",
        },
        limitations=check.limitations,
    )


def collect_report(
    root: Path = REPO_ROOT,
    *,
    target: Path,
    hosts: Sequence[str] = HOSTS,
    home: Path | None = None,
    run: Runner | None = None,
    git_run: GitRunner = fleet_doctor._run_read_only,
    which: Which = shutil.which,
    now: datetime | None = None,
) -> dict[str, object]:
    root = root.resolve()
    home = (home or Path.home()).resolve()
    unknown = [host for host in hosts if host not in HOSTS]
    if unknown or not hosts:
        raise ValueError(f"unknown or empty host selection: {sorted(unknown) or 'none selected'}")
    started = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    run_id = "probe-" + started.strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    revision, git_checks = fleet_doctor._git_checks(root, git_run)
    if revision == "unknown":
        detail = git_checks[0].summary if git_checks else "no revision evidence"
        raise ValueError(f"cannot prove a disposable install against an unknown revision: {detail}")
    target = _validate_target(target, root=root, home=home)
    if run is None:
        run = lambda argv, env: _run_probe(argv, env, root=root)  # noqa: E731

    checks_by_host: dict[str, tuple[str, list[Check]]] = {}
    for host in hosts:
        executable, version = _availability(host, which, run)
        if executable is None:
            checks_by_host[host] = (version, _unavailable_checks(host))
        elif host == "claude":
            checks_by_host[host] = (
                version,
                _probe_claude(root, target, home, run, executable=executable),
            )
        elif host == "codex":
            checks_by_host[host] = (version, _probe_codex(root, target, home))
        elif host == "vscode":
            checks_by_host[host] = (version, _probe_vscode(root, target, home))
        else:
            checks_by_host[host] = (
                version,
                _probe_copilot(root, target, home, run, executable=executable),
            )

    ended = started if now is not None else datetime.now(timezone.utc)
    envelopes = [
        _to_envelope(
            check,
            host=host,
            cli_version=version,
            root=root,
            revision=revision,
            run_id=run_id,
            started_at=started,
            ended_at=ended,
        )
        for host, (version, checks) in checks_by_host.items()
        for check in checks
    ]
    counts = Counter(item["status"] for item in envelopes)
    report: dict[str, object] = {
        "schema_version": 1,
        "run_id": run_id,
        "generated_at": evidence_envelope.format_timestamp(ended),
        "root": str(root),
        "revision": revision,
        "summary": {status: counts.get(status, 0) for status in fleet_doctor.STATUSES},
        "evidence": envelopes,
    }
    fleet_doctor.validate_report(report)
    return report


def render_human(report: Mapping[str, object]) -> str:
    return "Host install probe" + fleet_doctor.render_human(report)[len("Fleet doctor"):]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="fleet repository root")
    parser.add_argument(
        "--target",
        type=Path,
        required=True,
        help=(
            "explicit disposable target: absent or empty, outside user-owned configuration and the "
            "repository; removed afterwards unless --keep"
        ),
    )
    parser.add_argument(
        "--hosts",
        type=lambda value: tuple(item.strip() for item in value.split(",") if item.strip()),
        default=HOSTS,
        help="comma-separated subset of: " + ", ".join(HOSTS),
    )
    parser.add_argument("--json", action="store_true", help="emit the versioned JSON report")
    parser.add_argument(
        "--keep",
        action="store_true",
        help="keep the disposable target for inspection instead of removing it",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    target = args.target.expanduser()
    try:
        report = collect_report(args.root, target=target, hosts=args.hosts)
    except (OSError, ValueError, evidence_envelope.EnvelopeValidationError) as exc:
        print(f"host install probe could not produce a report: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, sort_keys=True) if args.json else render_human(report))
    resolved = Path(os.path.abspath(target))
    if resolved.exists():
        if args.keep:
            print(f"Disposable target kept for inspection: {resolved}", file=sys.stderr)
        else:
            shutil.rmtree(resolved)
            print(f"Disposable target removed: {resolved}", file=sys.stderr)
    return 1 if report["summary"]["fail"] else 0  # type: ignore[index]


if __name__ == "__main__":
    raise SystemExit(main())
