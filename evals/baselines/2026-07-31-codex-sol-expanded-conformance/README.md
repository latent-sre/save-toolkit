# Codex/Sol expanded skill conformance baseline - 2026-07-31

> [!WARNING]
> **REVOKED AS RELEASE EVIDENCE (2026-07-31).** The former runner placed `auth.json` where
> model-controlled read tools could access it and retained parsed final responses. The result below
> is preserved only as historical diagnostic data; it is not a current pass and must not gate merge
> or release. No disclosure was observed, but this method could not prove credential isolation.

## Outcome

**PASS - 11/11 required lanes, 0 failed, 0 inconclusive.** Codex installed the frozen
`sre-agents@latent-sre` plugin, reported exactly 26 skills, and produced 18 verified full-content
reads across the selected skills and progressive-disclosure references before returning every exact
oracle.

This supersedes the smaller Sol skill/reference snapshots for current coverage without rewriting
them. Historical Claude/Opus results remain separate and unchanged.

## Provenance

- Repository commit: `6e165e402cc08bf396cdbb56262a89415169515d`
- Run ID: `codex-skill-conformance-20260801T004132Z`
- Codex CLI: `codex-cli 0.145.0`
- Requested model: `gpt-5.6-sol`
- Reasoning effort: `high`
- Sandbox: `read-only`
- Approval policy: `never`
- Plugin inputs dirty: `false`
- Harness inputs dirty: `false`
- Installed skill count: `26`
- Runner SHA-256: `2b23d07c083b6458cf52334dd6089f2893ba31a094714ab5272832b51aeaa322`
- Manifest SHA-256: `9d17427e82aa475aae69ceb4dc5bcae8b0c94fdf0d635023718bb52c4fc3feab`
- Plugin-source SHA-256: `b9f08ecfa257c5166b934dccf98f0d4471de3050eb035693e2c172f43194356e`
- Plugin-inventory SHA-256: `f621d4919df3ef8bf5c55c2dd3d53d32ea550ef045a470a5d9fa9fed01332f5a`
- Result SHA-256: `5ef7b13cbc9f8d162a52d006bfe7dd016b543c3937bd964194e9212b6b7063c9`
- Duration: `163516 ms`
- Raw transcript persisted: `false`

Codex 0.145.0 JSONL did not expose a resolved model identifier for these lanes. The requested model
is bound to the explicit accepted CLI argument, and every result records
`observed_model_exposed: false` instead of overstating independent model evidence.

## Covered contracts

| Lane | Required installed artifacts | Verdict |
|---|---:|---|
| Stack profile | `stack-profile/SKILL.md` | pass |
| Backend API design | `backend-craft/SKILL.md` + API reference | pass |
| Database restore drill | `database-reliability/SKILL.md` + restore reference | pass |
| Frontend design, accessibility, and UX writing | `frontend-craft/SKILL.md` + 3 references | pass |
| TypeScript | `craft/SKILL.md` + TypeScript reference | pass |
| Multi-component tooling | `ops-tooling/SKILL.md` + multi-component reference | pass |
| Release rollback gate | `release-gate/SKILL.md` | pass |
| Production authorization gate | `production-change-gate/SKILL.md` | pass |
| Manual PCF deployment gate | `pcf-deploy/SKILL.md` | pass |
| Agent-security trifecta | `agent-security/SKILL.md` | pass |
| Two-window burn-rate alert | `obs-alerting/SKILL.md` | pass |

The grader required exact command cardinality, one simple successful full-content read per required
artifact, containment under the isolated installed plugin, and an exact JSON oracle. The manual-only
PCF lane additionally returned the source-bound `pd_4c91` canary. Multiple-command failures retain
only sanitized hashes, lengths, status, and allowlisted-path facts; raw argv and output are not
written.

The full sanitized machine result is [`result.json`](result.json). During calibration, the first
expanded run exposed contradictory prompt/read requirements (7/11), and two follow-up runs isolated
manual-only PCF variance (10/11). Those failures were not relabeled as passes. The committed prompt
contract, stale-canary validation, and sanitized diagnostics produced this clean-SHA 11/11 result.

## Limits

This baseline does not prove implicit skill discovery, Copilot/VS Code behavior, Claude behavior, or
that the resolved model independently echoed the requested slug. It proves the fixed direct lanes on
the recorded Codex CLI and source revision only.
