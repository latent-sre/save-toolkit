"""Outcome checks staged after the model turn; no third-party dependencies.

These inspect candidate modules in a disposable fixture, not arbitrary repositories.
They are public regression oracles, not hidden evaluations or a sandbox.
"""

import importlib.util
import io
import ipaddress
from itertools import product
from pathlib import Path
import subprocess
import sys
import tempfile
from unittest import TestCase, mock


CHECK = TestCase()


def load(filename):
    spec = importlib.util.spec_from_file_location("candidate", Path(filename).resolve())
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def refactor():
    process = load("batch.py").process
    for limit, result, effects in [
        (None, [0, 4, 6], [0, 2, 3]), (0, [], []), (1, [0], [0]),
        (2, [0, 4], [0, 2]), (10, [0, 4, 6], [0, 2, 3]),
    ]:
        values, emitted = [None, -1, 0, 2, 3], []
        actual = process(values, limit=limit, emit=emitted.append)
        CHECK.assertIs(type(actual), list)
        CHECK.assertTrue(all(type(value) is int for value in actual), "integer result type changed")
        CHECK.assertEqual(actual, result)
        CHECK.assertEqual(emitted, effects)
        CHECK.assertEqual(values, [None, -1, 0, 2, 3])
    values, emitted = [3, None, -1, 0, 3, 2], []
    CHECK.assertEqual(process(values, emit=emitted.append), [6, 0, 6, 4])
    CHECK.assertEqual(emitted, [3, 0, 3, 2])
    CHECK.assertEqual(values, [3, None, -1, 0, 3, 2])
    emitted = []
    with CHECK.assertRaisesRegex(ValueError, "^negative limit$"):
        process([1], limit=-1, emit=emitted.append)
    CHECK.assertEqual(emitted, [])
    CHECK.assertEqual(process([], emit=emitted.append), [])
    CHECK.assertEqual(process([None, -5], emit=emitted.append), [])
    CHECK.assertEqual(emitted, [])

    with CHECK.assertRaises(TypeError):
        process([1], None, emitted.append)
    CHECK.assertEqual(emitted, [])
    failure = RuntimeError("callback failed")

    def fail(value):
        emitted.append(value)
        if value == 2:
            raise failure

    with CHECK.assertRaisesRegex(RuntimeError, "^callback failed$") as raised:
        process([0, 2, 3], emit=fail)
    CHECK.assertIs(raised.exception, failure, "callback exception replaced")
    CHECK.assertEqual(emitted, [0, 2])

    # Exhaust the small input domain independently of the candidate's control flow.
    for width in range(4):
        for items in product((None, -2, 0, 1, 3), repeat=width):
            accepted = [item for item in items if item is not None and item >= 0]
            for limit in (None, -1, 0, 1, 2, 5):
                values, effects = list(items), []
                if limit == -1:
                    with CHECK.assertRaisesRegex(ValueError, "^negative limit$"):
                        process(values, limit=limit, emit=effects.append)
                    expected = []
                else:
                    expected = accepted if limit is None else accepted[:limit]
                    actual = process(values, limit=limit, emit=effects.append)
                    CHECK.assertIs(type(actual), list)
                    CHECK.assertTrue(all(type(value) is int for value in actual))
                    CHECK.assertEqual(actual, [value * 2 for value in expected])
                CHECK.assertEqual(effects, expected)
                CHECK.assertEqual(values, list(items))


class ObservedSource:
    """Observe logical consumption while allowing bounded text buffering."""

    def __init__(self, source):
        self.source = source
        self.eager = self.eof = False

    def __getattr__(self, name):
        return getattr(self.source, name)

    def __enter__(self):
        return self

    def __exit__(self, *error):
        return self.source.__exit__(*error)

    def __iter__(self):
        return self

    def __next__(self):
        line = self.readline()
        if not line:
            raise StopIteration
        return line

    def readline(self, size=-1):
        line = self.source.readline(size)
        self.eof |= size != 0 and line == ""
        return line

    def read(self, size=-1):
        self.eager |= size is None or size < 0
        text = self.source.read(size)
        self.eof |= size != 0 and text == ""
        return text

    def readlines(self, hint=-1):
        self.eager |= hint is None or hint <= 0
        lines = self.source.readlines(hint)
        self.eof |= not lines
        return lines


def generator():
    real_open = io.open
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "records.txt"
        path.write_text(" one \n\n two\n", encoding="utf-8")
        handles = []

        def tracked_open(*args, **kwargs):
            handle = ObservedSource(real_open(*args, **kwargs))
            handles.append(handle)
            return handle

        with mock.patch("builtins.open", tracked_open), mock.patch("io.open", tracked_open):
            read = load("records.py").iter_records
            records = read(path)
            CHECK.assertIs(iter(records), records)
            CHECK.assertEqual(next(records), "one")
            CHECK.assertTrue(handles, "the file was not opened")
            CHECK.assertFalse(any(handle.eager or handle.eof for handle in handles),
                              "source consumed eagerly before first yield")
            CHECK.assertTrue(any(not handle.closed for handle in handles))
            records.close()
            CHECK.assertTrue(all(handle.closed for handle in handles))
            handles.clear()
            CHECK.assertEqual(list(read(path)), ["one", "", "two"])
            CHECK.assertTrue(handles and all(handle.closed for handle in handles))
        path.write_bytes(b"\xff")
        handles.clear()
        with mock.patch("builtins.open", tracked_open), mock.patch("io.open", tracked_open):
            with CHECK.assertRaises(UnicodeDecodeError):
                list(read(path))
            CHECK.assertTrue(handles and all(handle.closed for handle in handles))


def migration():
    real_address = ipaddress.IPv4Address
    with mock.patch.object(ipaddress, "IPv4Address", wraps=real_address) as validator:
        parse = load("addresses.py").parse_address
        for value in ["0.0.0.0", "127.0.0.1", "192.0.2.1", "255.255.255.255"]:
            CHECK.assertEqual(parse(value), value)
        CHECK.assertGreaterEqual(validator.call_count, 4, "stdlib validator was not used")
        for value in [None, True, 1, b"\x7f\x00\x00\x01", "", "::1", "1.2.3",
                      "1.2.3.4.5", "256.0.0.1", "-1.0.0.0", "01.2.3.4",
                      "1.2.3.4 ", " 1.2.3.4", "١.2.3.4", "1.2.3.+4"]:
            with CHECK.assertRaisesRegex(ValueError, "^invalid address$"):
                parse(value)


def unchanged():
    predicate = load("predicates.py").is_nonnegative
    for value, expected in [(-10**100, False), (-1, False), (0, True), (1, True), (10**100, True)]:
        CHECK.assertIs(predicate(value), expected)


def modules():
    # Import caches cannot make a broken import order appear valid.
    if len(sys.argv) == 2:
        for first in ("reports", "formatting"):
            subprocess.run([sys.executable, "-I", "-B", str(Path(__file__).resolve()), "modules", first],
                           check=True, timeout=10)
        return
    sys.path.insert(0, str(Path.cwd()))
    importlib.import_module(sys.argv[2])
    formatting = importlib.import_module("formatting")
    reports = importlib.import_module("reports")
    client = importlib.import_module("client")
    CHECK.assertEqual(formatting.format_label.__module__, "formatting", "implementation was not moved")
    CHECK.assertEqual(client.FORMATTERS.get(formatting.format_label), "default",
                      "new callable lost the existing alias registry")
    for formatter in (formatting.format_label, reports.format_label, client.label_alias, client.configured_label):
        CHECK.assertEqual(formatter(" ada ", prefix="Dr. "), "Dr. ADA")
        CHECK.assertEqual(formatter("bob"), "BOB")
        with CHECK.assertRaises(TypeError):
            formatter("ada", "Dr. ")
        with CHECK.assertRaisesRegex(TypeError, "^name must be text$"):
            formatter(None)
        with CHECK.assertRaisesRegex(ValueError, "^empty name$"):
            formatter("  ")
    names = [" bob ", "ada", "bob"]
    CHECK.assertEqual(reports.render(names, prefix="!"), ["!BOB", "!ADA", "!BOB"])
    CHECK.assertEqual(names, [" bob ", "ada", "bob"])
    with mock.patch.object(reports, "format_label", side_effect=lambda name, **kw: "patched:" + name):
        CHECK.assertEqual(reports.render(["a", "b"]), ["patched:a", "patched:b"])


if __name__ == "__main__":
    checks = {"refactor": refactor, "generator": generator, "migration": migration,
              "unchanged": unchanged, "modules": modules}
    checks[sys.argv[1]]()
    print("contract passed:", sys.argv[1])
