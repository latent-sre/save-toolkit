# Designing and Writing Fresh Python Code

## Deliverable Scale and Entrypoints

- **Select the smallest matching layout:**
  - *Standalone utility:* Single import-safe `<name>.py` file with `main(argv: Sequence[str] | None = None) -> int`. Never generate `pyproject.toml`, `src/`, or build backends for an isolated script unless requested; use PEP 723 inline metadata (`# /// script`) when external deps are needed.
  - *CLI / service / library:* Importable package (`src/<pkg>/` prevents tests from importing an uninstalled checkout) separating pure domain logic from I/O adapters; expose `__all__`, `py.typed` (PEP 561), PEP 735 `[dependency-groups]` for dev/test tools, and lower-bound `>=` runtime pins on libraries so consumer apps are not over-constrained.
- **Import-safe modules:** Importing any module must perform no file creation, network I/O, stream reads, or required environment-variable reads at module scope.
- **Thin CLI/handler adapters (`main(argv=None) -> int`):**
  - Parse args, decode bytes/UTF-8 files or `sys.stdin`, and translate domain exceptions at the boundary. Keep `main` calling the shared core function via module attribute (`core.summarize(rows)` or `summarize(rows)` in the same module) so callers or monkeypatches replacing that public function change CLI behavior too.
  - Validate the entire input stream before emitting final `stdout`: on invalid arguments, malformed records, JSON errors, or read failures, write diagnostics to `stderr`, leave `stdout` empty, and return exit code `2` without raising `SystemExit` from library/core code.
  - A redirected `sys.stdin` or Windows console stream may use a non-UTF-8 codepage; open files with explicit `encoding="utf-8"` and handle UTF-8 decoding explicitly at the CLI boundary.

## Boundary Coercion and Representation Traps

- **`@dataclass(frozen=True, slots=True)` mutability trap:** `frozen=True` blocks attribute rebinding, not in-place mutation of nested `list`/`dict` fields—convert edge collections to `tuple`/`frozenset` when parsing untrusted inputs, and inject clocks/clients/RNGs via defaulted parameters.
- **`bool` is a subclass of `int`:** `isinstance(True, int)` is `True`. Integer validators must reject `isinstance(val, bool)` before `isinstance(val, int)` (or use Pydantic `StrictInt`).
- **`Decimal`, empty sums, and strict JSON:** Construct `Decimal` from `str`/`int`, never `float` (reject `isinstance(val, float)` and non-finite `NaN`/`Infinity` via `not val.is_finite()`). Pass `Decimal("0")` as the `start` argument to `sum(amounts, Decimal("0"))` so empty inputs return `Decimal("0")` rather than `int` `0`. Pass `parse_constant` to `json.loads` when strict JSON must reject `NaN`, `Infinity`, and `-Infinity` (Python's `json.loads` accepts them by default).
- **Unicode character predicates:** `.isdigit()`, `.isnumeric()`, `.isdecimal()`, `.isalnum()`, and `.isupper()` accept non-ASCII characters (`"²"`, `"١"`, `"Ｎ"`). Pair with `.isascii()` whenever validating ASCII SKUs, protocol tokens, or IPv4 octets.

## Resource Ownership, Streaming, and Asyncio Traps

- **Owner closes; borrower preserves:** A function opening a path or creating a client owns its `with`/`async with` block and closes it on exhaustion, error, or cancellation. A function accepting a caller-supplied iterable, stream, or `sys.stdin` borrows it and must never close or mutate it—even on error—and must propagate source iteration exceptions unchanged.
- **Generator-inside-`with` lifetime trap:** `with open(path) as f: return (line.strip() for line in f)` closes `f` immediately on return, raising `ValueError: I/O operation on closed file` on the first `next()`. Make the function itself a generator (`with open(path, encoding="utf-8") as f: for line in f: yield ...`) so Python keeps the context open until exhaustion, explicit `.close()`, or raised error.
- **True one-pass streaming:** Never materialize a borrowed stream (`list(rows)`, `len(rows)`, `if rows:`), never read ahead past the item being yielded, and keep per-key state bounded rather than retaining seen rows.
- **`asyncio.TaskGroup` and task lifetime traps:** `TaskGroup` raises `ExceptionGroup` on failure (`except ValueError` misses grouped errors and `except Exception` catches the whole group); handle expected errors per task or with `except*` (where `return`, `break`, and `continue` are syntax errors). `TaskGroup` does not cap concurrency—pair with `asyncio.Semaphore(n)`, bound multi-step operations under one `asyncio.timeout(budget)`, re-raise `asyncio.CancelledError` after cleanup, and hold strong references to background tasks (`tasks.add(t); t.add_done_callback(tasks.discard)`).

## Python 3.12–3.15 Capabilities and Floor Traps

| Floor | Capabilities to adopt | Silent traps and compatibility rules |
|---|---|---|
| 3.12 | PEP 695 `type Alias[T] = ...`, `itertools.batched(it, n)` | `type Alias = int \| str` creates a `TypeAliasType`, which raises `TypeError` in `isinstance(x, Alias)`—use `(int, str)` or `Alias.__value__`. `batched(it, n)` allows a shorter final tuple (`strict=True` added in 3.13) |
| 3.13 | `typing.TypeIs`, `typing.ReadOnly` (`TypedDict`), `@warnings.deprecated`, `copy.replace(obj, **changes)`, `itertools.batched(..., strict=True)`, `queue.Queue.shutdown()` | `TypeIs` narrows both `if` and `else` branches (return type must be assignable to input type, unlike `TypeGuard`). `@warnings.deprecated` warns at runtime; mypy flags deprecated callers only with `--enable-error-code=deprecated` |
| 3.14 | PEP 649/749 deferred annotations & `annotationlib.get_annotations(obj, format=...)`, PEP 750 `t"..."` (`string.templatelib.Template`), `compression.zstd`, `concurrent.interpreters.InterpreterPoolExecutor`, `uuid.uuid7()`/`uuid6()`/`uuid8()`, `Path.copy()`/`move()`/`info`, `functools.Placeholder`, bracketless `except ValueError, TypeError:` | Dropping `from __future__ import annotations` or unquoting forward refs raises `NameError` at class/def time on `<3.14`; runtime readers see `str` with `__future__` vs evaluated objects without it. `t"..."` produces a `Template` (not `str`) for injection-safe renderers. Bracketless `except` still needs parentheses with `as exc` |
| 3.15 | PEP 810 `lazy import pkg` / `lazy from pkg import sym` (`__lazy_modules__ = ["pkg"]` for `<3.15` fallback) | `lazy` is module-scope only (`SyntaxError` inside functions, classes, `try`, `with`, or `import *`) and defers import-time side effects/registrations until first attribute access |
