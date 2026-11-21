# Save Toolkit

A Claude Code plugin that helps a human SRE do their job on this team's stack: PCF (through Apps
Manager), Splunk, PCF App Metrics, Grafana, and Akamai, with Cloud Run migration guidance. The GCP
landing runtime remains undecided in `stack-profile`.

It fits together in three layers:

- **You own the work:** the incident, the change, the runbook.
- **An advisor thinks with you:** `incident-investigation` asks what to check next, says what each
  result means, and tells you when to mitigate.
- **Agents are your helpers:** you or the invoking workflow dispatch them for bounded jobs.
  `sre-assistant` performs a read-only lookup or investigation, `observability-engineer` tunes an
  alert, and `scribe` writes the runbook afterward.

The skills serve you and the agents alike: the same logs skill hands you a paste-ready Splunk
search and hands `sre-assistant` the method to build one, which is why a PCF check is always the
Apps Manager view with the `cf` command beside it. A human executes every production action, with
one narrow Grafana exception described under [Limits](#limits).

> **Pre-release.** New Claude Code installs resolve the plugin from the fetched GitHub
> marketplace. Existing installs receive updates when the plugin manifest version changes.
> Commits merged to `main` under the same version leave those installs on their cached copy.

## Install

### Claude Code

Use Claude Code 2.1.295 or later. Starting with that version, the plugin can block a Bash or
PowerShell call if its guard hook fails to start, crashes, or times out.
[Claude Code hook failure handling](https://code.claude.com/docs/en/hooks#block-the-action-when-a-hook-fails)

```sh
claude plugin marketplace add latent-sre/save-toolkit
claude plugin install save-toolkit@latent-sre
```

To update an existing install, refresh the marketplace and then update the plugin.

```sh
claude plugin marketplace update latent-sre
claude plugin update save-toolkit@latent-sre
```

Start a new session to load the update. Check the installed version with `claude plugin list`.
[Claude Code plugin updates](https://code.claude.com/docs/en/plugins/host-marketplace#release-a-new-version)

### VS Code and GitHub Copilot (beta)

Confirm `chat.plugins.enabled` is on, run **Chat: Install Plugin From Source**, and enter
`https://github.com/latent-sre/save-toolkit`. VS Code clones the repository and loads it as an
Agent Plugins 1.0 plugin, which the root [`plugin.json`](plugin.json) declares: canonical `skills/`
plus the generated Copilot agents and hooks in `com.github.copilot/`.

Alternatively, install the same marketplace through GitHub Copilot CLI v1.0.85 or later (earlier
versions do not discover `com.github.copilot/agents/`); VS Code automatically discovers Copilot
CLI-installed plugins:

```sh
copilot plugin marketplace add latent-sre/save-toolkit
copilot plugin install save-toolkit@latent-sre
```

Opening this repository without installing the plugin discovers `.github/agents/` and
`.github/skills/` directly; no custom skill-location setting is needed.

### Codex

The fleet is not distributed to Codex. Codex working *in* this repository picks up the root
[`AGENTS.md`](AGENTS.md) automatically, which is all it needs
([ADR](docs/decisions/2026-08-23-retire-codex-distribution-target.md)).

## Set up

**Declare your stack.** The canonical [`stack-profile` skill bundle](skills/stack-profile/)
declares *this* team's stack and pending migration decisions. Every platform-touching skill routes
through it — if that is not your stack, update its entrypoint and matching references first or the
fleet will confidently recommend someone else's tools.

**Give the Grafana read helper its credentials.** The bundled helper takes them from the
environment or, when the environment sets no `GRAFANA_*` variable, from
`~/.config/save-toolkit/grafana.env`:

1. Create a Grafana service account with the **Viewer** role and add a token.
2. Write the file yourself, one `NAME=value` per line with no quotes or spaces around `=`:
   `GRAFANA_URL` (the HTTPS origin), `GRAFANA_ORG_ID`, and `GRAFANA_SA_TOKEN`.
3. On macOS and Linux, `chmod 600` it; the helper refuses a file other accounts can read.

Setting any `GRAFANA_*` variable, even an empty one, makes the helper ignore the file. For
read-only observability without MCP, see
[Windows/macOS command access](skills/grafana/references/command-access.md).

## Use it

Describe the problem. Routing is by description; there are no commands to memorize.

- *"walk me through INC-4132, checkout is 502-ing since 14:02 UTC"* → `incident-investigation`
  sits beside you: what to check next in Apps Manager, Splunk, Grafana, or PCF App Metrics, what
  each result would mean, when to mitigate, who to page, and a board so nothing learned is lost.
- *"why is orders 502-ing in prod?"* → `incident-investigation` again; you own it, it advises.
- *"check cf events and recent logs for orders since 14:00 UTC"* → the `sre-assistant` agent gathers
  the requested evidence and limits, then returns to its caller.
- *"investigate the checkout latency dashboard while I check the database"* → `sre-assistant`
  interprets available evidence, follows related leads within the assignment, and returns findings
  and recommendations. Missing browser/API access stays explicit; a prompt cannot supply it.
- *"this alert is too noisy"* → `observability-engineer` with `obs-alerting`.
- *"write a runbook for the checkout deploy"* → the `scribe` agent with `operational-docs` in
  runbook mode.
- *"is PR #42 ready to merge?"* → `production-change-gate`'s merge-readiness checklist, including
  disposition of any known blocking findings; independent exact-SHA review is reserved for
  production deployments.

To select the advisor explicitly, start with `/save-toolkit:incident-investigation INC-4132` and
describe the symptom. This is a fallback when automatic selection misses, not a requirement for
ordinary use. A direct request for specific counts or logs stays a bounded helper job; asking the
advisor to use a helper keeps the original incident question with the advisor and you.

Two entry points are manual only, so type them: `/save-toolkit:adr` (ADR scaffold) and
`/save-toolkit:pcf-deploy` (PCF/TAS deploy plan — model invocation is disabled, so nothing
will offer it).

## The fleet

Save Toolkit is a host-loaded control layer, not a background orchestrator. The host supplies the
model and executes tools; the plugin supplies the specialist roles, reusable methods, routing, and
authority boundaries.

- An **agent** owns a lane with a distinct prompt, tool posture, and return contract.
- A **skill** adds a method or checklist without changing the current owner.
- **Delegation** gives a bounded task to a named helper, which returns its result to the caller.
  The calling agent checks that result against the assignment and continues the original task
  within its authority; you need not relay reports between helpers.

The last column is the Claude delegation graph, validated against each agent's frontmatter by
Gate A.

| Agent | What it does | Tools | Delegates to |
|---|---|---|---|
| `sre-assistant` | Bounded read-only lookup or investigation, dispatched by a human or invoking workflow; returns findings and recommendations while the caller keeps the broader investigation | Allowlist-guarded Bash/PowerShell and bundled Grafana helper; interactive browser tools that no hook guards | `researcher` |
| `observability-engineer` | Observability and dispatched Grafana changes; active diagnosis stays with the responder, and automation goes to `software-engineer` | Unguarded Bash; writes config and scoped Grafana dashboards, folders, alert rules, and silences | `scribe`, `researcher` |
| `scribe` | Writes evidence-bound runbooks, resolved-incident postmortems, and approved service, application, and alert knowledge | Local document write; no Bash, web, external MCP, or delegation | — |
| `software-engineer` | Builds, fixes, refactors, modernizes, and tests code or operations tooling | Local read/write and unguarded Bash/PowerShell for team-authored code; no web tools | `reviewer`, `scribe`, `researcher` |
| `principal-engineer` | System design and architecture before code: contract changes, migrations, new-service architecture, and tool or platform selection; returns a design record or proposed ADR for the human owner to accept | Local reads plus design-document and proposed-ADR writes; no execution or direct external access | `repository-investigator`, `sre-assistant`, `researcher` |
| `repository-investigator` | Local-only answers about private, current, or uncommitted checkout behavior, citing `file:line` | Read/Grep/Glob only | — |
| `reliability-engineer` | Service reliability assessment, resilience design, and toil reduction; implementation stays with its existing owner | Local reads plus design-document writes; no execution or direct external access | `repository-investigator`, `sre-assistant`, `researcher` |
| `researcher` | Cited public research from official docs, upstream code, packages, and advisories | External-only; no local read, Bash, Write, Skill, or Agent | — |
| `reviewer` *(for maintainers and builders)* | Independent investigation, isolated verification, and correctness/security review; owns the verdict while its caller dispatches fixes to `software-engineer` | Git/PR reads, scratch writes and checks, trusted skills; no direct web tools | `repository-investigator` |

The skills, by area (each `skills/<name>/SKILL.md` carries its own description and triggers):

- **Incident and operations** — `incident-investigation`, `root-cause`, `operational-docs`
  (runbooks, postmortems, knowledge closeout, and ownership lookups)
- **Observability** — `obs-analysis` (logs, metrics, and traces), `obs-alerting`,
  `obs-pipeline`, `grafana` (dashboard design and Grafana UI/API operations)
- **Platform** — `stack-profile`, `pcf-ops`, `pcf-deploy`, `gcp-ops`, `akamai-edge`
- **Change gates** — `production-change-gate`
- **Reliability improvement** — `resilience-analysis` (including existing service readiness),
  `toil-reduction`
- **Engineering craft** — `api-craft`, `python-craft`, `go-craft`, `frontend-craft`, `operator-cli`,
  `cicd-github`, `database-reliability`
- **For maintainers: the fleet itself and the graphs it designs** — `agent-authoring`

## Limits

- **A human executes production changes.** Production-facing or materially irreversible effects
  remain human decisions, and a handoff alone does not authorize a write. The one exception: an
  invoked [`observability-engineer`](agents/observability-engineer.md#change-authority) may apply
  requested Grafana dashboard and folder changes, individual Grafana-managed alert-rule
  create/update or pause/resume, and temporary silence create/update/expire under its complete
  change-authority rule.
- **The team's own inventories are not in this repository.** The query references under
  `skills/obs-analysis` use `<app>`/`<index>` placeholders, the PCF and GCP skills take the
  foundation or project from the caller, and service cards, alert cards, and runbooks are read
  from `operations/`, `runbooks/`, and `postmortems/` under the team's knowledge repository root.
  Until those are supplied, "where are the dashboards, logs, and runbooks for this service" has no
  answer here by design; the skills say so rather than guess.
- **Enforcement differs by host.** A field present in an agent file proves what the plugin
  requested, not what every host enforces. Claude Code loads the canonical agents and skills
  directly: tool absence is the primary role boundary, a read-only guard covers `sre-assistant`,
  and `Agent(target)` grants are enforced only on the main thread. VS Code and Copilot load
  generated copies, which do not restrict which agent may call which. See
  [`AGENTS.md`](AGENTS.md#enforcement-boundaries) and the
  [Copilot projection](docs/copilot-projection.md).

## Contribute

Start with [AGENTS.md](AGENTS.md) (the fleet guide and fleet-wide rules, loaded into every
session) and [CONTRIBUTING.md](CONTRIBUTING.md) (authoring, verification, and promotion policy).
Live and deferred work is tracked solely in [`docs/fleet-roadmap.md`](docs/fleet-roadmap.md).
