# Refactoring tools

Use existing tools where they improve the scoped transformation; none proves application behavior.

| Change | Suitable approach | Limit |
|---|---|---|
| Symbol-aware rename, move, extract, inline | Rope or an existing capable editor | Dynamic/uncertain references still need review |
| Repeated source migration across files | LibCST codemod | Matching rules and the transformation need their own tests |
| Pattern search or one-off rewrite across files | ast-grep | Matches syntax patterns, not resolved names; aliases and dynamic access need review |
| Unused definitions or declared dependencies | vulture; deptry | Entry points, registries, and dynamic lookups appear unused to static analysis |
| Supported lint or syntax fix | Ruff | Safe/unsafe classification and target version matter |
| Structural source analysis | Python AST | Unparsing does not preserve original source formatting |

## Rope

Bind the project/resources to the intended checkout. Before constructing a refactoring, call
`project.validate(project.root)` to invalidate cached analysis after edits outside Rope; reading
current source alone does not refresh that analysis. Derive offsets, calculate the change set,
and preview the complete diff before applying through the project. Close the project in `finally`
with `project.close()` when finished, including on failure.
Keep optional similar-occurrence replacement scoped; one selected extraction does not authorize
rewriting every similar block. Re-read the source and affected callers after application.

Rope exposes uncertain rename occurrences because some references cannot be resolved confidently.
Do not enable all unsure matches indiscriminately. Inspect dynamic attributes, import strings,
configuration names, keyword callers, and references outside the analyzed project. Project history
can undo a refactoring, but retain the task's recoverable Git state and preserve unrelated edits.

## LibCST

LibCST preserves comments/whitespace and provides scope metadata; neither proves semantic equivalence.

Test intended matches, already-migrated/no-op code, aliases, shadowed names, and comments affected by
the transformation. Use its codemod test facilities where appropriate. For an idempotent migration,
verify that a second application produces no further changes. Inspect a representative diff before
expanding to the selected files; then run their actual behavior checks.

## Ruff and Python AST

Use the project's configured rules and Python target. Ruff's safe fixes are intended to preserve
runtime behavior; unsafe fixes may change it or remove comments. Review their applicability before
opting in. A blanket unsafe-fix sweep is not a behavior-preserving refactoring strategy.

Start with `ruff check --no-fix --no-fix-only <paths>` and `ruff format --check <paths>`.
Both disabling flags matter: inherited `fix-only = true` can otherwise apply fixes and hide remaining
violations even with `--no-fix`. Preview eligible fixes with
`ruff check --diff <paths>`; this writes no source and returns nonzero when there are diffs, but
implies `--fix-only`, so a clean diff does not establish a clean lint run. Review configuration for
unsafe-fix opt-ins and rule-specific applicability overrides; use `--no-unsafe-fixes` when checking
only safe fixes. Keep formatting/import cleanup separate from semantic changes when it obscures
review. Run the configured type checker against public callers after signature or module changes.

AST unparsing can change source representation; a successful parse does not establish executable
validity. Use source-preserving tools when comments/formatting matter. `2to3`/`lib2to3` are absent
from Python 3.13+; check older recipes against the actual toolchain.

## Tool verification

Check the installed tool's parser support against the actual syntax, including modern annotations;
its minimum installable Python version does not establish support for every target syntax feature.
Keep tools in a development environment; report the tool/version and unresolved references when material.
