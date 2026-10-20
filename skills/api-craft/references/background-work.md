# Durable background work

Use the repository's durable-work system; load `stack-profile` before choosing another.

- **Acceptance:** follow the producer/consumer acknowledgement contract. HTTP `202` with a
  status resource is one pattern for long-running work. Acceptance is not completion.
- **Work owed after acknowledgement:** persist pending work atomically with the state that
  creates the obligation; workers resume it at startup and while running. `BackgroundTasks` and
  in-memory threads die with the process, and an acknowledged sender cannot be relied on to
  redeliver. Make each resumed step safe to repeat. Commit a local effect and completion together,
  guarded so one writer wins; remote effects follow [API-write recovery](./api-writes.md). Where
  repetition costs, atomically claim the step with a lease expiring soon after its deadline. Keep
  acceptance and completion distinct while work remains, even if its target record already exists.
- **Broker dispatch, when used:** commit business state and dispatch intent atomically with
  the existing transactional queue or an outbox. Publish outbox entries outside the transaction;
  mark sent only after the broker's contract confirms durable acceptance at the intended
  destination. Treat unroutable returns/rejections as failed dispatch; consumers tolerate
  duplicate publication.
- **Queue consumption, when used:** enforce event IDs unique by producer, tenant and logical
  consumer in the database. Commit deduplication and local effect together, retain deduplication through the
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
- **Shutdown/takeover:** bound concurrency and any prefetch; stop intake, drain within the deadline,
  leave unfinished work recoverable without a success acknowledgement. Scheduled jobs stay
  idempotent under one scheduler. Reuse coordination and fence stale lease owners at the write
  boundary during takeover.

Verify applicable boundaries against the configured persistent work store and, where used,
queue; mocks establish only handler behaviour.

| Failure case | Required observation |
|---|---|
| Crash after durable acceptance, before execution; restart against the same work store | Pending work resumes and commits one intended business effect |
| With a broker: crash after business commit/before publish, after publish/before marking sent, or after consumer commit/before ack | Eventual delivery with one business effect |
| With a broker: unroutable or rejected publish | Dispatch stays pending or failed, never sent; work remains recoverable |
| Duplicate/poison item in a partly successful batch | Deduplication, per-item outcomes, bounded retries, durable failed disposition |
| Shutdown with unfinished work; expired-lease takeover where supported | Recoverable work; stale owner cannot commit |
