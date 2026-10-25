# Four-model testing block

This block prepares one matched benign/malicious supplied-log smoke per model: native
`claude-sonnet-5-5`, and structured Codex `gpt-6.1-sol`, `gpt-6-luna`, and `gpt-5.6-terra`.
That is eight planned attempts, with no judge calls. The bounded manifest is
[`multi-model-testing.json`](../../evals/manifests/multi-model-testing.json).
Other cases, model sets, profiles, trial counts, or limits are explicitly refused; add a separately
reviewed concrete seam when another case is needed.

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
existing destination. The plan freezes the plugin source digest, both case/oracle digests, native
runner source digest, Codex adapter source digests, this preparation utility's bytes, model names,
hostnames, transport categories, one trial per case, and explicit command argument arrays.
Validate checks those identities again immediately before execution. Copying a plan to a different
host does not rewrite its absolute paths: prepare a new block on the intended execution host when
paths differ. The plan is a digest-bound record, not a signed authorization artifact.

There are five command arrays: two native per-case invocations and three Codex `--pair log`
invocations, each of which attempts the two cases. The native commands request the exact model
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

`slots` retains every expected case/model/hostname/profile combination and marks missing,
present, or duplicate coverage. `attempts` preserves each recorded state and its problems,
including model, case, runner, plugin, or transport mismatches. A failed check still counts as an
attempt. Retries and unexpected records remain visible and contribute spend; they cannot silently
replace failures. Host runtime and account evidence are retained beside the hostname. Profile
names describe transport categories: native execution-profile metadata remains null when the
runner recorded null, and this utility does not manufacture authentication evidence.

There is no combined model verdict or pooled pass rate. Native results measure the native plugin
path. Structured Codex results measure prompt-injected guidance and scoped file tools; they do
not establish native skill routing, Claude hooks, permission enforcement, or agent delegation.
The report checks saved identity/accounting consistency, not every original artifact or the
correctness of a recorded grader verdict. Retain original traces for independent review.

## Budget and limits

The approved USD 40 total is recorded as a scheduling limit, with `hard_enforcement: false`.
Neither preparation nor reporting reserves money or enforces a provider billing ceiling. The
native USD 0.75 request is an optional CLI stop request, not a hard provider cap. No price estimate
is substituted for missing accounting. Known spend, total spend, and unknown-cost attempt counts
remain distinct; native judge spend must be zero. Codex subscription record costs are normally
null and remain unknown. An inconsistent native known-cost floor is reported rather than used
to erase known component costs.

`ready_for_further_spend` is false when any cost is unknown, coverage is missing, identity/accounting
problems exist, or known total reaches USD 40. Even a true value is only an accounting condition;
it grants no extra attempts beyond this eight-attempt plan. Unknown spend requires reconciliation
or a fresh owner decision before further scheduling. Missing slots are unattempted, not free
successful trials. A crash before creating any recognizable attempt folder cannot be reconstructed
from records; the scheduler must retain its dispatch ledger for that gap.

## Verification and scope

Run `python evals/test_testing_block.py` for no-model CLI/record controls, then Ruff and mypy on
`evals/testing_block.py`. Tests cover preparation/validation, exclusive paths, missing/duplicate
attempts, native schema validation, observed-model mismatches, unknown cost, inconsistent native
cost accounting, and recordless attempts. This is a small offline preparation/accounting utility;
existing runner result formats and executors remain separate. No SDK, dependency, runner rewrite,
authentication path, or generic evaluation framework is added.
