// error-panel.tsx — one failing region shows its own card; the rest of the page keeps working.
// Wrap each route and each independent panel in <PanelErrorBoundary>. A render error inside it
// becomes an <ErrorCard> in place: what happened, what to do, the request ID (copyable — it is the
// key to the log line) with its log and trace links when runtime configuration provides the
// templates, the time with its zone, and a retry only when the request is safe to repeat. Errors
// from event handlers and async code are not caught by a boundary: pass them to <ErrorCard> yourself
// from the state your handler sets. Write this file into the app's shared components; it needs only
// React and its stylesheet, which draws it from the theme tokens. The test beside it runs in the
// app with Vitest and Testing Library.
import { Component, useState, type ReactNode } from "react";
import { UNKNOWN_REQUEST_ID, type Problem } from "./problem";
import "./error-panel.css";

export interface ErrorLinks {
  /** Templates with a {request_id} placeholder, e.g. "https://splunk.example.internal/search?q={request_id}". */
  logSearchUrlTemplate?: string;
  traceUrlTemplate?: string;
}

export interface ErrorCardProps {
  /** Short, in the user's words: "Orders did not load". Never the type URI. */
  title: string;
  /** What to do next. */
  detail?: string;
  requestId?: string;
  status?: number;
  /** When it happened; defaults to the moment the card first rendered, captured once. Rendered with its zone, because consoles are read across regions. */
  at?: Date;
  timeZone?: string;
  links?: ErrorLinks;
  /** Offer a retry only when the request is safe to repeat (a read, or a write under its own idempotency key). */
  onRetry?: () => void;
}

// Explicit components: dateStyle/timeStyle cannot be combined with timeZoneName, and the zone must
// show. An unknown zone name falls back to UTC rather than throwing inside the one component that
// must never throw: it is the boundary's own fallback.
const TIME_PARTS: Intl.DateTimeFormatOptions = {
  year: "numeric",
  month: "short",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
  timeZoneName: "short",
};

export function timeFormat(timeZone?: string): Intl.DateTimeFormat {
  try {
    return new Intl.DateTimeFormat(undefined, { ...TIME_PARTS, timeZone });
  } catch {
    return new Intl.DateTimeFormat(undefined, { ...TIME_PARTS, timeZone: "UTC" });
  }
}

function fill(template: string, requestId: string): string {
  return template.replaceAll("{request_id}", encodeURIComponent(requestId));
}

export function ErrorCard({ title, detail, requestId, status, at, timeZone, links, onRetry }: ErrorCardProps) {
  const [copied, setCopied] = useState(false);
  const [firstShown] = useState(() => new Date());
  const when = at ?? firstShown;
  const canCopy = typeof navigator !== "undefined" && !!navigator.clipboard;
  const copy = async () => {
    if (!requestId || !canCopy) return;
    try {
      await navigator.clipboard.writeText(requestId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };
  return (
    <section role="alert" aria-labelledby={undefined} data-error-card data-status="critical">
      <h2>{title}</h2>
      {detail ? <p>{detail}</p> : null}
      <dl>
        {status !== undefined ? (
          <>
            <dt>Status</dt>
            <dd>{status}</dd>
          </>
        ) : null}
        <dt>Request ID</dt>
        <dd>
          <code data-request-id>{requestId ?? "unknown"}</code>{" "}
          {requestId && canCopy ? (
            <button type="button" onClick={copy} aria-live="polite">
              {copied ? "Copied" : "Copy"}
            </button>
          ) : null}
          {requestId && links?.logSearchUrlTemplate ? (
            <>
              {" "}
              <a href={fill(links.logSearchUrlTemplate, requestId)} target="_blank" rel="noreferrer">
                Logs
              </a>
            </>
          ) : null}
          {requestId && links?.traceUrlTemplate ? (
            <>
              {" "}
              <a href={fill(links.traceUrlTemplate, requestId)} target="_blank" rel="noreferrer">
                Trace
              </a>
            </>
          ) : null}
        </dd>
        <dt>When</dt>
        <dd>
          <time dateTime={when.toISOString()}>{timeFormat(timeZone).format(when)}</time>
        </dd>
      </dl>
      {onRetry ? (
        <button type="button" onClick={onRetry}>
          Try again
        </button>
      ) : null}
    </section>
  );
}

/**
 * Builds ErrorCard props from a Problem the API client read, so every API failure renders the same
 * way. The helper's "unknown" sentinel means the server sent no correlation ID: the card then shows
 * "unknown" and offers no Copy, Logs or Trace action, since each would search for that word.
 */
export function problemCardProps(problem: Problem, title: string, links?: ErrorLinks): Omit<ErrorCardProps, "onRetry"> {
  return {
    title,
    detail: problem.detail ?? problem.title,
    requestId: problem.request_id === UNKNOWN_REQUEST_ID ? undefined : problem.request_id,
    status: problem.status,
    links,
  };
}

interface BoundaryProps {
  /** Names the region in the card: "Orders did not render". */
  title: string;
  children: ReactNode;
  links?: ErrorLinks;
  /**
   * Clears a shown card when it changes: pass the route's pathname (or the record id) so a failure
   * does not follow the user to the next route through a boundary the router keeps mounted.
   * Remounting the boundary with `key` does the same.
   */
  resetKey?: unknown;
  /** Called when the user chooses to try again, before the children render again: clear the cause here. */
  onReset?: () => void;
  /** Report to the browser error reporting with the release; never with sensitive values. */
  onError?: (error: unknown) => void;
}

interface BoundaryState {
  failed: boolean;
  requestId?: string;
  detail?: string;
  status?: number;
}

// Only a problem-shaped error (one carrying a request_id or status, as the API client throws)
// contributes its detail or title, which the API wrote for people. A plain Error's message names
// properties and internals: it goes to onError and the console, never to the card. The helper's
// "unknown" sentinel reaches the card as no request ID, exactly as problemCardProps maps it.
function describe(error: unknown): Omit<BoundaryState, "failed"> {
  if (error && typeof error === "object") {
    const e = error as { request_id?: unknown; status?: unknown; detail?: unknown; title?: unknown };
    const problemLike = typeof e.request_id === "string" || typeof e.status === "number";
    const text = typeof e.detail === "string" ? e.detail : typeof e.title === "string" ? e.title : undefined;
    return {
      requestId: typeof e.request_id === "string" && e.request_id !== UNKNOWN_REQUEST_ID ? e.request_id : undefined,
      status: typeof e.status === "number" ? e.status : undefined,
      detail: problemLike ? text : undefined,
    };
  }
  return {};
}

/** React catches render errors only in a class boundary. One per route and per independent panel. */
export class PanelErrorBoundary extends Component<BoundaryProps, BoundaryState> {
  state: BoundaryState = { failed: false };

  static getDerivedStateFromError(error: unknown): BoundaryState {
    return { failed: true, ...describe(error) };
  }

  componentDidCatch(error: unknown) {
    this.props.onError?.(error);
  }

  componentDidUpdate(previous: BoundaryProps) {
    if (this.state.failed && previous.resetKey !== this.props.resetKey) {
      this.setState({ failed: false, requestId: undefined, detail: undefined, status: undefined });
    }
  }

  // onReset runs first so the caller can clear the cause (refetch, reset a store) before the
  // children render again; if the cause persists, the card simply returns.
  reset = () => {
    this.props.onReset?.();
    this.setState({ failed: false, requestId: undefined, detail: undefined, status: undefined });
  };

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <ErrorCard
        title={this.props.title}
        detail={this.state.detail ?? "Reload this panel. If it fails again, share the request ID with the on-call engineer."}
        requestId={this.state.requestId}
        status={this.state.status}
        links={this.props.links}
        onRetry={this.reset}
      />
    );
  }
}
