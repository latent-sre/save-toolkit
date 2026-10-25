# Refactoring tools

Choose the technique first (see the playbook), then the tool that applies it most safely. Every
named tool here is a candidate, not a requirement. Confirm it is installed, check its version, and
confirm that version supports the project's Python syntax before relying on it. A
transformation tool belongs in development tooling, never in runtime dependencies, unless the
application itself uses it.

## Contents

- Selection
- Required procedure for any automated change
- Editor and language-server refactoring
- Rope
- LibCST
- Ruff fixes
- AST analysis
- Text search and manual edits
- Custom codemods
- Re-verify

## Selection

| Change | First choice | Fallback |
|---|---|---|
| Rename or move a symbol across modules | Editor or language-server rename or move; Rope | Inventory with search, then manual edits |
| Extract or inline function or variable, change signature | Editor refactoring; Rope | Manual edit with tests |
| The same syntactic rewrite at many sites (call pattern, import path, API migration) | LibCST codemod | Ruff fix if a rule exists; manual edits for a few sites |
| Syntax modernization to the supported Python floor, import sorting, rule-based fixes | Ruff with the project's target version | LibCST codemod |
| Inventory or measurement (who calls what, counting patterns) | `ast` script or search | Language-server references |
| Under about ten sites, or edits that need judgment per site | Scoped manual edits | — |

Prefer manual edits when automation would cost more to set up, review, or trust than the edits
themselves.

## Required procedure for any automated change

1. Isolate the tool's output so it can be reviewed apart from manual edits and existing changes:
   record the diff before the run, or run the tool in a temporary worktree.
2. Confirm compatibility: run the tool's version command and parse every target file with it, or
   with the project's minimum Python, before applying.
3. Preview: use a diff or dry-run mode, or apply to one module or an isolated copy first.
4. Review the proposed diff and the list of affected files. Reject edits outside the intended
   scope.
5. Review every unsafe or semantics-changing fix individually; never bulk-apply them unreviewed.
6. Apply in bounded batches. Run focused tests after each batch and the broader checks at the end.
7. Run the reference inventory again for dynamic and string references the tool cannot see.

A tool-generated change is not proof of correctness. Behavioral verification is still required.

## Editor and language-server refactoring

- Use language-server rename, move, and extract (Pyright-based servers, Jedi, `pylsp` with the
  `pylsp-rope` plugin) for static references when the environment exposes one.
- Update dotted-path strings, configuration, entry points, `getattr` names, and `mock.patch`
  targets from the inventory; language servers do not change them.
- Do not install an editor or language server for a rename that Rope or manual edits can do.

## Rope

- Library refactorings include rename, move, extract (method and variable), inline (method,
  variable, parameter), change signature, introduce parameter, introduce factory, encapsulate
  field, local-to-field, method object, use function, restructure, and module-to-package.
- Preview: `changes = refactoring.get_changes(...)`, then `changes.get_description()` shows the diff.
  Apply with `project.do(changes)`; `project.history.undo()` reverts changes Rope applied.
- Before use, confirm the installed Rope version parses the target files.

## LibCST

- Use LibCST for rewrites that must preserve comments and formatting; it reprints untouched code
  exactly.
- Codemods: subclass `VisitorBasedCodemodCommand`. Register its module in `.libcst.codemod.yaml`
  (created by `python -m libcst.tool initialize .`) or load it with `-x`, then run
  `python -m libcst.tool codemod <module.Command> <paths>`.
- `initialize` sets `formatter` to Black. Point it at the project's formatter (for example
  `['ruff', 'format', '-']`) or pass `--no-format`; otherwise every file fails when Black is absent.
- Test codemods with `CodemodTest.assertCodemod(before, after)`.
- Use metadata providers for semantic matching instead of matching names textually.
  `QualifiedNameProvider` and `FullyQualifiedNameProvider` resolve what a name refers to;
  `ScopeProvider` finds assignments and accesses; `PositionProvider` reports locations. Declare
  them in `METADATA_DEPENDENCIES`.
- Check that the installed LibCST version parses the project's newest syntax.

## Ruff fixes

- Safe fixes are intended to preserve behavior, but review every removed import and deleted
  statement against the import-time hazard: a safe unused-import fix can delete an import even
  when it runs side effects.
- Unsafe fixes may change behavior or remove comments. They apply only with `--unsafe-fixes`;
  preview them with `ruff check --diff --unsafe-fixes` and review each one.
- Preview with `ruff check --diff` and `ruff format --diff`; both write nothing.
- Scope a modernization with `--select`, such as `UP` for pyupgrade rules. Those rules depend on the
  target version, which Ruff infers from `requires-python` unless `target-version` is set. Confirm
  the effective value before applying, so syntax newer than the supported floor is not introduced.
- Changing `lint.extend-safe-fixes` or `lint.extend-unsafe-fixes` is a policy decision for the
  project, not a way to apply fixes faster.

## AST analysis

- Use the standard-library `ast` module for read-only analysis: find definitions and references,
  list imports, count patterns, or check structure in verification scripts.
- MUST NOT rewrite source by round-tripping through `ast.unparse`: the tree has no comments, and
  the output is not guaranteed to match the original text.
- `ast.parse(source, feature_version=(3, N))` is a best-effort grammar check for an older Python
  version, not proof of compatibility.

## Text search and manual edits

- Use search (`rg`, `grep`) to build the reference inventory, including strings, configuration,
  and documentation.
- MUST NOT use broad textual find-and-replace as the transformation for symbols.
- For manual edits, keep each step small and run focused tests between steps.

## Custom codemods

Before running a custom codemod on the repository:

1. Write before-and-after tests on representative cases.
2. Include cases that must remain unchanged: similar names, shadowed names, strings, comments,
   and aliased imports.
3. Cover the syntax and formatting edge cases the code base actually uses: decorators, async
   functions, multi-line calls, parenthesized imports, and type annotations.
4. When idempotence is expected, run the codemod twice and confirm the second run changes nothing.
5. Apply it to an isolated copy or fixture directory first, then to the repository in bounded
   batches under the required procedure above.

## Re-verify

Check these when an installed tool version behaves differently from this file.

- [Ruff linter: fix safety](https://docs.astral.sh/ruff/linter/)
- [Ruff configuration: target version inference](https://docs.astral.sh/ruff/configuration/)
- [Ruff settings: extend-safe-fixes, extend-unsafe-fixes](https://docs.astral.sh/ruff/settings/)
- [Ruff formatter](https://docs.astral.sh/ruff/formatter/)
- [LibCST README](https://github.com/Instagram/LibCST/blob/main/README.rst)
- [LibCST codemods](https://libcst.readthedocs.io/en/latest/codemods.html)
- [LibCST metadata](https://libcst.readthedocs.io/en/latest/metadata.html)
- [Rope library usage](https://rope.readthedocs.io/en/latest/library.html)
- [pylsp-rope](https://github.com/python-rope/pylsp-rope)
- [Python `ast` module](https://docs.python.org/3/library/ast.html)
