# Save Toolkit

A Claude Code plugin that helps a human SRE do their job on this team's stack: PCF (through Apps
Manager), Splunk, Wavefront and PCF App Metrics, Grafana, and Akamai, with Cloud Run migration
guidance. The GCP landing runtime is still undecided in `stack-profile`.

It fits together in three layers:

- **You own the work:** the incident, the change, the runbook.
- **An advisor thinks with you:** `incident-investigation` asks what to check next, says what each
  result means, and tells you when to mitigate.
- **Agents are your helpers**, dispatched by you or the invoking workflow for bounded jobs:
  `sre-assistant` performs a read-only lookup or investigation, `observability-engineer` tunes an
  alert, `scribe` writes the runbook afterward.

Skills serve you and the agents alike: the same logs skill hands you a paste-ready Splunk search
and hands `sre-assistant` the method to build one, which is why a PCF check always shows the Apps
Manager view with the `cf` command beside it. A human executes every production action, with one
narrow exception: an invoked `observability-engineer` may apply Grafana dashboards, alert rules,
and silences under its [change-authority rule](agents/observability-engineer.md#change-authority).

> **Pre-release (0.50.0).** Installs track `main` and may change without notice. The repository has
> no supported immutable release channel.

## Install (Claude Code)

```sh
claude plugin marketplace add latent-sre/save-toolkit
claude plugin install save-toolkit@latent-sre
```

**Before first use:** the [`stack-profile` skill](skills/stack-profile/) declares *this* team's
stack and pending migration decisions, and every platform-touching skill routes through it. If
that is not your stack, update its entrypoint and matching references first, or the fleet will
confidently recommend someone else's tools.

## Then just describe the problem

Routing is by description; there are no commands to memorize.

- *"walk me through INC-4132, checkout is 502-ing since 14:02 UTC"* → `incident-investigation`
  sits beside you: what to check next in Apps Manager, Splunk, or Wavefront, what each result would
  mean, when to mitigate, who to page, and a board so nothing learned is lost.
- *"why is orders 502-ing in prod?"* → `incident-investigation` again; you own it, it advises.
- *"check cf events and recent logs for orders since 14:00 UTC"* → `sre-assistant` gathers the
  requested evidence and its limits, then returns to its caller.
- *"investigate the checkout latency dashboard while I check the database"* → `sre-assistant`
  follows related leads within the assignment and returns findings and recommendations. Missing
  browser or API access stays explicit; a prompt cannot supply it.
- *"this alert is too noisy"* → `observability-engineer` with `obs-alerting`.
- *"write a runbook for the checkout deploy"* → `scribe` with the `runbook` skill.
- *"is PR #42 ready to merge?"* → `production-change-gate`'s merge-readiness checklist, including
  any known blocking findings. Independent exact-SHA review is reserved for production deployments.

If automatic selection misses the advisor, start with
`/save-toolkit:incident-investigation INC-4132` and describe the symptom. A direct request for
specific counts or logs stays a bounded helper job; asking the advisor to use a helper keeps the
incident question with the advisor and you.

Two entry points are manual only, so type them: `/save-toolkit:adr` (ADR scaffold) and
`/save-toolkit:pcf-deploy` (PCF/TAS deploy plan; model invocation is disabled, so nothing will
offer it).

## The fleet

| Agent | Lane | Routing |
|---|---|---|
| `sre-assistant` | Bounded read-only lookup or investigation, dispatched by a human or invoking workflow (guarded Bash/PowerShell on Claude) | Returns findings and recommendations; the caller keeps the broader investigation. Sanitized public fact checks go to `researcher` |
| `observability-engineer` | Observability, plus dispatched Grafana changes: dashboards, alert rules, and silences (unguarded Bash) | Docs to `scribe`, sanitized public lookups to `researcher`, automation to `software-engineer`. Active diagnosis stays with the responder and `incident-investigation` |
| `scribe` | Evidence-bound runbooks, resolved-incident postmortems, and approved service, application, and alert knowledge | Writes local documents only: no shell, web, external MCP, or delegation |
| `software-engineer` | Build, fix, refactor, and test code or operations tooling | Requested or risk-triggered review to `reviewer`, operational docs to `scribe`, sanitized public lookups to `researcher` |
| `repository-investigator` | Local-only answers about private, current, or uncommitted checkout behavior | Cites `file:line`; no shell, write, web, external MCP, skill, or delegation |
| `reliability-engineer` | Service reliability assessment, resilience design, and toil reduction | Local evidence and design documents; facts from `repository-investigator`, protected observations from `sre-assistant`, research from `researcher`. Implementation stays with its existing owner |
| `researcher` | Extended public research, or bounded external-source help for another agent | Cited evidence from official docs, upstream code, packages, and advisories. Quick lookups stay with a caller that already has the evidence or approved retrieval tools |
| `reviewer` *(maintainers and builders)* | Independent investigation, isolated verification, and correctness/security review | Gathers Git/PR evidence with focused evidence helpers and owns the verdict; its caller sends fixes to `software-engineer` |
| `agent-engineer` *(maintainers)* | The fleet's prompts, agents, skills, descriptions, and evals; prompt/eval loops; roster, delegation, and workflow-graph designs | Sanitized public lookups to `researcher`; the caller sends helper code to `software-engineer` and injection-surface review to `reviewer` |

The skills, by area (each `skills/<name>/SKILL.md` carries its own description and triggers):

- **Incident and operations** — `incident-investigation`, `root-cause`, `postmortem`, `runbook`,
  `operational-learning`, `service-lifecycle` (audit, onboard, and retire modes)
- **Observability** — `obs-logs`, `obs-metrics`, `obs-traces`, `obs-dashboards`, `obs-alerting`,
  `obs-pipeline`, `grafana` (Grafana UI/API operations and implementation)
- **Platform** — `stack-profile`, `pcf-ops`, `pcf-deploy`, `gcp-ops`, `akamai-edge`
- **Change gates** — `production-change-gate`
- **Reliability improvement** — `resilience-analysis`, `toil-reduction`; existing readiness
  coverage stays in `service-lifecycle`
- **Engineering craft** — `backend-craft`, `python-craft`, `frontend-craft`, `operator-cli`,
  `ci-actions`, `database-reliability`, `eng-ladder`
- **For maintainers: the fleet itself and the graphs it designs** — `agent-authoring`

Tool postures and the enforcement model are in [AGENTS.md](AGENTS.md), whose **Start here** table
maps each kind of change to its source.

## How it works

Save Toolkit is a host-loaded control layer, not a background orchestrator. The host supplies the
model and runs tools; the plugin supplies the specialist roles, reusable methods, routing, and
authority boundaries. Claude Code reads the canonical [`agents/`](agents) and [`skills/`](skills)
directly. One deterministic generator projects them for GitHub Copilot and VS Code; never edit its
output by hand.

```text
agents/ + skills/ (canonical)
  |-- Claude Code reads them directly
  `-- generator
        |-- com.github.copilot/ (agents, hooks) + skills/ -> installed VS Code/Copilot plugin
        `-- .github/agents/ + .github/skills/            -> Copilot working in this repository
```

- An **agent** owns a lane with a distinct prompt, tool posture, and return contract.
- A **skill** adds a method or checklist without changing the current owner.
- **Model delegation** uses the host's subagent tool to give a named child a bounded task. The
  caller checks the result against the assignment, combines the evidence, and continues within its
  authority, so you need not relay reports between helpers. Claude's
  `Agent(save-toolkit:target, ...)` grants become VS Code's `agent` tool plus the parent's
  `agents:` allowlist.
- A VS Code **handoff** (`handoffs:`) is a separate, human-selected change of owner. It keeps
  relevant conversation context but grants no approval or delegation authority.
- **Production-facing or materially irreversible effects remain human decisions.** The one
  exception is `observability-engineer`'s Grafana write set: dashboards and folders, individual
  Grafana-managed alert rules (create, update, pause, resume), and temporary silences (create,
  update, expire), under its complete
  [change-authority rule](agents/observability-engineer.md#change-authority). The
  [`grafana`](skills/grafana/SKILL.md) skill covers operational reads, alert and silence
  procedures, and dashboard implementation; `obs-dashboards` owns dashboard design. A handoff
  alone never authorizes a write.
- **The team's own inventories are not in this repository.** The log-index, metrics,
  PCF-foundation, and GCP-project references in `obs-logs`, `obs-metrics`, `pcf-ops`, and
  `gcp-ops` ship as placeholders. Service cards, alert cards, and runbooks are read from
  `operations/`, `runbooks/`, and `postmortems/` under the team's knowledge repository. Until those
  are filled in, "where are the dashboards, logs, and runbooks for this service" has no answer
  here by design; the skills say so rather than guess.

### Host guarantees and limits

A field in an agent file proves what the plugin requested, not what every host enforces. Treat
these as build-bound evidence and re-run the acceptance cases after host upgrades.

| Host | Contract shipped | Evidence |
|---|---|---|
| Claude Code | Canonical agents and skills load directly. Tool absence is the main role boundary, plus the plugin-level read-only Bash/PowerShell guard for `sre-assistant` | `Agent(target)` is enforced only on the main thread; restrictions at subagent depth are documentary. See [AGENTS.md](AGENTS.md#enforcement-boundaries) |
| VS Code / Copilot | Generated agents, skills, model-call `agents:`, and human-selected `handoffs:` | `[verified]` VS Code 1.137.0, 2026-09-10: the maintainer ran the [acceptance cases](docs/vscode-plugin-acceptance.md) against a local install of the 0.40.0 candidate and reported all passing, including the forbidden-child case that 1.135.0 had failed. Owner-reported with no transcript filed, so this row is the record. Not yet run on shipping bytes; the agent-scoped hook canary is unrun and `hooks/copilot-hooks.json` ships empty. Tracked as RELEASE-001 in the [roadmap](docs/fleet-roadmap.md) |

### Other hosts

For read-only observability without MCP, see
[Windows/macOS command access](skills/grafana/references/command-access.md). On Claude,
`sre-assistant` is limited to a small native command set and the bundled Grafana read/query helper.
Its browser interactions, native VS Code or Playwright, require a protected read-only session.
The standard Copilot profile has no terminal tools; its command preview must pass the
[installed-host canary](docs/vscode-plugin-acceptance.md#command-preview-canary) before adoption.

**VS Code / Copilot Chat (beta plugin):** confirm `chat.plugins.enabled` is on, run
**Chat: Install Plugin From Source**, and enter `https://github.com/latent-sre/save-toolkit`.
VS Code clones the repository; the root [`plugin.json`](plugin.json) declares Agent Plugins 1.0,
whose components are discovered from canonical `skills/` and the generated agents and hooks in
`com.github.copilot/`. No installed run has yet confirmed which layout VS Code loads (RELEASE-001).
Alternatively, install the same marketplace through GitHub Copilot CLI v1.0.85 or later (earlier
versions do not discover `com.github.copilot/agents/`); VS Code discovers plugins that Copilot CLI
installs:

```sh
copilot plugin marketplace add latent-sre/save-toolkit
copilot plugin install save-toolkit@latent-sre
```

For an unpublished local branch, use an isolated VS Code profile and register the branch worktree
with `chat.pluginLocations`:

```json
{
  "chat.pluginLocations": {
    "/absolute/path/to/save-toolkit": true
  }
}
```

Test the plugin from a neutral workspace: opening this repository also discovers `.github/agents/`
and `.github/skills/` as workspace customizations, which can hide duplicate-install mistakes. The
same discovery means working in this repository needs no plugin or extra setting. The
[VS Code plugin acceptance procedure](docs/vscode-plugin-acceptance.md) covers discovery, installed
helpers, delegation, return/resume, and disable/uninstall checks; its release section names the
immutable-artifact and rollback evidence still required for supported use.

**Codex:** the fleet is not distributed to Codex. Codex working *in* this repository picks up the
root [`AGENTS.md`](AGENTS.md) automatically, which is all it needs
([ADR](docs/decisions/2026-08-23-retire-codex-distribution-target.md)).

## Validate

On Windows use `python` or `py -3`, never `python3` (the Microsoft Store stub):

```sh
python scripts/gate_a.py                                          # the whole structural gate
python scripts/generate_platform_adapters.py --write              # after any canonical edit
python scripts/test_platform_adapters.py                          # Copilot projection + plugin contract
claude plugin validate .claude-plugin/marketplace.json --strict   # Claude marketplace, as CI runs it
claude plugin validate .claude-plugin/plugin.json                 # Claude plugin, as CI runs it
```

Gate A proves the fleet is well-formed, never that it is correct; the change-shaped checks in
[CONTRIBUTING.md](CONTRIBUTING.md)'s verification table are separate. Active behavioral and routing
evals live in [`evals/README.md`](evals/README.md). Accepted fleet failures become focused
regressions and ordinary PR evidence.

## Contribute

Start with [AGENTS.md](AGENTS.md) (the fleet guide, loaded into every session opened in this
repository) and [CONTRIBUTING.md](CONTRIBUTING.md) (authoring, verification, and promotion policy).
Live and deferred work is tracked only in [`docs/fleet-roadmap.md`](docs/fleet-roadmap.md).
