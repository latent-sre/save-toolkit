# Auth (serving side)

Read this when the service authenticates or authorizes a caller. The server is the source of truth
for auth — a frontend's checks are convenience; this is the boundary.

The universal backend rules live in `skills/backend-craft/SKILL.md`. On any conflict, SKILL.md wins.

## Auth (serving side)

The server is the source of truth for auth — the frontend's checks are convenience; this is the boundary.

- **Validate a token on every non-public route.** Short-lived access token (JWT or opaque server session), paired with the frontend's **httpOnly, Secure refresh cookie** for the refresh flow.
- **Hash passwords with argon2id** (or bcrypt) — never store or log credentials, never roll your own crypto.
- **Authz by scope/role**, checked at the handler — "authenticated" is not "authorized." Deny by default.
- Tokens expire; support refresh and **revocation** (a logout or a leaked token must be killable). Rate-limit auth endpoints hardest.
- **Machine callers too**: scripts and services calling your API get scoped, revocable API keys or client-credentials — logged like any user, never a shared admin token pasted into a script.

- **Authorize every resource on the server.** Check that the caller may act on this object, not merely
  that the caller is logged in; missing that object check is broken object-level authorization.
- A `reviewer` security pass is required for changes to authentication, authorization, token
  handling, cryptography, or other untrusted-input boundaries.
