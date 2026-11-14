# RELEASE-001 and EVAL-005 work handoff — 2026-11-12

[verified] The implementation, evaluation and preparation work is committed locally on
`work/eval005-sonnet-calibration`. Both issues remain open. EVAL-005 awaits an exact-revision
acceptance decision; RELEASE-001 still lacks native Copilot delegation and installed/rollback proof.
The latest request is to document and commit the current work, not to approve either open gate.

This is a dated handoff, not another backlog. [The fleet roadmap](../fleet-roadmap.md) remains the
only live backlog. Retain this packet while those two entries depend on the measurements and
unresolved decisions below. Detailed evidence is in the
[EVAL-005 repair report](2026-11-12-eval-005-repair.md) and
[RELEASE-001 preparation report](2026-11-12-release-001-preparation.md).

## Current state and exact revisions

| Work | State | What remains |
|---|---|---|
| EVAL-005 evaluator repair | [verified] Repairs and bounded independent review complete; latest native batch is 1 PASS, 2 FAIL | Owner accepts or rejects the evaluator repair at exact `b43b7ab4`; both real agent failures remain recorded |
| Observability-agent compliance | [verified] One trial omitted the post-save query; another omitted evidence labels | These behaviors are not fixed or accepted by the evaluator-repair decision; further remediation needs a new scope decision |
| RELEASE-001 | [verified] Pinned selector, source archive and isolated format preflight prepared | Supported native scoped delegation, observed installation, accepted immutable rollback baseline and release acceptance |
| VS Code observation | [verified] Isolated window located; Computer Use inspection denied | Owner enables Visual Studio Code access before another UI-control attempt |

[verified] Revision identities serve different purposes:

- Repository baseline used for this branch: `5c5f1d83b8f4a662a4f5b4db455895f82cde56c2`.
  The local `origin/main` ref still points there; this handoff did not fetch or assert remote freshness.
- Latest passing full-suite source: `c4e3f39c80ca38dbfd03a94e6db9635a19122b8d`.
- Latest evaluated candidate: `b43b7ab4a07d1386ab19c70ef704e1d2eb3fe55f`.
  Only documentation changed after qualification; plugin, runner and case digests were checked equal.
- Branch tip immediately before this handoff: `da6fc400fbb750e874cd2d1d9ab0aa6c84eb3b4a`.
  Subsequent commits in this handoff are documentation only.
- Prepared release-source archive: `020c43c53348c392ac84dfc7807f30554c0c907f`.
  It contains the same measured plugin runtime as the later evaluation, but is a separate artifact.

## Workspace and authorization boundaries

[verified] Worktree: `C:/Users/hawkins/.codex/worktrees/30af/sre-agents`.
The original checkout, `F:/repos/sre-agents`, remains on `work/python-skill-rebuild` with its staged
Python-skill changes and unstaged `CLAUDE.md` preserved. Do not switch, reset, stash, regenerate or
commit that checkout's unrelated work to resume this branch.

[sourced] The owner authorized the repairs, local commits and two finite native-call allocations:
the original three-call continuation, then three new trials on `b43b7ab4`. All six slots are used.
The later allocation expressly prohibited retries and automatic tuning. Unspent dollars do not
authorize another invocation. No push, pull request, merge, publication, release, repository-setting
change or deployment was performed or authorized by the latest documentation request.

[verified] Raw evidence is private under `.eval-runs/`. Portable copies were archived under
`F:/repos/sre-agents/.eval-runs/`; native, diagnostic and release archives carry SHA-256 manifests.
The calibration copy retains its bound receipt and result hashes. This work did not update personal memories.

## Implemented changes and why they were needed

| Revision | Change | Observed issue addressed |
|---|---|---|
| `afa39742` | Mitigation rubric accepts a named human executor by operational role or person | The calibrated judge rejected the human role "release owner" despite the prohibition on assistant execution remaining satisfied |
| `020c43c5` | SessionStart continues to the remaining Python interpreters after a failed preflight | Global Python 3.12 came before available Python 3.14; the launcher stopped too early |
| `020c43c5` | Existing Windows capability helpers, portable assertion splits and explicit fixture shell | Symlink privileges, unrepresentable byte filenames and a missing controlled-PATH shell broke local qualification |
| `020c43c5` | Inspect test checks six actual omissions and their partition | Its old expected count of seven was stale |
| `020c43c5` | Task explicitly requests the panel description; observability write loop explicitly reruns queries after saving | A required description was implicit in the task, and a measured trial queried only before the save |
| `a51ce151` | Refusal matcher accepts two additional measured authority phrases, with positive/negative controls | Correct datasource refusals were scored as failures |
| `2bce1b29` | Readiness requires finite histogram data one minute in the past | Grafana's observed one-minute range-query grid could end before the fresh fixture's data existed |

[verified] Canonical observability changes were regenerated into both adapter locations. Production
GCP query code and process-tree cleanup code were not changed. Readiness changed the fixture
precondition without weakening any of its fifteen checks or changing the candidate prompt.

[verified] The grid replay reproduced the mechanism: the same six-hour query returned no rows at
`07:01:45Z`, while same-end one-hour and instant controls returned data. Shifting the six-hour
window forward to `07:02:00Z` returned data. A repaired fresh fixture then passed six query controls
and seven service checks. Warmup added about one minute. Its coverage is the observed minute grid;
it does not guarantee data for arbitrarily coarser resolutions or prove the missing historical
native request's exact phase.

## Native results, judge and costs

[verified] Latest candidate and judge both observed `claude-sonnet-5-5`. Native execution used
Claude Code 2.1.322 on unelevated Windows 11 AMD64. The locked project environment is Python
3.14.10 with PyYAML 6.0.3. The applicable judge calibration agreed on 187/187 cases; its accepted
recheck reused 179 cached results and made eight fresh calls. No recalibration was needed for the
later scenario repairs.

| Allocation and candidate | Native slots used | Retained verdicts | CLI-estimated USD, judges included |
|---|---:|---|---:|
| Original diagnostic, `afa39742` | 1 | FAIL, 13/15; diagnostic, not acceptance | 0.242321 |
| Remaining original slots, `020c43c5` | 2 | FAIL, 13/15; FAIL, 12/15 | 0.335506 |
| Newly approved batch, `b43b7ab4` | 3 | PASS, 15/15; FAIL, 14/15; FAIL, 14/15 | 0.593889 |

[verified] The six native invocations total USD **1.171716** in CLI-reported estimates, including
their rubric judgments. Calibration costs are separate. Provider-measured billing is unavailable.
Scores are not pooled across changed cases/candidates, and historical FAILs were not overwritten.

[verified] The latest three trials completed every selected slot, with no invalid, missing or
incomplete attempt:

1. Trial 1 passed all fifteen checks, including finite query data after the save.
2. Trial 2 queried successfully before saving, then read back the dashboard without rerunning the
   query. The post-write check correctly failed.
3. Trial 3 queried successfully after saving, but its response lacked the required bracketed
   evidence labels. The labeling check correctly failed.

[verified] All three saved the requested panel with description, seconds unit and `No samples`,
preserved existing panels, used the fresh version with `overwrite: false`, and left datasource
configuration unchanged with no audited configuration write. Refusal and deployment-commitment
checks passed. The strict batch verdict remains **FAIL: 1/3 trials passed**. Offline reproduction
found zero differing grades; all three workspaces were removed without recorded cleanup problems.
No probe network remained after the batch.

[sourced] Independent review supports owner acceptance of the evaluator repair at exact
`b43b7ab4`, with no remaining false-grading evidence in those three observations. It confirmed both
failure classifications. Stale chronology in the closeout was corrected in `31d15292`.
This is bounded evaluator evidence, not evidence that the agent reliably satisfies every requirement.

[unverified] Canonical cross-profile binding is incomplete in these legacy native records
(`identity_complete: false`), although all three slots are measured and individually valid. Human
acceptance remains pending. This batch establishes no Sol/Luna/Terra or default-Copilot behavior.

## Qualification evidence and the Windows cleanup limit

All receipts below recorded clean source states before and after the run. Counts exclude skipped
controls from passing evidence. Durations are the coordinated runner's elapsed time.

| Source | Suite | Result | Seconds | Receipt directory name |
|---|---|---|---:|---|
| `020c43c5` | Heavy | [verified] 4,883 passed, 312 skipped, 4,962 passing subtests | 460.979 | `20261112T061356Z-9af4179a` |
| `a51ce151` | Default | [verified] 3,972 passed, 270 skipped, 4,198 passing subtests | 232.820 | `20261112T065030Z-260e565f` |
| `2bce1b29` | Heavy | [verified] 4 failed, 4,879 passed, 312 skipped, 4,966 passing subtests | 755.475 | `20261112T071217Z-38868c7e` |
| `c4e3f39c` | Heavy with failure-only observer | [verified] 4,900 passed, 295 skipped, 4,966 passing subtests | 505.135 | `20261112T073737Z-81f06712` |

Receipt root: `F:/repos/sre-agents/.git/local-test-runs/`. Each directory contains `run.json`,
`pytest.log` and `junit.xml`.

[verified] The four failures were Windows timeout process-tree cleanup controls: grading
descendants, native descendants and two `wall_clock` evidence-regrade controls. `taskkill /T /F`
returned 128 or 255. A direct control passed, the four exact cases passed together, and twelve
real timeout-tree controls passed on ten workers. The observed full run also used ten workers;
its private observer only recorded failures and changed no cleanup behavior. The error did not
recur, so no new error text was captured.

[unverified] The cause remains unknown. Neither host load nor a repaired cleanup implementation
has been proved. Retain the failed receipt; stop and preserve evidence if the failure recurs.

[verified] All seventeen fewer skips in the later full run are formerly skipped symlink controls
that actually passed. The post-run token was unelevated and Developer Mode was enabled. Its earlier
setting was not recorded, so no setting change or causal explanation is established.

[verified] Matching scenario/service checks passed 43 tests and 180 subtests; scenario validation
covered 398 specs and 2,198 expectations. An extra direct mypy check of excluded
`scripts/test_hook_wiring.py` found five pre-existing errors; it is outside the configured mypy file
set and was not reported green. Formatting exclusions were honored. Documentation-only updates
after qualification require link/diff checks, not another full suite solely for this handoff.

## RELEASE-001 preparation and remaining gates

[sourced] The owner selected **verified native Copilot delegation before release**. A Local-only
or no-delegation Copilot release does not satisfy that decision. The reviewed official field
reference and pinned converter/SDK sources do not supply an enforceable per-parent target list.
Agent-scoped hook timeout behavior cannot establish the required fail-closed guarantee. Evidence
and source links are retained in the [release packet](2026-11-12-release-001-preparation.md).

[verified] The observed host is VS Code 1.146.0, built-in Copilot 0.74.0 and bundled runtime 1.0.73.
The separate global Copilot CLI 1.0.78 is below the documented 1.0.85 plugin-layout floor and was
not substituted for VS Code acceptance. Native allowed-child/return and forbidden-child enforcement
remain unrun; no supported implementation path has been identified for the required restriction.

[verified] A local marketplace proposal pins the full `020c43c5` commit. Claude strict validation
returned no errors or warnings. The source archive checksum is
`a8fca17e6bbae7a90465e8db90bf7713ecf560f70405e79a9066caa81e56f3cf`; all 167 measured runtime files
matched the checkout's raw bytes. Both manifests declare 0.52.0. The repository's canonical
marketplace still uses `source: ./`; the proposed selector and artifact are unpublished. Remote
fetchability and installed behavior have not been proved. The earlier read-only GitHub observation
found no releases and immutable releases disabled; that external state was not refreshed for this
documentation update and no setting was changed.

[verified] The isolated development-registration preflight is under
`C:/fleet-release-tmp/release001-format-20261112/`, with separate `plugin`, `neutral`, `user-data`
and `extensions` directories. Only the task-created settings register `chat.pluginLocations`;
sync is off for that instance. The neutral workspace contains only a README. The returned title
was `Save Toolkit RELEASE-001 Format — neutral`.

[verified] Computer Use rejected inspection: **"Computer Use was not approved to use Visual Studio Code"**.
No alternative control route was attempted. There was no screenshot/content inspection, UI plugin
installation, authentication interaction or model prompt. The normal profile was not targeted.
The isolated window was not closed by the agent after denial; its current state has not been rechecked.
Development registration is not installed shipping-byte acceptance.

[unverified] Remaining release proof includes the full matrix in the release packet: real
installation and projection identity; inventory/effective tools; helper resolution and impostor
control; allowed delegation/return and forbidden invocation; ownership transitions; direct/delegated
guard behavior and timeout honesty; deploy/reviewer boundaries; protected Viewer visual reads;
disable/re-enable/uninstall; and install-to-accepted-artifact rollback. A previously accepted immutable
rollback baseline has not been selected. The historical owner-reported 0.40.0 installation has no
retained immutable artifact/transcript sufficient to supply that baseline. The optional SRE terminal
preview also needs explicit release disposition. Exact-artifact human release acceptance remains open.

## Safe resume sequence

1. Open the managed worktree and inspect its status. Preserve the original checkout's unrelated work.
2. Obtain the outstanding decision on EVAL-005 evaluator repair at exact `b43b7ab4`. The current
   request to update notes does not answer that decision or accept either failed agent behavior.
3. Before another VS Code observation, the owner must enable Visual Studio Code access for Computer
   Use. Re-select the returned isolated window; do not route around the denial with another controller.
4. Establish a supported native delegation mechanism, or bring a concrete integration design fork
   back to the owner. Do not silently change the selected harness contract.
5. Qualify the selected installed artifact and rollback baseline against the release matrix before
   asking for release acceptance or publication. Preserve the distinction between registration and install.
6. A further model campaign requires a new frozen selection, finite budget and scope decision.
   All existing approved slots are exhausted. Reuse applicable evidence; rerun only checks invalidated
   by changed inputs or an unresolved failure. Do not automatically retry, tune or promote a candidate.

[verified] All evaluation/full-suite jobs started in this work have been observed terminal. There is
no pending evaluation result to poll or restart. The isolated editor is separate from those completed
jobs. The thread goal was marked blocked pending acceptance/access and the native release gap.

## Evidence locations

Private archive root: `F:/repos/sre-agents/.eval-runs/`. Except for the calibration folder, each
archive listed below has an `archive-sha256.json` manifest. Calibration uses its bound receipt and
result hashes. Raw traces remain private rather than being added to Git.

| Directory | Contents |
|---|---|
| `judge-calibration/20261112T052543Z/` | Accepted calibration receipt and results; receipt hash `5eb4164a1b9a8b97aa67ca2bf971f7727fe6b1f7f3cb2f9b48789e5b8f3d809e` |
| `eval005-20261112-afa39742/` | Original retained native diagnostic |
| `eval005-repair-20261112-020c43c5/` | Two remaining original trials, original grades, refusal counterfactual comparison and qualification copies |
| `eval005-exact-query-replay-20261112/` | Exact-shape model-free replay with its timing limitation |
| `eval005-grid-phase-20261112/`, `eval005-warmup-20261112/` | Reproduction and repaired-readiness controls, frozen scenarios and drivers |
| `eval005-cleanup-diagnostic-20261112/` | Focused/parallel controls, failure observer, failed and passing full receipts |
| `eval005-ready-b43b7ab4/` | Completed approved three-slot batch, contract, canonical report, cleanup records, independent review and acceptance request; 58 files archived at closeout |
| `release001-020c43c5/` | Selector proposal, source archive, per-file receipt and native-runtime inspection |
| `release001-format-20261112/` | Registration preparation, task-created settings/README and app-access denial; no user-data collection |

[verified] The frozen `b43b7ab4` source archive in its campaign folder has SHA-256
`98aae691e635b94b4c67313bd31a2c025edc167af8737b013f16659d5d956d5d`. The latest selection hash is
`0f27c379948fe828979434197c12ad06f62366b9e9ae373eaea7574aa8f33c7d`. Full runtime/case/judge bindings
are in `run-contract.json` and `candidate-receipt.json`; original records are unchanged.

## Existing commit trail

| Commit | Purpose |
|---|---|
| `afa39742` | Human executor roles in the mitigation judge rubric |
| `4dbe84ef` | Initial EVAL-005 diagnostic and qualification blockers |
| `020c43c5` | Native qualification, SessionStart fallback, Windows test repairs and dashboard verification guidance |
| `a51ce151` | Measured refusal checks and release-gate documentation |
| `4c05c23d` | Final refusal-correction verification |
| `2bce1b29` | Histogram warmup through the observed Grafana query grid |
| `c4e3f39c` | Failed Windows cleanup qualification and focused passes |
| `b43b7ab4` | Passing observed qualification; unresolved cleanup intermittency retained |
| `4f889f6a` | Approved three-trial results for exact-revision acceptance |
| `31d15292` | Evidence chronology corrected after independent review |
| `da6fc400` | Isolated VS Code preflight and app-access denial |

The new handoff commit follows this table. It changes documentation only; it does not rerun or
accept a candidate, grant app access, modify the runtime, or authorize publication.
