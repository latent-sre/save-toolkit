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

- Trigger: a fragment needs a comment to explain it, repeats, or sits at a different level of
  detail. Inline when the body is as clear as the name or the wrapper only forwards.
- Preconditions: the fragment's inputs, outputs, and mutated variables are known; tests cover it.
- Transformation: move the fragment into a named function that takes its inputs as parameters and
  returns its outputs; replace the original with the call. To inline, substitute the body at each
  call site and delete the function once no reference remains.
- Verification: focused tests; unchanged evaluation order and mutation; reference inventory empty
  before deleting an inlined function.
- Avoid when: extraction needs many parameters or output variables (use Split Phase or Extract
  Class), or an inlined function is public, patched in tests, or registered by name.

### Extract Variable / Inline Variable

- Trigger: an expression is hard to read or repeats. Inline when the name adds nothing.
- Preconditions: the expression has no side effects, or it is evaluated exactly once and in the
  same order.
- Transformation: assign the expression to a well-named local; replace occurrences.
- Verification: tests; no change in evaluation count or order of side-effecting calls.
- Avoid when: hoisting would evaluate a short-circuited or conditional expression unconditionally.

### Extract Class / Inline Class

- Trigger: a subset of data and behavior changes together and apart from the rest of the class.
  Inline when a class no longer carries enough responsibility to justify itself.
- Preconditions: the cohesive subset and its callers are identified.
- Transformation: create the class (often a dataclass), move fields and methods, delegate from the
  original until callers move, then remove the delegation. Inline in reverse.
- Verification: tests; pickled or serialized forms and `__repr__` consumers still valid; public
  attributes still reachable or the break is authorized.
- Avoid when: the split only reorganizes code that changes together, or adds a class per function.

### Extract Module / Move Symbol

- Trigger: a module mixes unrelated responsibilities, or a symbol is used mostly by another module.
- Preconditions: complete reference inventory; import graph known.
- Transformation: create the destination module and move the implementation. Update internal
  callers to the new path. At the old path, keep a compatibility re-export (optionally with a
  `DeprecationWarning`) for every published or dynamically referenced name. Update configuration
  strings, entry points, and registries you own. Keep exactly one implementation. A class whose
  module path is persisted (pickles, stored type names) stays defined at that path unless a data
  migration is authorized: new pickles record the new module path even with a re-export at the
  old one.
- Verification: import each touched module in a fresh process and in both import orders; resolve
  every string path and entry point; tests; search confirms one implementation.
- Avoid when: the move would create an import cycle (move the shared piece lower first), or the
  only gain is a different folder.

### Rename Symbol / Change Function Declaration

- Trigger: a name misleads, or parameters are in the wrong order, missing, or unused.
- Preconditions: reference inventory, including keyword-argument call sites and string references.
- Transformation: use a symbol-aware rename where available. For a signature change, add the new
  form, migrate callers, then remove the old form. For public functions, keep the old name or
  keyword working for a deprecation period, or obtain authorization for the break.
- Verification: type checker over callers; tests; string and keyword references resolved.
- Avoid when: the name is persisted in data, configuration, or external clients and no migration
  is authorized.

### Introduce Parameter Object

- Trigger: the same group of parameters travels through several functions.
- Preconditions: the group is cohesive and has invariants worth stating.
- Transformation: define a frozen dataclass (or `NamedTuple` when tuple behavior is needed),
  validate invariants in it, change signatures one caller chain at a time.
- Verification: tests; type checker; validation errors raised at the same point as before or
  earlier with the change recorded.
- Avoid when: the parameters appear together only once.

### Split Phase

- Trigger: one routine parses, computes, and renders or writes, so a new input or output format
  means copying the computation.
- Preconditions: characterization tests over every existing output path.
- Transformation: compute an intermediate data structure (dataclass or plain typed structure) in
  one phase and consume it in the next. Make each renderer or writer a function of that structure.
- Verification: byte-for-byte comparison of existing outputs against the original over
  representative inputs; the shared phase runs once per request.
- Avoid when: the phases share almost nothing and the routine is short.

### Separate Query from Modifier

- Trigger: a function returns a value and also changes state, so callers cannot ask without acting.
- Preconditions: callers that rely on the combined behavior are known.
- Transformation: create a side-effect-free query; make the modifier return nothing or a status;
  update callers to call both in the original order.
- Verification: tests on both functions; side-effect order unchanged for existing callers.
- Avoid when: atomicity requires the combined operation (compare-and-set, pop); keep it and name it
  accordingly.

### Decompose Conditional / Consolidate Conditional

- Trigger: a condition or branch body needs reading twice; several conditions yield the same result.
- Preconditions: each branch is covered by a test.
- Transformation: extract the condition and branches into named predicates or functions; merge
  conditions with the same outcome into one named predicate.
- Verification: branch-by-branch tests, including boundary values.
- Avoid when: merging hides a distinction a future change needs, or evaluation order of
  side-effecting predicates would change.

### Guard Clauses

- Trigger: nesting exists only to handle special cases before the main path.
- Preconditions: special-case behavior is tested.
- Transformation: return or raise early for each special case; leave the main path unindented.
- Verification: tests for each early exit; resources still released on every path (use `with`).
- Avoid when: early returns would skip required cleanup that is not in a `finally` or context
  manager.

### Replace Conditional with Polymorphism or a dispatch table

- Trigger: the same switch on a type or kind repeats in several places, and variants actually
  differ in behavior.
- Preconditions: the variants and the operations that differ are enumerated.
- Transformation: use a mapping from key to function for behavior-only variation, `singledispatch`
  for type-based variation, or classes when variants also carry state. Fail loudly for unknown keys
  where the original did.
- Verification: a test per variant and for the unknown case.
- Avoid when: the switch occurs once, or there are two stable variants; a plain conditional is
  clearer.

### Parameterize Function / Consolidate Duplication

- Trigger: functions or branches differ only in literal values or a small step, and are meant to
  behave the same way.
- Preconditions: the copies' differences are listed and confirmed intentional or accidental.
  Accidental drift is a bug: record it and decide separately.
- Transformation: create one implementation with the difference as a parameter; point each copy at
  it; delete the copies.
- Verification: each former copy's tests pass against the shared implementation; one authoritative
  implementation remains.
- Avoid when: the similarity is coincidental and the copies are expected to diverge.

### Encapsulate Mutable State / Make Dependencies Explicit

- Trigger: module-level mutable state, singletons, caches, or hidden calls to the clock,
  environment, network, or filesystem make behavior depend on history or the host.
- Preconditions: every reader and writer of the state is in the inventory.
- Transformation: move state into an object with an explicit owner and lifetime, or pass it as a
  parameter; pass dependencies (clock, client, path) in at the entry point with defaults that keep
  existing callers working.
- Verification: tests that run in any order and in isolation; repeated calls with different inputs
  no longer interfere; existing callers unchanged.
- Avoid when: the state is a deliberate process-wide cache with tested invalidation, and the change
  only moves it.

### Remove Middle Man / Collapse Abstraction

- Trigger: a class, factory, provider, manager, or abstract base adds a layer without behavior,
  has one implementation, and no stated variation is coming.
- Preconditions: the public entry points and their callers are known; the "no other
  implementation" claim is checked against plugins, tests, and documentation.
- Transformation: point callers at the real implementation; inline forwarding layers; replace a
  single-implementation abstract base with the concrete type or a `Protocol` only where a test
  double needs it; delete emptied modules.
- Verification: public entry points behave identically; the forwarding layers are gone and callers
  reach the implementation directly; no dangling imports; tests pass.
- Avoid when: the layer is a published extension point, or real variation is planned and dated.

### Replace Inheritance with Delegation

- Trigger: a subclass uses part of a base class, overrides to disable behavior, or inherits only to
  reuse code.
- Preconditions: callers that rely on `isinstance` or the base's methods are known.
- Transformation: hold the former base as a field; forward only the needed methods; remove the
  inheritance.
- Verification: `isinstance` and type-checker expectations satisfied or authorized to change; tests.
- Avoid when: the subtype truly is substitutable for the base.

### Introduce Test Boundary

- Trigger: logic cannot be tested without real I/O, time, or randomness.
- Preconditions: the boundary operations are listed.
- Transformation: separate pure logic from I/O; pass the I/O operation or a small adapter in at the
  boundary; keep the production default. Prefer a fake implementing the narrow interface over deep
  mocking.
- Verification: unit tests for the logic without I/O; a contract or integration test for the real
  adapter.
- Avoid when: the boundary exists only for one test that a temporary directory or local fixture
  could serve.

### Preparatory Refactoring

- Trigger: the requested feature would otherwise be added by copying a branch or threading a flag
  through several layers.
- Preconditions: the feature's target shape is known.
- Transformation: first restructure with behavior unchanged and verified; then add the feature as
  a small, separately verified change.
- Verification: the refactor step passes the existing and characterization tests alone, before
  the feature step.
- Avoid when: the feature fits the current shape cleanly.

### Incremental Replacement

- Trigger: a bespoke component or a dependency should be replaced, and a single switch is too
  risky.
- Preconditions: the old component's used surface is inventoried; differential tests compare the
  old and new behavior on the same inputs.
- Transformation: introduce a seam that both implementations satisfy, route callers through it,
  migrate callers or traffic in steps, and switch fully when the cutover conditions hold.
- Verification: differential tests at each step; the cutover conditions measured, not assumed.
- Avoid when: the component is small enough to replace and verify in one step.

### Remove Dead Code

- Trigger: code appears unused.
- Preconditions: static search and the full reference inventory find no use; dynamic use is ruled
  out (registries, entry points, configuration, reflection, external callers of a published API).
  Where available, add runtime evidence: coverage under representative runs, entry-point usage, or
  logs. Dead-code finders give candidates, not proof.
- Transformation: delete the code and its tests; for a published API, deprecate first unless
  removal is authorized.
- Verification: tests; fresh imports; entry points resolve; the package builds.
- Avoid when: use cannot be ruled out; record it as a candidate instead.

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
