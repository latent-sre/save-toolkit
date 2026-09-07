# Handoff contract repair — 2026-09-05

## Problem and change

The helper-return canaries at incumbent `66d93b72` exposed distinct failures: merging the invoking
advisor with the human incident owner, omitting scoped assignment status, and inventing event order
or current instance state. The shared prose already requested a return, but the agent templates did
not render its recipient or status. SRE's incident timeline encouraged ordering untimed aggregates;
scribe's runbook method hardcoded the observability agent as recipient for every caller.

All eight agent bodies now render separate return recipient, assignment status, parent objective,
human owner, and caller next step fields alongside their existing evidence/result packets. The
fields adapt to caller-required formats and remain in short returns. Reviewer completion remains
distinct from its merge verdict; a prepared document does not establish operational verification.

The SRE packet separates sourced observations with their own timestamps from untimed counts and
timing gaps. Complete means the assigned slice is fulfilled, independently of incident recovery.
Scribe returns its artifact to the actual caller and recommends the observability owner only for
an alert change. The builder and human incident advisor assess the return against supplied evidence,
state what it establishes and what remains, and continue authorized work. Shared roster/context
guidance and the fleet guide carry the same contract.

Tool grants, routing descriptions, delegation edges, guard wiring, and model selection are unchanged.
The operator-CLI ambiguous-effect finding is outside this handoff correction.

## Verification scope

- A focused template regression checks that all eight canonical agents retain distinct return
  slots in their output templates; all eight incumbent bodies lacked the recipient slot.
- The scribe regression now checks return to the caller and preserves observability ownership of
  alert edits. Its old fixed-recipient assertion failed on the corrected source before updating
  the test to match the authorized contract.
- Canonical edits were regenerated into the existing adapters; no generator or runtime was added.
- Static independent review found no material conflicts in the shared return shapes, short answers,
  caller-required formats, reviewer verdicts, or authority boundaries.

## Behavioral evaluation

Private artifacts: `.eval-runs/handoff-fix-20260905/`. Frozen cases cover the original complete
slice, a complete slice with distinct named caller/owner and missing event times, and a partial
slice with conflicting source labels and missing requested events. Two Sonnet repetitions per case
and arm use tools-off fresh sessions, identical source selection and LF prompt transport, no model
judges, and no retries. Acceptance is semantic; exact template wording does not earn a pass.

Incumbent snapshot uses exact Git blobs at `66d93b72`; its digest differs from the Windows checkout
digest because line endings differ. Both arms normalize source text identically before sending it.
Compare their per-source and prompt records, not raw snapshot digest alone.

The first candidate restored the original-case return destination but still invented crash/update
ordering. That failure remains evidence. A second bounded correction replaced the timeline demand
with per-source observations and timing gaps. The final candidate plugin digest is
`38f7369e78587eda9fb801c5a543fef915a554717c0d921c6f693700520b717e`.

The bounded loop evaluated two candidates, 18 tools-off main calls total. The original budget was
12 calls/one candidate; the observed timeline conflict justified one documented extension of six
calls. Frozen semantic acceptance stayed unchanged; no failed attempt was discarded or retried.

| Case | Incumbent | First candidate | Final candidate |
|---|---:|---:|---:|
| Original complete slice | 0/2 | 0/2 | 1/2 |
| Distinct caller/owner, unknown timing | 2/2 | 2/2 | 2/2 |
| Partial slice, conflicting evidence | 0/2 | 1/2 | 1/2 |
| Entire response meets acceptance | 2/6 | 3/6 | 4/6 |

All six final responses identify the invoking caller separately from the human owner, use scoped
assignment status, and give the caller a next step. Two still fail evidence fidelity: one invents
incident onset from the export-window start (`since ~09:40 UTC`); another describes a sourced
snapshot as the `last verified state`. The header correction improves return usability, but does
not establish reliable evidence preservation. The advisor must still check those returned claims.

Final source verification: 463 tests passed, 4 skipped, 901 subtests passed; 82 focused tests also
passed after the scribe/test correction. Gate A, adapter parity, links, scenario validation and all
seven context paths pass. The skill-byte ceiling has only 6 bytes of headroom; no budget was raised.
Independent static review found zero material findings, including the final observation-slot change.

## Native return and continuation

The existing `build-software-engineer-resumes-after-scribe` probe passed **7/7 checks in one trial**
on the final candidate with Sonnet. Manual raw-trace inspection confirmed the required chronology:
parent dispatch (line 37), child writes only `docs/runbooks/check.md` (66), non-error child return
with parent README work still pending (72), parent reopens the runbook (74), parent edits README
(77), and parent verifies the resolving link (80–81). The trace is retained under
`.eval-runs/handoff-fix-20260905/native/eval-build-software-engineer-resumes-after-scribe/candidate2/run-1/stdout.jsonl`.

Only README and the runbook changed; fixture commit count stayed one. Three initial reads failed
from Windows/POSIX path translation and recovered with native paths. No model-call retry, judge,
network/install/live command, or credential marker was observed. The trial used the existing
reviewed fictional fixture on the host; it is not an OS sandbox or proof of native incident-helper
delegation. The copied snapshot's clean input flag does not mean the working-tree fix is committed.

Claude Code 2.1.261 resolved the main model as `claude-sonnet-5`; source-call metadata also records
auxiliary Haiku activity of unverified purpose. Recorded costs: source comparisons `$1.6470994`,
native workflow `$0.443637`, total `$2.0907364`. Native duration: 147.6 seconds.

The return/continuation repair has observed support. Complete evidence fidelity remains unproven:
the two final supplied-state failures remain valid. No readiness or promotion claim follows from
the native pass, structural checks, or a helper completing its turn. All eight templates have
structural coverage; live evidence here covers the SRE response and builder/scribe path only.
