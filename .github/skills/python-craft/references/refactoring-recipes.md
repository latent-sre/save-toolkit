# Refactoring recipes

## Contents

- Problem-to-Technique Decision Table
- Operational Refactoring Recipes (R1–R19)

Use [refactoring](./refactoring.md) for consumer contracts, characterization, migration sequencing
and Python hazards. Read only the recipes matching the observed problem.

## Problem-to-Technique Decision Table

Sequence several recipes when one improvement needs staged restructuring. Read every applicable
recipe in full.

| Observed problem | Recipe(s) |
|---|---|
| Long function mixing sub-steps, or trivial one-line indirection | R1 |
| Opaque repeated sub-expression, or pointless temporary | R2 |
| God class with unrelated state, or degenerate class with no responsibility | R3 |
| Module mixing responsibilities, or symbol in the wrong module | R4 |
| Misleading names or drifted signatures | R5 |
| Same parameter clump across functions | R6 |
| One pass interleaving parsing, validation, IO, and calculation | R7 |
| Function both returns a value and mutates state | R8 |
| Nested conditionals or scattered checks with the same outcome | R9, R10 |
| Same type/mode switch repeated across several operations | R11 |
| Near-identical functions differing by constants or policy | R12 |
| Module globals, mutable defaults, hidden clock/env/client reads | R13 |
| Wrappers, factories, or managers that only forward calls | R14 |
| Inheritance used only for code reuse | R15 |
| Policy coupled to files, sockets, subprocesses, or ORM sessions | R16 |
| A feature or fix would multiply branching in tangled code | R17 |
| Bespoke component or library needing replacement | R18 |
| Unused functions, classes, shims, or branches | R19 |

## Operational Refactoring Recipes

### R1. Extract and Inline Function
- **Trigger:** A block needs a comment to explain it or repeats a sub-step (*Extract*); a helper is no
  clearer than its body (*Inline*).
- **Preconditions:** Check local mutations, `nonlocal`/`global`, `yield`/`await`, and
  `return`/`break`/`continue` inside the block; an extracted `return` no longer exits the caller.
- **Transformation:** Lift the block into a function with explicit inputs and returned values, or
  replace call sites with the body and delete the helper.
- **Verification:** Cover every branch and exception path of the caller.
- **Avoid when:** Extraction needs 6+ mutable locals (apply R6/R7 first), or the helper is a public
  hook or documented `mock.patch` seam.

### R2. Extract and Inline Variable
- **Trigger:** A compound expression is hard to read or repeats; a temporary adds nothing.
- **Preconditions:** The expression is side-effect-free and moving it keeps short-circuit order.
- **Transformation:** Bind it to a descriptive local, or substitute a single-use temporary inline.
- **Verification:** Focused tests and the type checker.
- **Avoid when:** Repetition intentionally re-evaluates after mutation, or hoisting past `and`/`or`
  would raise (`ZeroDivisionError`, `AttributeError`).

### R3. Extract and Inline Class
- **Trigger:** Field/method subsets change independently (*Extract*); a class has one method or no
  independent state (*Inline*).
- **Preconditions:** Check `isinstance`/`issubclass` use, serialization schemas, and public exports.
- **Transformation:** Move cohesive fields and methods into a collaborator `@dataclass` and delegate,
  or fold the degenerate class into its caller and delete it.
- **Verification:** Unit and serialization/contract tests.
- **Avoid when:** External code subclasses the original and no compatibility alias remains.

### R4. Extract Module and Move Function/Class/Symbol
- **Trigger:** A module mixes sub-domains, or a symbol belongs with another module's data.
- **Preconditions:** Check `__all__`, `[project.scripts]`/entry points, `importlib` strings, and
  `mock.patch("pkg.old_mod.sym")` targets; apply [refactoring tools](./refactoring-tools.md).
- **Transformation:** Move the symbol and its private helpers; update internal imports,
  `package/__init__.py`, and dynamic target strings. Retain a re-export for supported consumers of the original
  module (`from .new_mod import sym as sym`, or list it in `__all__`) unless breaking the
  old path is explicitly requested.
- **Verification:** Fresh-process imports in both orders (`python -c "import a, b"` and
  `"import b, a"`), dynamic lookups, and the full suite.
- **Avoid when:** The move creates a source/destination cycle; extract shared types to a leaf module
  first.

### R5. Rename Symbol and Change Function Declaration
- **Trigger:** A name misleads about effects or return type, or parameters need adding, removing,
  reordering, or keyword-only `*`.
- **Preconditions:** Enumerate call sites, overrides, `Protocol` definitions, and `**kwargs` callers.
- **Transformation:** For public or multi-caller symbols, migrate in two steps: add the new form
  (default or alias), migrate callers, then remove the old form.
- **Verification:** Type checker for signature mismatches, then tests.
- **Avoid when:** It breaks a published API or CLI flag outside authorized scope.

### R6. Introduce Parameter Object
- **Trigger:** Three or more parameters travel together across several signatures.
- **Preconditions:** Check whether callers mutate individual arguments or rely on positional order.
- **Transformation:** Group them in a `@dataclass(frozen=True, slots=True)` with validation in
  `__post_init__`, and accept the object.
- **Verification:** Type checker plus valid and invalid value tests.
- **Avoid when:** It becomes a generic `Context`/`Options` bag hiding what each function reads.

### R7. Split Phase
- **Trigger:** One function interleaves parsing/IO, validation, calculation, and output.
- **Preconditions:** Check streaming/memory limits and error ordering between malformed input and
  calculation failures.
- **Transformation:** Split into parse/validate → pure calculation → format/persist, connected by
  typed records (or bounded generator stages for large streams).
- **Verification:** Test the calculation in memory; run end-to-end tests for IO and error order.
- **Avoid when:** Materializing the whole stream in phase 1 would break memory bounds.

### R8. Separate Query from Modifier
- **Trigger:** A function returns an answer and mutates state (`get_and_clear_alerts()`).
- **Preconditions:** Check whether the check-and-set must be atomic.
- **Transformation:** Split into a side-effect-free query and a separate command.
- **Verification:** Repeated queries return identical results without state drift.
- **Avoid when:** Splitting an atomic compare-and-swap or queue `pop` would introduce a race.

### R9. Decompose and Consolidate Conditionals
- **Trigger:** Complex predicates obscure the rule, or sequential branches share one outcome.
- **Preconditions:** Check short-circuit order and side effects in condition calls.
- **Transformation:** Name predicates (`is_eligible_for_rebate(fill)`); merge identical-outcome
  branches with `or`/`and` or `match`.
- **Verification:** Boundary values for every condition.
- **Avoid when:** Merging erases diagnostics callers need to tell apart.

### R10. Introduce Guard Clauses
- **Trigger:** The normal path is buried several nesting levels deep.
- **Preconditions:** Early exits must not skip cleanup; move cleanup into `with`/`try/finally` first.
- **Transformation:** Reject invalid or no-op cases at the top by returning or raising; keep the main
  path flat. Negate conditions literally (see Guard-clause and truthiness inversion below).
- **Verification:** Test each early exit and the main path.
- **Avoid when:** Required single-exit post-processing cannot move into a context manager.

### R11. Replace Conditional Dispatch with Polymorphism
- **Trigger:** Several functions switch on the same `kind`, and each new variant edits every switch.
- **Preconditions:** Variation is behavioral across operations, not one constant lookup.
- **Transformation:** Use a `typing.Protocol` or small class per variant, or a mapping of callables
  when stateless; route calls through it.
- **Verification:** Run every variant against a shared contract test.
- **Avoid when:** One function branches, or a `dict[Kind, Decimal]` table suffices.

### R12. Parameterize Function and Consolidate Genuine Behavioral Duplication
- **Trigger:** Functions implement the same policy with different constants or minor steps.
- **Preconditions:** The duplication is one shared rule, not independent rules that look alike.
- **Transformation:** Create one authoritative function parameterized by the varying values or a
  policy callable; route every entry point through it and delete the copies.
- **Verification:** A policy change in one place reaches all entry points; test each caller's values.
- **Avoid when:** Merging needs boolean mode flags that read worse than two short functions.

### R13. Encapsulate Mutable State and Make Dependencies Explicit
- **Trigger:** Functions use module globals, mutable defaults (`def f(x=[])`), or implicit
  `os.environ`/`datetime.now()`.
- **Preconditions:** Find every reader/writer and whether any caller or test imports the global.
- **Transformation:** Use `x: list[str] | None = None` with a fresh list in the body. When consumer inspection establishes a mutable
  global is private (including dynamic references), MUST delete it and its
  `.append()`/`.clear()` mutations, replacing it with a local accumulator or explicit state object.
  Inject clock/config/env as parameters.
- **Verification:** Call repeatedly in one process; prove no cross-call leakage or aliasing of
  returned collections.
- **Avoid when:** The module value is genuinely immutable (`Final`, `frozenset`, `tuple`).

### R14. Remove Middle Man and Simplify Unnecessary Abstractions
- **Trigger:** `*Manager`/`*Service`/`*Factory`/`*Proxy` classes only forward, or an `ABC` has one
  implementation.
- **Preconditions:** Confirm the wrapper enforces no security, transaction, caching, or published API
  boundary.
- **Transformation:** When modifying or cleaning up such a module, collapse and delete the wrappers
  instead of threading new parameters through them; call the implementation directly.
- **Verification:** Public entry points work and tests pass without the removed classes.
- **Avoid when:** It is an active isolation boundary or a plugin seam with external implementations.

### R15. Replace Unnecessary Inheritance with Delegation or Composition
- **Trigger:** A subclass exists to reuse a helper, inherits meaningless methods, or breaks base
  invariants.
- **Preconditions:** Check callers that test `isinstance(obj, Base)`.
- **Transformation:** Hold the collaborator as an attribute (or call a function) and delegate only
  what is needed.
- **Verification:** Type checker and behavioral tests.
- **Avoid when:** It is a true subtype or framework-required (`Exception`, `Enum`, `BaseModel`).

### R16. Introduce Narrow Testing or Integration Boundaries
- **Trigger:** Testing a rule needs a database, server, filesystem tree, or many internal mocks.
- **Preconditions:** Separate the data the rule needs from the transport.
- **Transformation:** Make the policy accept in-memory data (iterables, dataclasses, text streams);
  leave a thin IO adapter.
- **Verification:** Unit-test the policy without mocks; one integration test on the adapter.
- **Avoid when:** The function is already pure.

### R17. Preparatory Refactoring Before Implementing a Feature
- **Trigger:** Adding the change directly would copy branches, thread globals, or worsen tangling.
- **Preconditions:** Existing behavior is covered by baseline or characterization tests.
- **Transformation:** Step 1: behavior-preserving restructuring (R7, R12, R13). Step 2: the feature
  and its tests on the cleaned structure.
- **Verification:** Step 1 passes existing tests unchanged; step 2 passes existing and new tests.
- **Avoid when:** The preparation grows into an unbounded rewrite of unrelated modules.

### R18. Incremental Component or Dependency Replacement
- **Trigger:** Replacing a bespoke parser/client/validator (including when a bug exposes a broken
  hand-rolled TOML/JSON/CSV/URL parser) or a deprecated library.
- **Preconditions:** Verify target semantics in [libraries and modernization](./libraries-and-modernization.md); define cutover
  criteria.
- **Transformation:** Instead of patching the custom parser, put the stdlib module (`tomllib`,
  `json`, `csv`, `urllib.parse`) or maintained package behind the existing function, translate its
  exceptions (`raise ConfigError(...) from exc`), and delete the custom code.
- **Verification:** Differential tests over normal, empty, malformed, and boundary inputs; no
  references to the retired code remain.
- **Avoid when:** Old and new would both stay active with no completed cutover.

### R19. Remove Dead Code After Checking Static and Dynamic Usage
- **Trigger:** Uncalled code, obsolete flags, or retired shims.
- **Preconditions:** Search static references and dynamic mechanisms (`getattr`, `globals()`,
  `__all__`, entry points, templates, config, registries). Treat `vulture`/`deptry` output as leads:
  confirm the detector flags a known leftover before trusting a clean run.
- **Transformation:** Delete the symbol, its imports, and tests that only exercised it.
- **Verification:** Tests, linter (`F401`/`F841`), type checker, and import checks.
- **Avoid when:** It is public API (`__all__`) or invoked by external plugins/config.

