# API writes

Use this for writes a client may retry or send concurrently. Keep the project's interface,
datastore, auth and native tests.

## Identity and replay

- Reuse native idempotence when it is enough: a client-chosen resource ID, or an atomic
  precondition. Otherwise require an `Idempotency-Key` header for unsafe retries of a new HTTP write,
  and store replay state only when the operation needs it.
- For the key's status codes, follow the IETF Idempotency-Key draft
  (draft-ietf-httpapi-idempotency-key-header; expired, not an RFC). A missing key on a write that
  requires one is `400`. A key reused with a different payload is `422`: never replay or change the
  first result. A retry while the first request with that key is still in progress is `409` with
  `Retry-After`. Say in the problem `type` which case applies.
- Scope keys to the authenticated caller or tenant and to the operation. Authorize every attempt,
  replays included. Fingerprint the normalized, validated intent: payload, target and API version.
- Return the committed identity and the documented replay status, body and headers. While the first
  request is pending, wait for a bounded time or return an explicit in-progress response; never
  claim completion before commit. Store replay-safe business data only, never credentials, session
  cookies or per-attempt trace headers.
- Publish a retention window for keys and a reconciliation path after it expires. Keep longer-lived
  uniqueness with a durable business ID. Never expire unresolved work so that another attempt can
  run.

## Atomicity and recovery

- Enforce a unique, scoped claim in the database, and commit or roll back the mutation and its
  replay result together. Process-local locks and an unprotected check-then-insert are not enough.
  Resolve competing claims with the database's actual isolation, read the committed result, and
  bound lock waits and transaction retries.
- Protect read-modify-write operations separately, with a version or precondition, an atomic
  predicate or a suitable lock: requests with different keys can still overwrite each other. Test
  stale writers. Running migrations stays with `database-reliability` and the human owner.
- If the process dies before commit, nothing is committed and no receipt is marked complete, so a
  retry can complete the write. If the response is lost after commit, a retry after restart must
  replay the original identity and state without a second effect.
- A local transaction cannot make a remote effect atomic. Reuse the provider's idempotency key where
  it has one. Otherwise an interrupted call's outcome is UNKNOWN until an authoritative readback or
  operator reconciliation settles it. Never clear the claim and resend blindly, and never hold a
  database transaction open across the network call. Use the project's durable workflow when needed.

## Evidence

Adapt the [write acceptance tests](../assets/test_api_write_contract.py) to a compatible
create-and-replay contract, or translate them into native tests. Check the authoritative effects and
the stored business state, independently of response or receipt caches: matching IDs alone miss
corruption.

Test crash boundaries when a duplicate or lost response has a business effect, such as a page,
ticket, order or external call. A natural-key upsert or an idempotent `PUT` needs only a
duplicate-request test. Cover duplicates, conflicting payloads, isolation between authorized scopes,
and crashes on both sides of the commit.

- The second request must reach server arbitration before the first commits.
- Confirm that the failpoint was reached and that the killed worker exited. Overlapping client calls
  and caught exceptions do not prove either boundary.
- Restart workers and clients against the same storage. Bound every wait and use disposable targets.
- Add expiry, revoked-authorization and stale-update cases where they apply.

Offline controls prove only how the assertions behave; the adapted application tests must establish
database concurrency and recovery.

[Atomic replay recording](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/);
[PostgreSQL conflict primitive](https://www.postgresql.org/docs/17/sql-insert.html#SQL-ON-CONFLICT)
(replay and authorization policy stay application-owned);
[Idempotency-Key draft](https://datatracker.ietf.org/doc/draft-ietf-httpapi-idempotency-key-header/).
