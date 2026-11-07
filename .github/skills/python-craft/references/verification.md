# Verification

## Environment

Run checks with the project's interpreter and commands. Record `sys.executable` and `sys.version`,
run baseline and final checks through the same environment, and invoke tools as
`<python> -m pytest` or `-m mypy` so an unrelated install on PATH is not used. Type and import
checks must see the project environment (a fresh `uvx` environment lacks its dependencies); a
formatter may run standalone. Reuse a matching environment; install only within the task's
authority, with the required extras and groups, and honor constraints, markers, and indexes (a
constraints file limits versions and installs nothing). A missing interpreter is a gap, not
evidence from a substitute, and a missing or stale lock is an error to resolve explicitly.

With uv, run checks as `uv run --locked <command>`: plain `uv run` relocks and syncs first,
`--frozen` skips the freshness check, and `--no-sync` can run stale dependencies. `uv pip sync`
removes everything outside its input, so never feed it a partial requirements file in a shared
environment. A refactoring request implies no `uv init`, lock-format change, dependency upgrade, or
floor change.

## Risk to evidence

| Change or risk | Required evidence | Complete when |
|---|---|---|
| Any code change | Focused tests for touched behavior; the project's lint, format, and type commands on changed files | They pass, or a failure is shown on the unchanged base |
| New behavior or defect repair | A test that first fails for the intended reason, not an import or fixture error; boundaries (0, 1, empty, `None`, maximum, non-ASCII) and failure paths | It passes with the change |
| Restructuring poorly tested code | Characterization of values, types, exceptions, effects, argument mutation, and cleanup on the unmodified code; equality can hide a type change (`0 == Decimal("0")`) | The same tests pass unchanged; known bugs recorded apart |
| Extracted policy | Direct tests of the new function | Original entrypoint tests also pass |
| Replacement or migration | Differential checks over normal, edge, and malformed inputs, giving each side fresh equivalent inputs with controlled time, randomness, effects, and caches, paired with independent expectations | No caller reaches the old path |
| Parser, serializer, invariant-heavy code | Property-based tests (Hypothesis when present or justified) or bounded exhaustive sweeps | Round-trip, idempotence, or conservation holds |
| Changed external boundary | Contract or integration tests on local fixtures (`tmp_path`, test clients, subprocess exit codes and streams) | No live system touched |
| Moved modules, exports, entry points, package data | Fresh-process imports in relevant orders; build the release artifact; install outside the checkout and run its entry points | Imports, lookups, and bundled files work from the install |
| Supported Python range | Lint and type checks at the floor's target version; tests on the floor interpreter when available | Pass, or the gap is reported |
| Dependency change | Lock consistency (`uv lock --check` or equivalent); advisory scan when available | A clean scan means no known advisories, not safety |
| Streaming or async claim | Progress before full consumption; cleanup after a partial read; one forced task failure and cancellation | Bounded memory and cleanup shown |
| Performance claim | Before-and-after measurement on representative input (`perf_counter`, `cProfile`, `tracemalloc`) | Measured, not inferred |

Use a technique where it yields evidence; parametrized pytest often suffices. When comparative runs
could repeat external effects (payments, messages, shared files), use controlled fixtures.

## Testing anti-patterns

| Pattern | Consequence | Better approach |
|---|---|---|
| Test recomputes the implementation's logic | Passes with the bug | Expectations from requirements or worked examples |
| Mocks of internal functions | Tests pin structure and block refactoring | Test through narrow boundaries; fake only external effects |
| Happy path only | Failure behavior unverified | Forced failures, partial completion, cleanup |
| Coverage or complexity numbers cited as correctness | False assurance | Behavioral evidence; coverage or mutation only to find unreached code |
| Differential check alone | Old bugs become the specification | Pair with independent expectations |

## Defect leads and final review

Detector hits are leads; clean output proves nothing. When Ruff is present, a check-only defect pass
on the project's version and configuration is
`ruff check --no-fix --no-fix-only --extend-select B,S110,S113,BLE001,DTZ,PLW1510,ASYNC,RUF006,RUF032 <paths>`;
read each hit in context, and confirm the rules exist in that version and that per-file ignores
and excludes do not silence the target paths.

For substantial changes, review the final diff separately against the requirements, scope, and the
hazard tables of each reference the task matched. Use independent review when required, requested,
or warranted by material unresolved risk. Rerun affected checks after a review fix; otherwise reuse
accepted evidence. Close a genuine tooling gap in project configuration only when tooling is in
scope, and in CI only when CI work is authorized; otherwise report it.
