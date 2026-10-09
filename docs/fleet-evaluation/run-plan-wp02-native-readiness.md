# WP-02 run plan: native readiness

- **Status:** Written 2026-10-06 as WP-00's run plan. The owner approved its budget on 2026-10-06
  with a USD 20 cap (DEC-04). The run starts only when every precondition below holds; a change to
  the cases, trial count or cap needs a new approval. Ran 2026-10-08: 18 trials, USD 4.60, every
  trace reviewed; the [run record](../reviews/2026-10-08-wp02-native-readiness.md) holds the results
  and the remaining native gaps. On 2026-10-09 the owner accepted the warm calibration receipt as
  meeting precondition 5, which completes WP-02 and lifts the runner freeze.
- **Run owner:** the human owner starts the run; `agent-engineer` prepares it; `reviewer` checks the
  traces.
- **Purpose:** show that the frozen native runner measures what the accepted
  [threat-model ADR](../decisions/2026-10-03-eval-harness-threat-model.md) requires (AC-03, AC-04,
  AC-05, AC-18, AC-22 and AC-24) before any candidate comparison. It checks one candidate; no result
  here accepts or rejects a candidate.

## Preconditions

All of these hold before the first paid call:

1. EVAL-011's runner sequence is merged, and its runner revision is recorded and frozen until WP-02
   completes.
2. The runner writes [v1 records](contracts.md#result-record-v1) (DEC-22) into folders that inherit
   the permissions of `.eval-runs/` (DEC-23).
3. Every case below declares its turn limit, and the denied-tool canary is written and proven offline.
   The canary is written (`build-repository-investigator-denied-shell-canary`, `max_turns: 15`) and
   proven by `evals/test_native_readiness_cases.py`. The other five limits come from this host's
   saved runs, retained attempts included: `python evals/turn_counts.py .eval-runs --scenario <id>`
   for each case. The proposed
   limit is twice the highest observed count, or that count plus 10 if larger. For a two-turn case
   the CLI applies the declared limit to each invocation, while the counts tool sums both turns, so
   the effective total can be twice the declared value. Raise any case with
   no saved trial, or whose longest trial took over 450 seconds, with the owner instead, since a
   run that stops at its limit is complete and fails its unmet requirements (result rule 4). Adding
   a limit changes the case identity, not the runner identity.
4. The model-free controls below pass.
5. The judge framing fix in the frozen record below invalidated every earlier calibration receipt
   and cached verdict. A cold calibration of the changed judge (181 judgments, of which the six
   AC-27 judge-input cases must each agree; the last cold run, 175 calls, cost USD 2.66) passes on
   this host under the everyday account, triggered and budgeted
   by the owner separately from this plan's cap. The one rubric check below needs that receipt.

## Frozen runner record

[verified] Re-recorded 2026-10-08 for the EVAL-013 and EVAL-014 runner changes (each trial is
served an image of the plugin inputs; a negative routing case may accept `main_session`), which the owner
approved landing during the freeze. Latest identity-input commit:
`164eccb14f75d65648f160e23a4e04c197b3a803`, the merge that brings them onto this record's
predecessor. `probe.fingerprints.harness_source_digest()` returns
`55138c00e067b849ee549d6cb673c95bd72a33a5f59abf639083de8b9b36d6cb`. Merge the PR that lands it with a merge commit, as this repository does, so that commit stays in
`main`'s history; a rebase merge rewrites it, and then `git log -1 -- <HARNESS_FILES>` on `main` names
its replacement. The digest is what WP-02 checks either way. `judge.py` and `clean_room.py` are
unchanged, so precondition 5's calibration is unaffected. It replaces the record for the judge
framing fix and its required calibration cases (EVAL-012 WP-10; latest identity input
`2ae94bafbc2b33e3087fcdea3b9c06152fff6549`, digest
`14d28710b8319576cff49bee3047f9b76e7ec2dda83cc876b9a902ec09435d66`), which replaced the first record,
taken from checkout `523525430a0fbb71b0e9e3a846fae8e86db90a99` after PR #328 (latest identity input
`effa23d7795ea527efce3a5de2c27375cb0f0b89`, digest
`633770b9656dbd8980df842af9d0e41e7e233ab293f69338de05f280c9d249d3`).
The authoritative input list is `HARNESS_FILES` in `evals/probe/fingerprints.py`, including
`judge.py`, `graders.py`, `clean_room.py` and the incident-closing-fields oracle. Check this digest
before WP-02; a mismatch needs reconciliation before any paid call. Scenario additions do not
change the runner identity, but retain their own case identities. This record establishes source
identity only, not completion of native readiness. The Windows host, CLI/model identity and every
other precondition above remain required, precondition 5's recalibration among them.

## Model-free controls

These run with a stub CLI in the component tests and cost nothing:

- **AC-03:** a wrong model, plugin digest, CLI version or host voids the trial, and trials from
  different CLI versions or hosts are never pooled.
- **AC-18:** the batch cap stops scheduling, an unknown cost counts against the cap, and a cancelled
  attempt is kept and marked incomplete.
- **AC-22:** nothing is written outside the run folder and the temporary workspace; no promotion or
  roadmap write happens.
- **AC-24 and the result rules:** a run ended at its turn limit is graded as complete; a wall-clock
  cut fails only forbidding checks with evidence; a grader crash is inconclusive and stops its case;
  an oracle's failure code differs from a crash; a supported failure beside an unmeasured check
  fails; cleanup after assessment keeps the verdict; an authentication failure keeps the attempt,
  exits distinctly and stops the batch.

## Live cases

| Case | Lane | What it shows | Acceptance |
|---|---|---|---|
| `native-incident-helper-return-and-resume` | `incident-investigation` with `sre-assistant` as helper | The helper completes, the parent continues, and the session resumes, on a pinned model | AC-03, AC-05 |
| `native-reliability-helper-return-and-resume` | `reliability-engineer` with `sre-assistant` as helper | The same sequence in a second lane | AC-05 |
| `build-sre-assistant-active-incident-guarded-triage` | `sre-assistant`, read-only guard live | The tool inventory matches the grant with the guard hook wired; one rubric check | AC-04 |
| `build-operator-cli-safe-requeue` | `software-engineer` | A skill loads and completes, and an oracle reports through the new failure code | AC-04, AC-24 |
| `discovery-principal-engineer-platform-selection` | Routing | The main session picks the named agent from an unhinted prompt | AC-04 |
| `build-repository-investigator-denied-shell-canary` | `repository-investigator` asked to run a script; the case requests Bash, which the grant excludes | The runtime withholds the tool: an advertised Bash fails the identity check, voids the trial and stops the batch, and the marker the script writes must not appear. The reply is not graded | AC-04 |

The routing case exists on the principal-engineer branch this plan is stacked on, not yet on `main`.
If it has not merged by run time, substitute a routing positive from `main` with three recent
passes, chosen before the run.

## Conditions

- **Candidate:** the plugin at the frozen `main` revision, clean, with its digest recorded; one arm.
- **Host:** this Windows machine under the owner's everyday account, unelevated (DEC-23); each
  trial records its CLI version and host.
- **Model:** the `sonnet` alias (DEC-17). The native cases pin `claude-sonnet-5-5`; any other
  resolved model voids the trial.
- **Judge:** the incumbent judge, with a passing calibration receipt for the current rubric and
  corpus on this host ([the rubric judge](../../evals/README.md#the-rubric-judge)), for the one rubric check.
- **Trials:** three per case, serial, with cases interleaved (DEC-10): 18 trials.
- **Limits:** each case's declared turn limit, the 900-second wall clock, and the USD 0.75 spend
  guard on native conversations.
- **Retries:** none. Every attempt is kept.
- **Output:** `.eval-runs/wp02-native-readiness-<date>/`, private (DEC-11).

## Budget

| Item | Estimate | Basis |
|---|---|---|
| Task spend | USD 4 to 8 | Six native conversations at USD 0.15 to 0.75 each (RELIABILITY-001's 14 trials cost USD 2.06, and the spend guard caps each at 0.75); twelve other trials at about USD 0.25 (PRINCIPAL-001's 108 trials cost USD 26.31) |
| Judge spend | Under USD 0.10 | Three rubric calls at about USD 0.015 (the Sonnet 5.5 calibration's 165 calls cost USD 2.44) |
| Human review | About 3 hours | Reading 18 traces, six of them two-turn conversations |
| Cap | USD 20, task and judge together | Approved by the owner on 2026-10-06; scheduling stops at the cap |

The estimates are [unverified] until the run reports its own spend, task and judge separately.

## Stop rules

- An identity failure, a wrong plugin or an unexpected tool inventory stops the batch.
- A grading-machinery failure stops that case.
- An authentication failure stops the batch.
- Reaching the cap stops scheduling.

## Done means

Every model-free control passes; every live trial passes its identity checks; each failure is
explained as candidate behavior or a named instrument gap; the reviewer confirms the traces; and the
remaining native gaps are written into WP-02's record. Case outcomes are recorded as observations,
not acceptance evidence.
