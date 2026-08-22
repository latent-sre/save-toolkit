# ADR: Take `observability-engineer` off the read-only Bash guard

- Date: 2026-08-21
- Status: Accepted
- Decision owners: save-toolkit maintainers

## Context

`observability-engineer` owns Grafana dashboards as code. Until this decision it ran Bash under the
fail-closed allowlist guard (`scripts/readonly-guard.py`, wired in `hooks/hooks.json`) with `sre`'s
read set plus three config validators. The guard has no `curl`, no Grafana CLI, and no interpreter,
so the agent could not search, read, export, create, or update a dashboard on any Grafana instance.
The `obs-dashboards` skill on this branch spelled the consequence out: "guarded agents therefore do
not call this API themselves — they prepare the exact request for a human or CI." In practice every
dashboard task ended in a hand-off of a `curl` command for a person to paste, and the agent never
saw the response it was reasoning about.

The owner's call (2026-08-21) is that the guard is over-restrictive for this lane: the agent should
view, create, and edit dashboards itself, on any Grafana including production, over the HTTP API.

Three shapes were on the table:

1. Drop `observability-engineer` from the guard's roster; keep the guard on `sre`.
2. Remove the guard hook entirely.
3. Keep the guard and add `curl`/Grafana-CLI forms to the observability allowlist.

## Decision

Shape 1. `GUARDED_AGENT_NAMES` and the generator's `GUARDED_AGENTS` both shrink to `{"sre"}`;
`observability-engineer` holds unguarded Bash like `sde` and `prompt-engineer`. The agent body gains
a **dashboard write rule**: Grafana dashboard create/update over the HTTP API is the one live apply
this agent performs itself, in any environment, under four ordered conditions — target and full
JSON diff shown before the call; live model exported first as the rollback; updates pin the live
`version` with `overwrite: false`; the applied JSON is exported and committed to the
dashboards-as-code path in the same task with the PR/commit in the save `message`. Dashboards and
their folders only. Every other live change (alert rules, data sources, contact points, permissions,
pipelines) keeps its Tier 2/3 recommend-only posture.

The obs-only validator branches in the guard (`promtool check`, `yamllint`) are removed with the
roster entry: no guarded agent could reach them any more, and dead allowlist entries are exactly
the kind of text that later reads as a control.

## Alternatives considered

- **Remove the guard entirely (shape 2):** rejected for now. `sre` still needs the guard — it
  investigates live incidents with web egress and must not apply mitigations — and the removal
  touches ~50 files including two accepted ADRs, the adapter generator, `validate_fleet`, `gate_a`,
  `fleet_doctor`, and six test files. Nothing in the dashboard use case requires it.
- **Widen the allowlist (shape 3):** rejected. The guard is an allowlist of *readers* by design
  (its docstring records why a denylist lost). `curl -X POST` and `-d @file` are writers; admitting
  them means parsing curl flags to tell a GET from a POST, and the first missed flag is a silent
  allow. An agent that is meant to write should simply be unguarded, with the write rule stated in
  its body where a reviewer can read it.

## Consequences

- `observability-engineer` can now run anything `sde` can: interpreters, installs, `git push`. Its
  body restricts what it *should* do; nothing mechanical restricts what it *can*. Host and network
  egress controls are load-bearing for this lane, as they already were for `sde` and
  `prompt-engineer` (`AGENTS.md`, Honest limits).
- Credential hygiene moves from hook to doctrine: `cf env`, `gcloud auth print-access-token`,
  `gcloud secrets versions access`, and service-account tokens stay out of tracked files,
  transcripts, and packets because the agent body says so, not because a hook denies them.
- The Copilot projection of `observability-engineer` now carries the `execute` tool; the Codex
  projection is unchanged (it already requested `workspace-write` for a Write-holding role).
- `docs/rules.md`, `AGENTS.md`, `README.md`, `CLAUDE.md`, the `agent-security` and
  `production-change-gate` skills, and `.github/copilot-instructions.md` all state the new roster.
  `scripts/test_readonly_guard.py` proves the guard no-ops for both `agent_type` spellings of the
  role while still denying the identical commands to `sre`.
- The `obs-dashboards` skill is rewritten around the agent calling the API itself (same branch).

## Rollback

Restore `"observability-engineer"` to `GUARDED_AGENT_NAMES` in `scripts/readonly-guard.py` and to
`GUARDED_AGENTS` in `scripts/generate_platform_adapters.py`, reinstate the `promtool`/`yamllint`
branches, revert the agent body's Bash paragraph and dashboard write rule, and regenerate adapters
with `python scripts/generate_platform_adapters.py --write`. `validate_fleet.validate_guard_wiring`
fails if only one of the two rosters is reverted.
