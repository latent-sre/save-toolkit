# Improving existing Python

Improve what makes the code hard to understand, change, test, or trust; patterns serve that outcome.

## Contents

- Choose Pythonic patterns by problem
- Establish behavior and consumers
- Choose a coherent change
- Example: make a calculation usable without files
- Verify compatibility and improvement

## Choose Pythonic patterns by problem

Inspect a representative path and its callers. Prioritize demonstrated defects and recurring
maintenance work, using code evidence rather than a questionnaire or smell score.

| Problem | Pythonic option | Preserve or check |
|---|---|---|
| Nesting or duplicated policy | Guards; coherent helpers; inline trivial wrappers | Condition/effect order, cleanup, zero/None; share policies, not fragments |
| Mapping/filter loops | Comprehensions for simple transforms; loops for multi-step work | Order, duplicates, mutation, scope; avoid side-effect-only comprehensions |
| Index bookkeeping | Iteration, unpacking, `enumerate`, `zip` | Needed indexes/lengths; `zip` truncates, while `strict=True` raises on mismatch (3.10+) |
| Counting, grouping, searching | `Counter`, `defaultdict`, dict/set indexes | Key equality/hashability, multiplicity, order, result type, missing keys, memory |
| Parallel lists or opaque records | Dataclasses; `TypedDict` to retain a dict API | Construction, equality, aliasing, mutation, serialization; types are not validation |
| Mixed parsing, decisions, I/O | Separate phases and explicit data | Existing entrypoints share decisions; preserve effect/failure order |
| Repeated cleanup | `with`/`async with`; `ExitStack` for dynamic resources | Ownership, partial acquisition, cleanup order, cancellation, exception suppression |
| One-pass temporary collections | Generators/streaming where compatible | Deferred work/errors, repeatability, indexing, short-circuit effects, resource lifetime |
| Dispatch or custom machinery | Callable lookup or a suitable stdlib/library | Missing/overlapping cases, eager calls/defaults; use the modernization reference |

These are candidates, not prescriptions. Compare purpose, inputs, failure behavior, and reasons
to change: two occurrences can share a policy; three similar fragments may evolve independently.
Do not invent a framework to unify coincidental similarity.

An extracted return does not return from its caller; moved `break`/`continue` must retain loop effects.
Comprehension variables do not leak like loop variables. Generator expressions evaluate the outermost
iterable immediately; generator-function bodies wait for resumption. Neither can consume a file
already closed by its producer.
`mapping.get(key, expensive_default())` evaluates the default on a hit; store callables rather
than calls for selective dispatch. Ranges and ordered fallbacks may be clearer as conditionals.

## Establish behavior and consumers

Separate supported behavior from implementation details using requirements, examples, callers,
and tests. A characterization test records what happens today; a bug fix needs an independently
established expected result. Do not preserve a demonstrated bug as "refactoring safety," or silently
change a relied-on behavior because it looks wrong. Separate the fix from the structural steps
when authorized; otherwise report the defect and continue independent in-scope work. Ask when
intended behavior or permission to change compatibility is unresolved.

Find imports/re-exports, entry points, configuration/import strings, decorators/registries, and
persisted module-qualified names. A leading underscore does not prove a name has no external
consumer. Internal names, signatures, and data shapes may change with all controlled callers;
supported consumers keep their contract unless a migration is authorized. Add a compatibility
re-export only for an actual supported consumer, not every internal move.
Preserve supported positional/keyword-only call forms and defaults, import-time effects, and patch
locations; exercise dynamic lookup and both import orders when a move could create a cycle.

## Choose a coherent change

Plan medium-sized, coherent stages around meaningful improvements and their checks. Scale stages to
risk and testability, not function or file count. Keep unrelated cleanup and invented requirements out.

Rewrite a function, module, or the entire codebase in the agreed scope when replacement offers a
clearer, more maintainable design. Stages bound verification, not the total rewrite. Name the payoff,
establish behavior checks, and integrate controlled callers. Preserve required contracts, not the
old source. Remove superseded code once verified; rewriting does not authorize new requirements.

Extraction that merely relocates a confusing block with unrelated state is not enough: reconsider
the decomposition or data model. Keep the direct expression when a wrapper adds no useful boundary.

## Example: make a calculation usable without files

Here a preview caller and calculation tests need in-memory input, but the rule is trapped in I/O:

```python
def total_from_file(path):
    with open(path, encoding="utf-8") as source:
        total = 0
        for line in source:
            if line.strip():
                total += int(line)
        return total
```

Keep the existing file interface and give the calculation one reusable boundary:

```python
def total_from_lines(lines):
    return sum(int(line) for line in lines if line.strip())


def total_from_file(path):
    with open(path, encoding="utf-8") as source:
        return total_from_lines(source)
```

The benefit is independent calculation and shared policy; an explicit loop is equally valid.
Check empty/blank input, signed values, duplicates, one-pass
iterables, parse errors, string/keyword path callers, and file cleanup on failure. If no caller or
test benefits from the new boundary, do not manufacture one merely to split a short function.

## Verify compatibility and improvement

Use existing tests and characterize missing contracts; working behavior needs no artificial red.
Compare old/new code on equivalent fresh inputs and controlled state. Check values/types,
serialization, aliasing, mutation, accepted/rejected call forms, errors, and ordered effects.
When propagation is required, preserve the exception object, not only its type/message.
Pair differential checks with independent expectations so preserving an old bug cannot count as a fix.

Control time, randomness, effects, and caches independently. Use fresh processes for import order,
registries, or process state. Test existing entrypoints as well as new capabilities; testing only
a new helper misses callers that bypass it. Tests coupled to retired internals may change, but
retain their behavioral assertions rather than rewriting expected outputs to conceal regressions.

For small domains, exhaust bounded combinations. Use property-based tests for larger domains or
stateful sequences when useful, retaining named regressions and a defined comparison budget.
For streaming, verify progress before full consumption and cleanup after a prefix; an iterator
alone proves neither incremental processing nor bounded memory.

Demonstrate the benefit: one policy owner, testable decisions, removed layers, or a simpler next
change. Passing compatibility checks alone does not prove improvement.

[sourced] [Fowler's guard clauses](https://refactoring.com/catalog/replaceNestedConditionalWithGuardClauses.html),
[Extract Function](https://refactoring.com/catalog/extractFunction.html),
[Python expression semantics](https://docs.python.org/3/reference/expressions.html), and
[Hypothesis properties](https://hypothesis.readthedocs.io/en/latest/tutorial/introduction.html).
Pattern details: [iteration helpers](https://docs.python.org/3.11/library/functions.html),
[collections](https://docs.python.org/3.11/library/collections.html), and
[context managers](https://docs.python.org/3.11/library/contextlib.html).
