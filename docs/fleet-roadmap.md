# Fleet roadmap

> **Status: live.**
> This is the only document that tracks unfinished, blocked, or explicitly deferred work for the
> current fleet. Historical plans, reviews, audits, and decision records provide evidence and
> rationale; they do not independently add work to this queue.

The accepted architecture is
[`2026-07-31-multi-platform-plugin-packaging.md`](decisions/2026-07-31-multi-platform-plugin-packaging.md):
one canonical Claude plugin under `agents/`, `skills/`, and `commands/`, with generated host-native
adapters for Copilot/VS Code and Codex.

Closed work is retained in the
[`SAFE-001 closure`](reviews/2026-08-01-safe-001-closure.md) and
[`IMPROVE-001 closure`](reviews/2026-08-01-fleet-improvement-closure.md), plus the
[`VERIFY-001 closure`](reviews/2026-08-02-verify-001-closure.md),
[`PROTECT-001 closure`](reviews/2026-08-05-protect-001-closure.md),
[`HOST-001 closure`](reviews/2026-08-06-host-001-closure.md), and
[`ADAPT-001 closure`](reviews/2026-08-06-adapt-001-closure.md). The local Sol evaluator
decision is recorded separately in
[`2026-08-01-local-sol-conformance.md`](decisions/2026-08-01-local-sol-conformance.md).

## Item contract

Every live item carries:

| Field | Meaning |
|---|---|
| ID | Stable identifier used by plans, reviews, and release evidence |
| Status | `ready`, `active`, `blocked`, `deferred`, or `decision-needed` |
| Outcome | Observable result rather than a list of files |
| Source | Decision or review that established the work |
| Prerequisites | Controls that must exist first |
| Acceptance | Evidence required to close the item |
| Next action | Smallest safe step that advances it |

An item leaves this file after its acceptance evidence is committed and the change is merged. Git
history and archived source documents retain the implementation detail.

## Active runtime work

### WF-001 — establish a supported exact-dispatch boundary for Claude workflows

**Status:** `blocked`

**Outcome:** The repository carries no executable `ship-review` workflow until Claude provides a
supported way to dispatch one exact trusted workflow without granting caller-supplied workflow code.

**Source:** A version-pinned probe on Claude Code 2.1.221 found two incompatible behaviors. Setting
`CLAUDE_WORKFLOW_NAME_ONLY=1` suppresses inline-plugin workflows, so the trusted workflow cannot be
loaded. Without that flag, a native permission for `Workflow(save-toolkit:ship-review)` also admits
an input containing the same `name` plus caller-supplied `script`; the resolver executes that script
override. A plugin `PreToolUse` hook can deny the override, but the resulting launcher, hook receipt,
Git-object isolation, and upgrade matrix were a bespoke security broker disproportionate to this
fleet. That experiment was removed rather than shipped as a fragile control plane.

**Upstream refresh (2026-08-11):** Claude Code 2.1.227 now exposes the documented built-in
[`claude ultrareview`](https://code.claude.com/docs/en/ultrareview) subcommand. It removes the old
caller-supplied workflow-body surface, but does not yet satisfy this item: the research-preview
contract bundles the current working tree or clones a mutable PR target, documents no immutable
candidate SHA/digest in `bugs.json`, and exits 0 whether findings are present or absent. It also
uploads code to Anthropic's cloud sandbox and may consume paid usage credits. `--help` was inspected
without launching, uploading, posting, or spending; an undocumented live observation would not turn
these missing guarantees into a supported boundary.

**Prerequisites:** A documented direct-dispatch API, or documented permission semantics that bind
the registered workflow implementation as well as its name. Any alternative architecture needs an
accepted decision record before implementation.

**Acceptance:** Pin the supported CLI/API version and prove before merge that (1) only the intended
trusted workflow implementation can execute; (2) same-name `script`, `scriptPath`, resume, remote,
and extra-field variants are denied before task creation; (3) candidate bytes never reach an outer
tool-bearing model; (4) reviewer lanes have structurally bounded authority; and (5) incomplete or
failed review evidence cannot become approval. Gate A and mocked JavaScript are supporting evidence,
not substitutes for the live boundary proof.

**Next action:** Monitor the ultrareview/direct-dispatch result contract for a documented immutable
candidate identity and machine-enforceable finding verdict. Do not restore `ship-review`, wrap an
exit-0 result as approval, or launch a paid/uploading probe until an owner explicitly accepts that
external data/cost boundary and the remaining guarantees can be proven.

### RELEASE-001 — publish and roll back one immutable release

**Status:** `active` (2026-08-12) — PR
[#103](https://github.com/latent-sre/save-toolkit/pull/103) merged the repository implementation;
publication remains blocked and no release effect is authorized.

**Outcome:** One reviewed commit is versioned, tagged, published, installed, verified, and recoverable
without rebuilding or moving an unprotected ref.

**Source:** The historical distribution plan, rewritten for the accepted multi-platform plugin
architecture. Main-branch protection closed under
[`PROTECT-001 closure`](reviews/2026-08-05-protect-001-closure.md); host installation proof closed
under [`HOST-001 closure`](reviews/2026-08-06-host-001-closure.md).

**Prerequisites:** Repository preparation has no live prerequisite. Closure requires an independently
reviewed merged candidate, explicit owner authorization, immutable releases, the exact protected tag
ruleset, a human requester, exactly one distinct reviewer user or team on each of two release
environments, a protected reconciliation key, and the separately controlled publisher App. The host
closure's accepted limitations (Copilot CLI out of scope, UI-bound VS Code discovery, headless Codex
discovery, no model evidence) carry forward into this item's host distribution work.

**Acceptance:** Version parity and changelog pass; `claude plugin tag --dry-run` yields the exact
derived tag; promotion consumes the reviewed current-main/workflow SHA and merged-PR evidence under
the separated request/review/publish identities; strict install, exact inventory, marketplace and
plugin removal, standalone-agent cleanup, and authority checks pass from the published tag; a prior
immutable release is strictly rebound and reinstalled, or first-release uninstall is rehearsed;
immutability and unknown-outcome/replay behavior are evidenced without moving, deleting, or reusing a
version tag.

**Current implementation:** The accepted
[`exact-SHA promotion ADR`](decisions/2026-08-11-immutable-release-promotion.md) chooses one protected
annotated `save-toolkit--v<version>` tag plus an immutable GitHub Release, never a moving branch.
The prepared workflow, release-contract/mutation tests, changelog, strict remote-tag host-probe mode,
and [`release runbook`](release-runbook.md) are repository-local evidence only. The workflow separates
the configured human requester, distinct environment reviewer, Actions-read/no-write publisher App,
and environment-only HMAC proof. A non-replacing queue, permanent protected per-run version
reservation, prior-run/job scan, stable workflow-created issuance time, exact artifact IDs, and
prior-smoke guard make reruns reconciliation-only. The strict host evidence binds the checkout's
observed commit to an exact `ls-tree` ordinary-file/Git-blob map, then independently requires both
marketplace and installed Claude/Codex trees to match; identical non-HEAD source/install bytes and a
moving `HEAD` both fail closed. Claude Code 2.1.227 and Codex CLI 0.147.0 accepted a tag-pinned public
marketplace source in credential-isolated disposable probes. The release contracts, workflow mutation
suite, host-probe suite, Gate A, and Claude strict validation pass on the merged candidate tree. The
final PR head `4870c61f8b6decd6cce9a25a8120e30ad8a3d9bd` merged unchanged as `main` commit
`0d7a915d84b452be68a4bed462417a685a815728`; its post-merge Validate fleet run
[`31573152313`](https://github.com/latent-sre/save-toolkit/actions/runs/31573152313) passed on Linux,
macOS, and Windows plus the Claude plugin contract.

The pre-merge hash-bound review found no P0/P1 in the release state machine; the follow-up host
edge-case fixtures received no P0-P2 finding. Exact counts, byte identities, review boundaries, and
authorization limits are bound in the dated preparation-only
[`release/routing preparation evidence`](reviews/2026-08-11-release-routing-backlog-evidence.md). The
clean exact-commit tag dry-run derives `save-toolkit--v0.1.0`; no force flag was used and no tag or
Release was created.

**Sweep finding (2026-08-15), discovered and not fixed:** A mutation sweep of the two fail-closed
release contracts found their suites largely unpinned — `release_contract.py` at 35 surviving mutants
of 68, `release_workflow_contract.py` at 33 of 77 — with the survivors clustered on the authority
checks themselves: symlink rejection, every approval-expiry boundary, the UTC binding on
`issued_at`/`expires_at`, and the reservation-precedes-tag-creation ordering, whose five mutants all
survive. No claim is made that the workflow is wrong or that anything is exploitable; the narrower
claim is that the suite mutation-checking the release authority boundary is not itself
mutation-proof, so a future edit to those predicates could pass CI unnoticed. Evidence and triage are
in the [`fleet mutation sweep`](reviews/2026-08-15-fleet-mutation-sweep.md) packet. This does not
change the item's status and is not a merge, review, or publication blocker on its own; it is
context an owner should weigh before authorizing a live dispatch.

**Live blockers:** The merge step is complete. A post-merge audit reproduced a strict-host-evidence
false pass: the Claude authority check watches five selected locations under the real user
configuration, so an install-time write to an unlisted path such as `history.jsonl` is reported as
unchanged. RELEASE-001 cannot accept that authority criterion until the full user configuration tree,
or a closed and justified allowlist of expected writes, is censused with a red-first regression.

Live GitHub configuration remains absent: the 2026-08-12 API state has immutable releases disabled,
only an unprotected `copilot` environment, no release-tag ruleset, and no `release-tag` or
`release-finalize` environment. A separately controlled release App was not visible through the
available read-only repository surfaces. Creating those controls and dispatching the workflow are
external effects requiring an explicit owner-approved plan and rollback; the merge grants no
publication authority.

**Next action:** Repair and independently review the Claude user-configuration census, preserving the
strict no-user-write claim rather than weakening it. The owner then decides whether to authorize the
ADR's exact live GitHub configuration. If approved, record fresh API evidence, reopen EFFECT-001
before the first dispatch, dispatch the exact reviewed merged `main` SHA, preserve the strict
host/immutability reports, and add RELEASE-001 closure evidence. Do not create or move a release ref
manually.

### ROUTE-001 — routing evals for the 2026-08 description changes

**Status:** `active` (2026-08-12) — the owner-approved Codex/Terra rewrite, fixed evaluator bundle,
credential-free preflight, and trusted-bootstrap contracts merged in PR
[#103](https://github.com/latent-sre/save-toolkit/pull/103). The authenticated canary remains NO-GO on
the current host, the fixed 48-trial executor and campaign remain unfinished, and no Terra campaign,
result, or baseline exists.

**Outcome:** A provider-native Codex evaluator measures routing before/after for every description
edited or added in the SRE/GCP/Akamai expansion. Any measured regression (a component that stops
firing, or a near-miss that starts) is fixed or explicitly accepted without overstating what Codex
0.147 can trace.

**Source:** The 2026-08 expansion changed the descriptions of `obs-logs`, `obs-metrics`,
`obs-traces`, `obs-alerting`, and `runbook`, and added two new routed components (`gcp-ops`,
`akamai-edge`). The owner-approved provider rewrite and evidence boundary are recorded in
[`2026-08-11-codex-terra-routing.md`](decisions/2026-08-11-codex-terra-routing.md). This narrow
ROUTE-001 campaign does not reopen the broader deferred EVAL-001 Sol work.

**Prerequisites:** The fixed evaluator manifest, recorder, parser, snapshotter, catalog transformer,
and graders must be complete and pass their contract tests and Gate A. The exact evaluator bytes must
then be committed cleanly and independently reviewed. Live execution requires an externally pinned,
protected copy of the bootstrap; the exact nine-file evaluator-bundle manifest; a protected absolute
Python executable/DLL/standard-library closure (or a separate OS identity); independently reviewable
Codex 0.147 source evidence for the effective Terra tool plan; a precreated local fixed NTFS private
root; a clean launch account/registry with no managed/system/project MCP, dynamic-tool, guardian,
provider, API-route, proxy, or Command Processor AutoRun override; the
protected Git executable/DLL/runtime installation closure and sanitized Git object store with no
repository-config includes, object alternates, replacement refs, or UNC/network resolution; the
manifest-pinned Codex CLI executable bytes; the operator-owned Codex login; and only the fixed
non-secret prompts and isolated staged component bytes the owner approved for transmission. A
development canary from dirty or unreviewed evaluator bytes is instrument evidence only and cannot
become campaign or baseline evidence. An active same-SID compromise is outside this application-layer
boundary and must instead be excluded or isolated by the host.

**Acceptance:** Pin `gpt-5.6-terra` at medium reasoning, 300 seconds, two sequential trials, approval
policy `never`, and the no-local/effect-tools policy. Run five overlapping
scenarios against both
`a39a81f33f7ad7325c52d883822bbbdd80c7ed28` and
`b459a5d3a209d384acb2b2b7ca325aa63697113b`, then fourteen GCP/Akamai scenarios against the current
revision only: 48 trials total (20 paired and 28 current-only). Persist only sanitized
digest/count/verdict/runtime evidence. A non-root skill result remains explicitly
`behavioral-only-codex-0.147`; both root-scoped active-incident negatives must remain
`INCONCLUSIVE` with `root-delegation-unobservable-v2` under stock Codex 0.147. A report cannot grant
baseline, release, or owner acceptance to itself.

**Current evidence:** The implementation merged by PR #103 freezes the nineteen scenario IDs and
hashes, binds each `TrialSpec` to its manifest scenario digest, and embeds the exact development-canary
scenario rather than reopening mutable suite bytes. It also freezes both target revisions, Codex CLI
0.147.0 and its exact executable SHA-256,
`gpt-5.6-terra`, medium reasoning, two trials, and the
48-trial shape. Codex 0.147 exposes no supported filesystem-skill activation event, so ordinary skill
positives and near-miss negatives use deterministic response graders only and never claim exact skill
activation or target-skill absence. Non-root trials require zero tool receipts and zero collaboration
facts. Stock 0.147 cannot join its encrypted V2 spawn input, terminal child result, and root
consumption, so the two active-incident cases short-circuit to `INCONCLUSIVE` before response
grading. The fixed authenticated canary instead uses the non-root GCP Cloud Run startup case, only
the fixed linear `contains_all`, `contains_any`, and `cloud_run_rollback_packet` graders, and
256 KiB total/8 KiB per-line response limits. The structured rollback grader binds one exact fenced
JSON packet to service `checkout`, synthetic previous/failed revision IDs, 100% traffic, and matching
region/project context. A post-merge audit reproduced one remaining false pass: an additional
`gcloud run services` command continued with a POSIX backslash before `update-traffic` is accepted
outside the packet because the guard searches only one whitespace-normalized literal prefix. This
must be repaired and rebound into both manifests before any canary.

The evaluator now also has a bootstrap-only, credential-free preflight that reuses the actual
snapshot, executable/catalog probe, safe-catalog/config/hook construction, and drift gates and stops
before auth or a model process. On 2026-08-12 that preflight passed against the pinned concrete
versioned Codex 0.147.0 executable path; the normal launcher path was correctly rejected because it
crosses updater junctions. The result records host trust as unverified and grants no live authority.
The current Python/runtime and Git object-store trust prerequisites therefore remain open.

An owner-authorized managed response-only Terra smoke at commit `6d90943664ee0305726cc0ed8feb6b5d9a8e7f68`
exposed a grader-calibration defect without supplying a resolved-model, installed-skill, or harness
trace receipt. The red-first repair accepts equivalent placeholder and bind-address wording while
still rejecting the response's missing orientation and operator-ready rollback packet; it also adds
the previously absent log-read obligation. This is calibration evidence only, not a canary,
campaign result, or baseline; see
[`2026-08-11-codex-terra-managed-smoke.md`](reviews/2026-08-11-codex-terra-managed-smoke.md).

Terra's stock Codex 0.147 metadata would expose code-mode tooling, including an `apply_patch` read
surface. The catalog transformer verifies the exact bundled model entry and emits an authoritative
one-model catalog with code/local/effect model tools removed; the rendered configuration disables the
remaining shell, image, browser, computer, app, web, MCP, memory, plugin, guardian, proxy, and
workspace-dependency features, disables bundled/orchestrator skills and MCP, and pins the built-in
OpenAI provider/default ChatGPT route. The new
bootstrap rejects caller-selected evaluator mode/scenario/manifest overrides, accepts only the exact
nine-file closure, stages those bytes under `-I -S -B`, requires a local fixed NTFS private root, and
rechecks the stage after execution. Credential copying uses in-process ACLs, the exact hook import
directory is enforced, the disposable auth copy is removed before model-controlled parsing/grading,
decoded exact auth values are scanned, receipts and output are bounded, and every launched outcome
receives a post-trial drift check. Under the accepted live boundary, the operator login will still exist in a
disposable `CODEX_HOME` under the same OS user: this is application-layer isolation, not a
separate-principal sandbox, and that limitation must be retained in every result. The current host's
user-writable Python runtime closure does not satisfy the trusted-launch prerequisite, so no
authenticated canary was run. Historical Claude runs and the prepared Claude campaign remain
preserved under their original labels; none is relabeled as Terra evidence. The 2026-07-31 Sol results
remain retained but revoked as release evidence.

The exact offline checks, red-first defects, frozen byte manifest, and remaining live-host gates are
recorded in the
[`Codex/Terra pre-canary evidence packet`](reviews/2026-08-11-codex-terra-precanary.md). That packet
is preparation evidence only; it does not authorize credentials, model calls, campaign execution,
baseline eligibility, or release use.

**Grader repair (2026-08-15):** The outside-packet detector is repaired and evidenced in the
preparation-only
[`Cloud Run outside-command repair packet`](reviews/2026-08-15-cloud-run-outside-command-repair.md).
Probing the boundary first showed the recorded POSIX-continuation case was one of seven accepted
evasions, not the only one — continuations at other word boundaries, CRLF continuations, a
continuation with trailing horizontal space, and quoted or backslash-escaped separators all reached a
pass. The detector now normalizes those word-hiding devices before the literal search, so it matches
command shape rather than one rendering; it stays linear on adversarial input and still runs before
the packet's own commands are accepted. Prose that merely names `update-traffic` still passes.

Mutation-sweeping that repair then found two more defects **in the repair itself**, and both are the
reason the packet is worth reading. A POSIX continuation joins its halves with no separator, so
`serv\`+newline+`ices` is the word `services`; the first version substituted a space and split the
word, leaving a live bypass that every fixture passed over. The pattern also carried an unreachable
`\r?` that no fixture could kill, because the caller splits the response before the pattern sees it.
Both are fixed. The sweep also established that `mutation_guard` **cannot evaluate this code at
all** — its operator set generates zero mutants for a pure string transformation — so a clean guard
report there is near-vacuous and a hand-built mutant set is what actually holds the line: 3 of 9
killed on the first version, 9 of 9 now. Separately, `evals/graders.py` carries 54 surviving mutants
of 167, identical before and after this change and none in the new code, so they are pre-existing
gaps in the other graders rather than a regression. The
`evals/graders.py` row of the evaluator bundle was refreshed; the scenario, the routing manifest, the
frozen scenario digests, and the trial shape are unchanged, and no live trial was run. A known
limitation is recorded rather than implied covered: the detector is a normalizer plus a literal
search, not a shell parser. The typed record stays `observed` — its target paths already fit an
attempt, so the missing piece is an independent evaluation of the exact candidate.

**Next action:** Obtain independent exact-byte review of the grader repair and append that verdict to
the typed record. Then provision and independently bind a
protected Python runtime closure or separate OS identity plus the clean managed-config/registry,
protected Git installation, and sanitized object-store prerequisites before attempting the one-trial
canary. Only after the canary and its boundary pass may the still-unimplemented fixed 48-trial
executor be completed, reviewed, and run sequentially to produce a sanitized closure packet for
explicit owner disposition. Do not tune descriptions or claim a current baseline from historical
Claude/Sol output, a development canary, or unreviewed working-tree bytes.

## Repository work

### MUTATION-001 — close the mutation-guard evidence gaps

**Status:** `active` (2026-08-15) — attempt 1 is prepared and evidenced at candidate revision
`82333f42c9c1f55286632f0ad4fdad3fba45a5ff`; independent evaluation and the owner's rescope decision
are outstanding.

**Outcome:** `scripts/mutation_guard.py` never labels a sampled all-survivor result as proof that a
suite probably never exercises its subject, refuses invalid limits with a distinct exit status, and
documents sampling without implying that a bounded run covers the motivating mutant.

**Source:** The typed record
[`fi_mutation_untested_assertions`](../evals/improvements/fi_mutation_untested_assertions/record.json)
retains three independently verified control defects as open. The record remains `observed`; no
formal repair attempt or owner promotion has been appended.

**Prerequisites:** Use one bounded lifecycle attempt under the record's existing three-attempt budget.
Calibrate sampled versus unbounded semantics first, and keep refusal, instrument failure, survivor,
and clean-result exits distinguishable.

**Acceptance:** Red-first tests prove all three recorded guard defects; the focused mutation-guard
suite and Gate A pass; a deliberate load-bearing mutant is still killed; independent evaluation is
appended to the typed record without self-promoting it.

**Current evidence:** Attempt 1 is prepared, not evaluated. Each of the three recorded defects is
repaired behind a regression that fails when — and only when — its own fix is reverted; the reverts
were run per defect and each failed exactly its own test class. The unexercised claim now
additionally requires an unbounded run, invalid `--limit` values and every other argparse usage error
exit a distinct `EXIT_USAGE` rather than colliding with `EXIT_REFUSED`, and both docstrings state that
an evenly spaced sample can miss any given mutant. The mutation operator set, `DEFAULT_LIMIT`, and the
sampling algorithm are unchanged. The author's execution evidence, the deliberate-mutant sweep, and
the honest limits are bound in the preparation-only
[`mutation-guard evidence-gap packet`](reviews/2026-08-15-mutation-guard-evidence-gaps.md); it claims
no evaluation, promotion, or monitoring authority.

Two things block closure and neither is the author's to decide. No attempt is appended to the typed
record: its declared `target.artifact_paths` are `AGENTS.md` and `scripts/gate_a.py`, which this
candidate does not touch, so an attempt would violate the lifecycle's requirement that every declared
target path be touched by the net candidate diff — re-declaring the target to name the control and its
test is a rescope. And an attempt's evaluation must be a fresh evidence envelope produced outside the
authoring checkout, which the author cannot supply for itself. The record therefore stays `observed`
with an append-only limitations entry.

**Next action:** Obtain the owner's rescope decision on `target.artifact_paths`, then an independent
exact-revision evaluation of the candidate in a fresh context, and append that verdict to the typed
record. Confirm the macOS and Windows Gate A jobs on the exact candidate. Do not promote the record,
append a self-authored attempt outcome, or treat the author's own sweep as the independent evaluation.

### HOST-002 — measure VS Code tool enforcement and re-probe hook portability

**Status:** `ready` (2026-08-12)

**Outcome:** The guarded roles' VS Code posture rests on observed host behavior rather than
inference, and the fleet knows whether the read-only guard is portable to that host or whether
policy-delivered Copilot managed settings are the only real control there.

**Source:** A 2026-08-12 scan with two distinct evidence bases, cited separately because they were
not established the same way.

*Base A — the installed build, read directly.* VS Code 1.133.0, build commit
`a5b500951314efd502d07465bd138dfbd714a960`, file
`<install>/<build>/resources/app/out/vs/workbench/workbench.desktop.main.js`. Reproduce by searching
that bundle for the quoted identifier.

- `[verified]` The tool-set vocabulary the generator emits matches the host enum. Search `_m` :
  `a.execute="execute",a.edit="edit",a.search="search",a.agent="agent",a.read="read",a.web="web",a.todo="todo"`.
  `COPILOT_TOOL_ORDER` is a subset, so the projection's names resolve.
- `[verified]` The Claude→VS Code equivalence table matches `COPILOT_TOOL_MAP`. Search
  `toolEquivalent` — `Bash`→`execute`, `Grep`→`search/textSearch`, `Glob`→`search/fileSearch`,
  `Read`→`read/readFile`, `Write`/`Edit`→`edit/*`, `WebFetch`/`WebSearch`→`web`, `Task`→`agent`.
  The same table maps `Skill`, `LSP`, and `MCPSearch` to `[]`.
- `[verified]` `disable-model-invocation` is a recognized key, not inert: search
  `R.disableModelInvocation="disable-model-invocation"`, and the skill-conversion path emits it.
- `[verified]` Delegation is unscoped. Search `runSubagent` for the tool schema: `agentName` is
  `"Optional name of a specific agent to invoke. If not provided, uses the current agent."`
- `[verified]` The hook surface exists. Search `HOOKS_LOCATION_KEY` for
  `chat.hookFilesLocations`, `chat.useHooks`, `chat.useClaudeHooks`, alongside `mo.hooks`.

*Base B — upstream `microsoft/vscode` @ `0157e11`, read by an external research lane and* **not**
*independently confirmed here.* Treat as `[sourced]` at one remove; re-derive before relying on a
line number.

- Omission sets an explicit `false` for the model:
  `src/vs/workbench/contrib/chat/browser/tools/languageModelToolsService.ts:1611-1621`.
- Session outranks the agent file, extension agents alone are read-only, and the picker writes the
  user's change back: `.../browser/widget/input/chatSelectedTools.ts:136-143`, `:188`, `:202-220`.
- Official VS Code documentation at `microsoft/vscode-docs`
  `95cc3b3b226823b70306b8b6ef118def6f3c1842` describes tool checkboxes as per-session selection and
  says a prompt file's `tools:` list outranks a referenced custom agent's list:
  `learn/foundations/introduction-to-agent-first-development.md:115-125` and
  `docs/agent-customization/prompt-files.md:174-183`.
- Upstream `chatWidget.ts:2782-2816,3567-3584` confirms prompt-file metadata can switch the selected
  agent and tool map. Those lines do not establish the previously claimed chat-deep-link override;
  that unsupported attribution is removed rather than carried into the probe.

Base A establishes what the host recognizes; Base B establishes the override precedence that makes
`tools:` a default rather than a boundary. Only the second is load-bearing for the `AGENTS.md` limit,
and it is the half this item must confirm by observation.

**Prerequisites:** None beyond an installed VS Code and this checkout. The probe is observational: it
changes no live system, and it neither authorizes nor implies a Copilot hook implementation.

**Acceptance:** A dated review packet records, from an observed session, whether the tools picker
offers `execute` to `sre`; whether a session-level override reinstates it; and whether using the
picker mutates `.github/agents/sre.agent.md` on disk. It states the VS Code build tested, keeps
`[verified]`/`[sourced]` labels honest, and either confirms the `AGENTS.md` VS Code limit or replaces
it with the measured behavior. Any hook-portability finding is recorded as evidence only; wiring a
Copilot hook is separate work needing its own review.

**Next action:** Run the linked
[`HOST-002 VS Code tool-enforcement probe`](probes/host-002-vscode-tool-enforcement.md), validate its
per-criterion evidence envelopes, and record the dated packet. Do not weaken the `AGENTS.md` limit on
inference alone, and do not populate `hooks/copilot-hooks.json` before a probe shows the payload can
scope to an exact agent identity.

### EVAL-002 — make POSIX process-boundary cleanup idempotent

**Status:** `ready` (2026-08-13)

**Outcome:** A timed-out Codex trial terminates its complete process tree and closes the POSIX
boundary deterministically; final cleanup does not turn an already-completed termination into an
`EPERM` test error, and no exception handling masks a surviving descendant.

**Source:** The observed-only record
[`fi_macos_process_group_cleanup_race`](../evals/improvements/fi_macos_process_group_cleanup_race/record.json)
and its [intake packet](reviews/2026-08-13-macos-process-group-cleanup-race-intake.md) bind two
identical macOS failures on PR #106 to exact head `a2a046e1`, while the byte-identical merge tree
passed on main.

**Prerequisites:** Start one bounded lifecycle attempt from current main. First define the narrow
idempotent-cleanup invariant and a deterministic seam for the post-timeout `EPERM` state; do not
generalize from runner timing or broadly swallow `PermissionError`.

**Acceptance:** A red-first, mutation-sensitive regression proves the failure and the descendant-
termination guarantee; focused process-boundary tests pass repeatedly on macOS; Ubuntu, macOS, and
Windows Gate A jobs pass on the exact candidate; the typed record receives independent exact-revision
correctness/security review without self-promotion.

**Next action:** Prepare attempt 1 with a deterministic POSIX cleanup seam and the smallest repair that
separates an idempotent final close from a failed initial termination.

## Decisions needed

### REVIEW-001 — enforce final-SHA review reconciliation

**Status:** `decision-needed` (2026-08-12)

**Outcome:** A pull request cannot merge while its final candidate lacks the required independent
review or while actionable current findings remain undisposed, even when an automated reviewer skips
a large diff or comments on an earlier SHA.

**Source:** PR #103 exceeded Copilot's 20,000-line review limit and merged with unresolved review
threads, including the two reproducible false passes now recorded under RELEASE-001 and ROUTE-001.
The live `Protect main` ruleset requires a pull request but zero approvals and no review-thread
resolution; the separate Copilot rule reviews drafts but does not review every push. Repository policy
already requires immutable-candidate correctness and security review before merge.

**Prerequisites:** The owner chooses a solo-maintainer-compatible enforcement mechanism: GitHub
approval/thread settings, a protected exact-SHA review gate, or an equivalent control with no self-
approval. Changing live rulesets is an external effect and is not authorized by this item.

**Acceptance:** The chosen control requires review of the final candidate SHA, distinguishes stale or
rejected comments from actionable findings, fails closed when a reviewer declines or times out, and
has API/negative-test evidence that a PR like #103 cannot merge until current findings are fixed or
explicitly rejected with evidence.

**Next action:** Owner decision on the enforcement mechanism. Until then, treat final-SHA review and
thread reconciliation as a manual merge blocker rather than assuming green CI is review evidence.

### SWEEP-001 — dispose the 2026-08-15 mutation-sweep findings

**Status:** `decision-needed` (2026-08-15)

**Outcome:** Each finding from the fleet mutation sweep is either owned and repaired, or explicitly
accepted as not worth fixing with a recorded reason. None is left as an unowned number in a review
packet that a later reader mistakes for either a defect list or a clean bill of health.

**Source:** The findings-only
[`fleet mutation sweep`](reviews/2026-08-15-fleet-mutation-sweep.md), which swept seven modules
unbounded on the repo-pinned Python 3.12. Everything in it is discovered and **not** fixed, except
the one fail-open already closed under its own commit. The three highest-consequence groups:

- `[verified]` `scripts/release_contract.py` (35 of 68) and `scripts/release_workflow_contract.py`
  (33 of 77) — symlink rejection, every approval-expiry boundary, UTC binding, manifest identity,
  `required=True` on the release arguments, and the whole reservation-precedes-tag invariant are
  unpinned. These gate RELEASE-001's acceptance.
- `[verified]` `scripts/host_install_probe.py` (253 of 553) — the census machinery under
  `host.claude.probe-authority` is barely pinned, including the criterion that an unreadable tree
  must yield inconclusive rather than pass.
- `[verified]` `evals/graders.py` (54 of 167), pre-existing and unchanged before and after this
  session's grader repair.

**Prerequisites:** None to decide. Any repair is ordinary bounded work under the relevant record;
opening typed `fi_` records for the release-contract and host-probe groups is part of the decision,
not a precondition for it.

**Acceptance:** Every group above carries a disposition — `prepared`, `proposed`, `blocked`,
`duplicate`, or `not_applicable` — with an owner and a reason. Any group accepted as not worth
fixing says why in writing. Repairs land red-first, proving the mutant survives before the fix and
dies after.

**Next action:** Owner disposition per group. Treat the release-contract group as the highest
consequence, since RELEASE-001's acceptance rests on contracts whose own suite does not notice their
predicates changing. Do not read a survivor count as a defect count, and do not read a clean sweep
over `_authority_check` as evidence the census is sound — that code generates no mutants at all.

### NAV-001 — dispose the incident-navigation prototype

**Status:** `decision-needed` (2026-08-12)

**Outcome:** The recovered incident-navigation prototype is either preserved and resumed as a
current-main feature or explicitly archived/rejected; it is not silently lost, deleted, or treated as
accepted fleet behavior.

**Source:** `[verified]` The dirty local worktree `.worktrees/incident-navigation` contains an
uncommitted canonical skill, SRE-agent routing edits, direct/discovery scenarios, tests, and generated
projections. At the 2026-08-12 capture its branch had no unique commit, was 18 commits behind
`origin/main`, and had no pull request. Current main contains no accepted `incident-navigation`
component. The exact 11-file inventory and recoverable patch set are preserved in
[`2026-08-12-incident-navigation-preservation`](reviews/2026-08-12-incident-navigation-preservation/README.md).

**Prerequisites:** `[verified]` The file/digest inventory and recoverable patch prerequisite is
satisfied by the preservation packet outside the dirty worktree. The owner still must decide whether
responder-orientation is in current product scope before any cleanup, rebase, or implementation work.

**Acceptance:** If resumed, canonical sources are rebased onto current main, projections are regenerated,
route/behavior eval obligations are met, and independent review passes. If rejected, the owner records
the reason and explicitly authorizes removal only after the recoverable snapshot is verified.

**Next action:** Request the owner disposition: resume from canonical sources on current main, or
archive/reject with a recorded reason. The preservation packet grants neither acceptance nor cleanup
authority; do not delete, reset, or regenerate inside the source worktree without that decision.

## Deferred

### EVAL-001 — expand risk-weighted Sol coverage

**Status:** `deferred` (2026-08-02) — the Codex/Sol conformance runners, contract tests, and fixed
manifests are recoverable at tag `pre-trim-2026-08-02`. Gate A, the local Claude runner, and the
narrow active ROUTE-001 Terra evaluator are the beta's current verification surfaces; ROUTE-001 does
not supply this item's broader direct Sol coverage. Reopen when a Codex/Sol behavioral baseline is
actually needed for a release decision; the prerequisites and acceptance below are unchanged and
still apply at that point.

**Outcome:** The highest-risk skills and every explicitly installed Codex custom agent have direct
behavioral evidence on `gpt-5.6-sol`, while implicit routing remains an observational metric rather
than a release gate.

**Source:** Existing Sol reference and six-agent conformance baselines plus the measured headless
agent-discovery limitation.

**Prerequisites:** Clean committed plugin, generated-agent, and harness inputs; independent review of
that exact commit; and an operator-owned Codex login. Changes originating in an external branch or PR
must first be reviewed and committed into this repository before live evaluation.

**Acceptance:** Direct lanes cover the trust-separated research roles and risk-weighted release,
production-change, PCF, agent-security, and observability contracts. Every result distinguishes
`pass`, `fail`, and `inconclusive`, preserves exact model/runtime evidence, and never relabels the
historical Claude/Opus baselines.

**Current evidence:** Tag `pre-trim-2026-08-02` retains the fixed manifests, sanitized local runners,
contract tests, and their documented same-user credential limitation. The 2026-07-31 live results
remain retained but revoked and there is no current Sol behavioral baseline. The active ordinary
suite retains negative routing coverage for trust separation, `scribe` collisions, and the
operational-learning method's direct-writing boundary.

**Reopen trigger:** A named release decision requires a current Codex/Sol behavioral baseline that
the active structural and Claude evaluation surfaces cannot provide.

**Next action:** None while deferred. On reopen: recover the runners from tag `pre-trim-2026-08-02`,
independently review the exact recovered commit, then run both fixed manifests from its clean
checkout. Retain each sanitized report beside the matching review packet; acceptance of the pair is
an external human/protected-workflow decision, never a field the runner grants itself. Keep implicit
routing observational rather than making it a release gate.

### STATE-001 — durable orchestration state

**Status:** `deferred`

**Outcome:** If a real multi-agent workflow needs resumable ownership, add append-only run/task/attempt
state with versions, leases, cancellation, supersession, revision binding, and evidence-linked
completion.

**Source:** Fleet authority reviews that distinguish durable coordination state from prompt prose,
worktrees, and host-native session state.

**Prerequisites:** A named multi-session or multi-worker consumer whose ownership and completion
cannot be derived safely from Git, pull requests, and evidence artifacts alone.

**Acceptance:** A versioned append-only state contract, migration and rollback plan, lease and
supersession semantics, evidence-bound completion, and failure tests exist for that named consumer.

**Reopen trigger:** A workflow spans multiple independent workers or sessions and cannot safely derive
ownership and completion from the pull request, Git commits, and evidence artifacts alone.

**Next action:** None. Do not add a coordinator persona or unused state database first.

### EFFECT-001 — effect-bound execution broker

**Status:** `deferred`

**Outcome:** If protected automation is ever allowed to perform a live effect, approval is bound to
one exact action, target, argv/executable digest, expiry, nonce, rollback, and replay ledger.

**Source:** Fleet authority reviews that reject prose approval and require an explicit unknown-outcome
state for externally dispatched effects.

**Prerequisites:** A named workflow approved to cross the current prepare/recommend boundary, a
separately controlled execution identity, and live `main` ruleset enforcement as recorded in
[`docs/reviews/2026-08-05-protect-001-closure.md`](reviews/2026-08-05-protect-001-closure.md).

**Acceptance:** Effect-bound approval, dispatch, unknown-outcome reconciliation, replay prevention,
expiry, rollback, and operator-resolution tests pass for the named effect target.

**Reopen trigger:** A named workflow is approved to move beyond the fleet's current prepare/recommend
boundary and has a separately controlled execution identity.

**Next action:** None. Importing a broker before a legitimate consumer would broaden the apparent
execution path rather than reduce current authority.

**Current note (2026-08-11):** RELEASE-001 now has a target-specific workflow design, but its live
effect identity/configuration has not been approved or created, so this trigger is not yet satisfied.
If the owner authorizes that configuration, reopen EFFECT-001 before the first dispatch and close it
only with the workflow's effect-binding, expiry, replay, unknown-outcome, and rollback evidence.
