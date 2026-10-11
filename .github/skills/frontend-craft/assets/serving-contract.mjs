// Serving contract for a single-page app. Copy it into the repository and run it against the
// production build behind the production server configuration (not `vite preview`):
//   BASE_URL=http://localhost:8080 node --test serving-contract.mjs
// Optional checks: API_PREFIX=/v1/ (an unknown API path is not the app) and
// RUNTIME_CONFIG_PATH=/config.json (runtime configuration is fresh JSON). Needs no packages.
import assert from "node:assert/strict";
import { test } from "node:test";

const { BASE_URL, API_PREFIX, RUNTIME_CONFIG_PATH } = process.env;
if (!BASE_URL) throw new Error("Set BASE_URL to the served build, e.g. http://localhost:4173");

const missing = `serving-contract-${Date.now().toString(36)}`;

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
  assert.match(page.csp, /\bframe-ancestors\b/, `/ must send a Content-Security-Policy with frame-ancestors, got "${page.csp}"`);
  assert.equal(page.sniff, "nosniff", `/ must send X-Content-Type-Options: nosniff, got "${page.sniff}"`);
});

test("a deep link serves the app and revalidates", async () => {
  const bundle = await bundlePath();
  const page = await get(`/${missing}/deep/link`);
  assert.equal(page.status, 200, "a client route must fall back to index.html");
  assert.ok(isApp(page, bundle), "a client route must serve the app's HTML");
  assert.ok(revalidates(page), `a deep link must send Cache-Control: no-cache, got "${page.cache}"`);
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
