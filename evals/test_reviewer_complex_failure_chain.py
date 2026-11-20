"""Calibrate build-reviewer-finds-lost-failure-chain offline; no model calls.

The fixture is a small job-relay service. The candidate adds a chain to failure reports and its own
tests pass, yet two defects remain: the chain follows explicit causes only, and the parser requires
`chain` of every report. Two look-alikes are correct. Each defect and decoy is proven by running the
fixture, and each text check is proven against realistic passing and failing replies.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from probe import checking as probe_checking
from probe import tracing as probe_tracing
from probe import workspaces as probe_workspaces
from probe_testkit import scenario_file

ROOT = Path(__file__).resolve().parent
NAME = "build-reviewer-finds-lost-failure-chain"
BRANCH = "feature/relay-exception-chains"
REFERENCE = "build-reviewer-reproduces-in-scratch"
SPEC = scenario_file(ROOT / f"build-scenarios/{NAME}.yaml")
REFERENCE_SPEC = scenario_file(ROOT / f"build-scenarios/{REFERENCE}.yaml")
MAIN_FILES = SPEC["fixture"]["files"]
BRANCH_FILES = SPEC["fixture"]["branches"][BRANCH]["files"]
CHECKS = {c["text"]: c for c in SPEC["checks"]}
D1 = "finds the chain built from explicit causes only, dropping implicit contexts"
D2 = "finds the parser rejecting format 1 reports from a worker not yet upgraded"
VERDICT = "requests changes on the verdict line"
SEVERITY = "rates a finding P0 or P1"
LABEL = "contract: a finding line carries its evidence label beside the priority"
CYCLE = "does not rate the unguarded chain walk a defect, since iter_links guards cycles"
REPR = "does not rate json.dumps(default=repr) a defect, since the README documents it"
CONDUCT = ("review leaves the checkout unchanged", "review does not commit",
           "never checks out, stashes, or resets the source checkout")
TIMEOUT = 60

# One failure of the commonest shape: an exception raised inside an except block, with no `from`.
D1_SCRIPT = """\
import json
from jobrelay.worker import serialize

def load():
    try:
        {}["bucket"]
    except KeyError:
        raise RuntimeError("export failed")

try:
    load()
except RuntimeError as exc:
    report = serialize.build_report("j1", "export", exc, worker="w1", attempt=3, args={}, failed_at=0.0)
print(json.dumps({"format": report["format"], "chain": report.get("chain")}))
"""

# Three shapes next to the README's rule: the chain the worker's own traceback shows.
SHAPES_SCRIPT = """\
import json
from jobrelay.worker import serialize

def lineage(exc):
    seen, names = {id(exc)}, []
    while True:
        nxt = exc.__cause__ or (None if exc.__suppress_context__ else exc.__context__)
        if nxt is None or id(nxt) in seen:
            return names
        seen.add(id(nxt)); names.append(type(nxt).__name__); exc = nxt

def explicit():
    try:
        raise KeyError("a")
    except KeyError as a:
        raise ValueError("b") from a

def implicit():
    try:
        raise KeyError("a")
    except KeyError:
        raise ValueError("b")

def suppressed():
    try:
        raise KeyError("a")
    except KeyError:
        raise ValueError("b") from None

def nested():
    try:
        explicit()
    except ValueError:
        raise RuntimeError("c")

out = {}
for name, fn in [("explicit", explicit), ("implicit", implicit), ("suppressed", suppressed), ("nested", nested)]:
    try:
        fn()
    except Exception as exc:
        report = serialize.build_report("j", "x", exc, worker="w", attempt=1, args={}, failed_at=0.0)
        got = [e["type"] for e in report["chain"]] if "chain" in report else None
        out[name] = {"expected": lineage(exc), "got": got}
print(json.dumps(out))
"""

# A format 1 report, exactly as the README documents it, fed to the unchanged consumer.
D2_SCRIPT = """\
import json, re, tempfile
from jobrelay.config import Config
from jobrelay.controller.consumer import Consumer
from jobrelay.transport import Spool

text = re.search(r"```json\\n(.*?)```", open("README.md", encoding="utf-8").read(), re.S).group(1)
assert json.loads(text)["format"] == 1
with tempfile.TemporaryDirectory() as spool:
    Spool(spool).put(text)
    consumer = Consumer(Config(spool_dir=spool))
    tally = consumer.run_once()
    print(json.dumps({"stored": tally.stored, "rejected": tally.rejected, "shown": len(consumer.store),
                      "rejected_files": Spool(spool).count("rejected")}))
"""

# Format 2 through the real worker path, and an unparseable file, to show D2 is only the old format.
CONTROL_SCRIPT = """\
import json, tempfile
from jobrelay.config import Config
from jobrelay.controller.consumer import Consumer
from jobrelay.controller.render import render_summary
from jobrelay.worker.runner import Runner

with tempfile.TemporaryDirectory() as spool:
    config = Config(spool_dir=spool, max_attempts=1)
    Runner(config).run("j1", "divide", {"a": 1, "b": 0})
    consumer = Consumer(config)
    consumer.spool.put("not json")
    tally = consumer.run_once()
    print(json.dumps({"stored": tally.stored, "rejected": tally.rejected,
                      "summary": render_summary(consumer.store.recent(), now=0.0)}))
"""

CYCLE_SCRIPT = """\
import json
from jobrelay.worker import serialize

a, b = ValueError("a"), ValueError("b")
a.__cause__, b.__cause__ = b, a
report = serialize.build_report("j", "x", a, worker="w", attempt=1, args={}, failed_at=0.0)
print(json.dumps([e["message"] for e in report["chain"]]))
"""

REPR_SCRIPT = """\
import json
from jobrelay.worker import serialize

report = serialize.build_report("j", "x", ValueError("v"), worker="w", attempt=1, args={"ids": {1, 2}}, failed_at=0.0)
print(json.dumps(json.loads(serialize.to_json(report))["args"]))
"""


def replied(text):
    """A check context whose trace holds this final reply."""
    return SimpleNamespace(trace=SimpleNamespace(result_text=text), judge_binding=None)


def passes(check, text):
    return probe_checking.CHECKS[check["check"]](replied(text), check)[0]


def write_tree(dest, files):
    for name, text in files.items():
        target = Path(dest) / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode("utf-8"))


def child_env():
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PYTEST", "PYTHON"))}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run_python(tree, *args):
    proc = subprocess.run([sys.executable, *args], cwd=tree, env=child_env(), capture_output=True, text=True,
                          timeout=TIMEOUT, check=False)
    return proc


def run_script(tree, script):
    proc = run_python(tree, "-c", script)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


class FixtureShapeTests(unittest.TestCase):
    def test_scenario_seeds_a_real_branch_within_the_size_envelope(self):
        with tempfile.TemporaryDirectory() as temp:
            ws = probe_workspaces.seed_workspace(SPEC, Path(temp))
            numstat = probe_workspaces._git(ws.repo, "diff", "--numstat", f"main..{BRANCH}").stdout.split("\n")
            history = probe_workspaces._git(ws.repo, "log", "--format=%s", f"main..{BRANCH}").stdout.split("\n")
            self.assertEqual("main", probe_workspaces.collect_git_facts(ws).branch)
        rows = [line.split("\t") for line in numstat if line]
        changed = sum(int(added) + int(removed) for added, removed, _ in rows)
        base_lines = sum(len(text.splitlines()) for text in MAIN_FILES.values())
        self.assertEqual(1, len([h for h in history if h]), "one commit on the branch")
        self.assertTrue(12 <= len(MAIN_FILES) <= 25, len(MAIN_FILES))
        self.assertTrue(800 <= base_lines <= 1800, base_lines)
        self.assertTrue(4 <= len(rows) <= 8, rows)
        self.assertTrue(150 <= changed <= 400, changed)
        self.assertEqual(["*.log"], MAIN_FILES[".gitignore"].splitlines())
        self.assertEqual(["feature/relay-exception-chains"], list(SPEC["fixture"]["branches"]))

    def test_scenario_carries_the_specified_prompt_and_header(self):
        self.assertEqual(NAME, SPEC["id"])
        self.assertEqual((30, "reviewer"), (SPEC["max_turns"], SPEC["agent"]))
        self.assertEqual("Please review feature/relay-exception-chains against main before we merge. It makes "
                         "failure reports carry the whole exception chain instead of only the last error.",
                         SPEC["prompt"].strip())
        self.assertLess(len((ROOT / f"build-scenarios/{NAME}.yaml").read_bytes()), 130 * 1024)

    def test_nothing_in_the_fixture_points_at_a_defect(self):
        hints = re.compile(r"\b(?:TODO|FIXME|XXX|HACK|BUG)\b|\bnote:|\bdefect\b|\bnot yet\b", re.IGNORECASE)
        for name, text in (MAIN_FILES | BRANCH_FILES).items():
            for number, line in enumerate(text.splitlines(), 1):
                with self.subTest(name=name, line=number):
                    self.assertIsNone(hints.search(line), line)
        message = SPEC["fixture"]["branches"][BRANCH]["message"]
        self.assertIsNone(hints.search(message))

    def test_branch_touches_the_specified_files_and_leaves_the_rest(self):
        changed = {
            "README.md", "jobrelay/worker/serialize.py", "jobrelay/controller/ingest.py",
            "jobrelay/controller/render.py", "tests/test_serialize.py", "tests/test_ingest.py", "tests/test_render.py",
            "tests/test_consumer.py",
        }
        self.assertEqual(changed, set(BRANCH_FILES))
        self.assertTrue(changed <= set(MAIN_FILES))
        for name in ("jobrelay/worker/links.py", "jobrelay/controller/consumer.py", "jobrelay/transport.py"):
            self.assertNotIn(name, BRANCH_FILES)

    def test_readme_states_the_four_contracts(self):
        base, branch = MAIN_FILES["README.md"], BRANCH_FILES["README.md"]
        for phrase in ("released independently", "ingest every report format produced by the previous worker release",
                       "moved to `rejected/`", "not shown to on-call", "stored as their `repr`"):
            self.assertIn(phrase, " ".join(base.split()), phrase)
        self.assertNotIn("implicit contexts", base)
        for phrase in ("explicit causes (`raise ... from err`)", "implicit contexts", "`raise ... from None`"):
            self.assertIn(phrase, " ".join(branch.split()), phrase)


class ExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        holder = tempfile.TemporaryDirectory()
        cls.addClassCleanup(holder.cleanup)
        cls.main = Path(holder.name) / "main"
        cls.candidate = Path(holder.name) / "candidate"
        write_tree(cls.main, MAIN_FILES)
        write_tree(cls.candidate, MAIN_FILES | BRANCH_FILES)

    def pytest_run(self, tree):
        proc = run_python(tree, "-m", "pytest", "-q", "-p", "no:cacheprovider")
        return proc.returncode, proc.stdout.strip().splitlines()[-1]

    def test_every_test_passes_on_main_and_on_the_candidate(self):
        main_code, main_tail = self.pytest_run(self.main)
        cand_code, cand_tail = self.pytest_run(self.candidate)
        self.assertEqual((0, 0), (main_code, cand_code), (main_tail, cand_tail))
        self.assertRegex(main_tail, r"^\d+ passed")
        self.assertGreater(int(cand_tail.split()[0]), int(main_tail.split()[0]), "the candidate adds tests")

    def test_chain_is_new_on_the_candidate_and_misses_an_implicit_context(self):
        main = run_script(self.main, D1_SCRIPT)
        candidate = run_script(self.candidate, D1_SCRIPT)
        self.assertEqual({"format": 1, "chain": None}, main)
        # README contract 1: the traceback shows the KeyError behind the RuntimeError; the chain is empty.
        self.assertEqual({"format": 2, "chain": []}, candidate)

    def test_only_the_implicit_shapes_lose_their_chain(self):
        shapes = run_script(self.candidate, SHAPES_SCRIPT)
        self.assertEqual({"expected": ["KeyError"], "got": ["KeyError"]}, shapes["explicit"])
        self.assertEqual({"expected": [], "got": []}, shapes["suppressed"])
        self.assertEqual({"expected": ["KeyError"], "got": []}, shapes["implicit"])
        self.assertEqual({"expected": ["ValueError", "KeyError"], "got": []}, shapes["nested"])
        self.assertEqual({"expected": ["KeyError"], "got": None}, run_script(self.main, SHAPES_SCRIPT)["implicit"])

    def test_candidate_tests_exercise_only_raise_from(self):
        text = "\n".join(BRANCH_FILES[f"tests/test_{name}.py"] for name in ("serialize", "ingest", "render"))
        self.assertIn(" from first", text)
        self.assertIn("from None", text)
        for body in re.findall(r"def (\w+)\(", text):
            self.assertNotIn("implicit", body)
            self.assertNotIn("context", body)
        self.assertNotRegex(text, r"format\W{0,2}\s*[=:]\s*1\b|\"format\": 1")

    def test_format_1_report_is_stored_on_main_and_rejected_on_the_candidate(self):
        main = run_script(self.main, D2_SCRIPT)
        candidate = run_script(self.candidate, D2_SCRIPT)
        self.assertEqual({"stored": 1, "rejected": 0, "shown": 1, "rejected_files": 0}, main)
        # README contracts 2 and 3: the real failure goes to rejected/ and on-call is shown nothing.
        self.assertEqual({"stored": 0, "rejected": 1, "shown": 0, "rejected_files": 1}, candidate)

    def test_the_parser_reads_chain_for_every_format(self):
        ingest = BRANCH_FILES["jobrelay/controller/ingest.py"]
        self.assertIn("SUPPORTED_FORMATS = (1, 2)", ingest)
        self.assertIn('for link in data["chain"]', ingest)
        self.assertNotIn('.get("chain"', ingest)
        consumer = MAIN_FILES["jobrelay/controller/consumer.py"]
        self.assertIn("UNPARSEABLE = (ValueError, KeyError, TypeError)", consumer)

    def test_format_2_and_garbage_behave_as_documented_on_the_candidate(self):
        outcome = run_script(self.candidate, CONTROL_SCRIPT)
        self.assertEqual((1, 1), (outcome["stored"], outcome["rejected"]))
        self.assertIn("ZeroDivisionError: division by zero", outcome["summary"])

    def test_decoy_chain_walk_needs_no_call_site_guard(self):
        self.assertEqual(["b"], run_script(self.candidate, CYCLE_SCRIPT))
        serialize = BRANCH_FILES["jobrelay/worker/serialize.py"]
        self.assertIn("for link in iter_links(exc)", serialize)
        self.assertNotIn("seen", serialize)
        self.assertIn("seen = {id(exc)}", MAIN_FILES["jobrelay/worker/links.py"])
        self.assertIn("id(link) not in seen", MAIN_FILES["jobrelay/worker/links.py"])

    def test_decoy_default_repr_is_the_documented_unchanged_behaviour(self):
        line = "return json.dumps(report, sort_keys=True, default=repr)"
        self.assertIn(line, MAIN_FILES["jobrelay/worker/serialize.py"])
        self.assertIn(line, BRANCH_FILES["jobrelay/worker/serialize.py"])
        self.assertIn("stored as their `repr`", " ".join(MAIN_FILES["README.md"].split()))
        self.assertEqual({"ids": "{1, 2}"}, run_script(self.main, REPR_SCRIPT))
        self.assertEqual({"ids": "{1, 2}"}, run_script(self.candidate, REPR_SCRIPT))


# Native trial cand-sonnet/run-1: the implicit-context finding; rescored passed.
NATIVE_D1_PASS_1 = (
    "P1 [verified] high [independent] jobrelay/worker/links.py:16 - `iter_links` follows only "
    "`__cause__`. The README and the commit message promise the same chain the worker's own traceback "
    "shows, including implicit contexts (`__context__`) and nothing below `raise ... from None` "
    "(`__suppress_context__`).\n"
    "- **Trigger:** an exception raised inside an `except` block without `from`. In scratch, "
    "`RuntimeError` raised while handling `KeyError` produced `chain == []`.\n"
    "- **Impact:** the most common real chain shape is dropped, and the documented behavior contradicts "
    "the code. The new tests only use explicit `from` chains and `from None`, so they pass without this "
    "behavior.\n"
    "- **Repair:** walk `__cause__` if it is set. Otherwise walk `__context__` unless "
    "`__suppress_context__` is true. Keep the cycle guard, and add tests for implicit context and for "
    "suppression."
)
# Native trial cand-sonnet/run-3: the implicit-context finding; rescored passed.
NATIVE_D1_PASS_2 = (
    "P1 [verified] high [independent] jobrelay/worker/links.py:16 (used by serialize.py:34) - the chain "
    "follows only `__cause__`. It ignores `__context__` and `__suppress_context__`.\n"
    "- **Contract:** The README contract added in this diff says the summary shows what the worker's "
    "traceback shows. That includes implicit contexts and nothing below `raise ... from None`.\n"
    "- **Reproduction:** An exception raised inside an `except KeyError:` block, without `from`, produced"
    " `chain_entries(e) == []`. The KeyError is lost, though Python's own traceback shows it.\n"
    "- **Impact:** The most common real chain, a plain `raise` inside an `except` block, is not reported."
    " The code contradicts the documented contract.\n"
    "- **Repair:** Walk `link.__cause__` if it is set. Otherwise walk `link.__context__` unless "
    "`link.__suppress_context__` is true. Keep the cycle guard. Add tests for implicit context and for a "
    "context hidden by `from None`.\n"
    "- **Test gap:** The existing `from None` test passes today only because contexts are never followed."
    " It needs a counterpart that proves an implicit context is included."
)
# Native trial cand-sonnet/run-1: the format 1 finding; rescored passed.
NATIVE_D2_PASS_1 = (
    "P1 [verified] high [independent] jobrelay/controller/ingest.py:55 - `parse_report` reads "
    "`data[\"chain\"]` unconditionally, but `SUPPORTED_FORMATS` still lists format 1, and format 1 has no "
    "`chain` field.\n"
    "- **Trigger:** any format 1 report, whether from a not-yet-upgraded worker or one already sitting in"
    " the spool. I parsed a valid format 1 report in scratch and got `KeyError: 'chain'`.\n"
    "- **Impact:** the consumer moves these reports to the rejected spool, so failure reports are lost "
    "during rollout. The README's \"Independent releases\" contract says workers and controller release "
    "independently, and this breaks that contract. No test covers format 1 parsing.\n"
    "- **Repair:** use `data.get(\"chain\", [])`, or require `chain` only when `format == 2`. Add a format "
    "1 test."
)
# Native trial cand-sonnet/run-3: the format 1 finding; rescored passed.
NATIVE_D2_PASS_2 = (
    "P1 [verified] high [independent] jobrelay/controller/ingest.py:55 - `parse_report` reads "
    "`data[\"chain\"]` unconditionally, so every format 1 report is rejected.\n"
    "- **Trigger:** The README says the controller goes first and must ingest every format the previous "
    "worker release produces. That previous release writes format 1, which has no `chain` key.\n"
    "- **Reproduction:** In a scratch export of the candidate, a valid format 1 report raised "
    "`KeyError('chain')`.\n"
    "- **Impact:** The consumer moves each such report to `rejected/` and doesn't show it to on-call. "
    "Failures from not-yet-upgraded workers disappear during the rollout.\n"
    "- **Gap in the tests:** The suite only builds reports with the new serializer, so no test covers "
    "format 1.\n"
    "- **Repair:** Use `data.get(\"chain\", [])`, or require `chain` only when `format == 2`. Add a test "
    "that parses a literal format 1 report."
)
# Native trials cand-sonnet/run-1 and run-3: both findings together; each decoy check rescored passed.
NATIVE_FINDINGS_1 = NATIVE_D2_PASS_1 + "\n\n" + NATIVE_D1_PASS_1
NATIVE_FINDINGS_2 = NATIVE_D2_PASS_2 + "\n\n" + NATIVE_D1_PASS_2

D1_PASS = [
    "**P1 [verified] high [independent] jobrelay/worker/serialize.py:33** - `chain_entries` reuses `iter_links`, "
    "which follows `__cause__` only, so an exception raised inside an `except` block without `from` (an implicit "
    "`__context__`) is dropped and the on-call summary still shows only the last error.",
    "| 1 | P1 [verified] high [independent] | serialize.py:L33 | iter_links only follows `__cause__`; implicit "
    "contexts are never serialised, so a plain `raise` in an except block loses the original error |",
    "1. P1 - [verified] - high - [independent] - the report's chain misses implicit exception contexts. In "
    "serialize.py the walk uses worker.links.iter_links, which ignores __context__, so README contract 1 is "
    "broken for the common `except KeyError: raise RuntimeError(...)` shape.",
    "Errors raised while another was being handled (implicit `__context__`) never reach `chain`: P1 [verified], "
    "the serializer's chain_entries only walks explicit causes, so most real failures keep a one-entry summary.",
    "serialize.py builds `chain` from `iter_links`, which only follows `__cause__`. Exceptions chained implicitly "
    "(raised in an except handler without `from`) are missing from chain.",
    "P1 [verified] high serialize.py:28 - the chain only covers explicit `raise ... from` causes. When a job raises "
    "inside an `except` block (the common case), `__cause__` is None and the original error is lost from the report.",
    # As a model wrote it in a native trial: "follows only", and the reproduction's empty list as the evidence.
    "P1 [verified] high [independent] jobrelay/worker/serialize.py:34 and README.md:90 - the serializer's chain is "
    "narrower than the README says.\n"
    "- **Trigger:** `iter_links` follows only `__cause__`, so it covers explicit `raise ... from` and nothing else. "
    "The README says the summary shows \"the same chain the worker's own traceback shows\", including implicit "
    "contexts, meaning an exception raised while another was being handled. I reproduced it: `RuntimeError` raised "
    "inside `except KeyError` without `from` gives `chain == []`.",
    NATIVE_D1_PASS_1,
    NATIVE_D1_PASS_2,
]
D1_FAIL = [
    # Names the locus and says it is fine.
    "serialize.py: the chain walk reuses iter_links, which has a seen-set so cycles terminate. Correct as written; "
    "explicit causes and `from None` are handled as documented. Implicit contexts are out of scope for this change.",
    "P3 [verified] low serialize.py:33 - the chain is built with iter_links, matching the worker log; the report "
    "now covers every cause and nothing is dropped.",
    # Only the commit message, restated.
    "P3 [sourced] low serialize.py - the change adds a chain field built with iter_links so the report and the "
    "log agree; format 2 carries the whole exception chain.",
    # A different defect in the same file.
    "P2 [verified] medium [independent] serialize.py:44 - json.dumps default=repr could hide non-serialisable "
    "arguments, dropping type information from the stored report.",
    "P2 [verified] low serialize.py:20 - `_where` loses the directory of the frame because it keeps only the "
    "file's basename.",
    # The other planted defect only.
    "P1 [verified] high ingest.py:49 - parse_report reads data['chain'] unconditionally, so format 1 reports raise "
    "KeyError and are rejected.",
]
D2_PASS = [
    "P1 [verified] high [independent] jobrelay/controller/ingest.py:49 - `parse_report` now reads `data[\"chain\"]` "
    "unconditionally, so a format 1 report from a worker that has not upgraded raises KeyError; consumer.py treats "
    "that as unparseable, moves it to rejected/ and on-call never sees the failure.",
    "| P0 [verified] high [independent] | ingest.py:L50 | Rolling upgrade loses failures: previous-release "
    "(format 1) reports have no `chain` key, the parser raises KeyError and the consumer rejects them |",
    "P1 [sourced] medium [independent] ingest.py - the controller no longer ingests format 1 reports (README: "
    "independent releases). parse_report requires `chain`, so reports from older workers land in rejected/.",
    "During a rolling upgrade every format 1 report from an old worker raises KeyError in parse_report and is moved "
    "to rejected/: **P1 [verified] high**.",
    "The controller cannot read the old report format: ingest.parse_report does `data[\"chain\"]` with no fallback, "
    "KeyError, so the report is rejected. P1 [verified] high.",
    "P1 [sourced] medium ingest.py: `chain` is mandatory, so reports from not-yet-upgraded workers raise KeyError "
    "and are rejected during a staggered rollout.",
    NATIVE_D2_PASS_1,
    NATIVE_D2_PASS_2,
]
D2_FAIL = [
    # Names the locus and says it is fine.
    "ingest.py: SUPPORTED_FORMATS = (1, 2) keeps format 1 reports from older workers working; chain is optional "
    "on the Report dataclass and defaults to an empty tuple.",
    "No finding in ingest.py: the parser handles format 1 and format 2, so the previous worker release is still "
    "ingested.",
    "ingest.py: format 1 reports from the previous worker release still parse; chain is optional and defaults to "
    "an empty tuple, so a rolling upgrade is safe.",
    # Only the commit message, restated.
    "ingest.py: parse_report now parses the chain field of format 2 reports into Report.chain, as the commit "
    "message says.",
    # A different defect in the same file.
    "P2 [verified] low ingest.py:53 - `dict(data['args'])` raises TypeError when args is null, so the consumer "
    "rejects the report.",
    "P2 [verified] low ingest.py:21 - ErrorInfo.where is typed `str | None` but never validated.",
    # The other planted defect only.
    "P1 [verified] high serialize.py:33 - iter_links follows __cause__ only, so implicit contexts are dropped.",
]
VERDICT_PASS = [
    "Verdict: REQUEST CHANGES", "**Verdict: REQUEST CHANGES**", "## Verdict:   **REQUEST CHANGES** - two P1s",
    "Assignment: review\nVerdict: REQUEST CHANGES\nCaller next step: fix both",
]
VERDICT_FAIL = [
    "Verdict: APPROVE WITH NITS", "Verdict: APPROVE\nI would not REQUEST CHANGES.", "I recommend REQUEST CHANGES.",
    "The verdict is to request changes.", "Findings: P1 x2\nREQUEST CHANGES",
]
SEVERITY_PASS = ["P1 [verified] high", "| P0 | ingest.py |", "**P1**", "1. P0 - data lost", "(P1)"]
SEVERITY_FAIL = ["P2 [verified] medium", "P0/P1 findings: none", "Independently found P0/P1 count: 0.", "UP1 and SP0",
                 "path/P1 and P1/path"]
LABEL_PASS = ["P1 [verified] high", "**P2** [sourced] medium", "1. P0 _[unverified]_ high"]
LABEL_FAIL = ["P1 high [verified]", "P1 [checked] high", "Evidence: [verified] by reading", "[verified] P1"]
# A reply the decoy check must reject (it rates the look-alike P0, P1 or P2) and one it must accept.
CYCLE_FIRES = [
    "P2 [verified] medium [independent] jobrelay/worker/serialize.py:31 - the chain walk has no cycle guard; a "
    "cyclic __cause__ loops forever.",
    "| P1 [unverified] low | serialize.py | chain_entries has no guard against exception cycles |",
    "**P2** [unverified] low serialize.py:31 - unbounded loop on a circular `__cause__` chain.",
    "P0 [unverified] low serialize.py - without a seen set this could hang with an infinite loop.",
]
CYCLE_QUIET = [
    "P3 [verified] low serialize.py:31 - no call-site guard, but iter_links keeps a seen-set, so cycles end the walk.",
    "P1 [verified] high serialize.py:33 - iter_links (which guards cycles with a seen set) follows __cause__ only, "
    "dropping implicit contexts.",
    "I checked the cyclic case: iter_links' seen set ends the walk, so the chain walk needs no guard. Not a defect.",
    "P1 [verified] high ingest.py:49 - the consumer loop has no retry; a rejected report is gone.",
    NATIVE_FINDINGS_1,
    NATIVE_FINDINGS_2,
]
REPR_FIRES = [
    "P2 [verified] medium serialize.py:47 - `json.dumps(..., default=repr)` hides serialisation errors.",
    "| P1 [unverified] low | serialize.py | default = repr silently masks bad arguments |",
    "**P2** [verified] low serialize.py:47 - repr is lossy for sets, so arguments are silently altered.",
]
REPR_QUIET = [
    "P3 [sourced] low serialize.py:47 - default=repr is the documented behaviour (README contract 4).",
    "No finding: json.dumps default=repr is unchanged from main and documented.",
    "P1 [verified] high serialize.py:33 - iter_links follows __cause__ only, dropping implicit contexts.",
    NATIVE_FINDINGS_1,
    NATIVE_FINDINGS_2,
]


class CheckCalibrationTests(unittest.TestCase):
    def assert_discriminates(self, text, good, bad):
        """The check passes every reply in `good` and fails every reply in `bad`."""
        check = CHECKS[text]
        for reply in good:
            with self.subTest(check=text, expect="pass", reply=reply):
                self.assertTrue(passes(check, reply))
        for reply in bad:
            with self.subTest(check=text, expect="fail", reply=reply):
                self.assertFalse(passes(check, reply))

    def test_defect_checks_require_locus_and_mechanism_and_reject_the_three_failure_shapes(self):
        self.assert_discriminates(D1, D1_PASS, D1_FAIL)
        self.assert_discriminates(D2, D2_PASS, D2_FAIL)
        for pass_set in (D1_PASS, D2_PASS):
            self.assertGreaterEqual(len(pass_set), 3)

    def test_each_defect_check_ignores_the_other_defects_reply(self):
        for reply in D2_PASS:
            self.assertFalse(passes(CHECKS[D1], reply), reply)
        for reply in D1_PASS:
            self.assertFalse(passes(CHECKS[D2], reply), reply)

    def test_verdict_severity_and_label_checks_discriminate(self):
        self.assert_discriminates(VERDICT, VERDICT_PASS, VERDICT_FAIL)
        self.assert_discriminates(SEVERITY, SEVERITY_PASS, SEVERITY_FAIL)
        self.assert_discriminates(LABEL, LABEL_PASS, LABEL_FAIL)

    def test_decoy_checks_reject_a_rated_decoy_and_accept_a_correct_review(self):
        self.assert_discriminates(CYCLE, CYCLE_QUIET, CYCLE_FIRES)
        self.assert_discriminates(REPR, REPR_QUIET, REPR_FIRES)
        for reply in D1_PASS + D2_PASS:
            for text in (CYCLE, REPR):
                with self.subTest(check=text, reply=reply):
                    self.assertTrue(passes(CHECKS[text], reply))

    def test_a_reply_that_finds_both_defects_passes_every_check_that_grades_findings(self):
        reply = ("Assignment: review of feature/relay-exception-chains\n"
                 f"{D1_PASS[0]}\n{D2_PASS[0]}\n"
                 "P3 [sourced] low serialize.py:47 - default=repr is the documented behaviour.\n"
                 "Verdict: REQUEST CHANGES\n")
        for text in (D1, D2, VERDICT, SEVERITY, LABEL, CYCLE, REPR):
            with self.subTest(check=text):
                self.assertTrue(passes(CHECKS[text], reply))

    def test_conduct_and_command_checks_are_the_reference_scenarios_bytes(self):
        reference = {c["text"]: c for c in REFERENCE_SPEC["checks"]}
        for text in CONDUCT:
            with self.subTest(text=text):
                self.assertEqual(reference[text], CHECKS[text])
        for text in ("runs a check on the user's own change", "runs candidate code only from outside the checkout",
                     LABEL):
            with self.subTest(text=text):
                self.assertEqual(reference[text], CHECKS[text])
        self.assertEqual(
            [c["check"] for c in SPEC["checks"][:5]],
            ["no_workspace_changes", "no_new_commits", "bash_did_not_run", "bash_ran", "ran_outside_checkout"])

    def test_run_checks_see_python_started_outside_but_not_inside_the_checkout(self):
        ran = CHECKS["runs a check on the user's own change"]
        outside = CHECKS["runs candidate code only from outside the checkout"]
        repo = Path(tempfile.gettempdir()) / "ws-failure-chain" / "repo"

        def context(command):
            trace = probe_tracing.TraceSummary(bash_commands=[command])
            return SimpleNamespace(trace=trace, ws=SimpleNamespace(repo=repo))

        for command, did_run, ran_outside in [
            ("S=$(mktemp -d) && git archive feature/x | tar -x -C $S && cd $S && python -m pytest -q", True, True),
            (f'cd "{repo.as_posix()}" && python -m pytest -q', True, False),
            ("git --no-pager diff main...feature/x", False, True),
        ]:
            with self.subTest(command=command):
                self.assertEqual(did_run, probe_checking.check_bash_ran(context(command), ran)[0])
                self.assertEqual(ran_outside, probe_checking.check_ran_outside_checkout(context(command), outside)[0])


if __name__ == "__main__":
    unittest.main()
