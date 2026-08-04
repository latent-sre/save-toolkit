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
  the [schema catalog](schemas/catalog-v1.json), the
  [evidence envelope](schemas/evidence-envelope-v1.schema.json)
  ([`evidence_envelope.py`](scripts/evidence_envelope.py)), the
  [current knowledge update](skills/operational-learning/assets/knowledge-update-v2.schema.json)
  ([`knowledge_update.py`](skills/operational-learning/scripts/knowledge_update.py)), and the
  [fleet-improvement ledger](skills/agent-authoring/assets/fleet-improvement-v1.schema.json)
  (schema and records under [`evals/improvements/`](evals/improvements); the executable
  validators are parked at tag `pre-trim-2026-08-02`).
- [`evals/`](evals) — offline behavioral contracts, the manual Claude runner, baseline records, and
  the bounded improvement ledger; the Codex/Sol conformance runners are parked at tag
  `pre-trim-2026-08-02`; see [`evals/README.md`](evals/README.md).
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
| `sre` | Investigate active production or staging failures (guarded read-only Bash) | Delegates observability follow-up to `observability-engineer`, operational docs to `scribe`, and fact checks to `researcher` |
| `observability-engineer` | Steady-state observability as code (guarded read-only Bash) | Hands docs to `scribe`, active incidents to `sre`, automation to `sde`, and lookups to `researcher` |
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

## Use it in VS Code (Copilot Chat)

Both agents and skills are found by workspace folder scans; neither needs a plugin install.

**Agents — automatic.** VS Code scans `.github/agents/` in the open workspace, so opening this
repository exposes all eight roles in the Chat agent picker with no setup
([custom agents](https://code.visualstudio.com/docs/agent-customization/custom-agents)).

**Skills — one setting.** VS Code scans `.github/skills/`, `.claude/skills/`, and `.agents/skills/`
for project skills ([agent skills](https://code.visualstudio.com/docs/agent-customization/agent-skills)).
This fleet keeps its Copilot skill projection at `platforms/copilot/skills/`, the layout the
[packaging decision](docs/decisions/2026-07-31-multi-platform-plugin-packaging.md) accepted, so
[`.vscode/settings.json`](.vscode/settings.json) adds that directory through
`chat.agentSkillsLocations` instead of moving a generated root to suit one host.

For other workspaces, install at user level rather than copying files: VS Code also scans
`~/.copilot/agents/` and `~/.copilot/skills/`. Copied agent files arrive without their skills.

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
write location. The validator accepts v1 and v2; new packets use v2. The
[compatibility policy](docs/schema-compatibility.md) documents versioning and migration:

```powershell
py -3 skills/operational-learning/scripts/knowledge_update.py `
  .sre/knowledge-updates/<update-id>.json `
  --target-root C:\path\to\target-checkout `
  --allowed-knowledge-root docs/operations `
  --allowed-knowledge-root docs/runbooks
```

Migrate a v1 service packet to the current component-aware v2 shape without changing the source:

```powershell
py -3 skills/operational-learning/scripts/migrate_v1_to_v2.py `
  .sre/knowledge-updates/<update-id>.json `
  --output .sre/knowledge-updates/<update-id>-v2.json
```

Fleet-improvement records under [`evals/improvements/`](evals/improvements) follow the schema and
the lifecycle contract in
[`skills/agent-authoring/references/improvement-lifecycle.md`](skills/agent-authoring/references/improvement-lifecycle.md).
The executable lifecycle and corpus validators are parked at tag `pre-trim-2026-08-02` until the
ledger carries enough real records to justify them; the contract still holds: records come only from
measured encounters, and no agent approves, merges, deploys, or rewrites itself — protected
workflows remain the authority boundary.

### Behavioral evals

Claude behavioral evaluations under [`evals/`](evals) remain manual; see
[`evals/README.md`](evals/README.md) for the clean-room boundary, scenario contract, and the status
of the revoked 2026-07-31 Sol baselines. The Codex/Sol conformance runners and manifests are parked
at tag `pre-trim-2026-08-02` — Gate A plus the local Claude runner is the active verification
surface; the parked design and its limits are recorded in
[`docs/decisions/2026-08-01-local-sol-conformance.md`](docs/decisions/2026-08-01-local-sol-conformance.md).
For repository-controlled executable checks, use the digest-bound, networkless container boundary in
[`docs/verification-sandbox.md`](docs/verification-sandbox.md).

## Current status

- Canonical source, generated host adapters, hook wiring, manifests, and eval contracts are
  structurally gated (Gate A); Claude marketplace validation and isolated plugin loading are
  verified on the recorded CLI version.
- Codex/Sol conformance is parked at tag `pre-trim-2026-08-02` with no current runtime baseline.
  Copilot/VS Code runtime loading remains unverified because that runtime is not available on the
  current validation host.
- Publication is blocked on repository protection, distinct promotion authority, host install smoke
  tests, and rollback evidence — tracked in [`docs/fleet-roadmap.md`](docs/fleet-roadmap.md).

## Contribute

Start with [AGENTS.md](AGENTS.md) for the repository workflow and [CONTRIBUTING.md](CONTRIBUTING.md) for
authoring and review policy. The redesign's decision record is preserved in git history (tag
`pre-cleanup-2026-07-15`).
