# Conditional rule map

> **Status: live.**
> This page routes a change to the source that owns its contract. It does not restate those
> contracts or create another approval layer. When this map and a source disagree, the source wins.

Start with [`AGENTS.md`](../AGENTS.md) for fleet authority and safety, and
[`CONTRIBUTING.md`](../CONTRIBUTING.md) for the repository-change workflow. Unfinished work exists
only in [`fleet-roadmap.md`](fleet-roadmap.md). Canonical behavior lives in [`agents/`](../agents),
[`skills/`](../skills), and [`commands/`](../commands); generated adapters are consequences.

## Baseline for a push

Run the tests affected by the change, regenerate any affected adapters, and finish with
`python scripts/gate_a.py`. Gate A checks structure; it does not replace component tests, evals, or
a review required by one of the conditional sources below.

## Read only the rows your change touches

| Change | Authoritative source | Existing enforcement or evidence |
|---|---|---|
| Agent, skill, command, manifest, or generated adapter | [Packaging ADR](decisions/2026-07-31-multi-platform-plugin-packaging.md), [`agent-authoring`](../skills/agent-authoring/SKILL.md), and the changed canonical source | `generate_platform_adapters.py`, `validate_fleet.py`, and platform/component tests |
| Agent metadata, tools, model, delegation, handoff, MCP, or memory | [`claude-code-frontmatter.md`](../skills/agent-authoring/references/claude-code-frontmatter.md), [local/external separation ADR](decisions/2026-07-31-local-external-research-separation.md), and [`AGENTS.md`](../AGENTS.md) | Fleet and platform-adapter validation |
| Guard policy, hooks, or guarded commands | [`readonly-guard.py`](../scripts/readonly-guard.py), [`hooks.json`](../hooks/hooks.json), and the [packaging ADR](decisions/2026-07-31-multi-platform-plugin-packaging.md) | Guard, hook, and platform tests |
| Dependency, test entrypoint, or Gate A-path import | [`requirements-dev.txt`](../requirements-dev.txt), [dependency ADR](decisions/2026-08-23-allow-third-party-dependencies.md), and [`AGENTS.md`](../AGENTS.md) Hard rules | CI validation jobs, `python -m pytest`, and Gate A |
| Routing description or other LLM-consumed contract | [`CONTRIBUTING.md`](../CONTRIBUTING.md) and [`evals/README.md`](../evals/README.md) | Focused red/green regression for a new contract; overlapping clean-room scenarios when routing behavior changes |
| Eval runner, grader class, or durable eval evidence | [`evals/README.md`](../evals/README.md) and the [rubric-judge evaluation ADR](decisions/2026-09-01-rubric-judge-evaluation-contract.md) | `evals/test_*.py`; human acceptance remains the only promotion authority |
| Runtime, tool, language, cloud, or infrastructure recommendation | [`stack-profile`](../skills/stack-profile/SKILL.md) | Load that skill before deciding; test a copied decision contract at its canonical source, not here |
| Production change, deployment, release, or live dashboard write | [`production-change-gate`](../skills/production-change-gate/SKILL.md), [`release-gate`](../skills/release-gate/SKILL.md), and the acting agent's authority | The selected gate owns approval, executor, evidence, and rollback requirements |
| Schema contract | [`schema-compatibility.md`](schema-compatibility.md) | Schema compatibility checks |
| Roadmap-linked probe | The active [`fleet-roadmap.md`](fleet-roadmap.md) item and its probe instrument | Evidence envelope; a probe never grants production authority |
| Docker-backed verification | [`docker-verification.md`](docker-verification.md) and the acting lane's authority | Bounded command evidence; static validation proves only the exercised boundary |
| Query catalog or observability reference | [`query-catalog.md`](../skills/obs-logs/references/query-catalog.md) and the changed observability source | Affected component tests |
| Operational learning, runbook, or knowledge disposition | [`operational-learning`](../skills/operational-learning/SKILL.md), [disposition policy](../skills/operational-learning/references/disposition-policy.md), and this directory's [authority map](README.md) | Affected component tests |
| Plan, specification, ADR, review, or historical evidence | This directory's [authority map](README.md) and the document's named owner | Link checks as applicable |
| Repository workflow, branching, or publishing | [`CONTRIBUTING.md`](../CONTRIBUTING.md) | Preserve unrelated work and published history; publishing remains a separate authorization |
| Commit or independent review inside the operator-tool pipeline | [`ops-tooling`](../skills/ops-tooling/SKILL.md) | That skill owns its explicit-grant and reviewer-independence boundaries |

## Mechanical checks

The scripts report violations; they do not create additional policy:

- `validate_fleet.py` and adapter generation enforce fleet shape and projection consistency.
- `check_links.py` enforces skill frontmatter grammar, bundle link containment, and live-doc link
  resolution.
- Guard and hook tests enforce the guarded-command boundary.
- `gate_a.py` composes the structural checks used before push.

If a new invariant is important enough to block a change, put it in its owning source and add one
focused failing-then-passing check. Add a row here only when contributors need a new route; do not
copy the invariant into this page, `AGENTS.md`, and `CONTRIBUTING.md`.

## Related

- Documentation authority: [`README.md`](README.md)
- Live backlog: [`fleet-roadmap.md`](fleet-roadmap.md)
