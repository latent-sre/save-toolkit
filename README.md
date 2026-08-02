# SRE Agents

SRE Agents is a multi-host plugin containing **8 agents and 27 skills** for application engineering
and site reliability work. Claude Code reads the canonical [`agents/`](agents) and [`skills/`](skills)
sources directly. GitHub Copilot/VS Code and Codex receive committed, host-native projections made by
one deterministic generator; generated files are never edited by hand.

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
  (`readonly-guard.py`), generator, optional Codex agent installer, typed evidence validator,
  read-only fleet doctor, and mutation tests.
- [`evals/`](evals) — offline behavioral contracts, the manual Claude runner, operator-run local
  Codex/Sol conformance runners, baseline records, and the bounded improvement ledger.
- [`schemas/evidence-envelope-v1.schema.json`](schemas/evidence-envelope-v1.schema.json) — the
  portable runtime-evidence contract; the executable secret-field checks live in
  [`scripts/evidence_envelope.py`](scripts/evidence_envelope.py).
- [`skills/operational-learning/assets/knowledge-update-v1.schema.json`](skills/operational-learning/assets/knowledge-update-v1.schema.json)
  — the portable operational-learning contract; cross-record, lifecycle, prepared-file digest, and
  secret checks live in its bundled
  [`knowledge_update.py`](skills/operational-learning/scripts/knowledge_update.py).
- [`skills/agent-authoring/assets/fleet-improvement-v1.schema.json`](skills/agent-authoring/assets/fleet-improvement-v1.schema.json)
  — the portable bounded fleet-improvement ledger; its executable transition, budget,
  exact-subject, external-authority, and credential checks live in
  [`fleet_improvement.py`](skills/agent-authoring/scripts/fleet_improvement.py). Records live under
  [`evals/improvements/`](evals/improvements).

Routing is native. Claude plugin components are namespaced as `sre-agents:<name>`; generated hosts
use their native bare component names. The roster and enforcement model are in [AGENTS.md](AGENTS.md).

## Fleet inventory

<!-- fleet-inventory:start -->
### Agents (8)

| Agent | Lane | Routing |
|---|---|---|
| `sde` | Build, fix, refactor, and test code or operations tooling | Delegates review to `reviewer`, operational docs to `scribe`, and sanitized public lookups to `researcher` |
| `reviewer` | Read-only correctness, quality, and security review | Reports findings; hands approved fixes to `sde`; terminal |
| `repository-investigator` | Local-only answers about private, current, or uncommitted checkout behavior | Cites `file:line`; no shell, write, web, external MCP, skill, or delegation |
| `sre` | Investigate active production or staging failures (guarded read-only Bash) | Delegates observability follow-up to `sre-steward`, operational docs to `scribe`, and fact checks to `researcher` |
| `sre-steward` | Steady-state observability as code (guarded read-only Bash) | Hands docs to `scribe`, active incidents to `sre`, automation to `sde`, and lookups to `researcher` |
| `scribe` | Write evidence-bound runbooks, resolved-incident postmortems, and approved service/application/alert knowledge | Local document writer with no shell, web, external MCP, or delegation authority |
| `researcher` | External-only research against official docs, upstream code, packages, and advisories | No local file access; returns cited public evidence to caller |
| `prompt-engineer` | The fleet's own files: agents, skills, descriptions, evals | Hands helper code to `sde`, injection review to `reviewer` |

### Skills (27)

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
| `operational-learning` | Evidence-bound service, alert, runbook, and knowledge-index closeout |
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

Validate a knowledge-update packet after its documentation diff exists (prepared artifacts and
documentation duplicates require the exact Git worktree so their base transition or existing owner,
ordinary-file path, and result SHA-256 can be proved):

```powershell
py -3 skills/operational-learning/scripts/knowledge_update.py `
  .sre/knowledge-updates/<update-id>.json `
  --target-root C:\path\to\target-checkout `
  --allowed-knowledge-root docs/operations `
  --allowed-knowledge-root docs/runbooks
```

The allowed roots are caller policy supplied outside the packet. Repeat the flag for each trusted
documentation root; the packet's own `target.knowledge_roots` cannot authorize a write location.

Validate a fleet-improvement record with caller-owned artifact roots. These commands are for an
`sre-agents` source checkout: an installed `agent-authoring` bundle includes the portable schema and
standalone validator, but not the repository-root evidence validator or corpus scanner. Installed
callers must provide equivalent trusted code or run repository validation from the source checkout.

```powershell
py -3 skills/agent-authoring/scripts/fleet_improvement.py `
  evals/improvements/<improvement-id>/record.json `
  --repository-root . `
  --expected-repository latent-sre/sre-agents `
  --allowed-root agents --allowed-root skills --allowed-root evals `
  --allowed-root scripts --allowed-root schemas --allowed-root hooks --allowed-root commands `
  --allowed-evidence-root evals/evidence --allowed-evidence-root evals/baselines `
  --evidence-validator scripts/evidence_envelope.py `
  --authority-actor AUTHENTICATED_IDENTITY --authority-role triage

py -3 scripts/validate_improvement_ledger.py --repository-root .
```

This ledger activates only from measured encounters. It does not poll in the background or let an
agent approve, merge, deploy, or rewrite itself. See the
[`agent-authoring` lifecycle](skills/agent-authoring/references/improvement-lifecycle.md) for the
qualification rule, predeclared reservations and measured usage, three-attempt cumulative cap,
resolved evidence-envelope boundary, external shadow-set rule, retained Git history, and
authenticated outer-transition requirement. The repository scanner proves transition structure,
global fingerprint/event/evidence deduplication, and authoritative Git object relationships—not the
identity of historical actors; protected workflows remain the authority boundary. It fails
closed on a shallow clone, so any automation that runs Gate A must check out complete history. The
manually disabled **Validate fleet** workflow remains untouched; its checkout must use
`fetch-depth: 0` before it is re-enabled.

The v1 contract hard-caps a record at 60 model turns, 60 evaluator calls, 1,000,000 tokens, 14,400
wall-clock seconds, USD 100, and a 16 KiB aggregate target-path argv; a trusted caller may impose
lower ceilings. Fresh evaluation envelopes bind evaluator identity, reservation, and actual usage,
while monitoring envelopes bind the observer. Any retained protected-shadow result must pass before
review or promotion. Duplicate JSON keys fail before lifecycle validation. Schema and executable
validation both require literal uppercase `T` and `Z` in UTC timestamps.

The canonical `sre-agents-git-artifact-selection-v1` digest binds exact selected Git blob bytes and
metadata: candidate subjects must follow the recorded ancestry chain and touch every declared target.
Promotion is either the exact reviewed commit or a two-parent merge. For a merge, the reviewed commit
is one direct parent; the other parent descends from and has not drifted from the target base; and
that recorded base is their unique actual merge base. Promotion cannot change selected artifacts or
introduce a merge-only tree entry. Raw trees must be canonically ordered, structurally valid, bounded,
and portable across supported hosts, and every non-gitlink leaf must resolve to an existing Git blob.
Trusted queries disable Git commit-graph, graft, and replacement overlays and supervise stdin,
output, and process completion under one deadline. Divergent parent changes require rebase and
reevaluation.

Rollbacks must be exact one-parent inverses of the candidate-exclusive delta, or object-only
two-parent application merges of such a revert. They preserve unrelated bytes, reject later
target-path drift or rollback-only injection, descend from the promotion, and restore the base
artifact digest. Prior monitoring remains attached when a later non-monitoring trigger fires. A
direct `merged -> rolled_back` transition cannot add monitoring; monitoring failures and
inconclusive results must first enter `monitoring`, then roll back separately. An encoded terminal
lesson must resolve to a regular Git blob at the ledger revision. A `changes_requested` verdict
enters `in_review`; retrying as `candidate` or rejecting the record is a separate authorized
transition. Every record predeclares the mandatory rollback triggers for failed or inconclusive
monitoring, a security finding, revoked authority, and a merge error; owner-requested rollback is
optional.

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

Gate A owns its step list; do not copy that list into documentation. Claude behavioral evaluations
under [`evals/`](evals) remain manual. Live Codex/Sol conformance is also manual and accepts only the
local checkout with fixed manifests. Commit and independently review the exact revision before a live
run; the runner cannot verify that external review. It copies the operator's existing Codex login
into a disposable same-user home, so this is behavioral evidence rather than hostile-code containment.

Codex/Sol plugin conformance is a separate lane from the Claude runner:

```powershell
py -3 evals/run_codex_conformance.py --validate
```

See [`evals/README.md`](evals/README.md) for the credential boundary, pass oracle, and provenance
record. The five 2026-07-31 Codex/Sol snapshots are revoked as release evidence because their former
runner exposed `auth.json` to model-controlled reads and retained parsed final responses. Their bytes
remain for diagnosis, but there is no current Sol runtime baseline until both local runners evaluate
a clean committed revision and their sanitized reports are paired with independent review of that
exact revision. The static
manifests cover 11 skill/reference lanes
and thirteen custom-agent lanes, including both trust-separated refusals, reviewer authorization
behavior, and `scribe`'s non-execution plus knowledge-closeout contracts. None of these lanes proves
implicit routing or Claude-equivalent per-agent tool narrowing.
The skill lane disables both Codex multi-agent implementations. The agent lane accepts only the
current checkout's passive plugin and constrained agent configuration, caps V1 and V2 at one live
child with no V1 descendants, and
shares a runtime rollout budget across root and child; post-response usage ceilings and the provider
account quota remain independent outer checks. Raw output and temporary agent sessions are reduced to
hashes and structural facts, and the disposable home is deleted before the report is returned.
The runner always labels source review as unverified, independent evaluation as false, and baseline
eligibility and release grant as false. See the
[`local Sol conformance decision`](docs/decisions/2026-08-01-local-sol-conformance.md).

## Current status

- Canonical source, generated host adapters, hook wiring, manifests, installer collision behavior,
  and eval contracts are structurally gated.
- Claude marketplace validation and isolated plugin loading are verified on the recorded CLI version.
- Codex/Sol manifests, local same-user auth handling, response reduction, and explicit custom-agent
  contracts pass offline validation; a fresh exact-revision run plus external review remains pending.
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
