# Background work, schedules, and webhooks

Read for a queue, recurring job, scheduler, or inbound webhook.

- In-process work is only for short, bounded, loss-tolerant tasks. Work that must survive restart or
  be retried belongs in the repository's durable queue or platform job mechanism.
- Treat delivery as at-least-once unless the selected system proves otherwise. Make handlers
  idempotent, define retry/backoff and poison-message behavior, and expose dead-letter/recovery paths.
- Give recurring jobs one scheduler owner; prevent or safely handle overlap and replay. A sleeping
  process loop is not durable scheduling.
- Verify webhook authenticity before acknowledging it. Bound body size/time, deduplicate by provider
  event identity, acknowledge within the provider contract, and move slow work to the durable path.
- Record job/event identity, attempt, correlation, duration, outcome, and next recovery step without
  logging payload secrets.
