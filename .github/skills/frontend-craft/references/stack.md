# Frontend stack selection and PCF serving

Read when choosing or changing frontend tools, or serving a SPA on PCF. For hosting-only work,
read [Build & serve on PCF](#build--serve-on-pcf). The parent skill owns quality and verification.

## Select for the product

Honor the user's chosen stack; preserve an existing one unless changing it is in scope. Plain HTML
and any suitable framework are available. Explain consequential tradeoffs; use the invoking lane's
design process for unresolved architecture decisions.

| Decision | What to consider |
|---|---|
| Rendering and framework | Compare static generation, server and client rendering against content/interactivity, indexing/SEO, initial render, navigation, offline needs and hosting. Serving static files does not imply a server runtime. |
| Components and styling | Native HTML, styled kits (including Mantine), copied components, headless primitives and any CSS approach can fit. Evaluate version compatibility, accessible behavior, customization and maintenance. When combining systems, account for reset/layer ordering, providers and theme integration. |
| State, forms and requests | Use the framework's facilities, a shared store, a form library or a query cache according to ownership, lifetime, validation and synchronization needs. Preserve the API contract and avoid duplicate competing owners for the same state. |
| Charts and tables | Match data shape, volume, update rate, interactions, accessibility and licensing. Native tables, custom visualization and libraries including Mantine charts are available choices; measure rendering and fetching costs separately. |
| Build and dependencies | Follow the existing package manager and lockfile; establish them for a new project. Check runtime, peer dependencies, browser support, maintenance, licenses, asset delivery and bundle cost. |

Verify compatibility against official documentation and upstream evidence for the selected versions.
Examples are not requirements. Add capabilities the task needs without scaffolding an unused stack.

## Build & serve on PCF

This section applies to a client-rendered SPA; server-rendered applications need their framework's
runtime and routing configuration. Build assets with the repository's production build.
Serve through the `staticfile`/`nginx` buildpack or the API app. Fall back to `index.html` for
client routes, including deep links, only after reserving asset paths and backend routes:
missing JS/CSS, images and other static files must return 404, never HTML with 200. Include public
files outside the bundler's asset prefix. Co-served `/v1/*`, `/health/live` and `/health/ready` retain their
backend handlers and status codes, including problem responses for unknown API routes.

Staticfile's `pushstate: enabled` rewrites **all missing paths**; it alone does not enforce those
boundaries. Use the buildpack's supported custom configuration, an explicit NGINX configuration,
or the API's router to reserve them. `root: dist` selects the built directory when pushing the
whole project when `dist/` is the configured build output.

Revalidate HTML (`Cache-Control: no-cache`); immutable, content-hashed assets can use long cache
lifetimes. Keep prior chunks available during rollout or use bounded, user-visible recovery for
missing imports that protects unsaved work; avoid reload loops. Prefer an existing framework's
solution; Vite exposes `vite:preloadError` when that is the selected build tool.

Verify the production build, deep-link refreshes, asset content types/statuses and cache headers.
When co-serving, use the project's contract tests to check API 404s and healthy health endpoints
with the built UI mounted; testing without the build output misses conditional fallback wiring. Compatible
FastAPI services can reuse backend-craft's `test_unknown_path_is_a_problem`.
In a local or staging rollout check, keep a tab open across versions and navigate to a lazy-loaded
view. Deployment execution belongs to the human release owner; report unperformed checks as gaps.
Use the project's browser error, latency and navigation telemetry; where it uses mPulse, load
`akamai-edge`, and for trace/correlation headers load `obs-pipeline`. Keep credentials and sensitive
content out of collected URLs and events.
