# Breaking HTTP changes

Use when compatibility checks identify a break or a breaking change is requested. Additive
operations, optional fields/parameters and enum values consumers tolerate need no version migration.

1. Show the contract change, affected consumers and compatibility evidence (`oasdiff` for the
   house pipeline, existing checks for established services); identify unavailable evidence.
   Obtain the caller's approval for the concrete break unless existing approval already covers it.
2. Prefer expand/contract within `/v1`: add alongside the old shape, migrate consumers, remove
   only once the old shape has no callers. Rolling deploys and open browser tabs need both.
3. When consumers outside the release cannot migrate in time, serve `/v2` beside `/v1`, at most
   two versions live. Deprecating `/v1` responses carry `Deprecation: @<unix-seconds>` (RFC 9745),
   `Sunset: <HTTP-date>` (RFC 8594) no earlier than deprecation, and
   `Link: <successor-doc>; rel="deprecation"`. After sunset, `/v1` returns `410` problems.
4. When using oasdiff, record accepted breaks in its `--err-ignore` file: method, path and change
   text from its output; keep `--fail-on` intact. Otherwise use the service's exception mechanism.
   Name the reason and approving caller in the PR.

Existing services keep their established versioning and error conventions until an authorized
migration; adding a route alone does not authorize one.
