---
name: production-change-gate
description: >-
  Authorize a production-facing action only after the exact target, command, approval tier, blast radius,
  verification, rollback, and branch protection are proven. Triggers: 'authorize this production change',
  'can I run this cf command in prod', 'review this rollback plan'. Ownership map only—not a load:
  the `merge-gate` skill decides merge readiness and the `release-gate` skill decides ship readiness; this
  gate authorizes the prod action.
---

> **Evidence default — `[unverified]`.** Unless a paragraph carries a narrower label, each
> stack/product-specific command, query, API or CLI behavior, version, licensing statement, and
> runtime claim in this skill and its bundled files is `[unverified]` for the exact target.
> A narrower `[sourced]` or `[verified]` label takes precedence; handoffs never upgrade it.

# Production change gate

Any action that touches production must clear this gate **before execution**. The agent may classify,
prepare, and recommend. A human release owner or separately approved protected automation executes an
authorized live change; an agent never executes it.

> **The checklist is not the enforcement.** It records a human decision. The load-bearing controls are
> branch protection and protected environments with required reviewers, configured so administrators
> cannot bypass them. Treat this record as evidence riding on that boundary, not as the boundary itself.

## Checklist

- [ ] **Classify first** — Classify the change: Tier 0 (observe) / Tier 1 (prepare) / Tier 2 (reversible
      live) / Tier 3 (destructive or access-path). Tier 0–1 proceed; Tier 2 needs explicit approval of the
      exact command shown; Tier 3 needs Tier-2 evidence plus a proven backup/recovery path. Approval covers
      only the commands and target shown — a material change re-enters this gate.

      A human release owner or separately approved protected automation performs every Tier 2/3 live
      action; the agent never executes it. Approval does not grant the agent live-change authority.

### Worked example — a Tier 2 request (the shape, compressed)

> **Requesting approval for a human release owner to apply a Tier 2 change.**
>
> **Target**: `checkout` app, `prod` space, foundation `pcf-east`.
> **Change**: scale from 4 → 6 instances to absorb the 502 burst while the root cause is investigated.
> **Exact command**: `cf scale checkout -i 6`
> **Blast radius**: no restart of existing instances (`-i` only adds); ~40s until new instances pass
> health checks. No config or code changes.
> **Verification**: `cf app checkout` shows `6/6 running`; 502 rate in the dashboard drops within 5 min.
> **Rollback**: `cf scale checkout -i 4` — the exact inverse, no state carried.
>
> This is Tier 2 (reversible live change), so a human release owner needs explicit approval for this
> specific apply and then executes it; I do not apply live changes.
> Meanwhile I'll continue the Tier 0 investigation of what changed, which needs no approval.

The example is `[unverified]`: it is the required approval-request shape, not evidence from a foundation.

- [ ] **Readiness evidence present** — for a release, attach the reviewed SHA, green checks, exact release
      artifact, and named approver. Consume those records as existing evidence; do not load or execute a
      readiness gate. For a non-release action, mark artifact fields not applicable and attach the current
      reviewed command/diff and named approval instead.
- [ ] **The boundary is actually ON** — verified, not assumed. Everything below is a record; branch
      protection is the control and must be checked by an authorized human or protected evidence job:

      ```sh
      gh api repos/{owner}/{repo}/branches/{branch}/protection \
        --jq '{enforce_admins: .enforce_admins.enabled,
               required_reviews: .required_pull_request_reviews.required_approving_review_count,
               dismiss_stale: .required_pull_request_reviews.dismiss_stale_reviews}'
      ```

      `enforce_admins` must be **true** (GitHub's administrator bypass setting is disabled). If it is
      false — or the call **404s**, meaning no branch protection — **BLOCK** before any production change.
      Record the exact output. Until attached, the boundary and every dependent claim remain `[unverified]`.
- [ ] **Approved** — an authorized human explicitly approved this exact target, command or diff, applying
      actor, and time; attach the change record when the process requires one.
- [ ] **Blast radius understood** — record affected apps, routes, spaces, users or traffic share and the
      worst credible failure.
- [ ] **Backout plan, reversible** — record an exact rollback or backout plan, verification, and known-good
      recovery evidence. It is owned and executed by the human release owner; prefer rapidly reversible
      actions such as a blue-green route remap or flag flip over irreversible ones.
- [ ] **Authorized executor** — the human release owner or separately approved protected automation uses
      least-privilege credentials and does not bypass review or protection.
- [ ] **Plan/diff shown** — show all commands and the manifest or configuration diff; approval covers no
      undisclosed side effect.
- [ ] **Timing** — consider peak and freeze periods; document any emergency exception, maintenance window,
      or Moogsoft suppression.
- [ ] **Monitoring during change** — name the human watching the golden signals and agree abort criteria.
- [ ] **Comms** — notify stakeholders and on-call before and after the change.

## Verdict

```text
production-change-gate: APPROVED | BLOCKED
Tier: <0|1|2|3>   Target: <exact target>   Actor: <human or protected automation>
Change: <what, where>   Approved by: <human>   When: <UTC>
Backout: <exact reversible steps>
Watching: <who, which signals>   Abort if: <criteria>
Branch protection evidence: <output or [unverified]>
```

## Emergency exception

During a declared incident, mitigation speed can outweigh the full process, but never skip human
confirmation, exact scope, and a backout plan. Record who made the emergency decision and reconcile the
change record afterward. Tier 2/3 execution remains human-owned or protected-automation-owned.
