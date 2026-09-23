# Incident fast path

During a declared incident, use this checklist for reversible Tier 0–2 mitigation or rollback to
an already-live artifact. It replaces the full production checklist for covered actions. The
parent `SKILL.md` still owns classification and execution authority.

## Scope

Covered actions include route remaps, revision rollback, instance-count scale, flags, and
per-instance or rolling restarts with confirmed serving headroom and existing-droplet reuse without
staging. Unknown package/droplet state or a whole-app stop/start does not qualify; a memory, disk,
or log-rate scale stops and starts the whole app, so it does not qualify either. Use the
mitigation-selection reference in `incident-investigation` for selection. While a deployment is
deploying or paused, scaling the `web` process fails: wait for it, or cancel it knowingly.
New artifacts (including restage) retain the full release and production gates. Tier 3 destructive
or access-path actions retain the full gate and proven backup/recovery requirement.
Suspected compromise or integrity loss exits this path: preserve evidence and follow the human
security owner's direction.

## Before execution

Record together in the incident timeline:

- **Scope and approval:** tier, exact target, command and artifact/configuration identity, human
  executor or separately approved protected automation, and approving human. Approval covers the
  exact command or a bounded envelope ITO approves in the TLC, with `Valid until` UTC or an
  explicit incident-lifecycle end. Before each attempt the executor checks that approval is current
  and target, action, actor and identity still match. No repeat approval within that envelope;
  expiry, mismatch or action outside it requires new approval.
- **Effect and recovery:** blast radius, backout, verification window, stop criteria and human
  monitoring owner. Capture perishable diagnostic evidence or record the named human's decision
  to forgo unavailable capture for this reversible reliability mitigation.

The human release owner or approved protected automation executes; the agent does not. After every
attempt, record the executor, time (UTC), receipt and observed effect. An UNKNOWN outcome needs a
reconciliation owner and read-after-write check; do not retry until reconciled.

## After resolution

Reconcile deferred readiness/artifact records for covered actions, execution-boundary evidence,
timing/freeze documentation, suppression records, and the formal change system and record ID.
Already-live rollback reuses existing artifact records. No deployment-control or credential/role
API check sits on the recovery path. Existing incident roles and communications cover monitoring
and notification. These administrative records and unavailable diagnostic capture do not delay an
approved covered mitigation; effect-outcome reconciliation is never deferred. Give the completed
timeline to `scribe`.
