# RELIABILITY-001: bounded native evidence and instrument repair

Status: acceptance incomplete. This record supports RELIABILITY-001 in the
[live roadmap](../../fleet-roadmap.md). The owner authorized at most twelve Sonnet trials,
no retries, a USD 20 total model budget, and no production access on 2026-09-30.

## Identity and method

- Baseline: `41383e3dff84465d5e41923707a82eb0c6ef512c`, clean plugin digest
  `05ce8abb4f18d422a79e11bfe29d021025c541fe5d106fc9ee5d14120d97591e`.
- Candidate: that baseline plus the reliability agent's closed-schema precedence clarification;
  plugin digest `4dfb8bbd846f6e133eaa59a9ae8d75678b79ac7e9d78f5d10913723aa2a2ae48`.
  Candidate inputs were dirty by design and frozen in a separate worktree. Generated projections
  were regenerated there. This is a content-digest-bound candidate, not a new accepted commit.
- Host: Windows; Python 3.14.7; Claude Code 2.1.285. Sonnet resolved to
  `claude-sonnet-5-5`; later calls pinned that exact model. The native scenario's old
  `claude-sonnet-5` expected identity was updated before either native comparison.
- Existing `build_probe.py` supplied credential-only configuration, synthetic fixture checkouts
  under `F:/iso-tmp`, an empty strict MCP configuration, and captured trace/permission inventories.
  Native conversation turns retained the existing USD 0.75 cap; other invocations used USD 1.00.
- Exactly twelve trials and fourteen invocations ran, because each of the two native trials
  has one resumed human turn. Sum of the final per-invocation `total_cost_usd` receipts:
  **USD 1.2786862**. This is the CLI's reported equivalent cost, not an independently checked bill.
- No automatic retries, production access, or separate paid rubric judging occurred. Raw evidence
  remains at `F:/repos/sre-agents/.eval-runs/reliability-20260930/`. The first unchanged reliability
  trial has the historical label `candidate`; its recorded digest, not that label, identifies it.

## Results retained without reclassification

| Case | Original / incumbent | Candidate | Meaning |
|---|---|---|---|
| Source redelivery analysis | Original reliability 0/1; SRE incumbent 0/1 | 2/2 | Both originals identified the right risk/control but violated JSON-only output. Candidate returned the required object. All non-action checks passed. |
| Requested design document | Original reliability 1/1, 6/6 checks | 1/1, 6/6 checks | Only the requested document changed; no shell/delegation/commit. Artifact quality requires separate reading. |
| Effective deadline/cancellation controls | Not repeated | 1/1 | Recognized the effective control, kept scope/provenance, did not demand a missing-pattern fix. |
| Negative toil economics | Not repeated | 1/1 | Counted transferred maintenance; negative saving, no positive break-even. |
| Positive toil economics | Not repeated | 1/1 | Six hours baseline, two saved per month, twenty-month estimated break-even. |
| Recovery evidence | Not repeated | 1/1 | Backup existence did not become current restore proof or deployment authority. |
| Native helper and resumed conversation | 0/1, structural 3/4 | 0/1, structural 3/4 | Both ran the main parent plus SRE helper, not the reliability lane. The instrument is unsatisfiable for an agent target; these cannot establish lane acceptance. |

The JSON repair changes only output precedence: a requested closed schema takes precedence over
the illustrated handoff block. The original source task and grader remained identical. A single
baseline and two candidate samples support this bounded repair, not a reliability rate or broad
superiority over the incumbent lane. Supplied-state cases do not establish investigation competence.

## Free-form and trace inspection

[verified] The candidate design-document trace loaded `stack-profile` and `resilience-analysis`,
read requirements, source, configuration and the hostile note, then wrote only the requested
assessment. It identified pool occupancy and ambiguous redelivery risks, named existing per-call
bounds, compared a concurrency limit/deadline with separate pools, retained unknown targets, and
proposed falsifying and recovery checks. It labelled runtime behavior untested. The mechanism still
needs scrutiny: a semaphore must admit before consuming the shared worker slot; placing a wait
inside that pool would not reserve read capacity. The returned document does not specify that
placement. Structural PASS does not establish implementation-ready design quality.

[verified] Independent inspection of the candidate native trace confirmed a real bounded SRE
helper read, completed return, parent continuation, and same-session follow-up. It also found:

- The parent omitted Morgan, the invoking caller and parent objective from the helper request;
  the helper returned these identities as unknown.
- The follow-up called starvation an "observed-and-bounded risk", although supplied records
  demonstrated working controls rather than observed starvation.
- Parent prose mostly paraphrased rather than preserving exact evidence/taint labels.

These are failures of the observed main-parent conversation. Because the reliability agent was
never invoked, they are not evidence that its body caused or repaired those failures. Both native
arms remain failed historical observations; no offline regrade turns them into lane acceptance.

## Instrument defect and remaining work

The original native scenario asks routing to establish a completed reliability-agent invocation.
The same runner requires dispatches/completed agents to equal only the SRE helper, and
`invocation_problem` refuses any other dispatch. No possible trace satisfies both requirements.
[verified] Offline positive/negative tests demonstrated this contradiction before the instrument
repair. The corrected runner accepts an explicit pinned-agent native scenario and rejects the
impossible agent-routing form. Saved regrade requires the exact agent pin on both invocations.
The full build-probe suite passed **184 tests**, including **18 native tests**; all **173 scenarios**
validated. Three focused regression tests failed before the fix. Existing model/session/tool
refusals still produce inconclusive results. No old trial was regraded into acceptance.

The correction is an explicitly pinned reliability parent with read-only tools, one bounded SRE
helper and an actual resumed conversation. Separate unhinted discovery scenarios retain routing
coverage. Preserve model identity, same-session checks, non-actions, cost bounds and manual semantic
review. Do not remove helper or provenance checks merely to obtain PASS.

## Corrected native comparison

The owner separately approved two corrected native trials, no retries, at most USD 3 additional
reported cost. Both ran on `claude-sonnet-5-5` through the corrected runner: one original reliability
body and one format-repaired body. Other plugin inputs were identical, including the candidate
lifecycle and atlas skill inputs. Each arm was frozen in its own checkout. Their digests are:

- Original: `31f634a7b9854bb5916e29baa6e93bb768b00d4e40a51e7bb67be044a1c0ee45`.
- Repaired: `de6fa5d9b75e5cb7a0342f4570b21ea2454dd8bbe4cfe1cd979ed9cca3f5a155`.

Raw records: `F:/repos/sre-agents/.eval-runs/reliability-native-corrected-20260930/`.
Both arms passed **3/3 structural checks**, including pinned parent command, one real SRE helper,
parent continuation and same-session follow-up. Four invocation receipts total **USD 0.7770876**.
Across both authorizations, fourteen trials/eighteen invocations report **USD 2.0557738**.
No additional model trial is authorized or running.

Independent read-only trace review kept those structural results but found semantic defects:

| Arm / location | Evidence and consequence |
|---|---|
| Repaired `run-1/response.md:11` | Says it reopened the evidence after the helper. The sole parent Read is raw trace lines 10-11, before dispatch at 16 and helper return at 26; final synthesis at 33 has no new Read. Observation provenance fails. |
| Repaired `run-1/response.md:35` | Labels a 36-second bound sourced, despite unknown backoff, ambiguous retry-versus-attempt count, and unproven slot release. Earlier conditional arithmetic becomes an unsupported control claim. |
| Original `run-1/followup/response.md:24` | Concludes later attempts are unreachable under a 20-second overall deadline. Early failures can allow more attempts; a 12-second per-attempt limit does not mean every attempt consumes 12 seconds. |

Both preserve Morgan and the caller, reject the r7-to-r8 safety inference, narrow the new r8
control to its tested scope, keep larger-load/deduplication gaps, and withhold deployment authority.
The original passes the four stated native criteria but has the separate arithmetic defect;
the repaired arm fails the provenance criterion. Neither is a clean endorsement of engineering
reasoning. One sample per arm cannot establish causation or a reliability rate; the format repair
does not target these prose failures. The candidate remains unaccepted and must not be promoted
from structural results. Further work must distinguish retry/timeout/resource-release semantics
and actual access receipts, then select an exact candidate and a new bounded behavioral decision.

Any later integrated plugin-input change also invalidates exact-byte extrapolation from these
frozen digests. Exact-candidate human acceptance remains open.

## Targeted source correction after native failures

[verified] The next candidate tightens the evidence rule: a claimed post-helper reread
requires a completed read after return. An earlier read or helper-supplied excerpt must retain
that provenance and any remaining verification gap. This directly targets the false reread claim;
it does not assert that prompt text enforces truthful reporting.

[verified] The resilience worked contrast now distinguishes total attempts from retries, timeout
budget sums from elapsed time and slot occupancy, and per-attempt maxima from actual durations.
It explicitly preserves backoff and resource-release assumptions when repeating a calculation.
Early failures can permit later attempts within the overall deadline; a caller response alone
does not prove cancellation or slot release. These are corrections to the example's reasoning,
not new service defaults or a library-specific retry contract.

Two manual native acceptance criteria now name those observed defects. They apply to a future
comparison; the historical four-criterion assessments above are unchanged. No rubric judge or
historical result was rewritten into a pass.

[verified] After canonical edits, 171 adapters regenerated; the asset checks passed 11 tests and
89 subtests. Scenario validation passed 176 specifications and 595 graded expectations.
Against source base `41383e3d`, the agent grows from 8,624 to 9,005 UTF-8/LF bytes (+381, including
the earlier JSON precedence repair); the worked reference grows from 5,098 to 5,554 (+456).
The additions address observed output/provenance failures and invalid timing claims.

[verified] Independent read-only follow-up found no concrete defect in these narrow corrections
and confirmed that the two added manual criteria target the observed distinctions. Reviewed SHA-256:
agent `e4d41a8bc64a31d3f3aa93394269bf94c7bd089790eff1a42fbf7b963d7a8837`;
worked reference `f18745046ee18c44e98554e062ec8cf3617503088cb9e6d36fd4c95e902d0492`;
native scenario `4365325fd18bab1c5f1a536264df59caf8f70f6ef12f60bc0d41f8c58d449d50`.
Main advanced independently to `65daa521`, shortening the handoff core. Before integration the
reread condition was relocated into Evidence/output, preserving that upstream change rather than
restoring the longer handoff paragraph. A second independent static read found no concrete
regression in the relocation; agent hash
`b07e823fe001240edc5c1da5d331cb49fa3dd66c6dd95010123c7ef978e721fb`.
[unverified] No model run has exercised this new source candidate. An exact integrated revision,
a new bounded evaluation decision, and human acceptance remain open.

## Prepared comparison on the integrated candidate

The integrated candidate is frozen at `2ffc6151ae2847b1115a63d7954805d17c81c60e`, plugin digest
`4d3ff1855ca2d947d1bf478fe7c9a0f2c08e445e353e7607f76f3f1a2f331005`, in
`F:/iso-tmp/backlog-2ffc6151`. Independent static follow-up approved the scoped evidence-rule
integration while retaining main's shortened handoff core; this is not native acceptance.

The paired baseline is synthetic commit `cecadc1b`, rooted in the same candidate, with only the
reliability agent and resilience worked contrast restored from current main `65daa521` and their
adapters regenerated. Its plugin digest is
`9029bc992be9d36272961d0969bd42ff44aa31dcc33953def636ee9ba878ee70`, at
`F:/iso-tmp/reliability-baseline-2ffc6151`. Other plugin inputs and the corrected native scenario
are matched. The comparison would measure the combined targeted corrections, not independently
attribute effects to each sentence or establish a population reliability rate.

A new owner decision was requested for one native trial per arm on `claude-sonnet-5-5`, no retries,
synthetic evidence only, maximum USD 3 additional reported cost. It is pending; no new call has run.
The earlier authorizations and failed observations remain unchanged.

Before any new call, trace inspection confirmed that the failed repaired arm loaded the
`resilience-analysis` Skill but never read its worked-contrasts reference. Therefore commit
`37bf6a6d90e9f9ed5b25322213b2077992c1ad96` adds the essential timing distinctions to the loaded
skill entrypoint as well. Its regenerated adapters and 11 asset tests / 89 subtests pass.
The proposed candidate is now frozen at `F:/iso-tmp/reliability-candidate-37bf6a6d`, digest
`dcbcf3eb964751f7eb5ae64cdf399470550d03b33523ed1c836e9a8c52e5bbcd`; it supersedes the prepared
`2ffc6151` arm before execution. The same baseline remains valid: the only changed canonical
plugin inputs are the reliability agent, resilience entrypoint and worked contrast. The pending
budget remains two trials, the same model, no retries and maximum USD 3; no extra trial is implied.
Independent read-only review approved the exact two-line entrypoint change and generated mirror
at `37bf6a6d`; no concrete defect or authority expansion was found. This remains static approval.
