# Application and data stack

The [parent profile](../SKILL.md) owns runtime/platform boundaries. Inventory is neither migration
authority nor evidence of a target's exact version.

## Languages and CI

Services in the stack use **Java/JVM, Python, JavaScript/TypeScript, and Go**. Bash and PowerShell are
glue and automation, not service languages. GitHub + GitHub Actions; Bamboo is legacy.

**Java/JVM is support-only:** operate/troubleshoot Java/Spring Boot, but do not write, build, test
or run Java locally. Return source changes to the application owner; service inventory does not
grant authoring authority.

**CI uses GitHub environment secrets, not GitHub OIDC.** Do not design a GitHub-OIDC→CredHub
exchange; CredHub authenticates through UAA.

## Toolchain by language

Defaults for new code; a repository's own tooling wins. Rows without an operator statement are fleet
defaults until the owner records a decision here.

For Go implementation and language migrations, load `go-craft`; HTTP and CLI contracts remain
with `api-craft` and `operator-cli`.

| Language | Format and lint | Types and analysis | Tests | Environment or runtime |
|---|---|---|---|---|
| Python | `ruff` for both lint and format, with the `B` (bugbear) rules selected | `mypy` or `pyright`; prefer `dataclasses`/`pydantic` to loose dicts | `pytest` with `parametrize`, fixtures, `tmp_path`, `monkeypatch`, and an injected clock | `uv` (`poetry` is fine for a published library); never `pip install` into system Python |
| TypeScript/JavaScript | ESLint with `@typescript-eslint/no-floating-promises` and `no-misused-promises` | `strict` on, no `any`, `unknown` narrowed at the boundary; branded IDs and exhaustively switched discriminated unions | Vitest or Jest; React Testing Library for React, Vue Test Utils for Vue; MSW at the network boundary; Playwright for the few critical journeys | The repository's package manager and its `tsconfig` target; pin `typescript` to a release typescript-eslint supports (6.x while TypeScript 7 ships no compiler API) |
| Go | `gofmt`/`goimports` enforced in CI | `go vet`, and `golangci-lint` on the baseline `staticcheck`, `govet`, `errcheck`, `ineffassign`, `unused` | Table-driven `t.Run` subtests; `go test -race` targeted at concurrent code | `go.mod`'s `go` directive gates semantics; Semantic Import Versioning (`/v2`) |
| Bash | `shellcheck` clean, or a justified `# shellcheck disable=` carrying a reason | Header: `#!/usr/bin/env bash`, `set -Eeuo pipefail`, and the bare `shopt -s inherit_errexit` — the Bash 5.1 floor below allows it, so no `\|\| true` guard | `bats`: exit codes, stdout/stderr, idempotency | Bash 5.1 floor (see Hosts and runners) |
| PowerShell | PSScriptAnalyzer failing CI on `Error`, enforcing `PSUseApprovedVerbs`, `PSAvoidUsingCmdletAliases`, `PSUseShouldProcessForStateChangingFunctions`, `PSAvoidUsingInvokeExpression`, `PSAvoidUsingPlainTextForPassword`, `PSAvoidUsingConvertToSecureStringWithPlainText` | `[CmdletBinding()]`, approved verbs, `SupportsShouldProcess` on state changes; emit objects, never `Write-Host` for data | Pester 5 — Discovery then Run, so setup goes in `BeforeAll`/`BeforeEach` | State whether you target Windows PowerShell 5.1 or PowerShell 7+ |

## Frameworks

- **Backend:** FastAPI is established; other frameworks remain task/repository/contract choices.
  Huma is a Go option, not the default; Spring Boot remains support-only. `api-craft` owns HTTP/
  integration guidance, with identity, document workflows and verification selected per service.
- **Frontend:** React is the focus; Vue is in use. `frontend-craft` owns approved mixable kits,
  per-app identity, typed service integration and localhost/PCF serving; preserve the repository's framework.

## Hosts and runners

On-prem hosts/self-hosted Actions runners use **RHEL 9+**; GitHub-hosted Linux uses
**`runs-on: ubuntu-latest`**. Preserve that choice. Both are active, so portable shell targets
both with **Bash 5.1** as the floor; confirm exact target minors.

## Data stores

Operated engines are **PostgreSQL and SQL Server, on-prem**. MySQL is minor; **MariaDB/Oracle are
not used**. Embedded SQLite is not team-operated; a file on PCF ephemeral disk is neither shared
across app instances nor durable. Managed cloud databases are future candidates, not current estate:
their guidance is not yet applicable. Migration/locking/failover behavior needs exact-target evidence.
