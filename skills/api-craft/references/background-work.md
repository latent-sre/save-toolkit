# Durable background work

Use the repository's durable-work system; load `stack-profile` before choosing another.

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
- **Failures:** bound execution/retries. Persist each batch item's outcome,
  retry eligible failures with stable identities, and reconcile UNKNOWN effects. Never acknowledge
  a partly failed batch as complete. Permanent failures need durable failed/dead-letter state,
  redacted cause and operator disposition. Fix the cause and check prior effects before redrive;
  never reset identities or recycle poison messages indefinitely. Track pending age, retries,
  dead letters and stalled dispatch.
- **Shutdown/takeover:** bound concurrency and any prefetch; stop intake, drain within the deadline,
  leave unfinished work recoverable without a success acknowledgement. Scheduled jobs stay
  idempotent under one scheduler. Reuse coordination and fence stale lease owners at the write
  boundary during takeover.

Use the configured persistent store/queue, not handler mocks, to check: restart after acceptance
but before execution; crashes after business commit, publish and consumer commit; rejected/unroutable
dispatch; partly failed batches; shutdown and expired-lease takeover. Verify one effect, recoverable
work, honest sent/completion state, retained deduplication/outcomes and stale-writer fencing.
