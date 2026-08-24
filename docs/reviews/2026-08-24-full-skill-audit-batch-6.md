# Full skill audit — Batch 6 of 6

Date: 2026-08-24

Scope: `merge-gate`, `release-gate`, `production-change-gate`, `pcf-deploy`,
`service-onboarding`

Baseline commit ID: `2eff57c95089da2d38f4d2be5a3738f599b3daff`

Method: Baseline → Inspect → Research → Change → Validate → Compare

## Executive conclusion

These five skills form one release path with deliberately separate decisions: merge quality,
release readiness, production authorization, human-executed PCF deployment, and approved service
onboarding. The topology is sound. The gate skills consume recorded evidence rather than invoking
one another, `pcf-deploy` remains manual-only and recommend-only, and `service-onboarding` remains
an explicit workflow rather than a readiness-audit shortcut.

The audit found seven execution-relevant defects:

1. `merge-gate` blocked a P2 only when the change touched the same lines. That misses a
   candidate-introduced or worsened cross-file/behavioral defect and can wrongly block an unrelated
   pre-existing issue.
2. `merge-gate` treated size alone, with an unsupported approximate line threshold, as a blocking
   finding. The real decision is whether mixed concerns or volume prevent reliable review without
   destroying an atomic safe change.
3. `pcf-deploy` attributed canary and instance-step support to inaccurate CLI release milestones
   and described removal of old instances once per step rather than once per additional canary
   instance.
4. `service-onboarding` assumed every workload uses PCF manifests, HTTP health checks, at least two
   instances, Loki/Mimir/Tempo, request burn-rate alerts, and saturation alerts. Those assumptions
   contradict the approved PCF-to-GCP migration, override Cloud Run's valid scale-to-zero default,
   and fail for scheduled/asynchronous workloads.
5. The Tier 2 example called scale-down an exact inverse with no state carried. It restores desired
   count but cannot reverse in-flight requests, external effects, or transient rebalancing.
6. The incident reference's final authority sentence grouped Tier 3 with the covered Tier 2 fast
   path even though the body correctly excludes Tier 3.
7. The release verdict collapsed the source commit ID and artifact identity into one field, while
   the production verdict recorded neither explicitly. A PASS/APPROVED record could therefore lose
   the source-to-artifact binding required by both checklists.

All seven are corrected with focused regressions. Source candidates now use the user-requested term
“commit ID” consistently in all four affected gate surfaces. Artifact checksums and immutable
artifact identities remain separate concepts. No skill description, agent, delegation edge,
production authority, dependency, schema, or generated projection changed in this batch.

## Method and evidence

### Local baseline

- `[verified]` The baseline contains 30 canonical skill entrypoints. The five Batch 6 bundles contain
  11 tracked files totaling 41,830 Git blob bytes: five entrypoints, five references, and one
  manifest starter asset.
- `[verified]` Every file in all five bundles was inspected in full. Every reference and asset is
  reachable from its owning `SKILL.md`; no generated projection was treated as a source.
- `[verified]` The gate topology is locally consistent: merge readiness precedes release readiness;
  production authorization is a separate later decision; the deployment skill consumes those
  records and never grants itself live authority.
- `[verified]` Before correction, 10 assertions failed across the focused release-contract suite:
  four commit-identity surfaces plus P2 scope, review-size criteria, runtime-aware onboarding,
  canary prerequisites/semantics, rollback limits, and Tier 3 fast-path scope.
- `[verified]` Existing evals include positive and negative direct cases for all three gates, a
  direct unauthorized-PCF-deployment case, positive merge discovery, and negative manual-only
  discovery for `pcf-deploy` and `service-onboarding`.
- `[verified]` `docs/fleet-roadmap.md` was treated as the only live backlog. Historical release and
  onboarding documents were evidence only and did not authorize additional work.

### Current primary documentation via Context7

Context7 established documented contracts and remained separate from private-checkout inspection:

- `[sourced]` Cloud Foundry documents canary deployment as requiring cf CLI v8.8.0 or later and
  CAPI v3.173.0 or later. Instance-step values are successive percentages/weights; the deployment
  pauses at each step, and continuing after the final step completes rolling deployment:
  [rolling and canary deployments](https://docs.cloudfoundry.org/devguide/deploy-apps/rolling-deploy.html).
- `[sourced]` The same Cloud Foundry guide says one old instance is removed for each additional
  canary instance created after the first. A step may add multiple instances, so “one removal per
  step” is not equivalent.
- `[sourced]` Cloud Foundry application revisions retain code/start command/environment state but
  not routes, service bindings, scale, data, or external effects. Rollback creates a new current
  revision rather than rewinding history:
  [application revisions](https://docs.cloudfoundry.org/devguide/revisions.html).
- `[sourced]` GitHub immutable releases prevent modification/deletion of the release tag and assets
  after publication and generate attestations. Repository rulesets separately constrain tag update
  and deletion:
  [immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases)
  and [repository rules](https://docs.github.com/en/rest/repos/rules).
- `[sourced]` GitHub protected environments can require reviewers before a job accesses environment
  secrets. That supports the local distinction between repository review and the production
  credential boundary:
  [deployment environments](https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments).

### Current upstream implementation and adoption evidence via GitHits

GitHits was used for public source and real implementation evidence; it did not inspect the private
checkout:

- `[sourced]` Current `cloudfoundry/cli` source exposes rolling/canary flags including
  `--instance-steps` and `--max-in-flight`. Its instance-step capability check names CAPI 3.189.0 as
  the minimum, which is why the target API version remains a required gate rather than inferring
  support from CLI version alone:
  [cloudfoundry/cli](https://github.com/cloudfoundry/cli).
- `[sourced]` Current CLI manifest handling accepts an explicit app-name override for a single-app
  manifest and rejects an absent selected app in a multi-app manifest. That supports keeping the
  existing “show the resolved manifest/app” rule:
  [cloudfoundry/cli command source](https://github.com/cloudfoundry/cli/tree/main/command/v8).
- `[sourced]` Current `cloud_controller_ng` source models a revision with droplet, start command,
  and environment state and defaults the revision-retention ceiling to 100:
  [cloudfoundry/cloud_controller_ng](https://github.com/cloudfoundry/cloud_controller_ng).
- `[sourced]` Current Cloud Controller source and the public operations guide do not expose one
  universal staged-droplet retention value: the guide documents five while current source contains
  a different configurable default. The skill therefore keeps target retention `[unverified]` and
  requires confirmation of the actual rollback artifact rather than relying on either upstream
  number.

### Current official vendor documentation

- `[sourced]` Cloud Run service-level and revision-level minimum instances default to zero. A
  configured minimum is an optional latency/high-availability/cost trade-off rather than a universal
  onboarding prerequisite; even a configured minimum remains best effort:
  [Cloud Run minimum instances](https://docs.cloud.google.com/run/docs/configuring/min-instances).

### Provenance boundaries and disagreements retained

- Context7/official documentation establishes the supported behavior; GitHits current source
  establishes implementation floors and configurable defaults. Neither proves what a target PCF
  foundation has enabled.
- The public revisions guide says five staged droplets, while current upstream Cloud Controller
  configuration exposes a different default. The operational conclusion does not depend on picking
  a winner: the human release owner must prove that the intended droplet still exists.
- GitHub immutable-release settings and tag rulesets are repository controls. They support artifact
  immutability but do not grant production credentials or constitute production authorization.
- A documented CLI/API capability is not target adoption. The exact target API version,
  `cf push --help`, quota, and bounded non-production result remain required evidence.

---

## Skill: merge-gate

### Overall Assessment

**Significant Changes**

### Purpose

Decides whether a specific pull-request head is fit to merge based on trusted CI, regression
evidence, current findings, affected security/compatibility surfaces, scope, and operational docs.

### Findings

- **Routing:** The description cleanly owns “ready to merge” and names `release-gate` and
  `production-change-gate` as later decisions. Positive discovery and direct pass/block scenarios
  cover the principal boundary. No routing edit was needed.
- **Instructions:** The checklist is concise and correctly makes missing trusted CI a blocker. The
  former P2 rule used line overlap as a proxy for candidate responsibility; the corrected rule
  evaluates introduced/worsened behavior and material overlap.
- **Accuracy:** Exact lines are not the semantic unit of a correctness defect. A caller change can
  expose a defect in another file, and an unrelated pre-existing issue does not become candidate
  work merely because review discovered it. The new rubric reflects that causal distinction.
- **Context:** One entrypoint contains the full decision; no reference is needed. The gate avoids
  pulling in review or release procedures and consumes recorded evidence instead.
- **References / Assets / Scripts:** No supporting resource is needed. The focused release-contract
  test is repository-level regression coverage, not runtime skill context.
- **Tools:** Trusted CI and current-diff inspection are read-only evidence operations. The skill does
  not merge, approve, rerun production work, or infer a result from a reviewer packet.
- **Orchestration:** Review supplies findings when requested; the gate owns disposition and merge
  readiness. Release readiness and production exact-candidate review remain later boundaries.
- **Failure Handling:** Stale CI, untested behavior, unresolved current P0/P1, affected security
  risk, secrets, incompatible contracts, unreviewable scope, and missing operational updates fail
  closed. Size now blocks only when reliable review/safety evidence cannot be established.
- **Verification:** The focused regression rejects line-only P2 scope, an arbitrary size-only block,
  and the retired source-candidate terminology. Named in-memory mutants prove each oracle changes state.
- **Portability:** CI evidence, candidate causality, atomic review scope, and severity disposition
  are portable. The local `Protect main` configuration and typed handoff names are repository-specific.

### Routing Tests

#### Should trigger

1. “The review is complete and CI is green; is this pull request ready to merge?”
2. “Run the merge gate against the exact PR-head commit ID and list every blocker.”
3. “Can I merge this fix if its regression ran on the prior commit?”

#### Should not trigger

1. “Is this already-built artifact ready to deploy?” — `release-gate` owns ship readiness.
2. “Authorize this route remap in production” — `production-change-gate` owns live authorization.
3. “Review this diff for correctness and security” — `reviewer` owns finding discovery.

#### Boundary cases

1. “A P2 was found in an untouched helper called by the changed endpoint” — this gate decides
   whether the candidate introduced/worsened it or materially overlaps its behavior; line identity
   alone is not the test.
2. “This atomic migration is large” — request a split only if reliable review cannot be achieved;
   do not mechanically divide a smallest independently safe change.

### Recommended Changes

#### Change 1 — make P2 blocking candidate-causal and behavior-aware

- **Problem:** The former same-lines rule missed cross-file candidate defects and could misclassify
  unrelated pre-existing work.
- **Evidence:** Local reviewer policy excludes pre-existing issues unless the candidate worsens them;
  code behavior crosses file and line boundaries.
- **Change:** Block P2 findings introduced/worsened by the candidate or materially overlapping its
  changed behavior; link unrelated pre-existing P2 findings for follow-up.
- **Expected improvement:** Correct blocker ownership without hiding candidate-caused defects behind
  a textual-diff boundary.
- **Risk/tradeoff:** “Material overlap” requires judgment; the verdict must state the evidence so a
  human can challenge it.

#### Change 2 — replace the arbitrary size threshold with reviewability evidence

- **Problem:** The skill allowed a split solely for size and asserted an unsourced approximate line
  threshold as a universal defect-detection boundary.
- **Evidence:** No repository source established that number, and mechanical splits can make an
  atomic compatibility or migration change less safe.
- **Change:** Tie a blocking split request to mixed concerns or volume materially preventing reliable
  review, preserve the smallest independently safe unit, and name the split/evidence that clears it.
- **Expected improvement:** Smaller changes remain preferred without turning line count into a false
  safety guarantee.
- **Risk/tradeoff:** Review effort is less mechanically measurable; explicit clearance criteria make
  the decision auditable.

#### Change 3 — use commit ID for source identity

- **Problem:** Source candidates were labelled with lower-level hash terminology that the user does
  not want in the workflow output.
- **Evidence:** Git identifies the candidate by a commit ID; artifact digests are separate evidence.
- **Change:** Use “commit ID” in CI evidence, staleness checks, verdicts, and exact-candidate notes.
- **Expected improvement:** One consistent operator-facing term without weakening immutability.
- **Risk/tradeoff:** None, provided the recorded ID remains the full exact identifier where required.

### Keep As-Is

Keep the trusted-CI requirement, red-first regression evidence, current-finding disposition,
affected-surface security test, compatibility checks, secret scan, documentation handoff, waiver
record, and separation from production exact-candidate review.

---

## Skill: release-gate

### Overall Assessment

**Significant Changes**

### Purpose

Decides whether an immutable build is ready to ship to a named environment, independently of the
later decision about who is authorized to apply it to production.

### Findings

- **Routing:** “Ready to ship” is distinct from “ready to merge” and “authorized to act on prod.”
  Direct pass/block evals cover rollback presence and a complete packet. No routing edit was needed.
- **Instructions:** The checklist consumes a recorded merge result, verifies one promoted artifact,
  migration/flag safety, rollback, monitoring/abort criteria, and communications. It does not rerun
  a sibling gate. The verdict now records source and artifact identities in separate required fields.
- **Accuracy:** Current GitHub documentation supports the immutable-release endpoint and the
  post-publication tag/asset guarantee. Tag rulesets are a separate stricter local control and are
  correctly evaluated independently.
- **Context:** The single entrypoint holds a bounded readiness decision. It avoids loading CI,
  deployment, or production-authorization procedures.
- **References / Assets / Scripts:** No reference is needed; the repository API commands are short
  and decision-specific. A script would obscure current repository state and add no safety.
- **Tools:** `gh api` calls inspect settings/rulesets; they do not publish a release or change a rule.
  Equivalent non-GitHub distribution paths can prove immutable identity without GitHub controls.
- **Orchestration:** `merge-gate` supplies prior evidence, `observability-engineer` supplies coverage,
  and `production-change-gate` later consumes the exact candidate/target readiness record.
- **Failure Handling:** Missing merge evidence, rebuilt artifacts, mutable distribution identity,
  a missing source-to-artifact binding, unsafe migrations/flags, unproven rollback, missing abort
  criteria, or missing comms block. API absence is not silently converted into enabled controls.
- **Verification:** The focused regression requires “commit ID” in the merge-evidence and verdict
  surfaces and separately requires both verdict identities. Existing direct evals retain one pass
  and one no-rollback block case.
- **Portability:** Build-once/promote, immutable identity, reversible migrations, abort criteria, and
  readiness/authorization separation are portable. GitHub release APIs and tag rulesets are specific.

### Routing Tests

#### Should trigger

1. “The merge gate passed; is artifact 2.4.1 ready to ship to production?”
2. “Run the release gate and prove the tested artifact is the one being promoted.”
3. “Can we release if the migration passes forward but the rollback has not been rehearsed?”

#### Should not trigger

1. “Can this pull request merge?” — `merge-gate` owns merge quality.
2. “May I execute this production command?” — `production-change-gate` owns authorization.
3. “Deploy the PCF application now” — `pcf-deploy` prepares a human-run deployment plan.

#### Boundary cases

1. “GitHub immutable releases are enabled, so production is approved” — this gate can accept the
   artifact evidence but cannot grant production authority.
2. “The artifact is stored outside GitHub” — require the distribution system's equivalent immutable
   digest or non-replaceable version identity; do not impose GitHub-specific controls.

### Recommended Changes

#### Change 1 — preserve distinct source and artifact identities

- **Problem:** The source label was inconsistent and the verdict collapsed source commit ID and
  immutable artifact into one ambiguous slot.
- **Evidence:** The checklist requires an exact candidate plus the exact lower-environment artifact;
  either identity alone is insufficient to prove build-once/promote.
- **Change:** Use “commit ID” for source state and add a separate artifact identity/digest field.
- **Expected improvement:** The release record preserves the exact source-to-built-bytes binding for
  later production authorization.
- **Risk/tradeoff:** Packets gain one line; non-Git distribution paths still use their native
  immutable object/version identity.

### Keep As-Is

Keep the one-artifact promotion rule, GitHub/non-GitHub distribution branches, migration and flag
safety, evidenced rollback, monitoring and abort criteria, human ownership, and the explicit
readiness-versus-authorization boundary.

---

## Skill: production-change-gate

### Overall Assessment

**Significant Changes**

### Purpose

Records whether one exact production-facing action is authorized, who may execute it, its target and
blast radius, and how it will be verified and backed out.

### Findings

- **Routing:** The description owns production authorization and names both earlier gates as
  non-owning predecessors. Four direct scenarios exercise missing approval, incomplete evidence,
  missing execution authority, and a complete packet. No routing edit was needed.
- **Instructions:** Classification comes first; Tier 2/3 stays human/protected-automation executed;
  every approval is exact-target/exact-action; the checklist distinguishes deployment credentials
  from other least-privilege live roles. Deployment verdicts now retain the exact source, artifact,
  and release-readiness record rather than relying on an implicit attachment.
- **Accuracy:** Repository review is not production authorization. Protected environments can gate
  deployment secrets, while non-deployment actions require their own least-privilege executor
  evidence. The local model is technically coherent.
- **Context:** The main checklist holds planned-change requirements. The incident fast path and
  worked example are conditional references and are not loaded for ordinary packets.
- **References / Assets / Scripts:** The fast path isolates incident exceptions; the example teaches
  packet shape. The example's rollback claim was over-absolute and is now bounded to desired count.
- **Tools:** The skill may inspect evidence and prepare commands/diffs, but it never executes a live
  action. The sole dashboard exception remains owned by the named agent procedure.
- **Orchestration:** Release readiness is consumed, not rerun. The human release owner or separately
  approved automation executes; incident command can approve a bounded reversible envelope.
- **Failure Handling:** Missing classification, exact approval, execution-boundary proof, blast
  radius, reversible backout, disclosed diff, timing, watcher, abort criteria, or comms blocks.
  Tier 3 and new artifacts cannot use the incident fast path.
- **Verification:** The regression requires separate source/artifact/readiness verdict fields and
  rejects the retired source term, rollback claims that erase external effects, and any later
  sentence that re-admits Tier 3 to the fast path.
- **Portability:** Exact action/target, tiering, executor separation, backout, and observed abort
  criteria are portable. Protected environments, Remedy/Jira, and the dashboard exception are local.

### Routing Tests

#### Should trigger

1. “Authorize this exact `cf map-route` command against the production space.”
2. “Can the approved automation deploy this exact artifact to prod?”
3. “Review this rollback plan during the declared incident and classify its tier.”

#### Should not trigger

1. “Is the build ready to ship?” — `release-gate` owns readiness.
2. “Investigate why production latency increased” — `sre` owns active incident triage.
3. “Create this Grafana dashboard under the documented write rule” — the named dashboard exception
   stays with `observability-engineer`/`obs-dashboards`.

#### Boundary cases

1. “Roll back to the immediately previous live artifact during a P1” — the bounded fast path can
   cover it; shipping newly built bytes cannot.
2. “Delete corrupt production data to recover service” — Tier 3 remains on the full gate even during
   an incident; urgency does not make an irreversible action reversible.

### Recommended Changes

#### Change 1 — bound the Tier 2 rollback example

- **Problem:** Scaling 6→4 was described as an exact inverse carrying no state.
- **Evidence:** Desired instance count can be restored, but requests, emitted side effects, and
  transient load/rebalancing that occurred while scaled out cannot be undone by `cf scale`.
- **Change:** Say the command restores desired count and list the material effects it does not reverse.
- **Expected improvement:** Models stop treating configuration inversion as full system-state reversal.
- **Risk/tradeoff:** The example is slightly longer but remains immediately executable as packet shape.

#### Change 2 — align the incident authority summary with its scope

- **Problem:** The final sentence said Tier 2/3 execution remained on the fast path despite the
  reference explicitly excluding Tier 3 above.
- **Evidence:** The parent checklist and reference scope both keep every destructive/access-path
  action on the full gate.
- **Change:** Name covered Tier 2 execution and state that Tier 3 remains on the full gate.
- **Expected improvement:** Prevents the closing summary from overriding the load-bearing scope rule.
- **Risk/tradeoff:** None.

#### Change 3 — use commit ID for exact source review

- **Problem:** New-artifact review and the incident hotfix branch used a different label from the
  requested source-identity terminology.
- **Evidence:** Both refer to the exact source commit, not an artifact checksum.
- **Change:** Use “exact candidate commit ID” in the parent and fast-path reference.
- **Expected improvement:** One unambiguous term across the release chain.
- **Risk/tradeoff:** None; artifact identity remains separately required.

#### Change 4 — retain the source-to-artifact binding in authorization

- **Problem:** The production verdict did not explicitly record either identity even though its
  readiness checklist required both.
- **Evidence:** An attached packet can be dropped or replaced in transit; the authorization record
  must remain self-identifying for the exact candidate and artifact it approves.
- **Change:** Add separate candidate commit ID, immutable artifact identity, and release-readiness
  record fields, each allowing explicit not-applicable only for a non-deployment action.
- **Expected improvement:** An APPROVED record cannot silently authorize different bytes or lose the
  evidence chain it consumed.
- **Risk/tradeoff:** The verdict is three lines longer; the explicit fields materially reduce ambiguity.

### Keep As-Is

Keep classification-first behavior, human/protected-automation execution, exact approval scope,
production credential evidence, dashboard-only exception, rollback preference, declared-incident
envelope, new-artifact/Tier-3 exclusions, post-incident reconciliation, and typed scribe handoff.

---

## Skill: pcf-deploy

### Overall Assessment

**Significant Changes**

### Purpose

Builds an evidence-bound, human-executed PCF/TAS deployment plan with exact target, resolved
manifest, strategy, gates, rollback, observation, and post-change evidence.

### Findings

- **Routing:** The skill is explicitly manual-only and owns deployment planning/execution support,
  not app investigation or production authorization. Negative discovery and direct no-gate cases
  cover its highest-risk boundary. No routing edit was needed.
- **Instructions:** Target first, inspect before push, pin the artifact, choose one strategy, show the
  manifest diff, consume gate records, and hand exact commands to the human executor is an effective
  sequence.
- **Accuracy:** Official docs place canary support at CLI 8.8+/CAPI 3.173+. Current CLI source adds
  a CAPI 3.189 floor for instance steps. Old instances are removed per additional canary instance,
  not once per step. Those defects are corrected.
- **Context:** The entrypoint holds common authority and evidence requirements. Blue-green/manifest,
  rolling/revisions, and configuration/scaling details load only for matching plans.
- **References / Assets / Scripts:** Three references are meaningfully distinct. The manifest asset
  is loaded only when no project-owned starter exists and is explicitly not a production default.
- **Tools:** `cf` reads and help/version checks establish target state and capability. All pushes,
  route changes, rollback, scale, and config mutation remain human-executed after authorization.
- **Orchestration:** `release-gate` supplies ship readiness; `production-change-gate` supplies exact
  production authorization; `pcf-ops` owns diagnosis; the release owner executes and records results.
- **Failure Handling:** Wrong target, unresolved manifest app, changed variables/services/routes,
  insufficient quota, unsupported strategy flags, unhealthy new instances, stale rollback droplets,
  non-revision state, and failed abort signals have explicit stop/backout treatment.
- **Verification:** The regression requires both documented canary floors, the current instance-step
  API floor, per-instance removal semantics, and rejection of the former release-arrival claims.
  Target support remains `[unverified]` until the human packet supplies live evidence.
- **Portability:** Build-once/promote, explicit target, bounded rollout, rollback-state inventory, and
  observed abort criteria are portable. cf commands, manifests, routes, revisions, and quota are PCF-specific.

### Routing Tests

#### Should trigger

1. “Prepare the exact human-run PCF blue-green deployment and route-cutover plan.”
2. “Plan a canary with instance steps and prove the target CLI/API supports every flag.”
3. “Resolve this manifest against the selected app and show the production diff before approval.”

#### Should not trigger

1. “The PCF app is crashing; find the cause” — `pcf-ops` owns runtime investigation.
2. “Is the artifact ready to ship?” — `release-gate` owns release readiness.
3. “Deploy now without approval” — the skill refuses; a human executes only after the required gates.

#### Boundary cases

1. “Rollback with `cf rollback`” — this skill can prepare it only after proving the droplet exists
   and enumerating routes, bindings, scale, data, and external state the revision does not restore.
2. “Use the bundled manifest” — only when no project-owned manifest/starter exists; all placeholders
   remain decisions and require an approved diff.

### Recommended Changes

#### Change 1 — replace inaccurate version-arrival claims with capability floors

- **Problem:** The reference said canary arrived in CLI 8.10 and instance-step flags in CLI 8.16,
  which does not match the current documented contract and hides the target CAPI floor.
- **Evidence:** Cloud Foundry's current guide states CLI 8.8+/CAPI 3.173+ for canary; current CLI
  source checks CAPI 3.189+ for instance steps.
- **Change:** State those prerequisites, require `cf push --help`, record exact CLI/API versions, and
  retain a bounded non-production result.
- **Expected improvement:** Prevents approving a syntactically known flag against an API that cannot
  execute it.
- **Risk/tradeoff:** Future CLI/API releases may change floors; target help/version evidence remains
  the durable gate.

#### Change 2 — describe canary replacement per instance, not per step

- **Problem:** A step can create multiple canary instances, so “one old instance per later step”
  understates replacement and can mislead capacity/blast-radius planning.
- **Evidence:** Current Cloud Foundry documentation specifies one removal for each additional canary
  instance after the first.
- **Change:** State the per-instance rule and explicitly note that one step may remove several old
  instances while the deployment retains one extra instance above target.
- **Expected improvement:** Correct capacity, mixed-version population, and observation planning.
- **Risk/tradeoff:** Percent rounding and target-specific behavior still require a bounded rehearsal.

### Keep As-Is

Keep manual-only invocation, target pinning, inspect-before-push, immutable artifact promotion,
strategy choice, no-start exception, health/route cutover checks, configuration versus revision
rollback split, credential-read denials, human execution, and exact post-change evidence.

---

## Skill: service-onboarding

### Overall Assessment

**Significant Changes**

### Purpose

Coordinates an already-approved new or changed service into its runtime, telemetry, dashboard,
alert, SLO, delivery, runbook, and evidence-bound knowledge model without granting production authority.

### Findings

- **Routing:** The skill is manual-only and explicitly distinguishes effect-shaped onboarding from
  read-only `service-readiness-audit`. Its negative discovery scenario verifies that it does not
  auto-fire. No routing edit was needed.
- **Instructions:** The ordered checklist and explicit skipped-step reporting are strong. It listed
  `stack-profile` as a dependency but did not load it before the first PCF-specific assumption; that
  ordering is corrected.
- **Accuracy:** A Cloud Run service does not use a PCF `manifest.yml`; its minimum instances default
  to zero and scale-to-zero can be an intentional cost/traffic choice. A scheduled job may have no
  HTTP health endpoint or request SLI. Redundancy, signals, and alert classes depend on workload and
  runtime; backend destinations also vary during the approved migration.
- **Context:** One compact checklist is appropriate, but it must select runtime/workload branches
  before loading the detailed observability/deployment skills. The revision avoids enumerating every
  platform by delegating selection to `stack-profile` and `obs-pipeline`.
- **References / Assets / Scripts:** No local reference or script is justified. The named dependent
  skills are executable conditional loads and authoritative service/alert definitions remain inputs.
- **Tools:** Onboarding consumes approved plans and proof from authoritative systems. It prohibits
  credential-bearing reads and does not execute deployment or author knowledge records itself.
- **Orchestration:** `stack-profile` supplies platform facts; observability skills own signal-specific
  design; `ci-actions` owns delivery; `runbook` owns operating docs; `scribe` owns approved knowledge;
  `production-change-gate` owns any live authorization.
- **Failure Handling:** Missing approval/owner/definitions, unavailable runtime spec, absent health or
  success evidence, telemetry non-arrival, unowned alerts, missing runbooks, production authorization,
  and incomplete authoritative evidence remain explicit gaps rather than silently completed steps.
- **Verification:** The block-bound regression requires pre-step stack loading, PCF/Cloud Run
  deployment-spec branches, workload-appropriate success/availability, optional minimum instances
  with preserved scale-to-zero, stack-selected telemetry destinations, request/scheduled alert
  branches, and conditional saturation.
- **Portability:** Approved-plan inputs, health/success contracts, SLI-derived alerts, evidence-bound
  handoffs, and explicit skips are portable. PCF manifests, Cloud Run configuration, Grafana, and
  named internal skills/backends are local choices.

### Routing Tests

#### Should trigger

1. “Onboard this approved Cloud Run service into telemetry, alerts, SLOs, and operational knowledge.”
2. “Complete service onboarding for this PCF app and return every completed/skipped step.”
3. “Register this approved scheduled workload with success telemetry, freshness alerts, and a runbook.”

#### Should not trigger

1. “Audit whether this existing service is ready” — `service-readiness-audit` owns the read-only review.
2. “The new service is failing in production now” — `sre` owns active incident response.
3. “Write the service card from approved evidence” — `scribe` owns the knowledge artifact.

#### Boundary cases

1. “The service plan is approved but production authorization is missing” — complete preparatory
   steps and record the live step blocked; onboarding grants no permission.
2. “The workload has no request traffic” — use its success/failure/freshness SLI and alerts rather
   than manufacturing HTTP RED or burn-rate requirements.

### Recommended Changes

#### Change 1 — select the runtime before defining deployment and health

- **Problem:** Step 1 hardcoded a PCF manifest, HTTP health endpoint, and two-instance minimum before
  loading the canonical platform profile.
- **Evidence:** The approved GCP migration is in progress; Cloud Run uses service configuration/IaC,
  and job/worker health differs from a user-serving HTTP app.
- **Change:** Load `stack-profile` first; require a runtime-appropriate version-controlled deploy
  spec, workload-appropriate health/readiness/success check, and a justified availability/instance
  target. Configure minimum instances only when the approved SLO, latency, or availability plan
  requires them; otherwise preserve scale-to-zero where the runtime supports it.
- **Expected improvement:** The same checklist executes reliably across current PCF, Cloud Run, and
  non-request workloads without weakening health proof.
- **Risk/tradeoff:** Runtime details move to the canonical profile/deployment lane, so those inputs
  must be available before onboarding starts.

#### Change 2 — derive telemetry and alerts from the selected stack and SLI

- **Problem:** The checklist hardcoded Loki/Mimir/Tempo, RED, burn rate, and saturation for every service.
- **Evidence:** Migration-scoped Google backends are allowed, and scheduled/asynchronous workloads
  commonly require completion/freshness/failure signals rather than request-rate/error/duration.
- **Change:** Select destinations through `stack-profile`/`obs-pipeline`; require RED only for
  request-based services, workload-appropriate success signals otherwise, SLI-derived alert type,
  and saturation only when a meaningful saturation signal exists.
- **Expected improvement:** Onboarding produces actionable coverage instead of synthetic or
  impossible requirements.
- **Risk/tradeoff:** The checklist no longer supplies one uniform dashboard/alert template; the
  chosen SLI and authoritative definitions must carry the workload semantics.

#### Change 3 — use the exact repository commit ID in handoffs

- **Problem:** The input and closeout packet used generic “revision” while the release path now uses
  the user-requested source identity term.
- **Evidence:** The handoff must bind definitions and approval evidence to one exact repository state.
- **Change:** Require the exact repository commit ID at entry and in the scribe packet.
- **Expected improvement:** Consistent, unambiguous evidence across onboarding and release workflows.
- **Risk/tradeoff:** None; non-Git artifact identity remains a separate field where applicable.

### Keep As-Is

Keep explicit/manual invocation, approved-plan prerequisite, sanitized evidence rule, prohibited
credential reads, dependency loading, completed/skipped accounting, production-gate re-entry,
authoritative-definition requirement, scribe ownership, retained trust labels, and “what was not done.”

---

## Architecture Findings

1. **The three gates are separate decisions, not one ceremony.** Merge quality, artifact readiness,
   and production authority have different evidence, owners, and enforcement boundaries. Their
   recorded-evidence handoffs should remain explicit.
2. **Production authority is an executor property, not a checklist side effect.** Protected
   deployment credentials or a named least-privilege live role are load-bearing; branch protection,
   review, and gate output cannot substitute for them.
3. **Deployment procedure must consume, not recreate, gate decisions.** `pcf-deploy` correctly
   refuses to become a fourth approval system and remains human-executed.
4. **Onboarding is a coordinator, not the source of runtime truth.** Loading `stack-profile` before
   assumptions prevents a single workflow from fossilizing one platform during migration.
5. **Rollback has multiple state domains.** Source/app revisions, routes, bindings, scale, data,
   requests, and external side effects need separate treatment; reversing a command is not full
   state reversal.
6. **Review scope is behavioral.** Line count and line overlap are useful clues, but blocker
   causality and reliable review cannot be reduced to either one.

## Routing Conflicts

- `[verified]` No description-level routing conflict was found or changed in Batch 6.
- `[verified]` Gate ownership is mutually explicit: merge, ship, and production authorization remain
  three named lanes.
- `[verified]` `pcf-deploy` is manual-only and does not absorb `pcf-ops` investigation or either gate.
- `[verified]` `service-onboarding` remains manual-only and explicitly defers read-only assessment to
  `service-readiness-audit`, active impact to `sre`, and knowledge writing to `scribe`.
- `[verified]` The incident fast path is conditional context, not a routing lane and not a Tier 3 shortcut.

## Shared Resource Opportunities

- Do not merge the three gate checklists. Their repeated candidate/target fields are handoff
  consistency, while their decisions and enforcement evidence differ materially.
- Do not centralize production-change and PCF rollback text. The gate owns authorization/reversibility;
  `pcf-deploy` owns platform state that revisions do and do not restore.
- Keep the Tier 2 example and incident fast path conditional. Moving either into the production gate
  entrypoint would increase common context and make exceptional behavior easier to misapply.
- Keep the manifest starter under `pcf-deploy`; it is platform-specific and explicitly subordinate
  to project-owned configuration.

## Missing Capabilities

No new canonical SRE skill is justified. The observed gaps were incorrect scope/facts inside existing
lanes. Positive manual-invocation calibration for service onboarding and a richer authorized PCF
deployment behavior case are evaluation gaps, not missing runtime capabilities.

## Standards / Portability Issues

- Portable concepts: exact candidate identity, build-once/promote, immutable artifact identity,
  evidence freshness, candidate-causal findings, explicit executor authority, reversible backout,
  runtime/workload-aware health, and SLI-derived alerts.
- Vendor-specific: GitHub immutable-release/ruleset APIs, protected environments, cf CLI/CAPI
  versions, manifests, routes, revisions, and Cloud Run deployment configuration.
- Internal conventions: three named gates, typed agent handoffs, Remedy/Jira incident reconciliation,
  the dashboard write exception, and migration-selected observability destinations.
- “Commit ID” identifies source state. Artifact digests/checksums identify built bytes. The two must
  remain correlated but must not be collapsed into one field.

## Evaluation Gaps

- `release-gate` and `production-change-gate` have direct behavior cases but no positive discovery
  cases that distinguish “ready to ship” from “authorized to execute.”
- `service-onboarding` has a negative manual-only discovery case but no explicit-invocation behavior
  case for either a request service or scheduled workload.
- `pcf-deploy` has a strong unauthorized-production case but no direct complete-plan case that grades
  manifest resolution, target API capability, rollback-state inventory, and human execution together.
- Merge-gate evals do not exercise a cross-file candidate-caused P2 or an unrelated pre-existing P2.
- Offline tests cannot prove current repository settings, target foundation versions, API feature
  support, quota, protected credentials, live approval, health, telemetry arrival, or rollback artifacts.

## Recommended Architectural Changes

### Critical

None.

### High

- **Implemented:** Make `service-onboarding` load the stack first and branch deployment, health,
  telemetry, and alerts by runtime/workload instead of assuming one PCF request-service shape.

### Medium

- **Implemented:** Make merge P2 blocking candidate-causal/behavior-aware and separate unrelated
  pre-existing findings.
- **Implemented:** Replace size-only merge blocking with an evidenced reliable-review condition that
  preserves atomic safe changes.
- **Implemented:** Correct PCF canary CLI/API prerequisites and per-additional-instance replacement
  semantics.
- **Implemented:** Bound the Tier 2 rollback example to desired-state restoration rather than full
  system-state reversal.
- **Implemented:** Preserve separate source commit, immutable artifact, and readiness-record fields
  through release and production verdicts.
- **Implemented:** Make rollback and Tier 3 safety regressions reject later contradictory instructions.

### Low

- **Implemented:** Make the incident closing sentence explicitly keep Tier 3 on the full gate.
- **Implemented:** Use “commit ID” consistently for source candidates and repository states.
- **Deferred:** A few live fleet-wide handoff/rules surfaces outside these five skills retain a legacy
  synonym for commit ID. Normalize that wording only as a separately scoped cross-fleet change; do
  not broaden this five-skill batch or rewrite historical evidence for terminology alone.

## Validation record

- `[verified]` Red first: the untouched Batch 6 skills failed 10 focused assertions covering the four
  source-identity surfaces and the six defects found during initial inspection.
- `[verified]` Green after correction: 9/9 focused release-contract tests pass. The ninth test applies
  sixteen named regressions to block-bound in-memory text and every contract oracle rejects its
  matching mutant.
- `[verified]` `scripts/check_test_layout.py` passes; the link suite passes 28 tests with one expected
  skip; the direct link checker passes.
- `[verified]` The fleet-validator suite passes 42/42 after its exact-candidate contract was updated
  to the new commit-ID wording. Direct fleet validation reports only 37 generated Copilot-projection
  drift paths accumulated across the six canonical batches; regeneration remains deliberately
  deferred until Batch 6 is committed.
- `[verified]` Offline scenario validation passes all 84 scenarios, and grader tests pass 553/553.
- `[verified]` The report mechanically contains exactly three should-trigger, three should-not-trigger,
  and two boundary cases for each of the five skills. `git diff --check` passes.
- `[verified]` Fresh-context independent review found one material content gap (a mandatory minimum
  instance rule overrode Cloud Run scale-to-zero) and weak block association in several focused
  oracles. A second pass found that verdicts could lose the source-to-artifact binding and that two
  predicates accepted later contradictory instructions. The baseline onboarding text replays red
  under the corrected oracle; current text is green. The oracles now bind source-identity fields,
  gate verdicts, merge rubric/size blocks, onboarding steps, PCF version/strategy blocks, rollback
  text, and fast-path scope to their exact owners and reject later contradictions.
- `[verified]` Final fresh-context re-review found no remaining Critical, High, or Medium finding and
  marked Batch 6 commit-ready. It independently observed focused 9/9, fleet-validator 42/42,
  test-layout/link/diff checks green, and all 16 named mutants rejected.
- `[verified]` After all six batches, the generator wrote 158 adapters and changed the 37 Copilot
  projections implied by canonical edits. The adapter suite passes 28 tests with two expected skips;
  generator self-check and direct fleet validation pass.
- `[verified]` The unpublished branch rebased cleanly onto current `origin/main` with zero commits
  behind. All 24 `scripts/test_*.py` files pass through their required
  standalone entrypoints. The mutation-guard inventory now explicitly classifies the three new
  cross-skill prose-contract suites as non-module tests rather than tractable blind files.
- `[verified]` `claude plugin validate . --strict` passes after integration.
- `[pending]` The one final-tree Gate A run, push, and PR publication follow this post-integration
  validation commit.
- `[unverified]` No PCF foundation, GitHub repository setting, protected environment, release artifact,
  production target, approval system, telemetry backend, or service was accessed or changed.

No routing description changed, so no paid clean-room routing trial is required for this batch.
