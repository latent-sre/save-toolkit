// problem.ts — read a failed API response into something the UI can show.
// Supports RFC 9457 `application/problem+json`, including optional `request_id` and `errors[]`
// extensions with `{ loc, msg }` validation entries. It also reads native FastAPI shapes:
// `{ detail: [{ loc, msg, type }] }` for a 422 and `{ detail: "..." }` for an HTTPException,
// plus a JSON `message` or an HTML/empty gateway fallback. Match the client's handling to the
// service's actual contract; these supported shapes are not requirements for every service.
// readProblem() returns one Problem with a title, status and request ID from the supported body
// field or X-Request-ID header, or "unknown" when unavailable. Write this file beside the API
// client; run `node --test problem.test.ts`
// (Node 22.18+ or 24+, no packages).

export interface FieldError {
  /** Where the invalid value sits: for example ["body", "owner", "email"], ["body", "legs", 0, "qty"], or ["email"]. */
  loc: Array<string | number>;
  msg: string;
}

export interface Problem {
  /** A stable URI naming the error class; compare this, never the title. "about:blank" when unnamed. */
  type: string;
  title: string;
  status: number;
  /** What happened and what to do, for people. */
  detail?: string;
  instance?: string;
  /** Correlation value from a supported body field or response header; "unknown" when unavailable. */
  request_id: string;
  errors?: FieldError[];
}

export const UNKNOWN_REQUEST_ID = "unknown";

const REQUEST_PARTS = new Set(["body", "query", "path", "header", "cookie"]);

export function isProblemResponse(response: Response): boolean {
  return contentType(response).startsWith("application/problem+json");
}

function contentType(response: Response): string {
  return (response.headers.get("content-type") ?? "").trim().toLowerCase();
}

/**
 * Reads a failed response into a Problem. Never throws: an error path that throws leaves the
 * operator with nothing. For a response whose body another client already read (openapi-fetch
 * returns `{ error, response }` with the body consumed), use problemFromBody with that body.
 */
export async function readProblem(response: Response): Promise<Problem> {
  const type = contentType(response);
  if (!type.startsWith("application/problem+json") && !type.startsWith("application/json")) return problemFromBody(undefined, response);
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    body = undefined;
  }
  return problemFromBody(body, response);
}

/**
 * Builds a Problem from a body something else already parsed, with the response for its status,
 * content type and X-Request-ID. openapi-fetch reads every error body before it returns
 * `{ error, response }`, so `readProblem(response)` there sees a consumed stream and can only fall
 * back; pass its `error` here instead. A string (an HTML gateway page), undefined (an empty body)
 * or any non-object yields the fallback: the status, and the header's request ID or "unknown".
 */
export function problemFromBody(body: unknown, response: Response): Problem {
  const headerId = response.headers.get("x-request-id")?.trim();
  const fallback: Problem = {
    type: "about:blank",
    title: response.statusText || `HTTP ${response.status}`,
    status: response.status,
    request_id: headerId || UNKNOWN_REQUEST_ID,
  };
  if (!isRecord(body)) return fallback;
  return isProblemResponse(response) ? fromProblemBody(body, fallback) : fromPlainJson(body, fallback);
}

function fromProblemBody(raw: Record<string, unknown>, fallback: Problem): Problem {
  const problem: Problem = {
    type: typeof raw.type === "string" && raw.type ? raw.type : "about:blank",
    title: typeof raw.title === "string" && raw.title ? raw.title : fallback.title,
    status: typeof raw.status === "number" ? raw.status : fallback.status,
    request_id: typeof raw.request_id === "string" && raw.request_id ? raw.request_id : fallback.request_id,
  };
  if (typeof raw.detail === "string") problem.detail = raw.detail;
  if (typeof raw.instance === "string") problem.instance = raw.instance;
  const errors = Array.isArray(raw.errors) ? raw.errors.filter(isFieldError) : [];
  if (errors.length) problem.errors = errors;
  return problem;
}

// Native FastAPI shapes: `detail` is a list of validation errors or a plain message.
function fromPlainJson(raw: Record<string, unknown>, fallback: Problem): Problem {
  if (Array.isArray(raw.detail)) {
    const errors = raw.detail.filter(isFieldError);
    const problem: Problem = { ...fallback, title: "Validation failed", status: fallback.status || 422 };
    if (errors.length) problem.errors = errors;
    return problem;
  }
  if (typeof raw.detail === "string" && raw.detail) return { ...fallback, detail: raw.detail };
  if (typeof raw.message === "string" && raw.message) return { ...fallback, detail: raw.message };
  return fallback;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isFieldError(value: unknown): value is FieldError {
  if (!isRecord(value)) return false;
  return Array.isArray(value.loc) && value.loc.every((part) => typeof part === "string" || typeof part === "number") && typeof value.msg === "string";
}

/** The form field a location names: ["body", "owner", "email"] and ["owner", "email"] both give "owner.email". */
export function fieldName(loc: Array<string | number>): string {
  const parts = loc.map(String);
  const dropped = parts.length > 1 && REQUEST_PARTS.has(parts[0]) ? parts.slice(1) : parts;
  return dropped.join(".");
}

/** Validation messages grouped by field, so a form places each beside its input and keeps the typed value. */
export function fieldErrors(problem: Problem): Map<string, string[]> {
  const grouped = new Map<string, string[]>();
  for (const { loc, msg } of problem.errors ?? []) {
    const key = fieldName(loc);
    grouped.set(key, [...(grouped.get(key) ?? []), msg]);
  }
  return grouped;
}

/** Milliseconds to wait from a Retry-After header (seconds or an HTTP date); undefined when absent or unreadable. */
export function retryAfterMs(response: Response, now: number = Date.now()): number | undefined {
  const header = response.headers.get("retry-after")?.trim();
  if (!header) return undefined;
  if (/^\d+$/.test(header)) return Number(header) * 1000;
  const at = Date.parse(header);
  return Number.isNaN(at) ? undefined : Math.max(0, at - now);
}
