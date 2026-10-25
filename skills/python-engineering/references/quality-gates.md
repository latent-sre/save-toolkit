# Python Quality Gates and Verification Selection

## Contents

- Risk-to-Verification Selection Matrix
- Baseline, Iteration, and Final Execution Protocol
- Advanced Verification Techniques for High-Risk Changes
- Configuring and Improving Project Gates
- Verification Integrity and Final Review Rules

## Risk-to-Verification Selection Matrix

Select verification gates based on the risk and surface area of the change. Read only the rows that
match the task:

| Changed surface or risk | Required verification checks |
|---|---|
| Any Python code creation, edit, or refactoring | Focused unit/behavioral tests (`pytest` or `unittest`), linter ([`ruff check`](https://docs.astral.sh/ruff/linter/)), formatter check (`ruff format --check`), and static type check ([`mypy`](https://mypy.readthedocs.io/) or [`pyright`](https://microsoft.github.io/pyright/)) on affected modules |
| New behavior, bug fix, or input validation | Behavioral tests covering happy paths, boundary conditions (empty, zero, `None`, max limits, Unicode), and expected exception paths (`pytest.raises`), confirmed to **fail before the fix/feature** and pass after |
| Undertested legacy module restructuring | Characterization tests pinning existing outputs, state mutations, rounding, and error behavior **passing against the unmodified baseline** before decomposition |
| Cross-module symbol moves, package restructuring, or `pyproject.toml` packaging changes | Fresh-process import checks across import orders (`python -c "import a, b"` and `"import b, a"`), editable/wheel build and install check, and entry-point execution outside the source directory |
| Replacing a custom component or migrating libraries | Differential equivalence tests comparing old and new implementations over representative and edge-case inputs in isolated fixtures |
| Parser, serializer, normalization, or invariant-heavy algorithmic code | Property-based or bounded exhaustive domain tests (e.g., [`Hypothesis`](https://hypothesis.readthedocs.io/) when installed/justified, or deterministic `itertools.product` domain sweeps) |
| External boundary (HTTP, database, CLI subprocess, filesystem) | Contract and integration tests using controlled local fixtures (`tmp_path`, in-memory/test client, subprocess exit-code/stdout/stderr assertions) without hitting live production endpoints |
| Supported Python version compatibility (`requires-python` floor vs. dev version) | Syntax and lint target-version check (`ruff check --target-version py312`, `mypy --python-version 3.12`) and running tests on the minimum supported interpreter when available |
| Dependency addition, upgrade, or trust-boundary change | Lockfile consistency check (`uv lock --check` or project equivalent) and vulnerability advisory check ([`pip-audit`](https://pypi.org/project/pip-audit/) when available); note that a clean advisory scan checks known CVEs only and does not prove a package is safe |
| Material performance, latency, or memory requirement | Reproducible measurement before and after using `time.perf_counter`, `cProfile`, or `tracemalloc` on representative workloads |

## Baseline, Iteration, and Final Execution Protocol

1. **Establish the baseline before editing existing code.** Run the target test files and static gates
   before making changes. Record any pre-existing failures so they are separated from regressions
   introduced by your work.
2. **Use the repository's actual interpreter and commands.** Run checks using the project's virtual
   environment (`.venv/bin/python` or `.venv\Scripts\python.exe` / `uv run`) and configured flags in
   `pyproject.toml` or CI workflows.
3. **Iterate with fast, focused checks.** During step-by-step refactoring or vertical-slice
   implementation, run `python -m pytest <affected_test_file>` and `python -m ruff check <affected_files>`
   after each step to catch regressions immediately.
4. **Run broader checks on the final state.** Once implementation is complete, run the broader affected
   test suite, full linter/formatter check, and type checker across the modified package or repository.
5. **Rerun after review fixes.** Any edit made during final diff review requires rerunning the affected
   test and static checks before completion.

## Advanced Verification Techniques for High-Risk Changes

Select these techniques when risk warrants stronger proof; MUST NOT install extra testing frameworks
when standard `pytest`/`unittest` parametrized checks suffice:

- **Characterization testing:** Capture undocumented legacy behavior (including side effects on mutable
  arguments, log lines, and exact exception types) in tests that pass on the untouched code before
  extracting or splitting phases.
- **Differential testing:** When replacing a parser, calculator, or library that must remain
  behaviorally equivalent, run both the old and new functions against a shared corpus of normal,
  boundary, and malformed inputs inside a test or scratch harness. **Safeguard:** Use read-only or
  isolated temp fixtures (`tmp_path`) so comparative execution never duplicates destructive side
  effects (such as double-charging, sending live requests, or mutating shared files).
- **Property-based testing:** For round-trip serialization (`decode(encode(x)) == x`), idempotence
  (`normalize(normalize(x)) == normalize(x)`), or conservation invariants (sum of split payouts equals
  total), test invariants across generated inputs.
- **Performance and memory verification:** When claiming an algorithmic or streaming improvement,
  measure operation counts, wall time (`perf_counter`), or peak memory (`tracemalloc.get_traced_memory()`)
  on representative input sizes rather than asserting complexity from code inspection alone.

## Configuring and Improving Project Gates

- **New projects:** Establish a minimal coherent gate set in `pyproject.toml`:
  - `ruff check` with at least `["E", "F", "W", "I", "B", "UP", "SIM"]` and `ruff format --check`.
  - `mypy` (`strict = true`) or `pyright` covering source and test modules.
  - `pytest` with strict markers/config.
- **Existing projects:** Use the repository's configured toolchain. You MUST NOT add duplicate tools
  (e.g., adding `flake8`, `black`, or `isort` when `ruff` is already configured).
- **Closing genuine tooling gaps:** If a repository lacks linting, bugbear (`B`) checks, or type
  checking—or leaves modified modules excluded from checks—recommend closing the gap. When tooling
  improvements are in scope, configure them in `pyproject.toml` and wire them into CI workflow files
  so gates run automatically rather than relying on prose reminders.

## Verification Integrity and Final Review Rules

- **No gaming the gates.** You MUST NOT:
  - Weaken linter rules, disable strict typing flags, or lower test assertions to force a pass.
  - Add blanket `# noqa`, `# type: ignore`, or `cast(Any, ...)` escapes instead of fixing root causes
    (a narrow `# type: ignore[error-code]` is permissible only for a verified third-party stub defect
    with an inline explanation).
  - Delete or skip failing tests, or overwrite expected test values to match broken output.
  - Cite coverage percentages or cyclomatic complexity numbers as proof of correctness or good design.
  - Report unexecuted, stale, or hypothetical commands as passing.
- **Final diff review.** For substantial changes, inspect `git status` and `git diff` against the task
  requirements, Python-specific hazards ([refactoring-playbook.md](refactoring-playbook.md)), and
  scope boundaries. Use an independent `reviewer` lane when available and authorized; otherwise
  perform a dedicated self-review and label it accurately as self-review.
