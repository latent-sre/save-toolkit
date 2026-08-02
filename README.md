# SRE Agents

SRE Agents is a multi-host plugin containing **8 agents and 27 skills** for application engineering
and site reliability work. Claude Code reads the canonical [`agents/`](agents) and [`skills/`](skills)
sources directly. GitHub Copilot/VS Code and Codex receive committed, host-native projections made by
one deterministic generator; generated files are never edited by hand.

The roster, tool postures, and enforcement model are in [AGENTS.md](AGENTS.md). Routing is native:
Claude plugin components are namespaced as `sre-agents:<name>`; generated hosts use their native
bare component names.

## Layout

- [`agents/`](agents) — the eight canonical Claude plugin agent definitions; `tools` carries authority.
- [`skills/`](skills) — the 27 canonical skills and their progressive-disclosure `references/`,
  `assets/`, and `scripts/` bundles.
- [`commands/adr.md`](commands/adr.md) — the canonical Claude `/sre-agents:adr` scaffold.
- [`.claude-plugin/`](.claude-plugin) and [`hooks/`](hooks) — Claude manifest/marketplace plus the
  session-scoped guarded-Bash hook.
- [`plugin.json`](plugin.json), [`.github/agents/`](.github/agents), and
  [`platforms/copilot/skills/`](platforms/copilot/skills) — Copilot/VS Code plugin and projections.
- [`plugins/sre-agents/`](plugins/sre-agents) and [`.codex/agents/`](.codex/agents) — Codex skills
  plugin plus standalone custom-agent projections.
- [`scripts/`](scripts) — the structural gate (`gate_a.py`), the read-only allowlist guard
  (`readonly-guard.py`), the projection generator, supporting validators, and their tests.
- [`schemas/`](schemas) and the skill-bundled schema/validator pairs — portable evidence contracts:
  the [evidence envelope](schemas/evidence-envelope-v1.schema.json)
  ([`evidence_envelope.py`](scripts/evidence_envelope.py)), the
  [knowledge update](skills/operational-learning/assets/knowledge-update-v1.schema.json)
  ([`knowledge_update.py`](skills/operational-learning/scripts/knowledge_update.py)), and the
  [fleet-improvement ledger](skills/agent-authoring/assets/fleet-improvement-v1.schema.json)
  ([`fleet_improvement.py`](skills/agent-authoring/scripts/fleet_improvement.py)) with records under
  [`evals/improvements/`](evals/improvements).
- [`evals/`](evals) — offline behavioral contracts, the manual Claude runner, operator-run local
  Codex/Sol conformance runners, baseline records, and the bounded improvement ledger; see
  [`evals/README.md`](evals/README.md).
- [`docs/`](docs) — the only live backlog is [`docs/fleet-roadmap.md`](docs/fleet-roadmap.md);
  decisions live in [`docs/decisions/`](docs/decisions), closure evidence in
  [`docs/reviews/`](docs/reviews), and the documents under `docs/superpowers/plans/` are preserved
  implementation history, not task lists.

## The fleet

| Agent | Lane | Routing |
|---|---|---|
| `sde` | Build, fix, refactor, and test code or operations tooling | Delegates review to `reviewer`, operational docs to `scribe`, and sanitized public lookups to `researcher` |
| `reviewer` | Read-only correctness, quality, and security review | Reports findings; hands approved fixes to `sde`; terminal |
| `repository-investigator` | Local-only answers about private, current, or uncommitted checkout behavior | Cites `file:line`; no shell, write, web, external MCP, skill, or delegation |
| `sre` | Investigate active production or staging failures (guarded read-only Bash) | Delegates observability follow-up to `sre-steward`, operational docs to `scribe`, and fact checks to `researcher` |
| `sre-steward` | Steady-state observability as code (guarded read-only Bash) | Hands docs to `scribe`, active incidents to `sre`, automation to `sde`, and lookups to `researcher` |
| `scribe` | Write evidence-bound runbooks, resolved-incident postmortems, and approved service/application/alert knowledge | Local document writer with no shell, web, external MCP, or delegation authority |
| `researcher` | External-only research against official docs, upstream code, packages, and advisories | No local file access; returns cited public evidence to caller |
| `prompt-engineer` | The fleet's own files: agents, skills, descriptions, evals | Hands helper code to `sde`, injection review to `reviewer` |

The 27 skills, by area (each `skills/<name>/SKILL.md` carries its own description):

- **Engineering craft** — `craft`, `backend-craft`, `frontend-craft`, `ops-tooling`, `ci-actions`,
  `database-reliability`, `eng-ladder`
- **Platform** — `stack-profile`, `pcf-ops`, `pcf-deploy`
- **Change gates** — `merge-gate`, `release-gate`, `production-change-gate`
- **Incident and operations** — `root-cause`, `incident-command`, `postmortem`, `runbook`,
  `operational-learning`, `service-onboarding`
- **Observability** — `obs-logs`, `obs-metrics`, `obs-traces`, `obs-dashboards`, `obs-alerting`,
  `obs-pipeline`
- **The fleet itself** — `agent-authoring`, `agent-security`

## Validate and evaluate

Run the single structural entrypoint (on Windows use `python` or `py -3`, never `python3` — the
Microsoft Store stub):

```powershell
py -3 scripts/gate_a.py
```

Gate A owns its step list; do not copy that list into documentation. It proves the fleet is
well-formed, not that it is correct — the adversarial reviews in
[CONTRIBUTING.md](CONTRIBUTING.md) are separate.

Regenerate projections only after editing canonical sources:

```powershell
py -3 scripts/generate_platform_adapters.py --write
py -3 scripts/generate_platform_adapters.py
claude plugin validate . --strict
```

Install the generated Codex agents into an explicit scope without overwriting user-owned files:

```powershell
py -3 scripts/install_codex_agents.py --target C:\path\to\project\.codex\agents
# or, intentionally: py -3 scripts/install_codex_agents.py --user
```

Inspect repository and installed-host health without generating, installing, fetching, or starting a
model session (each check is a versioned evidence envelope; missing CLIs never count as passing):

```powershell
py -3 scripts/fleet_doctor.py
py -3 scripts/fleet_doctor.py --json
```

### Contract validators

Validate a knowledge-update packet after its documentation diff exists. The allowed roots are caller
policy supplied outside the packet — the packet's own `target.knowledge_roots` cannot authorize a
write location:

```powershell
py -3 skills/operational-learning/scripts/knowledge_update.py `
  .sre/knowledge-updates/<update-id>.json `
  --target-root C:\path\to\target-checkout `
  --allowed-knowledge-root docs/operations `
  --allowed-knowledge-root docs/runbooks
```

Validate a fleet-improvement record and the ledger corpus from a full-history source checkout (the
scanner fails closed on a shallow clone):

```powershell
py -3 skills/agent-authoring/scripts/fleet_improvement.py `
  evals/improvements/<improvement-id>/record.json `
  --repository-root . `
  --expected-repository latent-sre/sre-agents `
  --allowed-root agents --allowed-root skills --allowed-root evals `
  --allowed-root scripts --allowed-root schemas --allowed-root hooks --allowed-root commands `
  --allowed-evidence-root evals/evidence --allowed-evidence-root evals/baselines `
  --evidence-validator scripts/evidence_envelope.py `
  --authority-actor AUTHENTICATED_IDENTITY --authority-role triage

py -3 scripts/validate_improvement_ledger.py --repository-root .
```

The ledger's lifecycle rules, budget ceilings, artifact-selection digest, and rollback contract are
specified in one place:
[`skills/agent-authoring/references/improvement-lifecycle.md`](skills/agent-authoring/references/improvement-lifecycle.md).
It activates only from measured encounters and does not let an agent approve, merge, deploy, or
rewrite itself; protected workflows remain the authority boundary.

### Behavioral and conformance evals

Claude behavioral evaluations under [`evals/`](evals) remain manual. Codex/Sol conformance is also
manual and local: the runners accept only this repository checkout with fixed manifests, copy the
operator's existing Codex login into a disposable same-user home, and delete it before the report is
returned — behavioral evidence, not hostile-code containment. Every report labels source review as
unverified and sets independent evaluation, baseline eligibility, and release grant to false; commit
and independently review the exact revision before a live run. The design and its limits are recorded
in [`docs/decisions/2026-08-01-local-sol-conformance.md`](docs/decisions/2026-08-01-local-sol-conformance.md).

```powershell
py -3 evals/run_codex_conformance.py --validate
```

The credential boundary, pass oracle, provenance record, and the status of the revoked 2026-07-31
Sol baselines are documented in [`evals/README.md`](evals/README.md). For repository-controlled
executable checks, use the digest-bound, networkless container boundary in
[`docs/verification-sandbox.md`](docs/verification-sandbox.md).

## Current status

- Canonical source, generated host adapters, hook wiring, manifests, and eval contracts are
  structurally gated (Gate A); Claude marketplace validation and isolated plugin loading are
  verified on the recorded CLI version.
- Codex/Sol manifests, local same-user auth handling, response reduction, and explicit custom-agent
  contracts pass offline validation; a fresh exact-revision run plus external review remains
  pending. Copilot/VS Code runtime loading remains unverified because that runtime is not available
  on the current validation host.
- Publication is blocked on repository protection, distinct promotion authority, host install smoke
  tests, and rollback evidence — tracked in [`docs/fleet-roadmap.md`](docs/fleet-roadmap.md).

## Contribute

Start with [AGENTS.md](AGENTS.md) for the repository workflow and [CONTRIBUTING.md](CONTRIBUTING.md) for
authoring and review policy. The redesign's decision record is preserved in git history (tag
`pre-cleanup-2026-07-15`).
