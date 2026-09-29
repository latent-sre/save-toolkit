# Frontend stack selection and PCF serving

Read for **greenfield** stack selection or serving a SPA on PCF. An existing repository's stack
always wins; for hosting-only changes, read [Build & serve on PCF](#build--serve-on-pcf).

The universal frontend rules live in `../SKILL.md`. On any conflict, SKILL.md wins.

## Stack

An existing repo's stack always wins — match it. Greenfield uses a **React + TypeScript SPA on Vite**.
Add the dependencies below when the feature needs their capabilities. Keep UI behavior separate
from styling, with one reset and one token system.

**Paint — one reset, one token system:**
- **Tailwind** when a utility styling layer is needed.
- **shadcn/ui pattern on Radix (or Base UI) primitives** for interactive widgets needing accessible behavior you style yourself; use semantic HTML for simpler controls.
- **lucide-react** when icons help the workflow; **Framer Motion** only when CSS transitions aren't enough (CSS is right for hovers, fades, modals).
- Optional, same Tailwind world: **HeroUI v3** as a styled layer only when it can share the existing reset and token system; **Aceternity / Magic UI** as a sparing garnish for hero / login / empty-state moments — named in the review packet.

**Logic — zero CSS, decoupled from the paint:**
- **TanStack Query** when managing server state; **TanStack Router** when the app needs routes (typed routes, nested layouts, route-based code splitting, URL search-param state); **TanStack Table** when it needs data-grid behavior. Add only the parts in use.
- **@mantine/hooks** when shared utility logic is needed (disclosure, debounce, local storage, hotkeys, click-outside, media query, element size); **@mantine/form** when form state needs a library. Both ship no CSS and need no provider.
- Accessible *widget* behavior (focus trap, ARIA, roving tabindex) comes from **Radix / Base UI**, not from Mantine hooks.

The Mantine rule lives in `../SKILL.md`'s decisions table.

If the user explicitly asks for plain HTML or a static page, comply. Record a different greenfield
framework choice in the review packet; omitting an unused optional dependency needs no exception.

## Build & serve on PCF

Build hashed assets with the repository's production build (`vite build` for greenfield).
Serve through the `staticfile`/`nginx` buildpack or the API app. Fall back to `index.html` for
client routes, including deep links, only after reserving asset paths and backend routes:
missing JS/CSS, images and other static files must return 404, never HTML with 200. Include public
files outside the bundler's asset prefix. Co-served `/v1/*`, `/healthz` and `/readyz` retain their
backend handlers and status codes, including problem responses for unknown API routes.

Staticfile's `pushstate: enabled` rewrites **all missing paths**; it alone does not enforce those
boundaries. Use the buildpack's supported custom configuration, an explicit NGINX configuration,
or the API's router to reserve them. `root: dist` selects the built directory when pushing the
whole project. [sourced: [Staticfile options](https://docs.cloudfoundry.org/buildpacks/staticfile/index.html)
and [rewrite implementation](https://github.com/cloudfoundry/staticfile-buildpack/blob/22b502fd325f5725e0a1d5972f9b59ca9ec6d8c2/src/staticfile/finalize/data.go#L123); reviewed 2026-09-29]

Revalidate HTML (`Cache-Control: no-cache`); immutable, content-hashed assets can use long cache
lifetimes. Keep prior chunks available during rollout or use bounded, user-visible recovery for
missing imports that protects unsaved work; avoid reload loops. Prefer an existing framework's
solution; Vite exposes `vite:preloadError`. [sourced: [Vite deployment failures](https://vite.dev/guide/build.html#load-error-handling)
and [HTTP caching](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Caching#cache_busting); reviewed 2026-09-29]

Verify the production build, deep-link refreshes, asset content types/statuses and cache headers.
When co-serving, use the project's contract tests to check API 404s and healthy health endpoints
with the built UI mounted; testing without `dist/` misses conditional fallback wiring. Compatible
FastAPI services can reuse backend-craft's `test_unknown_path_is_a_problem`.
In a local or staging rollout check, keep a tab open across versions and navigate to a lazy-loaded
view. Deployment execution belongs to the human release owner; report unperformed checks as gaps.
Capture browser error, latency, and navigation telemetry: real-user monitoring through mPulse
(load `akamai-edge`), trace and correlation headers through `obs-pipeline`.
