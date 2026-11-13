"""Behavioral oracle for go-craft build and refactoring scenarios."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from oracle_protocol import FAILURE


def _run(cmd, *, cwd=None, stdin_data=None, timeout=60):
    """Run a subprocess and return CompletedProcess."""
    return subprocess.run(
        cmd,
        cwd=cwd,
        input=stdin_data,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def _fail(msg):
    """Print failure diagnostic and exit with oracle FAILURE code."""
    print(f"ORACLE FAIL: {msg}", file=sys.stderr)
    sys.exit(FAILURE)


def _require_go_vet_and_test():
    """Run go vet and go test -count=1 on the candidate workspace."""
    vet = _run(["go", "vet", "./..."])
    if vet.returncode != 0:
        _fail(f"go vet ./... failed:\n{vet.stdout}\n{vet.stderr}")
    test = _run(["go", "test", "-count=1", "./..."])
    if test.returncode != 0:
        _fail(f"go test -count=1 ./... failed:\n{test.stdout}\n{test.stderr}")


def _find_main_package():
    """Return the package path containing package main ('.' or './cmd/...')."""
    if Path("cmd").is_dir():
        for sub in sorted(Path("cmd").iterdir()):
            if sub.is_dir() and list(sub.glob("*.go")):
                return f"./cmd/{sub.name}"
    return "."


def check_new_cli():
    """Verify the fresh Go CLI (summarize) contract, exit codes, and pure core."""
    _require_go_vet_and_test()

    # Ensure os.Exit / log.Fatal are not used outside main.go.
    for go_file in Path(".").rglob("*.go"):
        if go_file.name.endswith("_test.go") or go_file.name == "main.go":
            continue
        text = go_file.read_text(encoding="utf-8")
        if "os.Exit(" in text or "log.Fatal" in text:
            _fail(f"{go_file} calls os.Exit or log.Fatal outside main.go")

    pkg = _find_main_package()
    with tempfile.TemporaryDirectory() as tmp:
        exe = Path(tmp) / ("summarize.exe" if os.name == "nt" else "summarize")
        build = _run(["go", "build", "-o", str(exe), pkg])
        if build.returncode != 0:
            _fail(f"go build {pkg} failed:\n{build.stdout}\n{build.stderr}")

        sample = Path(tmp) / "events.jsonl"
        sample.write_text(
            '{"status":"success","id":1}\n'
            '{"status":"failure","id":2}\n'
            '{"status":"success","id":3}\n'
            '{"status":"skipped","id":4}\n',
            encoding="utf-8",
        )
        res = _run([str(exe), str(sample)])
        if res.returncode != 0:
            _fail(f"valid file exited {res.returncode}: {res.stderr}")
        try:
            got = json.loads(res.stdout)
        except json.JSONDecodeError as exc:
            _fail(f"stdout is not valid JSON: {exc}; stdout={res.stdout!r}")
        want = {"success": 2, "failure": 1, "skipped": 1}
        if got != want:
            _fail(f"counts = {got}, want {want}")

        # Stdin '-'
        res_stdin = _run([str(exe), "-"], stdin_data='{"status":"failure"}\n')
        if res_stdin.returncode != 0:
            _fail(f"stdin '-' exited {res_stdin.returncode}: {res_stdin.stderr}")
        if json.loads(res_stdin.stdout) != {"success": 0, "failure": 1, "skipped": 0}:
            _fail(f"stdin counts = {res_stdin.stdout!r}")

        # Invalid status after a valid line -> exit 2, empty stdout, non-empty stderr.
        bad = Path(tmp) / "bad.jsonl"
        bad.write_text('{"status":"success"}\n{"status":"bogus"}\n', encoding="utf-8")
        res_bad = _run([str(exe), str(bad)])
        if res_bad.returncode != 2:
            _fail(f"invalid status exited {res_bad.returncode}, want 2")
        if res_bad.stdout.strip():
            _fail(f"invalid input wrote to stdout: {res_bad.stdout!r}")
        if not res_bad.stderr.strip():
            _fail("invalid input produced empty stderr")

        # Missing args -> exit 2, empty stdout.
        res_noargs = _run([str(exe)])
        if res_noargs.returncode != 2 or res_noargs.stdout.strip():
            _fail(f"no args: code={res_noargs.returncode}, stdout={res_noargs.stdout!r}")


def check_refactor_worker():
    """Verify refactored worker preserves contracts while removing bloat."""
    _require_go_vet_and_test()

    # Check that single-impl JobStore/jobStoreImpl bloat was collapsed.
    for go_file in Path(".").glob("*.go"):
        if go_file.name.endswith("_test.go"):
            continue
        text = go_file.read_text(encoding="utf-8")
        if "jobStoreImpl" in text:
            _fail(f"{go_file} still retains pointless jobStoreImpl wrapper")

    oracle_test = Path("oracle_contract_test.go")
    oracle_test.write_text(
        """package worker

import (
\t"context"
\t"encoding/json"
\t"errors"
\t"testing"
\t"time"
)

func TestOraclePreservesEmptySliceJSON(t *testing.T) {
\tresp, err := ProcessBatch(t.Context(), nil, nil, time.Date(2026, 1, 1, 0, 0, 0, 0, time.UTC))
\tif err != nil {
\t\tt.Fatalf("ProcessBatch(nil) unexpected error: %v", err)
\t}
\tb, err := json.Marshal(resp)
\tif err != nil {
\t\tt.Fatalf("json.Marshal: %v", err)
\t}
\tif string(b) != `{"results":[]}` {
\t\tt.Fatalf("json.Marshal(empty) = %s, want {\\\"results\\\":[]}", b)
\t}
}

func TestOracleErrorWrappingAndOrder(t *testing.T) {
\tsentinel := errors.New("boom")
\tjobs := []Job{
\t\t{ID: "b", Priority: 2},
\t\t{ID: "a", Priority: 1},
\t}
\tresp, err := ProcessBatch(t.Context(), jobs, func(_ context.Context, j Job) (string, error) {
\t\treturn "ok:" + j.ID, nil
\t}, time.Date(2026, 1, 1, 0, 0, 0, 0, time.UTC))
\tif err != nil {
\t\tt.Fatalf("ProcessBatch() unexpected error: %v", err)
\t}
\tif len(resp.Results) != 2 || resp.Results[0].ID != "a" || resp.Results[1].ID != "b" {
\t\tt.Fatalf("ProcessBatch() order = %+v, want [a, b]", resp.Results)
\t}

\t_, err = ProcessBatch(t.Context(), jobs, func(_ context.Context, _ Job) (string, error) {
\t\treturn "", sentinel
\t}, time.Date(2026, 1, 1, 0, 0, 0, 0, time.UTC))
\tif !errors.Is(err, sentinel) {
\t\tt.Fatalf("ProcessBatch() error = %v, want errors.Is(sentinel)", err)
\t}
}
""",
        encoding="utf-8",
    )
    try:
        res = _run(["go", "test", "-count=1", "./..."])
        if res.returncode != 0:
            _fail(f"oracle contract tests failed:\n{res.stdout}\n{res.stderr}")
    finally:
        oracle_test.unlink(missing_ok=True)


def check_synctest_debounce():
    """Verify Debouncer uses testing/synctest without wall-clock sleeps."""
    _require_go_vet_and_test()

    test_files = list(Path(".").rglob("*_test.go"))
    if not test_files:
        _fail("no *_test.go files created")
    joined = "\n".join(p.read_text(encoding="utf-8") for p in test_files)
    if "testing/synctest" not in joined or "synctest.Test(" not in joined:
        _fail("tests do not use testing/synctest (synctest.Test)")
    if "synctest.Wait(" not in joined:
        _fail("tests do not call synctest.Wait() for deterministic synchronization")

    oracle_test = Path("oracle_synctest_test.go")
    oracle_test.write_text(
        """package debounce

import (
\t"sync/atomic"
\t"testing"
\t"testing/synctest"
\t"time"
)

func TestOracleDebouncerCoalescesAndStops(t *testing.T) {
\tsynctest.Test(t, func(t *testing.T) {
\t\tvar calls atomic.Int32
\t\td := New(50*time.Millisecond, func() { calls.Add(1) })
\t\tctx := t.Context()
\t\tdone := make(chan struct{})
\t\tgo func() {
\t\t\tdefer close(done)
\t\t\td.Run(ctx)
\t\t}()

\t\td.Trigger()
\t\ttime.Sleep(30 * time.Millisecond)
\t\td.Trigger()
\t\tsynctest.Wait()
\t\tif got := calls.Load(); got != 0 {
\t\t\tt.Fatalf("calls before quiet window = %d, want 0", got)
\t\t}

\t\ttime.Sleep(50 * time.Millisecond)
\t\tsynctest.Wait()
\t\tif got := calls.Load(); got != 1 {
\t\t\tt.Fatalf("calls after quiet window = %d, want 1", got)
\t\t}
\t})
}
""",
        encoding="utf-8",
    )
    try:
        res = _run(["go", "test", "-count=1", "./..."])
        if res.returncode != 0:
            _fail(f"oracle synctest contract failed:\n{res.stdout}\n{res.stderr}")
    finally:
        oracle_test.unlink(missing_ok=True)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    modes = {
        "new-cli": check_new_cli,
        "refactor-worker": check_refactor_worker,
        "synctest-debounce": check_synctest_debounce,
    }
    if mode not in modes:
        _fail(f"unknown mode {mode!r}")
    modes[mode]()
    print(f"ORACLE PASS: {mode}")


if __name__ == "__main__":
    main()
