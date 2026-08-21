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

**Contract refresh (2026-08-18):** Context7's current official documentation and GitHits' exact
Claude Code `v2.1.227` repository agree on the public surface: the non-interactive command prints
findings, offers raw JSON, and distinguishes completion from command failure. Neither source exposes
an immutable reviewed-subject field or findings-sensitive approval verdict. WF-001 therefore remains
blocked; the separate provenance and queries are recorded in the
[`first-three backlog evidence packet`](reviews/2026-08-18-first-three-backlog-evidence.md).

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

**Live blockers:** The merge step is complete. The Claude authority-census false pass now has a
red-first defense-in-depth repair: an unlisted persistent `history.jsonl` write failed before the
change and is caught after the probe switches from five selected paths to the complete lexical
user-configuration root. Linked, special, unreadable, or racing trees now become inconclusive, and
the focused host-probe file is green at 74 tests with 2 platform skips.

Independent static review nevertheless requested changes on the load-bearing authority claim. A
before/after size-and-mtime census cannot observe a file created and deleted between snapshots or a
same-size modification whose mtime is restored. It proves no residual metadata-visible change, not
that every write stayed inside the disposable target. The traversal-race finding from that review
has a red-first local repair, but the P1 contract mismatch remains. This uncommitted preparation over
`41a20bab` therefore does not satisfy the strict no-user-write criterion. Evidence and limits are in
the [`first-three backlog evidence packet`](reviews/2026-08-18-first-three-backlog-evidence.md).

Live GitHub configuration remains absent: the 2026-08-12 API state has immutable releases disabled,
only an unprotected `copilot` environment, no release-tag ruleset, and no `release-tag` or
`release-finalize` environment. A separately controlled release App was not visible through the
available read-only repository surfaces. Creating those controls and dispatching the workflow are
external effects requiring an explicit owner-approved plan and rollback; the merge grants no
publication authority.

**Next action:** Keep the full-root census as residual-state defense in depth, obtain exact-byte
re-review before landing it, and do not cite it as release authority. The owner must accept a design
that structurally denies the host CLI write access to the real user configuration — for example a
separately controlled OS identity or an equivalent sandbox boundary — before publication can use the
strict no-user-write criterion. That design needs an accepted decision record and cross-host proof;
weakening the criterion to metadata-visible residue is not an implementation shortcut. Only after
that boundary and the missing live GitHub controls exist should the owner consider dispatch. Do not
create or move a release ref manually.

### ROUTE-001 — routing evals for the 2026-08 description changes

**Status:** `active` (2026-08-20) — PR
[#103](https://github.com/latent-sre/save-toolkit/pull/103) supplied the original evaluator. A
Linux Docker arm implements the fixed 48-trial executor and passes credential-free preflight. Four
owner-approved development canaries ended `INCONCLUSIVE`, and four later attempts reached behavior
grading and returned valid `FAIL` verdicts. The latest explicit body-load probe failed graders 0 and
4 while passing 1, 2, 3, and 5; it changed measured response shaping but did not test or repair
implicit routing. No campaign, routing result, or baseline followed. See the
[`Linux canary evidence packet`](reviews/2026-08-20-route001-linux-canary.md).

**Owner direction (2026-08-20) — measure on more than one provider.** This campaign is to be run
across providers rather than on Codex alone: a **Claude** arm (the components that actually ship to
Claude users, via `evals/run_evals.py`, which is confirmed working on this host as of 2026-08-20),
the existing **Codex/Terra** arm (which measures the *generated Codex adapters*, not the Claude
components — see the staging note below), and **a third provider such as Grok/xAI** as a candidate
once the first two produce comparable evidence. Each arm reports under its own label; no arm's
result is relabeled as another's. The Claude arm has no API-key prerequisite: subscription OAuth is
supported through a persistent, eval-only profile selected by
`SAVE_TOOLKIT_CLAUDE_EVAL_CONFIG_DIR`, so no API key is required. Each host must complete the
interactive `claude auth login` for that profile before running; the Terra arm's host prerequisites
are unchanged.

**Each arm needs a different isolation boundary — do not apply one arm's prerequisites to another.**
The three differ because the hosts differ, and conflating them either paralyses the cheap arm or
under-protects the expensive one:

| Arm | Boundary it needs | State |
|---|---|---|
| Claude | The clean-room in [`evals/clean_room.py`](../evals/clean_room.py): a persistent, eval-only OAuth profile selected by `SAVE_TOOLKIT_CLAUDE_EVAL_CONFIG_DIR` and serialized across batches so rotating credentials remain current; direct API auth uses an empty temporary profile. Both paths retain the digest-checked plugin snapshot, allowlisted child environment, empty working directory outside the repo, strict empty MCP, and exact `Skill,Task` tool allowlist. Documented in [`evals/README.md`](../evals/README.md) under *Clean-room boundary*, which states plainly that it is an evaluation boundary, **not** an OS security sandbox. | **Exists and runs.** Executed 2026-08-19/20 on two models. A new host needs one interactive login to the dedicated profile; no API key is required. |
| Codex/Terra | Full host trusted-launch: protected Python runtime closure (or a separate OS identity), protected bootstrap launch, precreated NTFS private root, clean launch account/registry with no MCP/dynamic-tool/guardian/proxy/AutoRun override, protected Git executable and sanitized object store. Heavier because Codex 0.147 exposes code-mode tooling and runs Windows hook commands through the shell, and because the credential copy is same-SID application-layer isolation only. | **Requirements documented; nothing provisioned.** No owner, date, or plan is recorded — this, not the evaluator, is what blocks the campaign. |
| Grok/xAI (candidate) | **Unanalysed.** Before any trial: what tool surface the CLI exposes by default, how its credentials are stored and whether they can be confined to a disposable config root, and whether an equivalent of the clean-room's tool allowlist and empty-MCP guarantee exists. | **Nothing written.** Do not schedule trials before this analysis exists. |

The [digest-bound verification sandbox](../docs/verification-sandbox.md) is a **different tool for a
different job** and cannot host any of these arms: it runs with `network mode none` by design, and
its own documentation records that network-enabled verification is unsupported and stays
`inconclusive`. It verifies reviewed bytes; it does not talk to model providers.

**Outcome:** A provider-native Codex evaluator measures routing before/after for every description
edited or added in the SRE/GCP/Akamai expansion. Any measured regression (a component that stops
firing, or a near-miss that starts) is fixed or explicitly accepted without overstating what the
Codex 0.148 campaign can trace.

**Source:** The 2026-08 expansion changed the descriptions of `obs-logs`, `obs-metrics`,
`obs-traces`, `obs-alerting`, and `runbook`, and added two new routed components (`gcp-ops`,
`akamai-edge`). The owner-approved provider rewrite and evidence boundary are recorded in
[`2026-08-11-codex-terra-routing.md`](decisions/2026-08-11-codex-terra-routing.md). This narrow
ROUTE-001 campaign does not reopen the broader deferred EVAL-001 Sol work.

**Prerequisites:** The fixed evaluator manifest, recorder, parser, snapshotter, catalog transformer,
and graders must be complete and pass their contract tests and Gate A. The exact evaluator bytes must
then be committed cleanly and independently reviewed. Live execution requires an externally pinned,
protected copy of the bootstrap; the exact ten-file evaluator-bundle manifest; a protected absolute
Python executable/DLL/standard-library closure (or a separate OS identity); independently reviewable
source evidence for the exact Codex version's effective Terra tool plan; a precreated local fixed NTFS private
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
`7aef80aede95394f6c4237ed2aedb911e141c3c0`, then fourteen GCP/Akamai scenarios against the current
revision only: 48 trials total (20 paired and 28 current-only). Persist only sanitized
digest/count/verdict/runtime evidence. A non-root skill result remains explicitly
`behavioral-only-codex-0.148`; both root-scoped active-incident negatives must remain
`INCONCLUSIVE` with `root-delegation-unobservable-v2`. A report cannot grant
baseline, release, or owner acceptance to itself.

**Current evidence:** The implementation merged by PR #103 freezes the nineteen scenario IDs and
hashes, binds each `TrialSpec` to its manifest scenario digest, and embeds the exact development-canary
scenario rather than reopening mutable suite bytes. Commit
`262dfc93daf8663b50f6175b7beb7fdfae9b15cc` preserves those inputs while repinning Codex CLI 0.148.0
and its exact Linux executable SHA-256; the validation-only
Windows manifest retains its historical 0.147.0 bytes. The campaign also freezes both target revisions,
`gpt-5.6-terra`, medium reasoning, two trials, and the
48-trial shape. The 0.148 campaign accepts no provider-native filesystem-skill activation event, so
ordinary skill positives and near-miss negatives use deterministic response graders only and never
claim exact skill activation or target-skill absence. Non-root trials require zero tool receipts and
zero collaboration facts. The accepted root trace cannot join a delegated task, terminal child result,
and root consumption, so the two active-incident cases short-circuit to `INCONCLUSIVE` before response
grading. The fixed authenticated canary instead uses the non-root GCP Cloud Run startup case, only
the fixed linear `contains_all`, `contains_any`, and `cloud_run_rollback_packet` graders, and
256 KiB total/8 KiB per-line response limits. The structured rollback grader binds one exact fenced
JSON packet to service `checkout`, synthetic previous/failed revision IDs, 100% traffic, and matching
region/project context. The current grader normalizes POSIX continuations, quotes, and backslash
escapes before rejecting an additional `gcloud run services update-traffic` command outside the
packet. That repair and its manifest binding still require independent exact-candidate review before
the campaign; the development canary cannot close that prerequisite.

The evaluator now also has a bootstrap-only, credential-free preflight that reuses the actual
snapshot, executable/catalog probe, safe-catalog/config/hook construction, and drift gates and stops
before auth or a model process. On 2026-08-12 that preflight passed against the pinned concrete
versioned Codex 0.147.0 executable path; the normal launcher path was correctly rejected because it
crosses updater junctions. The result records host trust as unverified and grants no live authority.
The historical Windows Python/runtime and Git object-store trust prerequisites therefore remain open.
On 2026-08-20 the replacement Linux image was rebuilt against Codex 0.148.0 and passed the same
credential-free preflight with no auth mount or model process. The evaluator is committed but remains
independently unreviewed.

An owner-authorized managed response-only Terra smoke at commit `6d90943664ee0305726cc0ed8feb6b5d9a8e7f68`
exposed a grader-calibration defect without supplying a resolved-model, installed-skill, or harness
trace receipt. The red-first repair accepts equivalent placeholder and bind-address wording while
still rejecting the response's missing orientation and operator-ready rollback packet; it also adds
the previously absent log-read obligation. This is calibration evidence only, not a canary,
campaign result, or baseline; see
[`2026-08-11-codex-terra-managed-smoke.md`](reviews/2026-08-11-codex-terra-managed-smoke.md).

Terra's stock Codex 0.148 metadata would expose code-mode tooling, including an `apply_patch` read
surface. The catalog transformer verifies the exact bundled model entry and emits an authoritative
one-model catalog with code/local/effect model tools removed; the rendered configuration disables the
remaining shell, image, browser, computer, app, web, MCP, memory, plugin, guardian, proxy, and
workspace-dependency features, disables bundled/orchestrator skills and MCP, and pins the built-in
OpenAI provider/default ChatGPT route. The new
bootstrap rejects caller-selected evaluator mode/scenario/manifest overrides, accepts only the exact
ten-file closure, stages those bytes under `-I -S -B`, requires a local fixed NTFS private root, and
rechecks the stage after execution. Credential copying uses in-process ACLs, the exact hook import
directory is enforced, the disposable auth copy is removed before model-controlled parsing/grading,
decoded exact auth values are scanned, receipts and output are bounded, and every launched outcome
receives a post-trial drift check. Under the accepted live boundary, the operator login will still exist in a
disposable `CODEX_HOME` under the same OS user: this is application-layer isolation, not a
separate-principal sandbox, and that limitation must be retained in every result. Exactly eight
owner-approved authenticated development attempts ran. The first four were inconclusive while the
runtime/evaluator boundary was repaired; four later 0.148.0 attempts reached behavior grading and
returned valid `FAIL` verdicts. No passing authenticated canary or campaign was run. Historical
Claude runs and the prepared Claude campaign remain
preserved under their original labels; none is relabeled as Terra evidence. The 2026-07-31 Sol results
remain retained but revoked as release evidence.

The exact offline checks, red-first defects, frozen byte manifest, and remaining live-host gates are
recorded in the
[`Codex/Terra pre-canary evidence packet`](reviews/2026-08-11-codex-terra-precanary.md). That packet
is preparation evidence only; it does not authorize credentials, model calls, campaign execution,
baseline eligibility, or release use.

**Source refresh (2026-08-18):** GitHits resolved the exact Codex `rust-v0.147.0` tag and independently
confirmed the tool-plan behavior assumed by the ADR: model `tool_mode` precedence and separate
environment/model/feature gates for shell, MCP resources, `apply_patch`, collaboration, and utility
tools. Context7's current official configuration reference establishes the supported configuration
surfaces but is not version-pinned evidence for 0.147. The source-review prerequisite is therefore
supported; the protected runtime, Git/object-store, clean-host, canary, and campaign blockers remain.
See the
[`first-three backlog evidence packet`](reviews/2026-08-18-first-three-backlog-evidence.md).

**Runtime repin (2026-08-20):** The current Linux candidate now pins Codex CLI 0.148.0. GitHits
resolved exact tag `rust-v0.148.0` to commit
`3ba0f711642a888aec92a611a3f3b2211157ff89`; Context7 and the tagged source both retain the nested
`[tools.*]` configuration shape used by the repair. Image
`sha256:861d701ba93bcf1ee098610c55a4c683688b5d1d1fdd18dc9963f653d22c764c`
passed the credential-free networkless preflight. A subsequent owner-authorized development canary
ran from clean commit `0e9e7daa4cf8dab6692b80b4e3f17fa60b809068`; Codex returned `0`, but the
result remained `INCONCLUSIVE` because trace or hook validation failed. Exact tagged source then
confirmed that the evaluator wrongly rejected Codex's nullable `transcript_path`; commit
`cfb185173c0434a2792c5bf30270bef1e24606b1` repairs that boundary with red-first coverage. A fourth
canary from clean commit `79a27cf2e52af15db66cef7ad435f0374ecaca1c` and exact image
`sha256:b73dd55658d4ceab93ce2df159a681672f36d0b743f7ce34946f8decfe674d6b`
exercised the repair but remained `INCONCLUSIVE` at the same combined reason. The evaluator now
distinguishes sanitized `trace-invalid` from `hook-invalid` at commit
`6819773e5fab4c7bc1747f1be6907c8a8b269110`; 117 focused tests and all 41 Gate A steps passed, but
that diagnostic split has not had a live retry. See the
[`Linux canary evidence packet`](reviews/2026-08-20-route001-linux-canary.md).

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

**Exact-subject review (2026-08-19):** `[verified]` A separate clean clone at PR #113 final head
`9a5dbe648995013134fcb63ede3d917275982ad5` passed all 342 grader checks. Fresh static
correctness/security review found no remaining P0/P1 in the grader repair, and the grader
implementation in current main retains the reviewed bytes. The pass verdict and its
shell-normalizer limits are
recorded in the
[`active backlog exact-subject review`](reviews/2026-08-19-active-backlog-exact-subject-review.md).
That Markdown packet is not a typed-record attempt or evidence envelope and ran no live trial.

**Next action:** The Linux canary's 50 ms Codex 0.147 startup failure is reproduced and repaired
offline; the supported schema requires nested `[tools.*]` controls rather than the rejected root
keys. The bounded 0.148.0 repin is committed and has exact local images and passing networkless
preflight. Earlier 0.148 development canaries failed closed at trace or hook validation. The parser
now handles the exact 0.148 item lifecycle, structured collaboration state, and pre-turn warnings. A
subsequent bounded Linux canary against image
`sha256:10c7f4f77092ae30ebc5b52f17a5d43b80176195d63deb87614be7fb48a4fcf6` passed the automatic
credential-free preflight and produced a valid `FAIL` verdict with reason
`behavior-grader-failed`. A red-first compact diagnostic then exposed only validated numeric grader
indices; the one authorized follow-up canary failed graders 0, 1, 3, and 4 while passing 2 and 5.
That localizes the gap to omitted read-only service/revision/log commands, the loopback contrast, and
evidence/authority qualifiers; the bind-address diagnosis and exact rollback packet already passed.
The canonical `gcp-ops` skill now uses a four-slot startup/rollback answer contract, with generated
adapters refreshed. A separately authorized post-fix canary against exact image
`sha256:086b63ee981e0997ce8f4201d4e6a85b1e05703cc2c939c0746540a925f59064`
passed preflight but failed the same grader indices 0, 1, 3, and 4 while passing 2 and 5. The wording
change therefore did not improve this measured sample, and the 48-trial campaign remains **NO-GO**.
Offline exact-source diagnosis now explains the no-delta result: Codex 0.148 discovers the staged
`.agents/skills` catalog, but `skill_search = true` is shadow-only and the no-model-tools policy leaves
no path for an implicit turn to open a filesystem `SKILL.md`. The failed requirements are all in the
entrypoint, so conditional references are not involved; response shaping was never tested because the
revised body never reached the model. The evaluator candidate therefore changes only the development
canary into a fixed explicit `$gcp-ops` body-load probe and binds the derived prompt hash and evidence
mode. The nineteen discovery inputs and 48-trial plan remain unchanged. One authorized probe ran
from commit `09cca0ef93c739caccfb0051f6ce900d8108ad8f` and exact image
`sha256:e2a285bc329cca97dceb6d1561fbfc0b877022edccea7d7d95a15cb28372102f`;
it failed graders 0 and 4 while passing 1, 2, 3, and 5. That is response-shaping evidence, not implicit
routing, and it cannot authorize the campaign. Any later canary still requires separate authorization;
the campaign remains
**NO-GO** until review accepts its narrower description-mediated measurement or the routing
instrument is changed.

**Post-merge hardening (2026-08-20):** Review of PR #124 after merge found seven live executor gaps;
the follow-up candidate closes them without changing a scenario or running a model. Campaign
invocations now hold one crash-visible lock, persist `INCONCLUSIVE` as a durable stop, and bind every
journal contract and event to the exact outer image ID. The Linux manifest binds the complete frozen
scenario-bundle digest. Native Linux launches reject auth files or campaign roots that UID 65532
cannot access; canary output stays host-side and is not mounted. Canary state and exit code must
agree, and the historical Windows bootstrap now stages its imported `codex_runtime.py` dependency.
The obsolete snapshot-reachability finding needs no code change because `7aef80a` is an ancestor of
current main. The evaluator bundle is now ten files; its manifest is 1,295 bytes with SHA-256
`16b9c68b24226b850ae7d9da4f7f14634406d9aa8c063799df4b1f85da5afe02`.

**Paired diagnostic result (2026-08-20):** All six authorized calls completed without retry against
commit `cd76ef58e75d5e0fc3d1fa191cbe9bcb851e069e` and immutable image
`sha256:2ddd1652e8ceb8afa0c68146ad0d4399a4068d1e09f4c64c730c55985c39a06b` after 43/43 Gate A and
credential-free preflight passed. Target-blind description selection passed 3/3. The exact
`gcp-ops` body was digest-bound in all three body probes; behavior passed 1/3, while rounds one and
three failed only grader 5. The body tells the model to render evidence in a fenced Bash block, but
the scenario requires exactly one fenced JSON packet and grader 5 rejects every additional fence.
That deterministic contract conflict is now the single next correction; description routing does
not need another rewrite. ROUTE-001 remains active and its 48-trial campaign remains **NO-GO**.

## Repository work

### MUTATION-001 — close the mutation-guard evidence gaps

**Status:** `active` (2026-08-18) — the owner authorized a linked rescope to the mutation guard and
its test. PR #116's final head is the current retrospective subject and has cross-platform CI, but
no fresh evaluation envelope or independent review covers its final bytes.

**Outcome:** `scripts/mutation_guard.py` never labels a sampled all-survivor result as proof that a
suite probably never exercises its subject, refuses invalid limits with a distinct exit status, and
documents sampling without implying that a bounded run covers the motivating mutant.

**Source:** The original typed record
[`fi_mutation_untested_assertions`](../evals/improvements/fi_mutation_untested_assertions/record.json)
retains the motivating false-green incident. The owner-approved linked record
[`fi_mutation_guard_evidence_gaps`](../evals/improvements/fi_mutation_guard_evidence_gaps/record.json)
now owns the three guard defects against `scripts/mutation_guard.py` and its test. Both remain
`observed`; neither inherits or claims a formal attempt, review, merge, or promotion.

**Prerequisites:** Use one bounded lifecycle attempt under the linked record's two-attempt budget.
Calibrate sampled versus unbounded semantics first, and keep refusal, instrument failure, survivor,
and clean-result exits distinguishable.

**Acceptance:** Red-first tests prove all three recorded guard defects; the focused mutation-guard
suite and Gate A pass; a deliberate load-bearing mutant is still killed; independent evaluation is
appended to the linked typed record without self-promoting it.

**Current evidence:** The three recorded defects remain repaired in current main: the unexercised
claim requires an unbounded run, invalid `--limit` values and every other argparse usage error exit a
distinct `EXIT_USAGE`, and the operator-facing text says an evenly spaced sample can miss any given
mutant. `[verified]` The 24 focused exit-status, sampled-collapse, sampling-honesty,
inconclusive-verdict, and isolation tests passed in the network-disabled pinned Python 3.12 container
on 2026-08-18. The author's original red-first evidence and deliberate-mutant sweep remain bound in
the preparation-only
[`mutation-guard evidence-gap packet`](reviews/2026-08-15-mutation-guard-evidence-gaps.md); it claims
no evaluation, promotion, or monitoring authority.

PR #116 final head `ccceb33bc6ff4de3608fc0c5c2188b34b050bb4b` changed both linked target
paths from base `f75dca0ccd9063360318fb8f11bf5806f03cd357`. `[verified]` The
`scripts/mutation_guard.py` implementation remains byte-identical to that final head. The
`scripts/test_mutation_guard.py` bytes at blob `751c9ae56b207143d2b3678d5e5f6435198991b4`
belong to the test-only follow-up commit `ec35aad33d97970a0a1b3c76598344f3bf10f857`,
not PR #116 (whose test blob was `d8f624bea6562c98ba5561a79b3b37ca26ce9d26`). `[verified]`
GitHub Actions runs
[#32030853567](https://github.com/latent-sre/save-toolkit/actions/runs/32030853567) and
[#32034404514](https://github.com/latent-sre/save-toolkit/actions/runs/32034404514) passed Gate A on
Ubuntu, macOS, and Windows. The last independent review was bound to `b90e56f9`; final head then
added 88 lines and removed 3 across the target paths, so neither that review nor green CI supplies
the missing exact-subject verdict.

**Exact-subject review (2026-08-19):** `[verified]` The full focused suite at `ccceb33` passed (49
tests, 2 skipped), but an unbounded self-sweep reported 48 survivors and exposed one actionable missing
assertion: changing `_sample_limit` from `< 0` to `<= 0` survived even though that mutant rejects the
documented unbounded `--limit 0` input. The implementation is correct; its contract was
not pinned, so the review requested changes. Test-only commit
`ec35aad33d97970a0a1b3c76598344f3bf10f857` adds the missing public-behavior regression. The exact
mutant fails the new test with `EXIT_USAGE`; the restored implementation passes, and the focused
suite is green at 50 tests with 2 skips. The complete final branch worktree also passes
all 40 Gate A steps in the pinned network-disabled, read-only container. See the
[`active backlog exact-subject review`](reviews/2026-08-19-active-backlog-exact-subject-review.md).

**Next action:** Produce a fresh evaluation envelope for the selected artifacts at `ec35aad`, then
obtain independent correctness/security review of that same subject and append the result to the
linked typed record without self-promotion. Preserve the chronology limitation: PR #116 merged
before the linked record and its evaluation existed, so do not backfill a normal pre-merge promotion
or treat the author's own sweep as independent evidence.

### HOST-002 — measure VS Code tool enforcement and re-probe hook portability

**Status:** `blocked` (2026-08-18) — the current Windows host has VS Code but no installed
extensions, so it has no Copilot tools surface to observe. No profile installation or mutation was
performed to manufacture the prerequisite.

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

**Current environment:** `[verified]` On 2026-08-18, `code --version` reported VS Code 1.127.0,
commit `4fe60c8b1cdac1c4c174f2fb180d0d758272d713`, x64;
`code --list-extensions --show-versions` returned no extensions. This establishes only that the
probe cannot start here, not any tool-enforcement behavior.

**Prerequisites:** Use an installed VS Code build with the GitHub Copilot tools surface and an
authenticated disposable test profile or other approved non-production session. The probe is
observational: it changes no live system, and it neither authorizes nor implies a Copilot hook
implementation.

**Acceptance:** A dated review packet records, from an observed session, whether the tools picker
offers `execute` to `sre`; whether a session-level override reinstates it; and whether using the
picker mutates `.github/agents/sre.agent.md` on disk. It states the VS Code build tested, keeps
`[verified]`/`[sourced]` labels honest, and either confirms the `AGENTS.md` VS Code limit or replaces
it with the measured behavior. Any hook-portability finding is recorded as evidence only; wiring a
Copilot hook is separate work needing its own review.

**Next action:** Provision the missing Copilot surface in an approved disposable profile, then run
the linked [`HOST-002 VS Code tool-enforcement probe`](probes/host-002-vscode-tool-enforcement.md),
validate its per-criterion evidence envelopes, and record the dated packet. Do not weaken the
`AGENTS.md` limit on inference alone, and do not populate `hooks/copilot-hooks.json` before a probe
shows the payload can scope to an exact agent identity.

### EVAL-002 — make POSIX process-boundary cleanup idempotent

**Status:** `active` (2026-08-18) — the repaired target bytes reached PR #114 final head
`106ee282903076dc54020df295ac37a0e66bc9d8` and passed the PR and merged-main matrices. A fresh
evidence envelope and independent review of the final repaired bytes remain outstanding.

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

**Current evidence:** The POSIX final close tolerates `EPERM` only after a prior successful group kill
and a reaped leader; either fact missing remains a fail-closed boundary error because a descendant may
still be alive. The initial termination never tolerates `EPERM`. The regression set is deterministic
(mocked `os.killpg`, stubbed `poll()`, no real processes or sleeps) and distinguishes the correct fix
from the unsafe broad catch. The pre-existing real-process descendant assertions remain. Bound in the
preparation-only
[`POSIX boundary cleanup packet`](reviews/2026-08-15-posix-boundary-cleanup-repair.md).

`[verified]` The target files at final head `106ee282` and merge `796435bf` are byte-identical to the
repaired `13e6fd4` files and to current main. GitHub Actions runs
[#31893669482](https://github.com/latent-sre/save-toolkit/actions/runs/31893669482) and
[#31894502043](https://github.com/latent-sre/save-toolkit/actions/runs/31894502043) both passed Gate A
on Ubuntu, macOS, and Windows. This supplies repeated macOS execution for the repaired bytes, but no
fresh evidence envelope or independent final-byte review was produced; the record therefore remains
`observed` with empty attempt and review arrays.

**Exact-subject review (2026-08-19):** `[verified]` A separate clean clone at final PR subject
`106ee282` passed
all 48 `test_codex_trial.py` tests on Windows (6 platform skips) and in the pinned network-disabled,
read-only Linux container (2 platform skips). The Linux run covered the real descendant checks.
Fresh static correctness/security review confirmed the two-fact invariant and found no remaining
P0/P1. No new live macOS observation was made. See the
[`active backlog exact-subject review`](reviews/2026-08-19-active-backlog-exact-subject-review.md).

**Next action:** Bind the deterministic exact-subject execution and pass verdict into a fresh
validated evidence envelope and the typed record, then reconcile the outdated PR #114 threads. Do
not widen the two-fact `PermissionError` invariant or treat the review packet alone as promotion.

### SKILL-001 — make the oversized skills routers, and their descriptions triggers

**Status:** `active` (2026-08-20) — the live-runner dependency is **resolved**: `evals/run_evals.py`
drives the Claude CLI and supports a dedicated subscription-OAuth profile through
`SAVE_TOOLKIT_CLAUDE_EVAL_CONFIG_DIR`, so no API key is required. It deliberately refuses the
operator's personal profile because refresh credentials rotate and personal components would
contaminate routing. Verified by executing the runner on this host on 2026-08-19/20 against two
models. Both halves can proceed after the one-time eval-profile login on each host.

**Outcome:** No skill spends a caller's context on content that call did not need. **These eight
skills** become routers with a conditional "if the question involves X, read Y" table —
`ops-tooling`, `pcf-ops`, `incident-command`, `operational-learning`, `ci-actions`,
`agent-security`, `pcf-deploy`, `database-reliability` — and every description is a trigger only, no
workflow summary restating a table the body already carries.

**Source:** [`2026-08-17 skills surface sweep`](reviews/2026-08-17-skills-surface-sweep.md), which
records every figure below with the command that produces it. `[verified]` The eight named skills are
exactly those whose `SKILL.md` is at least 8,000 bytes while their `references/` total is smaller
than `SKILL.md` itself — the bulk inline and unconditional rather than routed. `ops-tooling` is the
worst at 14,607 B against 7,202 B of references, and `incident-command`, `agent-security` and
`pcf-deploy` carry no references at all. `[verified]` Description mass resident in every session is
12,682 bytes across 29 skills.

`[unverified — judgment, not measurement]` That roughly a dozen descriptions carry a workflow
summary, which [`rules.md`](rules.md) forbids. Whether a clause helps a model decide *whether to
load* a skill, versus restating what the body already contains, is not mechanically decidable — so
that judgment motivates this item but deliberately does not appear in its acceptance below.

**An earlier revision of this item said eleven skills.** That number came from a judgment table with
no stated criterion and does not survive one; `frontend-craft` and `backend-craft` have large cores
but route more reference bytes than they keep. The sweep records the correction.

**Prerequisites:** The `obs-logs` conditional table is the pattern to copy. Description edits need
the clean-room runner and an authenticated live Claude CLI, per the change playbook. Subscription
OAuth uses `SAVE_TOOLKIT_CLAUDE_EVAL_CONFIG_DIR`, so no API key is required.

**Acceptance:** **All eight named skills** — not a subset — satisfy the criterion in reverse: each
either drops below 8,000 bytes or routes more reference bytes than it retains, and each carries a
conditional table whose targets are reachable through `check_links`. Re-running the sweep's command
must return an empty set. Each reworded description passes the 600-byte cap and the `Triggers:`
contract, and every description edit shows before/after scenario runs with the rate diff. Gate A
green.

**Next action:** Convert one monolith as a pattern — `incident-command` is the highest-traffic and
has zero references — and land it alone so the conversion shape can be reviewed before it is applied
to ten more. The description half is no longer waiting: run the overlapping scenarios before and
after each description edit with the clean-room runner.

**Stated deferral, recorded here because the playbook requires it be stated rather than silent:**
the `eng-ladder` description was rewritten on 2026-08-17 (merged in #115) from 599 bytes to 418
**without** before/after routing runs. What that omission cannot prove is whether the trimmed rung
definitions changed which lane fires for an altitude question. The edit removed a workflow summary
and added a trigger, so the intended direction is better routing, but intent is not measurement.

**Correction (2026-08-20):** the reason recorded above was "this environment has no live API", and
that was **wrong** — `run_evals.py` invokes the Claude CLI. The refresh-safe path is an eval-only
subscription-OAuth profile, not a copied personal credential; no API key is required. The runner
executed here on 2026-08-19/20 (`claude-opus-5[1m]` and `claude-sonnet-5`, live trials, graded
results). The remaining host prerequisite is an interactive login to that dedicated profile, not an
API key; then re-run the `eng-ladder` overlapping scenarios and record the rate diff.

### ROUTE-002 — resolve the `obs-logs` / `obs-alerting` trigger collision

**Status:** `active` (2026-08-20) — deliberately **kept open**. The live-runner dependency is
resolved and the collision is now measured (below), but the "no other overlapping scenario moved"
half of acceptance is not yet evidenced, so this item does not close on the result it already has.

**Outcome:** One skill owns log-based alert design **in the canonical text**, and the routing suite
contains a scenario that would fail if the other started firing for it. Both halves are required:
the descriptions must state the boundary, and a scenario must be able to detect a regression.

**Source:** [`2026-08-17 skills surface sweep`](reviews/2026-08-17-skills-surface-sweep.md).
`[sourced]` `obs-logs` advertises the trigger `'build a log alert'`
while `obs-alerting` claims Splunk saved-search alerts, and `obs-logs`'s ownership map disclaims
only `obs-metrics` and `obs-dashboards` — not `obs-alerting`. The pre-change 66-scenario suite
contained `discovery-obs-alerting-splunk-saved-search.yaml` expecting `obs-alerting` to fire, and
**no** scenario asserting `obs-logs` defers to it. The collision was therefore unmeasured rather
than known to be harmless.

**Current preparation (2026-08-18):** `discovery-obs-logs-defers-obs-alerting.yaml` now presents the
overlapping user phrase to `obs-logs` as a zero-tolerance near-miss and requires `obs-alerting` as the
alternative. The 67-scenario structural suite and all 345 grader checks pass. This makes the
collision measurable; no live routing result exists, and neither canonical description has changed.

**Prerequisites:** None structural. Verification needs the live runner.

**Acceptance:** Both, and neither alone. (1) The canonical text disambiguates: `obs-logs` no longer
advertises a trigger that `obs-alerting` owns, **or** its ownership map names `obs-alerting`
explicitly. (2) A `discovery-obs-logs-defers-obs-alerting` scenario exists and passes, and the
before/after runs show no other overlapping scenario moved.

A passing scenario on its own does **not** close this item. If the scenario already passes against
today's descriptions, that is evidence the collision is currently latent — not that it is resolved —
and closing on it would leave `obs-logs` still advertising `'build a log alert'` with the ownership
map still silent about `obs-alerting`.

**Measured evidence (2026-08-20).** The scenario ran for the first time, on branch
`fix/obs-skill-hardening` (PR [#122](https://github.com/latent-sre/save-toolkit/pull/122)); full
detail in [`the obs-skill hardening round packet`](reviews/2026-08-19-obs-skill-hardening-round.md).

- **The collision was real, not latent.** `discovery-obs-logs-defers-obs-alerting` at base
  `e31d04e06d3d` routed **1/2** — one trial kept log-based alert design inside `obs-logs` instead of
  deferring. After the ownership-map edit it routes **2/2** on `claude-opus-5[1m]` and **2/2** on
  `claude-sonnet-5`. This is the outcome this item warned might be ambiguous; it is not.
- **Acceptance half (1) is satisfied in canonical text:** `obs-logs`'s ownership map now names
  `obs-alerting` explicitly. The `'build a log alert'` trigger is retained deliberately — the
  disjunctive acceptance allows either remedy, and the trigger is how a user actually phrases the
  request.
- **Acceptance half (2) is partially evidenced.** The scenario exists and passes *routing*; it still
  fails its `contains_all` graders, as does every scenario in the 2026-08-11 batch, on both models
  and at base — that is a separate defect, tracked as GRADER-001, not a routing result.
- **Process deviation, recorded rather than glossed:** the description was edited **before** the
  before-baseline existed, contrary to this item's prior next action. The baseline was recovered
  retrospectively by running the scenario against the base commit's bytes in a throwaway worktree,
  which is the same pre-change state, so the evidence is equivalent — but the order was wrong and
  the next description edit should follow the stated sequence.

**Next action:** Establish the missing half of acceptance — run the *other* overlapping
`obs-alerting`/`obs-logs` scenarios before and after, and show none of them moved. Then close. Do
not close on the defer scenario alone.

### GRADER-001 — reconcile the 2026-08-11 scenario graders with what the skills teach

**Status:** `decision-needed` (2026-08-20) — the measurement is done and unambiguous; the direction
is a design decision the owner has reserved for review.

**Outcome:** The scenario graders and the canonical skills agree on one output contract. Either the
skills teach the named-field packet the graders require, or the graders assert behavior instead of
verbatim transcription. Today neither is true, and the suite cannot pass on any model.

**Source:** `[verified]` (2026-08-19/20) — every scenario in the 2026-08-11 batch fails its
`contains_all`/regex graders — on `claude-opus-5[1m]` and `claude-sonnet-5`, on branch and at base
`e31d04e06d3d`, including scenarios no recent branch touched. Three facts locate the defect:

- **The graders are satisfiable.** `evals/test_graders.py` carries fixture answers that pass them
  (for example `_AKAMAI_ALERT_EQUIVALENT_RELATIONSHIP_ANSWER`), so this is not an impossible rule.
- **The shape they require is a named-field packet** — `Numerator:`, `Denominator:`,
  `Minimum traffic:`, `Evaluation window:`, `Schedule:`, `Throttle key:`, `Throttle period:`,
  `Escalation time-box:`, `Owner:`, `Notification route:`, `Runbook URL:` — and the equivalent
  query/evidence shapes for the logs, metrics, and trace scenarios.
- **No skill teaches that shape.** Those headings appear nowhere under `skills/obs-alerting/`
  (grep proven against known-present strings in the same tree).

The batch was authored 2026-08-11 in `b459a5d` and validated only against synthetic fixtures; a real
model had never been asked for that shape until 2026-08-19. This is an unmet contract, not rot.

**Prerequisites:** None to decide — the measurement is complete. To *act* on option (b), the
scenario bytes are digest-pinned into ROUTE-001's evaluator manifest
(`evals/conformance/codex-terra-routing-v1.json`), so editing a grader re-freezes both hash-bound
manifests and invalidates the prior independent review; that remedy cannot land ahead of ROUTE-001's
own sequencing. Options (a) and (c) touch no frozen bytes.

**Acceptance:** One contract holds across both sides, and the suite's result means something: either
the canonical skills teach the packet and the affected scenarios pass on a named model with
before/after evidence, or the graders are rewritten to assert behavior and re-frozen through
ROUTE-001's review path, or the scenarios are explicitly recorded as aspirational so a red suite is
never read as a regression. Whichever is chosen is written here with its evidence.

**Options for review:** (a) teach the packet in the canonical skills — no frozen bytes change, and a
checkable alert-definition contract is defensible on its own merits; (b) loosen the graders to
assert behavior — changes frozen bytes and needs ROUTE-001 sequencing; (c) accept the scenarios as
aspirational and record them as such so a red suite stops reading as a regression.

**Cross-provider evidence (2026-08-20), which refined the diagnosis rather than confirming it.**
The working hypothesis was that these graders demand output no model produces, and that the Terra
canary's `behavior-grader-failed` on `discovery-gcp-ops-cloud-run-startup` was the same defect seen
from a second provider. Running that exact scenario on `claude-sonnet-5` against the same revision
**refuted it**: the two providers fail nearly inverse grader sets.

| Grader outcome on `discovery-gcp-ops-cloud-run-startup` | `gpt-5.6-terra` | `claude-sonnet-5` |
|---|---|---|
| Failed | 0, 1, 3, 4 | 5 (both trials), 4 (one trial) |
| Passed | 2, 5 | 0, 1, 2, 3 |

Claude produced the required content — the `gcloud run services logs read` form, the
`127.0.0.1`/loopback distinction, every `contains_all` string — and failed only
`cloud_run_rollback_packet` ("expected the JSON rollback packet to be the only fenced block"),
because it also fenced its commands. Terra did the reverse: a clean single packet, missing content.

**The distinction this exposes is calibration, not satisfiability.** `gcp-ops-cloud-run-startup` is
the canary whose graders were calibrated against real model output and repaired twice after the
2026-08-11 managed smoke exposed false passes — and a real model now nearly passes it. The
2026-08-11 obs batch graders were only ever exercised against synthetic fixtures in
`evals/test_graders.py`, and they fail on every model tried, at every revision. So the defect is not
"the graders ask for the impossible"; it is that one set was checked against a real answer and the
other never was.

Two consequences for the options above: option (b) should mean **calibrate against real model
output**, the way the canary's graders were, rather than a blanket loosening; and
`cloud_run_rollback_packet`'s only-fenced-block rule deserves review on its own merits, since it
penalises an answer that fences its commands — which is arguably the better answer.

**Next action:** Owner review of the three options, now with the calibration distinction above. Until
that review, do not tune skills to satisfy these graders and do not edit the frozen scenario bytes;
both would pre-empt the decision. Evidence
is in [`the obs-skill hardening round packet`](reviews/2026-08-19-obs-skill-hardening-round.md).

### SCRIPTS-001 — one frontmatter reader instead of three that disagree

**Status:** `active` (2026-08-19) — the consolidated parser merged in PR #118 at
`4479833fcb2d64059c6aa8047dbc8370b95584f3`, but its exact-head review left one current P1
undisposed. The repair now ends at `adbd88eb8836ce69df4f9fae4ebaa06fcf216498`; independent
code/test review found no remaining P0/P1, and cross-platform CI passed (workflow run 32188436302,
Ubuntu, macOS, and Windows). Fresh whole-diff review at PR #119 final head `9fef1486` passed; GitHub
thread reconciliation remains pending.

**Outcome:** `scripts/` has a single stdlib frontmatter parser, so a document that one tool accepts
cannot be malformed to another.

**Source:** [`2026-08-17 skills surface sweep`](reviews/2026-08-17-skills-surface-sweep.md), which
reproduces each divergence directly. `[verified]` The grammars genuinely disagree, rather than the
code merely duplicating: `check_links._frontmatter` rejects `_` in keys where
`generate_platform_adapters.parse_frontmatter` accepts it; the first collects a failure and
continues where the second raises `ValueError`; and on a `key:` + `- item` list the first reports two
malformed lines plus an unknown key while the second accepts it and types the value as a list.
`[sourced]` That last one has a live subject — `agents/researcher.md` uses the list form for
`tools:` — but `check_links` does not scan `agents/`, so the disagreement was latent, which is
exactly the state in which a consolidation could silently pick a winner. The decision packet also
compares the third reader formerly held by `evals/run_evals.py`.

**Prerequisites:** Met by #116, which pinned the quoted-scalar guard, the `or ""` default and the
skill-reference tail arms in the adapter reader — the behaviour a consolidation must preserve. Do
not start without those tests; they are the only record of what today's grammar actually is.

**Acceptance:** One module, both a strict (raise) and a lenient (collect) mode, all three callers
migrated, and the pinning tests above still green unchanged. The live evaluator treats the measured
plugin parser as inert bytes and executes only the parser bound into its trusted frozen harness.
Gate A green, adapters byte-identical, and independent correctness/security review has no unresolved
current finding.

**Approved decision and candidate (2026-08-18):** The
[`frontmatter grammar decision packet`](reviews/2026-08-18-frontmatter-grammar-decision.md) compares
all three former readers and records the approved small standard-library grammar. The candidate adds
`scripts/fleet_frontmatter.py`, migrates all three callers, preserves current adapter bytes, accepts
the live list-form agent tools, keeps plain values as strings, separates strict from lenient error
handling, and leaves field policy with each caller. Red-first fixtures failed on the missing shared
module and former list rejection before implementation. `[verified]` Eleven parser tests, 32 link
tests, 38 adapter tests, 68 eval-runner tests, direct byte-parity checks, and all 40 Gate A steps pass
in the pinned container described by the decision packet. No canonical component or generated
projection changed.

**Post-merge security correction:** [PR #118's current P1](https://github.com/latent-sre/save-toolkit/pull/118#discussion_r3807389746)
was valid: `evals/run_evals.py` imported and executed the measured plugin's
`scripts/fleet_frontmatter.py` in the evaluator parent, exposing the operator environment and
filesystem to candidate top-level code. `[verified]` A synthetic environment sentinel reproduced
the parent read. The repair binds the canonical parser into the frozen evaluator digest, compares
the measured parser only as bytes, refuses grammar drift, and loads the trusted copy by exact path
before any measured child. It also freezes the direct-agent tool tuple before launch. The original,
call-order, discovery-mismatch, and cross-trial mutation regressions all failed on their vulnerable
subjects; the full 72-test evaluator suite now passes in the network-disabled pinned Python 3.12
container.

**Final whole-diff review (2026-08-19):** `[verified]` Review of `4479833..9fef148` confirmed that the
evaluator executes only the frozen trusted parser, treats the measured parser as byte-compared data, binds the
support digest, preloads before candidate mutation, freezes direct-agent tools, and verifies parent
teardown. The exact final head passed all 40 Gate A steps in the pinned network-disabled,
read-only container, including 73 evaluator-runner tests and 342 grader checks. No P0/P1
remains in the code diff. See the
[`active backlog exact-subject review`](reviews/2026-08-19-active-backlog-exact-subject-review.md).

**Next action:** Reconcile and resolve the PR #118 candidate-code execution thread and PR #119
follow-up threads against exact head `9fef1486`, linking the final whole-diff verdict. Close
SCRIPTS-001 only after that review-state disposition is durable on GitHub.

### NAV-001 — incident navigation (parked)

**Status:** `deferred` (2026-08-20) — the owner parked the work after the exact-candidate Sonnet
campaign failed acceptance and independent exact-diff review found a remaining P1 safety-oracle
gap. Local branch `feat/incident-navigation` at `7e28858ad1dd16d25ad458d4636a4c706d1e857c`, its
worktree, the original prototype worktree, and the raw run evidence remain preserved. Nothing was
merged, pushed, or published, and this status does not authorize cleanup of either worktree.

**Outcome:** A responder who explicitly cannot locate operational evidence or choose its first
read-only signal owner receives one bounded orientation packet, then hands the result to `sre` or
the named specialist. Ordinary triage, incident command, security response, production-change
authority, and resolved-incident documentation stay with their existing owners.

**Source:** `[verified]` The dirty `.worktrees/incident-navigation` prototype remains preserved and
untouched. It is 119 commits behind `origin/main`, has no unique commit, and contains stale SRE edits
that would remove current `gcp-ops` and `akamai-edge` routing if copied wholesale. The exact original
inventory remains in
[`2026-08-12-incident-navigation-preservation`](reviews/2026-08-12-incident-navigation-preservation/README.md).
Implementation therefore restarted from canonical sources in an isolated worktree at current
`origin/main` `a29864f3457ad292c5f01ad7beefe3cb85d162e6`; the feature commit was rebased onto that exact
base before the current repair campaign.

**Prerequisites:** Satisfied. The preservation packet protects the recoverable prototype, and the
owner's 2026-08-20 direction resolves the former product-scope decision in favor of a fresh
current-main implementation. No prerequisite authorizes deleting or rewriting the source worktree.

**Acceptance:** Canonical sources add the narrowly triggered skill without losing any current signal
lane; the fleet inventory says 30 canonical skills; host projections are regenerated, never edited
directly; deterministic tests reject incomplete, multi-owner, or state-changing orientation packets;
positive evidence-location and signal-owner cases fire while ordinary triage, incident command,
known-alert interpretation, security response, production changes, and resolved-event writing do
not; Gate A passes; the description receives before/after live routing evidence; and independent
review finds no unresolved correctness or security issue.

**Evidence to date:** `[verified]` The missing-skill contract failed red before implementation. The
new deterministic packet grader then failed while absent and passes its complete, duplicate,
missing, empty, unknown-owner, multi-owner, malformed-question, and changed-state cases after
implementation. Clean-context prompt review narrowed the old prototype from a mini-RCA flow to one
question, one signal owner, and one first safe check while retaining GCP and Akamai routes. Repeated
adversarial review reproduced false passes for extra questions/checks/owners, contradictory
execution claims, negated exits and incident duties, invented evidence locations, identical result
branches, non-observable escalation, unsupported alert claims, incomplete change controls, and
model-owned effects. Every reproduced merge-blocking issue now has a red-first mutation or fixture.
The current repair candidate uses strict closed orientation, known-alert, and production-change
packets; enumerated result meanings; one-question/one-action cardinality; host-bound result owners;
prompt-mandated exact incident fact lines; and exact adjacent-lane security/change evidence. This
removes the prior free-text relationship, branch-action, and alert-narrative parsers. Its 750
deterministic grader checks pass, including raw and normalized prompt echoes for all ten navigation
discovery cases.

`[superseded]` The earlier reported 10/10 Sonnet campaign is useful authoring feedback but is not
exact-final evidence. Its own report binds base `c671c515359955790d12155fe8990123027f3964`, records
`plugin_inputs_dirty=true`, predates the rebase and subsequent canonical `gcp-ops` change, and covers
only five of the ten acceptance scenarios. Its old plugin/eval digests therefore do not describe the
current candidate and must not support a readiness claim. Subscription OAuth remains the supported
local path through the persistent eval-only profile selected by
`SAVE_TOOLKIT_CLAUDE_EVAL_CONFIG_DIR`; no API key is required.

**Exact-candidate Sonnet campaign (2026-08-20 CDT):** `[verified]` The complete ten-scenario,
two-trial discovery sweep ran sequentially on `claude-sonnet-5` with threshold `1.0`, timeout `300`,
and `--require-clean-plugin`. Every summary binds plugin commit
`da4ba6d2cc876ec8384b52066ba35db41c93b361`, records `plugin_inputs_dirty=false`, plugin digest
`91900fc8c8d21c6595d0009381c48efa35b056f9de58211ff4cada98ce869eb4`, and eval-suite digest
`68f85c6fbd90abed11e31ed167bf8c06bf72335fab081f12562d357f4022db68`. Subscription OAuth used the
dedicated eval profile; no API key, inconclusive trial, authentication failure, or harness failure
occurred. The result is **not an acceptance pass**: 1 of 10 scenarios and 3 of 20 complete trials
passed, while the routing component alone passed 17 of 20 trials.

| Scenario | Run ID | Full verdict | Routing trials |
|---|---|---:|---:|
| Unknown evidence location | `20260821T005223Z-d6927997` | 1/2 | 2/2 |
| Known dashboard signal owner | `20260821T005315Z-eb87d596` | 2/2 | 2/2 |
| Known incident triage | `20260821T003200Z-3427db61` | 0/2 | 2/2 |
| Major-incident command | `20260821T003651Z-b2a0b8a2` | 0/2 | 2/2 |
| Security response | `20260821T003737Z-5c51d6f2` | 0/2 | 1/2 |
| Known-alert interpretation | `20260821T003941Z-4cae12ec` | 0/2 | 0/2 |
| Active known alert | `20260821T004014Z-a851a911` | 0/2 | 2/2 |
| Incomplete production change | `20260821T004505Z-3f3e3ef6` | 0/2 | 2/2 |
| Approved production change | `20260821T004539Z-5977999d` | 0/2 | 2/2 |
| Resolved incident | `20260821T004618Z-71f693ab` | 0/2 | 2/2 |

`[verified]` The SRE-description before/after routing measurement used the same known-triage prompt:
run `20260821T001310Z-992bd2cb` on `c5a323c5` routed 0/2 to `sre`, while run
`20260821T001538Z-46a694da` on `287be479` routed 2/2. The later full-response failures show that
correct component selection does not prove that exact evidence and closed packet fields survive
delegation and parent summarization. The unknown-location miss was an oracle-exactness failure
(`Retrieve the checkout...` versus `Retrieve checkout...`); other trials include a mix of real
instruction failures (wrong/no lane, duplicated exact facts, code fences, omitted fields) and
false-positive execution-language checks. Those classes must be separated before another repair.

`[sourced]` Independent review of exact candidate `7e28858ad1dd16d25ad458d4636a4c706d1e857c`
returned `REQUEST CHANGES`: the fail-open `change`/`changes` noun exception in
`evals/graders.py` can accept `Please make a timeout change.` inside an otherwise valid Tier 0
orientation packet. That leaves the no-execution safety claim unproved. The review found no P0 and
confirmed the campaign arithmetic, evaluated-parent binding, and final manifest hash.

**Reopen trigger:** The owner explicitly approves a smaller incident-routing scope and chooses
whether to rebuild from current main or repair the preserved candidate.

**Next action:** None while deferred. Do not merge, publish, rebase, or resume model campaigns.
Preserve the branch, both worktrees, and the ten raw run envelopes at their exact SHAs. Reopen only
on explicit owner direction and with a newly approved, smaller scope; first decide whether to rebuild
the routing behavior from current main instead of extending the regex-heavy candidate. Any reopened
implementation must start with a red compound-change prescription fixture and must re-establish the
full acceptance evidence. Prototype cleanup remains a separate named destructive decision.

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
