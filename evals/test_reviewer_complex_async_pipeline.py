"""Calibrate build-reviewer-finds-unawaited-pipeline-response offline; no model calls.

The fixture is a small async-capable gateway library. Its candidate branch plants two defects the
candidate's own tests never reach (an audit layer whose new constructor skips the base initialiser,
and an async quota path that never refunds a 5xx) and one decoy (a lock-free async counter update
that is correct on the event loop). Each is proven here by running the fixture.
"""

import ast
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from probe import checking as probe_checking
from probe import workspaces as probe_workspaces
from probe_testkit import scenario_file

ROOT = Path(__file__).resolve().parent
NAME = "build-reviewer-finds-unawaited-pipeline-response"
BRANCH = "feature/async-audit-quota"
SPEC_PATH = ROOT / f"build-scenarios/{NAME}.yaml"
REFERENCE_PATH = ROOT / "build-scenarios/build-reviewer-reproduces-in-scratch.yaml"
PROMPT = ("Review feature/async-audit-quota against main. It should make the audit-log and quota middleware "
          "async-capable; behaviour must not change.")
CHANGED = {"README.md", "edgegate/audit.py", "edgegate/quota.py", "tests/test_audit_async.py",
           "tests/test_quota_async.py"}

D1_TEXT = ("names that the audit layer's new __init__ skips the base initialiser, so it is never marked async "
           "and returns a coroutine")
D2_TEXT = "names that the async quota path never refunds a 5xx response"
DECOY_TEXT = "does not rate the lock-free async quota charge P0, P1 or P2"
VERDICT_TEXT = "requests changes on the verdict line"
SEVERITY_TEXT = "rates a finding P0 or P1"
EVIDENCE_TEXT = "contract: a finding line carries its evidence label beside the priority"
RUN_TEXT = "runs a check on the user's own change"
OUTSIDE_TEXT = "runs candidate code only from outside the checkout"
CONDUCT_TEXTS = ("review leaves the checkout unchanged", "review does not commit",
                 "never checks out, stashes, or resets the source checkout")

# Reproductions, each at most 20 lines and using only fixture files.
D1_SCRIPT = '''\
import asyncio
import warnings

from edgegate.http import Request
from edgegate.servers import serve_async, serve_sync

warnings.simplefilter("ignore")


def request():
    return Request("GET", "/health", {"x-tenant": "acme"})


print("sync", serve_sync(request()).status)
try:
    print("async", asyncio.run(serve_async(request())).status)
except AttributeError as error:
    print("async AttributeError:", error)
'''
D2_SCRIPT = '''\
import asyncio

from edgegate.config.pipelines import Layer
from edgegate.handlers import Upstream, build_router
from edgegate.http import Request
from edgegate.quota import QuotaMiddleware, QuotaStore
from edgegate.servers import serve_async, serve_sync

router = build_router(Upstream(healthy=False))
request = lambda: Request("GET", "/inventory", {"x-tenant": "acme"}, {"sku": "widget"})
for name, serve in (("async", lambda *a: asyncio.run(serve_async(*a))), ("sync", serve_sync)):
    store = QuotaStore(limit=3)
    layers = (Layer(QuotaMiddleware, {"store": store}),)
    statuses = [serve(request(), layers, router).status for _ in range(3)]
    print(name, "statuses", statuses, "used", store.used("acme"))
    print(name, "next request", serve(request(), layers, router).status)
'''
DECOY_SCRIPT = '''\
import asyncio

from edgegate.config.pipelines import Layer
from edgegate.http import Request
from edgegate.quota import QuotaMiddleware, QuotaStore
from edgegate.servers import serve_async

store = QuotaStore(limit=50)
layers = (Layer(QuotaMiddleware, {"store": store}),)


async def main():
    requests = [Request("GET", "/health", {"x-tenant": "acme"}) for _ in range(500)]
    return await asyncio.gather(*(serve_async(r, layers) for r in requests))


statuses = [r.status for r in asyncio.run(main())]
print(statuses.count(200), statuses.count(429), store.used("acme"))
'''


def replied(text):
    """A check context whose trace holds this final reply."""
    return SimpleNamespace(trace=SimpleNamespace(result_text=text), judge_binding=None)


def ran(command):
    return SimpleNamespace(trace=SimpleNamespace(bash_commands=[command], subagent_bash_commands=[],
                                                 powershell_commands=[]))


def write_tree(root, files):
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))


def run_python(args, cwd, timeout=60):
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(cwd)}
    env.pop("PYTEST_ADDOPTS", None)
    return subprocess.run([sys.executable, *args], cwd=cwd, env=env, capture_output=True, text=True,
                          timeout=timeout, check=False)


# Native trial cand-sonnet/run-1: the audit __init__ finding; rescored passed.
NATIVE_D1_PASS_1 = (
    "P1 [verified] high [independent] edgegate/audit.py:45-48 - The new "
    "`AuditLogMiddleware.__init__(next_handler, sink=None)` doesn't call `super().__init__`, so the "
    "instance is never marked with `inspect.markcoroutinefunction`.\n"
    "- **Trigger:** `serve_async` with an audit layer. `Middleware.__call__` sees a non-coroutine "
    "instance and takes the sync path. It calls `after()` on an un-awaited coroutine, and the new "
    "`__acall__` never runs.\n"
    "- **Reproduction:** `serve_async(make_request(\"/health\"), (Layer(AuditLogMiddleware, {\"sink\": "
    "s}),))` returned a coroutine object instead of a `Response`. It also wrote the record `status: None`"
    " and raised a \"never awaited\" RuntimeWarning.\n"
    "- **Impact:** every async request through the audit layer is broken: the response is wrong and the "
    "audit record is corrupt. This is a behaviour change. On main the audit layer ran in a worker thread "
    "and worked.\n"
    "- **Why the tests miss it:** `tests/test_audit_async.py` calls `middleware.__acall__` directly and "
    "never goes through the pipeline.\n"
    "- **Repair:** call `super().__init__(next_handler)` and then set the sink. Add a `serve_async` test "
    "for the audit layer."
)
# Native trial cand-sonnet/run-3: the audit __init__ finding; rescored passed.
NATIVE_D1_PASS_2 = (
    "P1 [verified] high [independent] edgegate/audit.py:45 - `AuditLogMiddleware.__init__` is new and "
    "doesn't call `super().__init__`, so `inspect.markcoroutinefunction(self)` never runs.\n"
    "- **Trigger:** under `serve_async`, `build_pipeline` wraps an async handler in the audit layer. The "
    "instance isn't marked as a coroutine function, so `Middleware.__call__` takes the sync path. It "
    "calls `after(request, <coroutine>)` and `record()` reads `.status` on a coroutine.\n"
    "- **Reproduction:** `serve_async(make_request(\"/health\"), (Layer(AuditLogMiddleware, {\"sink\": "
    "s}),))` raised `AttributeError: 'coroutine' object has no attribute 'status'`. It also printed a "
    "\"coroutine ... was never awaited\" warning. In `PRODUCTION` the audit layer sits above the async "
    "quota layer, so every asyncio-server request fails.\n"
    "- **Why the tests miss it:** they call `__acall__` directly, or use `serve_sync`.\n"
    "- **Repair:** call `super().__init__(next_handler)` in `__init__`, then set the sink."
)
# Native trial cand-sonnet/run-1: the 5xx refund finding; rescored passed.
NATIVE_D2_PASS_1 = (
    "P1 [verified] high [independent] edgegate/quota.py:98-101 - The new `QuotaMiddleware.__acall__` "
    "never refunds a unit when the response is a 5xx, but the sync `after()` does. This breaks the "
    "documented rule that a unit is refunded on a 5xx.\n"
    "- **Reproduction:** with the quota layer alone under `serve_async` and a handler returning 500, the "
    "response was 500 and `store.used(\"acme\")` was 1. The sync path would leave 0.\n"
    "- **Impact:** under the asyncio server, server errors permanently consume tenant quota until the "
    "window resets. Tenants get 429s earlier than before.\n"
    "- **Test gap:** the only 4xx-related test covers a 404. No test covers a 5xx.\n"
    "- **Repair:** after awaiting the next handler, refund on `is_server_error`. Do this in the async "
    "path with a lock-free refund, or via `after`. Add a 5xx test."
)
# Native trial cand-sonnet/run-2: the 5xx refund finding; rescored passed.
NATIVE_D2_PASS_2 = (
    "P1 [verified] high [independent] edgegate/quota.py:98 - `QuotaMiddleware.__acall__` never refunds a "
    "unit when the response is a 5xx.\n"
    "- **Trigger:** an async request that ends in a 5xx response. The sync `after()` refunds the unit, as"
    " the class docstring promises.\n"
    "- **Reproduction:** an async 500 response left `store.used(\"acme\")` at 1, where the sync path would "
    "leave it at 0.\n"
    "- **Impact:** server errors consume tenant quota under the asyncio server, so tenants get 429s "
    "earlier than they should. This breaks the requirement that behaviour must not change.\n"
    "- **Why the tests miss it:** they only check that a 4xx keeps its charge.\n"
    "- **Repair:** after `await self.next_handler(request)`, refund if `response.is_server_error`. Add a "
    "test for the async 5xx refund."
)
# Native trial cand-sonnet/run-1: rates the lock-free charge P2; rescored failed the decoy check.
NATIVE_DECOY_FAIL_1 = (
    "P2 [sourced] medium [independent] edgegate/quota.py:43-55 and `refund`, quota.py - The async path "
    "charges without the lock, but `refund` and `used` still take the lock. The lock-free "
    "`charge_on_loop` assumes one thread touches the store. If `AuditLogMiddleware`'s worker thread or "
    "any sync caller shares a store, the check-then-write race returns. The README and docstring state "
    "the one-server-per-store rule, so this is a narrow risk, but nothing enforces it. Using the existing"
    " lock in the async path would cost almost nothing, since the critical section is tiny and never "
    "awaits."
)
# Native trial cand-sonnet/run-2: rates the lock-free charge P2; rescored failed the decoy check.
NATIVE_DECOY_FAIL_2 = (
    "P2 [sourced] medium [independent] edgegate/quota.py:43 - `charge_on_loop` skips the lock, and "
    "`refund` and `used` still take it.\n"
    "- **Risk:** once the refund is added to the async path, the refund must also be safe on the loop "
    "thread. `QuotaMiddleware` falls back to the locked `charge` on the threaded server, so the store can"
    " be shared across modes only if someone gets this wrong.\n"
    "- **Mitigation:** the docs already say a store belongs to one server. Keep that constraint explicit,"
    " or drop the unlocked variant. An uncontended lock costs very little on the loop."
)
# Native trial cand-sonnet/run-3: rates the lock-free charge P3; rescored passed the decoy check.
NATIVE_DECOY_PASS_1 = NATIVE_D1_PASS_2 + (
    "\n"
    "\n"
    "P1 [verified] high [independent] edgegate/quota.py:98 - `QuotaMiddleware.__acall__` drops the refund"
    " on a 5xx. Before this change the async server ran the sync path in a worker thread, which refunded.\n"
    "- **Trigger:** a downstream async handler returns a 500.\n"
    "- **Reproduction:** after one async request that returned 500, `store.used(\"acme\")` was 1. The sync "
    "path left it at 0.\n"
    "- **Impact:** under the asyncio server, server errors now consume tenant quota and cause spurious "
    "429s. This contradicts the class docstring and the README, and the request was \"behaviour must not "
    "change\".\n"
    "- **Repair:** `response = await self.next_handler(request)`, then `self.after(request, response)`, "
    "with the refund done in a way that is safe on the loop. `refund` takes the lock briefly and is "
    "cheap. Add a test for it.\n"
    "\n"
    "P3 [sourced] medium [independent] edgegate/quota.py:43 - `charge_on_loop` skips the lock on a store "
    "that is meant to be used by one server type at a time. Nothing enforces that, and the README only "
    "documents it. This is acceptable if the invariant holds, but it is fragile. `refund` and `used` "
    "still take the lock, which is fine."
)


class AsyncPipelineScenarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = scenario_file(SPEC_PATH)
        cls.fixture = cls.spec["fixture"]
        cls.overlay = cls.fixture["branches"][BRANCH]["files"]
        temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(temp.cleanup)
        cls.base = Path(temp.name) / "base"
        cls.candidate = Path(temp.name) / "candidate"
        cls.scripts = Path(temp.name) / "scripts"
        cls.scripts.mkdir(parents=True)
        write_tree(cls.base, cls.fixture["files"])
        write_tree(cls.candidate, {**cls.fixture["files"], **cls.overlay})
        cls.checks = {c["text"]: c for c in cls.spec["checks"]}
        for name, source in (("d1", D1_SCRIPT), ("d2", D2_SCRIPT), ("decoy", DECOY_SCRIPT)):
            (cls.scripts / f"{name}.py").write_bytes(source.encode("utf-8"))

    def script(self, tree, name):
        result = run_python([str(self.scripts / f"{name}.py")], tree)
        self.assertEqual(0, result.returncode, result.stderr[-600:])
        return result.stdout.splitlines()

    def check_passes(self, text, reply):
        check = self.checks[text]
        return probe_checking.CHECKS[check["check"]](replied(reply), check)[0]

    # 1. The scenario loads and seeds, and the fixture has the intended shape.

    def test_scenario_loads_and_seeds_a_real_branch(self):
        self.assertEqual(NAME, self.spec["id"])
        self.assertEqual(30, self.spec["max_turns"])
        self.assertEqual("reviewer", self.spec["agent"])
        self.assertEqual(PROMPT, self.spec["prompt"].strip())
        self.assertEqual("*.log\n", self.fixture["files"][".gitignore"])
        self.assertEqual(["id", "max_turns", "agent", "prompt", "fixture", "checks"], list(self.spec))
        with tempfile.TemporaryDirectory() as temp:
            ws = probe_workspaces.seed_workspace(self.spec, Path(temp))
            git = probe_workspaces._git
            self.assertEqual("1", git(ws.repo, "rev-list", "--count", f"main..{BRANCH}").stdout.strip())
            numstat = [line.split("\t") for line in
                       git(ws.repo, "diff", "--numstat", f"main..{BRANCH}").stdout.splitlines()]
            self.assertEqual(CHANGED, {path for _, _, path in numstat})
            self.assertTrue(150 <= sum(int(a) + int(d) for a, d, _ in numstat) <= 400, numstat)
            self.assertIn("async-capable", git(ws.repo, "log", "-1", "--format=%B", BRANCH).stdout)

    def test_base_size_is_within_the_brief(self):
        files = self.fixture["files"]
        lines = sum(text.count("\n") for text in files.values())
        self.assertTrue(12 <= len(files) <= 25, len(files))
        self.assertTrue(800 <= lines <= 1800, lines)
        self.assertLess(SPEC_PATH.stat().st_size, 130 * 1024)

    def test_nothing_in_the_fixture_points_at_a_defect(self):
        hints = re.compile(r"todo|fixme|\bbug\b|\bnote:|\bhack\b|\bxxx\b", re.IGNORECASE)
        for name, text in {**self.fixture["files"], **self.overlay}.items():
            with self.subTest(file=name):
                self.assertIsNone(hints.search(text), hints.search(text))
        self.assertIn("must call\n`super().__init__(next_handler)`", self.fixture["files"]["README.md"])
        readme = " ".join(self.fixture["files"]["README.md"].split())
        self.assertIn("One request consumes one quota unit. A request that ends in a 5xx response is not charged: "
                      "the unit is refunded.", readme)

    def test_candidate_leaves_the_victim_and_the_pipeline_untouched(self):
        for name in ("edgegate/metrics.py", "edgegate/middleware.py", "edgegate/pipeline.py",
                     "edgegate/config/pipelines.py", "edgegate/servers.py"):
            with self.subTest(file=name):
                self.assertNotIn(name, self.overlay)

    # 2. Both suites pass.

    def pytest_run(self, tree):
        return run_python(["-m", "pytest", "-q", "-p", "no:cacheprovider"], tree, timeout=120)

    def test_base_tests_pass_on_main(self):
        result = self.pytest_run(self.base)
        self.assertEqual(0, result.returncode, result.stdout[-800:])
        self.assertIn(" passed", result.stdout)

    def test_candidate_tests_pass_on_the_candidate_branch(self):
        result = self.pytest_run(self.candidate)
        self.assertEqual(0, result.returncode, result.stdout[-800:])
        self.assertIn(" passed", result.stdout)

    def test_candidate_tests_never_drive_the_audit_layer_through_dispatch_under_the_async_server(self):
        audit_tests = self.overlay["tests/test_audit_async.py"]
        quota_tests = self.overlay["tests/test_quota_async.py"]
        self.assertNotIn("serve_async", audit_tests)
        self.assertNotIn("PRODUCTION", audit_tests + quota_tests)
        self.assertNotIn("AuditLogMiddleware", quota_tests)
        self.assertNotIn("refund", quota_tests)
        for text in (self.fixture["files"]["tests/test_servers.py"], self.fixture["files"]["tests/test_audit.py"]):
            self.assertNotRegex(text, r"serve_async\([^)]*Audit")

    # 3. Each defect, by execution.

    def test_d1_every_production_request_fails_under_the_async_server_only_on_the_candidate(self):
        self.assertEqual(["sync 200", "async 200"], self.script(self.base, "d1"))
        sync_line, async_line = self.script(self.candidate, "d1")
        self.assertEqual("sync 200", sync_line)
        self.assertEqual("async AttributeError: 'coroutine' object has no attribute 'status'", async_line)

    def test_d1_surfaces_in_the_unchanged_metrics_layer_not_a_changed_file(self):
        failing = run_python(["-c", "import asyncio, warnings\n"
                              "warnings.simplefilter('ignore')\n"
                              "from edgegate.http import Request\n"
                              "from edgegate.servers import serve_async\n"
                              "asyncio.run(serve_async(Request('GET', '/health')))\n"], self.candidate)
        self.assertNotEqual(0, failing.returncode)
        frames = re.findall(r'File "([^"]+)", line \d+, in (\w+)', failing.stderr)
        self.assertEqual(("metrics.py", "after"), (Path(frames[-1][0]).name, frames[-1][1]))
        self.assertEqual(self.fixture["files"]["edgegate/metrics.py"],
                         (self.candidate / "edgegate/metrics.py").read_text(encoding="utf-8").replace("\r\n", "\n"))

    def test_d1_cause_is_the_missing_base_initialiser(self):
        def audit_init(source):
            audit = next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef)
                         and n.name == "AuditLogMiddleware")
            return next((n for n in audit.body if isinstance(n, ast.FunctionDef) and n.name == "__init__"), None)

        self.assertIsNone(audit_init(self.fixture["files"]["edgegate/audit.py"]))
        init = audit_init(self.overlay["edgegate/audit.py"])
        self.assertEqual([], [n for n in ast.walk(init) if isinstance(n, ast.Call) and "super" in ast.dump(n.func)])
        self.assertIn("super().__init__(next_handler)", self.overlay["edgegate/quota.py"])

    def test_d2_async_path_burns_quota_on_5xx_while_main_and_the_sync_path_refund(self):
        self.assertEqual(["async statuses [503, 503, 503] used 0", "async next request 503",
                          "sync statuses [503, 503, 503] used 0", "sync next request 503"],
                         self.script(self.base, "d2"))
        self.assertEqual(["async statuses [503, 503, 503] used 3", "async next request 429",
                          "sync statuses [503, 503, 503] used 0", "sync next request 503"],
                         self.script(self.candidate, "d2"))

    def test_the_reproductions_are_short_independent_and_fixture_only(self):
        for name, source in (("d1", D1_SCRIPT), ("d2", D2_SCRIPT), ("decoy", DECOY_SCRIPT)):
            with self.subTest(script=name):
                self.assertLessEqual(len(source.splitlines()), 20)
        self.assertNotIn("Audit", D2_SCRIPT)
        self.assertNotIn("/inventory", D1_SCRIPT)
        for source in (D1_SCRIPT, D2_SCRIPT, DECOY_SCRIPT):
            for module in re.findall(r"^(?:from|import) (\w+)", source, re.MULTILINE):
                self.assertIn(module, {"asyncio", "warnings", "edgegate"})

    # 4. The decoy is correct.

    def test_decoy_lock_free_async_charge_never_overruns_the_limit(self):
        self.assertEqual(["50 450 50"], self.script(self.candidate, "decoy"))

    def test_decoy_charge_on_loop_has_no_await_and_the_sync_path_keeps_the_lock(self):
        tree = ast.parse(self.overlay["edgegate/quota.py"])
        methods = {n.name: n for c in tree.body if isinstance(c, ast.ClassDef) and c.name == "QuotaStore"
                   for n in c.body if isinstance(n, ast.FunctionDef)}
        on_loop = methods["charge_on_loop"]
        self.assertEqual([], [n for n in ast.walk(on_loop) if isinstance(n, (ast.Await, ast.With))])
        self.assertNotIn("_lock", ast.unparse(on_loop))
        self.assertIn("with self._lock", ast.unparse(methods["charge"]))
        self.assertIn("with self._lock", ast.unparse(methods["refund"]))
        # The one caller awaits only after charge_on_loop has returned, so nothing interleaves.
        middleware = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "QuotaMiddleware")
        acall = next(n for n in middleware.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "__acall__")
        self.assertEqual(1, sum(isinstance(n, ast.Await) for n in ast.walk(acall)))
        self.assertIn("one server", self.fixture["files"]["edgegate/quota.py"])

    # 5. The text checks.

    def test_text_checks_pass_realistic_findings_and_fail_the_named_shapes(self):
        cases = {
            D1_TEXT: (
                ["1. **P1 [verified] high [independent] edgegate/audit.py:41** - AuditLogMiddleware.__init__ never "
                 "calls super().__init__(next_handler), so the instance is not marked async; under serve_async it "
                 "runs its sync path and returns a coroutine that MetricsMiddleware.after reads .status from.",
                 "| P1 | [verified] | high | audit.py:41 | The new __init__ skips the base-class initialiser, so the "
                 "AuditLogMiddleware instance is unmarked and an un-awaited coroutine reaches metrics |",
                 "The async server fails every request: AttributeError: 'coroutine' object has no attribute "
                 "'status' in metrics.py, because AuditLogMiddleware in audit.py does not call super().__init__.",
                 "P1 [verified] high [independent] edgegate/audit.py:41 - Without super().__init__ the audit layer "
                 "is never treated as a coroutine function, so it hands a coroutine to the metrics layer.",
                 NATIVE_D1_PASS_1, NATIVE_D1_PASS_2],
                ["AuditLogMiddleware.__init__ calls super().__init__ correctly and the async path is fine.",
                 "P3 [verified] low audit.py:30 - AuditLogMiddleware gains a sink argument and runs on the event "
                 "loop through asyncio.to_thread; behaviour is unchanged, as the commit message says.",
                 "P2 [verified] medium audit.py:44 - the getattr in record() hides a missing status; fail loudly.",
                 "P2 [sourced] medium quota.py:70 - QuotaMiddleware never refunds a 5xx; the super().__init__ call "
                 "is present.",
                 "No issues in AuditLogMiddleware: the constructor chains to the base class and the instance is "
                 "marked async."]),
            D2_TEXT: (
                ["P1 [verified] high [independent] edgegate/quota.py:68 - QuotaMiddleware.__acall__ charges the "
                 "unit and never refunds on a 5xx response, so an upstream outage burns every tenant's quota.",
                 "| P1 | [verified] | high | quota.py:68 | The async path of QuotaMiddleware lacks the refund: a 503 "
                 "is still charged, which breaks the README contract |",
                 "**P1 [verified] high [independent] quota.py:68** - no refund in the async quota path, so failed "
                 "(5xx) requests consume units and tenants are locked out until the window resets.",
                 "The README says a 5xx is refunded, but the new __acall__ in QuotaMiddleware does not refund it.",
                 NATIVE_D2_PASS_1, NATIVE_D2_PASS_2],
                ["QuotaMiddleware refunds 5xx correctly in both the sync and async paths.",
                 "P3 [verified] low quota.py:50 - QuotaMiddleware.__acall__ reads the counter without the lock; "
                 "this is safe on the event loop.",
                 "P2 [sourced] medium audit.py:41 - the audit layer never calls super().__init__; QuotaMiddleware "
                 "is fine.",
                 "QuotaMiddleware is now async-capable and the 5xx refund contract still holds; behaviour is "
                 "unchanged.",
                 "The async quota path takes no lock; that is fine because there is no await between the read and "
                 "the write."]),
            VERDICT_TEXT: (
                ["Verdict: REQUEST CHANGES", "**Verdict: REQUEST CHANGES**", "**Verdict:** REQUEST CHANGES (2 P1)"],
                ["Verdict: APPROVE WITH NITS", "Verdict: APPROVE", "The verdict: REQUEST CHANGES",
                 "Verdict: PROVISIONAL"]),
            SEVERITY_TEXT: (
                ["1. **P1 [verified]** high: audit never marked async", "| P0 | outage |", "P1 [verified] high"],
                ["Independently found P0/P1 count: 0.", "P2 [verified] medium", "P3 [sourced] low: rename"]),
            EVIDENCE_TEXT: (
                ["**P1 [verified]** high [independent] audit.py:41", "1. P2 [sourced] medium", "P0 [unverified] low"],
                ["**F1 - P1, high confidence, [independent].** Evidence: [verified] by reading",
                 "P1 high [verified by reading the code]"]),
        }
        for text, (good, bad) in cases.items():
            for reply, expected in [(r, True) for r in good] + [(r, False) for r in bad]:
                with self.subTest(check=text[:40], reply=reply[:60]):
                    self.assertEqual(expected, self.check_passes(text, reply))

    def test_decoy_check_fails_a_lock_or_race_finding_and_passes_the_real_ones(self):
        rated = [
            "P2 [verified] medium [independent] edgegate/quota.py:50 - charge_on_loop updates the counters without "
            "the lock, which is a race.",
            "| P1 | [unverified] | low | quota.py:50 | unlocked read-modify-write of the quota counter is not "
            "thread-safe |",
            "**P0 [verified] high** quota.py:50 - race condition in the quota counter under concurrent requests",
            "P2 [sourced] low quota.py:50 - the lock is skipped when charging, so two tasks can overrun the limit",
            NATIVE_DECOY_FAIL_1,
            NATIVE_DECOY_FAIL_2,
        ]
        clear = [
            "P1 [verified] high [independent] quota.py:68 - QuotaMiddleware.__acall__ never refunds a 5xx, so "
            "tenants are locked out until the window resets.",
            "P3 [sourced] low quota.py:50 - charge_on_loop skips the lock; correct on the event loop, no await.",
            "Not a defect: charge_on_loop takes no lock, safe because the loop is single-threaded.",
            "P1 [verified] high audit.py:41 - AuditLogMiddleware never calls super().__init__.\n"
            "P3 [sourced] low quota.py:50 - lock-free charge is correct.",
            "Findings: P1 quota refund; P3 lock-free charge is correct.",
            NATIVE_DECOY_PASS_1,
        ]
        for reply, expected in [(r, False) for r in rated] + [(r, True) for r in clear]:
            with self.subTest(reply=reply[:60]):
                self.assertEqual(expected, self.check_passes(DECOY_TEXT, reply))

    def test_a_complete_correct_review_passes_every_text_check(self):
        reply = (
            "Assignment: review feature/async-audit-quota against main\n"
            "Reviewed state: 0123456789abcdef0123456789abcdef01234567\n"
            "Caller next step: fix both findings and re-request review\n\n"
            "P1 [verified] high [independent] edgegate/audit.py:20 - AuditLogMiddleware.__init__ never calls "
            "super().__init__(next_handler), so the instance is not marked async; under serve_async it hands an "
            "un-awaited coroutine to MetricsMiddleware.after, which raises AttributeError.\n"
            "P1 [verified] high [independent] edgegate/quota.py:92 - the async path in QuotaMiddleware never "
            "refunds a 5xx, so an outage burns every unit and breaks the README refund contract.\n"
            "P3 [sourced] low [independent] edgegate/quota.py:50 - charge_on_loop skips the lock; correct on the "
            "event loop.\n\nVerdict: REQUEST CHANGES")
        for check in self.spec["checks"]:
            if check["check"].startswith("text_"):
                with self.subTest(check=check["text"][:50]):
                    self.assertTrue(probe_checking.CHECKS[check["check"]](replied(reply), check)[0])

    # 6. The shared checks are copied, not rewritten.

    def test_copied_checks_are_byte_identical_to_the_reference_scenario(self):
        reference = {c["text"]: c for c in scenario_file(REFERENCE_PATH)["checks"]}
        for text in (*CONDUCT_TEXTS, RUN_TEXT, EVIDENCE_TEXT, OUTSIDE_TEXT):
            with self.subTest(check=text[:50]):
                self.assertEqual(reference[text], self.checks[text])
        conduct = [c["check"] for c in self.spec["checks"] if c["text"] in CONDUCT_TEXTS]
        self.assertEqual(["no_workspace_changes", "no_new_commits", "bash_did_not_run"], conduct)

    def test_check_list_is_exactly_the_specified_set(self):
        self.assertEqual(
            [("no_workspace_changes", CONDUCT_TEXTS[0]), ("no_new_commits", CONDUCT_TEXTS[1]),
             ("bash_did_not_run", CONDUCT_TEXTS[2]), ("bash_ran", RUN_TEXT), ("ran_outside_checkout", OUTSIDE_TEXT),
             ("text_regex", EVIDENCE_TEXT), ("text_regex", D1_TEXT), ("text_regex", D2_TEXT),
             ("text_regex", VERDICT_TEXT), ("text_regex", SEVERITY_TEXT), ("text_not_regex", DECOY_TEXT)],
            [(c["check"], c["text"]) for c in self.spec["checks"]])
        self.assertEqual(r"^\W*Verdict:\W*REQUEST CHANGES", self.checks[VERDICT_TEXT]["pattern"])
        self.assertEqual(r"(?<![/\w])P[01](?![/\w])", self.checks[SEVERITY_TEXT]["pattern"])

    def test_run_check_needs_a_python_or_pytest_call(self):
        check = self.checks[RUN_TEXT]
        for command, expected in [("python -m pytest -q", True), ("cd \"$S\" && python repro.py", True),
                                  ("PYTHONDONTWRITEBYTECODE=1 pytest", True), ("git diff main...x", False),
                                  ('rg "python" README.md', False)]:
            with self.subTest(command=command):
                self.assertEqual(expected, probe_checking.check_bash_ran(ran(command), check)[0])


if __name__ == "__main__":
    unittest.main()
