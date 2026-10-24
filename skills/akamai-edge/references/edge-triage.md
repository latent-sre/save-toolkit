# Akamai edge triage — evidence surfaces and how to read them

Apply the [parent read/credential boundaries](../SKILL.md). Confirm exact values and available
features against official documentation and the target account; these descriptions are not live evidence.

## Edge Diagnostics (Control Center → Test & troubleshoot)

Control Center and the Edge Diagnostics API expose:

- **Translate Error String** — paste the error reference from an Akamai error page (for
  "Reference #9.6f64d440.1318965461.2f2b078" enter `#9.6f64d440.1318965461.2f2b078`, letters
  lowercase, up to 10 at once) and get the error summary plus edge logs. **Decode promptly: the
  logs behind a reference number survive only ~6–24 hours** depending on server and traffic.
  Enable *Trace forward logs* to include every edge server in the request path, not just the one
  that errored. Also accepts a Global Request Number (GRN, same format).
- **Get Error Statistics** — per URL or CP code, splits errors into the two legs: **client→edge**
  (edge response to client) and **edge→origin** (edge forward request), with HTTP codes and their
  share of traffic. Caveat: it is a ~9-second traffic sample from the last 2 minutes — a
  low-traffic property can sample to zero without being healthy.
- **URL Health Check** — one async job running GREP, dig, curl, MTR, and URL translation for a
  single URL simultaneously.
- **GREP (View Logs)** — raw edge-server log search when you already know which server/time.

## Cache status via debug headers — know which mechanism the property supports

**Enhanced Debug** uses an `Akamai-Debug` header with a time-limited token from the property's
configured debug key; check the exact key format in its schema, not a byte/hex-length assumption.
*Disable Pragma Debugging* defaults to disabling legacy unauthenticated `Pragma` headers.
Legacy support on other properties remains unconfirmed; check the actual property.

- `Akamai-Debug: <auth-token> cache` → returns `X-Cache`, `X-Cache-Remote`, `X-Check-Cacheable`, `X-Cache-Key`,
  `X-True-Cache-Key`, `Edge-Cache-Tag`, `Akamai-Cache-Status` and related headers.
- `Akamai-Debug: <auth-token> cache vars` ≈ the legacy set `Pragma: akamai-x-get-request-id, akamai-x-cache-on,
  akamai-x-cache-remote-on, akamai-x-check-cacheable, akamai-x-get-cache-key,
  akamai-x-get-true-cache-key, akamai-x-get-extracted-values`.
- The human supplies the token first, or in the case-sensitive `akamaidebugtoken` cookie with
  options alone in the header. An invalid/expired token returns `Akamai-Debug-Status` and no other
  debug headers; absent cache headers then say nothing about cache health. Never quote the token.
- The behavior can also emit an `Akamai-GRN` response header — feed it straight into Translate
  Error String.
- Staging responses carry `X-Akamai-Staging` (e.g. `ESSL`) — the header that proves you hit
  staging, not production.

**X-Cache values**:

| Value | Means |
|---|---|
| `TCP_HIT` | served from edge disk cache |
| `TCP_MEM_HIT` | served from edge memory — hot object |
| `TCP_MISS` | not in cache — fetched from origin |
| `TCP_REFRESH_HIT` | stale in cache; origin returned 304, served refreshed copy |
| `TCP_REFRESH_MISS` | stale in cache; the refresh got a new object from origin |
| `TCP_REFRESH_FAIL_HIT` | stale in cache and origin unreachable, so the stale object was served |
| `TCP_IMS_HIT` | client sent `If-Modified-Since`; object fresh in cache and served |
| `TCP_NEGATIVE_HIT` | a cached negative response (e.g. Not found) served again |

`TCP_REFRESH_FAIL_HIT` on a debug request means the origin is unreachable while the edge serves
stale content — an origin-leg finding, not a healthy edge; a delete purge removes that stale copy.

`akamai-x-cache-remote-on` adds `X-Cache-Remote` for tiered distribution / SiteShield: child-miss +
parent-hit reads as a miss on `X-Cache` and a hit on `X-Cache-Remote` — offload is working even
though the child missed.

Production debug-header requests stay **recommend-for-human** whatever tools the invoking lane
holds; show the exact `curl -H "Akamai-Debug: …"` line with a token placeholder and the expected
headers. Other observations follow the invoking agent's granted, scoped, output-protected read paths.

## DataStream 2 — the sustained/fleet-wide evidence

Resolve the destination from `stack-profile`'s edge row; do not invent an index. `obs-analysis`'s
query catalog supplies hostname/region error and cache-share shapes. Relevant DataStream 2 fields:

- `cacheStatus` — `0` means the object was absent from cache; `1` means present. Cached negative
  responses or stale objects can still be served from upstream, so presence alone does not prove
  origin offload; correlate cacheability and breadcrumbs when needed.
- `turnAroundTimeMSec` — milliseconds from the edge receiving the final request header until it
  writes the first response byte to the client. This interval can include edge and upstream work;
  it does not isolate origin latency. Compare cache status, breadcrumbs, and origin-side timing
  before attributing a regression.
- `errorCode` — edge error detail, e.g. `"ERR_ACCESS_DENIED|fwd_acl"`.
- `statusCode` (`0` when the client connection ended before a response), `reqHost`, `country`
  (where the request originated) and `serverCountry` (where it was served) — split error share by
  these to test a regional report.

Field availability on the target stream is unconfirmed until observed there.

Completeness limits:

- Low-latency delivery (~5 minutes) is less complete than log-completeness delivery (~60 minutes);
  absent early lines do not establish absent traffic.
- Upload failures can exhaust retries without backup. Monitor them rather than interpreting missing
  lines as missing traffic. [FAQ](https://techdocs.akamai.com/datastream2/docs/faq) and
  [troubleshooting](https://techdocs.akamai.com/datastream2/docs/troubleshooting) disagree on retry
  budgets; the applicable count remains unconfirmed.

## Offload and error reports (Control Center → Reporting)

Use **Traffic by Hostname**, not the discontinued Traffic report's filters. Reporting API v2 uses
`delivery/traffic/current`; omitted CP-code filtering covers all available CP codes. Offload
`(edge − origin) / edge × 100` is a working formula, not a quotation: the API defines
`offloadedHitsPercentage` in prose.

For falling offload/rising origin traffic, compare property activations, cache keys and TTL before
attributing capacity trouble.

## App & API Protector (WAF) — "is the WAF blocking real users?"

Read-only triage path:

1. **Web Security Analytics** (Security Center): dimensions/pivots and sampled request logs with
   headers and triggered attack types. Repeated rules on ordinary-looking user requests are a
   false-positive lead, not proof.
2. **Events report / WAF activity by attack group** — applied actions, targeted
   hostnames/policies, source geographies.
3. What the client saw: the standard deny is an **HTTP 403**, but properties may use **custom deny
   actions** (custom HTML/JSON, up to 20 per config) — so "no 403 in client logs" does not clear
   the WAF. Whether the default deny page's reference number decodes in Translate Error String is
   unconfirmed — try it, don't assert it.
4. **SIEM Integration** can deliver security events to Splunk; offset/time-based API fetches can
   replay the last **12 hours**. Older records depend on destination retention and portal availability.

Evidence of a false positive — the sampled requests, the rule id, the affected user share — goes to
the human security policy owner. This fleet never tunes or disables a protection itself.
