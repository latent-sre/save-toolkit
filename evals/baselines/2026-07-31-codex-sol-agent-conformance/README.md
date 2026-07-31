# Codex/Sol custom-agent conformance baseline - 2026-07-31

## Outcome

**PASS - 1/1 required lane, 0 failed, 0 inconclusive.** Codex installed all six generated
custom-agent profiles plus the frozen `sre-agents@latent-sre` plugin, then a main Sol thread
successfully delegated the fixed canary task to the `reviewer` role.

This is the standalone Codex custom-agent baseline. It is separate from plugin skill/reference
loading and from the historical Claude/Opus direct-agent and routing baselines.

## Provenance

- Repository commit: `7ea8a6c162e17c960b62d4a2a48f3b699b8d9adc`
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
- Manifest SHA-256: `b132cfe74c029870e6b9a6e553d035d7ed39912192cf025d160c0a9ec258b824`
- Plugin-source SHA-256: `744921e4e90c4025d815817d2ad3238e9c98abc58d7ad697cbb393b83082d64a`
- Agent-source SHA-256: `8328effa9f5a31b182635778a715d0c377ec4d843621b38589efd5ac63731bdd`
- Result SHA-256: `389a43d4f1f6eaa2afd0c7c01ba323daa665c9773cee39b5ba8e7eaf51a9215a`
- Raw transcript persisted: `false`

## Structural evidence

- One successful `spawn_agent` call selected `agent_type: reviewer`, `fork_turns: none`, and task
  `reviewer_canary`.
- One child rollout linked back to the parent as `agent_role: reviewer` at
  `/root/reviewer_canary`.
- The child received the exact installed reviewer `developer_instructions`; its instruction digest
  matched `a2aaddc0d2847cfa581c8a8c46ba847597f292198885bb491e216e3bfcf8543e`.
- Parent and child turn contexts both exposed Sol, high reasoning, read-only sandboxing, and approval
  policy `never`.
- The parent received exactly one child completion. The child made zero tool calls on this text-only
  task, returned the private instruction canary, and the parent returned the exact JSON oracle.
- Stderr contained zero runtime errors. The lane completed in 12.2 seconds.

The full sanitized machine result is [`result.json`](result.json). The runner inspected session
rollouts only inside its disposable Codex home, reduced them to the facts and hashes above, and
deleted the complete directory (including its temporary `auth.json`) before writing the result.

## Limits and next coverage

This baseline proves installed-profile loading and explicit delegation for `reviewer`. It does not
yet prove:

- the other five agents' behavioral contracts;
- implicit custom-agent discovery/routing;
- that Codex enforces the canonical Claude per-agent tool allowlists (Codex custom-agent TOML has no
  equivalent allowlist); or
- Copilot/VS Code runtime conformance.

The observed zero child tool calls are behavior for this lane, not proof that the runtime removed
those capabilities. The read-only sandbox remains the structural boundary for filesystem effects.
