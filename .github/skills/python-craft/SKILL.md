---
name: python-craft
description: >-
  Design, write, refactor, fix, and modernize Python across services, libraries, CLIs, workers,
  scripts, and tests. Load before writing, editing, explaining, or reviewing any Python: build
  fresh modules at a senior level from the start, reshape touched legacy code, fix defects, and
  replace custom plumbing with stdlib or maintained packages and frameworks. Compose with
  api-craft for HTTP APIs/clients and operator-cli for CLI contracts. Triggers:
  'write this in Python', 'refactor this Python code', 'modernize this Python module',
  'fix this Python bug'. Not for live incident response without code changes
  (incident-investigation) or non-Python language work (go-craft, frontend-craft).
argument-hint: "[Python module, feature, refactor, dependency, or defect]"
---

# Python Craft

The task and repository constraints set scope; this skill adds no tools or live authority.
Explanation, design, and review requests stop at those outputs unless implementation is requested;
when code already satisfies its contract with no defect or demonstrated maintenance problem, leave
it unchanged. When a request asks for only a JSON object, output raw JSON with no Markdown code
fences (`` ``` ``).

## Mandates and Leeway

1. **Bind the interpreter and environment floor first.** Check `requires-python`, `.python-version`,
   lockfiles, CI matrix, and any isolated runtime constraints (`python -I -S`) before choosing
   syntax or libraries. Never raise the Python floor or switch package managers without task
   authority. Even when production uses `python -I -S -B`, test `-I -S` inside a test or an
   earlier check; finish every code change by running the exact requested test suite (`python -m
   unittest discover -s tests -t .` or `<venv-python> -m pytest ...`, never with `-S`) as a
   standalone final foreground shell command **in its own turn after all file edits/writes have
   completed**—never chained (`&&`, `;`, heredocs), parallel with file writes in the same tool
   batch, piped (`|`), or backgrounded.
2. **Build fresh code right from the start.** Match deliverable scale cleanly without speculative
   scaffolding: start isolated utilities as a single import-safe `<name>.py` file (using PEP 723
   inline metadata if needed) rather than unrequested `pyproject.toml`/`src/` trees; use `src/<pkg>/`
   with `py.typed` and `__all__` for reusable libraries. Keep CLI (`main(argv=None) -> int`) and
   transport handlers as thin decoding adapters around a pure, importable domain core; parse
   untrusted inputs into explicit boundary types and bound all streams, iterators, and async tasks.
3. **Refactor touched code and adopt libraries with active leeway.** When fixing a bug, adding a
   feature, or refactoring, eliminate structural defects in scope (or across the codebase when broad
   improvement is requested): extract pure calculations from I/O, unify duplicated policy under one
   owner, collapse single-implementation `ABC`s and passthrough wrappers, remove private mutable
   globals, and fix resource/iterator lifetimes. Exercise free reign to replace fragile custom
   parsers, validators, retries, HTTP plumbing, and CLI boilerplate with `requires-python` stdlib
   modules or maintained packages whenever project and runtime constraints permit.
4. **Separate internal freedom from external contracts.** Reshape private helpers, internal data
   representations, and intra-package splits freely while updating all in-repo callers in one
   change (or coherent verified stages for multi-module refactors and justified whole-implementation
   rewrites). Preserve public APIs, runtime lookup seams (`module.func` targets), dotted config or
   plugin strings (`"pkg.mod:fn"`), wire schemas, exception contracts, and borrowed-stream
   ownership unless authorized to change them. When passing a borrowed iterator into a parser
   (`csv.reader(lines)`), iterate via a plain `for line in lines: yield line` wrapper (never
   `yield from`, which forwards `.close()`) that captures `source_err = exc` on any exception from
   the source, and check `if exc is source_err: raise` in **every** enclosing `except` handler
   (`csv.Error`, `DecimalException`, `ValueError`, etc.) before translating parser or conversion
   errors to `ValueError`, so a source exception propagates as the original object. Clarify
   unresolved external-effect or undocumented business-rule ambiguities before guessing, while
   continuing independent work.

| Rationalization (Reject) | Required Action |
|---|---|
| *"Keep the diff minimal / only patch the broken line"* | Apply Mandate 3 to touched functions and local helpers, unless the task explicitly scopes a narrow fix |
| *"Avoid third-party dependencies / keep custom plumbing"* | Replace bespoke parsing, validation, retries, or HTTP/CLI plumbing with stdlib or maintained packages when repo and runtime constraints (`-I -S`, offline, lockfile) permit |
| *"Match the existing pattern in this file"* | Follow repository layout and runner conventions, never local defects (mutable globals, swallowed errors, untyped `dict` bags, closed-file generators, forwarding layers) |
| *"Add a context object or keep old private helpers just in case"* | Use keyword-only flags (`*, compact: bool = False`) for independent options; migrate all in-repo callers and delete dead private code (`@warnings.deprecated` only for external bridges) |
| *"Deduplicate two identical formulas that belong to separate domain rules"* | Unify policy only when callers obey the same rule; keep coincidental expressions with independent domain owners separate |

## Composition and Reference Routing

Read the matching reference file below before writing or editing code; compose `api-craft` (HTTP
servers/clients/webhooks, FastAPI), `operator-cli` (CLI flags, exit codes, streams, signals),
`database-reliability` (migrations/pools/transactions), `root-cause` (non-obvious bugs/flakiness),
and `stack-profile` (unset repo tooling).

| Task or inspected code condition | Read |
|---|---|
| New module, package, entrypoint, data boundary, streaming/resource lifetime, asyncio, or Python 3.12–3.15 capabilities and floor traps | [design-and-new-code.md](./references/design-and-new-code.md) |
| Refactoring, bug fix, consumer mapping, replacing custom plumbing with stdlib/packages, or Ruff/LibCST/Rope codemods | [refactoring-and-libraries.md](./references/refactoring-and-libraries.md) |
| Environment/uv binding, characterization/differential/property tests, deterministic checks, or quality gates | [testing-and-verification.md](./references/testing-and-verification.md) |

## Guardrails

- Never add blanket `# noqa`, untargeted `# type: ignore`, or `cast(Any, ...)` to mask defects;
  never weaken or delete valid test assertions; never use `ast.unparse()` to rewrite source files in
  place; never claim unexecuted checks passed.
- Report structural/library improvements and their concrete benefit (one policy owner, pure core
  testable without I/O, removed custom machinery, bounded memory/lookups), preserved contracts,
  exact verification commands run, and any unverified paths.
