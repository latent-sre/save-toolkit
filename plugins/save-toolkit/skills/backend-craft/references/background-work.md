# Background work & scheduling

Read this when the task involves a queue, a scheduled or recurring job, or an inbound webhook.

The universal backend rules live in `skills/backend-craft/SKILL.md`. On any conflict, SKILL.md wins.

## Background work & scheduling

- **In-process** (FastAPI BackgroundTasks / a goroutine) only for short, fire-and-forget, loss-tolerant work. Anything that must not be lost goes to a **real queue** — ARQ or TaskIQ for async-native FastAPI, Celery when you need its ecosystem/scale.
- **Scheduled jobs** (polling an upstream, a nightly sync) via a scheduler (APScheduler / cron) with one owner — not a `sleep` loop; make each run **idempotent** so an overlap or replay is safe.
- **At-least-once is the norm**: jobs retry with backoff and land failures in a **dead-letter** path rather than vanishing; log job start/end with a correlation ID.
- **Receiving webhooks**: verify the signature, respond fast (202) and process async, and dedupe by event ID — deliveries repeat.
