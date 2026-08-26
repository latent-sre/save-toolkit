# SKILLS-003 `workflow-graph-engineering` implementation evidence

> **Correction, 2026-08-25.** The conclusion, acceptance-5 summary, and "what was not done"
> footer below were written before the live routing runs and were never updated when those runs
> landed in the routing-matrix section of this same document. They said no live trials ran while
> the section between them records three of them. All three are corrected in place; no measurement
> was changed. See the [addendum](#addendum-2026-08-25) for the merge and the remaining work.

**Conclusion:** The first candidate of the canonical `workflow-graph-engineering` skill is
implemented on branch `work/skills-003-workflow-graph-engineering` from the locally known
`origin/main` `773b596334c5fa5678fbcabad2de0fe35921bd06`. `[verified]` Structural, link, canary,
scenario-schema, grader-fixture, generator, and Gate A checks pass in a pinned container.
`[verified]` Two live clean-room routing batches ran on Sonnet at three trials per scenario, plus
an incumbent baseline batch; routing separation held on four of five scenarios (12/12 trials in
run 2), and the `runtime-selection` seam over-triggered at root 1/3 in both runs. `[unverified]`
`origin/main` could not be refreshed on the authoring host (`git fetch origin` was denied), and the
frozen five-case acceptance exercise on a committed SHA has not run. The development exercise
recorded below is a candidate pass on the uncommitted tree, not that acceptance pass. Human
acceptance of the exact revision remains the only promotion step.

## Exact evidence base

- Base: `origin/main` `773b596334c5fa5678fbcabad2de0fe35921bd06` as known locally on 2026-08-24;
  `git fetch origin` returned an access-rights error from both PowerShell and Git Bash, so
  freshness against the remote is `[unverified]` and must be re-checked before a PR.
- Host: Windows 11 Pro `10.0.26200`; Docker Engine `29.6.1` (linux); Claude Code CLI `2.1.241`.
  The only host `python`/`python3` is the Microsoft Store stub and no `py` launcher exists, so
  every Python step below ran under the AGENTS.md Docker-backed verification rule.
- Verification image: `python:3.12-slim@sha256:2c941e860699f878900b0edc2403613c234d4b32eda3cc9fa7036991a2a63c4a`
  (Python `3.12.14`). Derived image `sre-agents-verify:py3.12.14-pyyaml6.0.3` was built from that
  digest with `pip install --no-cache-dir pyyaml==6.0.3` (the pinned `requirements-dev.txt`
  version). The build used the network once; every verification run used `--rm --network none` and
  a bind mount of the worktree — read-only for checks, read-write only for the single
  `generate_platform_adapters.py --write` run. No socket or credential was mounted.
- Design-artifact exercise: session model `claude-fable-5` `[sourced: session identity]`, one
  fresh-context subagent per case and arm, outputs retained in the ephemeral session scratchpad
  per the `prompt-engineer` rule that scratch candidates and transcripts stay ephemeral.

## Discipline taxonomy (acceptance 1)

Derived from the canonical `agents/` and `skills/` bytes at the base commit. Generated projections
confirmed rendering only.

| Discipline | Canonical name and owner | Path | Input → output | State/authority boundary | Verifier | Neighbouring owner | Overlap or contradiction |
|---|---|---|---|---|---|---|---|
| Prompt engineering | `prompt-engineer` (agent); `agent-authoring` artifact tier | `agents/prompt-engineer.md`; `skills/agent-authoring/SKILL.md`, `references/artifact.md` | failing or missing LLM-facing behaviour → minimal diff with baseline/candidate evidence | prompt text only; schemas, runtime controls, and evaluator defects stay with their layer | `evals/run_evals.py` direct and discovery, one named regression per accepted failure | `sde` (helper code), `reviewer` (injection surface) | none new; this item adds a graph tier below the roster tier |
| Context engineering | `agent-authoring` context method | `skills/agent-authoring/references/context.md` | cold-start packet and evidence budget → bounded, labelled context | context isolation is not authority isolation | human review; no machine contract | `roster.md` handoffs | none; `workflow-graph-engineering` section 12 requires provenance and taint but does not restate selection or compaction |
| Handoff engineering | `agent-authoring` roster method and agent-body packet conventions | `references/roster.md` "Handoffs between contexts"; each agent body | sender state → fixed-field packet (owner, change, evidence, state, non-actions, criteria) | labels copied exactly, never upgraded in transit | review of packet fields | `workflow-graph-engineering` edge payloads | composes: the new skill requires taint and labels on every edge payload; it does not define a second packet format |
| Loop engineering | `agent-authoring` (artifact and roster tiers) | `SKILL.md` Loop Engineering paragraph; `references/artifact.md`; `references/roster.md` "The loop inside each lane" | entry state → bounded gather/action/verify/repeat with verifier, budgets, stops, promotion | inconclusive evidence is never success; human promotion | named regression under `artifact.md`; `docs/rules.md` row | `operational-learning`; `workflow-graph-engineering` cycles | kept separate by both skills' text: a bounded graph cycle is topology, the improvement loop owns verifier and promotion |
| Graph engineering (roster/delegation) | `agent-authoring` | `references/delegation-graph.md`; `validate_fleet.py` `EXPECTED_DELEGATION`; AGENTS.md roster table | agent grants → validated directed graph | main-thread enforcement only | `validate_fleet.py` | `workflow-graph-engineering` | boundary sharpened in `agent-authoring` body and description; not relocated |
| Graph engineering (executable workflow/state graph) | **new** `workflow-graph-engineering` | `skills/workflow-graph-engineering/` | request or existing design → fourteen-section portable design contract or review findings | designs and reviews only; no execution, runtime selection, code, credential, or production access | routing scenarios and grader fixtures only — no schema or validator, per the item's boundary | `sde` (implementation), `stack-profile` (runtime decision), `agent-authoring` (roster) | none found; `prompt-engineer` is the consumer |
| Graph engineering (code/dependency/knowledge/GraphRAG) | not activated (`codebase-atlas` candidate) | none | — | — | near-miss scenario only | `repository-investigator` for local source questions | none; the near-miss scenario keeps it out of the new skill |
| Self-learning → learning engineering | `operational-learning`; `roster.md` "Learning as repository state" | `skills/operational-learning/`; `references/disposition-policy.md` | completed task → disposition with evidence and owner | no autonomous self-modification or background promotion | disposition policy review | `prompt-engineer` for accepted fleet failures | none; the new skill adds no optimizer |

Context accounting: **canonical** — `agents/`, `skills/`, `evals/`; **preloaded** — `AGENTS.md`
through the `CLAUDE.md` import (skill count updated to 31); **generated** — `.github/agents/`
and `platforms/copilot/skills/`, regenerated once (166 files; only `prompt-engineer.agent.md`,
`agent-authoring/SKILL.md`, and the new `workflow-graph-engineering/` projection changed);
**host-specific** — the new skill uses only `name`, `description`, and `argument-hint`, so no
restricting frontmatter is lost on a host that drops Claude-only fields.

## Implementation dispositions

| Discovery | Disposition |
|---|---|
| `routing.expected_alternative` must be a `{kind, name}` mapping, not a bare name; `--validate` rejected the first draft | `worked` — three scenarios corrected; the validator's own message was sufficient guidance |
| No usable host Python (Store stub only; no `py`), so validators, generator, and grader tests could not run natively | `already owned` — AGENTS.md "Docker-backed local verification" covers this; applied with a pinned digest |
| `git fetch origin` denied on the authoring host | `dropped with reason` — host credential state, not fleet state; the owner must refresh and re-check divergence before a PR |
| Skill entrypoint is 7,748 bytes, above the 5,000-byte SKILL-001 candidate screen | `dropped with reason` — the item mandates always-loaded invariants, decision rules, routing table, and the fourteen-section contract; depth sits in six predicate-keyed references, the body is below the fleet median, and SKILL-001's router method applies if a later measurement finds the entrypoint too long |
| `test_graders.py` pins fixed counts per routing batch (`== 20`, `== 5`) | `already owned` — a separate `_ROUTING_WGE_CASES` dict and test follow the batch pattern rather than widening an existing count |
| README's "The fleet itself" area did not describe the new skill | `worked` — area renamed to "The fleet itself and the graphs it designs" |
| The live eval harness needs Python 3.12 and the Claude CLI on the same host; the container has no CLI or credential by design | `dropped with reason` — recorded as the exact set of trials the owner runs before review (routing matrix below) |
| skill-creator workspace conventions would place `evals/` and a workspace directory inside `skills/`, which the generator would project | `worked` — evals and outputs kept in the session scratchpad; nothing non-canonical entered `skills/` |

## Routing matrix (acceptance 2)

Live run 1: `[verified]` clean-room batch `20260824T205218Z-0b59db4b`, CLI 2.1.241, plugin
`773b596` (dirty candidate tree), `--model claude-sonnet-5` (resolved `claude-sonnet-5` on every
trial), `--timeout 600`, 3 trials per scenario, total cost about USD 4. Routing and behavioural
graders are reported separately because the batch failed on the latter, not the former.

| Scenario | Expect | Alternative | Split | Offline schema and fixtures | Live routing (run 1) | Live behavioural graders (run 1) |
|---|---|---|---|---|---|---|
| `discovery-workflow-graph-engineering-approval-effect` | fire | — | regression (promoted after this pass) | `[verified]` echo rejected, compliant passes, incomplete rejected | `[verified]` fired 3/3 | `[verified]` 3/3 |
| `discovery-workflow-graph-engineering-defers-roster-graph` | not_fire | skill `agent-authoring` | regression | `[verified]` | `[verified]` 3/3 — `agent-authoring` at root, target absent | 0/3 on the first grader vocabulary ("nodes", "delegation edge"); transcripts said "lanes", `Agent(...)` grants, "terminal node". Graders widened; `[verified]` offline regrade of the same three transcripts 3/3, echo still rejected |
| `discovery-workflow-graph-engineering-defers-code-graph` | not_fire | inline | regression | `[verified]` | `[verified]` 3/3 — stayed inline | 1/3 on the first vocabulary ("dependency graph"); transcripts said "source-code dependency analysis", "Nodes = packages". Graders widened; `[verified]` offline regrade 3/3, echo still rejected |
| `discovery-workflow-graph-engineering-defers-runtime-implementation` | not_fire | agent `sde` | calibration | `[verified]` | root: `sde` dispatched 3/3, target absent at root 3/3; the nested `sde` loaded the skill 2/3 while implementing — so any-invocation scope failed 2/3 | 2/3 (one trial omitted the verification disclosure) |
| `discovery-workflow-graph-engineering-defers-runtime-selection` | not_fire | skill `stack-profile` | calibration | `[verified]` | 2/3 — `stack-profile` at root 3/3; the skill also fired at root in one trial | 2/3 (the over-triggering trial also missed the platform-boundary grader) |

Corrections made after run 1, all in scenario shape or evaluator vocabulary, none in routing
descriptions: `defers-runtime-implementation` now declares `routing.scope: root` (the contract is
lane ownership; a routed `sde` reading the accepted contract is legitimate support under the
expected root, exactly the case `evals/README.md` reserves root scope for); the two regression
near-miss grader sets were widened against the real transcripts and re-proven to reject the
prompt echo; `approval-effect` moved to the regression split on its measured 3/3. The
`runtime-selection` seam (one root over-trigger in three) is recorded as a calibration result.

Candidate 2 (owner-approved 2026-08-24): the description's exclusions were sharpened to "writing
the code that implements a graph (sde)" and "choosing or standardizing on a workflow engine
(stack-profile)" (575 bytes), and the five friction fixes from the design exercise were applied
to the skill body. Live run 2: `[verified]` batch `20260824T220919Z-d783ef1e`, same CLI, model,
timeout, and trial count as run 1, on candidate 2 plus the scenario corrections above.

| Scenario | Live routing (run 2, candidate 2) | Live behavioural graders (run 2) |
|---|---|---|
| `approval-effect` | `[verified]` fired 3/3 | 2/3 — one transcript phrased intent rejection without "mismatch" / "different intent" / "rejected before dispatch" |
| `defers-roster-graph` | `[verified]` 3/3 correct | `[verified]` 3/3 — widened graders hold |
| `defers-code-graph` | `[verified]` 3/3 stayed inline | 1/3 — two transcripts described the task without any of the six "source-code structure" phrasings |
| `defers-runtime-implementation` (root scope) | `[verified]` 3/3 — `sde` at root, target absent at root | 2/3 — one transcript omitted the verification disclosure |
| `defers-runtime-selection` | 2/3 — one root over-trigger, as in run 1 | 1/3 — the over-triggering trial plus one platform-vocabulary miss |

Reading: routing is stable across both candidates on four of five scenarios (12/12 trials correct
in run 2), and the `runtime-selection` seam is unchanged at one-in-three on both candidates, so at
three trials the sharper wording cannot be shown to help or hurt; candidate 2 is retained as the
clearer text, not as a measured improvement. Every remaining red is behavioural-grader vocabulary
on the *alternative* lane's answer, which is not this skill's contract: `evals/README.md` reserves
the routing-only shape (one sanity grader) for exactly that case. Proposed next correction, not yet
applied: make the four near-miss scenarios routing-only and register them in
`_ROUTING_ONLY_DISCOVERY_SCENARIOS`, keep the positive's behavioural graders with the
intent-rejection vocabulary widened, then run the regression split once before review. The
`runtime-selection` seam stays a calibration measurement with two data points (1/3, 1/3).

Batch 2 (`agent-authoring` ×4, run `20260824T213919Z-68b945df`, candidate 1 description): routing
correct in 12/12 trials (no routing failure); all four scenarios failed *pre-existing* behavioural
graders on vocabulary. Because a description edit cannot change response content, this is an
incumbent evaluator defect rather than a regression from this change; the prior-revision baseline
on `origin/main` bytes was run to prove it.

Incumbent baseline: `[verified]` run `20260824T231543Z-53c0a77c` on plugin `773b596` with no
candidate bytes (the docs-only `work/graph-program-roadmap` worktree), same CLI, model, timeout,
and trials: **0/4 scenarios**, 0/12 trials, every failure a behavioural `contains_any` on the same
vocabulary (`delegation edge`, `human acceptance`, `cost budget`, `import graph` …), and **no
routing failure in any trial**. The candidate batch was marginally better (`loop-engineering`
2/3). Conclusion: the `agent-authoring` regression split is red on the incumbent on this model;
the description edit neither caused nor fixed it, and routing separation held on both revisions.
Disposition: `proposed to roadmap` — the four `agent-authoring` scenarios' behavioural graders
need the same treatment proposed above for this skill's near-misses (routing-only shape, or
vocabulary re-derived from real transcripts), owned by `prompt-engineer`; this change does not
touch them.

Changed routing content and the exact after-change trial set the owner runs (pinned `--model`
and `--timeout`, three trials, numerator/denominator recorded):

- `agents/prompt-engineer.md` description — agent-target discovery is calibration only; the direct
  contract `agent-direct-prompt-engineer-learning-loop` tests behaviour after explicit selection
  and is unaffected by description routing.
- `skills/agent-authoring/SKILL.md` description (new exclusion) —
  `python evals/run_evals.py --run --mode discovery --match agent-authoring --trials 3`.
- New skill — `python evals/run_evals.py --run --mode discovery --match workflow-graph-engineering --trials 3`.

## Artifact behaviour (acceptance 3) — development exercise

Five predeclared cases, one trial each, two arms: `with_skill` (fresh subagent given the
`SKILL.md` path) and `without_skill` (same prompt, no skill). This is a development candidate pass
on the uncommitted worktree; the frozen acceptance exercise on a committed SHA with a clean tree,
recorded input digest, host and CLI version, grader identities, per-call timeout, and cost budget
is a separate later step.

Each run was graded by a separate fresh subagent against the case's predeclared assertions
(skill-creator grader method); one assertion per case is the fourteen-section artifact shape, the
rest are design-substance checks. Tokens and wall clock are per run as reported by the harness.

| Case | With skill | Without skill | Notes |
|---|---|---|---|
| deterministic queue admission, fairness, backpressure, load shedding, worker liveness | 10/10 (149k tokens, 1021 s) | 7/10 (99k, 744 s) | baseline lacked a bounded queue capacity, a designated quarantine repair owner, and the artifact shape |
| model-selected handoff with authority and taint | 8/8 (104k, 602 s) | 7/8 (70k, 415 s) | baseline separated on artifact shape only; both bounded the router's destination set and enforced the cap at the effect boundary |
| fan-out/fan-in with partial failure and late results | 9/9 (121k, 719 s) | 8/9 (80k, 485 s) | baseline separated on artifact shape only; both quarantined late results and bounded fan-out |
| approval-gated external effect with semantic idempotency, `UNKNOWN`, reconciliation | 10/10 (110k, 677 s) | 6/10 (86k, 605 s) | baseline key was proposal-sequence based, had no mismatched-intent rejection before dispatch, and no stated retention floor |
| durable cyclic graph: checkpoint resume vs event-history replay, cooperative vs durable cancel, supersession, evals | 10/10 (120k, 784 s) | 6/10 (91k, 625 s) | baseline had no named cancel safe points, no termination-class table, and no edge/checkpoint lineage |

Totals: with skill 47/47; without skill 34/47 (content assertions 34/42, artifact shape 0/5).
Cost of the skill on this model: about +32% wall clock and +42% tokens per run (four to five
reference files read). No run selected a runtime or claimed execution evidence. Grader-flagged
assertion weaknesses and executor friction are recorded in the workspace `benchmark.json` notes and
feed the next candidate; they do not change this pass's result.

## Safety controls (acceptance 4)

No deterministic validator or machine contract was introduced, per the item's boundary. The
controls exist as prose and as offline grader fixtures:

- `[verified]` The positive scenario's `not_regex` graders reject a checkpoint offered as
  exactly-once proof and a runtime selected inside the design; `test_graders.py` proves the
  keyword-rich incomplete fixture for each of the five scenarios fails and the compliant fixture
  passes (585/585 checks).
- `[sourced]` `references/review-checklist.md` enumerates every rejection predicate the item lists:
  automatic replay of an unknown effect, reused key with mismatched intent, retention shorter
  than the retry or ambiguity window, approval not bound to action and state, admission without
  capacity/fairness/backpressure/liveness, cancellation without cooperative/durable semantics,
  checkpoint resume presented as replay, unbounded cycles, missing terminal states, taint dropped
  at a handoff, and checkpoint-equals-exactly-once claims.
- `[unverified]` As machine-enforced controls these predicates are not proven; a later proposal
  that adds a validator must name its consumer and prove each predicate red-to-green.

## Evidence separation (acceptance 5)

Activation/routing: offline schema and fixtures `[verified]`; live routing `[verified]` on Sonnet
across two candidate batches and one incumbent baseline, reported separately from the behavioural
graders that shared those batches. Artifact quality: development exercise above — a candidate pass,
not the frozen acceptance exercise. Runtime behaviour, durability, provider behaviour, effect
safety, and production readiness: `[unverified]` by construction — nothing was executed.

## Repository integrity (acceptance 6)

All in the pinned container against the worktree, `--network none`:

| Check | Result |
|---|---|
| `scripts/check_links.py` | PASS |
| `scripts/check_canary_tokens.py` (six new unique `q_wg…` tokens) | PASS |
| `scripts/check_stale_names.py` | PASS |
| `scripts/check_test_layout.py` | PASS |
| `scripts/generate_platform_adapters.py --write` | 166 adapter files; PASS; byte-clean on rerun |
| `scripts/gate_a.py` | PASS 6/6 |
| `evals/run_evals.py --validate` | eval suite OK — 89 scenarios (23 direct, 66 discovery, 37 regression) |
| `evals/test_graders.py` | 585/585 |
| `scripts/test_validate_fleet.py`, `test_check_links.py`, `test_canary_tokens.py` | 43, 28, 6 tests OK |
| `claude plugin validate . --strict` | `[verified]` PASS, but on the 2026-08-25 bookkeeping revision and CLI 2.1.245, not on this document's revision — see the addendum |
| Independent exact-revision review | `[unverified]` not requested yet |

## What was not done

No frozen acceptance exercise, no independent exact-revision review, no pull request, no remote
refresh, no runtime or schema selection, no `codebase-atlas`, and no change to any agent's tool
authority or delegation edges. Live routing trials *were* run — see the routing matrix above.

## Addendum 2026-08-25

`[verified]` **Merged.** The candidate landed as commit `f1afd57` on `origin/main` via pull request
[#162](https://github.com/latent-sre/save-toolkit/pull/162) (`work/graph-engineering-and-drills`,
merged 2026-08-25 02:47Z), bundled with the `incident-drill` skill and the graph-program roadmap
documents rather than as a dedicated SKILLS-003 pull request. The branch
`work/skills-003-workflow-graph-engineering` and its worktree no longer exist.

`[verified]` **Base freshness, resolved.** `git fetch origin` is still denied on this host
(SSH publickey), but `gh api repos/latent-sre/save-toolkit/commits/main` returns
`5d94987e37f6b9c9d4fd0f5427ea2269dab36131`, identical to the local `origin/main` ref. The
divergence question this document left open is answered: there is none.

`[verified]` **Routing-only correction, applied.** The correction this document proposed but did
not apply — move the four near-miss scenarios to the routing-only shape and register them in
`_ROUTING_ONLY_DISCOVERY_SCENARIOS` — is implemented on `work/skills-003-bookkeeping`. Each near
miss now carries one `contains_any` sanity grader chosen from the vocabulary its measured
transcripts actually used; the positive keeps its full behavioural set with the intent-rejection
grader widened against the one run-2 transcript that phrased rejection without the first three
terms. Offline: `test_graders.py` 655/655 (baseline 658 — the four scenarios give up three echo
and incomplete checks each, and the routing-only shape adds nine; the arithmetic is exact),
`run_evals.py --validate` OK at 94 scenarios, `gate_a.py` PASS 6/6. `[unverified]` The regression
split has not been re-run live against these graders; that run belongs with the acceptance pass.

`[verified]` **Strict plugin validation, run.** `claude plugin validate . --strict` passes on
CLI 2.1.245 against the bookkeeping revision (base `origin/main` `5d94987` plus the corrections
above). This closes the acceptance-6 row that this document had left unrun; it is evidence for that
revision, not retroactively for `f1afd57`.

**Still open for acceptance:** the frozen five-case exercise (acceptance 3) on the committed SHA
with its full pre-call record, and an independent exact-revision review. The two Codex reviews on PR #162 were taken at branch head `5a50cb3` over
the bundled change, not at this slice's revision.
