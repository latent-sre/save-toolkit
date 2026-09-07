# General incident help — 2026-09-06

**Disposition: reviewable draft; hold adoption.** The reference is implemented and statically
reviewed, but the small behavioral sample retains material errors and a missed-job regression.
The published branch remains unchanged; these findings do not authorize promotion.

## Scope

The approved first version helps a human responder choose a useful next observation when the
platform, failure location, service card, or telemetry is unknown. A conditional reference in
`incident-investigation` covers login failures, intermittent errors, slow requests, stale/wrong
data, and missed jobs. It supplies comparisons and their interpretation limits, plus a worked
exchange that continues after an inaccessible observation. It is a selection aid, not an intake
checklist or a replacement for the parent skill's evidence and human-ownership rules.

The advisor now uses the team-stack fallback only for known team-stack services. An unknown
environment starts with available observations before platform-specific instructions. No routing
description, agent authority, tool grant, or operational workflow changed. Platform commands and
navigation remain owned by the existing platform skills.

## Independent review

Static review found two diagnostic ambiguities before candidate evaluation. The login row could
conflate pre-completion authentication failures with reachability; it now distinguishes reaching
the page, submission/MFA, callbacks, and post-login denial. The intermittent row could treat an
attribute shared by a successful and failed request as discriminating; differences now supply leads
to confirm and shared attributes are explicitly non-discriminating. Both corrections were rechecked
without remaining findings in those rows.

## Size and verification

The new reference is 4,649 bytes. Together with the entrypoint changes it adds 4,975 skill bytes.
No existing examples or evidence rules were cut to make room. The skill ceiling increases from
571,000 to 576,000 bytes; the measured total is 575,969 bytes, leaving 31 bytes of headroom.

The PCF human-path accounting includes the full optional reference, even though a narrow known
failure may not need it. Measured context increases from 63,745 to 68,720 bytes. Its ceiling changes
from 64,000 to 73,000 using the existing measured-usage-plus-five-percent, rounded-to-1,000 policy.
Other context paths, agent and eval ceilings, and description bytes are unchanged. This is an
explicit cost allocation for the new human-facing reference, not a model-performance claim.

Existing link, adapter, fleet, weight and context tests: 135 passed, 3 skipped, 191 subtests passed.
Scenario validation: 65 specs and 324 expectations; no shipped grader or scenario changed.
Adapters were regenerated from canonical sources. Final focused verification repeated on the frozen
candidate: 135 passed, 3 skipped, 191 subtests passed. Gate A and whitespace checks pass.

## Behavioral protocol

Private artifacts: `.eval-runs/general-incident-20260906/`. Five two-step fictional conversations
and semantic acceptance were frozen before candidate review: login with limited access, an
intermittent save error with possible effects, slow UI searches, stale stock data, and a possibly
missed scheduled job. Each follow-up tests whether the advice uses new evidence and avoids
repeating an unavailable or completed check.

One incumbent and one candidate conversation per case: twenty Sonnet main calls total, no retries
or model judges. Each response is a fresh tools-off process. Step two receives the actual first
response plus a fixed follow-up; this reconstructs conversational context and does not test native
session continuity, skill discovery, or live tools. Cases are known regression/control cases, not
blind held-out evidence. Scores require feasible advice, useful outcome distinctions, faithful
facts and uncertainty, proportionality, and preserved human authority.

Incumbent is Git revision `dfc60311b40d1f4f990014eb1d139810fe7ae8f8`. The final candidate is the
working-tree plugin snapshot with digest
`d98932d088a76bbf83d4e39a4e7e04b93428cbd0a4ef574a59a695fd249aade7`.
Both arms use normalized LF source text and stdin transport; retained hashes identify their exact
inputs. Structural checks do not establish model reliability.

## Results and limitations

All 20 calls completed on Claude Code 2.1.263 with main init/assistant model `claude-sonnet-5`.
There were no model retries, judge calls, timeouts, runtime/boundary failures, tools, plugins or MCP
servers observed. Auxiliary Haiku usage appears in modelUsage; its purpose is unverified. Recorded
cost: `$1.711300`; cumulative call time: 392.829 seconds, excluding approval waits and interruptions.
The interruptions occurred before launch and between arms; completed calls were not replayed.

| Case | Incumbent passing steps | Candidate passing steps |
|---|---:|---:|
| Login without telemetry | 1/2 | 2/2 |
| Intermittent Save errors | 0/2 | 1/2 |
| Slow UI searches | 0/2 | 1/2 |
| Stale customer data | 0/2 | 0/2 |
| Possibly missed statement job | 1/2 | 0/2 |
| Total response steps | 2/10 | 4/10 |
| Both steps correct in a conversation | 0/5 | 1/5 |

The candidate gives useful ticket/UI comparisons, but unsupported conclusions remain alongside
them. Examples: visible draft counts treated as proof of idempotency; a generated-at timestamp
treated as fresh file contents; UI search scope treated as proof of an unbounded backend query;
missing scheduler history or a past next-run timestamp treated as proof that a job did not fire.
The missed-job first reply passed only in the incumbent. These are material interpretation errors,
not failures for using the wrong heading or asking several fields needed for one comparison.

Manual assessment and per-step quotes are retained in
`.eval-runs/general-incident-20260906/assessment.md`. Provisional concerns about question counts and
formal test-account isolation were not used as additional failure criteria. No frozen criteria or
response was changed. A helpful check does not cancel an unsupported claim that could misdirect it.

Each arm explicitly received available references as data; conditional reference loading and native
session continuity were not exercised. Second-step histories differ because they include each arm's
actual first answer. Temporary directories were outside the repository, with scrubbed config and
credentials, but were not initialized as separate Git roots; ancestor-instruction isolation is not
independently established. The observed tool/plugin/MCP inventories were empty.

This single small sample does not establish reliable improvement or suitability for live incident
decisions. The proposed next refinement is narrower observation-to-conclusion guidance for time,
missing records, and uncertain effects, keeping these cases as regressions and testing new variants.
No second candidate or additional calls were performed. The user subsequently authorized committing
this draft for preservation; that does not establish behavioral acceptance or authorize promotion.
