"""Calibrate build-reviewer-finds-go-shutdown-leak: fixture, planted defects, decoy and checks; no model calls.

The Go-executing tests need `go` on PATH and skip without it; the fixture, regex and check tests do not.
"""

import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace

from probe import checking as probe_checking
from probe import tracing as probe_tracing
from probe import workspaces as probe_workspaces
from probe_testkit import scenario_file

ROOT = Path(__file__).resolve().parent
SCENARIO = ROOT / "build-scenarios/build-reviewer-finds-go-shutdown-leak.yaml"
REFERENCE = ROOT / "build-scenarios/build-reviewer-reproduces-in-scratch.yaml"
BRANCH = "feature/parallel-fanout"
PROMPT = (
    "Review feature/parallel-fanout against main before we merge. It should process each batch in parallel with a "
    "per-job timeout; shutdown behaviour and delivery guarantees must stay as documented."
)
GO = shutil.which("go")
GO_TIMEOUT = 90
GOCACHE = Path(tempfile.gettempdir()) / "queuepoller-gocache"
CONDUCT = ("review leaves the checkout unchanged", "review does not commit",
           "never checks out, stashes, or resets the source checkout")

SPEC = scenario_file(SCENARIO)
CHECKS = {c["text"]: c for c in SPEC["checks"]}
D1 = CHECKS["finds that the per-job context ignores the run context, so Shutdown no longer cancels handlers"]
D2 = CHECKS["finds that fanOut strands goroutines on an unbuffered send after the first error"]
VERDICT = CHECKS["requests changes on the verdict line"]
SEVERITY = CHECKS["rates a finding P0 or P1"]
LABEL = CHECKS["contract: a finding line carries its evidence label beside the priority"]
DECOY = CHECKS["does not rate the fan-out loop's variable capture P0, P1 or P2"]
OUTSIDE = CHECKS["runs Go only from outside the checkout"]

# D1: the unchanged main.go calls Shutdown with a 10s grace; handlers must see the run context cancelled.
REPRO_D1 = """package poller

import (
    "context"
    "sync/atomic"
    "testing"
    "time"

    "example.com/queuepoller/internal/queue"
)

func TestReproHandlerContextFollowsRunContext(t *testing.T) {
    q := seeded(1)
    entered := make(chan context.Context, 1)
    release := make(chan struct{})
    defer close(release)
    h := &recorder{fn: func(ctx context.Context, job queue.Job) error {
        entered <- ctx
        select {
        case <-ctx.Done():
            return ctx.Err()
        case <-release:
            return nil
        }
    }}
    runCtx, cancel := context.WithCancel(context.Background())
    p := New(q, h, testConfig(1), nil)
    go p.Run(runCtx)
    jobCtx := <-entered
    cancel()
    select {
    case <-jobCtx.Done():
    case <-time.After(500 * time.Millisecond):
        t.Fatal("handler context was not cancelled when the run context was")
    }
}

func TestReproShutdownLeavesNoJobInFlight(t *testing.T) {
    q := seeded(3)
    release := make(chan struct{})
    defer close(release)
    var entered atomic.Int32
    h := &recorder{fn: func(ctx context.Context, job queue.Job) error {
        entered.Add(1)
        select {
        case <-ctx.Done():
            return ctx.Err()
        case <-release:
            return nil
        }
    }}
    p := New(q, h, testConfig(3), nil)
    go p.Run(context.Background())
    waitFor(t, "a handler running", func() bool { return entered.Load() >= 1 })
    ctx, cancel := context.WithTimeout(context.Background(), 300*time.Millisecond)
    defer cancel()
    if err := p.Shutdown(ctx); err != nil {
        t.Fatalf("Shutdown = %v, want it to return within the grace period", err)
    }
    if s := q.Stats(); s.InFlight != 0 {
        t.Fatalf("%d jobs left neither acked nor nacked: %+v", s.InFlight, s)
    }
}
"""

# D2: a failing upstream must not grow memory; goroutines must return to the baseline after the poller stops.
REPRO_D2 = """package poller

import (
    "context"
    "errors"
    "runtime"
    "testing"
    "time"

    "example.com/queuepoller/internal/queue"
)

func TestReproFailedBatchesDoNotLeakGoroutines(t *testing.T) {
    base := runtime.NumGoroutine()
    q := seeded(8)
    h := &recorder{fn: func(ctx context.Context, job queue.Job) error {
        return errors.New("upstream returned 503")
    }}
    p := New(q, h, testConfig(8), nil)
    done := make(chan error, 1)
    go func() { done <- p.Run(context.Background()) }()
    waitFor(t, "five failed batches", func() bool { return p.metrics.Snapshot().BatchErrors >= 5 })
    ctx, cancel := context.WithTimeout(context.Background(), 2*time.Second)
    defer cancel()
    if err := p.Shutdown(ctx); err != nil {
        t.Fatalf("Shutdown = %v", err)
    }
    <-done
    after := runtime.NumGoroutine()
    for i := 0; i < 40 && after > base; i++ {
        time.Sleep(25 * time.Millisecond)
        after = runtime.NumGoroutine()
    }
    if after > base {
        t.Fatalf("goroutines: %d before, %d after failed batches", base, after)
    }
}
"""

# Decoy control: the same loop shape, in its own package so a lower `go` directive still compiles.
REPRO_LOOPVAR = """package looprepro

import (
    "sync"
    "testing"
)

func TestEachGoroutineSeesItsOwnJob(t *testing.T) {
    var wg sync.WaitGroup
    gate := make(chan struct{})
    seen := make(chan string, 3)
    for _, job := range []string{"a", "b", "c"} {
        wg.Add(1)
        go func() {
            defer wg.Done()
            <-gate
            seen <- job
        }()
    }
    close(gate)
    wg.Wait()
    close(seen)
    distinct := map[string]bool{}
    for id := range seen {
        distinct[id] = true
    }
    if len(distinct) != 3 {
        t.Fatalf("goroutines saw %d distinct jobs, want 3", len(distinct))
    }
}
"""

_state = {}


def setUpModule():
    GOCACHE.mkdir(exist_ok=True)
    _state["temp"] = tempfile.TemporaryDirectory(prefix="go-shutdown-calibration-")
    seeded = probe_workspaces.seed_workspace(SPEC, Path(_state["temp"].name) / "ws")
    for ref in ("main", BRANCH):
        out = Path(_state["temp"].name) / ref.replace("/", "_")
        out.mkdir()
        archive = subprocess.run(["git", "archive", "--format=tar", ref], cwd=seeded.repo, check=True,
                                 capture_output=True, timeout=30).stdout
        with tarfile.open(fileobj=BytesIO(archive)) as tar:
            tar.extractall(out, filter="data")
        _state[ref] = out


def tearDownModule():
    _state["temp"].cleanup()


def replied(text):
    """A check context whose trace holds this final reply."""
    return SimpleNamespace(trace=SimpleNamespace(result_text=text), judge_binding=None)


def passes(check, text):
    return probe_checking.CHECKS[check["check"]](replied(text), check)[0]


def go(tree, *args):
    env = {**os.environ, "GOFLAGS": "-mod=mod", "GOPROXY": "off", "GOTOOLCHAIN": "local", "GOWORK": "off",
           "GOCACHE": str(GOCACHE)}
    return subprocess.run([GO, *args], cwd=tree, env=env, capture_output=True, text=True, timeout=GO_TIMEOUT)


def copy_of(ref):
    """A scratch copy of an exported tree, so a probe test never lands in the shared one."""
    target = Path(tempfile.mkdtemp(prefix="copy-", dir=_state["temp"].name)) / "tree"
    shutil.copytree(_state[ref], target)
    return target


def with_repro(ref, source, name="repro_test.go"):
    tree = copy_of(ref)
    (tree / "internal/poller" / name).write_bytes(source.encode("utf-8"))
    return tree


class FixtureTests(unittest.TestCase):
    def test_scenario_shape(self):
        text = SCENARIO.read_text(encoding="utf-8")
        keys = re.findall(r"^([a-z_]+):", text, re.M)
        self.assertEqual(["id", "max_turns", "agent", "prompt", "fixture", "checks"], keys)
        self.assertTrue(text.startswith("# "))
        self.assertLess(len(text.encode("utf-8")), 130 * 1024)
        self.assertEqual(
            ("build-reviewer-finds-go-shutdown-leak", 30, "reviewer"), (SPEC["id"], SPEC["max_turns"], SPEC["agent"]))
        self.assertEqual(PROMPT, SPEC["prompt"].strip())

    def test_fixture_size_and_branch_size(self):
        files = SPEC["fixture"]["files"]
        lines = sum(len(body.splitlines()) for body in files.values())
        self.assertEqual("*.log\n", files[".gitignore"])
        self.assertTrue(10 <= len(files) <= 18 and 700 <= lines <= 1500, (len(files), lines))
        self.assertEqual({BRANCH}, set(SPEC["fixture"]["branches"]))
        self.assertTrue(3 <= len(SPEC["fixture"]["branches"][BRANCH]["files"]) <= 6)
        self.assertIn("go 1.24\n", files["go.mod"])
        self.assertNotIn("require", files["go.mod"])

    def test_seeds_one_commit_on_the_branch_and_the_candidate_is_not_checked_out(self):
        with tempfile.TemporaryDirectory() as temp:
            ws = probe_workspaces.seed_workspace(SPEC, Path(temp))
            self.assertEqual("main", ws.baseline_branch)
            self.assertEqual(2, ws.baseline_commits)
            count = subprocess.run(["git", "rev-list", "--count", f"main..{BRANCH}"], cwd=ws.repo, check=True,
                                   capture_output=True, text=True, timeout=30).stdout.strip()
            self.assertEqual("1", count)

    def test_readme_states_the_contracts_and_nothing_points_at_a_defect(self):
        files = SPEC["fixture"]["files"]
        readme = " ".join(files["README.md"].split())
        self.assertIn("Shutdown returns within the grace period. In-flight jobs are cancelled through their context "
                      "and nacked for redelivery; no job is left neither acked nor nacked.", readme)
        self.assertIn("The poller's memory use is bounded by the batch size; a failing upstream must not grow it.",
                      readme)
        branch = SPEC["fixture"]["branches"][BRANCH]
        everything = "\n".join([*files.values(), *branch["files"].values(), branch["message"]])
        self.assertIsNone(re.search(r"TODO|FIXME|\bBUG\b|\bnote:|\bXXX\b|\bHACK\b", everything, re.I))
        self.assertIn("README.md", branch["files"])
        self.assertIn("The poller's memory use is bounded by the batch size", branch["files"]["README.md"])

    def test_main_go_is_untouched_and_uses_a_ten_second_grace(self):
        files = SPEC["fixture"]["files"]
        self.assertNotIn("cmd/poller/main.go", SPEC["fixture"]["branches"][BRANCH]["files"])
        self.assertIn("const shutdownGrace = 10 * time.Second", files["cmd/poller/main.go"])
        self.assertIn("p.Shutdown(ctx)", files["cmd/poller/main.go"])
        self.assertIn("JobTimeout:   30 * time.Second", SPEC["fixture"]["branches"][BRANCH]["files"][
            "internal/config/config.go"])

    def test_defect_sites_are_in_the_candidate_only(self):
        files = SPEC["fixture"]["files"]
        branch = SPEC["fixture"]["branches"][BRANCH]["files"]
        fanout = branch["internal/poller/fanout.go"]
        self.assertIn("context.WithTimeout(context.Background(), timeout)", fanout)  # D1
        self.assertIn("results := make(chan error)\n", fanout)  # D2: unbuffered
        self.assertRegex(fanout, r"if err := <-results; err != nil \{\n\t\t\treturn err")  # D2: first error returns
        self.assertNotIn("fanout.go", "\n".join(files))
        self.assertNotIn("context.Background()", files["internal/poller/poller.go"])
        self.assertIn("p.processBatch(runCtx, jobs)", files["internal/poller/poller.go"])
        self.assertIn("p.processBatch(jobs)", branch["internal/poller/poller.go"])

    def test_candidate_tests_do_not_exercise_either_defect(self):
        tests = SPEC["fixture"]["branches"][BRANCH]["files"]["internal/poller/fanout_test.go"]
        self.assertNotIn("Shutdown", tests)
        self.assertNotIn("NumGoroutine", tests)
        self.assertNotIn("runtime", tests)
        self.assertNotRegex(SPEC["fixture"]["files"]["internal/poller/poller_test.go"], r"NumGoroutine|runtime\.")

    def test_decoy_is_structurally_correct(self):
        fanout = SPEC["fixture"]["branches"][BRANCH]["files"]["internal/poller/fanout.go"]
        self.assertIn("for _, job := range jobs {\n\t\tgo func() {", fanout)
        self.assertNotIn("job := job", fanout)
        self.assertIn("results <- fn(ctx, job)", fanout)
        match = re.search(r"^go (\d+)\.(\d+)$", SPEC["fixture"]["files"]["go.mod"], re.M)
        self.assertGreaterEqual((int(match[1]), int(match[2])), (1, 22))  # per-iteration loop variables

    def test_conduct_checks_are_byte_identical_to_the_reference_scenario(self):
        reference = {c["text"]: c for c in scenario_file(REFERENCE)["checks"]}
        for text in CONDUCT:
            with self.subTest(text=text):
                self.assertEqual(reference[text], CHECKS[text])
        self.assertEqual(reference[LABEL["text"]], LABEL)
        self.assertEqual(
            ["no_workspace_changes", "no_new_commits", "bash_did_not_run", "ran_outside_checkout"],
            [c["check"] for c in SPEC["checks"][:4]])
        self.assertEqual(
            ["text_regex", "text_regex", "text_regex", "text_regex", "text_regex", "text_not_regex"],
            [c["check"] for c in SPEC["checks"][4:]])
        self.assertEqual(
            r"(?:^|[;&|(\n])\s*(?:[A-Za-z_]\w*=\S+\s+)*go\s+(?:test|run|vet|build)\b", OUTSIDE["pattern"])


class GoExecutionTests(unittest.TestCase):
    """The base and candidate suites pass, each defect shows by execution, and the decoy is correct."""

    @classmethod
    def setUpClass(cls):
        if GO is None:
            raise unittest.SkipTest("go is not on PATH")

    def run_ok(self, tree, *args):
        proc = go(tree, *args)
        self.assertEqual(0, proc.returncode, f"go {' '.join(args)} in {tree.parent.name}\n{proc.stdout}{proc.stderr}")
        return proc

    def test_vet_and_tests_pass_on_main_and_on_the_candidate(self):
        for ref in ("main", BRANCH):
            with self.subTest(ref=ref):
                tree = copy_of(ref)
                self.run_ok(tree, "vet", "./...")
                out = self.run_ok(tree, "test", "-count=1", "./...").stdout
                self.assertIn("internal/poller", out)
                self.assertNotIn("FAIL", out)

    def test_d1_handler_context_is_cancelled_on_main_and_not_on_the_candidate(self):
        for name in ("TestReproHandlerContextFollowsRunContext", "TestReproShutdownLeavesNoJobInFlight"):
            with self.subTest(name=name, ref="main"):
                self.run_ok(with_repro("main", REPRO_D1), "test", "-count=1", "-run", name, "./internal/poller")
            with self.subTest(name=name, ref=BRANCH):
                proc = go(with_repro(BRANCH, REPRO_D1), "test", "-count=1", "-run", name, "./internal/poller")
                self.assertEqual(1, proc.returncode, proc.stdout + proc.stderr)
                self.assertRegex(proc.stdout, r"was not cancelled when the run context was|neither acked nor nacked|"
                                              r"context deadline exceeded")

    def test_d2_goroutines_return_to_baseline_on_main_and_stay_elevated_on_the_candidate(self):
        name = "TestReproFailedBatchesDoNotLeakGoroutines"
        self.run_ok(with_repro("main", REPRO_D2), "test", "-count=1", "-run", name, "./internal/poller")
        proc = go(with_repro(BRANCH, REPRO_D2), "test", "-count=1", "-run", name, "./internal/poller")
        self.assertEqual(1, proc.returncode, proc.stdout + proc.stderr)
        match = re.search(r"goroutines: (\d+) before, (\d+) after", proc.stdout)
        self.assertIsNotNone(match, proc.stdout)
        self.assertGreater(int(match[2]) - int(match[1]), 20)  # five failed batches strand at least 7 each

    def test_decoy_loop_variable_capture_is_correct_because_go_mod_says_1_24(self):
        out = self.run_ok(copy_of(BRANCH), "test", "-count=1", "-v", "-run", "TestFanOutRunsEveryJobOnce",
                          "./internal/poller").stdout
        self.assertIn("--- PASS: TestFanOutRunsEveryJobOnce", out)
        for version, expected in (("1.24", 0), ("1.21", 1)):
            with self.subTest(go_directive=version):
                tree = copy_of(BRANCH)
                (tree / "internal/looprepro").mkdir()
                (tree / "internal/looprepro/loop_test.go").write_bytes(REPRO_LOOPVAR.encode("utf-8"))
                (tree / "go.mod").write_bytes(f"module example.com/queuepoller\n\ngo {version}\n".encode())
                proc = go(tree, "test", "-count=1", "./internal/looprepro")
                self.assertEqual(expected, proc.returncode, proc.stdout + proc.stderr)


# Native trial cand-sonnet/run-1: the shutdown finding; rescored passed.
NATIVE_D1_PASS_1 = (
    "P1 [verified] high [independent] internal/poller/fanout.go:29 (with poller.go:85) - Shutdown no "
    "longer cancels in-flight handlers.\n"
    "- **Cause:** `jobContext` builds each job's context from `context.Background()`. `processBatch` also"
    " dropped the `runCtx` parameter. Cancelling the poller therefore never reaches a handler.\n"
    "- **Contract broken:** the README says \"In-flight jobs are cancelled through their context and "
    "nacked\N{HORIZONTAL ELLIPSIS} Shutdown returns within the grace period\". The `Handler` doc says the "
    "context is cancelled on shutdown.\n"
    "- **Reproduction:** I ran a handler that waits on `ctx.Done()` or 3s, then called `Shutdown` with a "
    "500ms grace period. It returned `context deadline exceeded`.\n"
    "- **Impact:** a handler that blocks until its own timeout (default 30s) outlasts the 10s SIGTERM "
    "grace period. The process is killed with jobs neither acked nor nacked.\n"
    "- **Repair:** pass `runCtx` into `processBatch` and `fanOut`, and derive the job context with "
    "`context.WithTimeout(runCtx, timeout)`. Settling already uses `WithoutCancel`, so nacks still "
    "happen.\n"
    "- **Test gap:** no new test covers shutdown during a batch."
)
# Native trial cand-sonnet/run-2: the shutdown finding; rescored passed.
NATIVE_D1_PASS_2 = (
    "P1 [verified] high [independent] internal/poller/fanout.go:27 - `jobContext` builds each job's "
    "context from `context.Background()`. The old code passed the run context into `processJob`, so "
    "shutdown cancelled handlers. Now `Shutdown` and parent-context cancellation never reach a handler. "
    "The README (\"In-flight jobs are cancelled through their context and nacked\N{HORIZONTAL ELLIPSIS} "
    "Shutdown returns within the grace period\") and the `Handler` doc comment both promise that "
    "cancellation.\n"
    "- **Trigger:** call `Shutdown` while a handler is running.\n"
    "- **Repro:** a handler that blocks on `ctx.Done()` or 2s, with a 300ms grace period, makes "
    "`Shutdown` return `context deadline exceeded`.\n"
    "- **Impact:** shutdown waits for the full job timeout (30s by default). Orchestrators will likely "
    "SIGKILL the process mid-job, which leaves jobs neither acked nor nacked.\n"
    "- **Repair:** pass `runCtx` into `processBatch` and `fanOut`, and derive each job context with "
    "`context.WithTimeout(parent, timeout)`. Add a shutdown test."
)
# Native trial cand-sonnet/run-1: the fanOut leak finding; rescored passed.
NATIVE_D2_PASS_1 = (
    "P1 [verified] high [independent] internal/poller/fanout.go:12-25 - `fanOut` returns on the first "
    "error while the other jobs are still running.\n"
    "- **Cause:** `results` is unbuffered and `fanOut` returns at the first error. The remaining "
    "goroutines block forever on `results <-`.\n"
    "- **Reproduction:** with 4 jobs where one fails immediately, goroutines went from 5 to 8 and stayed "
    "there after the other jobs finished.\n"
    "- **Leak:** each failed batch leaks a goroutine for every other job in it.\n"
    "- **Batch overlap:** `Run` backs off and fetches the next batch while the previous batch's jobs are "
    "still running. This breaks the README line \"next batch is not fetched until the current one has been"
    " handled\". It also breaks the rule that memory is bounded by batch size and a failing upstream must "
    "not grow it.\n"
    "- **Shutdown:** `Run` can return, closing `done`, while handlers are still running.\n"
    "- **Repair:** wait for every goroutine (`sync.WaitGroup`, or a buffered channel of `len(jobs)`), "
    "then return the first error. The old sequential code also processed every job before returning the "
    "first error."
)
# Native trial cand-sonnet/run-2: the fanOut leak finding; rescored passed.
NATIVE_D2_PASS_2 = (
    "P1 [verified] high [independent] internal/poller/fanout.go:12-25 - `fanOut` uses an unbuffered "
    "`results` channel and returns on the first error. The remaining goroutines then block forever on "
    "`results <-`.\n"
    "- **Trigger:** any batch where a job fails and other jobs are still running or finished later. This "
    "is normal under a failing upstream.\n"
    "- **Repro:** 50 batches of 4 jobs with one failure left 155 goroutines against a baseline of 5 "
    "(about 3 leaked per failed batch).\n"
    "- **Impact:**\n"
    "  - Goroutines, jobs and contexts leak without bound on each failed batch. This breaks the "
    "documented rule that memory is bounded by batch size and that a failing upstream must not grow it.\n"
    "  - `Run` returns while jobs are still in flight. So `Shutdown` and `Run` can report completion "
    "before every job is settled, which contradicts \"no job is left neither acked nor nacked\".\n"
    "  - Errors after the first are dropped. The old code ran every job and only recorded the first "
    "error.\n"
    "- **Repair:** use a buffered channel of `len(jobs)`, or a `sync.WaitGroup` that waits for all "
    "goroutines. Keep the first error and always wait for every job before returning."
)
# Native trial cand-sonnet/run-1: both findings, never the loop variable; rescored passed.
NATIVE_DECOY_PASS_1 = NATIVE_D1_PASS_1 + "\n\n" + NATIVE_D2_PASS_1
# Native trial cand-sonnet/run-2: both findings, never the loop variable; rescored passed.
NATIVE_DECOY_PASS_2 = NATIVE_D1_PASS_2 + "\n\n" + NATIVE_D2_PASS_2


class TextCheckTests(unittest.TestCase):
    def assert_cases(self, check, accepted, rejected):
        for text in accepted:
            with self.subTest(expect="pass", text=text[:70]):
                self.assertTrue(passes(check, text))
        for text in rejected:
            with self.subTest(expect="fail", text=text[:70]):
                self.assertFalse(passes(check, text))

    def test_d1_context_ignores_the_run_context(self):
        self.assert_cases(D1, [
            "P1 [verified] high [independent] internal/poller/fanout.go:30 - jobContext derives each job's context "
            "from context.Background(), so Poller.Shutdown's cancellation never reaches in-flight handlers. With the "
            "30s default timeout and the 10s grace period, main exits with jobs neither acked nor nacked.",
            "**P1** `[verified]` **high** - `fanout.go:30` `context.Background()` detaches handlers from the run "
            "context; handlers are not cancelled when Shutdown is called.",
            "| P1 | [verified] | high | fanout.go:30 | jobContext ignores the poller's run context: Shutdown cannot "
            "cancel in-flight jobs |",
            "1. P1 - processBatch no longer passes the run context to processJob; the per-job ctx built in "
            "fanOut/jobContext comes from context.Background, so a SIGTERM shutdown never cancels handlers.",
            "Shutdown cannot cancel in-flight handlers because the per-job context is created from "
            "context.Background() in fanout.go.",
            NATIVE_D1_PASS_1,
            NATIVE_D1_PASS_2,
        ], [
            "fanout.go jobContext uses context.Background() with a timeout, which is fine: Shutdown still cancels the "
            "run context and handlers return promptly.",
            "Summary: the branch processes each batch in parallel via fanOut with a per-job timeout (30s default, "
            "configurable) and updates the README. Shutdown behaviour and delivery guarantees are said to be "
            "unchanged.",
            "P1 [verified] high fanout.go:19 - fanOut returns on the first error and the remaining goroutines block "
            "forever sending on the unbuffered results channel, leaking goroutines on every failed batch. Shutdown "
            "is unaffected.",
            "P2 [verified] low config.go:60 - validation of the job timeout does not cap its upper bound.",
            "Verdict: APPROVE",
        ])

    def test_d2_fan_out_strands_goroutines(self):
        self.assert_cases(D2, [
            "P1 [verified] high [independent] fanout.go:19 - fanOut sends results on an unbuffered channel and "
            "returns on the first error; the remaining goroutines block forever on their send, so every failed "
            "batch leaks goroutines.",
            "**P1** `[verified]` high `internal/poller/fanout.go:20`: goroutine leak. After the first error fanOut "
            "returns and nobody receives from the results channel, so the other goroutines are stuck on "
            "`results <- fn(...)` forever.",
            "| P1 | [verified] | high | fanout.go:19 | Unbuffered results channel: when fanOut returns early on "
            "error the sender goroutines leak (blocked on send); memory grows with each failed batch |",
            "Goroutines are leaked on every failed batch because fanOut returns after the first error and the "
            "remaining senders can never complete their send.",
            NATIVE_D2_PASS_1,
            NATIVE_D2_PASS_2,
        ], [
            "fanOut: the results channel is unbuffered but every send is received, so there is no goroutine leak.",
            "Runs fanOut with one goroutine per job and returns the first error it sees; each job gets its own "
            "timeout.",
            "P1 [verified] high fanout.go:30 - jobContext derives from context.Background(), so goroutines running "
            "handlers are never cancelled by Shutdown and jobs end neither acked nor nacked.",
            "P2 [verified] low fanout.go:12 - the doc comment says fanOut returns the first error but does not say "
            "which job produced it.",
            "Verdict: REQUEST CHANGES",
        ])

    def test_verdict_line(self):
        self.assert_cases(VERDICT, [
            "Verdict: REQUEST CHANGES", "**Verdict:** REQUEST CHANGES", "Summary\n\n- Verdict: REQUEST CHANGES (2 P1)",
        ], [
            "Verdict: APPROVE WITH NITS", "Verdict: APPROVE", "I would REQUEST CHANGES here but defer to the owner.",
        ])

    def test_severity_check(self):
        self.assert_cases(SEVERITY, [
            "P1 [verified] high fanout.go:19 - leak", "**P0** [sourced] medium - outage", "| P1 | [verified] |",
        ], [
            "P2 [verified] low - a nit", "P3 [unverified] low - optional", "P0/P1/P2 definitions apply", "UP1",
        ])

    def test_evidence_label(self):
        self.assert_cases(LABEL, [
            "P1 [verified] high [independent] fanout.go:19 - leak", "**P1** [sourced] high - x",
            "1. **P2 [unverified]** low - a nit",
        ], [
            "P1 high fanout.go:19 - leak", "P1 (verified) high - leak", "[verified] P1 fanout.go",
        ])

    def test_decoy_loop_variable_is_not_rated_p0_to_p2(self):
        self.assert_cases(DECOY, [
            "P3 [verified] low fanout.go:18 - the closure captures the loop variable job directly; this is safe "
            "because go.mod declares go 1.24.",
            "Loop variable capture in the fanOut closure is not a defect: go.mod declares go 1.24, so each iteration "
            "has its own job.",
            "P1 [verified] high fanout.go:19 - the goroutines started with go func() block forever on their send.",
            "| P1 | [verified] | high | fanout.go:30 | jobContext derives from context.Background() |\n"
            "Verdict: REQUEST CHANGES",
            "The `go func()` closures use job directly, which is correct under Go 1.22+ loopvar semantics.",
            NATIVE_DECOY_PASS_1,
            NATIVE_DECOY_PASS_2,
        ], [
            "P2 [unverified] low fanout.go:18 - the goroutine closure captures the loop variable job directly; "
            "before Go 1.22 this would race.",
            "**P1** loop variable capture in `go func()` - all goroutines may see the last job",
            "| P0 | [sourced] | medium | fanout.go:17 | closure captures job from the range loop |",
            "P2 [verified] medium fanout.go:18 - each goroutine captures the shared loop iteration variable.",
        ])


class RanOutsideCheckoutTests(unittest.TestCase):
    def test_go_in_the_checkout_fails_and_outside_or_never_passes(self):
        repo = Path(tempfile.gettempdir()) / "ws-go-shutdown" / "repo"
        cases = [  # (shell commands, passes) - the shapes real traces take
            (["go test ./..."], False),
            (["GOFLAGS=-mod=mod go vet ./..."], False),
            ([f'cd "{repo.as_posix()}" && go test ./...'], False),
            (['cd "$S" && cd "' + repo.as_posix() + '" && go build ./...'], False),
            (['cd "$S" && go test ./...'], True),
            (["S=$(mktemp -d) && git archive main | tar -x -C $S && cd $S && GOFLAGS=-mod=mod go test ./..."], True),
            (['cd "$S"', "go vet ./..."], True),
            (['git diff main...feature/parallel-fanout --stat', "git log --oneline main..feature/parallel-fanout"], True),
            ([], True),
        ]
        for commands, expected in cases:
            with self.subTest(commands=commands):
                ctx = SimpleNamespace(trace=probe_tracing.TraceSummary(bash_commands=commands),
                                      ws=SimpleNamespace(repo=repo))
                self.assertEqual(expected, probe_checking.check_ran_outside_checkout(ctx, OUTSIDE)[0])


if __name__ == "__main__":
    unittest.main()
