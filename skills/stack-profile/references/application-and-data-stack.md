# Application and data stack

Read when the request needs a service language, framework, CI platform, tooling, or authentication
design, runner/host assumption, or data-store choice. The parent `SKILL.md` owns the current-runtime
and platform boundaries. These facts do not authorize a migration or make a target-specific version
known.

## Languages and CI

Services are built in **Java/JVM, Python, JavaScript/TypeScript, and Go**. Bash and PowerShell are
glue and automation, not service languages. GitHub + GitHub Actions; Bamboo is legacy.
*[sourced: operator statement 2026-08-21]*

**CI jobs authenticate from GitHub environment secrets**, not GitHub OIDC. This settles the hedge
the `ci-actions` skill carries: do not design around a GitHub-OIDC→CredHub exchange — CredHub
authenticates via UAA and no turnkey integration exists. *[sourced: operator statement 2026-08-21]*

## Toolchain by language

Defaults for new code; a repository's own tooling wins. Rows without an operator statement are fleet
defaults until the owner records a decision here.

| Language | Format and lint | Types and analysis | Tests | Environment or runtime |
|---|---|---|---|---|
| Python | `ruff` for both lint and format, with the `B` (bugbear) rules selected | `mypy` or `pyright`; prefer `dataclasses`/`pydantic` to loose dicts | `pytest` with `parametrize`, fixtures, `tmp_path`, `monkeypatch`, and an injected clock | `uv` (`poetry` is fine for a published library); never `pip install` into system Python |
| Java | Spotless driving google-java-format or palantir-java-format, enforced in CI | Error Prone + NullAway with `-Xlint:all` as errors; `@NullMarked` packages (JSpecify); package by feature, not by layer | JUnit Jupiter + AssertJ, `@ParameterizedTest` for tables; Mockito only for collaborators you don't own | Wrapper checked in (`./mvnw` / `./gradlew`), versions from the Spring Boot BOM; read `maven.compiler.release` or the Gradle toolchain, not `java` on `PATH` |
| TypeScript/JavaScript | ESLint with `@typescript-eslint/no-floating-promises` and `no-misused-promises` | `strict` on, no `any`, `unknown` narrowed at the boundary; branded IDs and exhaustively switched discriminated unions | Vitest or Jest + React Testing Library, MSW at the network boundary, Playwright for the few critical journeys | The repository's package manager and its `tsconfig` target |
| Go | `gofmt`/`goimports` enforced in CI | `go vet`, and `golangci-lint` on the baseline `staticcheck`, `govet`, `errcheck`, `ineffassign`, `unused` | Table-driven `t.Run` subtests; `go test -race` targeted at concurrent code | `go.mod`'s `go` directive gates semantics; Semantic Import Versioning (`/v2`) |
| Bash | `shellcheck` clean, or a justified `# shellcheck disable=` carrying a reason | The four-line header: `#!/usr/bin/env bash`, `set -Eeuo pipefail`, and the bare `shopt -s inherit_errexit` — the 5.1 floor stated above allows it, so no `\|\| true` guard | `bats`: exit codes, stdout/stderr, idempotency | Bash 5.1 floor (see Hosts and runners) |
| PowerShell | PSScriptAnalyzer failing CI on `Error`, enforcing `PSUseApprovedVerbs`, `PSAvoidUsingCmdletAliases`, `PSUseShouldProcessForStateChangingFunctions`, `PSAvoidUsingInvokeExpression`, `PSAvoidUsingPlainTextForPassword`, `PSAvoidUsingConvertToSecureStringWithPlainText` | `[CmdletBinding()]`, approved verbs, `SupportsShouldProcess` on state changes; emit objects, never `Write-Host` for data | Pester 5 — Discovery then Run, so setup goes in `BeforeAll`/`BeforeEach` | State whether you target Windows PowerShell 5.1 or PowerShell 7+ |

## Frameworks

- **Backend:** **Spring Boot** on the JVM (matching the `java_buildpack_offline` in the PCF manifest
  example); **FastAPI** on Python.
- **Frontend:** **both React and Vue** are in use — neither reference in `frontend-craft` is
  surplus.

*[sourced: operator statement 2026-08-21]*

## Hosts and runners

On-prem hosts and self-hosted Actions runners are **RHEL 9+**. GitHub-hosted Linux runners are
Ubuntu. Both classes are in active use, so portable shell
must run on both: the effective **bash floor is 5.1**, past every pre-4.4 workaround.
*[sourced: operator statement 2026-08-21; confirm exact minor versions on the target]*

## Data stores

**PostgreSQL and SQL Server** are the operated engines, **all on-prem today**. Some applications
embed **SQLite**; treat it as something to be aware of, not an engine the team operates — the one
rule worth carrying is that a SQLite file behind a multi-instance app on PCF's ephemeral disk is
not shared and not durable. MySQL exists but is minor; **MariaDB and Oracle are not used**.
A managed cloud database is a possible future addition alongside the GCP migration, but
nothing is running there now: treat cloud-database guidance as not-yet-applicable rather than
optional. Engine-specific migration, locking, and failover mechanics remain `[unverified]` per
target until captured against a real instance. *[sourced: operator statement 2026-08-21]*
