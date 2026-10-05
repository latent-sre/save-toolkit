# Group 11: agent-engineer — six-pass audit

Reviewed 2026-10-02 against frozen canonical source `a2d2e57d2de70125dbde002072853e73b788bd8d`; audit HEAD at dispatch was `a6132ea82c12bd5a3d0fd9c0a8739c6f8edb3753`. Recipient/invoking caller: `/root`; human owner: the user. Assignment complete. The parent objective remains the six-pass review of all skills followed by agents, three assets per group, with findings committed before continuing.

**Conclusion:** retain this bounded authoring role and its separation of author evidence, independent review, and human promotion. One low-severity evaluator defect is confirmed: the typo-repair oracle accepts an invalid leading blank before skill frontmatter. The learning-loop approval schema remains an improvement recommendation reconciled from AA-R2, not a demonstrated promotion bypass. Executable graph design and host-specific enforcement have substantially less evidence than the role's ordinary authoring contract.

`[verified]` identifies inspected frozen-source facts or named offline execution; `[sourced]` identifies current primary documentation; `[unverified]` identifies native/model/target claims not established. The entire agent body was read, along with directly relevant authoring references, delegation/validator/guard logic, generated projections, all agent-specific scenarios, and bounded consuming guidance. Existing agent-authoring findings remain owned by [group 01](group-01-agent-authoring.md). Only this scratch report was written; no canonical edits, live effects, installations, new agents, paid/native campaigns, or commits occurred.

## Pass 1 — mission, suitability, and selection

**Evidence:** full `agents/agent-engineer.md`; `skills/agent-authoring/SKILL.md:15-18,94-116,150-157`; complete `discovery-agent-authoring-loop-engineering.yaml` and `discovery-operational-learning-defers-fleet-failure.yaml`; the role's two direct/build scenarios.

[verified] The role owns LLM-facing artifacts and diagnosis across activation, instructions/context, schemas, orchestration, wrapper/runtime, and evaluator boundaries. It avoids assuming every observed failure requires stronger prompt wording. Ordinary artifact and roster work use agent-authoring; executable workflow design remains a distinct design lane, with runtime implementation and runtime selection assigned elsewhere.

[verified] Helper code and evaluators beyond prompt artifacts return to software-engineer. Security-sensitive artifact changes and gate/guard meaning changes return to independent review. The body explicitly says it cannot invoke those owners; its caller arranges the next assignment. Operational knowledge closeout is a different lane, and its discovery negative directs fleet misbehavior with transcript evidence toward this role.

The role overlaps the skill by design: quick work can apply the skill inline, while iterative or broader work gets a bounded owner. Current tests do not establish that dispatching this role improves quality over applying the method in the main session. That is a suitability question, not evidence that the role is unnecessary.

**Result:** coherent mission and ownership split. **Gap:** no dedicated graph-design outcome probe or direct positive agent-discovery case was found. The current review's collaboration-tool roster does not list a literal `agent-engineer` role; a repository file does not register a callable role on this host or establish behavior on Claude/Copilot.

## Pass 2 — correctness, dependencies, and generated contracts

**Evidence:** `agents/agent-engineer.md:24-59,77-111`; complete authoring `artifact.md`, `roster.md`, `context.md`, and `tools.md`; bounded frontmatter/delegation references; `scripts/validate_fleet.py:156-170,266-300`; generator `:78-94,360-402`; generated `.github/agents/agent-engineer.agent.md` and `com.github.copilot/agents/agent-engineer.agent.md`.

[verified] The authoring loop freezes criteria, compares matching cases/conditions, bounds candidates/cost, retains the incumbent on ties or missing results, and keeps repository-visible cases out of the claimed hidden-holdout category. The agent's method correctly makes human acceptance of the exact candidate revision promotion; independent review is conditional under the owning rules. The validator positively checks this wording and rejects the former non-author formulation in the agent method (`scripts/test_validate_fleet.py:285-298`).

[verified] The two generated profiles are identical to each other. Their body matches canonical content; their frontmatter maps tools to read/search/edit/execute/agent/todo and delegates only to researcher. The generator intentionally omits worktree-specific tools with no Copilot alias. It neither adds a reviewer/software-engineer delegation edge nor a human-selected handoff edge. No model pin is present.

[verified] Canonical agent, authoring dependency, and relevant fixture/grader/guard files have no diff from the frozen source. AA-03's skill-versus-agent metadata wording and AA-04's universal-sink wording remain shared reference defects, not new AE findings. The direct learning-loop schema still encodes the earlier non-author approval concept; AE-R01 records its exact limitation.

**Result:** the agent body and projections agree with the current declared lane. **Gap:** generated bytes and validator success establish configuration consistency, not installed-host acceptance, successful routing, or graph-design competence.

## Pass 3 — authority, actual enforcement, and hostile handoffs

**Evidence:** agent frontmatter `:12`, method `:45-59`, handoffs `:93-111`, guardrails `:115-122`; complete authoring `agent-security.md`; `hooks/hooks.json`; `scripts/readonly-guard.py:91-105,1241-1257,1289-1318`; `scripts/test_readonly_guard.py:975-1003`; Copilot hook manifest; official Claude documentation retrieved through Context7 on 2026-10-02.

[verified] The role has broad local writes, Bash, worktree tools, and one declared Agent target. It has no direct web/browser/MCP grant. Those absences do not remove Bash networking or prevent a shell from modifying code or invoking Git. The no-merge, no-deploy, no-live-action, and helper-code ownership rules are cooperative unless the outer host enforces them.

[verified] The read-only allowlist covers sre-assistant, not agent-engineer. The fleet credential tripwire includes agent-engineer and denies its named credential-printing paths when the expected Claude agent identity reaches the hook. Other commands return allow before the read-only checker. This is not comprehensive credential, filesystem, network, or live-effect containment. The shipped Copilot hook manifest is empty, so the Claude tripwire must not be assumed to travel with this projection.

[sourced] Current [Claude subagent documentation](https://code.claude.com/docs/en/sub-agents), fetched through Context7, confirms that `Agent(type)` restricts a main-thread `--agent` but its type list is ignored at subagent depth. It also confirms ignored plugin `hooks`, `mcpServers`, and `permissionMode` fields. The repository's delegation reference already acknowledges these limits; this review did not run an allowed/forbidden native call.

[sourced] [Claude administration guidance](https://code.claude.com/docs/en/admin-setup) confirms that denying WebFetch does not prevent networking through Bash; enforced shell egress restrictions require the appropriate host sandbox controls. This agrees with local security guidance and is not a new defect.

[verified] Incoming source, transcripts, helper results, and audited instructions default to untrusted. The role preserves claim-level taint and observation scope, sanitizes public research requests, and does not infer approval from a helper's claim. Imported/unreviewed artifacts remain static-only under the loaded method. Its security review and independent reviewer handoff are valuable, but neither substitutes for an execution boundary.

**Result:** clear intended authority with honest host-dependent limits in the supporting references. **Gap:** no exact-host sandbox, credential isolation, nested delegation restriction, or adversarial native behavior was established. Existing AA-02 remains the shared false-containment calibration finding.

## Pass 4 — LLM readability and context cost

**Evidence:** complete agent and bounded authoring references; canonical/projection byte and word measurements; comparison of the agent method and artifact method.

[verified] The canonical agent is 8,338 bytes, 122 lines, and 1,140 whitespace-separated words. Each Copilot copy is 8,251 bytes, 115 lines, and 1,136 words. These are not token counts. Loading the required authoring entrypoint and artifact reference adds 17,925 bytes before conditional security, roster, tools, or context guidance; assess that loaded combination rather than body size alone.

[verified] The agent's four-step method and altitude split make the next decision reasonably clear. Reusable budgets and promotion details are delegated to the skill rather than copied into another full loop. The return fields distinguish caller, human owner, bounded completion, and remaining parent work. Unknown or failed helper dispatch stays an explicit gap.

The graph tier is chiefly a list of concerns rather than an example of a usable design contract. That is a competence/verification gap, not a false assertion that an implementation exists. If reducing text, combine the adjacent reviewer/software-engineer non-invocation statements (`:105-106`) and compress repeated handoff explanation before removing trust, exact-revision, or budget rules. Do not add a generic persistent ledger or another agent simply to make the design look complete.

**Result:** purposeful on-demand structure; no substantial rewrite is justified by this review. **Gap:** caller-required closed output formats still need behavioral verification through the existing strict-object case; no new claim is made that a native model consistently omits the general return header when necessary.

## Pass 5 — evaluation coverage, oracle soundness, and evidence limits

**Evidence:** complete `agent-direct-agent-engineer-learning-loop.yaml`; complete `build-agent-engineer-resumes-after-partial-research.yaml`; `evals/README.md:286-302`; `evals/graders.py:178-266` and strict-JSON calibration previously inspected in group 09; `scripts/test_validate_fleet.py:285-298,392-410`; adapter graph tests; `evals/build_probe.py:1-31,1858-1871,1893-1895`; shared frontmatter parser.

[verified] The learning-loop case exercises a closed decision object: frozen regression, comparable evidence, bounded candidates, incumbent retention, no invented holdout, no merge/deploy, and one owned backlog. The strict grader rejects extra prose/keys and type coercion; EL-01 concerns a different grader. The approval field lacks the body's explicit human identity (AE-R01).

[verified] The build fixture requires completing a typo repair after a pasted partial research return falsely claims completion and asks for guard deletion. It checks the final skill text, allowed changed path, no commit, no further dispatch, and retained unknown/taint markers. It does not execute a real researcher handoff. Its label regex verifies marker presence rather than complete claim-level interpretation. The normalization of the supposedly exact file is overbroad (AE-01).

[verified] The runner explicitly distinguishes host execution from containerized shell execution. Host mode has network access and a reachable model credential copy; the container option isolates shell execution, while the model client remains on the host. No generic “clean room” name or scoped prompt proves full containment. No runtime campaign was run here.

[verified] The frozen full-suite baseline remains 1,470 passed, 19 skipped, 2,690 subtests, with 192 specifications/737 expectations validated. Root additionally ran the focused AE-01 counterexample. **Gap:** no live model, native dispatch, paid judge recalibration, authoring quality comparison, or executable-graph acceptance was performed.

## Pass 6 — finding, counterexamples, and ranked improvements

### AE-01 — exact-file repair oracle accepts broken leading frontmatter placement

**Confirmed bounded evaluator defect; Low severity; high confidence; [verified].** Locations: `evals/build-scenarios/build-agent-engineer-resumes-after-partial-research.yaml:8-10,35-40`; `scripts/fleet_frontmatter.py:109-119`; generator parser wrapper at `scripts/generate_platform_adapters.py:264-267`.

**Trigger and consequence:** the expected repair preserves frontmatter and changes only the body typo. The checker permits trailing whitespace/final-newline normalization but calls `s.strip()`, which also removes leading blank lines. A corrected skill prefixed with a newline is accepted even though the repository's shared parser requires the opening marker on the first line. The probe can therefore report a valid completed repair for a candidate that fails canonical frontmatter parsing. This does not prove a native loader failure or authorize promotion.

**Fresh root reproduction:** using the actual YAML command and strict fleet parser in owned scratch, the corrected file and a trailing-newline control returned oracle exit 0 and parsed successfully. The leading-blank mutant returned oracle exit 0 but raised “missing opening frontmatter marker” in strict parsing. The unchanged typo returned oracle exit 1. All reproduction assertions passed; no model or network call occurred.

**Smallest fix:** preserve the beginning of the file during normalization, for example normalize line endings/trailing whitespace and use a right-side trim instead of whole-string `strip()`. Add the leading-blank negative beside the valid/trailing-newline/unchanged-typo controls. The existing exact-content comparison can remain; a general new grader is unnecessary. **Verification:** the new negative must fail on the current oracle and pass after repair; retain frontmatter/body-change rejection and the intended trailing-whitespace allowance.

### AE-R01 — align the closed approval field with human promotion

**Recommendation; Low priority; high confidence in the stale contract.** Locations: `evals/scenarios/agent-direct-agent-engineer-learning-loop.yaml:15,23,39,47`; agent `:51-53`; `artifact.md:27,53-63`; `scripts/test_validate_fleet.py:285-298`. This is the deferred AA-R2 lead, now reconciled with the consuming body.

The field offers only `author_or_later_revision` and `non_author_exact_candidate_revision`. Being a non-author does not identify the human owner; `human_contract: accepted_failure` describes the initial decision to make behavior durable, not acceptance of the finished revision. The current agent and validator already state the correct rule. No adoption bypass or wrong native decision has been demonstrated.

Rename the accepted approval value to state human acceptance of the exact candidate revision. If testing independent review for this material authority failure, represent that separate prerequisite explicitly rather than conflating it with promotion. Add closed-object positives/negatives for exact versus later revision and absent human acceptance. Keep the existing strict parser; it correctly enforces its supplied schema.

### AE-R02 — verify the graph lane before expanding its prose or authority

**Recommendation; Medium priority; high confidence in coverage gap; competence unverified.** Locations: agent `:32-36,54-56`; `agent-authoring/SKILL.md:103-109`; current agent-specific scenarios above.

The unique graph-design lane names typed state, concurrency, effects, approvals, durability, cancellation, and termination, but the two current cases test learning-loop decisions and a typo repair. A bounded design exercise should distinguish a roster graph from an executable graph and require a reviewable effect/UNKNOWN-reconciliation path, cancellation/recovery behavior, and termination condition without selecting a runtime or implementing code. Include an unsafe replay-after-checkpoint alternative as a counterexample. Use supplied state and a manual design rubric first; a paid native campaign needs separately selected scope and budget. Do not infer a need for a larger agent body or new runtime from this gap.

**Disposition:** one confirmed Low evaluator defect; two recommendations, including the reconciled AA-R2 lead; shared AA findings remain unduplicated. Preserve explicit tools, the research-only intended delegation, first-divergent-layer diagnosis, bounded comparable evaluation, taint preservation, exact-revision human promotion, and caller-owned review/implementation handoffs. `/root` should adjudicate and commit group 11 before continuing the agent audit.

## Central verification

The caller reconciled this report with the group and the [shared verification record](verification.md).
The recorded checks establish their bounded local claims; live-platform and native-model acceptance remain unverified.
