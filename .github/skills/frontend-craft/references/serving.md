# Production build, serving, and runtime configuration

Run served-build checks against a production build behind the real server/nginx configuration (`vite preview`
does not enforce missing-file 404 or header rules).

## Localhost & runtime configuration

- Proxy the backend API in Vite (`server.proxy` with `API_TARGET` and `ws: true`) to keep cookies and
  requests same-origin; discover the actual backend port.
- Build once (`vite build`) and fetch same-origin `/config.json` with `cache: "no-store"` before first
  render (`public/config.json` in dev). Validate against a strict schema (reject unknown keys and
  cross-origin `//` or non-`http(s)` URLs), show an explicit startup error on failure rather than a blank
  screen, display the environment in the shell and destructive confirms, and never place secrets in
  `config.json` or `VITE_*`.

## Cloud Foundry staticfile delivery (when the repository deploys on PCF)

When deploying a SPA with `staticfile_buildpack`, ship a CI-assembled bundle containing `dist/` and these files (never push `src/` or `node_modules`):

| File | Contract |
|---|---|
| `Staticfile` | `root: dist` (required so `location_include` paths resolve); `pushstate: enabled`; `location_include: includes/*.conf`; `force_https: true`; `http_strict_transport_security: true`. |
| `nginx/conf/includes/spa.conf` | Inside `location /`: HTML sets `Cache-Control: no-cache`, CSP, `X-Content-Type-Options: nosniff`, and `Referrer-Policy` with `always` (buildpack adds HSTS here). Because nginx nested `location` blocks with `add_header` **do not inherit parent headers**, repeat security headers and HSTS inside `location ^~ /assets/` (`max-age=31536000, immutable`, `try_files $uri =404`), `location = /config.json` (`no-cache`), and a file-extension regex location with `try_files $uri =404`. |
| `.profile` | Atomically generates `$HOME/public/config.json` from `UI_*` env vars before nginx starts; fails closed on missing required vars, control characters, or non-root-relative API paths. |
| `manifest.yml` | `staticfile_buildpack`, memory limit, HTTP health check `/`, host route, and `UI_*` vars. |

Co-serve the API on a context-path route of the same host (e.g. `host/v1`). Use `nginx_buildpack` with
a full `nginx.conf` if `staticfile` rewrite rules cannot satisfy the contract.

## Security headers, caching, and verification

- Serve HTML with `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, and CSP:
  `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; object-src 'none'; form-action 'self'`
- Set `build.assetsInlineLimit: 0`; list `X-Request-ID` and `Retry-After` in `Access-Control-Expose-Headers`.
  If using an inline pre-paint theme script (`localStorage.getItem("theme")`), add its `sha256-...` hash to `script-src`.
- HTML and `/config.json` must send an unqualified `no-cache` or `no-store` directive (`max-age=0` alone
  permits shared-cache stale reuse). Verify on the live served build that: `/` and deep client routes
  return `200 text/html` with `no-cache` and `frame-ancestors 'none'`; the hashed JS bundle serves as
  JavaScript; missing `.js`/`.css`/`.png`/`.woff2` paths return uncached `404` (never SPA HTML); unknown
  API paths return `>=400` non-HTML; and `/config.json` returns fresh JSON. Handle `vite:preloadError`
  without reload loops or losing unsaved input.
