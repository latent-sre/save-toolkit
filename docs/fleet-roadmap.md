# Fleet roadmap

> **Status: live; refreshed 2026-09-07 against `ed321035`.** This is the only backlog.
> Historical records supply evidence, not new work or authorization. Cleanup does not close an
> unresolved item, approve a model budget, or establish behavioral acceptance.

## Item contract

Every live item carries seven fields: **ID** (stable identifier), **Status** (`active`, `ready`,
`blocked`, `decision-needed`, or `deferred`, dated), **Owner**, **Outcome** (what done looks like, in
one or two sentences), **Next action** (the next concrete step and who takes it), **Evidence**
(one link to the record that proves current state, or `none yet`), and **SRE task** (the task a
human SRE does differently when this lands; an item that cannot name one is `deferred`). An item
leaves this file only when its Outcome is met and merged, or an owner disposition is committed.
Its removal commit is the closure record: name the ID, disposition, and supporting evidence in the
commit message or patch. The changelog is a recent summary, not a permanent closure register.

Find an older item's disposition with
`git log --first-parent -m -p -G '<ID>' -- docs/fleet-roadmap.md docs/roadmap-closed.md CHANGELOG.md`.
Inspect the removal patch; read an older closure entry with `git show <commit>:CHANGELOG.md`.
This also covers items recorded before the closed register and changelog were trimmed. Historical
records do not re-queue work.

## Repository work

### HOST-002 — verify the installed VS Code plugin before supported distribution

**Status:** `active` (2026-09-07).
**Owner:** Maintainers accept the host/release; `agent-engineer` owns the plugin contract and
`software-engineer` owns helper/adapter repairs.
**Outcome:** An SRE can install an identifiable plugin, use its helpers and agent returns, and
roll back to an accepted artifact with tested host limits.
**Next action:** Run the [acceptance procedure](vscode-plugin-acceptance.md) on an exact candidate
in a neutral workspace. Keep the Copilot hook empty until its separate canary passes. Source fixes
in merged PR #237 do not prove installed-host enforcement, model behavior, or release rollback.
**Evidence:** [Independent-review fixes](reviews/2026-09-07-independent-review-fixes.md).
**SRE task:** Install and use the toolkit outside this repository with the documented behavior.

### INCIDENT-QUALITY-001 — verify decision quality after the SRE contract repairs

**Status:** `decision-needed` (2026-09-07); behavioral acceptance remains on hold.
**Owner:** Maintainers select the exact candidate and evaluation budget; `agent-engineer` owns
the bounded follow-up.
**Outcome:** The advisor loads relevant guidance, dispatches a bounded helper, reconciles its
return, and advances without invented causes, timing, or current-state claims.
**Next action:** Address unsupported stage/timing/escalation conclusions and exact file resolution
before the next bounded candidate. The helper-scope repair at `c53ed2b6` used one helper in both
fresh samples; one completed the actual native return/resume sequence but failed semantic criteria
4 and 6. The second read the fixture then tried an unnecessary missing path, stopping before resume.
Preserve these failures; neither the source repair nor structural PASS establishes acceptance. See the
[selected-improvement record](reviews/2026-09-07-selected-sre-improvements.md).
The completed 24-session Sonnet campaign failed behavioral acceptance; later source merges are not
a fresh behavioral verdict. Preserve actual return/resume and sufficient-evidence recovery as
regressions. Separate decisions remain for limited Terra comparisons (zero calls; tool absence
unproved and host skills injected), six Sonnet pairs for task-sized outputs, and three pairs for
helper exchanges. These are pending choices, not permission to run them.
**Evidence:** [Second pass](reviews/2026-09-07-incident-quality-second-pass.md), its
[symptom-guidance](reviews/2026-09-06-general-incident-help.md) and
[first-repair](reviews/2026-09-06-sre-decision-quality-repairs.md) baselines, plus
[task-sized outputs](reviews/2026-09-07-task-sized-skill-outputs.md) and
[helper exchange](reviews/2026-09-07-incident-helper-exchange.md). The
[operational-contract report](reviews/2026-09-04-operational-contract-fixes.md) remains the
record-provenance evidence used by merged PR #237. Results apply to those records' named snapshots.
**SRE task:** Get a useful next check or closeout without mistaking a helper's completed assignment
or an untimed aggregate for evidence of incident recovery or cause.

### CONTEXT-001 — establish a generalized SRE operational-context contract

**Status:** `active` (2026-09-07).
**Owner:** Maintainers accept the generic alpha; `agent-engineer` owns consumer requirements and
`software-engineer` owns producer/resolver implementation.
**Outcome:** Explicit team, service, environment, and deployment selectors produce the smallest
schema-valid context projection. Missing or ambiguous context fails closed and grants no authority.
**Next action:** Obtain the owner's selected critical service, environment, and approved record
location, then prepare the smallest real-service slice through the existing contract. The newer
producer passes the current consumer's fixture requirements; it still prohibits operational data
and action selection. Verify real-service navigation, freshness/missing records, ownership, and
handoff before claiming usability. Do not replay the old consumer patch as proof of current coverage.
**Evidence:** Refreshed 2026-09-07 in the
[selected-improvement record](reviews/2026-09-07-selected-sre-improvements.md); the
[accepted scope](decisions/2026-08-24-sre-operational-context-contract.md) governs acceptance:

- [verified] Local source at `0450ea58`: the [consumer sidecar](../skills/service-lifecycle/context-requirements.yaml)
  declares `v1alpha2`; the current authority-path checks are in the [asset test](../scripts/test_skill_assets.py).
- [verified] Local producer branch `work/context-001-lifecycle-review` at `be29c942` is seven
  commits ahead of refreshed producer main `903ac830`; its mirror is `v1alpha2`, superseding the old
  `458f39c` compatibility assessment. Its 86 offline tests and an explicit fixture resolve against
  this consumer passed. The all-state PR query for the newer branch returned none.
- [unverified] No real service has been selected or made operational through that fixture-only
  producer. Compatibility, producer merge, service onboarding, and live usability are distinct claims.

**SRE task:** State team, service, environment, and deployment once instead of repeating context.

### SKILL-001 — make confirmed oversized skills conditional routers

**Status:** `active` (2026-09-07); one skill per slice, probe before routing changes.
**Owner:** Maintainers approve each slice; `agent-engineer` executes.
**Outcome:** Skills load only needed guidance. A component contract outranks the byte screen or
probe; reducing bytes alone does not prove better behavior.
**Next action:** Choose one probe-then-checkpoint slice from the refreshed screen; `agent-authoring`
remains the previously queued candidate. Run the link check and the selected skill's eval scenarios
after an authorized cut. No skill edit or model run is part of this roadmap refresh.
**Evidence:** [verified] UTF-8/LF entrypoint sizes at `ed321035`, measured 2026-09-07. Six exceed
the existing 7,800-byte screen (the old list of three is obsolete):

| Skill | Bytes |
|---|---:|
| [incident-investigation](../skills/incident-investigation/SKILL.md) | 16,904 |
| [agent-authoring](../skills/agent-authoring/SKILL.md) | 9,392 |
| [service-lifecycle](../skills/service-lifecycle/SKILL.md) | 8,639 |
| [pcf-deploy](../skills/pcf-deploy/SKILL.md) | 8,635 |
| [gcp-ops](../skills/gcp-ops/SKILL.md) | 8,187 |
| [runbook](../skills/runbook/SKILL.md) | 7,845 |

**SRE task:** Get the needed guidance with less irrelevant context and response delay.

### LIFECYCLE-001 — a service record stays true for the whole service life

**Status:** `active` (2026-09-07).
**Owner:** Save Toolkit maintainers.
**Outcome:** Change, remediation, refresh, and retirement each have an owner who keeps the service
record current or visibly marks it stale.
**Next action:** Verify those ownership transitions and reconcile producer support for freshness
and forbidden paths through CONTEXT-001. The consumer already declares `forbidden` and `maxAge`;
verify their shared semantics and the evidence needed for `last_verified`, rather than adding
another skill-local schema. Retirement is already a mode of `service-lifecycle`.
**Evidence:** Current [lifecycle requirements](../skills/service-lifecycle/context-requirements.yaml)
and [knowledge-disposition rules](../skills/operational-learning/SKILL.md); end-to-end acceptance
of all four transitions remains unverified.
**SRE task:** Know whether a service record still applies to the deployment being operated.

## Deferred

### EFFECT-001 — effect-bound execution broker

**Status:** `deferred`
**Owner:** Save Toolkit maintainers
**Outcome:** If protected automation is ever allowed to perform a live effect, approval is bound to
one exact action, target, argv/executable digest, expiry, nonce, rollback, and replay ledger.
**Next action:** None. Importing a broker before a legitimate consumer would broaden the apparent
execution path rather than reduce current authority. Reopens only when a named workflow is approved
to cross the current prepare/recommend boundary with a separately controlled execution identity.
**Evidence:** none yet
**SRE task:** An SRE approving a live automated action gets one exact, bound, revocable approval —
target, argv/executable digest, expiry, rollback — instead of an open-ended execution grant.

## Parked

All ten items below remain `deferred` (2026-09-03). Reopening requires a named SRE task and owner
decision, then a full seven-field item above. This refresh neither closes them nor authorizes runs.
The [prior roadmap](https://github.com/latent-sre/save-toolkit/blob/ed3210358557415023f33faaaf669315fe79d7ec/docs/fleet-roadmap.md)
retains their historical evidence paths and recovery commands; those measurements do not establish
current behavior. Consumed evaluation profiles remain non-reusable.

| ID | Required decision or evidence before work resumes |
|---|---|
| WF-001 | Prove dispatch of an exact trusted `ship-review` workflow without caller-supplied workflow code. Re-probe only on a material host/contract change. |
| ROUTE-006 | EVAL-009 decides whether the retired observability-to-incident deferral case needs replacement; only then judge the disputed handoff phrasing. |
| GRAPH-004 | Establish a named SRE use for `fleet-atlas`. [PR #205](https://github.com/latent-sre/save-toolkit/pull/205) is closed unmerged; preserve donor source/evidence and do not merge or rewrite it before GRAPH-006 semantic parity. |
| GRAPH-005 | Reconcile bridge findings and rerun the pinned-image six-case lifecycle before accepting the offline Agent Framework/AutoGen A2A bridge with its human decision boundary. |
| GRAPH-006 | Review a compact v2 atlas design and compatibility matrix: one typed pipeline and shared projection/provenance verifier for build/check/query. |
| ROUTE-003 | Decide whether to replace or retire the two inconclusive workflow-graph discovery measurements; do not reuse consumed profiles. |
| ROUTE-004 | Decide whether the surviving Mantine positive at threshold 1.0 suffices, or needs a replacement calibration case. |
| EVAL-005 | The [dashboard probe](../evals/build-scenarios/build-obs-dashboard-write-honours-the-carve-out.yaml) now seeds real Prometheus data. Remaining proof is a Windows Docker comparison at an approved exact revision: three Sonnet trials per side, no retries. |
| EVAL-007 | Resolve the closure contract for an incident-response verdict based on meaning: a structural or relation-based grader plus a clean guidance-removal counterfactual. |
| EVAL-009 | Reconcile the old fleet-weight/PR #224 prerequisites against current main before authorizing a new corpus baseline and judge calibration. Decide description ownership-map wording and injection-refusal coverage; include the eleven-description routing follow-up. |
