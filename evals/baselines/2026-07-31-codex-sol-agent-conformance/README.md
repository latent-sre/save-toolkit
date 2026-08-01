# Codex/Sol custom-agent conformance baseline - 2026-07-31

> [!WARNING]
> **REVOKED AS RELEASE EVIDENCE (2026-07-31).** The former runner placed `auth.json` where
> model-controlled read tools could access it and retained parsed final responses. The result below
> is preserved only as historical diagnostic data; it is not a current pass and must not gate merge
> or release. No disclosure was observed, but this method could not prove credential isolation.

## Outcome

**PASS - 6/6 required lanes, 0 failed, 0 inconclusive.** Codex installed all six generated
custom-agent profiles plus the frozen `sre-agents@latent-sre` plugin, then separate main Sol
threads successfully delegated fixed canary tasks to every fleet role: `prompt-engineer`,
`researcher`, `reviewer`, `sde`, `sre`, and `sre-steward`.

This is the standalone Codex custom-agent baseline. It is separate from plugin skill/reference
loading and from the historical Claude/Opus direct-agent and routing baselines.

## Provenance

- Repository commit: `807a35e28b049dc910663c1e2901dc91113aa581`
- Codex CLI: `codex-cli 0.145.0`
- Requested model: `gpt-5.6-sol`
- Observed parent and child model: `gpt-5.6-sol`
- Reasoning effort: `high`
- Sandbox: `read-only`
- Approval policy: `never`
- Plugin inputs dirty: `false`
- Agent inputs dirty: `false`
- Harness inputs dirty: `false`
- Installed agent count: `6`
- Runner SHA-256: `43e9f29d89bd355e5bdf666c47dc5d4353f2bbfb5062b158155026daef5f649e`
- Base-runner SHA-256: `8fdf226d76a21c274b9ec002b2a6bf464bcb5c1f87aec57648e1a710d6820357`
- Manifest SHA-256: `6b8d1233a9eb9f97fabada3fc6aa667ebe29c8d6066621646c155f25a09a32af`
- Plugin-source SHA-256: `744921e4e90c4025d815817d2ad3238e9c98abc58d7ad697cbb393b83082d64a`
- Agent-source SHA-256: `8328effa9f5a31b182635778a715d0c377ec4d843621b38589efd5ac63731bdd`
- Result SHA-256: `a7733b604186d7ba30dbd10996c6c034a9725130855c68399fd7809beadabc6c`
- Raw transcript persisted: `false`

## Structural evidence

- Each lane made exactly one successful `spawn_agent` call with the expected `agent_type`,
  `fork_turns: none`, and fixed task name.
- Each lane produced exactly one child rollout linked to its parent with the expected role and task
  path.
- Every child received the exact installed role's `developer_instructions`; all six instruction
  digests matched the source profiles.
- Parent and child turn contexts exposed Sol, high reasoning, read-only sandboxing, and approval
  policy `never` in every lane.
- Every parent received exactly one child completion. Each child made zero tool calls on its
  text-only task, returned its private instruction canary, and its parent returned the exact JSON
  oracle.
- Stderr contained zero runtime errors across all lanes. The full run completed in 88.8 seconds.

The full sanitized machine result is [`result.json`](result.json). The runner inspected session
rollouts only inside its disposable Codex home, reduced them to the facts and hashes above, and
deleted the complete directory (including its temporary `auth.json`) before writing the result.

## Limits and next coverage

This baseline proves installed-profile loading and explicit delegation for all six agents. It does
not prove:

- implicit custom-agent discovery/routing;
- that Codex enforces the canonical Claude per-agent tool allowlists (Codex custom-agent TOML has no
  equivalent allowlist); or
- Copilot/VS Code runtime conformance.

The observed zero child tool calls are behavior for these canary lanes, not proof that the runtime
removed those capabilities. The read-only sandbox remains the structural boundary for filesystem
effects. Five lanes used an explicit `wait_agent`; the fast `sre-steward` child was delivered
directly before another parent turn, which the harness accepts only when the linked completion is
present.
