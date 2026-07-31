#!/usr/bin/env python3
"""Isolate a harness trial from the operator's machine.

Both harnesses shell out to `claude -p ...`. With no explicit `env`, that inherits the operator's
entire Claude Code install: ~/.claude/skills, ~/.claude/agents, installed plugins (which may ship
those same skills AGAIN), and the operator's global CLAUDE.md. Those do not shadow the fleet by name
-- they COMPETE with it for skill discovery, which is the one thing a discovery probe exists to
measure. Every number it ever produced described the LAPTOP, not the fleet, and every recorded
baseline says so ("treat as a LOWER BOUND").

CLAUDE_CONFIG_DIR relocates the whole user config -- "If you set CLAUDE_CONFIG_DIR, every ~/.claude
path on this page lives under that directory instead" (code.claude.com/docs/en/claude-directory).
Point it at a temp dir holding ONLY the credentials, then load the repository explicitly with
`--plugin-dir`. The model sees this plugin and none of the operator's personal fleet.

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
import sys
import tempfile
from pathlib import Path

CREDENTIALS = ".credentials.json"

# Markers of an auth failure in a trial's output.
# NOT `subtype`: the result event of a not-logged-in run says subtype="success" while is_error=true.
AUTH_MARKERS = ("authentication_failed", "Not logged in")

# Env vars that authenticate `claude -p` WITHOUT a ~/.claude/.credentials.json file. An operator
# using an API key, Bedrock, or Vertex has none of that file and never will -- require_credentials()
# would otherwise refuse them permanently and point at "/login", which cannot help them.
API_KEY_ENV_VARS = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "CLAUDE_CODE_USE_BEDROCK", "CLAUDE_CODE_USE_VERTEX")

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
    """onexc handler for the clean-room rmtree: never fail silently, we're deleting a credential copy."""
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
            f"{CREDENTIALS}. (If you authenticate via ANTHROPIC_API_KEY/Bedrock/Vertex instead, set "
            f"that env var and this check is skipped entirely.)"
        )
    return p


def has_api_key_auth() -> bool:
    """True if an API-key/Bedrock/Vertex env var authenticates `claude -p` directly. Those operators
    have NO ~/.claude/.credentials.json file -- not a missing one, a nonexistent CONCEPT -- so
    require_credentials() must not be consulted for them at all."""
    return any(os.environ.get(v) for v in API_KEY_ENV_VARS)


def warn_if_settings_local_present() -> None:
    """`.claude/settings.local.json` is read from the CWD by Claude Code on every invocation,
    regardless of CLAUDE_CONFIG_DIR -- a second leak channel the clean room does not cover. This
    does not refuse (its contents may be perfectly benign, e.g. Bash allow-rules) -- it just makes
    the leak visible. Clean runs belong in a throwaway git worktree (see evals/README.md)."""
    if SETTINGS_LOCAL.is_file():
        print(
            f"clean_room: WARNING -- {SETTINGS_LOCAL} exists and is read from the CWD on every "
            f"trial regardless of CLAUDE_CONFIG_DIR. It can carry env/hooks/plugin keys, not just "
            f"Bash allow-rules -- operator-machine state inside the 'clean' namespace. Run clean "
            f"trials from a throwaway git worktree.",
            file=sys.stderr,
        )


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


def result_looks_like_auth(blob: str) -> bool:
    """Given a trial already known to be unmeasurable (is_error_event / returncode nonzero), does
    the CLI's OWN verdict look like an auth problem? This is used ONLY to pick the right human
    message ("looks like auth -- run /login" vs a generic runner-failure message) -- never as the
    detector of failure itself. It scans just the structured result event's own fields, never the
    full transcript, so a `tool_result` containing the literal marker text (a file the agent read)
    cannot trigger it.
    """
    evt = find_result_event(blob)
    if not evt:
        return False
    return any(m in json.dumps(evt) for m in AUTH_MARKERS)


@contextlib.contextmanager
def clean_env():
    """Yield an env whose CLAUDE_CONFIG_DIR holds ONLY the credentials (or nothing, for API-key/
    Bedrock/Vertex auth -- see has_api_key_auth()).

    The caller loads this repository with `--plugin-dir`; the model then sees that plugin and
    nothing else from the operator's personal Claude configuration.
    """
    warn_if_settings_local_present()
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
        # else: API-key/Bedrock/Vertex auth -- no credentials FILE exists to copy. Isolation is still
        # fully achieved (the temp dir has no personal skills/agents/plugins/CLAUDE.md); only the
        # credential-file check is inapplicable.
        yield dict(os.environ, CLAUDE_CONFIG_DIR=str(tmp))
    finally:
        shutil.rmtree(tmp, onexc=_warn_leftover)  # onexc (3.12+): repo/CI both pin Python 3.12.
