# First-three backlog evidence and Claude authority-census repair — 2026-08-18

**Status:** preparation evidence only. No live workflow, release, credentialed canary, or external
configuration change was authorized or performed. The RELEASE-001 repair is an uncommitted candidate
over `41a20bab5857355b34083864afd277e671b63ce6`. Independent static review requested changes: the
full-root census is useful residual-state evidence but cannot prove the stronger no-write boundary.

## Conclusion

- **WF-001 stays blocked.** Current official documentation and the exact public Claude Code
  `v2.1.227` repository confirm how `ultrareview` is invoked and reports completion, but expose no
  supported immutable reviewed-subject binding or findings-sensitive approval verdict.
- **RELEASE-001 advanced only as defense in depth.** A red-first regression reproduced the Claude
  authority false pass for a persistent `history.jsonl`; the candidate now censuses the complete
  lexical Claude configuration root and fails closed on links, special files, and unreadable
  traversal. It does not prove that no transient or metadata-restored write occurred, so the release
  authority criterion remains open.
- **ROUTE-001 gained version-pinned source evidence.** The exact Codex `rust-v0.147.0` source agrees
  with the accepted ADR's tool-plan assumptions. This closes the source-reading question, not the
  protected-runtime, clean-host, canary, or 48-trial campaign prerequisites.

## RELEASE-001 local repair

`[verified]` The previous Claude probe watched only `plugins`, `settings.json`, `.claude.json`,
`backups`, and `.claude.json.lock`. An install callback could create sibling `history.jsonl` while
`host.claude.probe-authority` still returned `pass`.

`[verified]` Red-first execution of `python scripts/test_host_install_probe.py` produced six expected
failures: the sibling write false pass, the old selected-file count, missing-to-empty-root drift,
linked root and child acceptance, and swallowed traversal failure. Independent review then exposed
a second-metadata-read race: `verification_sandbox._is_indirection` could raise `SandboxError`
after the first `lstat`, aborting the report instead of returning sanitized `inconclusive` evidence.
Two added regressions errored before that fix. A separate evidence-label regression then failed on
the old “all writes stayed” pass message before the report was narrowed to residual evidence. After
the bounded repair, the same file reports 74 tests run with no failures and 2 platform skips.

`[verified]` `python scripts/gate_a.py` then passed all 39 structural steps on the same mutable
worktree, including 67 parsed scenarios, 345/345 grader checks, and improvement-record schema
validation. As Gate A itself states, this proves well-formedness rather than correctness, and the
result is not bound to a committed candidate.

The candidate changes only the census boundary and its tests:

- one `Claude-config-root` census replaces the five-entry allowlist;
- `.absolute()` preserves the lexical root so root indirection is not erased by resolution;
- `lstat` distinguishes an absent root from an unreadable or linked root;
- only regular files and real directories are accepted;
- `os.walk` errors are raised into the existing `None`/`inconclusive` path; and
- indirection-inspection failures also become sanitized `inconclusive` evidence.

The helper is shared by the Claude, Codex, Copilot, and VS Code probes, so its stricter link,
special-file, and traversal behavior applies to every caller. Only path counts and category counts
reach a completed report; user paths and file contents remain absent.

`[verified]` The census still compares only before/after path presence, regular-file size, and
modification time. It can detect a residual persistent `history.jsonl`, but cannot observe a file
created and deleted between snapshots or a same-size modification whose mtime is restored. The
result therefore proves **no residual metadata-visible change**, not “all writes stayed inside the
target.” Independent review classified that mismatch as a P1 because RELEASE-001 deliberately
requires the stronger no-user-write boundary. A separate OS identity, sandbox, or another accepted
structural denial mechanism is needed before this check can satisfy release authority.

`[sourced]` Independent static review of the mutable diff returned `REQUEST CHANGES`: the metadata
blind spot blocks release acceptance, while the traversal-race finding has since received a
red-first local repair that still needs exact-byte re-review. No formal review envelope was emitted.

`[unverified]` This is not a committed candidate, no live Claude CLI probe was run, and no structural
write-denial mechanism has been selected. The typed improvement record therefore remains `observed`
with zero attempts.

## WF-001 external contract refresh

**Context7 / official documentation.** The current
[`ultrareview` documentation](https://code.claude.com/docs/en/ultrareview) describes a cloud review
of a working tree, branch, or pull request and machine-readable output. It does not document an
immutable candidate digest in the result or a findings-sensitive process exit status suitable for
granting approval.

**GitHits / exact upstream repository.** GitHits resolved Claude Code `v2.1.227` to public commit
[`54cc51a`](https://github.com/anthropics/claude-code/tree/54cc51a08a5d3900e5abd02ad75a2ce46f3f008c).
Its [versioned changelog](https://github.com/anthropics/claude-code/blob/54cc51a08a5d3900e5abd02ad75a2ce46f3f008c/CHANGELOG.md#L2092-L2096)
states that the non-interactive command prints findings, supports raw JSON, and exits 0 on completion
or 1 on failure. Exact-revision searches found no public `ReportFindingsOutput` or
`report_findings` implementation to establish stronger subject or verdict semantics.

There is no disagreement between the two sources: GitHits corroborates the documented command but
does not supply the missing security contract. Implementing a wrapper would therefore manufacture a
guarantee the provider does not document.

## RELEASE-001 external control refresh

**Context7 / official documentation.** GitHub's current environment contract allows up to six
required reviewers but requires only one approval, can prevent self-review, and withholds environment
secrets until approval. Immutable releases lock the associated tag and assets and create a release
attestation.

**GitHits / exact upstream documentation source.** The indexed GitHub Docs source independently
shows the [one-reviewer and no-self-review semantics](https://github.com/github/docs/blob/b2bcc821d9ea22964c477f4786138eacffac9f7d/content/actions/reference/workflows-and-actions/deployments-and-environments.md#L24-L34)
and the [immutable tag, asset, and attestation guarantees](https://github.com/github/docs/blob/b2bcc821d9ea22964c477f4786138eacffac9f7d/content/code-security/concepts/supply-chain-security/immutable-releases.md#L20-L30).

Those sources agree with the repository ADR. They do not prove that this repository's live GitHub
settings exist; the previously observed missing environments, tag ruleset, immutable-release switch,
and publisher identity remain external blockers.

## ROUTE-001 external implementation refresh

**Context7 / official documentation.** The current OpenAI
[`config.toml` reference](https://learn.chatgpt.com/docs/config-file/config-reference) documents
model-catalog, sandbox, skill, feature, and MCP configuration surfaces. Because it tracks current
Codex rather than the pinned `0.147.0` artifact, it is contract context and not version-specific
proof of the old tool planner.

**GitHits / exact upstream source.** GitHits resolved `rust-v0.147.0` to commit
[`be6e8ea`](https://github.com/openai/codex/tree/be6e8eac029b183056b7e4402879f15d2c85f61b).
The versioned source shows that the model's `tool_mode` takes precedence and otherwise falls back
through feature gates ([tool selection](https://github.com/openai/codex/blob/be6e8eac029b183056b7e4402879f15d2c85f61b/codex-rs/core/src/tools/mod.rs#L70-L91)).
The tool-plan source separately gates shell, MCP resources, `apply_patch`, collaboration, user-input,
and utility tools on environment, model metadata, and features
([tool registration](https://github.com/openai/codex/blob/be6e8eac029b183056b7e4402879f15d2c85f61b/codex-rs/core/src/tools/spec_plan.rs#L846-L1040)).

This agrees with the local catalog transform and accepted ADR: removing `tool_mode`,
`apply_patch_tool_type`, search support, and experimental tools is necessary to prevent those model
tool surfaces from being registered. It does not prove the surrounding executable, Python runtime,
Git object store, login copy, or host configuration is protected.

## What I did not do

- Did not restore `ship-review` or wrap `ultrareview` as approval.
- Did not create GitHub environments, rulesets, Apps, tags, Releases, or workflow runs.
- Did not use credentials, upload repository bytes, run a paid review, or start a Terra trial.
- Did not append an improvement attempt or claim independent review, promotion, or release evidence.
