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

Match existing language, flags, exit codes, and consumers. Load `stack-profile` before new tooling
choices (`go-craft` for Go, `python-craft` for Python). Establish the target API's idempotency and
timeout semantics before designing mutations.

## Output, exit codes, and composability

- `stdout` carries results (`--json` parses cleanly even on dry runs, partial failure, or signal
  interrupt); `stderr` carries diagnostics and progress.
- Report every planned batch item as `succeeded`, `failed` (rejected by target), `unknown`
  (timeout/disconnect/uncertain effect), or `skipped` (never attempted: dry-run items or items after
  an early stop).
- Exit codes for new contracts: `0` = complete success or `--dry-run`; `1` = operational failure (any
  `failed` or `unknown` item); `2` = usage error or missing non-interactive confirmation (before any
  effect or lock); `128+N` = signal `N` (`130` `SIGINT`, `143` `SIGTERM`, returned directly on Windows).
- Errors name the failure and recovery step (tracebacks only in debug mode); check subprocess and
  pipeline exit codes explicitly.
- `--help` covers a worked example, exit codes, config precedence (`flags > env > config > defaults`),
  and side effects; debug logs show non-secret config and secret sources, never secret values.
- Bound external calls, retries, pagination, and total work with explicit timeouts. Handle
  `BrokenPipeError` cleanly (redirect `stdout` to `os.devnull`, exit cleanly; mutating commands take
  the signal stop path first).

## Explicit effects, confirmation, crashes, and signals

- **Dry run & selectors:** `--dry-run` executes the same selection/decision logic with zero writes,
  showing exact targets, blast radius, and target environment (reporting planned items as `skipped`
  in `--json`). Empty filters, unset vars, or wildcards never select all items without `--all`.
  Validate inputs and permissions before the first write.
- **Confirmation & batching:** Confirmation binds the shown target set and environment (hash-checked
  plan or re-select/refuse drift). Prompt only on a TTY (`sys.stdin.isatty()`; Go `x/term.IsTerminal`,
  not `os.ModeCharDevice`) without `--no-input`; piped stdin must never confirm. Non-interactive runs
  without `--yes` (or `--confirm=<target>`) exit `2` before taking locks or issuing effects.
  Confirmation flags never authorize production changes. Bound bulk runs (`--max-items`/rate) and
  stop scheduling on failure/`unknown`, leaving remaining items `skipped`.
- **PowerShell:** `-WhatIf`/`-Confirm` reach only `$PSCmdlet.ShouldProcess`, not native commands or
  REST calls. Destructive cmdlets set `ConfirmImpact='High'`, require `-Confirm:$false` when
  non-interactive (else exit `2`), check `$LASTEXITCODE` / `$PSNativeCommandUseErrorActionPreference`,
  end with `exit <code>`, and schedule via `pwsh -File`.
- **Uncertain outcomes, restarts & locks:** Write a per-item intent (target, item, stable op ID,
  actor, UTC time) before consequential requests, or reconcile from the authoritative target
  (`get_status`/readback) on timeout/restart. On restart, skip confirmed successes and never blindly
  replay `unknown` items: retry only if no effect occurred or the target deduplicates by op ID;
  otherwise mark `unknown`, stop dependent work, exit `1`, and name recovery. Locks carry owner +
  expiry; break stale locks only once the owner is gone.
- **Signals & secrets:** Handle both `SIGINT` and `SIGTERM` (in Python use one handler for both
  rather than `KeyboardInterrupt` alone; in Go call `stop()` once `signal.NotifyContext` fires so a
  second signal skips cleanup). On signal, stop new work (leaving rest `skipped`), run time-bounded
  `finally` cleanup for owned locks/temps, emit the `--json`/status report, and exit `128+N`. Read
  secrets from established stores/bindings only, never CLI flags, logs, or dumps.

## Verify the operator contract

| Capability | Evidence needed at the real CLI boundary |
|---|---|
| State changes | `--dry-run` makes zero writes and outputs `skipped` plan; apply refuses set drift |
| Destructive actions | Piped stdin never confirms; missing non-interactive confirmation exits `2` before effects/locks |
| Re-runs & locks | No blind replay of `succeeded`/`unknown` items; competing runs respect owned locks |
| Consequential effects | Timeout/hard-kill after commit reconciles via readback or exits `1` with `unknown` (no replay) |
| Interruptible work | `SIGINT` (`130`) / `SIGTERM` (`143`) stops new items, frees owned locks, emits complete item report |
