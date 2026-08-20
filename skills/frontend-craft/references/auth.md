# Client authentication and session UX

Read when the UI has login, protected navigation, tokens, or cookie sessions. The server remains the
authorization boundary.

- Match the application's established identity/session design. Public clients do not ship a client
  secret. For OIDC browser flows, use the current provider-supported authorization flow and PKCE where
  required.
- Prefer an approved BFF/HttpOnly cookie session when the architecture supports it. If bearer tokens
  must exist in the browser, keep them out of URLs and persistent script-readable storage unless a
  documented threat model accepts that exposure.
- Centralize request/session handling. On `401`, perform at most the protocol's one safe refresh or
  reauthentication transition; prevent concurrent refresh storms and avoid replaying unsafe requests
  without an idempotency contract. Treat `403` as authorization failure, not refresh failure.
- Route guards and hidden controls improve UX but grant no authority. Render server denial safely and
  clear sensitive client state on logout/revocation.
- Cookie auth needs the selected SameSite/origin/CSRF design. Apply CSP and avoid rendering untrusted
  HTML. Auth/session changes require independent security review and real-browser failure tests.
