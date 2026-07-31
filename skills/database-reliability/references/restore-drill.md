# Restore drill — turn a backup into recovery evidence

Read when rehearsing recovery or claiming an RTO/RPO. A backup never restored is inventory, not
recovery evidence. State-changing work still requires the exact human-approved target/action/
rollback packet from `../SKILL.md`.

## Restore into scratch by default

Use a throwaway database name, container, or temporary path. Never overwrite the live service just
to test a backup. An in-place rehearsal is exceptional, production-facing, and requires an approved
plan plus a second recovery copy.

## Drill sequence

1. Name the service, exact backup/snapshot, expected RPO, and a concrete success criterion (a query,
   checksum, or application read—not “the command exited zero”).
2. Start the wall clock before locating the backup and runbook. The measured duration includes
   retrieval, credentials, restore, reconstruction, and verification.
3. Follow the current runbook exactly. Every deviation is a runbook finding; a restore performed
   from the original author's memory proves little about the 3 a.m. path.
4. Restore the newest eligible backup into scratch. Use failure-sensitive client flags so partial
   SQL errors cannot return success.
5. Verify data correctness and application usability against the criteria from step 1.
6. Inventory what the backup excluded: secrets/config, routes, certificates, ownership, schedules,
   and indexes that require rebuild. These are recovery-scope findings.
7. Record backup identity, timings, evidence, deviations, and verdict in the runbook; then tear down
   the scratch target.

## Verdict

- **Pass:** restored and verified inside the objective.
- **Pass with findings:** recovery worked but the runbook or recovery scope was incomplete.
- **Fail:** unusable, incomplete, or unverifiable backup. Treat this as an urgent durability gap,
  repair the backup path, and repeat the drill.

Never turn a partial drill into “probably fine.” Preserve `[verified]`, `[sourced]`, and
`[unverified]` labels and report locate, restore, and verify timings separately.
