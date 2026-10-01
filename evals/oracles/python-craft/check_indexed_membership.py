"""Independent public artifact oracle; standard library only, not an OS sandbox.

Operation counts establish this workload's improvement, not universal complexity.
Unobservable construction/query work returns exit 3 after behavioral checks, so counters
cannot certify an unmeasured implementation. This is not adversarial attestation.
String comparison/hash overrides only count calls and retain normal string semantics.
"""

import gc
import importlib.util
import inspect
from pathlib import Path
import sys
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


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(name + '.py').resolve())
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
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
    output = select(rows, allowed)
    CHECK.assertIs(iter(output), output, 'output must be an iterator')
    first = next(output)
    CHECK.assertEqual(str(first['id']), 'allowed-000')
    build_cost = CountedString.operations
    # Equal query strings are distinct objects and cannot impersonate the
    # supplied allowed values when checking construction observability.
    build_available = all(id(value) in CountedString.observed_objects for value in allowed)
    CHECK.assertLessEqual(build_cost, 4096, 'index construction cost exceeds bounded budget')
    CHECK.assertEqual(list(output), [])
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
    output = select(rows, allowed)
    CHECK.assertIs(iter(output), output, 'output must be an iterator')
    CHECK.assertEqual(rows.pulls, 0, 'rows consumed before output advancement')
    CHECK.assertTrue(all(not row.accesses for row in original), 'rows accessed eagerly')
    for expected, frontier in ((a, 1), (b, 3), (b, 4)):
        CHECK.assertIs(next(output), expected, 'row order, duplicates or identity changed')
        CHECK.assertEqual(rows.pulls, frontier, 'rows read ahead of the next matching row')
        CHECK.assertFalse(bad.accesses, 'missing-key access was not deferred')
        CHECK.assertFalse(tail.accesses, 'tail accessed ahead of its turn')
    with CHECK.assertRaises(KeyError) as raised:
        next(output)
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
    actual = list(select(rows, allowed))
    CHECK.assertEqual(len(actual), 4, 'output duplicates lost')
    for result, expected in zip(actual, [a, b, a, b]):
        CHECK.assertIs(result, expected, 'row order, duplicates or identity changed')
    CHECK.assertEqual([dict(row) for row in rows], snapshots, 'rows mutated')
    CHECK.assertEqual(allowed, ['a', 'b', 'a'], 'allowed input mutated')


def supplied_string_contract(select):
    for key, allowed_key in ((DisplayString('a'), 'a'), ('a', DisplayString('a'))):
        row = Row(id=key)
        actual = list(select(OnePass([row]), OnePass([allowed_key])))
        CHECK.assertEqual(len(actual), 1, 'supplied string membership semantics changed')
        CHECK.assertIs(actual[0], row, 'supplied string match copied the row')


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

        output = select(OnePass(fresh_rows()), ['selected'])
        if matching:
            for _ in range(width):
                next(output)  # The caller discards each selected row immediately.
        CHECK.assertEqual(next(output)['id'], 'selected')
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
        output = select(rows, allowed)
        CHECK.assertEqual(rows.pulls, 0, 'empty index consumed rows eagerly')
        try:
            next(output)
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
    output = select(rows, allowed)
    next(output)
    close = getattr(output, 'close', None)
    if close is not None:
        close()
    CHECK.assertFalse(rows.closed or allowed.closed, 'output closure closed caller iterators')
    CHECK.assertEqual(rows.pulls, 1, 'output closure consumed remaining rows')
    rows, allowed = OnePass([Row(id='a')]), OnePass(['a'])
    CHECK.assertEqual(len(list(select(rows, allowed))), 1)
    CHECK.assertFalse(rows.closed or allowed.closed, 'exhaustion closed caller iterators')
    CHECK.assertEqual(list(select(OnePass([]), OnePass(['a']))), [])


def main():
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
    if not cost_available:
        print('cost measurement unavailable: instrumented construction/query work was not fully observed', file=sys.stderr)
        raise SystemExit(3)
    print('indexed membership contract passed')


if __name__ == '__main__':
    main()
