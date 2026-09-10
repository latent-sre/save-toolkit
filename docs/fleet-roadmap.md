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


## Repository work

### RELEASE-001 — make the toolkit installable as an immutable, rollback-tested release

**Status:** `active` (2026-09-10).
**Owner:** Maintainers accept the release; `agent-engineer` owns the plugin contract and
`software-engineer` owns helper/adapter repairs.
**Outcome:** An SRE installs a pinned artifact rather than whatever `main` holds, and can roll back
to a previously accepted one. The 2026-09-10 acceptance run passed against a local install, not
those exact shipping bytes.
**Next action:** Retire the mutable `"source": "./"` selector in `.claude-plugin/marketplace.json`
for an immutable selector or checksum, then re-run the acceptance cases on those shipping bytes: the
2026-09-10 pass was against a local `./` install, and a passing run does not carry to bytes it did
not exercise. The enforcement results that were open on VS Code 1.135.0 are superseded by that run.
Still unrun: the agent-scoped hook canary, with `hooks/copilot-hooks.json` shipping empty. VS Code
1.111+ supports `PreToolUse` permission decisions whose payload fields match `readonly-guard.py`, so
the canary is shorter than the procedure implies -- what does not carry over is the 42/43/44
exit-code authentication and `agent_type` scoping.
**Evidence:** The 2026-09-10 VS Code 1.137.0 acceptance row in the host-support table of
[`README.md`](../README.md); HOST-002's closure commit records the owner disposition.
**SRE task:** Install a named version of the toolkit, and go back to the previous one if it regresses.


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
**Next action:** Review the owner-approved incident-investigation repairs and conditional-detail
candidate in [PR #248](https://github.com/latent-sre/save-toolkit/pull/248), recorded in the
retired 2026-09-08 quality-round report preserved in Git history.
The core is 7.4% smaller after restoring and clarifying the five opening questions; reference-read
scenarios and example checks are repaired, but fresh judge calibration and paired native behavior
are unverified.
Select their budget before behavioral acceptance. `agent-authoring` remains queued; this slice does
not authorize another skill's cut.
The owner-approved Terra prompt comparison now records supplied source and same-session updates;
opening coverage improved in its single paired sample, while direction-change checkpoint selection
still failed and the candidate inferred a database destination. The detailed Terra follow-up is
preserved in the retired quality-round report in Git history.
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
decision, then a full seven-field item above.

| ID | Required decision or evidence before work resumes |
|---|---|
| WF-001 | Prove dispatch of an exact trusted `ship-review` workflow without caller-supplied workflow code. Re-probe only on a material host/contract change. |
| GRAPH-004 | Establish a named SRE use for `fleet-atlas`. [PR #205](https://github.com/latent-sre/save-toolkit/pull/205) is closed unmerged; preserve donor source/evidence and do not merge or rewrite it before GRAPH-006 semantic parity. |
| GRAPH-005 | Reconcile bridge findings and rerun the pinned-image six-case lifecycle before accepting the offline Agent Framework/AutoGen A2A bridge with its human decision boundary. |
| GRAPH-006 | Review a compact v2 atlas design and compatibility matrix: one typed pipeline and shared projection/provenance verifier for build/check/query. |
| ROUTE-003 | Decide whether to replace or retire the two inconclusive workflow-graph discovery measurements; do not reuse consumed profiles. |
| ROUTE-004 | Decide whether the surviving Mantine positive at threshold 1.0 suffices, or needs a replacement calibration case. |
| EVAL-005 | The [dashboard probe](../evals/build-scenarios/build-obs-dashboard-write-honours-the-carve-out.yaml) now seeds real Prometheus data. Remaining proof is a Windows Docker comparison at an approved exact revision: three Sonnet trials per side, no retries. |
