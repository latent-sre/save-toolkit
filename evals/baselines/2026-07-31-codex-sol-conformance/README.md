# Codex/Sol plugin conformance baseline — 2026-07-31

> [!WARNING]
> **REVOKED AS RELEASE EVIDENCE (2026-07-31).** The former runner placed `auth.json` where
> model-controlled read tools could access it and retained parsed final responses. The result below
> is preserved only as historical diagnostic data; it is not a current pass and must not gate merge
> or release. No disclosure was observed, but this method could not prove credential isolation.

## Outcome

**PASS — 1/1 required lane.** Codex installed the frozen `sre-agents@latent-sre` plugin,
reported all 26 skills, loaded the installed-cache copy of `stack-profile`, and returned the exact
canary oracle.

This is a Codex plugin-skill baseline. It is separate from the historical Claude/Opus routing and
direct-agent baselines and does not change or relabel them.

## Provenance

- Repository commit: `2fdfbf35a53d9fa6dbb12317e66ce0e942da026f`
- Codex CLI: `codex-cli 0.145.0`
- Requested model: `gpt-5.6-sol`
- Reasoning effort: `high`
- Sandbox: `read-only`
- Approval policy: `never`
- Plugin inputs dirty: `false`
- Harness inputs dirty: `false`
- Runner SHA-256: `c93b6382f901a920ea75615028192796584377e1bfc9fb19d657b21bc8b4e3d0`
- Manifest SHA-256: `b7910b04ad8cda592029ca381154bd5f39fad9a2b50bda45d85b545127b4189f`
- Plugin-source SHA-256: `744921e4e90c4025d815817d2ad3238e9c98abc58d7ad697cbb393b83082d64a`
- Raw transcript persisted: `false`

The Codex 0.145.0 JSONL trace did not expose a resolved model identifier. The requested model is
therefore proven by the accepted explicit CLI argument, not independently repeated by a trace field.
The result records `observed_model_exposed: false` rather than overstating that evidence.

## Deterministic evidence

- Lane: `codex-sol-stack-profile-direct`
- Oracle: `{"marker":"SRE_CODEX_SOL_OK","canary":"sp_7c2e"}`
- Verdict: `pass`
- Command count: `1`
- Matched scope: `installed-cache`
- Simple skill-read command: `true`
- Full output matched: `true`
- Skill SHA-256: `49dc2d02f3bf95ab33341df6c0279b481ee5d24668269d2ed67cff4f0cfb6027`
- Transcript SHA-256: `56873544e3e88af73e530ceb903dd3d51917795e2c3a1de579938278b51e9a8a`

The full sanitized machine result is [`result.json`](result.json). Raw JSONL was reduced in memory
to deterministic facts and hashes and then discarded.

## Limits and next coverage

This baseline proves local marketplace registration, exact plugin identity, 26-skill installation,
and one direct installed-skill contract on Codex/Sol. It does **not** yet prove:

- standalone Codex custom-agent behavior;
- implicit skill discovery/routing;
- the other 25 skills' behavior;
- Copilot/VS Code runtime conformance; or
- that the CLI-resolved model matched the requested slug through an independent trace field.

Those remain separate lanes so one host or model cannot hide another lane's failure.
