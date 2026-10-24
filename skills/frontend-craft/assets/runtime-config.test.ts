// Contract test for runtime-config.ts. Run: node --test runtime-config.test.ts (Node 22.18+ or 24+, no packages).
import assert from "node:assert/strict";
import { test } from "node:test";
import { environmentTone, isUrlLike, loadRuntimeConfig, RuntimeConfigError, validateConfig } from "./runtime-config.ts";

const schema = {
  apiBaseUrl: "url",
  environment: "string",
  logSearchUrlTemplate: "url?",
  traceUrlTemplate: "url?",
  readOnly: "boolean?",
  pollIntervalSeconds: "number?",
} as const;

const serve = (body: unknown, status = 200) => async (input: string | URL | Request, init?: RequestInit) => {
  assert.equal(String(input), "/config.json");
  assert.equal(init?.cache, "no-store");
  return new Response(typeof body === "string" ? body : JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
};

test("a valid document loads, typed, with optional fields present or absent", async () => {
  const config = await loadRuntimeConfig(schema, {
    fetch: serve({ apiBaseUrl: "/v1", environment: "staging", logSearchUrlTemplate: "https://splunk.example.internal/search?q={request_id}", readOnly: false }),
  });
  assert.equal(config.apiBaseUrl, "/v1");
  assert.equal(config.environment, "staging");
  assert.equal(config.logSearchUrlTemplate, "https://splunk.example.internal/search?q={request_id}");
  assert.equal(config.readOnly, false);
  assert.equal(config.pollIntervalSeconds, undefined);
  assert.ok(Object.isFrozen(config));
});

test("every missing or malformed field is named in one error", () => {
  assert.throws(
    () => validateConfig(schema, { apiBaseUrl: "v1", readOnly: "no", pollIntervalSeconds: "5" }),
    (error: unknown) => {
      assert.ok(error instanceof RuntimeConfigError);
      assert.deepEqual(error.problems, [
        "apiBaseUrl must be an absolute http(s) URL or a path starting with /",
        "environment is missing (expected string)",
        "readOnly must be true or false",
        "pollIntervalSeconds must be a finite number",
      ]);
      return true;
    },
  );
});

test("a key the schema does not name is a startup error, so a misspelled optional flag cannot vanish", () => {
  assert.throws(
    () => validateConfig(schema, { apiBaseUrl: "https://api.example.internal", environment: "prod", readonly: true }),
    (error: unknown) => error instanceof RuntimeConfigError && error.problems.join() === "readonly is not a known setting (check the spelling)",
  );
  for (const inherited of ["constructor", "toString", "__proto__"]) {
    const document = JSON.parse(`{"apiBaseUrl": "/v1", "environment": "prod", ${JSON.stringify(inherited)}: 1}`);
    assert.throws(() => validateConfig(schema, document), new RegExp(`${inherited.replace("_", "\\_")} is not a known setting`));
  }
});

test("url fields accept http(s) URLs and root-relative paths only", () => {
  assert.equal(isUrlLike("/v1"), true);
  assert.equal(isUrlLike("https://api.example.internal/v1"), true);
  assert.equal(isUrlLike("//evil.example/v1"), false);
  assert.equal(isUrlLike("/\\\\evil.example/v1"), false);
  assert.equal(isUrlLike("/\\evil.example/v1"), false);
  assert.equal(isUrlLike("/v1/orders?limit=50#top"), true);
  assert.equal(isUrlLike("javascript:alert(1)"), false);
  assert.equal(isUrlLike("v1"), false);
});

test("a non-200 answer, a non-JSON body and a non-object document are startup errors", async () => {
  await assert.rejects(loadRuntimeConfig(schema, { fetch: serve("", 404) }), /answered HTTP 404/);
  await assert.rejects(loadRuntimeConfig(schema, { fetch: serve("<html>") }), /not valid JSON/);
  await assert.rejects(loadRuntimeConfig(schema, { fetch: serve([1, 2]) }), /not a JSON object/);
});

test("a network failure is reported as a startup error, not a thrown TypeError", async () => {
  const fetch = async () => { throw new TypeError("Failed to fetch"); };
  await assert.rejects(loadRuntimeConfig(schema, { fetch }), (error: unknown) => error instanceof RuntimeConfigError && /could not be fetched: Failed to fetch/.test(error.message));
});

test("environment names classify for the badge, production most distinctly", () => {
  assert.equal(environmentTone("production"), "production");
  assert.equal(environmentTone("PROD-EU"), "production");
  assert.equal(environmentTone("live"), "production");
  assert.equal(environmentTone("staging"), "staging");
  assert.equal(environmentTone("uat2"), "staging");
  assert.equal(environmentTone("dev"), "development");
  assert.equal(environmentTone("local"), "development");
  assert.equal(environmentTone("dr-site"), "other");
});

test("authority-form paths cannot collide with the validator's dummy origin", () => {
  for (const value of ["//same-origin.invalid/v1", "///same-origin.invalid/v1", "/\t/same-origin.invalid/v1", "/\n/same-origin.invalid/v1", "/\r/same-origin.invalid/v1"]) {
    assert.equal(isUrlLike(value), false, JSON.stringify(value));
    assert.throws(() => validateConfig(schema, { apiBaseUrl: value, environment: "prod" }), RuntimeConfigError);
  }
});
