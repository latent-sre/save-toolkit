"""Offline discrimination of suitable-package and bare-interpreter choices."""

from __future__ import annotations

import importlib.metadata
import subprocess
import tempfile
import textwrap
from pathlib import Path

import pytest
from probe_testkit import ROOT, load_oracle, run_python, scenario, write_tree

ORACLE = ROOT / "evals/oracles/python-craft/check_library_selection.py"
PROTOCOL = ROOT / "evals/oracles/oracle_protocol.py"
PREFIX = "build-python-library-selection-"

SCHEMA = """
import jsonschema
from jsonschema.exceptions import SchemaError, ValidationError

def validate_payload(schema, payload):
    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise ValueError("invalid schema") from exc
    if next(jsonschema.Draft202012Validator(schema).iter_errors(payload), None) is not None:
        raise ValueError("invalid payload")
    return payload
"""

CSV = """
import csv
from decimal import Decimal, InvalidOperation

def summarize(lines):
    totals = dict.fromkeys(("sales", "refunds", "fees"), Decimal("0"))
    source_errors = []
    def observed_lines():
        try:
            for line in lines:
                yield line
        except BaseException as exc:
            source_errors.append(exc)
            raise
    try:
        reader = csv.reader(observed_lines(), strict=True)
        if next(reader, None) != ["category", "amount", "note"]:
            raise ValueError("invalid header")
        for row in reader:
            if len(row) != 3 or row[0] not in totals:
                raise ValueError("invalid record")
            value = Decimal(row[1])
            if not value.is_finite():
                raise ValueError("invalid amount")
            totals[row[0]] += value
    except (csv.Error, InvalidOperation) as exc:
        if source_errors and exc is source_errors[0]:
            raise
        raise ValueError("invalid CSV") from exc
    return totals
"""

CSV_DICT = """
import csv
from decimal import Decimal, InvalidOperation

def summarize(lines):
    totals = dict.fromkeys(("sales", "refunds", "fees"), Decimal("0"))
    source_errors = []
    def observed_lines():
        try:
            for line in lines:
                yield line
        except BaseException as exc:
            source_errors.append(exc)
            raise
    try:
        reader = csv.DictReader(observed_lines(), strict=True)
        class CheckedRecords:
            def __init__(self, records):
                self.records = records
            def __iter__(self):
                return self
            def __next__(self):
                row = next(self.records)
                if not row:
                    raise ValueError("invalid record")
                return row
            @property
            def line_num(self):
                return self.records.line_num
        reader.reader = CheckedRecords(reader.reader)
        if reader.fieldnames != ["category", "amount", "note"]:
            raise ValueError("invalid header")
        for row in reader:
            if None in row or any(value is None for value in row.values()) or row["category"] not in totals:
                raise ValueError("invalid record")
            amount = Decimal(row["amount"])
            if not amount.is_finite():
                raise ValueError("invalid amount")
            totals[row["category"]] += amount
    except (csv.Error, InvalidOperation) as exc:
        if source_errors and exc is source_errors[0]:
            raise
        raise ValueError("invalid CSV") from exc
    return totals
"""

BROKEN_SOURCE_ERROR_CSV = CSV.replace("        if source_errors and exc is source_errors[0]:\n            raise\n", "")
BORROWED_CLOSING_CSV = CSV.replace("for line in lines:\n                yield line", "yield from lines")


def correct(mode: str) -> dict[str, str]:
    if mode == "schema":
        return {
            "validation.py": SCHEMA,
            "requirements.txt": "jsonschema==4.26.0\n",
            "tests/test_selection.py": """
import unittest
import api
class SelectionTests(unittest.TestCase):
    def test_preserves_payload(self):
        payload = {"name": "ok"}
        self.assertIs(api.submit({"type": "object"}, payload), payload)
    def test_integer_is_not_boolean(self):
        with self.assertRaises(ValueError):
            api.submit({"type": "integer"}, True)
""",
        }
    return {
        "money_report.py": CSV,
        "tests/test_selection.py": """
import unittest
from decimal import Decimal
import consumer
import money_report
class SelectionTests(unittest.TestCase):
    def test_exact_money(self):
        rows = iter(["category,amount,note\\n", "sales,0.1,ok\\n"])
        self.assertEqual(money_report.summarize(rows)["sales"], Decimal("0.1"))
    def test_late_invalid_record(self):
        rows = iter(["category,amount,note\\n", "sales,1,ok\\n", "other,1,bad\\n"])
        with self.assertRaises(ValueError):
            consumer.render(rows)
""",
    }


def artifact(mode: str, changes: dict[str, str] | None = None, *, oracle_source: str | None = None):
    with tempfile.TemporaryDirectory(prefix="library-selection-test-") as directory:
        root = Path(directory)
        candidate = root / "candidate"
        files = scenario(PREFIX + mode)["fixture"]["files"]
        files.update({name: textwrap.dedent(source) for name, source in (changes or {}).items()})
        write_tree(candidate, files)
        selected = ORACLE
        if oracle_source is not None:
            selected = root / "instrument.py"
            oracle_source = oracle_source.replace(
                "sys.path.insert(0, str(Path(__file__).resolve().parent.parent))",
                f"sys.path.insert(0, {str(PROTOCOL.parent)!r})",
                1,
            )
            selected.write_text(oracle_source, encoding="utf-8")
            # The bare deployment child still uses the existing supervised protocol.
            (candidate / "oracle_protocol.py").write_bytes(PROTOCOL.read_bytes())
        before = {path.relative_to(candidate): path.read_bytes() for path in candidate.rglob("*") if path.is_file()}
        result = run_python(["-B", str(PROTOCOL), str(selected), mode], cwd=candidate, isolated=True, timeout=70)
        after = {path.relative_to(candidate): path.read_bytes() for path in candidate.rglob("*") if path.is_file()}
        assert before == after, "oracle changed the candidate"
        return result


def eligible_schema_runtime():
    try:
        pin = importlib.metadata.version("jsonschema")
    except importlib.metadata.PackageNotFoundError:
        pytest.skip("schema calibration needs the supplied jsonschema runtime; no installation attempted")
    if pin != "4.26.0":
        pytest.skip("schema calibration needs the supplied jsonschema 4.26.0 runtime")


@pytest.mark.parametrize("mode", ["schema", "csv"])
def test_existing_fixture_is_runnable_but_fails_new_contract(mode):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        write_tree(root, scenario(PREFIX + mode)["fixture"]["files"])
        suite = run_python(["-B", "-m", "unittest", "discover", "-s", "tests", "-t", "."], cwd=root)
        assert suite.returncode == 0, suite.stderr
    result = artifact(mode)
    assert result.returncode == 10, result.stderr


@pytest.mark.parametrize("mode", ["schema", "csv"])
def test_correct_selection_passes_supervised_contract_without_candidate_writes(mode):
    if mode == "schema":
        eligible_schema_runtime()
    result = artifact(mode, correct(mode))
    assert result.returncode == 0, result.stderr
    assert "library-selection contract passed: " + mode in result.stdout


@pytest.mark.parametrize(
    "body",
    [
        """validator = jsonschema.validators.validator_for(schema)
    try:
        validator.check_schema(schema)
    except SchemaError as exc:
        raise ValueError("invalid schema") from exc
    if not validator(schema).is_valid(payload):
        raise ValueError("invalid payload")""",
        """try:
        jsonschema.validate(payload, schema)
    except SchemaError as exc:
        raise ValueError("invalid schema") from exc
    except ValidationError as exc:
        raise ValueError("invalid payload") from exc""",
        """try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise ValueError("invalid schema") from exc
    try:
        jsonschema.Draft202012Validator(schema).validate(payload)
    except ValidationError as exc:
        raise ValueError("invalid payload") from exc""",
    ],
    ids=["validator-for-is-valid", "top-level-validate", "instance-validate"],
)
def test_real_library_api_alternatives_are_eligible(body):
    eligible_schema_runtime()
    body = body.replace("\n    ", "\n")
    source = (
        "import jsonschema\nfrom jsonschema.exceptions import SchemaError, ValidationError\n"
        "def validate_payload(schema, payload):\n"
        "    if not isinstance(schema, (dict, bool)):\n        raise ValueError('invalid schema')\n    "
        + body.replace("\n", "\n    ")
        + "\n    return payload\n"
    )
    result = artifact("schema", correct("schema") | {"validation.py": source})
    assert result.returncode == 0, result.stderr


def test_dictreader_is_an_eligible_stdlib_alternative():
    result = artifact("csv", correct("csv") | {"money_report.py": CSV_DICT})
    assert result.returncode == 0, result.stderr


def test_source_csv_errors_cannot_be_normalized_as_parser_errors():
    result = artifact("csv", correct("csv") | {"money_report.py": BROKEN_SOURCE_ERROR_CSV})
    assert result.returncode == 10, result.stdout + result.stderr


def test_early_failure_must_not_close_borrowed_generator():
    result = artifact("csv", correct("csv") | {"money_report.py": BORROWED_CLOSING_CSV})
    assert result.returncode == 10, result.stdout + result.stderr


@pytest.mark.parametrize("active,error", [(True, AssertionError), (False, RuntimeError)])
def test_bare_runtime_timeout_distinguishes_candidate_and_instrument(monkeypatch, active, error):
    oracle = load_oracle(ORACLE)

    def timeout(command, **kwargs):
        Path(command[command.index("--child") + 2]).write_bytes(bytes([int(active)]))
        raise subprocess.TimeoutExpired(command, 45)

    monkeypatch.setattr(oracle.subprocess, "run", timeout)
    with pytest.raises(error, match="timed out"):
        oracle.bare_csv()


@pytest.mark.parametrize("requirements", ["missing_schema_library==1.0\n", "jsonschema==0.0.0\n"])
def test_missing_dependency_or_version_is_inconclusive_under_supervision(requirements):
    result = artifact("schema", {"requirements.txt": requirements})
    assert result.returncode == 3, result.stderr
    assert "INCONCLUSIVE: selected dependency" in result.stdout
    assert "contract passed" not in result.stdout


@pytest.mark.parametrize(
    "fault,diagnostic",
    [
        (
            SCHEMA.replace("return payload", "return dict(payload) if isinstance(payload, dict) else payload"),
            "identity lost",
        ),
        (
            SCHEMA.replace(
                "if next(jsonschema.Draft202012Validator(schema).iter_errors(payload), None) is not None:", "if False:"
            ),
            "ValueError not raised",
        ),
        (SCHEMA.replace("invalid schema", "invalid payload"), "invalid schema"),
        (
            SCHEMA.replace(
                "return payload",
                "\n    if isinstance(payload, dict):\n        payload['mutated'] = 1\n    return payload",
            ),
            "mutated",
        ),
    ],
    ids=["copies-payload", "ignores-library-errors", "wrong-error-policy", "mutates-payload"],
)
def test_schema_rejects_behavioral_faults(fault, diagnostic):
    eligible_schema_runtime()
    result = artifact("schema", correct("schema") | {"validation.py": fault})
    assert result.returncode == 10, result.stderr
    assert diagnostic in result.stderr


@pytest.mark.parametrize(
    "filename,source",
    [
        (
            "api.py",
            "from validation import validate_payload\ndef submit(schema, payload):\n    return validate_payload(schema, payload)\n",
        ),
        (
            "batch.py",
            "import validation\ndef load(schema, payloads):\n    return [dict(validation.validate_payload(schema, p)) for p in payloads]\n",
        ),
    ],
    ids=["bound-api-alias", "batch-copy"],
)
def test_schema_callers_cannot_keep_private_policy(filename, source):
    eligible_schema_runtime()
    result = artifact("schema", correct("schema") | {filename: source})
    assert result.returncode == 10, result.stderr


@pytest.mark.parametrize("position", ["before", "after"])
def test_schema_ceremonial_package_calls_cannot_hide_an_independent_engine(position):
    eligible_schema_runtime()
    # A correct independent engine makes normal behavior pass; controlled public
    # library policy then exposes both prevalidation and postvalidation copies.
    source = (
        SCHEMA
        + """
_independent = jsonschema.validators.extend(jsonschema.Draft202012Validator)
_library_validate = validate_payload
def validate_payload(schema, payload):
    try:
        _independent.check_schema(schema)
    except SchemaError as exc:
        raise ValueError("invalid schema") from exc
    PLACEHOLDER
    return payload
"""
    )
    independent = "if not _independent(schema).is_valid(payload):\n        raise ValueError('invalid payload')"
    # The library call's outcome is ignored; the copied engine remains authoritative.
    ceremonial = "try:\n        _library_validate(schema, payload)\n    except ValueError:\n        pass"
    body = independent + "\n    " + ceremonial if position == "before" else ceremonial + "\n    " + independent
    result = artifact("schema", correct("schema") | {"validation.py": source.replace("PLACEHOLDER", body)})
    assert result.returncode == 10, result.stderr


@pytest.mark.parametrize(
    "source,diagnostic",
    [
        (CSV.replace("Decimal(row[1])", "Decimal(float(row[1]))"), "money totals disagree"),
        (
            CSV.replace(
                "reader = csv.reader(observed_lines(), strict=True)",
                "reader = csv.reader(list(observed_lines()), strict=True)",
            ),
            "stream retention",
        ),
        (
            CSV.replace(
                "reader = csv.reader(observed_lines(), strict=True)",
                "reader = (line.rstrip('\\r\\n').split(',') for line in lines)",
            ),
            "invalid record",
        ),
        (CSV.replace("if not value.is_finite():", "if False:"), "ValueError not raised"),
        (CSV.replace("return totals", "lines.close()\n    return totals"), "borrowed input closed"),
        (
            CSV.replace(
                "if len(row) != 3 or row[0] not in totals:",
                "if len(row) != 3 or row[0] not in totals:\n                continue\n            if False:",
            ),
            "ValueError not raised",
        ),
    ],
    ids=["float-money", "materialized-lines", "split-parser", "nonfinite-money", "closed-borrowed", "ignored-late-row"],
)
def test_csv_rejects_targeted_faults(source, diagnostic):
    result = artifact("csv", {"money_report.py": source})
    assert result.returncode == 10, result.stderr
    assert diagnostic in result.stderr


def test_csv_rejects_consumer_that_binds_policy_at_import():
    fixture = scenario(PREFIX + "csv")["fixture"]["files"]["consumer.py"]
    source = fixture.replace("import money_report", "from money_report import summarize").replace(
        "money_report.summarize", "summarize"
    )
    result = artifact("csv", correct("csv") | {"consumer.py": source})
    assert result.returncode == 10, result.stderr
    assert "consumer bypassed owner" in result.stderr


def test_csv_rejects_unnecessary_dependency_manifest():
    result = artifact("csv", correct("csv") | {"requirements.txt": "pandas==3.0.0\n"})
    assert result.returncode == 10, result.stderr
    assert "bare deployment gained a dependency" in result.stderr


def test_csv_enforces_bare_runtime_for_even_an_unused_package_import():
    result = artifact("csv", {"money_report.py": "import jsonschema\n" + CSV})
    assert result.returncode == 10, result.stderr
    assert "No module named 'jsonschema'" in result.stderr


@pytest.mark.parametrize("mode", ["schema", "csv"])
@pytest.mark.parametrize("phase", ["import", "call"])
@pytest.mark.parametrize("fault", ["raise SystemExit(0)", "import os; os._exit(0)"])
def test_candidate_early_exit_does_not_pass_supervised_contract(mode, phase, fault):
    if mode == "schema":
        eligible_schema_runtime()
    files = correct(mode)
    filename = "validation.py" if mode == "schema" else "money_report.py"
    source = textwrap.dedent(files[filename])
    if phase == "import":
        source = fault + "\n" + source
    else:
        name = "validate_payload(schema, payload)" if mode == "schema" else "summarize(lines)"
        source = source.replace("def " + name + ":", "def " + name + ":\n    " + fault, 1)
    result = artifact(mode, files | {filename: source})
    assert result.returncode == 10, result.stderr
    assert "contract passed" not in result.stdout


def test_oracle_owned_fault_remains_machinery_failure():
    source = ORACLE.read_text(encoding="utf-8").replace(
        "def bare_csv():", "def bare_csv():\n    raise RuntimeError('oracle-owned crash')", 1
    )
    result = artifact("csv", correct("csv"), oracle_source=source)
    assert result.returncode == 1, result.stderr
    assert "oracle-owned crash" in result.stderr


def test_scenarios_bind_failure_unavailable_and_deployment_contracts():
    for mode in ("schema", "csv"):
        spec = scenario(PREFIX + mode)
        checks = [check for check in spec["checks"] if "writes_from" in check]
        assert len(checks) == 1
        assert checks[0]["failure_exit_code"] == 10
        assert checks[0]["command"].endswith("_python_library_oracle.py " + mode)
        assert checks[0]["writes_from"] == {
            "_python_library_oracle.py": "evals/oracles/python-craft/check_library_selection.py",
            "oracle_protocol.py": "evals/oracles/oracle_protocol.py",
        }
        assert "semantic review" in checks[0]["text"]
    assert scenario(PREFIX + "schema")["checks"][-1]["inconclusive_exit_code"] == 3
    oracle = load_oracle(ORACLE)
    assert oracle.STORAGE_GROWTH_ALLOWANCE == 32_768


@pytest.mark.parametrize("mode", ["schema", "csv"])
@pytest.mark.parametrize(
    "tests",
    [
        "import unittest\n",
        "import unittest\nclass Empty(unittest.TestCase):\n    def test_nothing(self):\n        pass\n",
    ],
)
def test_empty_and_vacuous_candidate_regressions_cannot_pass(mode, tests):
    if mode == "schema":
        eligible_schema_runtime()
    fixture = scenario(PREFIX + mode)["fixture"]["files"]
    files = correct(mode)
    files.update({name: "import unittest\n" for name in fixture if name.startswith("tests/test_")})
    files["tests/test_selection.py"] = tests
    result = artifact(mode, files)
    assert result.returncode == 10, result.stderr
    assert "candidate test suite is empty" in result.stderr or "candidate tests did not reject" in result.stderr


@pytest.mark.parametrize("mode", ["schema", "csv"])
def test_meaningful_tests_can_be_reorganized_without_name_lock(mode):
    if mode == "schema":
        eligible_schema_runtime()
    files = correct(mode)
    source = files.pop("tests/test_selection.py")
    files["tests/test_reorganized.py"] = source.replace("SelectionTests", "ReorganizedTests").replace(
        "test_", "test_alt_"
    )
    result = artifact(mode, files)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("mode", ["schema", "csv"])
@pytest.mark.parametrize(
    "body,diagnostic",
    [
        ("raise RuntimeError('test crash')", "candidate tests errored"),
        ("self.skipTest('skip')", "candidate tests errored"),
        ("raise SystemExit(0)", "candidate tests errored"),
        ("import os; os._exit(0)", "candidate tests exited without results"),
        ("self.fail('base assertion')", "candidate base test suite failed"),
    ],
)
def test_candidate_suite_errors_skips_and_exits_are_not_regression_evidence(mode, body, diagnostic):
    if mode == "schema":
        eligible_schema_runtime()
    files = correct(mode) | {
        "tests/test_runner_fault.py": "import unittest\nclass Fault(unittest.TestCase):\n    def test_fault(self):\n        "
        + body
        + "\n"
    }
    result = artifact(mode, files)
    assert result.returncode == 10, result.stderr
    assert diagnostic in result.stderr


@pytest.mark.parametrize("when", ["always", "replacement only", "sorted"])
def test_schema_batch_preserves_distinct_input_and_replacement_result_order(when):
    eligible_schema_runtime()
    source = """import validation
def load(schema, payloads):
    pairs = [(payload, validation.validate_payload(schema, payload)) for payload in payloads]
    results = [result for payload, result in pairs]
    REVERSE
    return results
"""
    reverse = (
        "results.reverse()"
        if when == "always"
        else ("if any(result is not payload for payload, result in pairs):\n        results.reverse()")
    )
    if when == "sorted":
        reverse = (
            "if all(isinstance(payload, dict) and 'name' in payload for payload, result in pairs):\n"
            "        results = [result for payload, result in sorted(pairs, key=lambda pair: pair[0]['name'])]"
        )
    result = artifact("schema", correct("schema") | {"batch.py": source.replace("REVERSE", reverse)})
    assert result.returncode == 10, result.stdout + result.stderr
    assert "batch order" in result.stderr
