// Contract test for idempotent-write.ts. Run: node --test idempotent-write.test.ts (Node 22.18+, no packages).
import assert from "node:assert/strict";
import { test } from "node:test";
import { newIntentKey, sendIdempotent } from "./idempotent-write.ts";

type Call = { key: string | null; method: string | undefined };

function fakeServer(statuses: Array<[number, Record<string, string>?]>) {
  const calls: Call[] = [];
  const fetch = (async (_input: string | URL, init?: RequestInit) => {
    calls.push({ key: new Headers(init?.headers).get("idempotency-key"), method: init?.method });
    const [status, headers] = statuses[Math.min(calls.length - 1, statuses.length - 1)];
    return new Response(status === 204 ? null : "{}", { status, headers });
  }) as typeof globalThis.fetch;
  return { fetch, calls };
}

const recordSleeps = () => {
  const waits: number[] = [];
  return { waits, sleep: async (ms: number) => void waits.push(ms) };
};

test("the request carries the intent's key", async () => {
  const server = fakeServer([[201]]);
  const response = await sendIdempotent("/v1/incidents", { method: "POST", body: "{}" }, "key-1", { fetch: server.fetch });
  assert.equal(response.status, 201);
  assert.deepEqual(server.calls, [{ key: "key-1", method: "POST" }]);
});

test("a 409 waits Retry-After and resends with the same key", async () => {
  const server = fakeServer([[409, { "retry-after": "2" }], [409, { "retry-after": "1" }], [201]]);
  const { waits, sleep } = recordSleeps();
  const response = await sendIdempotent("/v1/incidents", { method: "POST" }, "key-2", { fetch: server.fetch, sleep });
  assert.equal(response.status, 201);
  assert.deepEqual(server.calls.map((c) => c.key), ["key-2", "key-2", "key-2"]);
  assert.deepEqual(waits, [2000, 1000]);
});

test("a 409 without Retry-After waits the default", async () => {
  const server = fakeServer([[409], [201]]);
  const { waits, sleep } = recordSleeps();
  await sendIdempotent("/v1/incidents", { method: "POST" }, "k", { fetch: server.fetch, sleep, defaultWaitMs: 750 });
  assert.deepEqual(waits, [750]);
});

test("the last 409 is returned once the attempts are spent", async () => {
  const server = fakeServer([[409, { "retry-after": "0" }]]);
  const { sleep } = recordSleeps();
  const response = await sendIdempotent("/v1/incidents", { method: "POST" }, "k", { fetch: server.fetch, sleep, maxAttempts: 3 });
  assert.equal(response.status, 409);
  assert.equal(server.calls.length, 3);
});

test("other failures are returned, never retried", async () => {
  for (const status of [400, 422, 500, 503]) {
    const server = fakeServer([[status]]);
    const response = await sendIdempotent("/v1/incidents", { method: "POST" }, "k", { fetch: server.fetch });
    assert.equal(response.status, status);
    assert.equal(server.calls.length, 1, `a ${status} was re-sent`);
  }
});

test("intent keys are random UUIDs, with or without crypto.randomUUID", () => {
  const shape = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
  const first = newIntentKey();
  assert.match(first, shape);
  assert.notEqual(first, newIntentKey());
  const original = crypto.randomUUID;
  try {
    Object.defineProperty(crypto, "randomUUID", { value: undefined, configurable: true });
    const fallback = newIntentKey();
    assert.match(fallback, shape);
    assert.notEqual(fallback, newIntentKey());
  } finally {
    Object.defineProperty(crypto, "randomUUID", { value: original, configurable: true });
  }
});
