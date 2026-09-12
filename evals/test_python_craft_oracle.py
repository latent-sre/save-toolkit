"""Calibrate the Python craft outcome oracles against correct and broken artifacts."""

from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap
import unittest

import yaml


ROOT = Path(__file__).resolve().parent
ORACLE = ROOT / "oracles/python-craft/check_contracts.py"
SCENARIOS = {
    "refactor": ("build-python-refactor-effects", "batch.py"),
    "generator": ("build-python-generator-lifetime", "records.py"),
    "migration": ("build-python-library-migration", "addresses.py"),
    "unchanged": ("build-python-leaves-correct-code", "predicates.py"),
    "modules": ("build-python-module-move", "reports.py"),
}
CORRECT = {
    "refactor": '''
        def process(values, *, limit=None, emit):
            if limit is not None and limit < 0:
                raise ValueError("negative limit")
            result = []
            for value in values:
                if limit is not None and len(result) >= limit:
                    break
                if value is None or value < 0:
                    continue
                emit(value)
                result.append(value * 2)
            return result
    ''',
    "generator": '''
        def iter_records(path):
            with open(path, encoding="utf-8") as source:
                for line in source:
                    yield line.strip()
    ''',
    "migration": '''
        from ipaddress import IPv4Address

        def parse_address(value):
            if not isinstance(value, str):
                raise ValueError("invalid address")
            try:
                IPv4Address(value)
            except ValueError as exc:
                raise ValueError("invalid address") from exc
            return value
    ''',
    "unchanged": '''
        def is_nonnegative(value: int) -> bool:
            return value >= 0
    ''',
}


def scenario(mode):
    name, _ = SCENARIOS[mode]
    return yaml.safe_load((ROOT / "build-scenarios" / (name + ".yaml")).read_text(encoding="utf-8"))


CORRECT["modules"] = {
    **scenario("modules")["fixture"]["files"],
    "formatting.py": scenario("modules")["fixture"]["files"]["reports.py"].split("\n\ndef render")[0],
    "reports.py": '''
        from formatting import format_label

        def render(names, *, prefix=""):
            return [format_label(name, prefix=prefix) for name in names]
    ''',
}


class PythonCraftOracleTests(unittest.TestCase):
    def run_artifact(self, mode, source):
        with tempfile.TemporaryDirectory() as tmp:
            files = source if isinstance(source, dict) else {SCENARIOS[mode][1]: source}
            for name, text in files.items():
                path = Path(tmp) / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(textwrap.dedent(text), encoding="utf-8")
            return subprocess.run(
                [sys.executable, "-I", "-B", str(ORACLE), mode], cwd=tmp,
                capture_output=True, text=True, timeout=15,
            )

    def test_correct_artifacts_pass_each_outcome_oracle(self):
        for mode, source in CORRECT.items():
            with self.subTest(mode=mode):
                result = self.run_artifact(mode, source)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("contract passed: " + mode, result.stdout)

    def test_seed_contracts_and_known_gaps_are_distinguished(self):
        for mode in SCENARIOS:
            source = scenario(mode)["fixture"]["files"]
            with self.subTest(mode=mode):
                result = self.run_artifact(mode, source)
                if mode in {"refactor", "unchanged"}:
                    self.assertEqual(result.returncode, 0, result.stderr)
                else:
                    self.assertNotEqual(result.returncode, 0)
                    diagnostic = {"generator": "I/O operation on closed file",
                                  "migration": "stdlib validator was not used",
                                  "modules": "No module named 'formatting'"}[mode]
                    self.assertIn(diagnostic, result.stderr)

    def test_generator_open_aliases_remain_valid(self):
        source = "from io import open\n" + textwrap.dedent(CORRECT["generator"])
        result = self.run_artifact("generator", source)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_generator_rejects_eager_materialization_before_first_yield(self):
        for expression in ("source.readlines()", "list(source)", "source.read().splitlines()"):
            source = CORRECT["generator"].replace("for line in source:", f"for line in {expression}:")
            with self.subTest(expression=expression):
                result = self.run_artifact("generator", source)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("source consumed eagerly", result.stderr)

    def test_generator_accepts_readline_and_bounded_chunk_streaming(self):
        chunked = r'''
            def iter_records(path):
                with open(path, encoding="utf-8") as source:
                    pending = ""
                    while chunk := source.read(4):
                        pending += chunk
                        while "\n" in pending:
                            line, pending = pending.split("\n", 1)
                            yield line.strip()
                    if pending:
                        yield pending.strip()
        '''
        for source in (CORRECT["generator"].replace("for line in source:",
                                                   'for line in iter(source.readline, ""):'), chunked):
            with self.subTest(source=source):
                result = self.run_artifact("generator", source)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_generated_comparisons_catch_adjacent_duplicate_loss(self):
        source = textwrap.dedent(CORRECT["refactor"]).replace(
            "        emit(value)",
            "        if result and result[-1] == value * 2:\n            continue\n        emit(value)",
        )
        result = self.run_artifact("refactor", source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Lists differ", result.stderr)

    def test_module_move_rejects_broken_public_lookup_and_circular_imports(self):
        correct = CORRECT["modules"]
        for name, changes, diagnostic in [
            ("legacy export lost", {"reports.py": correct["reports.py"].replace(
                "from formatting import format_label", "from formatting import format_label as _label"
            ).replace("format_label(name", "_label(name")}, "cannot import name 'format_label'"),
            ("circular dependency", {"formatting.py": "from reports import render\n" + correct["formatting.py"]},
             "partially initialized module"),
            ("public patch bypassed", {"reports.py": "import formatting\n" + textwrap.dedent(
                correct["reports.py"]).replace("[format_label(name", "[formatting.format_label(name")},
             "Lists differ"),
            ("implementation not moved", {"reports.py": scenario("modules")["fixture"]["files"]["reports.py"],
                                         "formatting.py": "from reports import format_label\n"},
             "implementation was not moved"),
            ("implementation duplicated", {"reports.py": scenario("modules")["fixture"]["files"]["reports.py"]},
             "new callable lost the existing alias registry"),
        ]:
            with self.subTest(name=name):
                result = self.run_artifact("modules", {**correct, **changes})
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(diagnostic, result.stderr)

    def test_dataclass_helpers_with_postponed_annotations_remain_valid(self):
        source = ("from __future__ import annotations\nfrom dataclasses import dataclass\n"
                  "@dataclass\nclass Options:\n    threshold: int = 0\n"
                  "def is_nonnegative(value):\n    return value >= Options().threshold\n")
        result = self.run_artifact("unchanged", source)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_oracles_reject_specific_semantic_regressions(self):
        mutants = [
            ("result type changed", "refactor", CORRECT["refactor"].replace(
                "value * 2", "value * 2.0"), "integer result type changed"),
            ("zero becomes unlimited", "refactor", CORRECT["refactor"].replace(
                "limit is not None and len(result)", "limit and len(result)"), "Lists differ"),
            ("missing callback", "refactor", CORRECT["refactor"].replace(
                "emit(value)", "pass"), "Lists differ"),
            ("callback value changed", "refactor", CORRECT["refactor"].replace(
                "emit(value)", "emit(value * 2)"), "Lists differ"),
            ("input mutated", "refactor", CORRECT["refactor"].replace(
                "return result", "values.clear(); return result"), "Lists differ"),
            ("input order changed", "refactor", CORRECT["refactor"].replace(
                "for value in values:", "for value in sorted(v for v in values if v is not None):"), "Lists differ"),
            ("duplicates dropped", "refactor", CORRECT["refactor"].replace(
                "for value in values:", "for value in dict.fromkeys(values):"), "Lists differ"),
            ("resource leaked", "generator", '''
                def iter_records(path):
                    source = open(path, encoding="utf-8")
                    for line in source:
                        yield line.strip()
            ''', "False is not true"),
            ("decode error hidden", "generator", CORRECT["generator"].replace(
                'encoding="utf-8"', 'encoding="utf-8", errors="replace"'), "UnicodeDecodeError not raised"),
            ("nonstring contract widened", "migration", '''
                from ipaddress import IPv4Address
                def parse_address(value):
                    try:
                        return str(IPv4Address(value))
                    except ValueError as exc:
                        raise ValueError("invalid address") from exc
            ''', "ValueError not raised"),
            ("wrong boundary", "unchanged", CORRECT["unchanged"].replace(
                "value >= 0", "value > 0"), "False is not True"),
        ]
        for name, mode, source, diagnostic in mutants:
            with self.subTest(name=name):
                result = self.run_artifact(mode, source)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(diagnostic, result.stderr)

    def test_refactor_preserves_keyword_only_calls_and_propagated_exception_identity(self):
        replaced_error = textwrap.dedent(CORRECT["refactor"]).replace(
            "def process(", "def original(") + textwrap.dedent('''
            def process(values, *, limit=None, emit):
                try:
                    return original(values, limit=limit, emit=emit)
                except RuntimeError as exc:
                    raise RuntimeError(str(exc)) from exc
        ''')
        for name, source, diagnostic in [
            ("positional options accepted", CORRECT["refactor"].replace(
                "*, limit=None, emit", "limit=None, emit=None"),
             "TypeError not raised"),
            ("callback exception replaced", replaced_error, "callback exception replaced"),
        ]:
            with self.subTest(name=name):
                result = self.run_artifact("refactor", source)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(diagnostic, result.stderr)

    def test_build_checks_bind_the_correct_oracle_and_unchanged_scope(self):
        for mode in SCENARIOS:
            spec = scenario(mode)
            with self.subTest(mode=mode):
                outcome = [check for check in spec["checks"] if "writes_from" in check]
                self.assertEqual(len(outcome), 1)
                self.assertEqual(outcome[0]["command"], "python -I -B _python_oracle.py " + mode)
                self.assertEqual(outcome[0]["writes_from"], {
                    "_python_oracle.py": "evals/oracles/python-craft/check_contracts.py",
                })
                self.assertTrue(any(check["check"] == "skill_loaded" and check["skill"] == "python-craft"
                                    for check in spec["checks"]))
        self.assertTrue(any(check["check"] == "no_workspace_changes"
                            for check in scenario("unchanged")["checks"]))


if __name__ == "__main__":
    unittest.main()
