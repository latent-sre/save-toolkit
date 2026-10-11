// RFC 9457 problem details as the house contract shapes them: `request_id` on every problem and
// `errors[]` of `{ loc, msg }` on validation failures. Copy into the app's API layer and run
// `node --test problem.test.ts` (Node 22.18+ strips the types; no packages).

export interface FieldError {
  loc: string[];
  msg: string;
}

export interface Problem {
  type: string;
  title: string;
  status: number;
  detail?: string;
  instance?: string;
  request_id: string;
  errors?: FieldError[];
}

export const UNKNOWN_REQUEST_ID = "unknown";

export function isProblemResponse(response: Response): boolean {
  return (response.headers.get("content-type") ?? "").toLowerCase().startsWith("application/problem+json");
}

// Reads a failed response into a Problem the UI can show. A gateway may answer with HTML or an
// empty body instead of a problem; the result then carries the status and the X-Request-ID
// header, never a thrown error: an error path that throws leaves the operator with nothing.
export async function readProblem(response: Response): Promise<Problem> {
  const headerId = response.headers.get("x-request-id");
  const fallback: Problem = {
    type: "about:blank",
    title: response.statusText || `HTTP ${response.status}`,
    status: response.status,
    request_id: headerId ?? UNKNOWN_REQUEST_ID,
  };
  if (!isProblemResponse(response)) return fallback;
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    return fallback;
  }
  if (body === null || typeof body !== "object" || Array.isArray(body)) return fallback;
  const raw = body as Record<string, unknown>;
  const problem: Problem = {
    type: typeof raw.type === "string" ? raw.type : "about:blank",
    title: typeof raw.title === "string" ? raw.title : fallback.title,
    status: typeof raw.status === "number" ? raw.status : response.status,
    request_id: typeof raw.request_id === "string" && raw.request_id ? raw.request_id : fallback.request_id,
  };
  if (typeof raw.detail === "string") problem.detail = raw.detail;
  if (typeof raw.instance === "string") problem.instance = raw.instance;
  const errors = Array.isArray(raw.errors) ? raw.errors.filter(isFieldError) : [];
  if (errors.length) problem.errors = errors;
  return problem;
}

function isFieldError(value: unknown): value is FieldError {
  if (value === null || typeof value !== "object") return false;
  const { loc, msg } = value as Record<string, unknown>;
  return Array.isArray(loc) && loc.every((part) => typeof part === "string") && typeof msg === "string";
}

const LOCATION_PREFIXES = new Set(["body", "query", "path", "header", "cookie"]);

// The form field a validation location names: the request part ("body", "query"...) is dropped,
// so ["body", "title"] and ["title"] both name "title", and ["body", "owner", "email"] names
// "owner.email".
export function fieldName(loc: string[]): string {
  const parts = loc.length > 1 && LOCATION_PREFIXES.has(loc[0]) ? loc.slice(1) : loc;
  return parts.join(".");
}

// Groups validation messages by form field, so a form can place each message beside its input.
export function fieldErrors(problem: Problem): Map<string, string[]> {
  const grouped = new Map<string, string[]>();
  for (const { loc, msg } of problem.errors ?? []) {
    const key = fieldName(loc);
    grouped.set(key, [...(grouped.get(key) ?? []), msg]);
  }
  return grouped;
}

// Milliseconds to wait before a retry, from a Retry-After header in seconds or as an HTTP date;
// undefined when the header is absent or unreadable, so the caller falls back to its own backoff.
export function retryAfterMs(response: Response, now: number = Date.now()): number | undefined {
  const header = response.headers.get("retry-after");
  if (header === null) return undefined;
  if (/^\d+$/.test(header.trim())) return Number(header) * 1000;
  const date = Date.parse(header);
  return Number.isNaN(date) ? undefined : Math.max(0, date - now);
}
