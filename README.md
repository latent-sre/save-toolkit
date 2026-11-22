# Save Toolkit

A Claude Code plugin that helps a human SRE do their job on this team's stack: PCF (through Apps
Manager), Splunk, PCF App Metrics, Grafana, and Akamai, with Cloud Run migration guidance. The GCP
landing runtime remains undecided in `stack-profile`.

It fits together in three layers:

- **You own the work:** the incident, the change, the runbook.
- **An advisor thinks with you:** `incident-investigation` asks what to check next, says what each
  result means, and tells you when to mitigate.
- **Agents are your helpers:** you or the invoking workflow dispatch them for bounded jobs, such as
  a read-only lookup, an alert tune, or a runbook.

A human executes every production action, with one narrow Grafana exception described under
[Limits](#limits).

> **Pre-release.** An install updates only when the plugin version changes; commits merged to
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

### VS Code and GitHub Copilot (beta)

Confirm `chat.plugins.enabled` is on, run **Chat: Install Plugin from Source**, and enter
`https://github.com/latent-sre/save-toolkit`. VS Code clones the repository and loads the skills
plus the generated Copilot agents and hooks in `com.github.copilot/`.

Alternatively, install through GitHub Copilot CLI v1.0.85 or later; VS Code discovers Copilot
CLI-installed plugins automatically:

```sh
copilot plugin marketplace add latent-sre/save-toolkit
copilot plugin install save-toolkit@latent-sre
```

Opening this repository without installing the plugin discovers `.github/agents/` and
`.github/skills/` directly.

## Set up

**Declare your stack.** The [`stack-profile` skill bundle](skills/stack-profile/) declares *this*
team's stack and pending migration decisions, and every platform-touching skill routes through it.
If that is not your stack, update it first or the fleet will confidently recommend someone else's
tools.

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
- *"check cf events and recent logs for orders since 14:00 UTC"* → the `sre-assistant` agent
  gathers the requested evidence, then returns to its caller.
- *"this alert is too noisy"* → `observability-engineer` with `obs-alerting`.
- *"write a runbook for the checkout deploy"* → the `scribe` agent with `operational-docs`.
- *"is PR #42 ready to merge?"* → `production-change-gate`'s merge-readiness checklist.

If automatic selection misses, start the advisor yourself with
`/save-toolkit:incident-investigation INC-4132`. One entry point is manual only, so type it:
`/save-toolkit:adr` (ADR scaffold).

## The fleet

The host supplies the model and executes tools; the plugin supplies the roles, methods, routing,
and authority boundaries. An agent owns a job with its own tools, and a skill adds a method without
changing who owns the work. An agent that delegates checks the helper's result itself, so you need
not relay reports between helpers.

| Agent | What it does | Tools |
|---|---|---|
| `sre-assistant` | Read-only lookup or investigation; returns findings and recommendations to its caller | Guarded Bash/PowerShell and the Grafana helper; browser tools that no hook guards |
| `observability-engineer` | Observability work and scoped Grafana changes | Unguarded Bash; writes config and Grafana dashboards, folders, alert rules, and silences |
| `scribe` | Runbooks, postmortems, and service and alert knowledge | Document writes; no shell, web, or delegation |
| `software-engineer` | Builds, fixes, refactors, and tests code and operations tooling | Read/write and unguarded Bash/PowerShell; no web tools |
| `principal-engineer` | System design before code; returns a design record or proposed ADR for a human to accept | Reads and design-document writes; no execution or external access |
| `repository-investigator` | Answers questions about the current checkout, citing `file:line` | Read, Grep, and Glob only |
| `reliability-engineer` | Reliability assessment, resilience design, and toil reduction | Reads and design-document writes; no execution or external access |
| `researcher` | Cited public research | Web and documentation tools only; no local files or shell |
| `reviewer` | For maintainers and builders: independent verification and correctness/security review; owns the verdict | Git/PR reads and scratch-copy checks; no web tools |

The skills live in [`skills/`](skills) and cover incident work, observability, the platform, change
gates, reliability, and engineering craft; each `SKILL.md` carries its own description and
triggers.

## Limits

- **A human executes production changes.** A handoff alone does not authorize a write. The one
  exception: an invoked `observability-engineer` may apply requested Grafana dashboard, folder,
  alert-rule, and temporary-silence changes under its
  [change-authority rule](agents/observability-engineer.md#change-authority).
- **The team's own inventories are not in this repository.** Query references use placeholders
  such as `<app_index>` and `<project>`, and service cards, alert cards, and runbooks are read from
  `operations/`, `runbooks/`, and `postmortems/` in the team's knowledge repository. Until those
  are supplied, the skills say so rather than guess.
- **Enforcement differs by host.** A field in an agent file shows what the plugin requested, not
  what every host enforces; see [`AGENTS.md`](AGENTS.md#enforcement-boundaries) and the
  [Copilot projection](docs/copilot-projection.md).

## Contribute

Start with [AGENTS.md](AGENTS.md) (the fleet-wide rules, loaded into every session) and
[CONTRIBUTING.md](CONTRIBUTING.md) (authoring, verification, and promotion policy). Live and
deferred work is tracked solely in [`docs/fleet-roadmap.md`](docs/fleet-roadmap.md).
