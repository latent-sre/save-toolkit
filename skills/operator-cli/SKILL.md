---
name: operator-cli
description: >-
  Build or repair an operator-facing CLI that works interactively and in automation, including
  partial failures, machine output, dry runs, and interruption. Triggers: 'build an operator CLI',
  'make this command safe for automation', 'fix this CLI contract'. Not for running an existing
  operational command (production-change-gate; during a live incident, incident-investigation), a
  web UI (frontend-craft), or the HTTP API behind a CLI (api-craft).
argument-hint: "[command or operator workflow]"
---

# Operator CLI craft

Match existing language, framework, flags, exit codes, and consumers. Load `stack-profile` before
new tooling choices; the caller retains authority. Before designing effects, establish the target
API's effect and idempotency contract: can an item be applied twice, and what does a timeout mean?
For Go implementation, load `go-craft` alongside this command contract.

## Make the command composable

- Results go to stdout; diagnostics/progress to stderr. Machine output (`--json` or the existing
  format) parses even on partial failure.
- For batch operations, report every item's outcome (`succeeded`, `failed`, `unknown`, `skipped`).
  `skipped` means never attempted; an attempt the target rejected is `failed`. A new contract uses
  these exit codes:

| Exit | Meaning |
|---|---|
| 0 | Successful completion, including a dry run |
| 1 | Operational failure: any item `failed` or `unknown` |
| 2 | Usage error, including a destructive request without confirmation |
| 128+N | Stopped by signal N: 130 for SIGINT, 143 for SIGTERM (a Bash convention; on Windows the command returns it itself) |

- Expected errors name the failure and next step; tracebacks need debug mode. Check subprocess
  and pipeline outcomes explicitly: strict mode/linting does not prove failure propagation.
- Keep `--help` useful: one worked example, exit codes, configuration precedence, and side effects.
  Match existing precedence; for a new contract use flags > environment > config file > defaults.
  Debug output shows effective non-secret settings and where secrets came from, never their values.
- Bound external calls, retries, pagination, and total work; progress does not substitute for a
  timeout. A reader that closes early (`tool --json | head`) ends the command without a traceback;
  a state-changing command takes the signal stop path first. In Python, catch `BrokenPipeError`,
  then point stdout at `os.devnull` before exiting, as the `signal` docs show.

## Make effects explicit

- A state-changing command offers a real dry run: the same decision logic computes the plan,
  while the effect boundary performs no writes. Show exact targets, blast radius, and the target
  environment (account, project, cluster, org/space, or endpoint) before apply.
- An empty filter, unset variable, or match-all wildcard never selects everything without
  `--all`. Validate inputs and permissions before the first write.
- Confirmation covers the exact set and environment shown: apply consumes the saved plan (checked
  by hash) or re-selects and refuses if the set changed. Bulk effects run in bounded batches (a
  `--max-items` cap or a rate) and stop when a batch's failure rate crosses a stated threshold.
- Destructive actions require explicit confirmation. Prompt only when stdin is a TTY (Go:
  `x/term.IsTerminal`, not `os.ModeCharDevice`) and `--no-input` is unset; otherwise require the
  established confirmation flag or exit 2 at once. A non-interactive run names its environment
  rather than using the default context, and a severe action takes `--confirm=<target name>`. A
  confirmation flag is not production approval and cannot bypass an owner gate.
- PowerShell: `-WhatIf` and `-Confirm` reach only effects wrapped in `$PSCmdlet.ShouldProcess`,
  not native commands, REST calls, or other script modules; `What if:` lines are host text. A
  destructive command sets `ConfirmImpact='High'`, takes `-Confirm:$false` as the explicit flag,
  and without it exits 2 before any effect when non-interactive. Check `$LASTEXITCODE` after
  native commands (or set `$PSNativeCommandUseErrorActionPreference` on 7.4+), end with
  `exit <code>`, and schedule `pwsh -File` so the code propagates.
- Re-running after partial failure must converge safely or refuse with a useful recovery step. A
  disconnected, interrupted, or error-status effect may have happened: keep it `unknown` and read
  back target state before classifying or retrying.
- Assume crashes: SIGKILL, OOM and grace-period kills, and Windows `TerminateProcess` run no
  handler. Write a per-item receipt (JSON lines: target, item, operation id, outcome, UTC time,
  actor) to a named path or in `--json` output; a path receipt records intent before each effect,
  so a re-run skips succeeded items and reconciles an intent without an outcome as `unknown`.
  Locks carry an owner and an expiry; take over a stale lock only once its owner is gone.
- On SIGINT or SIGTERM, stop scheduling work, release owned locks/temp resources, report
  completed, failed, and `unknown` items, then exit 128+N. Cleanup is time-bounded; a second SIGINT or SIGTERM skips it. In Python,
  one flag-setting handler for both signals, checked between effects, replaces
  `KeyboardInterrupt`, which can land mid-effect. In Go, call `stop()` once the
  `signal.NotifyContext` context fires; `defer stop()` alone ignores a second Ctrl-C. Cleanup does
  not undo completed external effects or delete another process's resources.
- Obtain secrets through the established binding or store, never command-line flags, ad hoc
  environment variables, logs, tracebacks, or configuration dumps.

## Verify the operator contract

Use the project's language and test runner at the real command boundary. Select checks for its
actual capabilities; a read-only command needs no apply plan, effect receipt, confirmation, or
lock. Exercise effects against disposable targets or controlled clients.

| Capability | Evidence needed |
|---|---|
| State changes | Dry run makes zero effect calls; apply uses the shown target set or refuses drift |
| Destructive actions | Piped input never confirms; missing non-interactive confirmation exits 2 before any effect |
| Re-runs and locks | No blind replay of succeeded or `unknown` items; competing runs cannot violate the protected invariant; another owner's lock remains intact |
| Interruptible work | Signal exit status and owned-resource cleanup; completed effects reported and unresolved effects `unknown` |
