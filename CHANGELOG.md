# Changelog

All notable Save Toolkit changes are recorded here. This is pre-release repository history; a version
entry does not imply that a GitHub Release or immutable consumer selector exists.

## [Unreleased]

Changes after the prepared `0.1.0` baseline belong here.

## [0.1.0] - 2026-08-11

> **Prepared repository baseline, not a published release.** The date above records when this entry
> was prepared. The repository currently has no supported immutable release channel.

### Added

- Eight canonical engineering and SRE agents, with 29 canonical skills and one ADR command.
- Deterministic Copilot/VS Code and Codex projections generated from the Claude-native sources.
- Fail-closed guarded-Bash enforcement for the SRE lane, plus structural tests for
  tool authority, hook wiring, generated-byte parity, links, schemas, and routing scenarios.
- Conflict-safe standalone Codex-agent installation.
- Evidence envelopes, evidence-bound operational documentation closeout, release/readiness gates,
  and the single Gate A structural entrypoint used on Linux and Windows.

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

### Known limitations

- Copilot CLI distribution is out of scope by owner decision; VS Code and Codex custom-agent
  discovery evidence is file-level only, not UI or model-session proof.
