# Release readiness (`gate: release`)

The agent verifies readiness; the human release owner decides. Production deployment separately
requires `gate: production` in [SKILL.md](../SKILL.md).

| Item | Passes when |
|---|---|
| Reviewed source | `gate: merge` PASS and reviewed PR head attached. If build uses a later commit/merge-queue ref, trace every delta (base updates, conflict resolutions) with check and review evidence. |
| One immutable artifact | Build revision and inputs bound to the shipping artifact's digest; same immutable bytes promoted from lower-environment verification (see below). |
| Migrations | Schema/config remains compatible across supported consumers at each stage (expand before dependent code; contract only after old consumers retire) with tested recovery preserving accepted writes. |
| Consumer retirement | Consumer retirement confirmed before contraction; test remaining/recovery versions without requiring retired consumers to remain compatible. |
| Flags | Risky changes flag-gated with safe defaults and a tested toggle path. |
| Backout / recovery | Exact rollback where feasible, else non-reversible effects and evidenced recovery preserving writes/data (PCF behavior stays `[unverified]` without foundation evidence). |
| Monitoring & comms | Success/failure signals and abort criteria defined; `observability-engineer` covers new paging alerts/runbook links; stakeholders and on-call notified of the window. |

## Artifact evidence

Bind the shipping artifact to the exact bytes tested below production (`cicd-github` produces provenance).

- **GitHub Releases:** Inspect the release (`gh api repos/{owner}/{repo}/releases/tags/{tag}` → `"immutable": true`;
  new releases also check `.../immutable-releases` → `"enabled": true`) and verify attestations binding
  repository, tag, commit, and digest with `gh release verify {tag}` and `gh release verify-asset {tag} {file}`
  (auto-generated source archives are excluded). If repository policy requires extra tag rulesets,
  inspect `gh api repos/{owner}/{repo}/rulesets` / `.../rulesets/{id}` (`target: tag`, `enforcement: active`,
  update/deletion rules, and `bypass_actors`, noting `bypass_actors` requires write access to view).
- **Other distribution paths:** Verify an immutable digest or deletion-protected versioned object
  (container digest, signed checksum, versioned object) resolving to the tested lower-environment bytes.
- Immutability proves bytes didn't change, not that tests passed — attach both immutability and test evidence.
