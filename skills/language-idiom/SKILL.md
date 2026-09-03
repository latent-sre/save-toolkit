---
name: language-idiom
description: >-
  Write, review, test, debug, or safely refactor Python, Java, TypeScript, Bash, PowerShell, and Go
  using language-specific conventions. Triggers: 'write this in Python', 'review this Bash script',
  'refactor this Go code'. Not for API design (backend-craft) or UI architecture (frontend-craft).
argument-hint: "[the language and the code under review]"
---

# Language idiom — the team's choices

Match the repo's existing tooling first; the per-language defaults apply when none is set.

Load exactly one language reference for the language being changed. Do not preload the others.

- **Python** — `ruff` for lint and format, `uv` for environments, `mypy` or `pyright`, `pytest`;
  decision separated from effect so `--dry-run` is provable.
  → [`references/python.md`](./references/python.md)
- **Bash** — a 5.1 floor, so the bare `shopt -s inherit_errexit`; `shellcheck` clean; `bats` for tests.
  → [`references/bash.md`](./references/bash.md)
- **PowerShell** — state the 5.1 or 7+ target; `PSScriptAnalyzer` failing CI on `Error`; Pester 5.
  → [`references/powershell.md`](./references/powershell.md)
- **Go** — `gofmt`/`goimports` and `go vet` in CI; `golangci-lint` on the named baseline.
  → [`references/go.md`](./references/go.md)
- **Java** — Spotless, Error Prone + NullAway, JSpecify `@NullMarked`, package by feature,
  JUnit Jupiter + AssertJ. → [`references/java.md`](./references/java.md)
- **TypeScript/JavaScript** — `strict` on and no `any`; `no-floating-promises`; Vitest or Jest with
  React Testing Library and MSW. → [`references/typescript.md`](./references/typescript.md)
