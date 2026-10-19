# API writes

Use for retryable or concurrent writes; preserve the project's contract, datastore and auth.

## Choose the contract

- Choose native idempotence, client-chosen resource IDs, atomic preconditions or a replay key
  according to the operation. Persist replay state only when needed.
- Authorize every attempt, including replays.

## When recording replay keys

- Document missing-key, conflicting-intent and in-progress responses; choose statuses, retry
  hints and error shapes with consumers. A state conflict is distinct from schema validation.
  Never replace or replay a conflicting result.
- Scope keys by authenticated caller/tenant and operation. Fingerprint normalized, validated
  payload, target and API version.
- Replay the committed identity and documented status, body and headers, including any agreed
  replay indicator. Pending work waits a bounded time or returns in-progress, never completion
  before commit. Store business data, not credentials,
  cookies or per-attempt trace headers.
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
  different keys can still overwrite each other. Test stale writers. Use `database-reliability`
  for migration safety; the builder writes migration code and runs assigned isolated rehearsals.
  Live changes follow `production-change-gate`.
- Remote effects cannot share a local transaction. Retry with provider idempotency only within
  its documented scope and retention window; otherwise an interrupted call stays UNKNOWN until
  authoritative readback or operator reconciliation. Never resend blindly or hold a transaction
  across the network call. Use the project's durable workflow where needed.

## Verify the boundary

Test the chosen write contract with the project's native tests. Inspect authoritative effects
and stored business state independently of receipt/response caches; matching IDs alone miss
corruption.

Cover duplicates and authorization-scope isolation; for recorded replay, include conflicting
payloads and the promised response. An idempotent `PUT` or natural-key upsert needs a duplicate-request
test; where duplicates/lost responses have a business effect, also test crashes on both sides of
commit:

- Make the second request reach server arbitration before the first commits.
- Prove the failpoint ran and the killed worker exited; overlapping calls or caught exceptions
  prove neither.
- Restart workers/clients against the same storage, with bounded waits and disposable targets.
- Add applicable expiry, revoked-authorization and stale-update cases.

Offline controls establish assertion behaviour; application tests must establish database
concurrency and recovery.

[Atomic replay recording](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/),
[PostgreSQL conflict primitive](https://www.postgresql.org/docs/17/sql-insert.html#SQL-ON-CONFLICT)
(application owns replay/authorization policy),
[Idempotency-Key draft](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/).
