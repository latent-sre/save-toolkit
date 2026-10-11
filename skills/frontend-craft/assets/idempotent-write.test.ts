// Contract test for idempotent-write.ts. Run: node --test idempotent-write.test.ts (Node 22.18+ or 24+, no packages).
import assert from "node:assert/strict";
import { test } from "node:test";
import { IDEMPOTENCY_HEADER, isInFlight, newIntentKey, sendIdempotent } from "./idempotent-write.ts";

type Call = { url: string; key: string | null; body: string | null };

function server(...responses: Array<() => Response>) {
  const calls: Call[] = [];
  const waits: number[] = [];
  const fetch = async (input: string | URL | Request, init?: RequestInit) => {
    const headers = new Headers(init?.headers);
    calls.push({ url: String(input), key: headers.get(IDEMPOTENCY_HEADER), body: typeof init?.body === "string" ? init.body : null });
    const next = responses.shift();
    if (!next) throw new Error("no more responses");
    return next();
  };
  const sleep = async (ms: number) => { waits.push(ms); };
  return { calls, waits, fetch, sleep };
}

const ok = () => new Response('{"id":"ord-1"}', { status: 201, headers: { "content-type": "application/json" } });
const inFlight = (retryAfter: string) => () => new Response(null, { status: 409, headers: { "retry-after": retryAfter } });
const conflict = () => new Response('{"title":"Order already cancelled"}', { status: 409, headers: { "content-type": "application/problem+json" } });

test("newIntentKey mints a distinct v4 UUID each time", () => {
  const a = newIntentKey(); const b = newIntentKey();
  assert.match(a, /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
  assert.notEqual(a, b);
});

test("the key travels as Idempotency-Key and a success returns after one send", async () => {
  const s = server(ok);
  const response = await sendIdempotent("/v1/orders", { method: "POST", body: "{}" }, "key-1", s);
  assert.equal(response.status, 201);
  assert.deepEqual(s.calls.map((c) => c.key), ["key-1"]);
  assert.equal(s.waits.length, 0);
});

test("an in-flight 409 waits Retry-After and re-sends the same request under the same key", async () => {
  const s = server(inFlight("2"), inFlight("1"), ok);
  const response = await sendIdempotent("/v1/orders", { method: "POST", body: '{"qty":5}' }, "key-2", s);
  assert.equal(response.status, 201);
  assert.deepEqual(s.calls.map((c) => c.key), ["key-2", "key-2", "key-2"]);
  assert.deepEqual(s.calls.map((c) => c.body), ['{"qty":5}', '{"qty":5}', '{"qty":5}']);
  assert.deepEqual(s.waits, [2000, 1000]);
});

test("a Retry-After date is honoured and a wait is capped at maxWaitMs", async () => {
  const soon = new Date(Date.now() + 90_000).toUTCString();
  const s = server(inFlight(soon), ok);
  await sendIdempotent("/v1/orders", { method: "POST" }, "key-3", { ...s, maxWaitMs: 5000 });
  assert.deepEqual(s.waits, [5000]);
  const unreadable = server(inFlight("later"), ok);
  await sendIdempotent("/v1/orders", { method: "POST" }, "key-3b", { ...unreadable, defaultWaitMs: 250 });
  assert.deepEqual(unreadable.waits, [250]);
});

test("a 409 without Retry-After is a conflict, returned at once", async () => {
  const s = server(conflict);
  const response = await sendIdempotent("/v1/orders/ord-1/cancel", { method: "POST" }, "key-4", s);
  assert.equal(response.status, 409);
  assert.equal(isInFlight(response), false);
  assert.equal(s.calls.length, 1);
});

test("any other failure is returned without a retry", async () => {
  for (const status of [400, 401, 403, 422, 500, 503]) {
    const s = server(() => new Response(null, { status }));
    const response = await sendIdempotent("/v1/orders", { method: "POST" }, `key-${status}`, s);
    assert.equal(response.status, status);
    assert.equal(s.calls.length, 1);
  }
});

test("when maxAttempts is spent the last in-flight 409 is returned so the UI can say it is still running", async () => {
  const s = server(inFlight("0"), inFlight("0"), inFlight("0"), ok);
  const response = await sendIdempotent("/v1/orders", { method: "POST" }, "key-5", { ...s, maxAttempts: 3 });
  assert.equal(response.status, 409);
  assert.equal(isInFlight(response), true);
  assert.equal(s.calls.length, 3);
});

test("an abort given as init.signal also ends the wait", async () => {
  const controller = new AbortController();
  const s = server(inFlight("30"), ok);
  const sleep = (_ms: number, signal?: AbortSignal) =>
    new Promise<void>((_resolve, reject) => {
      assert.ok(signal, "the wait must receive the request's own signal");
      signal.addEventListener("abort", () => reject(signal.reason), { once: true });
      controller.abort(new Error("navigated away"));
    });
  await assert.rejects(
    sendIdempotent("/v1/orders", { method: "POST", signal: controller.signal }, "key-7", { fetch: s.fetch, sleep }),
    /navigated away/,
  );
  assert.equal(s.calls.length, 1);
});

test("an abort during the wait rejects with the abort reason and sends nothing more", async () => {
  const controller = new AbortController();
  const s = server(inFlight("30"), ok);
  const sleep = (_ms: number, signal?: AbortSignal) =>
    new Promise<void>((_resolve, reject) => {
      signal?.addEventListener("abort", () => reject(signal.reason), { once: true });
      controller.abort(new Error("user left the page"));
    });
  await assert.rejects(
    sendIdempotent("/v1/orders", { method: "POST" }, "key-6", { fetch: s.fetch, sleep, signal: controller.signal }),
    /user left the page/,
  );
  assert.equal(s.calls.length, 1);
});
