# Akamai edge triage — evidence surfaces and how to read them

Apply the [parent read/credential boundaries](../SKILL.md).

## Edge Diagnostics (Control Center → Test & troubleshoot)

- **Translate Error String** — paste the error reference from an Akamai error page (for
  "Reference #9.6f64d440.1318965461.2f2b078" enter `#9.6f64d440.1318965461.2f2b078`, letters
  lowercase, up to 10 at once) to retrieve the error summary and edge logs. **Decode promptly:
  edge logs behind a reference number last 6–24 hours** depending on server and traffic (budget
  for 6h). For a blocked request, the AppSec error translator reaches back 31 days. Enable *Trace
  forward logs* to include every edge server in the request path. Also accepts a Global Request
  Number (GRN, same format).
- **Get Error Statistics** — per URL or CP code, splits errors into **client→edge** (edge response
  to client) and **edge→origin** (edge forward request), with HTTP codes and traffic share.
  Caveat: it is a ~9-second traffic sample from the last 2 minutes; a low-traffic property can
  sample to zero without being healthy.
- **URL Health Check** — one async job running GREP, dig, curl, MTR, and URL translation for a URL.
- **GREP (View Logs)** — raw edge-server log search when server and time are already known.

## Cache status via debug headers

**Enhanced Debug** uses an `Akamai-Debug` header with a time-limited token from the property's
configured debug key; *Disable Pragma Debugging* disables legacy unauthenticated `Pragma` headers
by default. Check which mechanism the target property enables.

- `Akamai-Debug: <auth-token> cache` → returns `X-Cache`, `X-Cache-Remote`, `X-Check-Cacheable`,
  `X-Cache-Key`, `X-True-Cache-Key`, `Edge-Cache-Tag`, `Akamai-Cache-Status`, and related headers.
- `Akamai-Debug: <auth-token> cache vars` ≈ legacy `Pragma: akamai-x-get-request-id, akamai-x-cache-on,
  akamai-x-cache-remote-on, akamai-x-check-cacheable, akamai-x-get-cache-key,
  akamai-x-get-true-cache-key, akamai-x-get-extracted-values`.
- Give the human the exact `curl -H "Akamai-Debug: …"` command with a token placeholder (or the
  case-sensitive `akamaidebugtoken` cookie with options alone in the header). Never quote the token.
  An invalid or expired token returns `Akamai-Debug-Status` and no other debug headers.
- `Akamai-GRN` response headers feed straight into Translate Error String.
- Staging responses carry `X-Akamai-Staging` (`ESSL` or `EdgeSuite`), confirming staging vs. production.

**Read each cache code at its own hop.** `X-Cache` describes the child edge serving the client;
`X-Cache-Remote` (when present) describes the parent in Tiered Distribution or SiteShield;
`Akamai-Cache-Status` can report both hops in one header. Confirm an origin forward in Edge
Diagnostics or origin logs before attributing load or latency to origin.

| Value | Means |
|---|---|
| `TCP_HIT` | served from the reporting hop's disk cache |
| `TCP_MEM_HIT` | served from the reporting hop's memory cache |
| `TCP_MISS` | the reporting hop had no usable cached copy |
| `TCP_REFRESH_HIT` | a stale object was revalidated upstream and the cached copy was served |
| `TCP_REFRESH_MISS` | the upstream refresh returned a replacement object |
| `TCP_REFRESH_FAIL_HIT` | the upstream refresh failed and the hop served its stale copy |
| `TCP_IMS_HIT` | client sent `If-Modified-Since`; object fresh in cache and served |
| `TCP_NEGATIVE_HIT` | a cached negative response (e.g. Not found) served again |

## DataStream 2 — sustained and fleet-wide evidence

Resolve the log destination from `stack-profile`'s edge row; do not invent an index. Key fields:

- `cacheStatus` — `0` means absent from the reporting cache; `1` means present. Use `breadcrumbs`,
  where enabled, to identify upstream hops (`c` for cache parent, `o` for origin).
- `turnAroundTimeMSec` — milliseconds from the edge receiving the final request header until it
  writes the first response byte to the client (includes both edge and any upstream work; compare
  `cacheStatus`, `breadcrumbs`, and origin timing before attributing latency to origin).
- `errorCode` — edge error detail, e.g. `"ERR_ACCESS_DENIED|fwd_acl"`.
- `statusCode` (`0` when the client connection ended before a response), `reqHost`, `country`
  (client origin), and `serverCountry` (serving edge location).
- Low-latency delivery (~5m) is less complete than log-completeness delivery (~60m); absent early
  lines or upload failures do not prove absent traffic.

### DataStream 2 SPL — 5xx and cache-miss share with classification coverage

With midgress enabled, filter `isMidgress=0` (client-to-edge) to exclude `1` (internal edge-to-edge);
omit that predicate only for a verified client-only stream without the field. A literal
`statusCode=0` counts as a known non-5xx request. Report `pct_5xx` or `pct_not_in_cache` only when
its field covers every client request in that bucket (`status_known=requests`, `cache_known=requests`);
add `country` or `serverCountry` to `by` for regional splits:

```spl
index=<datastream_index> sourcetype=<datastream_sourcetype> earliest=<start_epoch> latest=<end_epoch> isMidgress=0
| bin _time span=5m
| eval status=if(match(statusCode, "^(0|[1-5][0-9]{2})$"), tonumber(statusCode), null()),
       cache=if(match(cacheStatus, "^[01]$"), tonumber(cacheStatus), null())
| stats count AS requests, count(status) AS status_known, count(cache) AS cache_known,
        count(eval(status>=500)) AS errors_5xx, count(eval(cache=0)) AS not_in_cache by _time, reqHost
| eval pct_status_known=round(100*status_known/requests, 2), pct_cache_known=round(100*cache_known/requests, 2),
       pct_5xx=if(status_known=requests, round(100*errors_5xx/requests, 2), null()),
       pct_not_in_cache=if(cache_known=requests, round(100*not_in_cache/requests, 2), null())
```

## Offload and error reports (Control Center → Reporting)

Use **Traffic by Hostname** (not the discontinued Traffic report's filters). Reporting API v2 uses
`delivery/traffic/current`; omitted CP-code filtering covers all available CP codes, and
`offloadedHitsPercentage` reports `(edge − origin) / edge × 100`.

## App & API Protector (WAF) — "is the WAF blocking real users?"

1. **Web Security Analytics** (Security Center): dimensions/pivots and sampled request logs with
   headers and triggered attack types. Repeated rules on ordinary user requests are a
   false-positive lead, not proof.
2. **Events report / WAF activity by attack group** — applied actions, targeted hostnames/policies,
   and source geographies.
3. **Custom deny actions:** standard deny is **HTTP 403**, but properties can configure **up to 20
   custom deny actions** with custom HTML/JSON and status codes — so "no 403 in client logs" does
   not clear the WAF. For a blocked request's reference number,
   `GET /appsec/v1/error-translator/{errorReferenceCode}` covers the past **31 days** and returns
   failure categories including `WAF`.
4. **SIEM Integration** delivers security events to Splunk: offset fetches resume from the last
   pull, while time-based replay (`from`/`to`) is limited to the last **12 hours**.
