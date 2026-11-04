"""Runtime timeout and executable CF-target oracle regression controls."""

import socket
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest
from probe_testkit import load_oracle
from test_eval011_oracles import execute

ROOT = Path(__file__).resolve().parent
GO = ROOT / "oracles/go-incidents-api/probe_checks.py"
CI = ROOT / "oracles/pcf-deploy-job/probe_ci_workflow.py"


@pytest.mark.parametrize(
    "prefix",
    [
        "# cf api https://api.invalid\n# cf target -o prod -s prod",
        "echo cf api https://api.invalid\necho cf target -o prod -s prod",
        "cf api\ncf target -o prod -s prod",
        'cf api "$UNSET"\ncf target -o prod -s prod',
        'cf api https://api.invalid\ncf target -o "$UNSET" -s prod',
        'cf api https://api.invalid\ncf target -o prod -s "$UNSET"',
        'cf api "unterminated\ncf target -o prod -s prod',
        "cf api https://api.invalid\ncf target -o -s prod",
        "cf push checkout\ncf api https://api.invalid\ncf target -o prod -s prod",
    ],
)
def test_cf_target_rejects_noncommands_or_missing_selection(prefix):
    oracle = load_oracle(CI)
    assert oracle._cf_target({"steps": [{"run": prefix + "\ncf push checkout"}]}, {})


@pytest.mark.parametrize(
    "prefix",
    [
        "cf api https://api.invalid\ncf target -o prod -s prod",
        "cf api https://api.invalid && cf target -s prod -o prod",
        "cf api https://api.invalid # endpoint\ncf target -o prod \\\n -s prod",
    ],
)
def test_cf_target_accepts_real_ordered_commands(prefix):
    oracle = load_oracle(CI)
    assert oracle._cf_target({"steps": [{"run": prefix + "\ncf push checkout"}]}, {}) is None


@pytest.mark.parametrize("mode", ["bounded", "unbounded", "streaming", "exited", "broken_http"])
def test_header_timeout_measures_launched_socket_not_source(tmp_path, monkeypatch, mode):
    oracle = load_oracle(GO)
    # These source markers used to pass even though the launched peer has no limit.
    (tmp_path / "main.go").write_text("// ReadHeaderTimeout\nvar unused = http.Server{ReadHeaderTimeout: 0}\n")
    monkeypatch.setattr(oracle, "WORKSPACE", tmp_path)
    monkeypatch.setattr(oracle, "HEADER_TIMEOUT_LIMIT", 0.15, raising=False)
    stop = threading.Event()
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        listener.settimeout(1)

        def serve():
            peer, _ = listener.accept()
            with peer:
                assert b"Host:" in peer.recv(4096)
                if mode == "streaming":
                    while not stop.wait(0.015):
                        try:
                            peer.sendall(b"x")
                        except OSError:
                            break
                else:
                    stop.wait(2 if mode == "unbounded" else 0.025)

        thread = threading.Thread(target=serve)
        thread.start()
        service = SimpleNamespace(
            port=listener.getsockname()[1],
            proc=SimpleNamespace(poll=lambda: 0 if mode == "exited" else None),
            request=lambda *args: (401 if mode == "broken_http" else 200, {}, b"ok"),
        )

        class Running:
            def __enter__(self):
                return service

            def __exit__(self, *args):
                pass

        monkeypatch.setattr(oracle, "Service", Running)
        try:
            with pytest.raises(SystemExit) as result:
                oracle.check_server_timeouts()
            assert result.value.code == (0 if mode == "bounded" else 10)
        finally:
            stop.set()
            thread.join(timeout=2)


@pytest.mark.parametrize("oracle,case", [(GO, "server_timeouts"), (CI, "cf-target")])
@pytest.mark.parametrize(
    "fault,code",
    [
        ("raise SystemExit(0)", 0),
        ("raise SystemExit(10)", 10),
        ("import os; os._exit(0)", 1),
        ("raise SystemExit(1)", 1),
        ("raise RuntimeError('oracle crash')", 1),
    ],
)
def test_changed_oracles_supervised_completion_outcomes(tmp_path, oracle, case, fault, code):
    source = oracle.read_text(encoding="utf-8")
    if oracle == GO:
        source = source.replace("    CHECKS[sys.argv[1]]()", "    " + fault)
    else:
        source = source.replace("        reason = CASES[sys.argv[1]]()", "        " + fault)
    result = execute(tmp_path, source, args=(case,))
    assert result.returncode == code, result.stdout + result.stderr


@pytest.mark.parametrize("commented", [False, True])
def test_actual_cf_target_supervised_assessment(tmp_path, commented):
    prefix = "# " if commented else ""
    workflow = (
        "jobs:\n  deploy:\n    steps:\n      - run: |\n"
        f"          {prefix}cf api https://api.invalid\n"
        f"          {prefix}cf target -o prod -s prod\n"
        "          cf push checkout\n"
    )
    result = execute(tmp_path, CI.read_text(encoding="utf-8"), {".github/workflows/ci.yml": workflow}, ("cf-target",))
    assert result.returncode == (10 if commented else 0), result.stdout + result.stderr


def test_actual_go_missing_tool_is_supervised_unavailable(tmp_path):
    source = GO.read_text(encoding="utf-8").replace('found = shutil.which("go")', "found = None")
    result = execute(tmp_path, source, args=("server_timeouts",))
    assert result.returncode == 1, result.stdout + result.stderr
    assert "go is not installed" in result.stdout


def test_cf_target_resolves_supported_literal_env_values():
    oracle = load_oracle(CI)
    job = {
        "env": {"API": "https://api.invalid", "ORG": "prod", "SPACE": "production space"},
        "steps": [{"run": 'cf api "$API"\ncf target -o "$ORG" -s "$SPACE"\ncf push checkout'}],
    }
    assert oracle._cf_target(job, {}) is None


@pytest.mark.parametrize("setup", ['echo "$UNSET"', 'echo "$(mktemp -d)"'])
def test_cf_target_does_not_resolve_unrelated_setup(setup):
    oracle = load_oracle(CI)
    job = {"steps": [{"run": setup + "\ncf api https://api.invalid\ncf target -o prod -s prod\ncf push checkout"}]}
    assert oracle._cf_target(job, {}) is None
