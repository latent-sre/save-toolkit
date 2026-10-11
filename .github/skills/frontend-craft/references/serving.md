# Build, configure and serve

Read when changing the build, runtime configuration, local development against the API, or how the
UI is served. The repository's existing build and hosting win; this file owns the contract they
meet, and [the serving contract](../assets/serving-contract.mjs) is its acceptance test: read it,
write it beside the build configuration with the editor tools, and run it against every served
build.

## Localhost

`vite` serves the app with hot reload and proxies the API prefix to the service on localhost
(`server.proxy` in the starting [vite.config.ts](../assets/vite.config.ts); FastAPI's default port
is 8000 and a Go service's often 8080; `API_TARGET` overrides). The browser then sees one origin,
cookies flow and no CORS is needed, the same shape as production. SSE streams pass through the
proxy; WebSockets need `ws: true` on their path. `public/config.json` holds the local runtime
configuration with `"environment": "local"`. `vite preview` serves the production build for a look,
but it is not a production server and fails the contract's missing-file check by design.

## One build, every environment

Build once per release (`vite build`, hashed assets under `dist/assets/`) and promote the same
files through every environment. Everything that differs per environment is runtime configuration:
`config.json` beside `index.html`, fetched and validated before the app renders through the
starting [runtime-config.ts](../assets/runtime-config.ts); a missing field is a startup error
naming it, never a blank page. It reaches every browser, so it never holds a secret. Show the
environment's name from it in the shell and in `document.title`, production most distinctly and in
every destructive confirm.

## Serve on PCF

The UI is its own app on the **staticfile buildpack**, pushed from a deploy directory that CI
assembles — `dist/`, `Staticfile`, `nginx/conf/includes/spa.conf`, `.profile`, `manifest.yml` —
never from the source tree. The starting files:

- [Staticfile](../assets/pcf/Staticfile): `root: dist`, which the buildpack requires for
  `location_include` to apply; `pushstate: enabled` for client routes; `location_include:
  includes/*.conf`; `force_https`; the HSTS options (`http_strict_transport_security` and its
  `_include_subdomains` variant), which are the only source of that header.
- [spa.conf](../assets/pcf/nginx/conf/includes/spa.conf): included inside nginx's `location /`,
  it sets the HTML's headers — `Cache-Control: no-cache`, the CSP, `nosniff`, `Referrer-Policy`,
  never HSTS, which the buildpack adds in the same location and a repeat would send twice — and
  nests locations for `/assets/` (immutable when the file exists; a missing file is a `404` with
  no cache header) and `/config.json` (always fresh). It exists because `pushstate` on its own rewrites every missing path to
  `index.html`, which would answer a broken deploy's missing chunk with HTML and a `200`. Whether
  the nested locations take precedence over that rewrite on the foundation's nginx is exactly what
  the contract's missing-file check proves; if it fails there, move to the nginx buildpack below.
- [profile.sh](../assets/pcf/profile.sh), saved as `.profile` at the deploy directory's root:
  Cloud Foundry runs it in the container before the app starts, and it writes `public/config.json`
  from the `UI_*` environment variables the manifest or Apps Manager set. The buildpack's own
  documentation does not describe this pairing, so the contract's runtime-config check is the proof
  on the foundation. Where a foundation forbids it, the API serves the UI's configuration from a
  public, secret-free endpoint instead.
- [manifest.yml](../assets/pcf/manifest.yml): the buildpack by name, 64M of memory (nginx needs
  about 20 MB to serve static files), an `http` health check on `/`, the host route, the `UI_*`
  values.

The API is a separate app mapped on the same host under its context path (`host.domain/v1`), so
the browser sees one origin: Cloud Foundry matches the path route first, and the API serves under
that prefix. Deployment belongs to the human release owner under `production-change-gate`; prepare
the exact push and its rollback.

When the buildpack's options are not enough — a second include, a rewrite, a custom error page —
move to the **nginx buildpack** with a complete `nginx.conf` (`{{port}}`, `{{env "NAME"}}`,
`try_files $uri /index.html` for client routes and `try_files $uri =404` under `/assets/`) and a
`buildpack.yml`; the serving contract stays the acceptance test.

## Security headers and the CSP

`index.html` is served with `Content-Security-Policy: default-src 'self'; script-src 'self';
style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self';
frame-ancestors 'none'; base-uri 'self'; object-src 'none'; form-action 'self'`, plus
`X-Content-Type-Options: nosniff` and `Referrer-Policy: strict-origin-when-cross-origin`; HSTS
belongs at the TLS edge and in the buildpack option, never in the include. A production Vite
build emits no inline scripts, so `script-src 'self'` holds and `'unsafe-inline'` for scripts is
never the answer. Styles are different: sonner's toaster, Mantine's provider and Emotion-based
kits such as Material UI insert `<style>` elements at runtime, a static server cannot mint the
per-response nonce they would need, and under `style-src 'self'` those styles are silently
dropped, so the shipped policy allows inline styles. Drop `'unsafe-inline'` only when every kit
in the app ships stylesheet files (Tailwind-based kits do) and the served build logs no CSP
violation. `build.assetsInlineLimit: 0` keeps small images as files, so `data:` matters only when
a kit inlines one. `connect-src 'self'` matches the same-origin API, and the profile script
refuses an absolute `UI_API_BASE_URL` for that reason; an API on another origin needs that origin
added to `connect-src`, the profile's check relaxed, and the contract run against the result. A
console whose actions run in one click never renders inside another site's frame.

The one inline script an app may want is the theme boot, which applies the saved light or dark
choice before first paint. Keep it tiny and static, and allow it by hash:

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

Hash the exact text between the tags and add the `'sha256-…'` value to `script-src` in the
include file:

```sh
node -e 'const s=require("fs").readFileSync("theme-boot.js","utf8");console.log("sha256-"+require("crypto").createHash("sha256").update(s).digest("base64"))'
```

## Caching and rollout

HTML and `config.json` revalidate (`no-cache`); hashed assets are immutable for a year, and a
missing one answers `404` with no cache header, so a chunk requested mid-rollout is retried
rather than pinned as missing (the contract checks this). Keep the
previous release's chunks available during a rollout, or handle Vite's `vite:preloadError` with a
bounded, user-visible recovery that protects unsaved work; never a reload loop.

## Verify

Run the contract against the production build behind the production server configuration, locally
and against each environment after a deploy:

```sh
BASE_URL=https://orders-console.apps.example.internal API_PREFIX=/v1/ RUNTIME_CONFIG_PATH=/config.json node --test serving-contract.mjs
```

Set `API_PREFIX` when the app co-serves an API and `RUNTIME_CONFIG_PATH` when it loads runtime
configuration; each unset variable skips its check. Then open the served build with the browser
console showing: a CSP violation names the directive and the blocked source, and a kit whose
styles never applied is a defect the contract cannot see. In a rollout check, keep a tab open
across versions and navigate to a lazy-loaded view. Report unperformed checks as gaps. Browser error,
latency and navigation telemetry: real-user monitoring through mPulse (load `akamai-edge`), trace
and correlation headers through `obs-pipeline`.
