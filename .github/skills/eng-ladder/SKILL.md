---
name: eng-ladder
description: >-
  Design method and review standard for work across services, teams, or migrations: a shared
  contract change, a new system's architecture, a hard-to-reverse migration, or a tool or platform
  selection. Use it to write such a design or to review a design document. Triggers: 'review this
  design doc', 'is this design sound', 'which platform should we pick'. A scoped change that follows
  an existing pattern or an accepted design is build work, not this. Active-alert troubleshooting
  belongs to incident-investigation.
argument-hint: "[design doc or design question]"
---

## Pick the reference

Read only the reference for the decision still open:

| Decision | Read |
|---|---|
| A change across a shared contract, services, or teams; a migration; a new system's architecture | [principal](./references/principal.md) |
| An unresolved tool or platform selection, a platform standard, or multi-year direction | [distinguished](./references/distinguished.md) |

A design-only assignment belongs to `principal-engineer`; implementing an accepted design belongs to
`software-engineer`. Active incidents and firing alerts route to the responder with
`incident-investigation`.

## Review a design

1. Apply the selected reference's checks: principal's **Design record** and **Before you return**,
   or distinguished's **Done means**.
2. Score **meets** or **gaps**, citing specific lines or sections. Assess the artifact's remit;
   unrequested implementation or architecture work is not a gap. A simple artifact done cleanly
   can meet the bar.
