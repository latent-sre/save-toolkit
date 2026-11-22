---
name: production-change-gate
description: >-
  Gate changes from code merge through production execution across three checklists: merge readiness,
  release readiness, and production authorization (plus the declared-incident fast path). Triggers:
  'is this ready to merge', 'is this build ready to ship', 'can I run this cf command in prod',
  'authorize this production change'. Not for code review itself (reviewer) or incident mitigation
  advice (incident-investigation).
argument-hint: "[the change, build, or production action to gate]"
---

# Production change gate

Three questions, one gate: **merge**, **release**, and **production**. Each consumes the earlier
verdict as evidence without re-running it. Agents classify, check, and record; **a human release
owner or separately approved protected automation executes**. The sole exception is an invoked
`observability-engineer`'s scoped Grafana writes (dashboards, folders, individual alert rules,
temporary silences); rule deletion and shared notification config remain gated here.

The checklist records a decision; it is not the control. The load-bearing control is the
least-privilege role or protected deployment environment gating production credentials.

## 1. Merge readiness (`gate: merge` · `PASS | BLOCKED`)

| Item | Passes when |
|---|---|
| Required checks | Every required hosted check passed for the current PR head (or provider merge ref); local runs never satisfy hosted checks. Inspect branch rules (`gh api repos/{owner}/{repo}/rules/branches/{branch}`) and classic protection (`.../protection`; 404 without admin rights = unknown, `enforce_admins` governs admin bypass). |
| Behaviour tested | Checks cover changed behavior and material failures; bug fixes prove regression fails before and passes after. |
| Findings disposed | Every current P0/P1 finding (security included) is fixed or refuted with evidence; no secrets/keys in code, fixtures, artifacts, or logs. **P2 and P3 never block merge.** |
| Compatible | Schema, API, and UI-state changes use expand-then-contract; web UI changes verify keyboard/WCAG behavior or record a waiver. |
| Scoped | Split only if size or mixed concerns prevent reliable review. |
| Docs and ops | Updated via `scribe` (runbooks/postmortems) or `observability-engineer` (dashboards/alerts/SLOs), or a recorded reason neither is needed. |

## 2. Release readiness (`gate: release` · `PASS | BLOCKED`)

Use [Release readiness](./references/release-readiness.md) to verify exact-commit provenance,
immutable artifact byte binding, migrations, consumer retirement, flags, recovery, and monitoring.

## 3. Production authorization (`gate: production` · `APPROVED | BLOCKED`)

Classify first; an unmet requirement blocks readiness. Any change to target, command, or actor
re-enters the gate.

| Tier | Action | Who may proceed |
|---|---|---|
| **0** | Observe: reads, health checks, config validation, dry runs | Agent (within granted read paths) or human |
| **1** | Prepare: edit version-controlled config, docs, or unapplied plans | Agent (never applying to live targets) |
| **2** | Reversible live change | Human release owner or approved protected automation after explicit approval of exact command |
| **3** | Destructive or access-path change (data deletion, storage/backup, credentials/identity, DNS, firewall, VPN, proxy, remote access) | Tier 2 controls + proven backup/recovery path preserving data |

| Item | Passes when |
|---|---|
| Readiness evidence | New-artifact deploy attaches exact-commit independent review, green checks, `gate: release` PASS, and named approver. Non-deploy actions attach exact command/diff and approval; live-artifact rollback reuses that artifact's records. |
| Execution boundary | Evidence that the named human/protected executor (not the agent) holds the least-privilege role or protected environment with required reviewers, self-review blocked, admin bypass off, and deployment branch/tag restriction. |
| Approved | Authorized human approved exact target, command/diff, actor, `Valid until` UTC expiry, and Remedy/Jira change record (per `stack-profile`). |
| Binding current | Executor confirms immediately before running that approval is unexpired and target, action, actor, and candidate digest still match. |
| Blast radius | Affected apps, routes, spaces, traffic share, and worst credible failure recorded. For `cf` writes, load `pcf-ops` (and its deploys, scaling, and rollback reference) for impact and whether it stages a new droplet. |
| Backout / recovery | Exact rollback where feasible, else non-reversible effects plus evidence-backed recovery path (recovery never lowers a Tier 3 action). |
| Plan shown & monitoring | Full commands/diff shown; peak/freeze checked; named human watches golden signals with abort criteria; stakeholders notified. |

## 4. Incident fast path (declared incidents only)

Urgency alone never opens this path; an incident must be declared. In a declared incident, this
replaces the full production checklist **only** for covered reversible Tier 0–2 mitigations or
rollback to an already-live artifact:

- **Covered:** route remaps, `cf rollback` (while the target revision's droplet is retained — 5 droplets
  vs. 100 revisions), instance-count scale (`-i`), feature flags, and per-instance or rolling restarts
  with confirmed serving headroom and existing-droplet reuse without staging.
- **Excluded (full gate required):** new artifacts, `cf restage`, unknown package/droplet state,
  whole-app stop/start or memory/disk/log-rate scale, all Tier 3 actions, and suspected compromise
  or data-integrity loss (preserve forensic state and follow the human security owner).
- **Controls:** ITO approves the exact command or a bounded envelope (with `Valid until` UTC or
  incident end) in the TLC; record blast radius, backout, verification window, stop criteria, monitoring
  owner, and perishable-diagnostic capture (or the human's waiver). Reconcile deferred change-record
  and readiness paperwork after resolution and hand the timeline to `scribe`.

## 5. Verdict & execution outcome

Return the requested gate verdict with `Target`, `Candidate commit / artifact`, `Evidence` (reusing
prior gate records), `Blocking items / Waivers`, `Backout / Watching / Abort if`, and for production:
`Tier`, `Actor`, `Approved by / Valid until`, `Execution-time binding`, and `Production execution boundary`.

After Tier 2/3 dispatch, record the executor's returned outcome (`executed | not executed | UNKNOWN`),
actor/UTC time, and receipt ID. **A timeout or missing response is `UNKNOWN`, not `not executed`** —
block any retry until the named reconciliation owner inspects read-after-write state and explicitly
authorizes retry.
