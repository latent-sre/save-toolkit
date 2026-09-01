# SKILL-001 — obs-alerting disposition

> **Conclusion:** `[verified]` `obs-alerting` remains the alert/SLO policy router. Generic SLI and
> worked burn-window recitation was removed while the pressure-dropped burn definition, paging,
> verification, authority, ownership, and routing contracts stayed explicit.

## Decision and exact revision

- Exact base: `fd1d8bbae0b20b0db885cb2fb4386a6e20e6fb24`.
- Exact candidate: `9d1e4766e8cf1ff4b232ad9bbba8d9b0d6d76dbf`.
- Canonical candidate blob: `7a8f4daa4a331b06dcfcb41e254e62cae8d81392`.
- Entrypoint: 7,930 → 5,804 immutable bytes (-2,126, -26.8%).
- Conditional references: unchanged at 32,843 bytes.
- Routing description: byte-identical.
- No test, eval scenario, calculator, or conditional reference was removed.

## Probe evidence

Five independent fresh `gpt-5.6-terra` forks reviewed the same alert proposal without repository,
memory, web, tools, or retries. The frozen prompt, rubric, raw responses, and scorecard are private
evidence under `.eval-runs/obs-alerting-workspace/probes/`.

Every run supplied nine of ten behaviors: good/valid-event SLI, request-unit error budget, paired
window AND, current-burn versus spent-budget separation, scheduled-job staleness/no-data, symptom
rather than assumed CPU-cause paging, fire/resolve verification, controlled non-production delivery,
owner, and runbook. All five omitted the exact definition `observed bad fraction / allowed bad
fraction`. The entrypoint therefore retains that definition while routing the generic SLI
construction and worked examples to the conditional burn-rate reference.

These probes measure content recall only. Provider cost and independently verified resolved-model
identity were unavailable; they are not native-plugin discovery or promotion evidence.

## Retained contract

- User-visible SLI population and unit discipline.
- Exact burn definition and paired-window semantics.
- No-data and scheduled-work treatment.
- Page on symptoms rather than assumed causes.
- Controlled non-production fire/delivery/resolve verification.
- Named owner, actionable runbook, evidence labels, and lane boundaries.
- Grafana/Splunk/Moogsoft/ThousandEyes details remain conditional.

## Verification and non-actions

The candidate was generated into the Copilot projection and passed its focused checks before
integration. The combined branch subsequently passed all 39 active component entrypoints and Gate A
8/8. A later exact-candidate native batch routed all three discovery trials to `obs-alerting` but
scored 0/3 because the prompt supplied no route while the grader demanded one and rejected two
Markdown-formatted named routes. That no-go remains authoritative; an offline repair now supplies
fixed fictional route/runbook values and preserves placeholder rejection. See the
[eval repair](2026-09-01-skill-001-obs-eval-repair.md). No live alert, notification route,
credential, push, or PR was changed by this disposition. Human acceptance of the exact PR revision
remains the promotion gate.
