---
name: operator-cli
description: >-
  Build or repair an operator-facing CLI that works interactively and in automation, including
  partial failures, machine output, dry runs, and interruption. Triggers: 'build an operator CLI',
  'make this command safe for automation', 'fix this CLI contract'. Not for running an existing
  operational command (production-change-gate; during a live incident, incident-investigation), a
  web UI (frontend-craft), or the service behind a CLI (backend-craft).
argument-hint: "[command or operator workflow]"
---

# Operator CLI craft

Match existing language, framework, flags, exit codes, and consumers. Load `stack-profile` before
new tooling choices; the caller retains authority. Before designing effects, establish the target
API's effect and idempotency contract: can an item be applied twice, and what does a timeout mean?

## Make the command composable

- Results go to stdout; diagnostics/progress to stderr. Machine output (`--json` or the existing
  format) parses even on partial failure. Human and machine views share result data. Preserve the
  published schema or provide a versioned migration.
- Report every item's outcome (`succeeded`, `failed`, `unknown`, `skipped`). `skipped` means
  never attempted; an attempt the target rejected is `failed`. Keep existing exit codes; a new
  contract uses these:

| Exit | Meaning |
|---|---|
| 0 | Every item succeeded, or a dry run completed |
| 1 | Operational failure: any item failed or remains UNKNOWN |
| 2 | Usage error, including a destructive request without confirmation |
| 128+N | Stopped by signal N: 130 for SIGINT, 143 for SIGTERM |

- Expected errors name the failure and next step; tracebacks need debug mode. Check subprocess
  and pipeline outcomes explicitly: strict mode/linting does not prove failure propagation.
- Keep `--help` useful: one worked example, exit codes, configuration precedence, and side effects.
  Match existing precedence; for a new contract use flags > environment > config file > defaults.
  Debug output shows effective non-secret settings and where secrets came from, never their values.
- Honor `NO_COLOR` and non-TTY output. Bound external calls, retries, pagination, and total work;
  progress does not substitute for a timeout. A reader that closes early (`tool --json | head`)
  ends the command without a traceback: in Python, catch `BrokenPipeError` as the `signal` docs
  show.

## Make effects explicit

- A state-changing command offers a real dry run: the same decision logic computes the plan,
  while the effect boundary performs no writes. Show exact targets and blast radius before apply.
- Confirmation covers the exact set shown: apply consumes the saved plan (checked by hash) or
  re-selects and refuses if the set changed. Bulk effects run in bounded batches (a `--max-items`
  cap or a rate) and stop when a batch's failure rate crosses a stated threshold.
- Destructive actions require explicit confirmation. Prompt only when stdin is a TTY and
  `--no-input` is unset; otherwise require the established confirmation flag or exit 2 at once.
  Never read a confirmation from a pipe. A confirmation flag is not production approval and cannot
  bypass an owner gate. PowerShell: the dry run is `-WhatIf` through `SupportsShouldProcess`, and
  a destructive command sets `ConfirmImpact='High'`, with `-Confirm:$false` as the explicit flag.
- Re-running after partial failure must converge safely or refuse with a useful recovery step.
  A disconnected or interrupted effect may have happened: retain UNKNOWN and reconcile target
  state before retrying, rather than treating a missing response as proof of failure.
  An error status alone does not prove no effect; read back state before classifying the outcome
  or retrying. Write a per-run receipt (JSON lines: target, item, operation id, outcome, UTC time,
  actor) to a named path or in `--json` output, so a re-run skips succeeded items and reconciles
  UNKNOWN ones.
- On SIGINT or SIGTERM, stop scheduling work, release owned locks/temp resources, report
  completed, failed, and UNKNOWN items, and exit 128+signal. A second SIGINT skips slow cleanup.
  Python turns only SIGINT into an exception (`KeyboardInterrupt`); install a SIGTERM handler that
  takes the same path, or schedulers and CI cancellation kill the command without cleanup. Cleanup
  does not undo completed external effects or delete another process's resources.
- Obtain secrets through the established environment, binding, or store—not command-line flags,
  logs, tracebacks, or configuration dumps. Live production changes remain prepared for the human
  release owner under `production-change-gate`; implementing the CLI grants no execution authority.

## Verify the operator contract

Start from the [contract test](./assets/test_cli_contract.py) and the
[reference command](./assets/cli_contract.py) it exercises: copy both, adapt the command, flags,
and effect seam to the task, and keep every case. Use the repo's test runner at the command
boundary, against disposable targets or controlled effects:

The reference requires positive `--older-than` minutes and a positive `--max-items` (default 100).
It refuses an oversized plan before effects, then stops at the first failed or UNKNOWN item and
reports the remainder as `skipped`. Dry-run JSON uses the same `items` schema, all `skipped`.
An exclusive local lock protects selection revalidation and apply; an existing or changed owner
causes refusal. This cooperative lock is scoped to the working directory, not a distributed API lock.

| Case | Evidence needed |
|---|---|
| Help and success | Useful usage; documented precedence; machine output parses without diagnostic chatter |
| Partial failure | Item outcomes preserved; exit 1; no blind replay of successful or UNKNOWN effects |
| Dry run and non-TTY destructive request | Effect calls stay zero; piped input never confirms; missing confirmation exits 2 promptly |
| Target set changes before apply | Refused, or apply uses the saved plan |
| Invalid bounds, oversized plan, first failure/UNKNOWN | Positive bounds required; oversized plan makes no effects; later items stay skipped |
| Existing, concurrent, or replaced lock | No overlapping apply; another owner's lock remains intact |
| SIGINT and SIGTERM during work | 130 and 143; owned resources released; completed items reported; unresolved effects UNKNOWN |
| Reader closes stdout early | No traceback |
