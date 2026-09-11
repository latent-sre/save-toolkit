"""Outcome checks staged after the model turn; no third-party dependencies.

These inspect candidate modules in a disposable fixture, not arbitrary repositories.
They are public regression oracles, not hidden evaluations or a sandbox.
"""

import importlib.util
import io
import ipaddress
from pathlib import Path
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

    def fail(value):
        emitted.append(value)
        if value == 2:
            raise RuntimeError("callback failed")

    with CHECK.assertRaisesRegex(RuntimeError, "^callback failed$"):
        process([0, 2, 3], emit=fail)
    CHECK.assertEqual(emitted, [0, 2])


def generator():
    real_open = io.open
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "records.txt"
        path.write_text(" one \n\n two\n", encoding="utf-8")
        handles = []

        def tracked_open(*args, **kwargs):
            handle = real_open(*args, **kwargs)
            handles.append(handle)
            return handle

        with mock.patch("builtins.open", tracked_open), mock.patch("io.open", tracked_open):
            read = load("records.py").iter_records
            records = read(path)
            CHECK.assertIs(iter(records), records)
            CHECK.assertEqual(next(records), "one")
            CHECK.assertTrue(handles, "the file was not opened")
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


if __name__ == "__main__":
    checks = {"refactor": refactor, "generator": generator, "migration": migration, "unchanged": unchanged}
    checks[sys.argv[1]]()
    print("contract passed:", sys.argv[1])
