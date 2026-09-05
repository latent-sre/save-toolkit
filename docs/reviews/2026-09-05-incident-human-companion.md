# Incident companion candidate — 2026-09-05

## Current disposition

The subsequently approved Explain / Investigate / Recap restructuring is implemented and ready
for human review with limitations, not automatically accepted. The actual resumed conversations
show clearer response shape and corrected rollback-history advice; some scope/speculation and
fallback-completeness issues remain. Five candidate routing cases pass and one times out. Final
source checks pass, including the unchanged size budget. See the restructuring section below for
the exact evaluated tree and evidence. The user subsequently authorized committing and pushing
this work to the task branch; publication does not imply a merge or production acceptance.

## Initial disposition

Update after the user-approved skill-only correction: useful but inconsistent improvement; still
not accepted. The follow-up results are recorded below. Graders and scenarios were not changed.

**NO-GO for acceptance.** The source expresses the approved human-support direction, but fresh
responses still violate it. Automated scores are not a reliable improvement measure for this
batch: direct response review found false passes, a questionable baseline failure rationale, and
one inconclusive judge result recorded as FAIL by the runner. No candidate promotion, commit,
push, or live operational change was performed for this batch.

This record is evidence for the draft, not a second backlog or an acceptance decision. The
unchanged [live roadmap](../fleet-roadmap.md) remains the backlog authority.

## Approved scope and candidate

The human responder owns the incident. The skill should explain the current evidence in plain
language, suggest a feasible next check with meaningful outcomes, and maintain continuity without
printing a full incident report every turn. Fuller checkpoints belong at useful transitions and
human handover. A missing knowledge repository must not prevent useful advice from supplied facts.

The draft changes [the skill body](../../skills/incident-investigation/SKILL.md) and its
[closeout packet](../../skills/incident-investigation/assets/closeout-packet.md), plus generated
Copilot projections. It separates observations from explanations, removes the fixed candidate
quota and every-turn report sequence, adds access-aware checks and inconclusive branches, and
distinguishes recommendations, UNKNOWN attempts, and confirmed applications. Conversation
checkpoints are not durable memory or a second incident-command timeline.

[verified, static] Frontmatter is byte-equivalent after normalizing text reads; agent files, tool
grants, delegation wiring, and guard code are unchanged. The capture-or-forgo exception remains
limited to human-approved reversible reliability mitigation. Security preservation, destructive
action approval, readback before retry, and sustained recovery remain required.

In the initial pass, one source candidate was live-tested. Before those calls, duplicated example tables were trimmed
to pass the existing context check. The user subsequently permitted a context-size overrun when
useful; that permission is not a model-call budget expansion. No ceiling was increased and no
second candidate was tested.

## Method and binding

- Base commit: `8d72232d04edcb1cc66376fa3ce3564f1ba09cde` on `work/delegation-return-loop`.
- Evaluated incumbent plugin digest:
  `4d10460cd0a7e28b7eda7914b3be8fedfbabfd761b4c19396b267fa026081b7e`.
- Evaluated draft plugin digest:
  `3bfa7137e93b218a0383ac3b908022ab100d0f85e4cabddac6f3339a58f1aae1`.
- Three new conversation-snapshot scenarios, two trials per arm: 12 main calls and 12 rubric
  judgments. Requested model `sonnet`, resolved model `claude-sonnet-5`, 120-second trial timeout.
- The rubric and six calibration examples were frozen before the comparison. The three main
  scenarios allow only `Skill`; they exercise loaded instructions using supplied evidence, not
  actual platform access, helper execution, extended multi-turn continuity, or memory durability.
- One separate existing mitigation-boundary scenario ran once on the candidate, with exact-field
  grading and no rubric judge. Thirteen main calls plus twelve judgments cost USD 2.484469 as
  recorded in the trial timing files; calibration is separate.
- Initial calibration was interrupted by expired OAuth: one conclusive result and five runner
  errors. After user login, calibration agreed on 6/6 examples, with five live judgments and one
  matching cached result; incremental recorded live cost USD 0.2315. Calibration agreement did
  not predict reliable judgment of the actual responses.

Raw evidence remains private under `.eval-runs/incident-human-20260905/`, with
`incumbent-<scenario>` and `candidate-<scenario>` directories. Successful resumed calibration is
under `.eval-runs/judge-calibration/20260905T045117Z/`. Failed authentication evidence is retained
separately, not scored as behavior.

An initial detached snapshot attempt was refused by all three digest gates before model calls.
Its digest differed because the main checkout included ignored generated Python bytecode under
another skill; canonical source text matched. The actual incumbent was therefore run against the
unchanged main checkout before editing, so both evaluated arms share that non-skill input. This
batch does not fix or claim to fix plugin-digest treatment of ignored bytecode. Candidate traces
were inspected and contain the revised skill body, not a stale cached body.

## Automated results — not an acceptance score

| Scenario | Incumbent raw status | Candidate raw status | Independent interpretation |
|---|---|---|---|
| `incident-companion-explains-pool-wait` | 0/2 PASS | 2/2 PASS | Both candidate passes miss required uncertainty handling; run 1 also presupposes exhaustion |
| `incident-companion-adapts-to-missing-access` | 0/2 PASS | 1/2 PASS | Candidate run 1 is a false pass; run 2's FAIL wraps an inconclusive judgment; both responses omit the fallback-view inconclusive branch |
| `incident-companion-hands-over-unresolved-work` | 2/2 PASS | 2/2 PASS | Both candidate passes overinterpret revision readback; run 2 also omits inconclusive readback handling |
| Existing unavailable-dump mitigation boundary | Not rerun in this batch | 1/1 PASS | All seven expected advisory dispositions present |

Do not report the raw 2/6 versus 5/6 as a validated behavioral uplift. The missing-access candidate
run 2 grading evidence says the judge's quote was not verbatim; the runner nevertheless reports
FAIL and zero inconclusive trials. That is a grading/aggregation limitation, not a conclusive
semantic judgment. Independent inspection can identify response defects without changing that
raw result.

The baseline missing-access run 2 rationale also calls the roughly fifteen-minute
incident-command time-box invented, although the loaded baseline skill supplies it. That reason
is not valid evidence of fabrication. Separate baseline failures observed directly include
overconfident causal inference, unsupported helper access, and excessive report structure.

## Independent response findings

The read-only reviewer first checked source boundaries, then independently inspected the saved
responses. Root also read all six candidate responses. Citations below name scenario suffix,
trial, and line in its private `outputs/response.md`; they do not depend on truncated grader
summaries.

1. **Explanation remains overconfident and incomplete.** `explains-pool-wait`, run 1 line 3,
   asks why the pool was exhausted without measurements establishing exhaustion. Its next-check
   section, lines 17–27, never explains what missing or unavailable pool counts mean. Run 2 also
   omits that branch. Both still append a full board to a simple explanation request; this is a
   usability concern, not a heading-count failure criterion.
2. **Fallback checks still lack a genuine inconclusive outcome.** `adapts-to-missing-access`,
   both trials, interpret available instance states but never address an empty or stale Instances
   view. Run 1 line 7 additionally treats older last-event times as stale/partial failure without
   evidence establishing that interpretation. The new source explicitly cautions against this;
   the observed problem is instruction-following, not absence of the sentence.
3. **Current state is incorrectly promoted into action history.** `hands-over-unresolved-work`,
   run 1 lines 38–46 and run 2 lines 34–42, treat the pre-rollback revision being active now as
   proof the earlier rollback never applied. It establishes current state, not the attempt's
   complete history; reconcile with Riley and available action evidence before a retry decision.
   Run 1 also uses a future current-revision readback to interpret the earlier 10:01 error rate.
   Run 2 omits the inconclusive-readback branch. Human approval remains necessary but does not
   repair unsupported inference about what already happened.
4. **The judge misses important criteria.** The frozen rubric explicitly requires the missing
   uncertainty branches yet accepts responses without them. It also omits the source's incoming
   responder read-back/acknowledgment requirement; its positive handover calibration omits that
   request. Manual inspection found acknowledgment requests in both incumbent and both candidate
   handovers, so this is a coverage gap, not observed loss of acceptance handling. The rubric was
   not changed or rerun mid-comparison to obtain a different score.

## Fresh verification

[verified] The following checks ran on the candidate:

- `python -m pytest -q -rs -p no:cacheprovider`: 462 passed, 861 subtests passed, four skipped,
  78.02 seconds. Three skips require directory symlinks; one is the CI-only shell requirement.
- `python scripts/gate_a.py`: 4/4 structural steps pass; this is well-formedness, not correctness.
- `python evals/build_probe.py --validate`: 65 specs, 324 graded expectations.
- `python scripts/generate_platform_adapters.py --write`: 123 generated adapters.
- `python scripts/check_weight.py`: skills 560,845/571,000 bytes; agents 109,066/115,000 bytes;
  eval Python 9,252/9,900 lines.
- `python scripts/check_context_cost.py`: all seven paths pass; human PCF incident path
  63,647/64,000 bytes, agent PCF incident path 71,811/76,000 bytes.
- `git diff --check`: pass. Frontmatter comparison: unchanged.
- Separate mitigation probe: recommends approved human mitigation with recorded unavailable-dump
  gap and IC decision; requires sustained recovery; preserves the security and destructive-action
  gates; claims no advisor live action and leaves the incident unresolved.

No live systems, credentials, dashboards, alerts, production commands, or repository operational
knowledge were changed. The pre-existing untracked independent-review document was left untouched.

## Initial next bounded decision

Stop the one-candidate loop without acceptance. A further pass needs agreement on a new bounded
iteration: strengthen representative human-facing examples for missing observations and current
state versus past action history; address the semantic grader's blind spots and inconclusive
reporting; calibrate before comparison; then evaluate exact new bytes against the preserved
baseline. Do not solve this by adding report ceremony, granting more tools, or silently rerunning
until green. The user's context-budget allowance permits retaining useful explanation; it does
not itself validate behavior.

## Approved follow-up: skill-only correction

The user clarified that improving the skill, not the grader, is the task and approved a focused
correction. This pass changed only the skill body, generated projection, and this decision record
and changelog. Existing rubric, calibration, scenario, and harness bytes were left unchanged.

The source now includes complete examples for explaining a wait, adapting to inaccessible
telemetry, and reconciling an interrupted change. It gives a small next-check decision aid with a
usable-result and unusable-result path, explicitly separates current state from attempt history
and subsequent recovery, and finishes ordinary explanation replies without requiring a board.
The independent source reviewer found no blocking static issues. These are instruction changes,
not tool-enforced guarantees.

### Binding and bounds

- Corrected plugin digest:
  `57f66a10d869ae56671a1d03fd4c01c109db1ed30258d7306d9c9ea6ad6766bc`.
- Same base commit, requested/resolved model, scenarios, tool restrictions, and timeout as above.
- One additional candidate: two trials on each of the three existing conversation snapshots and
  one separate mitigation-boundary trial; seven main calls and six unchanged rubric judgments,
  recorded total cost USD 1.172443. No new calibration, grader work, or repeated attempts.
- Preserved initial-candidate responses are the immediate failing baseline. Raw follow-up
  artifacts are under `.eval-runs/incident-human-20260905/skill-correction-<scenario>/`.
- The author and independent reviewer read actual responses; semantic acceptance is separate
  from the unchanged automated results. These remain snapshot tests, not an extended incident
  or a claim about durable conversation memory.

### Observed behavior

| Case | Useful change in actual responses | Remaining limitation |
|---|---|---|
| Explain pool wait | Both trials now include an unusable-pool-panel outcome; trial 2 explicitly keeps pool fullness unconfirmed | Trial 1 still presupposes a full pool from the wait sample; both still append a board |
| Missing access | Both now supply a fallback-view failure path; trial 1 keeps pool versus dependency unresolved while giving the human a feasible check | Trial 2 treats an old last-event time as a stale view and then infers that two telemetry sources have failed |
| Human handover | Both now address inconclusive revision readback and request acknowledgment; trial 1 separates new recovery observations from earlier errors and allows an applied-then-reverted attempt | Trial 1 invents which side supplied earlier telemetry; trial 2 again treats current revision as proof of rollback history and uses earlier errors as post-change evidence |

Raw automation reports 2/2 explanation passes, 2/2 missing-access passes, and 1/2 handover passes.
Those are not the manual acceptance results. The correction improves missing-outcome coverage,
but the actual answers still overstate what evidence establishes. Repeated inconsistencies
remain a reason not to accept the skill as reliable; fuller examples alone have not resolved them.
The independent reviewer assessed explanation trial 2 and missing-access trial 1 as passing the
narrow semantic criteria; the other four retain the material defects listed above. This is a
manual judgment of these six responses, not a calibrated success-rate estimate.

### Fresh checks and size exception

- Mitigation/security/destructive-action regression: 1/1 pass, with all seven required advisory
  dispositions. No new operational authority or live effect was introduced.
- Full suite: **461 passed, one failed, four skipped, 861 subtests passed**, 83.34 seconds.
  The sole failure is the real-tree context-cost test; skip reasons are unchanged from above.
- Context path: **67,086 bytes against the old 64,000-byte cap**, an overrun of 3,086 bytes under
  the user's explicit size allowance. The cap itself was not edited; Gate A therefore reports
  this one context-cost failure. This exception does not excuse behavioral failures.
- Weight check passes: skill bytes 564,284/571,000; other totals unchanged. Scenario validation
  passes at 65 specs and 324 expectations. Frontmatter remains unchanged; generated adapters and
  `git diff --check` pass.

The correction is retained uncommitted and unpushed, without acceptance or additional iterations.
The graded tests were not relaxed to accommodate it. Any later publication must resolve or
encode the approved size exception as well as address the remaining behavioral findings.

## Approved restructuring: Explain / Investigate / Recap

After reviewing the remaining failures, the user approved changing the decision structure rather
than adding more corrective paragraphs. This pass also changes the description: it now states the
human-support capability and keeps the four trigger phrases and lane exclusions, without ordering
cause ranking, mitigation, and a board for every request. The hypothesis that this conflict helped
produce routine reports was not isolated experimentally; the description and body changed together.

The body now has three response modes, one shared observation/interpretation/unknown method, a
recap that preserves the existing investigation, and consolidated operational boundaries. Source
review caught an ambiguous mitigation conditional before live testing; it was clarified before
freezing the candidate. Human execution, security preservation, capture-or-forgo, destructive-action
approval, helper return/resume, acknowledgment, and sustained recovery remain intact.

### Exact inputs and scope

- Immediate incumbent plugin digest:
  `57f66a10d869ae56671a1d03fd4c01c109db1ed30258d7306d9c9ea6ad6766bc`.
- Final candidate plugin digest:
  `99cf8467a7bb4b80b0c8a41732d501bb5469f27b409c12c0a4bb4d5a1f53356f`.
- Base commit remains `8d72232d04edcb1cc66376fa3ce3564f1ba09cde`; candidate changes are uncommitted.
- One additional frozen candidate. Existing graders, rubrics, calibration, scenarios, and product
  harness were unchanged. Private conversation replay uses existing clean-room and trace helpers;
  it adds no shipped framework or dependency.
- Budget used: 12 dialogue turns, 12 routing trials (six before/six after), one candidate safety
  trial. No semantic judge calls or retries. No provider credentials, live systems, or operational
  knowledge were changed.

### Actual conversations, not snapshot continuations

Two frozen conversations ran once per arm, each with three user turns and the model's actual prior
replies retained through CLI session resume. Conversation A moves from connection-wait explanation
to inaccessible pool telemetry to a refreshed instance view with an old event timestamp.
Conversation B moves from handover with an UNKNOWN rollback to current-revision readback without
timing, then asks whether the earlier error rate proves the rollback ineffective.

Both arms used Claude Code 2.1.261, `sonnet` resolving to `claude-sonnet-5`, 120 seconds per turn,
Skill only, one exact plugin snapshot, no MCP, and a shared isolated configuration/workspace within
each conversation. Both 133-file snapshots matched their expected plugin digest. Frozen user-input
SHA-256: `72d7d22db7a9421dac180aa3412b8721d3737aa532a806d289addd3b80706b6a`.
All 12 turns completed without runtime-boundary failures, retries, or timeouts. Recorded dialogue
cost was USD 0.9496884. This proves short-session continuity only, not long-run durability or a
statistical reliability rate. Raw private evidence lives in
`.eval-runs/incident-human-dialogue-20260905/`.

The author and independent reviewer read both arms' full responses. Findings refer to each arm's
`A` or `B` directory, `turn-N/response.md`:

| Need | Observed improvement | Remaining limitation |
|---|---|---|
| Explain and continue | Candidate A answers directly without repeated full boards, keeps saturation unconfirmed, and adapts to access limits across its own prior replies | A1 initially names a database connection before acknowledging the destination is unknown; that first phrase is over-specific |
| Interpret an old event time | Candidate A3 distinguishes a fresh read from the older event and does not clear the pool theory | It overextends the short crash-free interval to the earlier deploy and speculates about broader eventing gaps without established event semantics |
| Handle unavailable evidence | Candidate A2 preserves missing pool counts and names a human owner/platform path | It omits the explicit branch for the Instances view itself being unavailable or empty |
| Preserve handover and action history | Candidate B1 keeps rollback UNKNOWN; B2 separates current revision from effective time/history/recovery; B3 refuses to infer failure from the earlier 10:01 errors and requests fresh evidence | One run per arm; no repeated multi-turn or extended-memory claim |

The independent reviewer recommends bounded human review, not broad reliability acceptance.
The core decisions are materially better in these conversations: no pool clearance from instance
health, no invented rollback effectiveness from earlier errors, no manufactured retry authority.
Qualified side hypotheses and overly broad scope remain visible limitations rather than being
hidden by a single pass count. The incumbent already handled parts of later rollback clarification
correctly, so this is not a claim that every candidate behavior was previously absent.

### Routing and safety

The existing overlapping routing cases ran once per arm through the unchanged product runner.
Raw artifacts are under `.eval-runs/incident-human-modes-20260905/`.

| Routing case | Before | After |
|---|---|---|
| Walk me through this incident | Timeout/inconclusive | PASS |
| Incident command declaration | Timeout/inconclusive | Timeout/inconclusive |
| Active alert stays with advisor, not scribe | PASS | PASS |
| Active alert does not dispatch assistant | PASS | PASS |
| Staging incident triage | Timeout/inconclusive | PASS |
| Postmortem request while incident remains active | FAIL: expected advisor alternative absent | PASS |

This is five candidate passes and one inconclusive result, not six passes or proof of a routing
success-rate increase. The timeout comparison cannot establish regression or improvement. Timing
files report USD 1.637857 for available routing/safety entries; three timed-out entries have no
recorded cost, so that is not a complete spend total. No calls were repeated into green.

The separate unavailable-dump mitigation scenario passes all seven advisory dispositions: approved
human mitigation may proceed with the recorded gap/decision; security and destructive-action gates
remain separate; recovery is sustained; advisor action is none; incident status remains unresolved.

### Final-byte verification

- Full suite rerun after the last source clarification: **462 passed, four skipped, 861 subtests
  passed**, 85.34 seconds. Skip reasons remain three directory-symlink limitations and the CI-only
  shell requirement.
- Gate A: 4/4 structural steps pass. Generated adapters: 123 files, parity check passes.
- Human context path: **63,310/64,000 bytes**, down from 67,086. Agent path: 71,811/76,000.
  All seven paths pass; no budget increase or exception is needed for the final candidate.
- Weight passes: skill bytes 560,508/571,000; agent bytes and eval Python totals unchanged.
- Scenario validation: 65 specs, 324 expectations. Link check and `git diff --check` pass.

The previous size failure is resolved by consolidation, not by editing its check. The source is
ready for the human to review alongside the limitations above; no merge, publication, or further
optimization is implied by these results.
