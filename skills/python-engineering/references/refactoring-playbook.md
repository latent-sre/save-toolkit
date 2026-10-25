# Refactoring playbook

Read everything before the Recipes heading, then the complete recipe for every technique you
select. The recipes cover the baseline techniques; use another verified technique when the actual
problem needs it, and record the reason.

## Contents

- Procedure
- Reference inventory
- Contracts to preserve
- Python hazards
- Decision table
- Recipes (Trigger | Preconditions | Transformation | Verification | Avoid when)
- Large and incremental changes
- Re-verify

## Procedure

1. Name the structural problem and the intended benefit in one sentence each. If you cannot,
   do not refactor.
2. Choose the target design, then the smallest sequence of techniques that reaches it. Consider
   removing structure as seriously as adding it.
3. Inventory references (below) for every symbol you will move, rename, inline, or delete.
4. Establish behavioral evidence. When the code is poorly tested, write characterization tests that
   pass against the original before changing it:
   - Cover observable outputs, raised exception types and messages that callers match, side
     effects, and the odd cases: boundaries, empty and `None` inputs, negative and duplicate
     values, quirks that look like bugs.
   - Prove the tests detect change: alter one quirk temporarily in the original and confirm a test
     fails, then restore it.
   - Pin exact output (golden strings or files) where callers or people consume text.
5. Apply one technique at a time. Run the focused tests after each step; keep the code working
   between steps.
6. Record discovered bugs separately. Preserve them during the refactor unless fixing them is
   authorized; fix them in a separate, separately verified step.
7. Do not mix refactoring with a bug fix, a dependency migration, or a public API redesign in one
   step. Sequence them: preparatory refactor, then behavior change, then cleanup.

## Reference inventory

Search for each affected name in all of these before changing it. Text search is the inventory,
not the edit mechanism:

- Static callers, imports, and `from x import y` re-exports, including `__init__.py`, `__all__`,
  and star imports.
- Entry points and scripts in `pyproject.toml` or `setup.cfg`, console scripts, and plugin
  registrations.
- Dotted-path strings in configuration, settings, environment defaults, task queues, logging
  configuration, and serialized job payloads.
- Dynamic access: `getattr`, `importlib.import_module`, `__import__`, registries keyed by name,
  `globals()` lookups.
- Test references: `mock.patch("pkg.module.name")` targets, fixtures, and snapshot files.
- Persisted forms: pickled objects, which store module and class paths; JSON or database values
  holding class or enum names; migration files.
- Documentation and examples that users copy.

## Contracts to preserve

Unless the task authorizes a change, keep: return values and types, raised exception types and
the messages callers match, side effects and their order, mutation of arguments, output text and
encoding, serialization formats and field names, CLI arguments, exit codes, stdout and stderr,
public import paths, thread-safety and async behavior, resource ownership, laziness, and
performance characteristics that callers rely on.

## Python hazards

| Hazard | Check before and after |
|---|---|
| Decorators and wrappers | Moved or renamed functions keep decorator order, `functools.wraps` metadata, registration side effects, and `__wrapped__` access |
| Dynamic imports and reflection | Every string path and `getattr` name from the inventory still resolves |
| Public re-exports and entry points | Old import paths and entry-point targets still import, or the break is authorized and documented |
| Import-time behavior | Module-level code still runs once, in a valid order; no new circular import; import each touched module in a fresh process |
| Mutation and aliasing | Extracted code mutates the same objects, and only those; default arguments are not shared mutable objects; copies versus views unchanged |
| Evaluation order | Short-circuiting, argument evaluation, and side-effect order unchanged, including which `KeyError` fires first on malformed input |
| Floating point | Accumulation order unchanged unless verified: `sum()` over floats is not guaranteed to match a `+=` loop |
| Exceptions | Same types propagate; no new broad `except`; context preserved with `raise ... from` |
| Serialization | Pickle paths, dataclass field order, enum values, JSON keys, and `__repr__` used in logs or tests unchanged |
| Async and concurrency | Cancellation still propagates; locks, timeouts, and task lifetimes unchanged; no blocking call moved into the event loop |
| Resource lifetimes | Files, connections, generators, and context managers close at the same point; laziness preserved |

## Decision table

| Problem observed | Techniques |
|---|---|
| Long function mixing levels of detail | Extract Function, Split Phase, Decompose Conditional |
| Function body no clearer than its name, or needless indirection | Inline Function, Inline Variable, Remove Middle Man |
| Complex expression or repeated sub-expression | Extract Variable |
| Class doing two jobs, or data clumps traveling together | Extract Class, Introduce Parameter Object |
| Class or module with no remaining job | Inline Class, Remove Middle Man, Collapse Abstraction |
| Module grab bag, or code in the wrong module | Extract Module, Move Symbol |
| Misleading name or awkward signature | Rename Symbol, Change Function Declaration |
| Parse-compute-render tangled in one routine | Split Phase |
| Function both returns data and changes state | Separate Query from Modifier |
| Deep nesting or tangled conditions | Guard Clauses, Decompose Conditional, Consolidate Conditional |
| Same type switch repeated in several places | Replace Conditional with Polymorphism or a dispatch table |
| Near-duplicate functions or branches | Parameterize Function, Consolidate Duplication |
| Global or shared mutable state, hidden dependencies | Encapsulate Mutable State, Make Dependencies Explicit |
| Abstraction with one implementation and no planned variation | Collapse Abstraction, Inline Class, Remove Middle Man |
| Inheritance used only for reuse | Replace Inheritance with Delegation |
| Code untestable without real I/O | Introduce Test Boundary |
| Feature hard to add to the current shape | Preparatory Refactoring |
| Bespoke component or dependency to replace | Incremental Replacement |
| Code believed unused | Remove Dead Code |

## Recipes

### Extract Function / Inline Function

- Trigger: a fragment needs a comment, repeats, or mixes levels of detail. Inline when the body is
  as clear as the name or the wrapper only forwards.
- Preconditions: the fragment's inputs, outputs, and mutated variables are known; tests cover it.
- Transformation: move it into a named function that takes its inputs and returns its outputs. To
  inline, substitute the body at each call site, then delete the function.
- Verification: focused tests; evaluation order and mutation unchanged; no references remain
  before deleting.
- Avoid when: it needs many parameters or outputs (use Split Phase or Extract Class), or the
  inlined function is public, patched in tests, or registered by name.

### Extract Variable / Inline Variable

- Trigger: an expression is hard to read or repeats. Inline when the name adds nothing.
- Preconditions: no side effects, or evaluated exactly once in the same order.
- Transformation: assign it to a named local and replace the occurrences.
- Verification: tests; evaluation count and order of side effects unchanged.
- Avoid when: hoisting would evaluate a short-circuited or conditional expression unconditionally.

### Extract Class / Inline Class

- Trigger: a subset of data and behavior changes together, apart from the rest. Inline a class
  with too little responsibility left.
- Preconditions: the cohesive subset and its callers are known.
- Transformation: create the class (often a dataclass), move fields and methods, delegate until
  callers move, then drop the delegation. Inline in reverse.
- Verification: tests; serialized forms and `__repr__` consumers valid; public attributes still
  reachable or the break authorized.
- Avoid when: the split only reorganizes code that changes together.

### Extract Module / Move Symbol

- Trigger: a module mixes unrelated responsibilities, or a symbol is used mostly elsewhere.
- Preconditions: complete reference inventory; import graph known.
- Transformation: move the implementation and update internal callers. Keep a compatibility
  re-export (optionally warning) at the old path for every published or dynamically referenced
  name. Update configuration strings, entry points, and registries you own. Keep one
  implementation. Keep a class with a persisted path (pickles, stored type names) at that path
  unless a data migration is authorized; new pickles record the new path even with a re-export.
- Verification: import each touched module in a fresh process and in both orders; resolve every
  string path and entry point; tests; one implementation remains.
- Avoid when: it would create an import cycle (move the shared piece lower first), or only the
  folder changes.

### Rename Symbol / Change Function Declaration

- Trigger: a misleading name, or parameters in the wrong order, missing, or unused.
- Preconditions: inventory including keyword call sites and string references.
- Transformation: use a symbol-aware rename where available. For signatures, add the new form,
  migrate callers, remove the old. Keep public names or keywords working through a deprecation
  period unless the break is authorized.
- Verification: type check over callers; tests; string and keyword references resolved.
- Avoid when: the name is persisted in data, configuration, or external clients without an
  authorized migration.

### Introduce Parameter Object

- Trigger: the same parameter group travels through several functions.
- Preconditions: the group is cohesive and has invariants worth stating.
- Transformation: a frozen dataclass (or `NamedTuple` for tuple behavior) that validates its
  invariants; change one caller chain at a time.
- Verification: tests; type check; validation errors raised at the same point, or earlier with
  the change recorded.
- Avoid when: the group appears together only once.

### Split Phase

- Trigger: one routine parses, computes, and renders, so a new format means copying computation.
- Preconditions: characterization tests over every existing output path.
- Transformation: compute an intermediate typed structure in one phase; make each renderer or
  writer a function of it.
- Verification: existing outputs byte-identical to the original on representative inputs; the
  shared phase runs once per request.
- Avoid when: the phases share almost nothing and the routine is short.

### Separate Query from Modifier

- Trigger: a function returns a value and changes state, so callers cannot ask without acting.
- Preconditions: callers relying on the combined behavior are known.
- Transformation: a side-effect-free query plus a modifier returning nothing or a status; callers
  call both in the original order.
- Verification: tests on both; side-effect order unchanged.
- Avoid when: atomicity needs the combined operation (compare-and-set, pop).

### Decompose Conditional / Consolidate Conditional

- Trigger: a condition or branch needs reading twice, or several conditions share a result.
- Preconditions: each branch is tested.
- Transformation: name the predicates and branch bodies; merge same-outcome conditions into one
  predicate.
- Verification: branch-by-branch tests, including boundary values.
- Avoid when: merging hides a distinction a coming change needs, or changes the order of
  side-effecting predicates.

### Guard Clauses

- Trigger: nesting exists only to handle special cases before the main path.
- Preconditions: special cases are tested.
- Transformation: return or raise early per special case; leave the main path unindented.
- Verification: a test per early exit; resources released on every path.
- Avoid when: an early return would skip cleanup not held in `finally` or a context manager.

### Replace Conditional with Polymorphism or a dispatch table

- Trigger: the same type or kind switch repeats in several places, and variants truly differ.
- Preconditions: variants and differing operations enumerated.
- Transformation: a key-to-function mapping for behavior-only variation, `singledispatch` for type
  variation, classes when variants carry state; unknown keys fail as before.
- Verification: a test per variant and for the unknown case.
- Avoid when: the switch occurs once, or two stable variants read clearly as a conditional.

### Parameterize Function / Consolidate Duplication

- Trigger: functions or branches meant to behave alike differ only in values or a small step.
- Preconditions: differences listed and confirmed intentional or accidental; accidental drift is a
  bug to record and decide separately.
- Transformation: one implementation with the difference as a parameter; point the copies at it,
  then delete them.
- Verification: each former copy's tests pass against the shared implementation; one
  implementation remains.
- Avoid when: the similarity is coincidental and the copies will diverge.

### Encapsulate Mutable State / Make Dependencies Explicit

- Trigger: module-level mutable state, singletons, caches, or hidden clock, environment, network,
  or filesystem calls make behavior depend on history or host.
- Preconditions: every reader and writer is in the inventory.
- Transformation: give state an explicit owner and lifetime, or pass it in; pass dependencies in
  at the entry point with defaults that keep callers working.
- Verification: tests pass in any order and in isolation; repeated calls no longer interfere;
  callers unchanged.
- Avoid when: it is a deliberate process-wide cache with tested invalidation and the change only
  moves it.

### Remove Middle Man / Collapse Abstraction

- Trigger: a class, factory, provider, manager, or abstract base forwards without behavior, has
  one implementation, and no variation is stated.
- Preconditions: entry points and callers known; "no other implementation" checked against
  plugins, tests, and documentation.
- Transformation: point callers at the implementation, inline forwarding layers, replace a
  single-implementation base with the concrete type (or a `Protocol` only where a test double
  needs it), delete emptied modules.
- Verification: entry points behave identically; callers reach the implementation directly; no
  dangling imports; tests pass.
- Avoid when: the layer is a published extension point, or real variation is planned.

### Replace Inheritance with Delegation

- Trigger: a subclass uses part of its base, overrides to disable behavior, or inherits only for
  reuse.
- Preconditions: callers relying on `isinstance` or base methods are known.
- Transformation: hold the former base as a field, forward only what is needed, drop the
  inheritance.
- Verification: `isinstance` and type-check expectations kept or authorized to change; tests.
- Avoid when: the subtype truly substitutes for the base.

### Introduce Test Boundary

- Trigger: logic cannot be tested without real I/O, time, or randomness.
- Preconditions: the boundary operations are listed.
- Transformation: separate pure logic from I/O and pass the operation or a small adapter in,
  keeping the production default; prefer a narrow fake to deep mocking.
- Verification: logic tests without I/O; a contract or integration test for the real adapter.
- Avoid when: a temporary directory or local fixture serves the one test that needs it.

### Preparatory Refactoring

- Trigger: the feature would otherwise copy a branch or thread a flag through several layers.
- Preconditions: the feature's target shape is known.
- Transformation: restructure first with behavior unchanged and verified, then add the feature as
  a small separate change.
- Verification: the refactor step passes the existing and characterization tests on its own.
- Avoid when: the feature fits the current shape cleanly.

### Incremental Replacement

- Trigger: a bespoke component or dependency should be replaced, and one switch is too risky.
- Preconditions: the used surface is inventoried; differential tests compare old and new on the
  same inputs.
- Transformation: a seam both implementations satisfy; route callers through it; migrate in steps;
  switch when the cutover conditions hold.
- Verification: differential tests at each step; cutover conditions measured, not assumed.
- Avoid when: it is small enough to replace and verify in one step.

### Remove Dead Code

- Trigger: code appears unused.
- Preconditions: static search and the inventory find no use, and dynamic use is ruled out
  (registries, entry points, configuration, reflection, published API). Add runtime evidence where
  available: coverage on representative runs, entry-point usage, logs. Dead-code finders give
  candidates, not proof.
- Transformation: delete the code and its tests; deprecate a published API first unless removal is
  authorized.
- Verification: tests; fresh imports; entry points resolve; the package builds.
- Avoid when: use cannot be ruled out; record it as a candidate.

## Large and incremental changes

- Permit substantial cross-module restructuring and replacement of bespoke components when the
  decision row justifies it. Write down the target design and the ordered steps.
- For a staged migration, define the cutover conditions up front: which callers moved, which
  differential checks pass, and what the rollback is.
- When the purpose is complete, remove temporary adapters, duplicate paths, feature switches,
  compatibility shims you own, and migration scaffolding. Keep published compatibility re-exports
  for their announced deprecation period.

## Re-verify

Check these when an installed Python version or tool behaves differently from this file.

- [`sum()`: float summation changed in Python 3.12](https://docs.python.org/3/library/functions.html#sum)
- [Vulture: dynamic code and false positives](https://github.com/jendrikseipp/vulture)
- [Entry points specification](https://packaging.python.org/en/latest/specifications/entry-points/)
