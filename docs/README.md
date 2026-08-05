# Documentation map

This directory separates current work, durable decisions, round-scoped plans, and dated evidence.
Mixing those roles is how a landed item becomes an apparently open task, or a dated review silently
starts governing the current fleet. Nothing here overrides the canonical `agents/` and `skills/`
sources or the generated host adapters.

## Authority

| Document class | Where | Authority |
|---|---|---|
| Live tracker | [`fleet-roadmap.md`](fleet-roadmap.md) | The **only** owner of unfinished, blocked, and deferred work. Nothing else adds work to the queue |
| Decisions (ADRs) | [`decisions/`](decisions) | An **accepted** record governs its decision, names what lost, and states its reopen trigger; a proposed record carries no implementation authority. Never an execution checklist |
| Round plans and specs | [`superpowers/plans/`](superpowers/plans), [`superpowers/specs/`](superpowers/specs) | Operational only while their round is active. Each carries a top-of-file `Status:` banner marked `implemented`, `superseded`, or `historical`, and points back to `fleet-roadmap.md` — `check_plan_status.py` fails the build otherwise |
| Closure evidence | [`reviews/`](reviews) | Historical evidence of what a round landed and how it was verified. Never a task list |
| Live reference contracts | [`schema-compatibility.md`](schema-compatibility.md), [`verification-sandbox.md`](verification-sandbox.md) | Current, governing contracts — not dated snapshots. The schema-compatibility policy versions the machine-readable contracts in [`../schemas/catalog-v1.json`](../schemas/catalog-v1.json); the verification-sandbox spec governs the digest-bound boundary in [`../scripts/verification_sandbox.py`](../scripts/verification_sandbox.py). Both are linked from [`../README.md`](../README.md) and stay current with the code they describe |
| Dated evidence | [`AUDIT-2026-07-12.md`](AUDIT-2026-07-12.md), [`RESEARCH.md`](RESEARCH.md) | Point-in-time snapshots. The audit's `OPEN` labels describe the 2026-07-12 fleet, not today's; the research file is provenance current as of its dateline. Re-verify before relying on either; neither adds work |

## What is live right now

Only [`fleet-roadmap.md`](fleet-roadmap.md), the **accepted** records under [`decisions/`](decisions),
and the two live reference contracts govern the current fleet. `superpowers/plans/` and
`superpowers/specs/` are empty when no round is active; everything they and `reviews/` contain
otherwise is history. A historical file may retain a dated "open" section as evidence of what was
believed then — that section does not re-enter the queue unless the roadmap imports it.

## Rules

1. **The roadmap is the single live tracker.** A review or decision record owns detailed rationale;
   it never independently proves that work is still open.
2. **`check_plan_status.py` enforces the single-live-roadmap discipline mechanically.** It requires
   the roadmap to declare itself the only unfinished-work registry, rejects volatile pass-counts in
   its evidence blocks, and fails any plan or spec that lacks a historical status banner or a pointer
   back to the roadmap. It does not read this map — treat the map as the human-facing statement of
   the same discipline the script enforces.
3. **A plan retires to a short outcome record when its round finishes.** Its lasting decisions and
   evidence move to `reviews/` (or a decision record); git history keeps the exact execution payload.
   A plan file left lying around after its round is how a finished task keeps reading as pending work.
4. **When a file moves or is consolidated, update every tracked reference in the same commit** —
   root docs, decision records, and the roadmap all count. A dangling pointer is a silent defect.
5. **GitHub issues are evidence-bound intake, not a second tracker.** An issue adds work only when
   the roadmap imports it and names the source issue; an un-imported issue is field evidence awaiting
   triage. Letting the two lists drift is how the same work gets tracked twice or dropped once.
6. **Agent and skill definitions stay canonical in `agents/` and `skills/`.** Documentation and
   generated host adapters never override them.
