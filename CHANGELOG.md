# Changelog

Recent changes to the current Save Toolkit. This is a pre-release repository; entries do not
assert a published release or acceptance of an evaluated candidate. Earlier implementation history
is available in Git. Unfinished work belongs in [`docs/fleet-roadmap.md`](docs/fleet-roadmap.md).

## [Unreleased]

### Fixed

- Corrected wrong PCF mitigation guidance: whole-app `cf restart` stops every instance, so the
  covered restart is per-instance or rolling; a revision rollback restores the revision's env vars
  and creates a new `Rolled back to revision <n>` entry, so readback checks the description; rollback
  is a rolling deployment and cancelling it restores the bad droplet. Corrected the JVM
  `OutOfMemoryError` guidance (the message names the exhausted pool) and the Splunk top-offenders
  query (no `error` keyword; an empty result is a missing extraction). The incident advisor routes
  external-monitor and Situation pages to `obs-alerting`, opens Apps Manager Events first, and never
  searches for documentation; the runbook exemplar and template are console-first with
  `last_verified` bound to the drilled version; the commander's evidence rules match the helper's
  read contract. Ceilings rise to 610,565 skill bytes and a 77,000-byte human incident path. See the
  [quality round record](docs/reviews/2026-09-08-quality-round.md).
- Engineering lane, same round: the Spring problem-details advice no longer claims a property it
  makes redundant and names the security-filter 401/403 gap; the builder ladder keeps a scoped
  security fix builder-owned; the skill token budget is described as the compaction re-attachment
  budget; the CI starter and deploy skeleton carry `timeout-minutes`; the contract test carries an
  `auth_headers` fixture matching the bearer-protected OpenAPI starter; the Handoffs convention says
  what a review dispatch supplies; the reviewer's worked examples carry `Reviewed state:` and the
  non-execution line. Ceilings: 612,873 skill bytes, 116,305 agent bytes.
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

- Retired the standalone `incident-command` skill for the team's investigation role. The advisor
  retains its seven-field board, owns conditional mitigation and severity advice, and prepares
  technical updates for an existing bridge/TLC without opening another or assigning command roles.
  The human incident lead retains formal classification, coordination, and stakeholder communications.

- The `runbook`, `postmortem`, and `operational-learning` descriptions lead with what a person
  would say ("help me write a runbook for restarting pricing", "write a postmortem for INC-1234",
  "which team owns payments and how do I page them"); `operational-learning` answers ownership and
  dependency questions from the service cards; `ci-actions` excludes application deploys and
  runtime bugs; a `stack-profile` reference defines blast radius, golden signals, and the human
  roles. Four routing scenarios, two of them new, pass 3/3 on Sonnet. The reviewer's README row
  and three agent bodies lose rules they could not act on. Ceilings rise to 587,200 skill bytes and
  115,800 agent bytes. See the [quick-fix record](docs/reviews/2026-09-08-review-quick-fixes.md).
- The incident advisor's description now names the first responder and carries on-call trigger
  phrasing ('I just got paged, what do I do', 'customers are reporting errors, where do I start').
  In a clean batch on the merged head, the new unhinted first-page routing scenario fires it 3/3 on
  Sonnet and 3/3 on Opus; walk-me-through, staging triage, the no-dispatch negative, and the
  dispatched-read helper positive pass 3/3 on Sonnet. `discovery-active-alert-stays-with-advisor`
  and `native-incident-helper-return-and-resume` each pass 2 of 3 trials and keep an INCONCLUSIVE
  aggregate: one trial each ended in a denied or missing file read, not a routing miss. The
  skill-byte ceiling rose by 200 bytes, to 584,200, against an LF total of 584,042. See the
  [advisor on-call trigger evidence](docs/reviews/2026-09-08-advisor-oncall-triggers.md).

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
