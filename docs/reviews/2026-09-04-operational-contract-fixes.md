# Operational contract fixes — 2026-09-04

## Scope and conclusion

Five follow-up findings against `7753a0751af314e3daa725460b5ca3aa54298675` are corrected in
canonical guidance, with regenerated Copilot projections. No tool authority or production
execution permission is added. This is a source correction and bounded behavioral check, not
fleet-wide SRE readiness or human acceptance of a candidate.

| Finding | Correction |
|---|---|
| Incident fast path included restaging despite excluding new artifacts | New-droplet staging uses full gates. Restart qualifies only when existing-droplet reuse without staging is established; unknown package state blocks classification |
| Approval prerequisites prevented useful preparation | PCF deploy and lifecycle allow scoped inventory and explicitly unapproved drafts. Exact identities, applicable approvals, retention, consumer and recovery evidence still gate readiness and live effects |
| Advisor always demanded diagnostic capture first | A named human may knowingly forgo unavailable diagnostics for approved reversible reliability mitigation; security, integrity, destructive actions and required target/artifact evidence remain outside that exception |
| Researcher example invented HTTPX version history and fresh tool results | Replaced with a version-pinned, explicitly illustrative, tainted/source-labeled brief; removed unsupported release/advisory assertions |
| Builder could send a reviewer only a summary | Sender must prepare base identity, candidate binding, inspectable diff including untracked content, actual verification evidence and trusted-base instructions; unsafe instruction context blocks dispatch, without adding reviewer tools |

Independent source review caught two issues during implementation: generic deploy readiness
initially reimposed full release gates on covered existing-artifact mitigation, and the sender's
wording made base identity ambiguous for working-tree reviews. Both were corrected. A nearby
blanket diagnostic waiver was narrowed so it cannot waive required artifact/safety evidence.

## External evidence

- [sourced] Cloud Foundry's [restart/restage documentation](https://docs.cloudfoundry.org/devguide/deploy-apps/start-restart-restage.html)
  describes restarting the compiled droplet versus staging a new one (official contract, retrieved
  through Context7 on 2026-09-04).
- [sourced] The [upstream restart command](https://github.com/cloudfoundry/cli/blob/main/command/v7/restart_command.go)
  additionally documents staging the latest package when it is unstaged (GitHits exact source read,
  lines 18–32, retrieved 2026-09-04). That exception constrains the more general documentation;
  actual deployed CLI/CAPI behavior still needs target-specific confirmation.
- [sourced] [HTTPX 0.27.2 timeout documentation](https://github.com/encode/httpx/blob/0.27.2/docs/advanced/timeouts.md)
  already documents `timeout=None` disabling timeouts. The
  [0.28.0 release notes](https://github.com/encode/httpx/releases/tag/0.28.0) do not announce the
  alleged change. This resolves the example's historical claim, not local upgrade compatibility.

## Verification record

- [verified] Initial full suite: 460 passed, 857 subtests passed, 4 skipped. The skips are three
  Windows directory-symlink checks and one CI-only shell-requirement check.
- [verified] Structural Gate A: 4/4. Context cost: 7/7 within unchanged budgets. Weight: 9,252 eval
  Python lines, 559,742 skill bytes, 109,066 agent bytes, all within unchanged ceilings. The small
  harness change reuses reference grading rather than adding a grader or permission mechanism.
- [verified] Scenario validation: 62 specs / 318 expectations. Five final focused canaries pass,
  one trial per case on `claude-sonnet-5` (requested `sonnet`), Claude Code 2.1.261. All five also
  pass on the incumbent with the same final scenario prompts: **no measured behavioral improvement**
  is claimed. The changes remove sourced instruction contradictions and incomplete contracts;
  these supplied-state canaries show bounded compatibility, not reliable real-world performance.
- [verified] Unhinted lifecycle routing: one PASS, two timeout INCONCLUSIVE, across three trials.
  This does not establish reliable routing. No further routing campaign was run.
- [verified] Independent source review: provisional approval after the requested corrections;
  separate final harness review found no regression findings.
- [verified] Final full-suite rerun: `python -m pytest -q -rs -p no:cacheprovider` with Git Bash
  tools on PATH: **462 passed, 860 subtests passed, 4 skipped**, in 78.62 seconds. Skip reasons
  remain the three Windows directory-symlink checks and the CI-only shell requirement.

Final candidate plugin digest:
`4d10460cd0a7e28b7eda7914b3be8fedfbabfd761b4c19396b267fa026081b7e`.
Incumbent digest: `82d5ef2ef59bfb76a081470eda8026a170d396751d29fb15d9316efee1b1b1bf`.

| Final case | Candidate evidence directory under `.eval-runs/remaining-findings-20260904/` | Result |
|---|---|---|
| Reviewer preparation | `field-review-canary` | 1/1 |
| Retirement draft | `unquoted-lifecycle-canary` | 2/2 |
| Unavailable diagnostic capture | `final-incident-investigation-unavailable-dump-mitigation-boundary` | 2/2 |
| PCF deployment draft | `bound-build-pcf-deploy-unapproved-planning-body` | 6/6 |
| Restart/restage classification | `bound-build-production-change-gate-classifies-restart-and-restage` | 6/6 |

The two build traces were independently read back: each successful Read names the actual candidate
path under `F:/repos/sre-agents/skills/`, not the incumbent snapshot. The existing grader matches
reference path suffixes and does not itself prove absolute-root identity. PCF was not invoked as
a manual skill; no real builder-to-reviewer dispatch or production action was tested in this batch.

### Calibration limitations

Initial raw-JSON cases produced correct decisions inside Markdown fences, failing the strict JSON
grader. A first literal-field rewrite ambiguously said `Label: value`, and some responses literally
prefixed fields with `Label:`. Quoted alternatives also caused literal quote output. Final prompts
specify the field name directly, remove those prompt-only quotes, and use the existing
exact-fields grader; decision expectations did not change. These are test-design corrections,
not evidence that operational reasoning improved.

The contract runner does not preapprove reads outside its temporary workspace. Required bundled
reference reads were denied, yielding INCONCLUSIVE rather than PASS. Read-dependent cases use the
existing seeded-workspace build runner with explicit read-only tool inventories, not an expanded
permission mechanism. An initial PCF build guessed paths and never read the skill; it is not valid
body evidence. Two red-first tests reproduced the missing build-reference support and measured-root
prompt binding. The harness now supplies exact reference paths and requires successful reads in
build trials too. The manual-only PCF skill is read as a document: this is not proof of manual
skill activation. Initial results remain in private `.eval-runs/remaining-findings-20260904/`;
do not combine differing prompt variants into a before/after improvement score.

The generic installed Codex skill validator rejects this repository's existing Claude frontmatter
(`argument-hint`, and PCF's `compatibility`/`disable-model-invocation`). Those supported repository
fields were preserved; repository-native frontmatter validation and generated-adapter parity pass.
