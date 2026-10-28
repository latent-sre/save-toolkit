# Changelog

Recent changes to the current Save Toolkit. This is a pre-release repository; entries do not
assert a published release or acceptance of an evaluated candidate. Releases before 0.51.3 are in
Git history at `562a654b`. Unfinished work belongs in [`docs/fleet-roadmap.md`](docs/fleet-roadmap.md).

## [Unreleased]

### Changed

- Rebuild software-engineer around complete workflows, proportionate engineering judgment,
  and one evidence-reusing verification, review, and completion policy.
- Repair Windows evaluation fixtures, recognize CRLF verifier failure markers and allow
  bounded loopback refusal detection; retain explicit gaps for unavailable symlink privileges.
- Reconcile EVAL-012 preparation with recorded Linux trials, Windows verification gaps and the
  measured Docker quota failure; retain outstanding campaign and human-acceptance requirements.
- Clarify authoring reference selection and API client scope; trim repeated CI and database guidance
  while preserving operational authority, recovery rules, and executable examples.
- Consolidate `operational-learning`, `runbook`, and `postmortem` into `operational-docs` (27 to 25
  skills) with methods, assets, and importer behavior intact ([evidence](docs/reviews/2026-10-24-operational-docs-consolidation.md)).
- Trim the references of 22 skills, removing repeated narration, tutorials, and unconfirmed claims;
  contracts, recorded decisions, and fenced command blocks are unchanged.
- Correct reference facts: MSW 3 imports, configurable TraceQL windows, non-GPU startup-probe scope,
  Direct VPC sizing, and Confluence page-URL provenance; PCF rollback now checks installed capability.
- Drop unconfirmed observability team mandates; burn-rate thresholds and Splunk lookups are
  examples, and MQL, Alloy retention, Moogsoft, and ThousandEyes claims are corrected.
- Dashboard presentation and portability findings are advisory: advisory-only checks exit 0, query
  and missing-target findings exit 1, and unsupported or malformed input exits 2.
- Move the agent roster from `AGENTS.md` to README's Tools and delegation table, still validated
  against frontmatter by Gate A; two maintenance notes move from `AGENTS.md` to `CONTRIBUTING.md`.
- Condense this changelog to one entry per change and keep only the last two releases;
  `CONTRIBUTING.md` now states that rule.

### Removed

- Fleet tests that pinned `software-engineer` wording; a two-phrase check keeps the caller-owned
  review path.
- From `AGENTS.md`: the Grafana-exception bullet, the stack-profile load sentence, and passages
  repeated in the frontmatter reference or `CONTRIBUTING.md`.
- Five completed review packets that only the old changelog entries cited; Git keeps them at
  `562a654b`.

### Fixed

- The SWE-bench runner tests write their fixture scripts with LF line endings, so the runner no
  longer rejects them on Windows hosts.

## [0.51.4] - 2026-10-23

### Changed

- `software-engineer`: compress the handoff rows and remove `## Rules`; its one unique rule, hand to
  one agent at a time, moves into Handoffs.
- `sre-assistant`: remove text its skills or the guard already cover; it states that its developer
  access to team apps is read-only use.
- `observability-engineer`: principles and method steps defer to `obs-alerting` and
  `obs-dashboards`, and a caller's requested output format wins.
- Trim the `stack-profile`, `agent-authoring`, `toil-reduction`, and `pcf-ops` cores to what their
  readers lack; the MCP output-cap rule moves to the frontmatter reference.

### Removed

- Fleet-wide agent body-shape checks and the tests that pinned `sre-assistant` wording; the
  tool-authority checks remain.

### Fixed

- `software-engineer` treats a push or tag push as a CI submission and again keeps embedded
  remote-URL credentials out of its context.
- The routine-completion grader matches the current return-header fields.

## [0.51.3] - 2026-10-22

### Added

- `go-craft`, a candidate skill for Go services, CLIs, libraries, and workers; native routing and
  benefit are unmeasured (BACKEND-002).
- WP-12's GCP catalog: 20 families (40 A/B cases); the owner accepted all 64 cases at `9147ff91`
  under DEC-14.

### Changed

- `software-engineer` gets a leaner core for dispatched work (issue #403): caller-owned review,
  named verification scope, and the final message as the report; the `Changed` packet slot returns.
- `observability-engineer` drops its unguarded-Bash paragraph; the ADR, the guard, and the
  `grafana` trust rule still hold.
- Rename `backend-craft` to `api-craft`, scoped to HTTP APIs, webhook receivers, HTTP clients, and
  API-accepted work, with corrected FastAPI, Huma, and credential-renewal guidance.
- EVAL-005 ran six Sonnet trials, all FAIL under the all-checks threshold
  ([run record](docs/reviews/2026-10-18-eval-005-run.md)).

### Fixed

- Oracle and handoff validation use contract checks instead of arbitrary count and length
  thresholds.
