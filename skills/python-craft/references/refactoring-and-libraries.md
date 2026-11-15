# Refactoring, Fixing, and Library Adoption

## Refactoring Execution Loop

1. **Map static and dynamic consumers before moving or deleting anything:** Check static imports, `__all__`, `[project.scripts]` / plugin entry points, config files (`settings.json`, YAML/TOML dotted strings `"pkg.mod.fn"`), `importlib`/`getattr`, decorator registries, `mock.patch("pkg.mod.fn")` targets, and explicit release manifests (`release-files.txt`, `MANIFEST.in`, package-data globs). A leading underscore (`_legacy.py`, `_helper`) does not prove nothing imports or packages it.
2. **Establish baseline and pin behavior at the public entrypoint:** Run the existing checks first. Add passing characterization tests (for undertested code) or a failing reproduction test (for an established defect) through the public API—never pin internal helpers you are about to reshape, and never codify a demonstrated bug as required behavior.
3. **Transform completely (or in coherent verified stages):** For multi-module restructurings or justified whole-implementation rewrites, keep tests runnable between stages and finish migrating every in-repo caller before deleting old paths.
4. **Preserve compatibility and runtime-lookup seams:**
   - When moving a public or configured callable (`reports.format_label` -> `formatting.format_label`), re-export the identical callable object from the original module (`from .formatting import format_label as format_label`) so identity-keyed registries (`FORMATTERS[alias]`), `importlib` lookups, and callers resolve to the same function.
   - Where callers or tests replace a policy owner at runtime (`policy.normalize_order`, `calculation.total_from_lines`, `reports.format_label`), call through the module attribute (`policy.normalize_order(row)`) rather than binding a bare `from policy import normalize_order` at import time.
   - Verify fresh-process imports in both orders (`python -c "import mod_a, mod_b"` and `"import mod_b, mod_a"`).
5. **Retire dead code completely:** Delete superseded private helpers, `_legacy.py` modules, custom parsers, and obsolete entries in `release-files.txt` / `pyproject.toml` once callers move; use `@warnings.deprecated` only for external compatibility bridges with a stated removal condition.

## Smell-to-Transformation and Equivalence Traps

| Smell in touched code | Transformation | Guardrail / equivalence trap |
|---|---|---|
| Domain calculation trapped inside file/HTTP/DB I/O | **Extract pure core:** `total_from_lines(lines: Iterable[str])` over borrowed inputs; keep `total_from_file(path)` as a thin UTF-8 owner delegating at runtime | Never close borrowed iterators; preserve error order and file cleanup on parse failure |
| Duplicated rule drifted across CLI, API, and batch | **Unify policy owner:** Extract one pure module (`policy.normalize_order`) returning new validated records; keep transport framing in each adapter | Keep distinct domain rules separate even if two formulas currently look alike |
| Repeated linear scan (`row["id"] in allowed_ids`) | **Bounded index:** Build a `set`/`frozenset` from `allowed_ids` once (consume `allowed_ids` once so one-pass iterables work) and stream `rows` lazily | Consume `rows` only as output advances (no read-ahead); preserve order, duplicates, row object identity, and per-row `KeyError` timing |
| Parallel lists (`ids`, `qtys`, `prices`) or `dict[str, Any]` bags | **Ordered typed records:** Convert to a sequence/iterable of `@dataclass(frozen=True, slots=True)` values | Never collapse into a dict keyed by ID when duplicate keys or input order matter |
| Unreadable positional flags (`render(rows, True, False)`) | **Keyword-only options:** Change internal signature to `(*, compact: bool = False, include_header: bool = False)` and update callers | Do not invent a stateful `Options`/`Context` object when flags are independent; preserve positional calls for external APIs |
| Single-impl `ABC`, `*Factory`, `*Manager`, `*Service` passthrough | **Collapse abstraction:** Delete forwarding wrappers and call the boundary function/concrete class directly | Keep a boundary class only if it owns real state, transactions, locks, or multiple live implementations |
| Private mutable globals (`CACHE.append(...)`) | **Explicit scoped state:** Pass explicit state/return values and delete private globals | Verify no external consumer or test imports or resets the module global |

Check these silent equivalence traps on every refactor:
- **Guard-clause negation & `NaN`:** Negate an acceptance rule literally: `if not (limit is None or limit >= 0): raise ...`. Rewriting as `limit is not None and limit < 0` silently accepts `float("nan")` (both `< 0` and `>= 0` are `False`), and `if not limit:` breaks when `0` is valid.
- **Negative-zero slice (`items[-count:]`):** When `count == 0`, `-0 == 0`, so `items[-0:]` returns the entire sequence instead of `[]`; guard `if count <= 0: return []` explicitly.
- **Short-circuiting comprehensions (`all`/`any`):** Replacing a loop with `all(audit_and_accept(r) for r in rows)` stops on the first `False` and skips required side effects on later rows.

## Free Reign: Replacing Custom Plumbing with Stdlib & Packages

Prefer `requires-python` stdlib or maintained packages (`tomllib`, `csv`, `ipaddress`, `compression.zstd`, `pydantic`, `jsonschema`, `httpx`, `tenacity`, `click`/`typer`, `rich`, `polars`) over hand-rolled code whenever lockfile, license, and `-I -S` (stdlib-only) runtime constraints permit. Inspect installed API signatures via `<venv-python> -c "import pkg, inspect; ..."` rather than guessing from memory, translate library exceptions to caller-expected domain errors (`raise DomainError(...) from exc`), and delete the retired custom code.

| Replacement target | Migration & contract traps |
|---|---|
| `csv.reader` / `ipaddress.IPv4Address` | `csv.reader(lines)` handles quoted commas and embedded newlines that `.split(",")` corrupts, **but** wrapping `for row in reader:` catches exceptions raised by the borrowed `lines` iterator too—wrap with a plain `for line in lines: yield line` generator (never `yield from`, which forwards `.close()`) capturing `source_err = exc` on any source failure, and check `if exc is source_err: raise` in **every** enclosing `except` clause (`csv.Error`, `DecimalException`, `ValueError`, etc.) before `raise ValueError(...) from exc`. `IPv4Address(val)` accepts `int`/`bytes` too—check `isinstance(val, str)` (and strip/leading-zero rules) first, then re-raise the caller-expected error (`ValueError(...) from exc`) |
| `pydantic` v2 / `jsonschema` | Pydantic strict vs. coercing mode differs (`ConfigDict(strict=True, extra="forbid")`); verify missing, `None`, `bool`-as-`int`, and `float`-as-`Decimal`. With `jsonschema`, run `Draft202012Validator.check_schema(schema)` before validating, and note JSON Schema `integer` accepts integral floats (`1.0`) while rejecting `bool` |
| `httpx` | Does not follow redirects by default (`follow_redirects=False`) and defaults to a 5s timeout (`requests` follows redirects and has no timeout); share one `Client`/`AsyncClient` instead of creating one per call |
| `tenacity` | Bare `@retry` retries every exception forever with zero wait and never cancels an already-blocking call; always set `stop=stop_after_attempt(...)`, `wait=wait_exponential_jitter(...)`, `retry=retry_if_exception_type(...)`, and `reraise=True` under a single retry/deadline owner |
| `argparse` | Calls `sys.exit(2)` on parse failure unless `exit_on_error=False` or `error()` is overridden; align with callers expecting an `int` return code without `SystemExit` |

## Automated Refactoring and Analysis Tools

Keep `libcst`, `rope`, `vulture`, and `deptry` in dev dependency groups only.

- **Ruff (`ruff check` / `ruff format`):** Run read-only checks with `ruff check --no-fix --no-fix-only <paths>` (an inherited `fix-only = true` mutates files even with `--no-fix`, and `--diff` implies `--fix-only`, so zero diff does not mean zero violations). Scan leads with `--extend-select B,UP,SIM,ASYNC,DTZ,RUF,PTH,FURB,PERF --target-version py3xx`; preview `--unsafe-fixes` with `--diff` before applying.
- **LibCST (`libcst.codemod`) vs. `ast`:** Use `ast` + `tokenize` for read-only audits only; never rewrite source with `ast.unparse()` (strips comments and formatting). For lossless multi-file rewrites, use `libcst` (`VisitorBasedCodemodCommand` with `ScopeProvider`/`QualifiedNameProvider`) or `ast-grep`, and verify comments, shadowed/aliased no-ops, and second-run idempotence on one file first.
- **Rope (`rope`) & dead-code tools (`vulture`, `deptry`):** Call `project.validate(project.root)` before each Rope refactoring after external edits (otherwise cache is stale), preview `changes.get_description()`, close in `finally: project.close()`, delete `.ropeproject/`, and manually audit `unsure` matches plus dynamic string references. Confirm `vulture`/`deptry` flag a known unused item before trusting a clean run, and cross-check `__all__`, entry points, and registries.
