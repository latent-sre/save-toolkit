# Codex/Terra routing evidence for ROUTE-001

- **Date:** 2026-08-11
- **Status:** accepted; amended for the canonical Linux preflight and fixed canary only
- **Scope:** one current-revision GCP Cloud Run canary; the Windows arm and fixed campaign were
  retired 2026-08-22

## 2026-08-22 amendment: retire the Windows host arm

The canonical Linux container superseded the Windows host design. No protected Windows launcher,
runtime closure, owner, or in-repository consumer was ever provisioned, while its bootstrap and two
manifests continued to make every evaluator change maintain and test an unusable authority path.
The owner therefore retired `evals/codex_bootstrap.py`, its test suite, the Windows routing manifest,
and the evaluator-bundle manifest from the active tree. The immutable Linux image remains the only
supported live execution boundary.

Git history and the dated reviews preserve the exact Windows artifacts and results. Reopen Windows
execution only for a named requirement the Linux container cannot meet, with a named owner and a
newly reviewed trust boundary; do not restore the retired files as a default fallback.

## 2026-08-22 amendment: retire the fixed campaign

The original nineteen-scenario, 48-trial campaign never ran and produced no result artifact. Its
executor, duplicate frozen scenario bundle, before/current cohort plan, resumable journal, and
campaign-specific container mode nevertheless remained an active maintenance and authorization
surface. Survivor counts, a fixed call envelope, and provider-wide repetition were not findings, and
the instrument could not observe some of the authority claims the plan proposed to grade.

The owner therefore retired those campaign surfaces. The canonical Linux image keeps only the
credential-free preflight and one manifest-embedded canary with target-blind description and explicit
body arms. Canonical YAML scenarios and deterministic graders remain available to the separate
Claude evaluator; dated review packets and Git history preserve the original campaign design. This
retirement is not a passing result and grants no baseline or release authority.

Future paid work must begin with one named uncertainty that offline evidence cannot settle. It uses
one scenario, one arm, and one trial by default, then stops. A broader comparison requires a new
accepted decision, explicit budget, current evaluator design, and owner authorization; the original
48-call plan is not standing authority.

## Original decision (historical; operationally superseded)

The text below preserves the accepted rationale and limitations. Its call counts, execution gates,
and campaign scope are not standing work or authority after the 2026-08-22 amendments above.

Replace ROUTE-001's pending Claude/Sonnet campaign with a Codex campaign pinned to
`gpt-5.6-terra` at medium reasoning. This is a provider-specific rewrite, not a relabeling of Claude
evidence and not a reopening of the broader Codex/Sol EVAL-001 item.

The fixed evaluator manifest uses Codex CLI 0.147.0 and pins the installed executable SHA-256 to
`935a1911ed2556e4ffcec995f4886ac2ac425863ba26fed264df62e30272ad9d`. The executor copies only
those exact bytes into the private trial boundary, probes that copy, and rehashes it immediately
before auth copy and after the trial. It also fixes a 300-second timeout, two sequential trials,
read-only sandboxing, approval policy `never`, and a no-local/effect-tool model surface. Five scenarios
run against both the pre-expansion target
`a39a81f33f7ad7325c52d883822bbbdd80c7ed28` and the reviewed current target
`b459a5d3a209d384acb2b2b7ca325aa63697113b`; fourteen GCP/Akamai scenarios run against the current
target only. That is 48 planned trials: 20 paired and 28 current-only.

The exact model and reasoning effort are inputs, not response claims. The installed Codex model
catalog must contain the exact Terra slug, the command must pin it, and a trusted `SessionStart` hook
must report it. Medium is pinned because Terra's official model guidance identifies that setting as
the balanced starting point for this cost/intelligence tier.

## What Codex 0.147 can and cannot prove

A good response alone does not prove internal skill activation. Codex 0.147 exposes no supported
skill-start hook: its filesystem skill extension reads and injects `SKILL.md` internally without a
`PostToolUse` event or identity-bearing telemetry. ROUTE-001 therefore records skill selection as
**behavioral-only observational evidence**, not as a trace-grade activation fact. This limitation is
part of every result and is not upgraded by a passing answer.

Stock Codex 0.147 cannot supply a complete trace-grade ownership proof for its V2 custom-agent
path. `spawn_agent` exposes an encrypted message to hooks and returns after creation; `wait_agent`
reports only mailbox activity; `list_agents` can report a terminal result, but ordinary
`codex exec --json` omits the V2 spawn item and no event proves that the root consumed the child's
result. The two `routing.scope=root` incident cases therefore deterministically return
`INCONCLUSIVE` with `root-delegation-unobservable-v2`. They never become a routing `PASS` or `FAIL`
from answer text, agent type, or partial lifecycle receipts.

The authenticated development canary is instead the non-root
`discovery-gcp-ops-cloud-run-startup` case. It disables multi-agent, accepts only the fixed linear
`contains_all`, `contains_any`, and `cloud_run_rollback_packet` graders, and caps a response at
256 KiB total and 8 KiB per line before any grader runs. The structured grader accepts one fenced
JSON packet and binds its forward/inverse commands to exact scenario-provided service and revision
identities, 100% traffic, and matching region/project context; other traffic commands are rejected.
Every non-root trial permits zero command
or collaboration receipts. The evaluator installs
synchronous receipt hooks in a disposable Codex config only after copying and hashing the recorder
and parser into the private boundary. Receipts reduce to names, counts, verdict facts, and hashes;
session, turn, agent, tool-use, path, prompt, response, command, and raw payloads do not enter a
report.

The seventeen non-root skill cases pass only in the explicitly named observational mode when all hardened response graders
pass against the exact staged component bytes. A skill negative proves that the answer stayed in the
expected lane; it does **not** prove that the forbidden skill was never internally injected. The two
root-scoped incident cases remain `INCONCLUSIVE` unless a future, separately reviewed provider
instrument can bind plaintext delegated task, terminal child result, and root consumption.

## Evaluation boundary

The evaluated skills and custom agents are staged from exact Git objects into a neutral Codex
project as `.agents/skills/` and `.codex/agents/`. This tests the generated Codex descriptions and
instructions without loading the repository's `AGENTS.md`, ordinary user configuration, or personal
skills. Each generated agent loses exactly its one legacy `sandbox_mode` assignment during staging
and is otherwise required to contain only generated `name`, `description`, and
`developer_instructions` fields. Source and transformed agent-tree hashes are retained. This
prevents a role profile from replacing the evaluator's fixed session boundary while every routing
description and instruction byte remains unchanged. Plugin installation and distribution are
separate HOST-001/RELEASE-001 evidence and are not re-proved by ROUTE-001.

Terra's bundled Codex 0.147 metadata normally forces code mode and exposes `apply_patch`, which can
read a target file before a read-only write is rejected. The evaluator therefore refuses drift from
the reviewed bundled Terra entry, then supplies an authoritative one-model catalog that changes only
`tool_mode`, `apply_patch_tool_type`, `supports_search_tool`, and
`experimental_supported_tools`. Its fixed catalog SHA-256 is
`2d23cea7bd13463424eca49df927a38f8480501820eec853e3789015c6a321b6`. Shell, image, browser,
computer, app, web, MCP, memory, plugin, guardian, system-proxy, and workspace-dependency features
are also disabled; bundled and orchestrator skills/MCP plus plan/input tools are off. The command
pins the built-in `openai` provider, clears `openai_base_url`, and pins the default ChatGPT API
route. Exact source and transformed catalog hashes are report inputs, not model claims.

This tool-plan claim is sourced to the exact OpenAI Codex `rust-v0.147.0` tag: model `tool_mode`
precedence and direct-mode fallback live in
[`core/src/tools/mod.rs`](https://github.com/openai/codex/blob/rust-v0.147.0/codex-rs/core/src/tools/mod.rs#L63-L84);
shell, patch, view, and web registration gates are in
[`spec_plan.rs`](https://github.com/openai/codex/blob/rust-v0.147.0/codex-rs/core/src/tools/spec_plan.rs#L803-L974),
and image generation is independently gated in
[lines 518-556](https://github.com/openai/codex/blob/rust-v0.147.0/codex-rs/core/src/tools/spec_plan.rs#L518-L556).
Fresh `exec` starts without caller dynamic tools or selected capability roots in
[`exec/src/lib.rs`](https://github.com/openai/codex/blob/rust-v0.147.0/codex-rs/exec/src/lib.rs#L992-L1013).
The repository contract and runtime receipts must agree; transformed JSON alone is insufficient.

The operator's existing Codex login is copied only after credential-free staging into a disposable
`CODEX_HOME`. After Codex exits, the evaluator refreshes the exact-value guard, removes and verifies
absence of the disposable auth copy, and only then parses model-controlled JSON, loads receipts, or
grades the response. This is still same-user application-layer isolation, not a separate OS principal. The
catalog and frozen child profiles are designed to remove every general model-visible local-file tool;
that property is a live prerequisite, not something the transformed JSON may assert about itself.
The pre-canary packet must bind the complete tag-pinned 0.147 source entry, transformed entry, and
tool-registration precedence. Raw CLI
JSONL, session rollouts, hook payloads, and parsed response text exist only in that private temporary
run boundary. Output is checked both for credential-shaped material and exact opaque string values
from the transient auth file. A Windows kill-on-close Job Object (or a POSIX process group) bounds
descendants on timeout and cleanup; the raw boundary is deleted after reduction. Reports always
retain these authority facts:

- `source_review = not-verified-by-runner`
- `independent_evaluator = false`
- `baseline_eligible = false`
- `release_granted = false`

Live trials accept only the two fixed, independently reviewed repository revisions and the fixed
non-secret prompts. Each trial spec carries the manifest's exact scenario digest, and one stable
suite load is reused from validation through execution. The runner does not evaluate an external
branch, pull request, or caller-selected source. If executable, scenario, catalog, staged component,
hook, config, or child-profile drift reintroduces ambiguity or a file capability, the trial is
inconclusive before its response can count.

## Retired Windows trusted-launch design

The original Windows design did not allow a mutable checkout as an authenticated entrypoint. A
separately trusted launcher first had to verify and copy the exact reviewed
`evals/codex_bootstrap.py` bytes into a
protected location, then invoke that copy with an absolute protected Python installation using
`-I -S -B`. The external approval packet—not the bootstrap itself—pins the bootstrap digest, the
complete Python executable/DLL/standard-library closure, and the digest of
`evals/conformance/codex-terra-evaluator-v1.json`. The bootstrap
accepts exactly the ten-file evaluator closure, stages it create-only, synthesizes one fixed canary
request, and rechecks the exact staged tree after execution before any result is eligible. It also
requires a precreated empty private root on a local fixed NTFS volume; UNC, mapped, substituted,
remote, removable, and non-NTFS storage are rejected before any credential copy. Caller
mode, scenario, manifest, and temporary-path overrides are not part of the CLI contract.

The same boundary may synthesize one credential-free preflight. It exercises the fixed snapshot,
Codex version and bundled catalog probe, transformed catalog, neutral project, hook bundle, config,
and pre-auth drift checks, then exits before auth access or a model process. Its sanitized result is
always non-authoritative and explicitly labels host trust as not verified by the runner. A passing
preflight proves runner compatibility only; it cannot replace external runtime/config/registry
attestation or authorize the authenticated canary.

The current host's Python installation is writable by the operator identity, so an in-process
`python.exe` hash cannot establish that prerequisite: its DLL and standard-library closure may have
executed before the evaluator can check them. The current canary is therefore NO-GO until a protected
runtime closure or a separate OS identity is provisioned and independently reviewed. A clean launch
account and registry must also prove no managed/system/project MCP or dynamic-tool contribution, no
provider or API-route override, and no `cmd.exe` Command Processor AutoRun; Codex 0.147 executes
Windows hook commands through the active shell and its CMD fallback uses `/c`, not `/d`. The accepted
launch packet must additionally bind the protected Git executable/DLL/runtime installation closure
and a protected, sanitized Git object store: repository-local configuration includes, object
alternates, and replacement refs must be absent, and Git must not be allowed to resolve UNC/network
inputs. The exact executable and archive/tree digests prevent altered bytes from becoming accepted
evidence, but they do not protect load-time dependencies or prevent pre-validation Git reads.
The accepted
threat boundary also excludes an already-compromised process under the same Windows SID; current-user
ACLs cannot isolate the real or disposable login from another process with that identity. No live
canary has been attempted under the final harness.

## Verdicts and comparability

Authentication, timeout, mixed/missing model receipts, missing hooks, any non-permitted model tool
event, malformed or incomplete CLI events, input drift, receipt ambiguity, or an unavailable exact
target is `INCONCLUSIVE`, never a fleet failure. Both root cases are always `INCONCLUSIVE` on stock
0.147. For a measurable non-root case, response disagreement on a complete instrument is `FAIL`.
A measurable scenario is `PASS` only when both trials pass, and every skill PASS remains labeled
`behavioral-only-codex-0.147`.

Before/current numbers are comparable only when evaluator, manifest, scenario, CLI, model, effort,
sandbox, approval, timeout, trial-count, hook, recorder, and staged-surface hashes match. A report
cannot grant baseline or release authority. ROUTE-001 closure remains an explicit owner decision
over an independently reviewed exact evaluator revision and its sanitized 48-trial result.

## Preserved history and separate work

The earlier Claude runs and prepared Claude campaign remain historical evidence with their original
labels; they are neither deleted nor converted to Terra results. The revoked 2026-07-31 Sol reports
remain revoked. EVAL-001 stays deferred because its direct risk-weighted skill and eight-agent
coverage is broader than these nineteen routing cases.
