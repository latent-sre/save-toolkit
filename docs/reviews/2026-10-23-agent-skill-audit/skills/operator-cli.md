# Operator CLI skill audit

[verified] Target: `skills/operator-cli/SKILL.md` at `8b4f9b785e520944319e04fd8e5018d4545b6800`. No material source-contract finding confirmed. Specification and engineering-quality verdicts: partial, because source and deterministic evaluation coverage do not establish a generated CLI's full runtime contract.

## Contract assessment

[verified] The 88-line skill composes with existing consumer contracts instead of replacing exit codes or schemas. It separates machine results from diagnostics, defines skipped/failed/unknown outcomes, bounds work, requires real dry runs and exact-set confirmation, and preserves unknown effects until readback. Interruption stops scheduling, retains completed effects and releases only owned resources. Production authority remains with the release owner. Software-engineer's on-demand skill rule matches the described lane; existing operational execution routes away from CLI design.

[verified] No contradiction found between confirmation, dry-run planning and production authorization. Receipts and readback protect retries, while explicit target API effect/idempotency discovery prevents assuming all failures mean no effect. Existing schema/exit conventions take precedence over the suggested new contract. Read-only commands explicitly avoid irrelevant effect controls. These are actionable implementation requirements, not claims that static guidance enforces them.

## Evidence coverage

| Requirement | Evidence | Result |
|---|---|---|
| Design routing vs running production commands | Both discovery fixtures and software-engineer caller | [verified] Expected lane encoded; live routing unverified |
| Zero effects on dry run, noninteractive confirmation, partial outcomes | Full safe-requeue scenario and oracle | [verified] Exact calls, exits and JSON item set checked |
| Timeout-after-effect and uncertain readback | Probe-owned faulty client and oracle | [verified] No replay; succeeded or unknown only; stop at unresolved effect |
| Interrupt result and owned-resource cleanup | Oracle injects in-process SIGINT/SIGTERM after effect | [verified] Bounded outcome/exit/lock assertions; no real external cancellation assurance |
| Concurrency, target drift, receipts across runs, secret output, early pipe close | Source requirements; no corresponding checks in reviewed oracle | [unverified] Coverage gaps, not demonstrated source defects |

[verified] Full canonical read: `skills/operator-cli/SKILL.md` (one file, 88 lines). Full supporting reads: both `evals/scenarios/discovery-operator-cli-*.yaml`; `evals/build-scenarios/build-operator-cli-safe-requeue.yaml`; `evals/oracles/operator-cli/check_requeue.py`. Bounded reads: `agents/software-engineer.md` 195–235; `evals/test_operator_cli_oracle.py` 165–220 (mutation/calibration tail); relevant caller/test inventory searches. Stack-profile entrypoint read as shared guidance. No claim of full calibration-suite source review.

[sourced] The coordinator independently read the complete 169-line oracle and build scenario, and calibration lines 145–220. Mutants cover replay, incorrect failure/exit classification, stdout contamination, dry-run effects, interrupted result sets and lock cleanup. These checks substantiate the bounded contract; no additional defect was validated.

## Verification and limits

[verified] `diff -u skills/operator-cli/SKILL.md .github/skills/operator-cli/SKILL.md` produced no difference. `/home/hawkfire/save-toolkit/.venv/bin/python /tmp/audit_bundle_check.py` exited 0: source unchanged from target, bundle links resolve, one-file inventory confirmed. The unchanged-source coordinator test baseline is reused; no new tests, live model calls or host actions ran. Full suite success does not fill the runtime gaps above.

[verified] Only this report changed for this item. No canonical/test/configuration edits, installations, commits, pushes, deployment or repairs were performed. Reviewable guidance is assessed; human acceptance and live implementation verification remain separate.
