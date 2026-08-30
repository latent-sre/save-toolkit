# Save Toolkit

A multi-host engineering plugin: **8 agents and 33 skills** for application engineering and site
reliability work — build/review/ship lanes, incident command, PCF and GCP triage, observability, and
evidence-bound documentation. Claude Code reads the canonical [`agents/`](agents) and
[`skills/`](skills) directly; GitHub Copilot/VS Code receives a committed projection from one
deterministic generator, never edited by hand.

> **Pre-release (0.1.0).** Installs track `main` and may change without notice. The repository has
> no supported immutable release channel.

## How it works

Save Toolkit is a host-loaded control layer, not a background orchestrator. The host supplies the
model and executes tools; the plugin supplies the specialist roles, reusable methods, routing, and
authority boundaries.

```text
agents/ + skills/ (canonical)
  |-- Claude Code reads them directly
  `-- generator -> .github/agents/ + platforms/copilot/skills/ -> VS Code/Copilot
```

- An **agent** owns a lane with a distinct prompt, tool posture, and return contract.
- A **skill** adds a method or checklist without changing the current owner.
- **Model delegation** uses the host's subagent tool to give a bounded task to a named child, which
  returns its result to the caller. Canonical Claude `Agent(target, ...)` grants become VS Code's
  `agent` tool plus the parent's `agents:` allowlist.
- A VS Code **handoff** is a separate human-selected ownership transition from `handoffs:`. It keeps
  relevant conversation context but does not grant approval or model-delegation authority.
- Production-facing or materially irreversible effects remain human decisions even when an agent
  prepares the exact action, verification, and rollback.

### Host guarantees and limits

A field present in an agent file proves what the plugin requested, not what every host enforces.
Treat these as build-bound evidence, and rerun the linked probe after host upgrades.

| Host surface | Contract shipped | Current evidence boundary |
|---|---|---|
| Claude Code | Canonical agents and skills load directly; tool absence is the primary role boundary, with the plugin-level read-only Bash guard for `sre` | Claude has the richest enforceable contract, but `Agent(target)` is enforced only on the main thread; subagent-depth restrictions remain documentary. See [`AGENTS.md`](AGENTS.md#enforcement-boundaries) |
| VS Code 1.135.0 (`08d4889f`) | Generated agents, skills, model-call `agents:`, and human-selected `handoffs:` | `[verified]` On 2026-08-30, plugin registration, 8 agents, 33 skills, the separate ADR prompt, and a synthetic allowed child passed. A forbidden child still ran, the real `software-engineer` -> `reviewer` call was inconclusive, and no fleet Copilot hook is wired. See the [HOST-002 evidence](docs/reviews/2026-08-30-vscode-subagent-handoff-enforcement.md) |
| First installed VS Code build proven to contain `d679b159` | Upstream adds prepare/invoke rejection outside `agents:` and forwards each child's own list | `[sourced]` The [upstream change](https://github.com/microsoft/vscode/commit/d679b159e16d15d24e364b627ab85e144899ead0) is merged; `[unverified]` the installed plugin path until the [HOST-002 probe](docs/probes/host-002-vscode-agent-delegation.md) passes on that exact build |

## Quickstart

**Claude Code** (pre-release install from `main`):

```sh
claude plugin marketplace add latent-sre/save-toolkit
claude plugin install save-toolkit@latent-sre
```

**VS Code / Copilot Chat (beta plugin):** confirm `chat.plugins.enabled` is on, run
**Chat: Install Plugin From Source**, and enter `https://github.com/latent-sre/save-toolkit`.
VS Code clones the repository and loads the generated agents and skills selected by the root
[`plugin.json`](plugin.json). Alternatively, install the same marketplace through GitHub Copilot
CLI; VS Code automatically discovers Copilot CLI-installed plugins:

```sh
copilot plugin marketplace add latent-sre/save-toolkit
copilot plugin install save-toolkit@latent-sre
```

For an unpublished local branch, use an isolated VS Code profile and register the branch worktree
with `chat.pluginLocations` instead:

```json
{
  "chat.pluginLocations": {
    "/absolute/path/to/save-toolkit": true
  }
}
```

Open a neutral test workspace for that plugin check; opening this repository itself also discovers
`.github/agents/` as workspace agents and can hide duplicate-install mistakes. Opening the repository
without installing the plugin remains a checkout-only development path:
[`.vscode/settings.json`](.vscode/settings.json) registers the generated skill projection.
The exact beta discovery and agent-to-agent procedure is the
[`HOST-002 VS Code plugin probe`](docs/probes/host-002-vscode-agent-delegation.md).

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

The 33 skills, by area (each `skills/<name>/SKILL.md` carries its own description and triggers):

- **Engineering craft** — `language-idiom`, `backend-craft`, `frontend-craft`, `ops-tooling`,
  `ci-actions`, `database-reliability`, `eng-ladder`
- **Platform** — `stack-profile`, `pcf-ops`, `pcf-deploy`, `gcp-ops`, `akamai-edge`
- **Change gates** — `merge-gate`, `release-gate`, `production-change-gate`
- **Incident and operations** — `incident-investigation`, `root-cause`, `incident-command`, `postmortem`, `runbook`,
  `incident-drill` (explicit-only game day against the fleet itself),
  `operational-learning`, `service-readiness-audit`, `service-lifecycle`
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
python scripts/test_platform_adapters.py                 # Copilot projection + plugin contract
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
[`docs/rules.md`](docs/rules.md) (the must-follow index). Live and deferred work is tracked
solely in [`docs/fleet-roadmap.md`](docs/fleet-roadmap.md).
