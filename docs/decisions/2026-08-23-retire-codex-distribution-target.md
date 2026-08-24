# Retire Codex as a distribution target; keep it as a way to work in this repository

- **Date:** 2026-08-23
- **Status:** Accepted
- **Decision owner:** `latent-sre`
- **Supersedes**, in each case *only as it concerns Codex* — every Claude and Copilot/VS Code clause
  in these records stands unchanged:
  - [`2026-07-31-multi-platform-plugin-packaging.md`](2026-07-31-multi-platform-plugin-packaging.md)
    clauses **3** (Codex named among the generated roots), **5** (Codex agents as standalone TOML
    with a conflict-safe installer), **6** (the Codex `agents/openai.yaml` invocation policy), and
    the **installer-collision** term of clause 7 — that installer is deleted here, so its collision
    behavior is no longer a structural gate. Clause 7's other terms (generated drift, manifest
    parity, hook wiring, authority, exact MCP grants) remain in force.
  - [`2026-07-31-local-external-research-separation.md`](2026-07-31-local-external-research-separation.md)
    clause **5** and its Codex consequence: with no generated Codex profiles, there is no profile to
    make the outer-isolation claim about. The local/external split itself is untouched and still
    enforced by tool absence on Claude.

  Deliberately **not** superseded: the rename ADRs
  ([`2026-08-04`](2026-08-04-observability-engineer-rename.md),
  [`2026-08-05`](2026-08-05-language-idiom-rename.md),
  [`2026-08-05-save-toolkit-rename.md`](2026-08-05-save-toolkit-rename.md)) mention Codex only as
  dated evidence of what those renames touched, and `docs/rules.md` requires leaving such records
  under their old vocabulary rather than rewriting recorded results.
  [`2026-08-01-local-sol-conformance.md`](2026-08-01-local-sol-conformance.md) is already
  superseded, [`2026-08-11-codex-terra-routing.md`](2026-08-11-codex-terra-routing.md) already
  records its evaluator as retired, and
  [`2026-08-11-immutable-release-promotion.md`](2026-08-11-immutable-release-promotion.md) governs
  release machinery that `main` retired independently in `1d9d8f7`.

## Decision

The fleet is no longer projected to Codex. `scripts/generate_platform_adapters.py` emits two
generated roots — `.github/agents/` and `platforms/copilot/skills/` — and both former Codex roots
are registered in `RETIRED_GENERATED_ROOTS` so a stale copy left on disk fails validation instead of
being silently loadable by a host.

**Codex remains a supported way to work in this repository.** The two uses are independent and were
conflated by the original packaging ADR:

| | Retired | Kept |
|---|---|---|
| Codex as a **distribution target** — the fleet installed *into* Codex | yes | — |
| Codex as an **agent working in this checkout** | — | yes |

The second needs none of the deleted bytes. Codex reads `AGENTS.md` files from the repository
directly: *"The scope of an AGENTS.md file is the entire directory tree rooted at the folder that
contains it… The contents of the AGENTS.md file at the root of the repo… are included with the
developer message"* (`codex-rs/core/gpt_5_1_prompt.md:17-27` at `rust-v0.148.0`; the same spec
appears in `gpt_5_2_prompt.md`). This repository's root `AGENTS.md` therefore loads automatically in
every Codex session here, carrying the unconditional fleet rules and the Windows
`python`-not-`python3` rule. Change-specific verification lives in
[`CONTRIBUTING.md`](../../CONTRIBUTING.md), **Change-specific evidence**. Nothing needs to be added
for that to keep working.

## Why

Not because the host is unhealthy. `@openai/codex` is actively maintained — 0.149.0 published
2026-08-20, ~67M downloads/month, repository pushed 2026-08-23. The pin this repository carried
(0.147.0) was 16 days behind, not abandoned. Any argument from upstream decay would be false.

The reason is cost against value **to this repository**:

- 138 files and ~14,250 lines, of which 11,035 lines were markdown — 26% of all tracked markdown —
  existing only to mirror content that is authored once.
- A 287-line conflict-safe installer and its test suite.
- A third `plugin.json` manifest in the parity contract and a fourth host in `fleet_doctor`.

Against that: the projection's own generated disclaimer states that Codex custom-agent TOML *has no
per-agent tool allowlist* and that local-only/external-only roles therefore *require outer network
or mount isolation*. The fleet's primary control — authority by tool absence — could never be
carried across. We were paying full projection cost for the weakest enforcement of any host.

## Consequences

- **No release-path change is carried here.** An earlier revision of this work also removed Codex
  from the release smoke and the host-install probe. Those surfaces were retired independently on
  `main` by `1d9d8f7` before this landed, so that work was dropped rather than merged; nothing in
  this ADR depends on it.
- **`EVAL-001` is retired** by owner disposition. Its only reopen trigger was a Codex/Sol behavioral
  baseline; with no fleet component running on Codex, that trigger cannot fire.
- **`fleet_doctor` loses its `host.codex.custom-agents` check** and the `codex` CLI row, both of
  which measured distribution state.
- **Codex commands stay rejected by the `fleet_doctor` read-only allowlist.** Retiring the target is
  not a reason to let a tool reach a real Codex home on the operator's machine.
- Host-adapter search collapses from three copies of `skills/` to two.

## Migration: this retirement is breaking for anyone who installed

Deleting the repository's projections cannot reach copies already written into a Codex home. The
conflict-safe installer that owned those copies — and was the only thing that could remove them
without touching unmanaged roles — is deleted by this change, so cleanup is a documented manual step
rather than a tool.

Measured before choosing that: no release tag has ever existed (local or remote), so the plugin was
never published, and the only install path was the previously documented
`install_codex_agents.py --target <project>/.codex/agents` run from a checkout. On the maintainer
machine at the time of writing, zero save-toolkit agents were installed.

**A managed file is one whose *entire first line* is exactly one of these:**

```
# Managed by save-toolkit scripts/install_codex_agents.py; do not edit.
# Managed by sre-agents scripts/install_codex_agents.py; do not edit.
```

> **Do not delete by filename, prefix, or partial match.** Codex resolves custom agents from one
> flat directory shared with every other installed suite. A sibling fleet writes
> `# Managed by sde-agents scripts/install_codex_agents.py; do not edit.` — `sde`, not `sre`, a
> **one-character** difference — and its roles include `prompt-engineer`,
> `repository-investigator`, and `researcher`, which share names with this fleet's. Match the whole
> line, and leave anything marked `sde-agents` alone.

Look in the user scope (`$CODEX_HOME/agents`, default `~/.codex/agents`) and in any project scope
that was passed to `--target` (typically `<project>/.codex/agents`). List before deleting:

PowerShell:

```powershell
$markers = @(
  '# Managed by save-toolkit scripts/install_codex_agents.py; do not edit.',
  '# Managed by sre-agents scripts/install_codex_agents.py; do not edit.'
)
# Only include the user scope that actually applies. Interpolating an unset $env:CODEX_HOME would
# yield '\agents', i.e. the root of the current drive -- not something to hand a delete loop.
$dirs = @()
if ($env:CODEX_HOME) { $dirs += (Join-Path $env:CODEX_HOME 'agents') }
else                 { $dirs += (Join-Path $HOME '.codex\agents') }
$dirs += '<project>\.codex\agents'      # repeat for each --target used; drop if never installed
$dirs = $dirs | Where-Object { Test-Path -LiteralPath $_ }

$owned = Get-ChildItem -LiteralPath $dirs -Filter *.toml |
  Where-Object { $markers -contains (Get-Content -LiteralPath $_.FullName -TotalCount 1) }
$owned | Select-Object -ExpandProperty FullName    # review this list first
$owned | Remove-Item -LiteralPath { $_.FullName }  # then remove exactly those files
```

POSIX shell (the retired installer was cross-platform Python, so a Linux or macOS install is the
ordinary case, not an edge one):

```sh
marker_current='# Managed by save-toolkit scripts/install_codex_agents.py; do not edit.'
marker_legacy='# Managed by sre-agents scripts/install_codex_agents.py; do not edit.'

for dir in "${CODEX_HOME:-$HOME/.codex}/agents" "<project>/.codex/agents"; do
  [ -d "$dir" ] || continue
  for f in "$dir"/*.toml; do
    [ -e "$f" ] || continue
    first=$(head -n 1 "$f")
    if [ "$first" = "$marker_current" ] || [ "$first" = "$marker_legacy" ]; then
      printf '%s\n' "$f"        # review first; then re-run with the next line uncommented
      # rm -- "$f"
    fi
  done
done
```

Both forms compare the **whole** first line: PowerShell's `-contains` and the shell's `[ "$first" =
... ]` are equality, not pattern matching. A `-match`, `-like`, `case`, or `grep` filter would
reintroduce the partial-match hazard the warning above describes. `-LiteralPath` and `--` keep a
filename containing `[`, `]`, `*`, or `-` from being treated as a pattern or an option.

If the skills plugin was ever registered, also run:

```
codex plugin remove save-toolkit@latent-sre
codex plugin marketplace remove latent-sre
```

## Alternatives considered

- **Keep generating, stop testing.** Rejected: an unproven projection is worse than none — it looks
  installable and nothing shows when it rots.
- **Keep `.codex/agents/`, drop the skills projection.** Rejected: the TOML agents reference skills
  the host would no longer have, and the flat global agent namespace collides with other installed
  suites, which was already an observed problem.
- **Stop generating but leave the committed bytes.** Rejected outright — that is exactly the stale
  retired root `RETIRED_GENERATED_ROOTS` exists to fail on.

## Rollback

`git revert` this change's commits, then run `python scripts/generate_platform_adapters.py --write`.
The generated bytes are reproducible from canonical source by construction, so no Codex artifact
needs to be recovered from history — only the generator's Codex code paths, the installer, and the
`fleet_doctor` wiring do.

Restoring Codex as a distribution target requires a new accepted decision that names: the enforcement
story for local-only and external-only roles on a host with no per-agent tool allowlist,
and an owner for the projection's upkeep.
