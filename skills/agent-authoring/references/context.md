# Context engineering

Find the smallest set of high-signal tokens that lets the agent act correctly, and treat context
like least privilege: include what the step needs, nothing it doesn't. `../SKILL.md`'s
untrusted-data and label rules apply unchanged — compression, compaction, and handoff are the
easiest places to silently upgrade a label.

## Fleet rules the general techniques leave open

- **Durable knowledge lives outside the window** — for us that is runbooks, postmortems, and the
  knowledge loop, never a giant in-context scratchpad.
- **Preload the two things a step always needs; keep just-in-time retrieval for what only some
  steps require.** Forcing three fetches before work can start trades tokens for latency and for
  the chance of fetching the wrong files.
- **Fork or rewind only when replay is defined.** A checkpoint before a failed path gives a clean
  retry only when the runtime defines replay and effect semantics. Never replay an external side
  effect by assumption; otherwise correct in place and record the divergence.
- **Clearing old tool results is not lossless.** Clear only after retaining their load-bearing
  facts and only when the source can be read safely again.

## In this fleet

Thin agent bodies, on-demand detail, isolated bounded work, and compact evidence packets keep
context deliberate; apply them before reaching for a bigger model or a longer prompt. A cold-start
packet names the invoking caller and human owner separately, intent, source/state, success criteria,
scope, source trust, unknowns and [return fields](./roster.md#handoffs-between-contexts). Preserve
targets, windows, observed values and [verified], [sourced], [unverified], [UNTRUSTED] markers.
Missing chronology or current state stays unknown. The caller retains pending work, checks the
return against its evidence, and resumes within its authority.

## Handoffs

`../SKILL.md`'s handoff and production-gate rules apply unchanged. A handoff is itself a context
artifact: send the cold-start packet shape above, not a transcript.
