# Gorouter error interpretation

Apply the [parent header-capture, escalation and authority rules](../SKILL.md).
Status alone does not establish cause; use the router error and corroborating evidence:

| `X-Cf-RouterError` | Status | Means |
|---|---|---|
| `unknown_route` | **404** | route absent from the router table |
| `no_endpoints` | **503** | route exists, no healthy backends |
| `endpoint_failure` | **502** | backend selected; connection or response failed; app receipt unproven |
| `Connection Limit Reached` | 503 | backend connection limit |
| `route_service_unsupported` | 502 | route-service configuration problem |

- For `endpoint_failure`, check refused connections, mid-request crashes, router timeouts and
  keep-alive races; app receipt is unproven. Upstream Gorouter's backend idle timeout is hardcoded
  at 90 s. An app idle timeout **< 90s** can close a connection as Gorouter reuses it; propose
  **> 90s** for the app server (Tomcat: `server.tomcat.keep-alive-timeout`) under the parent change
  rules. This concerns router-to-app pooling; frontend idle timeout is separate and
  platform-configurable. Gorouter changes remain platform-owned.
- A 502 can also be **platform-side**: clock skew between Gorouter and a Diego cell makes the cell's
  TLS certificate look not-yet-valid (`x509: certificate ... is not yet valid`), surfaced as
  `ExpiredOrNotYetValidCertFailure`. Escalate that NTP/time-sync evidence to the platform team rather
  than chasing it app-side.
- A 503 with `no_endpoints` calls for backend-availability checks; `Connection Limit Reached`
  calls for connection-pressure checks. A bare 503 does not prove all instances are down.
- **One route/app affected while others are fine** points to the application lane; a foundation-wide
  pattern goes to the platform team with the parent skill's escalation packet.
