# Build, configure and serve

Use PCF guidance only for PCF delivery. Run the [serving contract](../assets/serving-contract.mjs)
against a served production build; `vite preview` fails its missing-file check.

## Localhost and runtime configuration

Proxy the actual API through Vite `server.proxy` (`API_TARGET`, `ws: true` for WebSockets) to
keep cookies/calls on one origin; discover its port rather than assuming a framework default.

When promoting one build (`vite build`, hashed `dist/assets/`) across environments, load
same-origin `/config.json` before first render with [runtime-config.ts](../assets/runtime-config.ts)
(`public/config.json` in dev). Render startup errors and show the environment in the shell and
destructive confirms. Never put secrets in `config.json` or `VITE_*`.

## PCF

Assemble a CI deploy directory with `dist/` and these files (never push the source tree):

| File | Contract |
|---|---|
| `Staticfile` | `root: dist` (without it `nginx/conf` moves into `public/` and never loads); `pushstate: enabled`; `location_include: includes/*.conf`; `force_https: true` and `http_strict_transport_security` |
| `nginx/conf/includes/spa.conf` | Inside `location /`: HTML gets `Cache-Control: no-cache`, CSP, `nosniff` and referrer policy with `always` (no HSTS here; the buildpack adds it). Repeat headers in nested locations: `location ^~ /assets/` (`max-age=31536000, immutable`, `try_files $uri =404`), `location = /config.json` (`no-cache`), and a regex location for file extensions returning uncached `404` |
| `.profile` | Writes `$HOME/public/config.json` atomically from `UI_*` env vars before nginx starts; fails on missing required values, control characters, or non-root-relative API paths |
| `manifest.yml` | `staticfile_buildpack`, workload-appropriate memory, HTTP health check on `/`, host route and `UI_*` values |

Serve the API on a context-path route of the same host (e.g. `host.domain/v1`). If `staticfile`
rewrite precedence cannot satisfy the contract, use `nginx_buildpack` with a full `nginx.conf`
(`try_files $uri /index.html` for routes, `try_files $uri =404` for assets).

## Security headers and the CSP

Serve HTML with `X-Content-Type-Options: nosniff`,
`Referrer-Policy: strict-origin-when-cross-origin` and:

```text
default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'; form-action 'self'
```

Set `build.assetsInlineLimit: 0` so small assets emit files; tighten `style-src` when kits emit
stylesheets. Never loosen `script-src` for styling. Separate API origins require explicit
`connect-src`, profile and CORS updates.

To persist theme before first paint, include this inline script and add its `sha256-...` hash to
`script-src`:

```html
<script>
  (function () {
    var saved = null;
    try { saved = localStorage.getItem("theme"); } catch (e) {}
    var dark = saved ? saved === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.dataset.theme = dark ? "dark" : "light";
  })();
</script>
```

## Caching, rollout and verification

HTML and `/config.json` revalidate (unqualified `no-cache`) or prevent storage (`no-store`);
`max-age=0` alone is insufficient because shared-cache and stale-reuse directives can override freshness.
Hashed assets cache `immutable` for a year;
missing assets return uncached `404`. Retain prior chunks during rollout or handle
`vite:preloadError` with bounded recovery that preserves unsaved input (never reload in a loop).

Verify the served build locally and after deploy:

```sh
BASE_URL=https://orders-console.apps.example.internal API_PREFIX=/v1/ RUNTIME_CONFIG_PATH=/config.json node --test serving-contract.mjs
```

Omit `API_PREFIX` or `RUNTIME_CONFIG_PATH` when not used.
