"""Probes of the live checkout: files the candidate wrote, and model-written commands run for grading."""

from __future__ import annotations

import os
import re
import subprocess

import clean_room

from .. import constants, invocation, workspaces
from ..outcomes import Outcome, Polarity, instrument, unmeasured, verdict
from . import registry
from .registry import Context, Need, Params


def grading_env(ctx: Context) -> dict[str, str]:
    """The env the probe uses to execute model-written code: the clean room's allowlist, not the operator's shell."""
    keys = set(clean_room.SAFE_ENV_KEYS) | {
        "PATH",
        "PATHEXT",
        "SYSTEMROOT",
        "WINDIR",
        "COMSPEC",
        "TEMP",
        "TMP",
        "HOME",
        "LANG",
        "PYTHONIOENCODING",
        "PYTHONUTF8",
    }
    env = {k: v for k, v in os.environ.items() if k in keys or k.upper() in keys}
    env["HARNESS_STATE_DIR"] = str(ctx.ws.state_dir)
    for key, value in workspaces.declared_env(ctx.spec).items():
        env[str(key)] = workspaces.service_value(workspaces.fixture_value(str(value), ctx.ws), ctx.services)
    workspaces.set_trial_temp(env, ctx.ws)
    return env


def _run(ctx: Context, command: str, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    """Execute model-written code for grading on the host, under the clean-room env."""
    return invocation.run_command(
        command,
        cwd=str(ctx.ws.repo),
        timeout=timeout,
        env=grading_env(ctx),
    )


@registry.declare("file_exists", Polarity.REQUIRES, needs={Need.CHECKOUT}, required=("path",), kind=registry.Kind.PROBE)
def check_file_exists(ctx: Context, p: Params) -> Outcome:
    ok = (ctx.ws.repo / p["path"]).is_file()
    return verdict(ok, f"{p['path']} {'present' if ok else 'missing'}")


@registry.declare(
    "glob_exists", Polarity.REQUIRES, needs={Need.CHECKOUT}, required=("pattern",), kind=registry.Kind.PROBE
)
def check_glob_exists(ctx: Context, p: Params) -> Outcome:
    hits = [x.relative_to(ctx.ws.repo).as_posix() for x in ctx.ws.repo.glob(p["pattern"])]
    return verdict(bool(hits), f"{p['pattern']} -> {hits or 'no match'}")


@registry.declare(
    "file_contains", Polarity.REQUIRES, needs={Need.CHECKOUT}, required=("path", "needle"), kind=registry.Kind.PROBE
)
def check_file_contains(ctx: Context, p: Params) -> Outcome:
    target = ctx.ws.repo / p["path"]
    if not target.is_file():
        return verdict(False, f"{p['path']} missing")
    ok = p["needle"] in target.read_text(encoding="utf-8", errors="replace")
    return verdict(ok, f"{p['needle']!r} {'found' if ok else 'absent'} in {p['path']}")


def _stage_writes(ctx: Context, p: Params) -> str | None:
    """Put the check's probe-owned files in the workspace; the reason it could not, or None.

    `writes:` carries the content inline. `writes_from:` names a file under `evals/oracles/`
    instead, so an oracle long enough to be a program lives on disk -- reviewable, runnable, and
    counted by the evals line ceiling -- rather than as a YAML block scalar that escapes both.
    """
    staged = dict(p.get("writes") or {})
    writes_from = p.get("writes_from")
    shape = registry.writes_from_shape_problem(writes_from) if writes_from is not None else None
    if shape:
        return shape
    for name, rel in (writes_from or {}).items():
        source = constants.oracle_source(rel)
        if source is None:
            return f"writes_from source {rel!r} must be a file under evals/oracles/"
        staged[name] = source.read_text(encoding="utf-8")
    for name, content in staged.items():
        problem = registry.probe_write_path_problem(name)
        if problem:
            return problem
        (ctx.ws.repo / name).write_text(content, encoding="utf-8")
    return None


def _staged_run(ctx: Context, p: Params) -> subprocess.CompletedProcess[str] | Outcome:
    """Stage the check's own files and run its command: the finished process, or the outcome that
    ends the check. A file the check cannot stage is misconfiguration, never the candidate (result
    rule 5); a command that outlives its timeout fails."""
    problem = _stage_writes(ctx, p)
    if problem:
        return instrument(problem)
    try:
        return _run(ctx, p["command"], timeout=int(p.get("timeout", 180)))
    except subprocess.TimeoutExpired:
        return verdict(False, f"{p['command']!r} timed out")


@registry.declare(
    "command_exit_zero",
    Polarity.REQUIRES,
    needs={Need.CHECKOUT},
    names_unmeasured=True,
    required=("command",),
    optional=("timeout", "writes", "writes_from", "failure_exit_code"),
    kind=registry.Kind.PROBE,
)
def check_command_exit_zero(ctx: Context, p: Params) -> Outcome:
    """Zero passes. A declared `inconclusive_exit_code` is an unavailable measurement. With a declared
    `failure_exit_code`, only that code fails the candidate, and any other nonzero exit, such as an
    oracle's own uncaught exception, is an instrument failure (AC-24); without one, every nonzero exit fails."""
    proc = _staged_run(ctx, p)
    if isinstance(proc, Outcome):
        return proc
    tail = (proc.stdout + proc.stderr).strip()[-300:].replace("\n", " | ")
    evidence = f"{p['command']!r} exit {proc.returncode}: {tail}"
    unavailable = p.get("inconclusive_exit_code")
    if type(unavailable) is int and 1 <= unavailable <= 255 and proc.returncode == unavailable:
        return unmeasured(evidence)
    failure = p.get("failure_exit_code")
    if type(failure) is int and 1 <= failure <= 255 and proc.returncode not in (0, failure):
        return instrument(f"{evidence} (not the declared failure exit {failure})")
    return verdict(proc.returncode == 0, evidence)


@registry.declare(
    "command_output_regex",
    Polarity.REQUIRES,
    needs={Need.CHECKOUT},
    required=("command", "pattern"),
    optional=("timeout", "writes", "writes_from"),
    kind=registry.Kind.PROBE,
)
def check_command_output_regex(ctx: Context, p: Params) -> Outcome:
    """An independent oracle: run a command on probe-owned input and require its stdout to match.

    The model wrote both the implementation and its tests, so a suite that is green when the probe
    runs it proves only that the two agree with each other; this check pins the behaviour to an
    input and answer the model never saw.
    """
    proc = _staged_run(ctx, p)
    if isinstance(proc, Outcome):
        return proc
    m = re.search(p["pattern"], proc.stdout, re.IGNORECASE | re.DOTALL)
    ok = proc.returncode == 0 and m is not None
    return verdict(
        ok,
        f"{p['command']!r} exit {proc.returncode}; stdout {proc.stdout.strip()[:200]!r}; /{p['pattern'][:60]}/ {'matched' if m else 'no match'}",
    )
