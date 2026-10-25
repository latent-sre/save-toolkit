"""Offline package-refactoring calibrations; no model calls or network."""

import subprocess
import tempfile
from pathlib import Path

import pytest
from probe_testkit import load_oracle, run_python, scenario_file, write_tree

ROOT = Path(__file__).resolve().parent
SCENARIO = ROOT / "build-scenarios/build-python-package-refactor.yaml"
SPEC = scenario_file(SCENARIO)
POLICY = """from decimal import Decimal

def total_from_lines(lines):
    total = Decimal("0")
    for line in lines:
        status, quantity, price = (field.strip() for field in line.split(","))
        if status == "posted":
            total += Decimal(quantity) * Decimal(price)
    return total
"""
REPORTING = """from . import calculation

def total_from_file(path):
    with open(path, encoding="utf-8") as lines:
        return calculation.total_from_lines(lines)
"""
PREVIEW = """from . import calculation

def total_from_lines(lines):
    return calculation.total_from_lines(lines)
"""
EXTRA_TESTS = """from decimal import Decimal
import unittest
from unittest import mock
from order_report import calculation, preview, reporting
from pathlib import Path
import tempfile

class RefactorTests(unittest.TestCase):
    def test_preview_signed_filtered_duplicates(self):
        lines = ["posted,-2,0.10\\n"] * 2 + ["ignored,bad,bad\\n"]
        self.assertEqual(preview.total_from_lines(iter(lines)), Decimal("-0.40"))

    def test_iteration_error_identity(self):
        error = OSError("borrowed source failed")
        def lines():
            yield "posted,1,0.10\\n"
            raise error
        with self.assertRaises(OSError) as raised:
            calculation.total_from_lines(lines())
        self.assertIs(raised.exception, error)

    def test_shared_owner(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "orders.csv"
            path.write_text("malformed\\n", encoding="utf-8")
            with mock.patch.object(calculation, "total_from_lines", return_value=Decimal("7")):
                self.assertEqual(reporting.total_from_file(path), Decimal("7"))
                self.assertEqual(preview.total_from_lines(["malformed\\n"]), Decimal("7"))
"""


def reference():
    files = dict(SPEC["fixture"]["files"])
    files.pop("order_report/_legacy.py")
    files["release-files.txt"] = files["release-files.txt"].replace(
        "order_report/_legacy.py", "order_report/calculation.py"
    )
    files.update(
        {
            "order_report/calculation.py": POLICY,
            "order_report/reporting.py": REPORTING,
            "order_report/preview.py": PREVIEW,
            "tests/test_refactor.py": EXTRA_TESTS,
        }
    )
    return files


def run_artifact(files=None, *, oracle_tail="", stage_protocol=True):
    check = next(c for c in SPEC["checks"] if c["check"] == "command_exit_zero")
    with tempfile.TemporaryDirectory(prefix="python-package-calibration-") as temporary:
        root = Path(temporary)
        write_tree(root, reference() if files is None else files)
        for name, source in check["writes_from"].items():
            if stage_protocol or name != "oracle_protocol.py":
                (root / name).write_text(
                    (ROOT.parent / source).read_text(encoding="utf-8")
                    + (oracle_tail if name == "_python_package_oracle.py" else ""),
                    encoding="utf-8",
                )
        return run_python(check["command"].split()[1:], cwd=root, timeout=60)


def test_fixture_baseline_runs():
    with tempfile.TemporaryDirectory() as temporary:
        write_tree(Path(temporary), SPEC["fixture"]["files"])
        result = run_python(
            ["-B", "-m", "unittest", "discover", "-s", "tests", "-t", "."],
            cwd=temporary,
        )
        assert result.returncode == 0, result.stderr
        assert "Ran 2 tests" in result.stderr


def test_reference_passes():
    result = run_artifact()
    assert result.returncode == 0, result.stderr
    assert "package refactoring contracts passed" in result.stdout


@pytest.mark.parametrize("dependency", ["site package", "checkout helper"])
def test_installed_preview_cannot_import_outside_release(dependency):
    files = reference()
    imported = "import yaml" if dependency == "site package" else "from tests.release_helper import value"
    files["order_report/preview.py"] = PREVIEW.replace(
        "    return calculation", f"    {imported}\n    return calculation"
    )
    if dependency == "checkout helper":
        files["tests/release_helper.py"] = "value = 1\n"
    result = run_artifact(files)
    assert result.returncode == 10, result.stdout + result.stderr
    assert "ModuleNotFoundError" in result.stderr


def test_alternate_policy_and_test_organization_pass():
    files = reference()
    files["order_report/calculation.py"] = """from decimal import Decimal

def contribution(line):
    status, quantity, price = map(str.strip, line.split(","))
    return Decimal(quantity) * Decimal(price) if status == "posted" else Decimal("0")

def total_from_lines(lines):
    return sum((contribution(line) for line in lines), Decimal("0"))
"""
    files["tests/test_reports.py"] += "\n" + files.pop("tests/test_refactor.py")
    result = run_artifact(files)
    assert result.returncode == 0, result.stderr


def test_buffered_file_adapter_passes_without_a_streaming_requirement():
    files = reference()
    files["order_report/reporting.py"] = """from pathlib import Path
from . import calculation

def total_from_file(path):
    text = Path(path).read_text(encoding="utf-8")
    return calculation.total_from_lines(text.splitlines(keepends=True))
"""
    result = run_artifact(files)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("module", ["builtins", "io"])
def test_imported_open_alias_preserves_cleanup_observation(module):
    files = reference()
    files["order_report/reporting.py"] = f"from {module} import open as file_open\n" + REPORTING.replace(
        "open(path", "file_open(path"
    )
    result = run_artifact(files)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("case", ["new module", "data", "legacy manifest", "legacy source"])
def test_release_and_retirement_failures(case):
    files = reference()
    if case == "new module":
        files["release-files.txt"] = files["release-files.txt"].replace("order_report/calculation.py\n", "")
    elif case == "data":
        files["release-files.txt"] = files["release-files.txt"].replace("order_report/settings.json\n", "")
    elif case == "legacy manifest":
        files["release-files.txt"] += "order_report/_legacy.py\n"
    else:
        files["order_report/_legacy.py"] = SPEC["fixture"]["files"]["order_report/_legacy.py"]
    result = run_artifact(files)
    assert result.returncode == 10, result.stderr


@pytest.mark.parametrize(
    ("file", "source"),
    [
        ("order_report/preview.py", POLICY),
        (
            "order_report/reporting.py",
            REPORTING.replace("from . import calculation", "from .calculation import total_from_lines").replace(
                "calculation.total_from_lines(lines)", "total_from_lines(lines)"
            ),
        ),
        (
            "order_report/preview.py",
            PREVIEW.replace("return calculation.total_from_lines(lines)", "return copied(lines)")
            + POLICY.replace("def total_from_lines", "def copied"),
        ),
    ],
    ids=["partial preview migration", "retained reporting alias", "decorative helper"],
)
def test_shared_policy_regressions(file, source):
    files = reference()
    files[file] = source
    result = run_artifact(files)
    assert result.returncode == 10, result.stderr
    assert "shared owner" in result.stderr


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ("Decimal(quantity) * Decimal(price)", "Decimal(float(quantity) * float(price))"),
        ("for line in lines:", "for line in set(lines):"),
        ('total = Decimal("0")', "total = 0"),
        ('if status == "posted":', 'if status != "posted":'),
        ("for line in lines:", "for line in list(lines):\n        pass\n    for line in lines:"),
        ("    return total", "    if hasattr(lines, 'close'):\n        lines.close()\n    return total"),
    ],
    ids=["float conversion", "duplicate loss", "empty result type", "changed filter", "two passes", "borrowed closure"],
)
def test_calculation_regressions(old, new):
    files = reference()
    files["order_report/calculation.py"] = POLICY.replace(old, new)
    result = run_artifact(files)
    assert result.returncode == 10, result.stderr


@pytest.mark.parametrize(
    "source",
    [
        """from . import calculation
def total_from_file(path):
    lines = open(path, encoding="utf-8")
    return calculation.total_from_lines(lines)
""",
        REPORTING.replace(
            "return calculation.total_from_lines(lines)",
            "return (value for value in [calculation.total_from_lines(lines)])",
        ),
        REPORTING.replace(
            "return calculation.total_from_lines(lines)",
            "try:\n            return calculation.total_from_lines(lines)\n        except OSError as error:\n            raise OSError(str(error))",
        ),
    ],
)
def test_file_lifetime_and_exception_regressions(source):
    files = reference()
    files["order_report/reporting.py"] = source
    result = run_artifact(files)
    assert result.returncode == 10, result.stderr


@pytest.mark.parametrize("behavior", ["suppressed", "replaced", "closed on error"])
def test_borrowed_error_contract_regressions(behavior):
    files = reference()
    tail = """
original_total = total_from_lines
def total_from_lines(lines):
    try:
        return original_total(lines)
"""
    if behavior == "suppressed":
        tail += "    except OSError:\n        return Decimal('0')\n"
    elif behavior == "replaced":
        tail += "    except OSError as error:\n        raise OSError(str(error))\n"
    else:
        tail += "    finally:\n        if hasattr(lines, 'close'):\n            lines.close()\n"
    files["order_report/calculation.py"] += tail
    result = run_artifact(files)
    assert result.returncode == 10, result.stderr


@pytest.mark.parametrize("case", ["configuration", "exports", "unsafe ZIP", "duplicate ZIP"])
def test_installed_contract_regressions(case):
    files = reference()
    if case == "configuration":
        files["order_report/settings.json"] = '{"calculator": "order_report.missing.total"}'
    elif case == "exports":
        files["order_report/__init__.py"] = ""
    elif case == "unsafe ZIP":
        files["build_release.py"] = files["build_release.py"].replace(
            "archive.write(root / entry, arcname=entry)",
            "archive.write(root / entry, arcname=entry)\n                archive.writestr('../escaped.py', '')",
        )
    else:
        files["release-files.txt"] += "order_report/calculation.py\n"
    result = run_artifact(files)
    assert result.returncode == 10, result.stderr
    assert "SyntaxError" not in result.stderr and "IndentationError" not in result.stderr


@pytest.mark.parametrize("file", ["order_report/reporting.py", "order_report/calculation.py"])
def test_broken_installed_import_is_candidate_failure(file):
    files = reference()
    files[file] = "from .missing import broken\n"
    result = run_artifact(files)
    assert result.returncode == 10, result.stderr


@pytest.mark.parametrize("code", ["raise SystemExit(0)\n", "import os\nos._exit(0)\n"])
def test_candidate_early_exit_cannot_pass(code):
    files = reference()
    files["order_report/calculation.py"] = code
    result = run_artifact(files)
    assert result.returncode == 10, result.stderr


@pytest.mark.parametrize("source", ["", "import os\nos._exit(0)\n"])
def test_empty_or_exiting_candidate_tests_cannot_pass(source):
    files = reference()
    files["tests/test_reports.py"] = source
    files["tests/test_refactor.py"] = ""
    result = run_artifact(files)
    assert result.returncode == 10, result.stderr


def test_seed_tests_do_not_establish_new_error_coverage():
    files = reference()
    files.pop("tests/test_refactor.py")
    result = run_artifact(files)
    assert result.returncode == 10, result.stderr
    assert "candidate tests did not reject" in result.stderr


def test_unexpected_success_is_not_a_passing_candidate_suite():
    files = reference()
    files["tests/test_unexpected.py"] = (
        "import unittest\nclass Unexpected(unittest.TestCase):\n"
        "    @unittest.expectedFailure\n    def test_unexpected(self):\n        pass\n"
    )
    result = run_artifact(files)
    assert result.returncode == 10, result.stdout + result.stderr


@pytest.mark.parametrize("active,error", [(True, AssertionError), (False, RuntimeError)])
def test_installed_timeout_distinguishes_candidate_and_instrument(monkeypatch, tmp_path, active, error):
    monkeypatch.syspath_prepend(str(ROOT / "oracles"))
    oracle = load_oracle(ROOT / "oracles/python-craft/check_package_refactor.py")

    def timeout(command, **kwargs):
        assert command[1:4] == ["-I", "-S", "-B"]
        Path(command[command.index("--child") + 2]).write_bytes(bytes([int(active)]))
        raise subprocess.TimeoutExpired(command, 30)

    monkeypatch.setattr(oracle.subprocess, "run", timeout)
    with pytest.raises(error, match="timed out"):
        oracle.checked_process(tmp_path / "oracle.py", tmp_path, "test")


def test_oracle_crash_and_unavailable_protocol_remain_measurement_failures():
    result = run_artifact(oracle_tail="\nraise RuntimeError('oracle calibration crash')\n")
    assert result.returncode == 1, result.stderr
    assert "oracle calibration crash" in result.stderr
    result = run_artifact(stage_protocol=False)
    assert result.returncode != 0 and result.returncode != 10, result.stderr


def test_scenario_scope_and_supervised_binding():
    checks = SPEC["checks"]
    assert SPEC["max_turns"] == 73
    assert any(c["check"] == "verification_completed" and c["runner"] == "unittest" for c in checks)
    assert any(c["check"] == "skill_loaded" and c["skill"] == "python-engineering" for c in checks)
    check = next(c for c in checks if c["check"] == "command_exit_zero")
    assert check["failure_exit_code"] == 10
    assert check["command"] == "python -I -B oracle_protocol.py _python_package_oracle.py"
    assert set(check["writes_from"]) == {"oracle_protocol.py", "_python_package_oracle.py"}
    allowed = next(c["allowed"] for c in checks if c["check"] == "changes_within")
    assert "release-files.txt" in allowed and "tests/" in allowed
    assert "build_release.py" not in allowed and "clients/" not in allowed


@pytest.mark.parametrize("module", ["calculation", "preview"])
def test_forwarding_generator_must_preserve_borrowed_input_after_validation_failure(module):
    files = reference()
    filename = f"order_report/{module}.py"
    if module == "calculation":
        files[filename] = POLICY.replace(
            "    for line in lines:",
            "    def forwarded():\n        yield from lines\n    for line in forwarded():",
        )
    else:
        files[filename] = PREVIEW.replace(
            "    return calculation.total_from_lines(lines)",
            "    def forwarded():\n        yield from lines\n    return calculation.total_from_lines(forwarded())",
        )
    result = run_artifact(files)
    assert result.returncode == 10, result.stdout + result.stderr
    assert "borrowed generator" in result.stderr


@pytest.mark.parametrize("module", ["calculation", "preview"])
def test_forwarding_without_generator_close_delegation_preserves_contract(module):
    files = reference()
    filename = f"order_report/{module}.py"
    forwarder = "    def forwarded():\n        for line in lines:\n            yield line\n"
    if module == "calculation":
        files[filename] = POLICY.replace("    for line in lines:", forwarder + "    for line in forwarded():")
    else:
        files[filename] = PREVIEW.replace(
            "    return calculation.total_from_lines(lines)",
            forwarder + "    return calculation.total_from_lines(forwarded())",
        )
    result = run_artifact(files)
    assert result.returncode == 0, result.stdout + result.stderr
