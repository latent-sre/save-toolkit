"""Offline calibration of the indexed-membership build probe's actual command."""

import tempfile
import textwrap
import unittest
from pathlib import Path

from probe_testkit import assert_completion, completion_env, run_python, scenario_file, write_tree

ROOT = Path(__file__).resolve().parent
SPEC = scenario_file(ROOT / 'build-scenarios/build-python-indexed-membership.yaml')
SEED_TESTS = SPEC['fixture']['files']['tests/test_selection.py']
SET = textwrap.dedent('''
    def iter_selected(rows, allowed_ids):
        index = set(allowed_ids)
        for row in rows:
            if row['id'] in index:
                yield row
''')
DICT = SET.replace('set(allowed_ids)', 'dict.fromkeys(allowed_ids)')
SORTED = '''
    from bisect import bisect_left
    def iter_selected(rows, allowed_ids):
        index = sorted(allowed_ids)
        for row in rows:
            key = row['id']
            offset = bisect_left(index, key)
            if offset < len(index) and index[offset] == key:
                yield row
'''
FOCUSED_TESTS = '''

class SearchCostTests(unittest.TestCase):
    def test_build_and_search_cost(self):
        class Key(str):
            operations = 0

            def __hash__(self):
                Key.operations += 1
                return str.__hash__(self)

            def __eq__(self, other):
                Key.operations += 1
                return str.__eq__(self, other)

            def __lt__(self, other):
                Key.operations += 1
                return str.__lt__(self, other)

        allowed = [Key(f'allowed-{i:03}') for i in range(128)]
        rows = [{'id': Key('allowed-000')}] + [
            {'id': Key(f'missing-{i:03}')} for i in range(512)]
        output = selected(iter(rows), iter(allowed))
        self.assertIs(next(output), rows[0])
        build = Key.operations
        self.assertLessEqual(build, 4096)
        self.assertEqual(list(output), [])
        self.assertLessEqual(Key.operations - build, 8192)
'''
# The suite a passing candidate leaves: the seed regressions plus focused build and search cost tests.
CANDIDATE_TESTS = SEED_TESTS + FOCUSED_TESTS


class IndexedMembershipTests(unittest.TestCase):
    def test_fixture_has_a_passing_existing_regression_suite(self):
        with tempfile.TemporaryDirectory() as tmp:
            write_tree(Path(tmp), SPEC['fixture']['files'])
            result = run_python(['-B', '-m', 'unittest', 'discover', '-s', 'tests', '-t', '.', '-v'], cwd=tmp,
                                isolated=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Ran 2 tests', result.stderr)
            self.assertIn('test_order_duplicates_and_identity', result.stderr)
            self.assertIn('test_missing_key_is_deferred_even_with_empty_allowlist', result.stderr)

    def run_artifact(self, source, tests=CANDIDATE_TESTS):
        check = next(c for c in SPEC['checks'] if c['check'] == 'command_exit_zero')
        with tempfile.TemporaryDirectory() as tmp:
            write_tree(Path(tmp), SPEC['fixture']['files'])
            (Path(tmp) / 'selection.py').write_text(textwrap.dedent(source), encoding='utf-8')
            (Path(tmp) / 'tests/test_selection.py').write_text(tests, encoding='utf-8')
            for name, oracle in check['writes_from'].items():
                (Path(tmp) / name).write_bytes((ROOT.parent / oracle).read_bytes())
            # Execute precisely the staged scenario command with the verified interpreter.
            return assert_completion(run_python([*check['command'].split()[1:]], cwd=tmp, env=completion_env(),
                                                timeout=15))

    def assert_passes(self, source, tests=CANDIDATE_TESTS):
        result = self.run_artifact(source, tests)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('indexed membership contract passed', result.stdout)

    def assert_fails(self, source, diagnostic, tests=CANDIDATE_TESTS, code=None):
        """The oracle names `diagnostic` and exits `code`, or with any failure when `code` is None."""
        result = self.run_artifact(source, tests)
        if code is None:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        else:
            self.assertEqual(result.returncode, code, result.stderr)
        self.assertIn(diagnostic, result.stderr)
        return result

    def test_candidate_system_exit_is_always_failure(self):
        for code in (0, 3):
            for phase, source in [('import', f'raise SystemExit({code})'),
                                  ('iteration', SET.replace('index = set(allowed_ids)',
                                                           f'raise SystemExit({code})'))]:
                with self.subTest(code=code, phase=phase):
                    self.assert_fails(source, 'candidate raised SystemExit', code=1)

    def test_seed_or_cosmetic_test_extensions_do_not_establish_cost_coverage(self):
        for tests in (SEED_TESTS, SEED_TESTS + '\n# Tests reviewed.\n', SEED_TESTS + '''
class CosmeticTests(unittest.TestCase):
    def test_true(self):
        self.assertTrue(True)
'''):
            with self.subTest(tests=tests):
                self.assert_fails(SET, 'candidate tests did not reject repeated linear search', tests, code=1)

    def test_nondict_mappings_are_covered(self):
        source = SET.replace("if row['id'] in index:",
                             "if not isinstance(row, dict):\n            raise TypeError('dict required')\n        if row['id'] in index:")
        self.assert_fails(source, 'dict required', code=1)

    def test_replays_preserve_candidate_helpers_imported_by_tests(self):
        source = SET + '\ndef supported_helper():\n    return 42\n'
        self.assert_passes(source, CANDIDATE_TESTS + '''
from selection import supported_helper

class HelperTests(unittest.TestCase):
    def test_helper(self):
        self.assertEqual(supported_helper(), 42)
''')

    def test_tests_must_cover_index_construction_too(self):
        tests = SEED_TESTS + FOCUSED_TESTS.replace('self.assertLessEqual(build, 4096)', 'pass')
        self.assert_fails(SET, 'candidate tests did not reject quadratic index construction', tests, code=1)

    def test_errors_or_skips_do_not_establish_cost_coverage(self):
        for replacement in ("if Key.operations - build > 8192: raise RuntimeError('over budget')",
                            "if Key.operations - build > 8192: self.skipTest('over budget')"):
            with self.subTest(replacement=replacement):
                tests = SEED_TESTS + FOCUSED_TESTS.replace('self.assertLessEqual(Key.operations - build, 8192)', replacement)
                self.assert_fails(SET, 'candidate tests did not reject repeated linear search', tests, code=1)

    def test_distinct_index_implementations_pass(self):
        repeated_lookup = SET.replace("if row['id'] in index:",
                                      "if isinstance(row['id'], str) and row['id'] in index:")
        for name, source in [('set', SET), ('dict', DICT), ('sorted', SORTED),
                             ('repeated mapping lookup', repeated_lookup)]:
            with self.subTest(implementation=name):
                self.assert_passes(source)

    def test_masked_lookup_or_index_build_work_is_inconclusive(self):
        for name, source in [
            ('lookup', SET.replace('set(allowed_ids)', '[str.__str__(value) for value in allowed_ids]').replace(
                "row['id'] in index", "str.__str__(row['id']) in index")),
            ('quadratic index build', SET.replace('index = set(allowed_ids)',
                'values = [str.__str__(value) for value in allowed_ids]\n'
                '    index = set(value for value in values if value in values)')),
        ]:
            with self.subTest(masked=name):
                result = self.assert_fails(source, 'cost measurement unavailable', code=3)
                self.assertNotIn('indexed membership contract passed', result.stdout)

    def test_seed_and_linear_search_fail_for_repeated_search_cost(self):
        for source in (SPEC['fixture']['files']['selection.py'], SET.replace('set(allowed_ids)', 'list(allowed_ids)')):
            with self.subTest(source=source):
                self.assert_fails(source, 'repeated search cost exceeds indexed budget')

    def test_caching_consumed_prefix_is_rejected(self):
        base = SET.replace('index = set(allowed_ids)', 'index = set(allowed_ids)\n    retained = []')
        for name, source in [('all consumed rows', base.replace(
                'for row in rows:', 'for row in rows:\n        retained.append(row)')),
                ('selected rows only', base.replace('yield row', 'retained.append(row)\n            yield row'))]:
            with self.subTest(cache=name):
                self.assert_fails(source, 'consumed row retention grows with input')

    def test_named_contract_regressions_are_rejected(self):
        mutants = [
            ('all rows materialized', SET.replace('for row in rows:', 'for row in list(rows):'),
             'rows read ahead of the next matching row'),
            ('duplicate rows lost', '''
                def iter_selected(rows, allowed_ids):
                    index, seen = set(allowed_ids), set()
                    for row in rows:
                        key = row['id']
                        if key in index and id(row) not in seen:
                            seen.add(id(row))
                            yield row
            ''', 'output duplicates lost'),
            ('output order reversed', '''
                def iter_selected(rows, allowed_ids):
                    index = set(allowed_ids)
                    return iter([row for row in rows if row['id'] in index][::-1])
            ''', 'row order, duplicates or identity changed'),
            ('input row mutated', SET.replace('yield row', "row['added'] = True\n            yield row"),
             'rows mutated'),
            ('row identity copied', SET.replace('yield row', 'yield dict(row)'),
             'row order, duplicates or identity changed'),
            ('empty index skips required row validation', SET.replace('for row in rows:',
                'if not index:\n        return\n    for row in rows:'), 'empty/nonmatching index skipped row validation'),
            ('missing-key exception replaced', '''
                def iter_selected(rows, allowed_ids):
                    index = set(allowed_ids)
                    for row in rows:
                        try:
                            key = row['id']
                        except KeyError:
                            raise KeyError('id') from None
                        if key in index:
                            yield row
            ''', 'missing-key exception replaced'),
            ('missing-key exception suppressed', SET.replace("if row['id'] in index:", "if row.get('id') in index:"),
             'KeyError not raised'),
            ('allowed onepass consumed and reused', SET.replace('set(allowed_ids)',
                "set(allowed_ids) if isinstance(allowed_ids, list) else (list(allowed_ids) and set(allowed_ids))"),
             'KeyError'),
            ('caller rows closed', SET.replace('index = set(allowed_ids)',
                "index = set(allowed_ids)\n    if hasattr(rows, 'close'):\n        rows.close()"),
             'caller row iterator closed'),
            ('caller allowed iterator closed', SET.replace('index = set(allowed_ids)',
                "index = set(allowed_ids)\n    if hasattr(allowed_ids, 'close'):\n        allowed_ids.close()"),
             'caller allowed iterator closed'),
            ('allowed input mutated', SET.replace('index = set(allowed_ids)',
                "index = set(allowed_ids)\n    if isinstance(allowed_ids, list):\n        allowed_ids.reverse()"),
             'allowed input mutated'),
            ('quadratic index construction', SET.replace('index = set(allowed_ids)',
                "values = list(allowed_ids)\n    index = set(value for value in values if value in values)"),
             'index construction cost exceeds bounded budget'),
            ('string display coerced into membership key', SET.replace('set(allowed_ids)',
                '[str(value) for value in allowed_ids]').replace("row['id'] in index", "str(row['id']) in index"),
             'supplied string membership semantics changed'),
        ]
        for name, source, diagnostic in mutants:
            with self.subTest(regression=name):
                result = self.assert_fails(source, diagnostic)
                self.assertNotIn('SyntaxError', result.stderr)
                self.assertNotIn('IndentationError', result.stderr)

    def test_row_and_allowed_string_coercion_each_break_membership(self):
        for source in (SET.replace("row['id'] in index", "str(row['id']) in index"),
                       SET.replace('set(allowed_ids)', 'set(str(value) for value in allowed_ids)')):
            with self.subTest(source=source):
                self.assert_fails(source, 'supplied string membership semantics changed')

    def test_eager_row_access_is_rejected(self):
        self.assert_fails('''
            def iter_selected(rows, allowed_ids):
                index = set(allowed_ids)
                accepted = [row for row in rows if row['id'] in index]
                return iter(accepted)
        ''', 'KeyError')

    def test_build_schema_scope_skill_and_oracle_binding(self):
        self.assertEqual(SPEC['id'], 'build-python-indexed-membership')
        self.assertEqual(SPEC['agent'], 'software-engineer')
        checks = SPEC['checks']
        outcome = [c for c in checks if c['check'] == 'command_exit_zero']
        self.assertEqual(len(outcome), 1)
        self.assertEqual(outcome[0]['command'], 'python -I -B _python_index_oracle.py')
        self.assertEqual(outcome[0]['inconclusive_exit_code'], 3)
        self.assertEqual(outcome[0]['writes_from'], {
            '_python_index_oracle.py': 'evals/oracles/python-craft/check_indexed_membership.py'})
        self.assertEqual(next(c['allowed'] for c in checks if c['check'] == 'changes_within'),
                         ['selection.py', 'tests/test_selection.py'])
        self.assertTrue(any(c['check'] == 'skill_loaded' and c['skill'] == 'python-craft' for c in checks))
        self.assertTrue(any(c['check'] == 'no_new_commits' for c in checks))
        self.assertTrue(any(c['check'] == 'verification_completed' and c['runner'] == 'unittest' for c in checks))
        self.assertEqual(set(SPEC['fixture']['files']), {
            '.gitignore', 'selection.py', 'consumer.py', 'tests/__init__.py', 'tests/test_selection.py'})


if __name__ == '__main__':
    unittest.main()
