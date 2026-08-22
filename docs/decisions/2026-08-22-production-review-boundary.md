# Production-only exact-SHA review boundary

**Status:** accepted 2026-08-22; disposes `REVIEW-001`.

## Decision

- Ordinary merges require no independent approval or automatic re-review after each push. Known
  P0/P1 findings still need an evidence-bound disposition before merge.
- `Protect main` keeps zero required approvals. Conversation resolution stays off: the solo
  maintainer tested it and found the workflow too restrictive.
- No callable exact-SHA review workflow will be built.
- A production deployment of a new artifact requires independent review of the exact candidate SHA.
  `production-change-gate` owns that check. Non-production releases and non-deployment production
  actions do not inherit it.

## Why

PR #103 demonstrated the real failure: it merged with six unresolved review threads, four still
current at the final SHA. Conversation resolution would prevent an accidental repeat, but a pull
request author can resolve their own threads, so it is acknowledgment rather than independent
approval. Requiring one approval would deadlock this solo-maintainer repository because an author
cannot approve their own pull request, and GitHub Copilot reviews do not count toward required
approvals. *[sourced: GitHub Docs, approving a pull request with required reviews; reviewed
2026-08-22]*

The rejected exact-SHA status workflow would add reviewer identity, timeout, privileged-status, and
recovery machinery to every pull request. That cost is not justified when the requirement matters
only at the production deployment boundary.

## Reopen trigger

Reconsider merge-time enforcement only if the repository gains another dependable maintainer or a
trusted review App whose approval can be required without blocking solo work. A desire for more
checklist coverage by itself is not a reopen trigger.

## Sources

- [GitHub: approving a pull request with required reviews](https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/approving-a-pull-request-with-required-reviews)
- [GitHub: about pull request reviews](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/about-pull-request-reviews)
- [PR #103](https://github.com/latent-sre/save-toolkit/pull/103)
