"""Offline calibration: real artifacts and exits, no model or external services."""

import tempfile
import unittest
from pathlib import Path

from probe_testkit import assert_completion, completion_env, run_python, scenario_file, write_tree

ROOT = Path(__file__).resolve().parent
ORACLE = ROOT / "oracles/python-craft/check_new_code.py"
SPEC = ROOT / "build-scenarios/build-python-new-streaming-cli.yaml"
API = '''
def summarize(rows):
    counts = dict.fromkeys(("success", "failure", "skipped"), 0)
    for index, row in enumerate(rows, 1):
        if not isinstance(row, Mapping) or not isinstance(row.get("status"), str) or row["status"] not in counts:
            raise ValueError(f"invalid record {index}")
        counts[row["status"]] += 1
    return counts
'''
COUNTER_API = '''
def summarize(rows):
    def statuses():
        for index, row in enumerate(rows, 1):
            if not isinstance(row, Mapping) or not isinstance(row.get("status"), str) or row["status"] not in CATEGORIES:
                raise ValueError(f"invalid record {index}")
            yield row["status"]
    counted = Counter(statuses())
    return {status: counted[status] for status in CATEGORIES}
'''
SHELL = '''from collections.abc import Mapping
from collections import Counter
import contextlib
import json
import sys
CATEGORIES = ("success", "failure", "skipped")
{api}
def reject_constant(value):
    raise ValueError("nonstandard JSON constant")

def parsed(source):
    for index, line in enumerate(source, 1):
        try:
            yield json.loads(line, parse_constant=reject_constant)
        except ValueError as exc:
            raise ValueError(f"invalid JSON record {{index}}") from exc

def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("expected one input", file=sys.stderr)
        return 2
    try:
        source = contextlib.nullcontext(sys.stdin) if argv[0] == "-" else open(argv[0], encoding="utf-8")
        with source as stream:
            result = summarize(parsed(stream))
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
'''
LEGACY_SOURCE = SHELL.format(api=API)
STDIN_HELPER = '''
@contextlib.contextmanager
def stdin_source():
    if not hasattr(sys.stdin, "buffer"):
        yield sys.stdin
        return
    text = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8")
    try:
        yield text
    finally:
        text.detach()

'''
SHELL = SHELL.replace("import json\n", "import json\nimport io\n").replace(
    "def main(", STDIN_HELPER + "def main(").replace("contextlib.nullcontext(sys.stdin)", "stdin_source()")
CORRECT = SHELL.format(api=API)
SELF_TEST = '''import unittest
import outcome_counts
class CountTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(outcome_counts.summarize([]), {"success": 0, "failure": 0, "skipped": 0})
    def test_duplicate(self):
        self.assertEqual(outcome_counts.summarize([{"status": "success"}] * 2)["success"], 2)
'''


class NewCodeProbeTests(unittest.TestCase):
    def run_artifact(self, source, tests=SELF_TEST):
        spec = scenario_file(SPEC)
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            write_tree(work, spec["fixture"]["files"])
            (work / "outcome_counts.py").write_text(source, encoding="utf-8")
            (work / "tests").mkdir()
            (work / "tests/__init__.py").write_text("", encoding="utf-8")
            (work / "tests/test_outcome_counts.py").write_text(tests, encoding="utf-8")
            (work / "_python_new_oracle.py").write_bytes(ORACLE.read_bytes())
            return assert_completion(run_python(["-B", "_python_new_oracle.py"], cwd=work, isolated=True,
                                                env=completion_env(), encoding="utf-8", timeout=45))

    def assert_passes(self, source):
        result = self.run_artifact(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("public contracts passed", result.stdout)

    def assert_fails(self, source, diagnostic, tests=SELF_TEST):
        result = self.run_artifact(source, tests)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn(diagnostic, result.stderr)

    def test_loop_and_generator_counter_implementations_pass(self):
        for source in (CORRECT, SHELL.format(api=COUNTER_API)):
            with self.subTest(source=source):
                self.assert_passes(source)

    def test_old_locale_stdin_artifact_fails_utf8_contract(self):
        # Force the formerly implicit stdin decoder to Latin-1 to reproduce the
        # defect across hosts, rather than depending on Windows' ambient cp1252.
        self.assert_fails(LEGACY_SOURCE.replace('if __name__ == "__main__":',
                                                'if __name__ == "__main__":\n    sys.stdin.reconfigure(encoding="latin-1")'),
                          "invalid UTF-8 stdin: failure exit status")

    def test_candidate_exits_cannot_skip_contract_checks(self):
        for code in (0, 3):
            for phase, source in (
                ("import", f"raise SystemExit({code})\n"),
                ("API", CORRECT.replace("def summarize(rows):", f"def summarize(rows):\n    raise SystemExit({code})")),
            ):
                with self.subTest(phase=phase, code=code):
                    result = self.run_artifact(source)
                    self.assertEqual(result.returncode, 1, result.stdout)
                    self.assertIn("candidate exited before contract checks completed", result.stderr)

    def test_retained_open_aliases_and_path_open_pass(self):
        for imported, expression in (
            ("from builtins import open as file_open", "file_open(argv[0], encoding=\"utf-8\")"),
            ("from io import open as file_open", "file_open(argv[0], encoding=\"utf-8\")"),
            ("from pathlib import Path", "Path(argv[0]).open(encoding=\"utf-8\")"),
        ):
            with self.subTest(imported=imported):
                self.assert_passes(imported + "\n" + CORRECT.replace('open(argv[0], encoding="utf-8")', expression))

    def test_compact_stream_retention_fails(self):
        api = API.replace("    for index, row", "    retained = bytearray()\n    for index, row").replace(
            '        counts[row["status"]] += 1', '        retained.append(CATEGORIES.index(row["status"]))').replace(
            "    return counts", "    return {status: retained.count(index) for index, status in enumerate(CATEGORIES)}")
        cases = (
            (SHELL.format(api=api), "summarize retained the stream"),
            (CORRECT.replace("    for index, line", "    retained = bytearray()\n    for index, line").replace(
                "        try:\n            yield", "        retained.append(0)\n        try:\n            yield"), "CLI retained the stream"),
        )
        for source, diagnostic in cases:
            with self.subTest(diagnostic=diagnostic):
                self.assert_fails(source, diagnostic)

    def test_large_constant_buffers_pass(self):
        self.assert_passes(CORRECT.replace("def summarize(rows):", "def summarize(rows):\n    buffer = bytearray(2_000_000)"))

    def test_binary_and_chunked_file_readers_pass(self):
        binary = CORRECT.replace('open(argv[0], encoding="utf-8")',
                                 'io.TextIOWrapper(open(argv[0], "rb"), encoding="utf-8")')
        chunked = CORRECT.replace("def parsed(source):", """def lines(source):
    pending = ""
    while chunk := source.read(4096):
        pending += chunk
        while "\\n" in pending:
            line, pending = pending.split("\\n", 1)
            yield line
    if pending:
        yield pending

def parsed(source):""").replace("enumerate(source, 1)", "enumerate(lines(source), 1)")
        for source in (binary, chunked, chunked.replace("4096", "1_048_576")):
            with self.subTest(source=source):
                self.assert_passes(source)

    def test_retained_open_aliases_still_expose_import_io_and_leaks(self):
        for library in ("builtins", "io"):
            alias = f"from {library} import open as file_open\n" + CORRECT.replace(
                'open(argv[0], encoding="utf-8")', 'file_open(argv[0], encoding="utf-8")')
            for source, diagnostic in (
                (alias + '\nfile_open("outcome_counts.py")\n', "import performed file I/O"),
                (alias.replace('else file_open(argv[0], encoding="utf-8")',
                               'else contextlib.nullcontext(file_open(argv[0], encoding="utf-8"))'),
                 "owned file handle leaked"),
            ):
                with self.subTest(library=library, diagnostic=diagnostic):
                    self.assert_fails(source, diagnostic)

    def test_file_text_wrapper_buffer_reader_passes(self):
        self.assert_passes("import codecs\n" + CORRECT.replace(
            "result = summarize(parsed(stream))",
            'result = summarize(parsed(codecs.iterdecode(stream.buffer, "utf-8") if argv[0] != "-" else stream))'))

    def test_owned_file_must_close_after_late_read_failure(self):
        wrapper = '''
@contextlib.contextmanager
def file_source(path):
    stream = open(path, encoding="utf-8")
    try:
        yield stream
    except OSError:
        raise
    except BaseException:
        stream.close()
        raise
    else:
        stream.close()

'''
        source = CORRECT.replace("def main(", wrapper + "def main(").replace(
            'else open(argv[0], encoding="utf-8")', "else file_source(argv[0])")
        self.assert_fails(source, "owned file handle leaked on read failure")

    def test_owned_file_late_read_errors_cannot_be_swallowed(self):
        source = CORRECT.replace("    for index, line in enumerate(source, 1):", """    try:
        yield from parsed_inner(source)
    except OSError:
        if source is sys.stdin:
            raise

def parsed_inner(source):
    for index, line in enumerate(source, 1):""")
        self.assert_fails(source, "file read error: failure exit status")

    def test_semantic_mutants_fail_for_the_named_defect(self):
        # Each mutation is independently executed in a fresh external temporary workspace.
        cases = [
            ("materializes rows", CORRECT.replace("enumerate(rows, 1)", "enumerate(list(rows), 1)"), "summarize retained the stream"),
            ("source error swallowed", CORRECT.replace("def summarize(rows):", "def real_summary(rows):").replace(
                "def reject_constant(", 'def summarize(rows):\n    try:\n        return real_summary(rows)\n    except OSError:\n        return dict.fromkeys(CATEGORIES, 0)\n\ndef reject_constant('), "OSError not raised"),
            ("source error replaced", CORRECT.replace("def summarize(rows):", "def real_summary(rows):").replace(
                "def reject_constant(", 'def summarize(rows):\n    try:\n        return real_summary(rows)\n    except OSError as exc:\n        raise OSError(str(exc))\n\ndef reject_constant('), "source iteration exception replaced"),
            ("stdin locale decoding", CORRECT.replace('text = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8")',
                                                    'text = io.TextIOWrapper(sys.stdin.buffer, encoding="latin-1")'), "invalid UTF-8 stdin: failure exit status"),
            ("ignores invalid row", CORRECT.replace('raise ValueError(f"invalid record {index}")', "continue"), "invalid row or record index ignored"),
            ("missing zeros", CORRECT.replace("    return counts", "    return {k: v for k, v in counts.items() if v}"), "count policy disagrees"),
            ("duplicate loss", CORRECT.replace('counts[row["status"]] += 1', 'counts[row["status"]] = 1'), "count policy disagrees"),
            ("closes borrowed input", CORRECT.replace("    return counts", "    if hasattr(rows, 'close'):\n        rows.close()\n    return counts"), "borrowed input closed"),
            ("wrong invalid index", CORRECT.replace("enumerate(rows, 1)", "enumerate(rows, 0)"), "invalid row or record index ignored"),
            ("mutates input", CORRECT.replace('counts[row["status"]] += 1', 'counts[row.pop("status")] += 1'), "input rows mutated"),
            ("copied CLI policy", CORRECT.replace("result = summarize(", "result = copied(").replace("def main(", API.replace("def summarize(", "def copied(") + "\ndef main("), "shared summarize policy"),
            ("CLI materializes parsed rows", CORRECT.replace("result = summarize(parsed(stream))", "result = summarize(list(parsed(stream)))"), "CLI retained the stream"),
            ("CLI keeps validation before delegation", CORRECT.replace("yield json.loads(line, parse_constant=reject_constant)", "row = json.loads(line, parse_constant=reject_constant)\n            if not isinstance(row, Mapping) or not isinstance(row.get('status'), str) or row['status'] not in CATEGORIES:\n                raise ValueError('bad status')\n            yield row"), "shared summarize policy"),
            ("early stdout", CORRECT.replace("    try:\n        source", "    print('{}')\n    try:\n        source"), "Extra data"),
            ("partial stdout on failure", CORRECT.replace("        print(str(exc), file=sys.stderr)", "        print('{}')\n        print(str(exc), file=sys.stderr)"), "partial stdout"),
            ("read errors swallowed", CORRECT.replace("    except (ValueError, OSError) as exc:", "    except OSError:\n        print(json.dumps(dict.fromkeys(CATEGORIES, 0)))\n        return 0\n    except ValueError as exc:"), "file open error: failure exit status"),
            ("late read errors swallowed", CORRECT.replace("    for index, line in enumerate(source, 1):", "    try:\n        yield from parsed_inner(source)\n    except OSError:\n        return\n\ndef parsed_inner(source):\n    for index, line in enumerate(source, 1):"), "read error: failure exit status"),
            ("borrowed stdin closed", CORRECT.replace("yield sys.stdin\n        return",
                "try:\n            yield sys.stdin\n        finally:\n            sys.stdin.close()\n        return"), "borrowed stdin closed"),
            ("nonstandard JSON accepted", CORRECT.replace("json.loads(line, parse_constant=reject_constant)", "json.loads(line)"), "late invalid JSON Lines: failure exit status"),
            ("blank lines ignored", CORRECT.replace("        try:\n            yield", "        if not line.strip():\n            continue\n        try:\n            yield"), "late invalid JSON Lines: failure exit status"),
            ("broken CLI entrypoint", CORRECT.replace("    raise SystemExit(main())", "    pass"), "Expecting value"),
            ("import output", CORRECT + "\nprint('import side effect')\n", "import wrote output"),
            ("import reads stdin", CORRECT + "\nsys.stdin.read()\n", "import read stdin"),
            ("file handle leaked", CORRECT.replace('else open(argv[0], encoding="utf-8")', 'else contextlib.nullcontext(open(argv[0], encoding="utf-8"))'), "owned file handle leaked"),
        ]
        for name, source, diagnostic in cases:
            with self.subTest(name=name):
                self.assertNotEqual(source, CORRECT)
                self.assert_fails(source, diagnostic)

    def test_self_tests_must_execute_and_pass(self):
        for tests, diagnostic in [("import unittest\n", "no self-tests executed"),
                                  (SELF_TEST.replace('"success": 0', '"success": 99'), "candidate self-tests failed")]:
            with self.subTest(tests=tests):
                self.assert_fails(CORRECT, diagnostic, tests)

    def test_scenario_binds_scope_oracle_and_trace_verification(self):
        spec = scenario_file(SPEC)
        self.assertEqual(spec["fixture"]["files"], {".gitignore": "__pycache__/\n"})
        checks = spec["checks"]
        outcome = [c for c in checks if "writes_from" in c]
        self.assertEqual(len(outcome), 1)
        self.assertEqual(outcome[0]["command"], "python -I -B _python_new_oracle.py")
        self.assertEqual(outcome[0]["writes_from"], {"_python_new_oracle.py": "evals/oracles/python-craft/check_new_code.py"})
        self.assertEqual(next(c for c in checks if c["check"] == "changes_within")["allowed"], ["outcome_counts.py", "tests/"])
        self.assertTrue(any(c["check"] == "no_new_commits" for c in checks))
        self.assertTrue(any(c["check"] == "skill_loaded" and c["skill"] == "python-craft" for c in checks))
        self.assertTrue(any(c["check"] == "verification_completed" and c["runner"] == "unittest" for c in checks))


if __name__ == "__main__":
    unittest.main()
