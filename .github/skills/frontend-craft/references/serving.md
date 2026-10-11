# Build, configure and serve

Read when changing the build, runtime configuration, or how the UI is served. The repository's
existing build and hosting win; this file owns the contract they must meet. Start from
[the serving contract](../assets/serving-contract.mjs): read it and write it into the repository
beside the build configuration with the editor tools, never a shell copy from the skill's folder. It is the acceptance test for everything below.

## One build, every environment

Build once per release and promote the same files through every environment. Serve
environment-specific values as same-origin runtime configuration — a `config.json` beside
`index.html`, written at deploy time or served by the backend — and fetch it before the app renders.
Validate the fields the app needs and show a startup error naming any missing field rather than a
blank page. Serve it with `Cache-Control: no-cache`. It reaches every browser, so it never holds
secrets. Outside production, show the environment's name in the app shell.

## Serve a single-page app

Build hashed assets with the repository's production build (`vite build` for a Vite app). Serve
through the platform's static server — on PCF the `staticfile` or `nginx` buildpack — or the API
app. Fall back to `index.html` for client routes, including deep links, only after reserving asset
paths and backend routes: missing JS/CSS, images and other static files must return 404, never
HTML with 200. Include public files outside the bundler's asset prefix. Co-served `/v1/*`,
`/health/live` and `/health/ready` retain their backend handlers and status codes, including
problem responses for unknown API routes.

Staticfile's `pushstate: enabled` rewrites **all missing paths**
([implementation](https://github.com/cloudfoundry/staticfile-buildpack/blob/22b502fd325f5725e0a1d5972f9b59ca9ec6d8c2/src/staticfile/finalize/data.go#L123)),
so it alone does not enforce those boundaries. Use the buildpack's supported custom configuration
([Staticfile options](https://docs.cloudfoundry.org/buildpacks/staticfile/index.html)), an explicit
NGINX configuration, or the API's router to reserve them. `root: dist` selects the built directory
when pushing the whole project.

Revalidate HTML (`Cache-Control: no-cache`); immutable, content-hashed assets can use long cache
lifetimes. Keep prior chunks available during rollout or use bounded, user-visible recovery for
missing imports that protects unsaved work; avoid reload loops. Prefer an existing framework's
solution; Vite exposes [`vite:preloadError`](https://vite.dev/guide/build.html#load-error-handling).

A platform other than PCF must meet the same contract. The team's next runtime is not decided:
load `stack-profile` before choosing one, and `gcp-ops` for work on GCP.

## Verify

Run the copied contract against the production build behind the production server configuration
(the NGINX or buildpack configuration, or the API app) and against each deployed environment; it
needs Node and no packages. `vite preview` is not a production server: it answers some missing
assets with `index.html`, so the contract fails there by design.

```sh
BASE_URL=http://localhost:8080 API_PREFIX=/v1/ RUNTIME_CONFIG_PATH=/config.json node --test serving-contract.mjs
```

Set `API_PREFIX` when the app co-serves an API and `RUNTIME_CONFIG_PATH` when it loads runtime
configuration; each unset variable skips its check. When co-serving, also run the project's
contract tests with the built UI mounted — testing without `dist/` misses conditional fallback
wiring; compatible FastAPI services can reuse backend-craft's `test_unknown_path_is_a_problem`.
In a local or staging rollout check, keep a tab open across versions and navigate to a lazy-loaded
view. Deployment execution belongs to the human release owner; report unperformed checks as gaps.
Capture browser error, latency, and navigation telemetry: real-user monitoring through mPulse
(load `akamai-edge`), trace and correlation headers through `obs-pipeline`.
