# Save Toolkit

A multi-host engineering plugin: **8 agents and 29 skills** for application engineering and site
reliability work — build/review/ship lanes, incident command, PCF and GCP triage, observability as
code, and evidence-bound documentation. Claude Code reads the canonical [`agents/`](agents) and
[`skills/`](skills) directly; GitHub Copilot/VS Code and Codex receive committed projections from
one deterministic generator, never edited by hand.

> **Pre-release (0.1.0).** Installs track `main` and may change without notice. Immutable tagged
> releases arrive when [`RELEASE-001`](docs/fleet-roadmap.md) closes; recovery and rollback then
> follow the [release runbook](docs/release-runbook.md).

## Quickstart

**Claude Code** (pre-release install from `main`):

```sh
claude plugin marketplace add latent-sre/save-toolkit
claude plugin install save-toolkit@latent-sre
```

**VS Code / Copilot Chat:** open this repository as the workspace — agents are discovered from
`.github/agents/` automatically, and [`.vscode/settings.json`](.vscode/settings.json) registers the
skill projection. For other workspaces install at user level (`~/.copilot/agents/`,
`~/.copilot/skills/`); copied agent files arrive without their skills.

**Codex:** `codex plugin marketplace add latent-sre/save-toolkit` and
`codex plugin add save-toolkit@latent-sre` install the skills; agents are a separate conflict-safe
install from a checkout: `python scripts/install_codex_agents.py --target <project>/.codex/agents`.

**Before first use:** [`skills/stack-profile/SKILL.md`](skills/stack-profile/SKILL.md) declares
*this* team's stack (PCF, GCP Cloud Run, Wavefront, Splunk, Akamai). Every platform-touching skill
routes through it — if that is not your stack, edit it first or the fleet will confidently
recommend someone else's tools.

**Then just describe the problem** — routing is by description, no commands to memorize:

- *"orders is 502-ing in prod since 14:20 UTC — investigate"* → the `sre` agent triages read-only
  and recommends a mitigation for a human to apply.
- *"is PR #42 ready to merge?"* → the `merge-gate` checklist, consuming the typed reviewer's packet.
- *"write a runbook for the checkout deploy"* → the `scribe` agent with the `runbook` skill.

The one manual command is `/save-toolkit:adr` (ADR scaffold).

## The fleet

| Agent | Lane | Routing |
|---|---|---|
| `sde` | Build, fix, refactor, and test code or operations tooling | Delegates review to `reviewer`, operational docs to `scribe`, and sanitized public lookups to `researcher` |
| `reviewer` | Read-only correctness, quality, and security review | Reports findings; hands approved fixes to `sde`; terminal |
| `repository-investigator` | Local-only answers about private, current, or uncommitted checkout behavior | Cites `file:line`; no shell, write, web, external MCP, skill, or delegation |
| `sre` | Investigate active production or staging failures (guarded read-only Bash) | Delegates observability follow-up to `observability-engineer`, operational docs to `scribe`, and fact checks to `researcher` |
| `observability-engineer` | Steady-state observability as code (guarded read-only Bash) | Hands docs to `scribe`, active incidents to `sre`, automation to `sde`, and lookups to `researcher` |
| `scribe` | Write evidence-bound runbooks, resolved-incident postmortems, and approved service/application/alert knowledge | Local document writer with no shell, web, external MCP, or delegation authority |
| `researcher` | External-only research against official docs, upstream code, packages, and advisories | No local file access; returns cited public evidence to caller |
| `prompt-engineer` | The fleet's own files: agents, skills, descriptions, evals | Hands helper code to `sde`, injection review to `reviewer` |

The 29 skills, by area (each `skills/<name>/SKILL.md` carries its own description and triggers):

- **Engineering craft** — `language-idiom`, `backend-craft`, `frontend-craft`, `ops-tooling`,
  `ci-actions`, `database-reliability`, `eng-ladder`
- **Platform** — `stack-profile`, `pcf-ops`, `pcf-deploy`, `gcp-ops`, `akamai-edge`
- **Change gates** — `merge-gate`, `release-gate`, `production-change-gate`
- **Incident and operations** — `root-cause`, `incident-command`, `postmortem`, `runbook`,
  `operational-learning`, `service-onboarding`
- **Observability** — `obs-logs`, `obs-metrics`, `obs-traces`, `obs-dashboards`, `obs-alerting`,
  `obs-pipeline`
- **The fleet itself** — `agent-authoring`, `agent-security`

The roster's tool postures, enforcement model, and design disciplines are in
[AGENTS.md](AGENTS.md); the repository layout and its consequences are that file's **Map**.

## Validate

One structural gate (on Windows use `python` or `py -3`, never `python3` — the Microsoft Store
stub):

```sh
python scripts/gate_a.py                                # the whole structural gate
python scripts/generate_platform_adapters.py --write    # after any canonical edit
claude plugin validate . --strict                       # Claude platform contract
python scripts/fleet_doctor.py                          # repo + installed-host health, read-only
```

Gate A proves the fleet is well-formed, never that it is correct — the adversarial reviews in
[CONTRIBUTING.md](CONTRIBUTING.md) are separate. Contract validators (knowledge-update packets,
schema migrations) are documented in the
[schema compatibility policy](docs/schema-compatibility.md); behavioral and routing evals — status,
clean-room boundary, and the ROUTE-001 Codex campaign — live in [`evals/README.md`](evals/README.md);
the fleet-improvement ledger contract is
[`improvement-lifecycle.md`](skills/agent-authoring/references/improvement-lifecycle.md).

## Status

Pre-release `0.1.0`: canonical source, generated adapters, hook wiring, and manifests are
structurally gated and marketplace-validated. Release publication is prepared but blocked pending
its external controls; live and deferred work — including that release item — is tracked solely in
[`docs/fleet-roadmap.md`](docs/fleet-roadmap.md). Must-follow constraints are indexed in
[`docs/rules.md`](docs/rules.md).

## Contribute

Start with [AGENTS.md](AGENTS.md) (the fleet guide, loaded into every session) and
[CONTRIBUTING.md](CONTRIBUTING.md) (authoring, verification, and promotion policy).
