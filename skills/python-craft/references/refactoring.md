# Refactoring Python

Preserve behavior through inspectable steps. A code smell suggests a question, not a rewrite.

## Contents

- Map the affected behavior
- Choose a worthwhile improvement
- Choose a transformation
- Guards and extraction together
- Dictionaries and comprehensions need semantic checks
- Check equivalence at the changed boundary

## Map the affected behavior

Find consumers in imports/re-exports, entry points, configuration/import strings,
decorators/registries, and tests. Classify supported boundaries separately from implementation:
internal names, signatures, and data shapes can change with all controlled callers in one coherent
refactor. A leading underscore is not evidence that no external consumer exists.

At supported boundaries, preserve positional/keyword-only calling rules and defaults. Check public
import paths, circular imports, import-time effects, and patch locations used by callers/tests.
If persisted objects or plugins refer to module-qualified names, exercise that lookup explicitly;
an internal move does not authorize breaking those consumers. Add a compatibility re-export only
when an actual supported caller needs it.

## Choose a worthwhile improvement

Identify what is hard to understand, test, or change from repository evidence, not a questionnaire.
Compare leaving it alone with a concrete improvement. Authorized scope may span a component and
its callers; take small verified steps without unrelated cleanup or invented requirements.

| Observed problem | Candidate improvement | Evidence of benefit |
|---|---|---|
| One rule must change in several places | Give that rule one owner | A rule change reaches each existing caller |
| Calculation tests need files, globals, or a service | Separate decision inputs from effects | Exercise the calculation without those effects; existing entrypoint still uses it |
| Mixed responsibilities or trivial indirection | Split a responsibility or inline | Trace the change through fewer unrelated concepts |
| A requested next change fights the structure | Prepare its boundary | Show how the known change fits; keep feature behavior separate |

Two occurrences can justify sharing one policy; three similar-looking fragments need not represent
the same concept. Extract for clarity even with one caller, but keep a direct implementation when
the helper merely renames syntax. Judge coupling and change ownership, not file count or line count.

## Choose a transformation

| Technique | Useful trigger | Preserve or check |
|---|---|---|
| Guard clauses | Terminal cases hide the normal path | Condition order, effects before return, cleanup, zero/None semantics |
| Extract function/method | A coherent calculation or operation lacks a name | Live inputs, returned state, mutation, exception and return boundaries |
| Inline helper | Indirection hides an already simple operation | Public callers and any hidden effect |
| Named predicate/variable | An expression hides domain meaning | Short-circuiting, evaluation order and number of calls |
| Dictionary lookup/dispatch | Branches compare stable keys for equality | Missing keys, hashability, duplicate/equal keys, and eager evaluation |
| List/dict/set comprehension | Simple mapping/filter builds the required collection | Scope, ordering, duplicate handling and materialization |
| Generator expression | Values can be consumed once and incrementally | Deferred work/errors, exhaustion, and resource lifetime |
| Standard collection operation | A loop duplicates a known operation | Empty cases, ordering, mutation and algorithmic cost |

For extraction, returning inside a new helper does not return from its caller. Adapt the caller
explicitly; likewise, a moved `break` or `continue` must retain its original loop effect. Avoid a
helper with a large bundle of unrelated inputs simply to reduce the caller's line count.

## Guards and extraction together

Both functions implement the same contract: ignore negative values and scale the sum, with `None`
meaning the default multiplier. The extracted calculation is useful despite having one caller.

```python
def total_before(values: list[int], multiplier: int | None) -> int:
    if values:
        subtotal = 0
        for value in values:
            if value >= 0:
                subtotal += value
        if multiplier is None:
            return subtotal
        return subtotal * multiplier
    return 0


def nonnegative_sum(values: list[int]) -> int:
    return sum(value for value in values if value >= 0)


def total_after(values: list[int], multiplier: int | None) -> int:
    if not values:
        return 0
    subtotal = nonnegative_sum(values)
    if multiplier is None:
        return subtotal
    return subtotal * multiplier
```

Check empty/mixed/all-negative inputs and `None`, zero, and negative multipliers. Keep exceptions
and effects outside this example under their own contract; the integers here have no external work.

## Dictionaries and comprehensions need semantic checks

Use a dispatch table for equality-based selection, keeping the established unknown-action result:

```python
def transform(text: str, action: str) -> str:
    handlers = {"upper": str.upper, "lower": str.lower}
    if action not in handlers:
        raise ValueError(f"unsupported action: {action}")
    return handlers[action](text)
```

Store callables when only the selected operation should execute. A dictionary containing function
*calls* evaluates those values during construction. `mapping.get(key, expensive_default())` also
evaluates its default on a hit. Ranges, overlapping predicates, and ordered fallbacks often remain
clearer as conditionals; hashing and equality must fit the keys the old code accepted.

Prefer a straightforward transformation with an optional filter. Keep an explicit loop when the
work needs several stages, per-item exceptions, logging, or effects. In Python 3, a comprehension's
iteration variable does not replace the surrounding variable as an ordinary loop does.

A generator expression delays element computation, but evaluates the outermost iterable expression
immediately. Replacing a list with a generator changes repeatability, indexing, length, and when
errors occur. A generator returned from a closed file context cannot consume that file. Passing a
generator to `any`/`all` may skip later effects that an eagerly built list performed.

## Check equivalence at the changed boundary

Use existing contract tests plus focused missing cases. For deterministic logic, compare old/new
implementations on equivalent fresh inputs; do not feed one run's mutated state to the other.
Check values/types, aliasing or mutation, accepted and rejected call forms, errors, and the relevant
ordered effect trace. When the contract propagates an exception, preserve that object rather than
manufacturing a new exception with the same message. Pair differential checks with independent
expectations: preserving an old bug does not satisfy a requested fix.

Keep time, randomness, external effects, and caches controlled independently for each run. Use a
fresh process where imports, global registries, or process state could contaminate the comparison.
Change one structural seam at a time and inspect its callers before expanding. Check extraction
through the existing public entrypoint; tests that only call the new helper can miss a broken caller.
Update tests tied only to retired internals when necessary, retaining their behavioral assertions
at the new boundary. Do not change expected outputs to conceal a regression. Check the selected
benefit separately: passing compatibility tests alone does not establish a better design.

For a small input domain, exhaust bounded combinations against independent expectations. Use
property-based testing when a larger domain or stateful operation sequence warrants it; retain
named regression examples. Define the invariant and comparison budget before generating cases.
For streaming changes, check progress before full consumption and cleanup after consuming only a
prefix; returning an iterator alone does not prove incremental processing or bounded memory.
The parent skill owns performance verification.

[sourced] [Fowler's guard clauses](https://refactoring.com/catalog/replaceNestedConditionalWithGuardClauses.html),
[Extract Function](https://refactoring.com/catalog/extractFunction.html),
[Python expression semantics](https://docs.python.org/3/reference/expressions.html), and
[Hypothesis properties](https://hypothesis.readthedocs.io/en/latest/tutorial/introduction.html).
