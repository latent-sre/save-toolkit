# Release artifact evidence

Read only when release readiness must prove that the shipping artifact is the immutable one that
was tested. The parent `SKILL.md` owns the release checklist and the verdict.

## GitHub Release as the distribution path

Inspect the current repository state, not a past release's flags:

```sh
gh api repos/{owner}/{repo}/immutable-releases        # require "enabled": true
gh api repos/{owner}/{repo}/rulesets                  # list candidate rulesets
gh api repos/{owner}/{repo}/rulesets/{ruleset_id}     # fetch the one matching the tag
```

The matching ruleset must show `target: tag`, `enforcement: active`, a `ref_name.include` pattern
that matches the selected tag, no matching exclusion, and both `update` and `deletion` rules. A prior
Release's `"immutable": true` is supporting object evidence, never a substitute for the current
setting. *[sourced: GitHub Docs, repository immutable releases and repository rulesets; reviewed
2026-08-23]*

## Any other distribution path

Attach the platform's equivalent immutable digest or non-replaceable object or version identity and
prove it resolves to the tested bytes: a container image digest, a signed package checksum, a
versioned object with deletion protection. Do not require GitHub Release controls for a path that
does not use them.

## What this does not prove

Immutability proves the bytes cannot change after promotion. It does not prove they were tested;
that is the lower-environment evidence in the release checklist, and the two are attached together.
