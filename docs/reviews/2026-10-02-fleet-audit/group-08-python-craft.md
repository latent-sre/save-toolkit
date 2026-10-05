# Group 08: python-craft — six-pass audit

Reviewed 2026-10-02 against canonical source `a2d2e57d2de70125dbde002072853e73b788bd8d`; starting audit HEAD `41a6d56c101dd4408c7bc86bb2ca8683884740c2` contains preceding reports. Initial tree clean; the bundle matched the frozen source. Recipient/invoking caller: `/root`; human owner: the user. Assignment complete. The parent objective remains skills before agents, three assets per group, six passes each, with findings committed before continuing.

**Conclusion:** the skill is useful, portable, and substantially more careful than generic Python style guidance. No new defect was confirmed in its instructions. Three Medium defects were reproduced in its outcome measurements: permitted chunk readers can fail, an early successful process exit can bypass checks, and a returned error string can count as a raised exception. Repair those bounded oracles while retaining the existing positive and negative controls.

All nine bundle files were read completely: `SKILL.md` and `references/{environment-and-checks,finding-defects,guard-clause-example,libraries-and-modernization,new-code,refactoring-tools,refactoring,writing-python}.md`. The bundle is 38,523 bytes, 572 lines, approximately 4,925 words; the entrypoint is 52 lines/428 words. There are no executable bundle assets. `[verified]` identifies current source inspection or named local execution; `[sourced]` identifies external documentary evidence; `[unverified]` identifies runtime/model facts not established. Only this scratch report was written by this reviewer. Parent-owned probes used disposable local fixtures; no installation, live service, credential access, product repair, or paid/native campaign occurred.

## Pass 1 — suitability, discovery, and neighboring responsibilities

**Sources:** complete entrypoint; `agents/software-engineer.md:89-105,216-227`; `skills/backend-craft/SKILL.md:75`; all five `discovery-python-*.yaml` specifications; both Python judgment scenarios.

[verified] The skill covers writing, explanation, refactoring, and deliberate modernization across scripts, libraries, tests, CLIs, and services. Explanation/review does not silently authorize edits. It permits justified rewrites without making old implementation structure a compatibility requirement, and permits a no-change conclusion when there is no benefit. HTTP contracts and CLI behavior remain the applicable layer skill's responsibility. The software-engineer consumer explicitly composes these responsibilities and checks support-only stack ownership before editing.

[verified] Positive discovery cases exercise refactoring, modernization, outcome-driven improvement, and explanation. The live production-worker case selects incident investigation instead. The judgment scenarios distinguish shared versus coincidentally identical policy, controlled versus external callers, missing requirements, unjustified layers, streaming/indexing, and explanation-only scope.

**Gap:** these specifications establish intended routing and supplied-state decisions. Neither routing validation nor an exact JSON answer proves consumer discovery, authoring quality, or native-host skill loading. Shared AA-01/EL-01 findings remain separately owned; no duplicate generic grader finding is raised here.

## Pass 2 — technical correctness and current dependency contracts

**Sources:** all eight references; official documentation through Context7; focused upstream files through GitHits. External checks were performed 2026-10-02, after local inspection.

[sourced] The sensitive tool claims are supported:

- Ruff's `fix-only` implies fixing and can suppress remaining diagnostics. Local guidance correctly disables both fixing modes, distinguishes a diff preview from a full lint run, and warns about safe/unsafe overrides (`refactoring-tools.md:42-53`; `finding-defects.md:9-20`). Context7 supplied [Ruff settings](https://docs.astral.sh/ruff/settings/) and [fix safety](https://docs.astral.sh/ruff/linter/#fix-safety). GitHits independently resolved source `9c4279c5`: [args.rs:262-267,843-846](https://github.com/astral-sh/ruff/blob/9c4279c5/crates/ruff/src/args.rs#L262) and [lib.rs:298-310](https://github.com/astral-sh/ruff/blob/9c4279c5/crates/ruff/src/lib.rs#L298) confirm separate flags and `fix || fix_only` application behavior.
- The distinctions between `uv run --locked`, `--frozen`, and `--no-sync` are correct: lock freshness, lock mutation, and environment synchronization are separate (`environment-and-checks.md:26-40`). See [official locking and syncing documentation](https://docs.astral.sh/uv/concepts/projects/sync/).
- Rope's validation, change preview, project application, and cleanup guidance matches [upstream library documentation](https://github.com/python-rope/rope/blob/master/docs/library.rst). GitHits confirmed observer validation and project cleanup in [project.py](https://github.com/python-rope/rope/blob/2bd17a85/rope/base/project.py#L92). LibCST's [codemod testing documentation](https://github.com/Instagram/LibCST/blob/main/docs/source/codemods_tutorial.md) supports positive/no-op checks; preserving concrete syntax does not prove semantic equivalence.
- `TaskGroup` ordinary failures, sibling cancellation, exception groups, and timeout/cancellation behavior agree with [Python 3.14 asyncio documentation](https://docs.python.org/3.14/library/asyncio-task.html). The skill correctly separates grouping from concurrency limits. Tenacity's unbounded/no-wait default is documented and implemented in [its constructor defaults](https://github.com/jd/tenacity/blob/3e58094d/tenacity/__init__.py#L252).

[verified] The before/after guard example preserves the original predicate, including NaN differences; the calculation example preserves the empty Decimal result and keeps its file consumer connected. Library examples are conditional investigation prompts, not unqualified package recommendations. Parser support, target Python floors, actual project dependencies, performance, and installed-tool behavior remain separate checks. No Rope/LibCST/Ruff package was installed or executed for this audit.

## Pass 3 — authority, trust, failure, and recovery

**Sources:** `SKILL.md:16-20,24-35`; `environment-and-checks.md:7-24,39-46`; `libraries-and-modernization.md:9-31`; `refactoring-tools.md:14-27`; `new-code.md:8-12,30-42`; `CONTRIBUTING.md:23-37,56-68`.

[verified] The skill adds no tools or authority. It preserves existing environments and unrelated edits, conditions installs on task authority, and does not infer a package-manager migration from cleanup. It requests direction only for consequential changes not already authorized. Public API research explicitly excludes private source and credentials. Tools preview changes; Rope history supplements recoverable Git state instead of replacing it.

[verified] New-code guidance names partial state and false success as design questions. Refactoring preserves effects, exception identity, resource ownership, cancellation, public imports, and patch seams. An independent requirement can establish that old behavior is a bug; characterization alone cannot authorize a guessed rule. These are valuable protections against both accidental behavior changes and excessive approval loops.

**Gap:** executing imported candidate modules is inherently executable work. The evals explicitly restrict their oracles to disposable reviewed fixtures and disclaim sandboxing. The local audit did not test an arbitrary untrusted repository or host isolation. The skill's no-authority statement and the caller's execution controls should remain distinct.

## Pass 4 — LLM readability, ambiguity, and context cost

**Sources:** entire bundle, especially `SKILL.md:22-52`; `new-code.md:14-26`; `refactoring.md:23-60,99-117`; `writing-python.md:3-54`.

[verified] A short entrypoint directs conditional loading of eight references. It keeps general Python guidance independent of fleet-specific recipes. Tables associate transformations with semantic risks; prose ties improvement to real consumers instead of line count or abstraction count. Language is generally decisive without absolute bans: loops, functions, classes, records, indexing, dependencies, and compatibility adapters are selected by their actual purpose.

[verified] High-value distinctions include truthiness versus absence; iterator creation versus consumption; exact decimal construction; borrowed versus owned resources; normal versus grouped exceptions; and signature/module changes versus external contracts. These should survive any compression.

**Recommendation PY-R01 — Low, high confidence:** prefer deletion of duplicated reporting/check reminders over adding a package catalogue or more mandatory references. `SKILL.md:50-52`, `new-code.md:35-42`, and `refactoring-tools.md:60-65` overlap in general reporting while retaining different interface/tool checks. Consolidate only the generic part and verify those unique checks remain reachable. There is no evidence supporting wholesale restructuring of the 428-word entrypoint.

## Pass 5 — verification coverage and evidentiary limits

**Sources:** all ten `build-python-*.yaml` specifications; both judgment and five discovery specifications; complete `evals/oracles/python-craft/{check_contracts,check_new_code,check_indexed_membership}.py`; relevant calibration cases in `test_python_craft_oracle.py`, `test_python_new_code_probe.py`, and `test_python_index_probe.py`; `evals/README.md:167-235`.

[verified] Coverage is unusually substantive. The effect oracle exhausts 936 bounded integer/None cases. Module moves use fresh processes, configured imports, identity-sensitive registries, keyword-only calls, and public patch points. Calculation/policy probes replace the shared policy to expose remaining copies. The new-code oracle exercises UTF-8 independently of locale, mappings, invalid input, late owned/borrowed read failures, cleanup, shared policy, runnable tests, and measured storage growth. The index oracle checks construction and lookup work, lazy row access, mapping identity, consumed-row retention, and whether candidate tests actually reject linear/quadratic regressions.

[verified] Positive alternatives and named negative artifacts are preserved. Newer oracles distinguish candidate exits from oracle-owned inconclusive measurement; memory/cost claims are explicitly workload-bounded. The README correctly states that the original effect probe proves compatibility plus an edit, not design improvement (`194-210`). That declared limit is not a new defect.

The parent reports the frozen-source baseline under Python 3.14.7: **1,470 passed, 19 skipped, one warning, 2,690 subtests**; specification validation: **192 scenarios, 737 expectations**, both exit 0. Fresh targeted parent probes below reveal three gaps despite that green baseline. They prove bounded oracle behavior, not a whole native trial, deployed Python compatibility, general complexity, or skill uplift. No full-suite rerun was needed.

## Pass 6 — adversarial challenge and prioritized findings

### PY-01 — tiny streaming fixture rejects permitted bounded readers

**Confirmed oracle defect; Medium severity; high confidence.** Evidence: `build-python-generator-lifetime.yaml:7-10,25-28`; `check_contracts.py:120-140,144-175`; `test_python_craft_oracle.py:291-322`; README `186-189`.

**Trigger → impact:** use the existing correct chunked reader with a fixed 64- or 8,192-character read instead of 4. The 12-character test input reaches logical EOF on the first bounded read, so the oracle labels it eager and rejects it. This biases evaluation against a permitted implementation even though large-file processing can remain incremental and bounded. The scenario expressly permits bounded chunk reads.

**[verified] Reproduction:** parent extracted the actual calibration implementations and ran the actual isolated `-I -B` generator oracle. Line iteration and chunk 4 each exited 0 with completion; chunks 64/8192 each exited 1 with the eager diagnostic. Eager `read()` and `list(source)` each remained rejected. Results: `group-08-python-probe-results.json` in the audit scratch directory.

**Smallest fix and verification:** separate tiny-file value/cleanup checks from progress checks on a source larger than supported fixed-buffer positive controls. Calibrate ordinary chunk sizes, including a large fixed buffer, alongside line iteration. Retain rejection of unbounded reads and whole-source materialization. State the tested workload/buffer range; a finite probe cannot establish arbitrary memory bounds. Do not prescribe four-character chunks as the repair.

### PY-02 — candidate SystemExit(0) bypasses the shared contract oracle

**Confirmed oracle defect; Medium severity; high confidence.** Evidence: `check_contracts.py:23-28,425-430`; generator scenario `25-28`. Contrast existing protections in `check_new_code.py:372-380` and `check_indexed_membership.py:376-383`.

**Trigger → impact:** `records.py` raises `SystemExit(0)` during import. The exception terminates the oracle before its assertions and completion output, yet the build check accepts the zero exit. An ordinary misplaced CLI exit in an importable module can therefore masquerade as successful contract verification; no deliberate attack is required. The promised iterator behavior was never checked.

**[verified] Reproduction:** actual generator oracle returned 0 with no completion for `SystemExit(0)`; the valid iterator returned 0 with completion, and `SystemExit(2)` returned 2. This establishes the outcome-check defect only. Direct-load sibling modes expose the same source pattern; they were not all separately replayed.

**Smallest fix and verification:** wrap shared-oracle execution so candidate `SystemExit` becomes a failed check, following the already-calibrated sibling pattern. Include import-time and API/iteration-time exits with zero and nonzero codes plus valid completion. Apply the guard inside fresh child processes as well. A completion receipt can strengthen runner accounting, but does not make the oracle an adversarial sandbox.

### PY-03 — policy parity equates a returned error string with ValueError

**Confirmed oracle defect; Medium severity; high confidence.** Evidence: `build-python-unify-policy.yaml:8-16,182-185`; `check_contracts.py:360-387`; calibration policy at `test_python_craft_oracle.py:92-147`.

**Trigger → impact:** change only the correct policy's `raise ValueError("invalid sku")` to `return "invalid sku"`. Expected invalid outcomes are strings, and `observe()` returns either the normal result or `str(exc)`. It erases the distinction between success and failure, so a contract-breaking return compares equal to the required exception. Downstream callers receive a normal string instead of entering their exception path.

**[verified] Reproduction:** parent seeded the real YAML fixture plus existing correct calibration overrides and the existing CLI-test correction. The actual policy oracle, including six fresh import-order processes and the retained fixture suite, accepted both the correct candidate and the returned-string mutant with exit 0/completion. A wrong-message control failed with exit 1/specification mismatch. Results: `group-08-python-policy-results.json`.

**Smallest fix and verification:** encode returned and raised outcomes with distinct tags, retaining exception class/message checks; alternatively assert exceptions explicitly for invalid cases. Add normal returned error strings as negative controls for each validation category, with valid-result and actual-exception positives. Preserve owner replacement, error identity, alias/registry, input immutability, import-order, and fixture-suite checks.

**Recommendation PY-R02 — Medium, high confidence:** after these oracle repairs, use their existing offline calibration suites before any separately authorized native evaluation. Keep native skill-loading, model identity, task completion, artifact outcomes, and meaningful design benefit as separate evidence. Favor these small executable controls over longer prompt rules. The broad API/tool statements need project/version-specific verification at adoption; this review does not certify every parser or deployment floor.

**Disposition/caller next step:** record PY-01 through PY-03 within the existing AUDIT-001 findings disposition; no new backlog queue or product repair was created. Assemble this report with the two peer reviews and commit group 08 before proceeding. The parent fleet audit remains in progress.

## Central verification

The caller reconciled this report with the group and the [shared verification record](verification.md).
The recorded checks establish their bounded local claims; live-platform and native-model acceptance remain unverified.
