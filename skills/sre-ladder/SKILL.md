---
name: sre-ladder
description: >-
  Help an SRE choose the investigation depth for an active alert or incident, especially when
  deciding whether to continue first response, begin hypothesis-driven investigation, or examine a
  systemic multi-service failure. Triggers: 'what incident mode is this', 'is first response still
  enough', 'does this need systemic analysis'. Not for engineering seniority or design rigor
  (eng-ladder), incident command or communications (incident-command), or resolved-incident
  documentation.
---

# SRE ladder

Select an **incident work mode**, not a person's title or seniority. The typed `sre` agent remains
the fleet owner of the technical investigation through verified recovery while assisting the human
SRE and incident team. This skill changes investigation depth only; it grants no tools, production
authority, command role, or permission to apply a mitigation.

## Select from current evidence

Start with the least-deep mode supported by the evidence. Read only that mode's reference, then
change modes when an observed predicate below becomes true. Do not preload neighboring modes as a
checklist.

| Evidence now | Mode and reference |
|---|---|
| A new alert or report is untriaged, impact is not bounded, or a documented procedure may apply | **First response** — read [first-response](./references/first-response.md) |
| The symptom is confirmed and the next task is to distinguish candidate causes with evidence | **Hypothesis investigation** — read [hypothesis-investigation](./references/hypothesis-investigation.md) |
| Evidence shows multi-service or shared-dependency scope, a cascade, retry storm, saturation collapse, feedback loop, or metastability | **Systemic failure** — read [systemic-failure](./references/systemic-failure.md) |

Signal characterization is a companion, not a higher mode. When exact start time, blast radius,
trend, or the baseline golden signals are missing, also read
[signal-characterization](./references/signal-characterization.md). Do not load it merely to repeat
signal definitions already established in the incident record.

## Preserve the incident spine

At every mode, keep these fields current and evidence-labelled; use `[unverified]` instead of
inventing a value:

- severity and user impact;
- blast radius and trend;
- UTC timeline;
- hypotheses with evidence for and against;
- mitigation already performed by a human or recommended for human execution.

The mode changes what evidence to seek, not who acts. Severity, roles, communications, and the
authoritative command timeline belong to `incident-command`; causal testing uses `root-cause`;
production effects remain human-executed under the existing gate. A resolved incident exits this
ladder before postmortem or operational closeout begins.
