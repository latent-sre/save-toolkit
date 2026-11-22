---
name: resilience-analysis
description: >-
  Analyze failure propagation and design service resilience using source, configuration, operational
  evidence, and explicit assumptions. Triggers: 'what happens if this dependency slows down',
  'find resilience weaknesses', 'design a safer recovery path'. Covers capacity under failure,
  partial completion, degraded behavior, recovery, and existing service readiness. Active incidents
  use incident-investigation; change verdicts belong to reviewer.
argument-hint: "[service or design, user outcome, environment, evidence]"
---

# Resilience analysis

Load `stack-profile` for ownership and platform constraints (e.g., Postgres/SQL Server on-prem, no
self-managed Kubernetes, PCF vs GCP migration). This method grants no execution, design approval, or
production-change authority; proposed experiments and fixes stay proposals until executed by an
authorized owner.

## Establish outcome, evidence, and failure paths

Name the critical user or batch outcome, environment, requirements, and accepted SLOs/recovery
targets (keep missing targets `unknown` or explicit owner proposals). Compare **intended**
(design/runbook), **implemented** (effective code/config/tests), and **observed**
(telemetry/rehearsal) behavior bound to exact revision, deployment, and time. Source-only analysis
establishes conditional design risk, never observed production impact or whole-service certification.

1. Follow user and data paths including async work, queues, shared slots/pools, and external calls;
   inspect actual callers and config overrides, not just defaults.
2. Select only relevant scenarios from the table below; trace **trigger -> component behavior ->
   propagation -> user effect -> protection -> recovery** and look for counter-evidence (overall
   deadlines, cancellation, admission limits, deduplication, failover headroom, degraded mode).
3. Separate normal, degraded, overloaded, and recovering behavior. A restart, cleared alert,
   completed backup, or reverted commit does not prove user recovery or data integrity. Use
   `database-reliability` for data/restore mechanics and `root-cause` for observed incidents.

| Scenario | Evidence separating failure from protection |
|---|---|
| Slow dependency | Enforced deadlines, retries, and cancellation release slots/connections; unrelated work retains capacity |
| Overload | Admission/overflow limits, queue bounds, and drain behavior tested above completion capacity; increasing shared slots alone leaves shared saturation intact |
| Lost failure domain | Surviving capacity handles demand including cold starts and shared DB/quota/network/control-plane dependencies |
| Partial completion | Commit/ack order, idempotency scope, deduplication retention, and reconciliation prevent duplicate or lost effects |
| Mixed versions | Old/new readers/writers and config overrides preserve compatibility across rollout and rollback |
| Restore | Current-revision schema/procedure compatibility plus a business-transaction check within RPO/RTO; backup existence alone or an old-version restore leaves recoverability as a verification gap |
| Control-plane loss | Serving and recovery paths still obtain config, credentials, and DNS |
| Skewed/missing telemetry | Freshness, sampling, and coverage checks separate missing signal from health |
| Operator procedure | Intended operator rehearses exact target/access steps; ambiguous steps, reversal, and escalation gaps stay explicit |

*(Note: configured pool max * instances = potential demand, not open connections; replica names do
not prove independence; batch/pipeline work requires freshness, completeness, duplication, and
deadline checks.)*

## Substantiate findings and readiness

Bind every material finding (`[verified]`, `[sourced]`, `[unverified]`) to target, method, and time:

| Result | Meaning |
|---|---|
| Observed defect | Direct/supplied evidence demonstrates failure under stated conditions |
| Supported design risk | Credible conditional failure path in source/config; frequency may be unknown |
| Verification gap | Important claim lacks evidence (e.g., backup exists without current-revision restore + transaction check) — not an observed defect |
| Improvement opportunity | Supported improvement justified without a defect |

- Inspect controls rather than demanding named patterns: e.g., an enforced shared overall deadline
  that cancels transport and releases connections protects the path without a circuit breaker.
- For **existing-service readiness audits**, check owner/on-call, runtime/health check,
  deploy/rollback path, telemetry arrival, SLI/SLO/alerts with runbooks, dependencies/headroom, and
  dated restore drills. Present-but-undocumented = documentation gap; absent from both = readiness gap.

## Engineer improvements, retry/capacity bounds, and proof

Compare the smallest effective change against alternatives (`principal-engineer` owns shared
contracts; application team implements; human owner approves production changes). Include when
applicable:

- **Retry paths:** State which return values (`false`/error vs. exception) re-enter the loop and
  which exit; unknown timeout behavior stays explicit until code/tests confirm it.
- **Retry-count basis:** Distinguish `"up to N total calls"` from `"initial call + N retries"`
  unless source resolves it; carry both interpretations beside derived sums and correct helper
  summaries that collapse them.
- **Timing and capacity basis:** Separate measured from assumed inputs. Never multiply per-attempt
  timeouts into a proven elapsed/occupancy bound — and when an enforced overall deadline is
  established, keep that effective overall bound instead of reopening per-attempt products. A
  concurrency bulkhead protects shared capacity only if admission/waiting happens *before* acquiring
  shared worker slots (or rejects/defers without holding a shared slot). Throughput from slots needs
  actual/explicit mean residence and shared-demand accounting (never substitute a max timeout for
  the mean).

**Verification proposals** stay `proposed` (never claim execution or trigger production faults): name
target/version, overload stimulus above completion capacity while protected work runs concurrently,
occupancy counts (active + waiting + retries), stop bounds, post-fault drain, and reconciliation checks.
