# Restore drill — turn a backup into recovery evidence

For recovery rehearsals or RTO/RPO claims, within `../SKILL.md`'s authority rule.

## Restore into scratch by default

For an explicitly assigned isolated drill, use the assignment's disposable target, permitted backup
data, and authorized actor; no separate production-change packet is needed. Isolate restored jobs,
integrations, and network access from live systems. A scratch name alone does not establish isolation.
Live or production-connected changes use `production-change-gate`. Never overwrite the live service
just to test a backup; an in-place rehearsal also needs a second recovery copy.

## Drill sequence

1. Name the service, backup/snapshot, recovery cutoff in UTC, expected RPO and RTO, and a data/
   application check. The cutoff is the simulated failure time or approved PITR target.
2. Start the wall clock before locating the backup and runbook. The measured duration includes
   retrieval, credentials, restore, reconstruction, and verification.
3. Follow the current runbook and record deviations, including steps that required undocumented
   knowledge.
4. Restore the newest eligible backup into scratch. Use failure-sensitive client flags so partial
   SQL errors cannot return success.
5. Verify data correctness and application usability. Record the recovered backup/PITR watermark
   and its UTC mapping, corroborated by recovered transactions. Measure the gap to the cutoff
   against RPO, separately from total elapsed recovery time against RTO. A backup filename or a
   successful query alone cannot prove freshness; missing watermark evidence leaves RPO unverified.
6. Inventory what the backup excluded: secrets/config, routes, certificates, ownership, schedules,
   and indexes that require rebuild. These are recovery-scope findings.
7. Return backup identity, watermarks, timings, evidence, deviations, and verdict. Update the runbook
   when that is part of the authorized assignment; an evidence-only helper returns proposed changes
   to its caller. The authorized drill owner tears down the scratch target.

## Verdict

- **Pass:** usable data restored with both RPO and RTO met.
- **Pass with findings:** both objectives met, with runbook or nonessential recovery-scope gaps.
- **Fail:** unusable/incomplete required recovery, or a measured objective missed. Name the gap and
  its owner before repeating the drill.
- **Inconclusive:** missing evidence prevents judging either objective; do not report a pass.

Report locate, restore, and verify timings separately.
