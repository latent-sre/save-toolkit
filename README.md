# Save Toolkit

A multi-host engineering plugin: **8 agents and 32 skills** for application engineering and site
reliability work — build/review/ship lanes, incident command, PCF and GCP triage, observability, and
evidence-bound documentation. Claude Code reads the canonical [`agents/`](agents) and
[`skills/`](skills) directly; GitHub Copilot/VS Code receives a committed projection from one
deterministic generator, never edited by hand.

> **Pre-release (0.1.0).** Installs track `main` and may change without notice. The repository has
> no supported immutable release channel.

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

**Codex:** the fleet is not distributed to Codex. Codex working *in* this repository picks up the
root [`AGENTS.md`](AGENTS.md) automatically, which is all it needs
([ADR](docs/decisions/2026-08-23-retire-codex-distribution-target.md)).

**Before first use:** the canonical [`stack-profile` skill bundle](skills/stack-profile/) declares
*this* team's stack (PCF, GCP Cloud Run, DX OpenExplore, Splunk, Akamai). Every platform-touching skill
routes through it — if that is not your stack, update its entrypoint and matching references first
or the fleet will confidently recommend someone else's tools.

**Then just describe the problem** — routing is by description, no commands to memorize:

- *"orders is 502-ing in prod since 14:20 UTC — investigate"* → the `sre` agent triages read-only
  and recommends a mitigation for a human to apply.
- *"is PR #42 ready to merge?"* → the `merge-gate` checklist, including disposition of any known
  blocking findings; independent exact-SHA review is reserved for production deployments.
- *"write a runbook for the checkout deploy"* → the `scribe` agent with the `runbook` skill.

The one manual command is `/save-toolkit:adr` (ADR scaffold).

## The fleet

| Agent | Lane | Routing |
|---|---|---|
| `software-engineer` | Build, fix, refactor, and test code or operations tooling | Routes requested or risk-triggered review to `reviewer`, operational docs to `scribe`, and sanitized public lookups to `researcher` |
| `reviewer` | Read-only correctness, quality, and security review | Reports findings; hands approved fixes to `software-engineer`; terminal |
| `repository-investigator` | Local-only answers about private, current, or uncommitted checkout behavior | Cites `file:line`; no shell, write, web, external MCP, skill, or delegation |
| `sre` | Investigate active production or staging failures (guarded read-only Bash) | Owns the incident through terminal recovery and delegates only sanitized public fact checks to `researcher`; the caller separately dispatches observability and documentation work after resolution |
| `observability-engineer` | Steady-state observability (unguarded Bash; applies Grafana dashboards directly) | Delegates docs to `scribe` and sanitized public lookups to `researcher`; the caller separately dispatches active incidents to `sre` and automation to `software-engineer` |
| `scribe` | Write evidence-bound runbooks, resolved-incident postmortems, and approved service/application/alert knowledge | Local document writer with no shell, web, external MCP, or delegation authority |
| `researcher` | External-only research against official docs, upstream code, packages, and advisories | No local file access; returns cited public evidence to caller |
| `agent-engineer` | The fleet's prompts, agents, skills, descriptions, evals, bounded prompt/eval loops, roster/delegation graphs, and portable executable workflow-graph designs | Delegates only sanitized public lookups to `researcher`; the caller separately dispatches helper code to `software-engineer` and injection-surface review to `reviewer` |

The 32 skills, by area (each `skills/<name>/SKILL.md` carries its own description and triggers):

- **Engineering craft** — `language-idiom`, `backend-craft`, `frontend-craft`, `ops-tooling`,
  `ci-actions`, `database-reliability`, `eng-ladder`
- **Platform** — `stack-profile`, `pcf-ops`, `pcf-deploy`, `gcp-ops`, `akamai-edge`
- **Change gates** — `merge-gate`, `release-gate`, `production-change-gate`
- **Incident and operations** — `root-cause`, `incident-command`, `postmortem`, `runbook`,
  `incident-drill` (explicit-only game day against the fleet itself),
  `operational-learning`, `service-readiness-audit`, `service-onboarding`
- **Observability** — `obs-logs`, `obs-metrics`, `obs-traces`, `obs-dashboards`, `obs-alerting`,
  `obs-pipeline`
- **The fleet itself and the graphs it designs** — `agent-authoring`, `agent-security`,
  `workflow-graph-engineering`

The roster's tool postures, enforcement model, and design disciplines are in
[AGENTS.md](AGENTS.md); the repository layout and its consequences are under **Start here**.

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
[CONTRIBUTING.md](CONTRIBUTING.md) are separate. Portable contracts are documented in the
[schema compatibility policy](docs/schema-compatibility.md); active behavioral and routing evals
live in [`evals/README.md`](evals/README.md). Accepted fleet failures become focused regressions and
ordinary PR evidence.

## Contribute

Start with [AGENTS.md](AGENTS.md) (the fleet guide, loaded into every session),
[CONTRIBUTING.md](CONTRIBUTING.md) (authoring, verification, and promotion policy), and
[`docs/rules.md`](docs/rules.md) (the must-follow index). Third-party attribution is in
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Live and deferred work is tracked solely
in [`docs/fleet-roadmap.md`](docs/fleet-roadmap.md).
