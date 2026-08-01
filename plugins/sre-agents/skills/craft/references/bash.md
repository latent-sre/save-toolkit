# Bash craft

Shell is for glue and orchestration. If a script grows real logic/data structures, recommend the
[Python conventions](./python.md) instead.

## Always start with
```bash
#!/usr/bin/env bash
set -Eeuo pipefail
shopt -s inherit_errexit 2>/dev/null || true   # bash>=4.4 only; best-effort on RHEL7-era on-prem hosts
```
- **Set `IFS` locally where you split, not globally.** A global `IFS=$'\n\t'` changes *every* unquoted
  expansion and surprises more than it helps; scope it to the read that needs it
  (`while IFS=',' read -r a b; do …`). Quoting every expansion is the real fix.
- Trap cleanup: `tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT`.
- **`set -e` is leakier than it looks** — suppressed inside `if`/`while`/`&&`/`||` conditions and
  command substitutions `$(...)`. `shopt -s inherit_errexit` makes `-e` reach `$(...)` (bash>=4.4; guard
  as `shopt -s inherit_errexit 2>/dev/null || true` on RHEL7-era on-prem hosts); the `-E` in
  `set -Eeuo pipefail` makes an `ERR` trap also fire inside functions/subshells.
- `((i++))` **returns non-zero when the result is 0**, which under `-e` exits the script — use
  `((i++)) || true` or `i=$((i+1))`.

## Quoting & tests (the #1 source of bugs)
- **Quote every expansion:** `"$var"`, `"${arr[@]}"`, `"$(cmd)"`. Unquoted = word-splitting + globbing bugs.
- Use `[[ ... ]]` not `[ ... ]`; `[[ -z "$x" ]]`, `[[ "$a" == "$b" ]]`, `[[ "$s" =~ regex ]]`.
- Arithmetic in `(( ... ))`; integer compare with `-eq`/`-lt` inside `[[ ]]`.
- **Never parse `ls`**; use globs or `find -print0 | while IFS= read -r -d ''`.
- Guard destructive paths: `rm -rf "${dir:?}"/...` — the `:?` aborts if `$dir` is empty/unset (stops an
  accidental `rm -rf /`; shellcheck SC2115).
- Capture command output into an array with `mapfile -t arr < <(cmd)`, not `arr=($(cmd))` (SC2207).

## Structure
- Functions + a `main "$@"`; `local` for function vars. Put `main` call at the bottom.
- Validate inputs early; print usage on bad args. Errors → stderr: `echo "msg" >&2`.
- Meaningful exit codes; check command success explicitly where `-e` isn't enough.
- `readonly`/`declare -r` for constants; prefer `$(...)` over backticks.

## Quality gate
- **Pass `shellcheck`** with no warnings (or justified `# shellcheck disable=` with a reason).
- POSIX-portable (`#!/bin/sh`) only if it must run on non-bash; otherwise bash is fine — state which.
- Make it idempotent; guard destructive actions (`rm`, overwrites) behind a confirm flag or dry-run.

## Tests
- `bats` (or an assert harness): check exit codes, stdout/stderr, and idempotency. See the [tests-first process](./tdd.md).
