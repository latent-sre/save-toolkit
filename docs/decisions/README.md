# Decision records

Retained contracts for the current fleet and unresolved roadmap work. Completed renames,
retired release and evaluation designs, and archive-location records are kept in Git history.
Accepted decision text stays unchanged; citations to removed files point to their committed versions.
Change a decision through a successor as described in [`commands/adr.md`](../../commands/adr.md).

The 2026-09-07 documentation cleanup removes restoration bundles from the working tree. Their
historical preservation instructions do not require a second copy here or reactivate the prototypes.
The cleanup does not change branch dispositions, current tool authority, or acceptance holds.

| Date | Decision | Status |
|---|---|---|
| 2026-08-21 | [Take `observability-engineer` off the read-only Bash guard](2026-08-21-observability-engineer-unguarded-bash.md) | Accepted |
| 2026-08-22 | [Agent discovery is model-labelled calibration](2026-08-22-agent-discovery-calibration.md) | accepted 2026-08-22; disposes `EVAL-002` |
| 2026-08-22 | [Production-only exact-SHA review boundary](2026-08-22-production-review-boundary.md) | accepted 2026-08-22; disposes `REVIEW-001` |
| 2026-08-23 | [Allow a per-agent model generation alias; keep the ban on full model IDs](2026-08-23-allow-model-aliases.md) | Accepted |
| 2026-08-23 | [Allow third-party dependencies everywhere, pinned in `requirements-dev.txt`](2026-08-23-allow-third-party-dependencies.md) | Accepted |
| 2026-08-23 | [Retire Codex as a distribution target; keep it as a way to work in this repository](2026-08-23-retire-codex-distribution-target.md) | Accepted |
| 2026-08-24 | [Establish a source-independent SRE operational-context contract](2026-08-24-sre-operational-context-contract.md) | Accepted |
| 2026-08-26 | [Use a consumer-specific Docker Compose sandbox for GRAPH-002](2026-08-26-graph-002-docker-sandbox-runtime.md) | Accepted |
| 2026-09-01 | [One Claude engine, deterministic structure graders, and a calibrated rubric judge](2026-09-01-rubric-judge-evaluation-contract.md) | Accepted 2026-09-01 |
| 2026-09-03 | [The incident lane is an advisor and a pair of hands](2026-09-03-incident-lane-advisor-and-hands.md) | Accepted 2026-09-03 |
| 2026-09-03 | [One eval runner, three scenario kinds](2026-09-03-one-eval-runner.md) | Accepted 2026-09-03; registry list superseded by [2026-09-04-eight-grader-registry](2026-09-04-eight-grader-registry.md) |
| 2026-09-04 | [The grader registry is eight graders](2026-09-04-eight-grader-registry.md) | Accepted 2026-09-04 |
