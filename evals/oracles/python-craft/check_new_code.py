"""Independent public-behavior checks for the greenfield streaming CLI fixture.

Staged only after the model turn. Standard library only; not an OS sandbox.
The traced-storage growth allowance detects whole-stream retention across two
workloads; it is neither a universal bounded-memory proof nor a benchmark.
"""

from collections.abc import Mapping
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import tracemalloc
from types import MappingProxyType
from unittest import TestCase, mock


CHECK = TestCase()
CATEGORIES = ("success", "failure", "skipped")
ZERO = dict.fromkeys(CATEGORIES, 0)


def counts(actual, expected):
    CHECK.assertIsInstance(actual, Mapping, "counts must be a mapping")
    CHECK.assertEqual(dict(actual), expected, "count policy disagrees with specification")
    CHECK.assertTrue(all(type(n) is int for n in actual.values()), "counts must be integers")


class Borrowed:
    def __init__(self, rows):
        self.rows = iter(rows)
        self.iterations = 0
        self.closed = False

    def __iter__(self):
        self.iterations += 1
        CHECK.assertEqual(self.iterations, 1, "borrowed iterable traversed twice")
        return self.rows

    def close(self):
        self.closed = True


class ReadFailure(io.StringIO):
    def __init__(self):
        super().__init__('{"status":"success"}\n')

    def readline(self, *args):
        if self.tell():
            raise OSError("injected late read failure")
        return super().readline(*args)

    def read(self, *args):
        raise OSError("injected read failure")


class ImportInput(io.StringIO):
    def read(self, *args):
        raise AssertionError("import read stdin")

    readline = read

    def __iter__(self):
        raise AssertionError("import read stdin")


def measured(action):
    tracemalloc.start()
    try:
        action()
        return tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def invoke(module, argv, stdin=None):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        with mock.patch.object(sys, "stdin", stdin if stdin is not None else io.StringIO()):
            code = module.main() if argv is None else module.main(argv)
    CHECK.assertIs(type(code), int, "main must return an integer, not exit")
    return code, out.getvalue(), err.getvalue()


def failure(result, label):
    code, out, err = result
    CHECK.assertEqual(code, 2, label + ": failure exit status")
    CHECK.assertEqual(out, "", label + ": partial stdout")
    CHECK.assertTrue(err.strip(), label + ": missing diagnostic")


def success(result, expected):
    code, out, err = result
    CHECK.assertEqual(code, 0, "success exit status")
    CHECK.assertEqual(err, "", "unexpected success diagnostic")
    counts(json.loads(out), expected)  # json.loads rejects a second output object.


def load():
    before = {str(p) for p in Path.cwd().rglob("*")}
    spec = importlib.util.spec_from_file_location("outcome_counts", Path("outcome_counts.py").resolve())
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # supports dataclasses and postponed annotations.
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        with mock.patch("builtins.open", side_effect=AssertionError("import performed file I/O")), \
                mock.patch("io.open", side_effect=AssertionError("import performed file I/O")), \
                mock.patch.object(sys, "stdin", ImportInput()):
            spec.loader.exec_module(module)
    CHECK.assertEqual(out.getvalue() + err.getvalue(), "", "import wrote output")
    CHECK.assertEqual({str(p) for p in Path.cwd().rglob("*")}, before, "import created files")
    return module


def api(module):
    counts(module.summarize(iter(())), ZERO)
    rows = [{"status": "success", "note": "雪"}, {"status": "success", "note": "雪"},
            {"status": "skipped"}, {"status": "failure"}]
    before = copy.deepcopy(rows)
    source = Borrowed(rows)
    counts(module.summarize(source), {"success": 2, "failure": 1, "skipped": 1})
    CHECK.assertEqual(rows, before, "input rows mutated")
    CHECK.assertFalse(source.closed, "borrowed input closed")
    counts(module.summarize([MappingProxyType({"status": "success"})]), {**ZERO, "success": 1})
    for invalid in (None, [], "success", {}, {"status": None}, {"status": True},
                    {"status": 1}, {"status": []}, {"status": "SUCCESS"}, {"status": "unknown"}):
        for index in (1, 2, 4):
            rows = [{"status": "success"} for _ in range(index - 1)] + [invalid]
            before = copy.deepcopy(rows)
            source = Borrowed(rows)
            with CHECK.assertRaisesRegex(ValueError, rf"\b{index}\b", msg="invalid row or record index ignored"):
                module.summarize(source)
            CHECK.assertEqual(rows, before, "input mutated on failure")
            CHECK.assertFalse(source.closed, "borrowed input closed on failure")

    source_error = OSError("borrowed iterator failed")

    def failing_rows():
        yield {"status": "success"}
        raise source_error

    source = Borrowed(failing_rows())
    with CHECK.assertRaisesRegex(OSError, "borrowed iterator failed") as raised:
        module.summarize(source)
    CHECK.assertIs(raised.exception, source_error, "source iteration exception replaced")
    CHECK.assertFalse(source.closed, "borrowed input closed on iterator failure")

    def generated(size):
        for n in range(size):
            yield {"status": "success", "unused": str(n) + "x" * 128}

    peaks = [measured(lambda: counts(module.summarize(generated(size)), {**ZERO, "success": size}))
             for size in (4_000, 80_000)]
    # Fresh per-row mappings prevent a repeated single object from hiding retention.
    # Compare growth rather than rejecting a large constant buffer or interpreter overhead.
    CHECK.assertLess(peaks[1] - peaks[0], 2_000_000,
                     "summarize retained the stream (storage growth exceeds 2 MB)")


def cli(module):
    def run(argv, text=None):
        return subprocess.run([sys.executable, "-I", "-B", "outcome_counts.py", *argv],
                              input=text, capture_output=True, text=True, encoding="utf-8", timeout=15)

    def real(argv, text=None):
        r = run(argv, text)
        return r.returncode, r.stdout, r.stderr

    expected = {"success": 2, "failure": 0, "skipped": 1}
    valid = '{"status":"success","note":"雪 café"}\n' * 2 + '{"status":"skipped"}\n'
    success(real(["-"], valid), expected)
    raw = subprocess.run([sys.executable, "-I", "-B", "outcome_counts.py", "-"],
                         input=valid.encode("utf-8") + b'{"status":"success","unused":"\xff"}\n',
                         capture_output=True, timeout=15)
    failure((raw.returncode, raw.stdout.decode("utf-8"), raw.stderr.decode("utf-8", errors="replace")),
            "invalid UTF-8 stdin")
    with mock.patch.object(sys, "argv", ["outcome_counts.py", "-"]):
        success(invoke(module, None, io.StringIO(valid)), expected)
    success(real(["-"], ""), ZERO)
    for text in ('\n', '{}\n', '[]\n', '{broken}\n', '{"status":"bad"}\n',
                 '{"status":"success","unused":NaN}\n',
                 '{"status":"success","unused":Infinity}\n',
                 '{"status":"success","unused":-Infinity}\n'):
        failure(real(["-"], valid + text), "late invalid JSON Lines")
    failure(real([]), "missing CLI argument")
    failure(real(["-", "extra"], valid), "extra CLI argument")
    failure(invoke(module, []), "main missing argument")
    failure(invoke(module, ["-", "extra"]), "main extra argument")
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "雪-input.jsonl"
        path.write_text(valid, encoding="utf-8")
        success(real([str(path)]), expected)
        failure(real([str(path) + ".missing"]), "file open error")
        path.write_bytes(valid.encode("utf-8") + b"\xff\n")
        failure(real([str(path)]), "UTF-8 decoding error")
        real_open = io.open
        handles = []

        def tracked(*args, **kwargs):
            handle = real_open(*args, **kwargs)
            handles.append(handle)
            return handle

        for content in (valid, valid + '{}\n'):
            path.write_text(content, encoding="utf-8")
            handles.clear()
            with mock.patch("builtins.open", tracked), mock.patch("io.open", tracked):
                result = invoke(module, [str(path)])
            (success(result, expected) if content == valid else failure(result, "file validation"))
            CHECK.assertTrue(handles, "file entrypoint did not open source")
            CHECK.assertTrue(all(h.closed for h in handles), "owned file handle leaked")
        peaks = []
        for size in (4_000, 80_000):
            with real_open(path, "w", encoding="utf-8") as stream:
                for _ in range(size):
                    stream.write('{"status":"success","unused":"' + 'x' * 128 + '"}\n')
            peaks.append(measured(lambda: success(invoke(module, [str(path)]), {**ZERO, "success": size})))
        CHECK.assertLess(peaks[1] - peaks[0], 2_000_000,
                         "CLI retained the stream (storage growth exceeds 2 MB)")
    for source in (io.StringIO(valid), ReadFailure(), io.StringIO(valid + '{}\n')):
        result = invoke(module, ["-"], source)
        CHECK.assertFalse(source.closed, "borrowed stdin closed")
        if isinstance(source, ReadFailure):
            failure(result, "read error")
        elif source.getvalue() == valid:
            success(result, expected)
        else:
            failure(result, "stdin validation")

    # An explicitly wrong ambient encoding makes this deterministic on every host;
    # the CLI must decode borrowed binary stdin as UTF-8 without closing either layer.
    binary = io.BytesIO(valid.encode("utf-8"))
    borrowed = io.TextIOWrapper(binary, encoding="latin-1")
    success(invoke(module, ["-"], borrowed), expected)
    CHECK.assertFalse(borrowed.closed or binary.closed, "borrowed binary stdin closed")

    # New accepted policy: catches copies both before and after shared delegation.
    calls = []
    sentinel = {"success": 7, "failure": 8, "skipped": 9}

    def replacement(rows):
        calls.append(list(rows))
        return sentinel

    with mock.patch.object(module, "summarize", replacement):
        result = invoke(module, ["-"], io.StringIO('{"status":"future"}\n'))
        CHECK.assertEqual(result[0], 0, "CLI bypassed shared summarize policy")
        success(result, sentinel)
    CHECK.assertEqual(calls, [[{"status": "future"}]], "CLI bypassed shared summarize policy")
    calls.clear()
    binary = io.BytesIO('{"status":"future","note":"雪 café"}\n'.encode("utf-8"))
    borrowed = io.TextIOWrapper(binary, encoding="latin-1")
    with mock.patch.object(module, "summarize", replacement):
        success(invoke(module, ["-"], borrowed), sentinel)
    CHECK.assertFalse(borrowed.closed or binary.closed, "borrowed binary stdin closed")
    CHECK.assertEqual(calls, [[{"status": "future", "note": "雪 café"}]],
                      "stdin CLI did not decode UTF-8 rows for shared policy")
    calls.clear()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "policy-雪.jsonl"
        path.write_text('{"status":"future","note":"雪 café"}\n', encoding="utf-8")
        with mock.patch.object(module, "summarize", replacement):
            result = invoke(module, [str(path)])
            CHECK.assertEqual(result[0], 0, "file CLI bypassed shared summarize policy")
            success(result, sentinel)
    CHECK.assertEqual(calls, [[{"status": "future", "note": "雪 café"}]],
                      "file CLI did not deliver UTF-8 rows to shared policy")
    with mock.patch.object(module, "summarize", side_effect=ValueError("replacement rejects record 1")):
        failure(invoke(module, ["-"], io.StringIO(valid)), "replacement policy failure")


def self_tests():
    CHECK.assertTrue(list(Path("tests").rglob("test*.py")), "no runnable self-tests")
    result = subprocess.run([sys.executable, "-I", "-B", "-m", "unittest", "discover", "-s", "tests", "-t", ".", "-v"],
                            capture_output=True, text=True, encoding="utf-8", timeout=30)
    CHECK.assertRegex(result.stderr, r"Ran [1-9]\d* tests?", "no self-tests executed")
    CHECK.assertEqual(result.returncode, 0, "candidate self-tests failed: " + result.stderr)
    CHECK.assertRegex(result.stderr, r"\.\.\. ok", "no self-test passed")


if __name__ == "__main__":
    candidate = load()
    api(candidate)
    cli(candidate)
    self_tests()
    print("greenfield Python public contracts passed")
