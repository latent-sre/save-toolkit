# Context and handoffs

Compression, compaction, and handoff are the easiest places to silently upgrade a label; the
entrypoint's label rules apply at each.

## Sending

Send a cold-start packet, not a transcript: invoking caller and human owner separately, intent,
source/state, success criteria, scope, source trust, unknowns, and the return fields the receiver's
agent body defines. Preserve targets, windows, observed values, and [verified], [sourced],
[unverified], [UNTRUSTED] markers.

Bind evidence to its subject, method, source, and time. Reading export E verifies its bytes;
`[sourced] export E reports 4/4 at 09:40` does not verify current health. Missing chronology or state
stays unknown.

## Receiving

Empty, malformed, partial, timed-out, or killed returns leave dependent work incomplete; seek the
missing evidence and continue independent work. Escalate a material decision, unavailable
capability, or exhausted budget with the precise gap. UNKNOWN effects require reconciliation before
retry. Finish with one synthesized answer against the original objective.

## Managing the window

- **Fork or rewind only when replay is defined.** A checkpoint before a failed path gives a clean
  retry only when the runtime defines replay and effect semantics. Never replay an external side
  effect by assumption; otherwise correct in place and record the divergence.
- **Clearing old tool results is not lossless.** Clear only after retaining their load-bearing
  facts and only when the source can be read safely again.
