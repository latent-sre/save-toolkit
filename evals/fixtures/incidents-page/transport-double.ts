/** Bounded calibration only: a fetch transport double, never the fixture's MSW integration. */
let handler;
export const http = { get: (_path, resolver) => resolver };
export const HttpResponse = {
  json: (body, init = {}) => new Response(JSON.stringify(body), {
    ...init, headers: { 'Content-Type': 'application/json' },
  }),
};
export const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
export const server = {
  use: (resolver) => { handler = resolver; },
  resetHandlers: () => { handler = undefined; },
  listen: () => {
    globalThis.fetch = async (input) => {
      const request = new Request(new URL(String(input), window.location.origin));
      if (new URL(request.url).pathname !== '/api/incidents' || !handler) {
        throw new Error(`Calibration forbids unhandled fetch: ${request.url}`);
      }
      return handler({ request });
    };
  },
};

// Imported by the oracle, but intentionally unavailable: bounded calibration never runs bar6.
export default { run: () => { throw new Error('axe is not part of bounded calibration'); } };
