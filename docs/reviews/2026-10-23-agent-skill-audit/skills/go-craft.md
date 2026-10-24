# Go craft skill audit

[verified] Target: `skills/go-craft/` at `8b4f9b785e520944319e04fd8e5018d4545b6800`, inspected on 2026-10-23. The sole tracked file, `SKILL.md` (63 lines), was read completely. Its workspace projection is byte-identical. No audited source changed.

## Conclusion and findings

[verified] **No new material source defect validated.** The skill gives a bounded language-level method and composes with existing API/CLI ownership. **Specification verdict: coherent. Engineering verdict: partial assurance.** Current model benefit and language-specific execution quality remain unmeasured, as the roadmap already states.

[sourced] Shared **P3 AUDIT-API-001** still limits the Go HTTP build: its `ReadHeaderTimeout` oracle accepts a comment or unused zero-valued server. The [API audit](api-craft.md) contains the source trace and bounded reproduction. This report does not duplicate that finding or treat it as a defect in Go craft's concurrency instructions.

## Contract coverage

| Contract | Evidence and assessment |
|---|---|
| Routing and composition | [verified] [SKILL.md](../../../../skills/go-craft/SKILL.md), lines 3–16, covers Go services, CLIs, libraries and workers, including upgrades, while excluding runtime-only incidents. [Software-engineer](../../../../agents/software-engineer.md), line 219, explicitly requires it for Go changes. [Operator CLI](../../../../skills/operator-cli/SKILL.md), lines 14–17, composes it with command contracts; [API Go guidance](../../../../skills/api-craft/references/go.md), line 45, assigns language checks here. Neither composition transfers execution authority. |
| Version and change scope | [verified] Go craft lines 20–30 requires inspection of module/workspace, build constraints, CI and deployment targets, distinguishes minimum language version from preferred toolchain, preserves platform/cgo support and limits modernization to the authorized change. A new compiler's successful build is explicitly not proof of minimum-version compatibility. |
| Compatibility | [verified] Lines 34–41 includes exported callers, error matching, shared mutable ownership and serialized/persisted data. JSON v2 is a deliberate contract change, with named nil, field-case, omission and malformed-input differences; it is not mandatory on compiler upgrade. |
| Concurrency and failure behavior | [verified] Lines 45–52 requires owner, stop path and completion signal per goroutine. Cancellation is not joining; admission must be bounded before spawning. It identifies non-cancellation-aware errgroup admission and the lifetime of its derived context, preventing later work from inheriting an already-cancelled context. These are implementation requirements, not a concurrency runtime supplied by the skill. |
| Verification and evidence | [verified] Lines 56–63 scopes format/vet/tests to changed packages and callers, separately tests promised toolchains/platforms, bounds race-detector claims to executed paths and distinguishes durable blocking from completion in fake-time tests. Real network behavior remains separate from fake-time assertions. |
| Packaging | [verified] The single-file shape has no missing owned references, scripts, assets or tests to load. Projection comparison found no host-specific semantic loss. Existing repository/caller trust and authority rules remain applicable to every suggested command. |

## Coverage and accepted limitations

[sourced] Three authored discovery cases cover library work, modernization and deferral of a live incident. They grade invocation, not the concurrency or compatibility behavior mentioned in their prompts. [The eval guide](../../../../evals/README.md), lines 482–492, states that no native routing campaign has run. The shared [Go HTTP build](../../../../evals/build-scenarios/build-software-engineer-go-incidents-api.yaml), lines 126–149, tests selected API behavior and requires skill loading; it does not isolate Go craft's benefit or prove cancellation under full admission, joining, race freedom or minimum-version support.

[sourced] [BACKEND-002](../../../fleet-roadmap.md), lines 178–190, is active: the candidate is authored, while human acceptance and a bounded language-specific comparison remain outstanding. Those are explicit known limits, not newly discovered missing deliverables. No paid evaluation or broad rerun was requested by this audit.

[sourced] Public verification supplied by the audit coordinator supports [Go 1.26 modernization and diff preview](https://go.dev/doc/go1.26#tools), [Go 1.27 JSON v2 default availability](https://github.com/golang/go/blob/go1.27.3/src/internal/buildcfg/exp.go#L75-L83) and [wire defaults](https://pkg.go.dev/encoding/json/v2@go1.27.0#Marshal), [Go 1.25 synctest semantics](https://github.com/golang/go/blob/go1.25.0/src/testing/synctest/synctest.go#L12-L85), and [errgroup v0.24.0 admission/context behavior](https://github.com/golang/sync/blob/v0.24.0/errgroup/errgroup.go#L43-L151). JSON options/custom methods can change defaults; errgroup evidence is version-bound, not a latest-version claim. No public question remains. [unverified] Actual project compatibility and concurrency behavior were not exercised. [verified] No Go program, compiler migration, race check or fake-time test ran here. [sourced] The caller's existing baseline reports 4,233 tests and 4,952 subtests passing with 84 documented skips. [verified] Scoped source diff is empty; the projection and report links were checked.

## Inspection manifest

[verified] Complete canonical `skills/go-craft/SKILL.md`; `.github/skills/go-craft/SKILL.md` by byte comparison. Bounded reads: `skills/operator-cli/SKILL.md` 1–35; `docs/fleet-roadmap.md` 175–193; software-engineer Go-load entry; API Go language-check entry. Reused full shared repository guidance, API Go reference, backend ADR and prior Go HTTP oracle/scenario analysis.

[sourced] Helper full reads: `evals/scenarios/discovery-go-craft-{library,modernize,defers-live-incident}.yaml`. Bounded reads: `evals/README.md` 482–492; `CHANGELOG.md` 97–107; Go HTTP build scenario 126–149. Search-only backend ADR Go-lane decisions and tests naming the skill. No next item was started.

[verified] Safe checkpoint: this ninth report completes the assigned skill batch. The user requested a pause; no further item or repair was started.
