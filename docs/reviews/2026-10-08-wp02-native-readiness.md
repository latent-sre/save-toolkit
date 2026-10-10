# WP-02 native readiness: run record (2026-10-08)

The owner approved starting WP-02 on 2026-10-08 under its [run plan](../fleet-evaluation/run-plan-wp02-native-readiness.md).
All 18 planned trials ran, and an independent `reviewer` checked every trace. The run checks the
frozen runner, not a candidate; case outcomes are observations, not acceptance evidence.

## Identity

- [verified] **Candidate:** plugin digest `a116976c…`, the bytes of `main` at `918a82fb`. The trials
  ran from `work/wp02-prep` at `8892ad5b`, whose only changes from `main` are the turn limits and one
  calibration case, so `plugin_commit` records the branch while the digest equals `main`'s. The
  reviewer recomputed the digest from committed blobs at both revisions.
- [verified] **Runner:** `harness_source_digest()` `55138c00…`, the frozen record.
- [verified] **Runtime and model:** CLI 2.1.295 on Windows 11 AMD64. Every init event,
  `modelUsage` entry and subagent message names `claude-sonnet-5-5`.
- [verified] **Profile:** in all 18 trials exactly one plugin, served from the recorded image, the
  runtime tool inventory equal to the grant, every result `success`, and every record `completed`.
- [verified] **Judge:** receipt `.eval-runs/judge-calibration/20261009T040121Z/`, 181/181. 180
  judgments are cache hits from the cold calibration `20261009T025721Z` of the same judge, and one is
  live, for the case reworded in `8892ad5b`.
- [verified] **Spend:** USD 4.60 for the 18 trials, task and judge, against the USD 20 cap. Outside
  the batch: the cold calibration USD 2.80, the recalibration USD 0.013, an attribution check USD 0.57
  and a guard probe USD 0.005.
- [verified] **Limits:** no trial reached its turn limit (highest 16 of 42) or the 900-second wall
  clock (longest 120 s).

## Results

| Case | Result | Explanation |
|---|---|---|
| `native-incident-helper-return-and-resume` | 0/3; structure 3/3 | Candidate behaviour, plus one instrument gap below |
| `native-reliability-helper-return-and-resume` | 3/3 | Structure verified; semantic assessment is manual by design |
| `build-sre-assistant-active-incident-guarded-triage` | 0/3 | Instrument: label checks stricter than the lane's contract |
| `build-operator-cli-safe-requeue` | 3/3 | Genuine passes; the oracle's failure code was not exercised |
| `discovery-principal-engineer-platform-selection` | 1/3 | Not the runner; follows the CLI change, attribution below |
| `build-repository-investigator-denied-shell-canary` | 3/3 | Bash withheld at the inventory; the marker never appeared |

**Incident helper.**
- [verified] `save-toolkit:incident-investigation` is advertised at init in all six invocations.
  The parent never calls Skill, and its first call is always the helper dispatch. The board check
  then fails, because the board contract lives in that skill. Thinking is redacted, so the reason is
  not visible.
- [verified] Base state: earlier runs loaded the skill 2 of 7 times, both on `claude-sonnet-5` at CLI
  2.1.289. On the pinned `claude-sonnet-5-5` it is 0 of 7 including this run.
- [sourced: independent trace review] The rubric failures in runs 1 and 2 are an instrument gap: the
  `statement_rerun` rubric case supplies only the follow-up facts, so the judge called timestamps
  invented that the fixture supplies. Run 3 passed with the same facts.

**Guarded triage.**
- [sourced: independent trace review] Only the label checks fail; the rubric passes 3/3 and every
  forbidding check passes. The lane's contract says to "retain these fields" and lets direct human
  answers combine them in prose within the caller's format.
- [verified] Every reply keeps each field as a labelled heading (`**Observations**`,
  `## Observations`), while the checks require `Label:`. The Assignment check also rejects
  `**Assignment:** complete`. The fleet's own incident oracle accepts heading and emphasised labels.

**Platform-selection routing.**
- [verified] On the old runner at CLI 2.1.291 this case handed off to `principal-engineer` as its
  first call 3/3. Here two trials explored the empty repository, loaded `stack-profile` and tried to
  write the design themselves; one handed off after exploring.
- [verified] An attribution run of the old runner, serving a checkout of the same plugin bytes on CLI
  2.1.295, handed off 0/3. The served plugin image is therefore not the cause; the drop follows the
  CLI change from 2.1.291 to 2.1.295, or model drift behind the same identifier.

**Guard liveness.**
- [verified] No trial ran a non-allowlisted command, so the 18 traces carry no evidence that the guard
  is live.
- [verified] A separate one-trial probe ran `sre-assistant` as the main loop through `--agent`, with
  Bash pre-approved, on CLI 2.1.295. Its `mkdir` was denied with the guard's allowlist reason, and no
  directory was created.

## Native gaps found in the original run

These observations describe the runner and evidence on 2026-10-08. The repair records below
distinguish the original gaps from current implementation; they do not rewrite the original trials.

1. **Account skills leak.** [verified] Sixteen account-level `anthropic-skills:*` skills were
   advertised in 5 of 18 trials, including all three routing trials. The runner neither records the
   skill inventory nor checks it.
2. **Guard coverage in the case.** The guarded-triage case never attempts a denied command, so it
   cannot show the guard live. The PowerShell guard path is not exercised.
3. **Oracle failure code (AC-24).** The operator-CLI oracle exits 1 on failure, the same code as a
   crash; a distinct failure code is neither implemented nor exercised.
4. **Turn limits on two-turn cases.** `max_turns` applies to each invocation, while `turn_counts.py`
   derives the limit from both turns summed, so a declared 17 can allow 34 in total.
5. **Contract label checks.** The guarded-triage label checks are stricter than the lane's contract.
   Repair them, then regrade beside the originals.
6. **Rubric case evidence.** The `statement_rerun` case lacks the earlier turn's facts.
7. **Ignored files in the digest.** [verified] Git-ignored files under measured folders, such as
   `__pycache__` bytecode, enter the plugin digest and the served image while `plugin_inputs_dirty`
   stays false. Fifteen such files were removed before this run.
8. **Calibration receipt.** Precondition 5 asks for a passing cold calibration. The cold run agreed
   180/181; the bound receipt is warm, with one live call after the case was reworded. The two rubrics
   this run used agreed fully in the cold run. The owner accepted the warm receipt on 2026-10-09,
   which completes WP-02.
9. **Batch cap (AC-18).** The cap and unknown-cost paths were enforced by the launcher, not exercised
   in the runner; no cost was unknown.
10. **Argv and host (AC-03).** The argv is kept only for two-turn follow-ups, and the host identity is
    platform-only, so it cannot show the everyday, unelevated account.
11. **Residue (AC-22).** `F:\eval-tmp\wp02` holds three `tmp.*` folders the operator-CLI trials made
    and seven empty CLI task outputs: candidate and CLI writes, not runner writes.

On 2026-10-09 the owner selected the first repairs, in order: gaps 1, 2, 5 and 3. All four are
implemented, under `EVAL-011`:
- [verified] Gap 1: every trial passes `syncClaudeAiSkills: false` and records its skill set, and a
  foreign skill fails the identity check. Account skills appeared in 7/8 unisolated probe sessions
  and 0/16 isolated ones.
- [verified] Gap 2: `build-sre-assistant-guard-denies-script-canary` requires one attempt at a
  command outside the allowlist and forbids its effect. One live Sonnet trial passed 4/4, with the
  guard's own refusal in the trace.
- [verified] Gap 5: the guarded-triage label checks accept the contract's labelled headings; all
  three WP-02 trials move from FAIL to PASS on rescore.
- [verified] Gap 3: the operator-CLI oracle exits 10 on a failed contract, which its scenario
  declares as `failure_exit_code`; any other nonzero exit is an instrument failure.

The owner then selected gap 4, answering Codex's P1 on PR #340, and it is implemented:
- [verified] Gap 4: a resumed invocation gets only the turns the first left, a conversation that
  spends its limit ends without its follow-up as a completed run, and a regrade refuses a saved
  conversation that ran past its limit. Rescoring the 19 saved two-turn runs with and without the
  change differs in none; the highest saved count is 7 + 1 of 18, so none came near its limit.

Raw records stay private under `.eval-runs/wp02-native-readiness-20261008/` and
`.eval-runs/wp02-attribution-20261008/`; the reviewer's scratch is under `F:/iso-tmp/wp02-review/`.

## EVAL-011 follow-up, 2026-10-10

The owner delegated the remaining routine repair and disposition decisions to finish EVAL-011.
The [closeout record](2026-10-10-eval-011-closeout.md) holds consolidated verification and saved-run
comparison evidence. This update records the completed targeted work without claiming a new native
candidate comparison or replacing the original WP-02 observations.

- **Gap 6, rubric evidence.** [verified] `statement_rerun` now includes the earlier turn's facts,
  with six additional calibration controls. Receipt
  `.eval-runs/judge-calibration/20261010T105741Z/identity.json` agrees on **187/187** cases:
  27 new judgments and 160 applicable cache hits, with no inconclusive calibration case. The three
  original saved final replies were then judged afresh under that binding. Runs 1 and 2 change
  from rubric FAIL to PASS; run 3 changes from PASS to FAIL because it treats a success receipt as
  the run's start and asserts an email arrival time the records do not establish. This is a
  supported semantic failure under the repaired evidence, not an instrumentation failure.
  Calibration and these rejudgments used **30 live calls, USD 0.902976** in total. Original replies,
  timing and grades remain unchanged; separate records live under
  `.eval-runs/wp02-native-readiness-eval011-rubric-rejudgments-20261010T110051Z/`. The original
  incident cases' independent structural failures still stand.
- **Gap 7, ignored inputs.** [verified] Hashing and staging use the same Git inventory. Ignored
  untracked residue enters neither the digest nor the served image; tracked files remain measured,
  and non-ignored untracked inputs remain
  measured and dirty. Unreadable inventories and explicitly named ignored hooks are refused.
- **Gap 9, batch spending controls.** [verified] Tests invoke the actual batch runner with a stub
  CLI and exercise the cap stopping further trials and an unknown cost stopping capped scheduling.
  This supplies the runner-path evidence the original launcher's enforcement did not provide;
  it adds no model-behavior or pricing claim.
- **Gap 10, invocation and account evidence.** [verified] Every attempted CLI call writes argv,
  workspace and launch state before execution, then exit and boundary evidence afterward. Runtime
  records include OS-observed hostname, account ID, elevation and observation source. New CLI
  batches reject incomplete identity or elevation before trials. Older v1 records remain readable;
  unknown host/account identity does not pool or establish matched comparison conditions.
- **Gap 11, residue.** [verified] Both CLI children and grading/oracle commands use workspace-owned
  temporary directories. A cleanup receipt records removal, intentional retention and problems;
  failed cleanup preserves the measured verdict and blocks batch reuse. The original ten files
  were moved from `F:/eval-tmp/wp02` to
  `.eval-runs/wp02-native-readiness-20261008/residue-archive-20261010/`; its manifest records their
  relative paths, sizes and SHA-256 digests. The source tree contains no remaining files.

[verified] Beyond these WP-02 gaps, supervised completion now covers 100 executable oracle
commands across 40 cases (93 Python, seven UI), with FAIL exit 10 distinct from INCONCLUSIVE exit 1;
eight semantic placeholders remain explicit unavailable measurements. All 242 active cases declare
turn limits: 235 newly sized offline, seven preserved. [unverified] These provisional limits do not
prove live completion time or candidate uplift. The original WP-02 run also remains without live
PowerShell guard-path evidence; its later live guard canary exercised Bash.
