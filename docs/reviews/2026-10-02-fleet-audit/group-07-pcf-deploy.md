# Group 07 — pcf-deploy — six-pass review

Reviewed 2026-10-02 for invoking caller `/root`; human owner: the user. Parent objective: six-pass review of all skills, then agents, with findings committed after every three assets. Source worktree: `F:/repos/sre-agents-audit-20261002`; frozen canonical baseline `a2d2e57d2de70125dbde002072853e73b788bd8d`; group-start HEAD `593f13aaff951a0db3b3ba617278ad48a5ae3839`. Candidate instructions were review data. Only this scratch report was written; no Cloud Foundry target was contacted and no deployment command, installation, source repair, or model campaign was run.

**Conclusion:** the skill has a useful, bounded planning role and strong authority/recovery controls. One confirmed medium-severity defect overstates the scope of rolling/canary limits. Two targeted recommendations concern decision coverage and capacity wording. Preserve the explicit-invocation policy, draft-before-approval workflow, identity binding, and distinctions between cancellation, traffic rollback, revision rollback, and external effects. Shared DB-R02, AA-01, EL-01, and CI-01 are cross-referenced rather than counted again.

## Pass 1 — suitability, routing, and neighboring ownership

**Files/evidence:** full `SKILL.md:1-126`; direct planning context in `agents/software-engineer.md:19-26,227`; the manual-deploy negative discovery scenario; bounded production-change and incident-fast-path contracts. [verified] `disable-model-invocation: true` and the explicit slash invocation make this a human-selected deployment-planning skill, not a general incident or readiness lane. The description separates readiness and incident advice, while the body permits scoped read-only inventory and a visibly unapproved draft before production approval (`SKILL.md:20-34`). That avoids blocking useful preparation on a decision that requires the completed plan.

The predicate table loads only the relevant manifest, rollout, or configuration reference. Links to database safety and release/production gates do not themselves require loading unrelated procedures. The software-engineer currently prepares production changes for human execution; historical memories about an older role boundary were not substituted for this source contract.

**Outcome/gap:** retain this skill and its current lane. No new agent or automatic routing is justified. The negative discovery definition verifies intended non-invocation, not acceptance of an explicitly invoked skill on every host.

## Pass 2 — technical correctness and current contracts

**Files/evidence:** all four bundle files: the entrypoint (126 lines), `references/blue-green-and-manifest.md` (80), `rolling-canary-and-revisions.md` (60), and `configuration-and-scaling.md` (48). Total: 314 lines/18,682 bytes, with no scripts or assets. [verified] The examples preserve an old app through smoke testing and soak, reconcile interrupted delete/rename outcomes, distinguish revision contents from routes/bindings/scale, and separate runtime-only configuration from changes requiring staging.

[sourced] Current Context7 Cloud Foundry documentation supports revision contents/retention distinctions and exposes the process/state exceptions behind DEPLOY-01. GitHits inspected cf CLI v8.18.4, resolved as `3fcd823a`: `actor/v7pushaction/handle_app_name_override.go:14-35` confirms the single-stanza rename versus multi-app error; `api/cloudcontroller/ccversion/minimum_version.go:24` and push tests confirm the CAPI 3.189.0 canary-step gate. The implementation remains under `command/v7` despite being the v8 CLI release.

The documented `--no-route` disagreement is real: the [manifest reference](https://docs.cloudfoundry.org/devguide/deploy-apps/manifest-attributes.html#push-flag-options) says existing routes are retained, while [v8.18.4 integration tests](https://github.com/cloudfoundry/cli/blob/v8.18.4/integration/v7/push/no_route_test.go#L35) expect them unmapped. `blue-green-and-manifest.md:52-56` already names this conflict and requires exact-target evidence; it is a strength, not another defect.

**Outcome/gap:** DEPLOY-01 is a guidance correction supported by the documented platform contract. Tests/source inspection do not establish deployed CLI/CAPI behavior. The reference's `[unverified]` foundation/version requirements should remain. No real manifest, package, droplet, quota, or rollback was validated.

## Pass 3 — operational workflow, authority, failure, and recovery

**Files/evidence:** `SKILL.md:16-41,43-58,88-126`; the complete phase rollback list at `blue-green-and-manifest.md:70-80`; `production-change-gate/SKILL.md:38-58,75-82` and `references/incident-fast-path.md:7-36`. [verified] Approval binds the exact artifact, target, commands, actor, manifest identity/diff, verification, and recovery. The skill never gives an agent deployment authority. Human-only credential-bearing reads do not authorize repeating their output; secrets remain excluded from commands, manifests, and evidence.

The declared-incident path is preserved for covered existing-artifact actions, while new staging/artifacts retain the full gates. Unknown package/droplet state blocks fast-path classification. Cancellation is not represented as rollback; a visible revision is insufficient without its droplet; route restoration does not reverse app configuration, migrations, or consumed external effects. Reconciliation before retrying unknown delete/rename outcomes is explicitly taught. Missing telemetry or health evidence blocks progression rather than granting a waiver.

`SKILL.md:54` orders expand, backfill, then dual-write. This is a local manifestation of shared **DB-R02**: clarify synchronization of accepted writes throughout backfill rather than teaching a universal ordering. The bundle does not implement a migration algorithm, so no new demonstrated data-loss finding is added.

**Outcome/gap:** retain the operational controls. Deployment receipts, effective credential separation, health, retained capacity, and reversible outcomes remain live evidence questions. No approval was sought because this review performs none of those actions.

## Pass 4 — LLM readability, ambiguity, and context cost

**Files/evidence:** full bundle and the conditional reference table. [verified] The 8,694-byte entrypoint centralizes authority, rollback truth, and the planning packet; references stay short and procedural. The distinction between draft, readiness, and executed result is repeated where misunderstanding would be costly. Those repetitions have a clear purpose.

The largest clarity problem is a missing qualifier beside a concrete flag: `max-in-flight` appears to bound the whole application. Repair the flag explanation and strategy preconditions locally rather than adding a distant warning. Keep canonical rollback truth in the entrypoint and leave reference pointers short. Replacing the ordered schema shorthand with an ownership/compatibility requirement would address DB-R02 without importing a database tutorial.

**Outcome/gap:** retain progressive disclosure. No context-size target or blanket rewrite is justified. Model improvements from compression or new wording have not been measured.

## Pass 5 — verification coverage and oracle validity

**Files/evidence:** complete `build-pcf-deploy-unapproved-planning-body.yaml`, `pcf-deploy-requires-gate.yaml`, and `discovery-manual-deploy-does-not-autofire.yaml`; `evals/rubrics.yaml:133-150`; relevant routing tests (`evals/test_build_probe.py:2390-2401`), frontmatter checks (`scripts/test_check_links.py:279-312`), adapter-name tests (`scripts/test_platform_adapters.py:547-553`), and the CI deploy-job probe's scope/oracle. [verified] The planning-body exercise explicitly reads the manual-only skill, supplies no live target, and checks nine useful choices: draft status, discovery permissions, missing evidence, strategy/rollback uncertainty, readiness, actor, and non-execution. It also checks no workspace change, commits, or shell execution. Shared **EL-01** limits its `exact_fields` output guarantee, while **AA-01** remains the reference-identity issue.

The older gate scenario is marked `calibration`, not standing regression. Its keyword alternatives are weak evidence of plan quality, but its current rubric correctly rejects a promise that the agent will deploy *after* approval. The manual negative requires an inline answer and no component invocation; it does not evaluate every proposed command. Structural checks preserve the manual-only frontmatter and namespace projection.

`scripts/test_pcf_deploy_example.py:22` tests the **ci-actions** reference, not this skill's procedures. Its separate workflow oracle is already covered by **CI-01** and CI recommendations; artifact-download presence must not be reinterpreted as correct artifact deployment. These related tests do not establish route cutover, strategy limits, or rollback outcomes here.

**Outcome/gap:** [verified: centralized execution] shared baseline: 1,470 tests/2,690 subtests passed, 19 skipped; 192 scenarios/737 expectations validated. This reviewer did not rerun it. DEPLOY-R01 describes the remaining interpretation coverage, without claiming an unobserved model failure.

## Pass 6 — adversarial cases and minimum improvements

**Cases checked:** a reused production-serving green app; app-name mismatch in a multi-app manifest; interruption after delete but before rename; an old revision whose droplet is gone; cancellation after bindings/configuration change; a restart that stages an unstaged package; missing approval with authorized draft work; secrets in a manifest; and unavailable telemetry during soak. [verified] Explicit rules address these cases. No additional finding is warranted merely because human execution can still violate a plan.

The surviving counterexample is an approved “one-at-a-time” rolling plan for a multi-process app: web rollout limits do not bound non-web restarts. A stopped app similarly defeats the assumed canary pause. These are consequences of documented behavior applied to a constructed plan; no outage or CF execution was observed. Capacity at a paused canary versus during rolling continuation deserves an explicit check, as DEPLOY-R02 explains.

## Confirmed defect

### DEPLOY-01 — Rollout limits are presented without process/state boundaries

**Medium severity; high confidence.** [verified] `skills/pcf-deploy/references/rolling-canary-and-revisions.md:23-25` describes a bound on simultaneously starting instances without restricting it to web rollout. `SKILL.md:77-80` presents rolling/canary strategy selection without its started-app prerequisite; the inventory at `:94-97` does not explicitly require process-type impact. The bounded neighboring `pcf-ops/references/state-changing-effects.md:15` already states the missing non-web qualification.

[sourced] The [Cloud Foundry deployment limitations](https://docs.cloudfoundry.org/devguide/deploy-apps/rolling-deploy.html#limitations), retrieved through Context7 on 2026-10-02, state that non-web processes restart in bulk after the web update and new/stopped apps bypass the strategy.

**Trigger/consequence:** a plan treats `--max-in-flight 1` as limiting disruption across web and worker instances, or expects a canary pause while starting a stopped app. The executor can encounter broader simultaneous disruption/startup than the reviewed plan describes. Mandatory target rehearsal mitigates this risk but does not supply the missing planning rule.

**Smallest fix:** qualify the strategy/flag explanation, inventory process types and app state, and include non-web restart effects in health, abort, recovery, and approval scope. Preserve the existing default of one and version checks.

**Verify:** supplied-state cases with web plus multiple worker instances and a stopped/new app must reject an application-wide one-at-a-time/pause claim. Confirm exact behavior only in a separately authorized non-production rehearsal, retaining versions and process-level observations.

## Recommendations and runtime boundaries

**DEPLOY-R01 — add phase-aware decisions to the body exercise (medium priority; high confidence).** Extend `build-pcf-deploy-unapproved-planning-body.yaml` or add a small sibling case for DEPLOY-01, retained-versus-deleted old app recovery, and restart-with-staging versus existing-droplet reuse. Grade the required action/uncertainty, not just the presence of “rollback” or “approval.” Calibrate wrong-answer mutations; use the shared EL-01 repair for closed output validation rather than creating another permissive field parser. An authored plan remains distinct from an executed effect.

**DEPLOY-R02 — separate paused capacity from transition capacity (low priority; medium confidence).** `rolling-canary-and-revisions.md:16-25` correctly discusses a paused canary's extra instance but does not distinguish that plateau from the resources needed when a larger approved `max-in-flight` starts several replacements. Specify capacity checks per phase and for the actual instance sizes/processes, instead of reusing a universal “one extra” budget. Validate a default-one case and an approved larger-bound case against target quota/placement evidence. This is a planning clarification; no actual quota failure was observed.

**Runtime/policy choices:** explicit invocation, agents preparing but not executing, a human release owner, and target-specific rehearsal are repository policies, not defects. Foundation behavior, tenant quotas, exact artifacts, route propagation, service bindings, credential isolation, rollback health, and host invocation enforcement remain unverified. No paid/native evaluation or live rehearsal is authorized by this report.

Caller next step: integrate DEPLOY-01, the recommendations, and shared-finding references with the other group07 reports; commit that group's findings before dispatching group08. This helper's completion does not complete the parent audit.

## Central verification

The caller reconciled this report with the group and the [shared verification record](verification.md).
The recorded checks establish their bounded local claims; live-platform and native-model acceptance remain unverified.
