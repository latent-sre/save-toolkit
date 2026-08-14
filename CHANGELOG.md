# Changelog

All notable Save Toolkit changes are recorded here. Versions identify immutable GitHub release tags
named `save-toolkit--v<version>`; a tag is never moved or reused.

## [Unreleased]

Empty by design: `0.1.0` has not been published, so in-flight work folds into it below rather than
accumulating here. This section opens once `save-toolkit--v0.1.0` exists.

## [0.1.0] - 2026-08-11

> **Prepared, not yet published.** No `save-toolkit--v0.1.0` tag or GitHub Release exists — the date
> above is when this entry was prepared, not a ship date. Publication is blocked on `RELEASE-001` in
> [`docs/fleet-roadmap.md`](docs/fleet-roadmap.md). The heading format is fixed by the release
> contract (`scripts/test_release_contract.py`), so the status is stated here rather than in it.

### Added

- Eight canonical engineering and SRE agents, with 29 canonical skills and one ADR command.
- Deterministic Copilot/VS Code and Codex projections generated from the Claude-native sources.
- Fail-closed guarded-Bash enforcement for the SRE and observability lanes, plus structural tests for
  tool authority, hook wiring, generated-byte parity, links, schemas, and routing scenarios.
- Conflict-safe standalone Codex-agent installation and disposable host install/inventory/uninstall
  probes that do not write user-owned configuration.
- Evidence envelopes, operational-learning contracts, release/readiness gates, and the single Gate A
  structural entrypoint used on Linux, macOS, and Windows.
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
