# Decision records

Retained contracts for the current fleet and unresolved roadmap work. Completed renames,
retired release and evaluation designs, and archive-location records are kept in Git history.
Accepted ADRs stay byte-for-byte unchanged, including citations to historical paths, unless the
ADR's decision owner, the business owner who accepted it, amends it. An owner amendment adds a dated
`Amended:` line naming the change, and its commit message says the decision owner made it. References
removed by this cleanup are in the [pre-cleanup snapshot](https://github.com/latent-sre/save-toolkit/tree/e6702ee04ca03f87e71595fb4dbf89a722df9fe9/docs/decisions);
earlier missing references require their own historical revision.
Six records the owner removed on 2026-11-03 are in the [pre-removal snapshot](https://github.com/latent-sre/save-toolkit/tree/74bc8ff1e5d3d74d5c081ffae0f5e0ff4ec892b4/docs/decisions).
Anyone else changes a decision through a successor as described in [`commands/adr.md`](../../commands/adr.md).

The [retention successor](2026-09-07-historical-artifact-retention.md) replaced the
incident-navigation and incident-autonomy bundle-preservation requirements when maintainers merged
PR #238 on 2026-09-07. It preserves branch dispositions, current tool authority, and acceptance holds.

| Date | Decision | Status |
|---|---|---|
| 2026-10-25 | [Explicit native evaluation selections](2026-10-25-explicit-native-selections.md) | Accepted for implementation; candidate acceptance remains separate |
| 2026-08-21 | [Take `observability-engineer` off the read-only Bash guard](2026-08-21-observability-engineer-unguarded-bash.md) | Accepted |
| 2026-08-22 | [Agent discovery is model-labelled calibration](2026-08-22-agent-discovery-calibration.md) | accepted 2026-08-22; disposes `EVAL-002` |
| 2026-08-23 | [Retire Codex as a distribution target; keep it as a way to work in this repository](2026-08-23-retire-codex-distribution-target.md) | Accepted |
| 2026-08-24 | [Establish a source-independent SRE operational-context contract](2026-08-24-sre-operational-context-contract.md) | Accepted |
| 2026-09-01 | [One Claude engine, deterministic structure graders, and a calibrated rubric judge](2026-09-01-rubric-judge-evaluation-contract.md) | Accepted 2026-09-01; failed-judge-call sentence superseded by [2026-10-03-eval-harness-threat-model](2026-10-03-eval-harness-threat-model.md) |
| 2026-09-03 | [One eval runner, three scenario kinds](2026-09-03-one-eval-runner.md) | Accepted 2026-09-03; registry list superseded by [2026-09-04-eight-grader-registry](2026-09-04-eight-grader-registry.md) |
| 2026-09-04 | [The grader registry is eight graders](2026-09-04-eight-grader-registry.md) | Accepted 2026-09-04 |
| 2026-09-21 | [Add a reliability engineering lane and two focused methods](2026-09-21-reliability-engineer.md) | Proposed; implementation authorized by the owner, exact-candidate acceptance pending (RELIABILITY-001) |
| 2026-09-07 | [Keep retired artifacts in Git history](2026-09-07-historical-artifact-retention.md) | Accepted on maintainer merge of PR #238, 2026-09-07 |
| 2026-10-03 | [What the eval harness defends against](2026-10-03-eval-harness-threat-model.md) | Accepted 2026-10-06, with result rules added before acceptance; amended by the owner 2026-11-02 to name what rules 5 and 6 record |
| 2026-10-04 | [The incident companion judge reads the case material, not a summary of it](https://github.com/latent-sre/save-toolkit/blob/7ac287d518df1f5b8c9397642a8204b0909ca2ac/docs/decisions/2026-10-04-rubric-judge-case-material.md) | Proposed amendment to 2026-09-01, never implemented; EVAL-010 closed 2026-10-07; file removed 2026-11-02, kept in Git |
| 2026-10-05 | [Add one principal engineering lane for system design and architecture](2026-10-05-principal-engineer.md) | Proposed |
| 2026-10-11 | [Rebuild frontend-craft on the owner's decisions](https://github.com/latent-sre/save-toolkit/blob/fd0a47ffb5f038858c4a46aeb6896563ff4f5eed/docs/decisions/2026-10-11-frontend-craft.md) | Superseded by [2026-10-11-frontend-craft-generalized](2026-10-11-frontend-craft-generalized.md); file removed 2026-11-02, kept in Git |
| 2026-10-11 | [Generalize frontend-craft: React first, any approved kit, mixable, no house look](2026-10-11-frontend-craft-generalized.md) | Decisions accepted by the owner 2026-10-11; implementing candidate pending |
| 2026-10-11 | [Rebuild backend-craft on the owner's decisions](2026-10-11-backend-craft.md) | Amended 2026-10-18: retire BACKEND-001 expansion, narrow to `api-craft`, and prefer current stable technology; implementing candidate pending |
| 2026-10-23 | [Gate software-engineer's return on the five-file review rule with a stop hook](https://github.com/latent-sre/save-toolkit/blob/fd0a47ffb5f038858c4a46aeb6896563ff4f5eed/docs/decisions/2026-10-23-review-gate-hook.md) | Rejected 2026-10-28; the owner dropped the five-file review trigger; file removed 2026-11-02, kept in Git |
| 2026-11-02 | [Rewrite the eval runner's core around a persisted evidence artifact](2026-11-02-probe-runner-refactor.md) | Accepted for implementation by the owner 2026-11-02; each stage's candidate is accepted separately; amended by the owner 2026-11-02 with the decisions the plan left open |
