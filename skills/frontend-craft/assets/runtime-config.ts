// runtime-config.ts — build once, configure at startup.
// The bundle is identical in every environment; what differs (the API base, the environment's name,
// log-search and trace URL templates) is served beside index.html as /config.json and loaded before
// the app renders. Declare the fields the app needs, load once at startup, and show a startup error
// naming any missing field rather than a blank page. The file reaches every browser, so it never
// holds a secret. Write this file into the app's bootstrap; run `node --test runtime-config.test.ts`
// (Node 22.18+ or 24+, no packages).

export type FieldKind = "string" | "string?" | "url" | "url?" | "boolean?" | "number?";
export type ConfigSchema = Record<string, FieldKind>;

type Value<K extends FieldKind> =
  K extends "string" | "url" ? string
  : K extends "string?" | "url?" ? string | undefined
  : K extends "boolean?" ? boolean | undefined
  : number | undefined;

type RequiredKeys<S extends ConfigSchema> = { [K in keyof S]: S[K] extends `${string}?` ? never : K }[keyof S];
type OptionalKeys<S extends ConfigSchema> = { [K in keyof S]: S[K] extends `${string}?` ? K : never }[keyof S];

/** Required kinds become required properties; optional kinds ("string?", "url?", ...) become optional ones. */
export type Config<S extends ConfigSchema> = { readonly [K in RequiredKeys<S>]: Value<S[K]> } & {
  readonly [K in OptionalKeys<S>]?: Value<S[K]>;
};

export class RuntimeConfigError extends Error {
  readonly problems: readonly string[];
  constructor(problems: string[]) {
    super(`Runtime configuration is unusable: ${problems.join("; ")}`);
    this.name = "RuntimeConfigError";
    this.problems = problems;
  }
}

export interface LoadOptions {
  /** Same-origin by default; a path keeps cookies and the CSP's connect-src simple. */
  url?: string;
  fetch?: typeof fetch;
}

const SAME_ORIGIN = "http://same-origin.invalid";

/** An absolute http(s) URL, or a root-relative path such as "/v1" that stays on this origin after the browser normalises it. */
export function isUrlLike(value: string): boolean {
  try {
    if (value.startsWith("/")) {
      // "//host/x" and "/\\host/x" both resolve to another origin once the URL parser normalises them.
      const resolved = new URL(value, SAME_ORIGIN);
      return resolved.origin === SAME_ORIGIN && !value.includes("\\");
    }
    const parsed = new URL(value);
    return parsed.protocol === "http:" || parsed.protocol === "https:";
  } catch {
    return false;
  }
}

function problemsFor(key: string, kind: FieldKind, value: unknown): string[] {
  const optional = kind.endsWith("?");
  if (value === undefined || value === null) return optional ? [] : [`${key} is missing (expected ${kind})`];
  switch (kind) {
    case "string": case "string?":
      return typeof value === "string" && value.length > 0 ? [] : [`${key} must be a non-empty string`];
    case "url": case "url?":
      return typeof value === "string" && isUrlLike(value) ? [] : [`${key} must be an absolute http(s) URL or a path starting with /`];
    case "boolean?":
      return typeof value === "boolean" ? [] : [`${key} must be true or false`];
    case "number?":
      return typeof value === "number" && Number.isFinite(value) ? [] : [`${key} must be a finite number`];
  }
}

/** Validates a parsed document against the schema. A key the schema does not name is a startup error, so a misspelled optional setting cannot silently disable itself. */
export function validateConfig<S extends ConfigSchema>(schema: S, document: unknown): Config<S> {
  if (document === null || typeof document !== "object" || Array.isArray(document)) {
    throw new RuntimeConfigError(["the document is not a JSON object"]);
  }
  const raw = document as Record<string, unknown>;
  const problems: string[] = [];
  const out: Record<string, unknown> = {};
  for (const [key, kind] of Object.entries(schema)) {
    const value = raw[key];
    problems.push(...problemsFor(key, kind, value));
    if (value !== undefined && value !== null) out[key] = value;
  }
  for (const key of Object.keys(raw)) {
    if (!(key in schema)) problems.push(`${key} is not a known setting (check the spelling)`);
  }
  if (problems.length) throw new RuntimeConfigError(problems);
  return Object.freeze(out) as Config<S>;
}

/** Fetches and validates /config.json. Rejects with RuntimeConfigError; the caller renders that, never a blank page. */
export async function loadRuntimeConfig<S extends ConfigSchema>(schema: S, options: LoadOptions = {}): Promise<Config<S>> {
  const doFetch = options.fetch ?? fetch;
  const url = options.url ?? "/config.json";
  let response: Response;
  try {
    response = await doFetch(url, { cache: "no-store", credentials: "same-origin", headers: { accept: "application/json" } });
  } catch (cause) {
    throw new RuntimeConfigError([`${url} could not be fetched: ${cause instanceof Error ? cause.message : String(cause)}`]);
  }
  if (!response.ok) throw new RuntimeConfigError([`${url} answered HTTP ${response.status}`]);
  let document: unknown;
  try {
    document = await response.json();
  } catch {
    throw new RuntimeConfigError([`${url} is not valid JSON`]);
  }
  return validateConfig(schema, document);
}

export type EnvironmentTone = "production" | "staging" | "development" | "other";

/** Classifies an environment name for the shell's badge; production is always the most distinct. */
export function environmentTone(name: string): EnvironmentTone {
  const n = name.trim().toLowerCase();
  if (/^(prod|production|live)(?![a-z])/.test(n)) return "production";
  if (/^(stag|staging|uat|preprod|pre-prod|qa)(?![a-z])/.test(n)) return "staging";
  if (/^(dev|development|local|sandbox|test)(?![a-z])/.test(n)) return "development";
  return "other";
}
