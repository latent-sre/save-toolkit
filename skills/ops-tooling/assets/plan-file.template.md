<!-- Plan file — instantiate at the plan-file path (default .agents/plan.md) before Phase 1.
     ORCHESTRATOR-OWNED, single writer: builders never write this file — their status flows through
     their own progress shards (see the environment card), which the orchestrator reads. This is the
     pipeline's durable coordination record: conversation memory does not survive compaction, so
     anything the pipeline must not forget lives HERE, not in the conversation. Update slots as
     state changes; never delete history — strike through and append. -->

# Plan — <tool name>

## Mission transaction

<!-- copy verbatim from the environment card's mission block — the Phase 4 gate runs exactly this -->

## Cadence contract

- **Commit policy**: <!-- required: e.g. "commit at every green batch boundary"; without an explicit grant, never commit -->
- **Pause points / user gates**: <!-- required: default = design approval, deploy artifacts; anything not named runs without a check-in -->

## Gate status

| Gate | Status (open / approved / n-a) | Evidence |
|---|---|---|
<!-- one row per named gate; approval evidence is a pointer to the user's words, never inferred -->

## Counters (survive compaction — the caps reset silently otherwise)

| Builder / component | Relaunches used (cap 1) | Fix→re-review rounds (cap 2) |
|---|---|---|

## Parked suspicions — never shown to the reviewer

<!-- defects the orchestrator suspects, recorded BEFORE the review returns; reconcile after.
     A reviewer handed a hypothesis can only echo it. -->

## Batch & checkpoint log

<!-- one line per spawn/return: builder, boundary given, returned at, packet verdict -->

## Safe resume point

<!-- required, kept current: the next safe action if this session dies right now — which batch is
     mid-flight, which files are possibly half-written, what to verify before continuing.
     A successor starts here, never by reconstructing the conversation. -->
