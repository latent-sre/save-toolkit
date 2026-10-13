"""Bounded installed-ZIP refactoring acceptance, staged after the model turn.

The release format is this fixture's ZIP contract, not wheel/backend conformance.
Execution is supervised measurement on a trusted host, not a hostile-code sandbox.
"""

import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parent))
from oracle_protocol import candidate_call

import builtins
import contextlib
from decimal import Decimal, InvalidOperation
import importlib
import io
import json
import secrets
import shutil
import stat
import subprocess
import tempfile
from unittest import TestCase, mock
import zipfile

CHECK = TestCase()
ORACLE = Path(__file__).resolve()
PROTOCOL = ORACLE.with_name("oracle_protocol.py")


class Borrowed:
    def __init__(self, lines):
        self.lines = iter(lines)
        self.iterations = 0
        self.closed = False

    def __iter__(self):
        self.iterations += 1
        CHECK.assertEqual(self.iterations, 1, "borrowed lines traversed twice")
        return self.lines

    def close(self):
        self.closed = True


def amount(actual, expected):
    CHECK.assertIsInstance(actual, Decimal, "result must remain a Decimal")
    CHECK.assertEqual(actual, Decimal(expected), "numeric, duplicate, or filtering policy changed")


def identical_error(function, args, error):
    with CHECK.assertRaises(type(error)) as raised:
        candidate_call(function, *args)
    CHECK.assertIs(raised.exception, error, "exception identity changed")


def borrowed_contract(function):
    for lines, expected in [
        ([], "0"),
        (["ignored,not-a-number,invalid\n"], "0"),
        (["posted,2,0.10\n"] * 2, "0.40"),
        ([" posted , -2.5 , +0.10 \n", "posted,3,-0.20\n"], "-0.850"),
        (["posted,3,0.1\n", "posted,1,0.2\n"], "0.5"),
    ]:
        source = Borrowed(lines)
        amount(candidate_call(function, source), expected)
        CHECK.assertFalse(source.closed, "borrowed source closed")
    for text, error_type in [
        ("\n", ValueError), ("posted,1\n", ValueError),
        ("ignored,1,2,extra\n", ValueError), ("posted,invalid,2\n", InvalidOperation),
    ]:
        source = Borrowed(["posted,1,0.10\n", text])
        with CHECK.assertRaises(error_type):
            candidate_call(function, source)
        CHECK.assertFalse(source.closed, "borrowed source closed on invalid input")
    for error in (OSError("late borrowed read failure"), ValueError("source value error")):
        def failed():
            yield "posted,1,0.10\n"
            raise error
        source = Borrowed(failed())
        identical_error(function, (source,), error)
        CHECK.assertFalse(source.closed, "borrowed source closed on iteration error")


class FileAccess:
    """Import-time wrappers retain active observation even through open aliases."""
    def __init__(self):
        self.original_builtin, self.original_io = builtins.open, io.open
        self.active = None

    def opened(self, opener, *args, **kwargs):
        target = args[0] if args else kwargs.get("file")
        if self.active is not None and isinstance(target, (str, Path)) and Path(target) == self.active[0]:
            _, replacement, open_error, handles = self.active
            if open_error is not None:
                raise open_error
            handle = replacement if replacement is not None else opener(*args, **kwargs)
            handles.append(handle)
            return handle
        return opener(*args, **kwargs)

    @contextlib.contextmanager
    def patched(self):
        with mock.patch("builtins.open", lambda *a, **k: self.opened(self.original_builtin, *a, **k)), \
                mock.patch("io.open", lambda *a, **k: self.opened(self.original_io, *a, **k)):
            yield

    @contextlib.contextmanager
    def observe(self, path, replacement=None, open_error=None):
        previous = self.active
        handles = []
        self.active = (path, replacement, open_error, handles)
        try:
            yield handles
        finally:
            self.active = previous


FILES = FileAccess()
observe_files = FILES.observe


def assert_closed(handles):
    CHECK.assertTrue(handles, "file adapter did not open its source")
    CHECK.assertTrue(all(handle.closed for handle in handles), "owned file handle leaked")


def installed(root, order):
    with FILES.patched():
        installed_contracts(root, order)


def installed_contracts(root, order):
    CHECK.assertTrue(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,
                     "installed assessment requires -I -S -B")
    # -I -S supplies only the interpreter's standard-library paths; this explicit
    # insertion adds the extracted release, never the source checkout.
    sys.path.insert(0, str(root))
    names = ["order_report.calculation", "order_report.reporting", "order_report.preview"]
    if order == "adapters-first":
        names.reverse()
    for name in names:
        candidate_call(importlib.import_module, name)
    calculation = sys.modules["order_report.calculation"]
    reporting = sys.modules["order_report.reporting"]
    preview = sys.modules["order_report.preview"]
    package = candidate_call(importlib.import_module, "order_report")
    client = candidate_call(importlib.import_module, "clients.scheduled_report")
    cli = candidate_call(importlib.import_module, "order_report.cli")
    for module in (calculation, reporting, preview, package, client, cli):
        CHECK.assertTrue(Path(module.__file__).resolve().is_relative_to(root),
                         "module imported outside the installed release")
    CHECK.assertEqual(calculation.total_from_lines.__module__, "order_report.calculation",
                      "calculation implementation was not extracted")
    CHECK.assertIs(package.total_from_file, reporting.total_from_file, "public file export changed")
    CHECK.assertIs(package.total_from_lines, preview.total_from_lines, "public preview export changed")
    CHECK.assertIs(client.report_alias, reporting.total_from_file, "scheduled consumer alias changed")
    borrowed_contract(calculation.total_from_lines)
    borrowed_contract(preview.total_from_lines)
    borrowed_contract(package.total_from_lines)

    path = Path.cwd() / "orders-雪.csv"
    path.write_text("posted,2,0.10\nposted,2,0.10\nignored,bad,bad\n", encoding="utf-8")
    for function in (reporting.total_from_file, package.total_from_file, client.run):
        amount(candidate_call(function, path), "0.40")
    from importlib.resources import files
    config = json.loads(files("order_report").joinpath("settings.json").read_text(encoding="utf-8"))
    CHECK.assertEqual(config, {"calculator": "order_report.reporting.total_from_file"},
                      "installed configuration contract changed")

    # An invalid line must reach the replacement unchanged; adapters may own I/O,
    # but must not retain a second parser or calculation policy.
    path.write_text("malformed\n", encoding="utf-8")
    seen = []
    def replacement(lines):
        CHECK.assertFalse(getattr(lines, "closed", False), "file closed before owner consumes it")
        seen.append(list(lines))
        return Decimal("7.31")
    def shared_result(function, lines):
        try:
            return candidate_call(function, lines)
        except (Exception, SystemExit) as exc:
            raise AssertionError("adapter bypassed shared owner") from exc
    with mock.patch.object(calculation, "total_from_lines", replacement):
        for function in (reporting.total_from_file, package.total_from_file, client.run):
            with observe_files(path) as handles:
                amount(shared_result(function, path), "7.31")
            assert_closed(handles)
        for function in (preview.total_from_lines, package.total_from_lines):
            source = Borrowed(["malformed\n"])
            amount(shared_result(function, source), "7.31")
            CHECK.assertFalse(source.closed, "preview closes borrowed source")
    CHECK.assertEqual(seen, [["malformed\n"]] * 5, "adapters do not use shared owner")

    for error in (OSError("replaced shared owner failed"), ValueError("replacement value error"),
                  RuntimeError("replacement custom error")):
        def raising(lines):
            raise error
        with mock.patch.object(calculation, "total_from_lines", raising):
            with observe_files(path) as handles:
                identical_error(reporting.total_from_file, (path,), error)
            assert_closed(handles)
            source = Borrowed([])
            identical_error(preview.total_from_lines, (source,), error)
            CHECK.assertFalse(source.closed, "preview closes borrowed input on replacement failure")

    for data, error_type in [(b"posted,2,0.10\n", None), (b"posted,1\n", ValueError),
                             (b"posted,1,invalid\n", InvalidOperation), (b"\xff\n", UnicodeError)]:
        path.write_bytes(data)
        with observe_files(path) as handles:
            if error_type is None:
                amount(candidate_call(reporting.total_from_file, path), "0.20")
            else:
                with CHECK.assertRaises(error_type):
                    candidate_call(reporting.total_from_file, path)
        assert_closed(handles)

    error = OSError("file open failure")
    with observe_files(path, open_error=error):
        identical_error(reporting.total_from_file, (path,), error)
    error = OSError("late owned read failure")
    class FailedRead(io.StringIO):
        def __next__(self):
            if self.tell():
                raise error
            return super().__next__()
        def read(self, *args):
            raise error
        def readline(self, *args):
            if self.tell():
                raise error
            return super().readline(*args)
    with observe_files(path, replacement=FailedRead("posted,1,0.10\n")) as handles:
        identical_error(reporting.total_from_file, (path,), error)
    assert_closed(handles)

    path.write_text("posted,2,0.10\nposted,2,0.10\n", encoding="utf-8")
    def cli_run(arguments):
        bootstrap = ("import sys,runpy;sys.path.insert(0," + repr(str(root)) + ");"
                     "sys.argv=['order_report.cli',*sys.argv[1:]];"
                     "runpy.run_module('order_report.cli',run_name='__main__')")
        try:
            return subprocess.run([sys.executable, "-I", "-S", "-B", "-c", bootstrap, *arguments],
                                  capture_output=True, text=True, timeout=15)
        except subprocess.TimeoutExpired:
            raise AssertionError("installed candidate CLI timed out") from None
    result = cli_run([str(path)])
    CHECK.assertEqual((result.returncode, result.stdout, result.stderr), (0, "0.40\n", ""),
                      "installed CLI behavior changed")
    for arguments in ([], [str(path), "extra"], [str(path) + ".missing"]):
        result = cli_run(arguments)
        CHECK.assertNotEqual(result.returncode, 0, "CLI swallowed input error")
        CHECK.assertEqual(result.stdout, "", "CLI produced success output on error")
        CHECK.assertTrue(result.stderr.strip(), "CLI error diagnostic missing")
    print("installed contracts passed")


def checked_process(oracle, cwd, label, *arguments):
    # Invoke the supervised child directly: the generic supervisor does not carry
    # -S to its own child. Fresh instrumentation outside the checkout also keeps
    # protocol._child's script-directory insertion from restoring source imports.
    with tempfile.TemporaryDirectory(prefix="package-completion-") as temporary:
        receipt, state = Path(temporary) / "result.json", Path(temporary) / "candidate-state"
        state.write_bytes(b"\0")
        nonce = secrets.token_hex(24)
        command = [sys.executable, "-I", "-S", "-B", str(oracle.with_name("oracle_protocol.py")),
                   "--child", str(receipt), str(state), nonce, str(oracle), *arguments]
        try:
            result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired:
            if state.read_bytes() == b"\1":
                raise AssertionError(label + " candidate timed out") from None
            raise RuntimeError(label + " instrument timed out") from None
        if not receipt.is_file():
            if state.read_bytes() == b"\1" and 0 <= result.returncode <= 255:
                raise AssertionError(label + " candidate exited before completion")
            raise RuntimeError(label + " missing completion:\n" + result.stderr)
        if json.loads(receipt.read_text(encoding="utf-8")) != {"nonce": nonce, "code": result.returncode}:
            raise RuntimeError(label + " completion receipt mismatch")
    if result.returncode == 1:
        # The supervised oracle explicitly reserves 1 for unavailable measurement.
        raise RuntimeError(label + " unavailable:\n" + result.stderr)
    CHECK.assertEqual(result.returncode, 0, label + " failed:\n" + result.stderr)
    return result


SUITE_RUNNER = '''import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from oracle_protocol import candidate_call
import json
import unittest
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
suite = candidate_call(unittest.defaultTestLoader.discover, "tests", top_level_dir=".")
result = candidate_call(unittest.TextTestRunner(verbosity=0).run, suite)
print(json.dumps({"nonce": sys.argv[1], "run": result.testsRun,
                  "failures": len(result.failures), "errors": len(result.errors),
                  "skips": len(result.skipped), "expected": len(result.expectedFailures),
                  "unexpected": len(result.unexpectedSuccesses)}))
'''


def suite_result(root):
    runner = root / "_package_suite.py"
    runner.write_text(SUITE_RUNNER, encoding="utf-8")
    shutil.copyfile(PROTOCOL, root / "oracle_protocol.py")
    nonce = secrets.token_hex(24)
    result = checked_process(runner, root, "candidate test execution", nonce)
    rows = []
    for line in result.stdout.splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and row.get("nonce") == nonce:
            rows.append(row)
    CHECK.assertEqual(len(rows), 1, "candidate tests stopped without a completed result")
    return rows[0]


def candidate_tests(source, directory):
    result = suite_result(source)
    CHECK.assertGreater(result["run"], 0, "candidate test suite is empty")
    CHECK.assertEqual((result["failures"], result["errors"]), (0, 0), "candidate tests fail")
    CHECK.assertEqual((result["expected"], result["unexpected"]), (0, 0),
                      "candidate tests must pass normally")
    # Two bounded sensitivity checks, independent of implementation syntax. These
    # demonstrate the requested adapter and iteration regressions, not universal quality.
    for name, relative, suffix in [
        ("preview calculation loss", "order_report/preview.py",
         '\nfrom decimal import Decimal\ndef total_from_lines(lines):\n    return Decimal("0")\n'),
        ("borrowed error suppression", "order_report/calculation.py",
         '\n_original_total = total_from_lines\ndef total_from_lines(lines):\n'
         '    try:\n        return _original_total(lines)\n'
         '    except OSError:\n        from decimal import Decimal\n        return Decimal("0")\n'),
    ]:
        replay = directory / name.replace(" ", "-")
        shutil.copytree(source, replay)
        target = replay / relative
        with target.open("a", encoding="utf-8") as stream:
            stream.write(suffix)
        outcome = suite_result(replay)
        CHECK.assertGreater(outcome["failures"], 0, "candidate tests did not reject " + name)
        CHECK.assertEqual((outcome["errors"], outcome["skips"], outcome["expected"], outcome["unexpected"]),
                          (0, result["skips"], 0, 0),
                          "errors or skips do not establish regression sensitivity")


def assess():
    root = Path.cwd()
    CHECK.assertFalse((root / "order_report/_legacy.py").exists(), "obsolete source retained")
    manifest = (root / "release-files.txt").read_text(encoding="utf-8").splitlines()
    CHECK.assertNotIn("order_report/_legacy.py", manifest, "obsolete release input retained")
    CHECK.assertTrue((root / "order_report/calculation.py").is_file(), "extracted module missing")
    with tempfile.TemporaryDirectory(prefix="package-refactor-oracle-") as temporary:
        scratch = Path(temporary)
        source = scratch / "candidate"
        shutil.copytree(root, source, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc", "release.zip"))
        release = scratch / "release.zip"
        build = subprocess.run([sys.executable, "-I", "-S", "-B", str(source / "build_release.py"), str(release)],
                               cwd=source, capture_output=True, text=True, timeout=15)
        CHECK.assertEqual(build.returncode, 0, "release build failed:\n" + build.stderr)
        CHECK.assertTrue(release.is_file(), "release builder did not create its artifact")
        runtime = scratch / "unrelated-cwd"
        runtime.mkdir()
        instruments = scratch / "instruments"
        instruments.mkdir()
        installed_oracle = instruments / ORACLE.name
        shutil.copyfile(ORACLE, installed_oracle)
        shutil.copyfile(PROTOCOL, instruments / "oracle_protocol.py")
        installed_root = runtime / "installed-release"
        with zipfile.ZipFile(release) as archive:
            entries = archive.infolist()
            names = [entry.filename for entry in entries]
            CHECK.assertEqual(len(names), len(set(names)), "duplicate ZIP entries")
            for entry in entries:
                path = PurePosixPath(entry.filename)
                CHECK.assertFalse(path.is_absolute() or ".." in path.parts or "\\" in entry.filename
                                  or ":" in entry.filename or not path.parts,
                                  "unsafe ZIP entry")
                CHECK.assertFalse(stat.S_ISLNK(entry.external_attr >> 16), "ZIP symlink entry")
            CHECK.assertIn("order_report/calculation.py", names, "new module missing from release")
            CHECK.assertIn("order_report/settings.json", names, "configuration data missing from release")
            CHECK.assertNotIn("order_report/_legacy.py", names, "obsolete code retained in release")
            archive.extractall(installed_root)
        for order in ("owner-first", "adapters-first"):
            result = checked_process(installed_oracle, runtime, "installed release " + order,
                                     "--installed", str(installed_root), order)
            CHECK.assertIn("installed contracts passed", result.stdout, "installed assessment incomplete")
        candidate_tests(source, scratch)
    print("package refactoring contracts passed")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--installed":
        installed(Path(sys.argv[2]).resolve(), sys.argv[3])
    else:
        assess()
