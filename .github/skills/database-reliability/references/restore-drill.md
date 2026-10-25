# Restore drill — turn a backup into recovery evidence

Use for rehearsals or RTO/RPO claims under the [parent authority rule](../SKILL.md).

## Restore into scratch by default

An explicitly assigned isolated drill uses its authorized disposable target, backup data and actor without a
separate production-change packet. Isolate restored jobs, integrations and network access; a scratch
name is not isolation. Live/production-connected changes need `production-change-gate`. Never overwrite
the live service to test a backup; an in-place rehearsal also needs a second recovery copy.

## Drill sequence

1. Identify service, backup/snapshot, UTC recovery cutoff (simulated failure or approved PITR target),
   expected RPO/RTO and data/application checks.
2. Start timing before locating backup/runbook; include retrieval, credentials, restore,
   reconstruction and verification. Report locate, restore and verify durations separately.
3. Follow the current runbook, recording deviations and undocumented knowledge needed.
4. Restore the newest eligible backup to scratch with failure-sensitive client flags: partial SQL
   errors must not return success.
5. Verify data correctness and application usability. Corroborate the recovered backup/PITR watermark
   and its UTC mapping with recovered transactions. Compare cutoff-to-watermark gap with RPO,
   separately from total elapsed recovery time against RTO. A filename or successful query cannot
   establish freshness; absent watermark proof leaves RPO unverified.
6. Inventory exclusions: secrets/config, routes, certificates, ownership, schedules and indexes
   needing rebuild. Report these as recovery-scope findings.
7. Return backup identity, watermarks, timings, evidence, deviations and verdict. Update the runbook
   only when assigned; evidence-only helpers return proposed changes. The authorized drill owner
   tears down scratch.

## Verdict

- **Pass:** usable data restored, both RPO/RTO met.
- **Pass with findings:** both met, with runbook or nonessential recovery-scope gaps.
- **Fail:** unusable/incomplete required recovery or a measured objective missed; name the gap and
  owner before repeating.
- **Inconclusive:** missing evidence prevents judging either objective; never report a pass.
