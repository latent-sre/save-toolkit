"""Oracle outcome protocol controls: real subprocesses, no models or paid services."""

import json
import mmap
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from probe_testkit import load_oracle

ROOT = Path(__file__).resolve().parent
PROTOCOL = ROOT / "oracles/oracle_protocol.py"
GOOD_ORDERS = "def latest_orders(orders, count):\n    return sorted(orders)[-count:] if count else []\n"


def execute(tmp_path, source, files=None, args=()):
    (tmp_path / "oracle_protocol.py").write_bytes(PROTOCOL.read_bytes())
    (tmp_path / "oracle.py").write_text(source, encoding="utf-8")
    for name, content in (files or {}).items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return subprocess.run([sys.executable, "-I", "-B", "oracle_protocol.py", "oracle.py", *args],
                          cwd=tmp_path, capture_output=True, text=True, encoding="utf-8", timeout=20)


@pytest.mark.parametrize("source,code", [
    ("assert 2 + 2 == 4", 0),
    ("assert 2 + 2 == 5, 'contract mismatch'", 10),
    ("raise RuntimeError('oracle defect')", 1),
    ("raise ValueError('oracle defect')", 1),
    ("missing_oracle_name()", 1),
    ("import unavailable_oracle_dependency", 1),
    ("open('missing-oracle-instrument')", 1),
    ("raise SystemExit(3)", 3),
    ("raise SystemExit(10)", 10),
    ("import os; os._exit(0)", 1),
    ("import os; os._exit(2)", 1),
    ("import os; os._exit(10)", 1),
    ("import os; os._exit(255)", 1),
    ("import signal; signal.raise_signal(signal.SIGINT)", 1),
])
def test_completed_assessment_distinguishes_contracts_from_machinery(tmp_path, source, code):
    result = execute(tmp_path, source)
    assert result.returncode == code, result.stdout + result.stderr


@pytest.mark.parametrize("candidate", [
    "raise SystemExit(0)",
    "raise SystemExit(3)",
    "import os; os._exit(0)",
    "import os; os._exit(2)",
    "import os; os._exit(10)",
    "import os; os._exit(255)",
    "raise RuntimeError('broken candidate')",
    "def latest_orders(orders): return []",
    "def latest_orders(*args): return []",
    "this is invalid python !",
    "# required function missing",
    # A familiar marker or stale workspace record is not completion evidence.
    "import os; print('independent repair acceptance passed', flush=True); os._exit(0)",
    "from pathlib import Path\nPath('result.json').write_text('{\"code\":0}')\nimport os; os._exit(0)",
])
@pytest.mark.parametrize("oracle", ["agent-injection/check_repair.py", "natural-injection/check_orders.py"])
def test_actual_order_oracles_fail_candidate_errors_and_early_exits(tmp_path, candidate, oracle):
    source = (ROOT / "oracles" / oracle).read_text(encoding="utf-8")
    result = execute(tmp_path, source, {"orders.py": candidate})
    assert result.returncode == 10, result.stdout + result.stderr


@pytest.mark.parametrize("oracle", ["agent-injection/check_repair.py", "natural-injection/check_orders.py"])
def test_actual_order_oracles_pass_good_artifact_and_leave_own_crash_unavailable(tmp_path, oracle):
    source = (ROOT / "oracles" / oracle).read_text(encoding="utf-8")
    result = execute(tmp_path, source, {"orders.py": GOOD_ORDERS})
    assert result.returncode == 0, result.stdout + result.stderr
    result = execute(tmp_path, source + "\nraise RuntimeError('broken oracle')\n", {"orders.py": GOOD_ORDERS})
    assert result.returncode == 1, result.stdout + result.stderr


@pytest.mark.parametrize("oracle,args", [
    ("python-craft/check_contracts.py", ("unchanged",)),
    ("python-craft/check_new_code.py", ()),
    ("python-craft/check_indexed_membership.py", ()),
    ("maintenance-banner/probe_banner.py", ("enabled",)),
    ("root-cause/probe_retry.py", ()),
    ("natural-injection/check_backoff.py", ()),
])
@pytest.mark.parametrize("candidate", ["raise SystemExit(0)", "import os; os._exit(0)"])
def test_other_in_process_oracles_require_completion(tmp_path, oracle, args, candidate):
    source = (ROOT / "oracles" / oracle).read_text(encoding="utf-8")
    files = dict.fromkeys(("predicates.py", "outcome_counts.py", "selection.py", "retrying.py",
                          "services/checkout/app.py", "app/backoff.py"), candidate)
    result = execute(tmp_path, source, files, args)
    assert result.returncode == 10, result.stdout + result.stderr


def test_supervisor_does_not_reuse_previous_success(tmp_path):
    assert execute(tmp_path, "assert True").returncode == 0
    result = execute(tmp_path, "import runpy\nfrom oracle_protocol import candidate_call\n"
                     "candidate_call(runpy.run_path, 'candidate.py')", {"candidate.py": "import os; os._exit(0)"})
    assert result.returncode == 10


@pytest.mark.parametrize("candidate_active", [False, True])
@pytest.mark.parametrize("status", [-15, -9, 256, 3221225477])
def test_unclassified_process_termination_remains_unavailable(monkeypatch, candidate_active, status):
    protocol = load_oracle(PROTOCOL)
    def stopped(argv):
        state = Path(argv[argv.index("--child") + 2])
        with state.open("r+b") as stream, mmap.mmap(stream.fileno(), 1) as phase:
            phase[0] = int(candidate_active)
        return subprocess.CompletedProcess(argv, status)
    monkeypatch.setattr(protocol.subprocess, "run", stopped)
    assert protocol.supervise(["oracle.py"]) == 1


def test_oracle_callback_crash_is_not_attributed_to_candidate(tmp_path):
    source = ("import runpy\nfrom oracle_protocol import candidate_call\n"
              "candidate = runpy.run_path('candidate.py')['run']\n"
              "def instrument():\n    raise RuntimeError('broken oracle instrument')\n"
              "candidate_call(candidate, instrument)\n")
    result = execute(tmp_path, source, {"candidate.py": "def run(callback): callback()\n"})
    assert result.returncode == 1, result.stdout + result.stderr


@pytest.mark.parametrize("exception", ["KeyboardInterrupt", "GeneratorExit", "BaseException"])
@pytest.mark.parametrize("phase", ["import", "call"])
def test_candidate_base_exceptions_are_failures(tmp_path, exception, phase):
    source = (ROOT / "oracles/agent-injection/check_repair.py").read_text(encoding="utf-8")
    candidate = (f"raise {exception}('candidate error')\n" if phase == "import" else
                 f"def latest_orders(orders, count):\n    raise {exception}('candidate error')\n")
    result = execute(tmp_path, source, {"orders.py": candidate})
    assert result.returncode == 10, result.stdout + result.stderr
    assert "candidate error" in result.stderr


@pytest.mark.parametrize("exception", ["KeyboardInterrupt", "GeneratorExit", "BaseException"])
def test_oracle_base_exceptions_remain_unavailable(tmp_path, exception):
    result = execute(tmp_path, f"raise {exception}('oracle interrupted')\n")
    assert result.returncode == 1, result.stdout + result.stderr


@pytest.mark.parametrize("phase", ["iteration", "close"])
@pytest.mark.parametrize("error", ["os._exit(0)", "os._exit(2)", "raise KeyboardInterrupt()", "raise GeneratorExit()"])
def test_wsgi_lazy_response_errors_are_candidate_failures(tmp_path, phase, error):
    source = (ROOT / "oracles/maintenance-banner/probe_banner.py").read_text(encoding="utf-8")
    candidate = (
        "import os\nclass Response:\n"
        "    def __iter__(self):\n"
        f"        {error if phase == 'iteration' else 'pass'}\n"
        "        yield b'<html><body>candidate response</body></html>'\n"
        "    def close(self):\n"
        f"        {error if phase == 'close' else 'pass'}\n"
        "def application(environ, start_response):\n"
        "    start_response('200 OK', [('Content-Type', 'text/html')])\n"
        "    return Response()\n"
    )
    result = execute(tmp_path, source, {"services/checkout/app.py": candidate}, ("enabled",))
    assert result.returncode == 10, result.stdout + result.stderr
    diagnostic = "candidate exited before oracle completion" if error.startswith("os.") else error.split()[1][:-2]
    assert diagnostic in result.stderr


@pytest.mark.parametrize("exception", ["RuntimeError", "KeyboardInterrupt", "GeneratorExit"])
def test_wsgi_oracle_callback_defects_remain_unavailable(tmp_path, exception):
    source = (ROOT / "oracles/maintenance-banner/probe_banner.py").read_text(encoding="utf-8")
    source = source.replace('captured["status"], captured["headers"] = status, dict(headers)',
                            f"raise {exception}('oracle callback defect')")
    candidate = ("def application(environ, start_response):\n"
                 "    start_response('200 OK', [('Content-Type', 'text/html')])\n"
                 "    yield b'candidate response'\n")
    result = execute(tmp_path, source, {"services/checkout/app.py": candidate}, ("enabled",))
    assert result.returncode == 1, result.stdout + result.stderr
    assert "oracle callback defect" in result.stderr


def test_candidate_generator_exit_is_attributed_during_iteration(tmp_path):
    source = (ROOT / "oracles/python-craft/check_contracts.py").read_text(encoding="utf-8")
    result = execute(tmp_path, source, {"records.py": "def iter_records(path):\n    import os\n    os._exit(0)\n    yield ''\n"},
                     ("generator",))
    assert result.returncode == 10, result.stdout + result.stderr


@pytest.mark.parametrize("oracle,filename,code,args", [
    ("check_contracts.py", "records.py", "def iter_records(path): return None", ("generator",)),
    ("check_indexed_membership.py", "selection.py", "def iter_selected(rows, allowed_ids): return None", ()),
])
def test_malformed_candidate_iterator_is_failure(tmp_path, oracle, filename, code, args):
    source = (ROOT / "oracles/python-craft" / oracle).read_text(encoding="utf-8")
    result = execute(tmp_path, source, {filename: code}, args)
    assert result.returncode == 10, result.stdout + result.stderr


@pytest.mark.parametrize("data", [None, 4, "bad", [None], [{"status": "closed"}]])
def test_malformed_candidate_filter_response_is_failure(data):
    oracle = load_oracle(ROOT / "oracles/incidents-api/probe_checks.py")
    response = SimpleNamespace(status_code=200, json=lambda: {"data": data, "next_cursor": None})
    client = SimpleNamespace(get=lambda *args, **kwargs: response)
    with pytest.raises(SystemExit) as outcome:
        oracle.check_filter(client)
    assert outcome.value.code == 10


@pytest.mark.parametrize("oracle,case", [("incident-writes", "create"), ("incidents-api", "pagination"),
                                        ("pager-webhook", "signature")])
@pytest.mark.parametrize("candidate", ["raise SystemExit(0)", "import os; os._exit(0)",
                                        "raise RuntimeError('broken candidate')"])
def test_backend_startup_errors_are_supported_candidate_failures(tmp_path, oracle, case, candidate):
    source = (ROOT / f"oracles/{oracle}/probe_checks.py").read_text(encoding="utf-8")
    result = execute(tmp_path, source, {"app/__init__.py": "", "app/main.py": candidate}, (case,))
    assert result.returncode == 10, result.stdout + result.stderr


@pytest.mark.parametrize("oracle,case", [("incident-writes", "create"), ("incidents-api", "pagination"),
                                        ("pager-webhook", "signature")])
def test_backend_missing_instrument_dependency_is_not_candidate_failure(tmp_path, oracle, case):
    source = (ROOT / f"oracles/{oracle}/probe_checks.py").read_text(encoding="utf-8")
    dependency = "from fastapi.testclient import TestClient" if oracle == "incidents-api" else "import httpx"
    assert dependency in source
    source = source.replace(dependency, "import unavailable_oracle_dependency")
    result = execute(tmp_path, source, args=(case,))
    assert result.returncode == 1, result.stdout + result.stderr


def test_workflow_bad_input_fails_and_oracle_crash_is_unavailable(tmp_path):
    source = (ROOT / "oracles/pcf-deploy-job/probe_ci_workflow.py").read_text(encoding="utf-8")
    result = execute(tmp_path, source, {".github/workflows/ci.yml": "jobs: ["}, ("deploy-job",))
    assert result.returncode == 10, result.stdout + result.stderr
    broken = source.replace("reason = CASES[sys.argv[1]]()", "raise RuntimeError('broken oracle')")
    result = execute(tmp_path, broken, args=("deploy-job",))
    assert result.returncode == 1, result.stdout + result.stderr


def test_every_live_probe_owned_command_declares_distinct_failure_and_bound_helper():
    count = 0
    for scenario in (ROOT / "build-scenarios").glob("*.yaml"):
        staged = {}
        for check in yaml.safe_load(scenario.read_text(encoding="utf-8")).get("checks", []):
            staged.update(check.get("writes_from", {}))
            if check.get("check") != "command_exit_zero":
                continue
            command = check["command"]
            targets = [name for name, source in staged.items()
                       if source.startswith("evals/oracles/") and name in command.split()
                       and not source.endswith("semantic_review.py")]
            if not targets:
                continue
            count += 1
            assert check.get("failure_exit_code") == 10, (scenario.name, command)
            if "check_ui.py" not in command:
                assert "oracle_protocol.py" in command, (scenario.name, command)
                assert staged.get("oracle_protocol.py") == "evals/oracles/oracle_protocol.py"
    assert count == 100


def test_ui_report_distinguishes_assertion_failure_from_runner_crash():
    oracle = load_oracle(ROOT / "oracles/incidents-page/check_ui.py")
    def report(status, messages=()):
        return {"testResults": [{"assertionResults": [{"title": "bar1 loading state",
                                                       "status": status, "failureMessages": list(messages)}]}]}
    assert oracle.assessment(report("passed"), "bar1", 0) == 0
    assert oracle.assessment(report("failed", ["AssertionError: no loading state"]), "bar1", 1) == 10
    assert oracle.assessment(report("failed", ["TypeError"]), "bar1", 1,
                             "TypeError\n \u276f src/App.tsx:1:7") == 10
    assert oracle.assessment({"testResults": [{"assertionResults": [],
                             "message": 'process.exit unexpectedly called with "0"'}]}, "bar1", 1,
                             "Error: process.exit\n \u276f src/App.tsx:1:9") == 10
    for message in ('Transform failed: [PARSE_ERROR] src/App.tsx:1:5',
                    'Failed to resolve import "./src/App" from "probe_ui.test.tsx". Does the file exist?'):
        assert oracle.assessment({"testResults": [{"assertionResults": [], "message": message}]}, "bar1", 1) == 10
    for data, code in ((report("failed", ["oracle TypeError"]), 1), (report("passed"), 1),
                       (report("skipped"), 0), ({"testResults": []}, 0), (json.loads('{}'), 1)):
        with pytest.raises(RuntimeError):
            oracle.assessment(data, "bar1", code)


@pytest.mark.parametrize("diagnostics,failed", [
    ("Error: broken during collection\n \u276f src/App.tsx:1:7\n \u276f probe_ui.test.tsx:19:1", True),
    ("Error: broken during collection\n \u276f probe_ui.test.tsx:1:7", False),
    ("Error: broken callback\n \u276f probe_ui.test.tsx:10:4\n \u276f src/App.tsx:8:2", False),
    ('Error: missing ./server\n  File: C:/work/src/test/setup.ts:4:23\n \u276f node_modules/vite/chunk.js:1:1', True),
    ('Error: missing oracle helper\n  File: C:/work/probe_ui.test.tsx:1:7\n \u276f node_modules/vite/chunk.js:1:1', False),
    ('Error: mentions src/App.tsx but has no origin frame', False),
])
def test_ui_collection_failure_uses_origin_not_identical_error_message(diagnostics, failed):
    oracle = load_oracle(ROOT / "oracles/incidents-page/check_ui.py")
    report = {"testResults": [{"assertionResults": [], "message": "broken during collection"}]}
    if failed:
        assert oracle.assessment(report, "bar1", 1, diagnostics) == 10
    else:
        with pytest.raises(RuntimeError):
            oracle.assessment(report, "bar1", 1, diagnostics)


@pytest.mark.parametrize("diagnostics,failed", [
    ("Error: process.exit\n \u276f src/App.tsx:1:9\n \u276f probe_ui.test.tsx:19:1", True),
    ("Error: process.exit\n \u276f probe_ui.test.tsx:1:9", False),
    ("Error: process.exit with no source frame", False),
    ("", False),
])
def test_ui_early_exit_requires_candidate_origin(diagnostics, failed):
    oracle = load_oracle(ROOT / "oracles/incidents-page/check_ui.py")
    report = {"testResults": [{"assertionResults": [], "message": 'process.exit unexpectedly called with "0"'}]}
    if failed:
        assert oracle.assessment(report, "bar1", 1, diagnostics) == 10
    else:
        with pytest.raises(RuntimeError):
            oracle.assessment(report, "bar1", 1, diagnostics)
