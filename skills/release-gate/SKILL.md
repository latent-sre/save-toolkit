---
name: release-gate
description: >-
  Pre-release **readiness** gate — is this build ready to ship? Use as the checkpoint before
  deploying/releasing a build to an environment (especially prod): verifies recorded merge-gate PASS
  evidence, the artifact is promotable, migrations and flags are ready, monitoring is in place, and a
  tested rollback exists. Triggers: "is this build ready to ship", "run the release gate", "can we
  release this". Ownership map only—not a load: merge-gate = ready to merge; release-gate = ready to
  ship; production-change-gate = authorized to act on prod.
---

# Release gate

A release is ready only when **all** checklist items pass. The gate is owned by a human release owner.
For production, this PASS establishes readiness only; authorization belongs to the separate, later `production-change-gate` skill using this recorded evidence.

## Checklist

- [ ] **Merge readiness exists** — attach a recorded PASS from the `merge-gate` skill for the exact
      reviewed SHA. This skill does not load or execute that sibling gate; missing evidence is a blocking
      item.
- [ ] **The release tag cannot move and the Release cannot be edited** — two GitHub controls, both
      checked as *state*, not assumed from the workflow file. A **tag ruleset** on the release tag
      pattern is what enforces "a released version tag is never moved, deleted, or reused" (rulesets
      are the only place tag deletion and renaming can be controlled), and an **immutable Release**
      locks that tag "to a specific commit, cannot be changed, and cannot be deleted while the
      release exists". `release.yml` requires both to be preconfigured and verifies them — it does
      not create them; this item confirms the ruleset is **Active** via
      `gh api repos/{owner}/{repo}/rulesets` and the prior release shows `"immutable": true` —
      a Disabled ruleset or a mutable Release means the guarantee is a comment, not a control.
      Whether this repo's tag ruleset exists and is Active is `[unverified]` until that read is
      attached. *[sourced: GitHub Docs, about rulesets and immutable releases; reviewed 2026-08-21]*
- [ ] **One identified artifact, promoted** — the version and changelog or release notes identify the
      candidate, and the exact artifact tested in lower environments is the one shipping; build once and
      promote rather than rebuilding.
- [ ] **Migrations safe** — DB, schema, and configuration migrations are backward-compatible, ordered
      before the code that needs them, and independently reversible.
- [ ] **Feature flags ready** — risky behavior is flag-gated, defaults safe, and the flag transition is
      tested.
- [ ] **Rollback written & reversible** — the human release owner records the exact rollback steps and
      evidence that they work. For PCF, the selected rollback method and target-foundation behavior remain
      `[unverified]` until foundation evidence is attached.
- [ ] **Monitoring & abort criteria** — define success and failure signals and exactly what trips an
      abort before the release; attach existing evidence from the typed `observability-engineer` agent
      that alerts and SLOs cover the new behavior and that new paging alerts have operator guidance.
- [ ] **Comms ready** — stakeholders and on-call know the window and update cadence.

## Verdict

```text
release-gate: PASS | BLOCKED
Candidate SHA/artifact: <immutable identity>
Target: <org/space/environment>   Strategy: <blue-green|rolling|canary|flag>
Rollback: <exact steps and evidence>
Blocking items: <the NOs>
```

## Notes

- **Gate topology:** recorded merge readiness is existing evidence consumed here. Production authorization
  is separate and later, and consumes this release-readiness record for the exact candidate and target.
- Ownership map only—not a load: the `ci-actions` skill owns workflow definition. The release packet must
  attach existing artifact-provenance and protected-environment evidence rather than invoke that skill.
- A release without a clean, evidenced rollback does not pass.
