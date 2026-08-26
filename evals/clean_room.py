#!/usr/bin/env python3
"""Isolate a harness trial from the operator's machine.

The harness shells out to `claude -p ...`. With no explicit `env`, that inherits the operator's
entire Claude Code install: ~/.claude/skills, ~/.claude/agents, installed plugins (which may ship
those same skills AGAIN), and the operator's global CLAUDE.md. Those do not shadow the fleet by name
-- they COMPETE with it for skill discovery, which is the one thing a discovery probe exists to
measure. Every number it ever produced described the LAPTOP, not the fleet, and every recorded
baseline says so ("treat as a LOWER BOUND").

CLAUDE_CONFIG_DIR relocates the whole user config -- "If you set CLAUDE_CONFIG_DIR, every ~/.claude
path on this page lives under that directory instead" (code.claude.com/docs/en/claude-directory).
Point it at a temp dir holding ONLY the credentials, scrub unrelated host variables, and run from
an empty temporary working directory while loading the repository explicitly with `--plugin-dir`.
The model sees this plugin and none of the operator's personal fleet or project guidance.

WHY THIS MODULE REFUSES RATHER THAN DEGRADES
An EMPTY config dir breaks auth, and that failure is silent in the worst possible way: `claude -p`
still emits a VALID stream-json trace (system/init and all), exits 1, and reports "Not logged in" in
the RESULT event -- while stderr carries only an unrelated stdin warning. A harness that parses that
trace finds no Skill() call and scores a clean NO-ROUTE. Every scenario "fails", and the report reads
as a devastating finding about the fleet rather than as a broken instrument. An eval harness that
converts its own breakage into findings about the thing it measures is the worst failure available to
it. So: no credentials -> AuthUnavailable, before a single trial runs; and an auth-failure trace is an
ERROR, never a routing outcome.
"""
from __future__ import annotations

import contextlib
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

CREDENTIALS = ".credentials.json"

# Markers of an auth failure in a trial's output.
# NOT `subtype`: the result event of a not-logged-in run says subtype="success" while is_error=true.
AUTH_MARKERS = ("authentication_failed", "Not logged in")

# Direct API authentication variables that must survive the environment scrub. Bedrock and Vertex
# selectors are handled separately: those modes depend on a wider, provider-specific credential
# environment that cannot be safely guessed and copied into a least-privilege eval subprocess.
API_KEY_ENV_VARS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")
CLOUD_AUTH_SELECTORS = ("CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX")

# Minimum host variables needed to launch a subprocess and establish TLS across the supported OSes.
# Deliberately absent: GitHub/cloud/service tokens, arbitrary CLAUDE_CODE_* behavior overrides, and
# repository-specific variables. Proxy variables are retained because they are transport settings;
# the runner denies stateful and egress tools and runs in an empty workspace.
SAFE_ENV_KEYS = (
    "PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC",
    "TEMP", "TMP", "TMPDIR", "HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA",
    "LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR",
    "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "no_proxy", "all_proxy",
)

# A file that, if it exists in the CWD, leaks operator-machine state into every trial regardless of
# CLAUDE_CONFIG_DIR (Claude Code reads project-local settings from the CWD, not from the config dir).
SETTINGS_LOCAL = Path(".claude/settings.local.json")


class AuthUnavailable(RuntimeError):
    """Fatal: the harness cannot produce a valid measurement. Never scored as a result."""


class RunnerFailed(RuntimeError):
    """Fatal for THIS trial: the subprocess did not complete for a reason OTHER than auth (rate
    limit, 5xx, network drop, bad flag, ...). Sibling of AuthUnavailable: a trial that did not
    complete produced no measurement, whatever broke it -- this must never be scored PASS/FAIL, nor
    folded into a routing bucket (no-route/misroute). Auth is only ONE way to get a non-zero exit
    with an empty trace; this is the general case."""


def _scrub_tree(path) -> None:
    """rmtree that reports what it could not delete, on every interpreter this repo blesses.

    `onexc` arrived in 3.12; `onerror` is deprecated there but still honored, and is all 3.11 has.
    Gate A's floor is 3.11, so naming either callback alone breaks one of the two interpreters --
    and it breaks it as a raised TypeError inside a `finally:` that is deleting a COPY OF THE AUTH
    CREDENTIALS. The teardown must not be the thing that fails.
    """
    if sys.version_info >= (3, 12):
        shutil.rmtree(path, onexc=_warn_leftover)
    else:
        shutil.rmtree(
            path, onerror=lambda func, p, exc_info: _warn_leftover(func, p, exc_info[1])
        )


def _warn_leftover(func, path, exc) -> None:
    """Failure handler for the clean-room rmtree: never fail silently, we're deleting a credential copy."""
    print(
        f"clean_room: WARNING -- failed to remove {path} ({func.__name__}: {exc}). "
        f"This directory holds a COPY OF THE AUTH CREDENTIALS and was left on disk.",
        file=sys.stderr,
    )


def user_config_dir() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude"))


def credentials_path() -> Path:
    return user_config_dir() / CREDENTIALS


def require_credentials() -> Path:
    p = credentials_path()
    if not p.is_file():
        raise AuthUnavailable(
            f"no Claude credentials at {p}.\n"
            f"The clean room needs them. Without them every trial returns 'Not logged in', which "
            f"this harness would parse as a trace with no Skill() call and score as a no-route -- "
            f"turning a broken instrument into a fake finding about the fleet. Refusing to run.\n"
            f"Fix: run `claude` and /login, or point CLAUDE_CONFIG_DIR at a config dir containing "
            f"{CREDENTIALS}. (If you authenticate via ANTHROPIC_API_KEY or ANTHROPIC_AUTH_TOKEN, "
            f"set it and this check is skipped entirely.)"
        )
    return p


def has_api_key_auth() -> bool:
    """True if a direct Anthropic API variable authenticates `claude -p`."""
    return any(os.environ.get(v) for v in API_KEY_ENV_VARS)


def scrubbed_child_env(config_dir: Path) -> dict[str, str]:
    """Build the child environment from an allowlist, retaining required direct authentication."""
    if any(os.environ.get(v) for v in CLOUD_AUTH_SELECTORS):
        raise AuthUnavailable(
            "Bedrock/Vertex auth is not supported by the credential-scrubbed eval harness because "
            "it requires provider-specific host credentials. Use Claude login credentials or a "
            "direct ANTHROPIC_API_KEY/ANTHROPIC_AUTH_TOKEN in a disposable environment."
        )
    env = {key: os.environ[key] for key in SAFE_ENV_KEYS if os.environ.get(key)}
    for key in API_KEY_ENV_VARS:
        if os.environ.get(key):
            env[key] = os.environ[key]
    env["CLAUDE_CONFIG_DIR"] = str(config_dir)
    return env


@contextlib.contextmanager
def neutral_workspace():
    """Yield an empty CWD outside the repository, then remove it.

    Claude discovers project instructions by walking upward from CWD. A system temp directory keeps
    AGENTS.md/CLAUDE.md from the plugin repository out of discovery measurements.
    """
    tmp = Path(tempfile.mkdtemp(prefix="fleet-eval-workspace-"))
    try:
        os.chmod(tmp, stat.S_IRWXU)
        resolved = tmp.resolve()
        plugin_root = Path(__file__).resolve().parent.parent
        if resolved.is_relative_to(plugin_root):
            raise RunnerFailed(f"neutral trial workspace resolved inside the plugin repository: {resolved}")
        init = subprocess.run(
            ["git", "init", "--quiet", str(resolved)],
            capture_output=True, text=True, check=False, encoding="utf-8", errors="replace",
        )
        if init.returncode != 0:
            raise RunnerFailed(f"could not create neutral git-root boundary: {init.stderr.strip()[:300]}")
        top = subprocess.run(
            ["git", "-C", str(resolved), "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, check=False, encoding="utf-8", errors="replace",
        )
        if top.returncode != 0 or Path(top.stdout.strip()).resolve() != resolved:
            raise RunnerFailed("neutral workspace is not its own git root; ancestor instructions may leak")
        contaminants = [
            resolved / "AGENTS.md", resolved / "CLAUDE.md",
            resolved / ".claude" / "settings.json", resolved / SETTINGS_LOCAL,
        ]
        if any(path.exists() for path in contaminants):
            raise RunnerFailed("neutral trial workspace contains project instructions or settings")
        yield tmp
    finally:
        _scrub_tree(tmp)


def is_auth_failure(text: str, returncode: int | None = None) -> bool:
    """True if a trial's output shows the run never authenticated.

    Gated on a NON-ZERO exit. This is an SRE fleet: a healthy response can legitimately quote a log
    line containing "Not logged in" (an auth incident, a Splunk triage scenario), and aborting the
    suite on that would be a false fatal -- as bad as the fail-open this module exists to close. A
    real auth failure exits 1 (probed); a healthy run exits 0. rc == 0 is therefore never an auth
    failure, whatever the text says.

    `returncode=None` means "unknown" (e.g. a TimeoutExpired, which carries no rc) -- fall back to
    the marker scan, since a timed-out run has no exit code to gate on.
    """
    if returncode == 0:
        return False
    return any(m in (text or "") for m in AUTH_MARKERS)


@contextlib.contextmanager
def clean_env(*, subscriber_only: bool = False):
    """Yield an allowlisted env whose CLAUDE_CONFIG_DIR holds only credentials (or nothing for
    direct Anthropic API authentication -- see has_api_key_auth()).

    The caller loads this repository with `--plugin-dir`; the model then sees that plugin and
    nothing else from the operator's personal Claude configuration.
    """
    if subscriber_only and has_api_key_auth():
        raise AuthUnavailable(
            "profile-backed fleet evals require the existing Claude subscriber session; "
            "remove ANTHROPIC_API_KEY/ANTHROPIC_AUTH_TOKEN from the runner environment"
        )
    creds = None if has_api_key_auth() else require_credentials()
    tmp = Path(tempfile.mkdtemp(prefix="fleet-cleanroom-"))
    try:
        # 0700 -- it may hold an auth secret. Advisory only on non-POSIX filesystems (e.g.
        # Windows/NTFS, where os.chmod cannot enforce POSIX user/group/other bits); real protection
        # there comes from the temp dir already being user-scoped. Enforced for real on the POSIX
        # CI runners this harness targets.
        os.chmod(tmp, stat.S_IRWXU)
        if creds is not None:
            dst = tmp / CREDENTIALS
            shutil.copyfile(creds, dst)
            os.chmod(dst, stat.S_IRUSR | stat.S_IWUSR)   # 0600 -- same advisory-only caveat as above.
        # else: direct API auth -- no credentials FILE exists to copy. Isolation is still
        # fully achieved (the temp dir has no personal skills/agents/plugins/CLAUDE.md); only the
        # credential-file check is inapplicable.
        yield scrubbed_child_env(tmp)
    finally:
        _scrub_tree(tmp)
