# SKILL-001 Phase 1 router-slice closure evidence

**Status:** Historical evidence captured on 2026-08-24. This document is not a task list.
[The fleet roadmap](../fleet-roadmap.md) is the only live backlog.

This record preserves the per-slice measurements, review corrections, verification, and explicitly
unverified behavior removed when the live SKILL-001 entry was compacted. Batch names and interim
candidate ordering below are historical; they do not authorize resuming a completed slice.

`[verified]` The required 2026-08-23 remeasurement on tree `8ea628d` found 30 entrypoints totaling
232,717 bytes and confirmed the same nine candidates. Exact per-skill bytes and reference totals are
recorded in the audit's
[`Batch 2 remeasurement`](2026-08-22-skill-clarity-routing-graph-audit.md#batch-2-remeasurement-and-first-router-candidate).
The first candidate reduces `incident-command` from 11,056 unconditional bytes to a 3,903-byte
entrypoint routing 9,977 reference bytes across three conditional lanes while retaining shared
authority and safety controls.

`[verified]` Candidate `cbda2b9` passed its focused static checks. Fixed run
`20260823T134724Z-a1b538a1` was overall inconclusive after two 180-second timeouts, but both raw
traces invoked `save-toolkit:incident-command` before the model became stuck trying to read linked
references in a discovery harness that denies `Read`. Activation is observed 2/2;
reference-dependent response behavior remains `[unverified]`. The audit records the exact evidence
and the disagreement between raw tool-use events and the timeout summary's empty derived invocation
fields.

The owner then authorized one timeout-calibration run on unchanged model-facing bytes. `[verified]`
Run `20260823T140515Z-83460c27`, clean commit `ea4cf74`, `claude-sonnet-5`, two trials, and a
540-second timeout passed 2/2. Trial durations were 263.594 and 40.531 seconds, so the first result
demonstrates that 180 seconds was an insufficient ceiling. The longer run is not rate-comparable to
the shorter run; it closes the after-change activation check under its own recorded condition. The
global runner default remains 300 seconds, and detailed reference-dependent behavior remains outside
the discovery evidence layer.

`[verified]` After PR #142 merged, the exact next-slice base
`17b4ba97aa0b8091a1b3bbff462bfc9bbae0d109` carried 30 entrypoints totaling 225,614 bytes and eight
remaining candidates: `agent-security`, `ci-actions`, `database-reliability`, `ops-tooling`,
`pcf-deploy`, `pcf-ops`, `production-change-gate`, and `stack-profile`. `ops-tooling` was the largest
at 14,427 unconditional entrypoint bytes versus two references totaling 7,202 bytes.

`[verified]` The second bounded implementation commit
`3b9559412ef06c1ae3e8a19e82fe23395a183ac0` converts only `ops-tooling`. Its unchanged description
now opens a 6,502-byte entrypoint that keeps the right-size exit, spawn-degradation behavior,
human-only production authority, evidence boundary, self-contained handoff contract, bounded phase
exits, and conditional `stack-profile` requirement. Six routed references total 17,897 bytes across
requirements/design, CLI, multi-component, build, review, and verification/handoff lanes. The full
canonical entrypoint corpus falls to 217,689 bytes and the mechanical candidate set to seven.

Those sizes are immutable Git-object measurements, not checkout byte lengths: run
`git ls-tree -r --format='%(objectsize)%x09%(path)' <sha> -- skills`, sum only
`skills/<name>/SKILL.md`, and use `git cat-file -s <sha>:skills/ops-tooling/SKILL.md` for the focused
entrypoint. Apply the same `ls-tree` command to `skills/ops-tooling/references` for the reference
total. The earlier values came from a line-ending-sensitive working tree and were not reproducible
from the commits they named.

The owner authorized one fixed five-agent fresh-context artifact exercise before commit. `[verified]`
Three lanes passed on the first candidate: early exit, independent review, and verification/handoff.
The requirements/design lane found the missing conditional `stack-profile` dependency and a stale
host-specific instruction in the environment-card asset; the multi-component build lane found that
the contract template loaded even when a project-owned contract already existed. The pre-commit
correction added the conditional `stack-profile` route, repaired the host-specific asset text, and
added a direct template predicate, but the agents were not rerun under the fixed budget. Independent
review of exact branch revision `270aab16cdc7c2dbd34557d1c395f550058a2634` later showed that the
multi-component procedure still bypassed that predicate and unconditionally instantiated the
template. It also found the non-reproducible byte counts above.

`[verified]` Follow-up commit `80c7c331b06bb5b593d8663475d0bbaa995e3880` makes the existing
project-owned versioned contract authoritative and limits the bundled contract template to the first
HTTP contract when none exists; its own header forbids duplicate contracts and applying its HTTP/RFC
9457 shape to non-HTTP interfaces. The router now separates procedure lanes from five optional asset
lanes: missing environment card, missing plan, new Python CLI without a project starter, first HTTP
contract when no project-owned versioned contract exists, and a drafted/replaced/relaunched builder
packet. A bounded fresh-context static regression passed the existing-contract, established-CLI,
existing-packet-validation, and existing-environment/plan cases without loading those assets. This
retest did not test host activation, final-response quality, or runtime behavior; those remain
`[unverified]` for the exact commit.

At `80c7c33`, the `ops-tooling` entrypoint is 6,922 immutable bytes, its six references total 18,709
bytes, the 30-entrypoint corpus totals 218,109 bytes, and the mechanical candidate set remains seven.

`[verified]` PR #143 merged exact head `2927a2120da0494195e8d901570963a15bdb877a` into `main` as
`14b7aeae7c22aff3b50800ef262123adb9a48bc3`. A bounded retrospective review of that immutable merge
found no P0/P1 issue and one merge-safe P2: the paragraph above counted four optional asset lanes
while naming only four of the five implemented predicates. The corrected count and omitted HTTP
contract predicate now match the Git object; no skill or projection byte changed in that correction.

`[verified]` The post-merge remeasurement on `14b7aea` keeps 30 entrypoints totaling 218,109 bytes
and seven candidates. `agent-security` is the largest at 13,629 unconditional bytes with no routed
references, so it is selected alone for the third bounded router slice.

`[verified]` The exact implementation and remediation each passed direct link and fleet validation,
strict Claude plugin validation, 112 focused link/adapter/fleet/canary tests (three skips), and
`git diff --check`; each canonical edit was regenerated once, producing 282 adapter files with byte
consistency. No description or eval scenario changed, no existing scenario targets `ops-tooling`,
and no paid routing run was required or performed.

`[verified]` Third bounded implementation commit
`e5838598c4d8f7ee52e788045c68f6b1033385ab` converts only `agent-security`. Its byte-identical
description now opens a 7,971-byte entrypoint that keeps the prompt-injection premise,
lethal-trifecta and Rule-of-Two decision, host-authority verification, cross-agent taint and
delegation limits, evidence labels, action-boundary validation, active-compromise stop, five-question
review, output contract, and human-approval handoff. Two explicit references total 7,188 bytes:
current-fleet/integration/MCP/host controls and the OWASP LLM Top 10 crosswalk. The 30-entrypoint
corpus falls to 212,451 bytes and the mechanical candidate set to six.

A fixed three-case fresh-context artifact exercise was attempted before commit. `[verified]` The
thread limit admitted two cases and rejected the OWASP case before execution. The risky
webhook/secret/MCP/egress case loaded only integration controls and returned the required structural
containment. The nominal core-only case unnecessarily loaded that reference because its first
predicate was too broad and also found an overclaim that a read-only reporter could not leak through
its output. One consolidated correction narrowed the predicate to secrets, external actions, host
enforcement, or tool-result envelopes and constrained the report channel while keeping its output
`[UNTRUSTED]`; the agents were not rerun under the one-candidate bound. Exact-candidate conditional
loading, OWASP response quality, host activation, and runtime behavior therefore remain
`[unverified]`.

`[verified]` One independent static review of exact commit `e583859` approved the complete immutable
nine-file canonical-plus-projection diff with no findings and no P0/P1. The reviewer confirmed the
description identity, always-loaded invariants, explicit reachable predicates, current fleet facts,
and absence of schema, runtime, capability, or authority expansion. It did not run tests, validators,
external source refreshes, or host probes.

`[verified]` The exact candidate passed the skill quick validator, direct link/fleet/roadmap/stale-name
validation, strict Claude plugin validation, 112 focused link/adapter/fleet/canary tests (three
skips), and `git diff --check`. The one required regeneration produced 286 adapter files with byte
consistency. Two direct calibration scenarios target `agent-security`, but its description routing
content is unchanged; no paid routing run was required or performed.

`[verified]` PR #145 merged final head `97008f442f282912e1e682af192811d833a0c8e5` into `main` as
`a10c8820ad569fcf2ef4f07866ef1836c081e3b1`. Its two review findings corrected the OWASP title and
an unreachable crosswalk control before merge; Linux validation, Windows validation, and the Claude
plugin contract passed on that final head. The final entrypoint remains 7,971 immutable bytes and
its two references total 7,231 bytes. These merge facts do not upgrade the earlier independent
review from `e583859` to the final head.

`[verified]` The required current-main remeasurement on
`80cd023b8606f4b94f7a8b508a70e2ed255e44aa` finds 30 entrypoints totaling 212,440 bytes and six
remaining candidates. `ci-actions` is largest at 12,197 unconditional entrypoint bytes with one
reference totaling 1,620 bytes, so it is selected alone for the fourth bounded router slice.

`[verified]` Fourth bounded implementation commit
`a5c425d69eaf5211226db81e42ddc277496dfd62` converts only `ci-actions`. Its byte-identical
description now opens a 7,282-byte entrypoint that keeps the build-once/promote contract,
project-owned-workflow precedence, human-only deployment authority, untrusted-input boundary,
least-privilege permissions, immutable action/image pins, event-injection and fork isolation,
protected-environment credential rule, non-cancellable production concurrency, layered verification,
and evidence-bound handoff. Three explicit references total 10,706 bytes across security/provenance,
execution/runners, and PCF deployment; the starter asset is available only when a new reusable
workflow is required and no project-owned workflow or starter exists. The 30-entrypoint corpus falls
to 207,525 bytes and the mechanical candidate set to five.

A bounded pre-commit static exercise covered invariant retention and an existing-workflow fork-cache
case against canonical blobs that are byte-identical in `a5c425d`. `[verified]` The cache case loaded
only the security/provenance and execution/runner references, kept the bundled starter unloaded,
proposed a narrow project-owned-workflow change, and preserved the fork/secret boundary; runtime
effectiveness remains `[unverified]`. The invariant review found one contradiction: the broad
credential predicate made the entrypoint's reference-free missing-secret diagnosis unreachable. The
correction limits the route to credential/OIDC design or changes, and a focused reread passed. This
was static artifact evidence, not host activation or runtime behavior.

`[verified]` Independent review approved exact commit `a5c425d69eaf5211226db81e42ddc277496dfd62`
with no findings and zero independently found P0/P1s. The candidate passed the skill quick validator,
direct link/fleet/roadmap/stale-name validation, strict Claude plugin validation, 102 focused
link/adapter/fleet/canary tests (three skips), generator byte validation, and `git diff --check`. The
one required regeneration produced 144 supported Copilot adapter files; the retired
`plugins/save-toolkit` root remains absent. No scenario targets `ci-actions`, its description routing
content is unchanged, and no paid routing run was required or performed. Gate A remains the single
push-boundary check.

`[verified]` Remeasurement of exact implementation commit `a5c425d` left five candidates and selected
`pcf-deploy`, then the largest at 10,351 unconditional entrypoint bytes with no routed references,
for the fifth one-skill slice.

`[verified]` PR #147 merged exact head `1034bc9a0807974293c667eb2938e2cbbb63acc7` into the PR #146
branch as `f6eeb59e741a859bbdc9cc42c900fe2e9f297c92` on 2026-08-23. PR #146 then merged that exact final
head into `main` as `829af56032ab921fdde208ae7c57f4ae329c9293`. Linux validation, Windows
validation, and the Claude plugin contract passed on `f6eeb59`; both reviewed implementation commits
are ancestors of the resulting `main`.

`[verified]` Fifth bounded implementation commit
`af9cb4bf7ba2a04a557160b975dd1b22913ae7bc` converts only `pcf-deploy`. Its byte-identical
frontmatter, including the manual-only controls, now opens a 7,854-byte entrypoint that keeps
agent-never-executes authority, release/change gate stop, exact artifact/target/approved-manifest
identity and diff, action-boundary revalidation, secret and human-only `cf env` rules, rollback
non-reversibility, owner maps, common strategy choices, target uncertainty, abort criteria, and the
evidence handoff. Three explicit references total 8,959 bytes across manifest/blue-green,
rolling/canary/revisions, and configuration/scaling; the starter manifest is available only when a
new manifest is required and no project-owned manifest or starter exists. The 30-entrypoint corpus
falls to 205,028 bytes and the mechanical candidate set to four.

A bounded pre-commit static exercise covered invariant retention and a valid-gate blue-green plan
with an existing project manifest. `[verified]` The plan loaded only the manifest/blue-green
reference, kept the starter asset and unrelated procedures unloaded, remained human-run, and named
phase-specific rollback; target behavior remains `[unverified]`. The invariant review found two
production-safety ambiguities: approval did not bind immutable manifest identity, and an instruction
asked for rollback commands even at irreversible boundaries. One correction binds the approved
manifest revision/hash and diff through action-time revalidation and requires rollback, recovery,
compensation, or an explicit irreversible declaration. A focused reread passed both corrections.

`[verified]` Independent review approved exact commit `af9cb4bf7ba2a04a557160b975dd1b22913ae7bc`
with no findings and zero independently found P0/P1s. The candidate passed direct
link/fleet/roadmap/stale-name validation, strict Claude plugin validation, 102 focused
link/adapter/fleet/canary tests (three skips), generator byte validation, and `git diff --check`. The
one required regeneration produced 147 supported Copilot adapter files. The generic Codex
skill-creator quick validator is not applicable to this existing manual Claude skill: after an
introduced incompatible prose character was removed, it still rejected the pre-existing,
repository-required `compatibility` and `disable-model-invocation` keys. The repository validators
and strict Claude plugin validation are the governing contracts.

Two scenarios target `pcf-deploy`: a negative discovery regression and a direct behavioral
calibration. Its description and manual-only routing metadata are byte-identical, so neither is an
affected routing scenario; no paid routing run was required or performed. Host activation,
final-response quality, and deployment runtime behavior remain `[unverified]`. Gate A remains the
single push-boundary check.

`[verified]` Post-merge remeasurement of exact current-main commit `829af56` leaves four candidates.
`pcf-ops` is largest at 10,173 unconditional entrypoint bytes with 1,543 routed reference bytes. It
is not started automatically; current-main inspection and an owner-accepted one-skill scope come
before any edit.

`[verified]` After PRs #149–#153 merged, the required remeasurement of exact current-main commit
`2294832ab0d4edc1199766530f4bea37367db197` found 30 canonical entrypoints totaling 195,009
immutable Git-object bytes. `stack-profile` was the sole remaining skill meeting this item's
criterion: an 8,673-byte entrypoint and zero reference bytes. The three newly merged routers no
longer met it, and no historical candidate ordering was reused.

`[verified]` Exact post-review implementation commit
`1cdecbd2a25b4fa2578e217f48e901169b43025d` converts only `stack-profile`. Its 425-character
description retains every trigger, use condition, and named alternative while replacing the false
single-file maintenance promise with the canonical skill-bundle boundary. It opens a 6,412-byte
entrypoint that keeps the current PCF/GCP runtime truth, pending landing-runtime decision,
no-self-managed-Kubernetes rule, three-state evidence contract, additive/no-retirement observability
decision, incident/change/documentation ownership, stay-in-lane and platform boundaries, and the
default-inherit/generation-alias/full-model-ID rules accepted in PR #153. Three explicit references
total 5,421 bytes across observability inventory and lifecycle, application/CI/runner/data-store
facts, and the current Copilot picker order. The 30-entrypoint corpus falls to 192,748 bytes and the
mechanical candidate set is empty.

A fixed five-agent fresh-context artifact exercise covered the shared runtime boundary, each of the
three conditional lanes, and a two-lane combined request. `[verified]` Every case read exactly the
matching reference set: zero for the runtime-only question, one each for observability,
application/data, and Copilot models, and observability plus application/data for the combined case.
The combined case initially invented an unsupported `[inference]` evidence state; one correction
made the entrypoint explicitly retain the fleet's three-state contract, and the same fifth agent's
focused retest used `[unverified]` for the inference with no routing or conclusion regression. These
are static fresh-context artifact results, not host activation or runtime-behavior evidence.

One independent read-only review of the pre-fix exact candidate found a P1 behavior-preservation
gap: the advertised broad `"what's our stack"` request matched no conditional row and could load
zero references. The current-main conformance pass also found the superseded blanket model-pin rule,
the false single-file promise, and an observability reference that claimed its missing parent owned
the additive-stack rule. `[verified]` The correction adds an explicit broad row, reconciles the
accepted alias-versus-full-ID policy, names the canonical bundle/projection boundary, and returns the
additive/no-retirement decision to the entrypoint. Two clean-context regressions then showed the
literal broad request loading all three and omitting no requested stack category, and the model case
permitting a cost/latency-justified `sonnet` alias while rejecting a full ID and refusing to treat the
Copilot picker order as Claude-agent authorization. No automated review loop was started.

A subsequent PR review of exact published head `8f2b62c` found two remaining context-selection gaps:
a narrow edge/CDN/WAF/RUM request and a general CI-platform/tooling request could omit the reference
that owns the requested inventory, and the setup instructions still pointed only to the entrypoint.
`[verified]` Fix commit `3a056e5d44c7b66d00ec8f0673a4b731d606a301` adds those predicates to
the router and matching reference lead-ins and points setup at the canonical skill bundle. The
description remains byte-identical. Direct link/fleet/roadmap/stale-name validation, 115 focused
link/adapter/fleet/frontmatter/canary tests (three skips), strict Claude plugin validation, and
`git diff --check` passed after the one required regeneration. Model-selected reference loading for
the two new narrow requests remains `[unverified]`; no discovery scenario targets this internal
reference-selection boundary, so no paid routing run was added.

`[verified]` The exact candidate passed direct link/fleet/roadmap/stale-name validation, read-only
adapter verification, 115 focused link/adapter/fleet/frontmatter/canary tests (three skips), strict
Claude plugin validation, and `git diff --check`. The review-fix canonical pass regenerated 158
adapter files with byte consistency. The existing `discovery-runtime-boundary` scenario targets
`stack-profile`, but its description's routing elements are unchanged; only the inaccurate
maintenance sentence changed. No affected routing scenario or paid live run was required or
performed. Gate A remains the single push-boundary check.
