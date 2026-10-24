# API writes

## Choose the contract

- Choose native idempotence, client-chosen resource IDs, atomic preconditions or a replay key
  according to the operation. Persist replay state only when needed.
- Authorize every attempt, including replays.

## When recording replay keys

- Define missing-key, conflicting-intent and in-progress responses with consumers; never replace
  or replay a conflicting result. State conflicts are distinct from schema validation.
- Scope keys by authenticated caller/tenant and operation. Fingerprint normalized, validated
  payload, target and API version.
- Replay the committed identity, status, body and agreed headers. Bound pending waits or return
  in-progress; never claim completion before commit. Store business data, not credentials, cookies
  or per-attempt trace headers.
- Publish key retention and post-expiry reconciliation. Keep durable business uniqueness beyond
  that window; never expire unresolved work into permission to run again.
- For local mutations, claim a unique scoped key in the database and commit or roll back the
  mutation and replay result together. Resolve competing claims under the database's isolation,
  read committed results and bound lock waits/retries. Process locks and check-then-insert do not
  arbitrate across instances. Death before commit leaves neither mutation nor completed receipt;
  a retry can finish. A lost response after commit must replay the original identity and result
  after restart, without a second effect.

## Concurrency and remote effects

- Protect read-modify-write separately with a version/precondition, atomic predicate or lock:
  different keys can still overwrite each other. Test stale writers.
- Remote effects cannot share a local transaction. Retry with provider idempotency only within
  its documented scope and retention window; otherwise an interrupted call stays UNKNOWN until
  authoritative readback or operator reconciliation. Never resend blindly or hold a transaction
  across the network call. Use the project's durable workflow where needed.

## Verify the boundary

Inspect authoritative effects and stored business state independently of receipt/response caches;
matching IDs alone miss corruption.

Test duplicates (including idempotent `PUT`/upsert), authorization isolation, replay conflicts and
the promised replay response.
Where duplicates/lost responses affect business state, test both sides of commit:

- Make the second request reach server arbitration before the first commits.
- Prove the failpoint ran and the killed worker exited; overlapping calls or caught exceptions
  prove neither.
- Restart against the same disposable storage with bounded waits.
- Add applicable expiry, revoked-authorization and stale-update cases.

Offline controls do not establish database concurrency or recovery.
