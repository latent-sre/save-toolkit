# Improving existing Python

## Choose the transformation

Share a policy only when callers need the same rule; identical fragments may evolve independently.
A helper beside copies still in use does not establish shared ownership. Judge a transformation
through callers, including construction/conversion costs and memory, not its shorter spelling.

## Simplify control flow and iteration

- Short-circuit replacements can skip effects/errors; use a sentinel when `None` is a valid result.
- `zip` truncates unless strict; indexing/grouping replacements can change duplicate handling,
  equality/hashability, ordering, missing-key insertion and result types.
- Dispatch tables do not preserve ordered/range predicates; `match` bare names capture rather than compare.
- Lazy replacements move work/errors and may lose repeatability. Cleanup restructuring must preserve
  partial acquisition, release order, cancellation and exception suppression.

An extracted `return` does not return from its caller; preserve moved `break`/`continue` effects.
Comprehension iteration variables do not leak like loop variables. Generator expressions evaluate
the outermost iterable immediately; generator-function bodies wait for resumption. Neither can
consume a file closed by its producer. `mapping.get(key, expensive_default())` evaluates the default
even on a hit; dispatch tables should store callables rather than their results.

### Guard-clause example

For an accepted condition `limit is None or limit >= 0`, reject with
`not (limit is None or limit >= 0)`. Substituting `limit is not None and limit < 0` changes NaN
behavior: both comparisons are false. `if not limit` confuses zero with absence. Invalid inputs
must fail before the effect; valid inputs reach it once, unchanged.

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

## Stage a large or multi-module change

Map consumers before choosing the boundary, including release inputs and non-code consumers such as
configured names and package data. For an unresolved rollout, compatibility, or recovery design,
use the project's design workflow; load `eng-ladder` for principal-level design guidance.

1. Complete a real consumer path before widening; dormant helpers can pass tests while callers
   still use old policy.
2. Add compatibility bridges only when supported consumers, mixed versions, or persisted data need
   them, and define when each can be removed. Mark a bridge with
   `warnings.deprecated` (3.13+; `typing_extensions.deprecated` before that): it warns at runtime,
   and type checkers can list remaining callers; mypy does so only with its `deprecated` error code
   enabled.
3. Retire superseded code and dependencies after callers and release inputs use the replacement.
   Find leftovers with an instrument and read its hits as leads: the type checker and text searches
   for callers, `vulture` for unreferenced definitions, `deptry` for declared dependencies nothing
   imports. Entry points, registries, and dynamic lookups look unused to static tools; confirm a
   detector reports a known leftover before trusting its clean run.
   For module-layout, entrypoint, or package-data changes, build the project's actual release
   artifact and exercise an installation outside the source checkout. Check imports, configured
   lookups, and bundled resources there; checkout tests can conceal missing release files.

Choose checkpoints by risk, not file counts; a small atomic replacement may be safer than a bridge.

## Characterization pitfalls

Characterize values, types, exceptions, effects and cleanup before restructuring. Equality can hide a
changed type (`0 == Decimal("0")`); preserve empty-result type and one-pass input behavior. Keep raised
outcomes raised rather than returning error strings. Record known bugs separately from required behavior.

## Verify behavior and benefit

Use coverage or reversible mutation when reach/sensitivity is uncertain, not universally. Working
behavior needs no red-first test; bug fixes need independent expectations.

Compare fresh equivalent inputs and controlled time, randomness, effects, and caches. Check relevant
values/types, serialization, aliasing/mutation, call forms, errors, and effect order. Preserve the
exception object when propagating it. Pair differential checks with independent expectations so an
old bug cannot count as correctness. Use fresh processes for relevant import orders, cycles, and
registries. Exercise existing entrypoints; retain behavioral assertions when retiring test wiring.

For streaming, check progress before full consumption and cleanup after a prefix; returning an
iterator proves neither streaming nor bounded memory.

Show the benefit through actual callers: a shared policy replaces copies, a calculation works without
I/O, conversions/layers disappear, or a real change becomes simpler. Profile and benchmark when
performance motivates the design; compatibility tests alone do not establish improvement.
