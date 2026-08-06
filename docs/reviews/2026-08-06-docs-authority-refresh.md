# Docs authority refresh — 2026-08-06

- Date: 2026-08-06
- Status: evidence/history (not a task list; live unfinished work stays in `docs/fleet-roadmap.md`)
- Scope: inventory of `docs/` authority, living Rules catalog, and stale live-claim hygiene

## Outcome

- Added the living Rules catalog at [`../rules.md`](../rules.md) and registered it in
  [`../README.md`](../README.md) as a live reference contract.
- Fixed stale live claims in root [`README.md`](../../README.md) Current status and in packaging /
  observability / language-idiom ADRs (paths, owners, citations).
- Accepted [`../decisions/2026-08-05-save-toolkit-rename.md`](../decisions/2026-08-05-save-toolkit-rename.md)
  so the plugin rename has a decision record; the naming-audit review remains evidence.
- Kept all historical plans, specs, reviews, `AUDIT`, and `RESEARCH` in place.

## What makes us good (preserve)

| Strength | Why it stays |
|---|---|
| Single live backlog + `check_plan_status.py` | Stops finished checklists from re-entering the queue |
| Authority map in `docs/README.md` | Separates live / decisions / reviews / dated evidence |
| Canonical-then-generate | One fleet; host adapters are consequences |
| Dual enforcement honesty | Tool absence + Claude guard; host non-equivalence stated |
| Evidence labels + dispositions as repo state | Learning is reviewable, not model memory |
| Gate A as the one structural entrypoint | Anti-drift: no transcribed step lists in docs |

## What restricts us (intentional — surface, do not dilute)

| Constraint | Why it stays |
|---|---|
| stdlib-only under `scripts/` | Every host package must validate anywhere Python does |
| No `model:` pins; inert plugin-agent keys forbidden | Pins and fake controls go stale silently |
| Agents never apply Tier 2/3 / prod changes | Human + protected environments are the real boundary |
| Researcher / investigator split | Local/external trust zones; sanitization is cooperative |
| Publication blocked on HOST-001 → RELEASE-001 | Protection is already closed; promotion is not |
| Stack stay-in-lane (`stack-profile`) | PCF/TAS lane; no K8s / infra-layer recommendations |
| Historical checklists must not re-queue | Roadmap is the only unfinished-work registry |

Full rule index: [`../rules.md`](../rules.md).

## Keep / needed vs not needed

| Class | Verdict | Notes |
|---|---|---|
| `docs/README.md` | **Needed** | Authority map; updated this pass |
| `docs/rules.md` | **Needed (new)** | Living must-follow index |
| `docs/fleet-roadmap.md` | **Needed** | Only live backlog |
| `docs/schema-compatibility.md` | **Needed** | Live contract |
| `docs/verification-sandbox.md` | **Needed** | Live contract |
| `docs/decisions/*` (accepted) | **Needed** | Governing decisions; owners/paths refreshed |
| `docs/reviews/*` | **Keep** | Closure evidence; never a task list |
| `docs/superpowers/plans|specs/*` | **Keep** | Bannered history; gated; do not execute |
| `docs/AUDIT-2026-07-12.md` | **Keep (archive candidate)** | Dated snapshot; OPEN labels are not today's queue |
| `docs/RESEARCH.md` | **Keep (archive candidate)** | Provenance; re-verify before relying |

## Archive candidates (do not delete in this pass)

1. **[`../AUDIT-2026-07-12.md`](../AUDIT-2026-07-12.md)** — fully superseded roster/skill counts; retain
   until a maintainer wants a smaller tree.
2. **[`../RESEARCH.md`](../RESEARCH.md)** — provenance snapshot; retain; re-verify before use.
3. **`docs/superpowers/plans|specs/*`** — bannered history already enforced by
   `check_plan_status.py`; no move needed.
4. Older ADR wording that still said `sre-agents` paths/owners — **amended in place**, not archived.

## Verification

- Structural: `python scripts/gate_a.py` after the hygiene commit.
- Link health: `rules.md`, this review, and the save-toolkit rename ADR are reachable from
  `docs/README.md` / ADR citations.
