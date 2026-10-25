# Python Refactoring and Transformation Tools

## Contents

- Tool Selection Matrix
- Pre-Application and Safety Requirements
- Conditional Tool Guidance
- Custom Codemod Engineering Procedure
- Anti-Patterns and Dependency Boundaries

## Tool Selection Matrix

Select the transformation mechanism after choosing the refactoring technique in
[refactoring-playbook.md](refactoring-playbook.md). Treat named tools as candidates—verify what is
installed in the active environment before invoking or recommending them.

| Transformation scope and goal | Recommended tool candidate | Why / boundary |
|---|---|---|
| Single-file or few-file extract, inline, signature update, or local restructuring | Narrowly scoped manual edits + `mypy`/`pyright` + `pytest` | Lowest overhead when call sites are few and directly inspectable; avoids codemod setup cost |
| IDE/LSP-supported workspace rename, move, or extract when language server is active | Existing editor or language-server refactoring (Pyright/Pylance, Jedi, PyCharm) | Uses live symbol resolution; still requires grep for dynamic string references |
| Programmatic project-wide symbol rename, move module/function, or change signature | [Rope](https://rope.readthedocs.io/) (`rope.base.project.Project`, `Rename`, `Move`, `ChangeSignature`) | Resolves Python scopes and updates imports across modules; preview `get_changes()` before `project.do()` |
| Syntax-aware multi-file codemods preserving comments, parentheses, and formatting | [LibCST](https://libcst.readthedocs.io/en/latest/codemods_tutorial.html) (`CSTTransformer`, `VisitorBasedCodemodCommand`) | Lossless Concrete Syntax Tree preserves trivia (comments and whitespace), unlike `ast.unparse` |
| Standardized lint/modernization rules (import sorting, `pyupgrade`, simplifications) | [Ruff](https://docs.astral.sh/ruff/linter/) (`ruff check --diff`, `ruff check --fix`) | Fast, deterministic rule-based rewrites (`I`, `UP`, `B`, `SIM`); distinguishes safe vs. unsafe fixes |
| Read-only structural discovery, call-graph auditing, or invariant checking | Standard-library [`ast`](https://docs.python.org/3/library/ast.html) + [`tokenize`](https://docs.python.org/3/library/tokenize.html) | Zero external dependencies; ideal for locating callers, decorators, imports, and signatures without mutating code |

## Pre-Application and Safety Requirements

Every automated transformation MUST satisfy these controls:

1. **Verify syntax and environment compatibility.** Confirm the tool supports the repository's
   `requires-python` version (e.g., `match`/`case`, `type` statement aliases, PEP 695 type parameters,
   f-string nesting in Python 3.12+) before parsing or rewriting files.
2. **Preview before applying broadly.** Generate a diff (`ruff check --diff`, Rope
   `changes.get_description()`, or running a LibCST codemod on a single target file) before writing
   across a package.
3. **Audit unsafe fixes explicitly.** Automated fixes marked unsafe (such as `ruff check --unsafe-fixes`)
   can alter runtime semantics, exception types, generator eagerness, or side-effecting imports.
   Always preview with `ruff check --diff --unsafe-fixes`, inspect every hunk, and MUST NOT apply
   unsafe fixes blindly across a repository.
4. **Review the full diff and scope.** Run `git diff` after any tool run to confirm no unrelated files,
   comments, or public contracts were unintentionally altered.
5. **Verify behavior after tool execution.** A tool-generated change is never proof of correctness.
   Execute the affected test suite and type checker after every automated transformation ([quality-gates.md](quality-gates.md)).

## Conditional Tool Guidance

### Narrowly Scoped Manual Edits
- **Use when:** Touching 1–5 files or <20 call sites where reading every caller takes less time and
  carries less risk than writing a script.
- **Required practice:** Combine manual edits with `ast`/grep caller searches and strict `mypy`/`pyright`
  verification so missed call sites fail immediately.

### Ruff Rule Transformations
- **Use when:** Modernizing syntax to the supported Python floor (`UP`), sorting/cleaning imports (`I`,
  `F401`), or applying safe simplifications (`SIM`).
- **Required practice:**
  - Scope rules to target files and project `--target-version` (e.g., `py312`).
  - Keep formatting (`ruff format`) separate from semantic refactoring commits or steps.
  - Check `__init__.py` and plugin registration modules before removing "unused" imports (`F401`) that
    exist for re-export or import-time registration side effects.

### LibCST for Lossless Codemods
- **Use when:** Rewriting call patterns, decorators, type annotations, or API migrations across many
  files where comments and formatting must be preserved.
- **Required practice:** Use `libcst.codemod.VisitorBasedCodemodCommand` with metadata providers
  (`PositionProvider`, `ScopeProvider`, `QualifiedNameProvider`) so transformations match qualified
  symbols rather than bare attribute names.

### Rope for Symbol-Aware Refactoring
- **Use when:** Moving functions/classes across modules or renaming symbols with many static import
  sites where Rope is available or justified in development tooling.
- **Required practice:** Always inspect `changes.get_description()` prior to `project.do(changes)`,
  remove any temporary `.ropeproject/` directory before committing, and manually check dynamic
  `importlib` / string references that Rope cannot see.

### Standard-Library `ast` Analysis
- **Use when:** Auditing symbol definitions, verifying all functions carry return annotations, finding
  mutable defaults, or checking import graphs without third-party dependencies.
- **Restriction:** You MUST NOT use `ast.parse()` followed by `ast.unparse()` to rewrite production
  source files in place, because `ast` discards all `#` comments and original formatting.

## Custom Codemod Engineering Procedure

When a bulk transformation justifies writing a custom codemod script, execute this checklist before
running it on the repository:

1. **Test representative positive cases.** Assert exact before-and-after code strings for target
   patterns.
2. **Test negative (no-op) cases.** Include look-alike symbols (e.g., a method with the same name on
   an unrelated class or shadowed local variable) that **must remain unchanged**.
3. **Cover syntax and formatting edge cases.** Test multiline arguments, trailing commas, inline
   comments above/inside the call, decorators, and aliased imports (`import pkg.mod as m`).
4. **Verify idempotence.** Run the codemod twice on the transformed output and assert the second run
   produces zero diff.
5. **Pilot on isolated fixtures or a single module.** Verify tests and `git diff` on one bounded
   subpackage before applying across the repository.

## Anti-Patterns and Dependency Boundaries

- **No blind regex/sed across modules.** You MUST NOT use broad text/regex replacements across files
  to rename symbols, change argument order, or rewrite imports when shadowed names, strings, or
  comments can match.
- **Keep refactoring tools out of runtime dependencies.** Libraries such as `libcst` or `rope` belong
  exclusively in development dependency groups (`[dependency-groups] dev`) or ephemeral tool environments—MUST NOT
  add them to `[project.dependencies]` unless the application itself is a code-transformation tool.
