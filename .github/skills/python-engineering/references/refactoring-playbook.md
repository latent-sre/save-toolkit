# Python Refactoring Playbook

## Contents

- Pre-Refactoring Protocol and Contract Preservation
- Problem-to-Technique Decision Table
- Operational Refactoring Recipes
- Python-Specific Refactoring Hazards
- Sequencing Mixed Work and Incremental Migrations

## Pre-Refactoring Protocol and Contract Preservation

1. **Name the structural problem and intended benefit first.** Before touching code, state the
   concrete defect (e.g., mixed IO and policy, mutable module state, duplicated rule drift, pass-through
   indirection) and the structural improvement the transformation will achieve.
2. **Inspect static and dynamic consumers.** Search callers, imports, `__all__`, entry points in
   `pyproject.toml`, configuration files, string-based `importlib.import_module` / `getattr` lookups,
   plugin registries, and test `mock.patch` targets before moving, renaming, or deleting symbols.
3. **Establish characterization tests for undertested code.** When existing tests do not pin edge
   cases, side effects, rounding, mutation, or error paths, write characterization tests that **pass
   against the current implementation** before restructuring.
4. **Preserve observable contracts.** Maintain return values, exception types and messages (where
   callers match on them), parameter mutation/aliasing semantics, CLI flags/exit codes/output streams,
   serialized data formats, and concurrency behavior unless the task explicitly authorizes a contract
   change.
5. **Handle discovered bugs separately.** If inspection or characterization reveals an unintended bug
   in existing behavior, record it explicitly. Fix it in a separate step only if within authorized
   scope; otherwise preserve current behavior during refactoring and report the defect.
6. **Weigh removal as seriously as addition.** Prefer collapsing speculative hierarchies, middle-man
   wrappers, and single-implementation interfaces over adding new layers.

## Problem-to-Technique Decision Table

Select techniques from the problem observed. Combine and sequence multiple recipes when a substantial
improvement requires staged restructuring; use additional verified techniques when needed.

| Observed structural problem | Primary technique recipe(s) |
|---|---|
| Long function mixing sub-calculations or trivial one-line indirection hiding logic | R1: Extract / Inline Function |
| Complex repeated sub-expression or redundant temporary variable | R2: Extract / Inline Variable |
| God class owning unrelated state, or degenerate class holding no distinct responsibility | R3: Extract / Inline Class |
| Oversized module mixing responsibilities or misplaced symbols across package boundaries | R4: Extract Module and Move Symbol |
| Misleading symbol names, awkward parameter lists, or drifted call signatures | R5: Rename Symbol and Change Function Declaration |
| Same clump of parameters passed together across multiple functions | R6: Introduce Parameter Object |
| Single function/loop interleaving parsing, validation, IO, and domain calculation | R7: Split Phase |
| Function both computes a value and mutates state or triggers external effects | R8: Separate Query from Modifier |
| Deeply nested `if/elif/else` trees or scattered checks returning the same outcome | R9: Decompose / Consolidate Conditionals; R10: Introduce Guard Clauses |
| Repeated type/mode branching across multiple operations with genuine behavioral variation | R11: Replace Conditional Dispatch with Polymorphism |
| Near-identical functions differing only by constants, thresholds, or policy callbacks | R12: Parameterize Function and Consolidate Duplication |
| Module-level globals, shared mutable defaults, or hidden clock/env/client reads | R13: Encapsulate Mutable State and Make Dependencies Explicit |
| Wrapper classes, factories, or managers forwarding calls without adding policy | R14: Remove Middle Man and Simplify Unnecessary Abstractions |
| Subclassing used only for code reuse, violating substitutability or coupling internals | R15: Replace Unnecessary Inheritance with Delegation/Composition |
| Core policy coupled directly to files, sockets, subprocesses, or ORM sessions | R16: Introduce Narrow Testing or Integration Boundaries |
| Adding a feature or fix to tangled code would multiply branching or duplication | R17: Preparatory Refactoring Before Feature Implementation |
| Bespoke or legacy component/library needs replacement without breaking callers | R18: Incremental Component or Dependency Replacement |
| Unused functions, classes, compatibility shims, or unreachable branches | R19: Remove Dead Code |

## Operational Refactoring Recipes

### R1. Extract and Inline Function
- **Trigger:** Code fragment requires a comment to explain its intent or duplicates a sub-step
  (*Extract*); helper body is as clear as its name or adds pointless indirection (*Inline*).
- **Preconditions:** Inspect local variable mutations, `nonlocal`/`global` bindings, `yield`/`await`
  points, and early `return`/`break`/`continue` statements.
- **Transformation:** For *Extract*, lift the block into a pure or narrowly scoped function passing
  explicit inputs and returning modified values. For *Inline*, replace call sites with the body and
  remove the helper if unused.
- **Verification:** Run unit tests covering all branches and exception paths of the caller.
- **Avoid when:** Extracting would require passing 6+ mutable locals by reference (apply R6/R7 first),
  or inlining a function that serves as a documented `mock.patch` seam or public hook.

### R2. Extract and Inline Variable
- **Trigger:** Compound expression is hard to read or repeats (*Extract*); temporary variable is
  assigned once to a trivial expression and adds no clarity (*Inline*).
- **Preconditions:** Confirm sub-expression is side-effect-free and evaluation order does not alter
  short-circuit behavior or exceptions.
- **Transformation:** Bind the expression to a descriptive local variable, or substitute the variable
  value directly into its single usage site.
- **Verification:** Run focused tests and type checker.
- **Avoid when:** Repeating a sub-expression intentionally relies on fresh evaluation after state
  mutation, or extracting across a short-circuit (`and`/`or`) triggers `ZeroDivisionError`/`AttributeError`.

### R3. Extract and Inline Class
- **Trigger:** A class has distinct subsets of fields and methods that change independently
  (*Extract*); a class left after refactoring has only one method or no independent state (*Inline*).
- **Preconditions:** Check `isinstance`/`issubclass` checks, serialization schemas, and public exports.
- **Transformation:** Move cohesive fields and methods into a new `@dataclass` or collaborator class
  and delegate (*Extract*); or fold the degenerate class's methods/fields into its caller and remove
  it (*Inline*).
- **Verification:** Run unit and serialization/contract tests.
- **Avoid when:** External callers rely on subclassing the original class unless compatibility aliases
  remain in place.

### R4. Extract Module and Move Function/Class/Symbol
- **Trigger:** A module mixes distinct sub-domains, or a symbol belongs with another module's data.
- **Preconditions:** Check `__all__`, `pyproject.toml` `[project.scripts]` / entry points, dynamic
  `importlib` strings, and test patch targets (`mock.patch("pkg.old_mod.sym")`).Consult
  [refactoring-tools.md](refactoring-tools.md) for cross-module moves.
- **Transformation:** Create or open the target module, move the symbol and its private helpers,
  update internal imports, `package/__init__.py`, and any dynamic `importlib` target strings, and
  **MUST** retain a compatibility re-export in the original non-private module
  (`from .new_mod import sym as sym` or listed in `__all__` so Ruff/mypy treat it as an intentional
  re-export) unless breaking old module import paths is explicitly requested.
- **Verification:** Test fresh-process imports in both import orders (`python -c "import a, b"` and
  `"import b, a"`) to rule out circular imports, and run full test suite.
- **Avoid when:** Moving creates a circular import between the source and destination modules (extract
  shared types/interfaces to a leaf module first).

### R5. Rename Symbol and Change Function Declaration
- **Trigger:** Name misleads readers about side effects or return type, or parameters need adding,
  removing, reordering, or keyword-only enforcement (`*`).
- **Preconditions:** Enumerate all internal and external call sites, subclass overrides, `Protocol`
  definitions, and keyword-argument dictionaries (`**kwargs`).
- **Transformation:** For multi-caller or public symbols, use a two-step deprecation/adapter migration
  (add new parameter with default or alias old name, migrate callers, then remove legacy parameter/name).
- **Verification:** Run type checker (`mypy`/`pyright`) to catch signature mismatches and run test suite.
- **Avoid when:** Breaking an external published API or CLI flag outside authorized scope.

### R6. Introduce Parameter Object
- **Trigger:** Three or more parameters (e.g., `start_time, end_time, venue, account_id`) travel
  together across multiple function signatures.
- **Preconditions:** Verify whether callers mutate individual arguments or rely on positional order.
- **Transformation:** Define a `@dataclass(frozen=True, slots=True)` holding the grouped parameters,
  move validation into `__post_init__` or a factory method, and update signatures to accept the object.
- **Verification:** Run type checker and behavioral tests covering valid and invalid parameter values.
- **Avoid when:** Grouping unrelated arguments into a generic `Context` or `Options` bag that hides
  what each function actually reads.

### R7. Split Phase
- **Trigger:** A function interleaves input parsing/IO, validation, domain calculation, and output
  formatting/persistence in one pass.
- **Preconditions:** Check streaming/memory constraints and exact error ordering when malformed input
  coexists with calculation errors.
- **Transformation:** Split into sequential phases connected by typed intermediate records (or a
  bounded generator pipeline when streaming large inputs): (1) parse/validate into typed structures,
  (2) execute pure domain calculation, (3) format/persist output.
- **Verification:** Test the pure calculation phase directly in memory and run end-to-end tests for
  IO and error ordering.
- **Avoid when:** Materializing an entire multi-gigabyte stream into a list in Phase 1 violates memory
  bounds (use typed generator stages instead).

### R8. Separate Query from Modifier
- **Trigger:** A function both returns a computed answer and mutates state (e.g., `get_and_clear_alerts()`
  or `calculate_total_and_charge()`).
- **Preconditions:** Check concurrency/atomicity requirements (whether check-and-set must hold a lock).
- **Transformation:** Split into an idempotent, side-effect-free query function and a distinct
  state-modifying command function.
- **Verification:** Verify calling the query repeatedly produces identical results without state drift.
- **Avoid when:** Separating an atomic compare-and-swap or queue `pop` across concurrent workers would
  introduce a race condition.

### R9. Decompose and Consolidate Conditionals
- **Trigger:** Complex boolean predicates obscure business rules (*Decompose*), or sequential branches
  perform the same action/return value (*Consolidate*).
- **Preconditions:** Verify short-circuit evaluation order and side effects inside condition calls.
- **Transformation:** Extract complex conditions into named predicate functions (`is_eligible_for_rebate(fill)`),
  and combine branches that lead to identical outcomes using `or`/`and` or `match`/`case`.
- **Verification:** Test boundary values for every branch condition.
- **Avoid when:** Consolidating branches merges distinct error diagnostics that callers need to tell apart.

### R10. Introduce Guard Clauses
- **Trigger:** Deeply nested `if/else` blocks where normal execution is buried several indent levels deep.
- **Preconditions:** Confirm no cleanup code at the bottom of the function is bypassed by early returns
  (use `with` context managers or `try/finally` for resource cleanup first).
- **Transformation:** Check edge cases, invalid states, or no-op conditions at the top of the function
  and return or raise immediately, leaving the main path flat.
- **Verification:** Run tests for each early-exit condition and the main execution path.
- **Avoid when:** A function requires single-exit post-processing that cannot be expressed cleanly via
  a context manager or helper.

### R11. Replace Conditional Dispatch with Polymorphism
- **Trigger:** Multiple functions switch on the same `type`/`kind` field to execute distinct behaviors,
  and adding a new variant requires editing every switch.
- **Preconditions:** Confirm genuine behavioral variation exists across multiple operations (not just
  a single lookup table of constants).
- **Transformation:** Define a ` typing.Protocol` or small class per variant (or a dispatch mapping of
  callable handlers when state is absent) and route calls through the unified interface.
- **Verification:** Test all variants against the shared contract test suite.
- **Avoid when:** Only one function branches on a kind tag, or a simple `dict[Kind, Decimal]` table of
  rates solves the variation without classes.

### R12. Parameterize Function and Consolidate Genuine Behavioral Duplication
- **Trigger:** Two or more functions implement the same algorithm or policy with different constants,
  field names, or minor step variations.
- **Preconditions:** Verify the duplication is genuine shared policy—not two independent rules that
  happen to look similar today but evolve separately.
- **Transformation:** Extract one authoritative function parameterized by the varying values or
  callable policy, and route existing entry points through it.
- **Verification:** Verify a policy change in the single authoritative function propagates to all
  entry points, and test each caller's specific parameters.
- **Avoid when:** Merging two independent domain rules requires adding boolean mode flags that make
  the shared function harder to understand than two separate 5-line functions.

### R13. Encapsulate Mutable State and Make Dependencies Explicit
- **Trigger:** Functions read or mutate module-level globals, mutable default arguments (`def f(x=[]):`),
  or implicit `os.environ` / `datetime.now()` calls.
- **Preconditions:** Identify all readers/writers of the global state across the repository and whether
  any external caller or test imports the global symbol.
- **Transformation:** Replace `def f(x=[])` with `def f(x: list[str] | None = None)` initializing a
  fresh list inside the body. When a module-level mutable global is private (leading underscore such as
  `_ALERTS` or `_CACHE`, not in `__all__`, and not imported by any caller or test), **delete the
  module-level mutable global and its `.clear()`/`.append()`/`.extend()` mutations completely**,
  replacing it with a local accumulator inside the function or an instance attribute on an explicit
  state object. Inject clock/config/env explicitly.
- **Verification:** Call the function multiple times in the same process and across isolated tests to
  prove zero cross-call state leakage.
- **Avoid when:** A module-level constant is genuinely immutable (`Final`, `frozenset`, ` tuple`, frozen
  dataclass).

### R14. Remove Middle Man and Simplify Unnecessary Abstractions
- **Trigger:** `*Manager`, `*Service`, `*Factory`, or `*Proxy` classes consist of pass-through methods
  delegating to another object, or an `ABC` has only one concrete subclass.
- **Preconditions:** Check whether the wrapper enforces security, transaction, caching, or public API
  stability boundaries.
- **Transformation:** When modifying or cleaning up a module with single-implementation `Abstract*`,
  `Base*`, `*Factory`, or `*Manager` pass-through classes, **collapse and delete the wrapper classes
  rather than threading new parameters through them**—let the public entry point invoke the real
  implementation directly.
- **Verification:** Confirm public entry points still work and all tests pass without the removed classes.
- **Avoid when:** The indirection is an active security/isolation boundary or a published plugin seam
  with external implementations.

### R15. Replace Unnecessary Inheritance with Delegation or Composition
- **Trigger:** A class inherits from a base class only to reuse 1–2 helper methods, inherits methods
  that make no sense on the subclass, or overrides methods in ways that break base invariants.
- **Preconditions:** Check whether callers pass the subclass to code checking `isinstance(obj, Base)`.
- **Transformation:** Replace base-class inheritance with an explicit attribute holding the helper
  collaborator or a standalone utility function, and delegate only the needed operations.
- **Verification:** Run type checker and behavioral tests.
- **Avoid when:** The relationship is a true subtype satisfying Liskov substitution or required by a
  framework (`Exception`, `enum.Enum`, `pydantic.BaseModel`).

### R16. Introduce Narrow Testing or Integration Boundaries
- **Trigger:** Testing business rules requires spinning up a database, HTTP server, filesystem tree,
  or mocking 5 internal module imports.
- **Preconditions:** Identify the minimal data needed by the business rule vs. the IO transport.
- **Transformation:** Extract the pure policy calculation to accept in-memory Python data structures
  (iterables, dataclasses, `io.TextIOBase`), leaving a thin adapter function to open files, query
  databases, or make HTTP calls.
- **Verification:** Exercise the core policy directly in unit tests without mocks or IO, and run one
  focused integration test on the thin IO adapter.
- **Avoid when:** Adding an abstraction layer around a function that is already a pure in-memory
  operation.

### R17. Preparatory Refactoring Before Implementing a Feature
- **Trigger:** Implementing a requested feature or bug fix directly in the current code would require
  copy-pasting branches, threading globals, or worsening a tangled function.
- **Preconditions:** Existing behavior is covered by baseline/characterization tests.
- **Transformation:** Step 1: Perform behavior-preserving refactoring (e.g., R7 Split Phase, R12
  Consolidate Duplication, R13 Encapsulate State) so the extension point is clean, and run tests to
  confirm zero behavioral change. Step 2: Add the new feature and its behavioral tests on the cleaned
  structure.
- **Verification:** Verify Step 1 passes existing tests unchanged, and Step 2 passes both existing and
  new feature tests.
- **Avoid when:** The preparatory refactoring balloons into an unbounded rewrite of unrelated modules.

### R18. Incremental Component or Dependency Replacement
- **Trigger:** Replacing a bespoke parser/client/validator (including when a bug report exposes syntax
  failures in a hand-rolled TOML/JSON/CSV/URL parser) or migrating from a deprecated library to a
  maintained one.
- **Preconditions:** Consult [dependencies.md](dependencies.md) to verify target library semantics
  (exception types, coercion rules, defaults, precision, timeouts). Define explicit cutover criteria.
- **Transformation:** Rather than patching regexes or line-splitting heuristics on a broken custom
  parser, replace it with the standard-library module (`tomllib`, `json`, `csv`, `urllib.parse`) or
  maintained package behind the existing public function, translating library exceptions (e.g.
  `tomllib.TOMLDecodeError`) to the caller's contract exception (`raise ConfigError(...) from exc`),
  and **delete the custom parsing code** before completion.
- **Verification:** Run differential tests on representative and edge-case inputs (empty, malformed,
  boundary types) and verify no references to the retired implementation remain.
- **Avoid when:** Leaving both old and new implementations active indefinitely without completing the
  cutover.

### R19. Remove Dead Code After Checking Static and Dynamic Usage
- **Trigger:** Uncalled functions, unused classes, obsolete feature flags, or retired migration shims.
- **Preconditions:** Search static references across the repo AND check dynamic mechanisms (`getattr`,
  `globals()`, `__all__`, entry points, templates, config files, serialization registries). When
  available, use `vulture` (unreferenced definitions) and `deptry` (declared-but-unimported
  dependencies) as leads only: confirm the detector reports a known leftover before trusting a clean
  run, and treat entry points, registries, and dynamic lookups as false "unused" hits.
- **Transformation:** Delete the dead symbol, its dead imports, and obsolete tests that only tested the
  deleted internal shim.
- **Verification:** Run test suite, linter (`F401`/`F841`), type checker, and package import checks.
- **Avoid when:** Symbol is part of the documented public package API (`__all__`) or invoked dynamically
  by external plugins/configs.

## Python-Specific Refactoring Hazards

Check these language-specific failure modes before and after every transformation:

- **Decorators and wrappers:** Extracting or moving a decorated function changes when the decorator runs
  (import time) and can break `functools.wraps` metadata, FastAPI/Click route registration, or
  `@classmethod`/`@property` descriptor binding.
- **Dynamic imports and reflection:** String references in `importlib.import_module`, `getattr`,
  `unittest.mock.patch("module.ClassName")`, Celery task names, and Pydantic forward refs are invisible
  to static rename/move tools. Always grep for string occurrences of moved/renamed symbols.
- **Public re-exports and entry points:** Moving a symbol out of a module where external callers or
  `__init__.py` import it breaks compatibility unless re-exported (`from .new_mod import Symbol as Symbol`).
- **Import-time behavior and circular imports:** Splitting one file into two mutually importing modules
  causes `ImportError: cannot import name ... from partially initialized module`. Keep dependency edges
  acyclic (DAG) and test importing each module first in a fresh Python process.
- **Mutation, aliasing, and evaluation order:** Extracting a helper or reordering statements can change
  whether a caller's passed-in `list`/`dict` is mutated in place vs. rebound (`xs.extend(...)` vs.
  `xs = xs + ...`), or when a generator expression captures loop variables (`lambda: i` late-binding
  hazard).
- **Generator exhaustion:** Replacing a `list` with a single-pass iterator/generator causes silent
  empty second passes if a downstream caller iterates over the value twice or checks `if items:`.
- **Exception hierarchy and chaining:** Replacing custom parsing or IO with a library often changes the
  raised exception (e.g., `tomllib.TOMLDecodeError` or `pydantic.ValidationError` instead of custom
  `ConfigError`). Catch and translate with `raise DomainError(...) from exc` when callers depend on the
  exception type.
- **Serialization and persisted representations:** Renaming dataclass fields, Enum members, or class
  names can silently break JSON/pickle/database payloads unless wire aliases are preserved.
- **Async cancellation, concurrency, and resource lifetimes:** Moving file/socket/lock acquisition out
  of a function must preserve deterministic context-manager (`with` / `async with`) lifetimes and
  propagate `asyncio.CancelledError` without swallowing it in broad `except BaseException:` blocks.
- **`TaskGroup` migrations (3.11+):** `asyncio.TaskGroup` is not a drop-in `gather` replacement or a
  concurrency limit. Failures arrive as `ExceptionGroup`, so `except ValueError` misses them; handle
  inside each task or use `except*` (whose handler cannot `return`, `break`, or `continue`). Wrap the
  whole operation in one deadline (`asyncio.timeout()`), not a fresh timeout per `await`.
- **Guard-clause and truthiness inversion:** Negate an accepted condition literally
  (`not (limit is None or limit >= 0)`); rewriting it as `limit is not None and limit < 0` lets
  `float("nan")` through because both comparisons are false. `if not x` conflates `0`, `""`, empty
  collections, and `None`. Computed slices need edge checks: `items[-n:]` returns everything when
  `n == 0`. Test zero, one, empty, NaN, and more-than-available inputs after the rewrite.
- **Annotation evaluation:** Removing `from __future__ import annotations` or unquoting forward
  references is safe only when every supported runtime is 3.14+ (deferred evaluation); below that
  floor it raises `NameError` at definition time, and runtime annotation readers (Pydantic,
  dataclasses, `typing.get_type_hints`) see strings vs. objects differently.

## Sequencing Mixed Work and Incremental Migrations

- **Never mix refactoring and behavior changes in one unverified jump.** When a task requires both
  restructuring and new behavior/bug fixes, complete and test the behavior-preserving refactoring step
  before introducing the behavioral change (or vice versa when a tiny bug fix is needed first).
- **Stage large restructurings through a target design.** Define the target module/data design, execute
  coherent steps that keep tests runnable between steps, and never substitute a blind from-scratch
  rewrite for understanding existing edge-case contracts.
- **Mark compatibility bridges that must outlive the task.** Decorate them with
  `warnings.deprecated` (3.13+; `typing_extensions.deprecated` below that floor) so runtime warnings
  fire and type checkers list remaining callers (mypy requires its `deprecated` error code enabled),
  and record the removal condition.
- **Finish the migration.** Remove temporary compatibility shims, duplicate old helpers, and unused
  imports in the same task once all in-scope callers are migrated and cutover criteria are met.
