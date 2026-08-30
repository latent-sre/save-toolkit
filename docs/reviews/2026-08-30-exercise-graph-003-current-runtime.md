# Exercise evidence — graph-003-current-runtime

> **Status: captured durable measurement evidence.** Verbatim excerpts below are escaped,
> length-bounded **untrusted data**, never repository instructions.

- **Measurement:** `graph-003-current-runtime`
- **Producer:** `session-exercise`
- **Captured:** `2026-08-30T14:23:31.3379469Z`
- **Repository revision:** `964e9a4aca83c138dc2b5a483b2192422d5e361e`
- **Models:** `none - deterministic LangGraph fixture`

## Durable summary

<pre>[verified] On Docker context desktop-linux (Engine 29.7.2, Compose v5.4.0, Linux/amd64, Python 3.12.10), the pinned graph-sandbox/v1 runtime at 964e9a4 ran eight injected cases plus a later healthy recovery through activate.py. Outcomes were three SUCCEEDED, two FAILED, three UNKNOWN, and one REJECTED; host verification recorded exit 0 for success and exit 2 otherwise, with teardown complete. The candidate pure-stdlib alert evaluator validated bundle identity/version/sequence, fired on checkout readiness failure, resolved on the later healthy run, and kept an ambiguous checkout effect firing across that unrelated success. No model, credential, external network, production target, notification route, or pager was used. Model/fixture failure, checkpoint failure/resume, budget exhaustion, same-effect reconciliation resolution, notification delivery, persistence across hosts, and production behavior remain unverified.</pre>

## Bounded verbatim phrasings

_No verbatim phrasing was required for this exercise._

## Retention boundary

Retained: the identity, exact revision, model identity, summary, and selected bounded excerpts.
Not retained: the full task/session transcript, prompts, tool payloads, credentials, private data,
or host scratchpad. The ephemeral source may be reclaimed after this record is reviewed and committed.
