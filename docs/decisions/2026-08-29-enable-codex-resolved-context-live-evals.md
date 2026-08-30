# Enable owner-authorized Codex resolved-context live evals

- **Date:** 2026-08-29
- **Status:** accepted
- **Owner:** `latent-sre`
- **Supersedes:** only the unconditional Codex process-start block in the
  [2026-08-26 multi-engine evaluation contract](2026-08-26-multi-engine-evaluation-contract.md)

## Decision

Remove the unconditional `CodexResolvedContextAdapter.require_safe_live_activation()` failure and
allow an explicitly approved Codex execution profile to start its subscriber-backed model process.
The owner accepts the residual risk that `--sandbox read-only` prevents mutation but is not proven
to confine reads to the resolved-context bundle.

This is a risk-acceptance and evidence-scope decision, not a claim that the missing isolation was
implemented. A Codex result does not establish bundle-only reads, credential isolation, native
plugin loading, native component invocation, advertised or callable tool boundaries, or Claude host
behavior. It supports only the claims registered for `codex-cli`; engine verdicts remain separate
and automated evidence never promotes a candidate.

## Retained controls

Every live run still requires a profile that binds the exact engine and model, scenario IDs,
required references, claims, trial count, per-trial timeout, total timeout, unavailable subscriber
cost, comparison contract, approval identity, approval time, and budget ID. Removing this restriction
does not authorize an unspecified or unbounded model campaign.

The adapter continues to require:

- a path-safe, size-bounded, immutable resolved-context bundle outside the candidate checkout;
- `codex exec --ephemeral`, `--ignore-user-config`, `--ignore-rules`, and `--strict-config`;
- `--sandbox read-only`, `approval_policy="never"`, no additional directories, no supplied MCP
  configuration, and no inherited shell environment;
- removal of provider API-key and provider-endpoint environment variables while retaining the
  operator's subscriber identity state;
- structured output, exact reference canaries, and trusted trace metadata for the resolved model
  and effective policy; and
- `INCONCLUSIVE` handling for authentication failure, timeout, nonzero exit, malformed or incomplete
  trace, wrong runtime policy, missing model identity, or canary mismatch.

[Official OpenAI sandbox documentation](https://learn.chatgpt.com/docs/sandboxing) describes
read-only mode as allowing file inspection while preventing editing and commands without approval.
That supports the mutation boundary but does not establish the stronger bundle-only-read claim this
repository previously required. The owner chooses to accept that difference rather than preserve a
permanent process-start prohibition.

## Implementation and compatibility

Adapter contract version 2 removes the pre-process exception and binds `host_read_confinement:
not_claimed` plus the dated owner risk acceptance into the requested policy digest. Comparison
contract version 2 prevents new envelopes from appearing comparable to contract-v1 inputs.

The retired ROUTE-001 and Codex/Sol evaluators remain retired. Codex is not restored as a plugin or
distribution target, and no historical evidence is relabelled.

## Verification and rollback

Before merge, require a red-first runner test proving the former block prevented process start, then
prove the same seam reaches a mocked read-only Codex subprocess and validates its structured trace.
Run the adapter, runner, execution-profile, engine-contract, evidence, resolved-context, full
component, Gate A, and diff checks on the exact candidate.

Rollback restores the unconditional pre-process failure, adapter/comparison contract v1, and the
former rules and operator documentation. Existing v2 evidence remains historical and must not be
relabelled as v1.
