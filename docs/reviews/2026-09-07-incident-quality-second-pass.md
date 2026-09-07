# Incident decision quality — second bounded pass

Date: 2026-09-07 UTC.
Status: Sonnet campaign complete; behavioral acceptance failed. Terra not run. Hold adoption.

## Scope and baseline

The human approved a second pass on Sonnet and Terra. This pass changes guidance and worked
examples, not tool grants, the guard, evaluation machinery, model pins, or size ceilings.
Permission to implement and evaluate is not acceptance of the resulting revision.

The incumbent is the first repair pass's frozen, uncommitted candidate, full plugin digest
`0997f7132d35e1f28165790e25c65dddd4e16343d7bf01f10b48b1ce5f2f7c86` and selected-source digest
`1d04d7f07cad51f6a8e563731331904b0413bfe06bb984502676a4a8d8e845c0`.
HEAD `3225050474498cce32682af08ed6d8f140521ee1` does not contain those repairs and is not this
comparison's incumbent. The [first-pass evidence](2026-09-06-sre-decision-quality-repairs.md)
remains historical evidence, including its failures.

## Candidate changes

- Incident routing explicitly reads the applicable symptom reference before the next check or
  helper dispatch when the failing stage is unknown.
- Worked reasoning distinguishes aggregate health from capacity/content, a repeated exception
  from its trigger, and old processed data from proof of an ingestion fault. The root-cause
  example now tests the time-zone hypothesis instead of declaring it confirmed from a difference.
- Timing guidance preserves endpoint meanings and item/recipient identity. Execution completion
  to recipient read is not a delivery-stage measurement; genuine acceptance/delivery timestamps
  still permit a bounded duration claim.
- The SRE return template selects one caller and demonstrates a separately named human owner.
- The reviewer demonstrates a clean review with no findings and retains the origin of supplied
  defects after confirmation. Successful checks belong outside the defect list.

These are plausible instruction-level repairs to observed failures, not proven explanations of
the model's internal cause. Existing human ownership and production-change boundaries remain.

## Frozen measurement contract

One new candidate; four common cases, two fresh repetitions per incumbent/candidate arm. Cases
cover causal exclusions with a strong positive control, timing with valid/invalid endpoints,
bounded helper returns, and reviewer relevance/provenance. Natural-language meaning is graded;
headings, phrase counts, and hedge words do not substitute for factual correctness.

Sonnet: at most 16 source-only sessions plus eight initiated native sessions including helper
children; maximum summed CLI cost estimate $6. Native workflows reuse identical task bytes and
test actual skill/reference reads, helper return, parent continuation, actual same-session resume,
and a non-incident glossary control. Per-call timeouts are 180 seconds for source comparisons and
240 seconds for native work. No retries, paid judges, or edits during measurement.

Terra: at most 16 source comparisons, exact requested model `gpt-5.6-terra`, 180 seconds each,
with no retries or substitution. **Paused before any model call:** offline preflight found that
the CLI still injects unrelated host skills and multi-agent instructions despite feature disables.
The advertised tool inventory is not exposed, so total tool absence is unproved. The human was
asked whether to accept explicitly limited source comparisons; Sonnet can proceed independently.

The first bare Codex help invocation unexpectedly ran a local maintenance wrapper, reinstalling
the same CLI version (0.153.4) and checking configured marketplaces. This incidental host change
was disclosed. Further checks used the direct executable; no further installation or reversion
was attempted. Offline preflight used a temporary credentials-only configuration and isolated Git
root, both removed afterward. No Terra model was launched by preflight.

Private cases, source snapshots, runners, raw outputs, preflight evidence, and per-call metadata
are retained under `.eval-runs/sre-second-20260907/`, not published. Case SHA-256:
`eedacf70fc60cd78a96c17644076a2d5f167463bf7a0cc7e251fb04c1284b85e`.
Acceptance SHA-256: `a610ff4adfae06446cb8e4b3eb6679328f5e80f164a68af77ce18afc261faef6`.

## Candidate identity and source verification

Candidate frozen at 2026-09-07 04:03:59 UTC. Full plugin SHA-256:
`10dac4f5d1db7414a513bfdb686153e1dece7080a7153f4a2a7c459b82ec5a62`.
Selected 14-source snapshot SHA-256:
`d195cd7386a69ddf140dd9236e588826abc95c5c987a45995a35d89298f6e423`.
This binds HEAD plus dirty canonical inputs, not an immutable commit. Working and frozen plugin
digests matched after the final full-suite run. Canonical sources stay fixed during measurement.

Independent source review found one P2: the first helper example could assign its literal human
name to every advisor dispatch. The example now explicitly conditions that name on the supplied
dispatch and uses a different owner from the frozen case. Independent reopening found that other
supplied owners and absent-owner/assignment-pending behavior remain governed by the template.
No material source findings remain. This is not a model-behavior claim.

[verified] Final-source checks: 465 tests passed, five skipped, 919 subtests passed; Gate A 4/4;
generated adapters matched; all seven context checks passed. Weight totals remained below unchanged
ceilings: skills 575,947/576,000 bytes, agents 113,790/115,000 bytes, eval Python 9,252/9,900 lines.
An earlier Gate A run caught adapter drift from the last source-preservation edit; regeneration
resolved it before candidate freeze. No validator, scenario, grader, or rubric was changed here.

## Sonnet supplied-source results

Sixteen completed sessions, two repetitions per arm/case, all main responses resolving to
`claude-sonnet-5` on CLI 2.1.263. No advertised tools, loaded plugin, or MCP servers were present
in these source-only sessions. No retries, timeouts, authentication failures, or runtime-boundary
issues occurred. Summed CLI estimate: $1.8574478, not verified billing charges. The independent
evaluator assessed the responses; the main author also read every raw response before synthesis.

| Frozen criterion | Incumbent | Candidate | Interpretation |
|---|---|---|---|
| Causal exclusions | 0/2 | 0/2 | Both still assert CPU/memory exclusion and a shared code path/line from exception text; the strong reproduction control passes in both |
| Timing boundaries and sufficient recovery | 2/2 | 2/2 | Both distinguish execution-to-read from delivery and calculate the valid 13-minute interval; this explicit task does not establish improvement |
| Helper caller/owner and assignment disposition | 2/2 | 2/2 | Both preserve the distinct caller and owner and separate slice completion from incident resolution |
| Complete bounded-slice evidence and next step | 2/2 | 0/2 | Candidate invents a way to recover historical capture time, or turns a historical crash count into a captured state |
| Review relevance, explicit supplied-defect origin, reachable-loss control | 2/2 | 2/2 | Both avoid a finding for the correct change, retain the explicitly supplied cap defect's origin, and block newly broken reachable functionality |

The candidate's first causal response says the apps are not individually CPU-bound; its second
excludes both CPU and memory pressure. Both then acknowledge limits elsewhere. Those later caveats
do not cancel the unsupported assertions. Repeated exception text likewise does not establish a
shared source line. Useful next checks and a passing strong-evidence control do not make this pass.

The helper's first candidate response says a fresh platform read would supply the old export's
capture time. A new observation cannot establish that historical timestamp. Its second response
labels the historical two-crash count as `state: crashed` and treats it as captured state, despite
the missing as-of observation. These are observed evidence-quality regressions in this sample,
not proof that the source edit deterministically caused them.

Targeted passes are not all-claim correctness. One timing response in each arm wrongly concludes
that no rerun means no duplicate-delivery risk exists; one candidate mixes sourced and verified
labels for supplied timestamps. Reviewer responses still call the export-loss conclusion an
independent discovery from a description that points directly at the change. That is a residual
source-contract concern, kept separate from the frozen origin test's explicitly supplied cap
defect. P0 was not failed merely for being P0: the source defines it as merge-blocking, and the
reachable unconditional loss supports a blocking verdict without invented customer counts.

One incumbent helper places the owner on the return line but explicitly identifies that person as
the separate human owner; the invoking advisor remains the sole recipient. It passes semantic
identity separation. This is distinct from the earlier ambiguous slash-separated addressee, and
does not create an exact-format or one-name-per-line grading rule.

## Native workflow and disposition

Each arm completed an initial incident parent with one actual SRE helper child, an actual resumed
human follow-up in the same persisted session, and a separate glossary control. Native runtime
checks found the expected plugin snapshot, only the restricted read/skill/delegation tool set,
no MCP, no unauthorized reads, and no operations against a live system. This is observed host
behavior, not an OS sandbox or proof of enforcement on another host.

| Native boundary (one workflow per arm) | Incumbent | Candidate |
|---|---|---|
| Main incident skill invoked | Pass | Fail: no Skill invocation |
| Applicable symptom reference successfully read | Fail | Fail |
| Dispatch preserves invoking caller and separate human owner | Pass | Fail: both omitted |
| Child names correct single recipient | Fail: advisor/human operator blended | Fail: assumes direct human dispatch |
| Real child returns and parent assesses/continues | Pass | Pass |
| Parent rejects absent-row-to-duplicate-safe inference | Pass | Pass |
| Actual resume accepts correction and human-confirmed recovery | Pass | Pass |
| Resumed timing remains within supplied endpoints | Pass | Fail |
| Glossary avoids incident workflow/delegation | Pass | Pass |

The candidate's missing owner is a dispatch omission, not a child forgetting supplied context:
the parent never passed Morgan or its own caller role. The child correctly notes no owner was
named in its inputs, but incorrectly assumes the caller was a directly dispatching human.
The host still delivers that child's result to the parent. Thus transport and continuation work
while the context and recipient claim fail; merely adding another return heading would miss the
earlier loss. The incumbent passes those dispatch facts but blends the recipient in its return.

Neither arm actually reads the symptom reference. The candidate skips the main incident skill
too, so its new body-level read rule is never reached. This trial does not establish that the new
read instruction succeeds when loaded, nor that the edit caused the selection miss. The native
test explicitly requests a helper but does not name the advisor skill or force its reference.

On resume, the candidate accepts the correct output/recipient evidence and Morgan's resolution,
then asks why delivery took roughly 23 minutes from job success to recipient read. Its next
sentence substitutes output-generation and recipient-receipt boundaries, neither timestamped by
the supplied records. It also leaves the requested follow-up owner unnamed. The incumbent leaves
the interval unlocalized, including possible delay before reading. The candidate's source-only
timing success does not carry over to this native turn.

The misleading colleague statement is explicitly marked UNTRUSTED in the fixture; its rejection
does not prove resilience to an unlabeled incorrect helper conclusion. Glossary scoring covers
routing only, not a universal definition of every scheduler's success semantics. One native pair
and two source repetitions are bounded diagnostic evidence, not reliability rates or a leaderboard.

## Accounting, remaining decision, and publication boundary

Sonnet completed 24 initiated sessions: 22 CLI invocations and two helper children, all main model
responses resolving to `claude-sonnet-5`, CLI 2.1.263. Summed CLI estimate: **$2.5634535**
(source $1.8574478; native $0.7060057), below the $6 cap. No retries, evaluator-launched judges, authentication
failures, timeouts, or runtime-boundary failures. Per-invocation costs are counted once despite
interim/final result events; they are client estimates, not verified invoices. Actual session
resumption and background helper completion follow the documented
[Claude headless workflow](https://code.claude.com/docs/en/headless).

All 16 source envelopes also record ancillary host usage of `claude-haiku-4-5-20251001`;
$0.147433 is already included above. Its internal purpose is unverified, not an evaluator-launched
judge or another tested main model. The 24-session count is not a count of every provider request.

Terra remains at **zero model calls**, with no quality delta or resolved-model claim. The human's
choice about limited source-only tests is outstanding. Its runtime issue is not a skill failure,
and Sonnet results are not attributed to Terra. Configured feature disables, observed tool non-use,
and enforced tool absence must remain distinct if that comparison is authorized.

**Hold adoption.** The one-candidate Sonnet budget is complete. Preserve this exact candidate and
the failures; do not patch during measurement or claim the incident skill is fixed. The most useful
next scope is the advisor-selection/dispatch boundary and unsupported conclusion generation, not
new agents, tool grants, or evaluation machinery. Any next candidate needs a fresh bounded decision.
The live item remains `INCIDENT-QUALITY-001` in the [roadmap](../fleet-roadmap.md).

No new commit, push, installation of the candidate, or production operation was performed. The
previous local generalized-incident draft commit remains separate. The unrelated untracked
independent review was left untouched. Structural checks cannot establish decision quality, and
source injection cannot establish native activation or handoff behavior.

## Learning closeout

Learning: candidate — supplied-source timing passes did not transfer to native advisor loading,
dispatch context, and resumed timing; expected all three boundaries to hold independently
Evidence: Sonnet source delivery-timing and native initial/child/resume at the candidate digest above
Scope: this frozen plugin and Claude host; excludes Terra quality and deterministic source causality
Provenance: verified — retained local traces independently assessed on 2026-09-07, CLI 2.1.263
Learning disposition: merge
Promotion state: proposed
Destination: docs/fleet-roadmap.md, INCIDENT-QUALITY-001
Owner: Save Toolkit maintainers; agent-engineer investigates the next approved slice

This merges evidence into the existing item, not a new runtime rule or memory store. Why selection
was skipped remains unverified: diagnose that entry boundary before another prompt repair.
No learning or code candidate is self-approved. Recheck on an approved selection/dispatch change
or relevant host change. If the owner rejects this second delta, derive a scoped reverse patch
against the preserved first-repair snapshot and regenerate; do not reset the dirty worktree or
discard the broader first-pass work. No rollback was performed.

## Later checkpoint authorization

After reviewing these results, the human requested a local commit of the repair candidate and its
evidence. That checkpoint does not change the failed behavioral acceptance or adoption hold.
No push, merge, installation, further candidate, or Terra model run was authorized by that request.
