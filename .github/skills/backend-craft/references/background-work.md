# Durable background work

Use the repository's queue; otherwise load `stack-profile`. ARQ/TaskIQ for async FastAPI and Celery
for its ecosystem are candidates, not defaults; accepted choices belong in `stack-profile`.

- **Acceptance:** new asynchronous HTTP receivers return `202` with status for long-running work;
  a provider's acknowledgement contract wins. Acceptance is not completion.
- **Work owed after acknowledgement:** persist pending work with the event in one transaction;
  workers resume it at startup and while running. `BackgroundTasks` and in-memory threads die
  with the process, and an acknowledged sender will not redeliver. Make each resumed step safe
  to repeat. Commit a local effect and completion together, guarded so one writer wins; remote
  effects follow [API-write recovery](./api-writes.md). Where repetition costs, atomically claim
  the step with a lease expiring soon after its deadline. Keep the acknowledgement `202` (or the
  provider's code) while work remains, even if the record it will complete already exists.
- **Dispatch:** atomically commit business state and dispatch intent using the existing
  transactional queue or an outbox added for this boundary. Publish outside the transaction;
  mark sent only after durable broker confirmation. Consumers tolerate duplicate publication.
- **Consumption:** enforce event IDs unique by producer, tenant and logical consumer in the
  database. Commit deduplication and local effect together, retain deduplication through the
  replay horizon, then acknowledge. Enforce aggregate sequence/version for ordering; remote
  effects follow API-write recovery. Verify queue persistence, acknowledgement and worker-loss
  settings: Celery `acks_late` alone acknowledges worker-process death; redelivery requires
  `task_reject_on_worker_lost`, which can loop on a message that kills workers.
- **Failures:** bound execution/retries with backoff and jitter. Persist each batch item's outcome,
  retry eligible failures with stable identities, and reconcile UNKNOWN effects. Never acknowledge
  a partly failed batch as complete. Permanent failures need durable failed/dead-letter state,
  redacted cause and operator disposition. Fix the cause and check prior effects before redrive;
  never reset identities or recycle poison messages indefinitely. Track pending age, retries,
  dead letters and stalled dispatch.
- **Shutdown/takeover:** bound concurrency and prefetch; stop intake, drain within the deadline,
  leave unfinished work recoverable without a success acknowledgement. Scheduled jobs stay
  idempotent under one scheduler. Reuse coordination and fence stale lease owners at the write
  boundary during takeover.

Verify changed boundaries against the configured queue; mocks establish only handler behaviour.

| Failure case | Required observation |
|---|---|
| Crash after business commit/before publish, after publish/before marking sent, or after consumer commit/before ack | Eventual delivery with one business effect |
| Duplicate/poison item in a partly successful batch | Deduplication, per-item outcomes, bounded retries, durable failed disposition |
| Shutdown with unfinished work; expired-lease takeover where supported | Recoverable work; stale owner cannot commit |

[Outbox rationale](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html),
[Celery worker-loss setting](https://docs.celeryq.dev/en/stable/userguide/configuration.html#task-reject-on-worker-lost).
