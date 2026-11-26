# Save Toolkit

Save Toolkit provides agents and skills for Claude Code and GitHub Copilot workspaces. Use
`incident-investigation` for guidance during an incident, or ask an agent to investigate
application impact, review a change, tune an alert, or write a runbook.

> **Pre-release.** A Claude Code installation updates only when the plugin version changes; commits merged to
> `main` under the same version leave it on its cached copy.

## Install

The fleet is not distributed to Codex, which picks up the root [`AGENTS.md`](AGENTS.md) when
working in this repository ([ADR](docs/decisions/2026-08-23-retire-codex-distribution-target.md)).

### Claude Code

Use Claude Code 2.1.295 or later. Starting with that version, the plugin can block a Bash or
PowerShell call if its guard hook fails to start, crashes, or times out.
[Claude Code hook failure handling](https://code.claude.com/docs/en/hooks#block-the-action-when-a-hook-fails)

```sh
claude plugin marketplace add latent-sre/save-toolkit
claude plugin install save-toolkit@latent-sre
```

To update an existing install, refresh the marketplace, update the plugin, and start a new
session. Check the installed version with `claude plugin list`.
[Claude Code plugin updates](https://code.claude.com/docs/en/plugins/host-marketplace#release-a-new-version)

```sh
claude plugin marketplace update latent-sre
claude plugin update save-toolkit@latent-sre
```

### VS Code and GitHub Copilot workspace

Open this repository in VS Code to use the workspace agents in `.github/agents/` and skills in
`.github/skills/`. They follow the checked-out revision. The installable Copilot plugin has been
retired. If you previously installed it, disable or uninstall that copy in the client where you
installed it so that Copilot discovers a single copy of each workspace agent.

## Set up

**Set your team's stack.** Update the profile if your platforms, telemetry, or ownership differ.
The supplied profile covers PCF, Splunk, PCF App Metrics, Grafana, and Akamai. Cloud Run is a
migration candidate. [Stack profile](skills/stack-profile/SKILL.md)

**Give the Grafana read helper its credentials.** The helper reads them from the environment or,
when none of its `GRAFANA_*` settings is set there, from `~/.config/save-toolkit/grafana.env`:

1. Create a Grafana service account with the **Viewer** role and add a token.
2. Write the file yourself, one `NAME=value` per line with no quotes or spaces around `=`:
   `GRAFANA_URL` (the HTTPS origin), `GRAFANA_ORG_ID`, and `GRAFANA_SA_TOKEN`.
3. On macOS and Linux, `chmod 600` it; the helper refuses a file other accounts can read.

Setting any of those variables in the environment, even to an empty value, makes the helper ignore
the file. For command-line access without MCP, see
[Windows/macOS command access](skills/grafana/references/command-access.md).

## Use it

Describe the problem. Routing is by description; there are no commands to memorize.

- *"walk me through INC-4132, checkout is 502-ing since 14:02 UTC"* → `incident-investigation`
  sits beside you: what to check next in Apps Manager, Splunk, Grafana, or PCF App Metrics, what
  each result would mean, when to mitigate, and who to page.
- *"check cf events and recent logs for orders since 14:00 UTC"* → in Claude Code with CF read
  access, `sre-assistant` can run those checks and report what they show about the app.
- *"this alert is too noisy"* → `observability-engineer` with `obs-analysis`.
- *"write a runbook for the checkout deploy"* → the `scribe` agent with `operational-docs`.
- *"is PR #42 ready to merge?"* → `production-change-gate`'s merge-readiness checklist.

In Claude Code, if automatic selection misses, start the advisor yourself with
`/save-toolkit:incident-investigation INC-4132`. One entry point is manual only, so type it:
`/save-toolkit:adr` (ADR scaffold).

## The fleet

The host executes tools. Each agent owns a job and checks any work it delegates.
The linked agent definitions list the tools requested in Claude Code. There, `sre-assistant`
can use guarded shell reads and `principal-engineer` can run guarded, read-only `git` and `gh`
commands. The standard Copilot workspace profiles for both omit terminal execution.
See [Copilot capabilities by agent](docs/copilot-projection.md#capability-choices).

| Agent | What it does |
|---|---|
| [`sre-assistant`](agents/sre-assistant.md) | Investigates application impact using read-only evidence from logs, metrics, dashboards, and platform state. |
| [`observability-engineer`](agents/observability-engineer.md) | Designs observability and applies requested Grafana changes within its authority. |
| [`scribe`](agents/scribe.md) | Writes runbooks, postmortems, and service and alert documentation. |
| [`software-engineer`](agents/software-engineer.md) | Builds, fixes, refactors, and tests code and operations tooling. |
| [`principal-engineer`](agents/principal-engineer.md) | Designs systems and drafts decision records for a human owner to accept. |
| [`repository-investigator`](agents/repository-investigator.md) | Answers questions about the current checkout and cites the relevant files and lines. |
| [`reliability-engineer`](agents/reliability-engineer.md) | Assesses reliability risks, designs for resilience, and identifies ways to reduce toil. |
| [`researcher`](agents/researcher.md) | Answers questions from public sources and cites the evidence. |
| [`reviewer`](agents/reviewer.md) | Independently verifies changes and reports a verdict on correctness and security. |

The skills live in [`skills/`](skills) and cover incident work, observability, the platform, change
gates, reliability, and engineering craft; each `SKILL.md` carries its own description and
triggers.

## Limits

- **Production changes** are executed by a human or protected automation. An invoked
  `observability-engineer` may apply requested Grafana dashboard, folder, alert-rule, and
  temporary-silence changes under its
  [change-authority rule](agents/observability-engineer.md#change-authority).
- **The team's own inventories are not in this repository.** Query references use placeholders
  such as `<app_index>` and `<project>`, and service cards, alert cards, and runbooks are read from
  `operations/`, `runbooks/`, and `postmortems/` in the team's knowledge repository. Until those
  are supplied, the skills say so rather than guess.
- **Enforcement differs by host.** A field in an agent file shows what the plugin requested, not
  what every host enforces; see [`AGENTS.md`](AGENTS.md#enforcement-boundaries) and the
  [Copilot projection](docs/copilot-projection.md).

## Contribute

See the [fleet rules](AGENTS.md), [contributor guide](CONTRIBUTING.md), and
[fleet roadmap](docs/fleet-roadmap.md).
