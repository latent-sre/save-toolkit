# SRE Agents

SRE Agents is a multi-host plugin containing **7 agents and 26 skills** for application engineering
and site reliability work. Claude Code reads the canonical [`agents/`](agents) and [`skills/`](skills)
sources directly. GitHub Copilot/VS Code and Codex receive committed, host-native projections made by
one deterministic generator; generated files are never edited by hand.

## Layout

- [`agents/`](agents) — the seven canonical Claude plugin agent definitions; `tools` carries authority.
- [`skills/`](skills) — the 26 canonical skills and their progressive-disclosure `references/`,
  `assets/`, and `scripts/` bundles.
- [`commands/adr.md`](commands/adr.md) — the canonical Claude `/sre-agents:adr` scaffold.
- [`.claude-plugin/`](.claude-plugin) and [`hooks/`](hooks) — Claude manifest/marketplace plus the
  session-scoped guarded-Bash hook.
- [`plugin.json`](plugin.json), [`.github/agents/`](.github/agents), and
  [`platforms/copilot/skills/`](platforms/copilot/skills) — Copilot/VS Code plugin and projections.
- [`plugins/sre-agents/`](plugins/sre-agents) and [`.codex/agents/`](.codex/agents) — Codex skills
  plugin plus standalone custom-agent projections.
- [`scripts/`](scripts) — the structural gate (`gate_a.py`), the read-only allowlist guard
  (`readonly-guard.py`), generator, optional Codex agent installer, typed evidence validator,
  read-only fleet doctor, and mutation tests.
- [`schemas/evidence-envelope-v1.schema.json`](schemas/evidence-envelope-v1.schema.json) — the
  portable runtime-evidence contract; the executable secret-field checks live in
  [`scripts/evidence_envelope.py`](scripts/evidence_envelope.py).

Routing is native. Claude plugin components are namespaced as `sre-agents:<name>`; generated hosts
use their native bare component names. The roster and enforcement model are in [AGENTS.md](AGENTS.md).

## Fleet inventory

<!-- fleet-inventory:start -->
### Agents (7)

| Agent | Lane | Routing |
|---|---|---|
| `sde` | Build, fix, refactor, and test code or operations tooling | Delegates review to `reviewer` and sanitized public lookups to `researcher` |
| `reviewer` | Read-only correctness, quality, and security review | Reports findings; hands approved fixes to `sde`; terminal |
| `repository-investigator` | Local-only answers about private, current, or uncommitted checkout behavior | Cites `file:line`; no shell, write, web, external MCP, skill, or delegation |
| `sre` | Investigate active production or staging failures (guarded read-only Bash) | Delegates steady-state work to `sre-steward`, fact checks to `researcher` |
| `sre-steward` | Steady state: observability as code + runbooks/postmortems (guarded Bash) | Hands active incidents to `sre`, automation to `sde`, lookups to `researcher` |
| `researcher` | External-only research against official docs, upstream code, packages, and advisories | No local file access; returns cited public evidence to caller |
| `prompt-engineer` | The fleet's own files: agents, skills, descriptions, evals | Hands helper code to `sde`, injection review to `reviewer` |

### Skills (26)

| Skill | Purpose |
|---|---|
| `stack-profile` | Runtime, platform, and ownership boundaries |
| `root-cause` | Evidence-led debugging and causal analysis |
| `runbook` | Operational runbook method and template |
| `eng-ladder` | Engineering and incident-response altitude |
| `craft` | Language craft, testing, and safe refactoring |
| `backend-craft` | Backend API, persistence, auth, and background-work patterns |
| `frontend-craft` | Frontend architecture, data views, forms, and auth patterns |
| `ops-tooling` | Operations CLI and tool design |
| `pcf-ops` | Application-side PCF/TAS investigation |
| `pcf-deploy` | PCF deployment procedure |
| `database-reliability` | Database reliability investigation and design |
| `ci-actions` | GitHub Actions CI design and migration |
| `merge-gate` | Pre-merge quality checkpoint |
| `release-gate` | Release-readiness checkpoint |
| `production-change-gate` | Human authorization for production change |
| `incident-command` | Incident severity, roles, communications, and timeline |
| `postmortem` | Blameless post-incident learning |
| `service-onboarding` | Ordered service onboarding and audit |
| `agent-authoring` | Agent, skill, tool, prompt, and roster authoring |
| `agent-security` | Agentic threat modeling and boundary review |
| `obs-logs` | Log investigation and query design |
| `obs-metrics` | Metrics, SLIs, and query design |
| `obs-traces` | Distributed tracing and trace-query design |
| `obs-dashboards` | Dashboard design and provisioning |
| `obs-alerting` | Alerting, error budgets, and correlation |
| `obs-pipeline` | Telemetry collection and routing pipelines |
<!-- fleet-inventory:end -->

## Validate and evaluate

Run the single structural entrypoint (on Windows use `python` or `py -3`, never `python3` — the
Microsoft Store stub):

```powershell
py -3 scripts/gate_a.py
```

Regenerate projections only after editing canonical sources:

```powershell
py -3 scripts/generate_platform_adapters.py --write
py -3 scripts/generate_platform_adapters.py
claude plugin validate . --strict
```

Codex currently discovers plugin skills separately from standalone custom agents. To install the
generated agents into an explicit project/user scope without overwriting user-owned files:

```powershell
py -3 scripts/install_codex_agents.py --target C:\path\to\project\.codex\agents
# or, intentionally: py -3 scripts/install_codex_agents.py --user
```

Inspect repository and installed-host health without generating, installing, fetching, or starting a
model session:

```powershell
py -3 scripts/fleet_doctor.py
py -3 scripts/fleet_doctor.py --json
```

Each doctor check is a versioned evidence envelope with `pass`, `fail`, `skip`, or `inconclusive`
status. Missing CLIs and unexecuted runtime behavior never count as passing evidence.

For repository-controlled executable checks, use the digest-bound, networkless container boundary in
[`docs/verification-sandbox.md`](docs/verification-sandbox.md). It requires a reviewed link-free
snapshot, full revision, preapproved tree digest, and a locally present digest-pinned image; it does
not add an autonomous verification agent or live-effect authority.

Gate A owns its step list; do not copy that list into documentation. Behavioral evaluations under
[`evals/`](evals) are intentionally manual and never run in CI. They execute only after source-trust and
disposable-harness requirements are satisfied.

Codex/Sol plugin conformance is a separate lane from the Claude runner:

```powershell
py -3 evals/run_codex_conformance.py --validate
py -3 evals/run_codex_conformance.py --run --output result.json
```

See [`evals/README.md`](evals/README.md) for the credential boundary, pass oracle, and provenance
record. The current clean-SHA Sol baselines prove 11 selected skill/reference lanes and nine lanes
covering all seven standalone Codex agents, including the two trust-separated refusal behaviors.
Older six-lane/six-agent results remain immutable historical snapshots. None of these baselines prove
implicit routing or Claude-equivalent per-agent tool narrowing; those remain separate host/runtime
questions.

## Current status

- Canonical source, generated host adapters, hook wiring, manifests, installer collision behavior,
  eval contracts, and the protected-main canary are structurally gated.
- Claude marketplace validation and isolated plugin loading are verified on the recorded CLI version.
- Codex/Sol direct skill/reference loading and explicit custom-agent delegation are verified by the
  committed baselines under [`evals/baselines/`](evals/baselines/).
- Copilot/VS Code runtime loading remains unverified because that runtime is not available on the
  current validation host. Static adapter success must not be presented as a live runtime pass.
- Publication is blocked on repository protection, distinct promotion authority, host install smoke
  tests, and rollback evidence.

The only live backlog is [`docs/fleet-roadmap.md`](docs/fleet-roadmap.md). The large documents under
`docs/superpowers/plans/` are preserved implementation history and are not executable task lists.

## Contribute

Start with [AGENTS.md](AGENTS.md) for the repository workflow and [CONTRIBUTING.md](CONTRIBUTING.md) for
authoring and review policy. The redesign's decision record is preserved in git history (tag
`pre-cleanup-2026-07-15`).
