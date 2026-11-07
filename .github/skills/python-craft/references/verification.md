# Environment, Verification, and Testing

## Interpreter and Environment Discipline

- **Bind the project interpreter**: check `sys.executable`, `sys.version`, `.venv`, and `pyproject.toml` first. Run `uv run ...` or `.venv/bin/python -m pytest` (`.venv\Scripts\python.exe` on Windows) instead of global `python` or `pytest`.
- **Respect lockfile and offline boundaries**: use `uv run --locked` (`--frozen` / `--no-sync` offline) to avoid mutating `uv.lock` or installing unrequested packages; use `uv pip sync` over `uv pip install` for exact pins; use `python -I` (`-S -B`) to isolate user-site/`PYTHONPATH` pollution.
- **Standalone foreground gates**: run final test/gate commands directly without piping (`| head`, `| tail`, `| Select-Object`) so exit codes and receipts stay intact.

## Proportional Verification Matrix

| Change or risk | Required evidence | Completion condition |
|---|---|---|
| New feature, CLI, or defect fix | Unit, boundary, and failure-path tests (`pytest`) | Fails before fix where practical; passes with it |
| Refactoring or legacy cleanup | Existing suite plus characterization tests | Outputs, exceptions, side effects, and state match |
| Library or parser replacement | Differential tests across valid, boundary, and invalid inputs | Coercion, error types/messages, defaults, timeouts match |
| Invariant-heavy parsing, math, round-trips | Property-based tests (`Hypothesis`) plus examples | Invariants hold across generated edge inputs (empty, Unicode, bounds, `NaN`) |
| Package split, move, or rename | Fresh-process imports in multiple orders (`python -c`) | Public imports, `__all__`, entrypoints, `mock.patch` resolve |
| Dependency addition or upgrade | Lockfile check, import smoke test, advisory/license check | Constraints, lockfile, and runtime imports align |
| Performance or memory fix | Operation counts, `time.perf_counter`, or `tracemalloc` | Algorithmic gain and bounded memory confirmed |
| All code modifications | Linter, formatter, and type checker (`ruff`, `mypy`/`pyright`) | Zero new diagnostics; pre-existing failures isolated |

## Testing Anti-Patterns and Gate Integrity

| Anti-pattern | Why it fails | Required practice |
|---|---|---|
| Over-mocking internal helpers or call order | Couples tests to internals; breaks on refactors | Test public interfaces with value objects and boundary fakes |
| Uncontrolled characterization or differential tests | Randomness, clocks, unordered sets, or temp paths flake | Inject clocks/seeds, normalize only unordered contracts, isolate `tmp_path` |
| Characterization-only checks on buggy code | Freezes historical defects as requirements | Pair characterization with contract assertions; fix or flag bugs |
| Weakening gates to pass | Deleting assertions, widening `# type: ignore`, `# noqa`, `xfail`, or skipping suites | Fix the root defect; scope unavoidable suppressions to one line/code with rationale |
| Claiming unexecuted verification | Misleads reviewers about confidence | Report exact commands run, outcomes, and unexecuted checks |

## Review, Limitations, and Reporting

- **Read-only reviews**: report findings ordered by severity (`file:line`, failure mechanism, concrete fix) without modifying files.
- **Unresolved limitations**: when a missing tool, dependency, or sandbox limit blocks a check, run all locally executable checks and state the exact skipped command and reason.
