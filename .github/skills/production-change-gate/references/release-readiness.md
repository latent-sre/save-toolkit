# Release readiness

The agent checks and records readiness; the human release owner decides. The
[parent production gate](../SKILL.md#production-authorization) separately authorizes production
using this record.

| Item | Passes when |
|---|---|
| Merge verdict | `gate: merge`, `verdict: PASS` exists for the exact candidate commit. |
| One immutable artifact | Version/release notes identify the candidate. Build once, promote the exact lower-environment-tested artifact; prove its byte identity and immutability using [distribution-specific evidence](#artifact-evidence). |
| Migrations | Schema/config stays compatible with supported consumers at each stage. Expand before dependent code; contract only after old consumers retire. Each stage has tested recovery preserving accepted writes/data. |
| Consumer retirement | Confirm retirement before contraction. Then validate remaining consumers and versions needed for recovery, without requiring retired readers to remain compatible. Before retirement, old readers still need compatibility evidence. |
| Flags | Risky behaviour is flag-gated with safe defaults and a tested transition. |
| Backout / recovery | Exact rollback where feasible; otherwise identify non-reversible effects and evidenced recovery preserving accepted writes/data. Record commands, verification and stops. PCF method/foundation behaviour stays `[unverified]` until foundation evidence is attached. |
| Monitoring and comms | Define success/failure signals and abort criteria before release. `observability-engineer` supplies coverage evidence for new behaviour, including operator guidance for new paging alerts. Stakeholders/on-call know the window and update cadence. |

Missing recovery evidence or uncovered migration stages block release. `ci-actions` owns artifact
production; this checklist consumes provenance without invoking that workflow.

## Artifact evidence

Bind the shipping artifact to the immutable bytes tested below production.

### GitHub Release as the distribution path

```sh
gh api repos/{owner}/{repo}/releases/tags/{tag}       # selected release: require "immutable": true
gh api repos/{owner}/{repo}/immutable-releases        # new publication: require 200 with "enabled": true
gh release verify {tag}                               # release attestation
gh release verify-asset {tag} {file}                  # each shipping asset against that attestation
gh api repos/{owner}/{repo}/rulesets                  # when repository policy requires additional tag rules
gh api repos/{owner}/{repo}/rulesets/{ruleset_id}     # inspect the applicable tag rule
```

Record release ID, tag, candidate commit, asset identity and verified release attestation where
available. The shipping asset's checked digest must match the exact candidate's lower-environment test evidence;
a filename/tag match is insufficient. Attestations must bind repository, release/tag, commit and
digest; check that binding with `gh release verify` and `gh release verify-asset`, which cannot
check the auto-generated source zip or tarball. Missing byte binding blocks readiness even for an
immutable release.

Current publication settings do not prove an older release immutable; check the selected object.
For new publication, also check the current setting: a 200 body is `{enabled, enforced_by_owner}`;
a 404 means disabled only for a caller with admin read access, and unknown for any other caller.
GitHub's immutable release already locks its tag and assets. If the repository's release policy
requires additional tag rules, check `target: tag`,
`enforcement: active`, matching `ref_name.include`, no matching exclusion, both `update` and
`deletion` rules, and the bypass actors; `bypass_actors` is returned only to callers with write
access to the ruleset, so without that access bypass is unknown. These policy checks do not replace
the selected-release and tested-byte evidence.

### Any other distribution path

Attach an immutable digest or non-replaceable object/version identity and prove it resolves to the
tested bytes: container image digest, signed package checksum, or versioned object with deletion
protection. Do not require GitHub Release controls for other distribution paths.

### What this does not prove

Immutability does not prove testing; attach both protection and exact-byte test evidence.
