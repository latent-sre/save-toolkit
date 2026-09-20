# Release artifact evidence

Read only when release readiness must prove that the shipping artifact is the immutable one that
was tested. The parent `SKILL.md` owns the release checklist and the verdict.

## GitHub Release as the distribution path

Bind evidence to the selected release and its exact tested asset:

```sh
gh api repos/{owner}/{repo}/releases/tags/{tag}       # selected release: require "immutable": true
gh api repos/{owner}/{repo}/immutable-releases        # require "enabled": true for publication policy
gh api repos/{owner}/{repo}/rulesets                  # list candidate rulesets
gh api repos/{owner}/{repo}/rulesets/{ruleset_id}     # fetch the one matching the tag
```

Record the selected release ID, tag, candidate commit, asset identity, and verified release
attestation where available. Require the shipping asset's checked digest to match the digest in
the exact candidate's lower-environment test evidence; a matching filename or tag is insufficient.
An attestation must bind that repository, release/tag, commit, and asset digest. Missing byte binding
blocks readiness even when the release is immutable. Enabling immutability affects future releases
only; current settings do not establish protection for an older candidate.

For this team's additional tag-protection policy, the matching ruleset must show `target: tag`,
`enforcement: active`, a `ref_name.include` pattern
that matches the selected tag, no matching exclusion, and both `update` and `deletion` rules. A prior
Release's `"immutable": true` is supporting object evidence, never a substitute for the current
setting for future publication. These repository controls do not replace the selected-release check.
*[sourced: GitHub [immutable releases](https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases)
and [enabling immutability](https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/establish-provenance-and-integrity/prevent-release-changes),
checked 2026-09-20; repository ruleset contract reviewed 2026-08-23]*

## Any other distribution path

Attach the platform's equivalent immutable digest or non-replaceable object or version identity and
prove it resolves to the tested bytes: a container image digest, a signed package checksum, a
versioned object with deletion protection. Do not require GitHub Release controls for a path that
does not use them.

## What this does not prove

Immutability proves the bytes cannot change after promotion. It does not prove they were tested;
that is the lower-environment evidence in the release checklist, and the two are attached together.
