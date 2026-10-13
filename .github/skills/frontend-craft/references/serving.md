# Build, configure and serve

Use localhost for development; load the PCF section only when PCF delivery is required. Reuse
equivalent build/hosting facilities. The [serving contract](../assets/serving-contract.mjs) checks
a served production build; it is separate from the app's component runner.

## Contents

- [Localhost](#localhost)
- [Runtime configuration](#runtime-configuration)
- [PCF](#pcf)
- [Security headers and the CSP](#security-headers-and-the-csp)
- [Caching and rollout](#caching-and-rollout)
- [Verify](#verify)

## Localhost

Vite hot-reloads the app and proxies the API prefix to the running service through
`server.proxy` in [vite.config.ts](../assets/vite.config.ts). `API_TARGET` selects the backend
(FastAPI commonly uses 8000, Go 8080). One browser origin keeps cookies and API calls aligned
without CORS. SSE passes through; WebSockets need `ws: true` on their path. When runtime
configuration is used, `public/config.json` identifies the environment as `local`.

`vite preview` is for inspecting the build, not production serving: its SPA fallback fails the
contract's missing-file check. Test the release using its intended server configuration.

## Runtime configuration

When one release is promoted through environments, build once (`vite build`, hashed
`dist/assets/`) and load environment differences from same-origin `config.json` before first
render. The [runtime-config helper](../assets/runtime-config.ts) validates it and names missing
fields in a startup error. Show the environment in the shell/title and destructive confirms,
production most distinctly. Runtime config and `VITE_*` values reach every browser: no secrets;
build-time values must be identical across promoted environments.

## PCF

Assemble a deploy directory in CI containing `dist/` and the selected assets; do not push the
source tree. Use the staticfile buildpack:

| Asset | Contract |
|---|---|
| [Staticfile](../assets/pcf/Staticfile) | `root: dist`, required for `location_include`; `pushstate: enabled`; `includes/*.conf`; HTTPS/HSTS buildpack options |
| [spa.conf](../assets/pcf/nginx/conf/includes/spa.conf) | Included inside `location /`; HTML security/revalidation headers, nested immutable-asset and fresh-config locations, missing assets as uncached `404` |
| [profile.sh](../assets/pcf/profile.sh), saved as `.profile` | Runs before app startup and writes `public/config.json` from manifest/Apps Manager `UI_*` values |
| [manifest.yml](../assets/pcf/manifest.yml) | Buildpack, 64M memory, HTTP health check on `/`, host route and `UI_*` values |

The API remains a separate app on the same host's context-path route, such as
`host.domain/v1`; Cloud Foundry chooses that route first and the API serves its prefix.
`pushstate` alone can return HTML/200 for missing chunks: run the contract on the foundation to
prove the nested asset locations win. The profile/buildpack pairing also needs that runtime-config
proof; if the foundation forbids the startup script, use a public, secret-free API config endpoint.

If staticfile options or rewrite precedence cannot satisfy the contract, use the nginx buildpack
with a complete `nginx.conf`, `{{port}}`, `{{env "NAME"}}`, `buildpack.yml`,
`try_files $uri /index.html` for client routes and `try_files $uri =404` for assets.
Deployment belongs to the human release owner under `production-change-gate`; prepare the
exact push and rollback.

## Security headers and the CSP

Serve HTML with `X-Content-Type-Options: nosniff`,
`Referrer-Policy: strict-origin-when-cross-origin` and this starting policy:

```text
default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'; form-action 'self'
```

HSTS belongs at the TLS edge/buildpack option; do not duplicate it in the include. Framing must
actually be refused: merely having a `frame-ancestors` directive is insufficient.
A production Vite build needs no inline script permission. Kits such as Sonner, Mantine and
Emotion-based Material UI insert styles at runtime; a static server cannot mint their
per-response nonce, hence inline styles in this starting policy. Tighten it when the selected
kits emit stylesheet files and the served app shows no violations. Never loosen script policy to
fix styling.

`build.assetsInlineLimit: 0` keeps small images as files; `data:` covers kit-inlined images.
The profile rejects absolute `UI_API_BASE_URL` values because `connect-src 'self'` assumes a
same-origin API. A separate API origin needs a deliberate CSP/profile adjustment, the API's
CORS/cookie contract and verification of the served result.

To persist the theme before first paint, use a small static boot script, allowed by its exact hash:

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

If the brief chooses a fixed default, substitute it for the OS fallback. Save the exact text
between the tags as `theme-boot.js`, then add its hash to `script-src`:

```sh
node -e 'const s=require("fs").readFileSync("theme-boot.js","utf8");console.log("sha256-"+require("crypto").createHash("sha256").update(s).digest("base64"))'
```

## Caching and rollout

HTML and config revalidate (`no-cache`); existing hashed assets are immutable for a year.
Missing assets return `404` without cache headers. Keep the previous release's chunks during
rollout, or handle `vite:preloadError` with bounded, visible recovery that protects unsaved work;
never reload in a loop.

## Verify

Run against the built app behind its intended server, locally and after each authorized deploy:

```sh
BASE_URL=https://orders-console.apps.example.internal API_PREFIX=/v1/ RUNTIME_CONFIG_PATH=/config.json node --test serving-contract.mjs
```

Enable `API_PREFIX` only for a co-served API and `RUNTIME_CONFIG_PATH` only for runtime
configuration; unset variables skip those checks. Inspect the served app's browser console for
CSP violations and missing styles. Keep a tab open across a rollout and visit a lazy-loaded view;
report unperformed checks as gaps. For required browser telemetry, use mPulse through
`akamai-edge`; trace/correlation headers through `obs-pipeline`.
