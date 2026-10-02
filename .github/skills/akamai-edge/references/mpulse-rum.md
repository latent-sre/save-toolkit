# mPulse RUM — reading real-user evidence

Sources reviewed 2026-08-07 against official `techdocs.akamai.com/mpulse` pages via indirect
retrieval (search extraction and indexed snapshots — not byte-level fetches).

## What it measures

mPulse is Akamai's real-user monitoring: the **boomerang** JavaScript library collects performance
and business data from real browsers and sends **beacons** to mPulse for aggregation
*[sourced: techdocs.akamai.com/mpulse/docs/how-mpulse-works,
…/mpulse-boomerang/docs/whats-in-an-mpulse-beacon]*. It carries:

- **Page timing**: Back-End Time runs from navigation start to the first response byte;
  Front-End Time runs from that byte until onload/page-ready and includes asset fetches and
  browser work *[sourced: [timer definitions](https://techdocs.akamai.com/mpulse/docs/use-metrics)]*.
- **Core Web Vitals**: LCP, INP, CLS; use INP for responsiveness *[sourced:
  [INP dashboard update](https://techdocs.akamai.com/mpulse/changelog/feb-20-2024-interaction-to-next-paint-dashboard)]*.
- **Custom timers and metrics** — any measurable user-defined duration or business event; the
  Query API (REST/JSON) pulls aggregates programmatically *[sourced: …/mpulse/reference/api]*.
- **Waterfall view** — object-level component timings (DNS lookup, TCP connect, SSL connect,
  request time, response time) from the W3C Resource Timing API *[sourced: …/mpulse/docs/waterfall]*.

## Diagnosing a regression — the slicing method

The built-in dimensions (browser, OS, device, network, geography, ISP) are the tool. The heuristic
— **our synthesis, not a quoted doc claim** `[unverified]`:

1. **Back-End Time moved, Front-End flat** → network/edge/origin side. Correlate with Akamai
   activations (property-config reference), offload changes (Traffic by Hostname), and origin latency
   from origin telemetry or mPulse's **Origin Time** timer when that measurement is available.
   DataStream 2 `turnAroundTimeMSec` includes edge/upstream turnaround and cannot isolate the origin.
   Localized geography/ISP impact raises a path hypothesis; uniform impact leaves shared edge,
   origin, and population changes open.
2. **Front-End Time moved, Back-End flat** → inspect post-first-byte work. This includes network
   and server waits for page assets as well as JS, third-party tags, and rendering. Use the Waterfall
   to distinguish resource fetch delays from browser execution before choosing an owner; a fast
   base document does not clear the servers used by later requests.
3. **Both moved at once** → compare shared delivery dependencies, traffic mix, page changes, and
   instrumentation changes. One shared slowdown can affect both the document and later assets;
   use the Waterfall and request evidence to distinguish the causes.
4. Always compare **equal-duration windows** and check whether traffic mix changed (a bot wave or a
   campaign changes the population, not the site).

*[sourced: [mPulse timer definitions](https://techdocs.akamai.com/mpulse/docs/use-metrics),
checked 2026-09-20; target timer availability and causal attribution remain unverified]*

## Boundaries

- mPulse samples browser sessions. A flat aggregate cannot clear a failing synthetic journey:
  compare URL/journey, time, geography, device/network mix, and beacon count/freshness. Failed
  sessions may never send a beacon. Corroborate with request logs or another journey check before
  attributing the disagreement; `obs-alerting`'s ThousandEyes reference owns the synthetic checks.
- A documented per-beacon edge cache hit/miss dimension is `[unverified]` — do not promise
  beacon-level cache attribution; use DataStream 2 for that.
- Beacon data is user telemetry: apply the fleet's redaction rules before quoting URLs or session
  attributes into a packet.
