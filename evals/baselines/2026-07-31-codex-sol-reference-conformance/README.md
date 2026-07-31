# Codex/Sol progressive-reference conformance baseline - 2026-07-31

## Outcome

**PASS - 6/6 required lanes, 0 failed, 0 inconclusive.** Codex installed the frozen
`sre-agents@latent-sre` plugin, reported exactly 26 skills, and loaded all 13 required artifacts
from the installed plugin cache before returning each exact deterministic oracle.

This expands the earlier one-skill Codex/Sol baseline to the reference material adapted from the
sister repository. It is separate from the historical Claude/Opus routing and direct-agent
baselines and does not change or relabel them.

## Provenance

- Repository commit: `dd2c21537be0d968c7284940d11b9acb8915d395`
- Codex CLI: `codex-cli 0.145.0`
- Requested model: `gpt-5.6-sol`
- Reasoning effort: `high`
- Sandbox: `read-only`
- Approval policy: `never`
- Plugin inputs dirty: `false`
- Harness inputs dirty: `false`
- Installed skill count: `26`
- Runner SHA-256: `d7a5a9e0890b1c5e2a768b548445b02f4625539c0adeeee05d11bf2a2b879897`
- Manifest SHA-256: `40044e47781685a2a748c71be07f4e929f53c8a25316244fd12d273f45445af0`
- Plugin-source SHA-256: `744921e4e90c4025d815817d2ad3238e9c98abc58d7ad697cbb393b83082d64a`
- Result SHA-256: `23269cf25b89e73b786fcd60a13ff97164c801bf3d114466de86a44aac680253`
- Raw transcript persisted: `false`

Codex 0.145.0 JSONL did not expose a resolved model identifier. The requested model is proven by
the accepted explicit CLI argument, not independently repeated by a trace field. Every lane records
`observed_model_exposed: false` rather than overstating that evidence.

## Covered contracts

| Lane | Required installed artifacts | Verdict |
|---|---:|---|
| Stack profile | `stack-profile/SKILL.md` | pass |
| Backend API design | `backend-craft/SKILL.md` + `references/api-design.md` | pass |
| Database restore drill | `database-reliability/SKILL.md` + `references/restore-drill.md` | pass |
| Frontend design, accessibility, and UX writing | `frontend-craft/SKILL.md` + 3 references | pass |
| TypeScript | `craft/SKILL.md` + `references/typescript.md` | pass |
| Multi-component tooling | `ops-tooling/SKILL.md` + `references/multi-component.md` | pass |

The grader required one simple, successful, full-content read per artifact; exact path containment
under the isolated installed cache; exact command cardinality; and an exact JSON response. The run
recorded 13 verified reads for 13 artifacts in 116 seconds.

The full sanitized machine result is [`result.json`](result.json). Raw JSONL was reduced in memory
to deterministic facts and hashes and then discarded.

## Limits and next coverage

This baseline proves direct progressive loading for the imported reference groups on Codex/Sol. It
does **not** yet prove:

- standalone Codex custom-agent behavior or delegation;
- implicit skill discovery/routing;
- the remaining skill and reference contracts;
- Copilot/VS Code runtime conformance; or
- that the CLI-resolved model matched the requested slug through an independent trace field.

Those remain separate lanes so one runtime or model cannot hide another lane's failure.
