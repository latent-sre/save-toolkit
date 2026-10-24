// Contract test for idempotent-write.ts. Run: node --test idempotent-write.test.ts (Node 22.18+ or 24+, no packages).
import assert from "node:assert/strict";
import { test } from "node:test";
import { IDEMPOTENCY_HEADER, isInFlight, newIntentKey, sendIdempotent } from "./idempotent-write.ts";

type Call = { url: string; key: string | null; body: string | null };

function server(...responses: Array<() => Response>) {
  const calls: Call[] = [];
  const waits: number[] = [];
  const fetch = async (input: string | URL | Request, init?: RequestInit) => {
    const request = new Request(input instanceof Request ? input : new URL(input, "https://api.example.test"), init);
    calls.push({ url: request.url, key: request.headers.get(IDEMPOTENCY_HEADER), body: request.body === null ? null : await request.text() });
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

test("a stream body is refused before any send or wait", async () => {
  const body = new ReadableStream({
    start(controller) { controller.enqueue(new TextEncoder().encode('{"qty":5}')); controller.close(); },
  });
  let sends = 0;
  let waits = 0;
  const fetch = async (input: string | URL | Request, init?: RequestInit) => {
    sends += 1;
    const request = new Request(input, { ...init, duplex: "half" } as RequestInit);
    await request.arrayBuffer();
    return sends === 1 ? inFlight("0")() : ok();
  };
  // Exercise the runtime boundary too: JavaScript callers can bypass the public body type.
  const init = { method: "POST", body } as unknown as Parameters<typeof sendIdempotent>[1];
  const error = await sendIdempotent("https://api.example.test/v1/orders", init, "key-stream", {
    fetch, sleep: async () => { waits += 1; },
  }).then(() => undefined, (error: unknown) => error);
  assert.equal(sends, 0);
  assert.equal(waits, 0);
  assert.equal(body.locked, false);
  assert.ok(error instanceof TypeError);
  assert.match(error.message, /replayable|stream/i);
});

test("a Retry-After beyond the wait budget returns the pending response without another send", async () => {
  for (const retryAfter of ["120", new Date("2099-01-01T00:00:00Z").toUTCString()]) {
    const pending = inFlight(retryAfter)();
    const s = server(() => pending, ok);
    const response = await sendIdempotent("/v1/orders", { method: "POST" }, "key-3", s);
    assert.equal(response, pending);
    assert.equal(s.calls.length, 1);
    assert.deepEqual(s.waits, []);
  }
});

test("a Retry-After equal to the wait budget is honoured in full", async () => {
  const s = server(inFlight("5"), ok);
  const response = await sendIdempotent("/v1/orders", { method: "POST" }, "key-3a", { ...s, maxWaitMs: 5000 });
  assert.equal(response.status, 201);
  assert.equal(s.calls.length, 2);
  assert.deepEqual(s.waits, [5000]);
});

test("an unreadable Retry-After uses the fallback wait", async () => {
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

test("invalid attempt counts are refused before sending or waiting", async () => {
  for (const maxAttempts of [NaN, Infinity, -Infinity, 1.5, 0, -1, Number.MAX_SAFE_INTEGER + 1]) {
    const s = server(inFlight("0"), inFlight("0"), ok);
    await assert.rejects(sendIdempotent("/v1/orders", { method: "POST" }, "invalid-count", { ...s, maxAttempts }), RangeError);
    assert.equal(s.calls.length, 0);
    assert.deepEqual(s.waits, []);
  }
});

test("default and single-attempt bounds return the final pending response", async () => {
  for (const maxAttempts of [undefined, 1]) {
    const s = server(...Array.from({ length: 6 }, () => inFlight("0")));
    const response = await sendIdempotent("/v1/orders", { method: "POST" }, "bounded", { ...s, maxAttempts });
    assert.equal(response.status, 409);
    assert.equal(s.calls.length, maxAttempts ?? 5);
    assert.equal(s.waits.length, (maxAttempts ?? 5) - 1);
  }
});
