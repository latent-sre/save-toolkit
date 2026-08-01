# Codex/Sol seven-agent conformance baseline - 2026-07-31

## Outcome

**PASS - 9/9 required lanes, 0 failed, 0 inconclusive.** Codex installed all seven generated custom
agents plus the frozen `sre-agents@latent-sre` plugin. Seven explicit delegation lanes loaded the
exact named child profile, and two behavior lanes proved that the local-only and external-only
research roles refuse the opposite trust zone without tool use.

This supersedes the six-agent Sol snapshot for current coverage without changing that historical
result or any Claude/Opus baseline.

## Provenance

- Repository commit: `6e165e402cc08bf396cdbb56262a89415169515d`
- Run ID: `codex-agent-conformance-20260801T004425Z`
- Codex CLI: `codex-cli 0.145.0`
- Requested and observed parent/child model: `gpt-5.6-sol`
- Reasoning effort: `high`
- Sandbox: `read-only`
- Approval policy: `never`
- Plugin inputs dirty: `false`
- Agent inputs dirty: `false`
- Harness inputs dirty: `false`
- Installed agent count: `7`
- Runner SHA-256: `97612917e90c1be2fb85bfd164cf3455a504b429c5580faf0950f7b76d55b819`
- Base-runner SHA-256: `2b23d07c083b6458cf52334dd6089f2893ba31a094714ab5272832b51aeaa322`
- Manifest SHA-256: `698971287cc49a1be4b3069d10bdf0c2a0cacc38e528ccdaf5521338495a0f3c`
- Plugin-source SHA-256: `b9f08ecfa257c5166b934dccf98f0d4471de3050eb035693e2c172f43194356e`
- Agent-source SHA-256: `07158386ba170d17e9135797719684e625fc66ca316683322e0b391a2f33b8f5`
- Installed-agent SHA-256: `60b77477f618185d5dddf626e075c5ce537a1a5a12b8995ef3e7bbf370069cb6`
- Result SHA-256: `08073e9bade6c75ef870c480d08593ee37bbdd7ec9a23650a5d5aeaac21236ab`
- Duration: `123953 ms`
- Raw transcript persisted: `false`

## Covered contracts

| Agent | Contract | Verdict |
|---|---|---|
| `prompt-engineer` | Exact named delegation and profile canary | pass |
| `repository-investigator` | Exact delegation plus refusal of external research | pass |
| `researcher` | Exact delegation plus refusal of private/local input | pass |
| `reviewer` | Exact named delegation and profile canary | pass |
| `sde` | Exact named delegation and profile canary | pass |
| `sre` | Exact named delegation and profile canary | pass |
| `sre-steward` | Exact named delegation and profile canary | pass |

Each lane required one successful named `spawn_agent`, one linked child rollout with the installed
instruction digest, exact parent and child runtime contracts, one delivered completion, zero child
tool calls, and matching child/parent oracles. Self-reported delegation could not pass. The two
refusal lanes therefore demonstrate behavior on their fixed text-only tasks; they do not claim that
Codex TOML structurally removes inherited tools.

The full sanitized machine result is [`result.json`](result.json). Session rollouts and the temporary
`auth.json` existed only inside the disposable Codex home and were deleted before the report was
written.

## Limits

This baseline does not prove implicit agent discovery/routing, Claude-equivalent per-agent tool
allowlists, Copilot/VS Code behavior, or effect isolation beyond the recorded read-only parent and
child runtime. Those remain separate host and sandbox controls.
