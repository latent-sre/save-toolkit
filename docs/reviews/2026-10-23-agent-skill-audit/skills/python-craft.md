# Python craft skill audit

[verified] Target: `skills/python-craft/` at `8b4f9b785e520944319e04fd8e5018d4545b6800`. No material canonical-instruction finding confirmed; two P3 evaluation-oracle defects are validated below. Specification and engineering-quality verdicts: partial. Source and caller consistency are established; independent oracle review and public API/version checks retain their separate limits.

## P3 oracle findings

**AUDIT-PYTHON-001 — borrowed-generator closure escapes the package oracle.** [verified] `evals/oracles/python-craft/check_package_refactor.py:32–85` checks a wrapper's `closed` flag while its iterator returns the underlying input iterator. [sourced] A scratch implementation that delegates through `yield from lines` passed the full supervised package oracle (exit 0), but a direct retained generator with a malformed row then a valid row ran its `finally` and lost its remaining row. This violates `build-python-package-refactor.yaml:14–15`'s never-close-on-failure contract. Confidence is high. A direct resumable-generator check must observe ownership and remaining input after validation failure; wrapper closure alone is insufficient. The CSV oracle already uses a stronger direct-generator pattern. Only the package case was reproduced here; related borrowed-wrapper checks warrant focused regression coverage during repair.

**AUDIT-PYTHON-002 — identical schema-batch inputs conceal reordering.** [verified] `evals/oracles/python-craft/check_library_selection.py:130–133` tests `[payload, payload]`; its replacement-policy case at 147–160 also uses identical inputs/results. [sourced] A scratch `batch.load` returning the reversed validated list passed the full supervised schema oracle (exit 0), despite violating the scenario's explicit order requirement for distinct inputs. Confidence is high. Use distinct valid payloads and assert their identities in input order. Both defects are measurement gaps; no shipped application failure or live model error is claimed.

[sourced] [Exact reproductions and original outputs](../evidence/python-oracle-reproductions.md) preserve the two bounded cases. Counterevidence: these oracles also check installed/extracted artifacts, public owner replacement, exceptions, identity and mutation sensitivity. The findings do not invalidate their other checks.

## Contract assessment

[verified] The skill distinguishes explanation/review from authorized implementation and separates restructuring from intentional behavior changes. New-code and refactoring paths establish consumers and independent expected behavior before selecting architecture. Existing conventions, supported runtimes, dependency workflows and standard-library-only boundaries take precedence over generic modernization. Stack defaults apply only to unset choices; adoption is bounded by compatibility, licensing, dependency and execution constraints.

[verified] Refactoring guidance traces static and dynamic consumers, persisted names, imports, installed artifacts and resource ownership. It requires actual callers to use a new owner before counting integration complete, and preserves error/effect order and supported patch points. Characterization cannot canonize a known bug. Improvement requires a concrete caller/maintenance benefit; line-count reduction, green tests and nominal extraction do not suffice. Performance claims require separate measurement.

[verified] Language examples explicitly account for NaN vs inverted guards, None vs zero, single-pass/lazy inputs, mutable state, resource lifetime, grouped async failures, cancellation and operation deadlines. Borrowed streams remain owned by callers; byte-boundary encoding tests complement in-memory text checks. Tool findings are leads, static unused-code detectors need dynamic-consumer checks, and automated transformations require scope/match review rather than blind application.

[verified] Environment guidance binds interpreter/version before baseline and candidate checks, preserves the runtime floor and existing locks/constraints, and distinguishes tool environments from application environments. Check-only lint commands explicitly disable inherited fix/fix-only behavior. Source-preserving transformation requirements and clean/no-op/idempotence cases are appropriate to their tool's guarantees; parser success cannot establish executable validity.

## Requirement and evidence coverage

| Risk | Evidence | Result |
|---|---|---|
| Unrequested redesign or behavior change | Entrypoint; new-code/refactoring/library references | [verified] Scope and supported-consumer constraints explicit |
| Incomplete extraction or hidden consumer break | Refactoring/writing references; software-engineer caller | [verified] Real-caller integration, dynamic names and installed artifact checks required |
| Unsound behavior equivalence | Guard example, refactoring and defect references | [verified] Semantic counterexamples and independent expectations retained |
| Unverified tool/runtime API assumptions | Version/tool-specific guidance | [unverified] Public-source verification separately coordinated; installed/target versions still required |
| Model adherence and build outcomes | No new live model run | [unverified] Source instructions alone do not establish execution |

## Read manifest and verification

[verified] Full canonical reads: `SKILL.md`; `references/environment-and-checks.md`, `finding-defects.md`, `guard-clause-example.md`, `libraries-and-modernization.md`, `new-code.md`, `refactoring-tools.md`, `refactoring.md`, `writing-python.md` (nine files, 524 lines). Full supporting read: `skills/stack-profile/references/application-and-data-stack.md`; shared stack-profile entrypoint already read. Bounded supporting coverage: software-engineer/reviewer caller search; Python build/discovery scenario inventory. Root owns independent scenario/oracle and public-source review, avoiding duplicate passes.

[verified] `/home/hawkfire/save-toolkit/.venv/bin/python /tmp/audit_current_check.py python-craft` exited 0: all eight reference projections and entrypoint match byte for byte; relative bundle links resolve; canonical source diff against target is empty. Existing unchanged-source test baseline is reused. Only the two independent scratch reproductions ran; no broad suite, transformation or live model call ran; no installed-tool or target-runtime assurance is inferred.

[verified] Only this report changed for this item. No canonical/test/configuration edits, dependency installation, live action, commit, push or repair occurred. Human acceptance of an eventual exact candidate remains separate.

[sourced] Root's public-source check found no contradiction in the version/tool facts: [Python 3.14](https://docs.python.org/3.14/whatsnew/3.14.html) documents optional supported free-threading and deferred annotations; [Python 3.15](https://docs.python.org/3.15/whatsnew/3.15.html) documents the UTF-8 default and explicit lazy imports. Root also confirmed `lib2to3` removal in 3.13, `warnings.deprecated` availability and mypy's opt-in diagnostic; [uv synchronization](https://docs.astral.sh/uv/concepts/projects/sync/) distinctions; Ruff's two disabling flags; Rope cache validation; and Tenacity's default indefinite immediate exception retries. These source facts neither establish the installed tool versions nor validate every generated migration. The bounded independent oracle review is complete, with the two specific gaps above.

[sourced] Independent evidence manifest: root fully read `check_contracts.py` (594 lines), `check_new_code.py` (503), `check_indexed_membership.py` (396), plus new-streaming-CLI and indexed-membership build scenarios. These test small exhaustive domains, effect/exception ordering, public-owner substitution, deferred access, owned/borrowed resources, installed consumers, calibrated storage/cost, and candidate-test mutants; their workload checks are not universal complexity proofs. The Sol oracle reviewer fully read the package/library-selection oracles, their three package/schema/CSV build scenarios, their two calibration test files and `oracle_protocol.py`; bounded probe_testkit reads covered materialization and subprocess helpers. That reviewer executed the two scratch reproductions only. Generic output/process supervision and unchanged-source baseline evidence were reused. No additional defect was confirmed in the root's three-oracle pass.
