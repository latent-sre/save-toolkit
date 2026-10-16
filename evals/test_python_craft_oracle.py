"""Calibrate the Python craft outcome oracles against correct and broken artifacts."""

import ast
import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

import pytest
from graders import exact_json
from probe_testkit import run_python, scenario_file, write_tree

ROOT = Path(__file__).resolve().parent
ORACLE = ROOT / "oracles/python-craft/check_contracts.py"
SCENARIOS = {
    "refactor": ("build-python-refactor-effects", "batch.py"),
    "generator": ("build-python-generator-lifetime", "records.py"),
    "migration": ("build-python-library-migration", "addresses.py"),
    "unchanged": ("build-python-leaves-correct-code", "predicates.py"),
    "modules": ("build-python-module-move", "reports.py"),
    "calculation": ("build-python-separate-calculation", "totals.py"),
    "policy": ("build-python-unify-policy", "policy.py"),
    "scoped": ("build-python-fix-stays-scoped", "fills.py"),
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
    "calculation": '''
        def total_from_lines(lines):
            return sum(int(line) for line in lines if line.strip())

        def total_from_file(path):
            with open(path, encoding="utf-8") as source:
                return total_from_lines(source)
    ''',
}


def scenario(mode):
    name, _ = SCENARIOS[mode]
    return scenario_file(ROOT / "build-scenarios" / (name + ".yaml"))


CORRECT["modules"] = {
    **scenario("modules")["fixture"]["files"],
    "formatting.py": scenario("modules")["fixture"]["files"]["reports.py"].split("\n\ndef render")[0],
    "reports.py": '''
        from formatting import format_label

        def render(names, *, prefix=""):
            return [format_label(name, prefix=prefix) for name in names]
    ''',
}


CORRECT["policy"] = {
    **scenario("policy")["fixture"]["files"],
    "policy.py": '''
        import re

        SKU = re.compile(r"[A-Z]{3}-\\d{4}")
        MAX_QUANTITY = 999


        def normalize_order(record):
            sku = record.get("sku")
            if not isinstance(sku, str) or not SKU.fullmatch(sku.strip().upper()):
                raise ValueError("invalid sku")
            quantity = record.get("quantity")
            if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= MAX_QUANTITY:
                raise ValueError("invalid quantity")
            unit_cents = record.get("unit_cents")
            if isinstance(unit_cents, bool) or not isinstance(unit_cents, int) or unit_cents < 0:
                raise ValueError("invalid price")
            return {"sku": sku.strip().upper(), "quantity": quantity, "unit_cents": unit_cents}
    ''',
    "api.py": '''
        import policy


        def submit(payload):
            return policy.normalize_order(payload)
    ''',
    "cli.py": '''
        import policy


        def run(line):
            fields = line.rstrip("\\n").split(",")
            if len(fields) != 3:
                raise ValueError("expected sku,quantity,unit_cents")
            sku, quantity, unit_cents = fields
            try:
                quantity, unit_cents = int(quantity), int(unit_cents)
            except ValueError:
                raise ValueError("expected integer quantity and unit_cents") from None
            return policy.normalize_order({"sku": sku, "quantity": quantity, "unit_cents": unit_cents})
    ''',
    "batch.py": '''
        import policy


        def load(rows):
            return [policy.normalize_order(row) for row in rows]
    ''',
    "legacy.py": '''
        from api import submit as submit_order
        from policy import MAX_QUANTITY
    ''',
    "tests/test_cli.py": scenario("policy")["fixture"]["files"]["tests/test_cli.py"].replace(
        'cli.run("abc-1234,100,250")', 'cli.run("abc-1234,1000,250")'),
}


CORRECT["scoped"] = scenario("scoped")["fixture"]["files"]["fills.py"].replace(
    "return ordered[-count:]", "return ordered[-count:] if count > 0 else []")


def run_artifact(mode, source, *child_args):
    with tempfile.TemporaryDirectory() as tmp:
        files = source if isinstance(source, dict) else {SCENARIOS[mode][1]: source}
        write_tree(Path(tmp), {name: textwrap.dedent(text) for name, text in files.items()})
        # Policy's aggregate command supervises six fresh import-order checks and a
        # fixture suite with its own 60s limit. Match command_exit_zero's 180s budget;
        # a single entrypoint still has the short bound used by the other calibrations.
        timeout = 180 if mode == "policy" and not child_args else 15
        return run_python(["-B", str(ORACLE), mode, *child_args], cwd=tmp, isolated=True, timeout=timeout)


def assert_rejected(mode, source, diagnostic, *child_args):
    """The oracle fails `source`, naming `diagnostic` unless it is None (any failure)."""
    result = run_artifact(mode, source, *child_args)
    assert result.returncode != 0
    if diagnostic is not None:
        assert diagnostic in result.stderr
    return result


class PythonCraftOracleTests(unittest.TestCase):
    def assert_grader_requires_each_decision(self, path, expected):
        fields = scenario_file(path)["graders"][0]["fields"]
        self.assertTrue(exact_json(json.dumps(expected), fields)[0])
        for key in expected:
            with self.subTest(case=key):
                self.assertFalse(exact_json(json.dumps(expected | {key: "incorrect"}), fields)[0])
                self.assertFalse(exact_json(json.dumps({k: v for k, v in expected.items() if k != key}), fields)[0])

    def test_refactoring_judgment_grader_rejects_each_wrong_decision(self):
        self.assert_grader_requires_each_decision(ROOT / "scenarios/python-refactoring-judgment.yaml", {
            "case_a": "share_policy", "case_b": "keep_separate",
            "case_c": "change_internal_and_callers", "case_d": "preserve_compatibility",
            "case_e": "no_change", "case_f": "coherent_stages",
            "case_g": "replace_custom_with_library", "case_h": "fix_established_defect",
            "case_i": "explain_without_changes", "case_j": "clarify_behavior",
            "case_k": "rewrite_implementation", "case_l": "preserve_effects_with_loop",
            "case_m": "name_independent_options", "case_n": "remove_empty_layers",
            "case_o": "keep_ordered_records", "case_p": "index_membership_stream_rows",
            "case_q": "separate_policy_from_transport"})

    def test_new_code_judgment_grader_rejects_wrong_or_missing_decisions(self):
        self.assert_grader_requires_each_decision(ROOT / "scenarios/python-new-code-judgment.yaml", {
            "case_a": "direct_synchronous_path", "case_b": "importable_core_cli_adapter",
            "case_c": "stream_aggregate_then_publish", "case_d": "clarify_failure_contract"})

    def assert_passes(self, mode, source):
        result = run_artifact(mode, source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("contract passed: " + mode, result.stdout)

    def test_correct_artifacts_pass_each_outcome_oracle(self):
        for mode, source in CORRECT.items():
            with self.subTest(mode=mode):
                self.assert_passes(mode, source)

    def test_seed_contracts_and_known_gaps_are_distinguished(self):
        diagnostics = {"generator": "I/O operation on closed file",
                       "migration": "stdlib validator was not used",
                       "modules": "No module named 'formatting'",
                       "calculation": "missing in-memory calculation boundary",
                       "policy": "No module named 'policy'",
                       "scoped": "latest_fills(fills, 0)"}
        for mode in SCENARIOS:
            source = scenario(mode)["fixture"]["files"]
            with self.subTest(mode=mode):
                if mode in {"refactor", "unchanged"}:
                    self.assert_passes(mode, source)
                else:
                    assert_rejected(mode, source, diagnostics[mode])

    def test_generator_open_aliases_remain_valid(self):
        self.assert_passes("generator", "from io import open\n" + textwrap.dedent(CORRECT["generator"]))

    def test_calculation_accepts_explicit_loop_without_prescribing_syntax(self):
        self.assert_passes("calculation", CORRECT["calculation"].replace(
            "return sum(int(line) for line in lines if line.strip())",
            "total = 0\n            for line in lines:\n                if line.strip():\n"
            "                    total += int(line)\n            return total",
        ))

    def test_calculation_observes_aliased_file_openers(self):
        for prefix in ("from io import open\n", "from builtins import open\n"):
            source = prefix + textwrap.dedent(CORRECT["calculation"])
            with self.subTest(prefix=prefix):
                self.assert_passes("calculation", source)
                source = source.replace("def total_from_lines(lines):",
                                        'def total_from_lines(lines):\n    open("unused", "w")')
                assert_rejected("calculation", source, "calculation attempted file I/O")

    def test_calculation_accepts_materialization_and_bare_reraise(self):
        for replacement in ("return total_from_lines(list(source))",
                            "try:\n            return total_from_lines(source)\n"
                            "        except ValueError:\n            raise"):
            source = textwrap.dedent(CORRECT["calculation"]).replace("return total_from_lines(source)", replacement)
            with self.subTest(replacement=replacement):
                self.assert_passes("calculation", source)

    def test_calculation_rejects_cosmetic_duplicate_and_behavior_regressions(self):
        seed = scenario("calculation")["fixture"]["files"]["totals.py"]
        source = textwrap.dedent(CORRECT["calculation"])
        duplicate = source.split("\ndef total_from_file")[0] + "\n" + seed
        for name, candidate, diagnostic in [
            ("comment only", seed + "\n# Clearer calculation\n", "missing in-memory calculation boundary"),
            ("duplicate rule", duplicate, "file entrypoint bypassed shared calculation"),
            ("prevalidates before delegation", source.replace("return total_from_lines(source)",
                'lines = list(source)\n        sum(int(line) for line in lines if line.strip())\n'
                '        return total_from_lines(lines)'), "file entrypoint bypassed shared calculation"),
            ("revalidates after delegation", source.replace("return total_from_lines(source)",
                'lines = list(source)\n        result = total_from_lines(lines)\n'
                '        sum(int(line) for line in lines if line.strip())\n        return result'),
                "accepted by replacement policy"),
            ("rejects string path", source.replace('open(path, encoding="utf-8")',
                                                 'path.open(encoding="utf-8")'), "has no attribute 'open'"),
            ("renames path keyword", source.replace("path", "filename"), "unexpected keyword argument 'path'"),
            ("drops signs", source.replace("int(line)", "abs(int(line))"), "!= 0"),
            ("float result", source.replace("sum(int(line)", "sum(float(line)"), "integer result type changed"),
            ("leaks file", source.replace('with open(path, encoding="utf-8") as source:\n        ',
                                         'source = open(path, encoding="utf-8")\n    '), "file handle leaked"),
            ("unnecessary I/O", source.replace("def total_from_lines(lines):",
                'def total_from_lines(lines):\n    open("unused")'), "calculation attempted file I/O"),
            ("replaces propagated error", source.replace("return total_from_lines(source)",
                'try:\n            return total_from_lines(source)\n        except RuntimeError as exc:\n'
                '            raise RuntimeError(str(exc))'), "calculation exception replaced"),
            ("replaces parse error", source.replace("return total_from_lines(source)",
                'try:\n            return total_from_lines(source)\n        except ValueError as exc:\n'
                '            raise ValueError(str(exc))'), "parse exception replaced"),
        ]:
            with self.subTest(name=name):
                assert_rejected("calculation", candidate, diagnostic)

    def test_generator_rejects_eager_materialization_before_first_yield(self):
        for expression in (
            "source.readlines()",
            "list(source)",
            "source.read().splitlines()",
            "source.read(path.stat().st_size).splitlines()",
            "source.readlines(path.stat().st_size * 10)",
        ):
            source = CORRECT["generator"].replace("for line in source:", f"for line in {expression}:")
            with self.subTest(expression=expression):
                assert_rejected("generator", source, "source consumed eagerly")

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
        sources = [CORRECT["generator"].replace("for line in source:",
                                                'for line in iter(source.readline, ""):')]
        sources.extend(chunked.replace("read(4)", f"read({size})") for size in (4, 64, 8192))
        for source in sources:
            with self.subTest(source=source):
                self.assert_passes("generator", source)

    def test_generated_comparisons_catch_adjacent_duplicate_loss(self):
        source = textwrap.dedent(CORRECT["refactor"]).replace(
            "        emit(value)",
            "        if result and result[-1] == value * 2:\n            continue\n        emit(value)",
        )
        assert_rejected("refactor", source, "Lists differ")

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
            ("render prefix made positional", {"reports.py": correct["reports.py"].replace(
                "def render(names, *, prefix", "def render(names, prefix"
            )}, "TypeError not raised"),
        ]:
            with self.subTest(name=name):
                assert_rejected("modules", {**correct, **changes}, diagnostic)

    def test_dataclass_helpers_with_postponed_annotations_remain_valid(self):
        self.assert_passes("unchanged", "from __future__ import annotations\nfrom dataclasses import dataclass\n"
                                        "@dataclass\nclass Options:\n    threshold: int = 0\n"
                                        "def is_nonnegative(value):\n    return value >= Options().threshold\n")

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
                assert_rejected(mode, source, diagnostic)

    def test_refactor_preserves_keyword_only_calls_and_propagated_exception_identity(self):
        replaced_error = textwrap.dedent(CORRECT["refactor"]).replace(
            "def process(", "def original(") + textwrap.dedent('''
            def process(values, *, limit=None, emit):
                try:
                    return original(values, limit=limit, emit=emit)
                except RuntimeError as exc:
                    raise RuntimeError(str(exc)) from exc
        ''')
        mutated_on_error = textwrap.dedent(CORRECT["refactor"]).replace(
            "def process(", "def original(") + textwrap.dedent('''
            def process(values, *, limit=None, emit):
                try:
                    return original(values, limit=limit, emit=emit)
                except RuntimeError:
                    values.clear()
                    raise
        ''')
        for name, source, diagnostic in [
            ("positional limit accepted", CORRECT["refactor"].replace(
                "*, limit=None, emit", "limit=None, *, emit"),
             "TypeError not raised"),
            ("positional emit accepted", CORRECT["refactor"].replace(
                "*, limit=None, emit", "emit, *, limit=None"),
             "TypeError not raised"),
            ("callback exception replaced", replaced_error, "callback exception replaced"),
            ("input mutated on callback failure", mutated_on_error, "Lists differ"),
        ]:
            with self.subTest(name=name):
                assert_rejected("refactor", source, diagnostic)

    def test_policy_seed_suite_is_green_before_the_refactor(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_tree(Path(tmp), scenario("policy")["fixture"]["files"])
            result = run_python(["-B", "-m", "unittest", "discover", "-s", "tests", "-t", "."], cwd=tmp, isolated=True,
                                timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Ran 10 tests", result.stderr)

    def test_policy_accepts_value_error_subclasses(self):
        correct = CORRECT["policy"]
        source = ('class PolicyError(ValueError):\n    pass\n\n' +
                  textwrap.dedent(correct["policy.py"]).replace("raise ValueError(", "raise PolicyError("))
        self.assert_passes("policy", correct | {"policy.py": source})

    def test_policy_rejects_returned_errors_and_wrong_exception_contracts(self):
        correct = CORRECT["policy"]
        source = textwrap.dedent(correct["policy.py"])
        for message in ("invalid sku", "invalid quantity", "invalid price"):
            original = f'raise ValueError("{message}")'
            for behavior, replacement, diagnostic in (
                ("returned error text", f'return "{message}"', "disagrees with the specification"),
                ("wrong exception class", f'raise TypeError("{message}")', None),
                ("wrong exception message", 'raise ValueError("other error")', "disagrees with the specification"),
            ):
                with self.subTest(message=message, behavior=behavior):
                    assert_rejected("policy", correct | {"policy.py": source.replace(original, replacement)}, diagnostic)

    def test_scoped_fix_rejects_unrequested_refactors_and_fix_regressions(self):
        correct = CORRECT["scoped"]
        start, end = correct.index("def filled_notional"), correct.index("def latest_fills")
        for name, source, diagnostic in [
            ("duplication folded into a helper", correct[:start] + '''def _notional(fills, status):
    return sum((Decimal(f["qty"]) * Decimal(f["price"]) for f in fills if f["status"] == status), Decimal("0"))


def filled_notional(fills):
    return _notional(fills, "FILLED")


def rejected_notional(fills):
    return _notional(fills, "REJECTED")


''' + correct[end:], "filled_notional changed although the fix did not need it"),
            ("unrelated annotations added", correct.replace(
                "def rejected_notional(fills):", "def rejected_notional(fills: list[dict]) -> Decimal:"),
             "rejected_notional changed although the fix did not need it"),
            ("length arithmetic wraps", correct.replace(
                "return ordered[-count:] if count > 0 else []", "return ordered[len(ordered) - count:]"),
             "latest_fills(fills, 5)"),
            ("newest first", correct.replace(
                "return ordered[-count:] if count > 0 else []",
                "return sorted(fills, key=lambda fill: fill[\"ts\"], reverse=True)[:count]"),
             "latest_fills(fills, 2)"),
            ("input sorted in place", correct.replace(
                "ordered = sorted(fills, key=lambda fill: fill[\"ts\"])",
                "fills.sort(key=lambda fill: fill[\"ts\"])\n    ordered = fills"),
             "input mutated"),
        ]:
            with self.subTest(name=name):
                self.assertNotEqual(source, correct)
                assert_rejected("scoped", source, diagnostic)

    def test_build_checks_bind_the_correct_oracle_and_unchanged_scope(self):
        for mode in SCENARIOS:
            spec = scenario(mode)
            with self.subTest(mode=mode):
                outcome = [check for check in spec["checks"] if "writes_from" in check]
                self.assertEqual(len(outcome), 1)
                self.assertEqual(outcome[0]["command"], "python -I -B oracle_protocol.py _python_oracle.py " + mode)
                self.assertEqual(outcome[0]["writes_from"], {
                    "_python_oracle.py": "evals/oracles/python-craft/check_contracts.py",
                    "oracle_protocol.py": "evals/oracles/oracle_protocol.py",
                })
                self.assertTrue(any(check["check"] == "skill_loaded" and check["skill"] == "python-craft"
                                    for check in spec["checks"]))
        self.assertTrue(any(check["check"] == "no_workspace_changes"
                            for check in scenario("unchanged")["checks"]))


def _policy_unification_cases():
    correct = CORRECT["policy"]
    seed = scenario("policy")["fixture"]["files"]
    policy_source = textwrap.dedent(correct["policy.py"])
    return [
        ("owner keeps the drifted limit", {"policy.py": policy_source.replace("MAX_QUANTITY = 999", "MAX_QUANTITY = 99")},
         "quantity limit drifted"),
        ("owner skips the strip", {"policy.py": policy_source.replace("sku.strip().upper()", "sku.upper()")},
         "disagrees with the specification"),
        ("api keeps its own rules before delegating", {"api.py": "import policy\n" + seed["api.py"].replace(
            'return {"sku": sku, "quantity": quantity, "unit_cents": unit_cents}',
            "return policy.normalize_order(payload)")},
         "api.submit bypassed the shared policy or kept its own rules"),
        ("batch copies the rules instead of delegating", {"batch.py": seed["batch.py"].replace(
            "SKU.match(sku.upper())", "SKU.match(sku.strip().upper())").replace(
            '"sku": sku.upper()', '"sku": sku.strip().upper()')},
         "batch.load bypassed the shared policy or kept its own rules"),
        ("bound-name import defeats the patch seam", {"api.py": '''
                from policy import normalize_order


                def submit(payload):
                    return normalize_order(payload)
            '''}, "api.submit bypassed the shared policy or kept its own rules"),
        ("legacy wraps instead of re-exporting", {"legacy.py": '''
                import api
                from policy import MAX_QUANTITY


                def submit_order(payload):
                    return api.submit(payload)
            '''}, "legacy name rebound"),
        ("policy exception replaced by a copy", {"api.py": '''
                import policy


                def submit(payload):
                    try:
                        return policy.normalize_order(payload)
                    except ValueError as exc:
                        raise ValueError(str(exc)) from None
            '''}, "policy exception replaced"),
        ("input mutated", {"api.py": '''
                import policy


                def submit(payload):
                    if isinstance(payload.get("sku"), str):
                        payload["sku"] = payload["sku"].strip().upper()
                    return policy.normalize_order(payload)
            '''}, "input mutated"),
        ("circular import", {"policy.py": "from api import submit\n" + policy_source}, "partially initialized module"),
        ("stale drift test kept", {"tests/test_cli.py": seed["tests/test_cli.py"]}, "fixture test suite failed"),
        ("drift test deleted instead of updated", {"tests/test_cli.py": "import unittest\n"},
         "candidate tests did not reject malformed CLI line accepted"),
    ]


@pytest.mark.parametrize("code", (0, 2))
@pytest.mark.parametrize("phase", ("import", "api/iteration"))
@pytest.mark.parametrize("mode,child_args", [
    pytest.param(mode, (), id=mode) for mode in CORRECT
] + [
    pytest.param(mode, (child,), id=f"{mode}-{child}")
    for mode, children in {"modules": ("reports", "formatting"),
                           "policy": ("policy", "api", "cli", "batch", "legacy", "registry")}.items()
    for child in children
])
def test_oracles_reject_candidate_system_exit_before_completion(mode, child_args, phase, code):
    api_names = {"refactor": "process", "generator": "iter_records", "migration": "parse_address",
                 "unchanged": "is_nonnegative", "modules": "render", "calculation": "total_from_lines",
                 "policy": "normalize_order", "scoped": "latest_fills"}
    original = CORRECT[mode]
    files = dict(original) if isinstance(original, dict) else {SCENARIOS[mode][1]: original}
    filename = SCENARIOS[mode][1]
    source = textwrap.dedent(files[filename])
    signature = next(line for line in source.splitlines() if line.startswith("def " + api_names[mode] + "("))
    # iter_records remains a generator: its exit occurs when iteration starts.
    mutant = (f"raise SystemExit({code})\n" + source if phase == "import" else
              source.replace(signature, signature + f"\n    raise SystemExit({code})", 1))
    # Child cases exercise fresh script entrypoints as well as their aggregate command.
    result = assert_rejected(mode, files | {filename: mutant},
                             "candidate exited before contract checks completed", *child_args)
    assert "contract passed: " + mode not in result.stdout


@pytest.mark.parametrize("changes,diagnostic", [
    pytest.param(changes, diagnostic, id=name) for name, changes, diagnostic in _policy_unification_cases()
])
def test_policy_unification_rejects_partial_ownership_and_lost_consumers(changes, diagnostic):
    assert_rejected("policy", {**CORRECT["policy"], **changes}, diagnostic)


def _policy_with_empty_tests(names=None):
    files = dict(CORRECT["policy"])
    erased = 0
    for name, source in files.items():
        if name.startswith("tests/test_") and name.endswith(".py"):
            tree = ast.parse(textwrap.dedent(source))
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.FunctionDef)
                    and node.name.startswith("test_")
                    and (names is None or node.name in names)
                ):
                    node.body = [ast.Pass()]
                    erased += 1
            files[name] = ast.unparse(ast.fix_missing_locations(tree))
    return files, erased


def test_policy_rejects_suite_with_all_test_bodies_erased():
    files, erased = _policy_with_empty_tests()
    assert erased == 10
    assert_rejected("policy", files, "candidate tests did not reject SKU normalization lost")


@pytest.mark.parametrize(
    "names,regression",
    [
        ({"test_normalizes_sku_and_keeps_values", "test_parses_one_line"}, "SKU normalization lost"),
        ({"test_rejects_quantity_above_limit"}, "quantity upper bound removed"),
        ({"test_rejects_bool_quantity"}, "boolean quantity accepted"),
        ({"test_rejects_negative_price"}, "negative price accepted"),
        ({"test_reports_malformed_line"}, "malformed CLI line accepted"),
        ({"test_reports_non_integer_fields"}, "noninteger CLI fields accepted"),
        ({"test_keeps_row_order"}, "batch row order reversed"),
        ({"test_empty_input"}, "empty batch result changed"),
    ],
)
def test_policy_rejects_suites_insensitive_to_each_named_regression(names, regression):
    files, erased = _policy_with_empty_tests(names)
    assert erased > 0
    assert_rejected("policy", files, "candidate tests did not reject " + regression)


@pytest.mark.parametrize(
    "after_acceptance,diagnostic",
    [
        ("raise RuntimeError('regression runtime error')", "candidate tests did not reject boolean quantity accepted"),
        ("import missing_policy_dependency", "candidate tests did not reject boolean quantity accepted"),
        ("self.skipTest('regression skip')", "candidate tests did not reject boolean quantity accepted"),
        ("raise SystemExit(0)", "candidate tests did not reject boolean quantity accepted"),
        ("import os; os._exit(0)", "candidate tests exited without results"),
    ],
)
def test_policy_does_not_count_runtime_errors_skips_or_exits_as_regression_assertions(after_acceptance, diagnostic):
    files = dict(CORRECT["policy"])
    source = textwrap.dedent(files["tests/test_api.py"])
    call = 'api.submit({"sku": "ABC-1234", "quantity": True, "unit_cents": 1})'
    files["tests/test_api.py"] = source.replace(call, call + "\n            " + after_acceptance, 1)
    result = _run_supervised_policy(files)
    assert result.returncode == 10, result.stderr
    assert diagnostic in result.stderr


def test_policy_accepts_reorganized_tests_and_alternative_assertion_syntax():
    files = dict(CORRECT["policy"])
    combined = []
    for index, name in enumerate(("tests/test_api.py", "tests/test_cli.py", "tests/test_batch.py")):
        tree = ast.parse(textwrap.dedent(files[name]))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                node.name = f"RewiredTests{index}"
            elif isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                node.name = "test_reorganized_" + node.name.removeprefix("test_")
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                for position, statement in enumerate(node.body):
                    if (
                        isinstance(statement, ast.Expr)
                        and isinstance(statement.value, ast.Call)
                        and isinstance(statement.value.func, ast.Attribute)
                        and statement.value.func.attr == "assertEqual"
                    ):
                        left, right = statement.value.args
                        node.body[position] = ast.Assert(
                            test=ast.Compare(left=left, ops=[ast.Eq()], comparators=[right]), msg=None
                        )
        combined.append(ast.unparse(ast.fix_missing_locations(tree)))
        files[name] = "import unittest\n"
    files["tests/test_reorganized.py"] = "\n".join(combined)
    # A different correct implementation remains eligible as well as different
    # test names, placement and assertion spelling.
    files["batch.py"] = """
        import policy
        def load(rows):
            result = []
            for row in rows:
                result.append(policy.normalize_order(row))
            return result
    """
    result = run_artifact("policy", files)
    assert result.returncode == 0, result.stderr


def test_policy_accepts_assertions_regrouped_into_three_test_methods():
    files = dict(CORRECT["policy"])
    methods = 0
    for name in ("tests/test_api.py", "tests/test_cli.py", "tests/test_batch.py"):
        tree = ast.parse(textwrap.dedent(files[name]))
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                grouped = []
                tests = [
                    method
                    for method in node.body
                    if isinstance(method, ast.FunctionDef) and method.name.startswith("test_")
                ]
                for method in tests:
                    grouped.append(
                        ast.With(
                            items=[
                                ast.withitem(
                                    context_expr=ast.Call(
                                        func=ast.Attribute(
                                            value=ast.Name(id="self", ctx=ast.Load()), attr="subTest", ctx=ast.Load()
                                        ),
                                        args=[],
                                        keywords=[ast.keyword(arg="case", value=ast.Constant(value=method.name))],
                                    )
                                )
                            ],
                            body=method.body,
                        )
                    )
                tests[0].name = "test_grouped_contracts"
                tests[0].body = grouped
                node.body = [tests[0]]
                methods += 1
        files[name] = ast.unparse(ast.fix_missing_locations(tree))
    assert methods == 3
    result = run_artifact("policy", files)
    assert result.returncode == 0, result.stderr


def test_policy_regression_replays_reach_cli_tests_using_subprocess_imports():
    files = dict(CORRECT["policy"])
    files["tests/test_cli.py"] = textwrap.dedent(files["tests/test_cli.py"]) + '''
import json
import subprocess
import sys

def run_in_process(line):
    script = """
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path.cwd()))
import cli
try:
    value = {"value": cli.run(sys.argv[1])}
except ValueError as exc:
    value = {"error": str(exc)}
print(json.dumps(value))
"""
    result = subprocess.run([sys.executable, "-I", "-B", "-c", script, line],
                            capture_output=True, text=True, check=True, timeout=5)
    value = json.loads(result.stdout)
    if "error" in value:
        raise ValueError(value["error"])
    return value["value"]

cli.run = run_in_process
'''
    result = run_artifact("policy", files)
    assert result.returncode == 0, result.stderr


def _run_supervised_policy(files, oracle_source=None):
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        candidate = root / "candidate"
        write_tree(candidate, {name: textwrap.dedent(source) for name, source in files.items()})
        oracle = ORACLE
        if oracle_source is not None:
            # Keep oracle-owned faults outside the candidate working directory.
            oracle = root / "check_policy.py"
            oracle.write_text(oracle_source, encoding="utf-8")
        return run_python(
            ["-B", str(ROOT / "oracles/oracle_protocol.py"), str(oracle), "policy"],
            cwd=candidate,
            isolated=True,
            timeout=180,
        )


def _oracle_copy(*replacements):
    """The policy oracle's source, runnable from a temporary path, with each (old, new) applied once."""
    source = ORACLE.read_text(encoding="utf-8")
    for old, new in (("sys.path.insert(0, str(Path(__file__).resolve().parent.parent))",
                      f"sys.path.insert(0, {str(ROOT / 'oracles')!r})"), *replacements):
        assert source.count(old) == 1, old
        source = source.replace(old, new)
    return source


@pytest.mark.parametrize(
    "test_body,diagnostic",
    [
        ("self.fail('candidate assertion')", "fixture test suite failed"),
        ("raise RuntimeError('candidate runtime error')", "fixture test suite failed"),
        ("self.skipTest('candidate skip')", "fixture tests did not all pass normally"),
        ("raise SystemExit(0)", "fixture test suite failed"),
        ("import os; os._exit(0)", "candidate tests exited without results"),
        ("import os; os._exit(2)", "candidate test runner failed"),
        ("import time; time.sleep(30)", "candidate test suite timed out before results"),
    ],
)
def test_policy_supervision_rejects_candidate_test_failures_and_early_exits(test_body, diagnostic):
    files = dict(CORRECT["policy"])
    files["tests/test_failure.py"] = (
        "import unittest\nclass FailureTests(unittest.TestCase):\n"
        "    def test_candidate(self):\n        " + test_body + "\n"
    )
    # The oracle's 15 s replay limit is waiting, not evidence; a short limit reaches the same branch.
    oracle_source = _oracle_copy(("text=True, timeout=15)", "text=True, timeout=3)")) if "sleep" in test_body else None
    result = _run_supervised_policy(files, oracle_source)
    assert result.returncode == 10, result.stderr
    assert diagnostic in result.stderr


def test_policy_supervision_passes_complete_assessment_without_mutating_candidate():
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        write_tree(root, {name: textwrap.dedent(source) for name, source in CORRECT["policy"].items()})
        before = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
        result = run_python(
            ["-B", str(ROOT / "oracles/oracle_protocol.py"), str(ORACLE), "policy"],
            cwd=root,
            isolated=True,
            timeout=180,
        )
        after = {path.relative_to(root): path.read_bytes() for path in root.rglob("*") if path.is_file()}
    assert result.returncode == 0, result.stderr
    assert before == after


@pytest.mark.parametrize(
    "fault,code,diagnostic",
    [
        ("raise RuntimeError('oracle crash')", 1, "oracle crash"),
        ("import os; os._exit(0)", 1, "INCONCLUSIVE: oracle process stopped without assessment"),
        ("raise SystemExit(3)", 3, ""),
    ],
)
def test_policy_supervision_keeps_oracle_crash_and_unavailable_outcomes_distinct(fault, code, diagnostic):
    # Exercise the real policy completion path, replacing only the oracle-owned
    # replay entrypoint so its internal faults cannot become candidate failures.
    source = _oracle_copy(("def policy_test_coverage():", "def policy_test_coverage():\n    " + fault))
    result = _run_supervised_policy(CORRECT["policy"], source)
    assert result.returncode == code, result.stderr
    assert diagnostic in result.stderr


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, *sys.argv[1:]]))
