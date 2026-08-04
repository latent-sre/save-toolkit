# Serving live data (SSE / WebSocket)

Read this when the service streams to clients — status, metrics, or logs pushed rather than polled.

The universal backend rules live in `skills/backend-craft/SKILL.md`. On any conflict, SKILL.md wins.

## Serving live data (SSE / WebSocket)

The frontend's default for live data is SSE — this is the serving half of that contract.

- **SSE for one-way push** (status, metrics, logs): send a keep-alive comment every 15–30 s so proxies don't kill idle streams; `Cache-Control: no-cache` and disable proxy buffering (flush per event).
- **Support resume**: give events `id`s and honor `Last-Event-ID` on reconnect — EventSource auto-reconnects, so design for dropped clients rather than pretending they don't happen.
- **WebSocket only when the client must push too**; then heartbeat/pong and close idle connections deliberately.
- **Bound it**: cap concurrent streams, drop slow consumers instead of buffering unbounded, and count open streams in your metrics.
- Streams are requests: authenticate them, tag them with a request ID, and close them cleanly during shutdown.
