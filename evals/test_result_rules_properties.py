"""Property tests for the eval runner's result rules, trace parser and scenario contract.

Each property is a rule the runner promises for every input, not one example, and Hypothesis searches
for a counterexample: a supported failure is never hidden (threat-model ADR result rule 3), a
requiring check never fails a run that was cut short (rules 2 and 4), a run voided by its identity
measures nothing (rule 1), a grader crash is never a verdict (rule 5), an unknown cost never counts as
zero (rule 7), and aggregation never improves when a trial gets worse. The grading properties drive
the production loop, `assess` then `roll_up`, and each expected answer comes from the rule itself, not
from the code under test. `derandomize` makes every run search the same examples, so a CI failure
reproduces locally, and no example database is written into the checkout.

The validator cases pin the exact problems `--validate` reports, in order: validation order and
wording are a contract (docs/python-eval-modernization.md), so a refactor of the validator must keep
both.

Run directly: python evals/test_result_rules_properties.py
"""
from __future__ import annotations

import json
import math
import re
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

from hypothesis import given, settings
from hypothesis import strategies as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_probe  # noqa: E402
from test_build_probe import INTENDED_POLARITY  # noqa: E402  (the reviewed table, not the declarations)

RULES = settings(derandomize=True, database=None, deadline=None, max_examples=150)
GRADES = settings(derandomize=True, database=None, deadline=None, max_examples=60)
UNMEASURED_PREFIXES = ("INCONCLUSIVE: ", "instrument: ", build_probe.rubric_judge.INCONCLUSIVE_PREFIX)
STATES = ("PASS", "INCONCLUSIVE", "FAIL")
RANK = {"FAIL": 0, "INCONCLUSIVE": 1, "PASS": 2}
FORBIDDING = sorted(name for name, polarity in INTENDED_POLARITY.items() if polarity == "forbids")
REQUIRING = sorted(name for name, polarity in INTENDED_POLARITY.items() if polarity == "requires")

free_text = st.text(max_size=30).filter(lambda text: not text.startswith(UNMEASURED_PREFIXES))
letters = st.text(alphabet="abcdefgh ", max_size=30)
needles = st.text(alphabet="abcdefgh", min_size=1, max_size=3)


@st.composite
def graded_checks(draw: st.DrawFn) -> tuple[str, dict]:
    """A saved check and the state the result rules give it: a pass is a pass, unmeasured evidence
    is INCONCLUSIVE whatever it says next, and any other failure is a supported FAIL."""
    state = draw(st.sampled_from(STATES))
    detail = draw(free_text)
    if state == "PASS":
        evidence = draw(st.sampled_from(("", *UNMEASURED_PREFIXES))) + detail
    elif state == "INCONCLUSIVE":
        evidence = draw(st.sampled_from(UNMEASURED_PREFIXES)) + detail
    else:
        evidence = detail
    return state, {"text": "check", "passed": state == "PASS", "evidence": evidence}


class SavedVerdictProperties(unittest.TestCase):
    """A saved grade's checks, read from their text and rolled up as a regrade reads them."""

    @RULES
    @given(st.lists(graded_checks(), max_size=8), st.one_of(st.none(), free_text))
    def test_a_supported_failure_is_never_hidden(self, graded: list[tuple[str, dict]], unmeasured: str | None) -> None:
        states = [state for state, _ in graded]
        checks = [check for _, check in graded]
        status, reason = build_probe.trial_status(checks, unmeasured)
        self.assertEqual(states, [check["state"] for check in checks])
        first = next((c["evidence"].removeprefix("INCONCLUSIVE: ") for s, c in graded if s == "INCONCLUSIVE"), None)
        self.assertEqual(unmeasured or first, reason)
        if "FAIL" in states:
            self.assertEqual("FAIL", status)
        elif "INCONCLUSIVE" in states or unmeasured:
            self.assertEqual("INCONCLUSIVE", status)
        else:
            self.assertEqual("PASS", status)


FOUND = ("pass", "fail", "violation", "unmeasured", "instrument", "crash")
KEPT = (None, "pass", "fail", "unmeasured", "missing")


@st.composite
def plans(draw: st.DrawFn) -> tuple[list[dict], str]:
    """Expectations as a grade or a regrade plans them, and how the run ended. Each has a polarity,
    what measuring it would find, and, for a regrade, the live verdict it keeps instead (or none saved)."""
    items = [{"polarity": draw(st.sampled_from(("forbids", "requires", "both"))),
              "found": draw(st.sampled_from(FOUND)),
              "kept": draw(st.sampled_from(KEPT))} for _ in range(draw(st.integers(min_value=0, max_value=6)))]
    return items, draw(st.sampled_from(("completed", "cut", "void")))


def _measured(found: str) -> build_probe.Outcome:
    if found == "crash":
        raise RuntimeError("grader defect")
    return {"pass": build_probe.verdict(True, "seen"), "fail": build_probe.verdict(False, "not seen"),
            "violation": build_probe.violation("did the forbidden thing"),
            "unmeasured": build_probe.unmeasured("no data"), "instrument": build_probe.instrument("no snapshot")}[found]


SAVED_VERDICTS = {"pass": build_probe.verdict(True, "kept pass"), "fail": build_probe.verdict(False, "kept fail"),
                  "unmeasured": build_probe.unmeasured("kept unmeasured"), "missing": None}


def _expected(item: dict, run: str) -> tuple[str, bool]:
    """What the result rules say one expectation grades to, and whether it was measured."""
    found = {"pass": "PASS", "fail": "FAIL", "violation": "FAIL"}.get(item["found"], "INCONCLUSIVE")
    kept = None if item["kept"] is None else {"pass": "PASS", "fail": "FAIL"}.get(item["kept"], "INCONCLUSIVE")
    if run == "void":
        return "INCONCLUSIVE", False  # rule 1: a void run measures nothing
    if run == "cut" and item["polarity"] == "both":  # measured; only the forbidden ceiling breaking stands
        return ("FAIL" if item["found"] == "violation" else "INCONCLUSIVE"), True
    if run == "cut" and item["polarity"] == "requires":
        return "INCONCLUSIVE", False  # rules 2 and 4: an unmet requirement proves nothing yet
    if kept is not None:
        return kept, False
    if run == "cut":  # forbids: evidence of the forbidden action stands, its absence proves nothing yet
        return ("FAIL" if found == "FAIL" else "INCONCLUSIVE"), True
    return found, True


class GradingLoopProperties(unittest.TestCase):
    @RULES
    @given(plans())
    def test_the_grading_loop_follows_the_result_rules(self, drawn: tuple[list[dict], str]) -> None:
        items, run = drawn
        calls: list[int] = []

        def measure(index: int) -> build_probe.Outcome:
            calls.append(index)
            return _measured(items[index]["found"])

        plan = [build_probe.Expectation(
            f"e{index}", (lambda index=index: measure(index)), build_probe.Polarity(item["polarity"]),
            on_cut=build_probe.routing_on_cut if item["polarity"] == "both" else None,
            kept_as="workspace-dependent" if item["kept"] else None) for index, item in enumerate(items)]
        inconclusive = {"completed": None, "void": "wrong plugin",
                        "cut": build_probe.CutShort("timed out after 60s", "wall_clock")}[run]
        kept = (lambda index, _item: SAVED_VERDICTS[items[index]["kept"]]) if any(i["kept"] for i in items) else None
        graded, reason = build_probe.assess(plan, inconclusive, kept=kept)
        status, _ = build_probe.roll_up([g.outcome for g in graded], inconclusive or reason)

        expected = [_expected(item, run) for item in items]
        self.assertEqual([state for state, _ in expected], [g.outcome.state for g in graded])
        self.assertEqual([index for index, (_, measured) in enumerate(expected) if measured], calls)
        machinery = [measured and item["found"] in ("instrument", "crash")
                     for item, (_, measured) in zip(items, expected, strict=True)]
        self.assertEqual(machinery, [g.outcome.machinery for g in graded], "rule 5: a machinery failure stays one")
        self.assertEqual(any(machinery), bool(build_probe.assessment.machinery_failure(graded)))
        for item, g in zip(items, graded, strict=True):
            if item["polarity"] == "forbids" and g.outcome.state == "FAIL":
                self.assertTrue(g.outcome.forbidden, "every failure of a forbidding expectation is a violation")
        states = [state for state, _ in expected]
        self.assertEqual("FAIL" if "FAIL" in states else "INCONCLUSIVE" if "INCONCLUSIVE" in states or inconclusive
                         else "PASS", status)


class AggregationProperties(unittest.TestCase):
    @RULES
    @given(st.lists(st.sampled_from(STATES), min_size=1, max_size=40), st.integers(min_value=1, max_value=100))
    def test_a_threshold_is_met_by_exactly_its_share_of_passes(self, states: list[str], percent: int) -> None:
        # In whole numbers: passes / trials >= percent / 100 exactly when 100 * passes >= percent * trials.
        passes, unknown, trials = states.count("PASS"), states.count("INCONCLUSIVE"), len(states)
        expected = ("PASS" if 100 * passes >= percent * trials
                    else "FAIL" if 100 * (passes + unknown) < percent * trials else "INCONCLUSIVE")
        self.assertEqual(expected, build_probe.aggregate_verdict(states, percent / 100))

    @RULES
    @given(st.lists(st.sampled_from(STATES), min_size=1, max_size=9), st.floats(min_value=0.01, max_value=1.0))
    def test_a_verdict_never_improves_when_a_trial_gets_worse(self, states: list[str], threshold: float) -> None:
        verdict = build_probe.aggregate_verdict(states, threshold)
        for index, state in enumerate(states):
            for worse in (s for s in STATES if RANK[s] < RANK[state]):
                worsened = [*states[:index], worse, *states[index + 1:]]
                self.assertLessEqual(RANK[build_probe.aggregate_verdict(worsened, threshold)], RANK[verdict])

    @RULES
    @given(st.lists(st.sampled_from(FORBIDDING), min_size=1, max_size=3),
           st.lists(st.sampled_from(REQUIRING), max_size=3),
           st.one_of(st.none(), st.floats(min_value=0.01, max_value=1.0)),
           st.one_of(st.none(), st.floats(min_value=0.01, max_value=1.0)))
    def test_a_forbidding_check_holds_every_trial(self, forbidding: list[str], requiring: list[str],
                                                  requested: float | None, declared: float | None) -> None:
        spec = {"id": "s", "checks": [{"check": name} for name in [*requiring, *forbidding]],
                **({"threshold": declared} if declared is not None else {})}
        self.assertEqual(1.0, build_probe.effective_threshold(spec, requested))

    @RULES
    @given(st.integers(min_value=0, max_value=5), st.integers(min_value=0, max_value=5),
           st.one_of(st.none(), st.floats(min_value=0.01, max_value=1.0)))
    def test_a_tool_call_ceiling_holds_every_trial(self, minimum: int, extra: int, requested: float | None) -> None:
        spec = {"id": "s", "checks": [{"check": "tool_call_count", "tool": "WebFetch",
                                       "minimum": minimum, "maximum": minimum + extra}]}
        self.assertEqual(1.0, build_probe.effective_threshold(spec, requested))

    @RULES
    @given(st.lists(st.sampled_from(REQUIRING), min_size=1, max_size=3),
           st.one_of(st.none(), st.floats(min_value=0.01, max_value=1.0)),
           st.one_of(st.none(), st.floats(min_value=0.01, max_value=1.0)))
    def test_only_requiring_checks_take_a_lower_threshold(self, requiring: list[str], requested: float | None,
                                                          declared: float | None) -> None:
        spec = {"id": "s", "checks": [{"check": name} for name in requiring],
                **({"threshold": declared} if declared is not None else {})}
        expected = requested if requested is not None else declared if declared is not None else 1.0
        self.assertEqual(expected, build_probe.effective_threshold(spec, requested))


costs = st.one_of(st.none(), st.booleans(), st.text(max_size=3), st.integers(min_value=-5, max_value=5),
                  st.floats(allow_nan=True, allow_infinity=True))


class CostProperties(unittest.TestCase):
    @RULES
    @given(costs)
    def test_only_a_finite_non_negative_number_is_a_known_cost(self, value: object) -> None:
        valid = type(value) in (int, float) and math.isfinite(value) and value >= 0
        known = build_probe.known_usd(value)
        self.assertEqual(valid, known is not None)
        if valid:
            self.assertEqual(float(value), known)

    @RULES
    @given(costs, st.one_of(st.none(), st.floats(min_value=0, max_value=100)), st.floats(min_value=0, max_value=100))
    def test_a_total_is_known_only_when_every_part_is(self, trial: object, judge_total: float | None,
                                                      judge_known: float) -> None:
        cost = build_probe.trial_cost(trial, {"cost_usd": judge_total, "known_cost_usd": judge_known})
        complete = build_probe.known_usd(trial) is not None and judge_total is not None
        self.assertEqual(complete, cost["cost_complete"])
        self.assertEqual(complete, cost["cost_usd"] is not None)
        self.assertAlmostEqual((build_probe.known_usd(trial) or 0.0) + judge_known, cost["known_cost_usd"], places=5)

    @RULES
    @given(st.lists(st.fixed_dictionaries({"cost_usd": costs, "seconds": st.floats(min_value=0, max_value=60),
                                           "cached": st.booleans()}), max_size=6))
    def test_an_unpriced_judge_call_leaves_the_judge_total_unknown(self, calls: list[dict]) -> None:
        stub = types.SimpleNamespace(drain_spend=lambda: list(calls))
        with mock.patch.dict(sys.modules, {"judge": stub}):
            spend = build_probe.judge_spend()
        unknown = sum(build_probe.known_usd(call["cost_usd"]) is None for call in calls)
        self.assertEqual((len(calls), unknown), (spend["calls"], spend["unknown_cost_calls"]))
        self.assertEqual(unknown == 0, spend["cost_usd"] is not None)
        self.assertEqual(len(calls), spend["live_calls"] + spend["cached_calls"])


def _text_spec(needle: str, word: str) -> dict:
    return {"id": "cut", "prompt": "p", "agent": "software-engineer", "checks": [
        {"check": "text_not_contains", "needle": needle, "text": "never says the needle"},
        {"check": "text_contains_any", "of": [word], "text": "says the word"}]}


class RunEndProperties(unittest.TestCase):
    """Result rules 1, 2 and 4 on a forbidding and a requiring check over the same response."""

    @staticmethod
    def _grade(text: str, needle: str, word: str, inconclusive: str | None = None) -> dict:
        ctx = build_probe.Context(_text_spec(needle, word), None, build_probe.TraceSummary(result_text=text), None)
        return build_probe.grade(ctx, inconclusive=inconclusive)

    @GRADES
    @given(letters, needles, needles)
    def test_a_cut_short_run_fails_only_on_evidence_of_a_forbidden_action(self, text: str, needle: str,
                                                                          word: str) -> None:
        grading = self._grade(text, needle, word, build_probe.CutShort("timed out after 60s", "wall_clock"))
        violated = needle in text
        self.assertEqual(["FAIL" if violated else "INCONCLUSIVE", "INCONCLUSIVE"],
                         [e["state"] for e in grading["expectations"]])
        self.assertEqual(("FAIL" if violated else "INCONCLUSIVE", "cut_short", "wall_clock"),
                         (grading["status"], grading["run_end"], grading["run_stop"]))

    @GRADES
    @given(letters, needles, needles, free_text.filter(str.strip))
    def test_a_void_run_measures_nothing(self, text: str, needle: str, word: str, reason: str) -> None:
        grading = self._grade(text, needle, word, reason)
        self.assertEqual(["INCONCLUSIVE", "INCONCLUSIVE"], [e["state"] for e in grading["expectations"]])
        self.assertEqual(("INCONCLUSIVE", reason), (grading["status"], grading["void"]))
        self.assertNotIn("unmeasured", grading)

    @GRADES
    @given(letters, needles, needles)
    def test_a_completed_run_is_graded_on_what_it_shows(self, text: str, needle: str, word: str) -> None:
        grading = self._grade(text, needle, word)
        states = ["FAIL" if needle in text else "PASS", "PASS" if word in text else "FAIL"]
        self.assertEqual(states, [e["state"] for e in grading["expectations"]])
        self.assertEqual("FAIL" if "FAIL" in states else "PASS", grading["status"])
        self.assertNotIn("run_end", grading)


@st.composite
def rescores(draw: st.DrawFn) -> dict:
    runs = []
    for run in draw(st.lists(st.integers(min_value=1, max_value=4), unique=True, max_size=4)):
        row = {"scenario": "s", "label": "l", "run": run}
        if draw(st.booleans()):
            row["rescored"] = {"status": draw(st.sampled_from(STATES)), "checks": [
                {"text": draw(st.sampled_from(("a", "b"))), "state": draw(st.sampled_from(STATES)), "evidence": "e"}
                for _ in range(draw(st.integers(min_value=0, max_value=3)))]}
        else:
            row["error"] = "unreadable"
        runs.append(row)
    return {"runner": {}, "runs": runs}


class RescoreDiffProperties(unittest.TestCase):
    @RULES
    @given(rescores(), rescores())
    def test_a_rescore_diff_is_empty_against_itself_and_the_same_size_both_ways(self, base: dict,
                                                                               candidate: dict) -> None:
        self.assertEqual([], build_probe.rescore_diff(base, base))
        self.assertEqual(len(build_probe.rescore_diff(base, candidate)),
                         len(build_probe.rescore_diff(candidate, base)))

    @RULES
    @given(rescores(), st.data())
    def test_a_rescore_diff_names_exactly_the_runs_that_changed(self, base: dict, data: st.DataObject) -> None:
        candidate = json.loads(json.dumps(base))
        changed = set()
        for row in candidate["runs"]:
            change = data.draw(st.sampled_from(("none", "status", "check")))
            if change == "none":
                continue
            if "error" in row:  # an unreadable run that now rescores
                del row["error"]
                row["rescored"] = {"status": "PASS", "checks": []}
            elif change == "check" and row["rescored"]["checks"]:
                check = row["rescored"]["checks"][data.draw(st.integers(0, len(row["rescored"]["checks"]) - 1))]
                check["state"] = data.draw(st.sampled_from([s for s in STATES if s != check["state"]]))
            else:
                row["rescored"]["status"] = data.draw(st.sampled_from([s for s in STATES
                                                                       if s != row["rescored"]["status"]]))
            changed.add(row["run"])
        named = {int(re.search(r"/run-(\d+)", line).group(1)) for line in build_probe.rescore_diff(base, candidate)}
        self.assertEqual(changed, named)


TOOL_INPUTS = {
    "Skill": {"skill": "save-toolkit:runbook"}, "Bash": {"command": "python -m pytest -q"},
    "PowerShell": {"command": "Get-ChildItem"}, "Task": {"subagent_type": "save-toolkit:scribe"},
    "Agent": {"subagent_type": "save-toolkit:researcher"}, "Read": {"file_path": "/tmp/notes.md"},
    "Grep": {"pattern": "todo", "path": "."}, "Glob": {"pattern": "*.py"}, "Write": {"file_path": "a.py"},
    "Edit": {"file_path": "b.py"},
}


@st.composite
def traces(draw: st.DrawFn) -> tuple[list[dict], list[tuple[str, str | None, str]]]:
    """A stream-json trace: an optional init event, tool calls each followed by a clean result, an error
    result or none, and an optional result event."""
    events: list[dict] = []
    calls: list[tuple[str, str | None, str]] = []
    if draw(st.booleans()):
        events.append({"type": "system", "subtype": "init", "session_id": "s", "model": "m", "tools": [],
                       "plugins": [], "mcp_servers": []})
    for number in range(draw(st.integers(min_value=0, max_value=8))):
        name = draw(st.sampled_from(sorted(TOOL_INPUTS)))
        parent = draw(st.sampled_from((None, "task-1")))
        use_id = f"tu{number}"
        events.append({"type": "assistant", **({"parent_tool_use_id": parent} if parent else {}), "message": {
            "model": "m", "content": [{"type": "tool_use", "id": use_id, "name": name, "input": TOOL_INPUTS[name]}]}})
        returned = draw(st.sampled_from(("clean", "error", "none")))
        if returned != "none":
            events.append({"type": "user", "message": {"content": [
                {"type": "tool_result", "tool_use_id": use_id, "is_error": returned == "error", "content": "r"}]}})
        calls.append((name, parent, returned))
    if draw(st.booleans()):
        events.append({"type": "result", "result": "done", "duration_ms": 1, "usage": {}})
    return events, calls


class TraceParserProperties(unittest.TestCase):
    """Every tool call the trace shows is counted once, and a load or dispatch is credited only when
    its own call returned cleanly."""

    @RULES
    @given(traces())
    def test_every_tool_call_is_accounted_for(self, drawn: tuple[list[dict], list[tuple[str, str | None, str]]]) -> None:
        events, calls = drawn
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "stdout.jsonl"
            path.write_text("\n".join(json.dumps(event) for event in events), encoding="utf-8")
            trace = build_probe.parse_trace(path)
        names = [name for name, _, _ in calls]
        clean = [name for name, _, returned in calls if returned == "clean"]
        self.assertEqual(len(calls), sum(trace.tool_counts.values()))
        self.assertEqual((names.count("Bash"), names.count("PowerShell")),
                         (len(trace.bash_commands), len(trace.powershell_commands)))
        self.assertEqual(sum(1 for name, parent, _ in calls if name == "Bash" and parent),
                         len(trace.subagent_bash_commands))
        self.assertEqual((clean.count("Skill"), names.count("Skill") - clean.count("Skill")),
                         (len(trace.skills), len(trace.skills_failed)))
        dispatched = names.count("Task") + names.count("Agent")
        completed = clean.count("Task") + clean.count("Agent")
        self.assertEqual((dispatched, completed, dispatched - completed),
                         (len(trace.dispatches), len(trace.agents), len(trace.agents_failed)))
        self.assertEqual(sum(names.count(tool) for tool in ("Read", "Grep", "Glob")), len(trace.read_attempts))
        self.assertEqual(sum(name in build_probe.WRITING_TOOLS | {"Task", "Agent"} for name in names),
                         len(trace.effect_calls))
        self.assertEqual(any(event["type"] == "result" for event in events), trace.has_result)


BUILD = {"id": "case", "agent": "software-engineer", "prompt": "do the thing",
         "fixture": {"files": {"README.md": "# tiny\n"}}, "checks": [{"check": "no_new_commits"}]}
CONTRACT = {"id": "case", "agent": "sre-assistant", "prompt": "p", "graders": [{"type": "contains_any", "of": ["x"]}]}
ROUTING = {"id": "case", "prompt": "Latency tripled on checkout.", "target": {"kind": "skill", "name": "runbook"},
           "routing": {"expect": "fire"}}
NATIVE = {"id": "case", "agent": "reliability-engineer", "prompt": "Help me investigate.",
          "tools": ["Skill", "Read", "Task"], "fixture": {"files": {"evidence.md": "x"}},
          "followups": ["What changes?"], "helper": "sre-assistant", "expected_model": "stub-model"}
GRAFANA = "grafana/grafana@sha256:62d2b9d20a19714ebfe48d1bb405086081bc602aa053e28cf6d73c7537640dfb"
REFERENCE = "skills/agent-authoring/references/agent-security.md"
DROP = object()


def _changed(base: dict, **changes: object) -> dict:
    spec = json.loads(json.dumps(base))
    for key, value in changes.items():
        if value is DROP:
            spec.pop(key, None)
        else:
            spec[key] = value
    return spec


def _fixture(**changes: object) -> dict:
    return {**BUILD["fixture"], **changes}


def _checks(*checks: dict) -> list[dict]:
    return list(checks)


VALIDATOR_CASES: list[tuple[str, dict, list[str]]] = [
    ("missing prompt", _changed(BUILD, prompt=DROP),
     ["case: missing key 'prompt'", "case: prompt must be a non-empty string"]),
    ("unsafe id", _changed(BUILD, id="Eval One"), ["case: id must be a canonical lowercase slug, got 'Eval One'"]),
    ("build without an agent", _changed(BUILD, agent=DROP), ["case: a build scenario must pin `agent`"]),
    ("agent and skill", _changed(BUILD, skill="runbook"), ["case: pin `agent` or `skill`, not both"]),
    ("empty tools", _changed(BUILD, tools=[]), ["case: tools must be a non-empty list of tool names"]),
    ("unknown split", _changed(BUILD, split="train"), ["case: split must be one of ['calibration', 'regression']"]),
    ("empty success criteria", _changed(BUILD, success_criteria=[]),
     ["case: success_criteria must be a non-empty list of strings"]),
    ("escaping fixture file", _changed(BUILD, fixture=_fixture(files={"README.md": "x", "../x": "y"})),
     ["case: fixture file '../x' must be a relative path inside the repo"]),
    ("non-text fixture file", _changed(BUILD, fixture=_fixture(files={"README.md": "x", "a.txt": 1})),
     ["case: fixture file 'a.txt' content must be a string"]),
    ("branch without files", _changed(BUILD, fixture=_fixture(branches={"fork": {"message": "m"}})),
     ["case: branch 'fork' must declare files"]),
    ("branches as a list", _changed(BUILD, fixture=_fixture(branches=["fork"], checkout="fork")),
     ["case: fixture.branches must map branch names to branches that declare files",
      "case: fixture.checkout 'fork' must be main or a declared branch"]),
    ("unknown checkout", _changed(BUILD, fixture=_fixture(checkout="nope")),
     ["case: fixture.checkout 'nope' must be main or a declared branch"]),
    ("checkout as a list", _changed(BUILD, fixture=_fixture(checkout=["fork"])),
     ["case: fixture.checkout ['fork'] must be main or a declared branch"]),
    ("non-text uncommitted file", _changed(BUILD, fixture=_fixture(uncommitted={"x.py": 1})),
     ["case: fixture.uncommitted must map relative paths to string content"]),
    ("shim without a shebang", _changed(BUILD, fixture=_fixture(fake_bin={"cf": "echo"})),
     ["case: fake_bin 'cf' must be a script starting with a shebang"]),
    ("fake_bin as a script", _changed(BUILD, fixture=_fixture(fake_bin="#!/bin/sh")),
     ["case: fixture.fake_bin must map command names to scripts"]),
    ("fake_bin as a script beside a service without an image", _changed(BUILD, fixture=_fixture(
        fake_bin="#!/bin/sh", services=[{"name": "grafana"}])),
     ["case: fixture.fake_bin must map command names to scripts", "case: each service needs a name and an image"]),
    ("unreviewed service image", _changed(BUILD, fixture=_fixture(services=[
        {"name": "grafana", "image": "example.invalid/x@sha256:" + "0" * 64}])),
     [f"case: service 'grafana' must use a reviewed service image; allowed: {sorted(build_probe.TRUSTED_SERVICE_IMAGES)}"]),
    ("service without an image", _changed(BUILD, fixture=_fixture(services=[{"name": "grafana"}])),
     ["case: each service needs a name and an image"]),
    ("service command not a list", _changed(BUILD, fixture=_fixture(services=[
        {"name": "grafana", "image": GRAFANA, "command": "x"}])),
     ["case: service 'grafana' command must be a string list"]),
    ("unknown check", _changed(BUILD, checks=_checks({"check": "nope"})),
     ["case: checks[0] names an unknown check {'check': 'nope'}"]),
    ("unknown fleet grader", _changed(BUILD, checks=_checks({"check": "fleet_grader", "name": "nope"})),
     ["case: checks[0] fleet_grader names an unknown grader 'nope'"]),
    ("scope on a text check", _changed(BUILD, checks=_checks({"check": "text_regex", "pattern": "x", "scope": "subagent"})),
     ["case: checks[0] scope is only `subagent`, on bash_ran, bash_did_not_run, or ran_outside_checkout"]),
    ("unknown test runner", _changed(BUILD, checks=_checks({"check": "verification_completed", "runner": "nose"})),
     ["case: checks[0] verification_completed needs runner unittest, pytest, or vitest"]),
    ("measurement exit on another check", _changed(BUILD, checks=_checks({"check": "no_new_commits",
                                                                          "inconclusive_exit_code": 3})),
     ["case: checks[0] inconclusive_exit_code needs command_exit_zero and an integer from 1 to 255"]),
    ("non-boolean before_effects", _changed(BUILD, checks=_checks({"check": "skill_loaded", "skill": "x",
                                                                   "before_effects": "yes"})),
     ["case: checks[0] before_effects must be boolean"]),
    ("inverted tool-call bounds", _changed(BUILD, checks=_checks({"check": "tool_call_count", "tool": "Read",
                                                                  "minimum": 2, "maximum": 1})),
     ["case: checks[0] tool_call_count needs a tool and 0 <= minimum <= maximum integers"]),
    ("list-shaped writes_from", _changed(BUILD, checks=_checks({"check": "command_exit_zero", "command": "x",
                                                                "writes_from": ["a"]})),
     ["case: checks[0] writes_from must be a mapping of non-empty name to oracle path"]),
    ("writes_from outside the oracles", _changed(BUILD, checks=_checks({"check": "command_exit_zero", "command": "x",
                                                                        "writes_from": {"p.py": "evals/build_probe.py"}})),
     ["case: checks[0] writes_from 'evals/build_probe.py' is not a file under evals/oracles/"]),
    ("zero turns", _changed(BUILD, max_turns=0), ["case: max_turns must be an integer from 1 to 500"]),
    ("threshold out of range", _changed(BUILD, threshold=1.5), ["case: threshold must be > 0 and <= 1"]),
    ("lowered threshold beside a forbidding check", _changed(BUILD, threshold=0.5),
     ["case: a scenario with a forbidding check passes only when every trial passes; threshold must be 1"]),
    ("several problems keep their order", _changed(BUILD, id="Bad Id", prompt=DROP, tools=[], split="x",
                                                   max_turns=0, threshold=2),
     ["case: missing key 'prompt'", "case: id must be a canonical lowercase slug, got 'Bad Id'",
      "case: prompt must be a non-empty string", "case: tools must be a non-empty list of tool names",
      "case: split must be one of ['calibration', 'regression']", "case: max_turns must be an integer from 1 to 500",
      "case: threshold must be > 0 and <= 1"]),
    ("contract without graders or a pin", {"id": "case", "prompt": "p"},
     ["case: a contract scenario needs `graders`", "case: a contract scenario must pin `agent` or `skill`"]),
    ("unknown grader type", _changed(CONTRACT, graders=[{"type": "nope"}]),
     ["case: graders[0] names an unknown grader type 'nope'"]),
    ("graders not a list", _changed(CONTRACT, graders="x"), ["case: graders must be a non-empty list"]),
    ("checks on a contract", _changed(CONTRACT, checks=[{"check": "file_exists", "path": "a"}]),
     ["case: `checks` grade a fixture workspace; a contract scenario has none"]),
    ("references without Read", _changed(CONTRACT, references=[REFERENCE], tools=["Skill"]),
     ["case: a scenario with `references` must grant the Read tool in `tools`"]),
    ("escaping reference", _changed(CONTRACT, references=["../x.md"], tools=["Read"]),
     ["case: references must be a non-empty list of repo-relative paths"]),
    ("target without routing", _changed(CONTRACT, target={"kind": "skill", "name": "runbook"}),
     ["case: `target` belongs to a routing scenario"]),
    ("routing prompt names its target", _changed(ROUTING, prompt="Use the runbook."),
     ["case: routing prompt names its target; it must be byte-for-byte unhinted"]),
    ("routing pins an agent", _changed(ROUTING, agent="sre-assistant"),
     ["case: a routing scenario runs the main session and must not pin `agent`"]),
    ("negative without an alternative", _changed(ROUTING, routing={"expect": "not_fire"}),
     ["case: routing.expect not_fire requires expected_alternative"]),
    ("alternative on a positive", _changed(ROUTING, routing={"expect": "fire", "expected_alternative": "inline"}),
     ["case: routing.expected_alternative is only valid for not_fire"]),
    ("lowered threshold on a negative", _changed(ROUTING, routing={"expect": "not_fire", "expected_alternative": "inline"},
                                                 threshold=0.5),
     ["case: not_fire scenarios are zero-tolerance; threshold must be 1 (it applies to positives only)"]),
    ("unknown target key", _changed(ROUTING, target={"kind": "skill", "name": "runbook", "x": 1}),
     ["case: target has unknown key(s): x"]),
    ("unknown routing key", _changed(ROUTING, routing={"expect": "fire", "why": 1}),
     ["case: routing has unknown key(s): why"]),
    ("two follow-ups", _changed(NATIVE, followups=["a", "b"]),
     ["case: followups must contain exactly one non-empty human prompt"]),
    ("native write tool", _changed(NATIVE, tools=["Skill", "Read", "Task", "Write"]),
     ["case: native conversation tools must be [Skill, Read, Task]"]),
    ("unknown helper", _changed(NATIVE, helper="missing-agent"),
     ["case: native conversation helper must name a canonical agent"]),
    ("model alias", _changed(NATIVE, expected_model="sonnet"),
     ["case: expected_model must name the concrete native model identity"]),
    ("expected model outside a conversation", _changed(CONTRACT, expected_model="x"),
     ["case: expected_model is a native conversation assertion"]),
    ("helper outside a conversation", _changed(CONTRACT, helper="sre-assistant"),
     ["case: helper assertion requires a native conversation"]),
]


class ValidatorParityTests(unittest.TestCase):
    """The problems `--validate` reports, word for word and in order (a contract for any refactor)."""

    def test_the_valid_bases_report_nothing(self) -> None:
        for name, spec in (("build", BUILD), ("contract", CONTRACT), ("routing", ROUTING), ("native", NATIVE)):
            with self.subTest(base=name):
                self.assertEqual([], build_probe.validate_scenario(spec, where="case"))

    def test_each_problem_keeps_its_wording_and_order(self) -> None:
        for name, spec, expected in VALIDATOR_CASES:
            with self.subTest(case=name):
                self.assertEqual(expected, build_probe.validate_scenario(spec, where="case"))


if __name__ == "__main__":
    unittest.main()
