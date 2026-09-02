# Save Toolkit

A Claude Code plugin that helps a human SRE do their job on this team's stack: PCF (through Apps
Manager), Cloud Run, Splunk, Wavefront and PCF App Metrics, Grafana, Akamai. It gives you an
advisor to think with during an incident, read-only helpers that gather evidence, and skills that
carry the team's own facts, queries, and checklists. A human executes every production action,
with one narrow exception: an invoked `observability-engineer` may apply Grafana dashboard and
folder writes under its [change-authority rule](agents/observability-engineer.md#change-authority).

> **Pre-release (0.1.0).** Installs track `main` and may change without notice. The repository has
> no supported immutable release channel.

## Install (Claude Code)

```sh
claude plugin marketplace add latent-sre/save-toolkit
claude plugin install save-toolkit@latent-sre
```

## Then just describe the problem

Routing is by description; there are no commands to memorize.

- *"walk me through INC-4132, checkout is 502-ing since 14:02 UTC"* → `incident-investigation`
  sits beside you: what to check next in Apps Manager, Splunk, or Wavefront, what each result would
  mean, when to mitigate, who to page, and a board so nothing learned is lost.
- *"why is orders 502-ing in prod? what changed?"* → the `sre` agent gathers one read-only evidence
  slice and recommends a mitigation for a human to apply.
- *"this alert is too noisy"* → `observability-engineer` with `obs-alerting`.
- *"write a runbook for the checkout deploy"* → the `scribe` agent with the `runbook` skill.
- *"is PR #42 ready to merge?"* → `production-change-gate`'s merge-readiness checklist, including
  disposition of any known blocking findings; independent exact-SHA review is reserved for
  production deployments.

**Before first use:** the canonical [`stack-profile` skill bundle](skills/stack-profile/) declares
*this* team's stack (PCF, GCP Cloud Run, DX OpenExplore, Splunk, Akamai). Every platform-touching skill
routes through it — if that is not your stack, update its entrypoint and matching references first
or the fleet will confidently recommend someone else's tools.

The one manual command is `/save-toolkit:adr` (ADR scaffold).

## The fleet

| Agent | Lane | Routing |
|---|---|---|
| `sre` | Investigate active production or staging failures (guarded read-only Bash) | Owns the incident through terminal recovery and delegates only sanitized public fact checks to `researcher`; the caller separately dispatches observability and documentation work after resolution |
| `observability-engineer` | Steady-state observability (unguarded Bash; applies Grafana dashboards directly) | Delegates docs to `scribe` and sanitized public lookups to `researcher`; the caller separately dispatches active incidents to `sre` and automation to `software-engineer` |
| `scribe` | Write evidence-bound runbooks, resolved-incident postmortems, and approved service/application/alert knowledge | Local document writer with no shell, web, external MCP, or delegation authority |
| `software-engineer` | Build, fix, refactor, and test code or operations tooling | Routes requested or risk-triggered review to `reviewer`, operational docs to `scribe`, and sanitized public lookups to `researcher` |
| `repository-investigator` | Local-only answers about private, current, or uncommitted checkout behavior | Cites `file:line`; no shell, write, web, external MCP, skill, or delegation |
| `researcher` | External-only research against official docs, upstream code, packages, and advisories | No local file access; returns cited public evidence to caller |
| `reviewer` *(for maintainers and builders)* | Read-only correctness, quality, and security review | Reports findings; hands approved fixes to `software-engineer`; terminal |
| `agent-engineer` *(for maintainers)* | The fleet's prompts, agents, skills, descriptions, evals, bounded prompt/eval loops, roster/delegation graphs, and portable executable workflow-graph designs | Delegates only sanitized public lookups to `researcher`; the caller separately dispatches helper code to `software-engineer` and injection-surface review to `reviewer` |

The 30 skills, by area (each `skills/<name>/SKILL.md` carries its own description and triggers):

- **Incident and operations** — `incident-investigation`, `investigation-depth`, `root-cause`, `incident-command`, `postmortem`, `runbook`,
  `operational-learning`, `service-lifecycle` (audit, onboard, and retire modes)
- **Observability** — `obs-logs`, `obs-metrics`, `obs-traces`, `obs-dashboards`, `obs-alerting`,
  `obs-pipeline`
- **Platform** — `stack-profile`, `pcf-ops`, `pcf-deploy`, `gcp-ops`, `akamai-edge`
- **Change gates** — `production-change-gate`
- **Engineering craft** — `language-idiom`, `backend-craft`, `frontend-craft`, `ops-tooling`,
  `ci-actions`, `database-reliability`, `eng-ladder`
- **For maintainers: the fleet itself and the graphs it designs** — `agent-authoring`,
  `workflow-graph-engineering`

The roster's tool postures, enforcement model, and design disciplines are in
[AGENTS.md](AGENTS.md); the repository layout and its consequences are under **Start here**.

## How it works

Save Toolkit is a host-loaded control layer, not a background orchestrator. The host supplies the
model and executes tools; the plugin supplies the specialist roles, reusable methods, routing, and
authority boundaries. Claude Code reads the canonical [`agents/`](agents) and [`skills/`](skills)
directly; GitHub Copilot/VS Code receives a committed projection from one deterministic generator,
never edited by hand.

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
- Production-facing or materially irreversible effects remain human decisions. The one narrow
  exception is an invoked [`observability-engineer`](agents/observability-engineer.md#change-authority)
  applying only Grafana dashboard or folder writes under its complete change-authority rule; a
  handoff alone does not activate that exception.

### Host guarantees and limits

A field present in an agent file proves what the plugin requested, not what every host enforces.
Treat these as build-bound evidence, and rerun the linked probe after host upgrades.

| Host surface | Contract shipped | Current evidence boundary |
|---|---|---|
| Claude Code | Canonical agents and skills load directly; tool absence is the primary role boundary, with the plugin-level read-only Bash guard for `sre` | Claude has the richest enforceable contract, but `Agent(target)` is enforced only on the main thread; subagent-depth restrictions remain documentary. See [`AGENTS.md`](AGENTS.md#enforcement-boundaries) |
| VS Code 1.135.0 (`08d4889f`) | Generated agents, skills, model-call `agents:`, and human-selected `handoffs:` | `[verified]` On 2026-08-30, plugin registration, 8 agents, 33 skills, the separate ADR prompt, and a synthetic allowed child passed. A forbidden child still ran, the real `software-engineer` -> `reviewer` call was inconclusive, and the separate hook canary was not run. See the [live transcript](docs/reviews/evidence/host-002/2026-08-30-vscode-plugin-delegation-transcript.md) |
| First installed VS Code build proven to contain `d679b159` | Upstream adds prepare/invoke rejection outside `agents:` and forwards each child's own list | `[sourced]` The [upstream change](https://github.com/microsoft/vscode/commit/d679b159e16d15d24e364b627ab85e144899ead0) is merged; `[unverified]` the installed plugin path until the [HOST-002 probe](docs/probes/host-002-vscode-agent-delegation.md) passes on that exact build |

### Other hosts

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

## Validate

One structural gate (on Windows use `python` or `py -3`, never `python3` — the Microsoft Store
stub):

```sh
python scripts/gate_a.py                                # the whole structural gate
python scripts/check_context_cost.py                    # canonical-task and description byte budgets
python scripts/generate_platform_adapters.py --write    # after any canonical edit
python scripts/test_platform_adapters.py                 # Copilot projection + plugin contract
claude plugin validate . --strict                       # Claude platform contract
```

Gate A proves the fleet is well-formed, never that it is correct — the adversarial reviews in
[CONTRIBUTING.md](CONTRIBUTING.md) are separate. Portable contracts are documented in the
[schema compatibility policy](docs/schema-compatibility.md); active behavioral and routing evals
live in [`evals/README.md`](evals/README.md). Accepted fleet failures become focused regressions and
ordinary PR evidence.

## Contribute

Start with [AGENTS.md](AGENTS.md) (the fleet guide and conditional rule map, loaded into every
session) and [CONTRIBUTING.md](CONTRIBUTING.md) (authoring, verification, and promotion policy).
Live and deferred work is tracked solely in [`docs/fleet-roadmap.md`](docs/fleet-roadmap.md).
