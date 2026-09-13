# Durable background work

`../SKILL.md` owns the house contract. The repository's queue wins; otherwise load `stack-profile`.
Defaults until recorded there: ARQ/TaskIQ for async FastAPI, Celery for its ecosystem.

- **Acceptance:** verify webhook authenticity and durably persist work before accepting. Default
  `202` for new asynchronous receivers; provider acknowledgement contracts win. Expose status for
  long-running work; acceptance is not completion.
- **Dispatch:** when a business transaction must enqueue, atomically commit business state and
  dispatch intent through an existing transactional queue or outbox/equivalent. Add an outbox only
  for that boundary. Publish outside the transaction; mark sent after durable broker confirmation.
  Consumers must tolerate duplicate publication after a crash.
- **Consumption:** database-enforce unique event IDs per producer/tenant/logical consumer. Commit
  dedupe and local business mutation together, retain dedupe through the replay horizon, then ack.
  Ordering also needs aggregate sequence/version checks. External effects use [API-write recovery](./api-writes.md).
  Verify queue persistence/ack/worker-loss settings: Celery `acks_late` alone does not ensure redelivery
  after worker-process loss.
- **Failures:** bound execution/retries with backoff/jitter; persist per-item batch outcomes, retry
  eligible failures, reconcile UNKNOWN effects under API writes, and preserve identities. Never ack
  an entire partly failed batch. Permanent failures need durable failed/dead-letter state, redacted
  cause and named operator disposition. Redrive only after fixing the cause and checking prior effects;
  never reset identity or endlessly recycle poison messages. Track pending age, retries, dead letters
  and stalled dispatch.
- **Shutdown/takeover:** bound concurrency/prefetch; stop intake, drain within deadline, and leave
  unfinished work recoverable without a success ack. Scheduled jobs remain idempotent under one
  scheduler. Reuse coordination; fence stale lease owners at the write boundary during takeover.

**Verify changed boundaries** against the configured queue; mocks establish only handler behavior.

| Failure case | Required observation |
|---|---|
| Crash after business commit/before publish, publish/before marking sent, consumer commit/before ack | Eventual delivery; one business effect |
| Duplicate or poison item in a partly successful batch | Dedupe; individual outcomes; bounded retries and durable failed disposition |
| Shutdown with unfinished work; expired lease takeover if supported | Recoverable work; stale owner cannot commit |

[Outbox rationale](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html)
and [Celery acknowledgement caveats](https://docs.celeryq.dev/en/stable/userguide/tasks.html#acks-late).
