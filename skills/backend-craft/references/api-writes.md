# API writes

For retryable or concurrent writes; preserve the project's interface, datastore, auth and native tests.

## Identity and replay

- Reuse sufficient native idempotence (stable resource ID/atomic precondition). Otherwise require
  `Idempotency-Key` for unsafe retries of a new HTTP write; store replay state only when needed.
- Scope keys to authenticated caller/tenant and operation; authorize every attempt, including replay.
  Fingerprint normalized, validated intent: payload, target and API version. Same key with different
  intent must return the project's conflict response without replaying or changing the first result.
- Return the committed identity and documented replay status/body/headers. While pending, use bounded
  waiting or an explicit in-progress response; never claim completion before commit. Store replay-safe
  business data, never credentials, session cookies or per-attempt trace headers.
- Define retention/retry horizons and reconciliation after expiry. Preserve longer-lived uniqueness
  with a durable business ID. Never expire unresolved work to enable another attempt.

## Atomicity and recovery

- Database-enforce a unique scoped claim; commit or roll back the mutation and replay result together.
  Process-local locks and unprotected check-then-insert are insufficient. Resolve competing claims
  using actual database isolation, read the committed result, and bound lock waits/transaction retries.
- Protect read-modify-write operations separately with a version/precondition, atomic predicate or
  appropriate lock; different keys can still lose updates. Test stale writers. Migration execution
  stays with `database-reliability` and the human owner.
- Before-commit termination leaves no committed effect or completed receipt; retry can complete.
  After-commit response loss must replay the original identity/state after restart, without another effect.
- A local transaction cannot make a remote effect atomic. Reuse provider-supported idempotency keys;
  otherwise interrupted calls remain UNKNOWN until authoritative readback/operator reconciliation.
  Never clear the claim and blindly resend, or hold a database transaction across the network call.
  Use the project's durable workflow when needed.

## Evidence

Adapt [write acceptance tests](../assets/test_api_write_contract.py) to a compatible create/replay
contract or translate to native tests. Inspect authoritative effects and detached stable business
state, independently of response/receipt caches; matching IDs alone miss corruption.

Cover duplicates, conflicting payloads, authorized scope isolation and both commit-boundary crashes.
The second request must reach server arbitration before the first commits. Confirm failpoint arrival
and killed-worker exit; client/response overlap and caught exceptions do not prove those boundaries.
Restart workers/clients against unchanged storage; bound every wait and use disposable targets.
Add expiry, revoked authorization and stale-update cases where applicable. Offline controls prove
assertion behavior; adapted application tests must establish database concurrency and recovery.

[Atomic replay recording](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/);
[PostgreSQL conflict primitive](https://www.postgresql.org/docs/17/sql-insert.html#SQL-ON-CONFLICT)
(replay/auth policy remains application-owned).
