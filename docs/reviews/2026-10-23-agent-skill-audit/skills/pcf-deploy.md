# PCF deploy skill audit

[verified] Target: `skills/pcf-deploy/` at `8b4f9b785e520944319e04fd8e5018d4545b6800`. No separate material source-contract finding confirmed; shared AUDIT-PCF-001 in the referenced operations procedure applies. Specification and engineering-quality verdicts: partial. The source provides a coherent human-executed planning contract; target CLI/CAPI behavior, model adherence and production outcomes remain unverified.

[sourced] The subsequently completed [PCF operations audit](pcf-ops.md) identifies an unsupported existing-droplet resize payload at its advertised minimum release. This shared procedure finding is counted once as AUDIT-PCF-001; it is not evidence of a live deployment failure.

## Contract assessment

[verified] Manual-only activation, agent non-execution, exact artifact/target approval, action-boundary revalidation and missing-evidence stop conditions are explicit. Scoped discovery and unapproved drafts remain allowed. Full release gates apply to new artifacts/staging; the incident fast path defers only permitted existing-artifact/reversible work. The production gate, incident-fast-path reference and pcf-ops effect reference agree on unknown package/droplet state and whole-app scale/restart limits.

[verified] Blue-green planning requires stable identities, isolation checks, smoke tests before production mapping, shared-route telemetry before unmapping, retained old app through soak and recovery after deletion/rename. Rollback distinguishes route traffic, revision-scoped settings, non-revision settings and irreversible external/data effects. Configuration/scaling and rolling/canary references require target version/capacity evidence and prohibit treating cancellation as rollback. Plans cannot claim readiness from prose or non-production evidence alone.

[verified] The bundle states public command/version facts while explicitly requiring bounded target evidence. The linked no-route documentation/test conflict is exposed rather than silently resolved. Public upstream correctness and target behavior are separate questions; the latter is not established by this audit's static evidence.

## Requirement-to-evidence coverage

| Risk | Evidence | Result |
|---|---|---|
| Autonomous invocation or deployment | Manual-only frontmatter; discovery fixture; body build fixture | [verified] Explicit boundary; body fixture deliberately does not test Skill activation |
| Approval blocking harmless planning | Body fixture exact-field classifications | [verified] Separates permissible draft from blocked readiness; model outcome unverified |
| Artifact creation misclassified as incident mitigation | Entrypoint, configuration reference, gate/fast-path/effects | [verified] Existing-droplet requirement and staging/full-gate boundary agree |
| Unsafe cutover/rollback assumption | All three bundled references | [verified] Failure phases and unreversed effects disclosed; rehearsal required |
| CLI/version-specific behavior | Command references and linked upstream sources | [unverified] Target CLI/CAPI/rehearsal evidence not supplied; public verification separately coordinated |

[verified] The legacy `pcf-deploy-requires-gate` scenario includes broad text/rubric criteria; it cannot prove deployment safety or actual target commands. Its `--dry-run`/`--no-start` examples are grader alternatives, not authority from the skill. The newer body fixture checks exact choices, no workspace changes, no commits and no Bash; these establish bounded decision/flow intent, not deployment execution or command semantics.

[sourced] Public verification supports [basic canary CLI/CAPI minimums](https://docs.cloudfoundry.org/devguide/deploy-apps/rolling-deploy.html), [instance-step gating](https://github.com/cloudfoundry/cli/blob/v8.19.0/command/v7/push_command.go#L541-L547), [separate revision/droplet retention](https://docs.cloudfoundry.org/devguide/revisions.html), [whole-app restart for memory/disk/log-rate scale flags](https://github.com/cloudfoundry/cli/blob/v8.19.0/command/v7/scale_command.go#L108-L150), and [single-stanza app-name override](https://github.com/cloudfoundry/cli/blob/v8.19.0/actor/v7pushaction/handle_app_name_override.go#L12-L32). Supplying resource flags triggers restart even if values are unchanged. The reference's disclosed no-route conflict remains qualified: CLI rejects simultaneous no-route/random-route flags, while public manifest prose says no-route does not unbind existing routes. [unverified] The exact first GA release of rollback was not established; implementation in 8.9.0 alone does not prove GA, and 8.10 notes do not settle it. No installed-target behavior was exercised.

[verified] Coordinator support reads: complete gate scenario and unapproved-planning-body scenario, adapter tests 505–535. The body fixture expressly excludes activation coverage and uses exact supplied-state decisions, no workspace changes, no commits and no Bash. The already-recorded deployment-job oracle defect remains in the [CI actions audit](ci-actions.md); no additional defect was established here.

## Read manifest and checks

[verified] Full canonical reads: `SKILL.md`, `references/blue-green-and-manifest.md`, `references/configuration-and-scaling.md`, `references/rolling-canary-and-revisions.md` (four files, 306 lines). Full supporting reads: production-change-gate entrypoint and incident-fast-path reference; pcf-ops state-changing-effects reference; stack-profile entrypoint; `evals/scenarios/pcf-deploy-requires-gate.yaml`, `evals/scenarios/discovery-manual-deploy-does-not-autofire.yaml`, `evals/build-scenarios/build-pcf-deploy-unapproved-planning-body.yaml`. Bounded reads: pcf-ops caller/effect inventory; `scripts/test_platform_adapters.py` 505–535; grader/test reference inventory. This is not a full read of pcf-ops, all production-gate references or the evaluator implementation.

[verified] `/home/hawkfire/save-toolkit/.venv/bin/python /tmp/audit_bundle_check.py` exited 0: all relative bundle links resolve, the three references equal their `.github/skills/pcf-deploy/` projections byte for byte, source diff against the target revision is empty. Entrypoint `diff -u` shows only namespaced-to-bare invocation and the generated explicit-only Copilot note; manual-only frontmatter is retained. Existing unchanged-source suite and adapter-gate evidence are reused; no redundant test run occurred.

[verified] Only this report changed for this item. No canonical/test/configuration fixes, installs, live model calls, target operations, commits, pushes or promotion occurred. No successful production deployment or live host assurance is claimed.
