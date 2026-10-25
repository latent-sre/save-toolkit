# Incident fast path

For a declared incident, this replaces the full production checklist only for covered reversible
Tier 0–2 mitigation or rollback to an already-live artifact. The [parent gate](../SKILL.md) retains
classification and execution authority.

## Scope

Covered: route remaps, revision rollback, instance-count scale, flags, and per-instance/rolling
restarts with confirmed serving headroom and existing-droplet reuse without staging. Excluded:
unknown package/droplet state, whole-app stop/start, and memory/disk/log-rate scale that stops and
starts the whole app. Use `incident-investigation`'s mitigation-selection reference to choose.
While deployment is deploying or paused, `web` scaling fails: wait or cancel knowingly.

New artifacts, including restage, require full release and production gates. Tier 3 retains the
full gate and proven recovery/backup. Suspected compromise or integrity loss exits this path:
preserve evidence and follow the human security owner's direction.

## Before execution

Record in the incident timeline:

- **Approval:** tier, exact target, command, artifact/configuration identity, human executor or
  separately approved protected automation, and approver. ITO may approve a bounded envelope in
  the TLC. Record `Valid until` UTC or explicit incident-lifecycle end. Before each attempt the
  executor checks current approval and target/action/actor/identity binding; no repeat approval
  inside that envelope, but expiry, mismatch or out-of-envelope action requires new approval.
- **Recovery:** blast radius, backout, verification window, stop criteria and human monitoring owner.
  Capture perishable diagnostics or record the named human's decision to forgo unavailable capture.

Only the human release owner or approved protected automation executes. Record executor, UTC time,
receipt and observed effect after every attempt. UNKNOWN needs a reconciliation owner and
read-after-write check; no retry until reconciled.

## After resolution

Reconcile deferred readiness/artifact records, execution-boundary evidence, timing/freeze documents,
suppression records, and formal change system/record ID. Already-live rollback reuses its records.
No deployment-control or credential/role API check sits on the recovery path. Existing incident
roles/communications cover monitoring and notification. These administrative records and unavailable
diagnostic capture never delay approved covered mitigation; effect-outcome reconciliation is never
deferred. Give the completed timeline to `scribe`.
