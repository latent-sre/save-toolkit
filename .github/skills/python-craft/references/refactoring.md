# Improving existing Python

Improve what makes the code hard to understand, change, test, or trust; patterns serve that outcome.

## Contents

- Diagnose the design problem
- Establish behavior and consumers
- Choose a coherent change
- Example: make a calculation usable without files
- Preserve Python semantics
- Verify compatibility and improvement

## Diagnose the design problem

Inspect a representative path and its callers. Prioritize demonstrated defects and recurring
maintenance work, using code evidence rather than a questionnaire or smell score.

| Observed problem | Consider | Evidence of improvement |
|---|---|---|
| One policy is repeated across callers | Give the policy one owner | A rule change reaches every relevant caller |
| Calculations depend on I/O or globals | Separate decisions from effects | Test decisions independently; real entrypoints still use them |
| Parallel collections, flags, or loose data obscure meaning | Clarify data and ownership | Fewer invalid combinations; preserve boundary representations |
| Long functions or modules mix responsibilities | Reshape control flow or move coherent responsibilities | Follow a change without understanding unrelated operations |
| Helpers, classes, or compatibility layers add no useful boundary | Inline or remove them with their dead callers | Fewer concepts to navigate without losing supported behavior |
| Custom machinery duplicates an existing capability | Evaluate a library and necessary compatibility adapter | Remove superseded logic, not just add an import |

These are candidates, not prescriptions. Two occurrences can justify sharing one policy; three
similar-looking fragments may represent independently evolving rules. Compare purpose, inputs,
failure behavior, and reasons to change before consolidating them. Do not invent a configurable
framework to unify coincidental similarity.

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

## Choose a coherent change

Plan medium-sized, coherent stages around meaningful improvements and their checks. A stage may
reshape a component and its callers; reduce its size when risk or weak tests make it hard to verify.
Do not fragment work by function or file count. Keep unrelated cleanup and invented requirements out.

An extraction should expose a meaningful operation, dependency, or ownership boundary. If it just
relocates a confusing block and passes a bundle of unrelated state, reconsider the decomposition
or data model. A direct expression can be clearer than a named wrapper. A library replacement
needs the parent skill's modernization reference, not just a successful import.

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

The benefit is independent calculation and shared policy, not the comprehension or the line count.
An explicit loop is equally valid. Check empty/blank input, signed values, duplicates, one-pass
iterables, parse errors, string/keyword path callers, and file cleanup on failure. If no caller or
test benefits from the new boundary, do not manufacture one merely to split a short function.

## Preserve Python semantics

Choose transformations with their specific risks in view:

- **Rename or move:** preserve supported positional/keyword-only call rules, defaults, public import
  paths, patch locations, registries, and import-time effects; check circular imports and dynamic lookup.
- **Guards, extraction, or inlining:** retain condition/effect order and cleanup. Returning from a
  helper does not return from its caller; moved `break`/`continue` must preserve their loop effect.
  Zero, `None`, false, and empty values are not interchangeable.
- **Dispatch or collections:** check missing keys, hashability, equal/duplicate keys, ordering,
  mutation, and eager evaluation. Store callables rather than calls when only the selected operation
  should execute. `mapping.get(key, expensive_default())` evaluates the default even on a hit.
  Ranges, overlapping predicates, or ordered fallbacks may be clearer as conditionals.
- **Comprehensions or generators:** keep loops for multi-step work, effects, or per-item failures.
  Comprehension variables do not leak like loop variables. Generators defer work/errors but evaluate
  their outermost iterable immediately; they change repeatability, indexing, and length. A generator
  cannot consume a file closed by its producer. `any`/`all` may skip effects after short-circuiting.

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

Finally, demonstrate the selected benefit: one policy owner, testable decisions, removed layers,
or a simpler path for the requested next change. Compatibility alone does not establish improvement;
the parent skill owns project checks, performance evidence, and the final report.

[sourced] [Fowler's guard clauses](https://refactoring.com/catalog/replaceNestedConditionalWithGuardClauses.html),
[Extract Function](https://refactoring.com/catalog/extractFunction.html),
[Python expression semantics](https://docs.python.org/3/reference/expressions.html), and
[Hypothesis properties](https://hypothesis.readthedocs.io/en/latest/tutorial/introduction.html).
