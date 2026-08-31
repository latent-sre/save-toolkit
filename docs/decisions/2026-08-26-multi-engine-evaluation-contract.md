# Multi-engine evaluation without restoring Codex distribution

- **Date:** 2026-08-26
- **Status:** Accepted 2026-08-26
- **Decision owner:** Save Toolkit maintainers
- **Roadmap item:** [`EVAL-003`](../fleet-roadmap.md#eval-003--add-claim-scoped-claude-and-codex-evaluation-engines)
- **Does not supersede:**
  [`2026-08-23-retire-codex-distribution-target.md`](2026-08-23-retire-codex-distribution-target.md),
  [`2026-08-11-codex-terra-routing.md`](2026-08-11-codex-terra-routing.md), or
  [`2026-08-22-agent-discovery-calibration.md`](2026-08-22-agent-discovery-calibration.md)

## Context

The current evaluator has one useful shared scenario and grader vocabulary but one hard-coded host.
`evals/run_evals.py` constructs a Claude command, parses Claude stream events, enforces a Claude
plugin/tool namespace, and writes a Claude-shaped summary. `[verified]` at current `main`
`0e2dfdf752871559720e800e3f24e317ca752e2c`.

The pending `HOST-003` finding is not on `main`. It is carried only by published branch
`docs/sre-agent-review-20260825` at observed tip `c93d8cb`: Claude Code 2.1.243–2.1.246 advertises
an agent-pinned `sre` lane's `Grep` and `Glob` tools even while denying calls, and the existing clean
room denies every reference read. That evidence is `[verified]` as branch content and
`[unverified]` for a future merged candidate. This decision must not silently import those bytes or
their backlog status into `main`; the implementation must either start after that candidate lands or
re-establish the same finding against its own exact base.

Codex remains a supported way to work in this checkout but is not a distribution target. A Codex
evaluation engine therefore may test portable instructions, reference use, deterministic grader
coverage, and divergence from Claude. It may not claim that a Codex projection, plugin install,
native namespace, or per-agent authority boundary exists.

The installed host provides Claude Code 2.1.246 and Codex CLI 0.149.1. `[verified]` No model call was
made while preparing this proposal. Codex documents `codex exec --ephemeral`, explicit sandbox
selection, and sign-in with ChatGPT subscription access. `[sourced]` The owner has selected existing
subscriber sessions for both engines; API keys and API-key provisioning are out of scope.

## Proposed decision

Adopt one shared evaluation core with explicit engine adapters and a claim-aware result reducer:

```text
versioned scenario YAML + deterministic graders
                    |
          versioned execution profile
             /                   \
 Claude native-plugin adapter    Codex resolved-context adapter
             \                   /
          eval-result-envelope/v1
                    |
       claim validation and separate verdicts
                    |
        optional divergence classification
```

The rollout is an **expand-then-migrate** change. The existing scenario schema and default Claude
CLI behavior remain compatible while the adapters and new envelope land beside the legacy summary.
Consumers migrate only after parity tests bind the legacy Claude result to the new Claude adapter.
No old contract is removed in the first implementation.

### 1. Shared core and profiles

Scenario YAML remains engine-neutral and continues to own prompts, targets, deterministic graders,
trial defaults, and thresholds. It does not gain provider command lines, authentication settings,
tool syntax, or engine-specific expected output.

A separate versioned execution profile selects an engine, scenarios, requested claims, model,
reasoning/effort setting when supported, trial count, timeout, and run budget. The runner validates
the entire profile before starting the first model process. A profile requesting an unsupported
claim is invalid, not downgraded at runtime.

Every profile also carries the same explicit cross-engine comparison identity and complete
Claude/Codex model matrix. A separate engine-neutral comparison digest binds that matrix, the
scenario/reference selection, trial count, timeouts, adapter contract version, and both requested
policy contracts. Observed engine-specific policy digests remain separate evidence; two envelopes
are comparable only when their comparison digests match.

Deterministic graders remain the automated regression gate. A model judge, if one is added later,
is calibration evidence only, uses hand-graded fixtures, and never changes a deterministic verdict.

### 2. Engine adapter contract

Each adapter owns only five host-specific operations:

1. resolve and freeze the bytes visible to the engine;
2. construct the non-interactive command and sanitized environment;
3. parse a complete trace into the shared trial record;
4. verify its host boundary and canaries; and
5. declare exactly which claim types it can support.

Adapters do not grade response prose. They return the normalized response and evidence required by
the shared deterministic graders. A timeout, authentication failure, incomplete trace, boundary
mismatch, missing required canary, changed snapshot, or unresolved model identity is
`INCONCLUSIVE`, never `FAIL` and never `PASS`.

### 3. Claim matrix

The following matrix is normative if this proposal is accepted. “Reducer” means the claim can be
made only from two individually valid envelopes, never by either engine adapter.

| Claim | Claude native plugin | Codex resolved context | Reducer |
|---|---:|---:|---:|
| `candidate_snapshot_integrity` | yes | yes | no |
| `native_plugin_loaded` | yes | no | no |
| `native_component_invoked` | yes | no | no |
| `advertised_tool_inventory` | yes | no | no |
| `callable_tool_boundary` | yes | no | no |
| `reference_used` | yes | yes | no |
| `behavioral_contract` | yes | yes | no |
| `deterministic_grader_result` | yes | yes | no |
| `cross_engine_divergence` | no | no | yes |

Codex `reference_used` means that the response proves use of the exact reference in the generated,
digest-bound context bundle. It does not prove a Claude Skill call or native plugin reference read.
Codex `behavioral_contract` means that the same deterministic grader accepted the portable response
under the recorded Codex context. It does not prove Claude routing, Claude tool enforcement, or a
Codex distribution artifact.

The reducer reports one of `agreement`, `behavioral_divergence`, `evidence_gap`, or `incomparable`
per scenario and claim. It never averages pass rates, costs, durations, or verdicts across engines.
Release and candidate views retain the separate Claude and Codex columns.

### 4. Claude native-plugin adapter and HOST-003

The Claude adapter continues to execute one frozen real plugin snapshot in a neutral project and a
strict empty MCP namespace. It records two different tool concepts:

- **advertised inventory:** the base tool names in each coherent Claude init epoch; and
- **callable policy:** the exact runner request, path rules, attempted calls, and observed allow or
  deny outcomes.

The advertised inventory is evidence of what the CLI listed, not proof that a call was permitted.
The callable policy is not inferred from the inventory.

For reference-bearing direct `sre` scenarios, the proposed HOST-003 choice is:

- include only the built-in read tools declared by the selected agent and required by the scenario;
- make `Read`, `Grep`, and `Glob` callable only against the frozen plugin snapshot through
  CLI-supported permission-rule specifiers;
- keep the neutral fixture and every path outside the snapshot denied with non-interactive
  fail-closed behavior;
- require the expected unique terminal canary from each reference whose use is a claim;
- require a traced successful `Read` of every required in-snapshot reference plus a traced denied
  `Read` of one evaluator-created out-of-snapshot sentinel in every reference-bearing trial; and
- reject an advertised undeclared base tool, a successful out-of-snapshot call, an ambiguous tool
  outcome, or a missing canary.

The implementation must probe the exact Claude version's path-rule semantics before relying on
them. Agent frontmatter path specifiers are not the boundary: this repository already records them
as inert for plugin agents. If the command-line permission rule cannot prove both an allowed
in-snapshot read and a denied traversal/out-of-snapshot read, direct reference-bearing measurements
remain `INCONCLUSIVE` and HOST-003 stays open.

### 5. Codex resolved-context adapter

The Codex adapter generates a new private temporary working root for every trial. It contains only:

- the scenario prompt and response schema;
- the selected canonical agent body;
- the transitively selected skill bodies and explicitly linked references;
- a small generated instruction file that explains the bundle layout and forbids mutation; and
- a manifest binding every path and digest plus the required reference paths. Expected canary
  tokens remain evaluator-private until comparison; exposing them in the bundle manifest would let
  a response copy a token without opening the reference.

The resolver rejects absolute paths, `..`, links/reparse points, files outside canonical plugin
roots, duplicate logical paths, size/count budget overflow, changed inputs, and a target whose
transitive references cannot be resolved. It writes ordinary files into the temporary tree, hashes
the completed tree, then makes it read-only before execution. The candidate checkout itself is not
the Codex working directory and is not added as a writable or readable extra root.

Codex runs non-interactively with the existing subscriber session, `codex exec --ephemeral`, an
explicit read-only sandbox, ignored user configuration and execution-policy rules, no session
resume, no MCP configuration supplied by the evaluator, and JSONL output. The adapter never reads,
copies, prints, or persists authentication material. It records `auth_mode: subscriber_session`
only.

`--ignore-user-config` is not assumed to suppress every user-level instruction source. The adapter
must bind the effective ambient policy into `policy_digest`, or fail closed if this CLI version
cannot identify and bind it. “Clean context” here means no candidate checkout, project instruction,
plugin projection, prior session, or evaluator-private grader state beyond the declared bundle; it
does not mean the subscriber account or host executable disappears.

Requested command flags are not observed policy evidence. The runtime trace must report both the
resolved model and the exact effective policy fields required by the adapter. If the installed CLI
omits either identity, the trial is `INCONCLUSIVE` and the envelope carries a null policy digest;
the adapter never substitutes the requested model or requested flags.

Read-only sandboxing does not confine reads. Candidate agent and skill text is untrusted model
context, while subscriber authentication retains host identity state; leaving shell tools enabled
would combine prompt injection, private-data access, and an exfiltration path. The offline adapter
therefore refuses before starting a Codex process. Live activation requires a structural no-tool or
bundle-only read boundary and a negative out-of-bundle probe on the exact CLI. Neither profile
approval nor a prompt instruction can bypass that gate.

Because subscription-backed Codex does not expose a trustworthy per-run dollar charge, the cost
field is explicitly `unavailable`, never zero. Trial count and wall-clock timeout are the enforced
Codex budgets. A live profile still requires the owner's separately approved model, trial count,
per-trial timeout, and total run timeout before the first call.

### 6. Normalized evidence

Add a dedicated `eval-result-envelope/v1` schema rather than changing the existing general
`evidence-envelope-v1`. Every engine result carries the same required fields:

- envelope and run identity;
- engine name and adapter version;
- CLI/runtime version, requested model, and resolved model;
- `auth_mode` without credential material;
- exact candidate Git SHA, clean/dirty state, and candidate-input digest;
- plugin snapshot digest with an explicit applicability flag;
- resolved-context digest with an explicit applicability flag;
- scenario-suite, grader, execution-profile, comparison-contract, and observed-policy digests;
- expected and observed reference canaries;
- requested, supported, and emitted claims;
- per-scenario and overall verdicts;
- start/end timestamps and duration;
- cost value and currency when trustworthy, otherwise a typed unavailable reason;
- trace completeness and integrity status; and
- bounded limitations and artifact digests, never raw credentials or complete transcripts.

Every emitted claim has `type`, `status`, `evidence`, and `limitations`. Schema validation rejects an
emitted claim absent from both the adapter's registered support set and the profile's requested set.
A clean exact candidate SHA is required for promotion-eligible evidence. Dirty-tree runs may be
retained for diagnosis when their actual input digest is recorded, but the envelope must say
`promotion_eligible: false`.

The new envelope is written beside the existing private trace and legacy summary during migration.
Durable review capture remains bounded and escaped. It records claim outcomes and artifact digests,
not full prompts, session IDs, tool payloads, or authentication state.

### 7. Promotion and comparison

No evaluator promotes a candidate. Only a human may accept the exact candidate revision, after
reviewing each engine's separate result and its limitations. A Claude failure cannot be offset by a
Codex pass; a Codex failure cannot erase a Claude native-plugin pass. Divergence is a diagnostic
that triggers investigation or an explicit disposition.

The initial Codex slice is calibration until the owner later accepts a named regression claim and
its stability evidence. This proposal does not reactivate the retired Codex/Terra ROUTE-001
campaign, restore a persistent Codex projection, or convert agent discovery into a regression gate.

## Required red-to-green evidence

Before an implementation can be accepted, focused tests must fail closed for:

1. an unexpected advertised tool;
2. a successful out-of-snapshot read;
3. path traversal, absolute path, link, or reparse-point input;
4. a missing, duplicated, or wrong reference canary;
5. a candidate, plugin, context, policy, grader, or profile digest mismatch;
6. a requested or emitted unsupported claim;
7. an incomplete or mixed trace;
8. an engine name or adapter/version mislabel;
9. a Codex result claiming native plugin, routing, or Claude tool-boundary evidence;
10. a cross-engine reducer presented with different scenarios, candidate SHA, grader digest, or
    incompatible model/run conditions; and
11. any attempt to represent unavailable subscription cost as zero.

Parity tests must also prove that the Claude adapter preserves the existing deterministic grader
outcomes and default CLI selection for representative direct and discovery fixtures. Offline
fixtures prove parser and policy behavior; they do not prove either subscriber session, live host
enforcement, or model behavior.

## Rollout and rollback

1. Land the schema, claim registry, fixtures, and adapter interfaces with no model execution.
2. Move current Claude behavior behind the Claude adapter while retaining the old CLI defaults and
   legacy summary; prove fixture parity.
3. Resolve HOST-003 against the exact merged SRE candidate and exact Claude CLI, including positive
   in-snapshot and negative out-of-snapshot canaries.
4. Add the Codex bundle resolver and adapter offline; prove bundle construction and
   unsupported-claim rejection while keeping live execution hard-disabled.
5. Establish and independently prove a structural Codex no-tool or bundle-only read boundary, then
   present a fixed live-run budget for explicit approval. Run one engine at a time and preserve
   separate evidence.
6. Add the divergence reducer only after both envelopes validate against the same candidate,
   scenario, grader, and policy identities.
7. Migrate durable capture consumers, then separately decide whether the legacy summary can retire.

Before merge, rollback is deletion of the proposal branch. After the expand phase lands, disable the
Codex execution profile and remove its adapter and bundle resolver; the default Claude path and
shared scenario/graders remain. HOST-003 can independently return to `INCONCLUSIVE` without
weakening the prior Claude boundary. No production system or data migration exists.

## Alternatives rejected by this proposal

- **One provider-neutral prompt runner with no adapters.** It hides host-specific isolation and
  creates false equivalence between a real plugin and a context bundle.
- **Generate/install Codex agents and test them natively.** That restores the retired distribution
  target and its unproven authority model.
- **Put engine keys into every scenario.** It forks the shared behavioral corpus and couples grader
  intent to provider command syntax.
- **Use an API-key harness.** The owner selected subscriber accounts; copying or provisioning keys
  adds a credential surface without improving the named claims.
- **Average engine pass rates.** A scalar can conceal a native-host regression and grants no useful
  debugging or promotion signal.
- **Let a model judge decide the gate.** It replaces a deterministic contract with another variable
  model and makes calibration look like promotion authority.

## Approval

Save Toolkit maintainers accepted this ADR on 2026-08-26. The approval covers the architecture and offline
implementation only, including the claim matrix, separate `eval-result-envelope/v1`, HOST-003
snapshot-scoped read boundary, and subscriber-session Codex adapter. It does **not** approve any
model call, paid campaign, push, merge, release, or promotion. The first live Claude or Codex run
requires a separate fixed-budget approval naming model, trials, per-trial timeout, total timeout,
and stop condition.
