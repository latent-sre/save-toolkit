# Bash idiom

Use shell for bounded glue. If the script needs complex data structures, concurrency, or substantial
business logic, use the repository's application language. State whether the target is Bash or POSIX
`sh`; do not use Bash syntax under `#!/bin/sh`.

## Shell options and status

- For a standalone Bash script, consider `set -Eeuo pipefail` only after auditing expected nonzero
  statuses. It is a backstop, not error policy. A sourced/library script must not unilaterally change
  its caller's options.
- `errexit` is suppressed in conditions and other contexts; command substitution and functions have
  version/context traps. Check the statuses that matter explicitly.
- Declare then assign when status matters: `local value; value=$(command)`. `local value=$(command)`
  reports `local`'s status. Arithmetic such as `((i++))` can return nonzero when the expression is zero.
- Use traps for bounded cleanup, with a verified temporary path. Cleanup must never expand an empty or
  unresolved target into a broad destructive command.

## Data and quoting

- Quote expansions (`"$value"`, `"${items[@]}"`) unless splitting/globbing is the explicit contract.
  Scope `IFS` to the read/split that needs it.
- Use `[[ ... ]]` and `(( ... ))` in Bash; use NUL-delimited paths for arbitrary filenames. Do not
  parse `ls` or capture command output into an array through unquoted substitution.
- Validate arguments early, send diagnostics to stderr, return meaningful status codes, and keep data
  output separate from logs.
- Guard state-changing and destructive paths with exact target validation, dry run/confirmation where
  authorized, and idempotent convergence.

## Verification

Run the repository's ShellCheck configuration and tests (Bats or another harness if present). Test
exit status, stdout/stderr, empty/space/newline/glob filenames, partial failure, signals/cleanup,
idempotency, and the dry-run effect boundary. Justify any analyzer suppression next to the exact line.
