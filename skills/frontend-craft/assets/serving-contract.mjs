// serving-contract.mjs — the acceptance test for how a single-page app is served.
// Run it against the production build behind the production server configuration (the PCF
// buildpack or nginx config, or the API app that co-serves the UI), locally and in each environment:
//   BASE_URL=http://localhost:8080 node --test serving-contract.mjs
// Optional checks: API_PREFIX=/v1/ (an unknown API path must not be the app) and
// RUNTIME_CONFIG_PATH=/config.json (runtime configuration is fresh JSON). Each unset variable skips
// its check. `vite preview` is not a production server and fails the missing-file check by design.
// Needs Node 22+ and no packages.
import assert from "node:assert/strict";
import { test } from "node:test";

const { BASE_URL, API_PREFIX, RUNTIME_CONFIG_PATH } = process.env;
if (!BASE_URL) throw new Error("Set BASE_URL to the served build, e.g. BASE_URL=http://localhost:8080");

const nonce = `serving-contract-${Date.now().toString(36)}`;

async function get(path) {
  const response = await fetch(new URL(path, BASE_URL), { redirect: "manual" });
  const header = (name) => (response.headers.get(name) ?? "").toLowerCase();
  return {
    status: response.status,
    type: header("content-type"),
    cache: header("cache-control"),
    csp: header("content-security-policy"),
    sniff: header("x-content-type-options"),
    body: await response.text(),
  };
}

const revalidates = (r) => /\bno-cache\b|\bno-store\b|\bmax-age=0\b/.test(r.cache);

// The app's HTML is recognised by its script bundle, which survives per-response nonces and hashes.
let bundle;
async function bundlePath() {
  if (bundle) return bundle;
  const index = await get("/");
  const match = index.body.match(/<script[^>]+src="([^"]+\.js)"/i);
  assert.ok(match, "index.html references no script bundle; is BASE_URL the built app?");
  bundle = new URL(match[1], new URL("/", BASE_URL)).pathname;
  return bundle;
}
const isApp = (r, b) => r.body.includes(b);

test("index.html is the app and revalidates", async () => {
  const page = await get("/");
  assert.equal(page.status, 200);
  assert.match(page.type, /text\/html/);
  assert.ok(revalidates(page), `/ must send Cache-Control: no-cache, got "${page.cache}"`);
});

test("index.html refuses framing and content sniffing", async () => {
  const page = await get("/");
  assert.match(page.csp, /\bframe-ancestors\b/, `/ must send a Content-Security-Policy with frame-ancestors, got "${page.csp}"`);
  assert.equal(page.sniff, "nosniff", `/ must send X-Content-Type-Options: nosniff, got "${page.sniff}"`);
});

test("a deep link serves the app and revalidates", async () => {
  const b = await bundlePath();
  const page = await get(`/${nonce}/orders/42`);
  assert.equal(page.status, 200, "a client route must fall back to index.html");
  assert.ok(isApp(page, b), "a client route must serve the app's HTML");
  assert.ok(revalidates(page), `a deep link must send Cache-Control: no-cache, got "${page.cache}"`);
});

test("the script bundle is served as JavaScript", async () => {
  const b = await bundlePath();
  const script = await get(b);
  assert.equal(script.status, 200);
  assert.match(script.type, /javascript/, `${b} must be served as JavaScript, got "${script.type}"`);
});

test("a missing static file is a 404, not the app", async () => {
  const b = await bundlePath();
  const dir = b.slice(0, b.lastIndexOf("/") + 1);
  // A hashed chunk under the bundle directory, and file-like paths at the root (a stylesheet, an
  // image, a font, a manifest): a stale or mistyped asset URL must never come back as HTML 200.
  for (const path of [`${dir}${nonce}.js`, `/${nonce}.css`, `/${nonce}.png`, `/${nonce}.woff2`, `/${nonce}.webmanifest`]) {
    const missing = await get(path);
    assert.equal(missing.status, 404, `${path} must be a 404; HTML with 200 hides a broken deploy`);
    assert.ok(!isApp(missing, b), `${path} must not be answered with the app's HTML`);
  }
});

const apiCheck = API_PREFIX ? test : test.skip;
apiCheck("an unknown API path is not the app", async () => {
  const b = await bundlePath();
  const prefix = API_PREFIX.endsWith("/") ? API_PREFIX : `${API_PREFIX}/`;
  const unknown = await get(`${prefix}${nonce}`);
  assert.ok(!isApp(unknown, b), `${prefix}${nonce} must reach the API, not the app's HTML`);
  assert.doesNotMatch(unknown.type, /text\/html/, `an unknown API path must not answer HTML, got "${unknown.type}"`);
  assert.ok(unknown.status >= 400, `an unknown API path must be an error status, got ${unknown.status}: a 200 here is a catch-all masking typos`);
});

const configCheck = RUNTIME_CONFIG_PATH ? test : test.skip;
configCheck("runtime configuration is fresh JSON", async () => {
  const config = await get(RUNTIME_CONFIG_PATH);
  assert.equal(config.status, 200);
  assert.match(config.type, /application\/json/, `${RUNTIME_CONFIG_PATH} must be application/json, got "${config.type}"`);
  assert.ok(revalidates(config), `${RUNTIME_CONFIG_PATH} must send Cache-Control: no-cache, got "${config.cache}"`);
  let parsed;
  assert.doesNotThrow(() => { parsed = JSON.parse(config.body); }, `${RUNTIME_CONFIG_PATH} must parse as JSON`);
  assert.ok(parsed !== null && typeof parsed === "object" && !Array.isArray(parsed), `${RUNTIME_CONFIG_PATH} must be a JSON object; the app refuses anything else at startup`);
});
