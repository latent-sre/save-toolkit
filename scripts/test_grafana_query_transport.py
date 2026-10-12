"""Native PowerShell option and literal macro transport, with entirely offline HTTP probes."""
import base64
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "skills/grafana/scripts/grafana_read.py"
EXPRESSION = 'rate(requests_total{job="caf\u00e9"}[$__rate_interval]) + $__range_s + $__interval_ms'


def _native_probe(tmp_path, shell, options, expression=EXPRESSION):
    executable = shutil.which(shell)
    if not executable:
        pytest.skip(f"{shell} unavailable")
    probe = tmp_path / "query_probe.py"
    probe.write_text(
        "import base64, contextlib, io, json, runpy, sys\n"
        f"helper = runpy.run_path({str(HELPER)!r})\n"
        "requests = []\n"
        "def transport(request):\n"
        "    requests.append({'url': request.full_url, 'body': json.loads(request.data) if request.data else None})\n"
        "    if request.full_url.endswith('/api/org'): payload = {'id': 7}\n"
        "    elif '/api/datasources/uid/' in request.full_url: payload = {'uid': 'metrics', 'type': 'prometheus', 'orgId': 7}\n"
        "    else: payload = {'results': {'A': {'frames': []}}}\n"
        "    return 200, json.dumps(payload).encode()\n"
        "output = io.StringIO()\n"
        "with contextlib.redirect_stdout(output):\n"
        "    code = helper['main'](sys.argv[1:], environ={'GRAFANA_URL': 'https://grafana.example', 'GRAFANA_ORG_ID': '7', 'GRAFANA_SA_TOKEN': 'probe-token'}, transport=transport)\n"
        "print(json.dumps({'argv': sys.argv[1:], 'requests': requests, 'response': json.loads(output.getvalue()), 'code': code}))\n"
        "raise SystemExit(code)\n",
        encoding="utf-8",
    )
    script = (
        "$ErrorActionPreference = 'Stop'\n"
        f"function python {{ & '{sys.executable}' -I -S '{probe}' @($args[3..($args.Count-1)]) }}\n"
        f"& '{HELPER.with_suffix('.ps1')}' -Datasource metrics -Kind prometheus -From 1000 -To 61000 "
        f"-Expr '{expression}' {options}\nexit $LASTEXITCODE"
    )
    return subprocess.run(
        [executable, "-NoProfile", "-NonInteractive", "-EncodedCommand", base64.b64encode(script.encode("utf-16le")).decode()],
        text=True, capture_output=True, timeout=20,
    )


@pytest.mark.skipif(sys.platform != "win32", reason="Native Windows argument transfer")
@pytest.mark.parametrize("shell", ["powershell.exe", "pwsh"])
@pytest.mark.parametrize("mode,output", [("instant", "summary"), ("range", "full")])
def test_native_wrapper_passes_all_options_and_literal_macros_then_python_expands(tmp_path, shell, mode, output):
    result = _native_probe(tmp_path, shell, f"-Mode {mode} -Output {output} -IntervalMs 2000 -RateIntervalMs 15000")
    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads(result.stdout)
    argv = report["argv"]
    assert base64.b64decode(argv[argv.index("--expr-base64") + 1]).decode() == EXPRESSION
    for flag, value in (("--mode", mode), ("--output", output), ("--interval-ms", "2000"), ("--rate-interval-ms", "15000")):
        assert argv.count(flag) == 1
        assert argv[argv.index(flag) + 1] == value
    query = report["requests"][-1]["body"]["queries"][0]
    assert "$__" not in query["expr"]
    assert 'job="caf\u00e9"' in query["expr"]
    assert "+ 60 + 2000" in query["expr"]
    assert query["intervalMs"] == 2000
    assert query["instant"] is (mode == "instant")
    assert query["range"] is (mode == "range")


@pytest.mark.skipif(sys.platform != "win32", reason="Native Windows argument transfer")
@pytest.mark.parametrize("shell", ["powershell.exe", "pwsh"])
def test_native_wrapper_old_invocation_keeps_original_argv_and_defaults(tmp_path, shell):
    result = _native_probe(tmp_path, shell, "", expression='up{job="checkout"}')
    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads(result.stdout)
    assert report["argv"] == [
        "query", "--datasource", "metrics", "--kind", "prometheus", "--from", "1000", "--to", "61000",
        "--expr-base64", base64.b64encode(b'up{job="checkout"}').decode(),
    ]
    query = report["requests"][-1]["body"]["queries"][0]
    assert query["expr"] == 'up{job="checkout"}'
    assert query["range"] is True and query["instant"] is False
    assert query["intervalMs"] == 1000


@pytest.mark.skipif(sys.platform != "win32", reason="Native Windows parameter validation")
@pytest.mark.parametrize("shell", ["powershell.exe", "pwsh"])
@pytest.mark.parametrize("options", [
    "-Mode instant -Mode range", "-Unknown value", "-IntervalMs 999 -RateIntervalMs 15000",
])
def test_native_wrapper_rejects_duplicate_unknown_and_out_of_range_options(tmp_path, shell, options):
    result = _native_probe(tmp_path, shell, options)
    assert result.returncode != 0
    if result.stdout.strip():
        report = json.loads(result.stdout)
        assert report["code"] == 2
        assert report["requests"] == []
        assert report["response"]["ok"] is False
