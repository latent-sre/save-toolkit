# Akamai Property Manager as code — versions, activation, rollback

Apply the [parent activation/authority rules](../SKILL.md).

## The change unit: a property version

Editing a property version prepares it; activation changes staging or production:

- **Staging** activations usually finish within **3 minutes** (smaller network, no end-user
  traffic). Resolve the staging edge hostname (the edge hostname with `-staging` before the final
  `.net`, e.g. `<host>.edgekey-staging.net`) to an IP, then request the **public property
  hostname** against that IP to preserve `Host`, SNI, and TLS verification:
  `curl --resolve '<public-host>:443:<staging-ip>' 'https://<public-host>/<safe-path>' -D - -o /dev/null`.
  Verify `X-Akamai-Staging` in the response (`ESSL` for Enhanced TLS, `EdgeSuite` for Standard
  TLS); requesting the edge hostname directly tests the wrong host.
- **Production** activation updates live-traffic servers first, then the remaining network
  ("Pending - Full Rollout"); users mapped to new edge locations can still receive the previous
  configuration during rollout. Normal estimate is up to **15 minutes**; exceptions take up to
  **60 minutes** (changes to >10 hostnames at once, custom/advanced configurations requiring Akamai
  intervention, or legacy Configuration Manager hostname migrations).

## Rollback — check eligibility as well as time

- **Fast Fallback, when eligible:** available for **60 minutes** after full rollout. Read the
  current activation's `fallbackInfo` (`canFastFallback`, `fallbackVersion`,
  `fastFallbackExpirationTime`) and pass `useFastFallback` on
  `POST /papi/v1/properties/{propertyId}/activations` while eligibility and expiry permit. First
  activations, hostname-set changes, and the 60-minute activation exceptions cannot use Fast Fallback.
- **Unavailable or expired:** activate a known-good previous version and budget the full activation
  time (or prepare an alternative recovery path for a first activation).

## Property change packet

Include the version diff, staging verification evidence, hostname/CP-code blast radius, exact
post-activation check, and verified rollback path (eligible Fast Fallback or known-good previous
version) for the human release owner under `production-change-gate`.

## Cache purge

Give the human release owner the exact URLs, cache tags, or CP code, method, network, expected
origin load, and verification check:

| Choice | Default | Why |
|---|---|---|
| Method | **Invalidate** (default): next request revalidates with origin (`If-Modified-Since`); edge can serve stale content if origin is unreachable when configured | **Delete** removes the object and increases origin load/bandwidth more than invalidate; reserve for compliance/copyright removal where stale serving is unacceptable |
| Scope | Narrowest covering scope: URL → cache tag → CP code (or ARL) | Wide scope revalidates everything under it at once — state expected origin load |
| Network | `staging` to rehearse; `production` (API default) for live traffic | A production purge has no undo; origin refetches the content |

Verify with an [enhanced debug request](./edge-triage.md#cache-status-via-debug-headers): expect a
refresh (`TCP_REFRESH_*`) at a hop that held an invalidated copy, or `TCP_MISS` where deleted.

## Config-as-code paths

- **Terraform:** property provisioning requires rule format ≥ `v2023-01-05`; `cli-terraform`
  exports an existing property to configuration plus an import script.
- **Akamai CLI `property-manager`:** local snippet-based editing and multi-environment pipelines
  (last release v0.7.8; check maintenance before adopting).
- **Akamai Sandbox:** tests a development rule tree locally on the host/port in
  `sandboxServerInfo`; supports iteration but does not replace staging validation.

## Review checklist for a property diff

- **Cache-key (`X-True-Cache-Key`) and TTL changes:** move offload and can stampede origin on
  activation; state expected offload delta.
- **Rule evaluation order:** conflicting behaviors use the **bottom-most match**; complementary
  behaviors accumulate, and a child rule applies only when its parent matches.
- **Debug behaviors:** when rotating Enhanced Debug keys, `disablePragma`, or GRN settings, confirm
  debug access remains available after activation.
