# Durable background work

`../SKILL.md` owns the house contract. The repository's queue wins; otherwise load `stack-profile`.
ARQ or TaskIQ for async FastAPI, and Celery for its ecosystem, are candidates to assess against the
workload, not fleet defaults; an accepted stack choice belongs in `stack-profile`.

- **Acceptance:** new asynchronous receivers answer `202`; a provider's acknowledgement contract
  wins. Expose status for long-running work: acceptance is not completion.
- **Work still owed after the acknowledgement** (follow-up calls, enrichment, notifications) is
  persisted as pending in the same transaction as the event, and a worker resumes pending work at
  startup and while running. FastAPI `BackgroundTasks` and in-memory threads die with the process,
  and a sender that got a 2xx will not redeliver, so work kept only in memory is lost on a crash.
  A pending step runs again after a crash, and on every instance that resumes it: make each step
  safe to repeat. Mark a local step done in the transaction that commits its effect, guarded so
  one writer wins. A remote call or notification cannot share that transaction and follows
  [API-write recovery](./api-writes.md). Where a repeat costs, claim the step first with an atomic
  update and a lease that expires soon after the step's deadline, so a crashed owner does not
  strand it. The acknowledgement stays `202`, or the provider's required code, while any of that
  work is pending, even when the record it will complete already exists.
- **Dispatch:** when a business transaction must enqueue work, commit the business state and the
  dispatch intent atomically, through an existing transactional queue or an outbox. Add an outbox
  only for that boundary. Publish outside the transaction and mark the message sent only after the
  broker durably confirms it. Consumers must tolerate a duplicate publish after a crash.
- **Consumption:** enforce unique event IDs per producer, tenant and logical consumer in the
  database. Commit the deduplication record and the local business change together, keep
  deduplication records through the replay horizon, then acknowledge. Ordering also needs aggregate
  sequence or version checks. External effects follow [API-write recovery](./api-writes.md).
  Check the queue's persistence, acknowledgement and worker-loss settings: Celery's `acks_late`
  alone still acknowledges a task whose worker process dies; redelivery needs
  `task_reject_on_worker_lost`, which can loop on a message that keeps killing workers.
- **Failures:** bound execution time and retries, with backoff and jitter. Persist each batch item's
  outcome, retry the eligible failures, reconcile UNKNOWN effects as API writes describes, and keep
  identities stable. Never acknowledge a whole batch that partly failed. A permanent failure needs a
  durable failed or dead-letter state, a redacted cause and a named operator disposition. Redrive
  only after fixing the cause and checking earlier effects; never reset an identity or recycle a
  poison message indefinitely. Track pending age, retries, dead letters and stalled dispatch.
- **Shutdown and takeover:** bound concurrency and prefetch. Stop intake, drain within the
  deadline, and leave unfinished work recoverable without a success acknowledgement. Scheduled jobs
  stay idempotent under one scheduler. Reuse existing coordination, and fence a stale lease owner at
  the write boundary during takeover.

**Verify changed boundaries** against the configured queue; mocks establish only handler behavior.

| Failure case | Required observation |
|---|---|
| Crash after the business commit but before publish; after publish but before marking sent; after the consumer commits but before ack | Eventual delivery with one business effect |
| A duplicate or poison item in a partly successful batch | Deduplication, per-item outcomes, bounded retries and a durable failed disposition |
| Shutdown with unfinished work; takeover of an expired lease, if supported | The work stays recoverable and the stale owner cannot commit |

[Outbox rationale](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)
and [Celery worker-loss setting](https://docs.celeryq.dev/en/stable/userguide/configuration.html#task-reject-on-worker-lost).
