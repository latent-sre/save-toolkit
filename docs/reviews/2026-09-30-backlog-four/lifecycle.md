# LIFECYCLE-001: ownership contract and producer compatibility

Checked 2026-09-30 against Save Toolkit base `41383e3d` plus the candidate files below.
This evidence is retained for the open [LIFECYCLE-001](../../fleet-roadmap.md#lifecycle-001--a-service-record-stays-true-for-the-whole-service-life)
and CONTEXT-001 acceptance decisions. **Partial implementation and fixture verification; no
real-service acceptance or promotion.**

## Change and reason

[verified] The original service-lifecycle entrypoint covered onboarding and retirement handoffs but
did not assign the change, remediation, and refresh ownership transitions. Its consumer already
declared `v1alpha2` forbidden paths and `P30D`. Producer inspection additionally found that lifecycle
and ownership metadata were discarded from its projection; repairing that shared output requires
a new immutable resolved schema, not a skill-local lifecycle schema.

The [conditional record guidance](../../../skills/service-lifecycle/references/record-transitions.md)
now assigns all four transitions, keeps accountability with the service/finding owner until
reviewed readback, and distinguishes catalog freshness, document review, and execution verification.
It requires visibly stale or pending claims after changes, failed remediation, document-only refresh,
and unresolved retirement transfers. It preserves existing `scribe`, review, and production gates.
The entrypoint grows by 400 UTF-8 bytes (8,623 to 9,023); the conditional reference adds 6,393 bytes.
The detail is loaded only for transitions or freshness-sensitive lookup.

## Fresh verification

Consumer interpreter: `F:/repos/sre-agents/.venv/Scripts/python.exe`, Python 3.14.7.
Producer interpreter: installed Python 3.12.10, matching its environment card.

[verified] A separate read-only reviewer inspected both working-tree diffs and found no validated
new defect. The review is bound to mutable candidate bytes and does not establish runtime or
real-service acceptance. The root coordinator independently repeated the actual producer/consumer
CLI and asset suite: **24 tests and 91 subtests passed**.

- [verified] Red check: the new transition-reference asset check failed because the entrypoint
  lacked its reference; result **1 failed, 1 passed, 10 external checks skipped** before the edit.
- [verified] With `SRE_CONTEXT_ROOT=F:/repos/sre-context/.worktrees/lifecycle-001-status-projection`,
  `python -m pytest -q scripts/test_service_lifecycle_context.py scripts/test_skill_assets.py`
  passed **24 tests and 91 subtests**. The producer candidate is on branch
  `work/lifecycle-001-status-projection`, based on `be29c942`; its changes are uncommitted.
  Tests copy synthetic catalogs to a
  temporary directory and invoke the producer's actual CLI using the consumer sidecar.
- [verified] Producer baseline `be29c942` passed 86 tests. Six new projection tests first failed
  on the absent fields/version (one assertion failure and eight subtest errors; owner source
  validation already passed). With the repair, `python -B -m unittest discover -s tests -q`
  passed **92 tests** under Python 3.12.10. The new tests cover separate lifecycle states,
  missing/wrong owners, mandatory projected fields, and previous-schema migration.
- [verified] Consumer/producer requirements match structurally. CLI checks prove age 30 passes,
  age 31 fails, missing/future evidence fails, and an explicit evaluation date is required.
  Refreshing the synthetic mapping changes its age to zero but retains fixture taint and prohibited
  action selection. Missing optional deployment is returned as a gap; an explicit missing
  deployment fails. Forbidden-path enforcement rejects a present harmless sentinel; source
  approval/credential fields are rejected before output. Error cases assert empty stdout.
- [verified] The required producer validation, Alpha readiness resolve, Beta lifecycle resolve,
  help and version commands all exit 0; JSON outputs parse, preserve taint, and emit `v1alpha6`
  target lifecycle/owner fields. Package/CLI version is `0.1.5` / `v1alpha1.5`.
- [verified] `git diff --check` passed for the candidate at the time of the focused checks.
  External tests intentionally skip when `SRE_CONTEXT_ROOT` is unset; that default is not producer
  compatibility evidence. Historical fixture dates are used only for reproducible boundaries.

## Producer repair and remaining limits

[verified] The producer root at `85164cac` rejects this consumer's unchanged `v1alpha2` requirements
as invalid source (exit 3, empty stdout) because it expects `v1alpha1`. The prior compatible
`be29c942` review checkout rejects the newly strengthened consumer with exit 5 and empty stdout:
`/target/service/lifecycle` and `/target/service/ownerRef` are missing. No silent fallback is used.

[verified] Fresh producer fetch resolved `origin/main` to `903ac830`; the compatible base `be29c942`
is seven commits ahead and not integrated. Main still selects requirements `v1alpha1` and resolved
output `v1alpha4` in `schema_validation.py`. Integration therefore includes those seven existing
compatibility commits as prerequisites, not only the new lifecycle projection diff.

[verified] An additional temporary-catalog experiment marked both the selected Service and
Deployment `metadata.lifecycle: retired`, then called the CLI with the current consumer and
`--as-of 2026-08-30`. It returned exit 0 with the same team/service/environment/deployment IDs and
`lastVerified`, but no lifecycle state. The new producer fixes that loss: service and selected
deployment each project their validated `lifecycle` and qualified `ownerRef` in immutable
`resolved-context-v1alpha6.schema.json`. Retired/deprecated targets remain resolvable for record
audit and stay action-prohibited; resolution success is not active status. The current reader also
validates unchanged `v1alpha5` during migration without inventing missing fields. Source schemas
are unchanged; the consumer and producer mirror both add required service lifecycle/owner paths.
Catalog assertions still do not establish live retirement or an accepted human ownership transfer.

| Required outcome | Candidate evidence | Still required for completion |
|---|---|---|
| Change keeps the affected service record current or visibly stale | Explicit release/service owner and changed-version invalidation rule | Actual selected-service change, proposed record diff, review/readback, caller continuation |
| Remediation retains ownership until evidence closes the gap | Finding owner and failed-drill/merged-code non-verification rule | Real repair result bound to target and version, reviewed record and follow-up disposition |
| Refresh separates mapping age, review, and execution evidence | Actual CLI stale-to-fresh fixture check plus distinct date rules | Real mapping authority and record review; execution receipt before any `last_verified` advance |
| Retirement preserves records and transfers retained resources | Real CLI returns synthetic retired service/deployment states with owners and taint; explicit accepting owner/readback rule | Actual retirement receipts, retained-resource acceptance, independent checks and retired record |
| Consumer and producer share forbidden/freshness semantics | Eleven external CLI acceptance tests against the producer candidate, including retired visibility | Review and integrate both exact candidates; operational contract remains fixture-only |

[unverified] No real service/environment, authorized operational record repository, or transition
receipts were supplied. On 2026-09-30 the owner confirmed these are not available. They remain
required to run the acceptance sequence in the conditional
reference. A synthetic walkthrough cannot substitute for those four actual ownership transitions.
No live reads/writes, paid model calls, deployments, commits, pushes, or acceptance were performed.
The original producer worktrees and their source remain unchanged. Save Toolkit adapters are owned
by the caller's final regeneration step.

## Candidate checkpoint

The previously verified producer bytes are now committed locally at
`8316a220fabd5319974eacb77158a6a344f888cc` on `work/lifecycle-001-status-projection`.
The branch is clean; no push or merge was performed. Its seven earlier compatibility commits
remain prerequisites. Save Toolkit's candidate checkpoint is `c6a27d39`, subsequently integrated
with main `65daa521` in `115f6f6c`; the post-integration verification checkout is `2ffc6151`.
These commits make review targets stable and do not accept the generic alpha or real-service use.

Independent read-only review approved the lifecycle source delta at producer `8316a220` against
`be29c942`, and the consumer source at `37bf6a6d` against `41383e3d`. It confirmed separate target
status/owner projection, the unchanged v1alpha5 reader, matching requirements, fixture/action
boundaries, and accountable transition/date semantics. No concrete defect was found. This scoped
approval does not silently approve the seven producer prerequisite commits against `903ac830`,
nor establish operational acceptance. Runtime evidence remains the explicitly scoped checks above.

## Prerequisite freshness defect and repair

Review of the full producer integration from `903ac830` found a P2 in the existing freshness
aggregation: checking only the oldest selected date allowed another selected record to be future
dated. This contradicts the every-selected-object contract even though the current consumer's
single deployment policy does not trigger it.

The real checkout fixture has two selected repositories. With one date `2026-08-24`, another
`2026-09-01`, a repository freshness policy of `P30D`, and `--as-of 2026-08-30`, the old code
incorrectly returned success. New resolver subcases reproduced the failure with either repository
carrying the future date; an actual module CLI invocation also returned 0 instead of 5. An initial
test-helper argument omission was corrected before these three genuine failing assertions were
recorded; it was not counted as a product failure.

Producer commit `3433f98e53cb824d183c097ee433a0d35c374ee8` now rejects any future date before
computing the oldest date and maximum age. Valid mixed dates still report age 6 from `2026-08-24`;
future evidence returns exit 5 with empty stdout. All **95 producer tests** passed on Python
3.12.10. The actual producer CLI cross-repository checks and consumer assets passed **24 tests
and 91 subtests** from Save Toolkit `46abca05`. Source diff checks passed; the producer branch is
clean and unpushed. This commit supersedes `8316a220` as the producer candidate. Independent
read-only review approved the full scoped integration from `903ac830` through `3433f98e`, including
all seven prerequisites and the freshness repair; no remaining concrete defect was found.
Real-service records and transition acceptance remain unavailable.
