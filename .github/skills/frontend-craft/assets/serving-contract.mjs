// Serving contract for a single-page app. Copy it into the repository and run it against the
// production build behind the production server configuration (not `vite preview`):
//   BASE_URL=http://localhost:8080 node --test serving-contract.mjs
// Optional checks: API_PREFIX=/v1/ (an unknown API path is not the app) and
// RUNTIME_CONFIG_PATH=/config.json (runtime configuration is fresh JSON). Needs no packages.
// FRAME_ANCESTORS_EXPECTED defaults to 'none'; intentional embedding must name its expected
// space-separated sources ('self' and/or explicit HTTP(S) origins).
import assert from "node:assert/strict";
import { test } from "node:test";

const { BASE_URL, API_PREFIX, RUNTIME_CONFIG_PATH, FRAME_ANCESTORS_EXPECTED } = process.env;
if (!BASE_URL) throw new Error("Set BASE_URL to the served build, e.g. http://localhost:4173");

const missing = `serving-contract-${Date.now().toString(36)}`;
const trimAscii = (value) => value.replace(/^[\t\n\f\r ]+|[\t\n\f\r ]+$/g, "");

// A deliberately bounded policy check, not a CSP engine. Reject syntax we cannot compare
// safely; in particular, never union policies or choose a later duplicate directive.
function ancestorSources(value, context) {
  const sources = trimAscii(value).split(/[\t\n\f\r ]+/);
  const normalized = sources.map((source) => {
    const lower = source.toLowerCase();
    if (lower === "'none'" || lower === "'self'") return lower;
    const origin = source.match(/^https?:\/\/([a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]*[a-z0-9])?)*)(?::[0-9]{1,5})?$/i);
    assert.ok(origin, `${context}: unsupported frame-ancestors source "${source}"; use 'none', 'self', or explicit HTTP(S) origins without wildcards or paths`);
    let url;
    try {
      url = new URL(lower);
    } catch {
      assert.fail(`${context}: unsupported frame-ancestors origin "${source}"`);
    }
    assert.equal(url.hostname, origin[1].toLowerCase(), `${context}: unsupported noncanonical frame-ancestors origin "${source}"`);
    assert.ok(!/^[0-9.]+$/.test(url.hostname), `${context}: unsupported IP frame-ancestors origin "${source}"; use a DNS host`);
    return url.origin;
  });
  assert.ok(!normalized.includes("'none'") || normalized.length === 1, `${context}: 'none' must be the only frame-ancestors source`);
  return [...new Set(normalized)].sort();
}

const expectedAncestors = ancestorSources(FRAME_ANCESTORS_EXPECTED ?? "'none'", "FRAME_ANCESTORS_EXPECTED");

function securityHeaders(page, path) {
  assert.ok(page.csp, `${path} must send an enforced Content-Security-Policy with frame-ancestors (report-only is insufficient)`);
  assert.ok(!page.csp.includes(","), `${path}: frame-ancestors in multiple/comma-separated CSP policies is unsupported; verify them separately without merging their sources`);
  const directives = page.csp.split(";").map((part) => trimAscii(part).split(/[\t\n\f\r ]+/));
  const ancestors = directives.filter(([name]) => name.toLowerCase() === "frame-ancestors");
  assert.equal(ancestors.length, 1, `${path}: expected one frame-ancestors directive; missing or duplicate directives are unsupported`);
  const actual = ancestorSources(ancestors[0].slice(1).join(" "), path);
  assert.deepEqual(actual, expectedAncestors, `${path}: frame-ancestors must match FRAME_ANCESTORS_EXPECTED (${expectedAncestors.join(" ")}), got "${page.csp}"`);
  assert.equal(page.sniff, "nosniff", `${path} must send X-Content-Type-Options: nosniff, got "${page.sniff}"`);
}

async function get(path) {
  const response = await fetch(new URL(path, BASE_URL), { redirect: "manual" });
  const header = (name) => (response.headers.get(name) ?? "").toLowerCase();
  return {
    status: response.status,
    type: header("content-type"),
    cache: header("cache-control"),
    csp: response.headers.get("content-security-policy") ?? "",
    sniff: header("x-content-type-options"),
    body: await response.text(),
  };
}

const revalidates = (response) => /\bno-cache\b|\bno-store\b|\bmax-age=0\b/.test(response.cache);

// The app's HTML is recognised by its script bundle, which survives per-response nonces.
async function bundlePath() {
  const index = await get("/");
  const match = index.body.match(/<script[^>]+src="([^"]+\.js)"/i);
  assert.ok(match, "index.html references no script bundle");
  return new URL(match[1], new URL("/", BASE_URL)).pathname;
}

const isApp = (response, bundle) => response.body.includes(bundle);

test("index.html is the app and revalidates", async () => {
  const page = await get("/");
  assert.equal(page.status, 200);
  assert.match(page.type, /text\/html/);
  assert.ok(revalidates(page), `/ must send Cache-Control: no-cache, got "${page.cache}"`);
});

test("index.html refuses framing and content sniffing", async () => {
  const page = await get("/");
  securityHeaders(page, "/");
});

test("a deep link serves the app and revalidates", async () => {
  const bundle = await bundlePath();
  const page = await get(`/${missing}/deep/link`);
  assert.equal(page.status, 200, "a client route must fall back to index.html");
  assert.ok(isApp(page, bundle), "a client route must serve the app's HTML");
  assert.ok(revalidates(page), `a deep link must send Cache-Control: no-cache, got "${page.cache}"`);
  securityHeaders(page, "a deep link");
});

test("the script bundle is served as JavaScript", async () => {
  const bundle = await bundlePath();
  const asset = await get(bundle);
  assert.equal(asset.status, 200, `${bundle} must exist`);
  assert.match(asset.type, /javascript/, `${bundle} has content-type "${asset.type}"`);
});

test("a missing static file is a 404, not the app", async () => {
  const bundle = await bundlePath();
  const directory = bundle.slice(0, bundle.lastIndexOf("/") + 1);
  for (const path of [`${directory}${missing}.js`, `/${missing}.css`, `/${missing}.png`]) {
    const response = await get(path);
    assert.equal(response.status, 404, `${path} returned ${response.status}`);
    assert.ok(!isApp(response, bundle), `${path} returned the app's HTML`);
  }
});

test("an unknown API path is not the app", { skip: !API_PREFIX && "API_PREFIX is not set" }, async () => {
  const bundle = await bundlePath();
  const path = `${API_PREFIX.replace(/\/?$/, "/")}${missing}`;
  const response = await get(path);
  assert.ok(response.status >= 400, `${path} returned ${response.status}`);
  assert.ok(!isApp(response, bundle), `${path} returned the app's HTML`);
});

test("runtime configuration is fresh JSON", { skip: !RUNTIME_CONFIG_PATH && "RUNTIME_CONFIG_PATH is not set" }, async () => {
  const config = await get(RUNTIME_CONFIG_PATH);
  assert.equal(config.status, 200, `${RUNTIME_CONFIG_PATH} returned ${config.status}`);
  assert.match(config.type, /json/, `${RUNTIME_CONFIG_PATH} has content-type "${config.type}"`);
  const value = JSON.parse(config.body);
  assert.ok(value !== null && typeof value === "object" && !Array.isArray(value), "configuration must be a JSON object");
  assert.ok(revalidates(config), `${RUNTIME_CONFIG_PATH} must send Cache-Control: no-cache, got "${config.cache}"`);
});
