# Read back an interrupted PCF rollback

Use for a PCF revision rollback. A flag change or route remap needs readback of its own effective
value or mapping; it does not require a deployment or droplet. The parent skill owns the general
attempt-reconciliation, human-authority, and recovery rules.

A successful rollback creates a new, higher revision number described `Rolled back to revision <n>`.
Do not require the active revision number to equal the target. Establish that the deployment has
completed and the expected instances run the intended droplet. While a rolling rollback is in
progress, both revisions may serve: a description or one converted instance settles nothing yet.
Revision state includes environment variables and the start command, so recheck any earlier
environment-based mitigation that the rollback could have undone; obtain only a sanitized result.
[Source: Cloud Foundry app revisions](https://docs.cloudfoundry.org/devguide/revisions.html).

A matching final state does not establish when the interrupted attempt landed, whether it later
reverted, or what caused recovery. Reconcile with the executor and available receipts/events before
any retry; missing evidence leaves the attempt UNKNOWN. Judge recovery using observations from
an established post-change interval.

Analysis excerpt for the board; include the other board fields in the full reply:

“Revision 14, described ‘Rolled back to revision 12’, is live at 10:10 [sourced]. That is the
expected revision shape; deployment completion and instance convergence still need readback.
We also lack the receipt or timing for the 09:50 attempt [unverified], so the 10:01 errors do not
yet tell us whether it helped. Ask the release owner to reconcile the attempt and obtain fresh
recovery observations. Preserve the earlier confirmed flag change as history, and verify whether
it still holds if it was environment-based. Scaling remains proposal-only. The existing incident
lead retains the mitigation decision; the release owner executes an approved change.”
