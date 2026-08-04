# Auth (client side)

Read this for any UI a teammate can reach — at work that is all of them.

The server still enforces; the UI is convenience, not the security boundary. The universal frontend
rules live in `skills/frontend-craft/SKILL.md`. On any conflict, SKILL.md wins.

## Auth

- Access token in memory; refresh via an **httpOnly, Secure cookie** — never localStorage for anything an XSS could steal.
- One fetch/Query wrapper does **401 → refresh once → retry, else redirect to login**; every call inherits it instead of reinventing it.
- Route guards gate whole areas and hide actions the user lacks — but the server still enforces; the UI is convenience, not the security boundary.

## Auth & web security

- **Auth:** OIDC **Authorization Code + PKCE** against corp SSO; **never** ship a client secret. Prefer a
  **BFF / httpOnly-cookie** session, or hold tokens **in memory** — **not `localStorage`** (XSS can
  exfiltrate it). Silent refresh; guard protected routes; treat the API's `401/403` as the real boundary.
- **XSS:** rely on framework escaping; avoid `dangerouslySetInnerHTML` on anything untrusted; set a
  **Content-Security-Policy**. **CSRF:** for cookie auth use `SameSite` + a CSRF token. Same-origin or a
  locked **server-side CORS allowlist**. Hand sensitive flows to the `reviewer` agent.
