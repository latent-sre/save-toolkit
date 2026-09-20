# Bounded CI runs

Read before submitting or rerunning remote validation. Use the caller's authorized scope and
current agent/host permissions. An existing request covering the run is sufficient; do not ask
for the same approval again. Local-edit or local-test permission alone does not authorize a remote run.

1. **Bind the target and effects.** Inspect the repository, workflow, selected ref and resolved
   commit, inputs, jobs, called workflows/actions, runner access, permissions, credential scopes
   and downstream `workflow_run` consumers from the **current default branch**, even when the
   candidate removes them: their branch filters select the upstream run, not the consumer's source.
   Follow their called workflows/actions at the revisions GitHub will actually use; same-repository
   relative reusable workflows use the caller's commit, while explicit `@ref` calls use that ref.
   Reuse matching established evidence rather than
   re-auditing unchanged dependencies. Every reachable effect must be authorized validation,
   CI artifacts or status reporting. Deployment, release/package publication, environment approval,
   protection changes and privileged untrusted-code execution are outside this permission; hand
   off without submitting. Unknown effects or unavailable definitions leave submission pending;
   continue authorized local checks.
2. **Account for reruns.** Bind the run ID, original commit/ref and actor's privileges, selected
   jobs and downstream effects, not the current branch or requesting actor. Rerunning a failed job
   can still trigger a downstream workflow; its name is not an effect boundary.
   Re-running all jobs re-resolves non-SHA reusable-workflow refs; failed/specific-job reruns retain
   their first attempt's workflow SHA. Check those dependency revisions as well as the parent commit.
3. **Use existing access.** Use scoped CI authentication without reading or printing secret values.
   Never broaden credentials, change protection settings or bypass a denied tool. Recheck the
   selected revision and material preflight facts immediately before submission; changes require
   renewed inspection. For dispatch, a preflight SHA check and later run-SHA comparison cannot prevent
   ref movement between inspection and execution. Use a supported branch/tag with established
   movement controls or coordinated ref freeze until the matching run receipt binds execution to
   the reviewed commit. Cover mutable dependency and default-branch consumer refs through their
   own event resolution. A unique tag name alone is insufficient; raw commit SHA dispatch is not a
   documented API contract. If those bindings cannot be established, hand off without submitting;
   this permission does not authorize creating refs or changing protection settings to obtain them.
   The skill grants no tool or host permission.
4. **Submit once and reconcile.** Record run ID/attempt; verify the actual commit, jobs and result
   before claiming candidate success. A mismatched commit does not verify the candidate. A timeout
   without a receipt leaves submission UNKNOWN: reconcile run history before retrying and return
   the gap if the outcome cannot be established. Keep retries within the authorized scope.

Report execution and required-check eligibility separately. A green `workflow_dispatch` run can
validate the candidate without satisfying the PR's required status check in a branch ruleset;
check the triggering event and actual PR/ruleset result before claiming that gate passed. A CI-only
run is not production-deployment evidence. The human release owner retains deployment and
publication execution under the existing process.

Sources: [rerun semantics](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs),
[reusable-workflow reruns](https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations#behavior-of-reusable-workflows-when-re-running-jobs),
[workflow_run effects](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_run),
[reusable-workflow reference selection](https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows#calling-a-reusable-workflow),
[dispatch ref contract](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event),
and [required-check eligibility](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks#checks-from-some-workflow-jobs-are-not-evaluated).
