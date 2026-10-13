# Frontend trial verification patch

This patch preserves four verification-wiring changes from the private trading-catalog
trial supporting PR #377. It requires that trial's pre-wiring `app/` files; it is not a
standalone app or an installed skill asset. The prototype, database, dependencies, browser
receipts, and raw evaluation traces remain private.

The patch puts the existing CSS regression check into `npm run verify`, alongside typecheck,
lint, component tests, build, and serving checks. The component suite already covers
login/logout heading focus. Both served checks use `BASE_URL`; the README records server
prerequisites and the separate host Playwright MCP handoff. No skill instructions are added.

`file-hashes.json` identifies the original and changed bytes. `after_lf_sha256` also records
the changed text with CRLF normalized to LF. From a directory containing the original `app/`,
use `git apply --check --ignore-space-change <path-to-verification-wiring.patch>`, then the
same command without `--check`. The current private app already contains these changes.

[verified] On 2026-10-13, the patch applied to copies matching all four recorded original
hashes and reproduced all four changed files after newline normalization. The changed app's
`npm run verify` exited 0: typecheck, lint, build, 16 component tests, six serving checks, and
the CSS check passed. One runtime-config check was skipped because the fixture has no such
endpoint. Browser verification was not repeated for command wiring.

Retain this patch while the craft trial's CSS and focus regression evidence is needed for
the guidance review. The invoking human owner decides its disposition when that review closes.
