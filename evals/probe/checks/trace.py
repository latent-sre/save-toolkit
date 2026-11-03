"""Checks of the trace: skills loaded, commands run, tool calls, dispatches and their namespaces, and the one probe that compares commands against the live checkout path."""

from __future__ import annotations

import functools
import re
import shlex

from .. import constants, tracing, workspaces
from ..constants import SHELL_TOOLS
from ..outcomes import Outcome, Polarity, instrument, unmeasured, verdict, violation
from ..tracing import TraceSummary
from . import registry
from .registry import Context, Need, Params


def _skill_load_needs(params: Params, _spec: Params) -> frozenset[Need]:
    # "Before any effect" is an ordering claim, which only the raw trace can support.
    return frozenset({Need.ORDERED_TRACE}) if params.get("before_effects") else frozenset({Need.TRACE})


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


@registry.declare(
    "skill_not_loaded", Polarity.FORBIDS, needs={Need.TRACE}, required=("skill",), kind=registry.Kind.CHECK
)
def check_skill_not_loaded(ctx: Context, p: Params) -> Outcome:
    if any(s.startswith("<unnamed") for s in ctx.trace.skills + ctx.trace.skills_failed):
        return instrument("a Skill call carried no name; cannot assert what was loaded")
    hits = [s for s in ctx.trace.skills if _names(s, p["skill"])]
    return verdict(
        not hits,
        f"{p['skill']} loaded {len(hits)}x; loads: {sorted(set(ctx.trace.skills))}"
        + _attempted_suffix(ctx, p["skill"]),
    )


@registry.declare(
    "skill_loaded",
    Polarity.REQUIRES,
    needs=_skill_load_needs,
    required=("skill",),
    optional=("before_effects",),
    kind=registry.Kind.CHECK,
)
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


@registry.declare(
    "ran_outside_checkout",
    Polarity.FORBIDS,
    needs={Need.TRACE, Need.CHECKOUT},
    optional=("pattern",),
    kind=registry.Kind.PROBE,
)
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


@registry.declare("bash_ran", Polarity.REQUIRES, needs={Need.TRACE}, required=("pattern",), kind=registry.Kind.CHECK)
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


@registry.declare(
    "verification_completed",
    Polarity.REQUIRES,
    needs={Need.ORDERED_TRACE},
    names_unmeasured=True,
    required=("runner",),
    kind=registry.Kind.CHECK,
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
    completed = call["completed"]  # the line of its matched result: never None once `success` holds
    if not call["success"] or completed is None:
        return unmeasured("test completion metadata is missing, interrupted, backgrounded, or unsupported")
    if any(prior["completed"] is None or prior["completed"] >= call["issued"] for prior in calls[:-1]):
        return unmeasured("an earlier potentially mutating action has missing or overlapping completion evidence")
    summary = call.get("test_summaries", {}).get(p["runner"])
    if not summary:
        failure = call.get("test_failures", {}).get(p["runner"])
        if failure:
            return verdict(False, failure)
        return unmeasured("matched shell result has no supported nonzero passing test summary")
    return verdict(True, f"{call['tool']} {call['id']} at trace lines {call['issued'] + 1}/{completed + 1}: {summary}")


@registry.declare(
    "bash_did_not_run", Polarity.FORBIDS, needs={Need.TRACE}, required=("pattern",), kind=registry.Kind.CHECK
)
def check_bash_did_not_run(ctx: Context, p: Params) -> Outcome:
    """The inverse of bash_ran: an ATTEMPTED forbidden command counts even if it failed for an unrelated reason."""
    hits = [c for c in _shell_commands(ctx, p, powershell=True) if _matches_command(p["pattern"], c)]
    return verdict(
        not hits,
        (f"ATTEMPTED /{p['pattern']}/: " + repr(hits[0][:120]))
        if hits
        else f"no Bash call matched /{p['pattern']}/ ({len(ctx.trace.bash_commands)} Bash calls)",
    )


@registry.declare(
    "tool_call_count",
    _floor_and_ceiling,
    needs={Need.TRACE},
    on_cut=_tool_calls_on_cut,
    required=("tool", "minimum", "maximum"),
    kind=registry.Kind.CHECK,
)
def check_tool_call_count(ctx: Context, p: Params) -> Outcome:
    """Count attempts, including failed calls; a positive count does not establish retrieval success."""
    count = ctx.trace.tool_counts.get(p["tool"], 0)
    evidence = f"{p['tool']}: {count} attempted call(s)"
    if count > p["maximum"]:
        return violation(evidence)
    if not ctx.tool_counts_recorded:
        return unmeasured("saved tool-call count evidence is missing or incomplete; re-run the trial")
    return verdict(p["minimum"] <= count, evidence)


@registry.declare(
    "no_task_dispatch", Polarity.FORBIDS, needs={Need.TRACE}, required=("target",), kind=registry.Kind.CHECK
)
def check_no_task_dispatch(ctx: Context, p: Params) -> Outcome:
    if any(d.startswith("<unnamed") for d in ctx.trace.dispatches):
        return instrument("a Task call carried no subagent_type; cannot assert who was dispatched")
    hits = [d for d in ctx.trace.dispatches if _names(d, p["target"])]
    return verdict(not hits, f"dispatches: {ctx.trace.dispatches or 'none'}")


@registry.declare(
    "task_completed", Polarity.REQUIRES, needs={Need.RAW_TRACE}, required=("target",), kind=registry.Kind.CHECK
)
def check_task_completed(ctx: Context, p: Params) -> Outcome:
    """Require a non-error Task return from the exact canonical agent, not an attempted dispatch."""
    expected = f"{tracing.runtime_namespace(ctx.trace, ctx.plugin_root)}:{p['target']}"
    return verdict(expected in ctx.trace.agents, f"expected {expected}; completed: {ctx.trace.agents or 'none'}")


@registry.declare(
    "dispatches_namespaced", Polarity.FORBIDS, needs={Need.TRACE}, optional=("prefix",), kind=registry.Kind.CHECK
)
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
