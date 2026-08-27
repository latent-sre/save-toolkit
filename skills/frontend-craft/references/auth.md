# Auth (client side)

Read this for any UI a teammate can reach — at work that is all of them.

The server still enforces; the UI is convenience, not the security boundary. The universal frontend
rules live in `../SKILL.md`. On any conflict, SKILL.md wins.

## Auth

- **OIDC Authorization Code + PKCE** against corp SSO; **never** ship a client secret.
- Prefer a **BFF / httpOnly-cookie** session; otherwise hold the access token **in memory** and
  refresh it through an **httpOnly, Secure cookie**. Never `localStorage` for anything an XSS could
  steal.
- One fetch/Query wrapper does **401 → refresh once → retry, else redirect to login**; every call
  inherits it instead of reinventing it. Silent refresh keeps the session alive.
- Route guards gate whole areas and hide actions the user lacks; the API's `401/403` is the real
  boundary.

## Web security

- **XSS:** rely on framework escaping; avoid `dangerouslySetInnerHTML` (or `v-html`) on anything
  untrusted; set a **Content-Security-Policy**.
- **CSRF:** for cookie auth use `SameSite` + a CSRF token. Same-origin or a locked **server-side CORS
  allowlist**.
- Hand sensitive flows to the `reviewer` agent.
