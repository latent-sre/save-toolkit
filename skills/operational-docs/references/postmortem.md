# Postmortem method

Start from the supplied incident timeline, severity, and root-cause evidence, including the
advisor's closeout packet and any `sre-assistant` slices. Given only an incident ID, ask for the
record rather than drafting placeholders. Resolved impact does not require a known cause:
mark unconfirmed causes `[unverified]` with an owner and next check; do not block the write-up on
certainty.

Use the [postmortem template](../assets/postmortem-template.md): full for P1/P2 or an explicit full
review; abbreviated for P3/P4 and near-misses unless policy or the owner requires full depth. Keep
unknown severity as YAML `null`; use full when evidenced impact was customer-visible or multi-service,
otherwise abbreviated. State that choice and reason, and confirm it with the owner before finalizing.

Fill the selected form's required facts from evidence. Missing facts stay `[unverified]`; genuinely
inapplicable requirements use `n/a — why`. Omit the unselected form and optional empty sections.
Use nullable times and keep impact end separate from human resolution confirmation.

## Causality and detection

For full causal analysis, choose and name a method suited to the evidence: Five Whys, a fault tree,
causal graph, or another method. Preserve branches and uncertainty rather than forcing a linear
story or line count. Explain decisions from the information available then, separating trigger,
mechanism, failed defenses, and system conditions; human error is not the root cause. Aim to reduce
recurrence or impact without promising zero recurrence.

"No data loss" needs evidence: name the row-count, checksum, write-path replay, or other check;
otherwise mark it `[unverified]`. Assess detection source, delay, available signals, and noise.
Human detection is not automatically a gap; propose `observability-engineer` follow-up only when
evidence supports an actionable earlier signal worth its paging cost.

## Actions and follow-ups

- Tag actions **mitigative** (impact/recovery) or **preventative** (recurrence), naming the risk
  reduced and remaining limits; no category quota. Each action needs an artifact, proof-of-done
  check, owner, due date, and tracking link.
- If proof depends on missing instrumentation, include the prerequisite and keep that action
  blocked until the signal, exporter, code, or pipeline/config change lands. Do not impose this
  dependency on unrelated actions.
- Route resilience and toil/automation design and economics to `reliability-engineer`, accepted
  implementation to `software-engineer`, detection/SLO to `observability-engineer`, open causal
  questions to `sre-assistant` (operational evidence) or `software-engineer` with `root-cause`
  (code), deploy/rollback safety to the human release owner, and operating documents to `scribe`.
- Keep one Follow-ups record with incoming IDs. A separately assigned
  [knowledge closeout](./knowledge-closeout.md) enriches those rows with artifact dispositions
  after the write-up; postmortem mode does not apply those changes by implication.

Include evidenced successes, gaps, and narrowly avoided failures ("where we got lucky"). A revealed
risk warrants a justified follow-up or explicit accepted risk, not an invented action to fill a
template.
