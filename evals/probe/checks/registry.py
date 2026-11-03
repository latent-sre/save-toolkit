"""The check registry: what a declaration says about a check, and the context every check reads.

A check's declaration is the single place its meaning lives (threat-model ADR result rules 2 and 3):
- `polarity`: whether it forbids an action, requires an outcome, or both (a floor and a ceiling);
- `needs`: the evidence it reads, from which a regrade decides whether it can re-measure the check
  from a saved run or must keep the live verdict;
- `kind`: whether it is a *check*, re-measured from saved evidence, or a *probe*, which reads the
  live checkout, a backing service or a paid judge and whose live outcome is therefore evidence;
- `on_cut`: how a `both` check is graded on a run cut short;
- `names_unmeasured`: whether its own INCONCLUSIVE names the trial's reason.

Grading and regrading read these declarations directly, so a new check cannot be registered
without being classified. The checks themselves live in this package's domain modules; `checking`
keeps every name importable.
"""

from __future__ import annotations

import enum
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Final

import judge as rubric_judge

from .. import constants
from ..backing import Service
from ..constants import ROOT
from ..outcomes import Outcome, Polarity
from ..tracing import TraceSummary
from ..workspaces import GitFacts, Workspace

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
    service_problem: str | None = None
    tool_counts_recorded: bool = True


class Need(enum.StrEnum):
    """Evidence a check reads. A regrade re-measures a check only from evidence a saved run keeps."""

    TEXT = "final text"
    TRACE = "trace"  # calls, call counts, loads and dispatches: the trace summary restores these
    RAW_TRACE = "raw trace"  # completed returns, reads and the plugin namespace: only the raw trace holds them
    ORDERED_TRACE = "ordered trace"  # completion order, which only the raw trace holds
    CHANGES = "workspace changes"  # commit identities, changed paths and `.agents/`, as the summary records them
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


class Kind(enum.StrEnum):
    """What a declaration registers: a check a regrade re-measures from saved evidence, or a probe
    that runs once at trial time because it reads what leaves with the run."""

    CHECK = "check"
    PROBE = "probe"


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
    kind: Kind | None = None  # None: a check or a probe depending on its parameters; see `kind_of`

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

    def kind_of(self, params: Params, spec: Params) -> Kind:
        """A check when a regrade can re-measure it from the saved run, else a probe."""
        return self.kind or (Kind.CHECK if self.can_regrade(params, spec) else Kind.PROBE)


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
    kind: Kind | None = None,
) -> Callable[[CheckRun], CheckRun]:
    """Register the decorated function as the check `name`, with what it asserts and reads, the
    parameters it takes, and whether it is a check or a probe. A declaration whose needs are fixed
    says which it is, and must agree with its needs; one whose needs depend on its parameters may
    say it when every choice agrees, or leave it to `CheckType.kind_of`."""

    def register(run: CheckRun) -> CheckRun:
        if name in CHECKS:
            raise ValueError(f"check {name!r} is declared twice")
        if polarity is Polarity.BOTH and on_cut is None:
            raise ValueError(f"check {name!r} has a floor and a ceiling but no cut-short rule")
        if polarity is Polarity.BOTH and kind is Kind.PROBE:
            raise ValueError(
                f"check {name!r} is a probe with a floor and a ceiling; a probe's outcome is kept, not cut"
            )
        rule: NeedsRule = needs if callable(needs) else frozenset(needs)
        fixed = rule if isinstance(rule, frozenset) else None
        if fixed is not None:
            derived = Kind.CHECK if (regradable if regradable is not None else fixed <= SAVED) else Kind.PROBE
            if kind is None:
                raise ValueError(f"check {name!r} must say whether it is a check or a probe")
            if kind is not derived:
                raise ValueError(f"check {name!r} is declared a {kind} but its needs make it a {derived}")
        CHECKS[name] = CheckType(
            name,
            run,
            polarity,
            rule,
            names_unmeasured,
            on_cut,
            regradable,
            required,
            optional,
            kind,
        )
        return run

    return register


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
