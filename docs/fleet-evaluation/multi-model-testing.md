# Four-model testing block

This block prepares selected admitted cases for native `claude-sonnet-5-5` and structured Codex
`gpt-6.1-sol`, `gpt-6-luna`, and `gpt-5.6-terra`, without executing them. The default
[`multi-model-testing.json`](../../evals/manifests/multi-model-testing.json) still selects the
matched supplied-log smoke: eight planned attempts, with no judge calls.

Selection is bounded by the Codex adapter's existing fifteen admitted cases. Select complete
benign/malicious pairs for `repository`, `repository-policy`, `log`, `log-role`, `helper`, or
`helper-relayed-owner`; both `build-gcp01-startup-a` and `build-gcp01-startup-b`; or the singleton
`build-reliability-engineer-proportionate-options`. Multiple groups may be combined. Pair arms
are normalized to benign/malicious or startup-a/startup-b order and kept adjacent, without
omitting a selected case. Unsupported cases, incomplete pairs, duplicate IDs, different model/profile
rows, judged cases, and trial counts outside 1..3 are refused.

A manifest declares a uniform `trials_per_case` from one to three and an `attempt_limit` equal to
selected cases × four models × trials. `approved_total_usd` must be a positive finite number;
its presence records budget data and grants no execution authority. The
[`wp10-model-testing.json`](../../evals/manifests/wp10-model-testing.json) example selects ordinary
log, log-role, and reliability for three trials: sixty slots and forty-two command arrays. It is
an example for future approval, not the independently frozen live campaign or authorization for
sixty calls. Unequal per-case trial counts and model upgrades need a separately reviewed seam.

## Prepare and validate offline

Use the project Python 3.14 environment. Supply the exact hostname expected in each transport's
saved host identity; use the same hostname twice if both run on the same host. Neither command
starts a model, examines authentication, discovers installed CLIs, or executes fixture tools.
Canonical plugin hashing may run read-only `git ls-files`; a previously staged plugin image needs
no Git subprocess. Candidate paths and output/input paths must not contain `..` or symlinks.

```bash
.venv/bin/python evals/testing_block.py prepare \
  --candidate-root /absolute/path/to/candidate \
  --native-host native-hostname --codex-host codex-hostname \
  --out .eval-runs/multi-model-smoke
.venv/bin/python evals/testing_block.py validate .eval-runs/multi-model-smoke
```

The fresh output directory contains `plan.json` and `case-bindings.json`. Preparation refuses any
existing destination. Pass `--manifest evals/manifests/wp10-model-testing.json` to prepare the
selected-case example instead of the default. The plan freezes the plugin source digest, all selected case/oracle digests, native
runner source digest, Codex adapter source digests, this preparation utility's bytes, model names,
hostnames, transport categories, every numbered trial slot, and explicit command argument arrays.
Validate checks those identities again immediately before execution. Copying a plan to a different
host does not rewrite its absolute paths: prepare a new block on the intended execution host when
paths differ. The plan is a digest-bound record, not a signed authorization artifact.

The default has five command arrays: two native per-case invocations and three Codex `--pair log`
invocations, each of which attempts the two cases. Selected groups produce one native command per
case/trial and one Codex pair or singleton command per model/group/trial. Native `--run-offset`
numbers trial slots from one without replacing earlier runs. Repeated Codex commands use exclusive
`results/<model>/trial-N/<group>/` destinations, while the default single-pair/single-trial smoke
keeps its original paths. The native commands request the exact model
rather than the moving `sonnet` alias. Each native invocation requests
`--max-invocation-usd 0.75`; a CLI response can overrun this request. Codex commands retain the
existing scoped fixture-tool approval flag and existing wall/tool-call limits. Preparation does
not execute these arrays; the owner-controlled scheduler owns launch authorization, available
credentials, serial scheduling, spend reconciliation, and stop decisions. A failed Codex first
case may prevent its second case from starting; that slot remains visibly missing.

The native runner has no case-binding-file option. Validate binds its current case bytes before
launch, and the report checks each saved native record's case digest afterward. The Codex adapter
consumes the emitted binding file directly. The native runner must include the optional
`--max-invocation-usd` interface before these commands are executed.

## Read saved results

Keep the original runner outputs under the block's `results/` directory as the generated command
arrays request, then write a new report file:

```bash
.venv/bin/python evals/testing_block.py report .eval-runs/multi-model-smoke \
  --records .eval-runs/multi-model-smoke/results \
  --out .eval-runs/multi-model-smoke/report.json
```

Reporting is read-only over saved evidence and does not regrade, call a judge, consult current
candidate bytes, or discover the current host. It refuses to overwrite a report. Native records
validate through `RecordV1`; Codex records stay `codex-record-v1`, with saved session model/thread
identity checked through the adapter's existing verifier and its recorded session digest. Records
with malformed identities remain counted attempts with explicit problems. Recordless native run,
history, and in-progress folders and Codex case folders also count, with unknown result/cost; a
path-derived slot binding is marked as such and establishes no measured identity.

`slots` retains every expected case/model/hostname/profile/trial combination and marks missing,
present, or duplicate coverage. `attempts` preserves each recorded state and its problems,
including model, case, runner, plugin, or transport mismatches. A failed check still counts as an
attempt. Retries and unexpected records remain visible and contribute spend; they cannot silently
replace failures. Host runtime and account evidence are retained beside the hostname. Profile
names describe transport categories: native execution-profile metadata remains null when the
runner recorded null, and this utility does not manufacture authentication evidence. Native trial
numbers come from the record's slot. Codex records have no trial field, so repeated trials bind
through their retained `trial-N` directory and are marked `trial_binding_from_path`; retain this
layout when moving bundles. A repeated record without a unique trial location is unplanned.
Older default plans without trial fields remain reportable as trial one; validating a historical
plan for new execution still requires matching all frozen source bytes.

Reliability and GCP slots carry `semantic_review_required`. Their recorded `state` is preserved,
and `semantic_review_status: required_not_assessed` makes the outstanding review explicit even
when mechanical checks report PASS. This utility does not perform semantic review, infer human
acceptance, or clear that requirement from recorded mechanical success.

There is no combined model verdict or pooled pass rate. Native results measure the native plugin
path. Structured Codex results measure prompt-injected guidance and scoped file tools; they do
not establish native skill routing, Claude hooks, permission enforcement, or agent delegation.
The report checks saved identity/accounting consistency, not every original artifact or the
correctness of a recorded grader verdict. Retain original traces for independent review.

## Separate WP04 subscription profile

[sourced] `codex_probe.py --wp04-fixture` admits one previously prepared indexed-v6 or indexed-v7
WP04 fixture at a time. This selector is separate from the fifteen-case testing block above;
it neither expands that block's manifests nor schedules extra models. The fixture may be YAML
or gzip-compressed YAML. Its ID and case digest must match the operator's existing binding file.
Only the five WP04 case IDs, `sre-assistant`, files-only fixtures and the exact recorded checks
are admitted. Historical v6 keeps its fence check; v7 keeps the strict submission check.

```bash
.venv/bin/python evals/codex_probe.py \
  --wp04-fixture /absolute/path/wp04-itbench-7-indexed-v6.yaml.gz \
  --candidate-root /absolute/path/to/candidate \
  --expect-plugin-digest <frozen-plugin-sha256> \
  --case-bindings /absolute/path/case-bindings.json \
  --out .eval-runs/wp04-sol-case7-trial1 \
  --model gpt-6.1-sol --timeout 900 --max-calls 64 --approve-fixture-tools
```

[sourced] A binding file is a JSON list of `id` and `case_sha256` objects. Reuse a verified
historical native record's case binding for an unchanged fixture, or compute it offline using
`codex_wp04.load_wp04_case` and `probe.fingerprints.case_digest`. Never load several expanded
WP04 fixtures together: case 7 alone is about 942 MB of serialized YAML. Verify fixture provenance,
the observation/answer boundary, and the source-bound selection before launching a model.

[sourced] The `wp04-readonly-v1` profile requires ChatGPT subscription authentication and refuses
API-key authentication. It supplies canonical role guidance in the prompt, stages skill references
as read-only files, and exposes only an exact allowlist through the fixture MCP server:

- `read_file` returns a complete small file, including skill guidance.
- `list_files` lists scoped allowlist names with explicit pagination.
- `search_files` performs case-sensitive literal searches, with bounded snippets and character
  locators. Follow `next_cursor` until `complete`, including empty partial pages; keep the query
  unchanged. It offers no regular-expression dialect or implicit current-state selection.
- `read_slice` pages exact Unicode characters while preserving newlines. Follow `next_offset`
  until `eof` when full content is required. Offsets are characters, not source line numbers.

[sourced] The prompt names `observations/index.json` instead of dumping thousands of fixture paths.
All admitted observations remain accessible. Every call/result is bound to a separate server
receipt and corroborated against the Codex session inventory. Search snippets do not establish
full record coverage. The file allowlist is an application boundary, not an OS sandbox. Native
shell, web, edits and delegation are prohibited; native Claude hooks/routing are not measured.
The WP04 process uses the shared runner's process-tree ownership for timeout/interruption cleanup.

[sourced] The expected manual-review INCONCLUSIVE is complete instrument evidence, not a semantic
pass. Other incomplete checks still stop scheduling. Native turn counts and Codex fixture-call
limits are different quantities. Compare the saved sources and conclusions, disclose the transport
difference, and retain all attempts. Keep subscription usage and dollar cost separate: a null dollar
cost is unknown, not zero. Authorization must bound attempts and resource use; no API fallback,
automatic retry, judge call or candidate promotion follows from preparing this profile.

## Budget and limits

The manifest's positive dollar total (USD 40 by default) is recorded as a scheduling limit,
with `hard_enforcement: false`. Changing that number never authorizes calls.
Neither preparation nor reporting reserves money or enforces a provider billing ceiling. The
native USD 0.75 request is an optional CLI stop request, not a hard provider cap. No price estimate
is substituted for missing accounting. Known spend, total spend, and unknown-cost attempt counts
remain distinct; native judge spend must be zero. Codex subscription record costs are normally
null and remain unknown. An inconsistent native known-cost floor is reported rather than used
to erase known component costs.

`ready_for_further_spend` is false when any cost is unknown, coverage is missing, identity/accounting
problems exist, or known total reaches the manifest's dollar limit. Even a true value is only an
accounting condition; it grants no calls or extra attempts beyond the separately authorized plan. Unknown spend requires reconciliation
or a fresh owner decision before further scheduling. Missing slots are unattempted, not free
successful trials. A crash before creating any recognizable attempt folder cannot be reconstructed
from records; the scheduler must retain its dispatch ledger for that gap.

## Verification and scope

Run `python evals/test_testing_block.py` for no-model CLI/record controls, then Ruff and mypy on
`evals/testing_block.py`. Tests cover preparation/validation, exclusive paths, missing/duplicate
attempts, native schema validation, observed-model mismatches, unknown cost, inconsistent native
cost accounting, recordless attempts, complete group selection, three-trial command offsets,
legacy plan reading, and semantic-review markers. This is a bounded offline preparation/accounting utility;
existing runner result formats and executors remain separate. No SDK, dependency, runner rewrite,
authentication path, or generic evaluation framework is added.
