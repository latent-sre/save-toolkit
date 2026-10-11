// One user intent, one Idempotency-Key. Mint the key when the user starts an action (opens the
// form, clicks "Close incident"), reuse it on every retry of that action, and mint a new one for
// a new action. While the first request with a key is still running, the house contract answers
// 409: wait Retry-After and send the same request with the same key again, never a fresh key.
// Self-contained so it drops into an app's API layer; `node --test idempotent-write.test.ts`.

export interface WriteOptions {
  fetch?: typeof fetch;
  /** Total sends, the first included. */
  maxAttempts?: number;
  /** Wait when a 409 carries no Retry-After. */
  defaultWaitMs?: number;
  sleep?: (ms: number) => Promise<void>;
  signal?: AbortSignal;
}

// crypto.randomUUID exists only in secure contexts (HTTPS or localhost); getRandomValues exists
// everywhere, so an internal tool served over plain HTTP still gets a random key.
export function newIntentKey(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

function waitFor(response: Response, fallbackMs: number): number {
  const header = response.headers.get("retry-after")?.trim();
  if (header && /^\d+$/.test(header)) return Number(header) * 1000;
  const date = header ? Date.parse(header) : Number.NaN;
  return Number.isNaN(date) ? fallbackMs : Math.max(0, date - Date.now());
}

// Sends a state-changing request under `key`. Returns the first response that is not a 409, or
// the last 409 once maxAttempts is spent so the caller can say the action is still running.
// Any other failure is returned, not retried: a write is replayed only by the user's own retry,
// which passes the same key.
export async function sendIdempotent(
  input: string | URL,
  init: RequestInit,
  key: string,
  options: WriteOptions = {},
): Promise<Response> {
  const doFetch = options.fetch ?? fetch;
  const sleep = options.sleep ?? ((ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms)));
  const maxAttempts = options.maxAttempts ?? 5;
  const headers = new Headers(init.headers);
  headers.set("Idempotency-Key", key);
  for (let attempt = 1; ; attempt += 1) {
    const response = await doFetch(input, { ...init, headers, signal: options.signal });
    if (response.status !== 409 || attempt >= maxAttempts) return response;
    await sleep(waitFor(response, options.defaultWaitMs ?? 1000));
  }
}
