"""Public-behavior controls for opposite dependency-selection pressures.

Selection rationale needs semantic review. Package metadata is an offline supplied
snapshot. The storage comparison detects calibrated row retention, not a universal
bounded-memory proof. These checks are measurement, not a security sandbox.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from oracle_protocol import candidate_call

import contextlib
import copy
import csv
from decimal import Decimal, InvalidOperation
import gc
import importlib
import importlib.metadata
import io
import json
import re
import secrets
import shutil
import subprocess
import tempfile
import tracemalloc
from unittest import TestCase, mock


CHECK = TestCase()
CATEGORIES = ("sales", "refunds", "fees")
ZERO = dict.fromkeys(CATEGORIES, Decimal("0"))
STORAGE_GROWTH_ALLOWANCE = 32_768


def load(names):
    for name in names:
        sys.modules.pop(name, None)
    sys.path.insert(0, str(Path.cwd()))
    out, err = io.StringIO(), io.StringIO()
    before = {p: p.read_bytes() for p in Path.cwd().rglob("*") if p.is_file()}
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        modules = [candidate_call(importlib.import_module, name) for name in names]
    CHECK.assertEqual(out.getvalue() + err.getvalue(), "", "import emitted output")
    after = {p: p.read_bytes() for p in Path.cwd().rglob("*") if p.is_file()}
    CHECK.assertEqual(after, before, "import changed workspace files")
    return modules


def rejected(function, *args, message=None):
    with CHECK.assertRaises(ValueError) as raised:
        candidate_call(function, *args)
    if message is not None:
        CHECK.assertEqual(str(raised.exception), message)


def dependency_runtime():
    declared = [line.split("#", 1)[0].strip() for line in Path("requirements.txt").read_text().splitlines()]
    declared = [line for line in declared if line]
    CHECK.assertEqual(len(declared), 1, "declare exactly one chosen direct dependency")
    match = re.fullmatch(r"([A-Za-z0-9_.-]+)\s*==\s*([A-Za-z0-9_.+-]+)", declared[0])
    CHECK.assertIsNotNone(match, "chosen dependency must use an exact available pin")
    name, pin = match.groups()
    try:
        installed = importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        print("INCONCLUSIVE: selected dependency is unavailable: " + declared[0])
        raise SystemExit(3)
    if installed != pin:
        print("INCONCLUSIVE: selected dependency version is unavailable: " + declared[0])
        raise SystemExit(3)
    if name.lower().replace("_", "-") != "jsonschema":
        print("INCONCLUSIVE: selected dependency needs a reviewed authoritative-library control: " + name)
        raise SystemExit(3)
    return importlib.import_module("jsonschema")


def schema_behavior(owner, api, batch):
    nested = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object", "required": ["orders"], "additionalProperties": False,
        "$defs": {"order": {"type": "object", "required": ["id", "amount"],
                            "additionalProperties": False,
                            "properties": {"id": {"type": "integer", "minimum": 1},
                                           "amount": {"type": "number", "minimum": 0},
                                           "note": {"type": "string", "maxLength": 8}}}},
        "properties": {"orders": {"type": "array", "minItems": 1, "maxItems": 2,
                                  "items": {"$ref": "#/$defs/order"}}},
    }
    cases = [
        (nested, {"orders": [{"id": 2.0, "amount": 0.1, "note": "雪"}]}, True),
        (nested, {"orders": [{"id": True, "amount": 1}]}, False),
        (nested, {"orders": [{"id": 1.5, "amount": 1}]}, False),
        (nested, {"orders": [{"id": 1}]}, False),
        (nested, {"orders": [{"id": 1, "amount": -1}]}, False),
        (nested, {"orders": [{"id": 1, "amount": 1, "other": 0}]}, False),
        (nested, {"orders": [{"id": 1, "amount": 1, "note": "too long here"}]}, False),
        (nested, {"orders": [], "other": 1}, False),
        (nested, {"orders": []}, False),
        (nested, {"orders": [{"id": 1, "amount": 1}] * 3}, False),
        ({"type": ["string", "null"]}, None, True),
        ({"type": ["string", "null"]}, 1, False),
        ({"allOf": [{"type": "number"}, {"exclusiveMinimum": 1}, {"maximum": 3}]}, 2, True),
        ({"allOf": [{"type": "number"}, {"exclusiveMinimum": 1}]}, 1, False),
        ({"anyOf": [{"type": "string"}, {"type": "integer"}]}, {}, False),
        ({"anyOf": [{"type": "string"}, {"type": "integer"}]}, "yes", True),
        ({"oneOf": [{"type": "number"}, {"type": "integer"}]}, 2, False),
        ({"oneOf": [{"type": "number"}, {"type": "integer"}]}, 2.5, True),
        ({"not": {"const": "blocked"}}, "blocked", False),
        ({"not": {"const": "blocked"}}, "open", True),
        ({"enum": [1]}, True, False),
        ({"const": False}, 0, False),
        ({"type": "string", "pattern": "^ok", "minLength": 3}, "ok!", True),
        ({"type": "string", "pattern": "^ok", "minLength": 3}, "no!", False),
        ({"type": "array", "uniqueItems": True}, [1, 1], False),
        ({"$defs": {"a/b": {"type": "integer"}}, "$ref": "#/$defs/a~1b"}, 1, True),
        ({"$defs": {"n": {"type": "integer"}}, "$ref": "#/$defs/n", "minimum": 3}, 2, False),
        (True, {"anything": [1, False]}, True), (False, {}, False),
    ]
    for schema, payload, valid in cases:
        before = copy.deepcopy((schema, payload))
        for function in (owner.validate_payload, api.submit):
            if valid:
                CHECK.assertIs(candidate_call(function, schema, payload), payload, "valid payload identity lost")
            else:
                rejected(function, schema, payload, message="invalid payload")
            CHECK.assertEqual((schema, payload), before, "schema or payload mutated")
        if valid:
            result = candidate_call(batch.load, schema, iter([payload, payload]))
            CHECK.assertEqual(len(result), 2, "batch order or duplicates lost")
            CHECK.assertTrue(all(item is payload for item in result), "batch copied payload")
        else:
            rejected(batch.load, schema, iter([payload]), message="invalid payload")
        CHECK.assertEqual((schema, payload), before, "schema or payload mutated")
    for schema in ({"type": "unknown"}, {"required": "name"}, {"required": [1]},
                   {"minItems": -1}, {"properties": {"x": {"type": "unknown"}}},
                   {"oneOf": []}, {"type": ["string", 1]}, 12):
        before = copy.deepcopy(schema)
        for function in (owner.validate_payload, api.submit):
            rejected(function, schema, {}, message="invalid schema")
        rejected(batch.load, schema, [{}], message="invalid schema")
        CHECK.assertEqual(schema, before, "invalid schema mutated")


def schema_callers(owner, api, batch):
    sentinel = object()
    schema, payload = {"type": "integer"}, {"otherwise": "invalid"}
    calls = []

    def replacement(actual_schema, actual_payload):
        calls.append((actual_schema, actual_payload))
        return sentinel

    with mock.patch.object(owner, "validate_payload", replacement):
        CHECK.assertIs(candidate_call(api.submit, schema, payload), sentinel, "API bypassed owner")
        CHECK.assertEqual(candidate_call(batch.load, schema, [payload, payload]), [sentinel, sentinel],
                          "batch bypassed owner")
    CHECK.assertEqual(calls, [(schema, payload)] * 3, "caller duplicated shared policy")
    failure = ValueError("replaced owner failure")
    with mock.patch.object(owner, "validate_payload", side_effect=failure):
        for function, argument in ((api.submit, payload), (batch.load, [payload])):
            with CHECK.assertRaises(ValueError) as raised:
                candidate_call(function, schema, argument)
            CHECK.assertIs(raised.exception, failure, "caller replaced owner exception")


def authoritative_schema(library):
    target = {"type": "object", "required": ["name"], "additionalProperties": False,
              "properties": {"name": {"type": "string"}}}
    real = library.Draft202012Validator.iter_errors
    for forced_error, payload in ((True, {"name": "valid"}), (False, {})):
        calls = []

        def controlled(validator, instance, *args, **kwargs):
            if validator.schema == target:
                calls.append(instance)
                return iter([library.ValidationError("controlled library policy")]) if forced_error else iter(())
            return real(validator, instance, *args, **kwargs)

        # Patch before candidate import: cached validators and imported aliases are eligible.
        # Metaschema validation still executes the real implementation.
        with mock.patch.object(library.Draft202012Validator, "iter_errors", controlled):
            owner, api, batch = load(("validation", "api", "batch"))
            for function, argument in ((owner.validate_payload, payload), (api.submit, payload),
                                       (batch.load, [payload])):
                calls.clear()
                if forced_error:
                    rejected(function, target, argument, message="invalid payload")
                else:
                    result = candidate_call(function, target, argument)
                    CHECK.assertTrue(result is payload or result == [payload], "manual validation overruled library")
                CHECK.assertTrue(calls, "chosen library did not own this validation outcome")


class Borrowed:
    def __init__(self, lines):
        self.lines = iter(lines)
        self.iterations = 0
        self.closed = False

    def __iter__(self):
        self.iterations += 1
        CHECK.assertEqual(self.iterations, 1, "borrowed input traversed twice")
        return self.lines

    def close(self):
        self.closed = True


def csv_lines(text):
    return Borrowed(io.StringIO(text, newline=""))


def money_result(module, text, expected):
    source = csv_lines(text)
    result = candidate_call(module.summarize, source)
    CHECK.assertEqual(dict(result), expected, "money totals disagree")
    CHECK.assertTrue(all(isinstance(value, Decimal) for value in result.values()), "totals must be Decimal")
    CHECK.assertFalse(source.closed, "borrowed input closed")


def csv_behavior(owner, consumer):
    valid = ('category,amount,note\r\n'
             'sales,0.1,"comma, and ""quote"""\r\n'
             'sales,0.2,"two\r\nphysical lines"\r\n'
             'sales,0.1,duplicate\r\nrefunds,-2.125,雪\r\nfees,1E-2,ok\r\n')
    expected = {"sales": Decimal("0.4"), "refunds": Decimal("-2.125"), "fees": Decimal("0.01")}
    money_result(owner, valid, expected)
    money_result(owner, "category,amount,note\n", ZERO)
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        CHECK.assertEqual(candidate_call(consumer.render, csv_lines(valid)),
                          '{"sales":"0.4","refunds":"-2.125","fees":"0.01"}')
    CHECK.assertEqual(out.getvalue() + err.getvalue(), "", "consumer published output")
    for text in ("", "amount,category,note\nsales,1,ok\n", "category,amount,note,extra\n",
                 "category,amount,note\nsales,1\n", "category,amount,note\nsales,1,ok,extra\n",
                 "category,amount,note\n sales,1,ok\n", "category,amount,note\nsales,NaN,ok\n",
                 "category,amount,note\nsales,Infinity,ok\n", "category,amount,note\nsales,-Infinity,ok\n",
                 "category,amount,note\nsales,not-money,ok\n", "category,amount,note\n\n",
                 'category,amount,note\nsales,1,"unclosed\n'):
        for function in (owner.summarize, consumer.render):
            source = csv_lines(text)
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rejected(function, source)
            CHECK.assertFalse(source.closed, "borrowed input closed on failure")
    for suffix in ("other,1,late\n", "fees,bad,late\n", 'fees,1,"unclosed\n'):
        for function in (owner.summarize, consumer.render):
            source = csv_lines(valid + suffix)
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rejected(function, source)
            CHECK.assertFalse(source.closed, "borrowed input closed on late failure")
    CHECK.assertEqual(out.getvalue() + err.getvalue(), "", "partial output on failure")
    for function in (owner.summarize, consumer.render):
        closed, exhausted = [], []
        def resumable_lines():
            try:
                yield "category,amount,note\n"
                yield "unknown,1,invalid\n"
                yield "sales,1,still borrowed\n"
                exhausted.append(True)
            finally:
                closed.append(True)
        source = resumable_lines()
        try:
            rejected(function, source)
            gc.collect()
            CHECK.assertFalse(closed and not exhausted, "early failure closed borrowed generator")
        finally:
            source.close()
    for error_type in (OSError, ValueError, csv.Error, InvalidOperation):
        source_error = error_type("late source failure")

        def failed_lines():
            yield "category,amount,note\n"
            yield "sales,1,ok\n"
            raise source_error

        for function in (owner.summarize, consumer.render):
            source = Borrowed(failed_lines())
            with CHECK.assertRaises(error_type) as raised:
                candidate_call(function, source)
            CHECK.assertIs(raised.exception, source_error, "source exception replaced")
            CHECK.assertFalse(source.closed, "borrowed input closed on source failure")

    def generated(size):
        yield "category,amount,note\n"
        for index in range(size):
            yield f"sales,0.1,note-{index}-" + "x" * 128 + "\n"

    peaks = []
    for size in (4_000, 80_000):
        tracemalloc.start()
        try:
            source = Borrowed(generated(size))
            result = candidate_call(owner.summarize, source)
            CHECK.assertEqual(result["sales"], Decimal(size) / 10)
            peaks.append(tracemalloc.get_traced_memory()[1])
        finally:
            tracemalloc.stop()
    CHECK.assertLess(peaks[1] - peaks[0], STORAGE_GROWTH_ALLOWANCE,
                     f"stream retention exceeded calibrated storage allowance: {peaks}")

    sentinel = {"sales": Decimal("7.125"), "refunds": Decimal("-9"), "fees": Decimal("0")}
    calls = []

    def replacement(lines):
        calls.append(lines)
        return sentinel

    source = csv_lines("not even CSV")
    with mock.patch.object(owner, "summarize", replacement):
        try:
            result = candidate_call(consumer.render, source)
        except ValueError:
            raise AssertionError("consumer bypassed owner") from None
        CHECK.assertEqual(result,
                          '{"sales":"7.125","refunds":"-9","fees":"0"}', "consumer bypassed owner")
    CHECK.assertEqual(calls, [source], "consumer duplicated policy")


def authoritative_csv():
    for forced_error, text in ((True, "category,amount,note\nsales,1,ok\n"),
                               (False, "invalid input without a header\n")):
        calls = []

        def controlled(lines, *args, **kwargs):
            calls.append(lines)
            # Consume once like the real parser; both reader and DictReader are eligible.
            for _ in lines:
                pass
            class ControlledRows:
                line_num = 0

                def __init__(self):
                    self.rows = iter([["category", "amount", "note"],
                                      ["other" if forced_error else "sales", "7.25", "controlled"]])

                def __iter__(self):
                    return self

                def __next__(self):
                    self.line_num += 1
                    return next(self.rows)

            return ControlledRows()

        with mock.patch.object(csv, "reader", controlled):
            owner, consumer = load(("money_report", "consumer"))
            if forced_error:
                rejected(owner.summarize, csv_lines(text))
                CHECK.assertTrue(calls, "CSV parser did not own API outcome")
                calls.clear()
                rejected(consumer.render, csv_lines(text))
            else:
                money_result(owner, text, {**ZERO, "sales": Decimal("7.25")})
                CHECK.assertTrue(calls, "CSV parser did not own API outcome")
                calls.clear()
                CHECK.assertEqual(candidate_call(consumer.render, csv_lines(text)),
                                  '{"sales":"7.25","refunds":"0","fees":"0"}')
            CHECK.assertTrue(calls, "CSV parser did not own consumer outcome")


SUITE_RUNNER = r'''
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path.cwd()))
def identifiers(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from identifiers(test)
        else:
            yield test.id()
try:
    suite = unittest.defaultTestLoader.discover("tests", top_level_dir=".")
    names = sorted(identifiers(suite))
    result = unittest.TextTestRunner(stream=sys.stderr).run(suite)
    data = {"ids": names, "run": result.testsRun, "failures": len(result.failures),
            "errors": len(result.errors), "skips": len(result.skipped),
            "unexpected": len(result.unexpectedSuccesses), "expected": len(result.expectedFailures)}
except BaseException as exc:
    data = {"discovery_error": type(exc).__name__}
Path(sys.argv[1]).write_text(json.dumps(data), encoding="utf-8")
'''


TEST_MUTANTS = {
    "schema": {
        "valid payload identity lost": '''
_suite_validate = validate_payload
def validate_payload(schema, payload):
    result = _suite_validate(schema, payload)
    return dict(result) if isinstance(result, dict) else result
''',
        "boolean accepted as integer": '''
import jsonschema as _SuiteSchema
_suite_integer_checker = _SuiteSchema.Draft202012Validator.TYPE_CHECKER
_SuiteSchema.Draft202012Validator.TYPE_CHECKER = _suite_integer_checker.redefine(
    "integer", lambda checker, value: isinstance(value, bool) or _suite_integer_checker.is_type(value, "integer"))
''',
    },
    "csv": {
        "exact decimal totals replaced by float": '''
from decimal import Decimal as _SuiteDecimal
_suite_summarize = summarize
def summarize(lines):
    return {key: _SuiteDecimal(float(str(value))) for key, value in _suite_summarize(lines).items()}
''',
        "late invalid record ignored": '''
from decimal import Decimal as _SuiteDecimal
_suite_summarize = summarize
def summarize(lines):
    try:
        return _suite_summarize(lines)
    except ValueError:
        return dict.fromkeys(("sales", "refunds", "fees"), _SuiteDecimal("0"))
''',
    },
}


def test_coverage(mode):
    """Bounded scratch replays prove sensitivity only to these named regressions."""
    filename = "validation.py" if mode == "schema" else "money_report.py"
    with tempfile.TemporaryDirectory(prefix="library-suite-") as directory:
        root = Path(directory)
        scratch = root / "candidate"
        shutil.copytree(Path.cwd(), scratch, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        source = (scratch / filename).read_text(encoding="utf-8")

        def run(label, mutation=""):
            (scratch / filename).write_text(source + mutation, encoding="utf-8")
            receipt = root / (str(len(list(root.glob("*.json")))) + ".json")
            try:
                result = subprocess.run([sys.executable, "-I", "-B", "-c", SUITE_RUNNER, str(receipt)],
                                        cwd=scratch, capture_output=True, text=True, timeout=15)
            except subprocess.TimeoutExpired:
                raise AssertionError("candidate tests timed out: " + label) from None
            CHECK.assertEqual(result.returncode, 0, "candidate test runner failed: " + label)
            CHECK.assertTrue(receipt.is_file(), "candidate tests exited without results: " + label)
            data = json.loads(receipt.read_text())
            CHECK.assertNotIn("discovery_error", data, "candidate tests could not be discovered: " + label)
            CHECK.assertGreater(data["run"], 0, "candidate test suite is empty")
            CHECK.assertEqual(data["errors"] + data["skips"] + data["unexpected"] + data["expected"], 0,
                              "candidate tests errored, skipped or did not pass normally: " + label)
            return data

        base = run("base")
        CHECK.assertEqual(base["failures"], 0, "candidate base test suite failed")
        for label, mutation in TEST_MUTANTS[mode].items():
            changed = run(label, mutation)
            CHECK.assertEqual(changed["ids"], base["ids"], "regression replay changed discovered tests")
            CHECK.assertEqual(changed["run"], base["run"], "regression replay changed executed test count")
            CHECK.assertGreater(changed["failures"], 0, "candidate tests did not reject " + label)


def bare_csv():
    """Reuse the existing supervised child protocol with -S preserved explicitly."""
    protocol = Path(__file__).resolve().parent.parent / "oracle_protocol.py"
    if not protocol.is_file():
        protocol = Path.cwd() / "oracle_protocol.py"
    with tempfile.TemporaryDirectory(prefix="csv-deployment-") as directory:
        receipt, state = Path(directory) / "result.json", Path(directory) / "candidate-state"
        state.write_bytes(b"\0")
        nonce = secrets.token_hex(24)
        try:
            result = subprocess.run(
                [sys.executable, "-I", "-S", "-B", str(protocol), "--child", str(receipt),
                 str(state), nonce, str(Path(__file__).resolve()), "csv-runtime"],
                capture_output=True, text=True, timeout=45,
            )
        except subprocess.TimeoutExpired:
            if state.read_bytes() == b"\1":
                raise AssertionError("bare-interpreter candidate timed out") from None
            raise RuntimeError("bare-interpreter instrument timed out") from None
        if not receipt.is_file():
            if state.read_bytes() == b"\1" and 0 <= result.returncode <= 255:
                raise AssertionError("candidate exited before bare-interpreter assessment")
            raise RuntimeError("bare-interpreter oracle stopped without assessment: " + result.stderr)
        CHECK.assertEqual(json.loads(receipt.read_text()), {"nonce": nonce, "code": result.returncode},
                          "bare-interpreter completion receipt mismatch")
        if result.returncode == 10:
            raise AssertionError("bare-interpreter candidate failed: " + result.stderr)
        if result.returncode:
            raise RuntimeError("bare-interpreter oracle unavailable: " + result.stderr)


def main(mode):
    if mode == "schema":
        library = dependency_runtime()
        owner, api, batch = load(("validation", "api", "batch"))
        schema_behavior(owner, api, batch)
        schema_callers(owner, api, batch)
        authoritative_schema(library)
        test_coverage("schema")
    elif mode == "csv":
        CHECK.assertFalse(Path("requirements.txt").read_text().strip(), "bare deployment gained a dependency")
        bare_csv()
        test_coverage("csv")
    elif mode == "csv-runtime":
        CHECK.assertTrue(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,
                         "deployment was not checked under -I -S -B")
        owner, consumer = load(("money_report", "consumer"))
        csv_behavior(owner, consumer)
        authoritative_csv()
    else:
        raise RuntimeError("unknown library-selection mode")
    print("library-selection contract passed: " + mode)


if __name__ == "__main__":
    main(sys.argv[1])
