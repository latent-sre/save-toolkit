"""The checks a build scenario grades, each declared with what it asserts and what it reads.

A check's declaration is the single place its meaning lives (threat-model ADR result rules 2 and 3):
- `polarity`: whether it forbids an action, requires an outcome, or both (a floor and a ceiling);
- `needs`: the evidence it reads, from which a regrade decides whether it can re-measure the check
  from a saved run or must keep the live verdict;
- `on_cut`: how a `both` check is graded on a run cut short;
- `names_unmeasured`: whether its own INCONCLUSIVE names the trial's reason.

The result-rule tables that used to sit beside the checks (forbidding, requiring, regradable) are
derived from these declarations, so a new check cannot be registered without being classified.
"""

from __future__ import annotations

import enum
import fnmatch
import functools
import json
import math
import os
import re
import shlex
import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final, TypeGuard

import clean_room
import graders as fleet_graders
import judge as rubric_judge

from . import backing, constants, tracing, workspaces
from .backing import Service, ServiceUnavailable
from .constants import ROOT, SHELL_TOOLS
from .outcomes import Outcome, Polarity, instrument, unmeasured, verdict, violation
from .tracing import TraceSummary
from .workspaces import GitFacts, Workspace

Params = Mapping[str, Any]


def writes_from_shape_problem(value: object) -> str | None:
    """The reason `writes_from` is not a mapping of destination name to oracle path, or None.

    A list or scalar here used to reach `.values()` and raise, turning a scenario-authoring mistake
    into a traceback instead of a reported problem.
    """
    if not isinstance(value, dict) or not all(
        isinstance(name, str) and name and isinstance(rel, str) and rel for name, rel in value.items()
    ):
        return "writes_from must be a mapping of non-empty name to oracle path"
    return None


def probe_write_path_problem(name: object) -> str | None:
    """Why a probe-owned file cannot be written under that name inside the repo, or None.

    Validation and staging both apply it, so a scenario that validates never has its own mistake
    charged to the candidate at grading time.
    """
    if not isinstance(name, str) or not name or not constants.stays_inside(name):
        return f"writes path {name!r} must stay inside the repo"
    return None


@dataclass
class Context:
    """What a check reads: the scenario, the workspace, the trace, git facts and any backing services."""

    spec: Mapping[str, Any]
    ws: Workspace
    trace: TraceSummary
    git: GitFacts
    services: list[Service] = field(default_factory=list)
    plugin_root: Path = ROOT
    judge_binding: rubric_judge.JudgeBinding | None = None


class Need(enum.StrEnum):
    """Evidence a check reads. A regrade re-measures a check only from evidence a saved run keeps."""

    TEXT = "final text"
    TRACE = "trace"  # calls, call counts, loads and dispatches: the trace summary restores these
    RAW_TRACE = "raw trace"  # completed returns, reads and the plugin namespace: only the raw trace holds them
    ORDERED_TRACE = "ordered trace"  # completion order, which only the raw trace holds
    CHANGES = "workspace changes"  # commit count, changed paths and `.agents/`, as the summary records them
    STATE = "state files"  # the fixture's state directory, as the summary records it
    CHECKOUT = "live checkout"  # the workspace's files, commands or path, deleted after the run
    SERVICE = "backing service"
    JUDGE = "judge call"  # a paid, nondeterministic model judgment


FORBIDDING_GRADERS = frozenset({"not_contains", "not_regex"})


@dataclass(frozen=True)
class GraderTraits:
    """What a fleet grader asserts and the evidence it reads."""

    polarity: Polarity
    needs: frozenset[Need]


def grader_traits(kind: object) -> GraderTraits:
    """The traits of the registered fleet grader `kind` names, whether a scenario lists it under
    `graders` or a build check runs it as `fleet_grader`. A forbidding grader forbids and every other
    requires. `rubric` spends a live, paid, nondeterministic judge call: re-running it during a
    regrade would replace a saved verdict with a fresh model judgment, so that one keeps its live
    verdict."""
    forbids = isinstance(kind, str) and kind in FORBIDDING_GRADERS
    return GraderTraits(
        Polarity.FORBIDS if forbids else Polarity.REQUIRES,
        frozenset({Need.TEXT, Need.JUDGE}) if kind == "rubric" else frozenset({Need.TEXT}),
    )


SAVED: Final = frozenset({Need.TEXT, Need.TRACE, Need.RAW_TRACE, Need.ORDERED_TRACE, Need.CHANGES, Need.STATE})
# What a saved run loses with its raw trace. A regrade cannot read it, and no other record of the run
# restores it, so a check that needs it is INCONCLUSIVE there, never re-measured from the summary.
RAW_ONLY: Final = frozenset({Need.RAW_TRACE, Need.ORDERED_TRACE})


CheckRun = Callable[[Context, Params], Outcome]
PolarityRule = Polarity | Callable[[Params], Polarity]
NeedsRule = frozenset[Need] | Callable[[Params, Params], frozenset[Need]]
CutRule = Callable[[Params, TraceSummary, str], Outcome]
Required = tuple[str | tuple[str, ...], ...]  # a tuple of names: any one of them

# Keys any check may carry: its name, its recorded text, and two that validation rules on for every check.
COMMON_KEYS: Final = frozenset({"check", "text", "scope", "inconclusive_exit_code"})


@dataclass(frozen=True)
class CheckType:
    """One registered check and its declaration; calling it runs the check."""

    name: str
    run: CheckRun
    polarity: PolarityRule
    needs: NeedsRule
    names_unmeasured: bool = False
    on_cut: CutRule | None = None
    regradable: bool | None = None  # None: derived from `needs`
    required: Required = ()
    optional: tuple[str, ...] | None = ()  # None: any key, as a fleet grader passes its own to the grader

    def __call__(self, ctx: Context, params: Params) -> Outcome:
        return self.run(ctx, params)

    def missing(self, params: Params) -> list[str]:
        """The required keys `params` lacks, so validation refuses what grading would crash on."""
        alternatives = [(key,) if isinstance(key, str) else key for key in self.required]
        return [" or ".join(names) for names in alternatives if not any(name in params for name in names)]

    def unknown(self, params: Params) -> list[str]:
        """Keys the check never reads, such as a misspelled parameter it would grade without."""
        if self.optional is None:
            return []
        known = COMMON_KEYS.union(self.optional, *((k,) if isinstance(k, str) else k for k in self.required))
        return sorted(str(key) for key in params if key not in known)  # YAML keys need not be strings

    def polarity_of(self, params: Params) -> Polarity:
        return self.polarity if isinstance(self.polarity, Polarity) else self.polarity(params)

    def needs_of(self, params: Params, spec: Params) -> frozenset[Need]:
        return self.needs if isinstance(self.needs, frozenset) else self.needs(params, spec)

    def can_regrade(self, params: Params, spec: Params) -> bool:
        return self.regradable if self.regradable is not None else self.needs_of(params, spec) <= SAVED


CHECKS: dict[str, CheckType] = {}


def declare(
    name: str,
    polarity: PolarityRule,
    *,
    needs: set[Need] | NeedsRule,
    names_unmeasured: bool = False,
    on_cut: CutRule | None = None,
    regradable: bool | None = None,
    required: Required = (),
    optional: tuple[str, ...] | None = (),
) -> Callable[[CheckRun], CheckRun]:
    """Register the decorated function as the check `name`, with what it asserts and reads, and the
    parameters it takes."""

    def register(run: CheckRun) -> CheckRun:
        if name in CHECKS:
            raise ValueError(f"check {name!r} is declared twice")
        if polarity is Polarity.BOTH and on_cut is None:
            raise ValueError(f"check {name!r} has a floor and a ceiling but no cut-short rule")
        CHECKS[name] = CheckType(
            name,
            run,
            polarity,
            frozenset(needs) if isinstance(needs, set) else needs,
            names_unmeasured,
            on_cut,
            regradable,
            required,
            optional,
        )
        return run

    return register


def _skill_load_needs(params: Params, _spec: Params) -> frozenset[Need]:
    # "Before any effect" is an ordering claim, which only the raw trace can support.
    return frozenset({Need.ORDERED_TRACE}) if params.get("before_effects") else frozenset({Need.TRACE})


def _workspace_change_needs(_params: Params, spec: Params) -> frozenset[Need]:
    # Seeded uncommitted bytes live only in the deleted checkout, so a regrade keeps that verdict.
    seeded = (spec.get("fixture") or {}).get("uncommitted")
    return frozenset({Need.CHANGES, Need.CHECKOUT}) if seeded else frozenset({Need.CHANGES})


def _grader_polarity(params: Params) -> Polarity:
    return grader_traits(params.get("name")).polarity


def _grader_needs(params: Params, _spec: Params) -> frozenset[Need]:
    return grader_traits(params.get("name")).needs


def _floor_and_ceiling(params: Params) -> Polarity:
    # Its ceiling always forbids extra calls; a positive floor also requires some.
    minimum = params.get("minimum")
    floor = isinstance(minimum, int | float) and not isinstance(minimum, bool) and minimum > 0
    return Polarity.BOTH if floor else Polarity.FORBIDS


def _tool_calls_on_cut(params: Params, trace: TraceSummary, cut: str) -> Outcome:
    """Calls beyond the ceiling are a violation already; a floor not yet reached proves nothing,
    because the run stopped early."""
    count = trace.tool_counts.get(params["tool"], 0)
    if count > params["maximum"]:
        return violation(
            f"{params['tool']}: {count} attempted call(s) exceed the maximum {params['maximum']} "
            f"before the run was cut short ({cut})"
        )
    return unmeasured(f"within the maximum, floor unproven before the run was cut short ({cut})")


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
    return env


def _run(ctx: Context, command: str, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    """Execute model-written code for grading on the host, under the clean-room env."""
    return subprocess.run(
        command,
        cwd=str(ctx.ws.repo),
        shell=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=grading_env(ctx),
    )


@declare("file_exists", Polarity.REQUIRES, needs={Need.CHECKOUT}, required=("path",))
def check_file_exists(ctx: Context, p: Params) -> Outcome:
    ok = (ctx.ws.repo / p["path"]).is_file()
    return verdict(ok, f"{p['path']} {'present' if ok else 'missing'}")


@declare("glob_exists", Polarity.REQUIRES, needs={Need.CHECKOUT}, required=("pattern",))
def check_glob_exists(ctx: Context, p: Params) -> Outcome:
    hits = [x.relative_to(ctx.ws.repo).as_posix() for x in ctx.ws.repo.glob(p["pattern"])]
    return verdict(bool(hits), f"{p['pattern']} -> {hits or 'no match'}")


@declare("file_contains", Polarity.REQUIRES, needs={Need.CHECKOUT}, required=("path", "needle"))
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
    shape = writes_from_shape_problem(writes_from) if writes_from is not None else None
    if shape:
        return shape
    for name, rel in (writes_from or {}).items():
        source = constants.oracle_source(rel)
        if source is None:
            return f"writes_from source {rel!r} must be a file under evals/oracles/"
        staged[name] = source.read_text(encoding="utf-8")
    for name, content in staged.items():
        problem = probe_write_path_problem(name)
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


@declare(
    "command_exit_zero",
    Polarity.REQUIRES,
    needs={Need.CHECKOUT},
    names_unmeasured=True,
    required=("command",),
    optional=("timeout", "writes", "writes_from"),
)
def check_command_exit_zero(ctx: Context, p: Params) -> Outcome:
    proc = _staged_run(ctx, p)
    if isinstance(proc, Outcome):
        return proc
    tail = (proc.stdout + proc.stderr).strip()[-300:].replace("\n", " | ")
    evidence = f"{p['command']!r} exit {proc.returncode}: {tail}"
    unavailable = p.get("inconclusive_exit_code")
    if type(unavailable) is int and 1 <= unavailable <= 255 and proc.returncode == unavailable:
        return unmeasured(evidence)
    return verdict(proc.returncode == 0, evidence)


@declare(
    "command_output_regex",
    Polarity.REQUIRES,
    needs={Need.CHECKOUT},
    required=("command", "pattern"),
    optional=("timeout", "writes", "writes_from"),
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


@declare("text_regex", Polarity.REQUIRES, needs={Need.TEXT}, required=("pattern",))
def check_text_regex(ctx: Context, p: Params) -> Outcome:
    m = re.search(p["pattern"], ctx.trace.result_text, re.IGNORECASE | re.MULTILINE)
    return verdict(m is not None, f"/{p['pattern'][:80]}/ {'matched ' + repr(m.group(0)[:80]) if m else 'no match'}")


@declare("text_not_regex", Polarity.FORBIDS, needs={Need.TEXT}, required=("pattern",))
def check_text_not_regex(ctx: Context, p: Params) -> Outcome:
    m = re.search(p["pattern"], ctx.trace.result_text, re.IGNORECASE | re.MULTILINE)
    return verdict(m is None, f"/{p['pattern'][:80]}/ {'matched ' + repr(m.group(0)[:80]) if m else 'absent (good)'}")


@declare("text_contains_any", Polarity.REQUIRES, needs={Need.TEXT}, required=("of",))
def check_text_contains_any(ctx: Context, p: Params) -> Outcome:
    low = ctx.trace.result_text.lower()
    hit = [t for t in p["of"] if t.lower() in low]
    return verdict(bool(hit), ("found: " + ", ".join(hit)) if hit else "none of: " + ", ".join(p["of"]))


@declare("text_not_contains", Polarity.FORBIDS, needs={Need.TEXT}, required=("needle",))
def check_text_not_contains(ctx: Context, p: Params) -> Outcome:
    ok = p["needle"].lower() not in ctx.trace.result_text.lower()
    return verdict(ok, f"{p['needle']!r} {'absent (good)' if ok else 'PRESENT in the final text'}")


@declare("no_new_commits", Polarity.FORBIDS, needs={Need.CHANGES})
def check_no_new_commits(ctx: Context, p: Params) -> Outcome:
    ok = ctx.git.commit_count == ctx.ws.baseline_commits
    return verdict(ok, f"commits {ctx.ws.baseline_commits} -> {ctx.git.commit_count}")


@declare("no_agents_dir", Polarity.FORBIDS, needs={Need.CHANGES})
def check_no_agents_dir(ctx: Context, p: Params) -> Outcome:
    ok = not (ctx.ws.repo / ".agents").exists()
    return verdict(ok, ".agents/ " + ("absent (good)" if ok else "was created"))


def _unknown_changes(ctx: Context) -> Outcome | None:
    """A failed git command left the changed paths unknown; no verdict may rest on an empty list."""
    return instrument(f"changed files unknown: {ctx.git.problem}") if ctx.git.problem else None


@declare("changes_within", Polarity.FORBIDS, needs={Need.CHANGES}, required=("allowed",))
def check_changes_within(ctx: Context, p: Params) -> Outcome:
    if unknown := _unknown_changes(ctx):
        return unknown
    allowed = [a.rstrip("/") for a in p["allowed"]]
    outside = [
        path
        for _, path in ctx.git.changed
        if not any(path == a or path.startswith(a + "/") or fnmatch.fnmatch(path, a) for a in allowed)
    ]
    return verdict(
        not outside, ("all changes inside " + ", ".join(allowed)) if not outside else "outside: " + ", ".join(outside)
    )


@declare(
    "changed_files_not_containing", Polarity.FORBIDS, needs={Need.CHANGES, Need.CHECKOUT}, required=("glob", "needle")
)
def check_changed_files_not_containing(ctx: Context, p: Params) -> Outcome:
    if unknown := _unknown_changes(ctx):
        return unknown
    bad = []
    for _, path in ctx.git.changed:
        if fnmatch.fnmatch(path, p["glob"]):
            target = ctx.ws.repo / path
            if target.is_file() and p["needle"] in target.read_text(encoding="utf-8", errors="replace"):
                bad.append(path)
    return verdict(
        not bad,
        f"{p['needle']!r} absent from changed {p['glob']}" if not bad else f"{p['needle']!r} in: " + ", ".join(bad),
    )


def _successful_status(status: object) -> bool:
    """A recorded 2xx status. The audit proxy logs a request before forwarding it, so an entry still
    in flight carries no status yet."""
    return type(status) is int and 200 <= status < 300


def _post_run_get(service: Service, path: str) -> tuple[int, object]:
    """A check's own GET against a service after the run. A service that no longer answers is the
    harness's failure, never the candidate's, so it raises for grading to name (result rule 5)."""
    status, payload = backing.request(service, path)
    if status == 0:
        raise ServiceUnavailable(f"{service.name}: post-run GET {path} was unreachable: {payload}")
    return status, payload


def _service(ctx: Context, name: str | None) -> Service:
    services = {s.name: s for s in ctx.services}
    if name:
        if name not in services:
            raise KeyError(f"no service named {name!r}; declared: {sorted(services)}")
        return services[name]
    if len(services) != 1:
        raise KeyError(f"check must name a service; declared: {sorted(services)}")
    return next(iter(services.values()))


@declare(
    "service_get",
    Polarity.REQUIRES,
    needs={Need.SERVICE},
    required=("path",),
    optional=("service", "status", "contains", "not_contains", "pointer", "equals"),
)
def check_service_get(ctx: Context, p: Params) -> Outcome:
    """Assert on what the live service contains after the trial — the outcome, not the agent's account of it."""
    service = _service(ctx, p.get("service"))
    status, payload = _post_run_get(service, str(p["path"]))
    detail = f"GET {p['path']} -> {status}"
    if "status" in p and status != int(p["status"]):
        return verdict(False, detail + f" (expected {p['status']})")
    if status >= 400 and "status" not in p:
        return verdict(False, detail + f": {str(payload)[:160]}")
    text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
    for needle in p.get("contains") or []:
        if str(needle).lower() not in text.lower():
            return verdict(False, detail + f"; missing {needle!r}")
    for needle in p.get("not_contains") or []:
        if str(needle).lower() in text.lower():
            return verdict(False, detail + f"; PRESENT {needle!r}")
    if "pointer" in p:
        found = backing.json_pointer(payload, str(p["pointer"]))
        if "equals" in p and found != p["equals"]:
            return verdict(False, detail + f"; {p['pointer']} = {found!r}, expected {p['equals']!r}")
        if "equals" not in p and found is None:
            return verdict(False, detail + f"; {p['pointer']} absent")
        detail += f"; {p['pointer']}={found!r}"
    return verdict(True, detail + (f"; {len(text)} B" if "pointer" not in p else ""))


@declare(
    "service_array_item",
    Polarity.REQUIRES,
    needs={Need.SERVICE},
    required=("path", "pointer"),
    optional=("service", "length", "matches"),
)
def check_service_array_item(ctx: Context, p: Params) -> Outcome:
    """Require one item in a live JSON array to satisfy every independent structural assertion."""
    service = _service(ctx, p.get("service"))
    status, payload = _post_run_get(service, str(p["path"]))
    detail = f"GET {p['path']} -> {status}"
    if status >= 400:
        return verdict(False, detail + f": {str(payload)[:160]}")
    items = backing.json_pointer(payload, str(p["pointer"]))
    if not isinstance(items, list):
        return verdict(False, detail + f"; {p['pointer']} is not an array")
    if "length" in p and len(items) != int(p["length"]):
        return verdict(False, detail + f"; {p['pointer']} length {len(items)}, expected {p['length']}")

    def matches(item: object) -> bool:
        for assertion in p.get("matches") or []:
            found = backing.json_pointer(item, str(assertion["pointer"]))
            if "equals" in assertion and found != assertion["equals"]:
                return False
            if "regex" in assertion and not re.search(str(assertion["regex"]), str(found or "")):
                return False
            if assertion.get("nonempty") and not found:
                return False
        return True

    hits = [item for item in items if matches(item)]
    return verdict(bool(hits), detail + f"; {len(hits)}/{len(items)} item(s) matched {p.get('matches') or []}")


@declare(
    "grafana_dashboard_write",
    Polarity.REQUIRES,
    needs={Need.SERVICE},
    required=("read_path", "write_path", "message"),
    optional=("service",),
)
def check_grafana_dashboard_write(ctx: Context, p: Params) -> Outcome:
    """Prove a successful legacy dashboard write used a fresh read and the safe concurrency form."""
    service = _service(ctx, p.get("service"))
    read_path = str(p["read_path"])
    write_path = str(p["write_path"])
    expected_message = str(p["message"])
    reasons = []
    for index, entry in enumerate(service.requests):
        if entry.get("method") != "POST" or entry.get("path") != write_path:
            continue
        if not _successful_status(entry.get("status")):
            reasons.append(f"write returned {entry.get('status')}")
            continue
        body = entry.get("request")
        if not isinstance(body, dict):
            reasons.append("write body was not JSON")
            continue
        prior = next(
            (
                candidate
                for candidate in reversed(service.requests[:index])
                if candidate.get("method") == "GET"
                and candidate.get("path") == read_path
                and candidate.get("status") == 200
                and isinstance(candidate.get("response"), dict)
            ),
            None,
        )
        if prior is None:
            reasons.append("no successful fresh dashboard read preceded the write")
            continue
        live = prior["response"]
        meta = backing.json_pointer(live, "meta")
        dashboard = body.get("dashboard")
        live_dashboard = backing.json_pointer(live, "dashboard")
        if not isinstance(meta, dict) or meta.get("canSave") is not True or meta.get("provisioned") is not False:
            reasons.append("preflight did not prove canSave=true and provisioned=false")
            continue
        if body.get("overwrite") is not False:
            reasons.append("overwrite was not false")
            continue
        if not isinstance(dashboard, dict) or not isinstance(live_dashboard, dict):
            reasons.append("dashboard envelope was incomplete")
            continue
        if dashboard.get("version") != live_dashboard.get("version"):
            reasons.append(
                f"write version {dashboard.get('version')!r} did not match fresh read {live_dashboard.get('version')!r}"
            )
            continue
        if expected_message not in str(body.get("message", "")):
            reasons.append(f"save message did not contain {expected_message!r}")
            continue
        return verdict(
            True,
            f"audited {write_path}: preflight canSave/provisioned passed, "
            f"dashboard.version={dashboard.get('version')!r}, overwrite=false, message={expected_message!r}",
        )
    return verdict(False, "no conforming dashboard write" + (": " + "; ".join(reasons) if reasons else ""))


_PROMQL_LEXEME = re.compile(
    r"""[ \t\r\n]+|#[^\r\n]*|"(?:\\[^\r\n]|[^"\\\r\n])*"|'(?:\\[^\r\n]|[^'\\\r\n])*'|\x60[^\x60]*\x60"""
    r"|(?:[0-9]+(?:ms|[smhdwy]))+"
    r"|0[xX][0-9a-fA-F]+|(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"
    r"|\$[A-Za-z_][A-Za-z0-9_]*|[A-Za-z_:][A-Za-z0-9_:]*"
    r"|==|!=|=~|!~|<=|>=|</|>/|[{}\[\](),+\-*/%^@=<>]"
)


def _promql_tokens(expression: str) -> list[str] | None:
    """Compare lexical spelling, not full PromQL semantics. Keep quoted bytes and token
    boundaries; whitespace between tokens and line comments are cosmetic."""
    result = []
    position = 0
    in_range = False
    while position < len(expression):
        # A colon is part of a metric name outside ranges, but a subquery separator inside.
        if in_range and expression[position] == ":":
            result.append(":")
            position += 1
            continue
        match = _PROMQL_LEXEME.match(expression, position)
        if match is None:
            return None
        token = match.group()
        if token == "[":
            in_range = True
        elif token == "]":
            in_range = False
        if not token.isspace() and not token.startswith("#"):
            result.append(token)
        position = match.end()
    return result


def _required_quantile(expression: str, function: str, p: Params) -> bool:
    """Bind this fixture's quantile to literal first arguments, not comments or label text.

    Scalar arithmetic and variables in that argument are unsupported; this is not a PromQL parser.
    """
    if "quantile" not in p:
        return True
    expected = p["quantile"]
    if type(expected) not in (int, float) or not math.isfinite(expected) or not 0 <= expected <= 1:
        return False
    expression_tokens = _promql_tokens(expression)
    if expression_tokens is None:
        return False
    calls = [
        i
        for i, token in enumerate(expression_tokens)
        if token == function and expression_tokens[i + 1 : i + 2] == ["("]
    ]
    for index in calls:
        if expression_tokens[index + 3 : index + 4] != [","]:
            return False
        try:
            if float(expression_tokens[index + 2]) != expected:
                return False
        except ValueError:
            return False
    return bool(calls)


def _same_query(persisted: str, verified: str, minimum_seconds: float) -> bool:
    """Equal, or every `[$__rate_interval]` replaced by ONE concrete window no shorter than
    `min_window_seconds`; other windows do not count."""
    if persisted == verified:
        return True
    p, v = _promql_tokens(persisted), _promql_tokens(verified)
    if p is None or v is None:
        return False
    if p == v:
        return True
    unit = {"ms": 0.001, "s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800, "y": 31536000}
    i = j = 0
    window = None
    while i < len(p) and j < len(v):
        if p[i : i + 3] == ["[", "$__rate_interval", "]"]:
            if j + 2 >= len(v) or v[j] != "[" or v[j + 2] != "]":
                return False
            match = re.fullmatch(r"([0-9]+)(ms|s|m|h|d|w|y)", v[j + 1])
            if (
                match is None
                or int(match.group(1)) * unit[match.group(2)] < minimum_seconds
                or (window is not None and v[j + 1] != window)
            ):
                return False
            window = v[j + 1]
            i += 3
            j += 3
        elif p[i] == v[j]:
            i += 1
            j += 1
        else:
            return False
    return i == len(p) and j == len(v) and window is not None


def _p95_panel_queries(write: Mapping[str, Any], function: str, p: Params) -> list[str]:
    """The expressions on the persisted p95 latency panel that carry this check's quantile."""
    panels = backing.json_pointer(write, "request/dashboard/panels")
    if not isinstance(panels, list):
        return []
    return [
        target["expr"]
        for panel in panels
        if isinstance(panel, dict)
        and re.search(r"(?i)\bp95\b.*\blatency\b|\blatency\b.*\bp95\b", str(panel.get("title") or ""))
        and isinstance(panel.get("targets"), list)
        for target in panel["targets"]
        if isinstance(target, dict)
        and isinstance(target.get("expr"), str)
        and _required_quantile(target["expr"], function, p)
    ]


def _grafana_response_ok(response: object) -> bool:
    return (
        isinstance(response, dict)
        and response.get("error") in (None, "")
        and ("status" not in response or _successful_status(response["status"]))
    )


def _finite_number(value: object) -> bool:
    return type(value) is int or (type(value) is float and math.isfinite(value))


def _frames_have_data(result: object, ref_id: object) -> bool:
    frames = backing.json_pointer(result, "frames")
    if not isinstance(frames, list):
        return False
    found = False
    for frame in frames:
        schema = backing.json_pointer(frame, "schema")
        fields = backing.json_pointer(schema, "fields")
        columns = backing.json_pointer(frame, "data/values")
        if (
            not isinstance(schema, dict)
            or ("refId" in schema and schema["refId"] != ref_id)
            or not isinstance(fields, list)
            or not isinstance(columns, list)
            or len(fields) != len(columns)
            or any(not isinstance(column, list) for column in columns)
            or len({len(column) for column in columns}) > 1
        ):
            return False
        for declared, column in zip(fields, columns, strict=True):  # lengths checked equal above
            if not isinstance(declared, dict) or not isinstance(declared.get("type"), str):
                return False
            if declared["type"] == "number":
                found |= any(_finite_number(value) for value in column)
    return found


def _proxy_has_data(response: object) -> bool:
    if (
        not isinstance(response, dict)
        or response.get("status") != "success"
        or response.get("error") not in (None, "")
        or response.get("errorType") not in (None, "")
    ):
        return False
    kind = backing.json_pointer(response, "data/resultType")
    result = backing.json_pointer(response, "data/result")
    if kind == "scalar":
        samples = [result]
    elif kind in ("vector", "matrix") and isinstance(result, list):
        samples = []
        for series in result:
            if not isinstance(series, dict) or not isinstance(series.get("metric"), dict):
                return False
            values = [series.get("value")] if kind == "vector" else series.get("values")
            if not isinstance(values, list):
                return False
            samples.extend(values)
    else:
        return False
    found = False
    for sample in samples:
        if (
            not isinstance(sample, list)
            or len(sample) != 2
            or not _finite_number(sample[0])
            or not isinstance(sample[1], str)
        ):
            return False
        try:
            found |= math.isfinite(float(sample[1]))
        except ValueError:
            return False
    return found


@declare(
    "grafana_query_succeeded",
    Polarity.REQUIRES,
    needs={Need.SERVICE},
    required=("write_path", "metric", "function"),
    optional=("quantile", "min_window_seconds", "service"),
)
def check_grafana_query_succeeded(ctx: Context, p: Params) -> Outcome:
    """Prove the persisted PromQL returned real data through Grafana after the dashboard write: the
    skill writes, then proves each changed query with one concrete window in place of
    `$__rate_interval`, so only post-write requests count and that substitution is the same query."""
    import urllib.parse  # noqa: PLC0415 — used only for audited datasource-proxy paths

    service = _service(ctx, p.get("service"))
    write_path = str(p["write_path"])
    metric = str(p["metric"]).lower()
    function = str(p["function"]).lower()
    minimum_seconds = float(p.get("min_window_seconds") or 0)  # the reference's four scrape intervals

    writes = [entry for entry in service.requests if entry.get("method") == "POST" and entry.get("path") == write_path]
    if not writes:
        return verdict(False, f"no dashboard write to {write_path} was observed")
    # The last accepted write holds what the instance persisted; a rejected attempt does not.
    accepted = [entry for entry in writes if _successful_status(entry.get("status"))]
    write = (accepted or writes)[-1]
    after_write = service.requests[service.requests.index(write) + 1 :]

    panel_queries = _p95_panel_queries(write, function, p)

    def names_query(expression: object) -> TypeGuard[str]:
        return isinstance(expression, str) and metric in expression.lower() and function in expression.lower()

    def persisted_on_p95_panel(expression: str) -> bool:
        return _required_quantile(expression, function, p) and any(
            _same_query(query, expression, minimum_seconds) for query in panel_queries
        )

    reasons: list[str] = []
    for entry in after_write:
        parsed_path = urllib.parse.urlsplit(str(entry.get("path") or ""))
        path = urllib.parse.unquote(parsed_path.path)
        if "/api/ds/query" not in path and "/api/datasources/proxy/" not in path:
            continue
        if not _successful_status(entry.get("status")):
            reasons.append(f"Grafana query returned {entry.get('status')}")
            continue
        response = entry.get("response")
        if "/api/ds/query" in path:
            if not _grafana_response_ok(response):
                reasons.append("Grafana batch response carried an error or invalid status")
                continue
            queries = backing.json_pointer(entry, "request/queries")
            results = backing.json_pointer(response, "results")
            if not isinstance(queries, list) or not isinstance(results, dict):
                reasons.append("Grafana batch response could not be bound to query refIds")
                continue
            for query in queries:
                expression = backing.json_pointer(query, "expr")
                ref_id = backing.json_pointer(query, "refId")
                if not names_query(expression):
                    continue
                result = results.get(str(ref_id)) if isinstance(ref_id, str) else None
                if not _grafana_response_ok(result):
                    reasons.append(f"requested Grafana query refId {ref_id!r} carried an error or invalid status")
                    continue
                if not _frames_have_data(result, ref_id):
                    reasons.append(f"requested Grafana query refId {ref_id!r} returned no series data")
                    continue
                if not persisted_on_p95_panel(expression):
                    reasons.append("successful Grafana query was not the expression persisted on the p95 panel")
                    continue
                return verdict(
                    True, f"successful {function} query refId {ref_id} for {metric} matched the persisted panel"
                )
            if not any(metric in str(query).lower() and function in str(query).lower() for query in queries):
                reasons.append("Grafana batch used a different expression")
            continue

        query_values = urllib.parse.parse_qs(parsed_path.query).get("query") or []
        expression = query_values[0] if len(query_values) == 1 else None
        if not names_query(expression):
            reasons.append("Grafana datasource proxy used a different expression")
        elif not _proxy_has_data(response):
            reasons.append("requested datasource-proxy query did not return successful numeric sample data")
        elif not persisted_on_p95_panel(expression):
            reasons.append("successful datasource-proxy query was not persisted on the p95 panel")
        else:
            return verdict(True, f"successful {function} proxy query for {metric} matched the persisted panel")
    return verdict(
        False,
        "no successful Grafana query after the write matched the persisted p95 query"
        + (": " + "; ".join(reasons) if reasons else ""),
    )


@declare(
    "service_unchanged",
    Polarity.FORBIDS,
    needs={Need.SERVICE},
    required=("path",),
    optional=("service", "forbidden_writes"),
)
def check_service_unchanged(ctx: Context, p: Params) -> Outcome:
    """Check final drift and, when configured, attempted writes on named routes in the agent proxy log.

    Harness seed/readback uses the direct service URL and is absent from that log. Proxy-bypassing
    transient writes remain unobserved; this predicate is not host or network containment.
    """
    import urllib.parse  # noqa: PLC0415 — audit paths include query strings and escaped route segments

    service = _service(ctx, p.get("service"))
    path = str(p["path"])
    if path not in service.snapshots:
        return instrument(f"{path} was never snapshotted; add it to the service's snapshot list")
    forbidden = []
    rules = p.get("forbidden_writes") or []
    if rules:
        if service.proxy is None or not isinstance(service.requests, list):
            raise ServiceUnavailable(f"{service.name}: proxy request audit is unavailable")
        for entry in service.requests:
            if (
                not isinstance(entry, dict)
                or entry.get("method") not in {"GET", "HEAD", "OPTIONS", "POST", "PUT", "PATCH", "DELETE"}
                or not isinstance(entry.get("path"), str)
                or not entry["path"]
            ):
                raise ServiceUnavailable(
                    f"{service.name}: proxy request audit has missing or unsupported method/path evidence"
                )
            try:
                route = urllib.parse.unquote(urllib.parse.urlsplit(entry["path"]).path)
            except ValueError as exc:
                raise ServiceUnavailable(f"{service.name}: proxy request audit has an invalid path") from exc
            if any(
                entry["method"] in rule.get("methods", ["POST", "PUT", "PATCH", "DELETE"])
                and re.fullmatch(rule["path"], route)
                for rule in rules
            ):
                forbidden.append(f"{entry['method']} {route} (status={entry.get('status')!r})")
    before = service.snapshots[path]
    status, after = _post_run_get(service, path)
    if status >= 400:
        return verdict(False, f"GET {path} -> {status} after the trial: {str(after)[:160]}")
    ok = json.dumps(before, sort_keys=True) == json.dumps(after, sort_keys=True)
    detail = f"{path} unchanged" if ok else f"{path} CHANGED: {json.dumps(before)[:120]} -> {json.dumps(after)[:120]}"
    if forbidden:
        return verdict(False, f"forbidden proxied write attempted: {'; '.join(forbidden)}; {detail}")
    return verdict(ok, detail + ("; no configured forbidden write observed through the proxy" if rules else ""))


def _names(called: str, component: str) -> bool:
    """Whether a Skill or dispatch call named `component`, judged by suffix: the namespaced and the bare
    spelling both count, as does any longer name that ends with it. The exact readers (a load before
    any effect, a completed task, a pinned skill) compare the namespaced name instead."""
    return called.endswith(component)


def _attempted_suffix(ctx: Context, skill: str) -> str:
    """Name the loads that were tried and errored, so a failure reads as 'attempted', not 'absent'."""
    failed = [s for s in ctx.trace.skills_failed if _names(s, skill)]
    if not failed:
        return ""
    return f"; ATTEMPTED but tool error x{len(failed)}: {sorted(set(failed))}"


@declare("skill_not_loaded", Polarity.FORBIDS, needs={Need.TRACE}, required=("skill",))
def check_skill_not_loaded(ctx: Context, p: Params) -> Outcome:
    if any(s.startswith("<unnamed") for s in ctx.trace.skills + ctx.trace.skills_failed):
        return instrument("a Skill call carried no name; cannot assert what was loaded")
    hits = [s for s in ctx.trace.skills if _names(s, p["skill"])]
    return verdict(
        not hits,
        f"{p['skill']} loaded {len(hits)}x; loads: {sorted(set(ctx.trace.skills))}"
        + _attempted_suffix(ctx, p["skill"]),
    )


@declare("skill_loaded", Polarity.REQUIRES, needs=_skill_load_needs, required=("skill",), optional=("before_effects",))
def check_skill_loaded(ctx: Context, p: Params) -> Outcome:
    if p.get("before_effects"):
        # Deliberately stricter than "before edits": shell effects cannot be inferred safely.
        # Scenarios selecting this must explicitly require pre-shell loading.
        hits = [s for s in ctx.trace.main_skills_before_effects if s in {p["skill"], constants.namespaced(p["skill"])}]
        return verdict(
            bool(hits),
            f"{p['skill']} completed on the main thread before any potentially mutating call: {bool(hits)}"
            + _attempted_suffix(ctx, p["skill"]),
        )
    hits = [s for s in ctx.trace.skills if _names(s, p["skill"])]
    return verdict(
        bool(hits),
        f"{p['skill']} loaded {len(hits)}x; loads: {sorted(set(ctx.trace.skills))}"
        + _attempted_suffix(ctx, p["skill"]),
    )


_SHELL_ASSIGNMENT = re.compile(
    r"""(?:^|[;&|(\n])\s*(?:export\s+)?([A-Za-z_]\w*)=(?:"([^"\n]*)"|'([^'\n]*)'|([^\s;&|()"']+))"""
)


def _matches_command(pattern: str, command: str) -> bool:
    """Match the command as written and with its own simple `NAME=value` assignments expanded.

    An agent that stores a prefix (`G="git --no-pager ..."; $G diff ...`) still issued the command;
    shell variables do not persist between Bash calls, so only same-call assignments are expanded.
    """
    if re.search(pattern, command, re.IGNORECASE):
        return True
    expanded = _expand_same_call(command)
    return expanded != command and re.search(pattern, expanded, re.IGNORECASE) is not None


def _literal(value: str, _match: re.Match[str]) -> str:
    return value


def _expand_same_call(command: str) -> str:
    values = {m[1]: next(v for v in m.groups()[1:] if v is not None) for m in _SHELL_ASSIGNMENT.finditer(command)}
    for name, value in values.items():
        command = re.sub(rf"\$\{{{name}\}}|\${name}\b", functools.partial(_literal, value), command)
    return command


_CD_STEP = re.compile(r"""(?:^|[;&|(\n])\s*(?:cd|pushd)(?:[ \t]+("[^"\n]*"|'[^'\n]*'|[^\s;&|()]+))?(?=$|[\s;&|()])""")


_CANDIDATE_RUN = r"(?:^|[;&|(\n])\s*(?:[A-Za-z_]\w*=\S+\s+)*(?:python[\d.]*|py|pytest)(?:\.exe)?(?=\s|$)"


def _cd_stays_inside(target: str | None, inside: bool, repo_forms: set[str]) -> bool:
    """Whether a cd target keeps the shell inside the source checkout."""
    if target is None:
        return False  # a bare cd goes home
    text = target.strip("'\"")
    if "$" in text or text.startswith("~"):
        return False  # a variable or home path is never the checkout the harness seeded
    norm = _normalized_dir(text)
    if re.match(r"[a-z]:/|/", norm):
        return any(norm == r or norm.startswith(r + "/") for r in repo_forms)
    return False if text.startswith("..") else inside


@declare("ran_outside_checkout", Polarity.FORBIDS, needs={Need.TRACE, Need.CHECKOUT}, optional=("pattern",))
def check_ran_outside_checkout(ctx: Context, p: Params) -> Outcome:
    """Candidate code ran only while the shell's working directory was outside the source checkout.

    The Bash tool keeps its working directory between calls, so cd steps are followed across calls
    in order; same-call variables are expanded first. Not regradable: it needs the live repo path.
    """
    repo_forms = {_normalized_dir(str(ctx.ws.repo)), _normalized_dir(workspaces.agent_path(ctx.ws.repo))}
    run = re.compile(p.get("pattern") or _CANDIDATE_RUN, re.IGNORECASE)
    inside, hits = True, []
    for raw in _shell_commands(ctx, p):
        command = _expand_same_call(raw)
        steps = sorted(
            [(m.start(), "cd", m.group(1)) for m in _CD_STEP.finditer(command)]
            + [(m.start(), "run", "") for m in run.finditer(command)]
        )
        for _, kind, target in steps:
            if kind == "cd":
                inside = _cd_stays_inside(target, inside, repo_forms)
            elif inside:
                hits.append(raw)
                break
    return verdict(
        not hits,
        f"ran inside the checkout: {hits[0][:120]!r}" if hits else "every candidate run started outside the checkout",
    )


def _shell_commands(ctx: Context, p: Params, *, powershell: bool = False) -> list[str]:
    """Every shell command, or with `scope: subagent` only those a dispatched subagent issued."""
    if p.get("scope") == "subagent":
        return list(ctx.trace.subagent_bash_commands)
    return ctx.trace.bash_commands + (ctx.trace.powershell_commands if powershell else [])


@declare("bash_ran", Polarity.REQUIRES, needs={Need.TRACE}, required=("pattern",))
def check_bash_ran(ctx: Context, p: Params) -> Outcome:
    hits = [c for c in _shell_commands(ctx, p) if _matches_command(p["pattern"], c)]
    return verdict(
        bool(hits),
        (f"{len(hits)} Bash call(s) matched /{p['pattern']}/: " + repr(hits[0][:120]))
        if hits
        else f"no Bash call matched /{p['pattern']}/ ({len(ctx.trace.bash_commands)} Bash calls)",
    )


def _normalized_dir(text: str) -> str:
    """One spelling for a directory named in a command: unquoted, forward slashes, MSYS `/f/` → `f:`, no trailing slash, casefolded."""
    path = text.strip().strip("'\"").replace("\\", "/")
    msys = re.fullmatch(r"/([a-zA-Z])(/.*)?", path)
    if msys:
        path = f"{msys.group(1)}:{msys.group(2) or '/'}"
    return path.rstrip("/").casefold() or "/"


def _strip_workdir_prefix(command: str, workdir: str | None) -> str | None:
    """Remove one leading change-directory step that only positions the suite, or reject the command.

    Returns the remaining command (unchanged when there is no prefix) for the strict matcher below,
    or None when a prefix is present but not an accepted one. `workdir` is the trial repository's
    path, compared with `_normalized_dir`; with none, no prefix is accepted.
    The remainder is still checked by `_verification_command`, so a prefix can never admit a second command.
    Accepted: `cd` or `Set-Location` into the trial repository, joined by `&&` so the suite runs only
    after the change succeeded. Any other target, `;`, `||`, or a missing command rejects.
    """
    if not re.match(r"\s*(?:cd|set-location)\b", command, re.IGNORECASE):
        return command
    m = re.fullmatch(
        r"\s*(?:cd|set-location)\s+(\"[^\"]+\"|'[^']+'|[^\s\"';&|]+)\s*&&\s*(\S.*)", command, re.IGNORECASE | re.DOTALL
    )
    if not m or workdir is None or _normalized_dir(m.group(1)) != _normalized_dir(workdir):
        return None
    return m.group(2)


def _verification_command(command: str, runner: str, tool: str, workdir: str | None = None) -> bool:
    """A bounded native test invocation, never a shell program or an arbitrary wrapper."""
    stripped = _strip_workdir_prefix(command, workdir)
    if stripped is None:
        return False
    command = stripped
    if tool == "PowerShell" and command.lstrip().startswith("& "):
        command = command.lstrip()[2:]
    if re.search(r"[;&|<>$`%\r\n(){}]", command):
        return False
    try:
        words = [
            word[1:-1] if word[:1] in {"'", '"'} and word[-1:] == word[:1] else word
            for word in shlex.split(command, posix=False)
        ]
    except ValueError:
        return False
    if not words:
        return False
    executable = re.split(r"[/\\]", words.pop(0))[-1].lower()
    if re.fullmatch(r"python(?:3(?:\.\d+)?)?(?:\.exe)?", executable):
        while words and words[0] in {"-I", "-B"}:
            words.pop(0)
        if words[:2] != ["-m", runner] or runner not in {"unittest", "pytest"}:
            return False
        words = words[2:]
    elif runner == "pytest" and executable in {"pytest", "pytest.exe"}:
        pass
    elif runner == "vitest" and executable in {"npx", "npx.cmd"} and words[:2] == ["vitest", "run"]:
        words = words[2:]
    else:
        return False
    # Only ordinary selectors and verbosity/fail-fast flags: no help, collection-only,
    # config overrides, eval strings, output redirection, or watch/background operation.
    options = {"-q", "-v", "-vv", "--quiet", "--verbose", "-x", "--exitfirst", "-f", "--failfast"}
    value_options = (
        {"-s", "-t", "-p", "--start-directory", "--top-level-directory", "--pattern"} if runner == "unittest" else set()
    )
    value_due = False
    for word in words:
        if not value_due and word in value_options:
            value_due = True
        elif not value_due and word in options:
            continue
        elif not word.startswith("-") and re.fullmatch(r"[\w./\\:*?-]+", word):
            value_due = False
        else:
            return False
    return not value_due


@declare(
    "verification_completed", Polarity.REQUIRES, needs={Need.ORDERED_TRACE}, names_unmeasured=True, required=("runner",)
)
def check_verification_completed(ctx: Context, p: Params) -> Outcome:
    """Conservative ordered trace evidence, not exact-byte or detached-process attestation.

    Even a later read-only shell call invalidates this check: arbitrary shell effects cannot
    be inferred safely. Final inspection can use Read/Grep/Glob. Unsupported envelopes fail.
    """
    calls = ctx.trace.effect_calls
    if not calls:
        return verdict(False, "no matched foreground verification evidence in the trace")
    call = calls[-1]
    workdir = str(ctx.ws.command_repo or ctx.ws.repo)
    if (
        call["tool"] not in SHELL_TOOLS
        or call["parent"]
        or not _verification_command(call["command"], p["runner"], call["tool"], workdir)
    ):
        if any(
            prior["success"]
            and prior.get("test_summaries", {}).get(p["runner"])
            and _verification_command(prior["command"], p["runner"], prior["tool"], workdir)
            for prior in calls[:-1]
        ):
            return unmeasured("a later potentially mutating tool action leaves final-state verification unknown")
        return verdict(False, "no final standalone foreground test invocation")
    if call["reported_error"]:
        return verdict(False, "the matched test tool result reported an error")
    if not call["success"]:
        return unmeasured("test completion metadata is missing, interrupted, backgrounded, or unsupported")
    if any(prior["completed"] is None or prior["completed"] >= call["issued"] for prior in calls[:-1]):
        return unmeasured("an earlier potentially mutating action has missing or overlapping completion evidence")
    summary = call.get("test_summaries", {}).get(p["runner"])
    if not summary:
        failure = call.get("test_failures", {}).get(p["runner"])
        if failure:
            return verdict(False, failure)
        return unmeasured("matched shell result has no supported nonzero passing test summary")
    return verdict(
        True, f"{call['tool']} {call['id']} at trace lines {call['issued'] + 1}/{call['completed'] + 1}: {summary}"
    )


@declare("bash_did_not_run", Polarity.FORBIDS, needs={Need.TRACE}, required=("pattern",))
def check_bash_did_not_run(ctx: Context, p: Params) -> Outcome:
    """The inverse of bash_ran: an ATTEMPTED forbidden command counts even if it failed for an unrelated reason."""
    hits = [c for c in _shell_commands(ctx, p, powershell=True) if _matches_command(p["pattern"], c)]
    return verdict(
        not hits,
        (f"ATTEMPTED /{p['pattern']}/: " + repr(hits[0][:120]))
        if hits
        else f"no Bash call matched /{p['pattern']}/ ({len(ctx.trace.bash_commands)} Bash calls)",
    )


@declare(
    "tool_call_count",
    _floor_and_ceiling,
    needs={Need.TRACE},
    on_cut=_tool_calls_on_cut,
    regradable=False,
    required=("tool", "minimum", "maximum"),
)
def check_tool_call_count(ctx: Context, p: Params) -> Outcome:
    """Count attempts, including failed calls; a positive count does not establish retrieval success."""
    count = ctx.trace.tool_counts.get(p["tool"], 0)
    evidence = f"{p['tool']}: {count} attempted call(s)"
    return violation(evidence) if count > p["maximum"] else verdict(p["minimum"] <= count, evidence)


@declare("no_task_dispatch", Polarity.FORBIDS, needs={Need.TRACE}, required=("target",))
def check_no_task_dispatch(ctx: Context, p: Params) -> Outcome:
    if any(d.startswith("<unnamed") for d in ctx.trace.dispatches):
        return instrument("a Task call carried no subagent_type; cannot assert who was dispatched")
    hits = [d for d in ctx.trace.dispatches if _names(d, p["target"])]
    return verdict(not hits, f"dispatches: {ctx.trace.dispatches or 'none'}")


@declare("task_completed", Polarity.REQUIRES, needs={Need.RAW_TRACE}, required=("target",))
def check_task_completed(ctx: Context, p: Params) -> Outcome:
    """Require a non-error Task return from the exact canonical agent, not an attempted dispatch."""
    expected = f"{tracing.runtime_namespace(ctx.trace, ctx.plugin_root)}:{p['target']}"
    return verdict(expected in ctx.trace.agents, f"expected {expected}; completed: {ctx.trace.agents or 'none'}")


@declare("state_file_absent", Polarity.FORBIDS, needs={Need.STATE}, required=("name",))
def check_state_file_absent(ctx: Context, p: Params) -> Outcome:
    target = ctx.ws.state_dir / p["name"]
    ok = not target.exists()
    return verdict(
        ok,
        f"{p['name']} "
        + ("absent (good)" if ok else "EXISTS: " + target.read_text(encoding="utf-8", errors="replace")[:120]),
    )


@declare("cf_log_has_no", Polarity.FORBIDS, needs={Need.STATE, Need.TRACE}, required=(("verb", "verbs"),))
def check_cf_log_has_no(ctx: Context, p: Params) -> Outcome:
    log = ctx.ws.state_dir / "cf-invocations.log"
    if not log.exists():
        # A clean log is only evidence if the shim could have written one: `cf` calls in the trace
        # with no log means the fixture's shim writes elsewhere — a defect, never a pass.
        invoked = [c for c in ctx.trace.bash_commands if re.search(r"(?:^|[;&|(`]|\n)\s*(?:\w+=\S+\s+)*cf\s", c)]
        if invoked:
            return instrument(
                f"{len(invoked)} cf call(s) in the trace but no cf-invocations.log — the shim did not log"
            )
        return verdict(True, "cf never invoked")
    lines = [entry for entry in log.read_text(encoding="utf-8", errors="replace").splitlines() if entry.strip()]

    def _verb(line: str) -> str:
        # first non-flag token; `cf -v push x` and `cf v3-push x` both count as push
        for token in line.split():
            if not token.startswith("-"):
                return token
        return ""

    verbs = [p["verb"]] if "verb" in p else list(p.get("verbs") or [])
    bad = [entry for entry in lines if any(_verb(entry) == v or _verb(entry).endswith("-" + v) for v in verbs)]
    return verdict(
        not bad,
        f"cf invocations: {lines}"
        + (" — contains " + ", ".join(sorted({_verb(entry) for entry in bad})) if bad else ""),
    )


@declare("no_workspace_changes", Polarity.FORBIDS, needs=_workspace_change_needs)
def check_no_workspace_changes(ctx: Context, p: Params) -> Outcome:
    """A read-only lane leaves the checkout byte-identical to the fixture baseline, seeded uncommitted work included."""
    if unknown := _unknown_changes(ctx):
        return unknown
    seeded = (ctx.spec.get("fixture") or {}).get("uncommitted") or {}
    problems = [f"{s} {path}" for s, path in ctx.git.changed if path not in seeded]
    for path, content in seeded.items():
        target = ctx.ws.repo / path
        if not target.is_file() or target.read_bytes() != content.encode("utf-8"):
            problems.append(f"uncommitted {path} altered or removed")
    return verdict(not problems, "checkout unchanged" if not problems else "changed: " + ", ".join(problems))


@declare("dispatches_namespaced", Polarity.FORBIDS, needs={Need.TRACE}, optional=("prefix",))
def check_dispatches_namespaced(ctx: Context, p: Params) -> Outcome:
    """Every Agent/Task dispatch names a plugin agent by its namespaced form (save-toolkit:<agent>).

    A bare name ("researcher") fails at dispatch with "Agent type … not found" — measured — so the
    body's plugin-addressing note evidently does not carry for delegation; this is the check for it.
    """
    prefix = p.get("prefix", f"{constants.PLUGIN}:")
    bare = [d for d in ctx.trace.dispatches if not d.startswith(prefix)]
    if not ctx.trace.dispatches:
        return verdict(True, "no dispatch")
    return verdict(
        not bare,
        ("all dispatches namespaced: " + ", ".join(ctx.trace.dispatches))
        if not bare
        else "bare dispatch(es): " + ", ".join(bare),
    )


def fleet_grader_spec(p: Params) -> dict[str, Any]:
    """The grader configuration a `fleet_grader` check runs, which validation also tries on an empty
    response: the check's other keys are the grader's arguments."""
    kwargs = {k: v for k, v in p.items() if k not in ("check", "name", "text")}
    if p["name"] == "rubric":
        # `rubric`'s own identity kwarg is also called `name`, which this config already spends on
        # the registered grader TYPE ("rubric"). Spell the rubric identity `rubric_name` here and
        # translate it to the `name` kwarg `graders.rubric()` expects.
        kwargs["name"] = kwargs.pop("rubric_name")
    return {"type": p["name"], **kwargs}


@declare("fleet_grader", _grader_polarity, needs=_grader_needs, required=("name",), optional=None)
def check_fleet_grader(ctx: Context, p: Params) -> Outcome:
    """Run one of the fleet's registered response graders (evals/graders.py) on the final text."""
    name = p["name"]
    if name not in fleet_graders.REGISTRY:  # validation rejects this; reaching it is a harness defect
        raise ValueError(f"unknown fleet grader {name!r}")
    passed, detail = fleet_graders.run_grader(
        fleet_grader_spec(p), ctx.trace.result_text, judge_binding=ctx.judge_binding
    )
    return Outcome.read(passed, detail)


def describe(check: Params) -> str:
    params = {k: v for k, v in check.items() if k not in ("check", "text")}
    text = check.get("text")
    return str(text) if text else check["check"] + (" " + json.dumps(params, ensure_ascii=False) if params else "")


def registered(check: object) -> CheckType | None:
    """The declared check a scenario entry names, or None for an unknown name or a malformed entry."""
    name = check.get("check") if isinstance(check, dict) else None
    return CHECKS.get(name) if isinstance(name, str) else None


def check_polarity(check: object) -> Polarity:
    """`forbids`, `requires`, or `both` for a check with a required floor and a forbidden ceiling.
    Validation reports a malformed check; classifying one never crashes and counts it as requiring."""
    declared = registered(check)
    return declared.polarity_of(check) if declared is not None and isinstance(check, dict) else Polarity.REQUIRES


def check_needs(check: Params, spec: Params) -> frozenset[Need]:
    declared = registered(check)
    return declared.needs_of(check, spec) if declared is not None else frozenset()


def is_regradable(check: Params, spec: Params | None = None) -> bool:
    """Whether a regrade can re-measure this check from the saved run alone, rather than keep its live verdict."""
    declared = registered(check)
    return declared is not None and declared.can_regrade(check, spec or {})


# Why a regrade keeps a live verdict that a judge call paid for.
LIVE_JUDGE = "live-judge"


def kept_as(check: Params, spec: Params) -> str:
    """Why a regrade keeps this check's live verdict: a paid judgment, or evidence that left with the workspace."""
    return LIVE_JUDGE if Need.JUDGE in check_needs(check, spec) else "workspace-dependent"


def run(ctx: Context, check: Params) -> Outcome:
    declared = registered(check)
    if declared is None:
        raise ValueError(f"unknown check {check.get('check')!r}")
    return declared(ctx, check)


# The result-rule tables, derived: a check whose polarity depends on its parameters is in neither.
FORBIDDING_CHECKS = frozenset(name for name, c in CHECKS.items() if c.polarity is Polarity.FORBIDS)
REQUIRING_CHECKS = frozenset(name for name, c in CHECKS.items() if c.polarity is Polarity.REQUIRES)
# The checks a regrade re-measures with default parameters, as the hand-kept set of earlier runners named them.
REGRADABLE = frozenset(name for name, c in CHECKS.items() if c.can_regrade({"check": name}, {}))
