# Documentation map

This directory separates current work, durable decisions, round-scoped plans, and dated evidence.
Mixing those roles is how a landed item becomes an apparently open task, or a dated review silently
starts governing the current fleet. Nothing here overrides the canonical `agents/` and `skills/`
sources or the generated host adapters.

## Authority

| Document class | Where | Authority |
|---|---|---|
| Live tracker | [`fleet-roadmap.md`](fleet-roadmap.md) | The **only** owner of unfinished, blocked, and deferred work. Nothing else adds work to the queue. It states what is still owed and cites its evidence rather than restating it |
| Closed-item register | [`roadmap-closed.md`](roadmap-closed.md) | The disposition of every item that has left the live tracker. Historical evidence, never a task list; a row closed by owner disposition states its own reopen condition |
| Decisions (ADRs) | [`decisions/`](decisions) | An **accepted** record governs its decision, names what lost, and states its reopen trigger; a proposed record carries no implementation authority. Never an execution checklist |
| Round plans and specs | [`superpowers/plans/`](superpowers/plans), [`superpowers/specs/`](superpowers/specs) | The directories always exist; they are **empty between rounds**, because the round's closing PR deletes its plan and git history keeps the payload. While a file is present it needs a `Status:` banner (`implemented`, `superseded`, or `historical`) and a pointer back to `fleet-roadmap.md`, which `check_plan_status.py` enforces |
| Roadmap-linked probe instruments | [`probes/`](probes) | Blank, repeatable procedures that are operational only while an active roadmap item links them. They are neither evidence nor a second task list; completed results live in validated evidence envelopes and dated review packets |
| Closure evidence | [`reviews/`](reviews) | Historical evidence of what a round landed and how it was verified. Never a task list |
| Live reference contracts | [`rules.md`](rules.md), [`schema-compatibility.md`](schema-compatibility.md) | Current, governing contracts — not dated snapshots. The rules catalog indexes must-follow constraints with primary sources; schema-compatibility versions the machine-readable contracts in [`../schemas/catalog-v1.json`](../schemas/catalog-v1.json). Both are linked from root docs and stay current with the fleet they describe |

## What is live right now

Only [`fleet-roadmap.md`](fleet-roadmap.md), the **accepted** records under [`decisions/`](decisions),
and the live reference contracts ([`rules.md`](rules.md) and
[`schema-compatibility.md`](schema-compatibility.md)) govern the current fleet.
`probes/` contains no independent authority: an instrument is live only through the active roadmap
item that links it. `superpowers/plans/` and `superpowers/specs/` are empty between rounds.
`reviews/` holds closure evidence that a roadmap item, a decision record, a live doc, or a test
still cites; a review nothing cites is removed the same way. [`roadmap-closed.md`](roadmap-closed.md)
records where each retired item landed. Everything in both is history, not a task list. A historical file may retain a dated "open" section as evidence of what was believed
then — that section does not re-enter the queue unless the roadmap imports it.

### Retained full-skill audit evidence

The 2026-08-24 repository-wide skill audit is retained as closure evidence for the review and
remediation of the canonical 30-skill corpus. Its six scoped packets preserve the local inspection,
public-source, and verification evidence behind that result:

- [`2026-08-24-full-skill-audit-batch-1.md`](reviews/2026-08-24-full-skill-audit-batch-1.md)
- [`2026-08-24-full-skill-audit-batch-2.md`](reviews/2026-08-24-full-skill-audit-batch-2.md)
- [`2026-08-24-full-skill-audit-batch-3.md`](reviews/2026-08-24-full-skill-audit-batch-3.md)
- [`2026-08-24-full-skill-audit-batch-4.md`](reviews/2026-08-24-full-skill-audit-batch-4.md)
- [`2026-08-24-full-skill-audit-batch-5.md`](reviews/2026-08-24-full-skill-audit-batch-5.md)
- [`2026-08-24-full-skill-audit-batch-6.md`](reviews/2026-08-24-full-skill-audit-batch-6.md)

These packets remain historical evidence, not an independent backlog; only `fleet-roadmap.md` can
import unfinished work from them.

### Folded eval measurement index

Sealed eval packets that no live document cited were folded into
[`2026-08-30-folded-eval-index.md`](reviews/2026-08-30-folded-eval-index.md). That index keeps the
batch IDs, verdicts, models, candidates, and scenario names; the full packets remain in git history.
Packets the live roadmap already names stay as their original files. The index is historical
evidence, not a task list.

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
