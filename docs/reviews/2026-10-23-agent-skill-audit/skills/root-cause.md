# Root cause skill audit

[verified] Target: `skills/root-cause/SKILL.md` at `8b4f9b785e520944319e04fd8e5018d4545b6800`. No material source-contract finding confirmed. Specification and engineering-quality verdicts: partial. The diagnostic method and caller boundaries are consistent; actual diagnosis quality and model adherence remain unverified.

## Contract assessment

[verified] The method establishes expected behavior from a contract, captures evidence, distinguishes hypotheses and chooses checks by information/cost/safety before permanent remediation. It allows intermittent or unsafe failures to use logs/traces or controlled simulations with stated limits. Unavailable evidence leaves alternatives unresolved; it cannot justify declaring them ruled out or repeatedly guessing fixes.

[verified] Full diagnosis differs explicitly from a bounded evidence lookup: reproduction, tables and remediation are not prerequisites for a requested read. Read-only callers stop at evidence/recommendations. Active impact permits authorized mitigation before cause certainty through incident-investigation; the method grants no execution authority and does not delay stabilization. Embedded commands in evidence remain data.

[verified] Every failed fix or changed symptom triggers reassessment; three failed attempts impose a stop and reopened diagnosis. Software-engineer's three-attempt reminder and unconditional on-demand loading before defect remediation compose with this stronger per-failure rule. The timezone example limits its causal conclusion to same-input/instant replay and local-time source evidence, requires both host-zone checks for repair, and leaves unrelated order effects open.

| Risk | Evidence | Result |
|---|---|---|
| Guess-and-patch instead of diagnosis | Full entrypoint and software-engineer caller | [verified] Causal loop, failed-fix reassessment and stopping rules explicit |
| Heavy diagnosis imposed on simple lookup | Entrypoint and SRE caller | [verified] Bounded-read exception retains evidence limits |
| Diagnostic work blocks urgent mitigation | Entrypoint and incident-investigation caller | [verified] Mitigate-first authority/approval separation retained |
| Familiar signature treated as proof | Worked timezone example and hypothesis rules | [verified] Discriminating replay and scoped inference required |
| Real repair/model correctness | No new diagnosis or live eval | [unverified] Static method cannot establish these outcomes |

## Read manifest and checks

[verified] Full canonical read: `skills/root-cause/SKILL.md` (one file, 73 lines; no supporting bundle files). Bounded supporting reads: `agents/software-engineer.md` 114–134 and on-demand rule search; `agents/sre-assistant.md` 45–68; `skills/incident-investigation/SKILL.md` 70–94 and method-routing search; test/scenario inventory. Earlier full reliability-engineer and Python finding-defects reference reads are reused. Root owns independent evaluation/oracle support, avoiding a duplicate pass.

[verified] `/home/hawkfire/save-toolkit/.venv/bin/python /tmp/audit_current_check.py root-cause` exited 0: generated entrypoint is byte-identical, source diff against target is empty and the bundle link check passes. Existing unchanged-source test baseline is reused. No new tests, reproduction experiments, model calls or runtime checks ran.

[verified] Only this report changed for this item. No canonical source/test/configuration edits, installs, live operations, commits, pushes, repairs or acceptance occurred.

[verified] Root independently read the complete 52-line retry oracle and 96-line `evals/test_root_cause_probe.py`. The oracle checks TimeoutError subclasses, exception identity, bounded attempt counts and recovery; calibration rejects increased budgets, blanket retry removal, swallowed errors and exact-type-only classification. Ordered-load tests reject incomplete/error/child/asynchronous/late skill loads and preserve ordering through follow-up trace merge. These establish bounded behavior and instrumentation, not diagnostic reasoning quality. No new defect was validated.
