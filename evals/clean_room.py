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
OAuth credentials are MUTABLE state: a successful refresh can rotate the refresh token. Copying the
operator's credential file into a throwaway directory discards the refreshed state; running two such
copies concurrently lets them race the same token and can invalidate the operator's login. OAuth
runs therefore require an explicitly selected, persistent, DEDICATED eval profile and serialize
batches with a profile lock. The profile is rejected if it contains behavior-bearing configuration.
Direct API authentication still uses an empty temporary config directory. In both modes unrelated
host variables are scrubbed and trials run from an empty temporary working directory while loading
the repository explicitly with `--plugin-dir`. The model sees this plugin and none of the operator's
personal fleet or project guidance.

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
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

CREDENTIALS = ".credentials.json"
EVAL_PROFILE_ENV = "SAVE_TOOLKIT_CLAUDE_EVAL_CONFIG_DIR"
EVAL_PROFILE_LOCK = ".save-toolkit-eval.lock"

# Any one of these would let the persistent auth profile shape routing or behavior. Claude may write
# caches, logs, and other inert runtime state into its dedicated profile; those are not model input
# and remain allowed. Runtime init separately proves the exact plugin, MCP, and tool boundary.
BEHAVIOR_BEARING_PROFILE_PATHS = (
    "CLAUDE.md",
    "settings.json",
    "settings.local.json",
    "agents",
    "skills",
    "plugins",
    "commands",
    "hooks",
)

# Markers of an auth failure in a trial's output.
# NOT `subtype`: the result event of a not-logged-in run says subtype="success" while is_error=true.
AUTH_MARKERS = (
    "authentication_failed",
    "Not logged in",
    "OAuth session expired and could not be refreshed",
)

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


def _warn_leftover(func, path, exc) -> None:
    """onexc handler for temporary eval directories: never fail cleanup silently."""
    print(
        f"clean_room: WARNING -- failed to remove {path} ({func.__name__}: {exc}). "
        f"This temporary evaluation directory may hold sensitive runtime state and was left on disk.",
        file=sys.stderr,
    )


def default_user_config_dir() -> Path:
    return Path.home() / ".claude"


def user_config_dir() -> Path:
    """Return the normal Claude profile path for diagnostics only.

    The eval runner never consumes this implicit location for OAuth. It is intentionally separate
    from EVAL_PROFILE_ENV so an operator cannot accidentally lend a personal profile to the model.
    """
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or default_user_config_dir())


def credentials_path(config_dir: Path | None = None) -> Path:
    return (config_dir if config_dir is not None else user_config_dir()) / CREDENTIALS


def require_credentials(config_dir: Path) -> Path:
    p = credentials_path(config_dir)
    if not p.is_file():
        raise AuthUnavailable(
            f"no Claude credentials at {p}.\n"
            f"The clean room needs them. Without them every trial returns 'Not logged in', which "
            f"this harness would parse as a trace with no Skill() call and score as a no-route -- "
            f"turning a broken instrument into a fake finding about the fleet. Refusing to run.\n"
            f"Fix: authenticate the dedicated profile named by {EVAL_PROFILE_ENV} with "
            f"`claude auth login`. An API key is not required. Direct ANTHROPIC_API_KEY or "
            f"ANTHROPIC_AUTH_TOKEN authentication is also supported when intentionally selected."
        )
    if _is_redirected(p):
        raise AuthUnavailable(f"Claude credential must be an ordinary file, not a link or reparse point: {p}")
    return p


def _is_redirected(path: Path) -> bool:
    """True for symlinks and Windows reparse points, including dangling symlinks."""
    if path.is_symlink():
        return True
    try:
        attrs = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return False
    return bool(attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))


def configured_eval_profile() -> Path:
    """Select the explicit, non-personal OAuth profile. Does not inspect secret contents."""
    raw = os.environ.get(EVAL_PROFILE_ENV)
    if not raw:
        raise AuthUnavailable(
            f"OAuth evals require an explicit dedicated profile in {EVAL_PROFILE_ENV}; ambient "
            f"CLAUDE_CONFIG_DIR and {default_user_config_dir()} are deliberately not copied because "
            f"refreshable credentials are mutable and concurrent copies can invalidate the login. "
            f"Authenticate a separate profile with `claude auth login`; an API key is not required."
        )
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    if not candidate.is_dir() or _is_redirected(candidate):
        raise AuthUnavailable(f"dedicated Claude eval profile is missing or redirected: {candidate}")
    profile = candidate.resolve()
    if profile == default_user_config_dir().resolve():
        raise AuthUnavailable(
            f"{EVAL_PROFILE_ENV} resolves to the personal default profile {profile}; create and "
            f"authenticate a separate eval-only profile instead. An API key is not required."
        )
    repository = Path(os.environ.get("FLEET_ROOT") or Path(__file__).resolve().parent.parent).resolve()
    if profile == repository or profile.is_relative_to(repository):
        raise AuthUnavailable(
            f"dedicated Claude eval profile must live outside the repository so "
            f"{CREDENTIALS} cannot be committed: {profile}"
        )
    return profile


def validate_eval_profile(profile: Path) -> None:
    """Fail closed if the auth profile could alter the component namespace or model behavior."""
    require_credentials(profile)
    contaminants = [
        name for name in BEHAVIOR_BEARING_PROFILE_PATHS
        if (profile / name).exists() or (profile / name).is_symlink()
    ]
    if contaminants:
        raise AuthUnavailable(
            f"dedicated Claude eval profile contains behavior-bearing configuration: "
            f"{', '.join(contaminants)}. Remove it from the eval-only profile; do not point the "
            f"harness at a personal Claude profile."
        )


@contextlib.contextmanager
def lock_eval_profile(profile: Path):
    """Hold a same-profile, cross-process batch lock around rotating OAuth state."""
    lock_path = profile / EVAL_PROFILE_LOCK
    owner = f"pid={os.getpid()} nonce={uuid.uuid4().hex}\n"
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, stat.S_IRUSR | stat.S_IWUSR)
    except FileExistsError as exc:
        raise AuthUnavailable(
            f"dedicated Claude eval profile is already in use: {profile}. OAuth refresh tokens may "
            f"rotate, so eval batches must not run in parallel. If no eval process is active, inspect "
            f"and remove the stale {EVAL_PROFILE_LOCK} file before retrying."
        ) from exc
    except OSError as exc:
        raise AuthUnavailable(f"could not lock dedicated Claude eval profile {profile}: {exc}") from exc
    try:
        with os.fdopen(fd, "w", encoding="ascii", newline="\n") as stream:
            stream.write(owner)
            stream.flush()
            os.fsync(stream.fileno())
        yield
    finally:
        try:
            if lock_path.read_text(encoding="ascii") == owner:
                lock_path.unlink()
            else:
                print(
                    f"clean_room: WARNING -- eval-profile lock ownership changed; left {lock_path} "
                    f"in place for inspection.",
                    file=sys.stderr,
                )
        except FileNotFoundError:
            print(
                f"clean_room: WARNING -- eval-profile lock disappeared during the batch: {lock_path}",
                file=sys.stderr,
            )
        except OSError as exc:
            print(
                f"clean_room: WARNING -- could not remove eval-profile lock {lock_path}: {exc}",
                file=sys.stderr,
            )


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
        shutil.rmtree(tmp, onexc=_warn_leftover)


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


def find_result_event(blob: str) -> dict | None:
    """The stream-json transcript's structured `{"type": "result", ...}` event, or None if the run
    never reached one (e.g. killed mid-stream by a client-side timeout).

    This is the ONLY reliable "did this trial complete" signal for a stream-json trace. Text
    elsewhere in the transcript -- including `tool_result` content, i.e. a FILE THE AGENT ITSELF
    READ or a command's output -- is not a signal about the harness's own health and must never be
    substring-scanned for one: this branch planted the literal string "Not logged in" in ~30 places
    across evals/ and docs/, so an agent scenario that greps this repo and then times out would
    otherwise abort the whole suite on a healthy run. Scanning only this one well-known top-level
    event, emitted once by the CLI itself at the very end, closes that off entirely.
    """
    evt = None
    for line in blob.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and parsed.get("type") == "result":
            evt = parsed  # keep the last one; the stream should carry exactly one
    return evt


def is_error_event(blob: str) -> bool:
    """True iff the transcript's structured result event says the run did not complete
    (`is_error: true`). `subtype` lies -- a not-logged-in run reports subtype="success" while
    is_error is true -- so this is the only field to trust.

    No result event at all (a killed/timed-out process) is NOT an error by this check alone; there
    is no structured signal either way, and callers combine this with the returncode / whether
    anything was invoked.
    """
    evt = find_result_event(blob)
    return bool(evt and evt.get("is_error"))


@contextlib.contextmanager
def clean_env():
    """Yield an allowlisted env with isolated, refresh-safe Claude authentication.

    OAuth uses an explicitly selected persistent eval-only profile so a refreshed token is not
    discarded. A profile lock prevents concurrent eval batches from racing rotating refresh state.
    Direct API authentication uses an empty disposable profile. The caller loads this repository
    with `--plugin-dir`; the model then sees that plugin and nothing else from the operator's
    personal Claude configuration.
    """
    if not has_api_key_auth():
        profile = configured_eval_profile()
        with lock_eval_profile(profile):
            validate_eval_profile(profile)
            yield scrubbed_child_env(profile)
        return

    tmp = Path(tempfile.mkdtemp(prefix="fleet-cleanroom-"))
    try:
        # Direct API auth has no credential file to copy. The empty temp profile still excludes
        # personal skills/agents/plugins/CLAUDE.md. 0700 is advisory on Windows/NTFS and enforced
        # on the POSIX runners this harness targets.
        os.chmod(tmp, stat.S_IRWXU)
        yield scrubbed_child_env(tmp)
    finally:
        shutil.rmtree(tmp, onexc=_warn_leftover)  # onexc (3.12+): repo/CI both pin Python 3.12.
