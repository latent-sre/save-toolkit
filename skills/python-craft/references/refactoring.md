# Improving existing Python

## Contents

- Choose the transformation
- Simplify control flow and iteration
- Preserve consumers and integrate
- Stage a large or multi-module change
- Characterization pitfalls
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
qualified names; an underscore does not prove a name is private. Search for qualified names as text
too (`"pkg.module.name"`, entry-point `"pkg.module:name"`) across code, configuration, and package
metadata; a rename tool or language server resolves only static references. Controlled internal
signatures and shapes may change with their callers. Preserve supported call forms/defaults,
import-time effects, and public patch points. An explicit `lazy import` (3.15) defers the imported
module's import-time effects until first use; adding or removing one moves them. Add compatibility
adapters only for actual supported consumers.

Avoid leaving callers with repeated shape conversions or copies of moved policy. A moved function
is not an integrated change until its real consumers use the new owner.

## Stage a large or multi-module change

Map consumers before choosing the boundary, including release inputs and non-code consumers such as
configured names and package data. For an unresolved rollout, compatibility, or recovery design,
use the project's design workflow; load `eng-ladder` for principal-level design guidance.

1. Map each material risk to an existing check or a missing regression before changing structure.
2. Complete one path through a real consumer before widening, then migrate the rest in coherent
   stages. Move the rule's ownership, not just its text: dormant helpers and duplicated decisions
   can pass tests while callers still use the old copy.
3. Add compatibility bridges only when supported consumers, mixed versions, or persisted data need
   them, and define when each can be removed. Mark a bridge with
   `warnings.deprecated` (3.13+; `typing_extensions.deprecated` before that): it warns at runtime,
   and type checkers can list remaining callers; mypy does so only with its `deprecated` error code
   enabled.
4. Retire superseded code and dependencies after callers and release inputs use the replacement.
   Find leftovers with an instrument and read its hits as leads: the type checker and text searches
   for callers, `vulture` for unreferenced definitions, `deptry` for declared dependencies nothing
   imports. Entry points, registries, and dynamic lookups look unused to static tools; confirm a
   detector reports a known leftover before trusting its clean run.
   For module-layout, entrypoint, or package-data changes, build the project's actual release
   artifact and exercise an installation outside the source checkout. Check imports, configured
   lookups, and bundled resources there; checkout tests can conceal missing release files.

Choose checkpoints by risk, not file counts; a small atomic replacement may be safer than a
compatibility layer. Report the checks completed and any installation or downstream coverage missing.

## Characterization pitfalls

Characterize values, types, exceptions, effects and cleanup before restructuring. Equality can hide a
changed type (`0 == Decimal("0")`); preserve empty-result type and one-pass input behavior. Keep raised
outcomes raised rather than returning error strings. Record known bugs separately from required behavior.

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
