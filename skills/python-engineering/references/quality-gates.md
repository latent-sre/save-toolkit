# Quality gates

Read the risk rows the change matches and the sections they need. The tests every change needs, the
completion rules, and the prohibitions are in SKILL.md; this file adds risk-specific checks and
execution detail.

## Contents

- Find the real gates
- Risk to check
- Stronger verification
- Execution
- Suppressions and type escapes
- Interpreting results
- Re-verify

## Find the real gates

1. Use the commands the repository actually runs, as written: CI workflows, `pyproject.toml` tool
   sections, `noxfile.py`, `tox.ini`, `Makefile`, pre-commit configuration, and the README.
2. New project: before the first feature lands, set up one formatter, one linter, one type checker,
   and one test runner, each runnable by one documented command. When CI is in scope, wire them
   into CI rather than only documenting them.
3. Existing project with a missing class of check: add it when the task authorizes quality-tooling
   work, and recommend it otherwise. MUST NOT add a second tool for a job an existing tool does.

## Risk to check

Leave a row out only when its risk is absent, not when the check is inconvenient.

| Risk in this change | Required check |
|---|---|
| Any code change | The tests in SKILL.md's Verify step, plus the project's lint and format on the changed files |
| Behavior-preserving refactor of covered code | Existing assertions unchanged and passing before and after; only mechanical test updates (imports, `mock.patch` targets, renamed names), each listed in the report |
| Refactor of poorly tested code | Characterization tests passing on the original, shown to fail when one quirk is altered |
| Public API, signature, or type change | Type check over callers; tests of callers; import of every published name |
| Moved or renamed modules, re-exports, entry points | Import each touched module in a fresh process; resolve entry points and dotted-path strings |
| Packaging, build, or metadata change | Build the sdist and wheel, install into a clean environment, import the package, run its entry points |
| Supported-version range, or syntax or standard-library changes | Tests on the minimum and maximum supported Python where available; otherwise a lint or parse check at the minimum target, reported as partial |
| Dependency added, removed, or upgraded | Clean install from the declared metadata or lockfile; lock consistency check; vulnerability scan; license check |
| New trust boundary (input parsing, subprocess, file paths, deserialization) | Tests with hostile and malformed input; the project's security lint rules |
| External boundary (HTTP, database, file format, CLI contract) | Contract or integration test against a controlled fixture or local service |
| Concurrency or async | Tests for cancellation, timeouts, and resource cleanup; repeated runs for ordering issues |
| Performance is a stated requirement or claim | Profile to find the cost before optimizing; benchmark before and after on the same machine and inputs |

## Stronger verification

Choose by risk; no task needs all of these, and a testing package is added only for a concrete need.

| Situation | Technique |
|---|---|
| New code is meant to be equivalent to old code | Differential tests: run both on the same generated and recorded inputs; compare outputs, exceptions, and side effects |
| Meaningful invariants over a large input space (round-trips, ordering, idempotence, bounds) | Property-based tests, for example Hypothesis, which can also generate equivalence tests |
| Undocumented existing behavior | Characterization tests pinned before the structure changes |
| Real adapter to an external system | Contract or integration test against a controlled fixture |
| Performance claim | A harness that repeats runs and reports variance (`pyperf`, or `timeit` with repeats); never a single timing |

Run comparisons in controlled fixtures or isolated environments. MUST NOT run destructive side
effects twice (deletes, sends, payments) while comparing implementations; record or fake them.

## Execution

1. **Baseline.** If the tree has changes at task start, save them before editing, using absolute
   paths: `git diff --binary HEAD > <patch-file>` for staged and unstaged edits, and
   `git ls-files -z --others --exclude-standard | tar --null -T - -cf <tar-file>` for untracked
   files. Run the relevant checks before editing, and keep the commands and results.
2. **Reproducing a failure on the starting state.** Use a temporary worktree:
   `git worktree add <temp-dir> HEAD`, then `git -C <temp-dir> apply <patch-file>` and
   `tar -xf <tar-file> -C <temp-dir>`. Run the failing check there, then
   `git worktree remove --force <temp-dir>`. Do not use `git archive`: export rules can drop tests
   or configuration.
3. **Iterate.** After each step, run the affected test module and lint the touched files.
4. **Finish.** On the final state, run the full suite when the change crosses modules, plus the type
   check, lint, format, and any build or install check the table requires.

## Suppressions and type escapes

- When a rule is wrong for one line, name the rule (`# noqa: B008`, `# type: ignore[arg-type]`) and
  put the reason on that line or the line above.
- File-wide or project-wide ignores, lowered rule sets, raised thresholds, and skip markers added to
  obtain a pass count as weakening a check.
- Confine `Any` and `cast` to an untyped boundary, with the reason in a comment.

## Interpreting results

- MUST NOT treat a vulnerability scan as proof a dependency is safe; it reports known advisories.
- MUST NOT treat a coverage percentage or complexity score as proof of correctness or design
  quality.
- When the change rests on tests you wrote, show once that they fail on a deliberate breakage.

## Re-verify

Check these when an installed version behaves differently from this file.

- [pytest good integration practices](https://docs.pytest.org/en/stable/explanation/goodpractices.html)
- [Hypothesis](https://hypothesis.readthedocs.io/en/latest/) and its [equivalence ghostwriter](https://hypothesis.readthedocs.io/en/latest/reference/integrations.html)
- [pyperf](https://pyperf.readthedocs.io/en/latest/run_benchmark.html) and [timeit](https://docs.python.org/3/library/timeit.html)
- [pip-audit](https://github.com/pypa/pip-audit)
- [importlib.metadata entry points](https://docs.python.org/3/library/importlib.metadata.html)
