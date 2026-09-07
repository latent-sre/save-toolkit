# Delegation return and caller continuation

The user requested a consistent helper-to-caller return and a caller that resumes the original
task. The patch makes that contract explicit across the eight agents and incident advisor.
Runtime verification also found a separate prerequisite: the existing bare Claude delegation
grants admitted no plugin child on the installed host. Qualification repairs the intended edges;
no new edge, tool family, production authority, or human-selected handoff was added.

## Subject and method

- Incumbent: clean `323c0d8661af102af8e0c5dbc4e4a607b3104703`, plugin digest
  `ae3f0e476f60d1a58b27e370db289ef01b008ebda267f852dee2f87e38419f42`.
- Prompt-only candidate: same HEAD with task-owned working edits, plugin digest
  `22f895e7f59e40fd0bcb1a5054fd8025290974d625ce9a8d8b112eadddf5f218`.
- Candidate with qualified grants: same HEAD with task-owned working edits, plugin digest
  `cb48b71ca819ce8ffd3dc7927a3796ad2642e2e45b5f2f365c0dc77d75015eb5`.
- Windows, Python 3.12.10, Claude Code 2.1.261, requested `sonnet`, observed `claude-sonnet-5`.
- The current `evals/build_probe.py` ran both plugin versions in its neutral fixtures. Decision
  cases used three trials per version and a 180-second timeout; the build case used one trial
  per version and a 300-second timeout. Inputs were fictional; no live service was requested.
- Private raw traces and timings: `.eval-runs/return-loop-20260904/`. The incumbent worktree is
  `.worktrees/return-loop-incumbent-20260904/`; neither is a shipped artifact.

## Decision cases

The caller case supplies a partial research return with unsupported passing-test and release
claims. Correct behavior retains the two original tasks, continues the independent authorized
item, preserves uncertainty, and refuses the helper's purported release approval. The helper
case supplies instance observations but unavailable logs: it must return a partial slice to the
invoking agent without closing the incident or taking over operational decisions.

| Version | Caller decision | Helper decision |
|---|---|---|
| Incumbent | 2/3 strict passes | 2/3 strict passes |
| Prompt-only candidate | 3/3 | 3/3 |
| Candidate with qualified grants | 3/3 | 3/3 |

Both incumbent misses contained the correct field values inside an unwanted Markdown fence.
These are response-format failures, not different operational decisions. The trials do not
establish a reasoning improvement. They grade supplied-state decisions, not actual tool execution.

## Actual delegation exposed the namespace defect

The build scenario asks the software engineer to delegate only a runbook to scribe, then resume
and integrate its returned path into README. A completed child call is required in addition to
the final files, so doing both jobs inline cannot pass as successful delegation.

- Incumbent: 6/7 checks. All final-artifact checks passed, but both `save-toolkit:scribe` and
  `scribe` calls returned `Agent type ... not found. Available agents: none`. The parent authored
  the runbook itself. Plugin discovery had listed the scribe, so discovery alone was insufficient.
- Prompt-only candidate: timed out at 300 seconds, INCONCLUSIVE; its partial trace contained the
  same two lookup errors. Prompt changes alone did not repair the call path.
- A minimal isolated two-agent probe held everything except the parent's grant constant:
  `Agent(child)` rejected `return-probe:child`; `Agent(return-probe:child)` received a non-error
  `CHILD_RETURNED` result. The parent had only Agent and the child had no tools. This identifies
  namespace matching on this host rather than assuming an unavailable plugin.
- The four delegating agents now name `save-toolkit:<target>` in their grants. The shared parser
  rejects bare, foreign, wildcard, malformed, and duplicate targets and emits the original bare
  target names for Copilot. The pinned expected graph is unchanged.

The final qualified-grant build passed **7/7 checks**, one trial in 151.5 seconds. The raw trace
records a namespaced scribe dispatch (line 42), a non-error return (45), the forwarded child Write
to `docs/runbooks/check.md` (80), and root-agent Read of that document (91) followed by root-agent
Edit of README (94). Child messages are forwarded after the tool result, so stream line order
inside the child is not a wall-clock timeline. The root's read and edit do follow the successful
return; the parent then runs its local link check (96). This proves an actual child result
consumed by the parent, not merely two final files.
All six decision trials also passed on this final plugin digest.

## Verification and limits

The completed-child checker first failed its test because no such check existed; after the
implementation it rejects missing, attempted, failed, wrong-namespace, bare, and similarly named
returns. The namespace regression first demonstrated that the old parser accepted the broken bare
grant and rejected the qualified one; its replacement shares parsing between validation and
generation. The added mechanism is eight harness lines and 35 test lines, plus the scoped namespace
parser changes; existing weight and context ceilings are retained.

The final full-suite run initially had one transient failure: the changelog linked this report
before it had been created (459 passed, one failed, four skipped, 857 subtests passed). After the
report existed, the affected link, adapter, and fleet-validator suites passed: 119 tests, three
symlink skips, and 151 subtests. The final consolidated result is recorded below.

- `python -m pytest -q -rs -p no:cacheprovider`: **460 passed, four skipped, 857 subtests passed**.
  Three skips require directory symlink privileges; one is a CI-only shell-presence assertion.
- `python scripts/gate_a.py`: **4/4 PASS**. Adapter parity and all seven context budgets pass.
- `python evals/build_probe.py --validate`: **57 scenarios, 301 graded expectations**.
- `claude plugin validate . --strict`: PASS (the command reported marketplace-manifest validation).
- `git diff --check`: PASS. No commits, pushes, installs, or live infrastructure changes made.
- The final plugin digest was re-read after verification and still matches `cb48b71ca819...` above.

The 21 harness trials recorded USD 1.171284; the two isolated namespace probes recorded
USD 0.0619252 together. The timed-out trial did not return billing metadata, so these amounts
are recorded costs rather than a complete billing total.

Independent static review approved the prompt and namespace changes. Its one prompt clarification
was incorporated: the new resume rule cannot reopen a stopped review/fix loop. Generated adapters
were regenerated from the canonical sources; the Copilot target sets remain unchanged.

The automated build checks prove a completed named call and integrated artifacts. Actor identity
and parent-after-child ordering require inspection of the raw trace. One task on one Claude host
does not establish every delegation edge, nested-depth enforcement, Copilot runtime behavior, or
general incident reliability. Human acceptance of the candidate remains separate from eval results.
