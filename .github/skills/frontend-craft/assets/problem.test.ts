// Contract test for problem.ts. Run: node --test problem.test.ts (Node 22.18+, no packages).
import assert from "node:assert/strict";
import { test } from "node:test";
import { fieldErrors, fieldName, isProblemResponse, readProblem, retryAfterMs, UNKNOWN_REQUEST_ID } from "./problem.ts";

const problemResponse = (body: unknown, status = 500, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/problem+json", ...headers },
  });

test("a house problem is read with its request id and detail", async () => {
  const problem = await readProblem(
    problemResponse({
      type: "https://errors.example.internal/internal-server-error",
      title: "Internal server error",
      status: 500,
      detail: "Try again in a moment.",
      request_id: "req-123",
    }),
  );
  assert.equal(problem.request_id, "req-123");
  assert.equal(problem.title, "Internal server error");
  assert.equal(problem.detail, "Try again in a moment.");
  assert.equal(problem.type, "https://errors.example.internal/internal-server-error");
  assert.equal(problem.errors, undefined);
});

test("unknown members are ignored and the body's status wins", async () => {
  const problem = await readProblem(
    problemResponse({ type: "about:blank", title: "Conflict", status: 409, request_id: "r", trace: { a: 1 } }, 500),
  );
  assert.equal(problem.status, 409);
  assert.ok(!("trace" in problem));
});

test("a 422 maps errors[] to form fields, dropping the request part of the location", async () => {
  const problem = await readProblem(
    problemResponse(
      {
        type: "https://errors.example.internal/validation-failed",
        title: "Validation failed",
        status: 422,
        request_id: "req-422",
        errors: [
          { loc: ["body", "title"], msg: "must not be empty" },
          { loc: ["title"], msg: "must be at most 200 characters" },
          { loc: ["query", "limit"], msg: "must be a positive integer" },
          { loc: ["body", "owner", "email"], msg: "must be an email address" },
          { loc: "not-a-list", msg: "ignored" },
        ],
      },
      422,
    ),
  );
  const byField = fieldErrors(problem);
  assert.deepEqual(byField.get("title"), ["must not be empty", "must be at most 200 characters"]);
  assert.deepEqual(byField.get("limit"), ["must be a positive integer"]);
  assert.deepEqual(byField.get("owner.email"), ["must be an email address"]);
  assert.equal(byField.size, 3);
  assert.equal(fieldName(["body"]), "body");
});

test("a gateway HTML error becomes a problem from the status and header", async () => {
  const response = new Response("<html>Bad Gateway</html>", {
    status: 502,
    statusText: "Bad Gateway",
    headers: { "content-type": "text/html", "x-request-id": "edge-77" },
  });
  assert.equal(isProblemResponse(response), false);
  const problem = await readProblem(response);
  assert.deepEqual(problem, { type: "about:blank", title: "Bad Gateway", status: 502, request_id: "edge-77" });
});

test("an unparseable problem body and a missing request id never throw", async () => {
  const broken = new Response("{not json", { status: 500, headers: { "content-type": "application/problem+json" } });
  const problem = await readProblem(broken);
  assert.equal(problem.status, 500);
  assert.equal(problem.request_id, UNKNOWN_REQUEST_ID);
  const noId = await readProblem(problemResponse({ type: "about:blank", title: "Oops", status: 500 }));
  assert.equal(noId.request_id, UNKNOWN_REQUEST_ID);
});

test("Retry-After is read in seconds or as an HTTP date", () => {
  const seconds = new Response(null, { status: 429, headers: { "retry-after": "30" } });
  assert.equal(retryAfterMs(seconds), 30_000);
  const now = Date.parse("Thu, 10 Oct 2026 12:00:00 GMT");
  const dated = new Response(null, { status: 503, headers: { "retry-after": "Thu, 10 Oct 2026 12:00:45 GMT" } });
  assert.equal(retryAfterMs(dated, now), 45_000);
  const past = new Response(null, { status: 503, headers: { "retry-after": "Thu, 10 Oct 2026 11:00:00 GMT" } });
  assert.equal(retryAfterMs(past, now), 0);
  assert.equal(retryAfterMs(new Response(null, { status: 503 })), undefined);
  assert.equal(retryAfterMs(new Response(null, { status: 503, headers: { "retry-after": "soon" } })), undefined);
});
