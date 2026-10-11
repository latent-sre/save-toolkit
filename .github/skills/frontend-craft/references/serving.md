# Build and serving

Read when packaging or serving a frontend, including a SPA on PCF. Use the selected framework's
production build and the target application's hosting contract. Load `stack-profile` for the
actual platform; frontend library freedom does not settle runtime or deployment decisions.

## Routes, assets, and APIs

For a SPA, support refresh and direct navigation to client routes. Reserve backend routes and
static assets before falling back to index.html: missing JS/CSS, images, and other static files
must return 404 rather than HTML with 200. Include public files outside the bundler's asset prefix.
Co-served /v1/*, /health/live, and /health/ready must retain their own handlers and status codes,
including problem responses for unknown API routes. Adapt these examples to the service's paths.

For server-rendered or statically generated sites, preserve the framework's route, asset, and
not-found behavior instead of imposing a blanket SPA fallback. Keep browser-only dependencies and
provider initialization compatible with the selected rendering mode.

## SPA serving on PCF

Serve the production output through the supported Staticfile/NGINX buildpack or the API application.
Staticfile's pushstate setting rewrites missing paths and does not by itself protect API/asset
boundaries. Use supported custom configuration, an explicit NGINX configuration, or the API router
to reserve those paths. Select the actual build output directory as the static root.

When a Python or Go application also serves the frontend, test the built UI mounted in that
application. A test run without the build directory can miss conditional fallback wiring. Verify
deep-link refreshes, missing assets, unknown API routes, and health endpoints together.

## Caching and recovery

Revalidate HTML; content-hashed immutable assets can use long cache lifetimes. Keep prior chunks
available during rollout or provide bounded, visible recovery for missing imports that protects
unsaved work. Avoid reload loops. Prefer the chosen framework's supported load-error mechanism.

Verify production assets, content types, status codes, cache headers, and framework-specific serving
behavior. Where a local or staging rollout check is in scope, keep a tab open across versions and
navigate to a lazy-loaded view. Report unperformed checks as gaps. Deployment execution remains
with the human release owner.

Use the project's browser error and performance telemetry. Carry supported trace/correlation
context to the API without recording sensitive input; consult `obs-pipeline` and `akamai-edge`
when the task involves the team's observability or mPulse setup.
