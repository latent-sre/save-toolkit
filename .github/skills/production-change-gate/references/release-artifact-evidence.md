# Release artifact evidence

For release readiness, bind the shipping artifact to the immutable bytes tested below production.
The [release checklist](./release-readiness.md) and [parent verdict](../SKILL.md#verdict) still apply.

## GitHub Release as the distribution path

```sh
gh api repos/{owner}/{repo}/releases/tags/{tag}       # selected release: require "immutable": true
gh api repos/{owner}/{repo}/immutable-releases        # new publication: require "enabled": true
gh api repos/{owner}/{repo}/rulesets                  # when repository policy requires additional tag rules
gh api repos/{owner}/{repo}/rulesets/{ruleset_id}     # inspect the applicable tag rule
```

Record release ID, tag, candidate commit, asset identity and verified release attestation where
available. The shipping asset's checked digest must match the exact candidate's lower-environment test evidence;
a filename/tag match is insufficient. Attestations must bind repository, release/tag, commit and
digest. Missing byte binding blocks readiness even for an immutable release.

Current publication settings do not prove an older release immutable; check the selected object.
For new publication, also check the current setting. GitHub's immutable release already locks its
tag and assets. If the repository's release policy requires additional tag rules, check `target: tag`,
`enforcement: active`, matching `ref_name.include`, no matching exclusion, and both `update` and
`deletion` rules. These policy checks do not replace the selected-release and tested-byte evidence.

## Any other distribution path

Attach an immutable digest or non-replaceable object/version identity and prove it resolves to the
tested bytes: container image digest, signed package checksum, or versioned object with deletion
protection. Do not require GitHub Release controls for other distribution paths.

## What this does not prove

Immutability does not prove testing; attach both protection and exact-byte test evidence.
