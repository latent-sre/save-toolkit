# Save Toolkit

Save Toolkit is a multi-host plugin containing **8 canonical host-facing agents and 29 skills** for
application engineering and site reliability work. Claude Code reads the canonical
[`agents/`](agents) and [`skills/`](skills) sources directly. GitHub Copilot/VS Code and Codex
receive committed, host-native projections made by one deterministic generator; generated files are
never edited by hand.

The roster, tool postures, and enforcement model are in [AGENTS.md](AGENTS.md). Routing is native:
Claude plugin components are namespaced as `save-toolkit:<name>`; generated hosts use their native
bare component names.

## Layout

- [`agents/`](agents) — the eight canonical Claude plugin agent definitions; `tools` carries authority.
- [`skills/`](skills) — the 29 canonical skills and their progressive-disclosure `references/`,
  `assets/`, and `scripts/` bundles.
- [`commands/adr.md`](commands/adr.md) — the canonical Claude `/save-toolkit:adr` scaffold.
- [`.claude-plugin/`](.claude-plugin) and [`hooks/`](hooks) — Claude manifest/marketplace plus the
  session-scoped guarded-Bash hook.
- [`plugin.json`](plugin.json), [`.github/agents/`](.github/agents), and
  [`platforms/copilot/skills/`](platforms/copilot/skills) — Copilot/VS Code plugin and projections.
- [`plugins/save-toolkit/`](plugins/save-toolkit) and [`.codex/agents/`](.codex/agents) — Codex skills
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
  (record shape checked by [`validate_improvements.py`](scripts/validate_improvements.py); lifecycle
  transition, authority, history, and revision-binding validators remain parked at tag
  `pre-trim-2026-08-02`).
- [`evals/`](evals) — offline behavioral contracts, the manual Claude runner, the active narrow
  ROUTE-001 Codex/Terra evaluator, baseline records, and the bounded improvement ledger; broader
  Codex/Sol conformance remains parked at tag `pre-trim-2026-08-02`; see
  [`evals/README.md`](evals/README.md).
- [`docs/`](docs) — the only live backlog is [`docs/fleet-roadmap.md`](docs/fleet-roadmap.md);
  must-follow rules are indexed in [`docs/rules.md`](docs/rules.md); decisions live in
  [`docs/decisions/`](docs/decisions), closure evidence in [`docs/reviews/`](docs/reviews), and the
  documents under `docs/superpowers/plans/` are preserved implementation history, not task lists.

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

The 29 skills, by area (each `skills/<name>/SKILL.md` carries its own description):

- **Engineering craft** — `language-idiom`, `backend-craft`, `frontend-craft`, `ops-tooling`, `ci-actions`,
  `database-reliability`, `eng-ladder`
- **Platform** — `stack-profile`, `pcf-ops`, `pcf-deploy`, `gcp-ops`, `akamai-edge`
- **Change gates** — `merge-gate`, `release-gate`, `production-change-gate`
- **Incident and operations** — `root-cause`, `incident-command`, `postmortem`, `runbook`,
  `operational-learning`, `service-onboarding`
- **Observability** — `obs-logs`, `obs-metrics`, `obs-traces`, `obs-dashboards`, `obs-alerting`,
  `obs-pipeline`
- **The fleet itself** — `agent-authoring`, `agent-security`

## Use it in VS Code (Copilot Chat)

Both agents and skills are found by workspace folder scans; neither needs a plugin install.

**Agents — automatic.** VS Code scans `.github/agents/` in the open workspace, so opening this
repository exposes the eight portable roles in the Chat agent picker with no setup
([custom agents](https://code.visualstudio.com/docs/agent-customization/custom-agents)).

**Skills — one setting.** VS Code scans `.github/skills/`, `.claude/skills/`, and `.agents/skills/`
for project skills ([agent skills](https://code.visualstudio.com/docs/agent-customization/agent-skills)).
This fleet keeps its Copilot skill projection at `platforms/copilot/skills/`, the layout the
[packaging decision](docs/decisions/2026-07-31-multi-platform-plugin-packaging.md) accepted, so
[`.vscode/settings.json`](.vscode/settings.json) adds that directory through
`chat.agentSkillsLocations` instead of moving a generated root to suit one host.

For other workspaces, install at user level rather than copying files: VS Code also scans
`~/.copilot/agents/` and `~/.copilot/skills/`. Copied agent files arrive without their skills.

## Install an immutable release

Save Toolkit releases use one protected source tag named `save-toolkit--v<version>` across hosts.
There is no moving `release` branch. The examples below become valid only after the matching GitHub
Release exists and `gh release verify <tag> --repo latent-sre/save-toolkit` succeeds; beta-era
version `0.1.0` is prepared but not published by this change.

Claude Code installs the canonical agents, skills, command, and session hook from the tagged
marketplace:

```powershell
$releaseTag = 'save-toolkit--v0.1.0'
claude plugin marketplace add "latent-sre/save-toolkit@$releaseTag"
claude plugin install save-toolkit@latent-sre
claude plugin list --json
```

Codex installs the generated skills plugin from the same tag. Its generated custom agents remain a
standalone, conflict-safe install from that tagged checkout because Codex plugins do not publish
custom agents:

```powershell
$releaseTag = 'save-toolkit--v0.1.0'
codex plugin marketplace add "latent-sre/save-toolkit@$releaseTag"
codex plugin add save-toolkit@latent-sre
git clone --branch $releaseTag --depth 1 https://github.com/latent-sre/save-toolkit.git save-toolkit-release
py -3 save-toolkit-release/scripts/install_codex_agents.py --target '<project>/.codex/agents'
```

VS Code consumes `.github/agents/`, the registered skill projection, and workspace settings from the
tagged checkout itself. Open `save-toolkit-release` in VS Code; UI discovery remains an accepted
file-level verification limitation.

Maintainers use the protected
[`Publish immutable release`](.github/workflows/release.yml) workflow only after its external GitHub
controls are approved and present. Release recovery never moves a tag; follow the
[`release runbook`](docs/release-runbook.md).

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
Gate A checks record shape with the repository's bounded JSON Schema subset. The executable
lifecycle and corpus validators are parked at tag `pre-trim-2026-08-02` until the ledger carries
enough real records to justify them; shape validity does not prove transition, history, authority,
or subject binding. The contract still holds: records come only from measured encounters, and no
agent approves, merges, deploys, or rewrites itself — protected workflows remain the authority
boundary.

### Behavioral evals

Claude behavioral evaluations under [`evals/`](evals) remain manual; see
[`evals/README.md`](evals/README.md) for the clean-room boundary, scenario contract, and the status
of the historical Claude evidence and revoked 2026-07-31 Sol baselines.

The owner-approved ROUTE-001 rewrite adds a separate, narrow Codex campaign pinned to Codex CLI
0.147.0 and `gpt-5.6-terra` at medium reasoning: five scenarios paired across the fixed before/current
revisions plus fourteen current-only cases, two trials each, for 48 trials. It has not been run and
has produced no baseline. Codex 0.147 skill evidence is explicitly behavioral-only; only the two
root-scoped incident negatives are not measurable with stock V2 receipts and therefore always remain
`INCONCLUSIVE`. The evaluator contract is
designed to remove local and effect tools through an authoritative model catalog and strict configuration;
non-root trials allow no tool or collaboration receipts. The fixed authenticated canary is the
non-root GCP Cloud Run startup case and uses only linear graders. Its disposable login remains a
same-user application-layer boundary rather than OS-principal isolation. The tool-removal property
must be independently bound to exact Codex 0.147 source before live use; transformed JSON is not its
own proof. The full campaign is gated on clean committed evaluator bytes and independent review.

The broader Codex/Sol conformance runners and manifests remain parked at tag
`pre-trim-2026-08-02`; ROUTE-001 does not reopen EVAL-001. The parked design and its limits are
recorded in
[`docs/decisions/2026-08-01-local-sol-conformance.md`](docs/decisions/2026-08-01-local-sol-conformance.md).
For repository-controlled executable checks, use the digest-bound, networkless container boundary in
[`docs/verification-sandbox.md`](docs/verification-sandbox.md).

The Terra canary is not launched from the mutable checkout. Its prepared path starts from an
externally verified, protected copy of `evals/codex_bootstrap.py` under an absolute protected Python
runtime with `-I -S -B`; that bootstrap accepts only the exact evaluator-bundle manifest and one
fixed canary argument shape. The same bootstrap has an auth-free preflight that exercises the real
snapshot, Codex/catalog, hook, config, and drift boundary but stops before auth or a model request;
its result is diagnostic only and never authorizes live use. The current host's Python runtime
closure is user-writable, so the
authenticated canary is currently NO-GO. A protected Python executable/DLL/standard-library closure
or separate OS identity, a local fixed NTFS private root, and a clean managed-config/registry boundary
with no MCP, provider-route, proxy, guardian, or Command Processor AutoRun override are required
before the canary can run. The live launch also requires a protected Git executable/DLL/runtime
installation closure and sanitized object store with no repository-config includes, object
alternates, replacement refs, or UNC/network resolution. No live Terra result is implied by the
offline harness tests.

## Current status

- Canonical source, generated host adapters, hook wiring, manifests, and eval contracts are
  structurally gated (Gate A); Claude marketplace validation and isolated plugin loading are
  verified on the recorded CLI version. Must-follow constraints are indexed in
  [`docs/rules.md`](docs/rules.md).
- ROUTE-001's nineteen-scenario/48-trial Codex/Terra campaign has a committed offline evaluator and
  credential-free preflight (merged in PR #103), but no live result or baseline; its authenticated
  canary is blocked on the trusted runtime/tool-plan
  prerequisites above. Broader Codex/Sol conformance remains parked at tag `pre-trim-2026-08-02` with
  no current runtime baseline. Disposable host install/inventory/uninstall smoke for Claude, Codex,
  VS Code, and Copilot CLI is closed under
  [`HOST-001`](docs/reviews/2026-08-06-host-001-closure.md); the Copilot CLI is out of scope by owner
  decision, VS Code UI discovery and headless Codex agent discovery remain documented gaps, and the
  broader model-behavior work stays with deferred EVAL-001.
- `main` repository protection is closed (PROTECT-001). RELEASE-001's implementation — the exact-SHA
  workflow, release contract, strict remote-tag host smoke, and rollback runbook — merged in PR #103.
  Live publication remains blocked until the strict-host Claude authority census is repaired and
  independently reviewed, immutable releases plus the tag ruleset/environment/App are configured with
  explicit owner approval, and the first protected run supplies published-artifact and rollback
  evidence — tracked in [`docs/fleet-roadmap.md`](docs/fleet-roadmap.md).
- The prepared release remains the unpublished `0.1.0` beta. No `1.0` release exists or is implied by
  the ROUTE-001 evaluator work.

## Contribute

Start with [AGENTS.md](AGENTS.md) for the repository workflow and [CONTRIBUTING.md](CONTRIBUTING.md) for
authoring and review policy. The redesign's decision record is preserved in git history (tag
`pre-cleanup-2026-07-15`).
