# Codex/Terra managed response smoke

- **Date:** 2026-08-11
- **Target:** `gpt-5.6-terra`, medium reasoning, requested through one managed subagent
- **Repository HEAD:** `6d90943664ee0305726cc0ed8feb6b5d9a8e7f68`
- **Authority:** response-only calibration evidence; not a ROUTE-001 canary, campaign, routing result,
  baseline, release, or model-resolution receipt

## Observation

The owner authorized one bounded response smoke using the fixed Cloud Run startup prompt. The
managed runtime accepted the requested model setting, but it exposed no independent resolved-model
receipt, installed-skill activation receipt, or repository-harness trace. No tool or delegation
receipt surfaced. The response therefore measures answer behavior only.

The answer supplied a read-only service/revision/log investigation, used explicit project and region
placeholders, compared the failed revision with a last-known-good revision, and correctly described
binding `0.0.0.0` on the injected `PORT` rather than loopback. Those are semantic equivalents of the
scenario's old literal `checkout`, `0.0.0.0:$PORT`, and `127.0.0.1` needles.

The answer did not supply `gcloud config list`, the exact human-run
`gcloud run services update-traffic ... --to-revisions ...` forward and inverse commands, the Tier 2
classification, the accountable human release owner, or error-rate verification. Those are
substantive omissions under the canonical `gcp-ops` skill, not grader wording differences.

## Calibration

The old grader conflated the harmless representation differences with the substantive omissions and
also failed to require a log-read command. A red-first regression added one behavior-complete variant
using `SERVICE`, `0.0.0.0` plus `PORT`, and `loopback`; the old grader rejected it, producing
`167/168` checks. A paired advisory-only fixture representing the managed response remains rejected.
A second red-first check required a bounded literal-occurrence grader and failed with a missing API
before implementation. Independent review then found that separate occurrence counts still allowed
the same forward command twice; its duplicate-forward regression failed at `177/178` before the
grader was replaced with a command-bound distinct-target check. A follow-up target-normalization
regression failed at `181/182` when the same target used different percentages, then passed after
angle-bracket and assignment-weight normalization.

The repair keeps grading linear and does not change the prompt, routing target, skill description, or
canonical skill. It now accepts both canonical log-read forms, both loopback representations, and
arbitrary revision names while requiring two `update-traffic --to-revisions` commands with distinct
traffic targets plus an inverse-action marker. The existing governance and verification obligations
remain. The prompt-only and whitespace-normalized echo regressions remain active.

Focused post-change evidence:

- `[verified]` `python evals/test_graders.py` — `182/182` checks passed.
- `[verified]` `python evals/test_run_codex_routing.py` — `18/18` tests passed.
- `[verified]` `python evals/test_codex_bootstrap.py` — `32/32` tests passed, with two expected
  Windows symlink-privilege skips.
- `[verified]` `python evals/run_codex_routing.py` — manifest valid, nineteen scenarios and
  forty-eight planned trials.
- `[verified]` `python scripts/gate_a.py` — `38/38` structural steps passed.

No second live model call was made. A future live retest remains a separately authorized effect and
cannot close the current host's authenticated-canary prerequisites.

This calibration changes the scenario and both hash-bound Terra manifests. The earlier pre-canary
packet remains valid only for its recorded historical bytes; it cannot authorize these changed
bytes. Any future canary decision must bind a committed SHA, a refreshed external evaluator-manifest
digest, and a fresh independent review.
