# Bash idiom

Shell is for glue and orchestration. If a script grows real logic or data structures, recommend the
[Python conventions](./python.md) instead.

## Always start with

```bash
#!/usr/bin/env bash
set -Eeuo pipefail
shopt -s inherit_errexit
```

**The fleet's bash floor is 5.1** — on-prem hosts and runners are RHEL 9+, and GitHub-hosted Linux
runners are Ubuntu; both are well past the 4.4 that `inherit_errexit` needs *[sourced: operator
statement 2026-08-21; confirm the exact minor on the target host]*. Write the bare `shopt`. The
defensive `shopt -s inherit_errexit 2>/dev/null || true` form belongs to pre-4.4 hosts, and carrying
it forward is worse than useless here: `|| true` swallows a genuine failure and leaves `-e` quietly
not reaching `$(...)`.

- **Pass `shellcheck`** with no warnings, or a justified `# shellcheck disable=` carrying a reason.
- Test with **`bats`**: check exit codes, stdout/stderr, and idempotency.
