# Codex/Terra managed response smoke

- **Date:** 2026-08-11
- **Target:** `gpt-5.6-terra`, medium reasoning, requested through one managed subagent
- **Managed-smoke source HEAD:** `6d90943664ee0305726cc0ed8feb6b5d9a8e7f68`
- **Calibration base:** immutable commit `1a95b72ae5f3d9ecca2ec396f63f5156a8bbfa08`
- **Calibration evidence state:** provisional mutable-worktree evidence; the tested surface is bound by
  the file hashes below and must be rerun after the corrective commit
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

The first calibration repair separated harmless wording variants from substantive omissions and
added the missing log-read obligation. Immutable review of commit `1a95b72` then reproduced two
material false passes: two different revisions at 50% were accepted, and command words could borrow
`--to-revisions` operands from later prose. Further adversarial fixtures exposed duplicated targets,
missing service positionals, malformed assignments, duplicate flags, swapped direction, a shared
wrong service, extra traffic commands, invalid literal placeholders, and mismatched region/project
context.

The final repair replaces natural-language direction inference with one closed
`cloud_run_rollback_packet` contract. The scenario now asks for exactly one fenced JSON object with
only `forward_command` and `inverse_command`. Both values must be single-line, directly runnable
commands using exact synthetic values: service `checkout`, previous revision
`checkout-00001-good`, failed revision `checkout-00002-fail`, region `us-central1`, project
`example-project`, and 100% traffic. The parser rejects duplicate/extra JSON fields, any additional
fence or traffic command outside the packet, shell controls or extra argv, wrong case, missing or
duplicate flags, direction swaps, and mismatched identities. Persisted grader details never echo
the command operands. The routing target and canonical skill are unchanged; the prompt changed only
to define this deterministic output contract. Prompt-echo and advisory-only regressions remain
active.

Focused post-change evidence:

- `[verified]` `python evals/test_graders.py` — `215/215` checks passed.
- `[verified]` `python evals/test_run_codex_routing.py` — `18/18` tests passed.
- `[verified]` `python evals/test_codex_bootstrap.py` — thirty tests passed, with two expected
  Windows symlink-privilege skips (thirty-two tests run).
- `[verified]` `python evals/run_codex_routing.py` — manifest valid, nineteen scenarios and
  forty-eight planned trials.
- `[verified]` `python scripts/gate_a.py` — `38/38` structural steps passed.

Exact tested mutable surface (`path`, byte size, SHA-256):

- `evals/graders.py`, `15149`,
  `9389c4181816d0872b7c2dcb9021f038677a1ac0d62fd87c03d945413fd174a9`
- `evals/run_codex_routing.py`, `24889`,
  `80e7b7391b6d977a54450a256fb8b34acc705d757aa30d9b84072570cf0272d6`
- `evals/scenarios/discovery-gcp-ops-cloud-run-startup.yaml`, `1767`,
  `3d3507272fbe0e6d3ee28bf51ad33cf2d913c5afb2e69a79881fba5ce29712fd`
- `evals/conformance/codex-terra-routing-v1.json`, `7495`,
  `d5c7c06902fe131448f6c7fb5d0e03180ccaff8eab4e4201f41315115e127887`
- `evals/conformance/codex-terra-evaluator-v1.json`, `1173`,
  `0f27b464607d2bd12c68f148abbeb26736954b37177522cf6bff276125266acc`
- `evals/test_graders.py`, `56669`,
  `f492e9f42156f43a9679bb9d2e3af76deaa1dea5a6d076fdda913a45e0a99034`
- `evals/test_run_codex_routing.py`, `18540`,
  `6e3a5c4b624fc0a5f1e98767ff9b6a65709b3f6d484f91c32bfb0c4f152d7976`

No second live model call was made. A future live retest remains a separately authorized effect and
cannot close the current host's authenticated-canary prerequisites.

This calibration changes the scenario and both hash-bound Terra manifests. The earlier pre-canary
packet remains valid only for its recorded historical bytes; it cannot authorize these changed
bytes. Any future canary decision must bind a committed SHA, a refreshed external evaluator-manifest
digest, and a fresh independent review.
