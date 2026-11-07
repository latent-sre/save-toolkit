# Deliberate Refactoring and Transformation Tools

## Refactoring to Resolve the Design Problem

1. **Diagnose root mechanism**: duplicated policy, primitive data, mixed logic and I/O, hidden state, leaked resources, speculative pass-through layers, or fragile custom infrastructure.
2. **Define target ownership, data model, and dependency direction**, then sequence moves to reach it. Cosmetic renaming or file splitting leaving coupled ownership intact is insufficient.
3. **Remove vs. add structure**: inline pass-through wrappers, single-use classes, and unused hooks when indirection is the problem; add a `dataclass`, `Protocol`, or module boundary only to isolate coupled responsibilities or I/O.
4. **Inventory consumers**: static imports, `__all__`, `__init__.py` re-exports, entrypoints, dynamic lookups (`importlib`, `getattr`), config/manifest strings (`release-files.txt`), wire keys, and `unittest.mock.patch` targets.
5. **Migrate callers and retire bridges**: update in-repo callers together; keep re-export shims or `@warnings.deprecated` bridges only for external callers during transition, then remove them.
6. **Prove design benefit**: simpler flow, isolated pure policy, removed duplication, narrower state, stronger types, or verified stdlib/library ownership.

## Problem-to-Technique Catalog

| Observed problem | Technique | Hazard or check |
|---|---|---|
| Duplicated policy or branching | Extract pure function or dispatch table | Preserve precedence, rounding, and errors |
| Mixed I/O, validation, and policy | Split adapter from pure core | Keep handles out of core; test without mocks |
| Primitive obsession or parallel dicts | Use `dataclass(frozen=True, slots=True)`, `NamedTuple`, `Enum`, `pydantic` | Preserve JSON/wire keys and equality |
| Deep nesting or flag arguments | Guard clauses, early returns, focused functions | Preserve side-effect order and errors |
| God module or catch-all `utils.py` | Split by cohesion; re-export API in `__init__.py` | Test fresh imports in both orders (`import pkg; import pkg.sub` and reverse) |
| Speculative ABCs, factories, wrappers | Inline delegating layers; drop unused hooks | Confirm no plugin or patch target relies on seam |
| Hidden globals or import-time reads | Parameterize deps or pass explicit config | Keep default entrypoints ergonomic |
| Leaked files, clients, locks, temp paths | Wrap in context managers or `ExitStack` | Verify cleanup on errors and partial generators |
| Fragile custom parsing, retry, HTTP | Replace with `ipaddress`, `tomllib`, `urllib.parse`, `pydantic`, `tenacity`, `httpx` | Audit coercion, leading zeros, `bool`/`int`, timeouts |
| Swallowed errors or low-level leaks | Narrow `try`; `raise DomainError(...) from exc` | Preserve `__cause__`, exit codes, exception types |
| Circular imports | Extract shared types to leaf module or invert deps | Avoid local-import hacks unless deferring heavy deps |
| N+1 lookups, repeated regex/JSON, buffering | Precompute `set`/`dict` indexes, hoist regexes, stream | Preserve order and single-pass streaming (`set(allowed_ids)`) |
| Legacy syntax or typing clutter | Upgrade to target-version `match`, `X | Y`, `type`, `Path`, `with` | Match `requires-python`; separate from logic diffs |

## Shared Python Refactoring Hazards

- **Import binding and patch seams**: `from pkg.mod import fn` binds at import time; if tests or callers patch `pkg.mod.fn`, look up `mod.fn` at call time or keep the attribute on the module/package.
- **Callable identity**: decorators and `@lru_cache` change identity (`is`), `__name__`, and pickleability—use `@functools.wraps` and check registries.
- **Evaluation order and truthiness**: reordering `and`/`or`/ternaries shifts side effects; use `x is None` rather than `not x` when `0`, `""`, `False`, or `[]` are valid.
- **Numeric and slice traps**: `isinstance(True, int)` is `True` (exclude `bool`); `float("nan") != float("nan")`; `items[-count:]` returns the full list when `count == 0`—guard `count <= 0` with `[]`.
- **Generators and streaming**: never wrap `with open(...)` around `yield` if callers manage lifetime or stop early; never `list(stream)` or read ahead past a stop condition on single-pass streams.
- **Cancellation**: never swallow `asyncio.CancelledError` or `KeyboardInterrupt`.

## Refactoring and Transformation Tools

| Tool | Best fit | Caution |
|---|---|---|
| Manual / LSP | Localized logic, model, and flow edits | Check `getattr`/`importlib`, `__all__`, `mock.patch` |
| `rope` | Multi-file rename, move, signature updates | Audit string refs and review diffs |
| `libcst` | CST codemods preserving comments/formatting | Test visitors on edge syntax and inspect diffs |
| `ruff check --select UP,I,B,SIM` | Target-version upgrades, imports, idioms | Preview with `--diff` or `--no-fix --no-fix-only` |
| `ast` (stdlib) | Read-only inventory of imports and symbols | Never rewrite files via `ast.unparse` |
