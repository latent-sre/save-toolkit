// idempotent-write.ts — one user intent, one Idempotency-Key.
// For services implementing this Idempotency-Key replay contract: a key
// replayed with the same payload returns the first result; a key reused with a different payload is
// answered 422; while the first request with a key is still running, a replay is answered 409 with
// Retry-After. So: mint a key when the user starts an action (opens the form, clicks "Cancel order"),
// send it on every attempt of that unchanged action, mint a new one when the user edits the payload,
// and wait out an in-flight 409 under the same key, never a fresh one. A 409 without Retry-After is a
// real conflict with current state and is returned at once. Copy this file and problem.ts beside the API client;
// run `node --test idempotent-write.test.ts` (Node 22.18+ or 24+, no packages).

import { retryAfterMs } from "./problem.ts";

export type ReplayableRequestInit = Omit<RequestInit, "body"> & {
  body?: Exclude<BodyInit, ReadableStream> | null;
};

export interface SendOptions {
  fetch?: typeof fetch;
  /** Positive safe-integer total sends, the first one included. Invalid counts throw before sending. */
  maxAttempts?: number;
  /** Wait when an in-flight 409 carries an unreadable Retry-After. */
  defaultWaitMs?: number;
  /** Maximum acceptable wait; a longer delay returns the pending response without retrying. */
  maxWaitMs?: number;
  sleep?: (ms: number, signal?: AbortSignal) => Promise<void>;
  signal?: AbortSignal;
}

export const IDEMPOTENCY_HEADER = "Idempotency-Key";

/** A fresh key for a new user intent. randomUUID needs a secure context; the fallback serves plain-HTTP internal tools. */
export function newIntentKey(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

/** True when the response is the contract's "still running, come back later" answer. */
export function isInFlight(response: Response): boolean {
  return response.status === 409 && response.headers.has("retry-after");
}

function defaultSleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) return reject(signal.reason ?? new DOMException("Aborted", "AbortError"));
    const timer = setTimeout(() => {
      signal?.removeEventListener("abort", onAbort);
      resolve();
    }, ms);
    function onAbort() {
      clearTimeout(timer);
      reject(signal?.reason ?? new DOMException("Aborted", "AbortError"));
    }
    signal?.addEventListener("abort", onAbort, { once: true });
  });
}

/**
 * Sends a state-changing request under `key`. Takes a URL and an init, never a `Request`: a
 * Request's body is a stream that one send consumes, so it cannot be re-sent after a 409.
 * The init accepts only replayable, non-stream bodies; streams are rejected before any send.
 * Returns the first response that is not an in-flight 409, or the last in-flight 409 once
 * maxAttempts is spent or its delay exceeds maxWaitMs, so the caller can say it is still running.
 * Every other failure is returned, never retried here: a write is replayed only by the user's
 * own retry, which passes the same key.
 */
export async function sendIdempotent(
  input: string | URL,
  init: ReplayableRequestInit,
  key: string,
  options: SendOptions = {},
): Promise<Response> {
  const body = init.body;
  // Check the stream interface rather than instanceof, which misses other browser realms.
  if (body !== null && typeof body === "object" && "getReader" in body && typeof body.getReader === "function") {
    throw new TypeError("sendIdempotent requires a replayable body; ReadableStream is not supported");
  }
  const doFetch = options.fetch ?? fetch;
  const sleep = options.sleep ?? defaultSleep;
  const maxAttempts = options.maxAttempts ?? 5;
  if (!Number.isSafeInteger(maxAttempts) || maxAttempts < 1) {
    throw new RangeError("maxAttempts must be a positive safe integer");
  }
  const defaultWaitMs = options.defaultWaitMs ?? 1000;
  const maxWaitMs = options.maxWaitMs ?? 30_000;
  const headers = new Headers(init.headers);
  headers.set(IDEMPOTENCY_HEADER, key);
  // One effective signal for the sends and the waits between them, whichever way it was given.
  const signal = options.signal ?? init.signal ?? undefined;
  const request: RequestInit = { ...init, headers, signal: signal ?? null };

  for (let attempt = 1; ; attempt += 1) {
    const response = await doFetch(input, request);
    if (!isInFlight(response) || attempt >= maxAttempts) return response;
    const waitMs = retryAfterMs(response) ?? defaultWaitMs;
    if (waitMs > maxWaitMs) return response;
    await sleep(waitMs, signal);
  }
}
