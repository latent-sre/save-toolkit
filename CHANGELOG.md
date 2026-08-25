# Changelog

All notable Save Toolkit changes are recorded here. This is pre-release repository history; a version
entry does not imply that a GitHub Release or immutable consumer selector exists.

## [Unreleased]

### Added

- Added the canonical `workflow-graph-engineering` skill (`SKILLS-003`): a runtime-neutral design
  and review contract for executable workflow/state graphs — typed state, node and edge classes,
  fan-out/fan-in, scheduling and admission, retries, effects with idempotency keys and an explicit
  `UNKNOWN` outcome, approvals, durability, cancellation, termination, taint, and graph-level
  evals — with six predicate-keyed references and a fourteen-section artifact template.
  `prompt-engineer` now routes executable-graph design there; `agent-authoring` keeps the
  roster/delegation graph and excludes the executable contract. Five routing scenarios cover the
  positive case and the roster, code-graph, runtime-implementation, and runtime-selection near
  misses. No runtime, schema, or validator is selected or added.

### Changed

- Generalized `release-gate` so non-GitHub distributions can prove immutable artifact identity
  without inheriting GitHub Release controls, while GitHub Releases still require current
  repository immutability and matching tag-ruleset evidence.

### Removed

- Retired the unpublished repository-specific release workflow, request and workflow contracts,
  release-only tests, and release runbook; no immutable release channel had been activated.
- Retired the standalone multi-host lifecycle probe and focused suite because no workflow, CI job,
  or named manual consumer called them.
- Retired the stale local Sol evaluation and unimplemented durable-state backlog items, retaining
  their historical evidence and explicit consumer-driven reopen triggers.
- Retired Codex as a **distribution target**: the generated `.codex/agents/` and
  `plugins/save-toolkit/` projections and the conflict-safe agent installer are gone
  ([ADR](docs/decisions/2026-08-23-retire-codex-distribution-target.md)). Codex remains a
  supported way to *work in* this repository — it reads the root `AGENTS.md` and needs none of
  those bytes. **Breaking for anyone who installed the Codex agents or skills plugin:** deleting
  the projections cannot reach copies already written into a Codex home, and the marker-aware
  installer that owned them is removed here. The ADR's *Migration* section carries the exact
  cleanup — match the whole first line against the `save-toolkit`/`sre-agents` markers, never a
  filename or prefix, because a sibling fleet's `sde-agents` marker differs by one character and
  shares three role names.

## [0.1.0] - 2026-08-11

> **Prepared repository baseline, not a published release.** No `save-toolkit--v0.1.0` tag or GitHub
> Release exists. The date above records when this baseline was prepared; the later retirement of
> its unpublished release machinery is recorded under `Unreleased` rather than rewriting this
> historical inventory.

### Added

- Eight canonical engineering and SRE agents, with 30 canonical skills and one ADR command.
- Deterministic Copilot/VS Code and Codex projections generated from the Claude-native sources.
- Fail-closed guarded-Bash enforcement for the SRE lane, plus structural tests for
  tool authority, hook wiring, generated-byte parity, links, schemas, and routing scenarios.
- Conflict-safe standalone Codex-agent installation and disposable host install/inventory/uninstall
  probes that do not write user-owned configuration.
- Evidence envelopes, evidence-bound operational documentation closeout, release/readiness gates,
  and the single Gate A structural entrypoint used on Linux and Windows.
- Exact-SHA immutable release preparation with permanent version reservations, non-replacing request
  serialization, attempt-addressed evidence artifacts, and consumer rollback instructions.

### Changed

- Renamed the fleet and plugin to Save Toolkit and consolidated observability ownership under the
  `observability-engineer` lane.
- Added GCP operations and Akamai edge-routing skills while preserving explicit PCF, active-incident,
  and observability lane boundaries.
- Gave declared incidents an explicit fast path through `production-change-gate`: a named
  never-skipped core (classification, human confirmation of an exact command or an IC-approved
  bounded envelope, blast radius, backout, named decider) with every other record reconciled after
  resolution, scoped to Tier 0–2 operational mitigation and rollback to an already-live artifact.
  Shipping a new artifact and any Tier 3 action stay on the full gate.
- Trimmed duplicate checklist items from the three gates and scoped handoff SHA pinning to
  references whose byte identity decides something downstream.
- Documented the four design disciplines the fleet is built on — loop, graph, handoff, and learning
  engineering — in `AGENTS.md` with depth in `agent-authoring/references/roster.md`.
- Rewrote the README around installation and first use, relocating validation, eval, and release
  detail to the documents that own it.

### Security

- Generated hosts state their weaker enforcement explicitly instead of claiming Claude hook or tool
  semantics they cannot enforce.
- External research is separated from private-checkout investigation, and destructive or production
  effects remain human- or protected-workflow-owned.
- Every read-only-guard denial now names the rule that fired instead of printing one static
  paragraph, and the guard permits shapes proven harmless (quoted comparison operators via
  token-level redirect detection, `>/dev/null`, `2>&1`, `timeout <n> <allowed command>`, and
  display-only `date`) without weakening command-substitution or backgrounding rules.
- Release host proof derives exact ordinary-file paths and Git blob bytes from the observed tagged
  commit, then requires both marketplace and installed Claude/Codex trees to match before publication
  can finalize; linked, special, missing, changed, and extra content fails closed.

### Known limitations

- Copilot CLI distribution is out of scope by owner decision; VS Code discovery is verified at the
  workspace-file level, not through its UI.
- Codex custom-agent discovery is verified at the installed-file level; no model session is part of
  the release smoke.
