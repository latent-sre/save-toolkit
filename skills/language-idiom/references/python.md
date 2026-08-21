# Python idiom

Match the repo's existing tooling first; defaults below apply when none is set.

## Establish the runtime contract first
- **Read `pyproject.toml`, lockfiles, and CI config before choosing syntax or APIs.**
  `[project].requires-python`, classifiers, and the tested interpreter matrix define compatibility —
  the interpreter on `PATH` does not.
- **Version-gate behavior, not just syntax.** `asyncio.TaskGroup`/`ExceptionGroup` need 3.11;
  `typing.override` needs 3.12; free-threaded CPython starts at 3.13; annotation evaluation goes
  lazy and template strings (`t'…'`) arrive in 3.14. Use a backport only when the repo already
  adopts it.
- **No import-time side effects.** Importing a module must not connect to a service, start a thread,
  parse `sys.argv`, or mutate global config. Startup goes behind an explicit function; scripts
  behind `if __name__ == "__main__"`.
- Don't name local modules after stdlib or installed packages (`types.py`, `logging.py`,
  `queue.py`) — shadowed imports fail far from the file that caused them.

## Style & tooling
- **Type hints everywhere** public; check with `mypy`/`pyright` (or the faster Rust checkers `ty`
  (Astral) / `pyrefly` (Meta) for editor-speed feedback — preview-grade, not for CI gating yet). Prefer
  precise types; avoid `Any`.
- **Format + lint** with `ruff` (lint+format) or `black`+`ruff`. Don't hand-format.
- **Structure:** small functions, early returns, no deep nesting. Prefer `dataclasses`/`pydantic` for
  structured data over loose dicts/tuples.
- **Paths & resources:** `pathlib.Path` over `os.path`; always context managers (`with`) for files,
  locks, connections.
- **Respect the env manager** in the repo; **`uv`** is the fast default (envs, locking, running tools —
  replaces pip/venv/pipx), `poetry` is fine for published libraries. Never `pip install` into system Python.

## Correctness traps to avoid
- Mutable default args (`def f(x=[])`) — use `None` + assign inside.
- **Swallowing** exceptions — bare `except:` or `except Exception: pass` hides bugs. Catch specific
  types; a top-level boundary may catch broadly but must **log and re-raise** (or convert), never silently continue.
- `==` vs `is` (use `is` only for `None`/singletons); truthiness bugs on `0`/`""`/empty collections —
  use `is None` when *absence* is the contract, not falsiness.
- Closures capture **names, not values** — a callback made in a loop reads the final binding; bind
  deliberately (`lambda item=item: item`).
- Generator exhaustion; modifying a list while iterating; floating-point equality (integer minor
  units or `Decimal` where the domain needs decimal rounding).
- Naive datetimes as instants — use timezone-aware values with an explicit offset throughout.
- Blocking calls inside `async` code; every created task needs an owner and a join point ("fire and
  forget" means failures get garbage-collected). If you catch `asyncio.CancelledError`, re-raise it
  after cleanup.

## Errors & logging
- Raise specific exceptions with context; don't return sentinel error codes. Chain with
  `raise DomainError(...) from exc` at translation boundaries; note `except Exception` does not
  catch `KeyboardInterrupt`, `SystemExit`, or `asyncio.CancelledError` — usually what you want.
- Use the `logging` module (not `print`) with structured/levelled logs. **Never log secrets, tokens,
  PII, or full request bodies.**
- Fail loud in tooling: non-zero exit + a clear stderr message.

## Operational safety (ops/automation code)
- `subprocess.run([...], check=True)` with a **list**. Avoid `shell=True`; if it's unavoidable, never
  interpolate variables into the command string.
- HTTP (`requests`/`httpx`): **always set timeouts**; retry idempotent calls with backoff; check status.
- Parameterize SQL — never f-string user input into a query. On 3.14, a **t-string** (`t'… {x} …'`)
  is not a string: it yields a `string.templatelib.Template` that keeps static text and
  interpolations apart at runtime, so a consuming library can escape or parameterize each value —
  the documented motivation is exactly SQL/HTML/shell sanitising. It only helps when the receiving
  API accepts a `Template`; an f-string-shaped habit with a `t` prefix handed to `str()` gains
  nothing. *[sourced: Python 3.14 What's New, PEP 750; reviewed 2026-08-21]*
- **Annotations are not runtime validation** — still validate decoded JSON, env vars, and user input
  at the boundary even when everything is typed.
- Credentials/reset tokens come from `secrets`, never `random`; never unpickle untrusted data.
- Make scripts idempotent and re-runnable; guard destructive actions behind an explicit flag.
- **Separate decision from effect** so logic is testable without side effects: a pure function computes
  *what* to do (e.g. `desired_replicas(...)`), a thin wrapper *does* it. `--dry-run` becomes trivial,
  provable with a spy: `spy = mocker.patch("mod.subprocess.run"); run(dry_run=True); spy.assert_not_called()`.

## Tests
- `pytest`: arrange-act-assert, `parametrize` for cases, fixtures for setup, `tmp_path` for files,
  `monkeypatch`/`unittest.mock` for boundaries, `freezegun`/injected clock for time. See the [tests-first process](./tdd.md).
- Test behavior and error paths, not internals. `pytest --cov` to find untested branches that matter.
