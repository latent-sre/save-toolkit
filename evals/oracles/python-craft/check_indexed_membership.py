"""Independent public artifact oracle; standard library only, not an OS sandbox.

Operation counts establish this workload's improvement, not universal complexity.
Unobservable construction/query work returns exit 3 after behavioral checks, so counters
cannot certify an unmeasured implementation. This is not adversarial attestation.
String comparison/hash overrides only count calls and retain normal string semantics.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from oracle_protocol import candidate_call

import gc
import importlib.util
import inspect
import json
import subprocess
import tempfile
from collections import UserDict
from collections.abc import Mapping
from types import MappingProxyType
from unittest import TestCase
import weakref


CHECK = TestCase()


class CountedString(str):
    operations = 0
    observed_queries = set()
    observed_objects = set()

    def count_operation(self, other=None):
        type(self).operations += 1
        # Comparison dispatch can use the index operand as its receiver. Record
        # both operands so sorted and hash indexes are measured on equal terms.
        for value in (self, other):
            if isinstance(value, CountedString):
                type(self).observed_objects.add(id(value))
                plain = str.__str__(value)
                if plain.startswith('missing-'):
                    type(self).observed_queries.add(plain)

    def __hash__(self):
        self.count_operation()
        return str.__hash__(self)

    def __eq__(self, other):
        self.count_operation(other)
        return str.__eq__(self, other)

    def __lt__(self, other):
        self.count_operation(other)
        return str.__lt__(self, other)

    def __le__(self, other):
        self.count_operation(other)
        return str.__le__(self, other)

    def __gt__(self, other):
        self.count_operation(other)
        return str.__gt__(self, other)

    def __ge__(self, other):
        self.count_operation(other)
        return str.__ge__(self, other)


class OnePass:
    def __init__(self, values):
        self.source = iter(values)
        self.pulls = 0
        self.closed = False

    def __iter__(self):
        return self

    def __next__(self):
        value = next(self.source)
        self.pulls += 1
        return value

    def close(self):
        self.closed = True


class DisplayString(str):
    """A display override does not change normal string membership semantics."""

    def __str__(self):
        return 'display:' + str.__str__(self)


class Row(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.accesses = []
        self.missing = KeyError('id')

    def __getitem__(self, key):
        self.accesses.append(key)
        if key == 'id' and key not in self:
            raise self.missing
        return super().__getitem__(key)


class MappingRow(Mapping):
    def __init__(self, values):
        self._values = values
        self.missing = KeyError('id')

    def __getitem__(self, key):
        if key not in self._values:
            raise self.missing
        return self._values[key]

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(name + '.py').resolve())
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    candidate_call(spec.loader.exec_module, module)
    return module


def cost_contract(select):
    # Stable list is also the old contract: unchanged baseline fails on cost here,
    # before the intentionally expanded one-pass allowed-input requirement.
    allowed = [CountedString(f'allowed-{i:03}') for i in range(128)]
    rows = OnePass([{'id': CountedString('allowed-000')}] +
                   [{'id': CountedString(f'missing-{i:03}')} for i in range(512)])
    CountedString.operations = 0
    CountedString.observed_queries.clear()
    CountedString.observed_objects.clear()
    output = candidate_call(select, rows, allowed)
    CHECK.assertIs(candidate_call(iter, output), output, 'output must be an iterator')
    first = candidate_call(next, output)
    CHECK.assertIsInstance(first, Mapping, 'selected row must remain a mapping')
    CHECK.assertIn('id', first, 'selected row lost its id')
    CHECK.assertEqual(str(first['id']), 'allowed-000')
    build_cost = CountedString.operations
    # Equal query strings are distinct objects and cannot impersonate the
    # supplied allowed values when checking construction observability.
    build_available = all(id(value) in CountedString.observed_objects for value in allowed)
    CHECK.assertLessEqual(build_cost, 4096, 'index construction cost exceeds bounded budget')
    CHECK.assertEqual(candidate_call(list, output), [])
    lookup_cost = CountedString.operations - build_cost
    CHECK.assertLessEqual(lookup_cost, 8192, 'repeated search cost exceeds indexed budget')
    CHECK.assertEqual([str(value) for value in allowed], [f'allowed-{i:03}' for i in range(128)],
                      'allowed input mutated')
    expected_queries = {f'missing-{i:03}' for i in range(512)}
    return build_available and CountedString.observed_queries == expected_queries


def row_contract(select, allowed):
    a, miss, b, bad, tail = Row(id='b'), Row(id='x'), Row(id='a'), Row(), Row(id='b')
    original = [a, miss, b, b, bad, tail]
    snapshots = [dict(row) for row in original]
    rows = OnePass(original)
    output = candidate_call(select, rows, allowed)
    CHECK.assertIs(candidate_call(iter, output), output, 'output must be an iterator')
    CHECK.assertEqual(rows.pulls, 0, 'rows consumed before output advancement')
    CHECK.assertTrue(all(not row.accesses for row in original), 'rows accessed eagerly')
    for expected, frontier in ((a, 1), (b, 3), (b, 4)):
        CHECK.assertIs(candidate_call(next, output), expected, 'row order, duplicates or identity changed')
        CHECK.assertEqual(rows.pulls, frontier, 'rows read ahead of the next matching row')
        CHECK.assertFalse(bad.accesses, 'missing-key access was not deferred')
        CHECK.assertFalse(tail.accesses, 'tail accessed ahead of its turn')
    with CHECK.assertRaises(KeyError) as raised:
        candidate_call(next, output)
    CHECK.assertIs(raised.exception, bad.missing, 'missing-key exception replaced')
    CHECK.assertEqual(rows.pulls, 5, 'error consumed later rows')
    CHECK.assertFalse(tail.accesses, 'tail accessed after error')
    CHECK.assertEqual([dict(row) for row in original], snapshots, 'rows mutated')
    CHECK.assertFalse(rows.closed, 'caller row iterator closed on error')
    if isinstance(allowed, OnePass):
        CHECK.assertEqual(allowed.pulls, 3, 'allowed input not indexed once')
        CHECK.assertFalse(allowed.closed, 'caller allowed iterator closed')


def values_contract(select):
    a, b, miss = Row(id='b'), Row(id='a'), Row(id='x')
    rows, allowed = [a, miss, b, a, b], ['a', 'b', 'a']
    snapshots = [dict(row) for row in rows]
    actual = candidate_call(list, candidate_call(select, rows, allowed))
    CHECK.assertEqual(len(actual), 4, 'output duplicates lost')
    for result, expected in zip(actual, [a, b, a, b]):
        CHECK.assertIs(result, expected, 'row order, duplicates or identity changed')
    CHECK.assertEqual([dict(row) for row in rows], snapshots, 'rows mutated')
    CHECK.assertEqual(allowed, ['a', 'b', 'a'], 'allowed input mutated')


def supplied_string_contract(select):
    for key, allowed_key in ((DisplayString('a'), 'a'), ('a', DisplayString('a'))):
        row = Row(id=key)
        actual = candidate_call(list, candidate_call(select, OnePass([row]), OnePass([allowed_key])))
        CHECK.assertEqual(len(actual), 1, 'supplied string membership semantics changed')
        CHECK.assertIs(actual[0], row, 'supplied string match copied the row')


def mapping_contract(select):
    for wrap in (MappingProxyType, UserDict, MappingRow):
        a, b, miss = wrap({'id': 'a'}), wrap({'id': 'b'}), wrap({'id': 'x'})
        actual = candidate_call(list, candidate_call(select, OnePass([a, miss, b, a]), OnePass(['a', 'b'])))
        CHECK.assertEqual(len(actual), 3)
        for result, expected in zip(actual, [a, b, a]):
            CHECK.assertIs(result, expected, 'mapping order, duplicates or identity changed')
        CHECK.assertEqual([dict(row) for row in (a, b, miss)],
                          [{'id': 'a'}, {'id': 'b'}, {'id': 'x'}], 'mapping input mutated')
        for allowed in ([], ['a']):
            bad, tail = wrap({}), wrap({'id': 'later'})
            rows = OnePass([a, bad, tail])
            output = candidate_call(select, rows, allowed)
            CHECK.assertEqual(rows.pulls, 0, 'mapping accessed before iteration')
            if allowed:
                CHECK.assertIs(candidate_call(next, output), a)
            with CHECK.assertRaises(KeyError) as raised:
                candidate_call(next, output)
            if isinstance(bad, MappingRow):
                CHECK.assertIs(raised.exception, bad.missing, 'mapping KeyError replaced')
            CHECK.assertEqual(rows.pulls, 2, 'mapping error consumed later rows')
            CHECK.assertIs(next(rows), tail)


def storage_contract(select):
    def retained_count(width, matching):
        references = []

        def fresh_rows():
            # The observer keeps only weak references; the source and consumer
            # keep at most the current row. No collected output list can retain
            # a prefix on behalf of the candidate.
            for position in range(width):
                row = Row(id='selected' if matching else f'missing-{position}')
                references.append(weakref.ref(row))
                yield row
            row = Row(id='selected')
            references.append(weakref.ref(row))
            yield row

        output = candidate_call(select, OnePass(fresh_rows()), ['selected'])
        if matching:
            for _ in range(width):
                candidate_call(next, output)  # The caller discards each selected row immediately.
        selected = candidate_call(next, output)
        CHECK.assertIsInstance(selected, Mapping, 'selected row must remain a mapping')
        CHECK.assertIn('id', selected, 'selected row lost its id')
        CHECK.assertEqual(selected['id'], 'selected')
        gc.collect()
        return sum(reference() is not None for reference in references)

    # A small allowance covers a fixed current-row cache without constraining
    # the implementation's iterator/container spelling. This is a bounded
    # workload observation, not proof of space complexity for every input.
    for matching in (False, True):
        small, large = retained_count(128, matching), retained_count(2048, matching)
        CHECK.assertLessEqual(large, small + 8, 'consumed row retention grows with input')


def empty_and_closure_contract(select):
    for allowed_values in ([], ['absent']):
        valid, bad, tail = Row(id='x'), Row(), Row(id='tail')
        rows, allowed = OnePass([valid, bad, tail]), OnePass(allowed_values)
        output = candidate_call(select, rows, allowed)
        CHECK.assertEqual(rows.pulls, 0, 'empty index consumed rows eagerly')
        try:
            candidate_call(next, output)
        except KeyError as exc:
            CHECK.assertIs(exc, bad.missing, 'empty/nonmatching index skipped row validation')
        except StopIteration:
            CHECK.fail('empty/nonmatching index skipped row validation')
        else:
            CHECK.fail('missing row did not raise KeyError')
        CHECK.assertIn('id', valid.accesses, 'nonmatching row was not validated')
        CHECK.assertEqual(rows.pulls, 2)
        CHECK.assertFalse(rows.closed or allowed.closed, 'caller iterator closed on error')
    rows, allowed = OnePass([Row(id='a'), Row(id='a')]), OnePass(['a'])
    output = candidate_call(select, rows, allowed)
    candidate_call(next, output)
    close = getattr(output, 'close', None)
    if close is not None:
        close()
    CHECK.assertFalse(rows.closed or allowed.closed, 'output closure closed caller iterators')
    CHECK.assertEqual(rows.pulls, 1, 'output closure consumed remaining rows')
    rows, allowed = OnePass([Row(id='a')]), OnePass(['a'])
    CHECK.assertEqual(len(candidate_call(list, candidate_call(select, rows, allowed))), 1)
    CHECK.assertFalse(rows.closed or allowed.closed, 'exhaustion closed caller iterators')
    CHECK.assertEqual(candidate_call(list, candidate_call(select, OnePass([]), OnePass(['a']))), [])


INDEXED = """\
def iter_selected(rows, allowed_ids):
    index = set(allowed_ids)
    for row in rows:
        if row['id'] in index:
            yield row
"""

# These implementations retain the public contract except for the named fault.
# The cost mutants also accept one-pass allowed input, so semantic/API failures
# cannot stand in for the requested cost assertions.
TEST_MUTANTS = {
    'repeated linear search': INDEXED.replace('set(allowed_ids)', 'list(allowed_ids)'),
    'quadratic index construction': INDEXED.replace(
        'index = set(allowed_ids)',
        'values = list(allowed_ids)\n    index = set(value for value in values if value in values)'),
}

SUITE_RUNNER = """\
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path.cwd()))
import selection
mutation = Path('_cost_mutant.py')
if mutation.is_file():
    exec(compile(mutation.read_text(encoding='utf-8'), str(mutation), 'exec'), selection.__dict__)
suite = unittest.defaultTestLoader.discover('tests', top_level_dir='.')
result = unittest.TextTestRunner(verbosity=0).run(suite)
Path('_suite_result.json').write_text(json.dumps({
    'run': result.testsRun, 'failures': len(result.failures),
    'errors': len(result.errors), 'skipped': len(result.skipped),
    'successful': result.wasSuccessful(),
}), encoding='utf-8')
"""


def test_coverage_contract():
    # Each replay gets its own scratch fixture and interpreter, avoiding cached
    # imports or candidate-file replacement in the actual evaluation workspace.
    def replay(source=None):
        with tempfile.TemporaryDirectory(prefix='index-suite-') as temporary:
            root = Path(temporary)
            (root / 'tests').mkdir()
            for name in ('selection.py', 'consumer.py', 'tests/__init__.py', 'tests/test_selection.py'):
                (root / name).write_bytes(Path(name).read_bytes())
            if source is not None:
                (root / '_cost_mutant.py').write_text(source, encoding='utf-8')
            result = subprocess.run([sys.executable, '-I', '-B', '-c', SUITE_RUNNER],
                                    cwd=root, capture_output=True, text=True, timeout=10)
            report = root / '_suite_result.json'
            CHECK.assertEqual(result.returncode, 0, 'candidate test runner failed: ' + result.stderr)
            CHECK.assertTrue(report.is_file(), 'candidate tests exited without results')
            return json.loads(report.read_text(encoding='utf-8')), result.stderr

    real, diagnostic = replay()
    CHECK.assertTrue(real['successful'] and real['run'] > 0, 'candidate tests failed: ' + diagnostic)
    for name, source in TEST_MUTANTS.items():
        result, diagnostic = replay(source)
        # Cost mutants preserve behavior, so only assertion failures establish
        # cost coverage. Import/runtime errors and skips cannot substitute.
        CHECK.assertTrue(result['failures'] > 0 and result['errors'] == 0,
                         'candidate tests did not reject ' + name + ': ' + diagnostic)


def candidate_contract():
    select = load('selection').iter_selected
    parameters = list(inspect.signature(select).parameters.values())
    CHECK.assertEqual([(p.name, p.kind, p.default) for p in parameters],
                      [(name, inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.empty)
                       for name in ('rows', 'allowed_ids')], 'public call signature changed')
    cost_available = cost_contract(select)
    consumer = load('consumer').selected
    values_contract(consumer)
    row_contract(consumer, ['a', 'b', 'a'])
    row_contract(consumer, OnePass(['a', 'b', 'a']))
    supplied_string_contract(consumer)
    storage_contract(consumer)
    empty_and_closure_contract(consumer)
    mapping_contract(consumer)
    test_coverage_contract()
    return cost_available


def main():
    try:
        cost_available = candidate_contract()
    except SystemExit as exc:
        raise AssertionError(f'candidate raised SystemExit({exc.code!r})') from exc
    if not cost_available:
        print('cost measurement unavailable: instrumented construction/query work was not fully observed', file=sys.stderr)
        raise SystemExit(3)
    print('indexed membership contract passed')


if __name__ == '__main__':
    main()
