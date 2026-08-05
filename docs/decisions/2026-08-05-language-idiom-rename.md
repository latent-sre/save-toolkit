# ADR: Rename the `craft` skill to `language-idiom`

- Date: 2026-08-05
- Status: Accepted
- Decision owners: save-toolkit maintainers

## Context

The `craft` skill sat in an apparent family with `backend-craft` and `frontend-craft`. Analysis of
how `sde` — its only consumer among the agents — actually loads the three showed the family is
false:

- `backend-craft` and `frontend-craft` are **layer** playbooks (design-altitude: endpoints,
  resiliency, UI state), siblings of `ops-tooling`, which carries no `-craft` suffix.
- `craft` is the orthogonal **language** axis (file-altitude: idiom, tooling, tests-first,
  behavior-preserving refactoring), loaded *alongside* a layer skill, not instead of one. Its load
  condition in `sde`'s required-skills list — "the file being changed" — trips on every code file,
  so a backend Go task loads `backend-craft` **and** the Go language file together.

The shared suffix asserted kinship where the real relationship is orthogonality. The fleet paid for
that correction in prose: three `Ownership map only—not a load` disclaimers, an "ownership label,
not a load" apology in `ops-tooling`, and "this skill neither preloads nor loads craft" — a
perimeter of signs pointing away from a skill that looked like the parent of its non-siblings.

`craft` ⊂ `backend-craft`/`frontend-craft` was also the fleet's last remaining component-name
substring collision (see the `observability-engineer` and `save-toolkit` ADRs for why that class
bites), latent rather than live: the Codex generator's backtick rewrite covers agent names only,
and no eval grader asserted the bare word.

## Decision

1. Rename the skill to `language-idiom`. The name is the fleet's own vocabulary — "language idiom"
   is the exact phrase three skills already used when disambiguating against this one — and it
   deliberately sits outside the `-craft` suffix family, the way `ops-tooling` already does,
   marking the axis contrast instead of a false kinship.
2. Keep the 6→1 consolidation. `tdd.md` (27 lines) and `safe-refactor.md` (26 lines) stay bundled:
   they have exactly one consumer path, load at the same moment as the language files, and `tdd.md`
   is deliberately coupled to them ("tdd owns the *method*; the language file owns the *tooling*").
   Re-splitting would add routing-surface cost (all skill descriptions share one listing cap) to
   break a designed coupling.
3. Fix the load-protocol defect in `sde.md`: the layer skill and the language file load **together**
   ("both axes"), replacing an "or" phrasing that read as pick-one and contradicted the
   required-skills list.
4. Resolve the TypeScript ownership contradiction in favor of **two-load**, aligning descriptions
   to the bodies: `frontend-craft` claimed to own "TypeScript/React idiom whole" while
   `language-idiom/references/typescript.md` said the universal rules live with the language files.
   Probing `frontend-craft`'s actual content settled it — it contains none of the universal TS
   rules (strict mode, discriminated unions, `unknown` narrowing), so the "whole" claim was
   unbacked and a one-load design would silently drop those rules for UI work. `frontend-craft` now
   claims UI-layer TS/React idiom only, and both descriptions state that the two skills load
   together for UI TypeScript.
5. Do **not** add `craft` to the stale-name list. Probed: the boundary regex would flag 19
   legitimate prose uses ("# Frontend craft", "reads as noise rather than craft"). A common English
   word cannot be machine-protected after retirement — recorded in `check_stale_names.py` as a
   naming lesson. Drift to the old name is caught by the adapter byte-for-byte check and the
   `language-idiom-router-go` eval instead.

## Alternatives considered

- **`language-craft`:** rejected. Keeps the suffix that miscommunicates the relationship; the
  analysis showed the name should mark the contrast (layer vs. language axis), not the kinship.
- **`code-idiom` / `code-craft` / `developer-idiom`:** rejected. "Code" and "developer" describe
  everything the consuming agent touches — words true of every skill in the roster carry no routing
  signal. "Developer" additionally names the consumer rather than the content and appears nowhere
  in fleet vocabulary. Consumer-derived names also trend toward embedding agent names
  (`sde-idiom`), which recreates the agent⊂skill substring class.
- **Re-splitting `tdd`/`safe-refactor` into skills:** rejected (Decision 2). They were standalone
  skills once and were deliberately consolidated in the plugin packaging; `STALE` enforces the
  retirement.
- **Keep the name, fix only the defects:** rejected. Leaves the last substring collision latent
  forever on a name that can never be stale-listed.

## Consequences

- Component names are now pairwise substring-free across the fleet (agents, skills, commands,
  plugin) — verified by exhaustive pairwise check.
- The disclaimers become self-documenting: "language idiom remains the caller's responsibility —
  see the `language-idiom` skill" needs no apology clause.
- UI TypeScript work is explicitly a two-skill load. That is one more load than the old
  description implied, and it is what the bodies always required; the descriptions no longer
  promise otherwise.
- Anyone with muscle memory for `save-toolkit:craft` gets a failed load, not a silent miss — the
  build cannot backstop this one (Decision 5), so review is the guard for reintroductions.

## Rollback

Revert the skill directory, `sde.md`, the sibling-skill descriptions, the eval, and this ADR
together, then regenerate adapters. The `sde.md` "both axes" fix and the `frontend-craft`
description narrowing stand on their own evidence and should be kept even on rollback of the name.
