// Contract test for problem.ts. Run: node --test problem.test.ts (Node 22.18+ or 24+, no packages).
import assert from "node:assert/strict";
import { test } from "node:test";
import { fieldErrors, fieldName, isProblemResponse, readProblem, retryAfterMs, UNKNOWN_REQUEST_ID } from "./problem.ts";

const reply = (body: unknown, status: number, contentType: string, headers: Record<string, string> = {}) =>
  new Response(typeof body === "string" ? body : JSON.stringify(body), {
    status,
    headers: { "content-type": contentType, ...headers },
  });
const problemJson = (body: unknown, status = 500, headers: Record<string, string> = {}) =>
  reply(body, status, "application/problem+json", headers);

test("a house problem is read with its request id, type and detail", async () => {
  const problem = await readProblem(
    problemJson({
      type: "https://errors.example.internal/order-locked",
      title: "Order is locked",
      status: 409,
      detail: "Another operator is editing it. Try again in a minute.",
      request_id: "req-0f3a",
    }, 409),
  );
  assert.equal(problem.type, "https://errors.example.internal/order-locked");
  assert.equal(problem.title, "Order is locked");
  assert.equal(problem.status, 409);
  assert.equal(problem.detail, "Another operator is editing it. Try again in a minute.");
  assert.equal(problem.request_id, "req-0f3a");
  assert.equal(problem.errors, undefined);
});

test("unknown members are ignored and the body's status wins over the response status", async () => {
  const problem = await readProblem(problemJson({ title: "Gone", status: 410, request_id: "r", trace: { a: 1 } }, 500));
  assert.equal(problem.status, 410);
  assert.equal(problem.type, "about:blank");
  assert.ok(!("trace" in problem));
});

test("a house 422 maps errors[] to form fields, dropping the request part of the location", async () => {
  const problem = await readProblem(
    problemJson({
      type: "about:blank", title: "Validation failed", status: 422, request_id: "req-422",
      errors: [
        { loc: ["body", "symbol"], msg: "Unknown symbol" },
        { loc: ["body", "limit", "price"], msg: "Must be positive" },
        { loc: ["body", "limit", "price"], msg: "At most 4 decimals" },
        { loc: ["query", "page"], msg: "Must be an integer" },
        { nonsense: true },
      ],
    }, 422),
  );
  const fields = fieldErrors(problem);
  assert.deepEqual([...fields.keys()], ["symbol", "limit.price", "page"]);
  assert.deepEqual(fields.get("limit.price"), ["Must be positive", "At most 4 decimals"]);
  assert.equal(fieldName(["title"]), "title");
  assert.equal(fieldName(["body"]), "body");
  assert.equal(fieldName(["body", "legs", 0, "qty"]), "legs.0.qty");
});

test("FastAPI's native 422 becomes a problem with fields and the header request id", async () => {
  const problem = await readProblem(
    reply({ detail: [{ loc: ["body", "account_id"], msg: "Field required", type: "missing", input: null }] }, 422, "application/json", { "x-request-id": "gw-77" }),
  );
  assert.equal(problem.status, 422);
  assert.equal(problem.title, "Validation failed");
  assert.equal(problem.request_id, "gw-77");
  assert.deepEqual(fieldErrors(problem).get("account_id"), ["Field required"]);
});

test("a FastAPI HTTPException's detail string becomes the problem's detail", async () => {
  const problem = await readProblem(reply({ detail: "Account 4411 not found" }, 404, "application/json; charset=utf-8"));
  assert.equal(problem.status, 404);
  assert.equal(problem.detail, "Account 4411 not found");
  assert.equal(problem.request_id, UNKNOWN_REQUEST_ID);
});

test("an HTML gateway page falls back to the status and the X-Request-ID header", async () => {
  const problem = await readProblem(reply("<html>502 Bad Gateway</html>", 502, "text/html", { "x-request-id": "edge-9" }));
  assert.equal(problem.status, 502);
  assert.equal(problem.title, "HTTP 502");
  assert.equal(problem.request_id, "edge-9");
  assert.equal(isProblemResponse(reply("", 500, "application/problem+json")), true);
});

test("an unreadable problem body still yields a problem, never a throw", async () => {
  const problem = await readProblem(new Response("{not json", { status: 500, headers: { "content-type": "application/problem+json" } }));
  assert.equal(problem.status, 500);
  assert.equal(problem.request_id, UNKNOWN_REQUEST_ID);
  const array = await readProblem(problemJson([1, 2, 3], 500));
  assert.equal(array.title, "HTTP 500");
});

test("Retry-After is read in seconds or as an HTTP date, else undefined", () => {
  const seconds = new Response(null, { status: 429, headers: { "retry-after": "7" } });
  assert.equal(retryAfterMs(seconds), 7000);
  const at = new Date("2026-10-11T12:00:30Z");
  const dated = new Response(null, { status: 503, headers: { "retry-after": at.toUTCString() } });
  assert.equal(retryAfterMs(dated, Date.parse("2026-10-11T12:00:00Z")), 30_000);
  assert.equal(retryAfterMs(dated, Date.parse("2026-10-11T13:00:00Z")), 0);
  assert.equal(retryAfterMs(new Response(null, { status: 503 })), undefined);
  assert.equal(retryAfterMs(new Response(null, { status: 503, headers: { "retry-after": "soon" } })), undefined);
});
