"""Independent public-behavior checks for the greenfield streaming CLI fixture.

Staged only after the model turn. Standard library only; not an OS sandbox.
The traced-storage growth allowance detects calibrated compact retention across two
workloads; it is neither a universal bounded-memory proof nor a benchmark.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from oracle_protocol import candidate_call

from collections.abc import Mapping
import builtins
import contextlib
import copy
import importlib.util
import io
import json
import subprocess
import tempfile
import tracemalloc
from types import MappingProxyType
from unittest import TestCase, mock


CHECK = TestCase()
CATEGORIES = ("success", "failure", "skipped")
ZERO = dict.fromkeys(CATEGORIES, 0)
STORAGE_GROWTH_ALLOWANCE = 32_768


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
        if self.tell():
            raise OSError("injected late read failure")
        return super().read(*args)


class ImportInput(io.StringIO):
    def read(self, *args):
        raise AssertionError("import read stdin")

    readline = read

    def __iter__(self):
        raise AssertionError("import read stdin")


class FileAccess:
    """Keep retained open aliases usable as checks move from import to runtime."""

    def __init__(self):
        self.importing = True
        self.observing = False
        self.inject_failure = False
        self.handles = []
        self.real_builtin_open = builtins.open
        self.real_io_open = io.open

    def open(self, opener, *args, **kwargs):
        CHECK.assertFalse(self.importing, "import performed file I/O")
        if self.inject_failure:
            mode = args[1] if len(args) > 1 else kwargs.get("mode", "r")
            # Text and binary readers both receive a valid first record. A binary
            # TextIOWrapper may request read1; all subsequent reads fail alike.
            binary = BinaryReadFailure()
            binary.name = str(args[0] if args else kwargs["file"])
            handle = binary if "b" in mode else io.TextIOWrapper(
                binary,
                encoding=args[3] if len(args) > 3 else kwargs.get("encoding"),
                errors=args[4] if len(args) > 4 else kwargs.get("errors"),
                newline=args[5] if len(args) > 5 else kwargs.get("newline"),
            )
        else:
            handle = opener(*args, **kwargs)
        if self.observing:
            self.handles.append(handle)
        return handle

    def builtin_open(self, *args, **kwargs):
        return self.open(self.real_builtin_open, *args, **kwargs)

    def io_open(self, *args, **kwargs):
        return self.open(self.real_io_open, *args, **kwargs)

    @contextlib.contextmanager
    def patched(self):
        with mock.patch("builtins.open", self.builtin_open), mock.patch("io.open", self.io_open):
            yield

    @contextlib.contextmanager
    def observe(self, *, inject_failure=False):
        self.handles.clear()
        self.observing = True
        self.inject_failure = inject_failure
        try:
            yield
        finally:
            self.observing = self.inject_failure = False


class BinaryReadFailure(io.BytesIO):
    def __init__(self):
        super().__init__(b'{"status":"success"}\n')

    def __next__(self):
        # BytesIO's native iterator bypasses an overridden readline method.
        line = self.readline()
        if not line:
            raise StopIteration
        return line

    def read(self, *args):
        if self.tell():
            raise OSError("injected late read failure")
        return super().read(*args)

    read1 = read

    def readline(self, *args):
        if self.tell():
            raise OSError("injected late read failure")
        return super().readline(*args)

    def readinto(self, buffer):
        if self.tell():
            raise OSError("injected late read failure")
        return super().readinto(buffer)


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
            code = candidate_call(module.main) if argv is None else candidate_call(module.main, argv)
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
    files = FileAccess()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        with files.patched(), mock.patch.object(sys, "stdin", ImportInput()):
            candidate_call(spec.loader.exec_module, module)
    files.importing = False
    CHECK.assertEqual(out.getvalue() + err.getvalue(), "", "import wrote output")
    CHECK.assertEqual({str(p) for p in Path.cwd().rglob("*")}, before, "import created files")
    return module, files


def api(module):
    counts(candidate_call(module.summarize, iter(())), ZERO)
    rows = [{"status": "success", "note": "雪"}, {"status": "success", "note": "雪"},
            {"status": "skipped"}, {"status": "failure"}]
    before = copy.deepcopy(rows)
    source = Borrowed(rows)
    counts(candidate_call(module.summarize, source), {"success": 2, "failure": 1, "skipped": 1})
    CHECK.assertEqual(rows, before, "input rows mutated")
    CHECK.assertFalse(source.closed, "borrowed input closed")
    counts(candidate_call(module.summarize, [MappingProxyType({"status": "success"})]), {**ZERO, "success": 1})
    for invalid in (None, [], "success", {}, {"status": None}, {"status": True},
                    {"status": 1}, {"status": []}, {"status": "SUCCESS"}, {"status": "unknown"}):
        for index in (1, 2, 4):
            rows = [{"status": "success"} for _ in range(index - 1)] + [invalid]
            before = copy.deepcopy(rows)
            source = Borrowed(rows)
            with CHECK.assertRaisesRegex(ValueError, rf"\b{index}\b", msg="invalid row or record index ignored"):
                candidate_call(module.summarize, source)
            CHECK.assertEqual(rows, before, "input mutated on failure")
            CHECK.assertFalse(source.closed, "borrowed input closed on failure")

    source_error = OSError("borrowed iterator failed")

    def failing_rows():
        yield {"status": "success"}
        raise source_error

    source = Borrowed(failing_rows())
    with CHECK.assertRaisesRegex(OSError, "borrowed iterator failed") as raised:
        candidate_call(module.summarize, source)
    CHECK.assertIs(raised.exception, source_error, "source iteration exception replaced")
    CHECK.assertFalse(source.closed, "borrowed input closed on iterator failure")

    def generated(size):
        for n in range(size):
            yield {"status": "success", "unused": str(n) + "x" * 128}

    peaks = [measured(lambda: counts(candidate_call(module.summarize, generated(size)), {**ZERO, "success": size}))
             for size in (4_000, 80_000)]
    # Fresh per-row mappings prevent a repeated single object from hiding retention.
    # Compare growth rather than rejecting a large constant buffer or interpreter overhead.
    # The 76,000-record delta exposes even one-byte-per-record retention while
    # leaving room for allocator noise. Large fixed buffers cancel in the delta.
    CHECK.assertLess(peaks[1] - peaks[0], STORAGE_GROWTH_ALLOWANCE,
                     f"summarize retained the stream (storage peaks: {peaks})")


def cli(module, files):
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
        for content in (valid, valid + '{}\n'):
            path.write_text(content, encoding="utf-8")
            with files.observe():
                result = invoke(module, [str(path)])
            (success(result, expected) if content == valid else failure(result, "file validation"))
            CHECK.assertTrue(files.handles, "file entrypoint did not open source")
            CHECK.assertTrue(all(h.closed for h in files.handles), "owned file handle leaked")
        with files.observe(inject_failure=True):
            result = invoke(module, [str(path)])
        failure(result, "file read error")
        CHECK.assertTrue(files.handles, "file read failure was not injected")
        CHECK.assertTrue(all(h.closed for h in files.handles), "owned file handle leaked on read failure")
        peaks = []
        # Both files exceed a 1 MiB chunk so calibrated fixed-size readers fill
        # their buffers at both sizes. This is still a workload-specific check.
        for size in (80_000, 160_000):
            with files.real_io_open(path, "w", encoding="utf-8") as stream:
                for _ in range(size):
                    stream.write('{"status":"success","unused":"' + 'x' * 128 + '"}\n')
            peaks.append(measured(lambda: success(invoke(module, [str(path)]), {**ZERO, "success": size})))
        CHECK.assertLess(peaks[1] - peaks[0], STORAGE_GROWTH_ALLOWANCE,
                         f"CLI retained the stream (storage peaks: {peaks})")
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
    try:
        candidate, file_access = load()
        api(candidate)
        with file_access.patched():
            cli(candidate, file_access)
        self_tests()
    except SystemExit as exc:
        raise AssertionError("candidate exited before contract checks completed") from exc
    print("greenfield Python public contracts passed")
