# Gorouter error interpretation

Status alone does not establish cause; inspect `X-Cf-RouterError` alongside app and platform evidence.
Agents do not probe untrusted routes; obtain response headers from a human or approved capture point.

| `X-Cf-RouterError` | Status | Means |
|---|---|---|
| `unknown_route` | **404** (400 if `X-Cf-App-Instance`/`X-Cf-Process-Instance` names a missing instance) | Route absent from the router table |
| `no_endpoints` | **503** | Route exists, no healthy backends |
| `endpoint_failure` | **502** by default (varies below) | Backend selected; connection or response failed; app receipt unproven (usually `endpoint_failure (<error>)`) |
| `Connection Limit Reached` | **503** | Backend connection limit reached |
| `route_service_unsupported` | **502** (503 for websocket upgrade) | Route-service configuration error |
| `empty_host` | **400** | `Host` header empty or equals remote address (often an upstream LB misconfig) |
| `invalid_cf_app_instance_header`, `invalid_cf_process_instance_header` | **400** | Malformed instance-routing header |
| `max-request-size-exceeded` | **431** | Request line and headers exceed router limit |

- **`endpoint_failure` status breakdown:** `525` TLS handshake failure or TLS to non-TLS backend;
  `503` backend cert hostname mismatch; `526` backend cert not verified; `496` backend rejected
  client cert; `502` otherwise. `499` (client cancelled before headers) appears only in Gorouter logs.
- **Keep-alive races:** Upstream Gorouter's backend idle timeout is hardcoded at **90 s**. An app
  server idle timeout `< 90 s` can close a socket right as Gorouter reuses it; recommend `> 90 s` on
  the app server (e.g. Tomcat `server.tomcat.keep-alive-timeout`) under `production-change-gate`.
  Gorouter configuration itself is platform-owned.
- **Platform clock skew:** A `502` with `ExpiredOrNotYetValidCertFailure` (`x509: certificate ... is not yet valid`)
  indicates clock skew between Gorouter and a Diego cell — escalate NTP/time-sync evidence to the
  platform team rather than debugging the app.
