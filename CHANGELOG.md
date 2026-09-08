# Changelog

Recent changes to the current Save Toolkit. This is a pre-release repository; entries do not
assert a published release or acceptance of an evaluated candidate. Earlier implementation history
is available in Git. Unfinished work belongs in [`docs/fleet-roadmap.md`](docs/fleet-roadmap.md).

## [Unreleased]

### Fixed

- Corrected evaluation assertion identity, candidate aggregation and trial-input attribution;
  removed ineffective retired policy tests and scoped CI dependency checks to the actual job.
- Resolved portable helpers from their installed skill, qualified Claude-only guard claims,
  preserved Confluence link/image references with conversion-loss accounting, and repaired the
  authoring and human-console guidance. Ordinary CI selects only its two test dependencies from
  the existing version pins. See the [review-fix evidence](docs/reviews/2026-09-07-independent-review-fixes.md)
  for focused regressions, measured weight and remaining host/model verification.

### Added

- Added conditional symptom comparisons to the human incident advisor for login failures,
  intermittent errors, slow requests, stale/wrong data, and missed jobs with limited telemetry.
  See the [general incident help evidence](docs/reviews/2026-09-06-general-incident-help.md) for
  evaluation and the explicit context/skill-size allocation.

- A human incident advisor with conditional symptom guidance and a bounded, read-only
  `sre-assistant` helper. The advisor supports explanations, investigation, recap, and operational
  closeout while the human owns incident decisions and production actions.
- An `operator-cli` skill for operator-facing command-line tools, including partial results,
  secret handling, and uncertain effect outcomes.

### Changed

- The incident advisor's description now names the first responder and carries on-call trigger
  phrasing ('I just got paged, what do I do', 'customers are reporting errors, where do I start').
  A new unhinted first-page routing scenario fires it 3/3 on Sonnet and 3/3 on Opus, and the
  existing advisor and helper routing scenarios still pass. The skill-byte ceiling rose by 200 bytes
  for it, to 584,200. See the [advisor on-call trigger evidence](docs/reviews/2026-09-08-advisor-oncall-triggers.md).

- Routine documentation handoffs and operational templates now use unique short commit IDs
  (8 characters, extended by Git when needed). Checkout evidence and approval requirements remain;
  full IDs are still accepted. Immutable-review identities, dependency pins and eval digests are
  unchanged.

- Kept contact-only runbook corrections, supplied log/metric explanations, and bounded telemetry
  repairs scoped to their tasks while retaining full-workflow checks when requested. Aligned design
  consultation and operating-document routing with existing owners, and made rollback versus
  evidence-backed recovery consistent without changing tool grants or human execution authority.
  See the [scope and owner follow-up](docs/reviews/2026-09-07-task-sized-skill-outputs.md).

- Delegated helpers return assignment status, evidence, results, and gaps to their caller. The
  caller checks the claims and continues the parent task; helper completion does not resolve an
  incident or complete the parent objective.
- Alert, trace, log, metric, runbook, and postmortem guidance scales to the requested task. Short
  corrections and explanations avoid a full workflow packet; full investigations retain their
  evidence and ownership requirements. Postmortem and knowledge closeout share follow-up records.
  See the [pending output assessment](docs/reviews/2026-09-07-task-sized-skill-outputs.md).
- Incident examples distinguish scoped observations from unsupported causal, timing, and current-
  state claims. The [helper-exchange assessment](docs/reviews/2026-09-07-incident-helper-exchange.md)
  records the source verification and remaining behavioral decision.
- Evaluation uses one runner, `evals/build_probe.py`, for routing, contract, and build scenarios,
  with structural graders and a rubric judge. See the [current eval contract](evals/README.md).

### Removed

- Retired incident-autonomy and incident-navigation restoration bundles, including their obsolete
  scenarios, rubric fragments, calibration cases, generated copies, and patches.
- Completed review and trim-evaluation reports, completed rename records, superseded release and
  multi-engine evaluation decisions, and the old archive-location records. Current regressions,
  unresolved-decision evidence, and applicable contracts remain.
- The accumulated development diary and obsolete baseline inventory from this changelog. Historic
  feature names, scenario counts, and retired commands no longer describe the current toolkit.

### Known limitations

- Incident-quality adoption remains on hold. The
  [second bounded assessment](docs/reviews/2026-09-07-incident-quality-second-pass.md) records failed
  behavioral acceptance and links its preceding evidence. Structural checks and source review do
  not clear that hold; further model work and exact-candidate acceptance remain owner decisions.
- VS Code plugin enforcement remains host-specific; the
  [installation and verification guidance](README.md) records its limits.
- Codex distribution was retired. Codex can still work in this repository through `AGENTS.md`;
  the [retirement contract](docs/decisions/2026-08-23-retire-codex-distribution-target.md) retains
  migration guidance for earlier installations.
