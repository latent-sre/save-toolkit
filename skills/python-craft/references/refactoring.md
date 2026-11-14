# Refactoring

## Diagnose, then target

Name the mechanism that makes change hard: duplicated policy, an unfit data model, mixed
responsibilities, hidden state, resource coupling, unnecessary layers, or fragile custom
infrastructure. State the target ownership, representation, or dependency structure in a sentence,
then choose transformations that reach it. Renaming, formatting, extraction, or file splitting is
insufficient while the mechanism remains. Weigh removing structure as seriously as adding it. Share a
rule only when callers need the same rule; look-alike code with independent owners stays separate.

Find consumers before changing a boundary: imports, re-exports and `__all__`, entry points,
`importlib`/`getattr` strings, registries and decorators, `mock.patch` targets, configuration,
templates, package data, persisted qualified names. Search qualified names as text
(`"pkg.mod.name"`, `"pkg.mod:name"`) across code, configuration, and metadata; rename tools see only
static references, and an underscore does not prove privacy. Supported contracts stay: values and
types, exceptions callers match, argument mutation, call forms and defaults, CLI flags and exit
codes, serialized formats, import-time effects, public patch points. Controlled internal interfaces
may change with their callers. Characterization records current behavior; it never makes a
demonstrated bug or a guessed rule a requirement. Record a bug found while refactoring separately:
fix it in its own verified step only when in scope, otherwise preserve and report it.

## Techniques

Coverage, not a checklist; other techniques are fine.

| Observed problem | Technique | Hazard or check |
|---|---|---|
| Block needing a comment, or repeated; helper no clearer than its body | Extract or inline function or variable | An extracted `return` no longer exits the caller; carry `break`/`continue`, `yield`/`await`, `nonlocal`; hoisting past `and`/`or` changes evaluation |
| Independent field groups in one class; class with no state or responsibility | Extract or inline class | `isinstance`, subclasses, serialization |
| Module mixing sub-domains; symbol far from its data | Extract module; move symbol | Re-export from the old public path unless removal is authorized; update import strings and patch targets; break cycles with a leaf module |
| Misleading name; drifted parameters | Rename; change signature | Overrides, `Protocol`s, keyword and `**kwargs` callers; adding `*` breaks positional callers; migrate public forms in two steps |
| Parameters that travel together | Introduce parameter object | Frozen dataclass with validation, not a generic context bag; independent flags become named keyword options |
| One pass mixing parse, validate, compute, output | Split phase | Typed records between phases; keep streaming bounds and error order |
| Function that answers and mutates | Separate query from modifier | Keep an atomic check-and-set atomic |
| Nested or scattered conditions | Decompose or consolidate conditionals; guard clauses | Negate literally: `not (x is None or x >= 0)` rejects NaN, `x is not None and x < 0` admits it; early exits must not skip cleanup; keep diagnostics callers distinguish |
| Same switch on a kind across several operations | Replace conditional dispatch with polymorphism, a `Protocol`, or a mapping of callables | Only for behavior varying across operations; one branch or a constant table stays; tables lose ordered and range predicates; bare `match` names capture |
| Near-identical functions differing by constants or policy | Parameterize; consolidate shared policy | One owner reached by every entrypoint; no boolean mode flags |
| Globals, mutable defaults, hidden clock, environment, or client reads | Encapsulate mutable state; make dependencies explicit | Find every reader and writer; delete a private mutable global rather than wrapping it |
| Managers, factories, or wrappers that only forward; single-implementation ABC | Remove forwarding layers and unnecessary abstractions | Keep one that owns transactions, validation, security, caching, compatibility, resources, or an external plugin seam |
| Subclass for helper reuse | Replace inheritance with composition or delegation | True subtypes and framework bases stay |
| Rule testable only with a database, server, files, or many mocks | Introduce a narrow testing or integration boundary | Policy over in-memory data; thin adapter with one integration test |
| Feature that would multiply tangled branches | Preparatory refactoring, then the feature | Verify each step separately; no unrelated rewrite |
| Bespoke component or deprecated library | Incremental component or dependency replacement | Behind the existing interface; translate exceptions; cut over; delete the old path |
| Unused code, flags, or shims | Remove dead code | Check dynamic use and public exports first; detector hits are leads |

## Replacement hazards

Check whichever apply to a transformation:

- `all`, `any`, and `next` short-circuit later effects and errors; use a sentinel when `None` is a
  valid result.
- `zip` truncates without `strict=True`; set or dict indexing changes duplicates, order, identity, and
  hashability; `items[-n:]` returns everything when `n == 0`.
- Lazy forms move work and errors and lose repeatability; eager arguments do extra work:
  `mapping.get(key, expensive())` evaluates the default on every call.
- Decorators register at import time; moving decorated code changes registration and
  `functools.wraps` metadata.
- In-place mutation versus rebinding (`xs.extend` versus `xs = xs + ...`); late-binding closures.
- Renamed fields, classes, or enum members break pickled, JSON, and database payloads.
- Cleanup restructuring keeps partial acquisition, release order, cancellation propagation, and
  exception suppression.

## Staging and migration

- Never combine a behavior change and a restructuring in one unverified step. Choose checkpoints by
  risk; a small atomic replacement can beat a bridge.
- Complete one real consumer path before widening; a dormant helper beside old callers is not a
  migration.
- Keep a compatibility bridge only for supported consumers, mixed versions, or persisted data, with
  a removal condition; mark it with `warnings.deprecated` (3.13+, else `typing_extensions`) so type
  checkers list remaining callers (mypy needs its `deprecated` error code).
- Finish the cutover: migrate callers and release inputs, then delete superseded code, shims, and
  dependencies. Hunt leftovers with the type checker, text search, `vulture`, and `deptry`, after
  confirming the detector reports a known leftover.

## Tools

Choose the lowest-overhead tool that handles the transformation reliably. Tools are candidates, not
dependencies, and generated edits prove nothing.

| Tool | Use when | Check |
|---|---|---|
| Manual edits with search and a type checker | Few files and call sites | Every caller read |
| Editor or language-server refactoring | Live symbol resolution available | Dynamic references still need text search |
| Rope | Programmatic rename, move, signature change | Root the project at the intended checkout; `project.validate(project.root)` after outside edits; preview the change set; never accept every unsure occurrence; keep similar-occurrence replacement to the requested site; `project.close()` in `finally`; remove `.ropeproject/` |
| LibCST | Multi-file codemods keeping comments and formatting | Test intended matches, look-alikes that must stay (aliases, shadowing), syntax hazards, idempotence; pilot on a fixture first |
| Ruff fixes | Lint fixes; `UP` modernization | Check-only needs `--no-fix --no-fix-only`; `--diff` implies fix-only; review configured unsafe-fix opt-ins and pass `--no-unsafe-fixes` for safe fixes only; never sweep unsafe fixes, inspect each unsafe hunk; `F401` in `__init__.py` or registration modules may be a re-export |
| `ast` | Read-only analysis | `ast.unparse` drops comments and formatting; never rewrite source with it |

Confirm the tool parses the target syntax, inspect the full diff after every run, keep formatting
in a step apart from semantic changes, and never use broad text replacement for a semantic rename.
