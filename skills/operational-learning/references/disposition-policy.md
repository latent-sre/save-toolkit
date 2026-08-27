# Operational knowledge disposition policy

`../SKILL.md` carries the learning contract, trust rules, and required invariants; they are not
restated here. This file owns what the body leaves open: the event→artifact map, the remaining
disposition-state definitions, default paths, and the evidence rules.

## Event-to-artifact map

| Observed event | Required disposition |
|---|---|
| An application, service, worker, job, datastore, platform, or other component is approved or materially changes | Create or update its component card and knowledge index; propose missing alert, runbook, ownership, dependency, backup/restore, or SLO work. |
| A component is decommissioned | Move its component card to `lifecycle: retired` and retire its knowledge-index entry with it, dated and citing the authorizing record; move dependent alert cards to `status: retired` and its runbooks to `status: retired` rather than deleting any of them; name every artifact and dependent component still referencing it. Removing live alerts, telemetry, dashboards, or platform resources is a production change under the existing gate, never a documentation disposition. |
| An alert is approved or materially changes | Create or update the alert card, link its service card and authoritative alert definition, and require a valid runbook target before paging. |
| An alert fires | Active event: route investigation and recommended action to `sre`; prepare no retrospective or KB change until resolution. |
| A runbook is missing or contradicted by evidence | Create or update it through `scribe` plus `runbook`; retain unsupported commands as `[unverified]`. |
| A drill exposes a bad or missing step | Update the runbook from the supplied drill record; change `last_verified` only when evidence binds artifact/version, target, actor, time, and outcome. |
| A resolved incident reveals a systemic lesson | Write the postmortem, then disposition runbook, service card, alert card, knowledge index, observability, automation, code, and accepted-risk follow-ups. |
| A fleet prompt, agent, or skill has an accepted behavioral failure | Route the observed divergence, evidence, and proposed named regression to `agent-engineer`; operational content never rewrites fleet definitions directly. |

## One-time disposition states

`prepared` and `duplicate` are fully defined by `../SKILL.md`'s required invariants; the
load-bearing gate on `prepared` is the caller-supplied `[verified]` checkout binding saying the
mounted checkout's current full SHA equals the target revision. The rest:

- `proposed` — the owner and next action are named, but no reviewable artifact change exists.
- `blocked` — the missing evidence, authority, dependency, or owner is named.
- `not_applicable` — the reason this artifact class does not apply is explicit.

## Default paths when the repository has no convention

Prefer the target repository's existing documented paths and index. When none exist, use:

- `docs/operations/index.md`
- `docs/operations/services/<component>.md`
- `docs/operations/alerts/<alert>.md`
- `docs/runbooks/<runbook>.md`
- `docs/postmortems/<yyyy-mm-dd>-<incident>.md`

Paths are repository-relative. Reject absolute paths, parent traversal, URLs as write targets, and
paths outside the caller-authorized documentation roots. Update an existing stable identifier
instead of creating a second record.

## Evidence and review rules

1. The version-controlled service or alert definition is authoritative for configuration; KB cards
   summarize and link it rather than copy details that will drift.
2. Prefer evidence for the exact target revision. If sources disagree, retain both labels, describe
   the conflict, mark the affected claim `[unverified]`, and assign one owner to resolve it.
3. `last_reviewed` and `last_verified` follow `../SKILL.md`'s invariants. The distinction they
   protect: document review does not prove a procedure works; only bound execution evidence does,
   and `last_verified` belongs only to rehearsed operational procedures.
4. Credential checks are defense in depth, not proof of absence. Store only the minimum evidence.

## Recommended course of action

Every closeout names one course of action: summary, owner, urgency, change tier, approval need,
verification, and rollback or recovery. The closeout recommends; it never grants authority or
performs the action.
