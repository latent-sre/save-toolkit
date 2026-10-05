# Improving existing Python

## Contents

- Choose the transformation
- Simplify control flow and iteration
- Preserve consumers and integrate
- Example: separate calculation from files
- Verify behavior and benefit

## Choose the transformation

Follow a representative operation through its data, decisions, and effects. Address the cause of
complexity: parallel values may need records, repeated scans an index, contradictory flags clearer
states, and forwarding layers removal. Compare construction, conversion, and memory costs with
work removed. For function and module choices, see [Writing Python](./writing-python.md).

Share a policy when callers require the same rule; identical fragments can evolve independently.
Check purpose, inputs, and failure behavior before unifying them. A helper beside copies still in
use does not establish shared ownership. Keep meaningful single-caller boundaries and real extension
points; remove generic machinery that contributes neither.

## Simplify control flow and iteration

| Situation | Consider | Preserve or check |
|---|---|---|
| Nesting obscures the main operation | Guard clauses; a named domain predicate | Condition/effect order, cleanup, and distinctions among `None`, zero, false, and empty |
| A flag/list only answers a question | `any`, `all`, or `next` over a generator | Short-circuiting skips work/errors; empty `any` is false, empty `all` true; distinguish no match from a valid `None` with a sentinel |
| Simple mapping/filtering | Comprehension; a loop for multi-step work or per-item handling | Order, duplicates, mutation, scope; avoid side-effect-only or dense nested comprehensions |
| Indexes only retrieve items | Iteration, unpacking, `enumerate`, `zip` | Needed positions and shape; `zip` truncates, `strict=True` raises on mismatch (3.10+) |
| Counting, grouping, repeated searches | `Counter`, `defaultdict`, dict/set index | Equality/hashability, duplicates, order, missing-key insertion, result type, memory |
| Exact-key call selection | Dictionary of callables | Unknown keys, key equality, lazy calls; keep ordered/range predicates as conditionals |
| Structured-data cases | `match` when clearer (3.10+) | Case/guard order, unmatched input; bare names capture, dotted constants compare |
| Temporary collection with one consumer | Generator/streaming | Deferred work/errors, repeatability, indexing, partial consumption, resource lifetime |
| Repeated or dynamic cleanup | `with`/`async with`, `ExitStack`/`AsyncExitStack` | Ownership, partial acquisition, cleanup order, cancellation, suppression |

Choose by meaning; a clear loop or conditional may remain best. Name a predicate when it explains a
decision, not every comparison. Invert the original guard before changing comparisons: `not (x >= 0)`
and `x < 0` differ for NaN; truthiness is not an explicit `None` check.
For a worked comparison when needed, see [Guard-clause example](./guard-clause-example.md).

An extracted `return` does not return from its caller; preserve moved `break`/`continue` effects.
Comprehension iteration variables do not leak like loop variables. Generator expressions evaluate
the outermost iterable immediately; generator-function bodies wait for resumption. Neither can
consume a file closed by its producer. `mapping.get(key, expensive_default())` evaluates the default
even on a hit; dispatch tables should store callables rather than their results.

## Preserve consumers and integrate

Establish required behavior from specifications and consumers. Characterization records current
behavior; it cannot justify preserving a demonstrated bug or guessing an undocumented rule.

Find imports/re-exports, entrypoints, configured import strings, registries/decorators, and persisted
qualified names; an underscore does not prove a name is private. Controlled internal signatures and
shapes may change with their callers. Preserve supported call forms/defaults, import-time effects,
and public patch points. Add compatibility adapters only for actual supported consumers.

Complete one usable path, then migrate remaining callers; avoid leaving them with repeated shape
conversions or copies of moved policy. Check new dependency boundaries and remove superseded code
once callers use the replacement. Checkpoints follow meaningful behavior and risk, not file counts.

## Example: separate calculation from files

A pre-trade preview needs in-memory rows, but the calculation is trapped in file I/O:

```python
import csv
from decimal import Decimal


def filled_notional_from_file(path):
    with open(path, newline="", encoding="utf-8") as source:
        total = Decimal("0")
        for row in csv.DictReader(source):
            if row["status"] == "FILLED":
                total += Decimal(row["qty"]) * Decimal(row["price"])
        return total
```

Expose the calculation and route the existing file entrypoint through it:

```python
def filled_notional(rows):
    return sum(
        (Decimal(row["qty"]) * Decimal(row["price"]) for row in rows if row["status"] == "FILLED"),
        Decimal("0"),
    )


def filled_notional_from_file(path):
    with open(path, newline="", encoding="utf-8") as source:
        return filled_notional(csv.DictReader(source))
```

The new boundary serves a caller; an explicit loop is equally valid. The start preserves an empty
`Decimal` result. Check filtered/signed/empty data, one-pass inputs, invalid numbers, missing fields,
string/`Path` callers, and cleanup on failure. Keep a short function intact if the extraction has no use.

## Verify behavior and benefit

Establish that tests exercise affected behavior; characterize material gaps. Use coverage or a
reversible mutation when reach/sensitivity is uncertain, not as a universal prerequisite. Working
behavior needs no red-first test; a bug fix needs an independent expected result.

Compare fresh equivalent inputs and controlled time, randomness, effects, and caches. Check relevant
values/types, serialization, aliasing/mutation, call forms, errors, and effect order. Preserve the
exception object when propagating it. Pair differential checks with independent expectations so an
old bug cannot count as correctness. Use fresh processes for relevant import orders, cycles, and
registries. Exercise existing entrypoints; retain behavioral assertions when retiring test wiring.

Exhaust small domains; consider property-based/stateful tests for larger ones with a bounded budget.
For streaming, check progress before full consumption and cleanup after a prefix; returning an
iterator proves neither streaming nor bounded memory.

Show the benefit through actual callers: a shared policy replaces copies, a calculation works without
I/O, conversions/layers disappear, or a real change becomes simpler. Profile and benchmark when
performance motivates the design; compatibility tests alone do not establish improvement.

[sourced] [guard clauses](https://refactoring.com/catalog/replaceNestedConditionalWithGuardClauses.html),
[Extract Function](https://refactoring.com/catalog/extractFunction.html),
[expression semantics](https://docs.python.org/3/reference/expressions.html),
[Hypothesis properties](https://hypothesis.readthedocs.io/en/latest/tutorial/introduction.html),
[iteration](https://docs.python.org/3.11/library/functions.html),
[collections](https://docs.python.org/3.11/library/collections.html), and
[context managers](https://docs.python.org/3.11/library/contextlib.html).
