# Eval Clean Room — Implementation Plan

> **Status: implemented — historical implementation record.** The clean-room work landed in PR #52
> and has since been extended by the current eval harness. Do not execute the unchecked steps in this
> preserved plan. Current unfinished work lives only in
> [`docs/fleet-roadmap.md`](../../fleet-roadmap.md).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the behavioural eval harnesses measure the *fleet* rather than the operator's laptop, and make them abort loudly instead of converting their own breakage into fake findings.

**Architecture:** One new stdlib-only helper (`evals/clean_room.py`) creates a temp `CLAUDE_CONFIG_DIR` containing only the credentials, so `claude -p` sees the project's `.claude/` and nothing else. Both harnesses (`discovery_probe.py`, `run_evals.py`) pass that env to `subprocess.run(...)` and treat an auth-failure trace as a fatal error, never as a routing outcome. Then the contaminated baselines are annotated as such, three clean baselines are taken, and one new capability scenario measures the question the follow-on decision actually rests on.

**Tech Stack:** Python 3, stdlib only for the helper (`tempfile`, `shutil`, `contextlib`, `stat`). PyYAML for the eval harness itself (already in `requirements-dev.txt`). The Claude Code CLI.

Design spec: `docs/superpowers/specs/2026-07-13-eval-clean-room-design.md` (commit `5249e74`).

## Global Constraints

- **Python on this box is `py -3`, NOT `python3`** (`python3` is not on PATH). The repo's docs and CI say `python3`/`python` — **do not change them**; they are correct for CI, which runs on Linux/macOS/Windows runners.
- **Stdlib only in `evals/clean_room.py`.** It is imported by `--validate`, which is a CI gate and must stay dependency-free. (PyYAML is fine elsewhere in `evals/` — CI installs `requirements-dev.txt` before the eval steps.)
- **`.credentials.json` is an auth secret.** The temp dir must be `0700`, the copied file `0600`, and both must be removed on exit **including on exception**.
- **Never score an auth failure as a routing outcome.** It is an ERROR that aborts. This is the whole point of the change.
- **Do not touch `~/.claude`.** The operator's environment is theirs; the harness must be robust to it.
- **Do not preload skills into agents.** That is the follow-on, gated behind the clean baseline this plan produces.
- These tests must stay green (all are CI-gated in `.github/workflows/validate.yml`): `scripts/validate_fleet.py`, `scripts/test_validate_fleet.py`, `scripts/test_readonly_guard.py`, `evals/test_graders.py`, `evals/test_discovery_probe.py`, `evals/run_evals.py --validate`.

## Facts established by probing (do not re-derive; do not doubt)

| Fact | Evidence |
|---|---|
| `CLAUDE_CONFIG_DIR` → temp dir holding only `.credentials.json` isolates the namespace | Probe asked "is each of these skills available? sde-ladder / eng-ladder / backend-craft" → **`YES, NO, NO`**. Project skill visible; personal and plugin skills gone. |
| An auth-failed run is **silently plausible** | It exits **1**, writes **4689 bytes of valid stream-json** to stdout (including a `system/init` event), and puts nothing useful on stderr — stderr carries only an unrelated *"no stdin data received"* warning. |
| The reliable auth markers | An `assistant` event carrying `error: "authentication_failed"`, and a `result` event with `is_error: true` whose text is `"Not logged in · Please run /login"`. |
| **`subtype` is a trap** | That same result event says **`subtype: "success"`** while `is_error: true`. Anything keying on `subtype` will call an auth failure a successful run. Do not use it. |

## File Structure

**Create:**
- `evals/clean_room.py` — the isolation helper. One responsibility: hand a caller an env that isolates a `claude` invocation, or refuse. Exports `AuthUnavailable`, `credentials_path()`, `require_credentials()`, `is_auth_failure()`, `clean_env()`.
- `evals/test_clean_room.py` — its tests, plus the two regression tests that assert each harness actually *passes* the env (otherwise a future edit silently reverts the isolation).
- `evals/discovery/capability-sde-engineer-reaches-ladder.yaml` — the new capability scenario.

**Modify:**
- `evals/discovery_probe.py` — `run_trial()` takes `env`, passes it to `subprocess.run`, and raises on an auth-failure trace. `discovery_rate()` threads `env` through. `main()` wraps the run in `clean_env()`.
- `evals/run_evals.py` — `run_agent()` same treatment.
- `evals/discovery/*.yaml` — annotate every existing `note:` as taken on a contaminated namespace.
- `evals/README.md` — document the clean room and the baseline-namespace convention.

---

### Task 1: `evals/clean_room.py` — the isolation helper

**Files:**
- Create: `evals/clean_room.py`
- Create: `evals/test_clean_room.py`

**Interfaces:**
- Produces (Tasks 2 and 3 consume these exact names):
  - `class AuthUnavailable(RuntimeError)` — fatal; never scored as a result.
  - `credentials_path() -> pathlib.Path`
  - `require_credentials() -> pathlib.Path` — raises `AuthUnavailable` if absent.
  - `is_auth_failure(text: str) -> bool`
  - `clean_env()` — a **context manager** yielding an `env: dict[str, str]`.

Test style: mirror `evals/test_discovery_probe.py` exactly — a `check(cond, label)` accumulator, `test_*()` functions, an explicit `tests = [...]` list in `main()`, a `N/M checks passed` summary, non-zero exit on failure. It runs standalone (`py -3 evals/test_clean_room.py`) **and** under pytest.

- [ ] **Step 1: Write the failing tests**

Create `evals/test_clean_room.py`:

```python
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


def test_is_auth_failure_recognises_a_real_not_logged_in_trace() -> None:
    # Verbatim shapes from a probed credential-less run. Note the trap: the result event says
    # subtype "success" while is_error is true -- anything keying on subtype calls this a good run.
    assistant = '{"type":"assistant","error":"authentication_failed"}'
    result = '{"type":"result","subtype":"success","is_error":true,"result":"Not logged in \\u00b7 Please run /login"}'
    check(clean_room.is_auth_failure(assistant), "detects error=authentication_failed")
    check(clean_room.is_auth_failure(result), "detects the 'Not logged in' result text")
    check(clean_room.is_auth_failure(assistant + "\n" + result), "detects it in a full trace")


def test_is_auth_failure_does_not_fire_on_a_healthy_trace() -> None:
    healthy = (
        '{"type":"system","subtype":"init","tools":["Skill","Task"]}\n'
        '{"type":"assistant","message":{"content":[{"type":"tool_use","name":"Skill",'
        '"input":{"command":"sde-ladder"}}]}}\n'
        '{"type":"result","subtype":"success","is_error":false,"result":"done"}'
    )
    check(not clean_room.is_auth_failure(healthy), "no false positive on a healthy trace")


def main() -> int:
    tests = [
        test_clean_env_copies_only_the_credentials,
        test_clean_env_is_removed_even_when_the_body_raises,
        test_missing_credentials_raises_instead_of_running,
        test_is_auth_failure_recognises_a_real_not_logged_in_trace,
        test_is_auth_failure_does_not_fire_on_a_healthy_trace,
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
```

- [ ] **Step 2: Run it and watch it fail**

```bash
py -3 evals/test_clean_room.py
```

Expected: `ModuleNotFoundError: No module named 'clean_room'`. That is the correct red — the module does not exist yet.

- [ ] **Step 3: Write `evals/clean_room.py`**

```python
#!/usr/bin/env python3
"""Isolate a harness trial from the operator's machine.

Both harnesses shell out to `claude -p ...`. With no explicit `env`, that inherits the operator's
entire Claude Code install: ~/.claude/skills, ~/.claude/agents, installed plugins (which may ship
those same skills AGAIN), and the operator's global CLAUDE.md. Those do not shadow the fleet by name
-- they COMPETE with it for skill discovery, which is the one thing discovery_probe.py exists to
measure. Every number it ever produced described the LAPTOP, not the fleet, and every recorded
baseline says so ("treat as a LOWER BOUND").

CLAUDE_CONFIG_DIR relocates the whole user config -- "If you set CLAUDE_CONFIG_DIR, every ~/.claude
path on this page lives under that directory instead" (code.claude.com/docs/en/claude-directory).
Point it at a temp dir holding ONLY the credentials and the model sees the project's .claude/ and
nothing else. Probed: sde-ladder (project) YES / eng-ladder (personal) NO / backend-craft
(personal + plugin) NO.

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
import tempfile
from pathlib import Path

CREDENTIALS = ".credentials.json"

# Markers of an auth failure in a trial's output.
# NOT `subtype`: the result event of a not-logged-in run says subtype="success" while is_error=true.
AUTH_MARKERS = ("authentication_failed", "Not logged in")


class AuthUnavailable(RuntimeError):
    """Fatal: the harness cannot produce a valid measurement. Never scored as a result."""


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
            f"{CREDENTIALS}."
        )
    return p


def is_auth_failure(text: str) -> bool:
    """True if a trial's output shows the run never authenticated."""
    return any(m in (text or "") for m in AUTH_MARKERS)


@contextlib.contextmanager
def clean_env():
    """Yield an env whose CLAUDE_CONFIG_DIR holds ONLY the credentials.

    The model then sees the project's .claude/skills and .claude/agents and nothing else: no personal
    skills, no personal agents, no installed plugins, no personal CLAUDE.md.
    """
    creds = require_credentials()
    tmp = Path(tempfile.mkdtemp(prefix="fleet-cleanroom-"))
    try:
        os.chmod(tmp, stat.S_IRWXU)                      # 0700 -- it holds an auth secret
        dst = tmp / CREDENTIALS
        shutil.copyfile(creds, dst)
        os.chmod(dst, stat.S_IRUSR | stat.S_IWUSR)       # 0600
        yield dict(os.environ, CLAUDE_CONFIG_DIR=str(tmp))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
```

- [ ] **Step 4: Run the tests and watch them pass**

```bash
py -3 evals/test_clean_room.py
```

Expected: `test_clean_room: 13/13 checks passed.` then `OK`.

- [ ] **Step 5: Commit**

```bash
git add evals/clean_room.py evals/test_clean_room.py
git commit -m "evals: add the clean room -- isolate a trial from the operator's machine

CLAUDE_CONFIG_DIR pointed at a temp dir holding only the credentials makes the
model see the project's .claude/ and nothing else. Probed: project sde-ladder
YES; personal eng-ladder NO; personal-and-plugin backend-craft NO.

Refuses rather than degrades. A credential-less run still emits a valid
stream-json trace and exits 1 with 'Not logged in' buried in the result event,
which a harness would score as a clean no-route -- turning its own breakage into
a fake finding about the fleet."
```

---

### Task 2: Wire the clean room into `discovery_probe.py`, and make it abort

**Files:**
- Modify: `evals/discovery_probe.py` — `run_trial()`, `discovery_rate()`, `main()`, module docstring
- Modify: `evals/test_clean_room.py` — add the regression test

**Interfaces:**
- Consumes: `clean_room.clean_env()`, `clean_room.is_auth_failure()`, `clean_room.AuthUnavailable`.
- Produces: `run_trial(prompt, settings, timeout, env=None)` and `discovery_rate(scenario, settings, trials, timeout, env=None)` — Task 3 mirrors this shape in `run_evals.py`.

The existing `run_trial` already *notices* a failing runner (it prints `[runner error rc=...]` and its comment even names "auth failure") — and then returns the parsed stream anyway, so the trial is still scored. That is the fail-open being closed.

- [ ] **Step 1: Write the failing regression test**

Append to `evals/test_clean_room.py` (and add both new functions to the `tests = [...]` list in its `main()`):

```python
def test_discovery_probe_passes_the_clean_env_to_subprocess() -> None:
    """If a future edit drops env=, the harness silently goes back to measuring the laptop.
    This is the tripwire for that."""
    import subprocess
    import unittest.mock as mock

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import discovery_probe  # noqa: E402

    fake = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    with mock.patch.object(discovery_probe.subprocess, "run", return_value=fake) as m:
        discovery_probe.run_trial("hi", None, 10, env={"CLAUDE_CONFIG_DIR": "/tmp/room"})
    kwargs = m.call_args.kwargs
    check("env" in kwargs and kwargs["env"] is not None,
          "run_trial passes env= to subprocess.run (else isolation is silently gone)")
    check((kwargs.get("env") or {}).get("CLAUDE_CONFIG_DIR") == "/tmp/room",
          "run_trial forwards CLAUDE_CONFIG_DIR unchanged")


def test_discovery_probe_aborts_on_an_auth_failure_trace() -> None:
    """The trial must ERROR, never be scored as a no-route."""
    import subprocess
    import unittest.mock as mock

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import discovery_probe  # noqa: E402

    # A real credential-less run: exit 1, a VALID stream-json trace, no Skill() call.
    trace = (
        '{"type":"system","subtype":"init"}\n'
        '{"type":"assistant","error":"authentication_failed"}\n'
        '{"type":"result","subtype":"success","is_error":true,"result":"Not logged in"}'
    )
    fake = subprocess.CompletedProcess(args=[], returncode=1, stdout=trace, stderr="")
    with mock.patch.object(discovery_probe.subprocess, "run", return_value=fake):
        try:
            discovery_probe.run_trial("hi", None, 10, env={"CLAUDE_CONFIG_DIR": "/tmp/room"})
            check(False, "auth-failure trace must raise, NOT return a scoreable (empty) result")
        except clean_room.AuthUnavailable:
            check(True, "auth-failure trace raises AuthUnavailable instead of scoring a no-route")
```

- [ ] **Step 2: Run and watch both fail**

```bash
py -3 evals/test_clean_room.py
```

Expected: the env test fails (`run_trial()` takes no `env` argument → `TypeError`) and the abort test fails (it returns an empty result instead of raising). Both are the correct red.

- [ ] **Step 3: Change `run_trial()`**

Replace the whole function in `evals/discovery_probe.py`:

```python
def run_trial(prompt: str, settings: str | None, timeout: int,
              env: dict[str, str] | None = None) -> dict[str, list[str]]:
    claude = os.environ.get("CLAUDE_BIN", "claude")
    cmd = [claude, "-p", prompt, "--output-format", "stream-json", "--verbose"]
    if settings:
        cmd += ["--settings", settings]
    try:
        # encoding/errors: text=True alone decodes with the locale codec (cp1252 on Windows), which
        # dies on non-latin-1 bytes in the model's output and yields stdout=None. Force UTF-8.
        # env: the CLEAN ROOM (clean_room.clean_env()). Without it this inherits the operator's
        # ~/.claude -- personal skills, personal agents, installed plugins -- which COMPETE with the
        # fleet for discovery, i.e. we would be measuring the laptop.
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False,
            encoding="utf-8", errors="replace", env=env,
        )
    except subprocess.TimeoutExpired as e:
        # A delegation may have been emitted BEFORE the (slow-subagent) timeout — parse the
        # partial trace rather than scoring a real routing decision as a miss.
        out = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode("utf-8", "replace")
        if clean_room.is_auth_failure(out):
            raise clean_room.AuthUnavailable(_AUTH_FAILED_MSG)
        print(f"    [runner timeout after {timeout}s — parsing partial trace]", file=sys.stderr)
        return _invocations_from_stream(out)

    # FAIL LOUD. A credential-less run exits 1 but still emits a VALID stream-json trace with no
    # Skill() call -- and puts "Not logged in" in the RESULT event, not on stderr (stderr carries an
    # unrelated stdin warning). Parsing it yields a clean NO-ROUTE. Every scenario would "fail" and
    # the report would read as a devastating finding about the fleet rather than a broken instrument.
    if clean_room.is_auth_failure(proc.stdout) or clean_room.is_auth_failure(proc.stderr):
        raise clean_room.AuthUnavailable(_AUTH_FAILED_MSG)

    if proc.returncode != 0:
        # Surface a failing runner instead of silently scoring it as a miss
        # (a bad --settings payload would otherwise corrupt results).
        print(f"    [runner error rc={proc.returncode}] {proc.stderr.strip()[:300]}", file=sys.stderr)
    return _invocations_from_stream(proc.stdout)
```

Add near the top of the module, after the imports:

```python
import clean_room

_AUTH_FAILED_MSG = (
    "a trial came back UNAUTHENTICATED. This is fatal, not a result: the trace is well-formed and "
    "contains no Skill() call, so scoring it would report a no-route -- a fake finding about the "
    "fleet caused by a broken instrument. Run `claude` and /login, then re-run."
)
```

`discovery_probe.py` lives in `evals/`, and `clean_room.py` sits beside it, so a plain `import clean_room` resolves when the script is run as `python3 evals/discovery_probe.py` (its directory is on `sys.path`). `evals/test_graders.py` already relies on this same sibling-import pattern (`import graders`).

- [ ] **Step 4: Thread `env` through `discovery_rate()` and open the room in `main()`**

In `discovery_rate`, change the signature and the one call site:

```python
def discovery_rate(scenario: dict, settings: str | None, trials: int, timeout: int,
                   env: dict[str, str] | None = None) -> tuple[int, list[list[str]]]:
```

and inside the loop:

```python
        full = run_trial(scenario["prompt"], settings, timeout, env=env)
```

In `main()`, wrap **only the `--run` / `--ab` paths** (the ones that invoke a model) so `--validate` and `--list` stay dependency-free and credential-free:

```python
    with clean_room.clean_env() as env:
        ...  # the existing per-scenario loop, passing env=env into discovery_rate(...)
```

- [ ] **Step 5: Run the tests and watch them pass**

```bash
py -3 evals/test_clean_room.py
py -3 evals/test_discovery_probe.py
py -3 evals/run_evals.py --validate
py -3 evals/discovery_probe.py --validate
```

Expected: all OK. `--validate` must still work **with no credentials present** — it invokes no model, so it must not touch the clean room. If `--validate` now demands credentials, the wrapping in Step 4 is too broad; narrow it.

- [ ] **Step 6: Prove the abort fires end-to-end, not just in a mock**

```bash
EMPTY=$(mktemp -d)
CLAUDE_CONFIG_DIR="$EMPTY" py -3 evals/discovery_probe.py --run --match craft-sde-ladder --trials 1
echo "exit=$?"
rm -rf "$EMPTY"
```

Expected: it **aborts immediately** with the `AuthUnavailable` message and a non-zero exit — and reports **zero** scenario results. It must NOT print a discovery rate of 0%. Paste this output into the commit; it is the evidence that the guard fires.

- [ ] **Step 7: Commit**

```bash
git add evals/discovery_probe.py evals/test_clean_room.py
git commit -m "discovery_probe: run trials in the clean room, and abort on auth failure

run_trial called subprocess.run with no env=, inheriting the operator's ~/.claude
-- 9 personal skills, 7 personal agents, and installed plugins shipping those
same skills again -- all of which COMPETE with the fleet for discovery. Every
number this probe produced described the laptop.

It also failed open: a credential-less run exits 1 but emits a valid stream-json
trace with no Skill() call, so the trial scored as a clean no-route. Every
scenario would 'fail' and the report would read as a finding about the fleet.
Now it raises AuthUnavailable before a single result is recorded.

A regression test asserts run_trial passes CLAUDE_CONFIG_DIR -- drop it and the
harness silently goes back to measuring the machine."
```

---

### Task 3: Wire the clean room into `run_evals.py`, and make it abort

**Files:**
- Modify: `evals/run_evals.py` — `run_agent()`, its caller, `main()`
- Modify: `evals/test_clean_room.py` — add one regression test

**Interfaces:**
- Consumes: `clean_room.clean_env()`, `clean_room.is_auth_failure()`, `clean_room.AuthUnavailable`.
- Produces: `run_agent(prompt, target, env=None) -> str`.

`run_evals` fails open differently: on `rc != 0` it **returns the error string as the model's response**, which is then fed to the text graders. An auth failure therefore produces a plausible-looking mixed grade rather than an error.

- [ ] **Step 1: Write the failing test**

Append to `evals/test_clean_room.py` (and add it to the `tests = [...]` list):

```python
def test_run_evals_aborts_on_auth_failure_instead_of_grading_the_error_string() -> None:
    import subprocess
    import unittest.mock as mock

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import run_evals  # noqa: E402

    fake = subprocess.CompletedProcess(
        args=[], returncode=1, stdout="Not logged in · Please run /login", stderr="",
    )
    with mock.patch.object(run_evals.subprocess, "run", return_value=fake) as m:
        try:
            run_evals.run_agent("hi", "sde-ladder", env={"CLAUDE_CONFIG_DIR": "/tmp/room"})
            check(False, "auth failure must raise, NOT return a string for the graders to score")
        except clean_room.AuthUnavailable:
            check(True, "run_agent raises AuthUnavailable instead of returning an error string")
    kwargs = m.call_args.kwargs
    check((kwargs.get("env") or {}).get("CLAUDE_CONFIG_DIR") == "/tmp/room",
          "run_agent passes the clean env to subprocess.run")
```

- [ ] **Step 2: Run and watch it fail**

```bash
py -3 evals/test_clean_room.py
```

Expected: `TypeError` (no `env` parameter) — the correct red.

- [ ] **Step 3: Change `run_agent()`**

```python
def run_agent(prompt: str, target: str, env: dict[str, str] | None = None) -> str:
    """Invoke the fleet in a fresh session. Replace with the Agent SDK if preferred.

    `env` is the CLEAN ROOM (clean_room.clean_env()): without it this inherits the operator's
    ~/.claude -- personal skills, personal agents, installed plugins, personal CLAUDE.md -- and the
    suite grades output produced under the influence of a fleet that is not this one.
    """
    claude = os.environ.get("CLAUDE_BIN", "claude")
    hint = f"(Use the {target} skill/agent.)\n\n" if target else ""
    proc = subprocess.run(
        [claude, "-p", hint + prompt],
        capture_output=True, text=True, timeout=300, check=False,
        # Decode as UTF-8 explicitly: text=True alone uses the locale codec, which on Windows is
        # cp1252 and dies on the em-dashes/box-drawing the fleet emits. The reader thread then
        # raises, stdout comes back None, and the grader fails with a confusing AttributeError.
        encoding="utf-8", errors="replace", env=env,
    )
    # FAIL LOUD. Returning the error string here would hand it to the TEXT graders, which would
    # score it -- an auth failure would come back as a plausible-looking scenario failure.
    if clean_room.is_auth_failure(proc.stdout) or clean_room.is_auth_failure(proc.stderr):
        raise clean_room.AuthUnavailable(
            "a trial came back UNAUTHENTICATED. This is fatal, not a result: the error text would "
            "otherwise be graded as if it were the fleet's answer. Run `claude` and /login."
        )
    if proc.returncode != 0:
        return f"[runner error rc={proc.returncode}] {proc.stderr.strip()}"
    return proc.stdout
```

Add `import clean_room` beside the other imports.

- [ ] **Step 4: Open the room around the `--run` path only**

In `main()`, wrap the scenario loop that calls `run_agent` in `with clean_room.clean_env() as env:` and pass `env=env` at the call site. Leave `--validate` and `--list` outside it: they invoke no model and are CI gates that must run without credentials.

- [ ] **Step 5: Run everything and watch it pass**

```bash
py -3 evals/test_clean_room.py
py -3 evals/test_graders.py
py -3 evals/test_discovery_probe.py
py -3 evals/run_evals.py --validate
```

Expected: all OK. `--validate` must still pass with no credentials.

- [ ] **Step 6: Prove the abort fires end-to-end**

```bash
EMPTY=$(mktemp -d)
CLAUDE_CONFIG_DIR="$EMPTY" py -3 evals/run_evals.py --run --match agent-security-injection --trials 1
echo "exit=$?"
rm -rf "$EMPTY"
```

Expected: aborts with `AuthUnavailable`, non-zero exit, **zero graded scenarios**. Paste the output into the commit.

- [ ] **Step 7: Commit**

```bash
git add evals/run_evals.py evals/test_clean_room.py
git commit -m "run_evals: run trials in the clean room, and abort on auth failure

Same inheritance bug as discovery_probe (no env=), plus its own fail-open: on a
non-zero exit it RETURNED the error string as the model's response, which the
text graders then scored -- so an auth failure came back as a plausible scenario
failure rather than a broken run."
```

---

### Task 4: Honest baselines + the scenario that measures the real question

**Files:**
- Create: `evals/discovery/capability-sde-engineer-reaches-ladder.yaml`
- Modify: every `evals/discovery/*.yaml` that has a `note:` — annotate the namespace
- Modify: `evals/README.md` — document the clean room and the baseline convention

**Interfaces:** none consumed; Task 5 runs the scenario created here.

- [ ] **Step 1: Create the new capability scenario**

`evals/discovery/capability-sde-engineer-reaches-ladder.yaml`:

```yaml
id: capability-sde-engineer-reaches-ladder
expected_agent: sde-engineer
# The question the preload decision actually rests on -- and one NO existing scenario asks.
#
# `craft-sde-ladder` measures MAIN-SESSION routing to the skill (expected: sde-ladder,
# also_acceptable: [sde-engineer]) -- it passes if the main session merely delegates to the agent.
# That is a different question, and it is exactly the false pass we must not take.
#
# `agent_must_reach_skill` demands that the DELEGATED AGENT invoke the skill ITSELF, proven via the
# stream's `parent_tool_use_id` (None = main session; an id = a subagent, under that Task call).
#
# WHY IT MATTERS: the ladder skills SET ALTITUDE ON EVERY TASK (CLAUDE.md). sde-engineer preloads
# none of its 15 skills and is merely TOLD to "load the skill" -- an instruction, and instructions
# bend. If it does not, the agent silently works at no altitude and nothing ever reports it.
#
# The prompt must be a real BUILD request (so sde-engineer is the right target), non-trivial enough
# that altitude genuinely matters (so loading the ladder is correct, not ceremony), and it must NOT
# name a skill, a ladder, a tier, or the word "design" -- naming any of them hands the agent the
# answer and turns a discovery probe into a compliance probe.
agent_must_reach_skill: sde-ladder
prompt: |
  The checkout service and the payments service both read the order table directly. I want to put
  an API in front of it so only payments owns the writes. Get started on it.
note: "namespace: NOT YET BASELINED — take a CLEAN baseline before acting on this scenario."
```

Note `agent_must_reach_skill` is set to the **skill name**, not `true`: `discovery_rate()` supports both (`bool(reached) if must_reach is True else must_reach in reached`), and naming it is what makes this a test of *the ladder specifically* rather than of "any skill at all."

- [ ] **Step 2: Verify it parses and its target resolves**

```bash
py -3 evals/discovery_probe.py --validate
```

Expected: the suite validates and the count rises by one (45 scenarios). If `sde-engineer` or `sde-ladder` did not resolve, this fails — that is the check doing its job.

- [ ] **Step 3: Annotate every contaminated baseline**

Every existing `note:` in `evals/discovery/*.yaml` records a number measured on a namespace polluted by the operator's skills. Prefix each with the namespace it was taken in, so it can never be silently read as a clean number. Mechanically:

```bash
py -3 - <<'PY'
import pathlib, re
n = 0
for p in sorted(pathlib.Path("evals/discovery").glob("*.yaml")):
    t = p.read_text(encoding="utf-8")
    if 'note: "' not in t or "namespace:" in t:
        continue
    t = t.replace('note: "', 'note: "namespace: CONTAMINATED (pre-clean-room; personal ~/.claude '
                             'skills+agents and installed plugins were visible and competing — NOT '
                             'comparable to a clean number). ', 1)
    p.write_text(t, encoding="utf-8", newline="")
    n += 1
print(f"annotated {n} scenario notes")
PY
py -3 evals/discovery_probe.py --validate
```

Expected: it annotates the scenarios that carry notes, and `--validate` still passes.

- [ ] **Step 4: Document the convention in `evals/README.md`**

Add a section:

```markdown
## The clean room (and why a baseline states its namespace)

Every trial runs with `CLAUDE_CONFIG_DIR` pointed at a temp dir holding only your credentials
(`evals/clean_room.py`). The model therefore sees this project's `.claude/skills` and
`.claude/agents` and **nothing else** — not your personal `~/.claude` skills or agents, not your
installed plugins, not your global `CLAUDE.md`.

This is not tidiness. Those things do not shadow the fleet by name; they **compete with it for
discovery**, which is the one thing `discovery_probe.py` measures. Before the clean room, every
number it produced was a property of the machine it ran on — and every baseline note said so
("treat as a LOWER BOUND").

**A baseline note must state the namespace it was taken in.** A number without one is not a
baseline. Notes marked `namespace: CONTAMINATED` predate the clean room and are not comparable to
clean numbers.

The harness **aborts** if it cannot authenticate. It does not degrade: a credential-less run still
emits a well-formed trace containing no `Skill()` call, which would score as a clean no-route —
turning a broken instrument into a fake finding about the fleet.
```

- [ ] **Step 5: Commit**

```bash
git add evals/discovery evals/README.md
git commit -m "evals: mark the contaminated baselines, and measure the real question

Every recorded baseline was taken on a namespace polluted by the operator's
personal skills and plugins; they are now annotated as such and are not
comparable to clean numbers.

Adds capability-sde-engineer-reaches-ladder: no existing scenario asks whether
the DELEGATED sde-engineer invokes its ladder itself. craft-sde-ladder measures
main-session routing and passes if the session merely delegates to the agent --
the exact false pass agent_must_reach_skill exists to kill."
```

---

### Task 5: Take the clean baselines (live model — slow, not CI)

**Files:**
- Modify: `evals/discovery/craft-sde-ladder.yaml`, `evals/discovery/obs-sre-ladder.yaml`,
  `evals/discovery/agent-reaches-skill.yaml`, `evals/discovery/capability-sde-engineer-reaches-ladder.yaml` — the `note:` fields only

**Interfaces:** consumes the clean room from Tasks 2–4.

This task invokes a **live model**. It is not CI-gated and it is slow — agent-routing scenarios spawn a real subagent that does real work (**minutes each**). Scope every run with `--match`. Do not run the whole suite.

- [ ] **Step 1: Confirm you are authenticated**

```bash
py -3 -c "import sys; sys.path.insert(0,'evals'); import clean_room; print('creds:', clean_room.require_credentials())"
```

Expected: it prints the credentials path. If it raises `AuthUnavailable`, run `claude` and `/login` first — do not proceed.

- [ ] **Step 2: Baseline the two ladder scenarios (skill routing)**

```bash
py -3 evals/discovery_probe.py --run --match sde-ladder --trials 5 --timeout 300
py -3 evals/discovery_probe.py --run --match sre-ladder --trials 5 --timeout 300
```

Record, per scenario: **hit / misroute / no-route** and the `saw:` list.

- [ ] **Step 3: Baseline the two capability probes (agent must reach skill — SLOW)**

```bash
py -3 evals/discovery_probe.py --run --match agent-reaches-skill --trials 3 --timeout 900
py -3 evals/discovery_probe.py --run --match capability-sde-engineer-reaches-ladder --trials 3 --timeout 900
```

These spawn real subagents. Minutes per trial. Raise `--timeout`, do not lower `--trials` below 3.

- [ ] **Step 4: Record the clean baselines in the `note:` fields**

Replace the `note:` on each of the four scenarios with the real numbers, in this exact shape:

```yaml
note: "namespace: CLEAN (clean_room; only this project's .claude/ visible). 2026-07-13 baseline (n=5): 3 hit / 0 misroute / 2 no-route. saw: sde-ladder, sde-engineer."
```

Use the actual measured values. **Do not round, do not tidy, do not omit a bad number.**

- [ ] **Step 5: Interpret honestly — and read this before you do**

**The clean numbers may be WORSE than the contaminated ones. That is a legitimate outcome, not a bug in this change.** The old notes called themselves a "lower bound" on the assumption that foreign skills only ever *stole* discoveries. They may also have been *helping*: the operator's `eng-ladder` and `root-cause` could have been absorbing prompts the fleet handles badly, flattering it.

If the clean numbers drop, that is a **real finding about the fleet**. Do not "fix" it by reverting the clean room, widening `also_acceptable`, or softening a prompt. Record it and report it.

- [ ] **Step 6: Commit**

```bash
git add evals/discovery
git commit -m "evals: first CLEAN baselines for the ladder and capability scenarios

Measured with only this project's .claude/ visible. These are the first numbers
this harness has produced that describe the FLEET rather than the laptop it ran
on. <state whether they went up, down, or held versus the contaminated notes —
and if they dropped, say so plainly>"
```

---

### Task 6: Full verification, CI, and the PR

**Files:** none modified. This task produces evidence.

- [ ] **Step 1: Everything green**

```bash
py -3 scripts/validate_fleet.py
py -3 -m unittest discover -s scripts -p 'test_validate_fleet.py'
py -3 scripts/test_readonly_guard.py
py -3 evals/test_clean_room.py
py -3 evals/test_graders.py
py -3 evals/test_discovery_probe.py
py -3 evals/run_evals.py --validate
py -3 evals/discovery_probe.py --validate
```

Record each command's **actual output**. A completion claim without it is not a completion claim.

- [ ] **Step 2: Add the new test to CI**

`.github/workflows/validate.yml` already runs the eval graders. Add `clean_room`'s tests beside them, **after** the `Install eval-harness deps` step (it is stdlib-only, but keeping the eval tests together is clearer and costs nothing):

```yaml
      - name: Test the eval graders
        run: |
          ${{ matrix.py }} evals/test_graders.py
          ${{ matrix.py }} evals/test_discovery_probe.py
          ${{ matrix.py }} evals/test_clean_room.py
```

- [ ] **Step 3: Confirm `--validate` still runs without credentials**

This is the check that the clean room did not accidentally become a CI dependency:

```bash
EMPTY=$(mktemp -d)
CLAUDE_CONFIG_DIR="$EMPTY" py -3 evals/run_evals.py --validate; echo "run_evals --validate exit=$?"
CLAUDE_CONFIG_DIR="$EMPTY" py -3 evals/discovery_probe.py --validate; echo "discovery_probe --validate exit=$?"
rm -rf "$EMPTY"
```

Expected: **both exit 0.** They invoke no model, so they must not require credentials. If either now demands them, CI will break on every runner — narrow the `clean_env()` wrapping to the `--run`/`--ab` paths only.

- [ ] **Step 4: Push and open the PR**

```bash
git push -u origin fix/eval-clean-room
gh pr create --base main --title "fix(evals): the harness was measuring the laptop, not the fleet" --body "<summary + the abort evidence + the clean baselines>"
```

The PR body must state, plainly: what the clean baselines came out at, and whether they went **down**.

- [ ] **Step 5: Watch CI**

```bash
gh pr checks <N> --watch
```

Expected: green on ubuntu, macos, windows, and the plugin-contract job.

---

## Notes for the implementer

- **The most important line in this plan is "watch the abort fire."** Tasks 2 and 3 each have an end-to-end step that points the harness at a credential-less config dir and asserts it *aborts* rather than reporting a suite of no-routes. Do not skip them. A guard never seen firing is not a guard — and this one exists to stop the harness from lying about the fleet.
- **`--validate` must never need credentials.** It is a CI gate and runs on machines with no `~/.claude` at all. If you find yourself adding a credentials check to it, you have wrapped `clean_env()` too broadly.
- **Do not use the trace's `subtype` field to detect health.** A not-logged-in run emits `{"type":"result","subtype":"success","is_error":true,...}`. It says *success*. Key on `is_error` / the auth markers instead.
- **Do not preload any skill into any agent in this PR.** That decision is the follow-on and is deliberately gated behind the clean baseline you are producing.
